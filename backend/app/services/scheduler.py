from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from app.jobs.reminder_jobs import send_upcoming_meeting_reminders, check_missing_minutes, check_overdue_action_items
from app.jobs.scheduled_tasks import (
    weekly_declaration_update,
    weekly_progress_report,
    setup_event_listeners,
)
from app.tasks.action_item_reminders import send_due_soon_action_item_reminders
import logging

logger = logging.getLogger(__name__)

class SchedulerService:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        
    def start(self):
        # Add jobs
        self.scheduler.add_job(
            send_upcoming_meeting_reminders,
            trigger=IntervalTrigger(hours=1),
            id="send_meeting_reminders",
            replace_existing=True
        )
        
        self.scheduler.add_job(
            check_missing_minutes,
            trigger=IntervalTrigger(hours=24), # Run daily
            id="check_missing_minutes",
            replace_existing=True
        )

        self.scheduler.add_job(
            check_overdue_action_items,
            trigger=IntervalTrigger(hours=6),
            id="check_overdue_action_items",
            replace_existing=True
        )

        # Due-soon action item reminders (R3) — nudges owners of items due in
        # the next 24-48h. Async coroutine opening its own AsyncSessionLocal,
        # same pattern/cadence as check_overdue_action_items. Per-item AuditLog
        # dedup makes the 6h interval safe (no double-nudging).
        self.scheduler.add_job(
            send_due_soon_action_item_reminders,
            trigger=IntervalTrigger(hours=6),
            id="send_due_soon_action_item_reminders",
            replace_existing=True
        )

        # Poll Google Drive for new meeting transcripts
        from app.services.drive_service import drive_service
        self.scheduler.add_job(
            drive_service.process_new_transcripts,
            trigger=IntervalTrigger(minutes=10),
            id="drive_transcript_poll",
            replace_existing=True
        )
        
        # Weekly Declaration Update - Every Monday at 06:00 UTC
        self.scheduler.add_job(
            weekly_declaration_update,
            trigger=CronTrigger(day_of_week='mon', hour=6, minute=0),
            id="weekly_declaration_update",
            replace_existing=True
        )
        logger.info("Weekly declaration update job scheduled (Mondays 06:00 UTC)")
        
        # Weekly Progress Report - Every Sunday at 18:00 UTC
        self.scheduler.add_job(
            weekly_progress_report,
            trigger=CronTrigger(day_of_week='sun', hour=18, minute=0),
            id="weekly_progress_report",
            replace_existing=True
        )
        logger.info("Weekly progress report job scheduled (Sundays 18:00 UTC)")
        
        # Initialize event listeners for phase completion events
        setup_event_listeners()
        
        self.scheduler.start()
        logger.info("APScheduler started")
        
    def shutdown(self):
        self.scheduler.shutdown()
        logger.info("APScheduler shut down")

scheduler_service = SchedulerService()
