"""
Authentication Service

Handles user authentication, registration, and token management.
"""

from datetime import datetime, timedelta
from typing import Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from fastapi import HTTPException, status
import uuid
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from app.models.models import User, RefreshToken, UserRole
from app.schemas.auth import UserRegister, UserLogin
from app.utils.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_token,
    validate_password_strength
)


class AuthService:
    """Service for handling authentication operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """
        Get user by email address.
        
        Args:
            email: User email
            
        Returns:
            User object if found, None otherwise
        """
        # Email is matched case-insensitively. Addresses are handed out by third parties in
        # whatever case their organisation uses (e.g. C.ACOLATSE@unido.org), and users type
        # them in lower case. An exact match made those accounts unreachable and surfaced as
        # "Incorrect email or password", which pointed people at the wrong thing entirely.
        result = await self.db.execute(
            select(User).where(func.lower(User.email) == (email or "").strip().lower())
        )
        return result.scalar_one_or_none()
    
    async def get_user_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        """
        Get user by ID.
        
        Args:
            user_id: User UUID
            
        Returns:
            User object if found, None otherwise
        """
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def register_user(self, user_data: UserRegister) -> Tuple[User, str, str]:
        """
        Register a new user.
        
        Args:
            user_data: User registration data
            
        Returns:
            Tuple of (User, access_token, refresh_token)
            
        Raises:
            HTTPException: If email already exists or validation fails
        """
        # Check if user already exists
        existing_user = await self.get_user_by_email(user_data.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Validate password strength
        is_valid, error_msg = validate_password_strength(user_data.password)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
        
        # Create new user
        hashed_pwd = hash_password(user_data.password)
        new_user = User(
            email=(user_data.email or '').strip().lower(),
            hashed_password=hashed_pwd,
            full_name=user_data.full_name,
            role=UserRole.TWG_MEMBER, # Default to TWG MEMBER, must be promoted by admin
            organization=user_data.organization,
            is_active=True # Auto-approve on registration (admin approval disabled)
        )
        
        self.db.add(new_user)
        await self.db.commit()
        await self.db.refresh(new_user)
        
        # Generate tokens
        access_token = create_access_token(data={"sub": str(new_user.id), "email": new_user.email})
        refresh_token_str = create_refresh_token(data={"sub": str(new_user.id)})
        
        # Store refresh token
        await self._store_refresh_token(new_user.id, refresh_token_str)
        
        return new_user, access_token, refresh_token_str
    
    async def authenticate_user(self, credentials: UserLogin) -> Tuple[User, str, str]:
        """
        Authenticate user and generate tokens.
        
        Args:
            credentials: Login credentials
            
        Returns:
            Tuple of (User, access_token, refresh_token)
            
        Raises:
            HTTPException: If credentials are invalid
        """
        # Get user
        user = await self.get_user_by_email(credentials.email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Verify password
        if not verify_password(credentials.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Check if user is active
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is inactive"
            )
        
        # Update last login
        user.last_login = datetime.utcnow()

        # Track first login (invite acceptance)
        if user.invite_accepted_at is None:
            user.invite_accepted_at = datetime.utcnow()

        await self.db.commit()

        # Generate tokens
        access_token = create_access_token(data={"sub": str(user.id), "email": user.email})
        refresh_token_str = create_refresh_token(data={"sub": str(user.id)})

        # Store refresh token
        await self._store_refresh_token(user.id, refresh_token_str)

        return user, access_token, refresh_token_str

    async def authenticate_google_user(self, google_id_token: str) -> Tuple[User, str, str]:
        """
        Authenticate user via Google ID token.
        
        Args:
            google_id_token: Google ID token from frontend
            
        Returns:
            Tuple of (User, access_token, refresh_token)
        """
        from app.core.config import settings
        
        try:
            # Verify the ID token
            id_info = id_token.verify_oauth2_token(
                google_id_token, 
                google_requests.Request(), 
                settings.GOOGLE_CLIENT_ID
            )
            
            # ID token is valid. Get user details from payload
            email = id_info.get("email")
            full_name = id_info.get("name", "")
            
            if not email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Google account must have an email address"
                )
                
            # Check if user exists
            user = await self.get_user_by_email(email)
            
            if not user:
                # SECURITY: Only users invited by admin can log in
                # Do not auto-create users from Google OAuth
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied. Your email is not authorized. Please contact the administrator."
                )
            
            if not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Account is inactive"
                )
                
            # Update last login
            user.last_login = datetime.utcnow()

            # Track first login (invite acceptance)
            if user.invite_accepted_at is None:
                user.invite_accepted_at = datetime.utcnow()

            await self.db.commit()

            # Generate tokens
            access_token = create_access_token(data={"sub": str(user.id), "email": user.email})
            refresh_token_str = create_refresh_token(data={"sub": str(user.id)})

            # Store refresh token
            await self._store_refresh_token(user.id, refresh_token_str)

            return user, access_token, refresh_token_str

        except ValueError as e:
            # Invalid token
            print(f"Google Auth ValueError: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Google ID token"
            )
        except Exception as e:
            print(f"Google Auth Unexpected Error: {type(e).__name__}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Google authentication failed: {str(e)}"
            )
    
    async def refresh_access_token(self, refresh_token_str: str) -> str:
        """
        Generate new access token from refresh token.
        
        Args:
            refresh_token_str: Refresh token string
            
        Returns:
            New access token
            
        Raises:
            HTTPException: If refresh token is invalid or expired
        """
        # Verify token
        payload = verify_token(refresh_token_str, token_type="refresh")
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
        
        # Check if refresh token exists and is valid
        result = await self.db.execute(
            select(RefreshToken).where(
                RefreshToken.token == refresh_token_str,
                RefreshToken.is_revoked == False
            )
        )
        db_token = result.scalar_one_or_none()
        
        if not db_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token revoked or not found"
            )
        
        # Check expiration
        if db_token.expires_at < datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token expired"
            )
        
        # Get user
        user = await self.get_user_by_id(uuid.UUID(user_id))
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )
        
        # Generate new access token
        access_token = create_access_token(data={"sub": str(user.id), "email": user.email})
        
        return access_token
    
    async def revoke_refresh_token(self, refresh_token_str: str) -> bool:
        """
        Revoke a refresh token (logout).
        
        Args:
            refresh_token_str: Refresh token to revoke
            
        Returns:
            True if successful
        """
        result = await self.db.execute(
            select(RefreshToken).where(RefreshToken.token == refresh_token_str)
        )
        db_token = result.scalar_one_or_none()
        
        if db_token:
            db_token.is_revoked = True
            await self.db.commit()
        
        return True
    
    async def change_password(
        self,
        user: User,
        current_password: str,
        new_password: str
    ) -> bool:
        """
        Change user password.
        
        Args:
            user: User object
            current_password: Current password
            new_password: New password
            
        Returns:
            True if successful
            
        Raises:
            HTTPException: If current password is incorrect or new password is invalid
        """
        # Verify current password
        if not verify_password(current_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )
        
        # Validate new password
        is_valid, error_msg = validate_password_strength(new_password)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
        
        # Update password
        user.hashed_password = hash_password(new_password)
        await self.db.commit()
        
        # Revoke all existing refresh tokens for security
        await self._revoke_all_user_tokens(user.id)
        
        return True
    
    async def _store_refresh_token(self, user_id: uuid.UUID, token: str) -> RefreshToken:
        """Store refresh token in database."""
        from app.core.config import settings
        
        expires_at = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        
        refresh_token = RefreshToken(
            token=token,
            user_id=user_id,
            expires_at=expires_at
        )
        
        self.db.add(refresh_token)
        await self.db.commit()
        
        return refresh_token
    
    async def _revoke_all_user_tokens(self, user_id: uuid.UUID) -> None:
        """Revoke all refresh tokens for a user."""
        result = await self.db.execute(
            select(RefreshToken).where(
                RefreshToken.user_id == user_id,
                RefreshToken.is_revoked == False
            )
        )
        tokens = result.scalars().all()
        
        for token in tokens:
            token.is_revoked = True
        
        await self.db.commit()
    
    async def request_password_reset(self, email: str) -> Optional[str]:
        """
        Generate a password reset token for a user.
        
        Args:
            email: User email address
            
        Returns:
            Reset token if user exists, None otherwise (for security, don't reveal if email exists)
        """
        from app.models.models import PasswordResetToken
        import secrets
        
        # Get user
        user = await self.get_user_by_email(email)
        if not user:
            # For security, don't reveal that email doesn't exist
            # Still return None but don't raise error
            return None
        
        # Generate secure random token
        reset_token = secrets.token_urlsafe(32)
        
        # Set expiration (1 hour from now)
        expires_at = datetime.utcnow() + timedelta(hours=1)
        
        # Store token in database
        password_reset = PasswordResetToken(
            token=reset_token,
            user_id=user.id,
            expires_at=expires_at
        )
        
        self.db.add(password_reset)
        await self.db.commit()
        
        return reset_token
    
    async def reset_password(self, token: str, new_password: str) -> bool:
        """
        Reset user password using a reset token.
        
        Args:
            token: Password reset token
            new_password: New password
            
        Returns:
            True if successful
            
        Raises:
            HTTPException: If token is invalid, expired, or already used
        """
        from app.models.models import PasswordResetToken
        
        # Find token
        result = await self.db.execute(
            select(PasswordResetToken).where(
                PasswordResetToken.token == token,
                PasswordResetToken.is_used == False
            )
        )
        reset_token = result.scalar_one_or_none()
        
        if not reset_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or already used reset token"
            )
        
        # Check expiration
        if reset_token.expires_at < datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reset token has expired"
            )
        
        # Get user
        user = await self.get_user_by_id(reset_token.user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Validate new password
        is_valid, error_msg = validate_password_strength(new_password)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
        
        # Update password
        user.hashed_password = hash_password(new_password)
        user.password_reset_at = datetime.utcnow()

        # Mark token as used
        reset_token.is_used = True

        await self.db.commit()

        # Revoke all existing refresh tokens for security
        await self._revoke_all_user_tokens(user.id)

        return True
