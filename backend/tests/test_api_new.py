import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.models import UserRole, TWGPillar, TWG

# Tests for Projects API
@pytest.mark.asyncio
async def test_create_project(client: AsyncClient, admin_token_headers, db_session: AsyncSession):
    # 1. Create a TWG
    twg = TWG(name="Energy TWG", pillar=TWGPillar.ENERGY)
    db_session.add(twg)
    await db_session.commit()
    await db_session.refresh(twg)
    
    # 2. Create Project as Admin
    payload = {
        "twg_id": str(twg.id),
        "name": "Solar Farm Alpha",
        "description": "50MW Solar Plant",
        "investment_size": 50000000.00,
        "currency": "USD",
        "status": "identified"
    }
    response = await client.post("/api/v1/projects/", json=payload, headers=admin_token_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Solar Farm Alpha"
    assert data["id"] is not None

@pytest.mark.asyncio
async def test_access_control_projects(client: AsyncClient, normal_user_token_headers, db_session: AsyncSession):
    # Determine behavior: Normal user without TWG access should fail or see empty list?
    # Current implementation: 403 if filtering by TWG user isn't in.
    
    # Create TWG user is NOT in
    twg = TWG(name="Mining TWG", pillar=TWGPillar.MINERALS)
    db_session.add(twg)
    await db_session.commit()
    await db_session.refresh(twg)
    
    # Try to list projects for this TWG
    response = await client.get(f"/api/v1/projects/?twg_id={twg.id}", headers=normal_user_token_headers)
    assert response.status_code == 403

# Tests for Action Items API
@pytest.mark.asyncio
async def test_create_action_item(client: AsyncClient, admin_token_headers, db_session: AsyncSession, test_user):
    # Create TWG
    twg = TWG(name="Transport TWG", pillar=TWGPillar.LOGISTICS)
    db_session.add(twg)
    await db_session.commit()
    await db_session.refresh(twg)

    payload = {
        "twg_id": str(twg.id),
        "description": "Draft policy brief",
        "owner_id": str(test_user.id),
        "due_date": "2024-12-31T23:59:59",
        "priority": "high"
    }
    response = await client.post("/api/v1/action-items/", json=payload, headers=admin_token_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["description"] == "Draft policy brief"
    assert data["owner_id"] == str(test_user.id)

# Tests for Documents API (Mocking upload)
import io

@pytest.mark.asyncio
async def test_upload_document(client: AsyncClient, admin_token_headers, db_session: AsyncSession):
    # Create TWG
    twg = TWG(name="Digital TWG", pillar=TWGPillar.DIGITAL)
    db_session.add(twg)
    await db_session.commit()
    await db_session.refresh(twg)
    
    # Prepare dummy file
    file_content = b"Draft Policy Content"
    files = {"file": ("policy.txt", file_content, "text/plain")}
    data = {"twg_id": str(twg.id)}
    
    response = await client.post(
        "/api/v1/documents/upload",
        files=files,
        data=data, # Send twg_id as form data
        headers=admin_token_headers
    )
    
    # Depending on setup, might need cleanup of uploaded file
    assert response.status_code == 201
    resp_data = response.json()
    assert resp_data["file_name"] == "policy.txt"
    assert "file_path" in resp_data
