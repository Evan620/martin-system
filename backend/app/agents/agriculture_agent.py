"""
Agriculture & Food Systems TWG Agent

Expert advisor for Agriculture & Food Systems Technical Working Group.
Focuses on food security and agribusiness development.
"""

from backend.app.agents.base_agent import BaseAgent


class AgricultureAgent(BaseAgent):
    """Agent for Agriculture & Food Systems TWG"""

    def __init__(self, keep_history: bool = True):
        """
        Initialize the Agriculture agent.

        Args:
            keep_history: Whether to maintain conversation history
        """
        super().__init__(
            agent_id="agriculture",
            keep_history=keep_history,
            max_history=15
        )


# Convenience function to create an agriculture agent
def create_agriculture_agent(keep_history: bool = True) -> AgricultureAgent:
    """Create and return an Agriculture agent instance"""
    return AgricultureAgent(keep_history=keep_history)
