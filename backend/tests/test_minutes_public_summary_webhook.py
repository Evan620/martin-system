"""Integration tests for the Wave-2 endpoint wiring (meetings.py):

  1. The minutes upsert endpoint accepts + persists an optional, chair-approved
     ``public_summary`` block onto ``Minutes.public_summary`` (existing callers
     that omit it are unaffected).
  2. Approving minutes emits the Campaign OS webhook EXACTLY ONCE with the
     public summary, but only when a ``public_summary`` is present.
  3. Approval NEVER fails on webhook error — a raising emit still returns 200.

The webhook service itself (payload/HMAC/gating/never-raises) is covered by
``test_twg_webhook_service.py``; here the emit is mocked so we assert the
endpoint's wiring/gating, not the network call.
"""
import uuid
from datetime import datetime, timedelta

import pytest

from app.core.config import settings
from app.models.models import (
    Meeting, MeetingStatus, Minutes, MinutesStatus, TWG, TWGPillar, User, UserRole,
)
from app.services import twg_webhook_service
from app.utils.security import create_access_token
from sqlalchemy import select


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

@pytest.fixture
async def approver_user(db_session):
    """A Secretariat Lead — allowed to both edit and approve minutes, and
    (as a privileged role) has access to every TWG."""
    user = User(
        email=f"ps_lead_{uuid.uuid4()}@ecowas.int",
        hashed_password="hashed_secret",
        full_name="Public Summary Lead",
        role=UserRole.SECRETARIAT_LEAD,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
def approver_headers(approver_user):
    token = create_access_token(data={"sub": str(approver_user.id)})
    return {"Authorization": f"Bearer {token}"}


async def _seed_meeting(db_session, *, with_minutes=False, minutes_status=None,
                        public_summary=None):
    """Create a TWG + meeting, optionally with a minutes row."""
    twg = TWG(
        id=uuid.uuid4(),
        name=f"PubSummary TWG {uuid.uuid4().hex[:8]}",
        pillar=TWGPillar.critical_minerals_industrialization,
    )
    db_session.add(twg)
    await db_session.flush()

    meeting = Meeting(
        id=uuid.uuid4(),
        twg_id=twg.id,
        title="WAIIS-2026 TWG — Critical Minerals",
        scheduled_at=datetime(2026, 7, 2, 14, 30, 0),
        duration_minutes=60,
        location="Virtual",
        status=MeetingStatus.COMPLETED,
        meeting_type="virtual",
    )
    db_session.add(meeting)
    await db_session.flush()

    if with_minutes:
        minutes = Minutes(
            meeting_id=meeting.id,
            content="# Full raw minutes\n\nConfidential deliberations here.",
            key_decisions="Raw key decision text — must never be emitted.",
            status=minutes_status or MinutesStatus.PENDING_APPROVAL,
            public_summary=public_summary,
        )
        db_session.add(minutes)
        await db_session.flush()

    await db_session.commit()
    return meeting


PUBLIC_SUMMARY = {
    "highlights": ["Signed MoU on cross-border grid", "Agreed 2027 pilot"],
    "decisions_milestones": ["Milestone A approved"],
    "institutions_public": ["ECOWAS Commission", "AfDB"],
    "next_milestone": "Ministerial review Q4",
}


# ---------------------------------------------------------------------------
# 1. Upsert endpoint persists public_summary
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_upsert_minutes_persists_public_summary(client, db_session, approver_headers):
    meeting = await _seed_meeting(db_session)

    resp = await client.post(
        f"/meetings/{meeting.id}/minutes",
        json={
            "content": "# Minutes\n\nDetailed discussion.",
            "public_summary": PUBLIC_SUMMARY,
        },
        headers=approver_headers,
    )
    assert resp.status_code == 200, resp.text

    row = (await db_session.execute(
        select(Minutes).where(Minutes.meeting_id == meeting.id)
    )).scalar_one()
    assert row.public_summary == PUBLIC_SUMMARY


@pytest.mark.asyncio
async def test_upsert_minutes_without_public_summary_leaves_it_null(
    client, db_session, approver_headers
):
    """Existing callers that never send public_summary are unaffected."""
    meeting = await _seed_meeting(db_session)

    resp = await client.post(
        f"/meetings/{meeting.id}/minutes",
        json={"content": "# Minutes\n\nNo public summary here."},
        headers=approver_headers,
    )
    assert resp.status_code == 200, resp.text

    row = (await db_session.execute(
        select(Minutes).where(Minutes.meeting_id == meeting.id)
    )).scalar_one()
    assert row.public_summary is None


# ---------------------------------------------------------------------------
# 2. Approve emits exactly once with the right payload (when summary present)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_approve_emits_once_with_public_summary(
    client, db_session, approver_headers, monkeypatch
):
    monkeypatch.setattr(settings, "TWG_WEBHOOK_ENABLED", True)
    meeting = await _seed_meeting(
        db_session,
        with_minutes=True,
        minutes_status=MinutesStatus.PENDING_APPROVAL,
        public_summary=PUBLIC_SUMMARY,
    )

    calls = []

    async def _fake_emit(meeting_arg, summary_arg, *args, **kwargs):
        calls.append((meeting_arg, summary_arg))
        return {"status": "sent", "status_code": 200, "meeting_id": str(meeting_arg.id)}

    monkeypatch.setattr(twg_webhook_service, "emit_minutes_published", _fake_emit)

    resp = await client.post(
        f"/meetings/{meeting.id}/minutes/approve", headers=approver_headers
    )
    assert resp.status_code == 200, resp.text

    # Emitted exactly once, with the meeting + the chair-approved summary.
    assert len(calls) == 1
    emitted_meeting, emitted_summary = calls[0]
    assert emitted_meeting.id == meeting.id
    assert emitted_summary == PUBLIC_SUMMARY


@pytest.mark.asyncio
async def test_approve_does_not_emit_without_public_summary(
    client, db_session, approver_headers, monkeypatch
):
    monkeypatch.setattr(settings, "TWG_WEBHOOK_ENABLED", True)
    meeting = await _seed_meeting(
        db_session,
        with_minutes=True,
        minutes_status=MinutesStatus.PENDING_APPROVAL,
        public_summary=None,
    )

    calls = []

    async def _fake_emit(*args, **kwargs):
        calls.append(args)
        return {"status": "sent"}

    monkeypatch.setattr(twg_webhook_service, "emit_minutes_published", _fake_emit)

    resp = await client.post(
        f"/meetings/{meeting.id}/minutes/approve", headers=approver_headers
    )
    assert resp.status_code == 200, resp.text
    # No public_summary → the route skips the emit entirely.
    assert calls == []


# ---------------------------------------------------------------------------
# 3. Approval never fails on webhook error
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_approve_still_succeeds_when_emit_raises(
    client, db_session, approver_headers, monkeypatch
):
    monkeypatch.setattr(settings, "TWG_WEBHOOK_ENABLED", True)
    meeting = await _seed_meeting(
        db_session,
        with_minutes=True,
        minutes_status=MinutesStatus.PENDING_APPROVAL,
        public_summary=PUBLIC_SUMMARY,
    )

    async def _boom(*args, **kwargs):
        raise RuntimeError("campaign os exploded")

    monkeypatch.setattr(twg_webhook_service, "emit_minutes_published", _boom)

    resp = await client.post(
        f"/meetings/{meeting.id}/minutes/approve", headers=approver_headers
    )
    # The webhook is a side-effect, not a gate — approval still returns 200.
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == MinutesStatus.APPROVED.value

    # And the status was actually persisted.
    row = (await db_session.execute(
        select(Minutes).where(Minutes.meeting_id == meeting.id)
    )).scalar_one()
    persisted = row.status.value if hasattr(row.status, "value") else str(row.status)
    assert persisted == MinutesStatus.APPROVED.value
