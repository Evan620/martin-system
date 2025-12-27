#!/usr/bin/env python3
"""
Supervisor Agent with Redis Memory Example

Demonstrates how to use the Supervisor agent with persistent Redis memory.
"""

import sys
from pathlib import Path
import uuid

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.agents.supervisor import create_supervisor
from loguru import logger


def main():
    """Demonstrate Redis-enabled Supervisor agent"""

    print("\n" + "=" * 70)
    print("Supervisor Agent with Redis Memory - Demo")
    print("=" * 70)

    # Generate a unique session ID
    session_id = f"demo-session-{uuid.uuid4().hex[:8]}"

    print(f"\n📋 Session ID: {session_id}")
    print("=" * 70)

    # Create supervisor with Redis memory enabled
    print("\n🔹 Creating supervisor agent with Redis memory...")
    supervisor = create_supervisor(
        keep_history=True,
        auto_register=True,
        session_id=session_id,
        use_redis=True,
        memory_ttl=3600  # 1 hour
    )

    print(f"✅ Supervisor created:")
    print(f"   - Agent ID: {supervisor.agent_id}")
    print(f"   - Session ID: {supervisor.session_id}")
    print(f"   - Redis Enabled: {supervisor.use_redis}")
    print(f"   - History Enabled: {supervisor.keep_history}")

    # Get supervisor status
    status = supervisor.get_supervisor_status()
    print(f"\n📊 Supervisor Status:")
    print(f"   - Registered Agents: {status['registered_agents']}")
    print(f"   - Agent Count: {status['agent_count']}")
    print(f"   - History Length: {status['history_length']}")

    # Simulate a conversation (without actual LLM calls for this demo)
    print("\n🔹 Simulating conversation...")

    # Add some fake history for demonstration
    supervisor.history = [
        {"role": "user", "content": "What are the ECOWAS energy initiatives?"},
        {"role": "assistant", "content": "ECOWAS has several energy initiatives including..."},
        {"role": "user", "content": "Tell me about renewable energy targets"},
        {"role": "assistant", "content": "The region targets 35% renewable energy by 2030..."}
    ]

    # Save to Redis
    if supervisor.use_redis and supervisor.redis_memory:
        supervisor.redis_memory.save_conversation_history(
            supervisor.agent_id,
            supervisor.session_id,
            supervisor.history
        )
        print(f"✅ Saved {len(supervisor.history)} messages to Redis")

    # Simulate loading conversation in a new session
    print("\n🔹 Creating new supervisor instance with same session...")
    supervisor2 = create_supervisor(
        keep_history=True,
        auto_register=False,
        session_id=session_id,
        use_redis=True
    )

    print(f"✅ New supervisor created:")
    print(f"   - Session ID: {supervisor2.session_id}")
    print(f"   - Loaded History: {len(supervisor2.history)} messages")

    if supervisor2.history:
        print(f"\n💬 Restored conversation:")
        for i, msg in enumerate(supervisor2.history, 1):
            role = msg['role'].upper()
            content = msg['content'][:60] + "..." if len(msg['content']) > 60 else msg['content']
            print(f"   {i}. [{role}] {content}")

    # Clean up
    print("\n🔹 Cleaning up test data...")
    supervisor.reset_history()
    print(f"✅ History cleared from Redis")

    print("\n" + "=" * 70)
    print("✅ Demo completed successfully!")
    print("=" * 70)

    print("\n💡 Key Features Demonstrated:")
    print("   • Redis-backed persistent memory")
    print("   • Session-based conversation tracking")
    print("   • Automatic history save/load")
    print("   • Cross-instance memory sharing")
    print("   • TTL management for cleanup")

    print("\n📚 To use in your application:")
    print("""
    from app.agents.supervisor import create_supervisor

    # Create with Redis memory
    supervisor = create_supervisor(
        keep_history=True,
        session_id=f"user-{user_id}",
        use_redis=True,
        memory_ttl=86400  # 24 hours
    )

    # Use supervisor normally
    response = supervisor.smart_chat("Your question here")

    # History is automatically saved to Redis!
    """)

    print("\n" + "=" * 70 + "\n")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
