"""
Digital Transformation TWG Agent - LangGraph Implementation

Proper LangGraph-based agent for Digital Transformation TWG.
"""

from app.agents.langgraph_base_agent import LangGraphBaseAgent


class LangGraphDigitalAgent(LangGraphBaseAgent):
    """LangGraph-based Digital Transformation TWG Agent"""

    def __init__(self, keep_history: bool = True, session_id: str = None):
        """
        Initialize the Digital agent with LangGraph.

        Args:
            keep_history: Whether to maintain conversation history
            session_id: Session identifier for checkpointing
        """
        super().__init__(
            agent_id="digital",
            keep_history=keep_history,
            max_history=15,
            session_id=session_id
        )


def create_langgraph_digital_agent(keep_history: bool = True, session_id: str = None) -> LangGraphDigitalAgent:
    """Create and return a LangGraph Digital agent instance."""
    return LangGraphDigitalAgent(keep_history=keep_history, session_id=session_id)
