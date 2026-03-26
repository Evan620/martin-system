"""
Energy Trade and Industrial Growth TWG Agent - LangGraph Implementation

Proper LangGraph-based agent for Energy Trade and Industrial Growth TWG.
"""

from app.agents.langgraph_base_agent import LangGraphBaseAgent


class LangGraphEnergyAgent(LangGraphBaseAgent):
    """LangGraph-based Energy Trade and Industrial Growth TWG Agent"""

    def __init__(self, keep_history: bool = True, session_id: str = None):
        """
        Initialize the Energy agent with LangGraph.

        Args:
            keep_history: Whether to maintain conversation history
            session_id: Session identifier for checkpointing
        """
        super().__init__(
            agent_id="energy",
            keep_history=keep_history,
            max_history=15,
            session_id=session_id
        )


def create_langgraph_energy_agent(keep_history: bool = True, session_id: str = None) -> LangGraphEnergyAgent:
    """Create and return a LangGraph Energy agent instance."""
    return LangGraphEnergyAgent(keep_history=keep_history, session_id=session_id)
