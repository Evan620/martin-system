"""
SupervisorLoop — replaces the 5-node LangGraph supervisor graph.
"""
from __future__ import annotations

import asyncio
import json
import re
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

    async def run(
        self,
        query: str,
        thread_id: str,
        twg_id: Optional[str] = None,
        user_timezone: Optional[str] = None,
        stream_callback: Optional[Callable] = None,
    ) -> AgentResponse:
        if twg_id:
            forced = get_agent_id_by_twg_id(twg_id)
            if forced and forced in self.twg_agents:
                logger.info(f"[SUPERVISOR] RBAC → {forced}")
                return await self.twg_agents[forced].run(
                    query, thread_id, user_timezone=user_timezone,
                    stream_callback=stream_callback,
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
    ) -> AsyncGenerator[Dict, None]:
        tokens: asyncio.Queue = asyncio.Queue()

        async def on_token(t: str):
            await tokens.put({"type": "token", "content": t})

        async def run_task():
            resp = await self.run(query, thread_id, twg_id, user_timezone, stream_callback=on_token)
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
