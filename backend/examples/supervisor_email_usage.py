"""
Supervisor Email Integration Examples

Demonstrates how the Supervisor agent can use Gmail tools to:
- Send meeting summaries
- Send status reports
- Send notifications
- Broadcast updates to all TWGs
- Search for relevant emails
"""

import asyncio
import sys
import os
from datetime import datetime

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agents.supervisor import create_supervisor


async def example_1_send_meeting_summary():
    """Example 1: Supervisor sends meeting summary to TWG members"""
    print("\n" + "=" * 70)
    print("EXAMPLE 1: Send Meeting Summary")
    print("=" * 70)

    supervisor = create_supervisor(auto_register=False)

    meeting_data = {
        "meeting_date": "December 26, 2025",
        "meeting_time": "10:00 AM - 12:00 PM WAT",
        "duration": "2 hours",
        "location": "ECOWAS Commission, Abuja",
        "participants": [
            "Energy TWG Coordinator",
            "Agriculture TWG Coordinator",
            "Minerals TWG Coordinator",
            "Digital TWG Coordinator",
            "Supervisor Agent"
        ],
        "agenda": [
            "Review Q1 progress across all TWGs",
            "Discuss Summit 2026 preparations",
            "Identify cross-TWG synergies",
            "Plan resource mobilization strategy"
        ],
        "discussion_points": [
            {
                "topic": "Energy Infrastructure Progress",
                "summary": "WAPP expansion on track. 3 solar projects initiated. Grid interconnection with Cote d'Ivoire 75% complete."
            },
            {
                "topic": "Agricultural Transformation",
                "summary": "Food security metrics improving. Digital agriculture platform launched in 3 countries. Irrigation projects progressing."
            },
            {
                "topic": "Minerals & Industrialization",
                "summary": "Battery value chain framework established. Lithium processing facility agreements signed. Local content requirements defined."
            }
        ],
        "action_items": [
            {
                "description": "Finalize cross-TWG investment pipeline for Deal Room",
                "owner": "All TWG Coordinators",
                "due_date": "January 15, 2026"
            },
            {
                "description": "Submit draft Declaration sections",
                "owner": "All TWG Coordinators",
                "due_date": "January 20, 2026"
            },
            {
                "description": "Coordinate VIP engagement schedule",
                "owner": "Protocol TWG",
                "due_date": "January 10, 2026"
            },
            {
                "description": "Prepare Summit readiness assessment",
                "owner": "Supervisor",
                "due_date": "January 25, 2026"
            }
        ],
        "decisions": [
            "Approved $50B investment pipeline target for Summit",
            "Agreed on unified regional digital payment platform priority",
            "Endorsed cross-border energy trading framework",
            "Committed to monthly coordination meetings"
        ],
        "next_meeting": "January 15, 2026 at 10:00 AM WAT",
        "notes": "Excellent alignment across all TWGs. Strong momentum toward Summit 2026 objectives."
    }

    result = await supervisor.send_meeting_summary_email(
        to=["twg-coordinators@ecowas.org"],
        meeting_data=meeting_data,
        cc=["director@ecowas.org"]
    )

    print(f"\nResult: {result.get('status')}")
    if result.get('status') == 'success':
        print(f"Message ID: {result.get('message_id')}")
        print("✓ Meeting summary sent successfully!")
    else:
        print(f"Error: {result.get('error')}")


async def example_2_send_summit_readiness_report():
    """Example 2: Supervisor sends Summit readiness report to Ministers"""
    print("\n" + "=" * 70)
    print("EXAMPLE 2: Send Summit Readiness Report")
    print("=" * 70)

    supervisor = create_supervisor(auto_register=False)

    report_data = {
        "report_title": "ECOWAS Summit 2026 - Readiness Assessment",
        "generated_date": datetime.now().strftime("%B %d, %Y"),
        "period": "Q4 2025 - Q1 2026",
        "summary": "All four pillars (Energy, Agriculture, Minerals, Digital) are on track for the Summit. Overall readiness: 85%. Investment pipeline stands at $47B, approaching the $50B target. Key deliverables progressing well with no major blockers identified.",
        "metrics": [
            {"name": "Overall Readiness", "value": "85%"},
            {"name": "Investment Pipeline", "value": "$47B"},
            {"name": "Deliverables On Track", "value": "92%"},
            {"name": "TWG Coordination Score", "value": "4.5/5.0"},
            {"name": "Stakeholder Engagement", "value": "450+ entities"},
            {"name": "Policy Frameworks", "value": "12 completed"}
        ],
        "data_sections": [
            {
                "title": "Energy & Infrastructure Pillar",
                "content": "Strong progress on regional power integration and renewable energy deployment.",
                "items": [
                    "WAPP expansion: 5 interconnection projects (3 completed, 2 in progress)",
                    "Solar energy: 800 MW added across 6 countries",
                    "Investment secured: $15.2B",
                    "Policy frameworks: Regional Energy Compact finalized"
                ]
            },
            {
                "title": "Agriculture & Food Security Pillar",
                "content": "Digital agriculture transformation and regional food systems strengthening.",
                "items": [
                    "Digital agri-platform deployed in 8 countries",
                    "Irrigation infrastructure: 45,000 hectares improved",
                    "Food security index improved 18% year-over-year",
                    "Investment secured: $12.8B"
                ]
            },
            {
                "title": "Critical Minerals & Industrialization Pillar",
                "content": "Battery value chain development and local content integration.",
                "items": [
                    "Lithium processing agreements signed with 4 countries",
                    "Battery manufacturing facility under construction in Ghana",
                    "Local content requirements: 30% minimum established",
                    "Investment secured: $11.5B"
                ]
            },
            {
                "title": "Digital Economy Pillar",
                "content": "Regional digital infrastructure and payment system integration.",
                "items": [
                    "Digital payment interoperability launched in 5 countries",
                    "Broadband coverage expanded to 65% regional average",
                    "E-government platforms deployed in 7 countries",
                    "Investment secured: $7.5B"
                ]
            }
        ],
        "notes": "Minor delays in 2 infrastructure projects due to rainy season. Mitigation plans in place. No impact on Summit timeline expected."
    }

    result = await supervisor.send_report_email(
        to=["ministers@ecowas.org"],
        report_data=report_data,
        subject="Summit 2026 Readiness Assessment - December 2025",
        cc=["commissioners@ecowas.org", "twg-coordinators@ecowas.org"]
    )

    print(f"\nResult: {result.get('status')}")
    if result.get('status') == 'success':
        print(f"Message ID: {result.get('message_id')}")
        print("✓ Summit readiness report sent successfully!")
    else:
        print(f"Error: {result.get('error')}")


async def example_3_send_notification():
    """Example 3: Supervisor sends notification about new documents"""
    print("\n" + "=" * 70)
    print("EXAMPLE 3: Send Notification")
    print("=" * 70)

    supervisor = create_supervisor(auto_register=False)

    result = await supervisor.send_notification_email(
        to=["twg-all@ecowas.org"],
        heading="New Summit Concept Note Available",
        message="The ECOWAS Summit 2026 Concept Note version 2.0 has been finalized and is now available for your review. This updated version incorporates feedback from all TWGs and Ministers.",
        details="Please review the document by January 5, 2026 and submit any final comments to the Supervisor.",
        action_url="https://portal.ecowas.org/documents/summit-2026-concept-note-v2",
        action_text="View Concept Note",
        cc=["director@ecowas.org"]
    )

    print(f"\nResult: {result.get('status')}")
    if result.get('status') == 'success':
        print(f"Message ID: {result.get('message_id')}")
        print("✓ Notification sent successfully!")
    else:
        print(f"Error: {result.get('error')}")


async def example_4_broadcast_to_all_twgs():
    """Example 4: Supervisor broadcasts update to all TWG coordinators"""
    print("\n" + "=" * 70)
    print("EXAMPLE 4: Broadcast to All TWGs")
    print("=" * 70)

    supervisor = create_supervisor(auto_register=True)

    # Define TWG coordinator emails
    twg_emails = {
        "energy": "energy-coordinator@ecowas.org",
        "agriculture": "agriculture-coordinator@ecowas.org",
        "minerals": "minerals-coordinator@ecowas.org",
        "digital": "digital-coordinator@ecowas.org",
        "protocol": "protocol-coordinator@ecowas.org",
        "resource_mobilization": "resource-mobilization@ecowas.org"
    }

    results = await supervisor.broadcast_email_to_all_twgs(
        subject="URGENT: Final Deliverables Due January 15",
        message="""
Dear TWG Coordinators,

This is a reminder that all final deliverables for the ECOWAS Summit 2026 are due on January 15, 2026.

Required deliverables:
1. Draft Declaration section (2-3 pages)
2. Investment pipeline summary (bankable projects)
3. Policy framework recommendations
4. Stakeholder engagement report
5. Risk assessment and mitigation plan

Please submit all materials through the Summit Portal by 5:00 PM WAT on January 15.

Contact the Supervisor if you need any support or extensions.

Best regards,
ECOWAS Summit 2026 Coordination Team
        """,
        html_body="""
<h2>URGENT: Final Deliverables Due January 15</h2>

<p>Dear TWG Coordinators,</p>

<p>This is a reminder that all final deliverables for the <strong>ECOWAS Summit 2026</strong> are due on <strong>January 15, 2026</strong>.</p>

<h3>Required Deliverables:</h3>
<ol>
    <li>Draft Declaration section (2-3 pages)</li>
    <li>Investment pipeline summary (bankable projects)</li>
    <li>Policy framework recommendations</li>
    <li>Stakeholder engagement report</li>
    <li>Risk assessment and mitigation plan</li>
</ol>

<p><strong>Deadline:</strong> January 15, 2026 at 5:00 PM WAT</p>

<p>Please submit all materials through the <a href="https://portal.ecowas.org">Summit Portal</a>.</p>

<p>Contact the Supervisor if you need any support or extensions.</p>

<p>Best regards,<br><strong>ECOWAS Summit 2026 Coordination Team</strong></p>
        """,
        twg_emails=twg_emails
    )

    print(f"\nBroadcast Results:")
    print("-" * 70)
    successful = 0
    failed = 0

    for twg_id, result in results.items():
        status = "✓" if result.get('status') == 'success' else "✗"
        print(f"{status} {twg_id.upper()}: {result.get('status')}")
        if result.get('status') == 'success':
            successful += 1
        else:
            failed += 1
            print(f"  Error: {result.get('error')}")

    print("-" * 70)
    print(f"Summary: {successful} successful, {failed} failed out of {len(results)} TWGs")


async def example_5_search_for_emails():
    """Example 5: Supervisor searches for important emails"""
    print("\n" + "=" * 70)
    print("EXAMPLE 5: Search for Emails")
    print("=" * 70)

    supervisor = create_supervisor(auto_register=False)

    # Search for unread emails from ministers
    print("\nSearching for unread emails from ministers...")
    results = await supervisor.search_emails(
        query="from:ministers@ecowas.org is:unread",
        max_results=10,
        include_body=False
    )

    if results.get('status') == 'success':
        print(f"\nFound {results.get('count', 0)} emails:")
        for i, email in enumerate(results.get('emails', [])[:5], 1):
            print(f"\n  {i}. {email['subject']}")
            print(f"     From: {email['from']}")
            print(f"     Date: {email['date']}")
            print(f"     Snippet: {email['snippet'][:80]}...")
    else:
        print(f"Search failed: {results.get('error')}")

    # Search for Summit-related emails
    print("\n" + "-" * 70)
    print("\nSearching for Summit-related emails...")
    results2 = await supervisor.search_emails(
        query="subject:Summit after:2025/12/01",
        max_results=15,
        include_body=False
    )

    if results2.get('status') == 'success':
        print(f"\nFound {results2.get('count', 0)} Summit-related emails since December 1")
    else:
        print(f"Search failed: {results2.get('error')}")


async def example_6_check_email_tools_status():
    """Example 6: Check email tools integration status"""
    print("\n" + "=" * 70)
    print("EXAMPLE 6: Email Tools Status")
    print("=" * 70)

    supervisor = create_supervisor(auto_register=False)

    status = await supervisor.get_email_tools_status()

    print(f"\nEmail Tools Available: {status['email_tools_available']}")
    print(f"Total Tools: {status['tool_count']}")

    print(f"\nAvailable Tools:")
    for tool_name in status['available_tools']:
        print(f"  • {tool_name}")

    print(f"\nAvailable Templates:")
    for template in status['templates_available']:
        print(f"  • {template}")


async def example_7_simple_email():
    """Example 7: Send a simple email"""
    print("\n" + "=" * 70)
    print("EXAMPLE 7: Send Simple Email")
    print("=" * 70)

    supervisor = create_supervisor(auto_register=False)

    result = await supervisor.send_email(
        to="coordinator@ecowas.org",
        subject="Test Email from Supervisor",
        message="This is a test email sent from the Supervisor agent using Gmail integration.",
        html_body="""
        <h2>Test Email</h2>
        <p>This is a test email sent from the <strong>Supervisor agent</strong> using Gmail integration.</p>
        <p>Email capabilities include:</p>
        <ul>
            <li>Plain text and HTML formatting</li>
            <li>File attachments</li>
            <li>Template-based emails</li>
            <li>CC and BCC</li>
        </ul>
        <p>All systems operational!</p>
        """
    )

    print(f"\nResult: {result.get('status')}")
    if result.get('status') == 'success':
        print(f"Message ID: {result.get('message_id')}")
        print("✓ Simple email sent successfully!")
    else:
        print(f"Error: {result.get('error')}")


async def run_all_examples():
    """Run all Supervisor email integration examples"""
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 15 + "SUPERVISOR EMAIL INTEGRATION EXAMPLES" + " " * 16 + "║")
    print("╚" + "=" * 68 + "╝")

    examples = [
        ("Meeting Summary", example_1_send_meeting_summary),
        ("Summit Readiness Report", example_2_send_summit_readiness_report),
        ("Notification", example_3_send_notification),
        ("Broadcast to TWGs", example_4_broadcast_to_all_twgs),
        ("Search Emails", example_5_search_for_emails),
        ("Email Tools Status", example_6_check_email_tools_status),
        ("Simple Email", example_7_simple_email)
    ]

    print("\nAvailable Examples:")
    for i, (name, _) in enumerate(examples, 1):
        print(f"  {i}. {name}")

    print("\n" + "=" * 70)
    print("\nNOTE: Update email addresses before running!")
    print("Replace example addresses with real ECOWAS addresses.")
    print("\nThese examples demonstrate the Supervisor's email capabilities:")
    print("  • Send formatted meeting summaries")
    print("  • Send comprehensive reports")
    print("  • Send notifications with action buttons")
    print("  • Broadcast to all TWGs simultaneously")
    print("  • Search emails with Gmail queries")
    print("=" * 70)

    # Uncomment to run specific examples
    # await example_6_check_email_tools_status()
    # await example_7_simple_email()


async def interactive_menu():
    """Interactive menu for running examples"""
    examples = {
        "1": ("Meeting Summary", example_1_send_meeting_summary),
        "2": ("Summit Readiness Report", example_2_send_summit_readiness_report),
        "3": ("Notification", example_3_send_notification),
        "4": ("Broadcast to TWGs", example_4_broadcast_to_all_twgs),
        "5": ("Search Emails", example_5_search_for_emails),
        "6": ("Email Tools Status", example_6_check_email_tools_status),
        "7": ("Simple Email", example_7_simple_email),
    }

    while True:
        print("\n" + "=" * 70)
        print("SUPERVISOR EMAIL EXAMPLES - Interactive Menu")
        print("=" * 70)

        for key, (name, _) in examples.items():
            print(f"  {key}. {name}")
        print("  0. Exit")

        choice = input("\nSelect example (0-7): ").strip()

        if choice == "0":
            print("\nExiting...")
            break

        if choice in examples:
            name, func = examples[choice]
            print(f"\nRunning: {name}")
            try:
                await func()
            except Exception as e:
                print(f"\nError: {e}")
                import traceback
                traceback.print_exc()

            input("\nPress Enter to continue...")
        else:
            print("\nInvalid choice. Please select 0-7.")


if __name__ == "__main__":
    try:
        # Run summary (doesn't actually send emails)
        asyncio.run(run_all_examples())

        # Uncomment for interactive menu
        # asyncio.run(interactive_menu())

    except KeyboardInterrupt:
        print("\n\nInterrupted by user.")
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()
