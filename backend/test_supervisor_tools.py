"""
Test Supervisor with Email Tools

Quick test to verify the Supervisor can detect and execute email tool requests.
"""

import asyncio
from app.agents.supervisor_with_tools import create_supervisor_with_tools


async def test_email_detection():
    """Test email tool detection and execution"""
    print("=" * 70)
    print("Testing Supervisor with Email Tools")
    print("=" * 70)

    supervisor = create_supervisor_with_tools(auto_register=False)

    # Test 1: Check last emails
    print("\nTest 1: 'what are the last 4 emails in my gmail'")
    print("-" * 70)
    response = await supervisor.chat_with_tools("what are the last 4 emails in my gmail")
    print(f"Response: {response}\n")

    # Test 2: Search unread emails
    print("\nTest 2: 'show me unread emails'")
    print("-" * 70)
    response = await supervisor.chat_with_tools("show me unread emails")
    print(f"Response: {response}\n")

    # Test 3: Check email tools
    print("\nTest 3: 'what email tools do you have'")
    print("-" * 70)
    response = await supervisor.chat_with_tools("what email tools do you have")
    print(f"Response: {response}\n")

    # Test 4: Regular question (no email tools)
    print("\nTest 4: 'what is ECOWAS' (no email tool)")
    print("-" * 70)
    response = await supervisor.chat_with_tools("what is ECOWAS")
    print(f"Response: {response}\n")

    print("=" * 70)
    print("Tests Complete!")
    print("=" * 70)


if __name__ == "__main__":
    try:
        asyncio.run(test_email_detection())
    except KeyboardInterrupt:
        print("\n\nTest interrupted.")
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()
