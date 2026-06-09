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
