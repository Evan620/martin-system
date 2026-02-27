"""
API routes for recurring meeting management.

Endpoints:
- POST /recurring-meetings/ - Create recurring meeting series
- POST /recurring-meetings/preview - Preview dates without creating
- GET /recurring-meetings/{id} - Get series details
- PATCH /recurring-meetings/{id} - Update series
- DELETE /recurring-meetings/{id} - Cancel series
- POST /recurring-meetings/{id}/pause - Pause generation
- POST /recurring-meetings/{id}/resume - Resume generation
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List, Optional
import uuid
import logging

from app.core.database import get_db
from app.models.models import (
    RecurringMeeting,
    RecurringMeetingStatus,
    User,
    UserRole,
)
from app.schemas.schemas import (
    RecurringMeetingCreate,
    RecurringMeetingRead,
    RecurringMeetingUpdate,
    RecurringMeetingPreview,
    MeetingRead,
)
from app.api.deps import get_current_active_user, require_facilitator, has_twg_access
from app.services.recurring_meeting_service import RecurringMeetingService

router = APIRouter(prefix="/recurring-meetings", tags=["Recurring Meetings"])
logger = logging.getLogger(__name__)


@router.post("/preview", response_model=RecurringMeetingPreview)
async def preview_recurring_meeting(
    preview_data: RecurringMeetingCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Preview occurrence dates for a recurring meeting without creating it.

    Returns:
        - List of occurrence dates (up to 20)
        - List of any detected conflicts with existing meetings
    """
    # Check user has access to this TWG
    if not has_twg_access(current_user, preview_data.twg_id):
        raise HTTPException(
            status_code=403,
            detail="You do not have access to this TWG"
        )

    service = RecurringMeetingService(db)
    occurrences, conflicts = await service.preview_occurrences(preview_data)

    return RecurringMeetingPreview(
        occurrence_dates=occurrences,
        conflicts_detected=conflicts,
    )


@router.post("/", response_model=RecurringMeetingRead, status_code=status.HTTP_201_CREATED)
async def create_recurring_meeting(
    create_data: RecurringMeetingCreate,
    current_user: User = Depends(require_facilitator),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new recurring meeting series.

    Requires FACILITATOR or ADMIN role.
    Automatically generates meeting instances for the next 30 days.

    Request body:
    - twg_id: TWG to create meetings for
    - title_template: Title template for instances
    - duration_minutes: Default meeting duration
    - location: Default location (optional)
    - meeting_type: "virtual" or "in_person"
    - recurrence_rule: Frequency and interval settings
    - recurrence_end: When to stop generating instances
    - start_date: First occurrence date
    - start_time: Meeting time in "HH:MM" format
    """
    # Check user has access to this TWG
    if not has_twg_access(current_user, create_data.twg_id):
        raise HTTPException(
            status_code=403,
            detail="You do not have access to manage meetings for this TWG"
        )

    service = RecurringMeetingService(db)

    try:
        recurring_meeting = await service.create_recurring_meeting(
            create_data, current_user
        )

        # Convert instances to MeetingRead for response
        upcoming_instances = []
        for instance in recurring_meeting.instances:
            upcoming_instances.append(MeetingRead.model_validate(instance))

        return RecurringMeetingRead(
            id=recurring_meeting.id,
            twg_id=recurring_meeting.twg_id,
            title_template=recurring_meeting.title_template,
            duration_minutes=recurring_meeting.duration_minutes,
            location=recurring_meeting.location,
            meeting_type=recurring_meeting.meeting_type,
            frequency=recurring_meeting.frequency,
            interval_weeks=recurring_meeting.interval_weeks,
            day_of_week=recurring_meeting.day_of_week,
            start_date=recurring_meeting.start_date,
            start_time=recurring_meeting.start_time,
            timezone=recurring_meeting.timezone,
            end_type=recurring_meeting.end_type,
            end_date=recurring_meeting.end_date,
            max_occurrences=recurring_meeting.max_occurrences,
            status=recurring_meeting.status,
            occurrences_created=recurring_meeting.occurrences_created,
            created_at=recurring_meeting.created_at,
            created_by_id=recurring_meeting.created_by_id,
            upcoming_instances=upcoming_instances,
        )
    except Exception as e:
        logger.error(f"Failed to create recurring meeting: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create recurring meeting: {str(e)}"
        )


@router.get("/{recurring_meeting_id}", response_model=RecurringMeetingRead)
async def get_recurring_meeting(
    recurring_meeting_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get details of a specific recurring meeting series.

    Includes upcoming instances that haven't occurred yet.
    """
    result = await db.execute(
        select(RecurringMeeting)
        .where(RecurringMeeting.id == recurring_meeting_id)
        .options(
            selectinload(RecurringMeeting.twg),
            selectinload(RecurringMeeting.instances),
        )
    )
    recurring = result.scalar_one_or_none()

    if not recurring:
        raise HTTPException(status_code=404, detail="Recurring meeting not found")

    # Check access
    if not has_twg_access(current_user, recurring.twg_id):
        raise HTTPException(
            status_code=403,
            detail="You do not have access to this recurring meeting"
        )

    # Filter to upcoming instances
    from datetime import datetime
    now = datetime.utcnow()
    upcoming = [
        MeetingRead.model_validate(m)
        for m in recurring.instances
        if m.scheduled_at > now and m.status != "CANCELLED"
    ]

    return RecurringMeetingRead(
        id=recurring.id,
        twg_id=recurring.twg_id,
        title_template=recurring.title_template,
        duration_minutes=recurring.duration_minutes,
        location=recurring.location,
        meeting_type=recurring.meeting_type,
        frequency=recurring.frequency,
        interval_weeks=recurring.interval_weeks,
        day_of_week=recurring.day_of_week,
        start_date=recurring.start_date,
        start_time=recurring.start_time,
        timezone=recurring.timezone,
        end_type=recurring.end_type,
        end_date=recurring.end_date,
        max_occurrences=recurring.max_occurrences,
        status=recurring.status,
        occurrences_created=recurring.occurrences_created,
        created_at=recurring.created_at,
        created_by_id=recurring.created_by_id,
        upcoming_instances=upcoming[:10],  # Limit to 10 upcoming
    )


@router.get("/", response_model=List[RecurringMeetingRead])
async def list_recurring_meetings(
    twg_id: Optional[uuid.UUID] = None,
    status: Optional[RecurringMeetingStatus] = None,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List recurring meetings visible to the current user.

    Query params:
    - twg_id: Filter to a specific TWG
    - status: Filter by status (active, paused, ended, cancelled)
    """
    query = select(RecurringMeeting).options(
        selectinload(RecurringMeeting.twg),
        selectinload(RecurringMeeting.instances),
    )

    # Filter by TWG access
    if current_user.role not in [UserRole.ADMIN, UserRole.SECRETARIAT_LEAD]:
        user_twg_ids = [t.id for t in current_user.twgs]
        query = query.where(RecurringMeeting.twg_id.in_(user_twg_ids))

    # Apply filters
    if twg_id:
        if not has_twg_access(current_user, twg_id):
            raise HTTPException(status_code=403, detail="Access denied to this TWG")
        query = query.where(RecurringMeeting.twg_id == twg_id)

    if status:
        query = query.where(RecurringMeeting.status == status)

    query = query.offset(skip).limit(limit).order_by(RecurringMeeting.created_at.desc())

    result = await db.execute(query)
    recurring_meetings = result.scalars().all()

    # Build response
    response = []
    from datetime import datetime
    now = datetime.utcnow()

    for rm in recurring_meetings:
        upcoming = [
            MeetingRead.model_validate(m)
            for m in rm.instances
            if m.scheduled_at > now and m.status != "CANCELLED"
        ]
        response.append(RecurringMeetingRead(
            id=rm.id,
            twg_id=rm.twg_id,
            title_template=rm.title_template,
            duration_minutes=rm.duration_minutes,
            location=rm.location,
            meeting_type=rm.meeting_type,
            frequency=rm.frequency,
            interval_weeks=rm.interval_weeks,
            day_of_week=rm.day_of_week,
            start_date=rm.start_date,
            start_time=rm.start_time,
            timezone=rm.timezone,
            end_type=rm.end_type,
            end_date=rm.end_date,
            max_occurrences=rm.max_occurrences,
            status=rm.status,
            occurrences_created=rm.occurrences_created,
            created_at=rm.created_at,
            created_by_id=rm.created_by_id,
            upcoming_instances=upcoming[:5],  # Limit for list view
        ))

    return response


@router.patch("/{recurring_meeting_id}", response_model=RecurringMeetingRead)
async def update_recurring_meeting(
    recurring_meeting_id: uuid.UUID,
    update_data: RecurringMeetingUpdate,
    current_user: User = Depends(require_facilitator),
    db: AsyncSession = Depends(get_db),
):
    """
    Update a recurring meeting series.

    update_scope determines what gets updated:
    - "future": Only affects future instances (default)
    - "all": Updates all instances (may be destructive)
    """
    result = await db.execute(
        select(RecurringMeeting)
        .where(RecurringMeeting.id == recurring_meeting_id)
        .options(
            selectinload(RecurringMeeting.twg),
            selectinload(RecurringMeeting.instances),
        )
    )
    recurring = result.scalar_one_or_none()

    if not recurring:
        raise HTTPException(status_code=404, detail="Recurring meeting not found")

    if not has_twg_access(current_user, recurring.twg_id):
        raise HTTPException(status_code=403, detail="Access denied")

    # Update recurring meeting fields
    update_fields = update_data.model_dump(exclude_unset=True, exclude={"update_scope"})
    for field, value in update_fields.items():
        if value is not None:
            setattr(recurring, field, value)

    await db.commit()
    await db.refresh(recurring)

    # If template fields changed, optionally update future instances
    if update_data.update_scope == "all":
        from datetime import datetime
        now = datetime.utcnow()
        template_fields = ["title_template", "duration_minutes", "location", "meeting_type"]

        should_update_instances = any(f in update_fields for f in template_fields)

        if should_update_instances:
            for instance in recurring.instances:
                if instance.scheduled_at > now and not instance.is_recurring_exception:
                    if "title_template" in update_fields:
                        instance.title = recurring.title_template
                    if "duration_minutes" in update_fields:
                        instance.duration_minutes = recurring.duration_minutes
                    if "location" in update_fields:
                        instance.location = recurring.location
                    if "meeting_type" in update_fields:
                        instance.meeting_type = recurring.meeting_type
                    db.add(instance)
            await db.commit()

    # Build response
    from datetime import datetime
    now = datetime.utcnow()
    upcoming = [
        MeetingRead.model_validate(m)
        for m in recurring.instances
        if m.scheduled_at > now and m.status != "CANCELLED"
    ]

    return RecurringMeetingRead(
        id=recurring.id,
        twg_id=recurring.twg_id,
        title_template=recurring.title_template,
        duration_minutes=recurring.duration_minutes,
        location=recurring.location,
        meeting_type=recurring.meeting_type,
        frequency=recurring.frequency,
        interval_weeks=recurring.interval_weeks,
        day_of_week=recurring.day_of_week,
        start_date=recurring.start_date,
        start_time=recurring.start_time,
        timezone=recurring.timezone,
        end_type=recurring.end_type,
        end_date=recurring.end_date,
        max_occurrences=recurring.max_occurrences,
        status=recurring.status,
        occurrences_created=recurring.occurrences_created,
        created_at=recurring.created_at,
        created_by_id=recurring.created_by_id,
        upcoming_instances=upcoming[:10],
    )


@router.delete("/{recurring_meeting_id}")
async def cancel_recurring_meeting(
    recurring_meeting_id: uuid.UUID,
    cancel_future: bool = True,
    current_user: User = Depends(require_facilitator),
    db: AsyncSession = Depends(get_db),
):
    """
    Cancel a recurring meeting series.

    Query params:
    - cancel_future: If true, cancels all future instances (default: true)
    """
    service = RecurringMeetingService(db)

    try:
        recurring = await service.cancel_recurring_meeting(
            recurring_meeting_id,
            cancel_future_instances=cancel_future,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return {
        "status": "cancelled",
        "recurring_meeting_id": str(recurring.id),
        "instances_cancelled": cancel_future,
    }


@router.post("/{recurring_meeting_id}/pause", response_model=RecurringMeetingRead)
async def pause_recurring_meeting(
    recurring_meeting_id: uuid.UUID,
    current_user: User = Depends(require_facilitator),
    db: AsyncSession = Depends(get_db),
):
    """
    Pause a recurring meeting series.

    No new instances will be generated until resumed.
    Existing instances are not affected.
    """
    service = RecurringMeetingService(db)

    try:
        recurring = await service.pause_recurring_meeting(recurring_meeting_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return RecurringMeetingRead(
        id=recurring.id,
        twg_id=recurring.twg_id,
        title_template=recurring.title_template,
        duration_minutes=recurring.duration_minutes,
        location=recurring.location,
        meeting_type=recurring.meeting_type,
        frequency=recurring.frequency,
        interval_weeks=recurring.interval_weeks,
        day_of_week=recurring.day_of_week,
        start_date=recurring.start_date,
        start_time=recurring.start_time,
        timezone=recurring.timezone,
        end_type=recurring.end_type,
        end_date=recurring.end_date,
        max_occurrences=recurring.max_occurrences,
        status=recurring.status,
        occurrences_created=recurring.occurrences_created,
        created_at=recurring.created_at,
        created_by_id=recurring.created_by_id,
        upcoming_instances=[],
    )


@router.post("/{recurring_meeting_id}/resume", response_model=RecurringMeetingRead)
async def resume_recurring_meeting(
    recurring_meeting_id: uuid.UUID,
    current_user: User = Depends(require_facilitator),
    db: AsyncSession = Depends(get_db),
):
    """
    Resume a paused recurring meeting series.

    Will generate any instances that should have been created
    during the pause period (up to 30 days ahead).
    """
    service = RecurringMeetingService(db)

    try:
        recurring = await service.resume_recurring_meeting(recurring_meeting_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    # Get upcoming instances
    from datetime import datetime
    now = datetime.utcnow()
    result = await db.execute(
        select(RecurringMeeting)
        .where(RecurringMeeting.id == recurring.id)
        .options(selectinload(RecurringMeeting.instances))
    )
    recurring = result.scalar_one()

    upcoming = [
        MeetingRead.model_validate(m)
        for m in recurring.instances
        if m.scheduled_at > now and m.status != "CANCELLED"
    ]

    return RecurringMeetingRead(
        id=recurring.id,
        twg_id=recurring.twg_id,
        title_template=recurring.title_template,
        duration_minutes=recurring.duration_minutes,
        location=recurring.location,
        meeting_type=recurring.meeting_type,
        frequency=recurring.frequency,
        interval_weeks=recurring.interval_weeks,
        day_of_week=recurring.day_of_week,
        start_date=recurring.start_date,
        start_time=recurring.start_time,
        timezone=recurring.timezone,
        end_type=recurring.end_type,
        end_date=recurring.end_date,
        max_occurrences=recurring.max_occurrences,
        status=recurring.status,
        occurrences_created=recurring.occurrences_created,
        created_at=recurring.created_at,
        created_by_id=recurring.created_by_id,
        upcoming_instances=upcoming[:10],
    )
