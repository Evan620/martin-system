"""
Authentication API Routes

Provides endpoints for user authentication and authorization.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.auth import (
    UserRegister,
    UserLogin,
    GoogleLogin,
    Token,
    TokenRefresh,
    AccessToken,
    PasswordChange,
    UserResponse,
    UserWithToken,
    ForgotPassword,
    ResetPassword
)
from app.services.auth_service import AuthService
from app.api.deps import get_current_active_user
from app.models.models import User

router = APIRouter(prefix="/auth", tags=["Authentication"])


# PUBLIC REGISTRATION DISABLED - Invite-only system
# Users must be created by administrators via /users/invite endpoint
@router.post("/register", response_model=UserWithToken, status_code=status.HTTP_403_FORBIDDEN)
async def register(
    user_data: UserRegister,
    db: AsyncSession = Depends(get_db)
):
    """
    Public registration is disabled.
    
    This system uses invite-only registration. Contact your administrator
    to receive an invitation.
    """
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Public registration is disabled. Please contact your administrator for an invitation."
    )


@router.post("/login", response_model=Token)
async def login(
    credentials: UserLogin,
    db: AsyncSession = Depends(get_db)
):
    """
    Authenticate user and obtain access tokens.
    
    - **email**: User email address
    - **password**: User password
    
    Returns access and refresh tokens.
    """
    auth_service = AuthService(db)
    user, access_token, refresh_token = await auth_service.authenticate_user(credentials)
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token
    )


@router.post("/refresh", response_model=AccessToken)
async def refresh_token(
    token_data: TokenRefresh,
    db: AsyncSession = Depends(get_db)
):
    """
    Refresh access token using refresh token.
    
    - **refresh_token**: Valid refresh token
    
    Returns new access token.
    """
    auth_service = AuthService(db)
    access_token = await auth_service.refresh_access_token(token_data.refresh_token)
    
    return AccessToken(access_token=access_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    token_data: TokenRefresh,
    db: AsyncSession = Depends(get_db)
):
    """
    Logout user by revoking refresh token.
    
    - **refresh_token**: Refresh token to revoke
    """
    auth_service = AuthService(db)
    await auth_service.revoke_refresh_token(token_data.refresh_token)
    
    return None




@router.post("/google", response_model=Token)
async def google_login(
    google_data: GoogleLogin,
    db: AsyncSession = Depends(get_db)
):
    """
    Authenticate user via Google.
    
    - **id_token**: Google ID token obtained from frontend
    
    Returns access and refresh tokens.
    """
    auth_service = AuthService(db)
    user, access_token, refresh_token = await auth_service.authenticate_google_user(google_data.id_token)
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current authenticated user profile.

    Requires valid access token in Authorization header.
    """
    # Ensure twgs relationship is loaded and compute twg_ids explicitly
    await db.refresh(current_user, attribute_names=['twgs'])
    twg_ids = [str(twg.id) for twg in current_user.twgs]

    # Return dict directly to avoid Pydantic model immutability issues
    # FastAPI will serialize this to UserResponse schema
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role,
        "organization": current_user.organization,
        "is_active": current_user.is_active,
        "last_login": current_user.last_login,
        "created_at": current_user.created_at,
        "twg_ids": twg_ids,
        "twgs": [{"id": str(twg.id), "name": twg.name} for twg in current_user.twgs]
    }


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Change user password.
    
    - **current_password**: Current password for verification
    - **new_password**: New strong password
    
    Requires authentication. All existing sessions will be invalidated.
    """
    auth_service = AuthService(db)
    await auth_service.change_password(
        current_user,
        password_data.current_password,
        password_data.new_password
    )
    
    return None


@router.post("/forgot-password", status_code=status.HTTP_200_OK)
async def forgot_password(
    forgot_data: ForgotPassword,
    db: AsyncSession = Depends(get_db)
):
    """
    Request a password reset email.
    
    - **email**: User email address
    
    Always returns success for security (doesn't reveal if email exists).
    """
    from app.services.email_service import email_service
    from app.core.config import settings
    
    auth_service = AuthService(db)
    reset_token = await auth_service.request_password_reset(forgot_data.email)
    
    if reset_token:
        # Get user to send personalized email
        user = await auth_service.get_user_by_email(forgot_data.email)
        if user:
            # Construct reset URL (frontend URL)
            reset_url_base = f"{settings.FRONTEND_URL}/reset-password"
            
            try:
                await email_service.send_password_reset_email(
                    to_email=user.email,
                    full_name=user.full_name,
                    reset_token=reset_token,
                    reset_url_base=reset_url_base
                )
            except Exception as e:
                print(f"Failed to send password reset email: {e}")
                # Don't raise error to user for security
    
    # Always return success message (security best practice)
    return {"message": "If the email exists, a password reset link has been sent."}


@router.post("/reset-password", status_code=status.HTTP_200_OK)
async def reset_password(
    reset_data: ResetPassword,
    db: AsyncSession = Depends(get_db)
):
    """
    Reset password using a reset token.
    
    - **token**: Password reset token from email
    - **new_password**: New password (min 8 characters)
    
    Returns success message if password was reset.
    """
    auth_service = AuthService(db)
    await auth_service.reset_password(reset_data.token, reset_data.new_password)
    
    return {"message": "Password has been reset successfully. You can now log in with your new password."}
