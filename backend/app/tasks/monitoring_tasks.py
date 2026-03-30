"""
Monitoring Tasks for Celery

These tasks replace the APScheduler jobs in continuous_monitor.py
Each task runs in isolation and won't block other tasks.
"""

from celery import shared_task
from loguru import logger
from app.core.database import get_db_session_context
# Note: We import ContinuousMonitor inside tasks to avoid circular imports


@shared_task(
    name="app.tasks.monitoring_tasks.scan_scheduling_conflicts",
    rate_limit="2/m",  # Max 2 per minute
    max_retries=2,
    default_retry_delay=300,  # 5 minutes
)
def scan_scheduling_conflicts():
    """Scan for scheduling conflicts between meetings"""
    logger.info("Celery task: scan_scheduling_conflicts started")
    try:
        import asyncio
        from app.services.continuous_monitor import ContinuousMonitor
        monitor = ContinuousMonitor()
        asyncio.run(monitor.scan_scheduling_conflicts())
        logger.info("Celery task: scan_scheduling_conflicts completed")
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Celery task: scan_scheduling_conflicts failed: {e}")
        raise


@shared_task(
    name="app.tasks.monitoring_tasks.scan_policy_divergences",
    rate_limit="1/h",  # Max 1 per hour (this is the expensive one)
    max_retries=2,
    default_retry_delay=600,  # 10 minutes
)
def scan_policy_divergences():
    """Scan for policy conflicts using LLM analysis"""
    logger.info("Celery task: scan_policy_divergences started")
    try:
        import asyncio
        from app.services.continuous_monitor import ContinuousMonitor
        monitor = ContinuousMonitor()
        asyncio.run(monitor.scan_policy_divergences())
        logger.info("Celery task: scan_policy_divergences completed")
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Celery task: scan_policy_divergences failed: {e}")
        raise


@shared_task(
    name="app.tasks.monitoring_tasks.check_twg_health",
    rate_limit="1/h",  # Max 1 per hour
    max_retries=2,
)
def check_twg_health():
    """Check health status of all TWGs"""
    logger.info("Celery task: check_twg_health started")
    try:
        import asyncio
        from app.services.continuous_monitor import ContinuousMonitor
        monitor = ContinuousMonitor()
        asyncio.run(monitor.check_twg_health())
        logger.info("Celery task: check_twg_health completed")
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Celery task: check_twg_health failed: {e}")
        raise


@shared_task(
    name="app.tasks.monitoring_tasks.scan_project_conflicts",
    rate_limit="1/6h",  # Max 1 per 6 hours
    max_retries=2,
)
def scan_project_conflicts():
    """Scan for project dependency and duplicate conflicts"""
    logger.info("Celery task: scan_project_conflicts started")
    try:
        import asyncio
        from app.services.continuous_monitor import ContinuousMonitor
        monitor = ContinuousMonitor()
        asyncio.run(monitor.scan_project_conflicts())
        logger.info("Celery task: scan_project_conflicts completed")
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Celery task: scan_project_conflicts failed: {e}")
        raise


@shared_task(
    name="app.tasks.monitoring_tasks.check_upcoming_meetings",
    rate_limit="60/h",  # Max 60 per hour (1 per minute)
    max_retries=1,
)
def check_upcoming_meetings():
    """Dispatch Attendee bots to upcoming meetings"""
    logger.info("Celery task: dispatch_attendee_bots started")
    try:
        import asyncio
        from app.services.continuous_monitor import ContinuousMonitor
        monitor = ContinuousMonitor()
        asyncio.run(monitor.dispatch_attendee_bots())
        logger.info("Celery task: dispatch_attendee_bots completed")
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Celery task: dispatch_attendee_bots failed: {e}")
        raise


@shared_task(
    name="app.tasks.monitoring_tasks.check_pending_transcripts",
    bind=True,
    max_retries=1  # Don't retry real-time checks too much
)
def check_pending_transcripts(self):
    """
    Celery wrapper for checking pending transcripts.
    Ideally run every 10-30 seconds via Beat.
    """
    # Simply fire-and-forget the async check
    async def _run():
        from app.services.continuous_monitor import ContinuousMonitor
        monitor = ContinuousMonitor()
        await monitor.check_pending_transcripts()
    
    try:
        import asyncio
        asyncio.run(_run())
    except Exception as e:
        logger.error(f"Error in check_pending_transcripts task: {e}")

@shared_task(
    name="app.tasks.monitoring_tasks.scan_policy_divergences_task",
    bind=True,
    max_retries=1,
    time_limit=600 # 10 minutes max for heavy LLM work
)
def scan_policy_divergences_task(self):
    """
    Heavy background task: Semantic Policy Conflict Detection.
    """
    async def _run():
        logger.info("Starting background policy scan...")
        async with get_db_session_context() as db:
            from app.services.continuous_monitor import ContinuousMonitor
            monitor = ContinuousMonitor()
            # We call the method directly. 
            # Note: ContinuousMonitor methods are instance methods but mostly use internal DB context.
            # We can instantiate it here.
            await monitor.scan_policy_divergences()
            
    try:
        import asyncio
        asyncio.run(_run())
        logger.info("Background policy scan completed.")
    except Exception as e:
        logger.error(f"Error in scan_policy_divergences_task: {e}")

        raise
