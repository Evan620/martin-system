import os
import io
import asyncio
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import json

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.models import Meeting, Minutes, MinutesStatus
from app.services.document_synthesizer import DocumentSynthesizer
from app.services.llm_service import get_llm_service
from loguru import logger

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

# Meet Recordings folder ID (from magwaro@ecowasiisummit.net Drive)
MEET_RECORDINGS_FOLDER_ID = '1INDXhbO0LTB9wX5uyyljHxb9ULS2N9sk'

class DriveService:
    """
    Service to interact with Google Drive, specifically to watch for 
    Meeting Recordings/Transcripts and ingest them.
    """
    def __init__(self):
        self.creds = None
        self.service = None
        self.state_file = "processed_transcripts.json"
        # We now initialize lazily on first use to avoid race conditions with startup credentials restoration

    def _load_state(self) -> Dict[str, str]:
        """Load processed files state {file_id: modified_time}"""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load state file: {e}")
        return {}

    def _save_state(self, state: Dict[str, str]):
        """Save processed files state"""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(state, f)
        except Exception as e:
            logger.error(f"Failed to save state file: {e}")

    def _setup_credentials(self):
        """Setup Google Drive credentials"""
        if self.service:
            return True
            
        try:
            # 1. Try OAuth2 User Token (Highest Priority for Bypass)
            if os.path.exists('token.json'):
                from google.oauth2.credentials import Credentials
                from google.auth.transport.requests import Request
                
                self.creds = Credentials.from_authorized_user_file('token.json', SCOPES)
                
                # Auto-refresh if needed
                if self.creds and self.creds.expired and self.creds.refresh_token:
                    logger.info("Refreshing Drive OAuth token...")
                    self.creds.refresh(Request())
                    with open('token.json', 'w') as token:
                        token.write(self.creds.to_json())
                
                self.service = build('drive', 'v3', credentials=self.creds)
                logger.info("DriveService initialized via token.json.")
                return True

            # 2. Fallback to Service Account
            creds_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
            if not creds_path and os.path.exists('google_credentials.json'):
                creds_path = 'google_credentials.json'
            
            if creds_path and os.path.exists(creds_path):
                self.creds = service_account.Credentials.from_service_account_file(
                    creds_path, scopes=SCOPES
                )
                self.service = build('drive', 'v3', credentials=self.creds)
                logger.info("DriveService initialized via Service Account.")
                return True
            else:
                logger.debug("No Google Credentials found yet.")
                return False
        except Exception as e:
            logger.warning(f"Failed to initialize DriveService: {e}")
            self.service = None
            return False

    def list_recent_transcripts(self, hours: int = 24) -> List[Dict[str, Any]]:
        """
        List transcript files modified in the last N hours.
        Searches for files with text/plain mimeType (transcripts) or Google Docs.
        Blocking call - should be run in thread.
        """
        if not self._setup_credentials():
            return []

        # Time filter
        time_threshold = (datetime.utcnow() - timedelta(hours=hours)).isoformat() + 'Z'
        
        query = (
            f"modifiedTime > '{time_threshold}' and "
            "trashed = false and "
            "(mimeType = 'text/plain' or mimeType = 'application/vnd.google-apps.document') and "
            "name contains 'Transcript'"
        )

        try:
            results = self.service.files().list(
                q=query,
                pageSize=10,
                fields="nextPageToken, files(id, name, modifiedTime, createdTime, mimeType)"
            ).execute(num_retries=3)
            items = results.get('files', [])
            return items
        except Exception as e:
            logger.error(f"Error listing Drive files: {e}")
            return []

    def download_file_content(self, file_id: str, mime_type: str) -> str:
        """Download text content of a file. Blocking call."""
        if not self._setup_credentials():
            return ""

        fh = None
        try:
            if mime_type == 'application/vnd.google-apps.document':
                request = self.service.files().export_media(fileId=file_id, mimeType='text/plain')
            else:
                request = self.service.files().get_media(fileId=file_id)

            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request, chunksize=1024*1024)  # 1MB chunks
            done = False
            
            # Add timeout protection
            max_iterations = 100  # Prevent infinite loops
            iteration = 0
            
            while not done and iteration < max_iterations:
                try:
                    status, done = downloader.next_chunk()
                    iteration += 1
                    
                    # Check file size to prevent memory exhaustion
                    if fh.tell() > 50 * 1024 * 1024:  # 50MB limit
                        logger.warning(f"File {file_id} exceeds 50MB, truncating")
                        break
                        
                except Exception as chunk_error:
                    logger.error(f"Error downloading chunk for {file_id}: {chunk_error}")
                    break

            # Get content and explicitly close buffer
            content = fh.getvalue().decode('utf-8', errors='ignore')
            fh.close()
            return content
            
        except Exception as e:
            logger.error(f"Error downloading file {file_id}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return ""
        finally:
            # Ensure buffer is always closed to prevent memory leaks
            if fh is not None:
                try:
                    fh.close()
                except:
                    pass

    async def process_new_transcripts(self):
        """
        Main logic: Check for new transcripts, match to meetings, generate minutes.
        Async compatible. Uses state tracking to avoid re-processing.
        """
        # Run blocking Google API call in thread
        files = await asyncio.to_thread(self.list_recent_transcripts, hours=24)
        
        if not files:
            return

        state = self._load_state()
        files_to_process = []

        # Filter out already processed files
        for file in files:
            file_id = file['id']
            modified_time = file['modifiedTime']
            
            # If we haven't seen this file, OR the modified time is different, process it
            if file_id not in state or state[file_id] != modified_time:
                files_to_process.append(file)
        
        if not files_to_process:
            return

        logger.info(f"Found {len(files_to_process)} new/modified transcripts to process.")

        async with AsyncSessionLocal() as db:
            try:
                # Warm up the async session
                await db.execute(text("SELECT 1"))
                
                synthesizer = DocumentSynthesizer(llm_client=get_llm_service())

                for file in files_to_process:
                    file_id = file['id']
                    filename = file['name']
                    modified_time = file['modifiedTime']
                    
                    logger.info(f"Processing transcript: {filename}")
                    
                    try:
                        # 1. MATCHING LOGIC (Lazy match first)
                        matched_meeting = await self._match_meeting(db, filename)
                        
                        if not matched_meeting:
                            logger.warning(f"Could not match transcript '{filename}' to any active meeting. Marking as processed to prevent retries.")
                            # Mark as processed so we don't spam logs. User must rename file to retry.
                            state[file_id] = modified_time
                            self._save_state(state)
                            continue

                        if matched_meeting.minutes:
                            logger.info(f"Meeting {matched_meeting.title} already has minutes. Skipping.")
                            state[file_id] = modified_time
                            self._save_state(state)
                            continue

                        # 2. DOWNLOAD CONTENT (Only if matched and needed)
                        logger.info(f"Match found: {matched_meeting.title}. Downloading content...")
                        mime_type = file.get('mimeType', 'text/plain')
                        content = await asyncio.to_thread(self.download_file_content, file_id, mime_type)

                        if not content:
                            logger.warning(f"Empty content for transcript: {filename}")
                            # Don't mark as processed? Or do? If empty, maybe persistent error. 
                            # Let's skip updating state so it retries if content appears later.
                            continue

                        logger.info(f"Generating minutes for meeting: {matched_meeting.title}")
                        
                        # Context for synthesizer
                        meeting_context = {
                            "meeting_title": matched_meeting.title,
                            "meeting_date": str(matched_meeting.scheduled_at),
                            "pillar_name": matched_meeting.twg.name if matched_meeting.twg else "General",
                            "attendees_list": "See transcript", 
                            "agenda_content": matched_meeting.agenda.content if matched_meeting.agenda else "Standard Agenda"
                        }
                        
                        # Synthesize minutes (wrap in thread since it's sync)
                        result = await asyncio.to_thread(
                            synthesizer.synthesize_minutes, 
                            content, 
                            meeting_context
                        )
                        minutes_text = result['content']
                        
                        # Save to DB with proper async handling
                        matched_meeting.transcript = content
                        
                        logger.info(f"Creating new minutes for meeting {matched_meeting.title}")
                        new_minutes = Minutes(
                            meeting_id=matched_meeting.id,
                            content=minutes_text,
                            status=MinutesStatus.DRAFT
                        )
                        db.add(new_minutes)
                        matched_meeting.minutes = new_minutes
                        
                        # Flush first to detect any errors early
                        await db.flush()
                        
                        # Commit the transaction
                        await db.commit()
                        
                        # Refresh to get updated state
                        await db.refresh(matched_meeting)
                        
                        logger.info(f"SUCCESS: Saved minutes for {matched_meeting.title}")
                        
                        # Update State on Success
                        state[file_id] = modified_time
                        self._save_state(state)
                    
                    except Exception as e:
                        logger.error(f"Error processing transcript '{filename}': {e}")
                        # Rollback this transaction and continue with next file
                        await db.rollback()
                        continue

            except Exception as e:
                logger.error(f"Error in transcript processing loop: {e}")
                await db.rollback()
    def search_meet_recordings_folder(self, hours: int = 24) -> List[Dict[str, Any]]:
        """
        Search the Meet Recordings folder for transcripts created in the last N hours.
        Returns list of transcript files (not recordings).
        Blocking call - should be run in thread.
        """
        if not self._setup_credentials():
            return []

        # Time filter
        time_threshold = (datetime.utcnow() - timedelta(hours=hours)).isoformat() + 'Z'
        
        # Search for transcript files (.sbv, .vtt, or text files with "Transcript" in name)
        query = (
            f"'{MEET_RECORDINGS_FOLDER_ID}' in parents and "
            f"createdTime >= '{time_threshold}' and "
            "trashed = false and "
            "(name contains 'Transcript' or name contains '.sbv' or name contains '.vtt')"
        )

        try:
            results = self.service.files().list(
                q=query,
                pageSize=20,
                orderBy='createdTime desc',
                fields="nextPageToken, files(id, name, createdTime, modifiedTime, mimeType)"
            ).execute(num_retries=3)
            items = results.get('files', [])
            logger.info(f"Found {len(items)} transcript files in Meet Recordings folder")
            return items
        except Exception as e:
            logger.error(f"Error searching Meet Recordings folder: {e}")
            return []

    async def process_drive_transcripts_fallback(self):
        """
        Fallback system: Check Meet Recordings folder for transcripts,
        match to meetings without transcripts, and process them.
        This catches meetings where Vexa wasn't admitted.
        """
        from sqlalchemy.orm import selectinload
        from difflib import SequenceMatcher
        
        # Get recent transcript files from Drive
        files = await asyncio.to_thread(self.search_meet_recordings_folder, hours=24)
        
        if not files:
            logger.debug("No new transcripts found in Meet Recordings folder")
            return

        async with AsyncSessionLocal() as db:
            try:
                # Get meetings from last 24 hours without transcripts
                time_threshold = datetime.utcnow() - timedelta(hours=24)
                result = await db.execute(
                    select(Meeting).where(
                        Meeting.scheduled_at >= time_threshold
                    ).options(
                        selectinload(Meeting.twg),
                        selectinload(Meeting.minutes),
                        selectinload(Meeting.agenda)
                    )
                )
                meetings = result.scalars().all()
                
                # Filter to meetings without transcripts
                meetings_without_transcripts = [
                    m for m in meetings 
                    if not m.transcript or m.transcript.strip() == ""
                ]
                
                if not meetings_without_transcripts:
                    logger.debug("All recent meetings already have transcripts")
                    return
                
                logger.info(f"Found {len(meetings_without_transcripts)} meetings without transcripts")
                
                state = self._load_state()
                
                for file in files:
                    file_id = file['id']
                    filename = file['name']
                    created_time = file['createdTime']
                    
                    # Skip if already processed
                    if file_id in state:
                        continue
                    
                    # Try to match to a meeting using fuzzy matching
                    best_match = None
                    best_score = 0.0
                    
                    for meeting in meetings_without_transcripts:
                        if not meeting.title:
                            continue
                        
                        # Calculate similarity score
                        similarity = SequenceMatcher(None, meeting.title.lower(), filename.lower()).ratio()
                        
                        # Also check if meeting title is substring of filename
                        if meeting.title.lower() in filename.lower():
                            similarity = max(similarity, 0.85)  # Boost score for substring match
                        
                        if similarity > best_score:
                            best_score = similarity
                            best_match = meeting
                    
                    # Only process if we have a good match (>70% similarity)
                    if best_match and best_score > 0.7:
                        logger.info(f"📄 Drive Fallback: Matched '{filename}' to meeting '{best_match.title}' (score: {best_score:.2f})")
                        
                        try:
                            # Download transcript content
                            content = await asyncio.to_thread(
                                self.download_file_content, 
                                file_id, 
                                file.get('mimeType', 'text/plain')
                            )
                            
                            if not content or len(content) < 50:
                                logger.warning(f"Transcript content too short or empty for {filename}")
                                continue
                            
                            # Process using Vexa service (reuse existing logic)
                            from app.services.vexa_service import vexa_service
                            
                            logger.info(f"Processing Drive transcript for meeting: {best_match.title}")
                            success = await vexa_service.process_transcript_text(
                                best_match, 
                                content, 
                                db
                            )
                            
                            if success:
                                logger.info(f"✅ Drive Fallback: Successfully processed transcript for {best_match.title}")
                                # Mark as processed
                                state[file_id] = created_time
                                self._save_state(state)
                                
                                # Broadcast update to frontend
                                try:
                                    from app.services.broadcast_service import get_broadcast_service
                                    broadcast = get_broadcast_service()
                                    await broadcast.notify_live_meeting(
                                        meeting_id=str(best_match.id),
                                        content=f"Transcript processed from Google Drive",
                                        source="google_drive",
                                        metadata={
                                            "type": "transcript_processed",
                                            "meeting_id": str(best_match.id)
                                        }
                                    )
                                except Exception as e:
                                    logger.warning(f"Failed to broadcast Drive transcript update: {e}")
                                
                                # Remove from list so we don't try to match it again
                                meetings_without_transcripts.remove(best_match)
                            else:
                                logger.warning(f"Failed to process Drive transcript for {best_match.title}")
                        
                        except Exception as e:
                            logger.error(f"Error processing Drive transcript {filename}: {e}")
                            continue
                    else:
                        if best_score > 0:
                            logger.debug(f"No good match for '{filename}' (best: {best_match.title if best_match else 'none'}, score: {best_score:.2f})")
                
            except Exception as e:
                logger.error(f"Error in Drive transcript fallback: {e}")
                await db.rollback()

    async def _match_meeting(self, db: AsyncSession, filename: str) -> Optional[Meeting]:
        """
        Attempt to match a transcript filename to a DB meeting.
        """
        # Import selectinload for eager loading
        from sqlalchemy.orm import selectinload
        
        # Fetch all meetings with TWG relationship eagerly loaded
        # This prevents lazy loading which causes greenlet errors
        result = await db.execute(
            select(Meeting).options(
                selectinload(Meeting.twg),
                selectinload(Meeting.minutes),
                selectinload(Meeting.agenda)
            )
        )
        all_meetings = result.scalars().all()
        
        # Simple heuristic match
        # Iterate through meetings to find a match in the filename
        # Prioritize longer titles to avoid "1" matching "Q1"
        sorted_meetings = sorted(all_meetings, key=lambda m: len(m.title) if m.title else 0, reverse=True)
        
        for meeting in sorted_meetings:
            if not meeting.title:
                continue
                
            # Ignore short titles to prevent false positives (e.g., title "1" matching "Q1")
            if len(meeting.title) < 3:
                continue
                
            if meeting.title in filename:
                return meeting
        
        return None

# Singleton
drive_service = DriveService()
