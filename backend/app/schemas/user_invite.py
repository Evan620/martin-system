"""
User Invitation Schema

Used by administrators to create new user accounts with invite emails.
"""

from pydantic import BaseModel, EmailStr
from typing import Optional
from app.models.models import UserRole
import uuid


class UserInvite(BaseModel):
    """Schema for inviting a new user (Admin only)."""
    email: EmailStr
    full_name: str
    role: UserRole = UserRole.TWG_MEMBER
    organization: Optional[str] = None
    twg_ids: Optional[list[uuid.UUID]] = None
    send_email: bool = True  # Whether to send invite email


class UserInviteResponse(BaseModel):
    """Response after creating an invited user."""
    user_id: uuid.UUID
    email: str
    temporary_password: str  # Only shown once
    invite_sent: bool


class ResendInviteResponse(BaseModel):
    """Response after resending an invite."""
    user_id: uuid.UUID
    email: str
    temporary_password: str
    invite_sent: bool
