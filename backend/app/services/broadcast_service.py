"""
Broadcast Service

Handles broadcasting of strategic context, documents, and alerts
from Supervisor to all TWG agents.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, UTC
from loguru import logger
from uuid import UUID

from app.schemas.broadcast_messages import (
    BroadcastMessage,
    BroadcastType,
    BroadcastPriority,
    ContextBroadcast,
    DocumentBroadcast,
    BroadcastAcknowledgement
)


class BroadcastService:
    """Service for managing broadcasts to agents"""

    def __init__(self):
        """Initialize broadcast service"""
        self._broadcast_history: List[BroadcastMessage] = []
        self._context_broadcasts: List[ContextBroadcast] = []
        self._document_broadcasts: List[DocumentBroadcast] = []
        self._acknowledgements: Dict[UUID, List[BroadcastAcknowledgement]] = {}

        # Active context (latest strategic playbook)
        self._active_context: Optional[ContextBroadcast] = None

    def broadcast_message(
        self,
        message: BroadcastMessage,
        agents: Dict[str, Any]
    ) -> Dict[str, bool]:
        """
        Broadcast a message to all or specific agents.

        Args:
            message: The broadcast message
            agents: Dictionary of agent_id -> agent instance

        Returns:
            Dict mapping agent_id to success status
        """
        self._broadcast_history.append(message)

        # Determine target agents
        if message.target_agents:
            target_ids = message.target_agents
        else:
            target_ids = list(agents.keys())

        results = {}
        for agent_id in target_ids:
            if agent_id not in agents:
                logger.warning(f"Agent {agent_id} not found in registry")
                results[agent_id] = False
                continue

            try:
                # Deliver broadcast to agent
                success = self._deliver_to_agent(
                    agent_id,
                    agents[agent_id],
                    message
                )
                results[agent_id] = success

                if success:
                    logger.info(
                        f"✓ Broadcast {message.broadcast_id} delivered to {agent_id}"
                    )
                else:
                    logger.warning(
                        f"✗ Failed to deliver broadcast to {agent_id}"
                    )

            except Exception as e:
                logger.error(
                    f"Error delivering broadcast to {agent_id}: {e}"
                )
                results[agent_id] = False

        return results

    def _deliver_to_agent(
        self,
        agent_id: str,
        agent: Any,
        message: BroadcastMessage
    ) -> bool:
        """
        Deliver a broadcast message to a specific agent.

        This injects the broadcast content into the agent's context
        so it can use it in responses.

        Args:
            agent_id: ID of the agent
            agent: Agent instance
            message: Broadcast message

        Returns:
            bool: True if delivery successful
        """
        try:
            # Format broadcast for agent consumption
            broadcast_context = self._format_for_agent(message)

            # Store in agent's context (if they support it)
            if hasattr(agent, 'add_broadcast_context'):
                agent.add_broadcast_context(broadcast_context)
            elif hasattr(agent, '_broadcast_context'):
                # Fallback: store in attribute
                if not hasattr(agent, '_broadcast_context'):
                    agent._broadcast_context = []
                agent._broadcast_context.append(broadcast_context)
            else:
                # No broadcast support, just log
                logger.debug(
                    f"Agent {agent_id} doesn't support broadcast context"
                )

            return True

        except Exception as e:
            logger.error(f"Error delivering to {agent_id}: {e}")
            return False

    def _format_for_agent(self, message: BroadcastMessage) -> str:
        """Format broadcast message for agent consumption"""
        priority_marker = {
            BroadcastPriority.CRITICAL: "🚨 CRITICAL",
            BroadcastPriority.HIGH: "⚠️  HIGH PRIORITY",
            BroadcastPriority.NORMAL: "📢 BROADCAST",
            BroadcastPriority.LOW: "ℹ️  FYI"
        }

        formatted = f"\n{'='*70}\n"
        formatted += f"{priority_marker.get(message.priority, '📢')} - {message.title}\n"
        formatted += f"{'='*70}\n\n"
        formatted += message.content
        formatted += "\n\n"

        if message.documents:
            formatted += "📄 ATTACHED DOCUMENTS:\n"
            for doc in message.documents:
                formatted += f"  - {doc.get('title', 'Untitled')}\n"
            formatted += "\n"

        if message.requires_acknowledgement:
            formatted += "⚠️  This broadcast requires acknowledgement.\n\n"

        formatted += f"{'='*70}\n"

        return formatted

    def broadcast_context(
        self,
        context: ContextBroadcast,
        agents: Dict[str, Any]
    ) -> Dict[str, bool]:
        """
        Broadcast strategic context to all agents.

        Args:
            context: Context broadcast
            agents: Dictionary of agents

        Returns:
            Dict of delivery results
        """
        self._context_broadcasts.append(context)
        self._active_context = context

        # Convert to BroadcastMessage
        message = BroadcastMessage(
            broadcast_id=context.broadcast_id,
            type=BroadcastType.STRATEGIC_CONTEXT,
            priority=BroadcastPriority.HIGH,
            title="Strategic Context Update",
            content=self._format_context_content(context),
            requires_acknowledgement=True
        )

        return self.broadcast_message(message, agents)

    def _format_context_content(self, context: ContextBroadcast) -> str:
        """Format context broadcast content"""
        content = "STRATEGIC PLAYBOOK UPDATE\n\n"

        if context.summit_objectives:
            content += "🎯 SUMMIT OBJECTIVES:\n"
            for i, obj in enumerate(context.summit_objectives, 1):
                content += f"{i}. {obj}\n"
            content += "\n"

        if context.strategic_priorities:
            content += "⭐ STRATEGIC PRIORITIES:\n"
            for i, priority in enumerate(context.strategic_priorities, 1):
                content += f"{i}. {priority}\n"
            content += "\n"

        if context.policy_constraints:
            content += "🚧 POLICY CONSTRAINTS:\n"
            for constraint in context.policy_constraints:
                content += f"  • {constraint}\n"
            content += "\n"

        if context.cross_cutting_themes:
            content += "🔗 CROSS-CUTTING THEMES:\n"
            for theme in context.cross_cutting_themes:
                content += f"  • {theme}\n"
            content += "\n"

        if context.coordination_points:
            content += "🤝 COORDINATION REQUIREMENTS:\n"
            for point, details in context.coordination_points.items():
                content += f"  • {point}: {details}\n"
            content += "\n"

        content += f"Version: {context.version}\n"
        content += f"Effective: {context.timestamp.isoformat()}\n"

        return content

    def broadcast_document(
        self,
        document: DocumentBroadcast,
        agents: Dict[str, Any]
    ) -> Dict[str, bool]:
        """
        Broadcast a key document to all agents.

        Args:
            document: Document broadcast
            agents: Dictionary of agents

        Returns:
            Dict of delivery results
        """
        self._document_broadcasts.append(document)

        # Convert to BroadcastMessage
        message = BroadcastMessage(
            broadcast_id=document.broadcast_id,
            type=BroadcastType.DOCUMENT_UPDATE,
            priority=BroadcastPriority.HIGH,
            title=f"New Document: {document.document_title} v{document.version}",
            content=self._format_document_content(document),
            requires_acknowledgement=True,
            metadata={
                "document_type": document.document_type,
                "version": document.version
            }
        )

        return self.broadcast_message(message, agents)

    def _format_document_content(self, document: DocumentBroadcast) -> str:
        """Format document broadcast content"""
        content = f"DOCUMENT UPDATE: {document.document_title}\n\n"
        content += f"Type: {document.document_type.value}\n"
        content += f"Version: {document.version}\n\n"

        content += "📋 SUMMARY:\n"
        content += f"{document.summary}\n\n"

        if document.key_points:
            content += "🔑 KEY POINTS:\n"
            for i, point in enumerate(document.key_points, 1):
                content += f"{i}. {point}\n"
            content += "\n"

        if document.changes_from_previous:
            content += "📝 CHANGES FROM PREVIOUS VERSION:\n"
            content += f"{document.changes_from_previous}\n\n"

        if document.file_path:
            content += f"📁 File: {document.file_path}\n"

        return content

    def acknowledge_broadcast(
        self,
        acknowledgement: BroadcastAcknowledgement
    ) -> None:
        """
        Record an agent's acknowledgement of a broadcast.

        Args:
            acknowledgement: Acknowledgement message
        """
        broadcast_id = acknowledgement.broadcast_id

        if broadcast_id not in self._acknowledgements:
            self._acknowledgements[broadcast_id] = []

        self._acknowledgements[broadcast_id].append(acknowledgement)

        logger.info(
            f"✓ Agent {acknowledgement.agent_id} acknowledged broadcast {broadcast_id}"
        )

        if acknowledgement.concerns:
            logger.warning(
                f"⚠️  Agent {acknowledgement.agent_id} raised concerns: "
                f"{acknowledgement.concerns}"
            )

    def get_acknowledgement_status(
        self,
        broadcast_id: UUID,
        expected_agents: List[str]
    ) -> Dict[str, Any]:
        """
        Get acknowledgement status for a broadcast.

        Args:
            broadcast_id: ID of the broadcast
            expected_agents: List of agents expected to acknowledge

        Returns:
            Dict with acknowledgement status
        """
        acks = self._acknowledgements.get(broadcast_id, [])
        acked_by = {ack.agent_id for ack in acks}

        return {
            "broadcast_id": broadcast_id,
            "total_expected": len(expected_agents),
            "acknowledged": len(acked_by),
            "pending": len(set(expected_agents) - acked_by),
            "acknowledged_by": list(acked_by),
            "pending_from": list(set(expected_agents) - acked_by),
            "completion_rate": len(acked_by) / len(expected_agents) if expected_agents else 0
        }

    def get_active_context(self) -> Optional[ContextBroadcast]:
        """Get the currently active strategic context"""
        return self._active_context

    def get_broadcast_history(
        self,
        limit: Optional[int] = None,
        broadcast_type: Optional[BroadcastType] = None
    ) -> List[BroadcastMessage]:
        """
        Get broadcast history.

        Args:
            limit: Maximum number of broadcasts to return
            broadcast_type: Filter by broadcast type

        Returns:
            List of broadcasts (most recent first)
        """
        history = self._broadcast_history

        if broadcast_type:
            history = [b for b in history if b.type == broadcast_type]

        # Sort by timestamp (most recent first)
        history = sorted(history, key=lambda b: b.timestamp, reverse=True)

        if limit:
            history = history[:limit]

        return history
