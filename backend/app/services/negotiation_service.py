"""
Negotiation Service

Facilitates automated negotiation between TWG agents to resolve conflicts.
Handles consensus-building, compromise proposals, and escalation.
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, UTC
from loguru import logger
from uuid import UUID

from app.schemas.broadcast_messages import (
    ConflictAlert,
    NegotiationRequest,
    create_negotiation_request
)


class NegotiationService:
    """Service for facilitating agent-to-agent negotiations"""

    def __init__(self, supervisor_llm: Optional[Any] = None):
        """
        Initialize negotiation service.

        Args:
            supervisor_llm: LLM client for supervisor to facilitate negotiations
        """
        self.supervisor_llm = supervisor_llm
        self._active_negotiations: Dict[UUID, NegotiationRequest] = {}
        self._negotiation_history: List[NegotiationRequest] = []

    def initiate_negotiation(
        self,
        conflict: ConflictAlert,
        agents: Dict[str, Any],
        constraints: Optional[List[str]] = None,
        max_rounds: int = 3
    ) -> NegotiationRequest:
        """
        Initiate a negotiation to resolve a conflict.

        Args:
            conflict: The conflict to resolve
            agents: Dictionary of agent instances
            constraints: Non-negotiable constraints
            max_rounds: Maximum negotiation rounds

        Returns:
            NegotiationRequest object tracking the negotiation
        """
        # Create negotiation request
        negotiation = create_negotiation_request(
            conflict_id=conflict.alert_id,
            participating_agents=conflict.agents_involved,
            issue=conflict.description,
            positions={
                agent_id: conflict.conflicting_positions[agent_id]
                for agent_id in conflict.agents_involved
            },
            constraints=constraints or [],
            success_criteria=[
                "All agents agree on resolution",
                "Resolution aligns with Summit objectives",
                "No new conflicts introduced"
            ],
            max_rounds=max_rounds
        )

        self._active_negotiations[negotiation.negotiation_id] = negotiation

        logger.info(
            f"🤝 Initiated negotiation {negotiation.negotiation_id} "
            f"between {', '.join(conflict.agents_involved)}"
        )

        return negotiation

    def run_negotiation(
        self,
        negotiation_id: UUID,
        agents: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Run a negotiation round between agents.

        Args:
            negotiation_id: ID of the negotiation
            agents: Dictionary of agent instances

        Returns:
            Dict with negotiation results
        """
        if negotiation_id not in self._active_negotiations:
            raise ValueError(f"Negotiation {negotiation_id} not found")

        negotiation = self._active_negotiations[negotiation_id]

        if negotiation.status == "resolved":
            return {
                "status": "already_resolved",
                "resolution": negotiation.proposals[-1] if negotiation.proposals else None
            }

        if negotiation.current_round >= negotiation.max_rounds:
            return self._escalate_negotiation(negotiation, "max_rounds_exceeded")

        # Run negotiation round
        negotiation.current_round += 1
        negotiation.status = "in_progress"

        logger.info(
            f"🔄 Negotiation round {negotiation.current_round}/{negotiation.max_rounds} "
            f"for {negotiation.negotiation_id}"
        )

        # 1. Collect proposals from each agent
        proposals = self._collect_proposals(negotiation, agents)

        # 2. Analyze proposals for consensus
        analysis = self._analyze_proposals(negotiation, proposals)

        # 3. Determine outcome
        if analysis["has_consensus"]:
            # Consensus reached!
            result = self._finalize_consensus(negotiation, analysis)
            return result

        elif negotiation.current_round >= negotiation.max_rounds:
            # No consensus after max rounds - escalate
            return self._escalate_negotiation(negotiation, "no_consensus")

        else:
            # Continue negotiation - supervisor provides guidance
            guidance = self._provide_negotiation_guidance(negotiation, analysis)
            return {
                "status": "in_progress",
                "round": negotiation.current_round,
                "guidance": guidance,
                "next_action": "continue"
            }

    def _collect_proposals(
        self,
        negotiation: NegotiationRequest,
        agents: Dict[str, Any]
    ) -> Dict[str, str]:
        """Collect compromise proposals from each participating agent"""
        proposals = {}

        # Build negotiation context
        context = self._build_negotiation_context(negotiation)

        for agent_id in negotiation.participating_agents:
            if agent_id not in agents:
                logger.warning(f"Agent {agent_id} not available for negotiation")
                continue

            agent = agents[agent_id]

            # Prompt agent for proposal
            prompt = f"""{context}

NEGOTIATION ROUND {negotiation.current_round}

Please propose a solution or compromise that:
1. Addresses the core issue
2. Respects the constraints listed above
3. Is acceptable to all parties
4. Aligns with ECOWAS Summit objectives

Your proposal (2-3 sentences):"""

            try:
                response = agent.chat(prompt)
                proposals[agent_id] = response
                logger.info(f"✓ Received proposal from {agent_id}")

            except Exception as e:
                logger.error(f"Failed to get proposal from {agent_id}: {e}")
                proposals[agent_id] = "[No proposal submitted]"

        # Store proposals
        negotiation.proposals.append({
            "round": negotiation.current_round,
            "timestamp": datetime.now(UTC).isoformat(),
            "proposals": proposals
        })

        return proposals

    def _build_negotiation_context(self, negotiation: NegotiationRequest) -> str:
        """Build context string for negotiation prompts"""
        context = f"""NEGOTIATION IN PROGRESS

ISSUE:
{negotiation.issue}

CURRENT POSITIONS:
"""
        for agent_id, position in negotiation.positions.items():
            context += f"  • {agent_id.upper()}: {position}\n"

        if negotiation.constraints:
            context += "\nCONSTRAINTS (Non-negotiable):\n"
            for i, constraint in enumerate(negotiation.constraints, 1):
                context += f"{i}. {constraint}\n"

        if negotiation.proposals:
            context += f"\nPREVIOUS ROUNDS: {len(negotiation.proposals)}\n"
            # Show last round's proposals
            last_round = negotiation.proposals[-1]
            context += "Last proposals:\n"
            for agent_id, proposal in last_round["proposals"].items():
                context += f"  • {agent_id}: {proposal[:100]}...\n"

        return context

    def _analyze_proposals(
        self,
        negotiation: NegotiationRequest,
        proposals: Dict[str, str]
    ) -> Dict[str, Any]:
        """Analyze proposals to detect consensus or common ground"""
        # Use supervisor LLM to analyze
        if not self.supervisor_llm:
            # Fallback: simple text similarity
            return self._simple_consensus_check(proposals)

        # LLM-based analysis
        analysis_prompt = f"""Analyze these negotiation proposals for consensus:

ISSUE: {negotiation.issue}

PROPOSALS:
"""
        for agent_id, proposal in proposals.items():
            analysis_prompt += f"\n{agent_id.upper()}: {proposal}\n"

        analysis_prompt += """
ANALYSIS REQUIRED:
1. Is there consensus? (YES/NO)
2. What is the common ground?
3. What are remaining differences?
4. Suggested compromise?

Respond in this format:
CONSENSUS: [YES/NO]
COMMON_GROUND: [what they agree on]
DIFFERENCES: [what they disagree on]
COMPROMISE: [suggested middle ground]
"""

        try:
            response = self.supervisor_llm.chat(analysis_prompt)

            # Parse response
            has_consensus = "CONSENSUS: YES" in response
            common_ground = self._extract_field(response, "COMMON_GROUND")
            differences = self._extract_field(response, "DIFFERENCES")
            compromise = self._extract_field(response, "COMPROMISE")

            return {
                "has_consensus": has_consensus,
                "common_ground": common_ground,
                "differences": differences,
                "suggested_compromise": compromise,
                "proposals": proposals
            }

        except Exception as e:
            logger.error(f"LLM analysis failed: {e}")
            return self._simple_consensus_check(proposals)

    def _simple_consensus_check(
        self,
        proposals: Dict[str, str]
    ) -> Dict[str, Any]:
        """Simple text similarity check for consensus"""
        # Convert all proposals to lowercase for comparison
        normalized = {k: v.lower() for k, v in proposals.items()}

        # Check if all proposals contain similar keywords
        all_words = set()
        for proposal in normalized.values():
            words = set(proposal.split())
            all_words.update(words)

        # Calculate overlap
        common_words = set()
        for word in all_words:
            if all(word in proposal for proposal in normalized.values()):
                common_words.add(word)

        # Simple heuristic: if >30% overlap, consider it consensus
        overlap_ratio = len(common_words) / len(all_words) if all_words else 0
        has_consensus = overlap_ratio > 0.3

        return {
            "has_consensus": has_consensus,
            "common_ground": " ".join(list(common_words)[:10]),
            "differences": "Automated analysis - human review recommended",
            "suggested_compromise": "Continue discussion",
            "proposals": proposals
        }

    def _extract_field(self, text: str, field_name: str) -> str:
        """Extract a field from LLM response"""
        for line in text.split('\n'):
            if line.startswith(f"{field_name}:"):
                return line.split(":", 1)[1].strip()
        return "Not specified"

    def _finalize_consensus(
        self,
        negotiation: NegotiationRequest,
        analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Finalize a successful negotiation"""
        resolution = analysis.get("common_ground", "Agreement reached")

        negotiation.status = "resolved"

        logger.info(
            f"✅ Negotiation {negotiation.negotiation_id} resolved! "
            f"Consensus reached in {negotiation.current_round} rounds"
        )

        # Move to history
        self._negotiation_history.append(negotiation)
        del self._active_negotiations[negotiation.negotiation_id]

        return {
            "status": "resolved",
            "resolution": resolution,
            "rounds": negotiation.current_round,
            "consensus_achieved": True,
            "proposals": analysis["proposals"]
        }

    def _provide_negotiation_guidance(
        self,
        negotiation: NegotiationRequest,
        analysis: Dict[str, Any]
    ) -> str:
        """Supervisor provides guidance to continue negotiation"""
        guidance = f"""SUPERVISOR GUIDANCE - Round {negotiation.current_round}

COMMON GROUND IDENTIFIED:
{analysis.get('common_ground', 'Still seeking alignment')}

REMAINING DIFFERENCES:
{analysis.get('differences', 'Multiple positions')}

SUGGESTED PATH FORWARD:
{analysis.get('suggested_compromise', 'Continue exploring options')}

Please refine your proposals in the next round, focusing on the common ground."""

        return guidance

    def _escalate_negotiation(
        self,
        negotiation: NegotiationRequest,
        reason: str
    ) -> Dict[str, Any]:
        """Escalate negotiation to human intervention"""
        negotiation.status = "escalated"

        logger.warning(
            f"⚠️  Negotiation {negotiation.negotiation_id} escalated: {reason}"
        )

        # Move to history
        self._negotiation_history.append(negotiation)
        del self._active_negotiations[negotiation.negotiation_id]

        return {
            "status": "escalated",
            "reason": reason,
            "rounds_attempted": negotiation.current_round,
            "requires_human_intervention": True,
            "summary": self._generate_escalation_summary(negotiation)
        }

    def _generate_escalation_summary(
        self,
        negotiation: NegotiationRequest
    ) -> str:
        """Generate summary for human review"""
        summary = f"""NEGOTIATION ESCALATION SUMMARY

Issue: {negotiation.issue}
Participants: {', '.join(negotiation.participating_agents)}
Rounds Attempted: {negotiation.current_round}

POSITIONS:
"""
        for agent_id, position in negotiation.positions.items():
            summary += f"  • {agent_id.upper()}: {position}\n"

        if negotiation.proposals:
            summary += f"\nFINAL PROPOSALS (Round {negotiation.current_round}):\n"
            last_proposals = negotiation.proposals[-1]["proposals"]
            for agent_id, proposal in last_proposals.items():
                summary += f"  • {agent_id.upper()}: {proposal}\n"

        summary += "\nRECOMMENDATION: Human coordination meeting required to resolve."

        return summary

    def get_active_negotiations(self) -> List[NegotiationRequest]:
        """Get all active negotiations"""
        return list(self._active_negotiations.values())

    def get_negotiation_status(self, negotiation_id: UUID) -> Dict[str, Any]:
        """Get status of a specific negotiation"""
        if negotiation_id in self._active_negotiations:
            negotiation = self._active_negotiations[negotiation_id]
            return {
                "negotiation_id": negotiation_id,
                "status": negotiation.status,
                "round": negotiation.current_round,
                "max_rounds": negotiation.max_rounds,
                "participants": negotiation.participating_agents,
                "is_active": True
            }

        # Check history
        for negotiation in self._negotiation_history:
            if negotiation.negotiation_id == negotiation_id:
                return {
                    "negotiation_id": negotiation_id,
                    "status": negotiation.status,
                    "round": negotiation.current_round,
                    "participants": negotiation.participating_agents,
                    "is_active": False
                }

        return {"error": "Negotiation not found"}

    def get_negotiation_summary(self) -> Dict[str, Any]:
        """Get summary of all negotiations"""
        active = len(self._active_negotiations)
        total = len(self._negotiation_history) + active

        by_status = {}
        for negotiation in self._negotiation_history:
            status = negotiation.status
            by_status[status] = by_status.get(status, 0) + 1

        for negotiation in self._active_negotiations.values():
            status = negotiation.status
            by_status[status] = by_status.get(status, 0) + 1

        return {
            "total_negotiations": total,
            "active_negotiations": active,
            "completed_negotiations": len(self._negotiation_history),
            "by_status": by_status,
            "success_rate": (
                by_status.get("resolved", 0) / total if total > 0 else 0
            )
        }
