"""Member can self-RSVP their own participant row; 404 when not a participant."""
import uuid
from datetime import datetime, timedelta
import pytest
from app.models.models import Meeting, MeetingParticipant, RsvpStatus, TWG, TWGPillar, MeetingStatus


async def _make_meeting_with_participant(db_session, user_id):
    twg = TWG(id=uuid.uuid4(), name="Energy", pillar=TWGPillar.energy_infrastructure)
    meeting = Meeting(
        id=uuid.uuid4(), title="Energy Sync", twg_id=twg.id,
        scheduled_at=datetime.utcnow() + timedelta(days=2),
        duration_minutes=60, status=MeetingStatus.SCHEDULED, meeting_type="virtual",
    )
    part = MeetingParticipant(id=uuid.uuid4(), meeting_id=meeting.id, user_id=user_id, rsvp_status=RsvpStatus.PENDING)
    db_session.add_all([twg, meeting, part])
    await db_session.commit()
    return meeting


@pytest.mark.asyncio
@pytest.mark.parametrize("value", ["ACCEPTED", "DECLINED", "TENTATIVE"])
async def test_member_can_self_rsvp(client, db_session, test_user, normal_user_token_headers, value):
    meeting = await _make_meeting_with_participant(db_session, test_user.id)
    resp = await client.put(
        f"/api/v1/meetings/{meeting.id}/my-rsvp",
        headers=normal_user_token_headers,
        json={"rsvp_status": value},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["rsvp_status"] == value


@pytest.mark.asyncio
async def test_non_participant_gets_404(client, db_session, test_user, normal_user_token_headers):
    # A meeting the member is NOT a participant of.
    twg = TWG(id=uuid.uuid4(), name="Other", pillar=TWGPillar.digital_economy_transformation)
    meeting = Meeting(id=uuid.uuid4(), title="Other", twg_id=twg.id, scheduled_at=datetime.utcnow())
    db_session.add_all([twg, meeting])
    await db_session.commit()
    resp = await client.put(
        f"/api/v1/meetings/{meeting.id}/my-rsvp",
        headers=normal_user_token_headers,
        json={"rsvp_status": "ACCEPTED"},
    )
    assert resp.status_code == 404
