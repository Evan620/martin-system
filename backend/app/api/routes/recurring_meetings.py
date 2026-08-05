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
from datetime import timezone
import uuid
import logging
import asyncio

from app.core.database import get_db
from app.models.models import (
    RecurringMeeting,
    RecurringMeetingStatus,
    MeetingStatus,
    Meeting,
    MeetingParticipant,
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
from app.services import recurring_meeting_service

RecurringMeetingService = recurring_meeting_service.RecurringMeetingService

router = APIRouter(prefix="/recurring-meetings", tags=["Recurring Meetings"])
logger = logging.getLogger(__name__)


def _meeting_to_read(m: Meeting) -> MeetingRead:
    """Convert a Meeting ORM instance to MeetingRead without triggering lazy loads."""
    return recurring_meeting_service.meeting_to_read(m)


def _series_load_options():
    return (
        selectinload(RecurringMeeting.twg),
        selectinload(RecurringMeeting.selected_members),
        selectinload(RecurringMeeting.instances).selectinload(Meeting.participants),
    )


def _series_to_read(recurring: RecurringMeeting, upcoming: list[MeetingRead]) -> RecurringMeetingRead:
    return RecurringMeetingRead(
        id=recurring.id, twg_id=recurring.twg_id, title_template=recurring.title_template,
        duration_minutes=recurring.duration_minutes, location=recurring.location,
        meeting_type=recurring.meeting_type, attendance_mode=recurring.attendance_mode,
        selected_member_ids=recurring.selected_member_ids, frequency=recurring.frequency,
        interval_weeks=recurring.interval_weeks, day_of_week=recurring.day_of_week,
        start_date=recurring.start_date, start_time=recurring.start_time,
        timezone=recurring.timezone, end_type=recurring.end_type, end_date=recurring.end_date,
        max_occurrences=recurring.max_occurrences, status=recurring.status,
        occurrences_created=recurring.occurrences_created, created_at=recurring.created_at,
        created_by_id=recurring.created_by_id, upcoming_instances=upcoming,
    )


async def _load_authorized_series(db, recurring_meeting_id, current_user):
    result = await db.execute(
        select(RecurringMeeting).where(RecurringMeeting.id == recurring_meeting_id).options(*_series_load_options())
    )
    recurring = result.scalar_one_or_none()
    if not recurring:
        raise HTTPException(status_code=404, detail="Recurring meeting not found")
    if not has_twg_access(current_user, recurring.twg_id):
        raise HTTPException(status_code=403, detail="Access denied")
    return recurring


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

    # Normalize tz-aware datetimes to naive UTC for PostgreSQL
    if preview_data.start_date and hasattr(preview_data.start_date, 'tzinfo') and preview_data.start_date.tzinfo is not None:
        preview_data.start_date = preview_data.start_date.astimezone(timezone.utc).replace(tzinfo=None)
    if preview_data.recurrence_end and preview_data.recurrence_end.end_date:
        end_dt = preview_data.recurrence_end.end_date
        if hasattr(end_dt, 'tzinfo') and end_dt.tzinfo is not None:
            preview_data.recurrence_end.end_date = end_dt.astimezone(timezone.utc).replace(tzinfo=None)

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

    # Normalize tz-aware datetimes to naive UTC for PostgreSQL
    if create_data.start_date and hasattr(create_data.start_date, 'tzinfo') and create_data.start_date.tzinfo is not None:
        create_data.start_date = create_data.start_date.astimezone(timezone.utc).replace(tzinfo=None)
    if create_data.recurrence_end and create_data.recurrence_end.end_date:
        end_dt = create_data.recurrence_end.end_date
        if hasattr(end_dt, 'tzinfo') and end_dt.tzinfo is not None:
            create_data.recurrence_end.end_date = end_dt.astimezone(timezone.utc).replace(tzinfo=None)

    service = RecurringMeetingService(db)

    try:
        recurring_meeting = await service.create_recurring_meeting(
            create_data, current_user
        )

        # Convert instances to MeetingRead for response
        upcoming_instances = []
        for instance in recurring_meeting.instances:
            upcoming_instances.append(_meeting_to_read(instance))

        return RecurringMeetingRead(
            id=recurring_meeting.id,
            twg_id=recurring_meeting.twg_id,
            title_template=recurring_meeting.title_template,
            duration_minutes=recurring_meeting.duration_minutes,
            location=recurring_meeting.location,
            meeting_type=recurring_meeting.meeting_type,
            attendance_mode=recurring_meeting.attendance_mode,
            selected_member_ids=list(create_data.selected_member_ids),
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
    except HTTPException:
        raise
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
    return await recurring_meeting_service.get_recurring_meeting_details(
        db,
        recurring_meeting_id,
        current_user,
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
        *_series_load_options(),
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
            _meeting_to_read(m)
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
            attendance_mode=rm.attendance_mode,
            selected_member_ids=rm.selected_member_ids,
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
            *_series_load_options(),
        )
    )
    recurring = result.scalar_one_or_none()

    if not recurring:
        raise HTTPException(status_code=404, detail="Recurring meeting not found")

    if not has_twg_access(current_user, recurring.twg_id):
        raise HTTPException(status_code=403, detail="Access denied")

    from datetime import datetime
    now = datetime.utcnow()

    update_fields = update_data.model_dump(exclude_unset=True, exclude={"update_scope"})

    # --- Decompose nested Pydantic objects into individual columns ---
    recurrence_rule_changed = False
    if "recurrence_rule" in update_fields and update_fields["recurrence_rule"] is not None:
        rule = update_fields.pop("recurrence_rule")
        old_freq, old_interval, old_day = recurring.frequency, recurring.interval_weeks, recurring.day_of_week
        if "frequency" in rule and rule["frequency"] is not None:
            recurring.frequency = rule["frequency"]
        if "interval_weeks" in rule and rule["interval_weeks"] is not None:
            recurring.interval_weeks = rule["interval_weeks"]
        if "day_of_week" in rule:
            recurring.day_of_week = rule["day_of_week"]
        recurrence_rule_changed = (
            recurring.frequency != old_freq
            or recurring.interval_weeks != old_interval
            or recurring.day_of_week != old_day
        )
    else:
        update_fields.pop("recurrence_rule", None)

    if "recurrence_end" in update_fields and update_fields["recurrence_end"] is not None:
        end = update_fields.pop("recurrence_end")
        if "end_type" in end and end["end_type"] is not None:
            recurring.end_type = end["end_type"]
        if "end_date" in end:
            recurring.end_date = end["end_date"]
        if "max_occurrences" in end:
            recurring.max_occurrences = end["max_occurrences"]
    else:
        update_fields.pop("recurrence_end", None)

    # Track start_time change before applying
    old_start_time = recurring.start_time
    start_time_changed = "start_time" in update_fields and update_fields["start_time"] != old_start_time

    # --- Apply remaining simple fields ---
    for field, value in update_fields.items():
        if value is not None:
            setattr(recurring, field, value)

    await db.flush()

    # --- Propagate start_time change to future instance scheduled_at ---
    if start_time_changed:
        try:
            new_hour, new_minute = map(int, recurring.start_time.split(":"))
        except (ValueError, AttributeError):
            new_hour, new_minute = 9, 0

        from zoneinfo import ZoneInfo
        from datetime import timezone as dt_tz
        try:
            meeting_tz = ZoneInfo(recurring.timezone or "UTC")
        except Exception:
            meeting_tz = ZoneInfo("UTC")

        for instance in recurring.instances:
            if instance.scheduled_at > now and instance.status != MeetingStatus.CANCELLED and not instance.is_recurring_exception:
                # Reinterpret the date portion in the meeting timezone with the new time
                utc_dt = instance.scheduled_at.replace(tzinfo=dt_tz.utc)
                local_dt = utc_dt.astimezone(meeting_tz)
                new_local = local_dt.replace(hour=new_hour, minute=new_minute, second=0, microsecond=0)
                instance.scheduled_at = new_local.astimezone(dt_tz.utc).replace(tzinfo=None)
                db.add(instance)

    # --- Regenerate instances if recurrence rule changed ---
    gcal_cancel_instance_ids = []
    if recurrence_rule_changed:
        # Cancel future non-exception instances (they'll be regenerated)
        for instance in recurring.instances:
            if instance.scheduled_at > now and instance.status != MeetingStatus.CANCELLED and not instance.is_recurring_exception:
                instance.status = MeetingStatus.CANCELLED
                recurring.occurrences_created = max(0, recurring.occurrences_created - 1)
                gcal_cancel_instance_ids.append(str(instance.id))
                db.add(instance)

        await db.flush()

        # Regenerate with new rules
        service = RecurringMeetingService(db)
        await service.generate_instances(recurring)

    # --- Propagate template fields to instances ---
    scope = update_data.update_scope or "future"
    template_fields = ["title_template", "duration_minutes", "location", "meeting_type"]
    should_update_instances = any(f in update_fields for f in template_fields)

    if should_update_instances:
        for instance in recurring.instances:
            if instance.status == MeetingStatus.CANCELLED or instance.is_recurring_exception:
                continue
            if scope == "future" and instance.scheduled_at <= now:
                continue
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

    # Reload with fresh instances for response
    result = await db.execute(
        select(RecurringMeeting)
        .where(RecurringMeeting.id == recurring_meeting_id)
        .options(
            *_series_load_options(),
        )
    )
    recurring = result.scalar_one()

    # --- Post-commit: Schedule background GCal sync + email notifications ---
    _needs_sync = (
        gcal_cancel_instance_ids
        or (not recurrence_rule_changed and (should_update_instances or start_time_changed))
        or should_update_instances or start_time_changed or recurrence_rule_changed
    )
    if _needs_sync:
        try:
            # Extract plain data before background task (ORM objects may detach after response)
            _bg_cancel_ids = list(gcal_cancel_instance_ids)
            _bg_update_instances = []
            if not recurrence_rule_changed and (should_update_instances or start_time_changed):
                _bg_update_instances = [
                    {
                        "id": str(inst.id),
                        "scheduled_at": inst.scheduled_at,
                        "duration_minutes": inst.duration_minutes,
                        "location": inst.location,
                        "title": inst.title,
                    }
                    for inst in recurring.instances
                    if inst.scheduled_at > now and inst.status != MeetingStatus.CANCELLED
                    and not inst.is_recurring_exception
                ]

            _bg_title = recurring.title_template
            _bg_start_time_str = recurring.start_time
            _bg_duration = recurring.duration_minutes
            _bg_location = recurring.location
            _bg_twg_name = recurring.twg.name if recurring.twg else "TWG"
            _bg_rm_id = str(recurring_meeting_id)
            _bg_start_time_changed = start_time_changed
            _bg_update_fields = dict(update_fields)
            _bg_recurrence_rule_changed = recurrence_rule_changed

            # Build changes list
            _bg_changes = []
            if "title_template" in _bg_update_fields:
                _bg_changes.append(f"Title changed to: {_bg_title}")
            if _bg_start_time_changed:
                _bg_changes.append(f"Time changed to: {_bg_start_time_str}")
            if "duration_minutes" in _bg_update_fields:
                _bg_changes.append(f"Duration changed to: {_bg_duration} minutes")
            if "location" in _bg_update_fields:
                _bg_changes.append(f"Location changed to: {_bg_location or 'Virtual'}")
            if _bg_recurrence_rule_changed:
                _bg_changes.append("Meeting schedule/recurrence pattern updated")

            # Get participant emails (session still alive here)
            _bg_participant_emails = []
            active_instance = next(
                (inst for inst in recurring.instances
                 if inst.scheduled_at > now and inst.status != MeetingStatus.CANCELLED),
                None
            )
            if active_instance:
                p_result = await db.execute(
                    select(User.email).join(
                        MeetingParticipant, MeetingParticipant.user_id == User.id
                    ).where(MeetingParticipant.meeting_id == active_instance.id)
                )
                _bg_participant_emails = list(set(row[0] for row in p_result.all() if row[0]))

            async def _do_update_gcal_email():
                try:
                    from app.services.calendar_service import calendar_service
                    from app.services.email_service import email_service
                    from app.core.config import settings

                    loop = asyncio.get_running_loop()

                    # 1. Cancel GCal events for old instances
                    for mid in _bg_cancel_ids:
                        try:
                            from app.services.recurring_meeting_service import _gcal_executor
                            await loop.run_in_executor(
                                _gcal_executor, lambda m=mid: calendar_service.cancel_meeting_event(m)
                            )
                        except Exception as e:
                            logger.warning(f"Failed to cancel GCal for old instance {mid}: {e}")
                        await asyncio.sleep(0.5)

                    # 2. Update GCal events for modified instances
                    for inst in _bg_update_instances:
                        try:
                            await loop.run_in_executor(
                                _gcal_executor,
                                lambda i=inst: calendar_service.update_meeting_event(
                                    meeting_id=i["id"],
                                    new_start_time=i["scheduled_at"] if _bg_start_time_changed else None,
                                    new_duration_minutes=i["duration_minutes"],
                                    new_location=i["location"] if "location" in _bg_update_fields else None,
                                    new_title=i["title"] if "title_template" in _bg_update_fields else None,
                                )
                            )
                        except Exception as e:
                            logger.warning(f"Failed to update GCal for instance {inst['id']}: {e}")
                        await asyncio.sleep(0.5)

                    # 3. Send consolidated update email
                    if _bg_participant_emails and _bg_changes:
                        await email_service.send_meeting_update(
                            to_emails=_bg_participant_emails,
                            template_context={
                                "user_name": "Valued Participant",
                                "meeting_title": _bg_title,
                                "pillar_name": _bg_twg_name,
                                "portal_url": f"{settings.FRONTEND_URL}/schedule",
                            },
                            meeting_details={"title": _bg_title},
                            changes=_bg_changes,
                        )
                except Exception as e:
                    logger.warning(f"GCal/email sync error for recurring meeting {_bg_rm_id}: {e}")

            asyncio.create_task(_do_update_gcal_email())
        except Exception as e:
            logger.warning(f"Failed to schedule GCal/email sync for recurring meeting {recurring_meeting_id}: {e}")

    upcoming = [
        _meeting_to_read(m)
        for m in recurring.instances
        if m.scheduled_at > now and m.status != "CANCELLED"
    ]

    return _series_to_read(recurring, upcoming[:10])


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
    await _load_authorized_series(db, recurring_meeting_id, current_user)
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
    await _load_authorized_series(db, recurring_meeting_id, current_user)
    service = RecurringMeetingService(db)

    try:
        recurring = await service.pause_recurring_meeting(recurring_meeting_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    recurring = await _load_authorized_series(db, recurring_meeting_id, current_user)
    return _series_to_read(recurring, [])


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
    await _load_authorized_series(db, recurring_meeting_id, current_user)
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
        .options(
            *_series_load_options(),
        )
    )
    recurring = result.scalar_one()

    upcoming = [
        _meeting_to_read(m)
        for m in recurring.instances
        if m.scheduled_at > now and m.status != "CANCELLED"
    ]

    return _series_to_read(recurring, upcoming[:10])
