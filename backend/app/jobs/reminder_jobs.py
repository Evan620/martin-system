import logging
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.core.database import AsyncSessionLocal
from app.models.models import Meeting, MeetingStatus, AuditLog, MeetingParticipant, TWG, ActionItem, ActionItemStatus, Notification, NotificationType
from app.services.email_service import email_service
from app.core.config import settings
from app.core.ws_manager import ws_manager

logger = logging.getLogger(__name__)

async def send_upcoming_meeting_reminders():
    """
    Job to check for meetings in the next 24 hours (with some buffer) 
    and send reminders if not already sent.
    """
    logger.info("Running send_upcoming_meeting_reminders job")
    
    async with AsyncSessionLocal() as db:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        # Check meetings starting between 23.5 and 24.5 h from now 
        start_window = now + timedelta(hours=23, minutes=30)
        end_window = now + timedelta(hours=24, minutes=30)
        
        query = select(Meeting).where(
            Meeting.status == MeetingStatus.SCHEDULED,
            Meeting.scheduled_at >= start_window,
            Meeting.scheduled_at <= end_window
        ).options(
            selectinload(Meeting.participants).selectinload(MeetingParticipant.user),
            selectinload(Meeting.twg)
        )
        
        result = await db.execute(query)
        meetings = result.scalars().all()
        
        for meeting in meetings:
            # Check if reminder already sent via AuditLog
            audit_query = select(AuditLog).where(
                AuditLog.resource_id == meeting.id,
                AuditLog.action == "MEETING_REMINDER_SENT"
            )
            audit_result = await db.execute(audit_query)
            if audit_result.scalar_one_or_none():
                continue # Skip if already sent
            
            # Send Reminder
            participant_emails = []
            for p in meeting.participants:
                if p.user and p.user.email:
                    participant_emails.append(p.user.email)
                elif p.email:
                    participant_emails.append(p.email)
            participant_emails = list(set(participant_emails))

            if not participant_emails:
                continue

            try:
                await email_service.send_meeting_reminder(
                    to_emails=participant_emails,
                    template_context={
                        "user_name": "Valued Participant",
                        "meeting_title": meeting.title,
                        "meeting_date": meeting.scheduled_at.strftime("%Y-%m-%d"),
                        "meeting_time": meeting.scheduled_at.strftime("%H:%M UTC"),
                        "location": meeting.location or "Virtual",
                        "pillar_name": meeting.twg.pillar.value if meeting.twg else "TWG",
                        "portal_url": f"{settings.FRONTEND_URL}/schedule"
                    },
                    meeting_details={
                        "title": meeting.title,
                        "start_time": meeting.scheduled_at,
                        "duration": meeting.duration_minutes,
                        "location": meeting.location
                    }
                )
                
                # Log action (System User)
                audit = AuditLog(
                    action="MEETING_REMINDER_SENT",
                    resource_type="meeting",
                    resource_id=meeting.id,
                    details={"emails_sent": len(participant_emails)},
                    ip_address="127.0.0.1" # System
                )
                db.add(audit)
                await db.commit()
                logger.info(f"Sent reminders for meeting {meeting.id}")
            except Exception as e:
                logger.error(f"Failed to send reminder for meeting {meeting.id}: {e}")

async def check_missing_minutes():
    """
    Check for meetings that ended > 24 hours ago but have no minutes uploaded.
    """
    logger.info("Running check_missing_minutes job")
    
    async with AsyncSessionLocal() as db:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        # Look for meetings ended between 24h and 48h ago
        window_start = now - timedelta(hours=48)
        window_end = now - timedelta(hours=24)
        
        query = select(Meeting).where(
            Meeting.status.in_([MeetingStatus.SCHEDULED, MeetingStatus.COMPLETED]),
            Meeting.scheduled_at >= window_start,
            Meeting.scheduled_at <= window_end
        ).options(
            selectinload(Meeting.minutes),
            selectinload(Meeting.twg).selectinload(TWG.political_lead), 
            selectinload(Meeting.twg).selectinload(TWG.technical_lead)
        )
        
        result = await db.execute(query)
        meetings = result.scalars().all()
        
        for meeting in meetings:
            if meeting.minutes:
                continue # Has minutes, good.
                
            # Check audit to ensure we haven't nudged already
            audit_query = select(AuditLog).where(
                AuditLog.resource_id == meeting.id,
                AuditLog.action == "MINUTES_NUDGE_SENT"
            )
            audit_result = await db.execute(audit_query)
            if audit_result.scalar_one_or_none():
                continue
            
            # Identify Leads
            emails_to_nudge = []
            twg = meeting.twg
            if twg.political_lead and twg.political_lead.email:
                emails_to_nudge.append(twg.political_lead.email)
            if twg.technical_lead and twg.technical_lead.email:
                emails_to_nudge.append(twg.technical_lead.email)
            
            if not emails_to_nudge:
                continue

            try:
                await email_service.send_minutes_nudge(
                    to_emails=emails_to_nudge,
                    template_context={
                        "user_name": "Facilitator",
                        "meeting_title": meeting.title,
                        "meeting_date": meeting.scheduled_at.strftime("%Y-%m-%d"),
                        "pillar_name": twg.pillar.value if twg else "TWG",
                        "portal_url": f"{settings.FRONTEND_URL}/schedule"
                    }
                )
                
                audit = AuditLog(
                    action="MINUTES_NUDGE_SENT",
                    resource_type="meeting",
                    resource_id=meeting.id,
                    details={"nudged_emails": emails_to_nudge},
                    ip_address="127.0.0.1"
                )
                db.add(audit)
                await db.commit()
                logger.info(f"Sent minutes nudge for meeting {meeting.id}")
            except Exception as e:
                 logger.error(f"Failed to send nudge for meeting {meeting.id}: {e}")


async def check_overdue_action_items():
    """
    Job to detect action items past their due date and flip them to OVERDUE.
    Creates a notification for each affected owner. Runs every 6 hours.
    """
    logger.info("Running check_overdue_action_items job")

    async with AsyncSessionLocal() as db:
        now = datetime.now(timezone.utc).replace(tzinfo=None)

        result = await db.execute(
            select(ActionItem).where(
                ActionItem.due_date < now,
                ActionItem.status.in_([ActionItemStatus.PENDING, ActionItemStatus.IN_PROGRESS])
            )
        )
        overdue_items = result.scalars().all()

        if not overdue_items:
            logger.info("No overdue action items found")
            return

        for item in overdue_items:
            item.status = ActionItemStatus.OVERDUE

            # Create notification for owner
            notification = Notification(
                user_id=item.owner_id,
                type=NotificationType.WARNING,
                title="Action Item Overdue",
                content=f"'{item.description[:80]}' is past its due date",
                link="/actions",
                is_read=False,
                created_at=datetime.utcnow()
            )
            db.add(notification)

            # Broadcast via WebSocket
            try:
                await ws_manager.send_personal_message(
                    {
                        "type": "NEW_NOTIFICATION",
                        "data": {
                            "id": str(notification.id),
                            "type": notification.type.value,
                            "title": notification.title,
                            "content": notification.content,
                            "link": notification.link,
                            "created_at": notification.created_at.isoformat()
                        }
                    },
                    str(item.owner_id)
                )
            except Exception as e:
                logger.warning(f"Failed to broadcast overdue notification: {e}")

        await db.commit()
        logger.info(f"Marked {len(overdue_items)} action items as OVERDUE")
