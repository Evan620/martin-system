"""
Gmail Tools Usage Examples

This file demonstrates how to use the Gmail tools in various scenarios.
"""

import asyncio
from app.tools.email_tools import (
    send_email,
    send_email_from_template,
    create_email_draft,
    search_emails,
    get_email,
    list_recent_emails,
    get_email_thread
)


async def example_1_send_simple_email():
    """Example 1: Send a simple plain text email"""
    print("\n=== Example 1: Send Simple Email ===")

    result = await send_email(
        to="recipient@example.com",
        subject="Simple Test Email",
        message="This is a plain text email sent via Gmail API."
    )

    print(f"Result: {result}")


async def example_2_send_html_email_with_attachments():
    """Example 2: Send HTML email with attachments and CC/BCC"""
    print("\n=== Example 2: Send HTML Email with Attachments ===")

    result = await send_email(
        to=["recipient1@example.com", "recipient2@example.com"],
        subject="Q4 Report",
        message="Please find the Q4 report attached.",
        html_body="""
        <h1>Q4 Report</h1>
        <p>Dear Team,</p>
        <p>Please find the <strong>Q4 report</strong> attached for your review.</p>
        <ul>
            <li>Revenue increased 15%</li>
            <li>Customer satisfaction up 8%</li>
            <li>New product launch successful</li>
        </ul>
        <p>Best regards,<br>The Team</p>
        """,
        cc=["manager@example.com"],
        bcc=["archive@example.com"],
        attachments=["/path/to/q4_report.pdf"]  # Replace with actual path
    )

    print(f"Result: {result}")


async def example_3_send_from_notification_template():
    """Example 3: Send email using notification template"""
    print("\n=== Example 3: Send from Notification Template ===")

    result = await send_email_from_template(
        template_name="notification",
        to="user@example.com",
        subject="New Task Assigned",
        variables={
            "title": "Task Assignment",
            "heading": "New Task Assigned to You",
            "message": "You have been assigned a new task: Review Q4 Budget Proposal",
            "details": "Due date: January 15, 2025\nPriority: High\nEstimated time: 2 hours",
            "action_url": "https://tasks.example.com/task/12345",
            "action_text": "View Task",
            "additional_info": "Please complete this task by the due date."
        }
    )

    print(f"Result: {result}")


async def example_4_send_meeting_summary():
    """Example 4: Send meeting summary using template"""
    print("\n=== Example 4: Send Meeting Summary ===")

    result = await send_email_from_template(
        template_name="meeting_summary",
        to=["team@company.com"],
        subject="Weekly Team Meeting Summary - Dec 26, 2025",
        variables={
            "meeting_date": "December 26, 2025",
            "meeting_time": "10:00 AM - 11:00 AM EST",
            "duration": "1 hour",
            "location": "Conference Room A / Zoom",
            "participants": [
                "Alice Johnson (Project Manager)",
                "Bob Smith (Lead Developer)",
                "Carol White (Designer)",
                "David Brown (QA Engineer)"
            ],
            "agenda": [
                "Review last week's progress",
                "Discuss Q1 roadmap",
                "Plan sprint activities",
                "Address blockers"
            ],
            "discussion_points": [
                {
                    "topic": "Q4 Performance",
                    "summary": "Exceeded targets by 15%. Customer retention improved significantly."
                },
                {
                    "topic": "Q1 Roadmap",
                    "summary": "Prioritized mobile app redesign and API v2 implementation."
                }
            ],
            "action_items": [
                {
                    "description": "Finalize Q1 budget proposal",
                    "owner": "Alice Johnson",
                    "due_date": "Jan 5, 2025"
                },
                {
                    "description": "Update technical documentation",
                    "owner": "Bob Smith",
                    "due_date": "Jan 3, 2025"
                },
                {
                    "description": "Create mockups for mobile redesign",
                    "owner": "Carol White",
                    "due_date": "Jan 8, 2025"
                }
            ],
            "decisions": [
                "Approved Q1 roadmap with mobile app as priority",
                "Allocated additional budget for cloud infrastructure",
                "Agreed to bi-weekly sprint cadence"
            ],
            "next_meeting": "January 2, 2025 at 10:00 AM EST",
            "notes": "Great teamwork this quarter. Looking forward to Q1!"
        }
    )

    print(f"Result: {result}")


async def example_5_create_draft():
    """Example 5: Create an email draft"""
    print("\n=== Example 5: Create Email Draft ===")

    result = await create_email_draft(
        to="client@example.com",
        subject="Proposal for Website Redesign",
        message="Dear Client, Please find our proposal for your website redesign project.",
        html_body="""
        <h2>Website Redesign Proposal</h2>
        <p>Dear Client,</p>
        <p>Thank you for considering us for your website redesign project.</p>
        <p>We propose the following approach:</p>
        <ol>
            <li>Discovery and requirements gathering (1 week)</li>
            <li>Design mockups and prototypes (2 weeks)</li>
            <li>Development and testing (3 weeks)</li>
            <li>Launch and training (1 week)</li>
        </ol>
        <p>Total timeline: 7 weeks</p>
        <p>Best regards,<br>Your Team</p>
        """
    )

    print(f"Result: {result}")


async def example_6_search_unread_emails():
    """Example 6: Search for unread emails from specific sender"""
    print("\n=== Example 6: Search Unread Emails ===")

    result = await search_emails(
        query="from:boss@company.com is:unread",
        max_results=10,
        include_body=False
    )

    print(f"Found {result.get('count', 0)} emails")
    if result.get('status') == 'success' and result.get('emails'):
        for email in result['emails'][:3]:  # Show first 3
            print(f"\n  Subject: {email['subject']}")
            print(f"  From: {email['from']}")
            print(f"  Date: {email['date']}")
            print(f"  Snippet: {email['snippet'][:100]}...")


async def example_7_search_with_date_filter():
    """Example 7: Search emails with date filter and attachment"""
    print("\n=== Example 7: Search with Date Filter ===")

    result = await search_emails(
        query="has:attachment after:2025/12/01 subject:report",
        max_results=20,
        include_body=False
    )

    print(f"Result: Found {result.get('count', 0)} emails with attachments containing 'report' since Dec 1")


async def example_8_get_specific_email():
    """Example 8: Get a specific email by ID"""
    print("\n=== Example 8: Get Specific Email ===")

    # First search for an email
    search_result = await search_emails(
        query="is:unread",
        max_results=1,
        include_body=False
    )

    if search_result.get('status') == 'success' and search_result.get('emails'):
        email_id = search_result['emails'][0]['id']

        # Now get the full email
        result = await get_email(
            message_id=email_id,
            format="full"
        )

        if result.get('status') == 'success':
            email = result['email']
            print(f"\n  Subject: {email['subject']}")
            print(f"  From: {email['from']}")
            print(f"  Body Preview: {email.get('body_plain', '')[:200]}...")


async def example_9_list_recent_unread():
    """Example 9: List recent unread emails"""
    print("\n=== Example 9: List Recent Unread Emails ===")

    result = await list_recent_emails(
        max_results=5,
        filter="unread",
        include_body=False
    )

    print(f"Found {result.get('count', 0)} unread emails")
    if result.get('status') == 'success' and result.get('emails'):
        for i, email in enumerate(result['emails'], 1):
            print(f"\n  {i}. {email['subject']}")
            print(f"     From: {email['from']}")
            print(f"     {email['snippet'][:80]}...")


async def example_10_get_email_thread():
    """Example 10: Get entire conversation thread"""
    print("\n=== Example 10: Get Email Thread ===")

    # First find a thread
    search_result = await search_emails(
        query="subject:meeting",
        max_results=1,
        include_body=False
    )

    if search_result.get('status') == 'success' and search_result.get('emails'):
        thread_id = search_result['emails'][0]['thread_id']

        # Get the full thread
        result = await get_email_thread(thread_id=thread_id)

        if result.get('status') == 'success':
            print(f"\n  Thread has {result['message_count']} messages")
            for i, msg in enumerate(result['messages'], 1):
                print(f"\n  Message {i}:")
                print(f"    From: {msg['from']}")
                print(f"    Subject: {msg['subject']}")
                print(f"    Date: {msg['date']}")


async def example_11_send_report():
    """Example 11: Send a formatted report"""
    print("\n=== Example 11: Send Formatted Report ===")

    result = await send_email_from_template(
        template_name="report",
        to="stakeholders@company.com",
        subject="Monthly Performance Report - December 2025",
        variables={
            "report_title": "Monthly Performance Report",
            "generated_date": "December 26, 2025",
            "period": "December 1-25, 2025",
            "summary": "Overall performance exceeded expectations with significant growth in key metrics. Customer acquisition increased 25% while maintaining high satisfaction scores.",
            "metrics": [
                {"name": "Revenue", "value": "$1.2M"},
                {"name": "New Customers", "value": "450"},
                {"name": "Customer Satisfaction", "value": "4.8/5.0"},
                {"name": "Response Time", "value": "< 2 hours"},
                {"name": "Task Completion", "value": "95%"}
            ],
            "data_sections": [
                {
                    "title": "Top Achievements",
                    "content": "This month saw several major accomplishments:",
                    "items": [
                        "Launched new product feature ahead of schedule",
                        "Onboarded 3 enterprise clients",
                        "Reduced infrastructure costs by 15%"
                    ]
                },
                {
                    "title": "Areas for Improvement",
                    "content": "Focus areas for next month:",
                    "items": [
                        "Streamline onboarding process",
                        "Enhance mobile app performance",
                        "Expand customer support coverage"
                    ]
                }
            ],
            "notes": "All data is preliminary and subject to final audit."
        }
    )

    print(f"Result: {result}")


async def run_all_examples():
    """Run all examples sequentially"""
    examples = [
        example_1_send_simple_email,
        example_2_send_html_email_with_attachments,
        example_3_send_from_notification_template,
        example_4_send_meeting_summary,
        example_5_create_draft,
        example_6_search_unread_emails,
        example_7_search_with_date_filter,
        example_8_get_specific_email,
        example_9_list_recent_unread,
        example_10_get_email_thread,
        example_11_send_report
    ]

    print("Gmail Tools Usage Examples")
    print("=" * 50)
    print("\nNOTE: These are demonstration examples.")
    print("Replace email addresses and file paths with real values before running.")
    print("\nTo run a specific example:")
    print("  python -m examples.gmail_usage_examples")
    print("\n" + "=" * 50)

    # Uncomment to run examples (comment out any send operations in production)
    # for example in examples:
    #     try:
    #         await example()
    #         await asyncio.sleep(1)  # Small delay between examples
    #     except Exception as e:
    #         print(f"Error in {example.__name__}: {e}")


if __name__ == "__main__":
    # Run examples
    asyncio.run(run_all_examples())

    print("\n" + "=" * 50)
    print("Examples completed!")
    print("\nTo use these tools in your code:")
    print("  from app.tools.email_tools import send_email")
    print("  result = await send_email(...)")
    print("=" * 50)
