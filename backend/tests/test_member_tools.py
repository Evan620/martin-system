"""Unit tests for the member personal-action tools (rsvp_meeting, set_reminder, get_notifications)."""
import uuid
import pytest

from app.models.models import UserRole


def _session_factory(session):
    """Return a zero-arg callable usable as `async with AsyncSessionLocal() as s`
    that yields the test's transactional session without closing it."""
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def _factory():
        yield session

    return _factory


@pytest.mark.asyncio
async def test_reminder_model_persists(db_session):
    """The Reminder model stores a member's personal reminder linked to user_id."""
    from app.models.models import Reminder, User

    rid = uuid.uuid4()
    uid = uuid.uuid4()
    # The reminders.user_id FK is enforced by the (PostgreSQL) test DB, so the
    # referenced User row must exist before the reminder can be inserted.
    user = User(
        id=uid,
        full_name="Member One",
        email=f"member-{uid}@example.org",
        hashed_password="x",
        role=UserRole.TWG_MEMBER,
    )
    db_session.add(user)
    await db_session.flush()

    reminder = Reminder(
        id=rid,
        user_id=uid,
        message="Prep notes for Energy TWG",
        remind_at=__import__("datetime").datetime(2026, 6, 10, 9, 0, 0),
    )
    db_session.add(reminder)
    await db_session.flush()

    fetched = await db_session.get(Reminder, rid)
    assert fetched is not None
    assert fetched.user_id == uid
    assert fetched.message == "Prep notes for Energy TWG"
    assert fetched.is_sent is False


@pytest.mark.asyncio
async def test_rsvp_meeting_updates_own_participant(db_session, monkeypatch):
    """rsvp_meeting sets the caller's own MeetingParticipant.rsvp_status to ACCEPTED."""
    from datetime import datetime
    from app.models.models import Meeting, MeetingParticipant, RsvpStatus, TWG, TWGPillar, User
    import app.tools.member_tools as member_tools

    # TWG.pillar is Mapped[TWGPillar] = mapped_column(Enum(TWGPillar)) — use the
    # enum, not a bare string (models.py: TWGPillar.energy_infrastructure, etc.).
    twg = TWG(id=uuid.uuid4(), name="Energy", pillar=TWGPillar.energy_infrastructure)
    meeting = Meeting(id=uuid.uuid4(), title="Energy Sync", twg_id=twg.id, scheduled_at=datetime(2026, 6, 10, 10, 0))
    uid = uuid.uuid4()
    # MeetingParticipant.user_id has a FK to users.id enforced by the test DB,
    # so the referenced User row must exist before the participant can be inserted.
    user = User(
        id=uid,
        full_name="Member One",
        email=f"rsvp-{uid}@example.org",
        hashed_password="x",
        role=UserRole.TWG_MEMBER,
    )
    part = MeetingParticipant(id=uuid.uuid4(), meeting_id=meeting.id, user_id=uid, rsvp_status=RsvpStatus.PENDING)
    db_session.add_all([twg, meeting, user, part])
    await db_session.flush()

    # Tool opens its own AsyncSessionLocal — point it at the test session factory.
    monkeypatch.setattr(member_tools, "AsyncSessionLocal", _session_factory(db_session))

    result = await member_tools.rsvp_meeting(
        meeting_id=str(meeting.id),
        response="ACCEPTED",
        user_id=str(uid),
        user_role=UserRole.TWG_MEMBER,
    )
    assert result["success"] is True
    assert result["rsvp_status"] == "ACCEPTED"


@pytest.mark.asyncio
async def test_rsvp_meeting_rejects_invalid_response(db_session, monkeypatch):
    """An unknown RSVP value returns an error dict, not a crash."""
    import app.tools.member_tools as member_tools
    monkeypatch.setattr(member_tools, "AsyncSessionLocal", _session_factory(db_session))
    result = await member_tools.rsvp_meeting(
        meeting_id=str(uuid.uuid4()),
        response="MAYBE_LATER",
        user_id=str(uuid.uuid4()),
        user_role=UserRole.TWG_MEMBER,
    )
    assert "error" in result


@pytest.mark.asyncio
async def test_rsvp_meeting_not_a_participant_returns_error(db_session, monkeypatch):
    """A member who is not a participant of the meeting cannot RSVP it."""
    import app.tools.member_tools as member_tools
    monkeypatch.setattr(member_tools, "AsyncSessionLocal", _session_factory(db_session))
    result = await member_tools.rsvp_meeting(
        meeting_id=str(uuid.uuid4()),
        response="ACCEPTED",
        user_id=str(uuid.uuid4()),
        user_role=UserRole.TWG_MEMBER,
    )
    assert "error" in result


# ---------------------------------------------------------------------------
# set_reminder
# ---------------------------------------------------------------------------

async def _make_member(db_session, prefix="member"):
    from app.models.models import User

    uid = uuid.uuid4()
    user = User(
        id=uid,
        full_name="Member One",
        email=f"{prefix}-{uid}@example.org",
        hashed_password="x",
        role=UserRole.TWG_MEMBER,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.mark.asyncio
async def test_set_reminder_creates_row_for_calling_user(db_session, monkeypatch):
    """set_reminder persists a Reminder row owned by the calling member (user_id)."""
    from datetime import datetime, timedelta, timezone
    from sqlalchemy import select
    from app.models.models import Reminder
    import app.tools.member_tools as member_tools

    user = await _make_member(db_session, "rem")
    monkeypatch.setattr(member_tools, "AsyncSessionLocal", _session_factory(db_session))

    remind_at = (datetime.now(timezone.utc) + timedelta(hours=3)).replace(microsecond=0)
    result = await member_tools.set_reminder(
        message="Submit the Energy TWG report",
        remind_at_iso=remind_at.isoformat(),
        user_id=str(user.id),
        user_role=UserRole.TWG_MEMBER,
    )
    assert result.get("success") is True, f"unexpected result: {result}"

    rows = (
        await db_session.execute(select(Reminder).where(Reminder.user_id == user.id))
    ).scalars().all()
    assert len(rows) == 1
    assert rows[0].message == "Submit the Energy TWG report"
    assert rows[0].is_sent is False
    # Stored as naive UTC (DB convention — reminder_jobs compares against utcnow).
    assert rows[0].remind_at == remind_at.replace(tzinfo=None)


@pytest.mark.asyncio
async def test_set_reminder_rejects_past_datetime(db_session, monkeypatch):
    """A remind_at in the past returns an error and creates NO row."""
    from datetime import datetime, timedelta, timezone
    from sqlalchemy import select
    from app.models.models import Reminder
    import app.tools.member_tools as member_tools

    user = await _make_member(db_session, "past")
    monkeypatch.setattr(member_tools, "AsyncSessionLocal", _session_factory(db_session))

    past = datetime.now(timezone.utc) - timedelta(hours=1)
    result = await member_tools.set_reminder(
        message="Too late",
        remind_at_iso=past.isoformat(),
        user_id=str(user.id),
        user_role=UserRole.TWG_MEMBER,
    )
    assert "error" in result
    rows = (
        await db_session.execute(select(Reminder).where(Reminder.user_id == user.id))
    ).scalars().all()
    assert rows == []


@pytest.mark.asyncio
async def test_set_reminder_rejects_unparseable_datetime(db_session, monkeypatch):
    """A non-ISO remind_at returns an error dict, not a crash."""
    import app.tools.member_tools as member_tools

    monkeypatch.setattr(member_tools, "AsyncSessionLocal", _session_factory(db_session))
    result = await member_tools.set_reminder(
        message="Prep notes",
        remind_at_iso="next tuesday-ish",
        user_id=str(uuid.uuid4()),
        user_role=UserRole.TWG_MEMBER,
    )
    assert "error" in result


@pytest.mark.asyncio
async def test_set_reminder_naive_datetime_interpreted_in_user_timezone(db_session, monkeypatch):
    """A naive remind_at_iso is interpreted in the member's timezone, stored as naive UTC."""
    from datetime import datetime, timedelta, timezone
    from sqlalchemy import select
    from app.models.models import Reminder
    import app.tools.member_tools as member_tools

    user = await _make_member(db_session, "tz")
    monkeypatch.setattr(member_tools, "AsyncSessionLocal", _session_factory(db_session))

    # 9pm tomorrow Nairobi time (UTC+3) → stored as 6pm UTC.
    local_dt = (datetime.now(timezone.utc) + timedelta(days=1)).replace(
        hour=21, minute=0, second=0, microsecond=0, tzinfo=None
    )
    result = await member_tools.set_reminder(
        message="Call the facilitator",
        remind_at_iso=local_dt.isoformat(),
        user_id=str(user.id),
        user_role=UserRole.TWG_MEMBER,
        user_timezone="Africa/Nairobi",
    )
    assert result.get("success") is True, f"unexpected result: {result}"
    rows = (
        await db_session.execute(select(Reminder).where(Reminder.user_id == user.id))
    ).scalars().all()
    assert len(rows) == 1
    assert rows[0].remind_at == local_dt.replace(hour=18)


# ---------------------------------------------------------------------------
# add_meeting_to_calendar
# ---------------------------------------------------------------------------

async def _make_meeting_with_participant(db_session, user):
    from datetime import datetime, timedelta
    from app.models.models import Meeting, MeetingParticipant, RsvpStatus, TWG, TWGPillar

    twg = TWG(id=uuid.uuid4(), name="Energy", pillar=TWGPillar.energy_infrastructure)
    meeting = Meeting(
        id=uuid.uuid4(),
        title="Energy Sync",
        twg_id=twg.id,
        scheduled_at=datetime.utcnow() + timedelta(days=2),
        duration_minutes=45,
        location="Virtual",
    )
    part = MeetingParticipant(
        id=uuid.uuid4(), meeting_id=meeting.id, user_id=user.id, rsvp_status=RsvpStatus.PENDING
    )
    db_session.add_all([twg, meeting, part])
    await db_session.flush()
    return meeting


@pytest.mark.asyncio
async def test_add_meeting_to_calendar_sends_invite_to_participant(db_session, monkeypatch):
    """A participant gets the meeting's .ics invite emailed to THEIR address only."""
    import app.tools.member_tools as member_tools
    from app.services.email_service import email_service

    user = await _make_member(db_session, "cal")
    meeting = await _make_meeting_with_participant(db_session, user)
    monkeypatch.setattr(member_tools, "AsyncSessionLocal", _session_factory(db_session))

    calls = []

    async def fake_send_meeting_invite(**kwargs):
        calls.append(kwargs)
        return True

    monkeypatch.setattr(email_service, "send_meeting_invite", fake_send_meeting_invite)

    result = await member_tools.add_meeting_to_calendar(
        meeting_id=str(meeting.id),
        user_id=str(user.id),
        user_role=UserRole.TWG_MEMBER,
    )
    assert result.get("success") is True, f"unexpected result: {result}"
    assert len(calls) == 1
    assert calls[0]["to_emails"] == [user.email]
    assert calls[0]["meeting_details"]["meeting_id"] == str(meeting.id)
    assert calls[0]["meeting_details"]["start_time"] == meeting.scheduled_at
    assert calls[0]["meeting_details"]["duration"] == 45


@pytest.mark.asyncio
async def test_add_meeting_to_calendar_denies_non_participant(db_session, monkeypatch):
    """A member who is NOT a participant of the meeting is denied — no email is sent."""
    import app.tools.member_tools as member_tools
    from app.services.email_service import email_service

    participant_user = await _make_member(db_session, "cal-in")
    outsider = await _make_member(db_session, "cal-out")
    meeting = await _make_meeting_with_participant(db_session, participant_user)
    monkeypatch.setattr(member_tools, "AsyncSessionLocal", _session_factory(db_session))

    calls = []

    async def fake_send_meeting_invite(**kwargs):
        calls.append(kwargs)
        return True

    monkeypatch.setattr(email_service, "send_meeting_invite", fake_send_meeting_invite)

    result = await member_tools.add_meeting_to_calendar(
        meeting_id=str(meeting.id),
        user_id=str(outsider.id),
        user_role=UserRole.TWG_MEMBER,
    )
    assert "error" in result
    assert calls == []


# ---------------------------------------------------------------------------
# Registry gating for the new tools
# ---------------------------------------------------------------------------

def test_new_member_tools_registered_and_gated():
    """set_reminder + add_meeting_to_calendar are in MEMBER_TOOLS, granted to the
    member agent, registered (callable), and denied to non-member agents."""
    from app.tools.tool_registry import (
        ToolRegistry,
        ToolAccessDenied,
        MEMBER_TOOLS,
        MEMBER_ONLY_TOOLS,
    )

    reg = ToolRegistry()
    reg.register_all()
    twg = str(uuid.uuid4())

    for name in ("set_reminder", "add_meeting_to_calendar"):
        assert name in MEMBER_TOOLS
        assert name in MEMBER_ONLY_TOOLS
        assert name in reg.list_tools(), f"{name} is not registered"
        assert reg.validate_tool_access(name, "member", twg_id=twg) is True
        for other_agent in ("energy", "supervisor", "resource_mobilization"):
            with pytest.raises(ToolAccessDenied):
                reg.validate_tool_access(name, other_agent, twg_id=twg)

    _defs, tool_map = reg.get_tools_for_agent("member", twg_id=twg)
    assert "set_reminder" in tool_map
    assert "add_meeting_to_calendar" in tool_map
