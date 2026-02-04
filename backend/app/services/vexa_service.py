import re
import aiohttp
import asyncio
import json
import logging
from typing import Optional, Dict, Any, List
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.models import Meeting, Minutes, MinutesStatus, ActionItem, ActionItemStatus, MeetingStatus, Agenda
from app.services.document_synthesizer import DocumentSynthesizer
from app.services.llm_service import get_llm_service
from datetime import datetime
import os
import uuid
import aiofiles

logger = logging.getLogger(__name__)

class VexaService:
    """
    Client service for Vexa Meeting Bot.
    """
    
    def __init__(self):
        self.api_url = settings.VEXA_API_URL
        self.api_key = settings.VEXA_API_KEY
        self.time_cache = {} # Cache for stable segment timestamps
        self.headers = {
            "X-API-Key": self.api_key,
            "Authorization": f"Bearer {self.api_key}", 
            "Content-Type": "application/json"
        }

    async def join_meeting(self, meeting_url: str, meeting_id: str, bot_name: str = "Secretariat Bot") -> Optional[Dict[str, str]]:
        """
        Dispatch a bot to join a meeting.
        Returns dict with session_id, platform, and native_meeting_id if successful.
        """
        url = f"{self.api_url}/bots"
        
        # Parse meeting URL to determine platform and extract meeting ID
        if "meet.google.com" in meeting_url:
            platform = "google_meet"
            # Extract meeting code from URL (e.g., abc-defg-hij)
            native_meeting_id = meeting_url.split("/")[-1].split("?")[0]
        elif "teams.microsoft.com" in meeting_url or "teams.live.com" in meeting_url:
            platform = "teams"
            # For Teams, extract numeric ID from URL
            # Format: https://teams.live.com/meet/9366473044740?p=xxx
            native_meeting_id = meeting_url.split("/meet/")[-1].split("?")[0]
        else:
            logger.warning(f"Unsupported meeting platform: {meeting_url}")
            return None
            
        payload = {
            "platform": platform,
            "native_meeting_id": native_meeting_id,
            "bot_name": bot_name,
            "metadata": {
                "meeting_id": meeting_id
            }
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=self.headers) as response:
                    if response.status in [200, 201]:
                        data = await response.json()
                        session_id = data.get('sessionId') or data.get('id')
                        logger.info(f"✓ Vexa Bot dispatched to {meeting_url}. Session ID: {session_id}")
                        logger.debug(f"Full Vexa response: {json.dumps(data, indent=2)}")
                        # Return all the info needed to fetch transcript later
                        return {
                            "session_id": session_id,
                            "platform": platform,
                            "native_meeting_id": native_meeting_id
                        }
                    else:
                        text = await response.text()
                        logger.error(f"✗ Failed to dispatch Vexa bot: HTTP {response.status}")
                        logger.error(f"Response body: {text}")
                        logger.error(f"Request payload: {json.dumps(payload, indent=2)}")
                        return None
        except Exception as e:
            logger.error(f"✗ Error connecting to Vexa API: {e}")
            logger.error(f"API URL: {url}")
            logger.error(f"Request payload: {json.dumps(payload, indent=2)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None

    async def get_transcript(self, platform: str, native_meeting_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch transcript using platform and native meeting ID.
        Returns dict with transcript text and status if ready, None if not ready or error.
        """
        transcript_url = f"{self.api_url}/transcripts/{platform}/{native_meeting_id}"
        logger.debug(f"Fetching transcript from Vexa API: {transcript_url}")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(transcript_url, headers=self.headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        
                        # Extract meeting status
                        status = data.get('status', 'unknown')
                        end_time = data.get('end_time')
                        is_completed = end_time is not None or status in ['completed', 'finished', 'ended']
                        
                        # Try to extract transcript text from various possible formats
                        transcript_text = None
                        
                        # Format 1: Direct text field
                        if 'text' in data and data['text']:
                            transcript_text = data['text']
                        # Format 2: Transcript field
                        elif 'transcript' in data and data['transcript']:
                            transcript_text = data['transcript']
                        # Format 3: Segments array (Vexa's actual format)
                        elif 'segments' in data and isinstance(data['segments'], list):
                            segments = data['segments']
                            if segments:
                                # Extract text from each segment with speaker identification
                                segment_texts = []
                                current_speaker = None
                                
                                for i, segment in enumerate(segments):
                                    if isinstance(segment, dict):
                                        text = segment.get('text', '').strip()
                                        if not text:
                                            continue
                                        
                                        # Extract speaker information
                                        speaker = (
                                            segment.get('speaker_name') or 
                                            segment.get('name') or 
                                            segment.get('speaker') or 
                                            segment.get('speaker_id') or
                                            "Unknown Speaker"
                                        )
                                        
                                        # Stability Key: use segment ID or platform/id/index
                                        segment_key = segment.get('id') or f"{platform}_{native_meeting_id}_{i}"
                                        
                                        if segment_key in self.time_cache:
                                            time_label = self.time_cache[segment_key]
                                        else:
                                            # Generate stable timestamp once
                                            time_label = datetime.now().strftime("%I:%M %p")
                                            
                                            seg_time = segment.get('time') or segment.get('timestamp') or segment.get('startTime')
                                            if seg_time:
                                                try:
                                                    if isinstance(seg_time, str):
                                                        time_label = datetime.fromisoformat(seg_time.replace('Z', '+00:00')).strftime("%I:%M %p")
                                                    elif isinstance(seg_time, (int, float)) and seg_time > 1000000000:
                                                        time_label = datetime.fromtimestamp(seg_time).strftime("%I:%M %p")
                                                except: pass
                                            
                                            self.time_cache[segment_key] = time_label
                                        
                                        formatted_block = f"{time_label}\n{speaker}:\n{text}"
                                        segment_texts.append(formatted_block)
                                    elif isinstance(segment, str):
                                        segment_texts.append(segment)
                                
                                if segment_texts:
                                    transcript_text = "\n".join(segment_texts)
                                else:
                                    # Empty segments array - no speech recorded
                                    logger.info(f"Vexa returned empty segments array for {platform}/{native_meeting_id}")
                                    return None
                            else:
                                # Empty segments array
                                logger.info(f"Vexa returned empty segments array for {platform}/{native_meeting_id}")
                                return None
                        
                        # If we still don't have text, the meeting might not have any content
                        if not transcript_text or not transcript_text.strip():
                            logger.info(f"No transcript content available for {platform}/{native_meeting_id}")
                            return None
                        
                        logger.info(f"✓ Vexa transcript retrieved for {platform}/{native_meeting_id} ({len(transcript_text)} chars, status: {status}, completed: {is_completed})")
                        
                        return {
                            "text": transcript_text,
                            "status": status,
                            "is_completed": is_completed,
                            "end_time": end_time
                        }
                    elif resp.status == 404:
                         # Meeting not found or transcript not ready yet
                         logger.debug(f"Transcript not ready yet for {platform}/{native_meeting_id} (404)")
                         return None
                    else:
                        error_text = await resp.text()
                        logger.warning(f"✗ Vexa transcript fetch failed for {platform}/{native_meeting_id}: HTTP {resp.status} - {error_text[:100]}")
                        return None
        except Exception as e:
            logger.error(f"✗ Error fetching transcript {platform}/{native_meeting_id}: {e}")
            return None

    async def analyze_live_chunk(self, meeting_id: str, chunk_text: str, db: AsyncSession):
        """
        Analyze a live transcript chunk for:
        1. "Hey Martin" / "Secretariat Bot" command triggers
        2. Real-time conflict detection against KB
        """
        try:
            logger.info(f"Analyzing live chunk for meeting {meeting_id}...")
            
            # 1. Command Detection (regex)
            # Pattern: Hey Martin, [question/command]
            command_pattern = r"(?i)(hey martin|secretariat bot),?\s*(.*)"
            match = re.search(command_pattern, chunk_text)
            
            if match:
                question = match.group(2).strip()
                logger.info(f"✓ Detected live command/question: {question}")
                await self._handle_live_command(meeting_id, question, db)
            
                    # 2. Live Analysis (Conflict & Agenda)
                    # try:
                    #     from app.services.conflict_detector import ConflictDetector
                    #     detector = ConflictDetector(llm_client=get_llm_service())
                    #     
                    #     # Fetch meeting with TWG and Agenda
                    #     stmt_m = select(Meeting).where(Meeting.id == meeting_id).options(
                    #         selectinload(Meeting.twg),
                    #         selectinload(Meeting.agenda)
                    #     )
                    #     res_m = await db.execute(stmt_m)
                    #     meeting = res_m.scalar_one_or_none()
                    #     
                    #     if meeting:
                    #         twg_name = meeting.twg.name if meeting.twg else "General"
                    #         context = {
                    #             "twg_name": twg_name,
                    #             "meeting_title": meeting.title
                    #         }
                    #         
                    #         from app.services.broadcast_service import get_broadcast_service
                    #         broadcast = get_broadcast_service()
                    #         
                    #         # 2a. Live Conflict Detection
                    #         live_conflict = await detector.detect_live_conflict(chunk_text, context)
                    #         if live_conflict:
                    #             logger.warning(f"⚠️ LIVE CONFLICT DETECTED: {live_conflict['reason']}")
                    #             await broadcast.notify_live_meeting(
                    #                 meeting_id=meeting_id,
                    #                 content=f"**POTENTIAL CONFLICT:** {live_conflict['reason']}\n\n*Suggestion:* {live_conflict['suggestion']}",
                    #                 source="live_conflict_detector"
                    #             )
                    #         
                    #         # 2b. Proactive Agenda Monitoring
                    #         if meeting.agenda:
                    #             logger.info(f"Running proactive agenda analysis for {meeting.title}...")
                    #             agenda_insight = await detector.analyze_live_agenda(
                    #                 chunk_text=chunk_text,
                    #                 agenda_content=meeting.agenda.content,
                    #                 context=context
                    #             )
                    #             
                    #             if agenda_insight and (agenda_insight.get('decisions') or agenda_insight.get('current_focus')):
                    #                 logger.info(f"✓ New Agenda Insight: {agenda_insight.get('insight_summary')}")
                    #                 # Send the whole payload for the specialized frontend component
                    #                 await broadcast.notify_live_meeting(
                    #                     meeting_id=meeting_id,
                    #                     content=agenda_insight.get('insight_summary') or "Progress update",
                    #                     source="agenda_monitor",
                    #                     # Extra data for the frontend
                    #                     metadata=agenda_insight
                    #                 )
                    # 
                    # except Exception as ce:
                    #     logger.error(f"Error in live analysis: {ce}")
                    #     import traceback
                    #     logger.error(traceback.format_exc())

        except Exception as e:
            logger.error(f"Failed to analyze live chunk for meeting {meeting_id}: {e}")

    async def _handle_live_command(self, meeting_id: str, question: str, db: AsyncSession):
        """
        Process a "Hey Martin" question during a live meeting.
        """
        try:
            from app.services.project_insights_service import ProjectInsightsService
            from app.services.broadcast_service import get_broadcast_service
            
            llm = get_llm_service()
            broadcast = get_broadcast_service()
            
            # 1. RAG Answer
            context_prompt = f"The following question was asked during a live ECOWAS meeting. Provide a concise, factual answer based on the knowledge base: \n\nQuestion: {question}"
            answer = await asyncio.to_thread(llm.chat, context_prompt)
            
            logger.info(f"Martin real-time response: {answer}")
            
            # 2. Notify the Live Dashboard
            # In a production environment, this would be a WebSocket push.
            # For now, we use the BroadcastService to send a "live_insight" notification.
            if hasattr(broadcast, "notify_live_meeting"):
                await broadcast.notify_live_meeting(
                    meeting_id=meeting_id,
                    content=answer,
                    source="live_command",
                    original_question=question
                )
            
        except Exception as e:
            logger.error(f"Error handling live command: {e}")

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
                 "attendees_list": "See transcript (Vexa)"
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
             logger.info(f"Generated Minutes for {meeting.title} from Vexa")

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
                     
                     # Check for duplications? Simple check based on description + meeting
                     # For now, just insert.
                     
                     # Parse Due Date
                     due_date = None
                     if action.get("due_date"):
                         try:
                             from datetime import datetime
                             due_date = datetime.strptime(action["due_date"], "%Y-%m-%d").date()
                         except:
                             pass
                     
                     # DISABLED: ActionItem creation requires owner_id (UUID) and twg_id (UUID)
                     # The AI extraction returns owner names as strings, not UUIDs
                     # TODO: Implement user lookup by name or assign to meeting creator
                     logger.debug(f"Skipping action item auto-creation: '{desc[:50]}...' (owner: {action.get('owner', 'TBD')})")
                     
                     # new_action = ActionItem(
                     #     twg_id=meeting.twg.id,  # Required UUID
                     #     meeting_id=meeting.id,
                     #     description=desc,
                     #     owner_id=???  # Need to resolve owner name to user UUID
                     #     due_date=due_date,
                     #     status=ActionItemStatus.PENDING,
                     # )
                     # db.add(new_action)
                     # action_count += 1
                 
                 
                 if action_count > 0:
                     logger.info(f"✓ Automatically extracted {action_count} action items from Vexa minutes.")
             except Exception as ae:
                 logger.error(f"Failed to auto-extract action items: {ae}")
                 import traceback
                 logger.error(f"Traceback: {traceback.format_exc()}")
             
             # --- AUTOMATED APPROVAL & DISTRIBUTION ---
             try:
                 logger.info(f"Automatically approving and distributing minutes for {meeting.title}...")
                 await self.finalize_and_distribute_minutes(meeting, db)
             except Exception as dist_e:
                 logger.error(f"Failed to auto-distribute minutes: {dist_e}")
                 import traceback
                 logger.error(f"Traceback: {traceback.format_exc()}")
             # -----------------------------------------

             return file_path # Return path for the Monitor to update Document
        except Exception as e:
            logger.error(f"Failed to process transcript for {meeting.title}: {e}")
            return False

    async def finalize_and_distribute_minutes(self, meeting: Meeting, db: AsyncSession):
        """
        updates minutes status to APPROVED, generates PDF, indexes to KB, and sends emails.
        """
        from app.services.pdf_service import pdf_service
        from app.services.email_service import email_service
        from app.core.knowledge_base import get_knowledge_base
        from app.models.models import MinutesStatus
        from app.core.config import settings
        
        # 1. Update Status
        if meeting.minutes:
            meeting.minutes.status = MinutesStatus.APPROVED
            await db.commit()
            await db.refresh(meeting.minutes)
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
        # Eager load participants if not loaded
        if not meeting.participants:
            # forceful reload if empty/unloaded
            # This relies on the session being active
            pass

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

vexa_service = VexaService()

