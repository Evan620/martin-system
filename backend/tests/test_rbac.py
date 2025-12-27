"""
Test Role-Based Access Control

Tests for role-based permissions and TWG access control.
"""

import pytest
from httpx import AsyncClient
import uuid

from app.models.models import UserRole


@pytest.mark.asyncio
async def test_admin_access_all_twgs(client: AsyncClient, db_session):
    """Test that admin can access all TWGs."""
    # Register admin user
    admin_response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "admin@ecowas.int",
            "password": "AdminPass123!",
            "full_name": "Admin User",
            "role": "admin"
        }
    )
    
    admin_token = admin_response.json()["access_token"]
    
    # Admin should be able to access any TWG endpoint
    # (This assumes TWG endpoints exist and are protected)
    response = await client.get(
        "/api/v1/twgs",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    # Should not get 403 Forbidden
    assert response.status_code != 403


@pytest.mark.asyncio
async def test_facilitator_role_assignment(client: AsyncClient):
    """Test that facilitator role is correctly assigned."""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "facilitator@ecowas.int",
            "password": "FacilitatorPass123!",
            "full_name": "Facilitator User",
            "role": "twg_facilitator"
        }
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["user"]["role"] == "twg_facilitator"


@pytest.mark.asyncio
async def test_member_role_default(client: AsyncClient):
    """Test that member is the default role."""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "member@ecowas.int",
            "password": "MemberPass123!",
            "full_name": "Member User"
            # No role specified
        }
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["user"]["role"] == "twg_member"


@pytest.mark.asyncio
async def test_inactive_user_cannot_login(client: AsyncClient, db_session):
    """Test that inactive users cannot access protected routes."""
    # Register user
    register_response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "inactive@ecowas.int",
            "password": "InactivePass123!",
            "full_name": "Inactive User"
        }
    )
    
    access_token = register_response.json()["access_token"]
    
    # Manually deactivate user in database
    from app.models.models import User
    from sqlalchemy import select
    
    result = await db_session.execute(
        select(User).where(User.email == "inactive@ecowas.int")
    )
    user = result.scalar_one()
    user.is_active = False
    await db_session.commit()
    
    # Try to access protected route
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    
    # Should be forbidden
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_user_roles_enum(client: AsyncClient):
    """Test all valid user roles can be assigned."""
    roles = ["admin", "twg_facilitator", "twg_member", "secretariat_lead"]
    
    for idx, role in enumerate(roles):
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": f"{role}{idx}@ecowas.int",
                "password": "RolePass123!",
                "full_name": f"{role.title()} User",
                "role": role
            }
        )
        
        assert response.status_code == 201
        assert response.json()["user"]["role"] == role
