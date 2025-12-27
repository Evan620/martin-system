"""
Email Tools for AI Agents

Provides Gmail integration tools for sending emails, creating drafts, and searching messages.
Tools follow the pattern from database_tools.py and knowledge_tools.py.
"""

import os
import re
import base64
import logging
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from email.utils import parsedate_to_datetime
from jinja2 import Environment, FileSystemLoader, TemplateNotFound

from app.services.gmail_service import get_gmail_service
from app.services.email_approval_service import get_email_approval_service
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

# Email template configuration
EMAIL_TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), '..', 'templates', 'email')


# =============================================================================
# Utility Functions
# =============================================================================

def validate_email_addresses(emails: Union[str, List[str]]) -> bool:
    """
    Validate email address format.

    Args:
        emails: Single email or list of emails

    Returns:
        True if all emails are valid
    """
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    email_list = [emails] if isinstance(emails, str) else emails

    for email in email_list:
        if not re.match(email_pattern, email.strip()):
            logger.warning(f"Invalid email address: {email}")
            return False
    return True


def parse_email_body(message: Dict[str, Any]) -> Dict[str, Optional[str]]:
    """
    Parse email body from Gmail message.

    Args:
        message: Gmail message object

    Returns:
        Dictionary with 'plain' and 'html' body parts
    """
    result = {'plain': None, 'html': None}

    def get_body_parts(payload):
        """Recursively extract body parts."""
        if 'body' in payload and 'data' in payload['body']:
            data = payload['body']['data']
            decoded = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')

            mime_type = payload.get('mimeType', '')
            if mime_type == 'text/plain':
                result['plain'] = decoded
            elif mime_type == 'text/html':
                result['html'] = decoded

        if 'parts' in payload:
            for part in payload['parts']:
                get_body_parts(part)

    if 'payload' in message:
        get_body_parts(message['payload'])

    return result


def format_email_response(message: Dict[str, Any], include_body: bool = False) -> Dict[str, Any]:
    """
    Format Gmail message into standardized response.

    Args:
        message: Gmail message object
        include_body: Whether to include full body content

    Returns:
        Formatted email data dictionary
    """
    # Extract headers
    headers = {h['name']: h['value'] for h in message.get('payload', {}).get('headers', [])}

    formatted = {
        'id': message.get('id'),
        'thread_id': message.get('threadId'),
        'label_ids': message.get('labelIds', []),
        'snippet': message.get('snippet', ''),
        'subject': headers.get('Subject', ''),
        'from': headers.get('From', ''),
        'to': headers.get('To', ''),
        'cc': headers.get('Cc'),
        'date': headers.get('Date', ''),
        'internal_date': message.get('internalDate')
    }

    # Parse date
    if formatted['date']:
        try:
            formatted['date_parsed'] = parsedate_to_datetime(formatted['date']).isoformat()
        except:
            formatted['date_parsed'] = None

    # Include body if requested
    if include_body:
        body_parts = parse_email_body(message)
        formatted['body_plain'] = body_parts['plain']
        formatted['body_html'] = body_parts['html']

    return formatted


def load_email_template(template_name: str, variables: Dict[str, Any]) -> str:
    """
    Load and render email template with variables.

    Args:
        template_name: Name of the template file (without .html extension)
        variables: Dictionary of variables to substitute

    Returns:
        Rendered HTML template

    Raises:
        TemplateNotFound: If template doesn't exist
    """
    try:
        env = Environment(loader=FileSystemLoader(EMAIL_TEMPLATES_DIR))
        template = env.get_template(f"{template_name}.html")
        rendered = template.render(**variables)
        logger.info(f"Rendered template: {template_name}")
        return rendered
    except TemplateNotFound:
        logger.error(f"Template not found: {template_name}")
        raise
    except Exception as error:
        logger.error(f"Error rendering template {template_name}: {error}")
        raise


# =============================================================================
# Email Sending Tools
# =============================================================================

async def send_email(
    to: Union[str, List[str]],
    subject: str,
    message: str,
    html_body: Optional[str] = None,
    cc: Optional[Union[str, List[str]]] = None,
    bcc: Optional[Union[str, List[str]]] = None,
    attachments: Optional[List[str]] = None,
    context: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create an email approval request (Human-in-the-Loop).

    This function creates an approval request instead of sending directly.
    The user must review and approve the email before it's sent.

    Args:
        to: Recipient email address(es)
        subject: Email subject line
        message: Plain text email body
        html_body: Optional HTML formatted email body
        cc: Optional CC recipient(s)
        bcc: Optional BCC recipient(s)
        attachments: Optional list of file paths to attach
        context: Optional context about why this email is being sent

    Returns:
        Dictionary with status, approval_request_id, and preview details

    Example:
        result = await send_email(
            to="user@example.com",
            subject="Test Email",
            message="Plain text content",
            html_body="<h1>HTML Content</h1>",
            context="Monthly report to stakeholder"
        )
    """
    try:
        # Validate email addresses
        if not validate_email_addresses(to):
            return {"status": "error", "error": "Invalid recipient email address"}

        if cc and not validate_email_addresses(cc):
            return {"status": "error", "error": "Invalid CC email address"}

        if bcc and not validate_email_addresses(bcc):
            return {"status": "error", "error": "Invalid BCC email address"}

        # Convert to lists if single strings
        to_list = [to] if isinstance(to, str) else to
        cc_list = [cc] if isinstance(cc, str) and cc else (cc or None)
        bcc_list = [bcc] if isinstance(bcc, str) and bcc else (bcc or None)

        # Get approval service
        approval_service = get_email_approval_service()

        # Create approval request
        approval_request = approval_service.create_approval_request(
            to=to_list,
            subject=subject,
            body=message,
            html_body=html_body,
            cc=cc_list,
            bcc=bcc_list,
            attachments=attachments,
            context=context
        )

        logger.info(f"Email approval request created: {approval_request.request_id}")

        # Return approval request details
        return {
            "status": "approval_required",
            "approval_request_id": approval_request.request_id,
            "draft_id": approval_request.draft.draft_id,
            "to": to_list,
            "subject": subject,
            "message": "Email draft created. Please review and approve before sending.",
            "preview": {
                "to": ", ".join(to_list),
                "cc": ", ".join(cc_list) if cc_list else None,
                "subject": subject,
                "body_preview": message[:200] + "..." if len(message) > 200 else message
            }
        }

    except HttpError as error:
        logger.error(f"Gmail API error: {error}")
        return {
            "status": "error",
            "error": f"Gmail API error: {error.reason if hasattr(error, 'reason') else str(error)}"
        }
    except Exception as error:
        logger.error(f"Error sending email: {error}")
        return {"status": "error", "error": str(error)}


async def send_email_from_template(
    template_name: str,
    to: Union[str, List[str]],
    subject: str,
    variables: Dict[str, Any],
    cc: Optional[Union[str, List[str]]] = None,
    bcc: Optional[Union[str, List[str]]] = None
) -> Dict[str, Any]:
    """
    Send an email using a predefined template.

    Args:
        template_name: Name of the template file (without .html extension)
        to: Recipient email address(es)
        subject: Email subject line
        variables: Dictionary of variables to substitute in template
        cc: Optional CC recipient(s)
        bcc: Optional BCC recipient(s)

    Returns:
        Dictionary with status, message_id, and thread_id

    Example:
        result = await send_email_from_template(
            template_name="meeting_summary",
            to="team@company.com",
            subject="Weekly Meeting Summary",
            variables={
                "meeting_date": "2025-12-26",
                "action_items": [...],
                "participants": [...]
            }
        )
    """
    try:
        # Load and render template
        html_body = load_email_template(template_name, variables)

        # Generate plain text version (simple HTML stripping)
        import re
        plain_text = re.sub('<[^<]+?>', '', html_body)

        # Send email
        return await send_email(
            to=to,
            subject=subject,
            message=plain_text,
            html_body=html_body,
            cc=cc,
            bcc=bcc
        )

    except TemplateNotFound:
        logger.error(f"Template not found: {template_name}")
        return {"status": "error", "error": f"Template '{template_name}' not found"}
    except Exception as error:
        logger.error(f"Error sending email from template: {error}")
        return {"status": "error", "error": str(error)}


async def create_email_draft(
    to: Union[str, List[str]],
    subject: str,
    message: str,
    html_body: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create an email draft in Gmail without sending.

    Args:
        to: Recipient email address(es)
        subject: Email subject line
        message: Plain text email body
        html_body: Optional HTML formatted email body

    Returns:
        Dictionary with status, draft_id, and message_id

    Example:
        result = await create_email_draft(
            to="user@example.com",
            subject="Draft Email",
            message="This is a draft"
        )
    """
    try:
        # Validate email addresses
        if not validate_email_addresses(to):
            return {"status": "error", "error": "Invalid recipient email address"}

        # Get Gmail service
        gmail = get_gmail_service()

        # Create draft
        result = gmail.create_draft(
            to=to,
            subject=subject,
            body=message,
            html_body=html_body
        )

        logger.info(f"Draft created successfully for {to}")
        return {
            "status": "success",
            "draft_id": result['draft_id'],
            "message_id": result['message_id']
        }

    except HttpError as error:
        logger.error(f"Gmail API error: {error}")
        return {
            "status": "error",
            "error": f"Gmail API error: {error.reason if hasattr(error, 'reason') else str(error)}"
        }
    except Exception as error:
        logger.error(f"Error creating draft: {error}")
        return {"status": "error", "error": str(error)}


# =============================================================================
# Email Retrieval Tools
# =============================================================================

async def search_emails(
    query: str,
    max_results: int = 10,
    include_body: bool = False
) -> Dict[str, Any]:
    """
    Search emails using Gmail query syntax.

    Args:
        query: Gmail search query (e.g., 'from:user@example.com is:unread')
        max_results: Maximum number of results to return (default: 10)
        include_body: Whether to include full email body content (default: False)

    Returns:
        Dictionary with status and list of matching emails

    Example:
        result = await search_emails(
            query="from:boss@company.com is:unread",
            max_results=20,
            include_body=True
        )

    Query Examples:
        - "from:user@example.com" - emails from specific sender
        - "subject:meeting" - emails with 'meeting' in subject
        - "is:unread" - unread emails
        - "is:starred" - starred emails
        - "has:attachment" - emails with attachments
        - "after:2025/12/01" - emails after specific date
    """
    try:
        gmail = get_gmail_service()

        # Search for messages
        messages = gmail.search_messages(query=query, max_results=max_results)

        if not messages:
            return {"status": "success", "count": 0, "emails": []}

        # Fetch full details for each message
        emails = []
        for msg in messages:
            try:
                full_message = gmail.get_message(msg['id'])
                formatted = format_email_response(full_message, include_body=include_body)
                emails.append(formatted)
            except Exception as error:
                logger.error(f"Error fetching message {msg['id']}: {error}")

        logger.info(f"Found {len(emails)} emails matching query: {query}")
        return {
            "status": "success",
            "count": len(emails),
            "emails": emails
        }

    except HttpError as error:
        logger.error(f"Gmail API error: {error}")
        return {
            "status": "error",
            "error": f"Gmail API error: {error.reason if hasattr(error, 'reason') else str(error)}"
        }
    except Exception as error:
        logger.error(f"Error searching emails: {error}")
        return {"status": "error", "error": str(error)}


async def get_email(
    message_id: str,
    format: str = "full"
) -> Dict[str, Any]:
    """
    Retrieve a specific email by its message ID.

    Args:
        message_id: Gmail message ID
        format: Message format - 'minimal', 'full', 'metadata' (default: 'full')

    Returns:
        Dictionary with status and email details

    Example:
        result = await get_email(
            message_id="18c5f2a3b4d5e6f7",
            format="full"
        )
    """
    try:
        gmail = get_gmail_service()

        # Get message
        message = gmail.get_message(message_id, format=format)

        # Format response
        formatted = format_email_response(message, include_body=(format == 'full'))

        logger.info(f"Retrieved email: {message_id}")
        return {
            "status": "success",
            "email": formatted
        }

    except HttpError as error:
        logger.error(f"Gmail API error: {error}")
        return {
            "status": "error",
            "error": f"Gmail API error: {error.reason if hasattr(error, 'reason') else str(error)}"
        }
    except Exception as error:
        logger.error(f"Error retrieving email: {error}")
        return {"status": "error", "error": str(error)}


async def list_recent_emails(
    max_results: int = 10,
    filter: str = "all",
    include_body: bool = False
) -> Dict[str, Any]:
    """
    List recent emails with optional filters.

    Args:
        max_results: Maximum number of emails to return (default: 10)
        filter: Filter type - 'all', 'unread', 'starred' (default: 'all')
        include_body: Whether to include full email body content (default: False)

    Returns:
        Dictionary with status and list of recent emails

    Example:
        result = await list_recent_emails(
            max_results=50,
            filter="unread",
            include_body=False
        )
    """
    try:
        gmail = get_gmail_service()

        # Map filter to label IDs
        label_map = {
            'all': None,
            'unread': ['UNREAD'],
            'starred': ['STARRED'],
            'inbox': ['INBOX']
        }

        label_ids = label_map.get(filter.lower())
        if filter.lower() not in label_map:
            return {"status": "error", "error": f"Invalid filter: {filter}. Use 'all', 'unread', 'starred', or 'inbox'"}

        # List messages
        messages = gmail.list_messages(max_results=max_results, label_ids=label_ids)

        if not messages:
            return {"status": "success", "count": 0, "emails": []}

        # Fetch full details for each message
        emails = []
        for msg in messages:
            try:
                full_message = gmail.get_message(msg['id'])
                formatted = format_email_response(full_message, include_body=include_body)
                emails.append(formatted)
            except Exception as error:
                logger.error(f"Error fetching message {msg['id']}: {error}")

        logger.info(f"Listed {len(emails)} recent emails with filter: {filter}")
        return {
            "status": "success",
            "count": len(emails),
            "emails": emails
        }

    except HttpError as error:
        logger.error(f"Gmail API error: {error}")
        return {
            "status": "error",
            "error": f"Gmail API error: {error.reason if hasattr(error, 'reason') else str(error)}"
        }
    except Exception as error:
        logger.error(f"Error listing emails: {error}")
        return {"status": "error", "error": str(error)}


async def get_email_thread(thread_id: str) -> Dict[str, Any]:
    """
    Retrieve an entire email conversation thread.

    Args:
        thread_id: Gmail thread ID

    Returns:
        Dictionary with status, thread info, and all messages

    Example:
        result = await get_email_thread(
            thread_id="18c5f2a3b4d5e6f7"
        )
    """
    try:
        gmail = get_gmail_service()

        # Get thread
        thread = gmail.get_thread(thread_id)

        # Format all messages in the thread
        messages = []
        for msg in thread.get('messages', []):
            formatted = format_email_response(msg, include_body=True)
            messages.append(formatted)

        logger.info(f"Retrieved thread {thread_id} with {len(messages)} messages")
        return {
            "status": "success",
            "thread_id": thread['id'],
            "message_count": len(messages),
            "messages": messages
        }

    except HttpError as error:
        logger.error(f"Gmail API error: {error}")
        return {
            "status": "error",
            "error": f"Gmail API error: {error.reason if hasattr(error, 'reason') else str(error)}"
        }
    except Exception as error:
        logger.error(f"Error retrieving thread: {error}")
        return {"status": "error", "error": str(error)}


# =============================================================================
# Tools Registry
# =============================================================================

EMAIL_TOOLS = [
    {
        "name": "send_email",
        "description": "Send an email via Gmail with support for HTML, CC/BCC, and file attachments",
        "parameters": {
            "to": "Recipient email address(es) - string or list",
            "subject": "Email subject line",
            "message": "Plain text email body",
            "html_body": "Optional HTML formatted email body",
            "cc": "Optional CC recipient(s)",
            "bcc": "Optional BCC recipient(s)",
            "attachments": "Optional list of file paths to attach"
        },
        "coroutine": send_email
    },
    {
        "name": "send_email_from_template",
        "description": "Send an email using a predefined HTML template with variable substitution",
        "parameters": {
            "template_name": "Name of the template file (without .html extension)",
            "to": "Recipient email address(es)",
            "subject": "Email subject line",
            "variables": "Dictionary of variables to substitute in template",
            "cc": "Optional CC recipient(s)",
            "bcc": "Optional BCC recipient(s)"
        },
        "coroutine": send_email_from_template
    },
    {
        "name": "create_email_draft",
        "description": "Create an email draft in Gmail without sending it",
        "parameters": {
            "to": "Recipient email address(es)",
            "subject": "Email subject line",
            "message": "Plain text email body",
            "html_body": "Optional HTML formatted email body"
        },
        "coroutine": create_email_draft
    },
    {
        "name": "search_emails",
        "description": "Search emails using Gmail query syntax (e.g., 'from:user@example.com is:unread')",
        "parameters": {
            "query": "Gmail search query string",
            "max_results": "Maximum number of results to return (default: 10)",
            "include_body": "Whether to include full email body content (default: False)"
        },
        "coroutine": search_emails
    },
    {
        "name": "get_email",
        "description": "Retrieve a specific email by its message ID",
        "parameters": {
            "message_id": "Gmail message ID",
            "format": "Message format - 'minimal', 'full', or 'metadata' (default: 'full')"
        },
        "coroutine": get_email
    },
    {
        "name": "list_recent_emails",
        "description": "List recent emails with optional filters (all/unread/starred/inbox)",
        "parameters": {
            "max_results": "Maximum number of emails to return (default: 10)",
            "filter": "Filter type - 'all', 'unread', 'starred', or 'inbox' (default: 'all')",
            "include_body": "Whether to include full email body content (default: False)"
        },
        "coroutine": list_recent_emails
    },
    {
        "name": "get_email_thread",
        "description": "Retrieve an entire email conversation thread with all messages",
        "parameters": {
            "thread_id": "Gmail thread ID"
        },
        "coroutine": get_email_thread
    }
]
