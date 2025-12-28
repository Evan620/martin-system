"""
Digital Economy & Transformation TWG Agent

Expert advisor for Digital Economy & Transformation Technical Working Group.
Focuses on digital infrastructure, services, and innovation.
"""

from backend.app.agents.base_agent import BaseAgent


class DigitalAgent(BaseAgent):
    """Agent for Digital Economy & Transformation TWG"""

    def __init__(self, keep_history: bool = True):
        """
        Initialize the Digital agent.

        Args:
            keep_history: Whether to maintain conversation history
        """
        super().__init__(
            agent_id="digital",
            keep_history=keep_history,
            max_history=15
        )


# Convenience function to create a digital agent
def create_digital_agent(keep_history: bool = True) -> DigitalAgent:
    """Create and return a Digital agent instance"""
    return DigitalAgent(keep_history=keep_history)
