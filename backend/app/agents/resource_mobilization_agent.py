"""
Resource Mobilization TWG Agent

Expert coordinator for Resource Mobilization.
Manages investment pipeline and Deal Room for flagship projects.
"""

from app.agents.base_agent import BaseAgent


class ResourceMobilizationAgent(BaseAgent):
    """Agent for Resource Mobilization TWG"""

    def __init__(self, keep_history: bool = True):
        """
        Initialize the Resource Mobilization agent.

        Args:
            keep_history: Whether to maintain conversation history
        """
        super().__init__(
            agent_id="resource_mobilization",
            keep_history=keep_history,
            max_history=15
        )


# Convenience function to create a resource mobilization agent
def create_resource_mobilization_agent(keep_history: bool = True) -> ResourceMobilizationAgent:
    """Create and return a Resource Mobilization agent instance"""
    return ResourceMobilizationAgent(keep_history=keep_history)
