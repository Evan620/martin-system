"""
LangGraphBaseAgent — backward-compatible wrapper around AgentLoop.

Public API is unchanged; internals replaced with tight while loop.
LangGraph is no longer used — the name is kept for caller compatibility.
"""
from __future__ import annotations

import time
from typing import Any, AsyncGenerator, Dict, List, Optional

from loguru import logger

from app.agents.agent_loop import AgentLoop, AgentResponse
from app.agents.prompts import get_prompt
from app.agents.utils import get_twg_id_by_agent_id
from app.services.llm_service import get_llm_service
from app.tools.tool_registry import get_tool_registry


_NOTIFICATION_CACHE_TTL = 30  # seconds


class LangGraphBaseAgent:
    """Thin wrapper — delegates to AgentLoop."""

    _notification_cache: Dict[str, tuple] = {}

    def __init__(
        self,
        agent_id: str = "supervisor",
        keep_history: bool = True,
        max_history: int = 20,
        session_id: Optional[str] = None,
        use_redis: bool = False,
        memory_ttl: Optional[int] = None,
    ):
        self.agent_id = agent_id
        self.session_id = session_id or "default"
        self.keep_history = keep_history
        self.max_history = max_history

        self.twg_id = get_twg_id_by_agent_id(agent_id)
        self.system_prompt = get_prompt(agent_id)
        self.llm_service = get_llm_service()

        registry = get_tool_registry()
        self.tools_def, self.tool_map = registry.get_tools_for_agent(
            agent_id=agent_id, twg_id=self.twg_id
        )
        self._tool_registry = registry

        self._loop = AgentLoop(
            agent_id=agent_id,
            system_prompt=self.system_prompt,
            tools=self.tools_def,
            tool_map=self.tool_map,
            llm=self.llm_service,
            twg_id=self.twg_id,
            max_iterations=10,
            max_history=max_history,
        )

        logger.info(f"[{agent_id}] LangGraphBaseAgent initialised (AgentLoop backend)")

    # ------------------------------------------------------------------
    # Public API (unchanged signatures)
    # ------------------------------------------------------------------

    def add_tool(self, tool_func) -> None:
        """Backward-compat: add a function as a tool."""
        import inspect
        func_name = tool_func.__name__
        doc = (tool_func.__doc__ or "").strip()
        sig = inspect.signature(tool_func)
        params: Dict[str, Any] = {}
        required: List[str] = []
        for name, param in sig.parameters.items():
            ptype = "string"
            if param.annotation == int:
                ptype = "integer"
            elif param.annotation == bool:
                ptype = "boolean"
            params[name] = {"type": ptype, "description": f"Parameter {name}"}
            if param.default == inspect.Parameter.empty:
                required.append(name)
        tool_def = {
            "type": "function",
            "function": {
                "name": func_name,
                "description": doc,
                "parameters": {"type": "object", "properties": params, "required": required},
            },
        }
        self.tools_def.append(tool_def)
        self.tool_map[func_name] = tool_func
        self._loop.tools = self.tools_def
        self._loop.tool_map = self.tool_map
        logger.info(f"[{self.agent_id}] Added tool: {func_name}")

    async def chat(
        self,
        message: str,
        thread_id: Optional[str] = None,
        user_timezone: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Non-streaming chat — returns dict with response/citations."""
        message = await self._inject_notifications(message)
        thread = thread_id or self.session_id
        logger.info(f"[{self.agent_id}:{thread}] Received: {message[:100]}...")

        resp: AgentResponse = await self._loop.run(
            query=message,
            thread_id=thread,
            user_timezone=user_timezone,
        )
        return {
            "response": resp.content,
            "citations": resp.citations,
            "agent_id": self.agent_id,
            "conversation_id": thread,
            "suggestions": [],
        }

    async def stream_chat(
        self,
        message: str,
        thread_id: Optional[str] = None,
        user_timezone: Optional[str] = None,
    ) -> AsyncGenerator[Dict, None]:
        """Streaming chat — yields SSE event dicts."""
        message = await self._inject_notifications(message)
        thread = thread_id or self.session_id
        async for event in self._loop.stream(message, thread, user_timezone=user_timezone):
            yield event

    async def process_query(
        self,
        query: str,
        thread_id: Optional[str] = None,
        user_timezone: Optional[str] = None,
    ) -> str:
        """Simple string-return interface (used by supervisor dispatch)."""
        resp = await self._loop.run(
            query=query,
            thread_id=thread_id or self.session_id,
            user_timezone=user_timezone,
        )
        return resp.content

    async def resume_chat(self, thread_id: str, resume_value: Dict) -> str:
        """No-op stub — interrupt/approval flow not used in AgentLoop."""
        logger.info(f"[{self.agent_id}] resume_chat called (no-op in AgentLoop backend)")
        return "Resumption not supported in this version."

    def reset_history(self, thread_id: Optional[str] = None) -> None:
        tid = thread_id or self.session_id
        AgentLoop._history.pop(tid, None)
        logger.info(f"[{self.agent_id}:{tid}] History cleared")

    def clear_history(self, thread_id: Optional[str] = None) -> None:
        self.reset_history(thread_id)

    def get_agent_info(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "agent_type": "AgentLoop",
            "tools": [t["function"]["name"] for t in self._loop.tools],
            "twg_id": self.twg_id,
            "session_id": self.session_id,
        }

    def get_graph_visualization(self) -> str:
        return "AgentLoop (no graph — tight while loop)"

    # ------------------------------------------------------------------
    # Notification injection (preserved from original)
    # ------------------------------------------------------------------

    async def _inject_notifications(self, message: str) -> str:
        """Append pending TWG notifications to the message context."""
        try:
            twg_id_str = self.twg_id
            if not twg_id_str:
                return message

            cache_entry = LangGraphBaseAgent._notification_cache.get(twg_id_str)
            if cache_entry and (time.monotonic() - cache_entry[1]) < _NOTIFICATION_CACHE_TTL:
                return message + (cache_entry[0] or "")

            from app.core.database import get_db_session_context
            from app.models.models import TWG, Notification, NotificationType
            from sqlalchemy import select, and_

            context_msg = ""
            async with get_db_session_context() as db:
                stmt = select(TWG).where(TWG.id == twg_id_str)
                res = await db.execute(stmt)
                twg = res.scalar_one_or_none()
                if twg and twg.technical_lead_id:
                    n_stmt = select(Notification).where(
                        and_(
                            Notification.user_id == twg.technical_lead_id,
                            Notification.is_read == False,
                            Notification.type.in_([NotificationType.ALERT, NotificationType.TASK]),
                        )
                    ).order_by(Notification.created_at.desc())
                    n_res = await db.execute(n_stmt)
                    notifs = n_res.scalars().all()
                    if notifs:
                        context_msg = "\n\n[SYSTEM ALERT: Supervisor Notifications Pending]"
                        for n in notifs:
                            context_msg += f"\n- {n.title}: {n.content}"
                        context_msg += "\nPlease address these items if relevant."

            LangGraphBaseAgent._notification_cache[twg_id_str] = (context_msg, time.monotonic())
            return message + context_msg
        except Exception as e:
            logger.warning(f"[{self.agent_id}] Notification inject failed: {e}")
            return message


def create_langgraph_agent(
    agent_id: str,
    keep_history: bool = True,
    session_id: Optional[str] = None,
) -> LangGraphBaseAgent:
    return LangGraphBaseAgent(agent_id=agent_id, keep_history=keep_history, session_id=session_id)


# Alias
create_base_agent = create_langgraph_agent
