"""Shared validation and participant creation for meeting attendance."""

import uuid
from collections.abc import Sequence

from fastapi import HTTPException
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import AttendanceMode, MeetingParticipant, RsvpStatus, User, twg_members


async def resolve_meeting_members(
    db: AsyncSession,
    twg_id: uuid.UUID,
    attendance_mode: AttendanceMode | str,
    selected_member_ids: Sequence[uuid.UUID] | None,
) -> list[User]:
    """Resolve active TWG members or reject an invalid fixed selection."""
    mode = AttendanceMode(attendance_mode)
    selected_ids = list(selected_member_ids or [])

    if mode == AttendanceMode.SPECIFIC_TWG_MEMBERS:
        if not selected_ids:
            raise HTTPException(status_code=422, detail="Select at least one TWG member")
        if len(set(selected_ids)) != len(selected_ids):
            raise HTTPException(status_code=422, detail="Selected member IDs must be unique")

    query = select(User).join(twg_members, twg_members.c.user_id == User.id).where(
        and_(twg_members.c.twg_id == twg_id, User.is_active.is_(True))
    )
    if mode == AttendanceMode.SPECIFIC_TWG_MEMBERS:
        query = query.where(User.id.in_(selected_ids))

    members = list((await db.execute(query)).scalars().all())
    if mode == AttendanceMode.SPECIFIC_TWG_MEMBERS:
        found_ids = {member.id for member in members}
        if found_ids != set(selected_ids):
            raise HTTPException(
                status_code=422,
                detail="All selected users must be active members of the supplied TWG",
            )
    return members


def add_meeting_participants(
    db: AsyncSession, meeting_id: uuid.UUID, members: Sequence[User]
) -> None:
    """Stage participant rows. The caller owns the surrounding transaction."""
    for member in members:
        db.add(
            MeetingParticipant(
                id=uuid.uuid4(),
                meeting_id=meeting_id,
                user_id=member.id,
                rsvp_status=RsvpStatus.PENDING,
            )
        )
