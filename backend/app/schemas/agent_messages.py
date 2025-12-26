"""
Agent Message Protocol Schema

Defines the structured message protocol for agent-to-agent communication
using Pydantic models for validation and serialization.

Message Types:
- REQUEST: Agent requesting action from another agent
- RESPONSE: Agent responding to a request
- ERROR: Error message
- EVENT: Pub/sub event notification
- DELEGATION: Agent delegating task to peer

Status Flow: PENDING → DELIVERED → PROCESSING → COMPLETED/FAILED
"""

from enum import Enum
from typing import Optional, Dict, Any, List
from datetime import datetime, UTC
from uuid import UUID, uuid4
from pydantic import BaseModel, Field, field_validator, ConfigDict


class MessageType(str, Enum):
    """Types of messages that can be exchanged between agents"""
    REQUEST = "request"
    RESPONSE = "response"
    ERROR = "error"
    EVENT = "event"
    DELEGATION = "delegation"


class MessageStatus(str, Enum):
    """Status of a message in its lifecycle"""
    PENDING = "pending"
    DELIVERED = "delivered"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class MessagePriority(str, Enum):
    """Priority levels for message processing"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class MessageMetadata(BaseModel):
    """
    Metadata for tracking and correlating messages.

    Fields:
        message_id: Unique identifier for this message
        timestamp: When the message was created (ISO format)
        sender_id: Agent ID that sent the message
        recipient_id: Agent ID that should receive the message
        session_id: Session identifier for grouping related messages
        trace_id: Trace ID for tracking delegation chains
        correlation_id: ID linking request/response pairs
        delegation_depth: Current depth in delegation chain (0 = original)
    """
    message_id: UUID = Field(default_factory=uuid4, description="Unique message identifier")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Message creation time")
    sender_id: str = Field(..., description="Sender agent ID")
    recipient_id: str = Field(..., description="Recipient agent ID")
    session_id: Optional[str] = Field(None, description="Session identifier")
    trace_id: UUID = Field(default_factory=uuid4, description="Delegation chain trace ID")
    correlation_id: Optional[UUID] = Field(None, description="Correlates request/response")
    delegation_depth: int = Field(default=0, ge=0, description="Delegation chain depth")

    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }
    )


class AgentMessage(BaseModel):
    """
    Base message for all agent-to-agent communication.

    This is the fundamental unit of communication between agents.
    All specialized message types extend this base class.
    """
    metadata: MessageMetadata
    type: MessageType
    status: MessageStatus = Field(default=MessageStatus.PENDING)
    priority: MessagePriority = Field(default=MessagePriority.NORMAL)
    payload: Dict[str, Any] = Field(default_factory=dict, description="Message content")
    error: Optional[str] = Field(None, description="Error message if status is FAILED")

    @field_validator('payload')
    @classmethod
    def validate_payload(cls, v):
        """Ensure payload is a dictionary"""
        if not isinstance(v, dict):
            raise ValueError("Payload must be a dictionary")
        return v

    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary for JSON serialization"""
        return self.model_dump(mode='json')

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentMessage':
        """Create message from dictionary"""
        return cls.model_validate(data)

    def mark_delivered(self) -> None:
        """Mark message as delivered"""
        self.status = MessageStatus.DELIVERED

    def mark_processing(self) -> None:
        """Mark message as being processed"""
        self.status = MessageStatus.PROCESSING

    def mark_completed(self) -> None:
        """Mark message as completed"""
        self.status = MessageStatus.COMPLETED

    def mark_failed(self, error: str) -> None:
        """Mark message as failed with error message"""
        self.status = MessageStatus.FAILED
        self.error = error

    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }
    )


class DelegationRequest(AgentMessage):
    """
    Specialized message for agent delegation requests.

    Used when one agent needs to delegate a task to another agent,
    either through the supervisor or peer-to-peer.

    Payload structure:
        - query: The question/task to delegate
        - context: Optional context from previous conversation
        - requires_response: Whether a response is expected
        - timeout: Maximum time to wait for response (seconds)
    """
    type: MessageType = Field(default=MessageType.DELEGATION, frozen=True)

    @field_validator('payload')
    @classmethod
    def validate_delegation_payload(cls, v):
        """Ensure delegation payload has required fields"""
        if 'query' not in v:
            raise ValueError("Delegation payload must contain 'query' field")
        return v

    @property
    def query(self) -> str:
        """Get the query from payload"""
        return self.payload.get('query', '')

    @property
    def context(self) -> Optional[List[Dict[str, str]]]:
        """Get optional conversation context"""
        return self.payload.get('context')

    @property
    def requires_response(self) -> bool:
        """Check if response is required"""
        return self.payload.get('requires_response', True)

    @property
    def timeout(self) -> int:
        """Get timeout in seconds"""
        return self.payload.get('timeout', 30)


class AgentResponse(AgentMessage):
    """
    Specialized message for agent responses.

    Used when an agent responds to a request or delegation.
    The correlation_id links this response to the original request.

    Payload structure:
        - response: The actual response content
        - confidence: Confidence score (0.0-1.0)
        - processing_time: Time taken to process (seconds)
        - sources: Optional list of sources/references
    """
    type: MessageType = Field(default=MessageType.RESPONSE, frozen=True)

    @field_validator('payload')
    @classmethod
    def validate_response_payload(cls, v):
        """Ensure response payload has required fields"""
        if 'response' not in v:
            raise ValueError("Response payload must contain 'response' field")
        return v

    @property
    def response(self) -> str:
        """Get the response content"""
        return self.payload.get('response', '')

    @property
    def confidence(self) -> Optional[float]:
        """Get confidence score (0.0-1.0)"""
        return self.payload.get('confidence')

    @property
    def processing_time(self) -> Optional[float]:
        """Get processing time in seconds"""
        return self.payload.get('processing_time')

    @property
    def sources(self) -> Optional[List[str]]:
        """Get sources/references"""
        return self.payload.get('sources')


class AgentEvent(AgentMessage):
    """
    Specialized message for pub/sub events.

    Used for broadcasting events that multiple agents may subscribe to.
    Events are fire-and-forget (no response expected).

    Payload structure:
        - event_type: Type of event (e.g., 'agent_started', 'task_completed')
        - data: Event-specific data
    """
    type: MessageType = Field(default=MessageType.EVENT, frozen=True)

    @field_validator('payload')
    @classmethod
    def validate_event_payload(cls, v):
        """Ensure event payload has required fields"""
        if 'event_type' not in v:
            raise ValueError("Event payload must contain 'event_type' field")
        return v

    @property
    def event_type(self) -> str:
        """Get the event type"""
        return self.payload.get('event_type', '')

    @property
    def data(self) -> Dict[str, Any]:
        """Get event data"""
        return self.payload.get('data', {})


class ErrorMessage(AgentMessage):
    """
    Specialized message for error notifications.

    Used when an agent encounters an error processing a request.

    Payload structure:
        - error_code: Machine-readable error code
        - error_message: Human-readable error message
        - stack_trace: Optional stack trace for debugging
        - original_request: Optional reference to request that caused error
    """
    type: MessageType = Field(default=MessageType.ERROR, frozen=True)

    @field_validator('payload')
    @classmethod
    def validate_error_payload(cls, v):
        """Ensure error payload has required fields"""
        if 'error_code' not in v or 'error_message' not in v:
            raise ValueError("Error payload must contain 'error_code' and 'error_message'")
        return v

    @property
    def error_code(self) -> str:
        """Get error code"""
        return self.payload.get('error_code', 'UNKNOWN')

    @property
    def error_message(self) -> str:
        """Get error message"""
        return self.payload.get('error_message', '')

    @property
    def stack_trace(self) -> Optional[str]:
        """Get stack trace if available"""
        return self.payload.get('stack_trace')


# Helper functions for creating messages

def create_delegation_request(
    sender_id: str,
    recipient_id: str,
    query: str,
    session_id: Optional[str] = None,
    context: Optional[List[Dict[str, str]]] = None,
    trace_id: Optional[UUID] = None,
    delegation_depth: int = 0,
    timeout: int = 30,
    priority: MessagePriority = MessagePriority.NORMAL
) -> DelegationRequest:
    """
    Create a delegation request message.

    Args:
        sender_id: Agent sending the delegation
        recipient_id: Agent receiving the delegation
        query: The question/task to delegate
        session_id: Session identifier
        context: Optional conversation context
        trace_id: Trace ID for delegation chain
        delegation_depth: Current depth in delegation chain
        timeout: Maximum wait time for response
        priority: Message priority

    Returns:
        DelegationRequest message
    """
    metadata = MessageMetadata(
        sender_id=sender_id,
        recipient_id=recipient_id,
        session_id=session_id,
        trace_id=trace_id or uuid4(),
        delegation_depth=delegation_depth
    )

    payload = {
        "query": query,
        "context": context,
        "requires_response": True,
        "timeout": timeout
    }

    return DelegationRequest(
        metadata=metadata,
        priority=priority,
        payload=payload
    )


def create_agent_response(
    sender_id: str,
    recipient_id: str,
    response: str,
    correlation_id: UUID,
    session_id: Optional[str] = None,
    confidence: Optional[float] = None,
    processing_time: Optional[float] = None,
    sources: Optional[List[str]] = None
) -> AgentResponse:
    """
    Create an agent response message.

    Args:
        sender_id: Agent sending the response
        recipient_id: Agent receiving the response
        response: The response content
        correlation_id: ID of the request being responded to
        session_id: Session identifier
        confidence: Confidence score (0.0-1.0)
        processing_time: Time taken to process
        sources: Optional sources/references

    Returns:
        AgentResponse message
    """
    metadata = MessageMetadata(
        sender_id=sender_id,
        recipient_id=recipient_id,
        session_id=session_id,
        correlation_id=correlation_id
    )

    payload = {
        "response": response,
        "confidence": confidence,
        "processing_time": processing_time,
        "sources": sources
    }

    return AgentResponse(
        metadata=metadata,
        status=MessageStatus.COMPLETED,
        payload=payload
    )


def create_agent_event(
    sender_id: str,
    event_type: str,
    data: Dict[str, Any],
    session_id: Optional[str] = None,
    priority: MessagePriority = MessagePriority.NORMAL
) -> AgentEvent:
    """
    Create an agent event message for pub/sub.

    Args:
        sender_id: Agent publishing the event
        event_type: Type of event
        data: Event-specific data
        session_id: Session identifier
        priority: Message priority

    Returns:
        AgentEvent message
    """
    metadata = MessageMetadata(
        sender_id=sender_id,
        recipient_id="*",  # Broadcast
        session_id=session_id
    )

    payload = {
        "event_type": event_type,
        "data": data
    }

    return AgentEvent(
        metadata=metadata,
        priority=priority,
        payload=payload
    )


def create_error_message(
    sender_id: str,
    recipient_id: str,
    error_code: str,
    error_message: str,
    correlation_id: Optional[UUID] = None,
    session_id: Optional[str] = None,
    stack_trace: Optional[str] = None
) -> ErrorMessage:
    """
    Create an error message.

    Args:
        sender_id: Agent reporting the error
        recipient_id: Agent to receive error notification
        error_code: Machine-readable error code
        error_message: Human-readable error message
        correlation_id: ID of request that caused error
        session_id: Session identifier
        stack_trace: Optional stack trace

    Returns:
        ErrorMessage
    """
    metadata = MessageMetadata(
        sender_id=sender_id,
        recipient_id=recipient_id,
        session_id=session_id,
        correlation_id=correlation_id
    )

    payload = {
        "error_code": error_code,
        "error_message": error_message,
        "stack_trace": stack_trace
    }

    return ErrorMessage(
        metadata=metadata,
        status=MessageStatus.FAILED,
        payload=payload
    )
