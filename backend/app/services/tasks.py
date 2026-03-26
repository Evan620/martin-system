from datetime import datetime, timedelta, timezone
import logging
from typing import List, Optional
import uuid
from sqlalchemy import select, and_

from app.core.celery_app import celery_app
from app.services.email_service import email_service
from app.services.calendar_service import calendar_service
from app.core.database import get_sync_db_session
from app.models.models import (
    Meeting, MeetingStatus, AuditLog, MeetingParticipant, RsvpStatus
)

logger = logging.getLogger(__name__)

# NOTE: Celery tasks run in a separate process/thread. 
# We use synchronous DB sessions for simplicity and stability in Celery workers.

@celery_app.task
def send_meeting_reminders():
    """
    Periodic task to send reminders for meetings starting in the next 24 hours.
    Checks AuditLog to ensure duplicate reminders are not sent.
    """
    logger.info("Starting send_meeting_reminders task")
    session = get_sync_db_session()
    try:
        now = datetime.now(timezone.utc)
        upcoming_window = now + timedelta(hours=24)
        
        # 1. Find upcoming meetings (next 24 hours) that are SCHEDULED
        # Note: We filter strictly by scheduled_at in the window
        meetings = session.execute(
            select(Meeting).where(
                and_(
                    Meeting.status == MeetingStatus.SCHEDULED,
                    Meeting.scheduled_at >= now,
                    Meeting.scheduled_at <= upcoming_window
                )
            )
        ).scalars().all()
        
        count_sent = 0
        
        for meeting in meetings:
            # 2. Check AuditLog for existing reminder
            # We look for action="reminder_sent" for this meeting resource
            existing_log = session.execute(
                select(AuditLog).where(
                    and_(
                        AuditLog.resource_id == meeting.id,
                        AuditLog.action == "reminder_sent"
                    )
                )
            ).scalars().first()
            
            if existing_log:
                logger.debug(f"Reminder already sent for meeting {meeting.id} ({meeting.title})")
                continue
            
            # 3. Send Email
            # Get participants emails
            # We need to load participants. Since we are sync, we can just access relationship if lazy loading works
            # or eager load. Safer to query.
            participants = session.execute(
                select(MeetingParticipant).where(
                    MeetingParticipant.meeting_id == meeting.id
                )
            ).scalars().all()
            
            recipient_emails = [p.email for p in participants if p.email]
            
            if not recipient_emails:
                logger.warning(f"No participants with emails for meeting {meeting.id}")
                continue
                
            # Prepare context
            context = {
                "meeting_title": meeting.title,
                "meeting_date": meeting.scheduled_at.strftime("%A, %B %d, %Y at %I:%M %p UTC"),
                "agenda_summary": "Please review the attached agenda." # Placeholder
            }
            
            meeting_details = {
                "title": meeting.title,
                "description": context["agenda_summary"],
                "start_time": meeting.scheduled_at,
                "duration": meeting.duration_minutes,
                "location": meeting.location
            }
            
            # Since email_service is async, we have to run it in sync context
            # However, running async code from sync Celery is tricky.
            # Best practice: keep email_service async and use asgiref or asyncio.run
            import asyncio
            try:
                asyncio.run(email_service.send_meeting_reminder(
                    to_emails=recipient_emails,
                    template_context=context,
                    meeting_details=meeting_details
                ))
                
                # 4. Log Success
                log = AuditLog(
                    action="reminder_sent",
                    resource_type="meeting",
                    resource_id=meeting.id,
                    details={"sent_to": recipient_emails, "timestamp": str(now)}
                )
                session.add(log)
                session.commit()
                count_sent += 1
                logger.info(f"Sent reminder for meeting {meeting.id}")
                
            except Exception as e:
                logger.error(f"Failed to send/log reminder for {meeting.id}: {e}")
                session.rollback() # Rollback on individual failure
                
        logger.info(f"Send meeting reminders task completed. Sent {count_sent} reminders.")
        return f"Sent {count_sent} reminders"

    except Exception as e:
        logger.error(f"Error in send_meeting_reminders task: {e}")
        session.rollback()
        raise e
    finally:
        session.close()

@celery_app.task
def sync_rsvps():
    """
    Periodic task to sync RSVPs from Google Calendar to Database.
    Refreshes status for upcoming meetings.
    """
    logger.info("Starting sync_rsvps task")
    session = get_sync_db_session()
    try:
        now = datetime.now(timezone.utc)
        
        # Sync for active future meetings (and maybe slightly past to catch late updates)
        # Getting meetings from now-7d to future to handle late RSVPs and recent history
        search_start = now - timedelta(days=7)
        
        meetings = session.execute(
            select(Meeting).where(
                and_(
                    Meeting.status == MeetingStatus.SCHEDULED,
                    Meeting.scheduled_at >= search_start
                )
            )
        ).scalars().all()
        
        updated_count = 0
        
        for meeting in meetings:
            # Fetch RSVPs from Calendar Service (this calls Google API)
            # Synchronous call (wrapper needed if it was async, but calendar_service methods are sync for GCal)
            # Check calendar_service.py: create_meeting_event is sync. get_meeting_rsvps is sync.
            from app.services.gcal_executor import gcal_executor
            rsvps = gcal_executor.submit(
                calendar_service.get_meeting_rsvps, str(meeting.id)
            ).result()
            
            if not rsvps:
                continue
                
            # Update participants
            participants = session.execute(
                select(MeetingParticipant).where(
                    MeetingParticipant.meeting_id == meeting.id
                )
            ).scalars().all()
            
            meeting_updated = False
            for p in participants:
                if p.email in rsvps:
                    gcal_status = rsvps[p.email]
                    new_status = _map_gcal_status(gcal_status)
                    
                    if p.rsvp_status != new_status:
                        p.rsvp_status = new_status
                        session.add(p) # Mark for update
                        meeting_updated = True
            
            if meeting_updated:
                session.commit()
                updated_count += 1
                
        logger.info(f"Sync RSVPs task completed. Updated {updated_count} meetings.")
        return f"Updated {updated_count} meetings"

    except Exception as e:
        logger.error(f"Error in sync_rsvps task: {e}")
        session.rollback()
        raise e
    finally:
        session.close()

def _map_gcal_status(gcal_status: str) -> RsvpStatus:
    """Map Google Calendar attendee status to internal RsvpStatus"""
    # Google statuses: 'needsAction', 'declined', 'tentative', 'accepted'
    status_map = {
        'accepted': RsvpStatus.ACCEPTED,
        'declined': RsvpStatus.DECLINED,
        'tentative': RsvpStatus.PENDING, # Or create a tentative status
        'needsAction': RsvpStatus.PENDING
    }
    return status_map.get(gcal_status, RsvpStatus.PENDING)

@celery_app.task
def generate_project_pdf(project_id: str, project_name: str, description: str):
    """
    Background task to generate investment memo PDF.
    """
    # Reuse previous simple implementation or expand if needed
    # For now keeping it simple as per original file, referencing format_service
    from app.services.format_service import format_service
    
    try:
        pdf_bytes = format_service.generate_pdf(
            title=f"Investment Memo: {project_name}",
            content=description,
            footer="Confidential - ECOWAS Investment Pipeline"
        )
        path = f"/tmp/{project_id}_memo.pdf"
        with open(path, "wb") as f:
            f.write(pdf_bytes)
        
        return {"status": "success", "path": path}
    except Exception as e:
        return {"status": "failed", "error": str(e)}
