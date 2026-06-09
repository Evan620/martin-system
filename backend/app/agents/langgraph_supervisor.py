"""
LangGraphSupervisor — backward-compatible wrapper around SupervisorLoop.

Public API is unchanged; LangGraph graph replaced with SupervisorLoop.
"""
from __future__ import annotations

from typing import Any, AsyncGenerator, Dict, Optional

from loguru import logger

from app.agents.langgraph_base_agent import LangGraphBaseAgent
from app.agents.supervisor_loop import SupervisorLoop
from app.services.llm_service import get_llm_service


class LangGraphSupervisor:
    """Thin wrapper — delegates to SupervisorLoop."""

    def __init__(
        self,
        keep_history: bool = True,
        session_id: Optional[str] = None,
        use_redis: bool = False,
        memory_ttl: Optional[int] = None,
    ):
        self.session_id = session_id or "default"
        self.keep_history = keep_history

        # Supervisor's own AgentLoop (handles general / secretariat queries)
        self.supervisor_agent = LangGraphBaseAgent(
            agent_id="supervisor",
            keep_history=keep_history,
            max_history=6,
            session_id=session_id,
        )

        self._twg_agents: Dict[str, LangGraphBaseAgent] = {}
        self._loop: Optional[SupervisorLoop] = None
        self._llm = get_llm_service()

        logger.info("LangGraphSupervisor initialised (SupervisorLoop backend)")

    # ------------------------------------------------------------------
    # Agent registration (unchanged API)
    # ------------------------------------------------------------------

    def register_agent(self, agent_id: str, agent: LangGraphBaseAgent) -> None:
        self._twg_agents[agent_id] = agent
        self._rebuild_loop()
        logger.info(f"[SUPERVISOR] Registered {agent_id}")

    def register_all_agents(self) -> None:
        from app.agents.langgraph_energy_agent import create_langgraph_energy_agent
        from app.agents.langgraph_agriculture_agent import create_langgraph_agriculture_agent
        from app.agents.langgraph_minerals_agent import create_langgraph_minerals_agent
        from app.agents.langgraph_digital_agent import create_langgraph_digital_agent
        from app.agents.langgraph_protocol_agent import create_langgraph_protocol_agent
        from app.agents.langgraph_resource_mobilization_agent import create_langgraph_resource_mobilization_agent

        agents = {
            "energy": create_langgraph_energy_agent(keep_history=True),
            "agriculture": create_langgraph_agriculture_agent(keep_history=True),
            "minerals": create_langgraph_minerals_agent(keep_history=True),
            "digital": create_langgraph_digital_agent(keep_history=True),
            "protocol": create_langgraph_protocol_agent(keep_history=True),
            "resource_mobilization": create_langgraph_resource_mobilization_agent(keep_history=True),
            # Member-scoped agent (gated to MEMBER_TOOLS). Registered with no TWG
            # binding; the caller's twg_id is supplied per-request via chat_with_tools
            # (force_agent_id="member" + twg_id) so TWG-scoped member reads are granted.
            "member": LangGraphBaseAgent(agent_id="member", keep_history=True),
        }
        for aid, agent in agents.items():
            self._twg_agents[aid] = agent
        self._rebuild_loop()
        logger.info(f"[SUPERVISOR] All {len(agents)} agents registered")

    def build_graph(self) -> None:
        """No-op — kept for API compatibility. Loop is built lazily."""
        self._rebuild_loop()
        logger.info("[SUPERVISOR] SupervisorLoop ready (no LangGraph graph needed)")

    # ------------------------------------------------------------------
    # Chat API (unchanged signatures)
    # ------------------------------------------------------------------

    async def chat(
        self,
        message: str,
        thread_id: Optional[str] = None,
        twg_id: Optional[str] = None,
        user_timezone: Optional[str] = None,
        force_agent_id: Optional[str] = None,
    ) -> dict:
        loop = self._get_loop()
        resp = await loop.run(
            query=message,
            thread_id=thread_id or self.session_id,
            twg_id=twg_id,
            user_timezone=user_timezone,
            force_agent_id=force_agent_id,
        )
        return {
            "response": resp.content,
            "citations": resp.citations,
            "agent_id": resp.agent_id,
            "conversation_id": thread_id or self.session_id,
            "suggestions": [],
            "interrupted": False,
            "interrupt_payload": None,
            "thread_id": thread_id or self.session_id,
        }

    async def stream_chat(
        self,
        message: str,
        thread_id: Optional[str] = None,
        twg_id: Optional[str] = None,
        user_timezone: Optional[str] = None,
        force_agent_id: Optional[str] = None,
    ) -> AsyncGenerator[Dict, None]:
        loop = self._get_loop()
        async for event in loop.stream(
            query=message,
            thread_id=thread_id or self.session_id,
            twg_id=twg_id,
            user_timezone=user_timezone,
            force_agent_id=force_agent_id,
        ):
            yield event

    async def resume_chat(self, thread_id: str, resume_value: Dict) -> str:
        """No-op stub — interrupt flow not used in SupervisorLoop."""
        logger.info("[SUPERVISOR] resume_chat called (no-op in SupervisorLoop backend)")
        return "Resumption not supported in this version."

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _rebuild_loop(self) -> None:
        # SupervisorLoop needs AgentLoop instances, not LangGraphBaseAgent.
        # Each LangGraphBaseAgent wraps an AgentLoop at self._loop.
        twg_agent_loops = {
            aid: agent._loop for aid, agent in self._twg_agents.items()
        }
        self._loop = SupervisorLoop(
            llm=self._llm,
            twg_agents=twg_agent_loops,
            supervisor_agent=self.supervisor_agent._loop,
        )

    def _get_loop(self) -> SupervisorLoop:
        if self._loop is None:
            self._rebuild_loop()
        return self._loop

    def get_registered_agents(self):
        return list(self._twg_agents.keys())

    def get_supervisor_status(self):
        return {
            "supervisor_type": "SupervisorLoop",
            "session_id": self.session_id,
            "registered_agents": self.get_registered_agents(),
            "agent_count": len(self._twg_agents),
            "history_enabled": self.keep_history,
        }

    def reset_history(self, thread_id: Optional[str] = None) -> None:
        from app.agents.agent_loop import AgentLoop
        AgentLoop._history.pop(thread_id or self.session_id, None)


def create_langgraph_supervisor(
    keep_history: bool = True,
    auto_register: bool = True,
    session_id: Optional[str] = None,
    use_redis: bool = False,
    memory_ttl: Optional[int] = None,
) -> LangGraphSupervisor:
    """Factory function — creates and optionally registers all TWG agents."""
    supervisor = LangGraphSupervisor(
        keep_history=keep_history,
        session_id=session_id,
        use_redis=use_redis,
        memory_ttl=memory_ttl,
    )
    if auto_register:
        supervisor.register_all_agents()
        supervisor.build_graph()
    return supervisor
