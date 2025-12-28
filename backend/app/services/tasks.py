from datetime import datetime, timedelta
import asyncio
from typing import List, Optional
import uuid

from backend.app.core.celery_app import celery_app
from backend.app.services.format_service import format_service
from backend.app.services.email_service import email_service
# Database access in celery tasks usually requires creating a new session manually
# Since projects.py is async, we need to run sync code or use asgiref.sync_to_async or similar wrapper
# But Celery runs in a separate process, often sync.
# For simplicity, we can use synchronous SQLAlchemy engine in tasks if needed
# OR use `asyncio.run` to call async service methods.
# Let's try `asyncio.run` wrapper.

def run_async(coro):
    return asyncio.get_event_loop().run_until_complete(coro)

# If running in worker, we might not have a loop.
# Better to use a sync wrapper with asyncio.run()

@celery_app.task
def generate_project_pdf(project_id: str, project_name: str, description: str):
    """
    Background task to generate investment memo PDF.
    In real app, we would fetch fresh data from DB.
    Here strictly formatted for demonstration.
    """
    try:
        pdf_bytes = format_service.generate_pdf(
            title=f"Investment Memo: {project_name}",
            content=description,
            footer="Confidential - ECOWAS Investment Pipeline"
        )
        # Store PDF (e.g., to S3 or disk)
        # For prototype, we just log size or save to tmp
        path = f"/tmp/{project_id}_memo.pdf"
        with open(path, "wb") as f:
            f.write(pdf_bytes)
        
        return {"status": "success", "path": path}
    except Exception as e:
        return {"status": "failed", "error": str(e)}

@celery_app.task
def send_meeting_reminders():
    """
    Periodic task to send reminders.
    Fetching DB in async within Celery is tricky. 
    Ideally, this calls an API endpoint or uses a separate sync DB session.
    Proposing a stub for now that logs checks.
    """
    print(f"Checking for meetings reminders at {datetime.now()}")
    # Real implementation would query DB for meetings in [now, now + 24h]
    # And call email_service.send_email()
    return "Checked reminders"
