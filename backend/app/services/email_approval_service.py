"""
Email Approval Service

Manages pending email approvals requiring human-in-the-loop confirmation.
"""

import uuid
from typing import Dict, Optional
from datetime import datetime, timedelta
from app.schemas.email_approval import EmailDraft, EmailApprovalRequest
import logging

logger = logging.getLogger(__name__)


class EmailApprovalService:
    """Service for managing email approval requests."""

    def __init__(self):
        """Initialize the email approval service."""
        # In-memory storage for pending approvals
        # In production, this should be Redis or a database
        self.pending_approvals: Dict[str, EmailApprovalRequest] = {}
        logger.info("Email Approval Service initialized")

    def create_approval_request(
        self,
        to: list,
        subject: str,
        body: str,
        html_body: Optional[str] = None,
        cc: Optional[list] = None,
        bcc: Optional[list] = None,
        attachments: Optional[list] = None,
        context: Optional[str] = None
    ) -> EmailApprovalRequest:
        """
        Create a new email approval request.

        Args:
            to: Recipient email addresses
            subject: Email subject
            body: Plain text body
            html_body: Optional HTML body
            cc: Optional CC recipients
            bcc: Optional BCC recipients
            attachments: Optional file attachments
            context: Optional context about why this email is being sent

        Returns:
            EmailApprovalRequest object
        """
        request_id = str(uuid.uuid4())
        draft_id = str(uuid.uuid4())

        draft = EmailDraft(
            draft_id=draft_id,
            to=to,
            subject=subject,
            body=body,
            html_body=html_body,
            cc=cc,
            bcc=bcc,
            attachments=attachments,
            context=context
        )

        approval_request = EmailApprovalRequest(
            request_id=request_id,
            draft=draft,
            message="Please review and approve this email before sending"
        )

        # Store the pending approval
        self.pending_approvals[request_id] = approval_request

        logger.info(f"Created email approval request {request_id} for draft {draft_id}")
        return approval_request

    def get_approval_request(self, request_id: str) -> Optional[EmailApprovalRequest]:
        """
        Get a pending approval request by ID.

        Args:
            request_id: The request ID

        Returns:
            EmailApprovalRequest if found, None otherwise
        """
        return self.pending_approvals.get(request_id)

    def remove_approval_request(self, request_id: str) -> bool:
        """
        Remove a pending approval request.

        Args:
            request_id: The request ID to remove

        Returns:
            True if removed, False if not found
        """
        if request_id in self.pending_approvals:
            del self.pending_approvals[request_id]
            logger.info(f"Removed approval request {request_id}")
            return True
        return False

    def cleanup_old_requests(self, max_age_hours: int = 24):
        """
        Clean up old approval requests that haven't been responded to.

        Args:
            max_age_hours: Maximum age in hours before cleanup
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
        expired_ids = [
            req_id for req_id, req in self.pending_approvals.items()
            if req.draft.created_at < cutoff_time
        ]

        for req_id in expired_ids:
            del self.pending_approvals[req_id]
            logger.info(f"Cleaned up expired approval request {req_id}")

        if expired_ids:
            logger.info(f"Cleaned up {len(expired_ids)} expired approval requests")


# Singleton instance
_email_approval_service: Optional[EmailApprovalService] = None


def get_email_approval_service() -> EmailApprovalService:
    """
    Get or create the email approval service singleton.

    Returns:
        EmailApprovalService instance
    """
    global _email_approval_service
    if _email_approval_service is None:
        _email_approval_service = EmailApprovalService()
    return _email_approval_service
