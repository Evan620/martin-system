#!/usr/bin/env python3
"""
Test Email Sending Pattern Detection

Tests that the supervisor can detect and parse email sending requests.
"""

import asyncio
from app.agents.supervisor_with_tools import create_supervisor_with_tools


async def test_email_sending_detection():
    """Test email sending pattern detection."""
    print("=" * 70)
    print("Testing Email Sending Pattern Detection")
    print("=" * 70)
    print()

    supervisor = create_supervisor_with_tools(auto_register=False)

    # Test queries
    test_queries = [
        "send a demo report to fredrickodondi9@gmail.com",
        "send a meeting summary to john@example.com",
        "send a notification to team@company.com",
        "send email to alice@example.com",
    ]

    for query in test_queries:
        print(f"Query: '{query}'")
        print("-" * 70)

        # Test pattern detection only (don't actually send)
        detected = supervisor._detect_email_request(query)

        if detected:
            print(f"✓ Detected: {detected['tool']}")
            print(f"  Recipient: {detected['args'].get('to')}")
            print(f"  Subject: {detected['args'].get('subject', 'N/A')}")
            print()
        else:
            print("✗ No email pattern detected")
            print()

    print("=" * 70)
    print("Pattern detection test complete!")
    print()
    print("To test actual email sending (requires OAuth):")
    print("  python scripts/chat_agent.py --agent supervisor")
    print("  Then: send a demo report to fredrickodondi9@gmail.com")
    print("=" * 70)


if __name__ == "__main__":
    try:
        asyncio.run(test_email_sending_detection())
    except KeyboardInterrupt:
        print("\n\nTest interrupted.")
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()
