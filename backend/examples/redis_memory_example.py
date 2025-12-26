"""
Redis Memory Service Example

Demonstrates how to use the Redis memory service for agent conversation persistence.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.app.services.redis_memory import get_redis_memory
from backend.app.agents.redis_agent import RedisAgent
from loguru import logger


def example_1_basic_memory_operations():
    """Example 1: Basic Redis memory operations"""
    print("\n" + "=" * 60)
    print("Example 1: Basic Redis Memory Operations")
    print("=" * 60)

    # Get Redis memory service
    redis_memory = get_redis_memory(
        host="redis.railway.internal",
        port=6379,
        password="irhqoDCLjWWHuMJSYyXCYMLRyjcKFCMO",
        db=0
    )

    # Check health
    if not redis_memory.health_check():
        print("❌ Redis connection failed!")
        return

    print("✅ Redis connection successful!")

    # Save conversation history
    agent_id = "energy"
    session_id = "user-123-session-1"

    history = [
        {"role": "user", "content": "What are the renewable energy targets?"},
        {"role": "assistant", "content": "ECOWAS aims for 35% renewable energy by 2030..."},
        {"role": "user", "content": "What about solar power?"},
        {"role": "assistant", "content": "Solar power is a key focus area..."}
    ]

    # Save history
    redis_memory.save_conversation_history(agent_id, session_id, history)
    print(f"✅ Saved {len(history)} messages for {agent_id}:{session_id}")

    # Retrieve history
    retrieved_history = redis_memory.get_conversation_history(agent_id, session_id)
    print(f"✅ Retrieved {len(retrieved_history)} messages")

    # Append new message
    new_message = {"role": "user", "content": "Tell me about wind energy"}
    redis_memory.append_to_history(agent_id, session_id, new_message, max_history=10)
    print(f"✅ Appended new message")

    # Get updated history
    updated_history = redis_memory.get_conversation_history(agent_id, session_id)
    print(f"✅ Updated history has {len(updated_history)} messages")

    # Get memory stats
    stats = redis_memory.get_memory_stats()
    print(f"\n📊 Redis Stats:")
    print(f"   - Used Memory: {stats.get('used_memory', 'N/A')}")
    print(f"   - Total Keys: {stats.get('total_keys', 'N/A')}")


def example_2_session_management():
    """Example 2: Session data management"""
    print("\n" + "=" * 60)
    print("Example 2: Session Data Management")
    print("=" * 60)

    redis_memory = get_redis_memory(
        host="redis.railway.internal",
        port=6379,
        password="irhqoDCLjWWHuMJSYyXCYMLRyjcKFCMO",
        db=0
    )

    session_id = "user-456-session-2"

    # Store session metadata
    session_data = {
        "user_id": "user-456",
        "twg": "agriculture",
        "started_at": "2025-12-25T10:00:00Z",
        "preferences": {
            "language": "en",
            "notifications": True
        }
    }

    redis_memory.set_session_data(session_id, "metadata", session_data)
    print(f"✅ Saved session metadata for {session_id}")

    # Retrieve session data
    retrieved_data = redis_memory.get_session_data(session_id, "metadata")
    print(f"✅ Retrieved session data:")
    print(f"   - User: {retrieved_data['user_id']}")
    print(f"   - TWG: {retrieved_data['twg']}")
    print(f"   - Language: {retrieved_data['preferences']['language']}")


def example_3_agent_state_persistence():
    """Example 3: Agent state persistence"""
    print("\n" + "=" * 60)
    print("Example 3: Agent State Persistence")
    print("=" * 60)

    redis_memory = get_redis_memory(
        host="redis.railway.internal",
        port=6379,
        password="irhqoDCLjWWHuMJSYyXCYMLRyjcKFCMO",
        db=0
    )

    agent_id = "supervisor"

    # Save agent state
    agent_state = {
        "active_agents": ["energy", "agriculture", "digital"],
        "pending_requests": 3,
        "last_activity": "2025-12-25T10:30:00Z",
        "delegation_count": {
            "energy": 5,
            "agriculture": 3,
            "digital": 2
        }
    }

    redis_memory.save_agent_state(agent_id, agent_state)
    print(f"✅ Saved state for {agent_id} agent")

    # Retrieve agent state
    retrieved_state = redis_memory.get_agent_state(agent_id)
    print(f"✅ Retrieved agent state:")
    print(f"   - Active Agents: {retrieved_state['active_agents']}")
    print(f"   - Pending Requests: {retrieved_state['pending_requests']}")
    print(f"   - Total Delegations: {sum(retrieved_state['delegation_count'].values())}")


def example_4_redis_agent_usage():
    """Example 4: Using RedisAgent for persistent conversations"""
    print("\n" + "=" * 60)
    print("Example 4: RedisAgent with Persistent Conversations")
    print("=" * 60)

    # Create a Redis-enabled agent
    session_id = "user-789-session-3"

    # First conversation
    print("\n🔹 Starting first conversation...")
    agent1 = RedisAgent(
        agent_id="energy",
        session_id=session_id,
        keep_history=True,
        max_history=10,
        use_redis=True
    )

    print(f"✅ Agent created: {agent1}")
    print(f"   - Session ID: {agent1.session_id}")
    print(f"   - History Length: {len(agent1.history)}")

    # Simulate some conversation (without actual LLM calls for this example)
    # In real usage, you would call: response = agent1.chat("Your question here")

    print("\n🔹 Simulating conversation history...")
    agent1.history = [
        {"role": "user", "content": "What are ECOWAS energy initiatives?"},
        {"role": "assistant", "content": "ECOWAS has several energy initiatives including WAPP..."}
    ]

    # Save to Redis
    agent1.redis_memory.save_conversation_history(
        agent1.agent_id,
        agent1.session_id,
        agent1.history
    )
    print(f"✅ Saved conversation to Redis")

    # Create a new agent instance with same session
    print("\n🔹 Creating new agent instance with same session...")
    agent2 = RedisAgent(
        agent_id="energy",
        session_id=session_id,
        keep_history=True,
        max_history=10,
        use_redis=True
    )

    print(f"✅ New agent created: {agent2}")
    print(f"   - History Length: {len(agent2.history)} (loaded from Redis)")
    print(f"   - Previous messages restored: {len(agent2.history) > 0}")

    # Get session info
    info = agent2.get_session_info()
    print(f"\n📋 Session Info:")
    for key, value in info.items():
        print(f"   - {key}: {value}")


def example_5_multi_agent_sessions():
    """Example 5: Managing multiple agent sessions"""
    print("\n" + "=" * 60)
    print("Example 5: Multi-Agent Session Management")
    print("=" * 60)

    redis_memory = get_redis_memory(
        host="redis.railway.internal",
        port=6379,
        password="irhqoDCLjWWHuMJSYyXCYMLRyjcKFCMO",
        db=0
    )

    # Create sessions for different agents
    sessions = [
        ("energy", "user-100-session-1"),
        ("energy", "user-100-session-2"),
        ("agriculture", "user-100-session-1"),
        ("digital", "user-200-session-1"),
    ]

    print("🔹 Creating multiple sessions...")
    for agent_id, session_id in sessions:
        history = [
            {"role": "user", "content": f"Question for {agent_id}"},
            {"role": "assistant", "content": f"Response from {agent_id}"}
        ]
        redis_memory.save_conversation_history(agent_id, session_id, history)
        print(f"   ✅ Created session: {agent_id}:{session_id}")

    # Get all sessions for energy agent
    print("\n🔹 Getting all sessions for 'energy' agent...")
    energy_sessions = redis_memory.get_all_sessions_for_agent("energy")
    print(f"   ✅ Found {len(energy_sessions)} sessions:")
    for session in energy_sessions:
        print(f"      - {session}")

    # Clear specific session
    print("\n🔹 Clearing a specific session...")
    redis_memory.clear_conversation_history("energy", "user-100-session-1")
    print(f"   ✅ Cleared session: energy:user-100-session-1")

    # Clear all data for an agent
    print("\n🔹 Clearing all data for 'digital' agent...")
    deleted = redis_memory.clear_all_agent_data("digital")
    print(f"   ✅ Deleted {deleted} keys")


def example_6_ttl_management():
    """Example 6: TTL (Time-To-Live) management"""
    print("\n" + "=" * 60)
    print("Example 6: TTL Management")
    print("=" * 60)

    redis_memory = get_redis_memory(
        host="redis.railway.internal",
        port=6379,
        password="irhqoDCLjWWHuMJSYyXCYMLRyjcKFCMO",
        db=0
    )

    agent_id = "protocol"
    session_id = "temp-session"

    # Save with custom TTL (1 hour = 3600 seconds)
    history = [
        {"role": "user", "content": "Schedule a meeting"},
        {"role": "assistant", "content": "Meeting scheduled for tomorrow"}
    ]

    redis_memory.save_conversation_history(
        agent_id,
        session_id,
        history,
        ttl=3600  # 1 hour
    )
    print(f"✅ Saved session with 1-hour TTL")

    # Extend TTL (e.g., user is still active)
    redis_memory.extend_ttl(agent_id, session_id, ttl=7200)  # 2 hours
    print(f"✅ Extended TTL to 2 hours")


def main():
    """Run all examples"""
    print("\n" + "=" * 60)
    print("Redis Memory Service Examples")
    print("ECOWAS Summit TWG Support System")
    print("=" * 60)

    try:
        # Run examples
        example_1_basic_memory_operations()
        example_2_session_management()
        example_3_agent_state_persistence()
        example_4_redis_agent_usage()
        example_5_multi_agent_sessions()
        example_6_ttl_management()

        print("\n" + "=" * 60)
        print("✅ All examples completed successfully!")
        print("=" * 60 + "\n")

    except Exception as e:
        logger.error(f"Example failed: {e}")
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
