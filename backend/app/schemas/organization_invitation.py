"""
Organization Invitation Schema

Used by administrators to invite external organizations to join TWGs.
"""

from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
from app.models.models import OrganizationInvitationStatus, InvitationMessageSender
import uuid


class OrganizationInvitationCreate(BaseModel):
    """Schema for creating a new organization invitation."""
    organization_name: str
    contact_email: EmailStr
    twg_id: uuid.UUID
    custom_message: Optional[str] = None
    send_email: bool = True  # Whether to send invitation email immediately


class OrganizationInvitationUpdate(BaseModel):
    """Schema for updating a pending organization invitation."""
    organization_name: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    twg_id: Optional[uuid.UUID] = None
    custom_message: Optional[str] = None


class OrganizationInvitationResponse(BaseModel):
    """Response schema for a single organization invitation."""
    id: uuid.UUID
    organization_name: str
    contact_email: str
    twg_id: uuid.UUID
    twg_name: Optional[str] = None
    custom_message: Optional[str] = None
    status: OrganizationInvitationStatus
    expires_at: datetime
    sent_at: Optional[datetime] = None
    responded_at: Optional[datetime] = None
    created_by_id: uuid.UUID
    created_by_name: Optional[str] = None
    resend_count: int = 0
    last_resend_at: Optional[datetime] = None
    created_at: datetime
    unread_message_count: int = 0
    has_messages: bool = False

    class Config:
        from_attributes = True


class OrganizationInvitationListResponse(BaseModel):
    """Response schema for paginated list of organization invitations."""
    items: List[OrganizationInvitationResponse]
    total: int
    page: int
    page_size: int
    pages: int


class ResendInvitationResponse(BaseModel):
    """Response after resending an organization invitation."""
    id: uuid.UUID
    organization_name: str
    contact_email: str
    invite_sent: bool
    message: str


class InvitationRespondRequest(BaseModel):
    """Schema for responding to an invitation (public endpoint)."""
    response: str  # "accept" or "decline"


class InvitationRespondResponse(BaseModel):
    """Response after accepting or declining an invitation."""
    id: uuid.UUID
    organization_name: str
    twg_name: str
    status: OrganizationInvitationStatus
    message: str


# --- Message Schemas ---

class InvitationMessageCreate(BaseModel):
    """Schema for creating a new message in an invitation thread."""
    content: str


class InvitationMessageResponse(BaseModel):
    """Response schema for a single invitation message."""
    id: uuid.UUID
    invitation_id: uuid.UUID
    sender_type: InvitationMessageSender
    sender_user_id: Optional[uuid.UUID] = None
    sender_name: str
    content: str
    is_read_by_admin: bool = False
    is_read_by_invitee: bool = False
    created_at: datetime

    # Computed field based on who is viewing
    is_read: bool = False

    class Config:
        from_attributes = True


class InvitationMessageListResponse(BaseModel):
    """Response schema for paginated list of invitation messages."""
    items: List[InvitationMessageResponse]
    total: int
    unread_count: int = 0


class PublicInvitationResponse(BaseModel):
    """Response schema for public invitation details (no auth required)."""
    id: uuid.UUID
    organization_name: str
    twg_name: str
    status: OrganizationInvitationStatus
    expires_at: datetime
    custom_message: Optional[str] = None
    has_messages: bool = False
