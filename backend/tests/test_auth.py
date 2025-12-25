"""
Test Authentication Endpoints

Tests for user registration, login, token refresh, and password management.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.models import User, UserRole


@pytest.mark.asyncio
async def test_register_user(client: AsyncClient):
    """Test user registration with valid data."""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "test@ecowas.int",
            "password": "SecurePass123!",
            "full_name": "Test User",
            "role": "twg_member",
            "organization": "ECOWAS"
        }
    )
    
    assert response.status_code == 201
    data = response.json()
    
    assert "user" in data
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["user"]["email"] == "test@ecowas.int"
    assert data["user"]["full_name"] == "Test User"
    assert data["user"]["role"] == "twg_member"


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient, db_session: AsyncSession):
    """Test registration with duplicate email fails."""
    # Create first user
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "duplicate@ecowas.int",
            "password": "SecurePass123!",
            "full_name": "First User"
        }
    )
    
    # Try to register with same email
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "duplicate@ecowas.int",
            "password": "DifferentPass456!",
            "full_name": "Second User"
        }
    )
    
    assert response.status_code == 400
    assert "already registered" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_register_weak_password(client: AsyncClient):
    """Test registration with weak password fails."""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "weak@ecowas.int",
            "password": "weak",
            "full_name": "Weak Password User"
        }
    )
    
    assert response.status_code == 422 or response.status_code == 400


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    """Test successful login."""
    # Register user first
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "login@ecowas.int",
            "password": "LoginPass123!",
            "full_name": "Login Test User"
        }
    )
    
    # Login
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "login@ecowas.int",
            "password": "LoginPass123!"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    """Test login with incorrect password fails."""
    # Register user
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "wrongpass@ecowas.int",
            "password": "CorrectPass123!",
            "full_name": "Wrong Pass User"
        }
    )
    
    # Try login with wrong password
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "wrongpass@ecowas.int",
            "password": "WrongPass123!"
        }
    )
    
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_nonexistent_user(client: AsyncClient):
    """Test login with non-existent email fails."""
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "nonexistent@ecowas.int",
            "password": "SomePass123!"
        }
    )
    
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user(client: AsyncClient):
    """Test getting current user profile."""
    # Register and login
    register_response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "profile@ecowas.int",
            "password": "ProfilePass123!",
            "full_name": "Profile User"
        }
    )
    
    access_token = register_response.json()["access_token"]
    
    # Get current user
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["email"] == "profile@ecowas.int"
    assert data["full_name"] == "Profile User"
    assert "hashed_password" not in data  # Should not expose password


@pytest.mark.asyncio
async def test_get_current_user_no_token(client: AsyncClient):
    """Test accessing protected route without token fails."""
    response = await client.get("/api/v1/auth/me")
    
    assert response.status_code == 403  # No credentials provided


@pytest.mark.asyncio
async def test_get_current_user_invalid_token(client: AsyncClient):
    """Test accessing protected route with invalid token fails."""
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid_token_here"}
    )
    
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token(client: AsyncClient):
    """Test token refresh."""
    # Register user
    register_response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "refresh@ecowas.int",
            "password": "RefreshPass123!",
            "full_name": "Refresh User"
        }
    )
    
    refresh_token = register_response.json()["refresh_token"]
    
    # Refresh access token
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_logout(client: AsyncClient):
    """Test logout (token revocation)."""
    # Register user
    register_response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "logout@ecowas.int",
            "password": "LogoutPass123!",
            "full_name": "Logout User"
        }
    )
    
    refresh_token = register_response.json()["refresh_token"]
    
    # Logout
    response = await client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": refresh_token}
    )
    
    assert response.status_code == 204
    
    # Try to use revoked refresh token
    refresh_response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token}
    )
    
    assert refresh_response.status_code == 401


@pytest.mark.asyncio
async def test_change_password(client: AsyncClient):
    """Test password change."""
    # Register user
    register_response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "changepass@ecowas.int",
            "password": "OldPass123!",
            "full_name": "Change Pass User"
        }
    )
    
    access_token = register_response.json()["access_token"]
    
    # Change password
    response = await client.post(
        "/api/v1/auth/change-password",
        json={
            "current_password": "OldPass123!",
            "new_password": "NewPass456!"
        },
        headers={"Authorization": f"Bearer {access_token}"}
    )
    
    assert response.status_code == 204
    
    # Try login with new password
    login_response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "changepass@ecowas.int",
            "password": "NewPass456!"
        }
    )
    
    assert login_response.status_code == 200


@pytest.mark.asyncio
async def test_change_password_wrong_current(client: AsyncClient):
    """Test password change with wrong current password fails."""
    # Register user
    register_response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "wrongcurrent@ecowas.int",
            "password": "CurrentPass123!",
            "full_name": "Wrong Current User"
        }
    )
    
    access_token = register_response.json()["access_token"]
    
    # Try to change password with wrong current password
    response = await client.post(
        "/api/v1/auth/change-password",
        json={
            "current_password": "WrongPass123!",
            "new_password": "NewPass456!"
        },
        headers={"Authorization": f"Bearer {access_token}"}
    )
    
    assert response.status_code == 400
