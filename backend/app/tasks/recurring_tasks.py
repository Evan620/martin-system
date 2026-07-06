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


# ── WAIIS TWG weekly invite dispatch ─────────────────────────────────────────
# Postgres advisory-lock key for the weekly invite dispatch. ContinuousMonitor
# runs inside every web instance (and the mis-provisioned "celery-worker" service
# currently runs a second copy of the web app), so without a cross-process lock
# two instances firing the Monday cron at the same second would double-invite.
# pg_try_advisory_lock is session-scoped and survives the per-meeting commits.
_INVITE_DISPATCH_LOCK_KEY = 728041


async def run_weekly_invite_dispatch():
    """
    Core weekly invite dispatch — importable (no Celery required) so the
    in-process ContinuousMonitor can run it directly. Celery beat is not deployed
    in this environment, so the scheduled home is ContinuousMonitor; this stays a
    plain async function and the Celery task below is a thin wrapper for manual /
    future-worker invocation.

    For SCHEDULED meetings starting within the next 7 days that have NO
    participants yet, add the meeting's TWG members as participants + Google
    Calendar attendees and send the invite AS the configured organizer
    (GOOGLE_IMPERSONATE_EMAIL, e.g. joseph.nganga@africacen.org) via the DWD
    service account.

    Idempotent + race-safe: gated by settings.INVITE_DISPATCH_ENABLED, guarded by
    a Postgres advisory lock (only one execution proceeds), and a meeting that
    already has participants is skipped — re-runs never double-invite.
    """
    from app.core.config import settings
    if not getattr(settings, "INVITE_DISPATCH_ENABLED", False):
        logger.info("[invite-dispatch] INVITE_DISPATCH_ENABLED=False - skipping (gated)")
        return {"status": "skipped_gated"}

    import os, json, uuid as _uuid
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from sqlalchemy import func, text
    from app.models.models import Meeting, MeetingParticipant, MeetingStatus, User, twg_members

    WINDOW_DAYS = 7
    SCOPES = ["https://www.googleapis.com/auth/calendar"]

    def _calendar():
        raw = (os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON") or "").strip()
        subject = getattr(settings, "GOOGLE_IMPERSONATE_EMAIL", None) or os.environ.get("GOOGLE_IMPERSONATE_EMAIL")
        creds = service_account.Credentials.from_service_account_info(
            json.loads(raw), scopes=SCOPES).with_subject(subject)
        return build("calendar", "v3", credentials=creds, cache_discovery=False)

    now = datetime.utcnow()
    horizon = now + timedelta(days=WINDOW_DAYS)
    sent = skipped = errs = 0
    async with get_db_session_context() as db:
        # Cross-process guard: bail out if another instance is already dispatching.
        got_lock = (await db.execute(
            text("SELECT pg_try_advisory_lock(:k)"),
            {"k": _INVITE_DISPATCH_LOCK_KEY})).scalar()
        if not got_lock:
            logger.info("[invite-dispatch] another instance holds the lock - skipping")
            return {"status": "skipped_locked"}
        try:
            res = await db.execute(
                select(Meeting).where(
                    Meeting.status == MeetingStatus.SCHEDULED,
                    Meeting.scheduled_at >= now,
                    Meeting.scheduled_at <= horizon,
                    Meeting.video_link.isnot(None),
                )
            )
            meetings = res.scalars().all()
            if not meetings:
                logger.info("[invite-dispatch] no meetings in the next %s days", WINDOW_DAYS)
                return {"sent": 0, "skipped": 0, "errors": 0}
            svc = _calendar()
            for m in meetings:
                cnt = (await db.execute(
                    select(func.count()).select_from(MeetingParticipant)
                    .where(MeetingParticipant.meeting_id == m.id))).scalar() or 0
                if cnt > 0:
                    skipped += 1
                    continue
                members = (await db.execute(
                    select(User).join(twg_members, twg_members.c.user_id == User.id)
                    .where(twg_members.c.twg_id == m.twg_id))).scalars().all()
                members = [u for u in members if u.email]
                if not members:
                    skipped += 1
                    continue
                try:
                    d0 = m.scheduled_at.strftime("%Y-%m-%dT00:00:00Z")
                    d1 = (m.scheduled_at + timedelta(days=1)).strftime("%Y-%m-%dT00:00:00Z")
                    evs = svc.events().list(calendarId="primary", timeMin=d0, timeMax=d1,
                                            singleEvents=True, maxResults=250).execute().get("items", [])
                    ev = next((e for e in evs if (e.get("hangoutLink") or "") == m.video_link
                               or f"ID: {m.id}" in (e.get("description") or "")), None)
                    if not ev:
                        errs += 1
                        logger.warning("[invite-dispatch] no calendar event found for meeting %s", m.id)
                        continue
                    svc.events().patch(
                        calendarId="primary", eventId=ev["id"],
                        body={"attendees": [{"email": u.email} for u in members]},
                        sendUpdates="all", conferenceDataVersion=1).execute()
                    for u in members:
                        db.add(MeetingParticipant(id=_uuid.uuid4(), meeting_id=m.id,
                                                  user_id=u.id, email=u.email,
                                                  name=getattr(u, "full_name", None)))
                    await db.commit()
                    sent += 1
                    logger.info("[invite-dispatch] invited %s to %s (%s)", len(members), m.title, m.id)
                except Exception as e:
                    errs += 1
                    await db.rollback()
                    logger.error("[invite-dispatch] failed for meeting %s: %s", m.id, e)
        finally:
            await db.execute(
                text("SELECT pg_advisory_unlock(:k)"),
                {"k": _INVITE_DISPATCH_LOCK_KEY})
    logger.info("[invite-dispatch] done: sent=%s skipped=%s errors=%s", sent, skipped, errs)
    return {"sent": sent, "skipped": skipped, "errors": errs}


@shared_task(
    name="app.tasks.recurring_tasks.dispatch_weekly_invites",
    bind=True,
    max_retries=1,
)
def dispatch_weekly_invites(self):
    """Thin Celery wrapper around run_weekly_invite_dispatch (see that function)."""
    import asyncio
    try:
        return asyncio.run(run_weekly_invite_dispatch())
    except Exception as e:
        logger.error("[invite-dispatch] task failed: %s", e)
        raise
