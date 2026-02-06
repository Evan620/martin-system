"""
Celery Application Configuration

Production-ready task queue for background jobs with:
- Job isolation (separate worker processes)
- Rate limiting
- Automatic retries with exponential backoff
- Scalability (add more workers as needed)
"""

from celery import Celery
from celery.schedules import crontab
from app.core.config import settings

# Build broker URL
if settings.REDIS_URL:
    broker_url = settings.REDIS_URL
    result_backend = settings.REDIS_URL
else:
    broker_url = f"redis://:{settings.REDIS_PASSWORD}@{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}"
    result_backend = broker_url

# Initialize Celery app
celery_app = Celery(
    "martin_system",
    broker=broker_url,
    backend=result_backend,
)

# Celery Configuration
celery_app.conf.update(
    # Task serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # Task execution
    task_acks_late=True,  # Acknowledge task after completion
    task_reject_on_worker_lost=True,  # Retry if worker dies
    
    # Rate limiting (default for all tasks)
    task_default_rate_limit="10/m",  # 10 tasks per minute
    
    # Retry configuration
    task_autoretry_for=(Exception,),  # Auto-retry on any exception
    task_retry_kwargs={"max_retries": 3},
    task_default_retry_delay=60,  # Wait 60s before retry
    
    # Result backend
    result_expires=3600,  # Results expire after 1 hour
    
    # Worker configuration
    worker_prefetch_multiplier=1,  # Fetch one task at a time (fair distribution)
    worker_max_tasks_per_child=1000,  # Restart worker after 1000 tasks (prevent memory leaks)
    
    # Task routes (organize tasks by queue)
    task_routes={
        # Fast / Real-time Monitoring
        "app.tasks.monitoring_tasks.check_pending_transcripts": {"queue": "high_priority"},
        "app.tasks.monitoring_tasks.check_upcoming_meetings": {"queue": "high_priority"},
        
        # Negotiations (Critical but can take 10-30s)
        "app.tasks.negotiation_tasks.*": {"queue": "negotiations"},
        "app.tasks.monitoring_tasks.scan_scheduling_conflicts": {"queue": "negotiations"}, # Medium priority
        
        # Heavy Background Tasks
        "app.tasks.monitoring_tasks.scan_policy_divergences_task": {"queue": "background"},
        "app.tasks.monitoring_tasks.scan_project_conflicts": {"queue": "background"},
        "app.tasks.monitoring_tasks.check_twg_health": {"queue": "background"},
        
        # Periodic / Default
        "app.services.tasks.send_meeting_reminders": {"queue": "periodic"},
        "app.services.tasks.sync_rsvps": {"queue": "periodic"},
        "app.services.tasks.generate_project_pdf": {"queue": "formatting"},
        "app.services.scoring_tasks.rescore_project_async": {"queue": "scoring"},
    },
)

# Periodic Task Schedule (Celery Beat)
celery_app.conf.beat_schedule = {
    # Existing tasks
    "send-meeting-reminders-every-30-mins": {
        "task": "app.services.tasks.send_meeting_reminders",
        "schedule": 1800.0,  # 30 minutes
    },
    "sync-rsvps-every-15-mins": {
        "task": "app.services.tasks.sync_rsvps",
        "schedule": 900.0,  # 15 minutes
    },
    
    # ── Governance scans — DISABLED (re-enable when needed) ──────────
    # These consume LLM tokens on every run. Not needed for meeting lifecycle.
    #
    # "scan-scheduling-conflicts": {
    #     "task": "app.tasks.monitoring_tasks.scan_scheduling_conflicts",
    #     "schedule": crontab(minute="*/30"),
    # },
    # "scan-policy-divergences": {
    #     "task": "app.tasks.monitoring_tasks.scan_policy_divergences_task",
    #     "schedule": crontab(minute="0"),
    # },
    # "check-twg-health": {
    #     "task": "app.tasks.monitoring_tasks.check_twg_health",
    #     "schedule": crontab(minute="0"),
    # },
    # "scan-project-conflicts": {
    #     "task": "app.tasks.monitoring_tasks.scan_project_conflicts",
    #     "schedule": crontab(minute="0", hour="*/6"),
    # },
    # "check-upcoming-meetings": {
    #     "task": "app.tasks.monitoring_tasks.check_upcoming_meetings",
    #     "schedule": crontab(minute="*"),  # No-op (Fireflies replaced Vexa)
    # },
    # "check-pending-transcripts": {
    #     "task": "app.tasks.monitoring_tasks.check_pending_transcripts",
    #     "schedule": 10.0,  # Redundant — APScheduler handles this at 15min interval
    # },
}
