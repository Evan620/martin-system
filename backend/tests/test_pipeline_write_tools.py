import pytest

from app.tools.pipeline_write_tools import (
    advance_project_stage,
    decline_project,
    mark_flagship,
    rescore_project,
    graduate_from_incubation,
    create_action_item,
    bulk_create_action_items,
)
from app.models.models import UserRole


@pytest.mark.asyncio
async def test_advance_returns_forbidden_for_twg_member():
    result = await advance_project_stage(
        project_id="bogus", target_stage="SUMMIT_READY",
        user_id="u1", user_role=UserRole.TWG_MEMBER, confirmed=False, action_id=None,
    )
    assert result["status"] == "forbidden"
    assert "TWG_FACILITATOR" in result["reason"]


@pytest.mark.asyncio
async def test_advance_returns_confirmation_required_for_facilitator():
    # Note: needs a real project_id; use the smoke-test fixture if your test DB has
    # any seeded projects, otherwise this assertion only requires the proposal shape.
    result = await advance_project_stage(
        project_id="00000000-0000-0000-0000-000000000000",
        target_stage="SUMMIT_READY",
        user_id="u1", user_role=UserRole.TWG_FACILITATOR, confirmed=False, action_id=None,
    )
    # Either project not found OR confirmation_required:
    assert result["status"] in {"confirmation_required", "not_found"}


@pytest.mark.asyncio
async def test_decline_requires_reason():
    result = await decline_project(
        project_id="00000000-0000-0000-0000-000000000000", reason="",
        user_id="u1", user_role=UserRole.SECRETARIAT_LEAD,
    )
    assert result["status"] == "invalid_input"


@pytest.mark.asyncio
async def test_mark_flagship_forbidden_for_facilitator():
    # Facilitator can edit but not toggle flagship.
    result = await mark_flagship(
        project_id="00000000-0000-0000-0000-000000000000", is_flagship=True,
        user_id="u1", user_role=UserRole.TWG_FACILITATOR,
    )
    assert result["status"] == "forbidden"


@pytest.mark.asyncio
async def test_rescore_allowed_for_facilitator():
    result = await rescore_project(
        project_id="00000000-0000-0000-0000-000000000000",
        user_id="u1", user_role=UserRole.TWG_FACILITATOR,
    )
    assert result["status"] in {"confirmation_required", "not_found"}


@pytest.mark.asyncio
async def test_graduate_forbidden_for_member():
    result = await graduate_from_incubation(
        project_id="00000000-0000-0000-0000-000000000000",
        user_id="u1", user_role=UserRole.TWG_MEMBER,
    )
    assert result["status"] == "forbidden"


@pytest.mark.asyncio
async def test_create_action_item_requires_description():
    result = await create_action_item(
        description="", user_id="u1", user_role=UserRole.TWG_FACILITATOR,
    )
    assert result["status"] == "invalid_input"


@pytest.mark.asyncio
async def test_create_action_item_proposes():
    result = await create_action_item(
        description="Get permits for Project X",
        user_id="u1", user_role=UserRole.TWG_FACILITATOR,
        due_date="2026-06-15", priority="high",
    )
    assert result["status"] == "confirmation_required"
    assert result["action_type"] == "create_action_item"
    assert result["payload"]["due_date"] == "2026-06-15"


@pytest.mark.asyncio
async def test_bulk_create_caps_at_50():
    result = await bulk_create_action_items(
        meeting_id="m1",
        items=[{"description": f"task {i}"} for i in range(51)],
        user_id="u1", user_role=UserRole.TWG_FACILITATOR,
    )
    assert result["status"] == "invalid_input"
    assert "max 50" in result["reason"]
