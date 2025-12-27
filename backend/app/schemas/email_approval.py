"""
Email Approval Schemas

Schemas for email approval workflow requiring human-in-the-loop confirmation.
"""

from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime


class EmailDraft(BaseModel):
    """Email draft for approval."""
    draft_id: str = Field(..., description="Unique identifier for this draft")
    to: List[EmailStr] = Field(..., description="Recipient email addresses")
    subject: str = Field(..., description="Email subject")
    body: str = Field(..., description="Plain text email body")
    html_body: Optional[str] = Field(None, description="HTML email body")
    cc: Optional[List[EmailStr]] = Field(None, description="CC recipients")
    bcc: Optional[List[EmailStr]] = Field(None, description="BCC recipients")
    attachments: Optional[List[str]] = Field(None, description="File paths for attachments")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Draft creation timestamp")
    context: Optional[str] = Field(None, description="Context/reason for this email")


class EmailApprovalRequest(BaseModel):
    """Request for email approval from user."""
    request_id: str = Field(..., description="Unique request identifier")
    draft: EmailDraft = Field(..., description="Email draft awaiting approval")
    message: str = Field(default="Please review and approve this email before sending", description="Request message to user")


class EmailApprovalResponse(BaseModel):
    """User's response to email approval request."""
    request_id: str = Field(..., description="Request identifier being responded to")
    approved: bool = Field(..., description="Whether email is approved for sending")
    modifications: Optional[EmailDraft] = Field(None, description="Modified email draft if user made changes")
    reason: Optional[str] = Field(None, description="Reason for approval/rejection")


class EmailApprovalResult(BaseModel):
    """Result after email approval decision."""
    success: bool = Field(..., description="Whether the operation succeeded")
    message: str = Field(..., description="Result message")
    email_sent: bool = Field(default=False, description="Whether email was sent")
    message_id: Optional[str] = Field(None, description="Gmail message ID if sent")
    thread_id: Optional[str] = Field(None, description="Gmail thread ID if sent")
