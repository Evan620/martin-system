"""Shared member-RSVP write logic, used by both the REST route and the Martin tool
so the two paths update MeetingParticipant.rsvp_status identically."""
import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import MeetingParticipant, RsvpStatus


async def apply_member_rsvp(
    session: AsyncSession,
    meeting_id: uuid.UUID,
    user_id: uuid.UUID,
    status: RsvpStatus,
) -> Optional[MeetingParticipant]:
    """Set the caller's own RSVP on a meeting.

    Finds the MeetingParticipant row for (meeting_id, user_id) — being a
    participant IS the authorization. Returns the updated row, or None if the
    user is not a participant of that meeting. Commits on success.
    """
    result = await session.execute(
        select(MeetingParticipant).where(
            MeetingParticipant.meeting_id == meeting_id,
            MeetingParticipant.user_id == user_id,
        )
    )
    participant = result.scalar_one_or_none()
    if participant is None:
        return None
    participant.rsvp_status = status
    await session.commit()
    await session.refresh(participant)
    return participant
