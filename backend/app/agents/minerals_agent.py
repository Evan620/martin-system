"""
Critical Minerals & Industrialization TWG Agent

Expert advisor for Critical Minerals & Industrialization Technical Working Group.
Focuses on mining value chain development and industrial transformation.
"""

from app.agents.base_agent import BaseAgent


class MineralsAgent(BaseAgent):
    """Agent for Critical Minerals & Industrialization TWG"""

    def __init__(self, keep_history: bool = True):
        """
        Initialize the Minerals agent.

        Args:
            keep_history: Whether to maintain conversation history
        """
        super().__init__(
            agent_id="minerals",
            keep_history=keep_history,
            max_history=15
        )


# Convenience function to create a minerals agent
def create_minerals_agent(keep_history: bool = True) -> MineralsAgent:
    """Create and return a Minerals agent instance"""
    return MineralsAgent(keep_history=keep_history)
