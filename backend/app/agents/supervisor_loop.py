"""
SupervisorLoop — replaces the 5-node LangGraph supervisor graph.
"""
from __future__ import annotations

import asyncio
import copy
import json
import re
import uuid
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional

from loguru import logger

from app.agents.agent_loop import AgentLoop, AgentResponse
from app.agents.utils import get_agent_id_by_twg_id


_CLASSIFY_PROMPT = """You are a routing assistant. Given the user query, decide which agent should handle it.

Available agents:
- "supervisor": general secretariat questions, cross-cutting topics, scheduling, emails, documents
- "energy": energy trade, industrial growth, power infrastructure
- "agriculture": agribusiness, food systems, farming
- "minerals": strategic minerals, natural resources
- "digital": digital transformation, technology
- "protocol": summit protocol, diplomatic procedures
- "resource_mobilization": funding, financing, resource mobilization

If the query clearly spans exactly two pillars, return both agent ids.
Otherwise pick the single best match.

Respond with ONLY valid JSON. Examples:
{{"agent": "agriculture"}}
{{"agent": "supervisor"}}
{{"agents": ["energy", "minerals"]}}

Query: {query}"""


class SupervisorLoop:
    def __init__(
        self,
        llm: Any,
        twg_agents: Dict[str, Any],
        supervisor_agent: Optional[Any] = None,
    ):
        self.llm = llm
        self.twg_agents = twg_agents
        self.supervisor_agent = supervisor_agent

    def _build_member_agent(self, twg_id: Optional[str]):
        """Build a per-request, member-scoped agent bound to the CALLER's twg_id.

        The "member" agent is not pillar-mapped, so a statically-registered member
        agent would have twg_id=None and be denied the TWG-scoped member reads. We
        therefore construct it per-request with the caller's twg_id so
        get_tools_for_agent("member", twg_id) grants those reads while facilitator/
        admin tools stay denied (tool_registry's agent_id=="member" gate).
        """
        from app.agents.langgraph_base_agent import LangGraphBaseAgent
        member_agent = LangGraphBaseAgent(
            agent_id="member", keep_history=True, twg_id=twg_id,
        )
        return member_agent._loop

    def _build_scoped_pillar_agent(self, agent_id: str, twg_id: str):
        """Build a pillar agent bound to the exact authorized request TWG.

        Cached pillar agents resolve their scope from the pillar and may bind to
        the first database row when multiple TWGs share that pillar. Scoped
        requests must instead carry their authorized UUID through to every tool.
        AgentLoop history remains keyed by thread_id, so constructing this wrapper
        per request does not discard the conversation.
        """
        cached_loop = self.twg_agents[agent_id]
        scoped_loop = copy.copy(cached_loop)
        scoped_loop.tools = list(cached_loop.tools)
        scoped_loop.tool_map = dict(cached_loop.tool_map)
        scoped_loop.twg_id = twg_id
        return scoped_loop

    async def _thread_user_has_twg_access(
        self, thread_id: str, twg_id: str, auth_binding_token: Optional[str] = None
    ) -> bool:
        """Authorize an exact TWG scope from the thread-bound user context.

        This is deliberately independent of route checks because supervisors can
        be called from non-route paths. A missing/invalid context fails closed.
        """
        from sqlalchemy import select

        from app.core.database import get_db_session_context
        from app.models.models import UserRole, twg_members
        from app.tools._rbac import get_thread_user_context

        context = get_thread_user_context(thread_id, auth_binding_token)
        if context is None:
            return False

        user_id, role = context
        if role in (UserRole.ADMIN, UserRole.SECRETARIAT_LEAD):
            return True
        if role not in (UserRole.TWG_FACILITATOR, UserRole.TWG_MEMBER):
            return False

        try:
            user_uuid = uuid.UUID(str(user_id))
            twg_uuid = uuid.UUID(str(twg_id))
        except (TypeError, ValueError, AttributeError):
            return False

        try:
            async with get_db_session_context() as db:
                result = await db.execute(
                    select(twg_members.c.user_id).where(
                        twg_members.c.user_id == user_uuid,
                        twg_members.c.twg_id == twg_uuid,
                    )
                )
                return result.scalar_one_or_none() is not None
        except Exception as exc:
            logger.error(f"[SUPERVISOR] TWG scope authorization failed: {exc}")
            return False

    async def run(
        self,
        query: str,
        thread_id: str,
        twg_id: Optional[str] = None,
        user_timezone: Optional[str] = None,
        stream_callback: Optional[Callable] = None,
        force_agent_id: Optional[str] = None,
        auth_binding_token: Optional[str] = None,
    ) -> AgentResponse:
        if twg_id and not await self._thread_user_has_twg_access(
            thread_id, twg_id, auth_binding_token
        ):
            logger.warning(
                f"[SUPERVISOR] Denied unauthorized request scope: twg_id={twg_id}"
            )
            return AgentResponse(
                content="Access denied: unauthorized TWG scope.",
                agent_id="supervisor",
            )

        # Member-scoped routing (the safety line): a TWG_MEMBER chat runs under the
        # "member" agent (gated to MEMBER_TOOLS) bound to the caller's twg_id —
        # NOT the pillar/facilitator agent. Bypasses the twg_id → pillar routing below.
        if force_agent_id == "member":
            logger.info(f"[SUPERVISOR] Member-scoped routing → member (twg={twg_id})")
            member_loop = self._build_member_agent(twg_id)
            return await member_loop.run(
                query, thread_id, user_timezone=user_timezone,
                stream_callback=stream_callback,
                auth_binding_token=auth_binding_token,
            )

        if twg_id:
            forced = get_agent_id_by_twg_id(twg_id)
            if forced and forced in self.twg_agents:
                logger.info(f"[SUPERVISOR] RBAC → {forced} (request-scoped TWG)")
                scoped_loop = self._build_scoped_pillar_agent(forced, twg_id)
                return await scoped_loop.run(
                    query, thread_id, user_timezone=user_timezone,
                    stream_callback=stream_callback,
                    auth_binding_token=auth_binding_token,
                )
            else:
                logger.warning(f"[SUPERVISOR] RBAC failure: twg_id={twg_id}")
                return AgentResponse(content="Access denied: TWG not found.", agent_id="supervisor")

        target = await self._classify_intent(query)
        logger.info(f"[SUPERVISOR] Routing → {target}")

        if isinstance(target, list):
            return await self._dispatch_multiple(target, query, thread_id, user_timezone)

        if target in self.twg_agents:
            return await self.twg_agents[target].run(
                query, thread_id, user_timezone=user_timezone,
                stream_callback=stream_callback,
            )

        if self.supervisor_agent:
            return await self.supervisor_agent.run(
                query, thread_id, user_timezone=user_timezone,
                stream_callback=stream_callback,
            )
        return AgentResponse(content="No agent available to handle this query.", agent_id="supervisor")

    async def stream(
        self,
        query: str,
        thread_id: str,
        twg_id: Optional[str] = None,
        user_timezone: Optional[str] = None,
        force_agent_id: Optional[str] = None,
        auth_binding_token: Optional[str] = None,
    ) -> AsyncGenerator[Dict, None]:
        tokens: asyncio.Queue = asyncio.Queue()

        async def on_token(t: str):
            await tokens.put({"type": "token", "content": t})

        async def run_task():
            resp = await self.run(
                query, thread_id, twg_id, user_timezone,
                stream_callback=on_token, force_agent_id=force_agent_id,
                auth_binding_token=auth_binding_token,
            )
            # The API route (POST /agents/chat/stream) only understands
            # "final_response" — a bare "done" carrying the AgentResponse was
            # silently dropped, so the client never received the answer.
            await tokens.put({
                "type": "final_response",
                "content": {"response": resp.content, "citations": resp.citations},
            })
            await tokens.put({"type": "done", "response": resp})

        task = asyncio.create_task(run_task())
        while True:
            event = await tokens.get()
            yield event
            if event["type"] == "done":
                break
        await task

    async def _classify_intent(self, query: str) -> str | List[str]:
        prompt = _CLASSIFY_PROMPT.format(query=query[:500])
        try:
            result = await self.llm.complete(
                messages=[{"role": "user", "content": prompt}],
                tools=None,
                system_prompt=None,
            )
            raw = result.get("content", "") if isinstance(result, dict) else str(result)
            raw = re.sub(r"```json|```", "", raw).strip()
            parsed = json.loads(raw)
            if "agents" in parsed:
                return parsed["agents"]
            return parsed.get("agent", "supervisor")
        except Exception as e:
            logger.warning(f"[SUPERVISOR] Classify failed ({e}), falling back to supervisor")
            return "supervisor"

    async def _dispatch_multiple(
        self,
        agent_ids: List[str],
        query: str,
        thread_id: str,
        user_timezone: Optional[str],
    ) -> AgentResponse:
        valid_ids = [a for a in agent_ids if a in self.twg_agents]
        if not valid_ids:
            return AgentResponse(content="No valid agents found for this query.", agent_id="supervisor")

        tasks = [
            self.twg_agents[aid].run(query, f"{thread_id}_{aid}", user_timezone=user_timezone)
            for aid in valid_ids
        ]
        responses: List[AgentResponse] = await asyncio.gather(*tasks)
        return self._synthesize(responses)

    def _synthesize(self, responses: List[AgentResponse]) -> AgentResponse:
        if len(responses) == 1:
            return responses[0]
        parts = []
        for r in responses:
            parts.append(f"**{r.agent_id.replace('_', ' ').title()} perspective:**\n{r.content}")
        combined = "\n\n".join(parts)
        all_citations = [c for r in responses for c in r.citations]
        all_tools = [t for r in responses for t in r.tool_calls_made]
        return AgentResponse(
            content=combined,
            agent_id="multi",
            citations=all_citations,
            tool_calls_made=all_tools,
        )
