"""
Resend Service Layer

Provides integration with Resend API for sending emails.
Replaces GmailService for outbound communication.
"""

import os
import logging
from typing import List, Dict, Any, Optional, Union
import resend
from app.core.config import settings

logger = logging.getLogger(__name__)

class ResendService:
    """Resend service for sending emails."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        default_from: Optional[str] = None
    ):
        """
        Initialize Resend service.

        Args:
            api_key: Resend API key (defaults to settings.RESEND_API_KEY)
            default_from: Default sender email (defaults to settings.EMAIL_FROM)
        """
        self.api_key = api_key or os.getenv("RESEND_API_KEY")
        # Use verified domain from settings
        self.default_from = default_from or getattr(settings, "EMAIL_FROM", os.getenv("EMAILS_FROM_EMAIL", "onboarding@resend.dev"))
        
        if not self.api_key:
            logger.warning("RESEND_API_KEY not found in environment")
        
        resend.api_key = self.api_key
        logger.info(f"Resend service initialized (sender: {self.default_from})")

    def send_message(
        self,
        to: Union[str, List[str]],
        subject: str,
        body: str,
        html_body: Optional[str] = None,
        cc: Optional[Union[str, List[str]]] = None,
        bcc: Optional[Union[str, List[str]]] = None,
        attachments: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Send an email message via Resend.

        Args:
            to: Recipient email address(es)
            subject: Email subject
            body: Plain text email body
            html_body: Optional HTML email body
            cc: Optional CC recipient(s)
            bcc: Optional BCC recipient(s)
            attachments: Optional list of file paths to attach

        Returns:
            Dictionary with message ID and status
        """
        try:
            # Convert single recipients to lists
            to_list = [to] if isinstance(to, str) else to
            cc_list = ([cc] if isinstance(cc, str) else cc) if cc else []
            bcc_list = ([bcc] if isinstance(bcc, str) else bcc) if bcc else []

            # SAFETY: reroute everything to the test inbox if EMAIL_TEST_REDIRECT_TO is set.
            from app.utils.email_guard import redirect_recipients, tag_subject
            to_list, cc_list, bcc_list, _redirected, _orig = redirect_recipients(to_list, cc_list, bcc_list)
            if _redirected:
                subject = tag_subject(subject, _orig)

            # Prepare attachment objects if any
            # Resend expects list of dicts: {"filename": "x.pdf", "content": [buffer]} or path?
            # Looking at Resend python docs, it supports 'attachments' param.
            # Local files usually need to be read.
            # Actually valid format is:
            # { "filename": "invoice.pdf", "content": list(bytes_content) } or "path"? 
            # SDK usually handles paths if passed correctly? 
            # The SDK expects 'content' as list of integers (bytes) usually.
            
            prepared_attachments = []
            if attachments:
                for path in attachments:
                    if os.path.exists(path):
                        with open(path, 'rb') as f:
                            content_bytes = list(f.read()) # Resend expects list of ints
                            prepared_attachments.append({
                                "filename": os.path.basename(path),
                                "content": content_bytes
                            })
                    else:
                        logger.warning(f"Attachment not found: {path}")

            params = {
                "from": self.default_from,
                "to": to_list,
                "subject": subject,
                "text": body,
            }

            if html_body:
                params["html"] = html_body
                
            if cc_list:
                params["cc"] = cc_list
                
            if bcc_list:
                params["bcc"] = bcc_list
                
            if prepared_attachments:
                params["attachments"] = prepared_attachments

            logger.info(f"Sending email via Resend to {to_list}")
            response = resend.Emails.send(params)
            
            # Response is typically a dict like {'id': 're_123...'}
            logger.info(f"Resend response: {response}")
            
            return {
                "status": "success", 
                "message_id": response.get("id"),
                "provider": "resend"
            }

        except Exception as error:
            logger.error(f"Error sending email via Resend: {error}")
            raise error

# Singleton instance
_resend_service: Optional[ResendService] = None

def get_resend_service() -> ResendService:
    """Get or create ResendService singleton."""
    global _resend_service
    if _resend_service is None:
        _resend_service = ResendService()
    return _resend_service
