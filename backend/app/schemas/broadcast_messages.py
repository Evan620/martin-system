"""
Broadcast Message Schemas

Defines message types for broadcasting context, documents, and policy updates
from Supervisor to all TWG agents.
"""

from datetime import datetime, UTC
from typing import Dict, List, Optional, Any
from enum import Enum
from pydantic import BaseModel, Field
from uuid import UUID, uuid4


class BroadcastType(str, Enum):
    """Types of broadcasts from Supervisor to agents"""
    STRATEGIC_CONTEXT = "strategic_context"  # Summit objectives, priorities
    DOCUMENT_UPDATE = "document_update"      # Core documents (Concept Note, Declaration)
    POLICY_GUIDANCE = "policy_guidance"      # Policy directions, constraints
    CONFLICT_ALERT = "conflict_alert"        # Notification of detected conflicts
    COORDINATION_REQUEST = "coordination_request"  # Request for inter-TWG alignment
    DEADLINE_REMINDER = "deadline_reminder"  # Important deadlines


class BroadcastPriority(str, Enum):
    """Priority levels for broadcasts"""
    CRITICAL = "critical"  # Must be acknowledged immediately
    HIGH = "high"          # Important, review soon
    NORMAL = "normal"      # Standard information
    LOW = "low"            # FYI only


class DocumentType(str, Enum):
    """Types of documents that can be broadcast"""
    CONCEPT_NOTE = "concept_note"
    DECLARATION_DRAFT = "declaration_draft"
    SUMMIT_OBJECTIVES = "summit_objectives"
    POLICY_FRAMEWORK = "policy_framework"
    STRATEGIC_PLAYBOOK = "strategic_playbook"
    GUIDELINES = "guidelines"
    REFERENCE_MATERIAL = "reference_material"


class BroadcastMessage(BaseModel):
    """Message broadcast from Supervisor to all agents"""
    broadcast_id: UUID = Field(default_factory=uuid4)
    type: BroadcastType
    priority: BroadcastPriority = Field(default=BroadcastPriority.NORMAL)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # Content
    title: str = Field(..., description="Brief title of the broadcast")
    content: str = Field(..., description="Main content or message")
    metadata: Dict[str, Any] = Field(default_factory=dict)

    # Document attachments (if applicable)
    documents: List[Dict[str, str]] = Field(default_factory=list)

    # Targeting
    target_agents: Optional[List[str]] = Field(
        default=None,
        description="Specific agents to target, None means all agents"
    )

    # Acknowledgement tracking
    requires_acknowledgement: bool = Field(default=False)
    acknowledged_by: List[str] = Field(default_factory=list)

    expires_at: Optional[datetime] = Field(
        default=None,
        description="When this broadcast becomes stale"
    )


class ContextBroadcast(BaseModel):
    """Broadcast of strategic context to all agents"""
    broadcast_id: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # Strategic context
    summit_objectives: List[str] = Field(
        default_factory=list,
        description="Overarching Summit objectives"
    )
    strategic_priorities: List[str] = Field(
        default_factory=list,
        description="Current strategic priorities"
    )
    policy_constraints: List[str] = Field(
        default_factory=list,
        description="Policy guardrails and constraints"
    )
    cross_cutting_themes: List[str] = Field(
        default_factory=list,
        description="Themes that span all TWGs (e.g., youth, gender, climate)"
    )

    # Coordination guidelines
    coordination_points: Dict[str, str] = Field(
        default_factory=dict,
        description="Key points where TWGs must coordinate"
    )

    # Version tracking
    version: str = Field(default="1.0")
    supersedes: Optional[UUID] = Field(
        default=None,
        description="Previous context broadcast this replaces"
    )


class DocumentBroadcast(BaseModel):
    """Broadcast of a key document to agents"""
    broadcast_id: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

    document_type: DocumentType
    document_title: str
    version: str

    # Content
    full_text: Optional[str] = Field(
        default=None,
        description="Full document text"
    )
    summary: str = Field(..., description="Executive summary")
    key_points: List[str] = Field(
        default_factory=list,
        description="Key points agents should note"
    )

    # Relevant sections per agent
    relevant_sections: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Map of agent_id to relevant sections"
    )

    # File reference
    file_path: Optional[str] = Field(default=None)
    file_url: Optional[str] = Field(default=None)

    # Change tracking
    changes_from_previous: Optional[str] = Field(
        default=None,
        description="Summary of changes from previous version"
    )
    supersedes_version: Optional[str] = Field(default=None)


class ConflictAlert(BaseModel):
    """Alert about detected conflicts between TWG outputs"""
    alert_id: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # Conflict details
    conflict_type: str = Field(
        ...,
        description="Type of conflict (policy, session, target, resource)"
    )
    severity: str = Field(
        ...,
        description="Severity: critical, high, medium, low"
    )

    # Involved parties
    agents_involved: List[str] = Field(
        ...,
        description="TWG agents involved in conflict"
    )

    # Conflict description
    description: str = Field(..., description="Clear description of conflict")
    conflicting_positions: Dict[str, str] = Field(
        ...,
        description="Map of agent_id to their position"
    )

    # Context
    impact: str = Field(..., description="Impact of this conflict")
    urgency: str = Field(..., description="How urgent is resolution")

    # Resolution
    suggested_resolution: Optional[str] = Field(default=None)
    requires_negotiation: bool = Field(default=False)
    requires_human_intervention: bool = Field(default=False)

    # Status tracking
    status: str = Field(
        default="pending",
        description="Status: pending, in_negotiation, resolved, escalated"
    )
    resolution: Optional[str] = Field(default=None)
    resolved_at: Optional[datetime] = Field(default=None)


class NegotiationRequest(BaseModel):
    """Request for agents to negotiate and reconcile differences"""
    negotiation_id: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # Related conflict
    conflict_id: UUID = Field(..., description="ID of conflict being negotiated")

    # Participants
    participating_agents: List[str] = Field(
        ...,
        description="Agents that must participate in negotiation"
    )

    # Issue to resolve
    issue: str = Field(..., description="Clear statement of issue")
    positions: Dict[str, str] = Field(
        ...,
        description="Current position of each agent"
    )

    # Negotiation parameters
    negotiation_type: str = Field(
        default="consensus",
        description="Type: consensus, compromise, arbitration"
    )
    deadline: Optional[datetime] = Field(default=None)
    max_rounds: int = Field(default=3, description="Max negotiation rounds")

    # Constraints and guidelines
    constraints: List[str] = Field(
        default_factory=list,
        description="Non-negotiable constraints"
    )
    success_criteria: List[str] = Field(
        default_factory=list,
        description="What constitutes a successful resolution"
    )

    # Tracking
    current_round: int = Field(default=0)
    proposals: List[Dict[str, Any]] = Field(default_factory=list)
    status: str = Field(
        default="initiated",
        description="Status: initiated, in_progress, resolved, failed, escalated"
    )


class BroadcastAcknowledgement(BaseModel):
    """Acknowledgement of a broadcast by an agent"""
    ack_id: UUID = Field(default_factory=uuid4)
    broadcast_id: UUID = Field(..., description="ID of broadcast being acknowledged")
    agent_id: str = Field(..., description="Agent acknowledging")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # Acknowledgement details
    acknowledged: bool = Field(default=True)
    understood: bool = Field(default=True)

    # Optional feedback
    notes: Optional[str] = Field(
        default=None,
        description="Agent's notes or questions about the broadcast"
    )
    concerns: Optional[str] = Field(
        default=None,
        description="Any concerns flagged by the agent"
    )

    # Impact assessment
    impact_on_work: Optional[str] = Field(
        default=None,
        description="How this broadcast affects the agent's work"
    )


def create_context_broadcast(
    summit_objectives: List[str],
    strategic_priorities: List[str],
    policy_constraints: Optional[List[str]] = None,
    cross_cutting_themes: Optional[List[str]] = None,
    coordination_points: Optional[Dict[str, str]] = None,
    version: str = "1.0"
) -> ContextBroadcast:
    """Helper to create a context broadcast"""
    return ContextBroadcast(
        summit_objectives=summit_objectives,
        strategic_priorities=strategic_priorities,
        policy_constraints=policy_constraints or [],
        cross_cutting_themes=cross_cutting_themes or [],
        coordination_points=coordination_points or {},
        version=version
    )


def create_document_broadcast(
    document_type: DocumentType,
    title: str,
    version: str,
    summary: str,
    key_points: List[str],
    full_text: Optional[str] = None,
    relevant_sections: Optional[Dict[str, List[str]]] = None
) -> DocumentBroadcast:
    """Helper to create a document broadcast"""
    return DocumentBroadcast(
        document_type=document_type,
        document_title=title,
        version=version,
        summary=summary,
        key_points=key_points,
        full_text=full_text,
        relevant_sections=relevant_sections or {}
    )


def create_conflict_alert(
    conflict_type: str,
    severity: str,
    agents_involved: List[str],
    description: str,
    conflicting_positions: Dict[str, str],
    impact: str,
    urgency: str,
    suggested_resolution: Optional[str] = None,
    requires_negotiation: bool = False,
    requires_human_intervention: bool = False
) -> ConflictAlert:
    """Helper to create a conflict alert"""
    return ConflictAlert(
        conflict_type=conflict_type,
        severity=severity,
        agents_involved=agents_involved,
        description=description,
        conflicting_positions=conflicting_positions,
        impact=impact,
        urgency=urgency,
        suggested_resolution=suggested_resolution,
        requires_negotiation=requires_negotiation,
        requires_human_intervention=requires_human_intervention
    )


def create_negotiation_request(
    conflict_id: UUID,
    participating_agents: List[str],
    issue: str,
    positions: Dict[str, str],
    constraints: Optional[List[str]] = None,
    success_criteria: Optional[List[str]] = None,
    deadline: Optional[datetime] = None,
    max_rounds: int = 3
) -> NegotiationRequest:
    """Helper to create a negotiation request"""
    return NegotiationRequest(
        conflict_id=conflict_id,
        participating_agents=participating_agents,
        issue=issue,
        positions=positions,
        constraints=constraints or [],
        success_criteria=success_criteria or [],
        deadline=deadline,
        max_rounds=max_rounds
    )
