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
from datetime import datetime, timedelta, UTC
from loguru import logger
from typing import List, Optional, Tuple
import asyncio
from uuid import UUID


from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm.attributes import flag_modified

from app.core.database import get_db_session_context
from app.models.models import (
    Meeting, Conflict, TWG, ConflictStatus, Notification, NotificationType, Document, User, MeetingParticipant, VipProfile,
    ConflictType, ConflictSeverity, MeetingStatus
)
from app.services.conflict_detector import ConflictDetector
from app.services.vexa_service import vexa_service
from app.services.conflict_detector import ConflictDetector
from app.services.vexa_service import vexa_service

class ContinuousMonitor:
    """
    Background service for maintaining global state integrity.
    """
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.conflict_detector = ConflictDetector() # Initialize without LLM for now, or inject if needed
        self.is_running = False
        
    def start(self):
        """Start the background monitor."""
        if self.is_running:
            return
            
        logger.info("Starting Continuous Monitor...")
        
        # 1. Temporal Conflict Scan (Every 30 mins)
        self.scheduler.add_job(
            self.scan_scheduling_conflicts,
            trigger=IntervalTrigger(minutes=30),
            id="scan_scheduling",
            replace_existing=True
        )
        
        # 2. Semantic Conflict Scan (Every 60 mins to reduce API calls)
        # 2. Semantic Conflict Scan (Every 60 mins to reduce API calls)
        # self.scheduler.add_job(
        #     self.scan_policy_divergences,
        #     trigger=IntervalTrigger(minutes=60),
        #     id="scan_policy",
        #     replace_existing=True
        # )
        
        # 3. Health Check (Hourly)
        self.scheduler.add_job(
            self.check_twg_health,
            trigger=IntervalTrigger(hours=1),
            id="health_check",
            replace_existing=True
        )
        
        
        # 4. Project Conflict Scan (Every 6 hours)
        self.scheduler.add_job(
            self.scan_project_conflicts,
            trigger=IntervalTrigger(hours=6),
            id="scan_projects",
            replace_existing=True
        )

        # 5. Vexa Meeting Dispatch (Every 1 min)
        self.scheduler.add_job(
            self.check_upcoming_meetings,
            trigger=IntervalTrigger(minutes=1),
            id="vexa_dispatch",
            replace_existing=True
        )

        # 6. Check Pending Transcripts (Every 10 seconds for real-time sync)
        self.scheduler.add_job(
            self.check_pending_transcripts,
            trigger=IntervalTrigger(seconds=10),
            id="vexa_transcript_check",
            replace_existing=True
        )

        # 7. Sync Pending Calendar Links (Every 30 seconds)
        self.scheduler.add_job(
            self.sync_pending_calendar_events,
            trigger=IntervalTrigger(seconds=30),
            id="calendar_sync_check",
            replace_existing=True
        )
        
        # 8. Google Drive Transcript Fallback (Every 5 minutes)
        self.scheduler.add_job(
            self.check_drive_transcripts_fallback,
            trigger=IntervalTrigger(minutes=5),
            id="drive_transcript_fallback",
            replace_existing=True
        )
        
        # 9. Auto-Complete Past Meetings (Every hour)
        self.scheduler.add_job(
            self.auto_complete_past_meetings,
            trigger=IntervalTrigger(hours=1),
            id="auto_complete_meetings",
            replace_existing=True
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
                    # Double check if we already tried and failed recently? 
                    # For now just retry. 
                    
                    logger.info(f"Generating link for meeting: {meeting.title} ({meeting.id})")
                    
                    # Call Calendar Service (Synchronous, so wrap in thread if blocking IO is heavy)
                    # For simplicity calling directly as simple HTTP reqs usually fine in async loop if not too many
                    import asyncio
                    
                    # Need to construct attendees list if available
                    # For now passing empty list or fetching participants
                    attendee_emails = [] 
                    # If we had loaded participants we could add them. 
                    # Skipping for speed - focus is the LINK.
                    
                    event = await asyncio.to_thread(
                        calendar_service.create_meeting_event,
                        title=meeting.title,
                        start_time=meeting.scheduled_at, # This comes out as naive UTC from DB usually
                        duration_minutes=meeting.duration_minutes,
                        description=f"Generated by Martin AI. ID: {meeting.id}",
                        attendees=attendee_emails,
                        meeting_id=str(meeting.id)
                    )
                    
                    if event and event.get('htmlLink'):
                        video_link = event.get('hangoutLink') # This is the Meet link
                        if not video_link:
                             video_link = event.get('htmlLink') # Fallback to event link
                        
                        meeting.video_link = video_link
                        
                        # Clean up "Pending" from location if present
                        if meeting.location and "Pending" in meeting.location:
                            meeting.location = meeting.location.replace("(Pending Link)", "").strip()
                            if meeting.location == "Virtual": 
                                 meeting.location = "Virtual (Google Meet)"
                        
                        logger.info(f"✓ Link generated: {video_link}")
                        
                        # Save
                        flag_modified(meeting, "video_link")
                        await db.commit()
                    else:
                        logger.warning(f"Failed to generate link for {meeting.title}. Token might be invalid.")
                        
            except Exception as e:
                logger.error(f"Error syncing calendar links: {e}")

    async def check_upcoming_meetings(self):
        """
        Check for meetings starting in < 5 mins and dispatch Vexa bot.
        Also checks for completed sessions to retrieve transcripts.
        """

        # 1. Dispatch to upcoming meetings
        logger.info("Checking for upcoming meetings to record...")
        async with get_db_session_context() as db:
            try:
                # Find meetings starting in next 5-10 mins
                now = datetime.utcnow()
                five_mins_from_now = now + timedelta(minutes=5)
                ten_mins_from_now = now + timedelta(minutes=10)
                
                stmt = select(Meeting).where(
                    and_(
                        Meeting.scheduled_at >= now,
                        Meeting.scheduled_at <= ten_mins_from_now,
                        # Check if we already have a transcript or if cancelled
                        or_(Meeting.transcript.is_(None), Meeting.transcript == ""), 
                        Meeting.status != MeetingStatus.CANCELLED
                    )
                ).options(selectinload(Meeting.participants))
                result = await db.execute(stmt)
                meetings = result.scalars().all()
                
                for meeting in meetings:
                     # Check if we already dispatched a bot to this meeting
                     # by looking for an existing placeholder document
                     existing_placeholder_stmt = select(Document).where(
                         and_(
                             Document.meeting_id == meeting.id,
                             Document.document_type == "transcript_placeholder"
                         )
                     )
                     existing_placeholder_result = await db.execute(existing_placeholder_stmt)
                     existing_placeholder = existing_placeholder_result.scalar_one_or_none()
                     
                     if existing_placeholder:
                         # Bot already dispatched, skip
                         logger.debug(f"Bot already dispatched to meeting: {meeting.title} (Session: {existing_placeholder.metadata_json.get('vexa_session_id')})")
                         continue
                     
                     # Check for Google Meet link in 'location' OR 'video_link'
                     meet_url = None
                     if meeting.location and "meet.google.com" in meeting.location:
                         meet_url = meeting.location
                     elif meeting.video_link and "meet.google.com" in meeting.video_link:
                         meet_url = meeting.video_link
                     
                     if not meet_url:
                         continue
                         
                     logger.info(f"Dispatching Vexa to meeting: {meeting.title}")
                     bot_info = await vexa_service.join_meeting(
                         meeting_url=meet_url,
                         meeting_id=str(meeting.id),
                         bot_name="Martin Ai Meeting Notetaker"
                     )
                     
                     if bot_info:
                         session_id = bot_info["session_id"]
                         platform = bot_info["platform"]
                         native_meeting_id = bot_info["native_meeting_id"]
                         
                         logger.info(f"Successfully dispatched bot to {meeting.title}. Session: {session_id}")
                         # Create Placeholder Document to track session status
                         
                         # Hack to get a valid user ID for 'uploaded_by' without triggering lazy loads
                         # Just fetch the first system user.
                         res_u = await db.execute(select(User.id).limit(1))
                         uploader_id = res_u.scalars().first()
                         
                         if uploader_id:
                             # Create Placeholder Document with platform and native_meeting_id
                             doc = Document(
                                 twg_id=meeting.twg_id,
                                 meeting_id=meeting.id,
                                 file_name=f"Vexa Recording - {meeting.title}",
                                 file_path="vexa_pending",
                                 file_type="transcript_placeholder",
                                 document_type="transcript_placeholder",
                                 uploaded_by_id=uploader_id,
                                 metadata_json={
                                     "vexa_session_id": session_id,
                                     "platform": platform,
                                     "native_meeting_id": native_meeting_id,
                                     "status": "processing"
                                 }
                             )
                             db.add(doc)
                             logger.info(f"Created placeholder document for Vexa session {session_id}")
                             await db.commit()
                     else:
                         logger.warning(f"Vexa join failed for {meeting.title}")
            except Exception as e:
                logger.error(f"Error in Vexa dispatch: {e}")

    async def check_pending_transcripts(self):
        """
        Poll Vexa for transcripts of ongoing/completed sessions.
        """
        logger.info("Checking pending Vexa transcripts...")
        async with get_db_session_context() as db:
            try:
                # Find placeholder documents
                stmt = select(Document).where(Document.document_type == "transcript_placeholder")
                result = await db.execute(stmt)
                docs = result.scalars().all()
                
                for doc in docs:
                    session_id = doc.metadata_json.get("vexa_session_id")
                    platform = doc.metadata_json.get("platform")
                    native_meeting_id = doc.metadata_json.get("native_meeting_id")
                    
                    # CRITICAL: Skip documents that have failed permanently
                    doc_status = doc.metadata_json.get("status", "")
                    if doc_status == "failed":
                        logger.debug(f"Skipping session {session_id} - marked as FAILED")
                        continue
                    
                    # CRITICAL: Skip documents in backoff period
                    next_retry_after = doc.metadata_json.get("next_retry_after")
                    if next_retry_after:
                        from datetime import datetime as dt
                        next_retry_time = dt.fromisoformat(next_retry_after)
                        if dt.utcnow() < next_retry_time:
                            time_remaining = (next_retry_time - dt.utcnow()).total_seconds() / 60
                            logger.debug(f"Skipping session {session_id} - in backoff period ({time_remaining:.1f} min remaining)")
                            continue
                    
                    if not platform or not native_meeting_id:
                        logger.warning(f"Document {doc.id} missing platform or native_meeting_id, skipping")
                        continue
                        
                    logger.info(f"Polling Vexa for {platform}/{native_meeting_id} (Session: {session_id}, Meeting: {doc.meeting_id})")
                    transcript_data = await vexa_service.get_transcript(platform, native_meeting_id)
                    
                    if transcript_data:
                        transcript_text = transcript_data.get("text")
                        is_completed = transcript_data.get("is_completed", False)
                        status = transcript_data.get("status", "unknown")
                        
                        logger.info(f"✓ Transcript ready for session {session_id}! Length: {len(transcript_text)} chars, Status: {status}, Completed: {is_completed}")
                        
                        # UPDATE MEETING STATUS TO IN_PROGRESS
                        # This ensures the dashboard "unlocks" live sync and detail page shows "LIVE"
                        res_m = await db.execute(select(Meeting).where(Meeting.id == doc.meeting_id))
                        meeting_obj = res_m.scalar_one_or_none()
                        if meeting_obj and meeting_obj.status != MeetingStatus.IN_PROGRESS and not is_completed:
                            logger.warning(f"Updating meeting {meeting_obj.id} status to IN_PROGRESS (Vexa active)")
                            meeting_obj.status = MeetingStatus.IN_PROGRESS
                            await db.commit()
                        
                        # IDLE TIMEOUT LOGIC
                        # Check if transcript has stopped growing for > 5 minutes
                        from datetime import datetime, timedelta, UTC
                        
                        current_length = len(transcript_text)
                        last_length = doc.metadata_json.get("last_transcript_length", 0)
                        last_check_time_str = doc.metadata_json.get("last_check_time")
                        
                        should_force_complete = False
                        
                        if current_length != last_length:
                            # Transcript is growing, update state
                            doc.metadata_json["last_transcript_length"] = current_length
                            doc.metadata_json["last_check_time"] = datetime.utcnow().isoformat()
                            # Commit validation updates
                            flag_modified(doc, "metadata_json")
                            await db.commit()
                        elif last_check_time_str:
                            # Length hasn't changed, check how long it's been
                            try:
                                last_check_time = datetime.fromisoformat(last_check_time_str)
                                time_diff = datetime.utcnow() - last_check_time
                                
                                # If idle for more than 5 minutes (300 seconds) AND has content
                                if time_diff.total_seconds() > 300 and current_length > 0:
                                    logger.warning(f"⚠️ Session {session_id} idle for {int(time_diff.total_seconds())}s. Forcing completion.")
                                    should_force_complete = True
                            except Exception as e:
                                logger.error(f"Error parsing date: {e}")
                        else:
                            # First check, init metadata
                            doc.metadata_json["last_transcript_length"] = current_length
                            doc.metadata_json["last_check_time"] = datetime.utcnow().isoformat()
                            flag_modified(doc, "metadata_json")
                            await db.commit()

                        # REAL-TIME INCREMENTAL PROCESSING
                        # Check if transcript has grown since last pulse
                        last_processed_pos = doc.metadata_json.get("last_processed_pos", 0)
                        
                        if current_length > last_processed_pos:
                             # Extract the new chunk
                             new_chunk = transcript_text[last_processed_pos:]
                             logger.info(f"Processing NEW TRANSCRIPT CHUNK ({len(new_chunk)} chars) for meeting {doc.meeting_id}")
                             
                             # 1. ALWAYS SYNC TO FRONTEND (Regardless of AI status)
                             try:
                                 from app.services.broadcast_service import get_broadcast_service
                                 broadcast = get_broadcast_service()
                                 await broadcast.notify_live_meeting(
                                     meeting_id=doc.meeting_id,
                                     content=new_chunk,
                                     source="vexa_transcript_sync"
                                 )
                                 
                                 # Sync the full currently available transcript to the Meeting record
                                 if meeting_obj:
                                     meeting_obj.transcript = transcript_text
                             except Exception as be:
                                 logger.error(f"Failed to broadcast transcript chunk: {be}")

                             # 2. RUN AI ANALYSIS (Fails gracefully)
                             try:
                                 await vexa_service.analyze_live_chunk(
                                     meeting_id=doc.meeting_id,
                                     chunk_text=new_chunk,
                                     db=db
                                 )
                             except Exception as ae:
                                 logger.error(f"AI analysis failed for chunk: {ae}")
                                 
                             # 3. ALWAYS MARK AS PROCESSED
                             # We update this even on AI failure to avoid infinite re-tries of same chunk
                             doc.metadata_json["last_processed_pos"] = current_length
                             flag_modified(doc, "metadata_json")
                             await db.commit()

                        # ---------------------------------------------------------
                        # COMPLETION LOGIC (Only generate minutes when finished/timeout)
                        # ---------------------------------------------------------

                        # CRITICAL: Only process transcript if meeting has ended OR timed out
                        if not is_completed and not should_force_complete:
                            logger.info(f"⏳ Meeting still active (status: {status}). Still monitoring for live insights.")
                            continue
                        
                        if should_force_complete:
                            logger.info(f"✓ Forcing final minutes generation due to idle timeout ({current_length} chars)")
                        
                        # Process it
                        # Need to fetch Meeting object
                        stmt_m = select(Meeting).where(Meeting.id == doc.meeting_id)
                        res_m = await db.execute(stmt_m)
                        meeting = res_m.scalar_one_or_none()
                        
                        if meeting:
                            logger.info(f"Processing transcript for completed meeting: {meeting.title}")
                            file_path_or_success = await vexa_service.process_transcript_text(meeting, transcript_text, db)
                            if file_path_or_success:
                                # Update Document to be the actual transcript
                                doc.document_type = "transcript"
                                doc.file_type = "text/plain" 
                                # Use the absolute path or relative?
                                # Usually backend stores relative to UPLOAD_DIR or full path
                                # vexa_service returns full path.
                                # Let's store full path for now, or relative to be safe?
                                # Project uses 'uploads/...'
                                
                                # Handle path string
                                saved_path = str(file_path_or_success)
                                if "uploads" in saved_path:
                                    # Try to make it relative for portability if possible, 
                                    # but absolute key is fine for local.
                                    pass
                                
                                doc.file_path = saved_path
                                doc.metadata_json["status"] = "completed"
                                logger.info(f"✓ Transcript processed and saved to {saved_path}")
                                
                                # CRITICAL: Update meeting status to COMPLETED
                                meeting.status = MeetingStatus.COMPLETED
                                logger.info(f"✓ Meeting {meeting.title} status updated to COMPLETED")
                                
                                # CRITICAL: Commit changes to database
                                await db.commit()
                                logger.info(f"✓ Minutes and transcript committed to database for meeting: {meeting.title}")
                            else:
                                # CRITICAL FIX: Track failed attempts to prevent infinite retries
                                logger.error(f"✗ Failed to process transcript text for session {session_id}")
                                
                                # Initialize retry tracking if not present
                                if "retry_count" not in doc.metadata_json:
                                    doc.metadata_json["retry_count"] = 0
                                if "last_retry_at" not in doc.metadata_json:
                                    doc.metadata_json["last_retry_at"] = None
                                
                                # Increment retry count
                                doc.metadata_json["retry_count"] += 1
                                doc.metadata_json["last_retry_at"] = datetime.utcnow().isoformat()
                                
                                # Exponential backoff: 5min, 15min, 30min, 1hr, then give up
                                retry_count = doc.metadata_json["retry_count"]
                                if retry_count >= 5:
                                    doc.metadata_json["status"] = "failed"
                                    doc.metadata_json["failure_reason"] = "Max retries exceeded (rate limit)"
                                    logger.warning(f"⚠️ Marking session {session_id} as FAILED after {retry_count} attempts")
                                else:
                                    # Calculate next retry time (exponential backoff)
                                    backoff_minutes = [5, 15, 30, 60][min(retry_count - 1, 3)]
                                    doc.metadata_json["next_retry_after"] = (
                                        datetime.utcnow() + timedelta(minutes=backoff_minutes)
                                    ).isoformat()
                                    logger.info(f"⏳ Will retry session {session_id} after {backoff_minutes} minutes (attempt {retry_count}/5)")
                                
                                # Mark the field as modified and commit
                                flag_modified(doc, "metadata_json")
                                await db.commit()
                        else:
                            logger.error(f"✗ Meeting {doc.meeting_id} not found for document {doc.id}")
                            await db.delete(doc) # Cleanup orphan
                            await db.commit()
                    else:
                        # Transcript not ready yet
                        logger.debug(f"Transcript not yet available for session {session_id}")
            except Exception as e:
                logger.error(f"Error checking pending transcripts: {e}")

    async def check_drive_transcripts_fallback(self):
        """
        Fallback system: Check Google Drive Meet Recordings folder for transcripts.
        This catches meetings where Vexa wasn't admitted or failed to join.
        Runs every 5 minutes (less aggressive than Vexa's 10-second polling).
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
                stmt = select(Meeting).where(Meeting.scheduled_at > datetime.utcnow()).options(
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

