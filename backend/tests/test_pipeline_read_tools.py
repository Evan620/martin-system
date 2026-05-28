import pytest

from app.tools.pipeline_read_tools import (
    pipeline_summary, my_action_items, next_deadlines,
)
from app.models.models import UserRole


@pytest.mark.asyncio
async def test_pipeline_summary_rejects_bad_scope():
    r = await pipeline_summary(user_id="u", user_role=UserRole.ADMIN, scope="weird")
    assert r["status"] == "invalid_input"


@pytest.mark.asyncio
async def test_pipeline_summary_returns_shape():
    r = await pipeline_summary(user_id="u", user_role=UserRole.ADMIN, scope="all", period="week")
    assert r["status"] == "ok"
    assert "by_stage" in r and "total_projects" in r and "moved_in_window" in r


@pytest.mark.asyncio
async def test_next_deadlines_rejects_bad_window():
    r = await next_deadlines(user_id="00000000-0000-0000-0000-000000000000",
                             user_role=UserRole.ADMIN, window="7days")
    assert r["status"] == "invalid_input"
