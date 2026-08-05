"""
Service for managing recurring meetings.

Handles the business logic for:
- Calculating occurrence dates based on frequency rules
- Generating meeting instances
- Previewing occurrences before creation
- Conflict detection with existing meetings
"""

import uuid
from datetime import datetime, timedelta, timezone as dt_tz
from typing import List, Optional, Tuple
from calendar import monthrange
from zoneinfo import ZoneInfo
import logging
import asyncio
import pytz
from fastapi import HTTPException
from app.services.gcal_executor import gcal_executor as _gcal_executor

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, update
from sqlalchemy.orm import selectinload

from app.models.models import (
    RecurringMeeting,
    RecurringMeetingStatus,
    RecurrenceFrequency,
    RecurrenceEndType,
    Meeting,
    MeetingStatus,
    MeetingParticipant,
    RsvpStatus,
    TWG,
    User,
    UserRole,
    twg_members,
    AttendanceMode,
    RecurringMeetingSelectedMember,
)
from app.schemas.schemas import (
    RecurringMeetingCreate,
    RecurringMeetingRead,
    RecurrenceRule,
    RecurrenceEnd,
    MeetingRead,
)
from app.api.deps import has_twg_access
from app.services.meeting_participant_service import add_meeting_participants, resolve_meeting_members

logger = logging.getLogger(__name__)

# How many days ahead to generate instances
GENERATION_HORIZON_DAYS = 30


def meeting_to_read(meeting: Meeting) -> MeetingRead:
    """Convert a meeting instance without triggering unloaded relationships."""

    return MeetingRead(
        id=meeting.id,
        twg_id=meeting.twg_id,
        title=meeting.title,
        scheduled_at=meeting.scheduled_at,
        duration_minutes=meeting.duration_minutes,
        location=meeting.location,
        status=meeting.status,
        meeting_type=meeting.meeting_type,
        transcript=meeting.transcript,
        video_link=meeting.video_link,
        recurring_meeting_id=meeting.recurring_meeting_id,
        is_recurring_exception=meeting.is_recurring_exception,
        attendance_mode=meeting.attendance_mode,
        selected_member_ids=[
            p.user_id for p in meeting.__dict__.get("participants", []) if p.user_id
        ],
    )


async def get_recurring_meeting_details(
    db: AsyncSession,
    recurring_meeting_id: uuid.UUID,
    current_user: User,
) -> RecurringMeetingRead:
    """Return one accessible recurring series and its next ten instances."""

    result = await db.execute(
        select(RecurringMeeting)
        .where(RecurringMeeting.id == recurring_meeting_id)
        .options(
            selectinload(RecurringMeeting.twg),
            selectinload(RecurringMeeting.instances).selectinload(Meeting.participants),
            selectinload(RecurringMeeting.selected_members),
        )
    )
    recurring = result.scalar_one_or_none()
    if not recurring:
        raise HTTPException(status_code=404, detail="Recurring meeting not found")

    if not has_twg_access(current_user, recurring.twg_id):
        raise HTTPException(
            status_code=403,
            detail="You do not have access to this recurring meeting",
        )

    now = datetime.utcnow()
    upcoming = [
        meeting_to_read(meeting)
        for meeting in recurring.instances
        if meeting.scheduled_at > now and meeting.status != "CANCELLED"
    ]

    return RecurringMeetingRead(
        id=recurring.id,
        twg_id=recurring.twg_id,
        title_template=recurring.title_template,
        duration_minutes=recurring.duration_minutes,
        location=recurring.location,
        meeting_type=recurring.meeting_type,
        attendance_mode=getattr(recurring, "attendance_mode", AttendanceMode.ALL_TWG_MEMBERS),
        selected_member_ids=getattr(recurring, "selected_member_ids", []),
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


def _format_meeting_time_for_email(scheduled_at: datetime) -> tuple:
    """Returns (date_str, time_str) with EAT + UTC labels."""
    display_tz = pytz.timezone("Africa/Nairobi")
    utc_time = pytz.UTC.localize(scheduled_at) if scheduled_at.tzinfo is None else scheduled_at
    local_display = utc_time.astimezone(display_tz)
    date_str = local_display.strftime("%A, %B %d, %Y")
    time_str = f"{local_display.strftime('%I:%M %p')} EAT ({scheduled_at.strftime('%H:%M')} UTC)"
    return date_str, time_str



# Track background GCal/email tasks so Celery can drain them before exit
_pending_gcal_tasks: list = []


async def _sync_new_instances_gcal_email(
    instance_data: list,
    participant_emails: list,
    twg_id,
):
    """Background task: create GCal events + send invite emails for new recurring instances."""
    try:
        from app.services.calendar_service import calendar_service
        from app.services.email_service import email_service
        from app.core.config import settings
        from app.core.database import get_db_session_context

        # Get TWG name using a fresh DB session
        async with get_db_session_context() as db:
            twg_result = await db.execute(select(TWG).where(TWG.id == twg_id))
            twg_obj = twg_result.scalar_one_or_none()
            twg_display_name = twg_obj.name if twg_obj else "TWG"

        loop = asyncio.get_running_loop()
        video_link_updates = {}
        gcal_failures = []
        email_failures = []

        for idx, inst in enumerate(instance_data):
            # 1. Create Google Calendar event with Meet link (with retry)
            gcal_success = False
            for attempt in range(3):
                try:
                    calendar_event = await loop.run_in_executor(
                        _gcal_executor,
                        lambda i=inst: calendar_service.create_meeting_event(
                            title=i["title"],
                            start_time=i["scheduled_at"],
                            duration_minutes=i["duration_minutes"],
                            description=f"Recurring meeting for {twg_display_name}",
                            attendees=participant_emails,
                            meeting_id=i["id"],
                        )
                    )
                    if calendar_event.get("hangoutLink"):
                        video_link_updates[inst["id"]] = calendar_event["hangoutLink"]
                        inst["video_link"] = calendar_event["hangoutLink"]
                    gcal_success = True
                    logger.info(f"GCal event created for recurring instance {inst['id']}")
                    break
                except Exception as e:
                    if attempt < 2:
                        wait = 2 ** (attempt + 1)  # 2s, 4s
                        logger.warning(f"GCal attempt {attempt+1}/3 failed for {inst['id']}: {e}. Retrying in {wait}s...")
                        await asyncio.sleep(wait)
                    else:
                        logger.error(f"GCal FAILED after 3 attempts for instance {inst['id']}: {e}")
                        gcal_failures.append(inst["id"])

            # 2. Send email invite (with retry)
            email_success = False
            if participant_emails:
                for attempt in range(3):
                    try:
                        date_str, time_str = _format_meeting_time_for_email(inst["scheduled_at"])
                        await email_service.send_meeting_invite(
                            to_emails=participant_emails,
                            subject=f"Meeting Invitation: {inst['title']}",
                            template_name="meeting_invite.html",
                            template_context={
                                "user_name": "Valued Participant",
                                "meeting_title": inst["title"],
                                "meeting_date": date_str,
                                "meeting_time": time_str,
                                "location": inst.get("location") or "Virtual",
                                "video_link": inst.get("video_link"),
                                "pillar_name": twg_display_name,
                                "portal_url": settings.FRONTEND_URL + "/schedule",
                            },
                            meeting_details={
                                "title": inst["title"],
                                "meeting_id": inst["id"],
                                "start_time": inst["scheduled_at"],
                                "duration": inst["duration_minutes"],
                                "location": inst.get("video_link") or inst.get("location") or "Virtual",
                            },
                        )
                        email_success = True
                        break
                    except Exception as e:
                        if attempt < 2:
                            wait = 2 ** (attempt + 1)
                            logger.warning(f"Email attempt {attempt+1}/3 failed for {inst['id']}: {e}. Retrying in {wait}s...")
                            await asyncio.sleep(wait)
                        else:
                            logger.error(f"Email FAILED after 3 attempts for instance {inst['id']}: {e}")
                            email_failures.append(inst["id"])

            # Rate-limit pause between instances — longer for GCal API
            if idx < len(instance_data) - 1:
                await asyncio.sleep(2)

        # Log summary so failures are visible
        total = len(instance_data)
        if gcal_failures:
            logger.error(f"GCal sync: {len(gcal_failures)}/{total} instances FAILED: {gcal_failures}")
        else:
            logger.info(f"GCal sync: all {total} instances created successfully")
        if email_failures:
            logger.error(f"Email sync: {len(email_failures)}/{total} instances FAILED: {email_failures}")
        else:
            logger.info(f"Email sync: all {total} invites sent successfully")

        # Persist video_link updates using a fresh DB session
        if video_link_updates:
            try:
                async with get_db_session_context() as db:
                    for mid, link in video_link_updates.items():
                        await db.execute(
                            update(Meeting)
                            .where(Meeting.id == uuid.UUID(mid))
                            .values(video_link=link)
                        )
            except Exception as e:
                logger.error(f"Failed to persist video_link updates: {e}")

    except Exception as e:
        logger.error(f"Background GCal/email sync error: {e}")


async def _cancel_instances_gcal_email(
    instance_data: list,
    participant_emails: list,
    twg_display_name: str,
):
    """Background task: cancel GCal events + send cancellation emails."""
    try:
        from app.services.calendar_service import calendar_service
        from app.services.email_service import email_service
        from app.core.config import settings

        loop = asyncio.get_running_loop()

        for inst in instance_data:
            try:
                await loop.run_in_executor(
                    _gcal_executor,
                    lambda mid=inst["id"]: calendar_service.cancel_meeting_event(mid)
                )
                logger.info(f"GCal event cancelled for recurring instance {inst['id']}")
            except Exception as e:
                logger.warning(f"Failed to cancel GCal event for instance {inst['id']}: {e}")

            try:
                if participant_emails:
                    date_str, time_str = _format_meeting_time_for_email(inst["scheduled_at"])
                    await email_service.send_meeting_cancellation(
                        to_emails=participant_emails,
                        template_context={
                            "user_name": "Valued Participant",
                            "meeting_title": inst["title"],
                            "meeting_date": date_str,
                            "meeting_time": time_str,
                            "location": inst.get("location") or "Virtual",
                            "pillar_name": twg_display_name,
                            "reason": "Recurring meeting series cancelled",
                            "portal_url": f"{settings.FRONTEND_URL}/schedule",
                        },
                        meeting_details={
                            "title": inst["title"],
                            "meeting_id": inst["id"],
                            "start_time": inst["scheduled_at"],
                            "duration": inst["duration_minutes"],
                            "location": inst.get("location"),
                        },
                        reason="Recurring meeting series cancelled",
                    )
            except Exception as e:
                logger.warning(f"Failed to send cancellation email for instance {inst['id']}: {e}")

            await asyncio.sleep(0.5)

    except Exception as e:
        logger.warning(f"Background GCal/email cancellation error: {e}")


class RecurringMeetingService:
    """Service class for recurring meeting operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def _resolve_series_members(self, recurring_meeting: RecurringMeeting) -> list[User]:
        if recurring_meeting.attendance_mode == AttendanceMode.SPECIFIC_TWG_MEMBERS:
            result = await self.db.execute(
                select(User)
                .join(
                    RecurringMeetingSelectedMember,
                    RecurringMeetingSelectedMember.user_id == User.id,
                )
                .join(twg_members, twg_members.c.user_id == User.id)
                .where(
                    and_(
                        RecurringMeetingSelectedMember.recurring_meeting_id
                        == recurring_meeting.id,
                        twg_members.c.twg_id == recurring_meeting.twg_id,
                        User.is_active == True,
                    )
                )
            )
            return list(result.scalars().all())
        return await resolve_meeting_members(
            self.db, recurring_meeting.twg_id, AttendanceMode.ALL_TWG_MEMBERS, []
        )

    def calculate_occurrence_dates(
        self,
        recurring_meeting: RecurringMeeting,
        start_from: Optional[datetime] = None,
        end_at: Optional[datetime] = None,
        max_count: Optional[int] = None,
    ) -> List[datetime]:
        """
        Calculate all occurrence dates for a recurring meeting.

        Args:
            recurring_meeting: The RecurringMeeting model instance
            start_from: Start calculating from this date (defaults to start_date or now)
            end_at: Stop calculating at this date (defaults to end_date or horizon)
            max_count: Maximum number of occurrences to return

        Returns:
            List of datetime objects representing each occurrence
        """
        occurrences = []

        # Determine start point
        if start_from:
            current = start_from.replace(
                hour=0, minute=0, second=0, microsecond=0
            )
        else:
            current = recurring_meeting.start_date.replace(
                hour=0, minute=0, second=0, microsecond=0
            )

        # Determine end point
        if end_at:
            end_limit = end_at
        elif recurring_meeting.end_type == RecurrenceEndType.AFTER_DATE and recurring_meeting.end_date:
            end_limit = recurring_meeting.end_date
        else:
            # Default to horizon
            end_limit = datetime.utcnow() + timedelta(days=GENERATION_HORIZON_DAYS)

        # Parse start time
        try:
            hour, minute = map(int, recurring_meeting.start_time.split(":"))
        except (ValueError, AttributeError):
            hour, minute = 9, 0  # Default to 9:00 AM

        # Determine day of week (0=Monday, 6=Sunday)
        target_weekday = recurring_meeting.day_of_week

        # Calculate occurrences
        occurrence_count = 0
        max_occurrences = (
            recurring_meeting.max_occurrences
            if recurring_meeting.end_type == RecurrenceEndType.AFTER_OCCURRENCES
            else max_count or 1000
        )

        # Adjust current to first occurrence
        if target_weekday is not None:
            # Find first occurrence on the target weekday
            days_ahead = target_weekday - current.weekday()
            if days_ahead < 0:
                days_ahead += 7
            current = current + timedelta(days=days_ahead)

        # Safety limit to prevent infinite loops
        safety_limit = 1000
        iterations = 0

        while iterations < safety_limit:
            iterations += 1

            # Check end conditions
            if current > end_limit:
                break
            if occurrence_count >= max_occurrences:
                break

            # Skip if before start date
            if current.date() < recurring_meeting.start_date.date():
                current = self._get_next_occurrence(current, recurring_meeting)
                continue

            # Create occurrence datetime with the specified time in the meeting's timezone,
            # then convert to naive UTC for DB storage
            try:
                meeting_tz = ZoneInfo(recurring_meeting.timezone or "UTC")
            except Exception:
                meeting_tz = ZoneInfo("UTC")
            local_occurrence = current.replace(hour=hour, minute=minute, tzinfo=meeting_tz)
            utc_occurrence = local_occurrence.astimezone(dt_tz.utc).replace(tzinfo=None)
            occurrences.append(utc_occurrence)
            occurrence_count += 1

            # Move to next occurrence
            current = self._get_next_occurrence(current, recurring_meeting)

        return occurrences

    def _get_next_occurrence(
        self, current: datetime, recurring_meeting: RecurringMeeting
    ) -> datetime:
        """Calculate the next occurrence date based on frequency."""
        if recurring_meeting.frequency == RecurrenceFrequency.WEEKLY:
            return current + timedelta(weeks=recurring_meeting.interval_weeks)
        elif recurring_meeting.frequency == RecurrenceFrequency.BIWEEKLY:
            return current + timedelta(weeks=2 * recurring_meeting.interval_weeks)
        elif recurring_meeting.frequency == RecurrenceFrequency.MONTHLY:
            # Same day of week/month in the next month
            # Calculate next month
            month = current.month + recurring_meeting.interval_weeks
            year = current.year
            while month > 12:
                month -= 12
                year += 1

            # Get the same weekday occurrence in the new month
            # (e.g., 2nd Tuesday of the month)
            target_weekday = recurring_meeting.day_of_week
            if target_weekday is None:
                target_weekday = current.weekday()

            # Find the nth occurrence of this weekday in the month
            first_of_month = current.replace(year=year, month=month, day=1)
            first_weekday = first_of_month.weekday()

            # Which occurrence in the month (1st, 2nd, 3rd, 4th)
            week_in_month = (current.day - 1) // 7 + 1

            # Calculate target day
            days_until_target = (target_weekday - first_weekday + 7) % 7
            target_day = days_until_target + 1 + (week_in_month - 1) * 7

            # Handle months that don't have enough days
            max_day = monthrange(year, month)[1]
            if target_day > max_day:
                target_day = max_day - ((target_day - max_day) // 7 + 1) * 7
                if target_day < 1:
                    target_day = max_day

            return current.replace(year=year, month=month, day=target_day)

        return current + timedelta(days=7)

    async def generate_instances(
        self,
        recurring_meeting: RecurringMeeting,
        days_ahead: int = GENERATION_HORIZON_DAYS,
    ) -> List[Meeting]:
        """
        Generate Meeting instances for the recurring meeting.

        Creates meetings for dates that:
        - Don't already have an instance
        - Are within the generation horizon
        - Haven't exceeded max occurrences

        Args:
            recurring_meeting: The RecurringMeeting to generate instances for
            days_ahead: How many days ahead to generate (default 30)

        Returns:
            List of newly created Meeting instances
        """
        # Serialize generation with every series-wide participant mutation.
        # Reload rather than trusting the caller's potentially stale ORM object.
        locked_result = await self.db.execute(
            select(RecurringMeeting)
            .where(RecurringMeeting.id == recurring_meeting.id)
            .with_for_update()
        )
        recurring_meeting = locked_result.scalar_one_or_none()
        if recurring_meeting is None:
            raise ValueError("Recurring meeting not found")

        # Get existing instances only after the parent row lock is held.
        result = await self.db.execute(
            select(Meeting)
            .where(Meeting.recurring_meeting_id == recurring_meeting.id)
            .options(selectinload(Meeting.twg))
        )
        existing_instances = result.scalars().all()
        existing_dates = {m.scheduled_at.date() for m in existing_instances}

        # Calculate new occurrence dates
        now = datetime.utcnow()
        end_horizon = now + timedelta(days=days_ahead)

        all_dates = self.calculate_occurrence_dates(
            recurring_meeting,
            start_from=now,
            end_at=end_horizon,
        )

        # Filter out dates that already have instances
        new_dates = [d for d in all_dates if d.date() not in existing_dates]

        # Check against total occurrences limit
        if recurring_meeting.end_type == RecurrenceEndType.AFTER_OCCURRENCES:
            remaining = recurring_meeting.max_occurrences - recurring_meeting.occurrences_created
            if remaining <= 0:
                await self.db.commit()
                return []
            new_dates = new_dates[:remaining]

        # Create new Meeting instances
        new_instances = []
        for occurrence_date in new_dates:
            meeting = Meeting(
                id=uuid.uuid4(),
                twg_id=recurring_meeting.twg_id,
                title=recurring_meeting.title_template,
                scheduled_at=occurrence_date,
                duration_minutes=recurring_meeting.duration_minutes,
                location=recurring_meeting.location,
                meeting_type=recurring_meeting.meeting_type,
                status=MeetingStatus.SCHEDULED,
                recurring_meeting_id=recurring_meeting.id,
                original_scheduled_at=occurrence_date,
                attendance_mode=recurring_meeting.attendance_mode,
            )
            self.db.add(meeting)
            new_instances.append(meeting)

        # Update occurrence count
        if new_instances:
            recurring_meeting.occurrences_created += len(new_instances)
            self.db.add(recurring_meeting)

        participant_users = await self._resolve_series_members(recurring_meeting)
        for meeting in new_instances:
            add_meeting_participants(self.db, meeting.id, participant_users)

        # Single atomic commit — instances + participants all or nothing
        await self.db.commit()

        logger.info(
            f"Generated {len(new_instances)} new instances for recurring meeting {recurring_meeting.id}"
        )

        # --- Post-commit: Schedule background GCal + Email integration ---
        if new_instances:
            # Collect ALL participant emails: TWG members, creator, AND external guests.
            # Query the actual meeting_participants table (covers everyone added above).
            all_emails = set()
            first_meeting = new_instances[0]
            participant_result = await self.db.execute(
                select(MeetingParticipant)
                .where(MeetingParticipant.meeting_id == first_meeting.id)
            )
            for mp in participant_result.scalars().all():
                if mp.user_id:
                    user_result = await self.db.execute(
                        select(User.email).where(User.id == mp.user_id)
                    )
                    email = user_result.scalar_one_or_none()
                    if email:
                        all_emails.add(email)
                elif mp.email:
                    # External guest participant
                    all_emails.add(mp.email)

            participant_emails = list(all_emails)
            logger.info(f"Recurring series emails → {len(participant_emails)} recipients: {participant_emails}")
            instance_data = [
                {
                    "id": str(inst.id),
                    "title": inst.title,
                    "scheduled_at": inst.scheduled_at,
                    "duration_minutes": inst.duration_minutes,
                    "location": inst.location,
                }
                for inst in new_instances
            ]
            try:
                task = asyncio.create_task(
                    _sync_new_instances_gcal_email(
                        instance_data, participant_emails, recurring_meeting.twg_id
                    )
                )
                def _on_done(t):
                    if t.exception():
                        logger.error(f"Background GCal/email task failed: {t.exception()}")
                task.add_done_callback(_on_done)
                _pending_gcal_tasks[:] = [t for t in _pending_gcal_tasks if not t.done()]
                _pending_gcal_tasks.append(task)
            except RuntimeError:
                logger.debug("No event loop for background GCal/email task")

        return new_instances

    async def preview_occurrences(
        self,
        create_data: RecurringMeetingCreate,
        days_ahead: int = 60,
    ) -> Tuple[List[datetime], List[dict]]:
        """
        Preview occurrence dates without creating meetings.

        Also checks for conflicts with existing meetings.

        Args:
            create_data: The RecurringMeetingCreate schema
            days_ahead: How many days to preview (default 60)

        Returns:
            Tuple of (occurrence_dates, conflicts)
        """
        # Create a temporary RecurringMeeting for calculation
        temp_recurring = RecurringMeeting(
            id=uuid.uuid4(),
            twg_id=create_data.twg_id,
            title_template=create_data.title_template,
            duration_minutes=create_data.duration_minutes,
            location=create_data.location,
            meeting_type=create_data.meeting_type,
            frequency=create_data.recurrence_rule.frequency,
            interval_weeks=create_data.recurrence_rule.interval_weeks,
            day_of_week=create_data.recurrence_rule.day_of_week,
            start_date=create_data.start_date,
            start_time=create_data.start_time,
            timezone=getattr(create_data, 'timezone', None) or "Africa/Nairobi",
            end_type=create_data.recurrence_end.end_type,
            end_date=create_data.recurrence_end.end_date,
            max_occurrences=create_data.recurrence_end.max_occurrences,
        )

        # Calculate occurrences
        now = datetime.utcnow()
        end_horizon = now + timedelta(days=days_ahead)
        occurrences = self.calculate_occurrence_dates(
            temp_recurring,
            start_from=create_data.start_date,
            end_at=end_horizon,
            max_count=20,  # Limit preview to 20 occurrences
        )

        # Check for conflicts
        conflicts = await self._detect_conflicts(
            create_data.twg_id,
            occurrences,
            create_data.duration_minutes,
        )

        return occurrences, conflicts

    async def _detect_conflicts(
        self,
        twg_id: uuid.UUID,
        occurrences: List[datetime],
        duration_minutes: int,
    ) -> List[dict]:
        """
        Detect scheduling conflicts with existing meetings.

        Args:
            twg_id: The TWG to check for conflicts
            occurrences: List of proposed occurrence datetimes
            duration_minutes: Duration of each meeting

        Returns:
            List of conflict dictionaries
        """
        conflicts = []

        if not occurrences:
            return conflicts

        # Query existing meetings in the date range
        min_date = min(occurrences) - timedelta(minutes=duration_minutes)
        max_date = max(occurrences) + timedelta(minutes=duration_minutes)

        result = await self.db.execute(
            select(Meeting)
            .where(
                and_(
                    Meeting.twg_id == twg_id,
                    Meeting.status != MeetingStatus.CANCELLED,
                    Meeting.scheduled_at >= min_date,
                    Meeting.scheduled_at <= max_date,
                )
            )
        )
        existing_meetings = result.scalars().all()

        # Check each occurrence for conflicts
        for occurrence in occurrences:
            occurrence_end = occurrence + timedelta(minutes=duration_minutes)

            for existing in existing_meetings:
                existing_end = existing.scheduled_at + timedelta(
                    minutes=existing.duration_minutes
                )

                # Check for overlap
                if occurrence < existing_end and occurrence_end > existing.scheduled_at:
                    conflicts.append({
                        "proposed_time": occurrence.isoformat(),
                        "conflicting_meeting_id": str(existing.id),
                        "conflicting_meeting_title": existing.title,
                        "conflicting_meeting_time": existing.scheduled_at.isoformat(),
                    })

        return conflicts

    async def create_recurring_meeting(
        self,
        create_data: RecurringMeetingCreate,
        user: User,
    ) -> RecurringMeeting:
        """
        Create a new recurring meeting and generate initial instances.

        Args:
            create_data: The RecurringMeetingCreate schema
            user: The user creating the recurring meeting

        Returns:
            The created RecurringMeeting with instances
        """
        # Create the recurring meeting
        recurring_meeting = RecurringMeeting(
            id=uuid.uuid4(),
            twg_id=create_data.twg_id,
            title_template=create_data.title_template,
            duration_minutes=create_data.duration_minutes,
            location=create_data.location,
            meeting_type=create_data.meeting_type,
            frequency=create_data.recurrence_rule.frequency,
            interval_weeks=create_data.recurrence_rule.interval_weeks,
            day_of_week=create_data.recurrence_rule.day_of_week,
            start_date=create_data.start_date,
            start_time=create_data.start_time,
            timezone=getattr(create_data, 'timezone', None) or "Africa/Nairobi",
            end_type=create_data.recurrence_end.end_type,
            end_date=create_data.recurrence_end.end_date,
            max_occurrences=create_data.recurrence_end.max_occurrences,
            status=RecurringMeetingStatus.ACTIVE,
            created_by_id=user.id,
            attendance_mode=AttendanceMode(create_data.attendance_mode.value),
        )

        selected_users = await resolve_meeting_members(
            self.db,
            create_data.twg_id,
            create_data.attendance_mode,
            create_data.selected_member_ids,
        )
        self.db.add(recurring_meeting)
        await self.db.flush()  # Get the ID
        if create_data.attendance_mode.value == AttendanceMode.SPECIFIC_TWG_MEMBERS.value:
            for member in selected_users:
                self.db.add(RecurringMeetingSelectedMember(
                    recurring_meeting_id=recurring_meeting.id, user_id=member.id
                ))
            await self.db.flush()

        # Calculate horizon large enough to cover the full requested series.
        # The default 30-day horizon is fine for the daily cron job, but on
        # initial creation we must generate ALL requested instances so the user
        # sees them immediately (e.g. 6 weekly meetings = 42 days).
        if recurring_meeting.end_type == RecurrenceEndType.AFTER_OCCURRENCES and recurring_meeting.max_occurrences:
            weeks_per_occurrence = recurring_meeting.interval_weeks or 1
            if recurring_meeting.frequency == RecurrenceFrequency.MONTHLY:
                initial_horizon = recurring_meeting.max_occurrences * weeks_per_occurrence * 35
            elif recurring_meeting.frequency == RecurrenceFrequency.BIWEEKLY:
                initial_horizon = recurring_meeting.max_occurrences * weeks_per_occurrence * 15
            else:  # WEEKLY
                initial_horizon = recurring_meeting.max_occurrences * weeks_per_occurrence * 8
            initial_horizon = max(initial_horizon, GENERATION_HORIZON_DAYS)
        elif recurring_meeting.end_type == RecurrenceEndType.AFTER_DATE and recurring_meeting.end_date:
            initial_horizon = (recurring_meeting.end_date - datetime.utcnow()).days + 2
            initial_horizon = max(initial_horizon, GENERATION_HORIZON_DAYS)
        else:
            initial_horizon = GENERATION_HORIZON_DAYS

        # Generate initial instances with full horizon
        await self.generate_instances(recurring_meeting, days_ahead=initial_horizon)

        # Load relationships
        result = await self.db.execute(
            select(RecurringMeeting)
            .where(RecurringMeeting.id == recurring_meeting.id)
            .options(
                selectinload(RecurringMeeting.instances).selectinload(Meeting.participants),
                selectinload(RecurringMeeting.twg),
                selectinload(RecurringMeeting.selected_members),
            )
        )

        return result.scalar_one()

    async def pause_recurring_meeting(
        self, recurring_meeting_id: uuid.UUID
    ) -> RecurringMeeting:
        """Pause a recurring meeting (stop generating new instances)."""
        result = await self.db.execute(
            select(RecurringMeeting).where(
                RecurringMeeting.id == recurring_meeting_id
            )
        )
        recurring = result.scalar_one_or_none()

        if not recurring:
            raise ValueError(f"RecurringMeeting {recurring_meeting_id} not found")

        recurring.status = RecurringMeetingStatus.PAUSED
        await self.db.commit()

        return recurring

    async def resume_recurring_meeting(
        self, recurring_meeting_id: uuid.UUID
    ) -> RecurringMeeting:
        """Resume a paused recurring meeting."""
        result = await self.db.execute(
            select(RecurringMeeting).where(
                RecurringMeeting.id == recurring_meeting_id
            )
        )
        recurring = result.scalar_one_or_none()

        if not recurring:
            raise ValueError(f"RecurringMeeting {recurring_meeting_id} not found")

        recurring.status = RecurringMeetingStatus.ACTIVE
        await self.db.commit()

        # Generate any missing instances
        await self.generate_instances(recurring)

        return recurring

    async def cancel_recurring_meeting(
        self,
        recurring_meeting_id: uuid.UUID,
        cancel_future_instances: bool = True,
    ) -> RecurringMeeting:
        """
        Cancel a recurring meeting.

        Args:
            recurring_meeting_id: The ID of the recurring meeting
            cancel_future_instances: Whether to cancel all future instances

        Returns:
            The cancelled RecurringMeeting
        """
        result = await self.db.execute(
            select(RecurringMeeting)
            .where(RecurringMeeting.id == recurring_meeting_id)
            .options(selectinload(RecurringMeeting.instances))
        )
        recurring = result.scalar_one_or_none()

        if not recurring:
            raise ValueError(f"RecurringMeeting {recurring_meeting_id} not found")

        recurring.status = RecurringMeetingStatus.CANCELLED

        cancelled_future_instances = []
        if cancel_future_instances:
            now = datetime.utcnow()
            for instance in recurring.instances:
                if instance.scheduled_at > now:
                    cancelled_future_instances.append(instance)

        # Prepare background task data BEFORE commit (keeps post-commit instant)
        bg_task_data = None
        if cancelled_future_instances:
            try:
                p_result = await self.db.execute(
                    select(User.email).join(
                        MeetingParticipant, MeetingParticipant.user_id == User.id
                    ).where(MeetingParticipant.meeting_id == cancelled_future_instances[0].id)
                )
                participant_emails = [row[0] for row in p_result.all() if row[0]]

                twg_result = await self.db.execute(
                    select(TWG).where(TWG.id == recurring.twg_id)
                )
                twg_obj = twg_result.scalar_one_or_none()
                twg_display_name = twg_obj.name if twg_obj else "TWG"

                instance_data = [
                    {
                        "id": str(inst.id),
                        "title": inst.title,
                        "scheduled_at": inst.scheduled_at,
                        "duration_minutes": inst.duration_minutes,
                        "location": inst.location,
                    }
                    for inst in cancelled_future_instances
                ]
                bg_task_data = (instance_data, participant_emails, twg_display_name)
            except Exception as e:
                logger.warning(f"Failed to prepare GCal/email data for {recurring_meeting_id}: {e}")

        # Soft-delete: mark cancelled so they're hidden but preserved for audit
        for instance in cancelled_future_instances:
            instance.status = MeetingStatus.CANCELLED
            self.db.add(instance)

        await self.db.commit()

        # Fire-and-forget — no DB work after commit
        if bg_task_data:
            try:
                asyncio.create_task(_cancel_instances_gcal_email(*bg_task_data))
            except RuntimeError:
                pass

        return recurring


# Standalone function for Celery task
async def generate_all_upcoming_recurring_instances(db: AsyncSession) -> int:
    """
    Generate instances for all active recurring meetings.

    This is called by the Celery beat task.

    Args:
        db: AsyncSession for database operations

    Returns:
        Total number of instances generated
    """
    service = RecurringMeetingService(db)

    # Queue immutable IDs. A rollback expires ORM instances in the session, so
    # retaining series objects here would make later iteration/logging unsafe.
    result = await db.execute(
        select(RecurringMeeting.id).where(
            RecurringMeeting.status == RecurringMeetingStatus.ACTIVE
        )
    )
    active_recurring_ids = list(result.scalars().all())

    total_generated = 0
    for recurring_id in active_recurring_ids:
        try:
            recurring_result = await db.execute(
                select(RecurringMeeting).where(RecurringMeeting.id == recurring_id)
            )
            recurring = recurring_result.scalar_one_or_none()
            if recurring is None:
                logger.warning(
                    f"Recurring meeting {recurring_id} no longer exists; skipping"
                )
                continue
            instances = await service.generate_instances(recurring)
            total_generated += len(instances)
        except Exception as e:
            await db.rollback()
            logger.error(
                f"Error generating instances for recurring meeting {recurring_id}: {e}"
            )
            continue

    logger.info(
        f"Generated {total_generated} instances across {len(active_recurring_ids)} recurring meetings"
    )

    # Drain pending background GCal/email tasks before returning
    # (In Celery context, asyncio.run() would cancel pending tasks on exit)
    if _pending_gcal_tasks:
        pending = [t for t in _pending_gcal_tasks if not t.done()]
        if pending:
            logger.info(f"Waiting for {len(pending)} background GCal/email tasks...")
            await asyncio.gather(*pending, return_exceptions=True)
        _pending_gcal_tasks.clear()

    return total_generated
