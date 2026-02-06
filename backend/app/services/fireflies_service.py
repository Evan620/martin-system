"""
Fireflies.ai Service

Handles meeting transcription via Fireflies.ai GraphQL API.
Provides methods to fetch transcripts, list meetings, and manage transcription data.
"""

import aiohttp
import logging
import asyncio
import os
import time
import aiofiles
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.models.models import Meeting, Minutes, MinutesStatus, ActionItem, ActionItemStatus, MeetingStatus
from app.services.document_synthesizer import DocumentSynthesizer
from app.services.llm_service import get_llm_service
from sqlalchemy import select, and_, or_
import datetime
from datetime import datetime, UTC

logger = logging.getLogger(__name__)

class FirefliesService:
    """Service for interacting with Fireflies.ai API"""
    
    def __init__(self):
        self.api_key = settings.FIREFLIES_API_KEY
        self.api_url = settings.FIREFLIES_API_URL
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        # Rate-limit state
        self._rate_limited_until: float = 0.0  # Unix timestamp when we can retry
        self._consecutive_failures: int = 0

    # ── Rate-limit helpers ────────────────────────────────────────────

    def _is_rate_limited(self) -> bool:
        """Return True if we should skip API calls due to an active rate-limit backoff."""
        if time.time() < self._rate_limited_until:
            remaining = int(self._rate_limited_until - time.time())
            logger.info(f"Fireflies API rate-limited — skipping call ({remaining}s remaining)")
            return True
        return False

    def _record_rate_limit(self, retry_after: Optional[int] = None):
        """Back off after a 429 or repeated failure. Uses Retry-After header if available."""
        self._consecutive_failures += 1
        if retry_after and retry_after > 0:
            backoff_secs = retry_after
        else:
            # Exponential backoff: 30s, 60s, 120s, … capped at max
            backoff_secs = min(
                30 * (2 ** (self._consecutive_failures - 1)),
                settings.FIREFLIES_MAX_BACKOFF_MINUTES * 60,
            )
        self._rate_limited_until = time.time() + backoff_secs
        logger.warning(
            f"Fireflies rate-limit recorded — backing off {backoff_secs}s "
            f"(consecutive failures: {self._consecutive_failures})"
        )

    def _record_success(self):
        """Reset failure counter on a successful API call."""
        if self._consecutive_failures > 0:
            logger.info(f"Fireflies API recovered after {self._consecutive_failures} consecutive failures")
        self._consecutive_failures = 0

    def get_rate_limit_status(self) -> Dict[str, Any]:
        """Public status for the monitor to decide whether to poll."""
        now = time.time()
        return {
            "is_rate_limited": now < self._rate_limited_until,
            "seconds_remaining": max(0, int(self._rate_limited_until - now)),
            "consecutive_failures": self._consecutive_failures,
        }

    # ── Centralised GraphQL caller ────────────────────────────────────

    async def _make_request(self, query: str, variables: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Send a GraphQL request to Fireflies with rate-limit gating and 429 handling.
        Returns the parsed JSON body on success, or None on failure.
        """
        if self._is_rate_limited():
            return None

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.api_url,
                    json={"query": query, "variables": variables},
                    headers=self.headers,
                    timeout=aiohttp.ClientTimeout(total=60),
                ) as response:
                    if response.status == 429:
                        retry_after = None
                        raw = response.headers.get("Retry-After")
                        if raw:
                            try:
                                retry_after = int(raw)
                            except ValueError:
                                pass
                        self._record_rate_limit(retry_after)
                        return None

                    if response.status == 200:
                        self._record_success()
                        return await response.json()

                    error_text = await response.text()
                    logger.error(f"Fireflies API error {response.status}: {error_text}")
                    self._record_rate_limit()
                    return None
        except aiohttp.ClientError as e:
            logger.error(f"Network error calling Fireflies API: {e}")
            self._record_rate_limit()
            return None
        except Exception as e:
            logger.error(f"Unexpected error calling Fireflies API: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    async def get_transcript(self, meeting_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch transcript from Fireflies using GraphQL.

        Args:
            meeting_id: Fireflies meeting/transcript ID

        Returns:
            Dict containing transcript data or None if not found
        """
        query = """
        query Transcript($transcriptId: String!) {
          transcript(id: $transcriptId) {
            id
            title
            date
            sentences {
              text
              raw_text
              speaker_name
              speaker_id
              start_time
              end_time
            }
            summary {
              keywords
              action_items
              outline
              shorthand_bullet
              overview
              bullet_gist
            }
            participants
            duration
          }
        }
        """

        variables = {"transcriptId": meeting_id}
        data = await self._make_request(query, variables)

        if data is None:
            return None

        if "errors" in data:
            logger.warning(f"Fireflies GraphQL returned errors (partial data may be available): {data['errors']}")

        transcript_data = data.get("data", {}).get("transcript")
        if transcript_data:
            logger.info(f"✓ Retrieved transcript {meeting_id} from Fireflies")
            return transcript_data
        elif "errors" in data:
            logger.error("Fireflies query failed with no data returned.")
            return None
        else:
            logger.warning(f"No transcript found for ID: {meeting_id}")
            return None
    
    async def list_transcripts(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        List recent transcripts from Fireflies.

        Args:
            limit: Maximum number of transcripts to return

        Returns:
            List of transcript summaries
        """
        query = """
        query Transcripts($limit: Int!) {
          transcripts(limit: $limit) {
            id
            title
            date
            duration
            participants
            summary {
              keywords
              overview
            }
          }
        }
        """

        variables = {"limit": limit}
        data = await self._make_request(query, variables)

        if data is None:
            return []

        if "errors" in data:
            logger.warning(f"Fireflies GraphQL errors (listing): {data['errors']}")

        transcripts = data.get("data", {}).get("transcripts", [])
        if transcripts:
            logger.info(f"✓ Retrieved {len(transcripts)} transcripts from Fireflies")
        return transcripts
    
    async def search_transcripts_by_title(self, title: str) -> Optional[Dict[str, Any]]:
        """
        Search for a transcript by meeting title.
        
        Args:
            title: Meeting title to search for
            
        Returns:
            First matching transcript or None
        """
        # Fireflies doesn't have a direct title search in their API
        # So we'll list recent transcripts and filter
        transcripts = await self.list_transcripts(limit=50)
        
        for transcript in transcripts:
            if title.lower() in transcript.get("title", "").lower():
                # Fetch full transcript data
                return await self.get_transcript(transcript["id"])
        
        logger.warning(f"No transcript found matching title: {title}")
        return None
    
    def format_transcript_text(self, transcript_data: Dict[str, Any]) -> str:
        """
        Format Fireflies transcript data into readable text.
        
        Args:
            transcript_data: Raw transcript data from Fireflies
            
        Returns:
            Formatted transcript text
        """
        if not transcript_data:
            return ""

        # Fireflies returns sentences under "sentences" or aliased as "transcript_text"
        sentences = transcript_data.get("sentences") or transcript_data.get("transcript_text") or []
        if not sentences:
            logger.warning(f"No sentences found in transcript data. Keys present: {list(transcript_data.keys())}")
            return ""
        
        # Group by speaker and format
        formatted_lines = []
        current_speaker = None
        
        for sentence in sentences:
            speaker = sentence.get("speaker_name", "Unknown")
            text = sentence.get("text", sentence.get("raw_text", ""))
            
            if speaker != current_speaker:
                if current_speaker is not None:
                    formatted_lines.append("")  # Add blank line between speakers
                formatted_lines.append(f"{speaker}:")
                current_speaker = speaker
            
            formatted_lines.append(f"  {text}")
        
        return "\n".join(formatted_lines)

    async def process_transcript_text(self, meeting: Meeting, transcript_text: str, db: AsyncSession):
        """
        Generate minutes from transcript text and save to DB.
        """
        try:
             logger.info(f"Generating minutes for {meeting.title}...")
             
             # Save transcript to file (for Download button)
             file_name = f"transcript_{meeting.id}.txt"
             upload_dir = os.path.join(settings.UPLOAD_DIR, "transcripts")
             os.makedirs(upload_dir, exist_ok=True)
             file_path = os.path.join(upload_dir, file_name)
             
             async with aiofiles.open(file_path, 'w') as f:
                 await f.write(transcript_text)
                 
             logger.info(f"Transcript saved to disk: {file_path}")

             # Save transcript to meeting
             meeting.transcript = transcript_text
             
             # Generate Minutes
             synthesizer = DocumentSynthesizer(llm_client=get_llm_service())
             minutes_ctx = {
                 "meeting_title": meeting.title,
                 "meeting_date": str(meeting.scheduled_at),
                 "attendees_list": "See transcript (Fireflies)"
             }
             
             # Blocking call in thread
             res = await asyncio.to_thread(synthesizer.synthesize_minutes, transcript_text, minutes_ctx)
             
             new_minutes = Minutes(
                meeting_id=meeting.id,
                content=res['content'],
                status=MinutesStatus.DRAFT
             )
             db.add(new_minutes)
             meeting.minutes = new_minutes
             logger.info(f"Generated Minutes for {meeting.title} from Fireflies")

             # --- NEW: Extract Action Items Automatically ---
             try:
                 logger.info("Extracting action items...")
                 
                 # Safely get pillar value with fallback
                 pillar_val = "energy"  # Default fallback
                 try:
                     if meeting.twg and hasattr(meeting.twg, 'pillar'):
                         pillar_val = meeting.twg.pillar.value if hasattr(meeting.twg.pillar, 'value') else str(meeting.twg.pillar)
                 except AttributeError as attr_err:
                     logger.warning(f"Could not access meeting.twg.pillar: {attr_err}. Using default pillar 'energy'")
                 
                 # Run extraction
                 actions_list = await synthesizer.extract_action_items(
                     res['content'],
                     pillar_val
                 )
                 
                 action_count = 0
                 for action in actions_list:
                     desc = action.get("description")
                     if not desc: continue
                     
                     logger.debug(f"Skipping action item auto-creation: '{desc[:50]}...' (owner: {action.get('owner', 'TBD')})")
                     # Logic for adding action items can be enabled here if needed
                 
                 if action_count > 0:
                     logger.info(f"✓ Automatically extracted {action_count} action items from minutes.")
             except Exception as ae:
                 logger.error(f"Failed to auto-extract action items: {ae}")
                 import traceback
                 logger.error(f"Traceback: {traceback.format_exc()}")
             
             # -----------------------------------------
             
             # Flush the minutes to DB before distribution
             await db.flush()
             await db.refresh(new_minutes)
             logger.info(f"Minutes flushed to database with ID: {new_minutes.id}, meeting_id: {new_minutes.meeting_id}")

             return file_path # Return path for the Monitor to update Document
        except Exception as e:
            logger.error(f"Failed to process transcript for {meeting.title}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            # Rollback to prevent transaction corruption
            await db.rollback()
            return False

    async def finalize_and_distribute_minutes(self, meeting: Meeting, db: AsyncSession):
        """
        updates minutes status to APPROVED, generates PDF, indexes to KB, and sends emails.
        """
        from app.services.pdf_service import pdf_service
        from app.services.email_service import email_service
        from app.core.knowledge_base import get_knowledge_base
        from app.models.models import MinutesStatus
        
        # 1. Update Status
        if meeting.minutes:
            # Ensure the minutes object is attached to the session and has meeting_id
            await db.refresh(meeting.minutes)
            meeting.minutes.status = MinutesStatus.APPROVED
            # Explicitly set meeting_id to prevent NULL constraint violation
            if not meeting.minutes.meeting_id:
                meeting.minutes.meeting_id = meeting.id
            await db.flush()  # Flush instead of commit to keep transaction open
            logger.info("Minutes status updated to APPROVED")
            
        # 2. Generate PDF
        pdf_bytes = None
        try:
            pillar_display = "General"
            if meeting.twg:
                pillar_display = meeting.twg.pillar.value.replace("_", " ").title() if hasattr(meeting.twg.pillar, 'value') else str(meeting.twg.pillar)
            
            pdf_context = {
                "pillar_name": pillar_display,
                "meeting_title": meeting.title,
                "meeting_date": meeting.scheduled_at.strftime('%Y-%m-%d') if meeting.scheduled_at else "TBD",
                "meeting_time": meeting.scheduled_at.strftime('%H:%M') if meeting.scheduled_at else "",
                "location": meeting.location or "Virtual",
            }
            
            # Ensure we have the latest content
            if meeting.minutes and meeting.minutes.content:
                pdf_bytes = pdf_service.generate_minutes_pdf(
                    minutes_markdown=meeting.minutes.content,
                    template_context=pdf_context
                )
                logger.info("Minutes PDF generated successfully")
        except Exception as e:
            logger.error(f"PDF Generation Failed: {e}")

        # 2b. Save PDF to disk and create Document record for the Document Library
        if pdf_bytes:
            try:
                from app.models.models import Document, User
                upload_dir = os.path.join(settings.UPLOAD_DIR, "minutes")
                os.makedirs(upload_dir, exist_ok=True)
                pdf_filename = f"Minutes - {meeting.title}.pdf"
                pdf_path = os.path.join(upload_dir, f"minutes_{meeting.id}.pdf")
                with open(pdf_path, "wb") as f:
                    f.write(pdf_bytes)

                # Check if a minutes Document already exists
                existing = await db.execute(
                    select(Document).where(
                        and_(Document.meeting_id == meeting.id, Document.document_type == "minutes")
                    )
                )
                if not existing.scalar_one_or_none():
                    res_u = await db.execute(select(User.id).limit(1))
                    uploader_id = res_u.scalars().first()
                    if uploader_id:
                        minutes_doc = Document(
                            twg_id=meeting.twg_id,
                            meeting_id=meeting.id,
                            file_name=pdf_filename,
                            file_path=pdf_path,
                            file_type="application/pdf",
                            document_type="minutes",
                            uploaded_by_id=uploader_id,
                            metadata_json={
                                "meeting_id": str(meeting.id),
                                "meeting_title": meeting.title,
                                "status": "approved",
                                "file_size": len(pdf_bytes),
                            }
                        )
                        db.add(minutes_doc)
                        await db.flush()
                        logger.info(f"Minutes Document record created for '{meeting.title}'")
            except Exception as e:
                logger.error(f"Minutes Document creation failed: {e}")

        # 3. Index to Knowledge Base
        try:
            if meeting.minutes and meeting.minutes.content:
                kb = get_knowledge_base()
                kb.add_document(
                    content=meeting.minutes.content,
                    metadata={
                        "source": "official_minutes",
                        "meeting_id": str(meeting.id),
                        "date": meeting.scheduled_at.isoformat() if meeting.scheduled_at else None,
                        "pillar": meeting.twg.pillar.value if meeting.twg and hasattr(meeting.twg.pillar, 'value') else "unknown",
                        "status": "approved",
                        "file_name": f"Minutes - {meeting.title}"
                    },
                    namespace=f"twg-{meeting.twg.id}" if meeting.twg_id else "global"
                )
                logger.info("Minutes indexed to Knowledge Base")
        except Exception as e:
            logger.error(f"KB Indexing Failed: {e}")

        # 4. Send Emails
        recipients = set()
        for p in meeting.participants:
            if p.user and p.user.email:
                recipients.add(p.user.email)
            elif p.email:
                recipients.add(p.email)
        
        recipient_list = list(recipients)
        
        if pdf_bytes and recipient_list:
            try:
                pillar_display = "General"
                if meeting.twg:
                     pillar_display = meeting.twg.pillar.value.replace("_", " ").title() if hasattr(meeting.twg.pillar, 'value') else str(meeting.twg.pillar)

                email_context = {
                    "recipient_name": "Colleague", 
                    "meeting_title": meeting.title,
                    "date_str": meeting.scheduled_at.strftime('%Y-%m-%d') if meeting.scheduled_at else "TBD",
                    "pillar_name": pillar_display,
                    "dashboard_url": f"{settings.FRONTEND_URL}/meetings/{meeting.id}"
                }
                
                logger.info(f"Sending Minutes PDF to {len(recipient_list)} recipients...")
                await email_service.send_minutes_published_email(
                    to_emails=recipient_list,
                    template_context=email_context,
                    pdf_content=pdf_bytes,
                    pdf_filename=f"Minutes - {meeting.title}.pdf"
                )
                logger.info("Minutes emails sent successfully")
            except Exception as e:
                logger.error(f"Email Sending Failed: {e}")

    async def process_webhook(self, payload: Dict[str, Any]):
        """
        Process incoming webhook from Fireflies.
        Fireflies sends: {"meetingId": "...", "eventType": "Transcription completed"}
        We use the meetingId to fetch the full transcript via the GraphQL API.
        """
        try:
            logger.info("Processing Fireflies webhook...")

            # Fireflies webhook payload: {"meetingId": "...", "eventType": "..."}
            fireflies_meeting_id = payload.get("meetingId")

            if not fireflies_meeting_id:
                logger.warning(f"Webhook payload missing meetingId: {payload.keys()}")
                return

            logger.info(f"Webhook received for Fireflies meetingId: {fireflies_meeting_id}")

            # Fetch the full transcript from Fireflies API
            full_transcript = await self.get_transcript(fireflies_meeting_id)
            if not full_transcript:
                logger.error(f"Could not fetch transcript for meetingId={fireflies_meeting_id}")
                return

            title = full_transcript.get("title", "")
            if not title:
                logger.warning("Fetched transcript has no title, cannot match to local meeting")
                return

            logger.info(f"Fetched transcript: '{title}' (Fireflies ID: {fireflies_meeting_id})")

            # Format the transcript text
            text = self.format_transcript_text(full_transcript)
            if not text:
                logger.warning(f"Transcript sentences empty for '{title}'. Fireflies may still be processing.")
                return

            logger.info(f"Formatted transcript for '{title}': {len(text)} chars")

            from app.core.database import get_db_session_context
            from sqlalchemy.orm import selectinload
            from app.models.models import MeetingParticipant
            from datetime import datetime, UTC

            async with get_db_session_context() as db:
                # Find local meeting by title match (no transcript yet)
                stmt = select(Meeting).options(
                    selectinload(Meeting.twg),
                    selectinload(Meeting.minutes),
                    selectinload(Meeting.participants).selectinload(MeetingParticipant.user),
                ).where(
                     and_(
                        Meeting.title.ilike(f"%{title}%"),
                        or_(Meeting.transcript.is_(None), Meeting.transcript == "")
                     )
                ).order_by(Meeting.scheduled_at.desc())

                result = await db.execute(stmt)
                candidate_meetings = result.scalars().all()

                matched_meeting = None

                # Try date matching first
                webhook_date = full_transcript.get("date")
                webhook_dt = None
                if webhook_date:
                    try:
                        if isinstance(webhook_date, (int, float)):
                            webhook_dt = datetime.fromtimestamp(webhook_date / 1000.0, tz=UTC)
                    except Exception:
                        pass

                for meeting in candidate_meetings:
                    if webhook_dt:
                        meeting_dt = meeting.scheduled_at.replace(tzinfo=UTC)
                        if abs((meeting_dt - webhook_dt).total_seconds()) < 3600 * 24:
                            matched_meeting = meeting
                            break
                    else:
                        matched_meeting = meeting
                        break

                if matched_meeting:
                     logger.info(f"Matched webhook to local meeting: {matched_meeting.title} ({matched_meeting.id})")
                     
                     # Process
                     file_path = await self.process_transcript_text(matched_meeting, text, db)

                     # Update status
                     matched_meeting.status = MeetingStatus.COMPLETED

                     # Create a Document record so it appears in meeting documents
                     if file_path and isinstance(file_path, str):
                         from app.models.models import Document, User
                         res_u = await db.execute(select(User.id).limit(1))
                         uploader_id = res_u.scalars().first()
                         if uploader_id:
                             doc = Document(
                                 twg_id=matched_meeting.twg_id,
                                 meeting_id=matched_meeting.id,
                                 file_name=f"Fireflies Transcript - {matched_meeting.title}.txt",
                                 file_path=file_path,
                                 file_type="text/plain",
                                 document_type="transcript",
                                 uploaded_by_id=uploader_id,
                                 metadata_json={
                                     "provider": "fireflies",
                                     "fireflies_id": fireflies_meeting_id,
                                     "meeting_id": str(matched_meeting.id),
                                 }
                             )
                             db.add(doc)

                     await db.commit()
                     logger.info("Webhook processing complete — transcript saved, minutes drafted.")

                     # Auto-approve minutes and distribute (PDF + email)
                     try:
                         logger.info(f"Auto-approving and distributing minutes for '{matched_meeting.title}'...")
                         await self.finalize_and_distribute_minutes(matched_meeting, db)
                         await db.commit()
                         logger.info(f"Minutes auto-approved and distributed for '{matched_meeting.title}'")
                     except Exception as approve_err:
                         logger.error(f"Auto-approval/distribution failed: {approve_err}")
                         import traceback
                         logger.error(traceback.format_exc())

                     # Broadcast real-time update to frontend
                     try:
                         from app.services.broadcast_service import get_broadcast_service
                         broadcast = get_broadcast_service()
                         await broadcast.notify_meeting_update(matched_meeting.id, {
                             "status": "COMPLETED",
                             "has_transcript": True,
                             "has_minutes": True,
                             "minutes_approved": True,
                             "title": matched_meeting.title
                         })
                     except Exception as broadcast_err:
                         logger.error(f"Broadcast after webhook failed: {broadcast_err}")
                     
                else:
                    logger.warning(f"No local meeting found matching webhook title: {title}")

        except Exception as e:
            logger.error(f"Error processing webhook: {e}")
            import traceback
            logger.error(traceback.format_exc())

# Singleton instance
fireflies_service = FirefliesService()
