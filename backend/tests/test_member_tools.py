"""Unit tests for the member personal-action tools (rsvp_meeting, set_reminder, get_notifications)."""
import uuid
import pytest

from app.models.models import UserRole


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
