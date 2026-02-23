"""
Organization Invitation Schema

Used by administrators to invite external organizations to join TWGs.
"""

from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
from app.models.models import OrganizationInvitationStatus
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
