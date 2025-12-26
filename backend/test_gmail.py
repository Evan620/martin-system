"""
Quick Gmail Tools Test Script

This script tests the Gmail integration and helps complete the OAuth flow.
Run this first to authorize the app and generate gmail_token.json.
"""

import asyncio
import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.tools.email_tools import (
    send_email,
    search_emails,
    list_recent_emails,
    EMAIL_TOOLS
)


async def test_oauth_connection():
    """Test OAuth connection by listing recent emails"""
    print("=" * 60)
    print("Gmail Tools - OAuth Connection Test")
    print("=" * 60)
    print("\nThis will open a browser window for OAuth authorization.")
    print("Please log in with your Gmail account and grant permissions.")
    print("\nTesting connection by listing recent emails...")
    print("-" * 60)

    try:
        # Try to list recent emails (this will trigger OAuth flow if needed)
        result = await list_recent_emails(
            max_results=5,
            filter="inbox",
            include_body=False
        )

        if result.get('status') == 'success':
            print("\n✅ SUCCESS! Gmail connection established.")
            print(f"\nFound {result.get('count', 0)} recent emails in inbox:")

            for i, email in enumerate(result.get('emails', []), 1):
                print(f"\n  {i}. {email['subject']}")
                print(f"     From: {email['from']}")
                print(f"     Date: {email['date']}")
                print(f"     Snippet: {email['snippet'][:80]}...")

            print("\n" + "=" * 60)
            print("OAuth token saved to: credentials/gmail_token.json")
            print("You can now use all Gmail tools!")
            print("=" * 60)
            return True

        else:
            print("\n❌ ERROR: Failed to connect to Gmail")
            print(f"Error: {result.get('error')}")
            return False

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        print("\nTroubleshooting:")
        print("1. Check that gmail_credentials.json exists in credentials/")
        print("2. Verify your Google Cloud OAuth app is configured correctly")
        print("3. Make sure Gmail API is enabled in Google Cloud Console")
        print("4. Check that redirect URI includes http://localhost")
        return False


async def test_search():
    """Test email search functionality"""
    print("\n" + "=" * 60)
    print("Testing Search Functionality")
    print("=" * 60)

    try:
        result = await search_emails(
            query="is:unread",
            max_results=5,
            include_body=False
        )

        if result.get('status') == 'success':
            print(f"\n✅ Found {result.get('count', 0)} unread emails")

            for i, email in enumerate(result.get('emails', [])[:3], 1):
                print(f"\n  {i}. {email['subject']}")
                print(f"     From: {email['from']}")

            return True
        else:
            print(f"\n❌ Search failed: {result.get('error')}")
            return False

    except Exception as e:
        print(f"\n❌ Search error: {e}")
        return False


async def test_send_email_to_self():
    """Test sending email (sends to yourself as a test)"""
    print("\n" + "=" * 60)
    print("Testing Send Email Functionality")
    print("=" * 60)

    # Get user's email from recent emails
    try:
        print("\nRetrieving your email address...")
        list_result = await list_recent_emails(max_results=1, filter="inbox")

        if list_result.get('status') != 'success' or not list_result.get('emails'):
            print("❌ Could not determine your email address")
            return False

        # Extract 'To' field from a recent email (which is likely your address)
        user_email = list_result['emails'][0].get('to', '').split('<')[-1].strip('>')

        if not user_email or '@' not in user_email:
            print("❌ Could not determine valid email address")
            user_email = input("\nPlease enter your email address to send a test email: ")

        print(f"\nSending test email to: {user_email}")
        print("This will send an email to yourself as a test.")

        confirm = input("Continue? (y/n): ").lower()
        if confirm != 'y':
            print("Test skipped.")
            return False

        result = await send_email(
            to=user_email,
            subject="Gmail Tools Test - Success!",
            message="This is a test email from your Gmail Tools integration.",
            html_body="""
            <h2>Gmail Tools Test Email</h2>
            <p>Congratulations! Your Gmail integration is working correctly.</p>
            <ul>
                <li>✅ OAuth authentication successful</li>
                <li>✅ Email sending functional</li>
                <li>✅ HTML formatting working</li>
            </ul>
            <p>You can now use all Gmail tools in your AI Agent System!</p>
            <hr>
            <p style="color: #666; font-size: 12px;">
                This is an automated test email from the Gmail Tools integration.
            </p>
            """
        )

        if result.get('status') == 'success':
            print("\n✅ Email sent successfully!")
            print(f"   Message ID: {result.get('message_id')}")
            print("\nCheck your inbox for the test email.")
            return True
        else:
            print(f"\n❌ Failed to send email: {result.get('error')}")
            return False

    except Exception as e:
        print(f"\n❌ Send test error: {e}")
        return False


async def show_available_tools():
    """Display all available email tools"""
    print("\n" + "=" * 60)
    print("Available Gmail Tools")
    print("=" * 60)

    for i, tool in enumerate(EMAIL_TOOLS, 1):
        print(f"\n{i}. {tool['name']}")
        print(f"   {tool['description']}")
        print(f"   Parameters: {', '.join(tool['parameters'].keys())}")


async def main():
    """Run all tests"""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 15 + "GMAIL TOOLS TEST SUITE" + " " * 21 + "║")
    print("╚" + "=" * 58 + "╝")

    # Test 1: OAuth and connection
    oauth_success = await test_oauth_connection()

    if not oauth_success:
        print("\n⚠️  OAuth connection failed. Please fix the issue before continuing.")
        return

    # Test 2: Search
    await test_search()

    # Test 3: Show available tools
    await show_available_tools()

    # Test 4: Send email (optional)
    print("\n" + "=" * 60)
    send_test = input("\nWould you like to test sending an email? (y/n): ").lower()
    if send_test == 'y':
        await test_send_email_to_self()

    # Summary
    print("\n" + "=" * 60)
    print("Test Suite Complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Review the documentation in EMAIL_TOOLS_README.md")
    print("2. Check examples in examples/gmail_usage_examples.py")
    print("3. Integrate the tools with your AI agents")
    print("\nAll 7 Gmail tools are ready to use:")
    print("  • send_email")
    print("  • send_email_from_template")
    print("  • create_email_draft")
    print("  • search_emails")
    print("  • get_email")
    print("  • list_recent_emails")
    print("  • get_email_thread")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user.")
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
