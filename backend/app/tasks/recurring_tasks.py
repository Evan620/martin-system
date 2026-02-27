"""
Celery tasks for recurring meeting management.

This module contains background tasks that:
- Generate upcoming meeting instances for active recurring meetings
- Clean up expired recurring meeting series
- Send notifications about upcoming recurring meetings
"""

import logging
from datetime import datetime, timedelta

from celery import shared_task
from sqlalchemy import select

from app.core.celery_app import celery_app
from app.core.database import get_db_session_context
from app.models.models import (
    RecurringMeeting,
    RecurringMeetingStatus,
    RecurrenceEndType,
)
from app.services.recurring_meeting_service import generate_all_upcoming_recurring_instances

logger = logging.getLogger(__name__)


@shared_task(
    name="app.tasks.recurring_tasks.generate_upcoming_recurring_instances",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def generate_upcoming_recurring_instances_task(self):
    """
    Celery task to generate meeting instances for all active recurring meetings.

    This task runs daily (at 2 AM by default) and:
    1. Finds all ACTIVE recurring meetings
    2. For each, generates instances for the next 30 days
    3. Skips any dates that already have instances
    4. Respects end conditions (date-based or count-based)

    Returns:
        dict: Summary of generated instances
    """
    logger.info("Starting recurring meeting instance generation...")

    try:
        import asyncio

        async def _generate():
            async with get_db_session_context() as db:
                return await generate_all_upcoming_recurring_instances(db)

        total_generated = asyncio.run(_generate())

        logger.info(f"Generated {total_generated} total recurring meeting instances")

        return {
            "status": "success",
            "instances_generated": total_generated,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to generate recurring instances: {e}")
        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))


@shared_task(
    name="app.tasks.recurring_tasks.cleanup_ended_recurring_meetings",
    bind=True,
    max_retries=2,
)
def cleanup_ended_recurring_meetings_task(self):
    """
    Mark recurring meetings as ENDED when they've reached their end condition.

    This runs weekly to:
    1. Find ACTIVE recurring meetings with end_date in the past
    2. Find ACTIVE recurring meetings that hit max_occurrences
    3. Update their status to ENDED

    Returns:
        dict: Summary of cleaned up meetings
    """
    logger.info("Starting recurring meeting cleanup...")

    try:
        import asyncio

        async def _cleanup():
            async with get_db_session_context() as db:
                now = datetime.utcnow()
                ended_count = 0

                # Find meetings past their end date
                result = await db.execute(
                    select(RecurringMeeting).where(
                        RecurringMeeting.status == RecurringMeetingStatus.ACTIVE,
                        RecurringMeeting.end_type == RecurrenceEndType.AFTER_DATE,
                        RecurringMeeting.end_date < now,
                    )
                )
                past_date_meetings = result.scalars().all()

                for rm in past_date_meetings:
                    rm.status = RecurringMeetingStatus.ENDED
                    db.add(rm)
                    ended_count += 1
                    logger.info(f"Marked recurring meeting {rm.id} as ENDED (past end date)")

                await db.commit()
                return ended_count

        ended_count = asyncio.run(_cleanup())

        logger.info(f"Marked {ended_count} recurring meetings as ENDED")

        return {
            "status": "success",
            "meetings_ended": ended_count,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to cleanup recurring meetings: {e}")
        raise self.retry(exc=e)


@shared_task(
    name="app.tasks.recurring_tasks.send_recurring_meeting_reminders",
    bind=True,
    max_retries=2,
)
def send_recurring_meeting_reminders_task(self):
    """
    Send reminders about upcoming recurring meeting instances.

    This runs daily to notify organizers about:
    - Meetings scheduled for tomorrow
    - Any changes to the recurring series

    Returns:
        dict: Summary of reminders sent
    """
    logger.info("Starting recurring meeting reminder task...")

    try:
        import asyncio

        async def _send_reminders():
            async with get_db_session_context() as db:
                from app.models.models import Meeting, MeetingParticipant, User
                from app.models.models import Notification, NotificationType

                tomorrow = datetime.utcnow() + timedelta(days=1)
                tomorrow_start = tomorrow.replace(hour=0, minute=0, second=0, microsecond=0)
                tomorrow_end = tomorrow.replace(hour=23, minute=59, second=59, microsecond=999999)

                # Find recurring meetings happening tomorrow
                result = await db.execute(
                    select(Meeting)
                    .where(
                        Meeting.recurring_meeting_id.isnot(None),
                        Meeting.scheduled_at >= tomorrow_start,
                        Meeting.scheduled_at <= tomorrow_end,
                        Meeting.status != "CANCELLED",
                    )
                )
                upcoming_meetings = result.scalars().all()

                reminders_sent = 0
                for meeting in upcoming_meetings:
                    # Notify the meeting creator (or TWG lead)
                    # Get TWG technical lead
                    if meeting.twg and meeting.twg.technical_lead_id:
                        notification = Notification(
                            user_id=meeting.twg.technical_lead_id,
                            type=NotificationType.INFO,
                            title="Upcoming Recurring Meeting",
                            content=f"'{meeting.title}' is scheduled for tomorrow at {meeting.scheduled_at.strftime('%H:%M UTC')}.",
                            link=f"/meetings/{meeting.id}",
                        )
                        db.add(notification)
                        reminders_sent += 1

                await db.commit()
                return reminders_sent

        reminders_sent = asyncio.run(_send_reminders())

        logger.info(f"Sent {reminders_sent} recurring meeting reminders")

        return {
            "status": "success",
            "reminders_sent": reminders_sent,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to send recurring meeting reminders: {e}")
        raise self.retry(exc=e)
