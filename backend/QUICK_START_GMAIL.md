# Gmail Tools - Quick Start Guide

## ✅ Status: READY FOR USE

All Gmail tools are implemented, integrated, and validated. You can now use the Supervisor to interact with Gmail via natural language.

---

## How to Use

### 1. Start the Supervisor Chat Agent

```bash
cd backend
source venv/bin/activate
python scripts/chat_agent.py --agent supervisor
```

### 2. Complete OAuth Flow (First Run Only)

On the first run, a browser window will open asking you to:
1. Sign in to your Google account
2. Grant Gmail access permissions
3. Allow the application to read/send emails

After authorization, a token is saved to `credentials/gmail_token.json` and you won't need to authorize again (token auto-refreshes).

### 3. Test with Natural Language Queries

Once the chat agent is running, try these queries:

#### Check Recent Emails
```
You: what are the last 4 emails in my gmail
You: check my inbox
You: show me recent emails
```

**Expected Response**: List of emails with subject, sender, date, and preview

#### Check Unread Emails
```
You: show me unread emails
You: what unread emails do I have
```

**Expected Response**: List of unread emails

#### Send Demo Emails ✨ NEW
```
You: send a demo report to fredrickodondi9@gmail.com
You: send a meeting summary to john@example.com
You: send a notification to team@company.com
You: send email to alice@example.com
```

**Expected Response**: "Email sent successfully! Message ID: [id]"

**Note**: These send predefined demo content. The email type is detected from keywords:
- "report" → Professional ECOWAS report with metrics
- "meeting" or "summary" → Meeting summary with action items
- "notification" or "alert" → System notification with action button
- Default → Generic demo email

#### Check Email Tools Status
```
You: what email tools do you have
You: can you send emails
You: email capabilities
```

**Expected Response**: List of available email tools

---

## What Works Now

### Natural Language Email Retrieval
The Supervisor automatically detects and executes Gmail queries:

| Query | Tool Called | Parameters |
|-------|-------------|------------|
| "last 4 emails" | search_emails() | query="is:inbox", max_results=4 |
| "unread emails" | search_emails() | query="is:unread", max_results=50 |
| "check inbox" | search_emails() | query="is:inbox", max_results=5 |
| "email tools" | get_email_tools_status() | - |

### Natural Language Email Sending ✨ NEW
The Supervisor now automatically detects and sends emails:

| Query | Tool Called | Content |
|-------|-------------|---------|
| "send a demo report to user@example.com" | send_report_email() | Professional ECOWAS report with metrics |
| "send a meeting summary to user@example.com" | send_meeting_summary_email() | TWG coordination meeting summary |
| "send a notification to user@example.com" | send_notification_email() | System notification with action button |
| "send email to user@example.com" | send_email() | Generic demo email with HTML |

### Pattern Detection Examples

**Number Extraction**:
- "last 10 emails" → max_results=10
- "last 3 emails" → max_results=3
- "all emails" → max_results=50

**Query Modification**:
- "unread" → adds "is:unread" to query
- "inbox" → uses "is:inbox" query
- Default → "is:inbox"

---

## What Doesn't Work Yet (Future Enhancement)

### Custom Email Content via Natural Language
Currently NOT supported:
```
You: send email to john@example.com about project update with subject "Q4 Progress"
```

**Why**: Extracting custom subject/body from natural language requires more sophisticated NLP.

**Current Behavior**: System sends predefined demo content based on email type (report/meeting/notification).

**Workaround**: Use programmatic API for custom content (see below)

### Complex Searches
Currently NOT supported:
```
You: find emails from john@example.com about budget
```

**Why**: Pattern detection only handles basic inbox/unread searches.

**Workaround**: Use programmatic API with Gmail query syntax

---

## Programmatic API Usage

For advanced use cases, you can call email tools directly:

### Python Example

```python
import asyncio
from app.agents.supervisor_with_tools import create_supervisor_with_tools

async def main():
    supervisor = create_supervisor_with_tools(auto_register=False)

    # Search emails with custom query
    result = await supervisor.search_emails(
        query="from:john@example.com subject:budget",
        max_results=10,
        include_body=True
    )
    print(result)

    # Send email
    result = await supervisor.send_email(
        to="recipient@example.com",
        subject="Test Email",
        message="Plain text message",
        html_body="<h1>HTML formatted message</h1>",
        attachments=["/path/to/file.pdf"]
    )
    print(result)

    # Send using template
    result = await supervisor.send_email_from_template(
        template_name="notification",
        to="team@example.com",
        subject="System Alert",
        variables={
            "heading": "Urgent Update",
            "message": "System maintenance scheduled",
            "action_url": "https://example.com",
            "action_text": "View Details"
        }
    )
    print(result)

asyncio.run(main())
```

### Gmail Query Syntax

You can use powerful Gmail query syntax:

```python
# Search by sender
query = "from:boss@company.com"

# Search by subject
query = "subject:meeting"

# Search unread
query = "is:unread"

# Search with attachments
query = "has:attachment"

# Search by date
query = "after:2025/12/01"

# Combine criteria
query = "from:boss@company.com is:unread subject:urgent"
```

---

## Available Email Tools (All 7)

### 1. send_email
Send emails with HTML, CC/BCC, and attachments
```python
await supervisor.send_email(
    to="user@example.com",
    subject="Subject",
    message="Plain text",
    html_body="<h1>HTML</h1>",
    cc="cc@example.com",
    bcc="bcc@example.com",
    attachments=["/path/to/file.pdf"]
)
```

### 2. send_email_from_template
Use Jinja2 templates with variables
```python
await supervisor.send_email_from_template(
    template_name="notification",
    to="user@example.com",
    subject="Notification",
    variables={"heading": "Alert", "message": "Message"}
)
```

### 3. create_email_draft
Create draft without sending
```python
await supervisor.create_email_draft(
    to="user@example.com",
    subject="Draft",
    message="Content"
)
```

### 4. search_emails
Search with Gmail query syntax
```python
await supervisor.search_emails(
    query="is:unread from:boss@company.com",
    max_results=10,
    include_body=True
)
```

### 5. get_email
Get specific email by ID
```python
await supervisor.get_email(
    message_id="abc123",
    format="full"  # minimal/full/metadata
)
```

### 6. list_recent_emails
List N most recent emails
```python
await supervisor.list_recent_emails(
    max_results=10,
    filter="unread",  # all/unread/starred
    include_body=False
)
```

### 7. get_email_thread
Get entire conversation thread
```python
await supervisor.get_email_thread(
    thread_id="thread_abc123"
)
```

---

## Email Templates

4 professional HTML templates available in `app/templates/email/`:

### 1. base.html
Base layout with header and footer

### 2. notification.html
Notifications with action buttons
```python
variables = {
    "heading": "System Alert",
    "message": "Your attention needed",
    "details": "Additional information",
    "action_url": "https://example.com",
    "action_text": "Take Action"
}
```

### 3. report.html
Professional reports with metrics
```python
variables = {
    "title": "Monthly Report",
    "summary": "Report summary",
    "metrics": [
        {"label": "Users", "value": "1,234", "trend": "+12%"},
        {"label": "Revenue", "value": "$56,789", "trend": "+8%"}
    ],
    "sections": [
        {"title": "Section 1", "content": "Content"}
    ]
}
```

### 4. meeting_summary.html
Meeting summaries with action items
```python
variables = {
    "meeting_title": "Team Sync",
    "date": "2025-12-26",
    "attendees": ["Alice", "Bob", "Charlie"],
    "summary": "Meeting discussion",
    "action_items": [
        {"task": "Review document", "assignee": "Alice", "due_date": "2025-12-28"},
        {"task": "Send update", "assignee": "Bob", "due_date": "2025-12-29"}
    ],
    "next_meeting": "2026-01-02 10:00 AM"
}
```

---

## Troubleshooting

### Browser Doesn't Open for OAuth

If OAuth browser doesn't open automatically:
1. Check terminal for authorization URL
2. Manually copy URL into browser
3. Complete authorization
4. Copy code back to terminal

### "Permission Denied" Error

Make sure Gmail API scopes include:
```python
GMAIL_SCOPES = ["https://mail.google.com/"]
```

This provides full Gmail access (read + send). If you only need read access:
```python
GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
```

But note: Sending emails requires write scope.

### Token Expired

Token auto-refreshes, but if you get "invalid_grant" error:
1. Delete `credentials/gmail_token.json`
2. Restart chat agent
3. Re-authorize in browser

### Supervisor Still Giving Instructions

If supervisor says "To assist you..." instead of actually fetching emails:

**Check 1**: Verify chat_agent.py is using chat_with_tools:
```bash
grep -n "chat_with_tools" scripts/chat_agent.py
```

Should show lines 506-508 with `asyncio.run(agent.chat_with_tools(user_input))`

**Check 2**: Verify supervisor_with_tools is imported:
```bash
grep -n "supervisor_with_tools" scripts/chat_agent.py
```

Should show line 26: `from app.agents.supervisor_with_tools import create_supervisor_with_tools`

**Check 3**: Run validation:
```bash
python validate_gmail_integration.py
```

All checks should pass.

---

## Testing Pattern Detection

Test pattern detection without OAuth:

```bash
python test_supervisor_tools.py
```

This tests:
1. "what are the last 4 emails in my gmail" → Detects search_emails with max_results=4
2. "show me unread emails" → Detects search_emails with query="is:unread"
3. "what email tools do you have" → Detects get_email_tools_status
4. "what is ECOWAS" → No tool detected, uses regular chat

---

## Next Steps

### Immediate
1. ✅ Start chat agent: `python scripts/chat_agent.py --agent supervisor`
2. ✅ Complete OAuth (first run only)
3. ✅ Test: "what are the last 4 emails in my gmail"
4. ✅ Verify: Should return actual email list, NOT instructions

### Future Enhancements
1. Add more patterns for email sending via natural language
2. Add patterns for complex searches (from:, subject:, etc.)
3. Add calendar integration
4. Add Google Drive integration
5. Switch to function-calling LLM (GPT-4/Claude) for better NLU

---

## Files Reference

### Core Implementation
- **Service**: [app/services/gmail_service.py](app/services/gmail_service.py)
- **Tools**: [app/tools/email_tools.py](app/tools/email_tools.py)
- **Wrapper**: [app/agents/supervisor_with_tools.py](app/agents/supervisor_with_tools.py)
- **Integration**: [scripts/chat_agent.py](scripts/chat_agent.py)

### Configuration
- **Settings**: [app/core/config.py](app/core/config.py)
- **Prompt**: [app/agents/prompts/supervisor.txt](app/agents/prompts/supervisor.txt)
- **OAuth Creds**: [credentials/gmail_credentials.json](credentials/gmail_credentials.json)

### Templates
- **Base**: [app/templates/email/base.html](app/templates/email/base.html)
- **Notification**: [app/templates/email/notification.html](app/templates/email/notification.html)
- **Report**: [app/templates/email/report.html](app/templates/email/report.html)
- **Meeting**: [app/templates/email/meeting_summary.html](app/templates/email/meeting_summary.html)

### Documentation
- **Complete Guide**: [GMAIL_TOOLS_COMPLETE.md](GMAIL_TOOLS_COMPLETE.md)
- **Setup**: [GMAIL_SETUP.md](GMAIL_SETUP.md)
- **Solution**: [SUPERVISOR_TOOLS_SOLUTION.md](SUPERVISOR_TOOLS_SOLUTION.md)

### Testing
- **Validation**: [validate_gmail_integration.py](validate_gmail_integration.py)
- **Pattern Test**: [test_supervisor_tools.py](test_supervisor_tools.py)

---

## Support

### Getting Help
- Review [SUPERVISOR_TOOLS_SOLUTION.md](SUPERVISOR_TOOLS_SOLUTION.md) for architecture
- Check [GMAIL_TOOLS_COMPLETE.md](GMAIL_TOOLS_COMPLETE.md) for full documentation
- Run `python validate_gmail_integration.py` to diagnose issues

### Common Issues
1. **ModuleNotFoundError**: Run `pip install jinja2 google-api-python-client`
2. **Supervisor gives instructions**: Check chat_agent.py integration (see Troubleshooting)
3. **OAuth fails**: Delete token.json and re-authorize
4. **Permission denied**: Check Gmail API scopes in config

---

**Implementation Date**: December 26, 2025
**Status**: ✅ Complete and validated
**Ready**: For OAuth + live Gmail testing

**Quick Test**: `python scripts/chat_agent.py --agent supervisor` then ask `"what are the last 4 emails in my gmail"`
