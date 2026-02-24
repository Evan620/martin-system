"""
Email Tools for AI Agents

Provides email integration tools for sending emails and creating drafts.
All emails are sent via Resend with approval workflow.
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

from app.services.email_approval_service import get_email_approval_service

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
    context: Optional[str] = None,
    pillar_name: Optional[str] = None,
    use_template_wrapper: bool = True
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
        pillar_name: Optional TWG pillar name for branding
        use_template_wrapper: Whether to wrap HTML in beautiful ECOWAS template (default: True)

    Returns:
        Dictionary with status, approval_request_id, and preview details

    Example:
        result = await send_email(
            to="user@example.com",
            subject="Test Email",
            message="Plain text content",
            html_body="<h1>HTML Content</h1>",
            context="Monthly report to stakeholder",
            pillar_name="Energy"
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

        # Convert to lists if single strings or None
        to_list = [to] if isinstance(to, str) else to
        cc_list = [cc] if isinstance(cc, str) and cc else (cc or None)
        bcc_list = [bcc] if isinstance(bcc, str) and bcc else (bcc or None)

        # Handle flexible attachments input (string, list, or None)
        attachments_list = []
        if attachments:
            if isinstance(attachments, str):
                attachments_list = [attachments] if attachments.strip() else []
            elif isinstance(attachments, list):
                attachments_list = attachments
        
        # Override with sanitized list
        attachments = attachments_list

        # Wrap content in beautiful template if wrapper is enabled
        if use_template_wrapper:
            try:
                from app.utils.email_templates import wrap_email_content
                import html

                # Determine content to wrap
                content_to_wrap = html_body
                if not content_to_wrap and message:
                    # Convert plain text to simple HTML
                    # Escape text to prevent HTML injection, then replace newlines
                    escaped_msg = html.escape(message)
                    content_to_wrap = f"<div style='font-family: inherit; white-space: pre-wrap;'>{escaped_msg}</div>"
                
                if content_to_wrap:
                    # Wrap the content in the beautiful ECOWAS template
                    html_body = wrap_email_content(
                        content=content_to_wrap,
                        pillar_name=pillar_name,
                        ai_generated=True  # Mark as AI-generated
                    )
                    logger.info("Wrapped email content in ECOWAS template")
            except Exception as e:
                logger.warning(f"Failed to wrap email in template: {e}. Using original content.")

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
            "message": f"Email draft created (Request ID: {approval_request.request_id}). Please review and approve before sending.",
            "draft": {
                "draft_id": approval_request.draft.draft_id,  # REQUIRED for modifications validation
                "to": to_list,
                "cc": cc_list,
                "bcc": bcc_list,
                "subject": subject,
                "body": message,
                "html_body": html_body,
                "attachments": attachments,
                "created_at": approval_request.draft.created_at.isoformat() if approval_request.draft.created_at else None
            },
            "preview": {
                "to": ", ".join(to_list),
                "cc": ", ".join(cc_list) if cc_list else None,
                "subject": subject,
                "body_preview": message[:200] + "..." if len(message) > 200 else message
            }
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
    html_body: Optional[str] = None,
    pillar_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create an email draft for approval (uses Resend approval workflow).
    
    This is now an alias for send_email since all emails go through approval.

    Args:
        to: Recipient email address(es)
        subject: Email subject line
        message: Plain text email body
        html_body: Optional HTML formatted email body
        pillar_name: Optional TWG pillar name for branding

    Returns:
        Dictionary with status, draft_id (approval_request_id), and message

    Example:
        result = await create_email_draft(
            to="user@example.com",
            subject="Draft Email",
            message="This is a draft",
            pillar_name="Energy"
        )
    """
    # Simply call send_email - it creates an approval request (draft)
    return await send_email(
        to=to,
        subject=subject,
        message=message,
        html_body=html_body,
        pillar_name=pillar_name,
        context="Email draft created by AI agent"
    )


# =============================================================================
# Email Retrieval Tools (DISABLED - Gmail dependency removed)
# =============================================================================
# 
# NOTE: These functions are disabled because they depend on Gmail API.
# If email search/retrieval is needed, implement using Resend or another service.
#
# async def search_emails(...) - DISABLED
# async def get_email(...) - DISABLED  
# async def list_recent_emails(...) - DISABLED
# async def get_email_thread(...) - DISABLED


# =============================================================================
# Tools Registry
# =============================================================================

EMAIL_TOOLS = [
    {
        "name": "send_email",
        "description": "Send a beautifully formatted email via Resend (triggers approval workflow). Emails are automatically wrapped in professional ECOWAS branding with AI badge. Supports HTML, CC/BCC, and attachments.",
        "parameters": {
            "to": "Recipient email address(es) - string or list",
            "subject": "Email subject line",
            "message": "Plain text email body",
            "html_body": "Optional HTML formatted email body (will be wrapped in ECOWAS template)",
            "cc": "Optional CC recipient(s)",
            "bcc": "Optional BCC recipient(s)",
            "attachments": "Optional list of file paths to attach",
            "pillar_name": "Optional TWG pillar name for branding (e.g., 'Energy', 'Agriculture')"
        },
        "coroutine": send_email
    },
    {
        "name": "create_email_draft",
        "description": "Create an email draft for human approval (Alias for send_email). Use this when you want to explicitly state you are drafting.",
        "parameters": {
            "to": "Recipient email address(es) - string or list",
            "subject": "Email subject line",
            "message": "Plain text email body",
            "html_body": "Optional HTML formatted email body",
            "pillar_name": "Optional TWG pillar name for branding"
        },
        "coroutine": create_email_draft
    }
]
