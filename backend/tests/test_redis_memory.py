"""
Tests for Redis Memory Service

Unit tests for Redis-based conversation memory and state management.
"""

import pytest
from app.services.redis_memory import RedisMemoryService


@pytest.fixture
def redis_memory():
    """Create a Redis memory service instance for testing"""
    # Use test database (db=15) to avoid conflicts
    service = RedisMemoryService(
        host="redis.railway.internal",
        port=6379,
        db=15,  # Test database
        password="irhqoDCLjWWHuMJSYyXCYMLRyjcKFCMO"
    )
    yield service

    # Cleanup: Clear all test data after tests
    # Note: In production, you'd want to be more selective
    service.close()


def test_redis_connection(redis_memory):
    """Test Redis connection health check"""
    assert redis_memory.health_check() is True


def test_save_and_get_conversation_history(redis_memory):
    """Test saving and retrieving conversation history"""
    agent_id = "test-agent"
    session_id = "test-session-1"

    history = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"},
        {"role": "user", "content": "How are you?"},
        {"role": "assistant", "content": "I'm doing well, thanks!"}
    ]

    # Save history
    result = redis_memory.save_conversation_history(agent_id, session_id, history)
    assert result is True

    # Retrieve history
    retrieved = redis_memory.get_conversation_history(agent_id, session_id)
    assert len(retrieved) == 4
    assert retrieved == history


def test_append_to_history(redis_memory):
    """Test appending messages to conversation history"""
    agent_id = "test-agent"
    session_id = "test-session-2"

    # Start with initial history
    initial_history = [
        {"role": "user", "content": "Message 1"},
        {"role": "assistant", "content": "Response 1"}
    ]
    redis_memory.save_conversation_history(agent_id, session_id, initial_history)

    # Append new message
    new_message = {"role": "user", "content": "Message 2"}
    redis_memory.append_to_history(agent_id, session_id, new_message)

    # Verify
    history = redis_memory.get_conversation_history(agent_id, session_id)
    assert len(history) == 3
    assert history[-1] == new_message


def test_append_with_max_history(redis_memory):
    """Test that history is trimmed when max_history is exceeded"""
    agent_id = "test-agent"
    session_id = "test-session-3"

    # Create history with 10 messages
    history = [
        {"role": "user" if i % 2 == 0 else "assistant", "content": f"Message {i}"}
        for i in range(10)
    ]
    redis_memory.save_conversation_history(agent_id, session_id, history)

    # Append with max_history=5
    new_message = {"role": "user", "content": "New message"}
    redis_memory.append_to_history(agent_id, session_id, new_message, max_history=5)

    # Should only keep last 5 messages
    retrieved = redis_memory.get_conversation_history(agent_id, session_id)
    assert len(retrieved) == 5
    assert retrieved[-1] == new_message


def test_clear_conversation_history(redis_memory):
    """Test clearing conversation history"""
    agent_id = "test-agent"
    session_id = "test-session-4"

    # Save history
    history = [{"role": "user", "content": "Test"}]
    redis_memory.save_conversation_history(agent_id, session_id, history)

    # Clear history
    result = redis_memory.clear_conversation_history(agent_id, session_id)
    assert result is True

    # Verify it's cleared
    retrieved = redis_memory.get_conversation_history(agent_id, session_id)
    assert len(retrieved) == 0


def test_save_and_get_agent_state(redis_memory):
    """Test saving and retrieving agent state"""
    agent_id = "test-agent"

    state = {
        "active": True,
        "pending_tasks": 5,
        "last_update": "2025-12-25T10:00:00Z",
        "metadata": {
            "version": "1.0",
            "config": {"timeout": 30}
        }
    }

    # Save state
    result = redis_memory.save_agent_state(agent_id, state)
    assert result is True

    # Retrieve state
    retrieved = redis_memory.get_agent_state(agent_id)
    assert retrieved == state


def test_session_data(redis_memory):
    """Test session data storage and retrieval"""
    session_id = "test-session-5"
    key = "user-preferences"

    data = {
        "language": "en",
        "theme": "dark",
        "notifications": True
    }

    # Save session data
    result = redis_memory.set_session_data(session_id, key, data)
    assert result is True

    # Retrieve session data
    retrieved = redis_memory.get_session_data(session_id, key)
    assert retrieved == data


def test_get_all_sessions_for_agent(redis_memory):
    """Test getting all sessions for an agent"""
    agent_id = "test-agent"

    # Create multiple sessions
    sessions = ["session-1", "session-2", "session-3"]
    for session_id in sessions:
        history = [{"role": "user", "content": f"Message in {session_id}"}]
        redis_memory.save_conversation_history(agent_id, session_id, history)

    # Get all sessions
    retrieved_sessions = redis_memory.get_all_sessions_for_agent(agent_id)

    # Verify all sessions are present
    assert len(retrieved_sessions) >= 3
    for session_id in sessions:
        assert session_id in retrieved_sessions


def test_extend_ttl(redis_memory):
    """Test extending TTL for a session"""
    agent_id = "test-agent"
    session_id = "test-session-6"

    # Save with initial TTL
    history = [{"role": "user", "content": "Test"}]
    redis_memory.save_conversation_history(agent_id, session_id, history, ttl=60)

    # Extend TTL
    result = redis_memory.extend_ttl(agent_id, session_id, ttl=120)
    assert result is True


def test_memory_stats(redis_memory):
    """Test getting memory statistics"""
    stats = redis_memory.get_memory_stats()

    assert "connected" in stats
    assert stats["connected"] is True
    assert "total_keys" in stats
    assert isinstance(stats["total_keys"], int)


def test_clear_all_agent_data(redis_memory):
    """Test clearing all data for an agent"""
    agent_id = "test-agent-cleanup"

    # Create multiple sessions and state
    redis_memory.save_conversation_history(agent_id, "session-1", [{"role": "user", "content": "Test"}])
    redis_memory.save_conversation_history(agent_id, "session-2", [{"role": "user", "content": "Test"}])
    redis_memory.save_agent_state(agent_id, {"test": "state"})

    # Clear all agent data
    deleted = redis_memory.clear_all_agent_data(agent_id)
    assert deleted >= 3  # At least 2 history keys + 1 state key


def test_nonexistent_session(redis_memory):
    """Test retrieving non-existent session"""
    history = redis_memory.get_conversation_history("nonexistent-agent", "nonexistent-session")
    assert history == []

    state = redis_memory.get_agent_state("nonexistent-agent")
    assert state is None

    data = redis_memory.get_session_data("nonexistent-session", "nonexistent-key")
    assert data is None


def test_complex_data_structures(redis_memory):
    """Test storing complex nested data structures"""
    session_id = "test-session-7"
    key = "complex-data"

    complex_data = {
        "users": [
            {"id": 1, "name": "Alice", "roles": ["admin", "user"]},
            {"id": 2, "name": "Bob", "roles": ["user"]}
        ],
        "settings": {
            "theme": {
                "primary": "#007bff",
                "secondary": "#6c757d"
            },
            "features": ["chat", "calendar", "documents"]
        },
        "metrics": {
            "sessions": 150,
            "messages": 1500,
            "avg_response_time": 1.5
        }
    }

    # Save and retrieve
    redis_memory.set_session_data(session_id, key, complex_data)
    retrieved = redis_memory.get_session_data(session_id, key)

    assert retrieved == complex_data
    assert retrieved["users"][0]["name"] == "Alice"
    assert retrieved["settings"]["features"] == ["chat", "calendar", "documents"]
    assert retrieved["metrics"]["avg_response_time"] == 1.5
