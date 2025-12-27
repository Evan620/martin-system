"""
Energy & Infrastructure TWG Agent

Expert advisor for Energy & Infrastructure Technical Working Group.
Focuses on regional power integration and renewable energy transition.
"""

from app.agents.base_agent import BaseAgent


class EnergyAgent(BaseAgent):
    """Agent for Energy & Infrastructure TWG"""

    def __init__(self, keep_history: bool = True):
        """
        Initialize the Energy agent.

        Args:
            keep_history: Whether to maintain conversation history
        """
        super().__init__(
            agent_id="energy",
            keep_history=keep_history,
            max_history=15
        )


# Convenience function to create an energy agent
def create_energy_agent(keep_history: bool = True) -> EnergyAgent:
    """Create and return an Energy agent instance"""
    return EnergyAgent(keep_history=keep_history)
