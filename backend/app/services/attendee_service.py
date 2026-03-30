"""
Attendee Meeting Bot Service

Self-hosted meeting transcription via Attendee (open-source, MIT).
Supports Google Meet, Zoom, and Microsoft Teams.
Replaces both Fireflies.ai and Vexa integrations.

API: REST (POST /bots, GET /bots/{id}, GET /bots/{id}/transcript, POST /bots/{id}/leave)
Auth: Token-based (Authorization: Token <key>)
Webhooks: transcript.update, bot.state_change (HMAC-SHA256 verified)
"""

import re
import aiohttp
import asyncio
import logging
import os
import time
import aiofiles
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload
from app.core.config import settings
from app.models.models import (
    Meeting, Minutes, MinutesStatus, ActionItem, ActionItemStatus,
    ActionItemPriority, MeetingStatus, MeetingParticipant, User, UserRole,
    Document
)
from app.services.document_synthesizer import DocumentSynthesizer
from app.services.llm_service import get_llm_service
from datetime import datetime, timezone, timedelta

UTC = timezone.utc
logger = logging.getLogger(__name__)


class AttendeeService:
    """Service for interacting with self-hosted Attendee meeting bot API."""

    def __init__(self):
        self.api_url = settings.ATTENDEE_API_URL.rstrip("/")
        self.api_key = settings.ATTENDEE_API_KEY
        self.webhook_secret = settings.ATTENDEE_WEBHOOK_SECRET
        self.bot_name = settings.ATTENDEE_BOT_NAME
        self.headers = {
            "Authorization": f"Token {self.api_key}",
            "Content-Type": "application/json",
        }
        # Rate-limit state
        self._rate_limited_until: float = 0.0
        self._consecutive_failures: int = 0

    # ── Rate-limit helpers ────────────────────────────────────────────

    def _is_rate_limited(self) -> bool:
        if time.time() < self._rate_limited_until:
            remaining = int(self._rate_limited_until - time.time())
            logger.info(f"Attendee API rate-limited — skipping call ({remaining}s remaining)")
            return True
        return False

    def _record_rate_limit(self, retry_after: Optional[int] = None):
        self._consecutive_failures += 1
        if retry_after and retry_after > 0:
            backoff_secs = retry_after
        else:
            backoff_secs = min(
                30 * (2 ** (self._consecutive_failures - 1)),
                settings.ATTENDEE_MAX_BACKOFF_MINUTES * 60,
            )
        self._rate_limited_until = time.time() + backoff_secs
        logger.warning(
            f"Attendee rate-limit recorded — backing off {backoff_secs}s "
            f"(consecutive failures: {self._consecutive_failures})"
        )

    def _record_success(self):
        if self._consecutive_failures > 0:
            logger.info(f"Attendee API recovered after {self._consecutive_failures} consecutive failures")
        self._consecutive_failures = 0

    def get_rate_limit_status(self) -> Dict[str, Any]:
        now = time.time()
        return {
            "is_rate_limited": now < self._rate_limited_until,
            "seconds_remaining": max(0, int(self._rate_limited_until - now)),
            "consecutive_failures": self._consecutive_failures,
        }

    # ── Centralised HTTP caller ───────────────────────────────────────

    async def _make_request(
        self,
        method: str,
        path: str,
        json_body: Optional[Dict] = None,
        timeout: int = 60,
    ) -> Optional[Dict[str, Any]]:
        """
        Send an HTTP request to Attendee with rate-limit gating and 429 handling.
        Returns parsed JSON on success, or None on failure.
        """
        if self._is_rate_limited():
            return None

        url = f"{self.api_url}{path}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method,
                    url,
                    json=json_body,
                    headers=self.headers,
                    timeout=aiohttp.ClientTimeout(total=timeout),
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

                    if response.status in (200, 201):
                        self._record_success()
                        return await response.json()

                    error_text = await response.text()
                    logger.error(f"Attendee API error {response.status} {method} {path}: {error_text}")
                    if response.status >= 500:
                        self._record_rate_limit()
                    return None
        except aiohttp.ClientError as e:
            logger.error(f"Network error calling Attendee API: {e}")
            self._record_rate_limit()
            return None
        except Exception as e:
            logger.error(f"Unexpected error calling Attendee API: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None

    # ── Bot management API ────────────────────────────────────────────

    async def dispatch_bot(
        self,
        meeting_url: str,
        meeting_id: str,
        bot_name: Optional[str] = None,
    ) -> Optional[str]:
        """
        Dispatch a bot to join a meeting.
        Returns the bot_id on success, or None on failure.
        """
        payload = {
            "meeting_url": meeting_url,
            "bot_name": bot_name or self.bot_name,
            "transcription_settings": {"meeting_closed_captions": {}},
        }
        # Register per-bot webhook for instant transcript delivery
        webhook_url = settings.ATTENDEE_WEBHOOK_URL
        if webhook_url:
            payload["webhooks"] = [
                {
                    "url": webhook_url,
                    "triggers": ["bot.state_change", "transcript.update"],
                }
            ]
        data = await self._make_request("POST", "/bots", json_body=payload)
        if data:
            bot_id = data.get("id") or data.get("bot_id")
            logger.info(f"Attendee bot dispatched to {meeting_url} — bot_id={bot_id}")
            return bot_id
        return None

    async def get_bot_status(self, bot_id: str) -> Optional[Dict[str, Any]]:
        """Get the current state of a bot. Returns full bot object or None."""
        return await self._make_request("GET", f"/bots/{bot_id}")

    async def get_transcript(self, bot_id: str) -> Optional[List[Dict[str, Any]]]:
        """
        Fetch transcript for a bot.
        Returns list of transcript entries [{speaker_name, transcription, timestamp_ms}] or None.
        """
        data = await self._make_request("GET", f"/bots/{bot_id}/transcript")
        if data is None:
            return None
        # Attendee may return {"transcript": [...]} or a bare list
        if isinstance(data, list):
            return data
        return data.get("transcript", data.get("results", []))

    async def leave_bot(self, bot_id: str) -> bool:
        """Tell the bot to leave the meeting. Returns True on success."""
        data = await self._make_request("POST", f"/bots/{bot_id}/leave")
        if data is not None:
            logger.info(f"Attendee bot {bot_id} instructed to leave")
            return True
        return False

    # ── Transcript formatting ─────────────────────────────────────────

    def format_transcript_text(self, transcript_data: List[Dict[str, Any]]) -> str:
        """
        Convert Attendee transcript array to readable text.
        Input: [{speaker_name, transcription, timestamp_ms}, ...]
        Output: Speaker-grouped text blocks.
        """
        if not transcript_data:
            return ""

        formatted_lines = []
        current_speaker = None

        for entry in transcript_data:
            speaker = entry.get("speaker_name") or entry.get("speaker") or "Unknown"
            raw = entry.get("transcription") or entry.get("text") or ""
            # transcription may be a dict like {"transcript": "Hello"} or a plain string
            text = raw.get("transcript", "") if isinstance(raw, dict) else str(raw)
            if not text.strip():
                continue

            if speaker != current_speaker:
                if current_speaker is not None:
                    formatted_lines.append("")
                formatted_lines.append(f"{speaker}:")
                current_speaker = speaker

            formatted_lines.append(f"  {text}")

        return "\n".join(formatted_lines)

    # ── Transcript processing (carried over from FirefliesService) ────

    async def process_transcript_text(self, meeting: Meeting, transcript_text: str, db: AsyncSession):
        """
        Generate minutes from transcript text and save to DB.
        Returns file_path on success, False on failure.
        """
        try:
            logger.info(f"Generating minutes for {meeting.title}...")

            # Save transcript to file
            file_name = f"transcript_{meeting.id}.txt"
            upload_dir = os.path.join(settings.UPLOAD_DIR, "transcripts")
            os.makedirs(upload_dir, exist_ok=True)
            file_path = os.path.join(upload_dir, file_name)

            async with aiofiles.open(file_path, 'w') as f:
                await f.write(transcript_text)
            logger.info(f"Transcript saved to disk: {file_path}")

            meeting.transcript = transcript_text

            # Generate Minutes
            synthesizer = DocumentSynthesizer(llm_client=get_llm_service())
            minutes_ctx = {
                "meeting_title": meeting.title,
                "meeting_date": str(meeting.scheduled_at),
                "attendees_list": "See transcript (Attendee)",
            }

            res = await asyncio.to_thread(synthesizer.synthesize_minutes, transcript_text, minutes_ctx)

            new_minutes = Minutes(
                meeting_id=meeting.id,
                content=res['content'],
                status=MinutesStatus.DRAFT,
            )
            db.add(new_minutes)
            meeting.minutes = new_minutes
            logger.info(f"Generated Minutes for {meeting.title} from Attendee")

            # Extract Action Items
            try:
                logger.info("Extracting action items...")
                pillar_val = "energy"
                try:
                    if meeting.twg and hasattr(meeting.twg, 'pillar'):
                        pillar_val = meeting.twg.pillar.value if hasattr(meeting.twg.pillar, 'value') else str(meeting.twg.pillar)
                except AttributeError as attr_err:
                    logger.warning(f"Could not access meeting.twg.pillar: {attr_err}. Using default pillar 'energy'")

                actions_list = await synthesizer.extract_action_items(res['content'], pillar_val)

                default_owner_id = await self._resolve_default_owner(meeting.id, db)
                action_count = 0
                for action in actions_list:
                    desc = action.get("description")
                    if not desc:
                        continue

                    owner_id = None
                    owner_name = action.get("owner", "")
                    if owner_name and owner_name.upper() not in ("TBD", "N/A", ""):
                        owner_id = await self._resolve_owner_by_name(meeting.id, owner_name, db)

                    if not owner_id:
                        owner_id = default_owner_id

                    if not owner_id:
                        logger.warning(f"Skipping action item (no owner found): '{desc[:60]}'")
                        continue

                    due_date = None
                    raw_due = action.get("due_date") or action.get("deadline")
                    if raw_due:
                        try:
                            due_date = datetime.fromisoformat(str(raw_due).replace("Z", "+00:00"))
                        except (ValueError, TypeError):
                            pass
                    if not due_date:
                        due_date = datetime.now(UTC) + timedelta(days=14)

                    new_action = ActionItem(
                        twg_id=meeting.twg_id,
                        meeting_id=meeting.id,
                        description=desc,
                        owner_id=owner_id,
                        due_date=due_date,
                        status=ActionItemStatus.PENDING,
                        priority=ActionItemPriority.MEDIUM,
                    )
                    db.add(new_action)
                    action_count += 1
                    logger.info(f"Created action item: '{desc[:60]}' (owner: {owner_name or 'default'})")

                if action_count > 0:
                    logger.info(f"Automatically extracted {action_count} action items from minutes.")
            except Exception as ae:
                logger.error(f"Failed to auto-extract action items: {ae}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")

            # Flush minutes to DB
            await db.flush()
            await db.refresh(new_minutes)
            logger.info(f"Minutes flushed to database with ID: {new_minutes.id}")

            return file_path
        except Exception as e:
            logger.error(f"Failed to process transcript for {meeting.title}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            await db.rollback()
            return False

    async def _resolve_owner_by_name(self, meeting_id, owner_name: str, db: AsyncSession):
        """Match an owner name string to a meeting participant's user_id."""
        try:
            result = await db.execute(
                select(User.id)
                .join(MeetingParticipant, MeetingParticipant.user_id == User.id)
                .where(
                    MeetingParticipant.meeting_id == meeting_id,
                    User.full_name.ilike(f"%{owner_name.strip()}%"),
                )
                .limit(1)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.debug(f"Owner name lookup failed for '{owner_name}': {e}")
            return None

    async def _resolve_default_owner(self, meeting_id, db: AsyncSession):
        """Find default owner: TWG facilitator > first participant > first admin."""
        try:
            # 1. TWG Facilitator among participants
            result = await db.execute(
                select(User.id)
                .join(MeetingParticipant, MeetingParticipant.user_id == User.id)
                .where(
                    MeetingParticipant.meeting_id == meeting_id,
                    User.role == UserRole.TWG_FACILITATOR,
                )
                .limit(1)
            )
            facilitator_id = result.scalar_one_or_none()
            if facilitator_id:
                return facilitator_id

            # 2. First participant with a user_id
            result = await db.execute(
                select(MeetingParticipant.user_id)
                .where(
                    MeetingParticipant.meeting_id == meeting_id,
                    MeetingParticipant.user_id.isnot(None),
                )
                .limit(1)
            )
            participant_uid = result.scalar_one_or_none()
            if participant_uid:
                return participant_uid

            # 3. First admin in the system
            result = await db.execute(
                select(User.id).where(User.role == UserRole.ADMIN).limit(1)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Failed to resolve default owner for meeting {meeting_id}: {e}")
            return None

    # ── Minutes finalization & distribution (carried over from FirefliesService) ──

    async def finalize_and_distribute_minutes(self, meeting: Meeting, db: AsyncSession):
        """Approve minutes, generate PDF, index to KB, and send emails."""
        from app.services.pdf_service import pdf_service
        from app.services.email_service import email_service
        from app.core.knowledge_base import get_knowledge_base

        # 1. Update Status
        if meeting.minutes:
            await db.refresh(meeting.minutes)
            meeting.minutes.status = MinutesStatus.APPROVED
            if not meeting.minutes.meeting_id:
                meeting.minutes.meeting_id = meeting.id
            await db.flush()
            logger.info("Minutes status updated to APPROVED")

        # 2. Generate PDF
        pdf_bytes = None
        try:
            pillar_display = "General"
            if meeting.twg:
                pillar_display = (
                    meeting.twg.pillar.value.replace("_", " ").title()
                    if hasattr(meeting.twg.pillar, 'value')
                    else str(meeting.twg.pillar)
                )

            pdf_context = {
                "pillar_name": pillar_display,
                "meeting_title": meeting.title,
                "meeting_date": meeting.scheduled_at.strftime('%Y-%m-%d') if meeting.scheduled_at else "TBD",
                "meeting_time": meeting.scheduled_at.strftime('%H:%M') if meeting.scheduled_at else "",
                "location": meeting.location or "Virtual",
            }

            if meeting.minutes and meeting.minutes.content:
                pdf_bytes = pdf_service.generate_minutes_pdf(
                    minutes_markdown=meeting.minutes.content,
                    template_context=pdf_context,
                )
                logger.info("Minutes PDF generated successfully")
        except Exception as e:
            logger.error(f"PDF Generation Failed: {e}")

        # 2b. Save PDF to cloud storage (primary) with local fallback
        if pdf_bytes:
            try:
                from app.models.models import TWG
                from app.services.storage_service import get_storage_service

                pdf_filename = f"Minutes - {meeting.title}.pdf"

                existing = await db.execute(
                    select(Document).where(
                        and_(Document.meeting_id == meeting.id, Document.document_type == "minutes")
                    )
                )
                if existing.scalar_one_or_none():
                    logger.info(f"Minutes Document already exists for '{meeting.title}', skipping")
                else:
                    res_u = await db.execute(select(User.id).limit(1))
                    uploader_id = res_u.scalars().first()
                    if not uploader_id:
                        logger.warning("No user found to set as uploader for minutes document")
                    else:
                        file_path = None
                        metadata_extra = {}

                        # Cloud storage (primary)
                        try:
                            storage = get_storage_service()
                            twg_result = await db.execute(select(TWG).where(TWG.id == meeting.twg_id))
                            twg_obj = twg_result.scalar_one_or_none()
                            target_folder_id = None
                            if twg_obj:
                                target_folder_id = storage.get_or_create_twg_folder(twg_obj.name)

                            timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
                            safe_filename = f"{timestamp}_minutes_{meeting.id}.pdf"
                            cloud_file_id, cloud_view_link, cloud_download_url = storage.upload_bytes(
                                file_bytes=pdf_bytes,
                                file_name=safe_filename,
                                mime_type="application/pdf",
                                folder_id=target_folder_id,
                            )
                            if cloud_file_id:
                                file_path = cloud_file_id
                                metadata_extra = {
                                    "storage_mode": "cloud",
                                    "cloud_file_id": cloud_file_id,
                                    "cloud_view_link": cloud_view_link,
                                    "cloud_download_url": cloud_download_url,
                                }
                                logger.info(f"Uploaded minutes PDF to cloud storage: {cloud_file_id}")
                        except Exception as cloud_err:
                            logger.warning(f"Cloud storage upload failed, falling back to local: {cloud_err}")

                        # Local fallback
                        if not file_path:
                            upload_dir = os.path.join(settings.UPLOAD_DIR, "minutes")
                            os.makedirs(upload_dir, exist_ok=True)
                            local_path = os.path.join(upload_dir, f"minutes_{meeting.id}.pdf")
                            with open(local_path, "wb") as f:
                                f.write(pdf_bytes)
                            file_path = local_path
                            metadata_extra = {"storage_mode": "local"}
                            logger.info(f"Saved minutes PDF to local disk: {local_path}")

                        minutes_doc = Document(
                            twg_id=meeting.twg_id,
                            meeting_id=meeting.id,
                            file_name=pdf_filename,
                            file_path=file_path,
                            file_type="application/pdf",
                            document_type="minutes",
                            uploaded_by_id=uploader_id,
                            metadata_json={
                                "meeting_id": str(meeting.id),
                                "meeting_title": meeting.title,
                                "status": "approved",
                                "file_size": len(pdf_bytes),
                                **metadata_extra,
                            },
                        )
                        db.add(minutes_doc)
                        await db.commit()
                        logger.info(f"Minutes Document record created for '{meeting.title}'")
            except Exception as e:
                logger.error(f"Minutes Document creation failed: {e}")
                import traceback
                logger.error(traceback.format_exc())

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
                        "file_name": f"Minutes - {meeting.title}",
                    },
                    namespace=f"twg-{meeting.twg.id}" if meeting.twg_id else "global",
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
                    pillar_display = (
                        meeting.twg.pillar.value.replace("_", " ").title()
                        if hasattr(meeting.twg.pillar, 'value')
                        else str(meeting.twg.pillar)
                    )

                email_context = {
                    "recipient_name": "Colleague",
                    "meeting_title": meeting.title,
                    "date_str": meeting.scheduled_at.strftime('%Y-%m-%d') if meeting.scheduled_at else "TBD",
                    "pillar_name": pillar_display,
                    "dashboard_url": f"{settings.FRONTEND_URL}/meetings/{meeting.id}",
                }

                logger.info(f"Sending Minutes PDF to {len(recipient_list)} recipients...")
                await email_service.send_minutes_published_email(
                    to_emails=recipient_list,
                    template_context=email_context,
                    pdf_content=pdf_bytes,
                    pdf_filename=f"Minutes - {meeting.title}.pdf",
                )
                logger.info("Minutes emails sent successfully")
            except Exception as e:
                logger.error(f"Email Sending Failed: {e}")

    # ── Webhook handler ───────────────────────────────────────────────

    async def process_webhook(self, payload: Dict[str, Any]):
        """
        Process incoming webhook from Attendee.
        Events: transcript.update, bot.state_change
        Uses meeting.attendee_bot_id for direct DB lookup (no fuzzy title matching).
        """
        try:
            event = payload.get("event", "")
            bot_id = payload.get("bot_id") or payload.get("data", {}).get("bot_id")
            logger.info(f"Processing Attendee webhook — event={event}, bot_id={bot_id}")

            if not bot_id:
                logger.warning(f"Webhook payload missing bot_id: {payload.keys()}")
                return

            from app.core.database import get_db_session_context

            async with get_db_session_context() as db:
                # Direct lookup by bot_id — no fuzzy matching needed
                stmt = (
                    select(Meeting)
                    .options(
                        selectinload(Meeting.twg),
                        selectinload(Meeting.minutes),
                        selectinload(Meeting.participants).selectinload(MeetingParticipant.user),
                    )
                    .where(Meeting.attendee_bot_id == bot_id)
                )
                result = await db.execute(stmt)
                meeting = result.scalar_one_or_none()

                if not meeting:
                    logger.warning(f"No meeting found with attendee_bot_id={bot_id}")
                    return

                if event == "transcript.update":
                    await self._handle_transcript_update(meeting, bot_id, db)
                elif event == "bot.state_change":
                    new_state = payload.get("data", {}).get("state", "")
                    logger.info(f"Bot {bot_id} state changed to: {new_state}")
                    if new_state in ("ended", "post_processing", "done", "completed"):
                        # Bot finished — fetch transcript immediately
                        logger.info(f"Bot ended for '{meeting.title}', fetching transcript now...")
                        await self._handle_transcript_update(meeting, bot_id, db)
                    elif new_state == "fatal_error":
                        logger.error(f"Bot {bot_id} encountered fatal error for meeting '{meeting.title}'")
                else:
                    logger.debug(f"Ignoring unhandled webhook event: {event}")

        except Exception as e:
            logger.error(f"Error processing Attendee webhook: {e}")
            import traceback
            logger.error(traceback.format_exc())

    async def _handle_transcript_update(self, meeting: Meeting, bot_id: str, db: AsyncSession):
        """Handle a transcript.update webhook — fetch, process, finalize."""
        # Skip if meeting already has a transcript
        if meeting.transcript and len(meeting.transcript) > 100:
            logger.info(f"Meeting '{meeting.title}' already has transcript, skipping webhook")
            return

        # Fetch transcript from Attendee API
        transcript_data = await self.get_transcript(bot_id)
        if not transcript_data:
            logger.warning(f"Could not fetch transcript for bot_id={bot_id}")
            return

        transcript_text = self.format_transcript_text(transcript_data)
        if not transcript_text:
            logger.warning(f"Formatted transcript is empty for bot_id={bot_id}")
            return

        logger.info(f"Processing transcript for '{meeting.title}' ({len(transcript_text)} chars)")

        # Process transcript → generate minutes
        file_path = await self.process_transcript_text(meeting, transcript_text, db)

        if file_path and isinstance(file_path, str):
            meeting.status = MeetingStatus.COMPLETED

            # Create Document record for transcript
            res_u = await db.execute(select(User.id).limit(1))
            uploader_id = res_u.scalars().first()
            if uploader_id:
                doc = Document(
                    twg_id=meeting.twg_id,
                    meeting_id=meeting.id,
                    file_name=f"Attendee Transcript - {meeting.title}.txt",
                    file_path=file_path,
                    file_type="text/plain",
                    document_type="transcript",
                    uploaded_by_id=uploader_id,
                    metadata_json={
                        "provider": "attendee",
                        "bot_id": bot_id,
                        "meeting_id": str(meeting.id),
                    },
                )
                db.add(doc)

            await db.commit()
            logger.info("Webhook processing complete — transcript saved, minutes drafted.")

            # Auto-approve and distribute
            try:
                logger.info(f"Auto-approving and distributing minutes for '{meeting.title}'...")
                await self.finalize_and_distribute_minutes(meeting, db)
                await db.commit()
                logger.info(f"Minutes auto-approved and distributed for '{meeting.title}'")
            except Exception as approve_err:
                logger.error(f"Auto-approval/distribution failed: {approve_err}")
                import traceback
                logger.error(traceback.format_exc())

            # Broadcast real-time update
            try:
                from app.services.broadcast_service import get_broadcast_service
                broadcast = get_broadcast_service()
                await broadcast.notify_meeting_update(meeting.id, {
                    "status": "COMPLETED",
                    "has_transcript": True,
                    "has_minutes": True,
                    "minutes_approved": True,
                    "title": meeting.title,
                })
            except Exception as broadcast_err:
                logger.error(f"Broadcast after webhook failed: {broadcast_err}")

    # ── Live meeting features (carried over from VexaService) ─────────

    async def analyze_live_chunk(self, meeting_id: str, chunk_text: str, db: AsyncSession):
        """
        Analyze a live transcript chunk for "Hey Martin" command triggers.
        """
        try:
            logger.info(f"Analyzing live chunk for meeting {meeting_id}...")
            command_pattern = r"(?i)(hey martin|secretariat bot),?\s*(.*)"
            match = re.search(command_pattern, chunk_text)
            if match:
                question = match.group(2).strip()
                logger.info(f"Detected live command/question: {question}")
                await self._handle_live_command(meeting_id, question, db)
        except Exception as e:
            logger.error(f"Failed to analyze live chunk for meeting {meeting_id}: {e}")

    async def _handle_live_command(self, meeting_id: str, question: str, db: AsyncSession):
        """Process a 'Hey Martin' question during a live meeting."""
        try:
            from app.services.broadcast_service import get_broadcast_service

            llm = get_llm_service()
            broadcast = get_broadcast_service()

            context_prompt = (
                f"The following question was asked during a live ECOWAS meeting. "
                f"Provide a concise, factual answer based on the knowledge base:\n\n"
                f"Question: {question}"
            )
            answer = await asyncio.to_thread(llm.chat, context_prompt)
            logger.info(f"Martin real-time response: {answer}")

            if hasattr(broadcast, "notify_live_meeting"):
                await broadcast.notify_live_meeting(
                    meeting_id=meeting_id,
                    content=answer,
                    source="live_command",
                    original_question=question,
                )
        except Exception as e:
            logger.error(f"Error handling live command: {e}")


# Singleton instance
attendee_service = AttendeeService()
