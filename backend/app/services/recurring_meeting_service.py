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
)
from app.schemas.schemas import (
    RecurringMeetingCreate,
    RecurrenceRule,
    RecurrenceEnd,
    MeetingRead,
)

logger = logging.getLogger(__name__)

# How many days ahead to generate instances
GENERATION_HORIZON_DAYS = 30


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

        for inst in instance_data:
            # 1. Create Google Calendar event with Meet link
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
                    logger.info(f"GCal event created for recurring instance {inst['id']}")
            except Exception as e:
                logger.warning(f"Failed to create GCal event for instance {inst['id']}: {e}")

            # 2. Send email invite
            try:
                if participant_emails:
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
            except Exception as e:
                logger.warning(f"Failed to send invite email for instance {inst['id']}: {e}")

            await asyncio.sleep(0.5)

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
                logger.warning(f"Failed to persist video_link updates: {e}")

    except Exception as e:
        logger.warning(f"Background GCal/email sync error: {e}")


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
        # Get existing instances
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
            )
            self.db.add(meeting)
            new_instances.append(meeting)

        # Update occurrence count
        if new_instances:
            recurring_meeting.occurrences_created += len(new_instances)
            self.db.add(recurring_meeting)

        # Auto-include all SECRETARIAT_LEAD users as participants
        secretariat_result = await self.db.execute(
            select(User).where(User.role == UserRole.SECRETARIAT_LEAD).where(User.is_active == True)
        )
        secretariat_users = secretariat_result.scalars().all()

        for meeting in new_instances:
            for secretariat_user in secretariat_users:
                existing_participant = await self.db.execute(
                    select(MeetingParticipant).where(
                        and_(
                            MeetingParticipant.meeting_id == meeting.id,
                            MeetingParticipant.user_id == secretariat_user.id
                        )
                    )
                )
                if not existing_participant.scalar_one_or_none():
                    participant = MeetingParticipant(
                        id=uuid.uuid4(),
                        meeting_id=meeting.id,
                        user_id=secretariat_user.id,
                        rsvp_status=RsvpStatus.ACCEPTED
                    )
                    self.db.add(participant)

        # Auto-include all TWG members as participants (same as normal meetings)
        twg_member_result = await self.db.execute(
            select(User).join(twg_members, twg_members.c.user_id == User.id).where(
                and_(twg_members.c.twg_id == recurring_meeting.twg_id, User.is_active == True)
            )
        )
        twg_member_users = twg_member_result.scalars().all()

        for meeting in new_instances:
            for member in twg_member_users:
                existing_participant = await self.db.execute(
                    select(MeetingParticipant).where(
                        and_(
                            MeetingParticipant.meeting_id == meeting.id,
                            MeetingParticipant.user_id == member.id
                        )
                    )
                )
                if not existing_participant.scalar_one_or_none():
                    participant = MeetingParticipant(
                        id=uuid.uuid4(),
                        meeting_id=meeting.id,
                        user_id=member.id,
                        rsvp_status=RsvpStatus.PENDING
                    )
                    self.db.add(participant)

        # Single atomic commit — instances + participants all or nothing
        await self.db.commit()

        logger.info(
            f"Generated {len(new_instances)} new instances for recurring meeting {recurring_meeting.id}"
        )

        # --- Post-commit: Schedule background GCal + Email integration ---
        if new_instances:
            participant_emails = list(set(
                [u.email for u in secretariat_users if u.email] +
                [u.email for u in twg_member_users if u.email]
            ))
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
        )

        self.db.add(recurring_meeting)
        await self.db.flush()  # Get the ID

        # Generate initial instances
        await self.generate_instances(recurring_meeting)

        # Load relationships
        result = await self.db.execute(
            select(RecurringMeeting)
            .where(RecurringMeeting.id == recurring_meeting.id)
            .options(
                selectinload(RecurringMeeting.instances),
                selectinload(RecurringMeeting.twg),
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

    # Get all active recurring meetings
    result = await db.execute(
        select(RecurringMeeting).where(
            RecurringMeeting.status == RecurringMeetingStatus.ACTIVE
        )
    )
    active_recurring = result.scalars().all()

    total_generated = 0
    for recurring in active_recurring:
        try:
            instances = await service.generate_instances(recurring)
            total_generated += len(instances)
        except Exception as e:
            logger.error(
                f"Error generating instances for recurring meeting {recurring.id}: {e}"
            )
            continue

    logger.info(
        f"Generated {total_generated} instances across {len(active_recurring)} recurring meetings"
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
