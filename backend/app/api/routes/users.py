"""
User Management API Routes

Provides endpoints for administrators to manage user accounts, roles, and access.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
import uuid

from app.core.database import get_db
from app.models.models import User, UserRole
from app.schemas.auth import UserResponse, UserUpdate
from app.api.deps import require_admin

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
    query = select(User).offset(skip).limit(limit)
    
    if is_active is not None:
        query = query.where(User.is_active == is_active)
    if role is not None:
        query = query.where(User.role == role)
        
    query = query.order_by(User.created_at.desc())
    
    result = await db.execute(query)
    users = result.scalars().all()
    
    return [UserResponse.model_validate(u) for u in users]


@router.get("/{user_id}", response_model=UserResponse)
async def get_user_details(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """
    Get detailed information about a specific user.
    """
    query = select(User).where(User.id == user_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
        
    return UserResponse.model_validate(user)


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
    query = select(User).where(User.id == user_id)
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
    
    for field, value in update_data.items():
        setattr(user, field, value)
        
    await db.commit()
    await db.refresh(user)
    
    return UserResponse.model_validate(user)


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
