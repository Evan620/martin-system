"""
Phase 1 lifecycle tests — gender/youth stage gate for UNDER_REVIEW → SUMMIT_READY.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import HTTPException
from app.services.lifecycle_service import LifecycleService
from app.models.models import ProjectStatus, UserRole


def make_user(role=UserRole.ADMIN):
    u = MagicMock()
    u.role = role
    u.id = "user-1"
    return u


def make_project(status, women_pct=None, youth_pct=None):
    p = MagicMock()
    p.id = "proj-1"
    p.status = status
    p.afcen_score = 75
    p.women_employment_pct = women_pct
    p.youth_employment_pct = youth_pct
    return p


@pytest.mark.asyncio
async def test_gender_gate_blocks_when_women_pct_missing():
    """UNDER_REVIEW → SUMMIT_READY blocked when women_employment_pct is None."""
    db = AsyncMock()
    project = make_project(ProjectStatus.UNDER_REVIEW, women_pct=None, youth_pct=28.0)
    result_mock = MagicMock()
    result_mock.scalars.return_value.first.return_value = project
    db.execute.return_value = result_mock

    with pytest.raises(HTTPException) as exc_info:
        await LifecycleService.transition_project_status(
            db, "proj-1", ProjectStatus.SUMMIT_READY, make_user()
        )
    assert exc_info.value.status_code == 400
    assert "women" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_gender_gate_blocks_when_below_threshold():
    """Blocks when women_employment_pct < 30 threshold."""
    db = AsyncMock()
    project = make_project(ProjectStatus.UNDER_REVIEW, women_pct=20.0, youth_pct=28.0)
    result_mock = MagicMock()
    result_mock.scalars.return_value.first.return_value = project
    db.execute.return_value = result_mock

    with pytest.raises(HTTPException) as exc_info:
        await LifecycleService.transition_project_status(
            db, "proj-1", ProjectStatus.SUMMIT_READY, make_user()
        )
    assert exc_info.value.status_code == 400
    assert "30%" in exc_info.value.detail


@pytest.mark.asyncio
async def test_gender_gate_passes_when_thresholds_met():
    """Allows transition when both gender and youth thresholds are met."""
    db = AsyncMock()
    project = make_project(ProjectStatus.UNDER_REVIEW, women_pct=35.0, youth_pct=28.0)
    result_mock = MagicMock()
    result_mock.scalars.return_value.first.return_value = project
    db.execute.return_value = result_mock
    db.add = MagicMock()

    # Should not raise
    result = await LifecycleService.transition_project_status(
        db, "proj-1", ProjectStatus.SUMMIT_READY, make_user()
    )
    assert result.status == ProjectStatus.SUMMIT_READY
