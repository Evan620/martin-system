"""
Resolution Notifier Service

Handles all notifications when a conflict resolution is applied:
- Updates Google Calendar events
- Sends email notifications to participants
- Creates in-app notifications
"""

from typing import List, Optional
from datetime import datetime
from loguru import logger
from uuid import UUID
import asyncio
import concurrent.futures

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.models import Meeting, MeetingParticipant, NotificationType
from app.services.calendar_service import calendar_service
from app.services.email_service import email_service
from app.services.notification_service import create_notification

# Dedicated thread pool for blocking GCal API calls
_gcal_executor = concurrent.futures.ThreadPoolExecutor(max_workers=2, thread_name_prefix="gcal-notifier")


class ResolutionNotifier:
    """
    Orchestrates notifications when conflict resolutions are applied.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def notify_meeting_rescheduled(
        self, 
        meeting: Meeting, 
        old_time: datetime, 
        new_time: datetime
    ) -> dict:
        """
        Notify all participants that a meeting has been rescheduled.
        """
        results = {
            "calendar_updated": False,
            "emails_sent": False,
            "notifications_created": 0
        }
        
        # 1. Update Google Calendar (in thread pool to avoid blocking event loop)
        try:
            loop = asyncio.get_running_loop()
            _mid = str(meeting.id)
            _new_time = new_time
            _dur = meeting.duration_minutes
            results["calendar_updated"] = await loop.run_in_executor(
                _gcal_executor,
                lambda: calendar_service.update_meeting_event(
                    meeting_id=_mid,
                    new_start_time=_new_time,
                    new_duration_minutes=_dur
                )
            )
        except Exception as e:
            logger.error(f"Calendar update failed for meeting {meeting.id}: {e}")

        # 2. Get participant emails
        participant_emails = await self._get_participant_emails(meeting.id)

        if participant_emails:
            # 3. Send email notifications
            try:
                template_context = {
                    "meeting_title": meeting.title,
                    "old_time": old_time.strftime("%A, %B %d at %I:%M %p UTC"),
                    "new_time": new_time.strftime("%A, %B %d at %I:%M %p UTC"),
                    "location": meeting.location or "Virtual",
                    "video_link": meeting.video_link
                }

                meeting_details = {
                    "title": meeting.title,
                    "description": f"Rescheduled from {old_time} to {new_time}",
                    "start_time": new_time,
                    "duration": meeting.duration_minutes,
                    "location": meeting.location
                }

                changes = [f"Time changed from {old_time.strftime('%I:%M %p')} to {new_time.strftime('%I:%M %p')}"]

                await email_service.send_meeting_update(
                    to_emails=participant_emails,
                    template_context=template_context,
                    meeting_details=meeting_details,
                    changes=changes
                )
                results["emails_sent"] = True
                logger.info(f"Sent reschedule emails to {len(participant_emails)} participants")
            except Exception as e:
                logger.error(f"Email notification failed: {e}")

        # 4. Create in-app notifications
        results["notifications_created"] = await self._create_participant_notifications(
            meeting=meeting,
            title="Meeting Rescheduled",
            content=f"'{meeting.title}' has been moved to {new_time.strftime('%B %d at %I:%M %p')}.",
            link=f"/meetings/{meeting.id}"
        )
        
        logger.info(f"Resolution notification complete for meeting {meeting.id}: {results}")
        return results

    async def notify_meeting_venue_changed(
        self, 
        meeting: Meeting, 
        old_venue: str, 
        new_venue: str
    ) -> dict:
        """
        Notify all participants that staying venue has changed.
        """
        results = {
            "calendar_updated": False,
            "emails_sent": False,
            "notifications_created": 0
        }
        
        # 1. Update Google Calendar (in thread pool to avoid blocking event loop)
        try:
            loop = asyncio.get_running_loop()
            _mid = str(meeting.id)
            _venue = new_venue
            results["calendar_updated"] = await loop.run_in_executor(
                _gcal_executor,
                lambda: calendar_service.update_meeting_event(
                    meeting_id=_mid,
                    new_location=_venue
                )
            )
        except Exception as e:
            logger.error(f"Calendar update failed for meeting {meeting.id}: {e}")

        # 2. Get participant emails
        participant_emails = await self._get_participant_emails(meeting.id)
        
        if participant_emails:
            # 3. Send email notifications
            try:
                template_context = {
                    "meeting_title": meeting.title,
                    "old_venue": old_venue or "Not specified",
                    "new_venue": new_venue,
                    "meeting_time": meeting.scheduled_at.strftime("%A, %B %d at %I:%M %p UTC"),
                    "video_link": meeting.video_link
                }
                
                meeting_details = {
                    "title": meeting.title,
                    "description": f"Venue changed from {old_venue} to {new_venue}",
                    "start_time": meeting.scheduled_at,
                    "duration": meeting.duration_minutes,
                    "location": new_venue
                }
                
                changes = [f"Venue changed from '{old_venue}' to '{new_venue}'"]
                
                await email_service.send_meeting_update(
                    to_emails=participant_emails,
                    template_context=template_context,
                    meeting_details=meeting_details,
                    changes=changes
                )
                results["emails_sent"] = True
            except Exception as e:
                logger.error(f"Email notification failed: {e}")

        # 4. Create in-app notifications
        results["notifications_created"] = await self._create_participant_notifications(
            meeting=meeting,
            title="Meeting Venue Changed",
            content=f"'{meeting.title}' has been moved to {new_venue}.",
            link=f"/meetings/{meeting.id}"
        )
        
        return results

    async def notify_meeting_cancelled(
        self, 
        meeting: Meeting, 
        reason: str = None
    ) -> dict:
        """
        Notify all participants that a meeting has been cancelled.
        """
        results = {
            "calendar_updated": False,
            "emails_sent": False,
            "notifications_created": 0
        }
        
        # 1. Cancel in Google Calendar (in thread pool to avoid blocking event loop)
        try:
            loop = asyncio.get_running_loop()
            _mid = str(meeting.id)
            results["calendar_updated"] = await loop.run_in_executor(
                _gcal_executor,
                lambda: calendar_service.cancel_meeting_event(meeting_id=_mid)
            )
        except Exception as e:
            logger.error(f"Calendar cancellation failed for meeting {meeting.id}: {e}")

        # 2. Get participant emails
        participant_emails = await self._get_participant_emails(meeting.id)
        
        if participant_emails:
            # 3. Send cancellation emails
            try:
                template_context = {
                    "meeting_title": meeting.title,
                    "original_time": meeting.scheduled_at.strftime("%A, %B %d at %I:%M %p UTC"),
                    "location": meeting.location or "Virtual"
                }
                
                meeting_details = {
                    "title": meeting.title,
                    "meeting_id": str(meeting.id),
                    "start_time": meeting.scheduled_at,
                    "duration": meeting.duration_minutes,
                    "location": meeting.location
                }
                
                await email_service.send_meeting_cancellation(
                    to_emails=participant_emails,
                    template_context=template_context,
                    meeting_details=meeting_details,
                    reason=reason or "Resolved via AI conflict negotiation"
                )
                results["emails_sent"] = True
            except Exception as e:
                logger.error(f"Email notification failed: {e}")

        # 4. Create in-app notifications
        results["notifications_created"] = await self._create_participant_notifications(
            meeting=meeting,
            title="Meeting Cancelled",
            content=f"'{meeting.title}' scheduled for {meeting.scheduled_at.strftime('%B %d')} has been cancelled.",
            link=None
        )
        
        return results

    async def _get_participant_emails(self, meeting_id: UUID) -> List[str]:
        """
        Get all participant emails for a meeting.
        """
        stmt = select(MeetingParticipant).where(
            MeetingParticipant.meeting_id == meeting_id
        ).options(selectinload(MeetingParticipant.user))
        
        result = await self.db.execute(stmt)
        participants = result.scalars().all()
        
        emails = []
        for p in participants:
            if p.email:
                emails.append(p.email)
            elif p.user and p.user.email:
                emails.append(p.user.email)
        
        return list(set(emails))  # Deduplicate

    async def _create_participant_notifications(
        self, 
        meeting: Meeting, 
        title: str, 
        content: str,
        link: Optional[str] = None
    ) -> int:
        """
        Create in-app notifications for all meeting participants.
        """
        stmt = select(MeetingParticipant).where(
            MeetingParticipant.meeting_id == meeting.id
        ).options(selectinload(MeetingParticipant.user))
        
        result = await self.db.execute(stmt)
        participants = result.scalars().all()
        
        count = 0
        for p in participants:
            if p.user_id:
                try:
                    await create_notification(
                        db=self.db,
                        user_id=p.user_id,
                        type=NotificationType.ALERT,
                        title=title,
                        content=content,
                        link=link
                    )
                    count += 1
                except Exception as e:
                    logger.error(f"Failed to create notification for user {p.user_id}: {e}")
        
        return count
