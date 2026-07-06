"""
Continuous Monitor Service

Runs background jobs to detect:
1. Temporal Conflicts (Scheduling overlaps)
2. Semantic Conflicts (Policy divergences)
3. TWG Health (Inactivity deadlines)

Uses APScheduler for periodic execution.
"""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_MISSED
from datetime import datetime, timedelta, timezone
UTC = timezone.utc
from loguru import logger
from typing import List, Optional, Tuple
import asyncio
from uuid import UUID
from app.services.gcal_executor import gcal_executor as _gcal_executor


from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm.attributes import flag_modified

from app.core.config import settings
from app.core.database import get_db_session_context
from app.models.models import (
    Meeting, Conflict, TWG, ConflictStatus, Notification, NotificationType, Document, User, MeetingParticipant, VipProfile,
    ConflictType, ConflictSeverity, MeetingStatus, RsvpStatus
)
from app.services.conflict_detector import ConflictDetector
from app.services.attendee_service import attendee_service
from app.services.subgroup_health import scan_stalled_subgroups

class ContinuousMonitor:
    """
    Background service for maintaining global state integrity.
    """
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.conflict_detector = ConflictDetector() # Initialize without LLM for now, or inject if needed
        self.is_running = False
        self._job_failures: dict[str, int] = {}  # Track consecutive failures per job
        
    def start(self):
        """Start the background monitor."""
        if self.is_running:
            return
            
        logger.info("Starting Continuous Monitor...")

        # Visibility: warn (once, at startup) if the Attendee meeting-bot env vars
        # are unset so bot dispatch / webhook verification isn't a silent no-op.
        try:
            settings.log_attendee_config_status()
        except Exception as cfg_e:
            logger.debug(f"Attendee config status check failed: {cfg_e}")

        # Wire up error listener for crash resilience
        self.scheduler.add_listener(self._on_job_event, EVENT_JOB_ERROR | EVENT_JOB_MISSED)
        
        # ── Governance scans — DISABLED (re-enable when needed) ─────────
        # These consume LLM tokens. Not needed for core meeting lifecycle.
        #
        # self.scheduler.add_job(
        #     self.scan_scheduling_conflicts,
        #     trigger=IntervalTrigger(minutes=30),
        #     id="scan_scheduling", replace_existing=True
        # )
        # self.scheduler.add_job(
        #     self.scan_policy_divergences,
        #     trigger=IntervalTrigger(minutes=60),
        #     id="scan_policy", replace_existing=True
        # )
        # self.scheduler.add_job(
        #     self.check_twg_health,
        #     trigger=IntervalTrigger(hours=1),
        #     id="health_check", replace_existing=True
        # )
        # self.scheduler.add_job(
        #     self.scan_project_conflicts,
        #     trigger=IntervalTrigger(hours=6),
        #     id="scan_projects", replace_existing=True
        # )

        # 6. Dispatch Attendee bots to upcoming meetings (every 60s)
        self.scheduler.add_job(
            self.dispatch_attendee_bots,
            trigger=IntervalTrigger(seconds=60),
            id="attendee_bot_dispatch",
            replace_existing=True,
            misfire_grace_time=60
        )

        # 7. Check Pending Transcripts (safety-net poll; webhooks are primary delivery)
        self.scheduler.add_job(
            self.check_pending_transcripts,
            trigger=IntervalTrigger(minutes=settings.ATTENDEE_POLL_INTERVAL_MINUTES),
            id="attendee_transcript_check",
            replace_existing=True,
            misfire_grace_time=120
        )

        # 7. Sync Pending Calendar Links (Every 30 seconds)
        self.scheduler.add_job(
            self.sync_pending_calendar_events,
            trigger=IntervalTrigger(seconds=30),
            id="calendar_sync_check",
            replace_existing=True,
            misfire_grace_time=60  # tolerate up to 60s delay from LLM calls
        )
        
        # 8. Google Drive Transcript Fallback (Every 60 minutes — webhook is primary)
        self.scheduler.add_job(
            self.check_drive_transcripts_fallback,
            trigger=IntervalTrigger(minutes=60),
            id="drive_transcript_fallback",
            replace_existing=True,
            misfire_grace_time=300  # tolerate up to 5 min delay
        )
        
        # 9. Auto-Complete Past Meetings (Every hour)
        self.scheduler.add_job(
            self.auto_complete_past_meetings,
            trigger=IntervalTrigger(hours=1),
            id="auto_complete_meetings",
            replace_existing=True,
            misfire_grace_time=300  # tolerate up to 5 min delay
        )

        # 10. Scan for stalled sub-groups (R4) — alerts the sub-group lead when
        # a group is "stalling". Opens its own session via get_db_session_context
        # and de-duplicates alerts within ALERT_DEDUP_HOURS (24h), so the 6h
        # interval will not spam leads.
        self.scheduler.add_job(
            scan_stalled_subgroups,
            trigger=IntervalTrigger(hours=6),
            id="scan_stalled_subgroups",
            replace_existing=True,
            misfire_grace_time=300  # tolerate up to 5 min delay
        )

        # 11. Weekly invite dispatch (Mon 06:00 EAT). Celery beat is NOT deployed
        # in this environment, so the weekly dispatch lives here, in-process. The
        # task is gated (INVITE_DISPATCH_ENABLED), advisory-locked (safe across the
        # multiple web instances that run this monitor), and idempotent (skips
        # meetings that already have participants). misfire_grace_time covers a
        # restart across the 06:00 mark.
        self.scheduler.add_job(
            self.dispatch_weekly_invites,
            trigger=CronTrigger(day_of_week="mon", hour=6, minute=0, timezone="Africa/Nairobi"),
            id="weekly_invite_dispatch",
            replace_existing=True,
            misfire_grace_time=3600
        )

        # 12. RSVP sync (every 10 min). Pulls attendee responses from Google
        # Calendar into rsvp_status so the platform reflects accepts/declines.
        # (The Celery sync_rsvps task never runs — no beat — and matched events
        # by an extended property the TWG events don't carry.)
        self.scheduler.add_job(
            self.sync_meeting_rsvps,
            trigger=IntervalTrigger(minutes=10),
            id="rsvp_sync",
            replace_existing=True,
            misfire_grace_time=300
        )

        self.scheduler.start()
        self.is_running = True
        logger.info("Continuous Monitor started.")

    def stop(self):
        """Stop the background monitor."""
        if self.is_running:
            self.scheduler.shutdown()
            self.is_running = False
            logger.info("Continuous Monitor stopped.")

    def _on_job_event(self, event):
        """Handle APScheduler job errors and misses."""
        job_id = event.job_id
        if hasattr(event, 'exception') and event.exception:
            self._job_failures[job_id] = self._job_failures.get(job_id, 0) + 1
            logger.error(
                f"Background job '{job_id}' FAILED "
                f"(consecutive: {self._job_failures[job_id]}): {event.exception}",
                exc_info=event.traceback is not None
            )
        else:
            # Job was missed (scheduler was busy)
            logger.warning(f"Background job '{job_id}' MISSED its scheduled run")

    async def dispatch_weekly_invites(self):
        """Weekly (Mon 06:00 EAT) TWG invite dispatch. Delegates to the shared,
        advisory-locked core so it is safe to run in every web instance."""
        from app.tasks.recurring_tasks import run_weekly_invite_dispatch
        result = await run_weekly_invite_dispatch()
        logger.info(f"[invite-dispatch] weekly run result: {result}")
        return result

    async def sync_meeting_rsvps(self):
        """
        Pull attendee RSVP responses from Google Calendar into rsvp_status.

        The platform previously never reflected RSVPs: the only sync (tasks.py
        sync_rsvps) is a Celery task and Celery beat is not deployed, and it
        matched events by privateExtendedProperty — which the directly-created
        TWG events don't carry. This in-process job matches events the robust way
        (hangoutLink == video_link, or "ID: <meeting_id>" in the description) and
        reads the response as the organizer (Joseph) via the DWD service account,
        so it works for every meeting the platform manages.
        """
        import os, json
        raw = (os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON") or "").strip()
        subject = getattr(settings, "GOOGLE_IMPERSONATE_EMAIL", None) or os.environ.get("GOOGLE_IMPERSONATE_EMAIL")
        if not raw or not subject:
            return  # DWD not configured in this environment — nothing to sync

        gmap = {
            "accepted": RsvpStatus.ACCEPTED,
            "declined": RsvpStatus.DECLINED,
            "tentative": RsvpStatus.TENTATIVE,
            "needsAction": RsvpStatus.PENDING,
        }

        def _fetch_rsvps(scheduled_at, meeting_id, video_link):
            """Blocking Google call — run inside _gcal_executor. Returns
            {email_lower: responseStatus} or None on hard failure."""
            from google.oauth2 import service_account
            from googleapiclient.discovery import build
            creds = service_account.Credentials.from_service_account_info(
                json.loads(raw), scopes=["https://www.googleapis.com/auth/calendar"]
            ).with_subject(subject)
            svc = build("calendar", "v3", credentials=creds, cache_discovery=False)
            d0 = scheduled_at.strftime("%Y-%m-%dT00:00:00Z")
            d1 = (scheduled_at + timedelta(days=1)).strftime("%Y-%m-%dT00:00:00Z")
            evs = svc.events().list(calendarId="primary", timeMin=d0, timeMax=d1,
                                    singleEvents=True, maxResults=250).execute().get("items", [])
            ev = next((e for e in evs if (e.get("hangoutLink") or "") == video_link
                       or f"ID: {meeting_id}" in (e.get("description") or "")), None)
            if not ev:
                return {}
            return {a["email"].lower(): a.get("responseStatus")
                    for a in ev.get("attendees", []) if a.get("email")}

        now = datetime.utcnow()
        lo = now - timedelta(days=2)      # keep syncing briefly past-due for late RSVPs
        hi = now + timedelta(days=21)
        loop = asyncio.get_running_loop()
        updated = 0
        async with get_db_session_context() as db:
            res = await db.execute(
                select(Meeting).where(
                    Meeting.status == MeetingStatus.SCHEDULED,
                    Meeting.scheduled_at >= lo,
                    Meeting.scheduled_at <= hi,
                    Meeting.video_link.isnot(None),
                ).options(selectinload(Meeting.participants))
            )
            meetings = [m for m in res.scalars().all() if m.participants]
            if not meetings:
                return
            for m in meetings:
                try:
                    rsvps = await loop.run_in_executor(
                        _gcal_executor,
                        lambda sa=m.scheduled_at, mid=m.id, vl=m.video_link: _fetch_rsvps(sa, mid, vl)
                    )
                    if not rsvps:
                        continue
                    changed = False
                    for p in m.participants:
                        if p.email and p.email.lower() in rsvps:
                            ns = gmap.get(rsvps[p.email.lower()], RsvpStatus.PENDING)
                            if p.rsvp_status != ns:
                                p.rsvp_status = ns
                                changed = True
                    if changed:
                        await db.commit()
                        updated += 1
                except Exception as e:
                    await db.rollback()
                    logger.error(f"[rsvp-sync] failed for meeting {m.id}: {e}")
        if updated:
            logger.info(f"[rsvp-sync] updated RSVPs for {updated} meeting(s)")

    async def sync_pending_calendar_events(self):
        """
        Check for virtual meetings that are missing a video link and generate one.
        This enables async link generation so the Agent can respond immediately.
        """
        logger.info("Checking for pending calendar links...")
        from app.services.calendar_service import calendar_service
        
        async with get_db_session_context() as db:
            try:
                # Find meetings that are:
                # 1. Future (or recent past)
                # 2. Virtual (Location contains 'Virtual' or 'Online')
                # 3. Missing valid video_link (None, empty, or 'Pending')
                
                now = datetime.utcnow()
                # Look back 24h just in case, look forward indefinitely
                lookback = now - timedelta(hours=24)
                
                stmt = select(Meeting).where(
                    and_(
                        Meeting.scheduled_at >= lookback,
                        Meeting.status != MeetingStatus.CANCELLED,
                        # Skip recurring instances — handled by recurring_meeting_service background tasks
                        Meeting.recurring_meeting_id.is_(None),
                        or_(
                            Meeting.location.ilike("%Virtual%"),
                            Meeting.location.ilike("%Online%"),
                            Meeting.location.ilike("%Meet%"),
                            Meeting.location.ilike("%Zoom%")
                        ),
                        or_(
                            Meeting.video_link.is_(None),
                            Meeting.video_link == "",
                            Meeting.video_link.ilike("%Pending%")
                        )
                    )
                )
                
                result = await db.execute(stmt)
                meetings = result.scalars().all()
                
                if not meetings:
                    return

                logger.info(f"Found {len(meetings)} meetings needing Google Meet links.")
                
                for meeting in meetings:
                    logger.info(f"Generating link for meeting: {meeting.title} ({meeting.id})")

                    # Check if a Google Calendar event already exists for this meeting
                    # to prevent creating duplicates
                    import asyncio
                    loop = asyncio.get_running_loop()

                    existing_event = await loop.run_in_executor(
                        _gcal_executor,
                        lambda m=meeting: calendar_service.get_meeting_event(str(m.id))
                    )

                    if existing_event:
                        # Event exists — just grab the link, don't create a duplicate
                        video_link = existing_event.get('hangoutLink') or existing_event.get('htmlLink')
                        if video_link:
                            meeting.video_link = video_link
                            flag_modified(meeting, "video_link")
                            await db.commit()
                            logger.info(f"✓ Found existing event, linked: {video_link}")
                            continue

                    # Fetch participant emails for this meeting
                    participant_result = await db.execute(
                        select(User.email).join(
                            MeetingParticipant, MeetingParticipant.user_id == User.id
                        ).where(MeetingParticipant.meeting_id == meeting.id)
                    )
                    attendee_emails = [row[0] for row in participant_result.all() if row[0]]

                    event = await loop.run_in_executor(
                        _gcal_executor,
                        lambda m=meeting, emails=attendee_emails: calendar_service.create_meeting_event(
                            title=m.title,
                            start_time=m.scheduled_at,
                            duration_minutes=m.duration_minutes,
                            description=f"Generated by Martin AI. ID: {m.id}",
                            attendees=emails,
                            meeting_id=str(m.id)
                        )
                    )

                    if event and event.get('htmlLink'):
                        video_link = event.get('hangoutLink')
                        if not video_link:
                             video_link = event.get('htmlLink')

                        meeting.video_link = video_link

                        if meeting.location and "Pending" in meeting.location:
                            meeting.location = meeting.location.replace("(Pending Link)", "").strip()
                            if meeting.location == "Virtual":
                                 meeting.location = "Virtual (Google Meet)"

                        logger.info(f"✓ Link generated: {video_link}")

                        flag_modified(meeting, "video_link")
                        await db.commit()
                    else:
                        logger.warning(f"Failed to generate link for {meeting.title}. Token might be invalid.")
                        
            except Exception as e:
                logger.error(f"Error syncing calendar links: {e}")

    async def _resolve_bot_alert_recipient(self, meeting: Meeting, db: AsyncSession) -> Optional[UUID]:
        """Best-effort: find a user to notify about a meeting-bot dispatch problem.

        Prefers the meeting's TWG technical lead, then any ADMIN/SECRETARIAT_LEAD.
        Returns None if no recipient can be resolved (caller then logs only).
        """
        try:
            twg = await db.get(TWG, meeting.twg_id) if meeting.twg_id else None
            if twg and getattr(twg, "technical_lead_id", None):
                return twg.technical_lead_id
        except Exception as e:
            logger.debug(f"Could not resolve TWG lead for bot alert: {e}")
        try:
            from app.models.models import UserRole
            stmt = (
                select(User.id)
                .where(User.role.in_([UserRole.SECRETARIAT_LEAD, UserRole.ADMIN]))
                .limit(1)
            )
            res = await db.execute(stmt)
            return res.scalars().first()
        except Exception as e:
            logger.debug(f"Could not resolve admin fallback for bot alert: {e}")
            return None

    async def _notify_bot_dispatch_issue(self, meeting: Meeting, reason: str, db: AsyncSession):
        """Surface a meeting that should have had a bot but didn't, via a notification.

        Non-destructive: best-effort recipient resolution; if none is found we
        only log. Failures here never affect the dispatch path.
        """
        try:
            link = f"/meetings/{meeting.id}"
            # Idempotent: do not re-alert if an alert for this meeting already exists.
            existing = await db.execute(
                select(Notification.id).where(
                    and_(
                        Notification.link == link,
                        Notification.title == "Meeting bot not dispatched",
                    )
                ).limit(1)
            )
            if existing.scalars().first():
                logger.debug(f"Bot-dispatch alert already exists for '{meeting.title}', skipping")
                return

            user_id = await self._resolve_bot_alert_recipient(meeting, db)
            if not user_id:
                logger.warning(
                    f"Meeting bot not dispatched for '{meeting.title}' ({reason}); "
                    f"no recipient resolved for alert notification"
                )
                return
            from app.services.notification_service import create_notification
            await create_notification(
                db=db,
                user_id=user_id,
                type=NotificationType.WARNING,
                title="Meeting bot not dispatched",
                content=(
                    f"Martin could not send a recording bot to '{meeting.title}'. "
                    f"Reason: {reason}. Minutes will not be auto-generated for this meeting "
                    f"unless a transcript is provided manually."
                ),
                link=f"/meetings/{meeting.id}",
            )
            logger.info(f"Bot-dispatch alert notification created for '{meeting.title}' ({reason})")
        except Exception as e:
            logger.error(f"Failed to create bot-dispatch alert for '{meeting.title}': {e}")

    async def _notify_meetings_missing_bot_link(self, db: AsyncSession):
        """Alert on meetings that are about to start but can't get a bot (no usable link).

        These never enter the dispatch query (which requires a video_link), so
        without this they would be silently skipped. Idempotent: skips a meeting
        if a matching alert notification (same /meetings/{id} link) already exists,
        so the 60s cadence does not produce duplicate alerts. Non-destructive —
        only reads meetings and inserts notifications.
        """
        try:
            now = datetime.utcnow()
            dispatch_window = now + timedelta(minutes=settings.ATTENDEE_DISPATCH_MINUTES_BEFORE)
            stmt = select(Meeting).where(
                and_(
                    Meeting.scheduled_at <= dispatch_window,
                    Meeting.scheduled_at >= now - timedelta(minutes=5),
                    or_(Meeting.video_link.is_(None), Meeting.video_link == ""),
                    Meeting.attendee_bot_id.is_(None),
                    Meeting.status == MeetingStatus.SCHEDULED,
                )
            )
            result = await db.execute(stmt)
            linkless = result.scalars().all()
            for meeting in linkless:
                link = f"/meetings/{meeting.id}"
                # De-dup: skip if we already raised this exact alert.
                existing = await db.execute(
                    select(Notification.id).where(
                        and_(
                            Notification.link == link,
                            Notification.title == "Meeting bot not dispatched",
                        )
                    ).limit(1)
                )
                if existing.scalars().first():
                    continue
                await self._notify_bot_dispatch_issue(
                    meeting,
                    "no video link (in-person or link not yet provisioned)",
                    db,
                )
        except Exception as e:
            logger.error(f"Error checking meetings missing bot link: {e}")

    async def dispatch_attendee_bots(self):
        """
        Dispatch Attendee bots to upcoming meetings.
        Runs every 60 seconds. Finds meetings starting within ATTENDEE_DISPATCH_MINUTES_BEFORE
        that have a video_link but no attendee_bot_id yet.
        """
        async with get_db_session_context() as db:
            try:
                now = datetime.utcnow()
                dispatch_window = now + timedelta(minutes=settings.ATTENDEE_DISPATCH_MINUTES_BEFORE)

                stmt = select(Meeting).where(
                    and_(
                        Meeting.scheduled_at <= dispatch_window,
                        Meeting.scheduled_at >= now - timedelta(minutes=5),  # Don't dispatch for meetings that started >5 min ago
                        Meeting.video_link.isnot(None),
                        Meeting.video_link != "",
                        Meeting.attendee_bot_id.is_(None),
                        Meeting.status == MeetingStatus.SCHEDULED,
                    )
                )
                result = await db.execute(stmt)
                meetings = result.scalars().all()

                if meetings:
                    logger.info(f"Dispatching Attendee bots for {len(meetings)} upcoming meetings")

                    for meeting in meetings:
                        try:
                            bot_id = await attendee_service.dispatch_bot(
                                meeting_url=meeting.video_link,
                                meeting_id=str(meeting.id),
                            )
                            if bot_id:
                                meeting.attendee_bot_id = bot_id
                                await db.commit()
                                logger.info(f"Dispatched Attendee bot {bot_id} for '{meeting.title}'")
                            else:
                                logger.warning(f"Failed to dispatch Attendee bot for '{meeting.title}'")
                                await self._notify_bot_dispatch_issue(
                                    meeting, "dispatch returned no bot id (Attendee API may be unreachable)", db
                                )
                        except Exception as e:
                            logger.error(f"Error dispatching bot for '{meeting.title}': {e}")
                            await self._notify_bot_dispatch_issue(
                                meeting, f"dispatch error: {e}", db
                            )

                # Surface meetings that should have had a bot but have no usable link
                # (in-person / link not yet provisioned) — otherwise silently skipped.
                await self._notify_meetings_missing_bot_link(db)

            except Exception as e:
                logger.error(f"Error in dispatch_attendee_bots: {e}")
                import traceback
                logger.error(traceback.format_exc())

    async def check_pending_transcripts(self):
        """
        Safety-net poll for Attendee transcripts.
        Primary delivery is via the /api/v1/webhooks/attendee webhook.
        This poll catches any transcripts missed by the webhook path.
        """
        rl_status = attendee_service.get_rate_limit_status()
        if rl_status["is_rate_limited"]:
            logger.info(
                f"Skipping Attendee poll — rate-limited for {rl_status['seconds_remaining']}s "
                f"(consecutive failures: {rl_status['consecutive_failures']})"
            )
            return

        logger.info("Checking pending Attendee transcripts (safety-net poll)...")
        async with get_db_session_context() as db:
            try:
                start_window = datetime.utcnow() - timedelta(hours=24)

                # Find meetings with a bot dispatched but no transcript yet
                stmt = select(Meeting).options(
                    selectinload(Meeting.twg),
                    selectinload(Meeting.minutes),
                    selectinload(Meeting.participants).selectinload(MeetingParticipant.user),
                ).where(
                    and_(
                        Meeting.attendee_bot_id.isnot(None),
                        Meeting.scheduled_at >= start_window,
                        or_(Meeting.transcript.is_(None), Meeting.transcript == ""),
                        Meeting.status.in_([MeetingStatus.IN_PROGRESS, MeetingStatus.COMPLETED, MeetingStatus.SCHEDULED]),
                    )
                )
                result = await db.execute(stmt)
                candidate_meetings = result.scalars().all()

                if not candidate_meetings:
                    logger.debug("No pending meetings found for Attendee transcript check")
                    return

                logger.info(f"Found {len(candidate_meetings)} meetings to check for Attendee transcripts")

                for meeting in candidate_meetings:
                    try:
                        # Check bot status
                        bot_status = await attendee_service.get_bot_status(meeting.attendee_bot_id)
                        if not bot_status:
                            continue

                        state = bot_status.get("state", bot_status.get("status", ""))
                        logger.debug(f"Bot {meeting.attendee_bot_id} state: {state}")

                        if state == "fatal_error":
                            logger.error(f"Bot {meeting.attendee_bot_id} fatal error for '{meeting.title}'")
                            continue

                        if state not in ("ended", "post_processing", "done", "completed"):
                            continue

                        # Bot has ended — fetch transcript
                        transcript_data = await attendee_service.get_transcript(meeting.attendee_bot_id)
                        if not transcript_data:
                            logger.debug(f"Transcript not ready yet for bot {meeting.attendee_bot_id}")
                            continue

                        transcript_text = attendee_service.format_transcript_text(transcript_data)
                        if not transcript_text:
                            logger.warning(f"Formatted transcript is empty for '{meeting.title}'")
                            continue

                        logger.info(f"Processing transcript for '{meeting.title}' ({len(transcript_text)} chars)")

                        file_path = await attendee_service.process_transcript_text(meeting, transcript_text, db)

                        if file_path:
                            meeting.status = MeetingStatus.COMPLETED
                            logger.info(f"Meeting '{meeting.title}' status updated to COMPLETED")

                            res_u = await db.execute(select(User.id).limit(1))
                            uploader_id = res_u.scalars().first()
                            if uploader_id:
                                doc = Document(
                                    twg_id=meeting.twg_id,
                                    meeting_id=meeting.id,
                                    file_name=f"Attendee Transcript - {meeting.title}.txt",
                                    file_path=str(file_path) if isinstance(file_path, str) else f"attendee/{meeting.attendee_bot_id}",
                                    file_type="text/plain",
                                    document_type="transcript",
                                    uploaded_by_id=uploader_id,
                                    metadata_json={
                                        "provider": "attendee",
                                        "bot_id": meeting.attendee_bot_id,
                                        "meeting_id": str(meeting.id),
                                    },
                                )
                                db.add(doc)

                            await db.commit()

                            if settings.ATTENDEE_REQUIRE_MINUTES_REVIEW:
                                # SAFE default: leave minutes in the human approval queue
                                # via the existing review mechanism; do not auto-email.
                                try:
                                    if meeting.minutes:
                                        await db.refresh(meeting.minutes)
                                        from app.models.models import MinutesStatus
                                        meeting.minutes.status = MinutesStatus.PENDING_APPROVAL
                                        await db.commit()
                                    logger.info(
                                        f"Minutes for '{meeting.title}' left PENDING_APPROVAL for human review "
                                        f"(ATTENDEE_REQUIRE_MINUTES_REVIEW=True)"
                                    )
                                except Exception as review_e:
                                    logger.error(f"Failed to mark minutes pending review: {review_e}")
                                    import traceback
                                    logger.error(traceback.format_exc())
                            else:
                                # Finalize and distribute (legacy behavior)
                                try:
                                    logger.info(f"Finalizing and distributing minutes for '{meeting.title}'...")
                                    await attendee_service.finalize_and_distribute_minutes(meeting, db)
                                    await db.commit()
                                except Exception as dist_e:
                                    logger.error(f"Failed to finalize/distribute minutes: {dist_e}")
                                    import traceback
                                    logger.error(traceback.format_exc())

                            # Broadcast update
                            try:
                                from app.services.broadcast_service import get_broadcast_service
                                broadcast = get_broadcast_service()
                                await broadcast.notify_meeting_update(meeting.id, {"status": "COMPLETED", "has_transcript": True})
                            except Exception as be:
                                logger.error(f"Broadcast failed: {be}")
                        else:
                            logger.error(f"Failed to process transcript for '{meeting.title}'")

                    except Exception as me:
                        logger.error(f"Error processing meeting '{meeting.title}': {me}")
                        import traceback
                        logger.error(traceback.format_exc())

            except Exception as e:
                logger.error(f"Error checking Attendee transcripts: {e}")
                import traceback
                traceback.print_exc()

    async def check_drive_transcripts_fallback(self):
        """
        Fallback system: Check Google Drive Meet Recordings folder for transcripts.
        This catches meetings where the primary webhook path missed a transcript.
        Runs every 60 minutes (webhook is the primary delivery mechanism).
        """
        logger.info("Checking Google Drive for transcript fallbacks...")
        try:
            from app.services.drive_service import drive_service
            await drive_service.process_drive_transcripts_fallback()
        except Exception as e:
            logger.error(f"Error in Drive transcript fallback: {e}")

    async def auto_complete_past_meetings(self):
        """
        Auto-complete meetings that have ended but are still in SCHEDULED status.
        This handles meetings without Vexa transcripts or where transcript processing failed.
        Runs every hour.
        """
        logger.info("Auto-completing past meetings...")
        async with get_db_session_context() as db:
            try:
                from datetime import datetime, timedelta
                
                # Find meetings that:
                # 1. Are in SCHEDULED or IN_PROGRESS status
                # 2. Have ended (scheduled_at + duration < now)
                # 3. Are not cancelled
                
                now = datetime.utcnow()
                
                # Query meetings that should be completed
                # We need to calculate end_time = scheduled_at + duration_minutes
                # SQLAlchemy doesn't have a direct way to add minutes in the query,
                # so we'll fetch candidates and filter in Python
                
                stmt = select(Meeting).where(
                    and_(
                        Meeting.status.in_([MeetingStatus.SCHEDULED, MeetingStatus.IN_PROGRESS]),
                        Meeting.scheduled_at < now  # At least started
                    )
                )
                
                result = await db.execute(stmt)
                meetings = result.scalars().all()
                
                completed_count = 0
                
                for meeting in meetings:
                    # Calculate end time
                    end_time = meeting.scheduled_at + timedelta(minutes=meeting.duration_minutes)
                    
                    # Check if meeting has ended
                    if end_time < now:
                        logger.info(f"Auto-completing meeting: {meeting.title} (ID: {meeting.id}, ended at {end_time})")
                        meeting.status = MeetingStatus.COMPLETED
                        completed_count += 1
                
                if completed_count > 0:
                    await db.commit()
                    logger.info(f"✓ Auto-completed {completed_count} past meetings")
                else:
                    logger.info("No meetings to auto-complete")
                    
            except Exception as e:
                logger.error(f"Error in auto_complete_past_meetings: {e}")


    async def scan_scheduling_conflicts(self):
        """
        Check for:
        - Overlapping meetings for same TWG
        - VIP double bookings (simplified check for now)
        - Venue conflicts
        """
        logger.info("Running scan_scheduling_conflicts...")
        async with get_db_session_context() as db:
            try:
                # 1. Fetch upcoming meetings with participants loaded
                # Fix: Use naive UTC to match DB TIMESTAMP WITHOUT TIME ZONE
                stmt = select(Meeting).where(Meeting.scheduled_at > datetime.utcnow(), Meeting.status != MeetingStatus.CANCELLED).options(
                    selectinload(Meeting.participants).selectinload(MeetingParticipant.user).selectinload(User.vip_profile)
                )
                result = await db.execute(stmt)
                meetings = result.scalars().all()
                
                # Check for overlaps
                conflicts_found = []
                for i in range(len(meetings)):
                    for j in range(i + 1, len(meetings)):
                        m1 = meetings[i]
                        m2 = meetings[j]
                        
                        # Overlap logic: (StartA < EndB) and (EndA > StartB)
                        # We need end time. computed from duration
                        m1_end = m1.scheduled_at + timedelta(minutes=m1.duration_minutes)
                        m2_end = m2.scheduled_at + timedelta(minutes=m2.duration_minutes)
                        
                        if (m1.scheduled_at < m2_end) and (m1_end > m2.scheduled_at):
                            reason = ""
                            severity = ConflictSeverity.LOW
                            
                            # Physical Venue Conflict? (Exclude virtual venues - unlimited capacity)
                            if (m1.location and m2.location and 
                                m1.location == m2.location and 
                                m1.location.lower() not in ['virtual', 'online', 'remote']):
                                reason = f"Venue conflict at {m1.location}"
                                severity = ConflictSeverity.HIGH
                            
                            # Same TWG Double Booking? (Check independently - applies to both physical and virtual)
                            if m1.twg_id == m2.twg_id:
                                reason = "Double booking for TWG"
                                severity = ConflictSeverity.MEDIUM

                            # Shared Participants / VIP Conflict
                            # Get sets of user IDs to find intersection
                            p1_map = {p.user_id: p.user for p in m1.participants if p.user}
                            p2_map = {p.user_id: p.user for p in m2.participants if p.user}
                            
                            shared_user_ids = set(p1_map.keys()) & set(p2_map.keys())
                            if shared_user_ids:
                                shared_users = [p1_map[uid] for uid in shared_user_ids]
                                participant_severity, description = self._calculate_severity(shared_users)
                                
                                # Escalate if participant severity is higher
                                severity_levels = {
                                    ConflictSeverity.LOW: 1, 
                                    ConflictSeverity.MEDIUM: 2, 
                                    ConflictSeverity.HIGH: 3, 
                                    ConflictSeverity.CRITICAL: 4
                                }
                                if severity_levels.get(participant_severity, 1) > severity_levels.get(severity, 1):
                                    severity = participant_severity
                                    reason = f"{reason}; {description}" if reason else description
                                else:
                                    if reason:
                                         reason += f"; {description}"
                                    else:
                                         reason = description

                            if reason:
                                logger.warning(f"Conflict found: {reason} between {m1.title} and {m2.title}")
                                
                                # Auto-handle conflict
                                await self._handle_detected_conflicts(
                                    db_session=db, 
                                    conflict_data = {
                                        "description": f"{reason} between {m1.title} and {m2.title}",
                                        "conflict_type": ConflictType.SCHEDULE_CLASH,
                                        "severity": severity,
                                        "conflicting_positions": {
                                            "meeting_1": str(m1.id),
                                            "meeting_2": str(m2.id),
                                            "reason": reason
                                        }
                                    },
                                    agents_involved=[str(m1.twg_id), str(m2.twg_id)] # Assuming twg_id is what we need, or name
                                )
                                
            except Exception as e:
                import traceback
                traceback.print_exc()
                logger.error(f"Error in scheduling scan: {e}")

    def _calculate_severity(self, shared_participants: List[User]) -> Tuple[str, str]:
        """
        Calculate severity based on shared participants.
        Returns (severity, description)
        """
        vips = []
        ministers = []
        directors = []
        
        for p in shared_participants:
            # Check for Minister
            is_minister = False
            # Check Role
            if p.role == "secretariat_lead": # Example mapping
                pass 
            
            # Check VIP Profile
            if p.vip_profile:
                vips.append(p)
                title = p.vip_profile.title.lower() if p.vip_profile.title else ""
                if "minister" in title or "head of state" in title:
                    ministers.append(p)
                    is_minister = True
                elif "director" in title or "commissioner" in title:
                    directors.append(p)
            
            # Fallback simple role check if no profile but role says something?
            # Assuming Role enum doesn't have MINISTER directly, using VipProfile
            
        if ministers:
            names = ", ".join([u.full_name for u in ministers])
            return ConflictSeverity.CRITICAL, f"Minister(s) double-booked: {names}"
        
        if directors:
             names = ", ".join([u.full_name for u in directors])
             return ConflictSeverity.HIGH, f"Director(s)/High-level VIPs double-booked: {names}"
             
        if len(shared_participants) > 10:
             return ConflictSeverity.HIGH, f"Large group overlap ({len(shared_participants)} participants)"
             
        if len(shared_participants) > 3:
             return ConflictSeverity.MEDIUM, f"Multiple participants overlap ({len(shared_participants)} people)"
             
        # confirmed overlap <= 3 regular people
        names = ", ".join([u.full_name for u in shared_participants])
        return ConflictSeverity.LOW, f"Participant overlap: {names}"

    async def _handle_detected_conflicts(
        self, 
        db_session: AsyncSession, 
        conflict_data: dict,
        agents_involved: List[str]
    ):
        """
        Autonomous conflict handling.
        1. Save to DB
        2. Notify involved TWG Leads (Feedback Loop)
        3. Trigger auto-negotiation
        """
        try:
            # DEDUPLICATION CHECK
            # Check if an active conflict with the same description already exists
            stmt = select(Conflict).where(
                and_(
                    Conflict.description == conflict_data["description"],
                    Conflict.conflict_type == conflict_data["conflict_type"],
                    Conflict.status.in_([ConflictStatus.DETECTED, ConflictStatus.NEGOTIATING, ConflictStatus.ESCALATED])
                )
            )
            result = await db_session.execute(stmt)
            existing_conflict = result.scalars().first()

            if existing_conflict:
                logger.debug(f"Skipping duplicate conflict: {conflict_data['description']} (ID: {existing_conflict.id})")
                return

            # Create Conflict Record
            conflict = Conflict(
                conflict_type=conflict_data["conflict_type"],
                severity=conflict_data["severity"],
                description=conflict_data["description"],
                agents_involved=[str(a) for a in agents_involved],
                conflicting_positions=conflict_data.get("conflicting_positions", {}),
                status=ConflictStatus.DETECTED,
                detected_at=datetime.utcnow(),
                metadata_json=conflict_data # Store full data in metadata
            )
            db_session.add(conflict)
            await db_session.flush() # Get ID
            
            # NOTIFICATION LOGIC (Supervisor -> TWG Feedback)
            logger.info(f"Notifying agents for Conflict {conflict.id}")
            resolved_agents_involved = []
            
            for agent_id_str in agents_involved:
                try:
                    # Resolve TWG UUID or Name
                    twg_obj = None
                    try:
                        # Try parsing as UUID first
                        val_uuid = UUID(agent_id_str)
                        stmt = select(TWG).where(TWG.id == val_uuid)
                        result = await db_session.execute(stmt)
                        twg_obj = result.scalar_one_or_none()
                    except (ValueError, TypeError):
                        # Not a valid UUID, try resolving by name
                        stmt = select(TWG).where(TWG.name == agent_id_str)
                        result = await db_session.execute(stmt)
                        twg_obj = result.scalar_one_or_none()
                    
                    if twg_obj:
                        resolved_agents_involved.append(str(twg_obj.id))
                        if twg_obj.technical_lead_id:
                            # Create Notification
                            notification = Notification(
                                user_id=twg_obj.technical_lead_id,
                                type=NotificationType.ALERT,
                                title="Supervisor Insight: Conflict Detected",
                                content=f"The Supervisor has detected a {conflict.conflict_type} that affects your TWG: {conflict.description}",
                                link=f"/conflicts/{conflict.id}",
                                is_read=False,
                                created_at=datetime.utcnow()
                            )
                            db_session.add(notification)
                            logger.info(f"Notification queued for TWG {twg_obj.name} (Lead: {twg_obj.technical_lead_id})")
                        else:
                            logger.warning(f"Could not notify TWG {twg_obj.name}: Lead not found")
                    else:
                        logger.warning(f"Could not resolve agent identifier: {agent_id_str}")
                        # Keep original string if resolution fails, though it might cause issues later
                        resolved_agents_involved.append(agent_id_str)
                        
                except Exception as ex:
                    logger.error(f"Failed to process agent identifier {agent_id_str}: {ex}")

            # Update conflict with resolved UUIDs if they changed
            if resolved_agents_involved != conflict.agents_involved:
                conflict.agents_involved = resolved_agents_involved
                flag_modified(conflict, "agents_involved")

            logger.info(f"Triggering auto-negotiation for Conflict {conflict.id}")
            
            # Trigger Auto-Negotiation (Background Task)
            # We offload this to Celery to avoid blocking the monitor loop
            # from app.tasks.negotiation_tasks import run_negotiation_task
            # run_negotiation_task.delay(str(conflict.id))
            # logger.info(f"Queued negotiation task for Conflict {conflict.id}")
                
            await db_session.commit()
            
        except Exception as e:
            logger.error(f"Failed to handle conflict: {e}")

    async def scan_policy_divergences(self):
        """
        Check for semantic conflicts in recent TWG outputs/documents.
        Offloaded to Celery.
        """
        from app.tasks.monitoring_tasks import scan_policy_divergences_task
        logger.info("Triggering background scan_policy_divergences task...")
        scan_policy_divergences_task.delay()

    async def check_twg_health(self):
        # Check for stalled TWGs (no activity > 48h).
        # Simulated metric for now.
        logger.info("Running check_twg_health...")
        async with get_db_session_context() as db:
            try:
                # In a real implementation:
                # 1. Check last message associated with TWG agents
                # 2. Check last document update
                # 3. Check for overdue ActionItems
                
                # For this prototype: basic connectivity check/log
                result = await db.execute(select(TWG))
                twgs = result.scalars().all()
                for twg in twgs:
                    # Log check
                    # logger.info(f"Health check for TWG: {twg.name}")
                    pass
                    
            except Exception as e:
                logger.error(f"Error in health check: {e}")

    async def scan_project_conflicts(self):
        """
        Detect dependency and duplicate conflicts for Projects.
        Runs every 6 hours.
        """
        logger.info("Running scan_project_conflicts...")
        async with get_db_session_context() as db:
            try:
                # Run detections
                dependency_conflicts = await self.conflict_detector.detect_project_dependency_conflicts(db)
                duplicate_conflicts = await self.conflict_detector.detect_duplicate_projects(db)
                
                all_conflicts = dependency_conflicts + duplicate_conflicts
                
                if not all_conflicts:
                    logger.info("No project conflicts detected.")
                    return

                logger.info(f"Detected {len(all_conflicts)} potential project conflicts")
                
                new_conflicts_count = 0
                
                for conflict in all_conflicts:
                    # Check for existing conflict (Active or Resolved recently?)
                    # Simplified check: same type and same project IDs involved
                    
                    # Extract project IDs from metadata to query
                    project_a_id = None
                    project_b_id = None
                    
                    if conflict.metadata_json:
                        if "dependent_project_id" in conflict.metadata_json:
                             project_a_id = conflict.metadata_json["dependent_project_id"]
                             project_b_id = conflict.metadata_json["prerequisite_project_id"]
                        elif "project_a_id" in conflict.metadata_json:
                             project_a_id = conflict.metadata_json["project_a_id"]
                             project_b_id = conflict.metadata_json["project_b_id"]
                    
                    # If we can't identify projects, we might skip dedupe check or use agents
                    # But assuming our detector works, we have IDs.
                    
                    if project_a_id and project_b_id:
                        # Check DB
                        # We need to query if a conflict with these project IDs exists
                        # Since metadata_json is JSONB (Postgres) or JSON, querying it might be tricky depending on DB
                        # Alternative: Filter by `agents_involved` and `conflict_type` and iterate results?
                        # Or just adding and ignoring?
                        # For now, let's try to filter by metadata if possible or fallback to python
                        
                        # Fetch all active conflicts of this type
                        stmt = select(Conflict).where(
                            and_(
                                Conflict.conflict_type == conflict.conflict_type,
                                Conflict.status.in_([ConflictStatus.DETECTED, ConflictStatus.NEGOTIATING, ConflictStatus.ESCALATED])
                            )
                        )
                        existing_result = await db.execute(stmt)
                        existing_conflicts = existing_result.scalars().all()
                        
                        is_duplicate = False
                        for exc in existing_conflicts:
                            # Check metadata match
                            e_meta = exc.metadata_json or {}
                            # Check for cross-match too? (A vs B is same as B vs A for Duplicates?)
                            # Dependencies are directional. Duplicates are bidirectional.
                            
                            if conflict.conflict_type == "duplicate_project_conflict": # String match or Enum?
                                # Check pairs
                                e_a = e_meta.get("project_a_id")
                                e_b = e_meta.get("project_b_id")
                                if {e_a, e_b} == {project_a_id, project_b_id}:
                                    is_duplicate = True
                                    break
                            else:
                                # Dependency
                                if (e_meta.get("dependent_project_id") == project_a_id and 
                                    e_meta.get("prerequisite_project_id") == project_b_id):
                                    is_duplicate = True
                                    break
                        
                        if is_duplicate:
                            continue
                            
                    # If not duplicate, add it
                    db.add(conflict)
                    new_conflicts_count += 1
                    
                    # Notify? Trigger Auto-Negotiation?
                    # The prompt suggests auto-negotiating dependencies
                    if conflict.conflict_type == "project_dependency_conflict": 
                        # We need to commit to get ID first? Or add logic here?
                        # Let's save first.
                        pass
                
                await db.commit()
                logger.info(f"Saved {new_conflicts_count} new project conflicts")
                
                # Post-save actions (Trigger negotiation/Notification)
                # We iterate again or handle above?
                # Ideally we handle after commit if we need IDs, 
                # but we can rely on ContinuousMonitor waking up again? 
                # No, better to trigger now.
                # However, complex logic might be better separated.
                        
            except Exception as e:
                logger.error(f"Error in project conflict scan: {e}")

# Singleton
_monitor_instance = None

def get_continuous_monitor() -> ContinuousMonitor:
    global _monitor_instance
    if not _monitor_instance:
        _monitor_instance = ContinuousMonitor()
    return _monitor_instance

