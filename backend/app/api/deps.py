"""
API Dependencies

Provides reusable dependencies for authentication and authorization.
"""

from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from backend.app.core.database import get_db
from backend.app.models.models import User, UserRole
from backend.app.utils.security import verify_token
from backend.app.services.auth_service import AuthService

# HTTP Bearer token scheme
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Get current authenticated user from JWT token.
    
    Args:
        credentials: HTTP Bearer credentials
        db: Database session
        
    Returns:
        Current user
        
    Raises:
        HTTPException: If token is invalid or user not found
    """
    token = credentials.credentials
    
    # Verify token
    payload = verify_token(token, token_type="access")
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Extract user ID
    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get user from database
    auth_service = AuthService(db)
    user = await auth_service.get_user_by_id(uuid.UUID(user_id_str))
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get current active user.
    
    Args:
        current_user: Current user from token
        
    Returns:
        Active user
        
    Raises:
        HTTPException: If user is inactive
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    
    return current_user


def require_role(*allowed_roles: UserRole):
    """
    Dependency factory for role-based access control.
    
    Args:
        *allowed_roles: Roles that are allowed access
        
    Returns:
        Dependency function
    """
    async def role_checker(current_user: User = Depends(get_current_active_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role: {', '.join([r.value for r in allowed_roles])}"
            )
        return current_user
    
    return role_checker


# Convenience dependencies for specific roles
require_admin = require_role(UserRole.ADMIN)
require_facilitator = require_role(UserRole.ADMIN, UserRole.TWG_FACILITATOR, UserRole.SECRETARIAT_LEAD)


async def require_twg_access(
    twg_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Check if user has access to specific TWG.
    
    Admins have access to all TWGs.
    Other users must be members of the TWG.
    
    Args:
        twg_id: TWG UUID
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Current user if access granted
        
    Raises:
        HTTPException: If user doesn't have access
    """
    # Admins have access to everything
    if current_user.role == UserRole.ADMIN:
        return current_user
    
    # Check if user is member of the TWG
    user_twg_ids = [twg.id for twg in current_user.twgs]
    
    if twg_id not in user_twg_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this TWG"
        )
    
    return current_user


def has_twg_access(user: User, twg_id: uuid.UUID) -> bool:
    """
    Check if user has access to a TWG (non-dependency version).
    
    Args:
        user: User object
        twg_id: TWG UUID
        
    Returns:
        True if user has access, False otherwise
    """
    # Admins have access to everything
    if user.role == UserRole.ADMIN:
        return True
    
    # Check if user is member of the TWG
    user_twg_ids = [twg.id for twg in user.twgs]
    return twg_id in user_twg_ids
