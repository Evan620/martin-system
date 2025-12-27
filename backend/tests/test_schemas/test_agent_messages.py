"""
Unit Tests for Agent Message Schema

Tests all message types, validation, serialization/deserialization,
and helper functions.
"""

import pytest
import json
from uuid import uuid4, UUID
from datetime import datetime

from app.schemas.agent_messages import (
    MessageType,
    MessageStatus,
    MessagePriority,
    MessageMetadata,
    AgentMessage,
    DelegationRequest,
    AgentResponse,
    AgentEvent,
    ErrorMessage,
    create_delegation_request,
    create_agent_response,
    create_agent_event,
    create_error_message
)


class TestMessageEnums:
    """Test message enums"""

    def test_message_type_enum(self):
        """Test MessageType enum values"""
        assert MessageType.REQUEST == "request"
        assert MessageType.RESPONSE == "response"
        assert MessageType.ERROR == "error"
        assert MessageType.EVENT == "event"
        assert MessageType.DELEGATION == "delegation"

    def test_message_status_enum(self):
        """Test MessageStatus enum values"""
        assert MessageStatus.PENDING == "pending"
        assert MessageStatus.DELIVERED == "delivered"
        assert MessageStatus.PROCESSING == "processing"
        assert MessageStatus.COMPLETED == "completed"
        assert MessageStatus.FAILED == "failed"

    def test_message_priority_enum(self):
        """Test MessagePriority enum values"""
        assert MessagePriority.LOW == "low"
        assert MessagePriority.NORMAL == "normal"
        assert MessagePriority.HIGH == "high"
        assert MessagePriority.URGENT == "urgent"


class TestMessageMetadata:
    """Test MessageMetadata model"""

    def test_create_metadata_minimal(self):
        """Test creating metadata with minimal fields"""
        metadata = MessageMetadata(
            sender_id="supervisor",
            recipient_id="energy"
        )

        assert metadata.sender_id == "supervisor"
        assert metadata.recipient_id == "energy"
        assert isinstance(metadata.message_id, UUID)
        assert isinstance(metadata.timestamp, datetime)
        assert isinstance(metadata.trace_id, UUID)
        assert metadata.delegation_depth == 0
        assert metadata.session_id is None
        assert metadata.correlation_id is None

    def test_create_metadata_full(self):
        """Test creating metadata with all fields"""
        message_id = uuid4()
        trace_id = uuid4()
        correlation_id = uuid4()
        timestamp = datetime.utcnow()

        metadata = MessageMetadata(
            message_id=message_id,
            timestamp=timestamp,
            sender_id="supervisor",
            recipient_id="energy",
            session_id="test-session",
            trace_id=trace_id,
            correlation_id=correlation_id,
            delegation_depth=2
        )

        assert metadata.message_id == message_id
        assert metadata.timestamp == timestamp
        assert metadata.sender_id == "supervisor"
        assert metadata.recipient_id == "energy"
        assert metadata.session_id == "test-session"
        assert metadata.trace_id == trace_id
        assert metadata.correlation_id == correlation_id
        assert metadata.delegation_depth == 2

    def test_metadata_json_serialization(self):
        """Test metadata serializes to JSON correctly"""
        metadata = MessageMetadata(
            sender_id="supervisor",
            recipient_id="energy"
        )

        metadata_dict = metadata.model_dump(mode='json')

        assert isinstance(metadata_dict['message_id'], str)
        assert isinstance(metadata_dict['timestamp'], str)
        assert isinstance(metadata_dict['trace_id'], str)


class TestAgentMessage:
    """Test base AgentMessage model"""

    def test_create_message_minimal(self):
        """Test creating message with minimal fields"""
        metadata = MessageMetadata(
            sender_id="supervisor",
            recipient_id="energy"
        )

        message = AgentMessage(
            metadata=metadata,
            type=MessageType.REQUEST
        )

        assert message.metadata == metadata
        assert message.type == MessageType.REQUEST
        assert message.status == MessageStatus.PENDING
        assert message.priority == MessagePriority.NORMAL
        assert message.payload == {}
        assert message.error is None

    def test_create_message_with_payload(self):
        """Test creating message with payload"""
        metadata = MessageMetadata(
            sender_id="supervisor",
            recipient_id="energy"
        )

        payload = {"query": "What are the energy initiatives?"}

        message = AgentMessage(
            metadata=metadata,
            type=MessageType.REQUEST,
            payload=payload
        )

        assert message.payload == payload
        assert message.payload["query"] == "What are the energy initiatives?"

    def test_message_status_transitions(self):
        """Test message status transition methods"""
        metadata = MessageMetadata(
            sender_id="supervisor",
            recipient_id="energy"
        )

        message = AgentMessage(
            metadata=metadata,
            type=MessageType.REQUEST
        )

        # Initial status
        assert message.status == MessageStatus.PENDING

        # Mark delivered
        message.mark_delivered()
        assert message.status == MessageStatus.DELIVERED

        # Mark processing
        message.mark_processing()
        assert message.status == MessageStatus.PROCESSING

        # Mark completed
        message.mark_completed()
        assert message.status == MessageStatus.COMPLETED

    def test_message_mark_failed(self):
        """Test marking message as failed"""
        metadata = MessageMetadata(
            sender_id="supervisor",
            recipient_id="energy"
        )

        message = AgentMessage(
            metadata=metadata,
            type=MessageType.REQUEST
        )

        message.mark_failed("Connection timeout")

        assert message.status == MessageStatus.FAILED
        assert message.error == "Connection timeout"

    def test_message_to_dict(self):
        """Test message serialization to dict"""
        metadata = MessageMetadata(
            sender_id="supervisor",
            recipient_id="energy"
        )

        message = AgentMessage(
            metadata=metadata,
            type=MessageType.REQUEST,
            payload={"test": "data"}
        )

        message_dict = message.to_dict()

        assert isinstance(message_dict, dict)
        assert message_dict['type'] == "request"
        assert message_dict['status'] == "pending"
        assert message_dict['payload'] == {"test": "data"}

    def test_message_from_dict(self):
        """Test message deserialization from dict"""
        message_dict = {
            "metadata": {
                "message_id": str(uuid4()),
                "timestamp": datetime.utcnow().isoformat(),
                "sender_id": "supervisor",
                "recipient_id": "energy",
                "trace_id": str(uuid4()),
                "delegation_depth": 0
            },
            "type": "request",
            "status": "pending",
            "priority": "normal",
            "payload": {"test": "data"}
        }

        message = AgentMessage.from_dict(message_dict)

        assert message.type == MessageType.REQUEST
        assert message.status == MessageStatus.PENDING
        assert message.payload == {"test": "data"}

    def test_message_invalid_payload(self):
        """Test that non-dict payload raises error"""
        from pydantic import ValidationError

        metadata = MessageMetadata(
            sender_id="supervisor",
            recipient_id="energy"
        )

        with pytest.raises(ValidationError, match="Input should be a valid dictionary"):
            AgentMessage(
                metadata=metadata,
                type=MessageType.REQUEST,
                payload="invalid"
            )


class TestDelegationRequest:
    """Test DelegationRequest message"""

    def test_create_delegation_request(self):
        """Test creating delegation request"""
        metadata = MessageMetadata(
            sender_id="supervisor",
            recipient_id="energy"
        )

        payload = {
            "query": "What are the energy initiatives?",
            "context": [{"role": "user", "content": "Hello"}],
            "requires_response": True,
            "timeout": 60
        }

        request = DelegationRequest(
            metadata=metadata,
            payload=payload
        )

        assert request.type == MessageType.DELEGATION
        assert request.query == "What are the energy initiatives?"
        assert request.context == [{"role": "user", "content": "Hello"}]
        assert request.requires_response is True
        assert request.timeout == 60

    def test_delegation_request_missing_query(self):
        """Test that delegation without query raises error"""
        metadata = MessageMetadata(
            sender_id="supervisor",
            recipient_id="energy"
        )

        with pytest.raises(ValueError, match="must contain 'query' field"):
            DelegationRequest(
                metadata=metadata,
                payload={}
            )

    def test_create_delegation_helper(self):
        """Test create_delegation_request helper function"""
        request = create_delegation_request(
            sender_id="supervisor",
            recipient_id="energy",
            query="What are energy initiatives?",
            session_id="test-session",
            delegation_depth=1,
            timeout=45
        )

        assert request.metadata.sender_id == "supervisor"
        assert request.metadata.recipient_id == "energy"
        assert request.metadata.session_id == "test-session"
        assert request.metadata.delegation_depth == 1
        assert request.query == "What are energy initiatives?"
        assert request.timeout == 45


class TestAgentResponse:
    """Test AgentResponse message"""

    def test_create_agent_response(self):
        """Test creating agent response"""
        correlation_id = uuid4()

        metadata = MessageMetadata(
            sender_id="energy",
            recipient_id="supervisor",
            correlation_id=correlation_id
        )

        payload = {
            "response": "Here are the energy initiatives...",
            "confidence": 0.95,
            "processing_time": 2.5,
            "sources": ["doc1", "doc2"]
        }

        response = AgentResponse(
            metadata=metadata,
            payload=payload
        )

        assert response.type == MessageType.RESPONSE
        assert response.response == "Here are the energy initiatives..."
        assert response.confidence == 0.95
        assert response.processing_time == 2.5
        assert response.sources == ["doc1", "doc2"]

    def test_agent_response_missing_response(self):
        """Test that response without response field raises error"""
        metadata = MessageMetadata(
            sender_id="energy",
            recipient_id="supervisor"
        )

        with pytest.raises(ValueError, match="must contain 'response' field"):
            AgentResponse(
                metadata=metadata,
                payload={}
            )

    def test_create_agent_response_helper(self):
        """Test create_agent_response helper function"""
        correlation_id = uuid4()

        response = create_agent_response(
            sender_id="energy",
            recipient_id="supervisor",
            response="Energy initiatives include...",
            correlation_id=correlation_id,
            confidence=0.9,
            processing_time=1.5
        )

        assert response.metadata.sender_id == "energy"
        assert response.metadata.correlation_id == correlation_id
        assert response.response == "Energy initiatives include..."
        assert response.confidence == 0.9
        assert response.status == MessageStatus.COMPLETED


class TestAgentEvent:
    """Test AgentEvent message"""

    def test_create_agent_event(self):
        """Test creating agent event"""
        metadata = MessageMetadata(
            sender_id="energy",
            recipient_id="*"
        )

        payload = {
            "event_type": "agent_started",
            "data": {"agent_id": "energy", "timestamp": "2025-01-01T00:00:00"}
        }

        event = AgentEvent(
            metadata=metadata,
            payload=payload
        )

        assert event.type == MessageType.EVENT
        assert event.event_type == "agent_started"
        assert event.data == {"agent_id": "energy", "timestamp": "2025-01-01T00:00:00"}

    def test_agent_event_missing_event_type(self):
        """Test that event without event_type raises error"""
        metadata = MessageMetadata(
            sender_id="energy",
            recipient_id="*"
        )

        with pytest.raises(ValueError, match="must contain 'event_type' field"):
            AgentEvent(
                metadata=metadata,
                payload={}
            )

    def test_create_agent_event_helper(self):
        """Test create_agent_event helper function"""
        event = create_agent_event(
            sender_id="energy",
            event_type="task_completed",
            data={"task_id": "123", "result": "success"},
            priority=MessagePriority.HIGH
        )

        assert event.metadata.sender_id == "energy"
        assert event.metadata.recipient_id == "*"
        assert event.event_type == "task_completed"
        assert event.data == {"task_id": "123", "result": "success"}
        assert event.priority == MessagePriority.HIGH


class TestErrorMessage:
    """Test ErrorMessage"""

    def test_create_error_message(self):
        """Test creating error message"""
        metadata = MessageMetadata(
            sender_id="energy",
            recipient_id="supervisor"
        )

        payload = {
            "error_code": "TIMEOUT",
            "error_message": "Request timed out after 30 seconds",
            "stack_trace": "Traceback..."
        }

        error = ErrorMessage(
            metadata=metadata,
            payload=payload
        )

        assert error.type == MessageType.ERROR
        assert error.error_code == "TIMEOUT"
        assert error.error_message == "Request timed out after 30 seconds"
        assert error.stack_trace == "Traceback..."

    def test_error_message_missing_fields(self):
        """Test that error without required fields raises error"""
        metadata = MessageMetadata(
            sender_id="energy",
            recipient_id="supervisor"
        )

        with pytest.raises(ValueError, match="must contain 'error_code' and 'error_message'"):
            ErrorMessage(
                metadata=metadata,
                payload={}
            )

    def test_create_error_message_helper(self):
        """Test create_error_message helper function"""
        correlation_id = uuid4()

        error = create_error_message(
            sender_id="energy",
            recipient_id="supervisor",
            error_code="CONN_ERROR",
            error_message="Connection failed",
            correlation_id=correlation_id,
            stack_trace="Stack trace here"
        )

        assert error.metadata.sender_id == "energy"
        assert error.metadata.correlation_id == correlation_id
        assert error.error_code == "CONN_ERROR"
        assert error.error_message == "Connection failed"
        assert error.status == MessageStatus.FAILED


class TestMessageSerialization:
    """Test JSON serialization/deserialization"""

    def test_full_serialization_cycle(self):
        """Test that message can be serialized and deserialized"""
        original = create_delegation_request(
            sender_id="supervisor",
            recipient_id="energy",
            query="Test query",
            session_id="test-session"
        )

        # Serialize to dict
        message_dict = original.to_dict()

        # Serialize to JSON string
        json_str = json.dumps(message_dict)

        # Deserialize from JSON
        restored_dict = json.loads(json_str)

        # Restore message
        restored = DelegationRequest.from_dict(restored_dict)

        assert restored.metadata.sender_id == original.metadata.sender_id
        assert restored.metadata.recipient_id == original.metadata.recipient_id
        assert restored.query == original.query
        assert str(restored.metadata.message_id) == str(original.metadata.message_id)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
