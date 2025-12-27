"""
Authentication Pydantic Schemas

Defines request/response schemas for authentication endpoints.
"""

from pydantic import BaseModel, EmailStr, Field, field_validator, ConfigDict
from typing import Optional
from datetime import datetime
import uuid
from app.models.models import UserRole


class UserRegister(BaseModel):
    """Schema for user registration."""
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str = Field(..., min_length=1, max_length=255)
    role: UserRole = UserRole.TWG_MEMBER
    organization: Optional[str] = Field(None, max_length=255)
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
        if not any(c in special_chars for c in v):
            raise ValueError('Password must contain at least one special character')
        return v


class UserLogin(BaseModel):
    """Schema for user login."""
    email: EmailStr
    password: str


class GoogleLogin(BaseModel):
    """Schema for Google login."""
    id_token: str


class Token(BaseModel):
    """Schema for token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenRefresh(BaseModel):
    """Schema for token refresh request."""
    refresh_token: str


class AccessToken(BaseModel):
    """Schema for access token response."""
    access_token: str
    token_type: str = "bearer"


class PasswordChange(BaseModel):
    """Schema for password change."""
    current_password: str
    new_password: str = Field(..., min_length=8)
    
    @field_validator('new_password')
    @classmethod
    def validate_new_password(cls, v):
        """Validate new password strength."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
        if not any(c in special_chars for c in v):
            raise ValueError('Password must contain at least one special character')
        return v


class UserResponse(BaseModel):
    """Schema for user data response."""
    id: uuid.UUID
    email: str
    full_name: str
    role: UserRole
    organization: Optional[str]
    is_active: bool
    last_login: Optional[datetime]
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class UserWithToken(BaseModel):
    """Schema for user data with authentication tokens."""
    user: UserResponse
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserUpdate(BaseModel):
    """Schema for updating user data (Admin only)."""
    full_name: Optional[str] = None
    role: Optional[UserRole] = None
    organization: Optional[str] = None
    is_active: Optional[bool] = None
