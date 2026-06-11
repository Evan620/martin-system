"""Tests for GET /api/v1/martin/briefing"""
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.api.routes.martin import _query_briefing_data


@pytest.mark.asyncio
async def test_briefing_requires_auth():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/martin/briefing")
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Unit tests for _query_briefing_data (fake session — no real DB needed)
# ---------------------------------------------------------------------------

class _FakeResult:
    def __init__(self, items):
        self._items = items

    def scalars(self):
        return self

    def all(self):
        return self._items


class _FakeDB:
    """Returns canned results for the three sequential queries
    (meetings, threshold projects, notifications)."""

    def __init__(self, meetings=None, projects=None, notifications=None):
        self._results = [meetings or [], projects or [], notifications or []]

    async def execute(self, _query):
        return _FakeResult(self._results.pop(0))


def _fake_meeting(video_link, minutes_ahead=60):
    now_naive = datetime.now(timezone.utc).replace(tzinfo=None)
    return SimpleNamespace(
        id=uuid.uuid4(),
        title="Energy TWG Sync",
        twg=SimpleNamespace(name="Energy TWG"),
        scheduled_at=now_naive + timedelta(minutes=minutes_ahead),
        video_link=video_link,
    )


@pytest.mark.asyncio
async def test_upcoming_meeting_carries_video_link_and_meeting_id():
    meeting = _fake_meeting(video_link="https://meet.google.com/abc-defg-hij")
    db = _FakeDB(meetings=[meeting])

    upcoming, _, _ = await _query_briefing_data(
        db=db,
        is_admin=True,
        user_twg_ids=[],
        user_id=uuid.uuid4(),
        now=datetime.now(timezone.utc),
    )

    assert len(upcoming) == 1
    item = upcoming[0]
    assert item["video_link"] == "https://meet.google.com/abc-defg-hij"
    assert item["meeting_id"] == str(meeting.id)
    # existing fields are untouched
    assert item["title"] == "Energy TWG Sync"
    assert item["twg_name"] == "Energy TWG"
    assert "starts_at" in item and "minutes_until" in item


@pytest.mark.asyncio
async def test_upcoming_meeting_without_video_link_is_null_safe():
    meeting = _fake_meeting(video_link=None)
    db = _FakeDB(meetings=[meeting])

    upcoming, _, _ = await _query_briefing_data(
        db=db,
        is_admin=True,
        user_twg_ids=[],
        user_id=uuid.uuid4(),
        now=datetime.now(timezone.utc),
    )

    assert len(upcoming) == 1
    item = upcoming[0]
    # key must be present so clients can rely on the shape; value is null
    assert "video_link" in item
    assert item["video_link"] is None
    assert item["meeting_id"] == str(meeting.id)
