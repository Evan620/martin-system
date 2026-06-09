"""apply_member_rsvp updates the caller's own participant row; None when absent."""
import uuid
from datetime import datetime
import pytest
from app.models.models import Meeting, MeetingParticipant, RsvpStatus, TWG, TWGPillar, User, UserRole
from app.services.rsvp_service import apply_member_rsvp


@pytest.mark.asyncio
async def test_apply_updates_own_participant(db_session):
    twg = TWG(id=uuid.uuid4(), name="Energy", pillar=TWGPillar.energy_infrastructure)
    meeting = Meeting(id=uuid.uuid4(), title="Sync", twg_id=twg.id, scheduled_at=datetime(2026, 6, 10, 10, 0))
    uid = uuid.uuid4()
    user = User(id=uid, full_name="M", email=f"m-{uid}@x.org", hashed_password="x", role=UserRole.TWG_MEMBER)
    part = MeetingParticipant(id=uuid.uuid4(), meeting_id=meeting.id, user_id=uid, rsvp_status=RsvpStatus.PENDING)
    db_session.add_all([twg, meeting, user, part])
    await db_session.flush()

    result = await apply_member_rsvp(db_session, meeting.id, uid, RsvpStatus.TENTATIVE)
    assert result is not None
    assert result.rsvp_status == RsvpStatus.TENTATIVE


@pytest.mark.asyncio
async def test_apply_returns_none_when_not_participant(db_session):
    result = await apply_member_rsvp(db_session, uuid.uuid4(), uuid.uuid4(), RsvpStatus.ACCEPTED)
    assert result is None
