"""
Supervisor Agent

Central coordinator and orchestrator for all TWG agents.
Routes requests, synthesizes outputs, and maintains global consistency.
"""

from typing import Dict, List, Optional, Any
from loguru import logger
from uuid import UUID

from app.agents.base_agent import BaseAgent
from app.services.broadcast_service import BroadcastService
from app.services.conflict_detector import ConflictDetector
from app.services.negotiation_service import NegotiationService
from app.schemas.broadcast_messages import (
    ContextBroadcast,
    DocumentBroadcast,
    BroadcastType,
    BroadcastPriority,
    ConflictAlert,
    create_context_broadcast,
    create_document_broadcast
)


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

        # Initialize broadcast and conflict management services
        self.broadcast_service = BroadcastService()
        self.conflict_detector = ConflictDetector(llm_client=self.llm)
        self.negotiation_service = NegotiationService(supervisor_llm=self.llm)

        # Agent domain keywords for intelligent routing
        # Primary keywords (strong signals) and secondary keywords (weak signals)
        self._agent_domains = {
            "energy": {
                "primary": ["energy", "power", "electricity", "renewable", "solar", "wind", "wapp"],
                "secondary": ["grid", "transmission", "hydroelectric", "fuel", "petroleum"]
            },
            "agriculture": {
                "primary": ["agriculture", "agricultural", "food security", "farming", "crop", "livestock", "agribusiness"],
                "secondary": ["fertilizer", "irrigation", "harvest", "rural", "farmer", "food production"]
            },
            "minerals": {
                "primary": ["mining", "mineral", "cobalt", "lithium", "gold", "bauxite", "extraction"],
                "secondary": ["industrialization", "ore", "quarry", "geology"]
            },
            "digital": {
                "primary": ["digital", "technology", "internet", "broadband", "fintech", "e-commerce", "e-government"],
                "secondary": ["cybersecurity", "ai", "software", "tech", "online", "platform"]
            },
            "protocol": {
                "primary": ["meeting", "schedule", "logistics", "protocol", "venue", "registration"],
                "secondary": ["deadline", "agenda", "ceremony", "security", "vip"]
            },
            "resource_mobilization": {
                "primary": ["investment", "financing", "deal room", "funding", "investor", "bankable"],
                "secondary": ["finance", "capital", "donor", "partner", "budget"]
            }
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
        Identify which TWG agents are relevant for a given query using keyword scoring.

        Scoring system:
        - Primary keyword match: 10 points
        - Secondary keyword match: 3 points
        - Threshold for relevance: 5 points
        - This allows detection of cross-TWG queries

        Args:
            query: User query or message

        Returns:
            List of relevant agent IDs (sorted by relevance score)
        """
        query_lower = query.lower()
        agent_scores = {}

        # Score each agent based on keyword matches
        for agent_id, keywords in self._agent_domains.items():
            score = 0

            # Check primary keywords (strong signal)
            for keyword in keywords.get("primary", []):
                if keyword in query_lower:
                    score += 10
                    logger.debug(f"Primary match '{keyword}' for {agent_id} (+10)")

            # Check secondary keywords (weak signal)
            for keyword in keywords.get("secondary", []):
                if keyword in query_lower:
                    score += 3
                    logger.debug(f"Secondary match '{keyword}' for {agent_id} (+3)")

            if score > 0:
                agent_scores[agent_id] = score

        # Filter agents that meet the threshold (5 points minimum)
        # This means at least 1 primary keyword OR 2 secondary keywords
        relevant_threshold = 5
        relevant = [
            agent_id for agent_id, score in agent_scores.items()
            if score >= relevant_threshold
        ]

        # Sort by score (highest first)
        relevant.sort(key=lambda x: agent_scores[x], reverse=True)

        if relevant:
            scores_str = ", ".join([f"{a}({agent_scores[a]})" for a in relevant])
            logger.info(f"Relevant agents identified: {scores_str}")

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

        Now displays individual agent responses clearly before synthesis.

        Args:
            query: Original query
            responses: Dictionary of agent responses

        Returns:
            Synthesized response with clear agent attribution
        """
        if not responses:
            return "I couldn't get responses from the relevant agents."

        # Build header showing which agents were consulted
        agent_list = ", ".join([agent_id.upper() for agent_id in responses.keys()])
        output = f"[Consulted {len(responses)} TWGs: {agent_list}]\n\n"
        output += "=" * 70 + "\n"

        # Display each agent's response clearly
        for i, (agent_id, response) in enumerate(responses.items(), 1):
            output += f"\n📋 {agent_id.upper()} TWG Response:\n"
            output += "-" * 70 + "\n"
            output += response + "\n"

            if i < len(responses):  # Not the last one
                output += "\n" + "=" * 70 + "\n"

        output += "\n" + "=" * 70 + "\n"

        # Build synthesis prompt for the supervisor
        synthesis_prompt = f"""Original Question: {query}

I have consulted {len(responses)} TWG agents and received these responses:

"""
        for agent_id, response in responses.items():
            synthesis_prompt += f"\n{agent_id.upper()} TWG:\n{response}\n"

        synthesis_prompt += "\n\nAs the Supervisor, provide a brief (2-3 sentence) strategic synthesis that highlights how these TWG perspectives complement each other and what the key takeaways are."

        # Get supervisor's synthesis
        synthesis = super().chat(synthesis_prompt)

        # Add synthesis at the end
        output += f"\n🎯 SUPERVISOR'S SYNTHESIS:\n"
        output += "-" * 70 + "\n"
        output += synthesis + "\n"

        return output

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

    # =========================================================================
    # Cross-TWG Synthesis Methods
    # =========================================================================

    def collect_twg_status(self, agent_ids: Optional[List[str]] = None, brief: bool = True) -> Dict[str, str]:
        """
        Collect current status from multiple TWGs.

        Args:
            agent_ids: List of agent IDs to query (None = all registered agents)
            brief: If True, request brief responses (much faster, recommended)

        Returns:
            Dictionary mapping agent_id to their status summary
        """
        if agent_ids is None:
            agent_ids = self.get_registered_agents()

        # Use VERY brief query for faster responses (reduces timeout issues)
        if brief:
            status_query = "In 2-3 sentences max: What are your top 2 priorities right now?"
        else:
            status_query = "Provide a brief status update covering: current priorities, recent progress, upcoming milestones, and any blockers or dependencies on other TWGs."

        statuses = {}
        for agent_id in agent_ids:
            try:
                logger.info(f"Querying {agent_id} TWG...")
                response = self.delegate_to_agent(agent_id, status_query)
                if response:
                    statuses[agent_id] = response
                    logger.info(f"✓ Got response from {agent_id}")
            except Exception as e:
                logger.error(f"✗ Failed to collect from {agent_id}: {e}")
                statuses[agent_id] = f"[Error: {str(e)[:100]}]"

        return statuses

    def generate_pillar_overview(self, pillar_agent_id: str) -> str:
        """
        Generate a strategic overview of a single pillar.

        Args:
            pillar_agent_id: Agent ID (energy, agriculture, minerals, digital)

        Returns:
            Formatted pillar overview
        """
        from app.agents.synthesis_templates import (
            SynthesisType,
            format_synthesis_prompt
        )

        # Collect detailed input from the pillar TWG
        pillar_query = """Provide a comprehensive overview of your pillar including:
1. Key priorities and strategic goals
2. Flagship initiatives and projects
3. Expected outcomes and impacts
4. Critical success factors
5. Main risks and dependencies"""

        twg_input = self.delegate_to_agent(pillar_agent_id, pillar_query)

        if not twg_input:
            return f"Could not generate overview for {pillar_agent_id} - agent not available"

        # Format synthesis prompt
        pillar_names = {
            "energy": "Energy & Infrastructure",
            "agriculture": "Agriculture & Food Security",
            "minerals": "Critical Minerals & Industrialization",
            "digital": "Digital Economy & Transformation"
        }

        prompt = format_synthesis_prompt(
            SynthesisType.PILLAR_OVERVIEW,
            twg_inputs={pillar_agent_id: twg_input},
            pillar_name=pillar_names.get(pillar_agent_id, pillar_agent_id.title())
        )

        # Generate synthesis
        logger.info(f"Generating pillar overview for {pillar_agent_id}")
        return super().chat(prompt)

    def generate_cross_pillar_synthesis(self, agent_ids: List[str]) -> str:
        """
        Generate synthesis identifying synergies between multiple pillars.

        Args:
            agent_ids: List of agent IDs to synthesize (2+ pillars)

        Returns:
            Cross-pillar synthesis report
        """
        from app.agents.synthesis_templates import (
            SynthesisType,
            format_synthesis_prompt
        )

        if len(agent_ids) < 2:
            return "Cross-pillar synthesis requires at least 2 pillars"

        # Collect inputs from all specified TWGs
        query = "Describe your pillar's priorities, key projects, and any dependencies or synergies with other pillars (energy, agriculture, minerals, digital)."

        twg_inputs = {}
        for agent_id in agent_ids:
            response = self.delegate_to_agent(agent_id, query)
            if response:
                twg_inputs[agent_id] = response

        if not twg_inputs:
            return "Could not collect TWG inputs for synthesis"

        # Format pillar names
        pillar_names_map = {
            "energy": "Energy",
            "agriculture": "Agriculture",
            "minerals": "Minerals",
            "digital": "Digital"
        }
        pillars_names = " & ".join([pillar_names_map.get(aid, aid.title()) for aid in agent_ids])
        pillars_list = ", ".join([pillar_names_map.get(aid, aid.title()) for aid in agent_ids])

        # Generate synthesis
        prompt = format_synthesis_prompt(
            SynthesisType.CROSS_PILLAR,
            twg_inputs=twg_inputs,
            pillars_names=pillars_names,
            pillars_list=pillars_list
        )

        logger.info(f"Generating cross-pillar synthesis for: {pillars_list}")
        return super().chat(prompt)

    def generate_strategic_priorities(self) -> str:
        """
        Generate strategic priorities synthesis across all TWGs.

        Returns:
            Strategic priorities report
        """
        from app.agents.synthesis_templates import (
            SynthesisType,
            format_synthesis_prompt
        )

        # Collect status from all TWGs
        twg_inputs = self.collect_twg_status()

        if not twg_inputs:
            return "Could not collect TWG inputs for strategic priorities"

        # Generate synthesis
        prompt = format_synthesis_prompt(
            SynthesisType.STRATEGIC_PRIORITIES,
            twg_inputs=twg_inputs
        )

        logger.info("Generating strategic priorities synthesis across all TWGs")
        return super().chat(prompt)

    def generate_policy_coherence_check(self) -> str:
        """
        Generate policy coherence check across all TWGs.

        Returns:
            Policy coherence analysis
        """
        from app.agents.synthesis_templates import (
            SynthesisType,
            format_synthesis_prompt
        )

        # Query TWGs about their policy recommendations
        policy_query = "List your key policy recommendations and regulatory proposals for the summit."

        twg_inputs = {}
        for agent_id in self.get_registered_agents():
            response = self.delegate_to_agent(agent_id, policy_query)
            if response:
                twg_inputs[agent_id] = response

        if not twg_inputs:
            return "Could not collect policy inputs from TWGs"

        # Generate coherence check
        prompt = format_synthesis_prompt(
            SynthesisType.POLICY_COHERENCE,
            twg_inputs=twg_inputs
        )

        logger.info("Generating policy coherence check across all TWGs")
        return super().chat(prompt)

    def generate_summit_readiness_assessment(self) -> str:
        """
        Generate comprehensive summit readiness assessment.

        Returns:
            Summit readiness report
        """
        from app.agents.synthesis_templates import (
            SynthesisType,
            format_synthesis_prompt
        )

        # Collect comprehensive status from all TWGs including protocol
        readiness_query = "Provide a readiness assessment covering: deliverables status, timeline adherence, resource needs, stakeholder engagement, and any critical issues."

        twg_inputs = {}
        for agent_id in self.get_registered_agents():
            response = self.delegate_to_agent(agent_id, readiness_query)
            if response:
                twg_inputs[agent_id] = response

        if not twg_inputs:
            return "Could not collect readiness inputs from TWGs"

        # Generate assessment
        prompt = format_synthesis_prompt(
            SynthesisType.SUMMIT_READINESS,
            twg_inputs=twg_inputs
        )

        logger.info("Generating summit readiness assessment")
        return super().chat(prompt)

    # =========================================================================
    # BROADCAST AND CONTEXT MANAGEMENT
    # =========================================================================

    def broadcast_strategic_context(
        self,
        summit_objectives: List[str],
        strategic_priorities: List[str],
        policy_constraints: Optional[List[str]] = None,
        cross_cutting_themes: Optional[List[str]] = None,
        coordination_points: Optional[Dict[str, str]] = None,
        version: str = "1.0"
    ) -> Dict[str, bool]:
        """
        Broadcast strategic context to all registered TWG agents.

        This ensures all agents work from the same strategic playbook,
        including Summit objectives, core documents, and policy guardrails.

        Args:
            summit_objectives: Overarching Summit objectives
            strategic_priorities: Current strategic priorities
            policy_constraints: Policy guardrails and constraints
            cross_cutting_themes: Themes that span all TWGs (e.g., youth, gender)
            coordination_points: Key coordination requirements
            version: Version identifier for this context update

        Returns:
            Dict mapping agent_id to delivery success status

        Example:
            >>> supervisor.broadcast_strategic_context(
            ...     summit_objectives=[
            ...         "Accelerate regional integration through infrastructure",
            ...         "Mobilize $50B for strategic investments"
            ...     ],
            ...     strategic_priorities=[
            ...         "WAPP expansion to 5000 MW by 2026",
            ...         "Digital payment interoperability"
            ...     ],
            ...     policy_constraints=[
            ...         "All projects must align with ECOWAS protocols",
            ...         "Climate neutrality required for energy projects"
            ...     ]
            ... )
        """
        context = create_context_broadcast(
            summit_objectives=summit_objectives,
            strategic_priorities=strategic_priorities,
            policy_constraints=policy_constraints,
            cross_cutting_themes=cross_cutting_themes,
            coordination_points=coordination_points,
            version=version
        )

        results = self.broadcast_service.broadcast_context(
            context,
            self._agent_registry
        )

        successful = sum(1 for success in results.values() if success)
        logger.info(
            f"📢 Strategic context broadcast to {successful}/{len(results)} agents"
        )

        return results

    def broadcast_document(
        self,
        document_type: str,
        title: str,
        version: str,
        summary: str,
        key_points: List[str],
        full_text: Optional[str] = None,
        relevant_sections: Optional[Dict[str, List[str]]] = None
    ) -> Dict[str, bool]:
        """
        Broadcast a key document to all TWG agents.

        This distributes core documents like Concept Notes, Declaration drafts,
        or Summit guidelines to ensure all agents reference the same materials.

        Args:
            document_type: Type of document (e.g., "concept_note", "declaration_draft")
            title: Document title
            version: Version identifier
            summary: Executive summary
            key_points: Key points agents should note
            full_text: Full document text (optional)
            relevant_sections: Map of agent_id to relevant sections (optional)

        Returns:
            Dict mapping agent_id to delivery success status

        Example:
            >>> supervisor.broadcast_document(
            ...     document_type="concept_note",
            ...     title="ECOWAS Summit 2026 Concept Note",
            ...     version="2.1",
            ...     summary="Framework for regional integration summit...",
            ...     key_points=[
            ...         "Focus on 4 pillars: Energy, Agriculture, Minerals, Digital",
            ...         "Deal Room target: $50B investment pipeline"
            ...     ]
            ... )
        """
        from app.schemas.broadcast_messages import DocumentType

        # Convert string to enum
        doc_type_enum = DocumentType(document_type)

        document = create_document_broadcast(
            document_type=doc_type_enum,
            title=title,
            version=version,
            summary=summary,
            key_points=key_points,
            full_text=full_text,
            relevant_sections=relevant_sections
        )

        results = self.broadcast_service.broadcast_document(
            document,
            self._agent_registry
        )

        successful = sum(1 for success in results.values() if success)
        logger.info(
            f"📄 Document '{title}' broadcast to {successful}/{len(results)} agents"
        )

        return results

    def get_active_context(self) -> Optional[ContextBroadcast]:
        """Get the currently active strategic context"""
        return self.broadcast_service.get_active_context()

    # =========================================================================
    # CONFLICT DETECTION AND RESOLUTION
    # =========================================================================

    def detect_conflicts(
        self,
        twg_outputs: Optional[Dict[str, str]] = None,
        query: Optional[str] = None
    ) -> List[ConflictAlert]:
        """
        Detect conflicts and contradictions across TWG outputs.

        This catches policy divergences, overlapping sessions, contradictory
        targets, and resource conflicts before they reach Ministers.

        Args:
            twg_outputs: Dictionary mapping agent_id to their output text.
                        If None, collects latest outputs from all agents.
            query: Optional query to collect outputs for (if twg_outputs not provided)

        Returns:
            List of detected conflicts

        Example:
            >>> conflicts = supervisor.detect_conflicts()
            >>> for conflict in conflicts:
            ...     print(f"{conflict.severity}: {conflict.description}")
            ...     if conflict.requires_negotiation:
            ...         supervisor.initiate_negotiation(conflict)
        """
        # If no outputs provided, collect from all agents
        if twg_outputs is None:
            if query is None:
                query = "What are your current policy recommendations and key targets?"

            logger.info("Collecting TWG outputs for conflict detection...")
            twg_outputs = {}
            for agent_id in self.get_registered_agents():
                try:
                    response = self.delegate_to_agent(agent_id, query)
                    if response:
                        twg_outputs[agent_id] = response
                except Exception as e:
                    logger.error(f"Failed to collect from {agent_id}: {e}")

        # Run conflict detection
        conflicts = self.conflict_detector.detect_conflicts(twg_outputs)

        if conflicts:
            logger.warning(
                f"⚠️  Detected {len(conflicts)} conflicts across TWG outputs"
            )
            for conflict in conflicts:
                logger.warning(
                    f"  • [{conflict.severity.upper()}] {conflict.description}"
                )
        else:
            logger.info("✓ No conflicts detected - all TWGs aligned")

        return conflicts

    def initiate_negotiation(
        self,
        conflict: ConflictAlert,
        constraints: Optional[List[str]] = None,
        max_rounds: int = 3
    ) -> Dict[str, Any]:
        """
        Initiate automated negotiation to resolve a conflict.

        The supervisor facilitates multi-round negotiation between agents
        to build consensus and resolve differences without human intervention.

        Args:
            conflict: The conflict to resolve
            constraints: Non-negotiable constraints (optional)
            max_rounds: Maximum negotiation rounds (default: 3)

        Returns:
            Dict with negotiation results

        Example:
            >>> conflict = conflicts[0]  # High-priority conflict
            >>> result = supervisor.initiate_negotiation(
            ...     conflict,
            ...     constraints=["Must align with ECOWAS protocols"],
            ...     max_rounds=3
            ... )
            >>> if result["status"] == "resolved":
            ...     print(f"Consensus reached: {result['resolution']}")
            >>> elif result["status"] == "escalated":
            ...     print("Human intervention required")
        """
        # Create negotiation
        negotiation = self.negotiation_service.initiate_negotiation(
            conflict,
            self._agent_registry,
            constraints=constraints,
            max_rounds=max_rounds
        )

        logger.info(
            f"🤝 Starting negotiation between {', '.join(conflict.agents_involved)}"
        )

        # Run negotiation
        result = self.negotiation_service.run_negotiation(
            negotiation.negotiation_id,
            self._agent_registry
        )

        # Log outcome
        if result["status"] == "resolved":
            logger.info(
                f"✅ Negotiation resolved: {result['resolution']}"
            )
        elif result["status"] == "escalated":
            logger.warning(
                f"⚠️  Negotiation escalated to humans: {result['reason']}"
            )
        elif result["status"] == "in_progress":
            logger.info(
                f"🔄 Negotiation in progress: Round {result['round']}"
            )

        return result

    def auto_resolve_conflicts(
        self,
        conflicts: Optional[List[ConflictAlert]] = None,
        auto_negotiate: bool = True
    ) -> Dict[str, Any]:
        """
        Automatically resolve conflicts through negotiation.

        This is the "90% automated consensus-building" feature that resolves
        minor issues before they reach Ministers.

        Args:
            conflicts: List of conflicts to resolve. If None, detects conflicts first.
            auto_negotiate: If True, automatically initiate negotiations for
                          conflicts that require it (default: True)

        Returns:
            Dict with resolution summary

        Example:
            >>> summary = supervisor.auto_resolve_conflicts()
            >>> print(f"Resolved: {summary['resolved']}")
            >>> print(f"Escalated: {summary['escalated']}")
            >>> print(f"Success rate: {summary['resolution_rate']:.1%}")
        """
        # Detect conflicts if not provided
        if conflicts is None:
            logger.info("🔍 Running automated conflict detection...")
            conflicts = self.detect_conflicts()

        if not conflicts:
            return {
                "total_conflicts": 0,
                "resolved": 0,
                "escalated": 0,
                "resolution_rate": 1.0,
                "message": "No conflicts detected"
            }

        resolved = 0
        escalated = 0
        in_progress = 0

        for conflict in conflicts:
            if not auto_negotiate or not conflict.requires_negotiation:
                # Skip conflicts that don't need negotiation
                if conflict.requires_human_intervention:
                    escalated += 1
                continue

            # Attempt automated resolution
            try:
                result = self.initiate_negotiation(conflict)

                if result["status"] == "resolved":
                    resolved += 1
                elif result["status"] == "escalated":
                    escalated += 1
                else:
                    in_progress += 1

            except Exception as e:
                logger.error(f"Negotiation failed: {e}")
                escalated += 1

        resolution_rate = resolved / len(conflicts) if conflicts else 0

        summary = {
            "total_conflicts": len(conflicts),
            "resolved": resolved,
            "escalated": escalated,
            "in_progress": in_progress,
            "resolution_rate": resolution_rate,
            "message": f"Resolved {resolved}/{len(conflicts)} conflicts automatically"
        }

        logger.info(
            f"📊 Auto-resolution complete: {resolved} resolved, "
            f"{escalated} escalated, {in_progress} in progress"
        )

        return summary

    def get_conflict_summary(self) -> Dict[str, Any]:
        """Get summary of all detected conflicts"""
        return self.conflict_detector.get_conflict_summary()

    def get_negotiation_summary(self) -> Dict[str, Any]:
        """Get summary of all negotiations"""
        return self.negotiation_service.get_negotiation_summary()


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
