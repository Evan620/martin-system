#!/usr/bin/env python3
"""
Gmail Tools Integration Validation

This script validates that all Gmail tools are properly integrated and ready to use.
It checks imports, tool registration, supervisor integration, and chat agent configuration.
"""

import sys
import os
from pathlib import Path

# Color codes for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def check(condition, message):
    """Print check result with color."""
    if condition:
        print(f"{GREEN}✓{RESET} {message}")
        return True
    else:
        print(f"{RED}✗{RESET} {message}")
        return False

def info(message):
    """Print info message."""
    print(f"{BLUE}ℹ{RESET} {message}")

def warning(message):
    """Print warning message."""
    print(f"{YELLOW}⚠{RESET} {message}")

def main():
    print("=" * 70)
    print("Gmail Tools Integration Validation")
    print("=" * 70)
    print()

    all_checks_passed = True

    # Check 1: File existence
    print("1. Checking file existence...")
    files_to_check = [
        'app/services/gmail_service.py',
        'app/tools/email_tools.py',
        'app/agents/supervisor_with_tools.py',
        'app/agents/supervisor.py',
        'app/agents/prompts/supervisor.txt',
        'app/templates/email/base.html',
        'app/templates/email/notification.html',
        'app/templates/email/report.html',
        'app/templates/email/meeting_summary.html',
        'credentials/gmail_credentials.json',
        'scripts/chat_agent.py',
    ]

    for file in files_to_check:
        all_checks_passed &= check(Path(file).exists(), f"{file}")
    print()

    # Check 2: Module imports
    print("2. Checking module imports...")
    try:
        from app.services.gmail_service import get_gmail_service, GmailService
        check(True, "gmail_service imports successfully")
    except ImportError as e:
        check(False, f"gmail_service import failed: {e}")
        all_checks_passed = False

    try:
        from app.tools.email_tools import EMAIL_TOOLS
        check(True, f"email_tools imports successfully ({len(EMAIL_TOOLS)} tools)")
    except ImportError as e:
        check(False, f"email_tools import failed: {e}")
        all_checks_passed = False

    try:
        from app.agents.supervisor_with_tools import create_supervisor_with_tools, SupervisorWithTools
        check(True, "supervisor_with_tools imports successfully")
    except ImportError as e:
        check(False, f"supervisor_with_tools import failed: {e}")
        all_checks_passed = False

    try:
        from app.agents.supervisor import SupervisorAgent
        check(True, "supervisor imports successfully")
    except ImportError as e:
        check(False, f"supervisor import failed: {e}")
        all_checks_passed = False
    print()

    # Check 3: Dependencies
    print("3. Checking dependencies...")
    try:
        import jinja2
        check(True, f"jinja2 installed (v{jinja2.__version__})")
    except ImportError:
        check(False, "jinja2 NOT installed - run: pip install jinja2")
        all_checks_passed = False

    try:
        import googleapiclient
        check(True, "google-api-python-client installed")
    except ImportError:
        check(False, "google-api-python-client NOT installed - run: pip install google-api-python-client")
        all_checks_passed = False

    try:
        import google.auth
        check(True, "google-auth installed")
    except ImportError:
        check(False, "google-auth NOT installed - run: pip install google-auth-httplib2 google-auth-oauthlib")
        all_checks_passed = False
    print()

    # Check 4: Email tools registry
    print("4. Checking email tools registry...")
    try:
        from app.tools.email_tools import EMAIL_TOOLS
        expected_tools = [
            'send_email',
            'send_email_from_template',
            'create_email_draft',
            'search_emails',
            'get_email',
            'list_recent_emails',
            'get_email_thread'
        ]

        tool_names = [tool['name'] for tool in EMAIL_TOOLS]
        for expected_tool in expected_tools:
            all_checks_passed &= check(
                expected_tool in tool_names,
                f"{expected_tool} registered"
            )
    except Exception as e:
        check(False, f"Failed to check email tools: {e}")
        all_checks_passed = False
    print()

    # Check 5: Supervisor email methods
    print("5. Checking supervisor email methods...")
    try:
        from app.agents.supervisor import SupervisorAgent
        supervisor_methods = [
            'send_email',
            'send_meeting_summary_email',
            'send_report_email',
            'send_notification_email',
            'broadcast_email_to_all_twgs',
            'search_emails',
            'get_email_tools_status'
        ]

        for method in supervisor_methods:
            all_checks_passed &= check(
                hasattr(SupervisorAgent, method),
                f"SupervisorAgent.{method}() exists"
            )
    except Exception as e:
        check(False, f"Failed to check supervisor methods: {e}")
        all_checks_passed = False
    print()

    # Check 6: SupervisorWithTools pattern detection
    print("6. Checking SupervisorWithTools pattern detection...")
    try:
        from app.agents.supervisor_with_tools import SupervisorWithTools

        all_checks_passed &= check(
            hasattr(SupervisorWithTools, 'chat_with_tools'),
            "SupervisorWithTools.chat_with_tools() exists"
        )
        all_checks_passed &= check(
            hasattr(SupervisorWithTools, '_detect_email_request'),
            "SupervisorWithTools._detect_email_request() exists"
        )
        all_checks_passed &= check(
            hasattr(SupervisorWithTools, '_execute_tool'),
            "SupervisorWithTools._execute_tool() exists"
        )
    except Exception as e:
        check(False, f"Failed to check SupervisorWithTools: {e}")
        all_checks_passed = False
    print()

    # Check 7: Chat agent integration
    print("7. Checking chat_agent.py integration...")
    try:
        with open('scripts/chat_agent.py', 'r') as f:
            chat_agent_content = f.read()

        all_checks_passed &= check(
            'from app.agents.supervisor_with_tools import create_supervisor_with_tools' in chat_agent_content,
            "Imports create_supervisor_with_tools"
        )
        all_checks_passed &= check(
            'import asyncio' in chat_agent_content,
            "Imports asyncio"
        )
        all_checks_passed &= check(
            'chat_with_tools' in chat_agent_content,
            "Uses chat_with_tools() method"
        )
        all_checks_passed &= check(
            '"supervisor": create_supervisor_with_tools' in chat_agent_content,
            "Uses create_supervisor_with_tools in factory"
        )
    except Exception as e:
        check(False, f"Failed to check chat_agent.py: {e}")
        all_checks_passed = False
    print()

    # Check 8: OAuth credentials
    print("8. Checking OAuth credentials...")
    creds_exist = Path('credentials/gmail_credentials.json').exists()
    if creds_exist:
        try:
            import json
            with open('credentials/gmail_credentials.json', 'r') as f:
                creds = json.load(f)

            check(True, "gmail_credentials.json exists and is valid JSON")

            if 'installed' in creds:
                has_client_id = 'client_id' in creds['installed']
                has_client_secret = 'client_secret' in creds['installed']
                all_checks_passed &= check(has_client_id and has_client_secret, "OAuth client credentials configured")
            else:
                warning("Credentials file format not recognized")
        except Exception as e:
            check(False, f"Failed to read credentials: {e}")
            all_checks_passed = False
    else:
        check(False, "gmail_credentials.json not found")
        all_checks_passed = False

    token_exists = Path('credentials/gmail_token.json').exists()
    if token_exists:
        info("gmail_token.json exists (OAuth already completed)")
    else:
        warning("gmail_token.json not found (OAuth flow will run on first use)")
    print()

    # Check 9: Template system
    print("9. Checking email templates...")
    try:
        from jinja2 import Environment, FileSystemLoader
        template_dir = 'app/templates/email'

        env = Environment(loader=FileSystemLoader(template_dir))

        templates = ['base.html', 'notification.html', 'report.html', 'meeting_summary.html']
        for template in templates:
            try:
                env.get_template(template)
                all_checks_passed &= check(True, f"{template} loads successfully")
            except Exception as e:
                check(False, f"{template} failed to load: {e}")
                all_checks_passed = False
    except Exception as e:
        check(False, f"Failed to check templates: {e}")
        all_checks_passed = False
    print()

    # Final summary
    print("=" * 70)
    if all_checks_passed:
        print(f"{GREEN}✓ All checks passed! Gmail tools are ready to use.{RESET}")
        print()
        print("Next steps:")
        print("1. Run: python scripts/chat_agent.py --agent supervisor")
        print("2. Complete OAuth flow (browser will open on first run)")
        print("3. Test with: 'what are the last 4 emails in my gmail'")
    else:
        print(f"{RED}✗ Some checks failed. Please fix the issues above.{RESET}")
    print("=" * 70)

    return 0 if all_checks_passed else 1

if __name__ == "__main__":
    sys.exit(main())
