"""
Supervisor Agent

Central coordinator and orchestrator for all TWG agents.
Routes requests, synthesizes outputs, and maintains global consistency.
"""

from typing import Dict, List, Optional, Any
from loguru import logger

from app.agents.base_agent import BaseAgent


class SupervisorAgent(BaseAgent):
    """Supervisor agent for coordinating all TWG agents"""

    def __init__(
        self,
        keep_history: bool = True,
        session_id: Optional[str] = None,
        use_redis: bool = False,
        memory_ttl: Optional[int] = None
    ):
        """
        Initialize the Supervisor agent.

        Args:
            keep_history: Whether to maintain conversation history (default: True)
            session_id: Session identifier for Redis memory (optional)
            use_redis: If True, use Redis for persistent memory
            memory_ttl: TTL for Redis keys in seconds (optional)
        """
        super().__init__(
            agent_id="supervisor",
            keep_history=keep_history,
            max_history=20,  # Supervisors may need longer context
            session_id=session_id,
            use_redis=use_redis,
            memory_ttl=memory_ttl
        )

        # Registry of all TWG agents
        self._agent_registry: Dict[str, BaseAgent] = {}

        # Agent domain keywords for intelligent routing
        self._agent_domains = {
            "energy": ["energy", "power", "electricity", "renewable", "solar", "wind", "grid", "transmission", "wapp"],
            "agriculture": ["agriculture", "food", "farming", "crop", "livestock", "agribusiness", "fertilizer", "irrigation"],
            "minerals": ["mining", "mineral", "cobalt", "lithium", "gold", "bauxite", "industrialization", "extraction"],
            "digital": ["digital", "technology", "internet", "broadband", "cybersecurity", "fintech", "e-government", "ai"],
            "protocol": ["meeting", "schedule", "logistics", "protocol", "venue", "registration", "deadline"],
            "resource_mobilization": ["investment", "financing", "deal room", "project", "funding", "investor", "bankable"]
        }

    def register_agent(self, agent_id: str, agent: BaseAgent) -> None:
        """
        Register a TWG agent with the supervisor.

        Args:
            agent_id: Unique identifier for the agent
            agent: The agent instance to register
        """
        self._agent_registry[agent_id] = agent
        logger.info(f"Supervisor: Registered {agent_id} agent")

    def register_all_agents(self) -> None:
        """
        Automatically register all TWG agents.
        This creates instances of all available agents.
        """
        from app.agents.energy_agent import create_energy_agent
        from app.agents.agriculture_agent import create_agriculture_agent
        from app.agents.minerals_agent import create_minerals_agent
        from app.agents.digital_agent import create_digital_agent
        from app.agents.protocol_agent import create_protocol_agent
        from app.agents.resource_mobilization_agent import create_resource_mobilization_agent

        agents = {
            "energy": create_energy_agent(keep_history=False),
            "agriculture": create_agriculture_agent(keep_history=False),
            "minerals": create_minerals_agent(keep_history=False),
            "digital": create_digital_agent(keep_history=False),
            "protocol": create_protocol_agent(keep_history=False),
            "resource_mobilization": create_resource_mobilization_agent(keep_history=False)
        }

        for agent_id, agent in agents.items():
            self.register_agent(agent_id, agent)

        logger.info(f"Supervisor: All {len(agents)} TWG agents registered successfully")

    def identify_relevant_agents(self, query: str) -> List[str]:
        """
        Identify which TWG agents are relevant for a given query.

        Args:
            query: User query or message

        Returns:
            List of relevant agent IDs
        """
        query_lower = query.lower()
        relevant = []

        for agent_id, keywords in self._agent_domains.items():
            if any(keyword in query_lower for keyword in keywords):
                relevant.append(agent_id)

        return relevant

    def delegate_to_agent(self, agent_id: str, query: str) -> Optional[str]:
        """
        Delegate a query to a specific TWG agent.

        Args:
            agent_id: ID of the agent to delegate to
            query: The query to send to the agent

        Returns:
            Agent's response or None if agent not found
        """
        if agent_id not in self._agent_registry:
            logger.warning(f"Supervisor: Agent '{agent_id}' not registered")
            return None

        agent = self._agent_registry[agent_id]
        logger.info(f"Supervisor: Delegating to {agent_id} agent")

        try:
            response = agent.chat(query)
            return response
        except Exception as e:
            logger.error(f"Supervisor: Error delegating to {agent_id}: {e}")
            return f"Error from {agent_id} agent: {str(e)}"

    def consult_multiple_agents(self, query: str, agent_ids: List[str]) -> Dict[str, str]:
        """
        Consult multiple TWG agents and collect their responses.

        Args:
            query: The query to send to all agents
            agent_ids: List of agent IDs to consult

        Returns:
            Dictionary mapping agent IDs to their responses
        """
        responses = {}

        for agent_id in agent_ids:
            response = self.delegate_to_agent(agent_id, query)
            if response:
                responses[agent_id] = response

        return responses

    def synthesize_responses(self, query: str, responses: Dict[str, str]) -> str:
        """
        Synthesize multiple agent responses into a coherent answer.

        Args:
            query: Original query
            responses: Dictionary of agent responses

        Returns:
            Synthesized response
        """
        if not responses:
            return "I couldn't get responses from the relevant agents."

        # Build synthesis prompt
        synthesis_prompt = f"""Original Question: {query}

I have consulted the following TWG agents and received these responses:

"""
        for agent_id, response in responses.items():
            synthesis_prompt += f"\n{agent_id.upper()} TWG Response:\n{response}\n"

        synthesis_prompt += "\nAs the Supervisor, synthesize these responses into a coherent, strategic answer that maintains consistency and highlights cross-TWG synergies or dependencies."

        # Use supervisor's own LLM to synthesize
        return super().chat(synthesis_prompt)

    def smart_chat(self, message: str, auto_delegate: bool = True) -> str:
        """
        Enhanced chat method with automatic agent delegation.

        Args:
            message: User message
            auto_delegate: If True, automatically delegate to relevant TWG agents

        Returns:
            Response (either direct or synthesized from multiple agents)
        """
        if not auto_delegate or not self._agent_registry:
            # Standard chat without delegation
            return super().chat(message)

        # Identify relevant agents
        relevant_agents = self.identify_relevant_agents(message)

        if not relevant_agents:
            # No specific TWG identified, use supervisor's general knowledge
            logger.info("Supervisor: No specific TWG identified, using general knowledge")
            return super().chat(message)

        if len(relevant_agents) == 1:
            # Single agent - delegate directly
            agent_id = relevant_agents[0]
            logger.info(f"Supervisor: Delegating to single agent: {agent_id}")
            response = self.delegate_to_agent(agent_id, message)

            # Add supervisor's context
            context = f"[Consulted {agent_id.upper()} TWG]\n\n{response}"
            return context

        else:
            # Multiple agents - consult all and synthesize
            logger.info(f"Supervisor: Consulting multiple agents: {relevant_agents}")
            responses = self.consult_multiple_agents(message, relevant_agents)
            return self.synthesize_responses(message, responses)

    def get_registered_agents(self) -> List[str]:
        """
        Get list of all registered agent IDs.

        Returns:
            List of agent IDs
        """
        return list(self._agent_registry.keys())

    def get_supervisor_status(self) -> Dict[str, Any]:
        """
        Get comprehensive status of the supervisor and all agents.

        Returns:
            Dictionary with supervisor status information
        """
        return {
            "supervisor_id": self.agent_id,
            "registered_agents": self.get_registered_agents(),
            "agent_count": len(self._agent_registry),
            "history_enabled": self.keep_history,
            "history_length": len(self.history),
            "delegation_enabled": len(self._agent_registry) > 0
        }


# Convenience function to create a supervisor agent
def create_supervisor(
    keep_history: bool = True,
    auto_register: bool = True,
    session_id: Optional[str] = None,
    use_redis: bool = False,
    memory_ttl: Optional[int] = None
) -> SupervisorAgent:
    """
    Create and return a Supervisor agent instance.

    Args:
        keep_history: Whether to maintain conversation history
        auto_register: If True, automatically register all TWG agents
        session_id: Session identifier for Redis memory (optional)
        use_redis: If True, use Redis for persistent memory
        memory_ttl: TTL for Redis keys in seconds (optional)

    Returns:
        Configured SupervisorAgent instance
    """
    supervisor = SupervisorAgent(
        keep_history=keep_history,
        session_id=session_id,
        use_redis=use_redis,
        memory_ttl=memory_ttl
    )

    if auto_register:
        supervisor.register_all_agents()

    return supervisor
