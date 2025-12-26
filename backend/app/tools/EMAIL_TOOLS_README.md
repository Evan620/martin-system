# Gmail Tools Documentation

Complete Gmail integration for sending and retrieving emails in the AI Agent System.

## Overview

The Gmail tools provide comprehensive email capabilities including:
- Send emails with HTML, attachments, CC/BCC
- Send emails using templates with variable substitution
- Create email drafts
- Search emails with Gmail query syntax
- Retrieve specific emails by ID
- List recent emails with filters
- Get entire email conversation threads

## Files Created

### Core Files
1. **`app/services/gmail_service.py`** (488 lines)
   - Gmail service layer with OAuth authentication
   - Singleton pattern for Gmail API access
   - Core methods for all email operations

2. **`app/tools/email_tools.py`** (720+ lines)
   - 7 async tool functions for email operations
   - Utility functions for email parsing and validation
   - EMAIL_TOOLS registry for agent integration

3. **`app/core/config.py`** (modified)
   - Added Gmail configuration settings
   - Email template directory configuration

### Email Templates
Created in `app/templates/email/`:
1. **`base.html`** - Base template with header/footer layout
2. **`notification.html`** - Simple notification template
3. **`report.html`** - Formatted report template with metrics tables
4. **`meeting_summary.html`** - Detailed meeting summary with action items

## Setup Instructions

### 1. Gmail OAuth Credentials

Since you have credentials ready:

1. Place your `gmail_credentials.json` in `backend/credentials/`
2. On first run, the OAuth flow will open a browser for authorization
3. `gmail_token.json` will be created automatically and auto-refreshes

### 2. Environment Variables (Optional)

Add to your `.env` file if you want to override defaults:

```bash
# Gmail Configuration
GMAIL_CREDENTIALS_FILE=./credentials/gmail_credentials.json
GMAIL_TOKEN_FILE=./credentials/gmail_token.json

# Email Templates
EMAIL_TEMPLATES_DIR=./app/templates/email
DEFAULT_EMAIL_FROM=your-email@example.com
```

## Available Tools

### 1. send_email

Send an email with full feature support.

**Parameters:**
- `to` (str | list): Recipient email(s)
- `subject` (str): Email subject
- `message` (str): Plain text body
- `html_body` (str, optional): HTML formatted body
- `cc` (str | list, optional): CC recipients
- `bcc` (str | list, optional): BCC recipients
- `attachments` (list, optional): File paths to attach

**Example:**
```python
from app.tools.email_tools import send_email

result = await send_email(
    to="user@example.com",
    subject="Project Update",
    message="Here's the project update...",
    html_body="<h1>Project Update</h1><p>Here's the update...</p>",
    cc=["manager@example.com"],
    attachments=["/path/to/report.pdf"]
)

# Returns:
# {
#     "status": "success",
#     "message_id": "18c5f2a3b4d5e6f7",
#     "thread_id": "18c5f2a3b4d5e6f8"
# }
```

### 2. send_email_from_template

Send an email using a predefined template.

**Parameters:**
- `template_name` (str): Template filename without .html
- `to` (str | list): Recipient email(s)
- `subject` (str): Email subject
- `variables` (dict): Template variables
- `cc` (str | list, optional): CC recipients
- `bcc` (str | list, optional): BCC recipients

**Example:**
```python
from app.tools.email_tools import send_email_from_template

result = await send_email_from_template(
    template_name="meeting_summary",
    to="team@company.com",
    subject="Weekly Meeting Summary - Dec 26, 2025",
    variables={
        "meeting_date": "December 26, 2025",
        "meeting_time": "10:00 AM",
        "duration": "1 hour",
        "participants": ["Alice", "Bob", "Charlie"],
        "action_items": [
            {
                "description": "Review Q4 report",
                "owner": "Alice",
                "due_date": "Jan 5"
            },
            {
                "description": "Update documentation",
                "owner": "Bob",
                "due_date": "Jan 3"
            }
        ],
        "decisions": ["Approved new feature roadmap", "Budget increase approved"]
    }
)
```

### 3. create_email_draft

Create a draft without sending.

**Parameters:**
- `to` (str | list): Recipient email(s)
- `subject` (str): Email subject
- `message` (str): Plain text body
- `html_body` (str, optional): HTML body

**Example:**
```python
from app.tools.email_tools import create_email_draft

result = await create_email_draft(
    to="client@example.com",
    subject="Proposal Draft",
    message="Please find our proposal below...",
    html_body="<p>Please find our <strong>proposal</strong> below...</p>"
)

# Returns:
# {
#     "status": "success",
#     "draft_id": "r-123456789",
#     "message_id": "18c5f2a3b4d5e6f7"
# }
```

### 4. search_emails

Search emails using Gmail query syntax.

**Parameters:**
- `query` (str): Gmail search query
- `max_results` (int, optional): Max results (default: 10)
- `include_body` (bool, optional): Include full body (default: False)

**Query Examples:**
- `"from:user@example.com"` - From specific sender
- `"subject:meeting"` - Subject contains "meeting"
- `"is:unread"` - Unread emails
- `"is:starred"` - Starred emails
- `"has:attachment"` - Has attachments
- `"after:2025/12/01"` - After specific date
- `"from:boss@company.com is:unread"` - Combined filters

**Example:**
```python
from app.tools.email_tools import search_emails

result = await search_emails(
    query="from:boss@company.com is:unread",
    max_results=20,
    include_body=True
)

# Returns:
# {
#     "status": "success",
#     "count": 15,
#     "emails": [
#         {
#             "id": "18c5f2a3b4d5e6f7",
#             "thread_id": "18c5f2a3b4d5e6f8",
#             "subject": "Q4 Report",
#             "from": "boss@company.com",
#             "to": "me@company.com",
#             "date": "Thu, 26 Dec 2025 10:30:00 -0500",
#             "snippet": "Please review the attached Q4 report...",
#             "body_plain": "Full plain text...",
#             "body_html": "<html>Full HTML...</html>"
#         },
#         ...
#     ]
# }
```

### 5. get_email

Retrieve a specific email by ID.

**Parameters:**
- `message_id` (str): Gmail message ID
- `format` (str, optional): "minimal", "full", or "metadata" (default: "full")

**Example:**
```python
from app.tools.email_tools import get_email

result = await get_email(
    message_id="18c5f2a3b4d5e6f7",
    format="full"
)

# Returns:
# {
#     "status": "success",
#     "email": {
#         "id": "18c5f2a3b4d5e6f7",
#         "subject": "Project Update",
#         "from": "colleague@company.com",
#         "to": "me@company.com",
#         "date_parsed": "2025-12-26T10:30:00-05:00",
#         "body_plain": "Full text...",
#         "body_html": "<html>...</html>"
#     }
# }
```

### 6. list_recent_emails

List recent emails with filters.

**Parameters:**
- `max_results` (int, optional): Max results (default: 10)
- `filter` (str, optional): "all", "unread", "starred", "inbox" (default: "all")
- `include_body` (bool, optional): Include body (default: False)

**Example:**
```python
from app.tools.email_tools import list_recent_emails

result = await list_recent_emails(
    max_results=50,
    filter="unread",
    include_body=False
)

# Returns:
# {
#     "status": "success",
#     "count": 35,
#     "emails": [...]
# }
```

### 7. get_email_thread

Get entire conversation thread.

**Parameters:**
- `thread_id` (str): Gmail thread ID

**Example:**
```python
from app.tools.email_tools import get_email_thread

result = await get_email_thread(
    thread_id="18c5f2a3b4d5e6f8"
)

# Returns:
# {
#     "status": "success",
#     "thread_id": "18c5f2a3b4d5e6f8",
#     "message_count": 5,
#     "messages": [
#         # All messages in chronological order with full content
#     ]
# }
```

## Email Template System

### Template Structure

Templates use Jinja2 syntax and extend `base.html`:

```html
{% extends "base.html" %}

{% block header_title %}Your Title{% endblock %}

{% block content %}
<h2>{{ heading }}</h2>
<p>{{ message }}</p>

{% if details %}
<div>{{ details }}</div>
{% endif %}
{% endblock %}
```

### Available Templates

#### 1. notification.html
Variables:
- `title` - Email title
- `heading` - Main heading
- `message` - Main message content
- `details` - Optional details box
- `action_url` - Optional button URL
- `action_text` - Button text (default: "View Details")
- `additional_info` - Optional footer info

#### 2. report.html
Variables:
- `report_title` - Report title
- `generated_date` - Generation date
- `period` - Report period
- `summary` - Executive summary
- `metrics` - List of `{name, value}` dicts
- `data_sections` - List of `{title, content, items}` dicts
- `notes` - Optional notes

#### 3. meeting_summary.html
Variables:
- `meeting_date` - Meeting date
- `meeting_time` - Meeting time
- `duration` - Meeting duration
- `location` - Optional location
- `participants` - List of participant names
- `agenda` - List of agenda items
- `discussion_points` - List of `{topic, summary}` dicts
- `action_items` - List of `{description, owner, due_date}` dicts
- `decisions` - List of decision strings
- `next_meeting` - Next meeting info
- `notes` - Additional notes

### Creating Custom Templates

1. Create a new `.html` file in `app/templates/email/`
2. Extend `base.html`
3. Use Jinja2 syntax for variables
4. Call with `send_email_from_template()`

Example:
```html
{% extends "base.html" %}

{% block header_title %}Custom Template{% endblock %}

{% block content %}
<h2>Hello {{ user_name }}</h2>
<p>{{ custom_message }}</p>
{% endblock %}
```

## Tool Registry

The `EMAIL_TOOLS` list in `email_tools.py` contains all tool metadata:

```python
EMAIL_TOOLS = [
    {
        "name": "send_email",
        "description": "Send an email via Gmail...",
        "parameters": {...},
        "coroutine": send_email
    },
    # ... 6 more tools
]
```

This registry can be used to:
- Register tools with agents
- Generate documentation
- Expose tools via API
- Integrate with LangGraph or other frameworks

## Error Handling

All tools return consistent error responses:

```python
# Success
{
    "status": "success",
    "message_id": "...",
    ...
}

# Error
{
    "status": "error",
    "error": "Error message description"
}
```

Errors are logged with Python logging:
```python
import logging
logger = logging.getLogger(__name__)
```

## Dependencies

All required dependencies are already in `requirements.txt`:
- `google-api-python-client==2.116.0`
- `google-auth-httplib2==0.2.0`
- `google-auth-oauthlib==1.2.0`
- `jinja2==3.1.3`

## Usage in Agents

### Option 1: Direct Function Calls

```python
from app.tools.email_tools import send_email, search_emails

# In your agent code
async def handle_email_task(self, task: str):
    if "send email" in task.lower():
        result = await send_email(
            to="user@example.com",
            subject="Task Complete",
            message="Your task is complete"
        )
        return result
```

### Option 2: Tool Registry

```python
from app.tools.email_tools import EMAIL_TOOLS

# Get all available email tools
for tool in EMAIL_TOOLS:
    print(f"Tool: {tool['name']}")
    print(f"Description: {tool['description']}")
    print(f"Parameters: {tool['parameters']}")

    # Call the tool
    result = await tool['coroutine'](**params)
```

### Option 3: Future Integration

The tools are designed to integrate with:
- LangGraph tool calling
- OpenAI function calling
- Anthropic tool use
- Custom agent frameworks

## Testing

To test the Gmail tools:

```python
import asyncio
from app.tools.email_tools import send_email, search_emails

async def test_gmail():
    # Test sending
    result = await send_email(
        to="test@example.com",
        subject="Test Email",
        message="This is a test"
    )
    print(f"Send result: {result}")

    # Test searching
    result = await search_emails(
        query="is:unread",
        max_results=5
    )
    print(f"Search result: {result}")

# Run test
asyncio.run(test_gmail())
```

## Security Notes

1. **OAuth Tokens**: Keep `gmail_token.json` secure and in `.gitignore`
2. **Credentials**: Never commit `gmail_credentials.json` to version control
3. **Email Validation**: All email addresses are validated before sending
4. **File Attachments**: Be cautious with file paths from user input
5. **Rate Limits**: Gmail API has rate limits; implement retry logic if needed

## Gmail API Scopes

Current scope: `https://mail.google.com/`
- Full access to read, send, delete emails
- Can be restricted to more limited scopes if needed:
  - `gmail.send` - Send only
  - `gmail.readonly` - Read only
  - `gmail.compose` - Create drafts only

## Troubleshooting

### OAuth Flow Issues
- Ensure `gmail_credentials.json` is in the correct location
- Check that the OAuth app is configured in Google Cloud Console
- Verify redirect URIs include `http://localhost:*`

### Import Errors
```python
# Make sure you're importing from the correct path
from app.tools.email_tools import send_email
from app.services.gmail_service import get_gmail_service
```

### Template Not Found
- Check template name (without .html extension)
- Verify `EMAIL_TEMPLATES_DIR` in config
- Ensure template exists in `app/templates/email/`

### API Errors
- Check Gmail API is enabled in Google Cloud Console
- Verify credentials have correct scopes
- Check internet connectivity
- Review quota limits in Google Cloud Console

## Next Steps

1. **Agent Integration**: Connect tools to your AI agents
2. **Testing**: Create comprehensive test suite
3. **Rate Limiting**: Add retry logic for API limits
4. **Monitoring**: Add metrics for email operations
5. **Advanced Features**:
   - Email labeling
   - Mark as read/unread
   - Archive/delete operations
   - Calendar integration

## Support

For issues or questions:
1. Check the logs for detailed error messages
2. Verify OAuth credentials are correct
3. Review Gmail API documentation
4. Check Google Cloud Console for API status

## License

This implementation follows the existing codebase patterns and is part of the ECOWAS Summit TWG Support System.
