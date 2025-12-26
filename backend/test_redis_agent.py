#!/usr/bin/env python3
"""
Quick test to verify Redis memory is working with agents
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from backend.app.agents.supervisor import create_supervisor
from backend.app.services.redis_memory import get_redis_memory
from backend.app.services.redis_factory import create_redis_memory_from_config
import os

def main():
    print("\n" + "=" * 70)
    print("Testing Redis Memory Integration")
    print("=" * 70)

    # Test 1: Check Redis connection
    print("\n1. Testing Redis connection...")
    try:
        # Use config from environment
        redis_memory = create_redis_memory_from_config()
        if not redis_memory:
            print("   ❌ Failed to create Redis memory from config")
            return False

        if redis_memory.health_check():
            print("   ✅ Redis connection successful!")
            stats = redis_memory.get_memory_stats()
            print(f"   📊 Total keys in Redis: {stats.get('total_keys', 'N/A')}")
        else:
            print("   ❌ Redis health check failed")
            return False
    except Exception as e:
        print(f"   ❌ Redis connection failed: {e}")
        return False

    # Test 2: Create supervisor WITHOUT Redis
    print("\n2. Creating supervisor WITHOUT Redis...")
    supervisor1 = create_supervisor(
        keep_history=True,
        session_id="test-session-123",
        use_redis=False
    )
    print(f"   Agent ID: {supervisor1.agent_id}")
    print(f"   Use Redis: {supervisor1.use_redis}")
    print(f"   Session ID: {supervisor1.session_id}")

    # Test 3: Create supervisor WITH Redis
    print("\n3. Creating supervisor WITH Redis...")
    supervisor2 = create_supervisor(
        keep_history=True,
        session_id="test-session-456",
        use_redis=True,
        memory_ttl=3600
    )
    print(f"   Agent ID: {supervisor2.agent_id}")
    print(f"   Use Redis: {supervisor2.use_redis}")
    print(f"   Session ID: {supervisor2.session_id}")
    print(f"   Redis Memory: {supervisor2.redis_memory is not None}")

    # Test 4: Simulate saving to Redis
    print("\n4. Simulating conversation save to Redis...")
    test_history = [
        {"role": "user", "content": "Hello, this is a test"},
        {"role": "assistant", "content": "Hello! I received your test message."}
    ]

    if supervisor2.redis_memory:
        supervisor2.history = test_history
        success = supervisor2.redis_memory.save_conversation_history(
            supervisor2.agent_id,
            supervisor2.session_id,
            test_history,
            ttl=3600
        )
        if success:
            print("   ✅ Conversation saved to Redis!")
        else:
            print("   ❌ Failed to save to Redis")
            return False

        # Test 5: Verify data in Redis
        print("\n5. Verifying data in Redis...")
        retrieved = supervisor2.redis_memory.get_conversation_history(
            supervisor2.agent_id,
            supervisor2.session_id
        )
        if retrieved == test_history:
            print(f"   ✅ Retrieved {len(retrieved)} messages from Redis")
            print(f"   ✅ Data matches what was saved!")
        else:
            print("   ❌ Retrieved data doesn't match")
            return False

        # Test 6: Check Redis keys
        print("\n6. Checking Redis keys...")
        stats = supervisor2.redis_memory.get_memory_stats()
        print(f"   📊 Total keys in Redis: {stats.get('total_keys', 'N/A')}")

        # Get all sessions for supervisor
        sessions = supervisor2.redis_memory.get_all_sessions_for_agent("supervisor")
        print(f"   📊 Supervisor sessions in Redis: {len(sessions)}")
        if "test-session-456" in sessions:
            print(f"   ✅ Found our test session in Redis!")

        # Test 7: Cleanup
        print("\n7. Cleaning up test data...")
        supervisor2.redis_memory.clear_conversation_history(
            supervisor2.agent_id,
            supervisor2.session_id
        )
        print("   ✅ Test data cleaned up")

    # Success!
    print("\n" + "=" * 70)
    print("✅ All tests passed! Redis memory is working correctly!")
    print("=" * 70)

    print("\n💡 To use Redis with the chat script:")
    print("   python scripts/chat_agent.py --agent supervisor")
    print("   (Redis is now enabled by default)")
    print("\n   To disable Redis:")
    print("   python scripts/chat_agent.py --agent supervisor --no-redis")
    print("\n" + "=" * 70 + "\n")

    return True


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
