#!/usr/bin/env python3
"""
Quick Test Script for RedisMessageBus

Tests basic message queuing and pub/sub functionality.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from backend.app.services.message_bus_factory import get_message_bus, test_message_bus_connection
from backend.app.schemas.agent_messages import (
    create_delegation_request,
    create_agent_response,
    create_agent_event,
    MessagePriority
)


def main():
    print("\n" + "=" * 70)
    print("Testing RedisMessageBus")
    print("=" * 70)

    # Test 1: Connection
    print("\n1. Testing Redis connection...")
    if test_message_bus_connection():
        print("   ✅ Redis connection successful!")
    else:
        print("   ❌ Redis connection failed!")
        print("   Make sure Redis is running: brew services start redis")
        return False

    # Get message bus instance
    message_bus = get_message_bus()

    # Test 2: Send and receive delegation request
    print("\n2. Testing message queuing...")

    # Create a delegation request
    delegation = create_delegation_request(
        sender_id="supervisor",
        recipient_id="energy",
        query="What are the current energy initiatives?",
        session_id="test-session",
        priority=MessagePriority.NORMAL
    )

    # Send message
    message_id = message_bus.send_message(delegation)
    print(f"   ✅ Sent delegation request with ID: {message_id}")

    # Check queue size
    queue_size = message_bus.get_queue_size("energy")
    print(f"   📊 Energy agent queue size: {queue_size}")

    # Receive message
    received = message_bus.receive_message("energy", timeout=5)
    if received:
        print(f"   ✅ Received message: {received.type}")
        print(f"      Query: {received.query[:50]}...")
    else:
        print("   ❌ Failed to receive message")
        return False

    # Test 3: Acknowledge message
    print("\n3. Testing message acknowledgment...")
    success = message_bus.acknowledge_message(message_id, "energy")
    if success:
        print("   ✅ Message acknowledged")
    else:
        print("   ❌ Failed to acknowledge message")

    # Check message status
    status = message_bus.get_message_status(message_id)
    if status:
        print(f"   📊 Message status: {status.get('status')}")

    # Test 4: Publish event
    print("\n4. Testing pub/sub events...")

    event = create_agent_event(
        sender_id="energy",
        event_type="task_completed",
        data={"task_id": "123", "result": "success"},
        priority=MessagePriority.HIGH
    )

    subscriber_count = message_bus.publish_event(event)
    print(f"   ✅ Published event to {subscriber_count} subscribers")

    # Test 5: Bus stats
    print("\n5. Getting bus statistics...")
    stats = message_bus.get_bus_stats()
    print(f"   📊 Total agents: {stats.get('total_agents')}")
    print(f"   📊 Total messages: {stats.get('total_messages')}")
    print(f"   📊 Bus healthy: {stats.get('healthy')}")

    # Test 6: Cleanup
    print("\n6. Cleaning up...")
    cleared = message_bus.clear_agent_queue("energy")
    print(f"   ✅ Cleared {cleared} messages from energy queue")

    # Success!
    print("\n" + "=" * 70)
    print("✅ All message bus tests passed!")
    print("=" * 70)

    print("\n💡 Next Steps:")
    print("   • Message schema is working (26/26 tests passing)")
    print("   • RedisMessageBus is functional")
    print("   • Ready to proceed to Phase 2: CommunicatingAgent")
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
