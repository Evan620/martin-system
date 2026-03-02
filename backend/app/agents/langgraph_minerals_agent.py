"""
Strategic Minerals and Natural Resource Development TWG Agent - LangGraph Implementation

Proper LangGraph-based agent for Strategic Minerals and Natural Resource Development TWG.
"""

from app.agents.langgraph_base_agent import LangGraphBaseAgent


class LangGraphMineralsAgent(LangGraphBaseAgent):
    """LangGraph-based Strategic Minerals and Natural Resource Development TWG Agent"""

    def __init__(self, keep_history: bool = True, session_id: str = None):
        """
        Initialize the Minerals agent with LangGraph.

        Args:
            keep_history: Whether to maintain conversation history
            session_id: Session identifier for checkpointing
        """
        super().__init__(
            agent_id="minerals",
            keep_history=keep_history,
            max_history=15,
            session_id=session_id
        )


def create_langgraph_minerals_agent(keep_history: bool = True, session_id: str = None) -> LangGraphMineralsAgent:
    """Create and return a LangGraph Minerals agent instance."""
    return LangGraphMineralsAgent(keep_history=keep_history, session_id=session_id)
