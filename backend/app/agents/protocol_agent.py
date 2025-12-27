"""
Protocol & Logistics TWG Agent

Expert coordinator for Protocol & Logistics.
Manages operational and ceremonial aspects of the summit.
"""

from app.agents.base_agent import BaseAgent


class ProtocolAgent(BaseAgent):
    """Agent for Protocol & Logistics TWG"""

    def __init__(self, keep_history: bool = True):
        """
        Initialize the Protocol agent.

        Args:
            keep_history: Whether to maintain conversation history
        """
        super().__init__(
            agent_id="protocol",
            keep_history=keep_history,
            max_history=15
        )


# Convenience function to create a protocol agent
def create_protocol_agent(keep_history: bool = True) -> ProtocolAgent:
    """Create and return a Protocol agent instance"""
    return ProtocolAgent(keep_history=keep_history)
