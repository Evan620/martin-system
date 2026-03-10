"""
User Management API Routes

Provides endpoints for administrators to manage user accounts, roles, and access.
"""

from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
import uuid
import io
import csv

from sqlalchemy.orm import selectinload
from app.core.database import get_db
from app.models.models import User, UserRole, TWG
from app.core.config import settings
from app.schemas.auth import UserResponse, UserUpdate
from app.api.deps import require_admin
from app.schemas.user_invite import UserInvite, UserInviteResponse, ResendInviteResponse, BulkInviteRequest, BulkInviteResponse, BulkUserInvite
import secrets
import string

router = APIRouter(prefix="/users", tags=["User Management"])


@router.get("/", response_model=List[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    is_active: Optional[bool] = None,
    role: Optional[UserRole] = None,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """
    List all users.

    Admins can filter by active status and role.
    """
    query = select(User).options(selectinload(User.twgs)).offset(skip).limit(limit)

    if is_active is not None:
        query = query.where(User.is_active == is_active)
    if role is not None:
        query = query.where(User.role == role)

    query = query.order_by(User.created_at.desc())

    result = await db.execute(query)
    users = result.scalars().all()

    # Return dict list directly to avoid Pydantic model immutability issues
    return [
        {
            "id": u.id,
            "email": u.email,
            "full_name": u.full_name,
            "role": u.role,
            "organization": u.organization,
            "is_active": u.is_active,
            "last_login": u.last_login,
            "created_at": u.created_at,
            "invite_sent_at": u.invite_sent_at,
            "invite_accepted_at": u.invite_accepted_at,
            "password_reset_at": u.password_reset_at,
            "twg_ids": [str(twg.id) for twg in u.twgs],
            "twgs": [{"id": str(twg.id), "name": twg.name} for twg in u.twgs]
        }
        for u in users
    ]


@router.get("/{user_id}", response_model=UserResponse)
async def get_user_details(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """
    Get detailed information about a specific user.
    """
    query = select(User).where(User.id == user_id).options(selectinload(User.twgs))
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Explicitly compute twg_ids to ensure proper serialization
    await db.refresh(user, attribute_names=['twgs'])

    # Return dict directly to avoid Pydantic model immutability issues
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "organization": user.organization,
        "is_active": user.is_active,
        "last_login": user.last_login,
        "created_at": user.created_at,
        "invite_sent_at": user.invite_sent_at,
        "invite_accepted_at": user.invite_accepted_at,
        "password_reset_at": user.password_reset_at,
        "twg_ids": [str(twg.id) for twg in user.twgs],
        "twgs": [{"id": str(twg.id), "name": twg.name} for twg in user.twgs]
    }


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: uuid.UUID,
    user_update: UserUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """
    Update a user's details, role, or active status.
    """
    # Eager load TWGs to enable relationship update
    query = select(User).where(User.id == user_id).options(selectinload(User.twgs))
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Prevent admin from deactivating themselves or changing their own role
    if user.id == admin.id:
        if user_update.is_active is False:
             raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Administrators cannot deactivate themselves"
            )
        if user_update.role and user_update.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Administrators cannot demote themselves"
            )

    update_data = user_update.model_dump(exclude_unset=True)

    # Check for email duplicate if email is being updated
    if user_update.email is not None and user_update.email != user.email:
        existing = await db.execute(select(User).where(User.email == user_update.email))
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists"
            )

    # Update TWG assignments if provided
    if user_update.twg_ids is not None:
        twg_query = select(TWG).where(TWG.id.in_(user_update.twg_ids))
        twg_res = await db.execute(twg_query)
        new_twgs = twg_res.scalars().all()
        user.twgs = new_twgs  # Update relationship

    update_data = user_update.model_dump(exclude_unset=True, exclude={'twg_ids'})

    for field, value in update_data.items():
        setattr(user, field, value)

    await db.commit()
    await db.refresh(user, attribute_names=['twgs'])

    # Explicitly compute twg_ids to ensure proper serialization
    response = UserResponse.model_validate(user)
    response.twg_ids = [str(twg.id) for twg in user.twgs]
    return response


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """
    Permanently delete a user account.
    """
    query = select(User).where(User.id == user_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
        
    if user.id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Administrators cannot delete themselves"
        )
        
    await db.delete(user)
    await db.commit()
    
    return None


@router.post("/invite", response_model=UserInviteResponse, status_code=status.HTTP_201_CREATED)
async def invite_user(
    invite_data: UserInvite,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """
    Invite a new user (Admin only).
    
    Creates a user account with a temporary password and optionally sends
    an invitation email.
    """
    from app.services.auth_service import AuthService
    from app.schemas.auth import UserRegister
    
    # Generate secure temporary password (guarantee one from each required category)
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    required = [
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.digits),
        secrets.choice("!@#$%^&*"),
    ]
    rest = [secrets.choice(alphabet) for _ in range(12)]
    combined = required + rest
    secrets.SystemRandom().shuffle(combined)
    temp_password = ''.join(combined)

    # Check if user already exists
    existing = await db.execute(select(User).where(User.email == invite_data.email))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )
    
    # Create user via auth service
    auth_service = AuthService(db)
    user_register = UserRegister(
        email=invite_data.email,
        password=temp_password,
        full_name=invite_data.full_name,
        organization=invite_data.organization
    )
    
    user, _, _ = await auth_service.register_user(user_register)
    
    # Re-fetch user with TWGs loaded to prevent MissingGreenlet error during assignment
    # This ensures the relationship is ready for async modification
    query = select(User).where(User.id == user.id).options(selectinload(User.twgs))
    result = await db.execute(query)
    user = result.scalar_one()
    
    # Update role
    user.role = invite_data.role
    
    # Assign TWGs if provided
    if invite_data.twg_ids:
        twg_query = select(TWG).where(TWG.id.in_(invite_data.twg_ids))
        twg_res = await db.execute(twg_query)
        user.twgs = twg_res.scalars().all()
    
    await db.commit()
    await db.refresh(user)
    
    # Send invitation email
    invite_sent = False
    if invite_data.send_email:
        try:
            from app.services.email_service import email_service
            
            # Use configured frontend URL
            login_url = settings.FRONTEND_URL

            await email_service.send_user_invite(
                to_email=user.email,
                full_name=user.full_name,
                password=temp_password,
                role=user.role.value,
                login_url=login_url
            )
            invite_sent = True
        except Exception as e:
            # Log error but don't fail the request
            print(f"Failed to send invite email: {e}")
            pass

    # Track invite timestamp
    user.invite_sent_at = datetime.utcnow()
    await db.commit()

    return UserInviteResponse(
        user_id=user.id,
        email=user.email,
        temporary_password=temp_password,
        invite_sent=invite_sent
    )


@router.post("/{user_id}/resend-invite", response_model=ResendInviteResponse)
async def resend_invite(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """
    Resend invite to an existing user (Admin only).

    Generates a new temporary password, updates the user's credentials,
    sends an invite email, and revokes all existing refresh tokens.
    """
    from app.services.auth_service import AuthService
    from app.utils.security import hash_password

    query = select(User).where(User.id == user_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Generate new temporary password (guarantee one from each required category)
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    required = [
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.digits),
        secrets.choice("!@#$%^&*"),
    ]
    rest = [secrets.choice(alphabet) for _ in range(12)]
    combined = required + rest
    secrets.SystemRandom().shuffle(combined)
    temp_password = ''.join(combined)

    # Update user's password
    user.hashed_password = hash_password(temp_password)

    # Revoke all existing refresh tokens for security
    auth_service = AuthService(db)
    await auth_service._revoke_all_user_tokens(user.id)

    # Send invite email
    invite_sent = False
    try:
        from app.services.email_service import email_service

        login_url = settings.FRONTEND_URL

        await email_service.send_user_invite(
            to_email=user.email,
            full_name=user.full_name,
            password=temp_password,
            role=user.role.value,
            login_url=login_url
        )
        invite_sent = True
    except Exception as e:
        print(f"Failed to send invite email: {e}")

    # Update invite tracking
    user.invite_sent_at = datetime.utcnow()
    await db.commit()

    return ResendInviteResponse(
        user_id=user.id,
        email=user.email,
        temporary_password=temp_password,
        invite_sent=invite_sent
    )


@router.post("/bulk-invite", response_model=BulkInviteResponse, status_code=status.HTTP_201_CREATED)
async def bulk_invite_users(
    request: BulkInviteRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """
    Bulk invite multiple users (Admin only).

    Creates multiple user accounts with temporary passwords and optionally sends
    invitation emails. Returns lists of successful and failed creations.
    """
    from app.services.auth_service import AuthService
    from app.schemas.auth import UserRegister
    from app.services.email_service import email_service

    successful = []
    failed = []
    login_url = settings.FRONTEND_URL

    for user_data in request.users:
        try:
            # Check if user already exists
            existing = await db.execute(select(User).where(User.email == user_data.email))
            if existing.scalar_one_or_none():
                failed.append({
                    "email": user_data.email,
                    "full_name": user_data.full_name,
                    "error": "User with this email already exists"
                })
                continue

            # Generate secure temporary password (guarantee one from each required category)
            alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
            required = [
                secrets.choice(string.ascii_uppercase),
                secrets.choice(string.ascii_lowercase),
                secrets.choice(string.digits),
                secrets.choice("!@#$%^&*"),
            ]
            rest = [secrets.choice(alphabet) for _ in range(12)]
            combined = required + rest
            secrets.SystemRandom().shuffle(combined)
            temp_password = ''.join(combined)

            # Create user via auth service
            auth_service = AuthService(db)
            user_register = UserRegister(
                email=user_data.email,
                password=temp_password,
                full_name=user_data.full_name,
                organization=user_data.organization
            )

            user, _, _ = await auth_service.register_user(user_register)

            # Re-fetch user with TWGs loaded
            query = select(User).where(User.id == user.id).options(selectinload(User.twgs))
            result = await db.execute(query)
            user = result.scalar_one()

            # Update role
            try:
                user.role = UserRole(user_data.role) if user_data.role else UserRole.TWG_MEMBER
            except ValueError:
                user.role = UserRole.TWG_MEMBER

            # Assign TWGs if provided
            if user_data.twg_ids:
                try:
                    twg_uuids = [uuid.UUID(twg_id) for twg_id in user_data.twg_ids if twg_id]
                    if twg_uuids:
                        twg_query = select(TWG).where(TWG.id.in_(twg_uuids))
                        twg_res = await db.execute(twg_query)
                        user.twgs = twg_res.scalars().all()
                except ValueError:
                    pass  # Invalid UUID, skip TWG assignment

            await db.commit()
            await db.refresh(user)

            # Send invitation email
            invite_sent = False
            if request.send_emails:
                try:
                    await email_service.send_user_invite(
                        to_email=user.email,
                        full_name=user.full_name,
                        password=temp_password,
                        role=user.role.value,
                        login_url=login_url
                    )
                    invite_sent = True
                except Exception as e:
                    print(f"Failed to send invite email to {user.email}: {e}")

            # Track invite timestamp
            user.invite_sent_at = datetime.utcnow()
            await db.commit()

            successful.append({
                "user_id": str(user.id),
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role.value,
                "temporary_password": temp_password,
                "invite_sent": invite_sent
            })

        except Exception as e:
            failed.append({
                "email": user_data.email,
                "full_name": user_data.full_name,
                "error": str(e)
            })

    return BulkInviteResponse(
        successful=successful,
        failed=failed,
        total=len(request.users),
        success_count=len(successful),
        failure_count=len(failed)
    )
