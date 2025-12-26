# Gmail Tools Setup Guide

## ✅ Setup Status

Your Gmail tools are now configured and ready to test! Here's what has been set up:

### Files Created
- ✅ `credentials/gmail_credentials.json` - OAuth credentials configured
- ✅ `app/services/gmail_service.py` - Gmail service layer
- ✅ `app/tools/email_tools.py` - 7 email tools
- ✅ `app/templates/email/` - 4 HTML email templates
- ✅ `test_gmail.py` - Test script for verification
- ✅ `.gitignore` - Updated to exclude credentials

### Configuration
- ✅ Gmail OAuth credentials added
- ✅ Config.py updated with Gmail settings
- ✅ All dependencies already installed

## 🚀 Quick Start

### Step 1: Test the Gmail Connection

Run the test script to complete OAuth authorization:

```bash
cd backend
python test_gmail.py
```

This will:
1. Open your browser for Gmail authorization
2. Create `gmail_token.json` automatically
3. Test listing your recent emails
4. Optionally send a test email to yourself

### Step 2: Authorize the Application

When the browser opens:
1. Sign in with your Gmail account
2. Click "Allow" to grant permissions
3. The browser will show "Authentication successful"
4. Return to the terminal

### Step 3: Verify Success

You should see:
```
✅ SUCCESS! Gmail connection established.
Found X recent emails in inbox:
  1. [Email subject]
     From: [sender]
     Date: [date]
```

## 📧 Using the Gmail Tools

### Send a Simple Email

```python
import asyncio
from app.tools.email_tools import send_email

async def send_test():
    result = await send_email(
        to="recipient@example.com",
        subject="Hello from AI Agent",
        message="This is a test email",
        html_body="<h1>Hello!</h1><p>This is a <strong>test</strong> email.</p>"
    )
    print(result)

asyncio.run(send_test())
```

### Search Your Emails

```python
from app.tools.email_tools import search_emails

async def search_unread():
    result = await search_emails(
        query="is:unread",
        max_results=10,
        include_body=False
    )

    print(f"Found {result['count']} unread emails")
    for email in result['emails']:
        print(f"- {email['subject']} from {email['from']}")

asyncio.run(search_unread())
```

### Send Email from Template

```python
from app.tools.email_tools import send_email_from_template

async def send_meeting_summary():
    result = await send_email_from_template(
        template_name="meeting_summary",
        to="team@company.com",
        subject="Team Meeting Summary",
        variables={
            "meeting_date": "December 26, 2025",
            "participants": ["Alice", "Bob", "Charlie"],
            "action_items": [
                {
                    "description": "Review Q4 report",
                    "owner": "Alice",
                    "due_date": "Jan 5"
                }
            ]
        }
    )
    print(result)

asyncio.run(send_meeting_summary())
```

## 📚 Available Tools

### 1. **send_email**
Send emails with HTML, attachments, CC/BCC

### 2. **send_email_from_template**
Send using predefined templates

### 3. **create_email_draft**
Create drafts without sending

### 4. **search_emails**
Search with Gmail query syntax
- `"from:user@example.com"`
- `"subject:meeting"`
- `"is:unread"`
- `"has:attachment"`

### 5. **get_email**
Get specific email by ID

### 6. **list_recent_emails**
List recent with filters (all/unread/starred/inbox)

### 7. **get_email_thread**
Get entire conversation threads

## 📖 Documentation

Detailed documentation available in:
- `app/tools/EMAIL_TOOLS_README.md` - Complete tool reference
- `examples/gmail_usage_examples.py` - 11 practical examples

## 🔧 Configuration

Configuration is in `app/core/config.py`:

```python
# Gmail API Configuration
GMAIL_CREDENTIALS_FILE = "./credentials/gmail_credentials.json"
GMAIL_TOKEN_FILE = "./credentials/gmail_token.json"
GMAIL_SCOPES = ["https://mail.google.com/"]

# Email Templates
EMAIL_TEMPLATES_DIR = "./app/templates/email"
```

You can override these in your `.env` file:

```bash
GMAIL_CREDENTIALS_FILE=./credentials/gmail_credentials.json
GMAIL_TOKEN_FILE=./credentials/gmail_token.json
EMAIL_TEMPLATES_DIR=./app/templates/email
```

## 🔐 Security

- ✅ Credentials files are in `.gitignore`
- ✅ OAuth tokens auto-refresh
- ✅ Email addresses are validated
- ⚠️ Never commit `gmail_credentials.json` or `gmail_token.json`

## 🎨 Email Templates

4 professional HTML templates included:

### base.html
Base template with header/footer styling

### notification.html
For notifications and alerts
```python
variables = {
    "title": "Alert",
    "heading": "Important Update",
    "message": "Your attention is required",
    "action_url": "https://example.com/action",
    "action_text": "Take Action"
}
```

### report.html
For formatted reports with metrics
```python
variables = {
    "report_title": "Monthly Report",
    "metrics": [
        {"name": "Revenue", "value": "$1.2M"},
        {"name": "Users", "value": "450"}
    ]
}
```

### meeting_summary.html
For detailed meeting summaries
```python
variables = {
    "meeting_date": "Dec 26, 2025",
    "participants": ["Alice", "Bob"],
    "action_items": [
        {"description": "Task", "owner": "Alice", "due_date": "Jan 5"}
    ]
}
```

## 🔍 Gmail Search Query Examples

```python
# From specific sender
"from:boss@company.com"

# Unread emails
"is:unread"

# With attachments
"has:attachment"

# Subject contains text
"subject:meeting"

# After date
"after:2025/12/01"

# Combined filters
"from:boss@company.com is:unread has:attachment"
```

## 🐛 Troubleshooting

### OAuth Flow Fails
1. Check `gmail_credentials.json` exists in `backend/credentials/`
2. Verify credentials are correct
3. Ensure Gmail API is enabled in Google Cloud Console
4. Check redirect URIs include `http://localhost`

### Import Errors
```python
# Use correct import paths
from app.tools.email_tools import send_email
from app.services.gmail_service import get_gmail_service
```

### Template Not Found
1. Check template name (without .html)
2. Verify template exists in `app/templates/email/`
3. Check `EMAIL_TEMPLATES_DIR` in config

### API Quota Exceeded
- Gmail API has rate limits
- Implement exponential backoff for retries
- Monitor usage in Google Cloud Console

## 📊 Tool Registry

All tools are registered in `EMAIL_TOOLS` list:

```python
from app.tools.email_tools import EMAIL_TOOLS

# List all tools
for tool in EMAIL_TOOLS:
    print(f"{tool['name']}: {tool['description']}")

# Call a tool
tool = EMAIL_TOOLS[0]  # send_email
result = await tool['coroutine'](
    to="user@example.com",
    subject="Test",
    message="Hello"
)
```

## 🎯 Integration with AI Agents

The tools can be integrated with your agents:

```python
from app.tools.email_tools import EMAIL_TOOLS

class EmailAgent:
    def __init__(self):
        self.tools = {tool['name']: tool['coroutine'] for tool in EMAIL_TOOLS}

    async def handle_request(self, action: str, params: dict):
        if action in self.tools:
            return await self.tools[action](**params)
```

## ✨ Next Steps

1. ✅ Run `python test_gmail.py` to complete OAuth
2. ✅ Test sending an email to yourself
3. ✅ Try searching your emails
4. ✅ Experiment with templates
5. ✅ Integrate with your AI agents

## 📞 Support

Check these files for help:
- `EMAIL_TOOLS_README.md` - Comprehensive documentation
- `examples/gmail_usage_examples.py` - Code examples
- `test_gmail.py` - Testing and verification

## 🎉 You're Ready!

Your Gmail tools are fully configured and ready to use. Run the test script to get started:

```bash
cd backend
python test_gmail.py
```

Happy emailing! 📧
