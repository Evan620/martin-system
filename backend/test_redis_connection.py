#!/usr/bin/env python3
"""
Quick Redis Connection Test Script

Tests connection to Railway Redis using the credentials from .env.example
"""

import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from backend.app.services.redis_memory import RedisMemoryService
from loguru import logger


def test_redis_connection():
    """Test Redis connection with Railway credentials"""

    print("\n" + "=" * 70)
    print("ECOWAS Summit - Redis Connection Test")
    print("=" * 70)

    # Railway Redis credentials
    config = {
        "host": "redis.railway.internal",
        "port": 6379,
        "password": "irhqoDCLjWWHuMJSYyXCYMLRyjcKFCMO",
        "db": 0
    }

    print("\n📋 Configuration:")
    print(f"   Host: {config['host']}")
    print(f"   Port: {config['port']}")
    print(f"   Database: {config['db']}")
    print(f"   Password: {'*' * len(config['password'])}")

    try:
        print("\n🔄 Connecting to Redis...")

        # Create Redis memory service
        redis_memory = RedisMemoryService(
            host=config["host"],
            port=config["port"],
            password=config["password"],
            db=config["db"]
        )

        print("✅ Connection established!")

        # Test 1: Health check
        print("\n🔍 Test 1: Health Check")
        is_healthy = redis_memory.health_check()
        if is_healthy:
            print("   ✅ Health check passed")
        else:
            print("   ❌ Health check failed")
            return False

        # Test 2: Basic read/write
        print("\n🔍 Test 2: Basic Read/Write Operations")
        test_data = {
            "system": "ECOWAS Summit TWG Support",
            "version": "0.1.0",
            "timestamp": "2025-12-25T10:00:00Z"
        }

        redis_memory.set_session_data("test-session", "test-data", test_data, ttl=300)
        print("   ✅ Write successful")

        retrieved = redis_memory.get_session_data("test-session", "test-data")
        if retrieved == test_data:
            print("   ✅ Read successful - data matches")
        else:
            print("   ❌ Read failed - data mismatch")
            return False

        # Test 3: Conversation history
        print("\n🔍 Test 3: Conversation History Management")
        history = [
            {"role": "user", "content": "What are the ECOWAS energy initiatives?"},
            {"role": "assistant", "content": "ECOWAS has several energy initiatives..."},
            {"role": "user", "content": "Tell me about renewable energy targets"},
            {"role": "assistant", "content": "The region targets 35% renewable energy by 2030..."}
        ]

        redis_memory.save_conversation_history("energy", "test-user-123", history)
        print("   ✅ Conversation history saved")

        retrieved_history = redis_memory.get_conversation_history("energy", "test-user-123")
        if len(retrieved_history) == len(history):
            print(f"   ✅ History retrieved - {len(retrieved_history)} messages")
        else:
            print("   ❌ History retrieval failed")
            return False

        # Test 4: Agent state persistence
        print("\n🔍 Test 4: Agent State Persistence")
        agent_state = {
            "active_agents": ["energy", "agriculture", "digital"],
            "pending_requests": 5,
            "last_delegation": "energy"
        }

        redis_memory.save_agent_state("supervisor", agent_state)
        print("   ✅ Agent state saved")

        retrieved_state = redis_memory.get_agent_state("supervisor")
        if retrieved_state == agent_state:
            print("   ✅ Agent state retrieved successfully")
        else:
            print("   ❌ Agent state retrieval failed")
            return False

        # Test 5: Memory statistics
        print("\n🔍 Test 5: Memory Statistics")
        stats = redis_memory.get_memory_stats()
        print(f"   📊 Used Memory: {stats.get('used_memory', 'N/A')}")
        print(f"   📊 Peak Memory: {stats.get('used_memory_peak', 'N/A')}")
        print(f"   📊 Total Keys: {stats.get('total_keys', 'N/A')}")
        print(f"   ✅ Statistics retrieved successfully")

        # Test 6: Cleanup
        print("\n🔍 Test 6: Data Cleanup")
        redis_memory.clear_conversation_history("energy", "test-user-123")
        redis_memory.clear_all_agent_data("supervisor")
        print("   ✅ Test data cleaned up")

        # Success summary
        print("\n" + "=" * 70)
        print("✅ All tests passed successfully!")
        print("=" * 70)
        print("\n💡 Redis memory service is ready for use with the following features:")
        print("   • Persistent conversation history")
        print("   • Agent state management")
        print("   • Session data storage")
        print("   • Automatic TTL management")
        print("   • Multi-agent support")
        print("\n" + "=" * 70 + "\n")

        return True

    except Exception as e:
        print(f"\n❌ Connection test failed!")
        print(f"   Error: {str(e)}")
        print("\n💡 Troubleshooting tips:")
        print("   1. Ensure Redis server is running on Railway")
        print("   2. Check network connectivity to redis.railway.internal")
        print("   3. Verify credentials in .env file")
        print("   4. Check firewall settings")
        print("\n" + "=" * 70 + "\n")
        return False


if __name__ == "__main__":
    success = test_redis_connection()
    sys.exit(0 if success else 1)
