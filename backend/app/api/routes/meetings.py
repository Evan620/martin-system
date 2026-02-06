from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Request, WebSocket, WebSocketDisconnect, Query
from app.services.audit_service import audit_service
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text, and_, or_
from typing import List, Optional
import uuid
from datetime import datetime, timedelta, timezone
import asyncio
import json
import redis
import logging
import traceback

from app.core.database import get_db
from app.models.models import Meeting, Agenda, Minutes, User, UserRole, MinutesStatus, MeetingParticipant, RsvpStatus, ActionItem, ActionItemStatus, TWG, Document, MeetingStatus, MeetingDependency, DependencyType
from app.schemas.schemas import (
    MeetingCreate, MeetingRead, MeetingUpdate, MeetingCancel, MeetingUpdateNotification,
    AgendaCreate, AgendaRead, MinutesCreate, MinutesRead, MinutesUpdate, MinutesRejectionRequest,
    MinutesVersionRead, MinutesUpdateWithVersion,
    ActionItemCreate, ActionItemRead, MeetingParticipantCreate, MeetingParticipantRead,
    MeetingParticipantUpdate, MeetingDependencyRead,
    DependencyType as DependencyTypeSchema
)
from app.api.deps import get_current_active_user, require_facilitator, require_twg_access, has_twg_access
from app.services.email_service import email_service
from app.core.config import settings
from sqlalchemy.orm import selectinload
from app.services.document_synthesizer import DocumentSynthesizer
from app.services.llm_service import llm_service
from app.utils.security import verify_token
from app.core.ws_manager import ws_manager
from app.services.vexa_service import VexaService
from app.core.database import get_db, get_db_session_context

router = APIRouter(prefix="/meetings", tags=["Meetings"])

@router.get("/active")
async def get_active_meeting(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Returns the currently active meeting (status=IN_PROGRESS) for the user's TWGs.
    """
    # Find a meeting that is currently happening (In Progress)
    # Using status if existing, or just based on time
    stmt = select(Meeting).where(
        and_(
            Meeting.status == MeetingStatus.IN_PROGRESS,
            # Or simplified for now: starts within last 2 hours and hasn't ended
        )
    ).order_by(Meeting.scheduled_at.desc()).limit(1)
    
    # Actually, let's look for meetings that have a transcript placeholder active
    # as that's what Vexa is recording.
    stmt = select(Meeting).join(Document, Meeting.id == Document.meeting_id).where(
        Document.document_type == "transcript_placeholder"
    ).options(
        selectinload(Meeting.participants).selectinload(MeetingParticipant.user),
        selectinload(Meeting.agenda),
        selectinload(Meeting.minutes),
        selectinload(Meeting.twg),
        selectinload(Meeting.documents).selectinload(Document.uploaded_by),
        selectinload(Meeting.successors).selectinload(MeetingDependency.target_meeting),
        selectinload(Meeting.predecessors).selectinload(MeetingDependency.source_meeting)
    ).order_by(Meeting.scheduled_at.desc()).limit(1)
    
    result = await db.execute(stmt)
    meeting = result.scalar_one_or_none()
    
    if not meeting:
        # Fallback: find any meeting scheduled for now
        now = datetime.utcnow()
        stmt = select(Meeting).where(
            and_(
                Meeting.scheduled_at <= now,
                Meeting.scheduled_at >= now - timedelta(hours=2),
                Meeting.status != 'cancelled'
            )
        ).options(
            selectinload(Meeting.participants).selectinload(MeetingParticipant.user),
            selectinload(Meeting.agenda),
            selectinload(Meeting.minutes),
            selectinload(Meeting.twg),
            selectinload(Meeting.documents).selectinload(Document.uploaded_by),
            selectinload(Meeting.successors).selectinload(MeetingDependency.target_meeting),
            selectinload(Meeting.predecessors).selectinload(MeetingDependency.source_meeting)
        ).order_by(Meeting.scheduled_at.desc()).limit(1)
        result = await db.execute(stmt)
        meeting = result.scalar_one_or_none()

    if not meeting:
        raise HTTPException(status_code=404, detail="No active meeting found")
    
    # Map titles for UI
    if meeting:
        for s in meeting.successors:
            s.target_meeting_title = s.target_meeting.title
        for p in meeting.predecessors:
            p.source_meeting_title = p.source_meeting.title
            
    return meeting

@router.post("/", response_model=MeetingRead, status_code=status.HTTP_201_CREATED)
async def create_meeting(
    meeting_in: MeetingCreate,
    current_user: User = Depends(require_facilitator),
    db: AsyncSession = Depends(get_db)
):
    """
    Schedule a new meeting.
    
    Requires FACILITATOR or ADMIN role.
    User must have access to the TWG.
    """
    import traceback
    from datetime import timezone

    try:
        # Check if facilitator has access to this TWG
        if not has_twg_access(current_user, meeting_in.twg_id):
            raise HTTPException(status_code=403, detail="You do not have access to manage meetings for this TWG")

        # Ensure scheduled_at is naive UTC
        if meeting_in.scheduled_at and meeting_in.scheduled_at.tzinfo:
             meeting_in.scheduled_at = meeting_in.scheduled_at.astimezone(timezone.utc).replace(tzinfo=None)

        # GENERATE GOOGLE MEET LINK
        # Only if configured and virtual
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"CREATE_MEETING: meeting_type='{meeting_in.meeting_type}'")
        
        # Generate ID explicitly so we can link it in GCal
        meeting_id = uuid.uuid4()
        
        generated_video_link = None
        if meeting_in.meeting_type == "virtual":
            logger.warning("CREATE_MEETING: Entering virtual meeting block")
            try:
                from app.services.calendar_service import calendar_service
                calendar_event = calendar_service.create_meeting_event(
                    title=meeting_in.title,
                    start_time=meeting_in.scheduled_at,
                    duration_minutes=meeting_in.duration_minutes,
                    description=f"Automated meeting for TWG: {meeting_in.twg_id}",
                    attendees=[],
                    meeting_id=str(meeting_id)
                )
                if calendar_event.get('hangoutLink'):
                     logger.warning(f"CREATE_MEETING: Generated link: {calendar_event.get('hangoutLink')}")
                     generated_video_link = calendar_event.get('hangoutLink')
                else:
                     logger.warning(f"CREATE_MEETING: Event created but NO link found")
            except Exception as e:
                # Log detailed error but DO NOT fail the meeting creation
                logger.error(f"CREATE_MEETING: Failed to generate Meet link: {e}")
                # If it's an HttpError, it might be the 'Invalid conference type value'
                # causing issues with service accounts. We proceed without video link.

        # Create meeting with video_link
        meeting_data = meeting_in.model_dump()
        meeting_data['id'] = meeting_id
        meeting_data['video_link'] = generated_video_link
        db_meeting = Meeting(**meeting_data)
        db.add(db_meeting)
        await db.commit()
        
        # Eagerly load relationships to avoid MissingGreenlet during serialization
        result = await db.execute(
            select(Meeting)
            .options(
                selectinload(Meeting.participants).selectinload(MeetingParticipant.user),
                selectinload(Meeting.twg),
                selectinload(Meeting.agenda),
                selectinload(Meeting.minutes),
                selectinload(Meeting.documents).selectinload(Document.uploaded_by),
                selectinload(Meeting.successors).selectinload(MeetingDependency.target_meeting),
                selectinload(Meeting.predecessors).selectinload(MeetingDependency.source_meeting)
            )
            .where(Meeting.id == db_meeting.id)
        )
        db_meeting = result.scalar_one()
            
        return db_meeting
    except Exception as e:
        logger.error(f"CREATE_MEETING FAILED: {str(e)}") # Improved logging
        import traceback
        traceback.print_exc()
        raise e

@router.get("/", response_model=List[MeetingRead])
async def list_meetings(
    skip: int = 0,
    limit: int = 100,
    twg_id: Optional[uuid.UUID] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List all meetings visible to the user.
    """
    # If admin, show all (unless filtered). If member, show only their TWG meetings.
    query = select(Meeting).offset(skip).limit(limit)
    
    if twg_id:
        if not has_twg_access(current_user, twg_id):
             raise HTTPException(status_code=403, detail="Access denied to this TWG")
        query = query.where(Meeting.twg_id == twg_id)
    elif current_user.role not in [UserRole.ADMIN, UserRole.SECRETARIAT_LEAD]:
        # Get IDs of TWGs user belongs to
        user_twg_ids = [twg.id for twg in current_user.twgs]
        query = query.where(Meeting.twg_id.in_(user_twg_ids))
        
    query = query.options(
        selectinload(Meeting.participants).selectinload(MeetingParticipant.user), # Fix for 500 error
        selectinload(Meeting.twg),
        selectinload(Meeting.documents).selectinload(Document.uploaded_by),
        selectinload(Meeting.documents).selectinload(Document.twg),
        selectinload(Meeting.successors),
        selectinload(Meeting.predecessors)
    )
        
    
    result = await db.execute(query)
    meetings_list = result.scalars().all()
    
    return meetings_list

@router.get("/{meeting_id}", response_model=MeetingRead)
async def get_meeting(
    meeting_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get meeting details.
    """
    print(f"DEBUG: get_meeting called for {meeting_id}")
    query = select(Meeting).where(Meeting.id == meeting_id).options(
        selectinload(Meeting.participants).selectinload(MeetingParticipant.user),
        selectinload(Meeting.agenda),
        selectinload(Meeting.minutes),
        selectinload(Meeting.twg),
        selectinload(Meeting.documents).selectinload(Document.uploaded_by),
        selectinload(Meeting.successors).selectinload(MeetingDependency.target_meeting),
        selectinload(Meeting.predecessors).selectinload(MeetingDependency.source_meeting)
    )
    result = await db.execute(query)
    db_meeting = result.scalar_one_or_none()
    
    if not db_meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    # Map titles for UI
    for s in db_meeting.successors:
        s.target_meeting_title = s.target_meeting.title
    for p in db_meeting.predecessors:
        p.source_meeting_title = p.source_meeting.title
    
    # Check access
    if not has_twg_access(current_user, db_meeting.twg_id):
        raise HTTPException(status_code=403, detail="Access denied")
        
    return db_meeting

@router.get("/{meeting_id}/agenda")
async def get_meeting_agenda(
    meeting_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    # Verify meeting exists and access rights
    result = await db.execute(select(Meeting).where(Meeting.id == meeting_id))
    db_meeting = result.scalar_one_or_none()
    if not db_meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
        
    if not has_twg_access(current_user, db_meeting.twg_id):
        raise HTTPException(status_code=403, detail="Access denied")

    result = await db.execute(select(Agenda).where(Agenda.meeting_id == meeting_id))
    db_agenda = result.scalar_one_or_none()
    if not db_agenda:
        raise HTTPException(status_code=404, detail="Agenda not found")
    return db_agenda

@router.get("/{meeting_id}/minutes")
async def get_meeting_minutes(
    meeting_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    # Verify meeting exists and access rights
    result = await db.execute(select(Meeting).where(Meeting.id == meeting_id))
    db_meeting = result.scalar_one_or_none()
    if not db_meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
        
    if not has_twg_access(current_user, db_meeting.twg_id):
        raise HTTPException(status_code=403, detail="Access denied")

    result = await db.execute(select(Minutes).where(Minutes.meeting_id == meeting_id))
    db_minutes = result.scalar_one_or_none()
    if not db_minutes:
        raise HTTPException(status_code=404, detail="Minutes not found")
    return db_minutes

@router.patch("/{meeting_id}", response_model=MeetingRead)
async def update_meeting(
    meeting_id: uuid.UUID,
    meeting_in: MeetingUpdate,
    current_user: User = Depends(require_facilitator),
    db: AsyncSession = Depends(get_db)
):
    """
    Update meeting details (e.g., add transcript, change status).
    """
    query = select(Meeting).where(Meeting.id == meeting_id).options(
        selectinload(Meeting.participants).selectinload(MeetingParticipant.user),
        selectinload(Meeting.twg),
        selectinload(Meeting.agenda),
        selectinload(Meeting.minutes),
        selectinload(Meeting.documents).selectinload(Document.uploaded_by),
        selectinload(Meeting.successors).selectinload(MeetingDependency.target_meeting),
        selectinload(Meeting.predecessors).selectinload(MeetingDependency.source_meeting)
    )
    result = await db.execute(query)
    db_meeting = result.scalar_one_or_none()
    
    if not db_meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
        
    if not has_twg_access(current_user, db_meeting.twg_id):
        raise HTTPException(status_code=403, detail="Access denied")
        
    update_data = meeting_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_meeting, key, value)
        
    try:
        await db.commit()
        await db.refresh(db_meeting)
    except Exception as e:
        import traceback
        print(f"DEBUG: Update Meeting Failed: {e}")
        print(traceback.format_exc())
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error during update: {str(e)}")
        
    return db_meeting

@router.post("/{meeting_id}/minutes", response_model=MinutesRead)
async def upsert_minutes(
    meeting_id: uuid.UUID,
    minutes_in: MinutesUpdate, # Allow partial updates or full content
    current_user: User = Depends(require_facilitator),
    db: AsyncSession = Depends(get_db)
):
    """
    Create or Update meeting minutes.
    Automatically creates version snapshots for audit trail.
    """
    from app.models.models import Minutes, MinutesVersion, ActionItem
    from sqlalchemy import select
    
    # Verify meeting
    result = await db.execute(select(Meeting).where(Meeting.id == meeting_id))
    db_meeting = result.scalar_one_or_none()
    if not db_meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
        
    if not has_twg_access(current_user, db_meeting.twg_id):
        raise HTTPException(status_code=403, detail="Access denied")

    # Check for existing minutes
    result = await db.execute(select(Minutes).where(Minutes.meeting_id == meeting_id))
    db_minutes = result.scalar_one_or_none()
    
    if db_minutes:
        # CREATE VERSION SNAPSHOT before updating
        if minutes_in.content and minutes_in.content != db_minutes.content:
            # Snapshot Action Items
            stmt = select(ActionItem).where(ActionItem.meeting_id == meeting_id)
            ai_result = await db.execute(stmt)
            current_actions = ai_result.scalars().all()
            
            actions_snapshot = [
                {
                    "description": item.description,
                    "owner_id": str(item.owner_id) if item.owner_id else None,
                    "due_date": item.due_date.isoformat() if item.due_date else None,
                    "status": item.status.value if item.status else "pending",
                    "priority": item.priority.value if hasattr(item, 'priority') and item.priority else "medium"
                }
                for item in current_actions
            ]
            
            version = MinutesVersion(
                minutes_id=db_minutes.id,
                version_number=db_minutes.current_version,
                content=db_minutes.content,  # Save OLD content
                key_decisions=db_minutes.key_decisions,
                change_summary=getattr(minutes_in, 'change_summary', None),
                action_items_snapshot=actions_snapshot,
                created_by=current_user.id,
                created_at=datetime.utcnow()
            )
            db.add(version)
            
            # Increment version
            db_minutes.current_version += 1
        
        # Update current minutes
        update_data = minutes_in.model_dump(exclude_unset=True)
        # Remove change_summary from minutes update (it's only for version)
        update_data.pop('change_summary', None)
        
        for key, value in update_data.items():
            setattr(db_minutes, key, value)
        
        # Track editor
        db_minutes.last_edited_by = current_user.id
        db_minutes.last_edited_at = datetime.utcnow()
    else:
        # Create new minutes (version 1)
        if not minutes_in.content:
             raise HTTPException(status_code=400, detail="Content required for creating minutes")
        
        minutes_data = minutes_in.model_dump(exclude_unset=True)
        minutes_data.pop('change_summary', None)  # Remove version-only field
        
        db_minutes = Minutes(
            meeting_id=meeting_id, 
            **minutes_data,
            current_version=1,
            last_edited_by=current_user.id,
            last_edited_at=datetime.utcnow()
        )
        db.add(db_minutes)
    
    await db.commit()
    await db.refresh(db_minutes)
    return db_minutes

@router.post("/{meeting_id}/generate-minutes", response_model=MinutesRead)
async def generate_minutes(
    meeting_id: uuid.UUID,
    current_user: User = Depends(require_facilitator),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate 'Zero Draft' minutes from the meeting transcript using AI.
    """
    # 1. Fetch Meeting with all context
    query = select(Meeting).where(Meeting.id == meeting_id).options(
        selectinload(Meeting.participants).selectinload(MeetingParticipant.user),
        selectinload(Meeting.agenda),
        selectinload(Meeting.twg)
    )
    result = await db.execute(query)
    db_meeting = result.scalar_one_or_none()
    
    if not db_meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
        
    if not has_twg_access(current_user, db_meeting.twg_id):
        raise HTTPException(status_code=403, detail="Access denied")

    # 2. Validation & Fallback for Active Vexa Meetings
    if not db_meeting.transcript:
        # Check if we have a Vexa placeholder and can fetch a partial transcript
        from app.services.vexa_service import vexa_service
        
        # Find placeholder doc
        placeholder_doc = None
        for doc in db_meeting.documents:
            if doc.document_type == "transcript_placeholder":
                placeholder_doc = doc
                break
        
        if placeholder_doc and placeholder_doc.metadata_json:
            platform = placeholder_doc.metadata_json.get("platform")
            native_meeting_id = placeholder_doc.metadata_json.get("native_meeting_id")
            
            if platform and native_meeting_id:
                try:
                    print(f"Attempting to fetch partial transcript for {platform}/{native_meeting_id}")
                    transcript_data = await vexa_service.get_transcript(platform, native_meeting_id)
                    
                    if transcript_data and transcript_data.get("text"):
                        # Save the partial transcript to the meeting
                        db_meeting.transcript = transcript_data.get("text")
                        await db.commit()
                        print(f"Fetched and saved partial transcript ({len(db_meeting.transcript)} chars)")
                except Exception as e:
                    print(f"Failed to fetch partial transcript: {e}")

    if not db_meeting.transcript:
        raise HTTPException(status_code=400, detail="No transcript available for this meeting. Please add a transcript first or wait for Vexa processing.")

    # 3. Prepare Context for Synthesizer
    attendees_list = []
    for p in db_meeting.participants:
        name = p.user.full_name if (p.user and p.user.full_name) else (p.name or p.email or "Unknown")
        role = f" ({p.user.role.value})" if (p.user and p.user.role) else ""
        attendees_list.append(f"- {name}{role}")
    
    # Get robust Pillar/TWG Name
    pillar_name = "General"
    if db_meeting.twg:
        if hasattr(db_meeting.twg, 'name') and db_meeting.twg.name:
            pillar_name = db_meeting.twg.name
        elif hasattr(db_meeting.twg, 'pillar'):
             # Handle Enum or string
             val = db_meeting.twg.pillar
             pillar_name = val.value if hasattr(val, 'value') else str(val)

    meeting_context = {
        "meeting_title": db_meeting.title,
        "meeting_date": db_meeting.scheduled_at.strftime("%Y-%m-%d"),
        "pillar_name": pillar_name,
        "attendees_list": "\n".join(attendees_list),
        "agenda_content": db_meeting.agenda.content if db_meeting.agenda else "No formal agenda provided."
    }

    # 4. Generate Minutes
    synthesizer = DocumentSynthesizer(llm_client=llm_service)
    try:
        minutes_result = synthesizer.synthesize_minutes(
            transcript_text=db_meeting.transcript,
            meeting_context=meeting_context
        )
        generated_content = minutes_result["content"]
        
        # 5. Save to DB (Upsert)
        # Check for existing minutes
        min_result = await db.execute(select(Minutes).where(Minutes.meeting_id == meeting_id))
        db_minutes = min_result.scalar_one_or_none()
        
        if db_minutes:
             # CREATE VERSION SNAPSHOT before updating
             # Even for AI regeneration, we should save the previous version
             from app.models.models import MinutesVersion
             
             if db_minutes.content: # Only snapshot if there was content
                 # Snapshot Action Items
                 stmt = select(ActionItem).where(ActionItem.meeting_id == meeting_id)
                 ai_result = await db.execute(stmt)
                 current_actions = ai_result.scalars().all()
                 
                 actions_snapshot = [
                     {
                         "description": item.description,
                         "owner_id": str(item.owner_id) if item.owner_id else None,
                         "due_date": item.due_date.isoformat() if item.due_date else None,
                         "status": item.status.value if item.status else "pending",
                         "priority": item.priority.value if hasattr(item, 'priority') and item.priority else "medium"
                     }
                     for item in current_actions
                 ]
                 
                 version = MinutesVersion(
                    minutes_id=db_minutes.id,
                    version_number=db_minutes.current_version,
                    content=db_minutes.content,
                    key_decisions=db_minutes.key_decisions,
                    change_summary="Auto-archived before AI re-generation",
                    action_items_snapshot=actions_snapshot,
                    created_by=current_user.id,
                    created_at=datetime.utcnow()
                 )
                 db.add(version)
                 db_minutes.current_version += 1
             
             db_minutes.content = generated_content
             db_minutes.status = MinutesStatus.DRAFT
             db_minutes.last_edited_by = current_user.id
             db_minutes.last_edited_at = datetime.utcnow()
        else:
            db_minutes = Minutes(
                meeting_id=meeting_id,
                content=generated_content,
                status=MinutesStatus.DRAFT,
                current_version=1,
                last_edited_by=current_user.id,
                last_edited_at=datetime.utcnow()
            )
            db.add(db_minutes)
            
        # --- NEW: Extract Action Items Automatically ---
        try:
            import asyncio
            # Run extraction (blocking) in thread to avoid blocking loop
            # Or just call sync if we accept blocking (current synthesize_minutes is blocking)
            # Let's use thread for safety as it involves another LLM call
            
            actions_list = await synthesizer.extract_action_items(
                generated_content,
                pillar_name
            )
            
            # Create participant mapping for owner resolution
            user_map = {}
            for p in db_meeting.participants:
                if p.user:
                    if p.user.full_name:
                        user_map[p.user.full_name.lower()] = p.user.id
                        # Also map just first name
                        parts = p.user.full_name.split()
                        if len(parts) > 0:
                            user_map[parts[0].lower()] = p.user.id
            
            action_count = 0
            for action in actions_list:
                desc = action.get("description")
                if not desc: continue
                
                # Parse Due Date
                due_date = None
                if action.get("due_date"):
                    try:
                        due_date = datetime.strptime(action["due_date"], "%Y-%m-%d").date()
                    except:
                        pass
                
                # Resolve Owner
                owner_name = action.get("owner", "").strip()
                owner_id = current_user.id # Default to facilitator
                
                if owner_name:
                    if owner_name.lower() in user_map:
                        owner_id = user_map[owner_name.lower()]
                    else:
                        # Try first name matching
                        parts = owner_name.split()
                        if len(parts) > 0 and parts[0].lower() in user_map:
                            owner_id = user_map[parts[0].lower()]
                
                new_action = ActionItem(
                    meeting_id=meeting_id,
                    twg_id=db_meeting.twg_id,
                    description=desc,
                    owner_id=owner_id,
                    due_date=due_date,
                    status=ActionItemStatus.PENDING
                )
                db.add(new_action)
                action_count += 1
                
            if action_count > 0:
                print(f"✓ Automatically extracted {action_count} action items.")
        except Exception as ae:
            print(f"Failed to auto-extract action items: {ae}")
        # -----------------------------------------------
            
        # Log activity
        await audit_service.log_activity(
            db=db,
            user_id=current_user.id,
            action="MINUTES_GENERATED",
            resource_type="meeting",
            resource_id=meeting_id,
            details={"transcript_length": len(db_meeting.transcript)}
        )
        
        await db.commit()
        await db.refresh(db_minutes)
        return db_minutes

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to generate minutes: {str(e)}")






@router.get("/{meeting_id}/invite-preview")
async def get_invite_preview(
    meeting_id: uuid.UUID,
    current_user: User = Depends(require_facilitator),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a preview of the meeting invitation email and participant list.
    This allows the facilitator to review before approving.
    """
    from app.schemas.schemas import InvitePreview, InviteStatus
    
    query = select(Meeting).where(Meeting.id == meeting_id).options(
        selectinload(Meeting.participants).selectinload(MeetingParticipant.user),
        selectinload(Meeting.twg)
    )
    result = await db.execute(query)
    db_meeting = result.scalar_one_or_none()

    if not db_meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    if not has_twg_access(current_user, db_meeting.twg_id):
        raise HTTPException(status_code=403, detail="Access denied")

    # Collect participant emails
    participant_emails = []
    for participant in db_meeting.participants:
        if participant.user and participant.user.email:
            participant_emails.append(participant.user.email)
        elif participant.email:
            participant_emails.append(participant.email)
    participant_emails = list(set(participant_emails))

    # Render email template for preview
    template_context = {
        "user_name": "Valued Participant",
        "meeting_title": db_meeting.title,
        "meeting_date": db_meeting.scheduled_at.strftime("%Y-%m-%d") if db_meeting.scheduled_at else "TBD",
        "meeting_time": db_meeting.scheduled_at.strftime("%H:%M UTC") if db_meeting.scheduled_at else "TBD",
        "location": db_meeting.location or "Virtual",
        "video_link": db_meeting.video_link,
        "pillar_name": db_meeting.twg.pillar.value if db_meeting.twg else "TWG",
        "portal_url": f"{settings.FRONTEND_URL}/schedule"
    }
    
    # Render the template
    try:
        template = email_service.jinja_env.get_template("meeting_invite.html")
        html_content = template.render(**template_context)
    except Exception as e:
        html_content = f"<p>Template rendering failed: {str(e)}</p>"

    # Determine status
    status = InviteStatus.SENT if db_meeting.status == MeetingStatus.SCHEDULED else InviteStatus.DRAFT

    return InvitePreview(
        meeting_id=meeting_id,
        subject=f"INVITATION: {db_meeting.title}",
        html_content=html_content,
        participants=participant_emails,
        ics_attached=True,
        status=status
    )


@router.post("/{meeting_id}/schedule", status_code=status.HTTP_200_OK)
async def schedule_meeting_draft(
    meeting_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(require_facilitator),
    db: AsyncSession = Depends(get_db)
):
    """
    Mark a meeting as ready to schedule (DRAFT state).
    Does NOT send emails - use /approve-invite after reviewing the preview.
    """
    query = select(Meeting).where(Meeting.id == meeting_id).options(
        selectinload(Meeting.participants),
        selectinload(Meeting.twg)
    )
    result = await db.execute(query)
    db_meeting = result.scalar_one_or_none()

    if not db_meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    if not has_twg_access(current_user, db_meeting.twg_id):
        raise HTTPException(status_code=403, detail="Access denied")

    if not db_meeting.participants:
        raise HTTPException(status_code=400, detail="No participants assigned to this meeting")

    # Don't change status yet - wait for approval
    # Just return the preview info
    participant_count = len(db_meeting.participants)

    # Log activity
    await audit_service.log_activity(
        db=db,
        user_id=current_user.id,
        action="MEETING_DRAFT_CREATED",
        resource_type="meeting",
        resource_id=meeting_id,
        details={"status": "draft_ready", "participant_count": participant_count},
        ip_address=request.client.host if request.client else None
    )

    return {
        "status": "ready_for_approval",
        "message": "Please review the invite preview and click 'Approve & Send' to dispatch invitations.",
        "participant_count": participant_count
    }


@router.post("/{meeting_id}/approve-invite", status_code=status.HTTP_200_OK)
async def approve_and_send_invite(
    meeting_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(require_facilitator),
    db: AsyncSession = Depends(get_db)
):
    """
    HITL Approval Gate: Actually send the meeting invitations after human review.
    This is the final step that dispatches emails to participants.
    """
    query = select(Meeting).where(Meeting.id == meeting_id).options(
        selectinload(Meeting.participants).selectinload(MeetingParticipant.user),
        selectinload(Meeting.twg)
    )
    result = await db.execute(query)
    db_meeting = result.scalar_one_or_none()

    if not db_meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    if not has_twg_access(current_user, db_meeting.twg_id):
        raise HTTPException(status_code=403, detail="Access denied")

    if not db_meeting.participants:
        raise HTTPException(status_code=400, detail="No participants assigned to this meeting")

    # Mark as scheduled
    db_meeting.status = MeetingStatus.SCHEDULED

    # Collect emails
    participant_emails = []
    for participant in db_meeting.participants:
        if participant.user and participant.user.email:
            participant_emails.append(participant.user.email)
        elif participant.email:
            participant_emails.append(participant.email)
    participant_emails = list(set(participant_emails))

    # Fetch Agenda for Meeting Pack
    from app.services.pdf_service import pdf_service
    from app.models.models import Agenda, Document, Minutes
    from sqlalchemy import desc, and_
    
    agenda_query = select(Agenda).where(Agenda.meeting_id == meeting_id)
    agenda_result = await db.execute(agenda_query)
    agenda = agenda_result.scalar_one_or_none()
    
    attachments = []
    
    # 1. Attach Agenda (PDF)
    if agenda and agenda.content:
        try:
            # Safeguard TWG/Pillar
            pillar_val = "TWG"
            if db_meeting.twg and db_meeting.twg.pillar:
                pillar_val = db_meeting.twg.pillar.value
                
            pdf_bytes = pdf_service.generate_agenda_pdf(
                agenda_markdown=agenda.content,
                template_context={
                    "pillar_name": pillar_val,
                    "meeting_title": db_meeting.title,
                    "meeting_date": db_meeting.scheduled_at.strftime("%Y-%m-%d"),
                    "meeting_time": db_meeting.scheduled_at.strftime("%H:%M UTC"),
                    "location": db_meeting.location or "Virtual"
                }
            )
            attachments.append({
                "filename": f"Agenda - {db_meeting.title}.pdf",
                "content": pdf_bytes,
                "content_type": "application/pdf"
            })
            print(f"Generated PDF Agenda size: {len(pdf_bytes)} bytes")
        except Exception as e:
            print(f"Failed to generate PDF Agenda: {e}")

    # 2. Compile Meeting Pack (Previous Minutes & Concept Notes)
    # ---------------------------------------------------------
    try:
        # A. Find Previous Approved Minutes for this TWG
        # Sort by created_at desc, filter by status=FINAL/APPROVED
        from sqlalchemy import or_
        minutes_query = select(Minutes).join(Meeting).where(
            Meeting.twg_id == db_meeting.twg_id,
            Meeting.id != meeting_id, # Not this meeting
            or_(Minutes.status == MinutesStatus.FINAL, Minutes.status == MinutesStatus.APPROVED)
        ).order_by(desc(Minutes.created_at)).limit(1)
        
        minutes_result = await db.execute(minutes_query)
        prev_minutes = minutes_result.scalar_one_or_none()
        
        if prev_minutes and prev_minutes.content:
             # Generate PDF from content
             try:
                 # Need to fetch the meeting title for the previous minutes
                 # Lazy load might trigger error if not eager loaded, but let's try
                 # We joined Meeting in query so it might be attached if we selected it, 
                 # but we selected Minutes.
                 # Let's just use generic title or try to access relationship
                 
                 # Better: fetch meeting details for context
                 prev_meeting_result = await db.execute(select(Meeting).where(Meeting.id == prev_minutes.meeting_id))
                 prev_meeting_obj = prev_meeting_result.scalar_one_or_none()
                 
                 prev_title = prev_meeting_obj.title if prev_meeting_obj else "Previous Meeting"
                 prev_date = prev_meeting_obj.scheduled_at.strftime("%Y-%m-%d") if (prev_meeting_obj and prev_meeting_obj.scheduled_at) else "Date Unknown"
                 
                 minutes_pdf = pdf_service.generate_minutes_pdf(
                    minutes_markdown=prev_minutes.content,
                    template_context={
                        "pillar_name": db_meeting.twg.pillar.value if db_meeting.twg else "TWG",
                        "meeting_title": prev_title,
                        "meeting_date": prev_date,
                        "location": prev_meeting_obj.location if prev_meeting_obj else "Virtual",
                        "attendees": [] # Simplified for now
                    }
                 )
                 
                 attachments.append({
                     "filename": f"Minutes - {prev_title}.pdf",
                     "content": minutes_pdf,
                     "content_type": "application/pdf"
                 })
                 print(f"Attached Previous Minutes PDF")
             except Exception as e:
                 print(f"Failed to generate previous minutes PDF: {e}")

        # B. Find relevant "Zero Draft" or "Concept Note" from last 30 days
        # This is a heuristic for "Pre-read materials"
        from datetime import datetime as dt_cls, timedelta
        thirty_days_ago = dt_cls.utcnow() - timedelta(days=30)  # Naive UTC to match DB
        
        docs_query = select(Document).where(
            Document.twg_id == db_meeting.twg_id,
            Document.created_at >= thirty_days_ago, # Recent
            (Document.file_name.ilike("%concept note%") | Document.file_name.ilike("%zero draft%"))
        ).limit(3)
        
        docs_result = await db.execute(docs_query)
        concept_notes = docs_result.scalars().all()
        
        for doc in concept_notes:
            try:
                import os
                if doc.file_path and os.path.exists(doc.file_path):
                    with open(doc.file_path, "rb") as f:
                        content = f.read()
                    attachments.append({
                        "filename": doc.file_name,
                        "content": content,
                        "content_type": doc.file_type or "application/pdf"
                    })
                    print(f"Attached Concept Note: {doc.file_name}")
            except Exception as e:
                print(f"Failed to attach concept note {doc.file_name}: {e}")
                
    except Exception as e:
        print(f"Error compiling meeting pack: {e}")
        # Don't fail the whole send just for attachments
    
    # ---------------------------------------------------------

    # Send emails
    try:
        if participant_emails:
            # Safeguard for potentially missing TWG or Pillar
            pillar_name = "TWG"
            if db_meeting.twg and db_meeting.twg.pillar:
                pillar_name = db_meeting.twg.pillar.value
            
            await email_service.send_meeting_invite(
                to_emails=participant_emails,
                subject=f"INVITATION: {db_meeting.title}",
                template_name="meeting_invite.html",
                template_context={
                    "user_name": "Valued Participant",
                    "meeting_title": db_meeting.title,
                    "meeting_date": db_meeting.scheduled_at.strftime("%Y-%m-%d"),
                    "meeting_time": db_meeting.scheduled_at.strftime("%H:%M UTC"),
                    "location": db_meeting.location or "Virtual",
                    "video_link": db_meeting.video_link,
                    "pillar_name": pillar_name,
                    "portal_url": f"{settings.FRONTEND_URL}/schedule"
                },
                meeting_details={
                    "title": db_meeting.title,
                    "start_time": db_meeting.scheduled_at,
                    "duration": db_meeting.duration_minutes,
                    "location": db_meeting.location
                },
                attachments=attachments
            )
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"CRITICAL ERROR: Failed to send invitations for meeting {meeting_id}:\n{error_trace}")
        
        # Return partial success/warning instead of 500 crash
        # This allows the UI to show the specific error message
        return {
            "status": "warning",
            "message": f"Invites failed to send: {str(e)}",
            "emails_sent": 0
        }

    
    # Log Audit
    await audit_service.log_activity(
        db=db,
        user_id=current_user.id,
        action="MEETING_INVITES_SENT",
        resource_type="meeting",
        resource_id=meeting_id,
        details={
            "participant_count": len(participant_emails),
            "pdf_attached": bool(agenda and agenda.content),
            "invite_mode": "email"
        },
        ip_address=request.client.host if request.client else None
    )

    await db.commit()
    return {
        "status": "invites_sent",
        "message": f"Successfully sent invitations to {len(participant_emails)} participant(s).",
        "emails_sent": len(participant_emails)
    }


@router.post("/{meeting_id}/cancel", status_code=status.HTTP_200_OK)
async def cancel_meeting(
    meeting_id: uuid.UUID,
    cancel_data: MeetingCancel,
    request: Request,
    current_user: User = Depends(require_facilitator),
    db: AsyncSession = Depends(get_db)
):
    """
    Cancel a meeting and send cancellation notices with ICS cancellation.
    """
    query = select(Meeting).where(Meeting.id == meeting_id).options(
        selectinload(Meeting.participants).selectinload(MeetingParticipant.user),
        selectinload(Meeting.twg)
    )
    result = await db.execute(query)
    db_meeting = result.scalar_one_or_none()

    if not db_meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    if not has_twg_access(current_user, db_meeting.twg_id):
        raise HTTPException(status_code=403, detail="Access denied")

    # Update status to cancelled
    db_meeting.status = MeetingStatus.CANCELLED
    
    emails_sent = 0
    if cancel_data.notify_participants and db_meeting.participants:
        # Collect emails
        participant_emails = []
        for participant in db_meeting.participants:
            if participant.user and participant.user.email:
                participant_emails.append(participant.user.email)
            elif participant.email:
                participant_emails.append(participant.email)
        
        participant_emails = list(set(participant_emails))

        if participant_emails:
            from app.services.email_service import email_service
            try:
                await email_service.send_meeting_cancellation(
                    to_emails=participant_emails,
                    template_context={
                        "user_name": "Valued Participant",
                        "meeting_title": db_meeting.title,
                        "meeting_date": db_meeting.scheduled_at.strftime("%Y-%m-%d") if db_meeting.scheduled_at else "TBD",
                        "meeting_time": db_meeting.scheduled_at.strftime("%H:%M UTC") if db_meeting.scheduled_at else "TBD",
                        "location": db_meeting.location or "Virtual",
                        "pillar_name": db_meeting.twg.pillar.value if db_meeting.twg else "TWG",
                        "reason": cancel_data.reason,
                        "portal_url": f"{settings.FRONTEND_URL}/schedule"
                    },
                    meeting_details={
                        "title": db_meeting.title,
                        "start_time": db_meeting.scheduled_at or datetime.now(),
                        "duration": db_meeting.duration_minutes,
                        "location": db_meeting.location
                    },
                    reason=cancel_data.reason
                )
                emails_sent = len(participant_emails)
            except Exception as e:
                # Log full traceback for debugging to stdout
                import traceback
                error_trace = traceback.format_exc()
                print(f"CRITICAL ERROR: Failed to send cancellation emails:\n{error_trace}")
                # Don't fail the cancellation just because email failed
                pass

    await audit_service.log_activity(
        db=db,
        user_id=current_user.id,
        action="MEETING_CANCELLED",
        resource_type="meeting",
        resource_id=meeting_id,
        details={
            "reason": cancel_data.reason,
            "notify_participants": cancel_data.notify_participants,
            "emails_sent": emails_sent
        },
        ip_address=request.client.host if request.client else None
    )

    await db.commit()
    return {"status": "cancelled", "emails_sent": emails_sent}


@router.post("/{meeting_id}/notify-update", status_code=status.HTTP_200_OK)
async def notify_meeting_update(
    meeting_id: uuid.UUID,
    update_data: MeetingUpdateNotification,
    current_user: User = Depends(require_facilitator),
    db: AsyncSession = Depends(get_db)
):
    """
    Send an update notification to participants with updated ICS details.
    This should be called after modifying meeting details.
    """
    query = select(Meeting).where(Meeting.id == meeting_id).options(
        selectinload(Meeting.participants).selectinload(MeetingParticipant.user),
        selectinload(Meeting.twg)
    )
    result = await db.execute(query)
    db_meeting = result.scalar_one_or_none()

    if not db_meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    if not has_twg_access(current_user, db_meeting.twg_id):
        raise HTTPException(status_code=403, detail="Access denied")

    emails_sent = 0
    if update_data.notify_participants and db_meeting.participants:
        # Collect emails
        participant_emails = []
        for participant in db_meeting.participants:
            if participant.user and participant.user.email:
                participant_emails.append(participant.user.email)
            elif participant.email:
                participant_emails.append(participant.email)
        
        participant_emails = list(set(participant_emails))

        if participant_emails:
            from app.services.email_service import email_service
            try:
                await email_service.send_meeting_update(
                    to_emails=participant_emails,
                    template_context={
                        "user_name": "Valued Participant",
                        "meeting_title": db_meeting.title,
                        "meeting_date": db_meeting.scheduled_at.strftime("%Y-%m-%d") if db_meeting.scheduled_at else "TBD",
                        "meeting_time": db_meeting.scheduled_at.strftime("%H:%M UTC") if db_meeting.scheduled_at else "TBD",
                        "location": db_meeting.location or "Virtual",
                        "pillar_name": db_meeting.twg.pillar.value if db_meeting.twg else "TWG",
                        "changes": update_data.changes,
                        "portal_url": f"{settings.FRONTEND_URL}/schedule"
                    },
                    meeting_details={
                        "title": db_meeting.title,
                        "start_time": db_meeting.scheduled_at or datetime.now(),
                        "duration": db_meeting.duration_minutes,
                        "location": db_meeting.location
                    },
                    changes=update_data.changes
                )
                emails_sent = len(participant_emails)
            except Exception as e:
                # Log full traceback for debugging to stdout
                import traceback
                error_trace = traceback.format_exc()
                print(f"CRITICAL ERROR: Failed to send update emails:\n{error_trace}")
                # Raise warning but don't strictly crash 500 if we want to be lenient,
                # BUT since this endpoint is *only* for notification, a failure IS an error.
                # Use 500 but log it properly so user sees it in Railway.
                raise HTTPException(status_code=500, detail=f"Failed to send update emails: {str(e)}")

    return {"status": "notification_sent", "emails_sent": emails_sent}


@router.post("/{meeting_id}/conflict-check")
async def check_meeting_conflicts(
    meeting_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Check for scheduling conflicts before sending invites.
    Scans for:
    - VIP double-bookings (same participant in two meetings at same time)
    - Venue conflicts (same location booked at same time)
    - TWG member overlaps (key members in conflicting meetings)
    
    This is the Supervisor Agent's "Air Traffic Control" function.
    """
    from datetime import timedelta
    
    # Get the meeting with participants
    result = await db.execute(
        select(Meeting)
        .options(
            selectinload(Meeting.participants).selectinload(MeetingParticipant.user),
            selectinload(Meeting.twg)
        )
        .where(Meeting.id == meeting_id)
    )
    db_meeting = result.scalar_one_or_none()
    
    if not db_meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    
    if not has_twg_access(current_user, db_meeting.twg_id):
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Check if meeting has a scheduled time
    if not db_meeting.scheduled_at:
        return {
            "meeting_id": str(meeting_id),
            "conflicts": [],
            "has_conflicts": False,
            "can_proceed": True,
            "message": "Meeting has no scheduled time - skipping conflict check"
        }
    
    conflicts = []
    meeting_start = db_meeting.scheduled_at
    meeting_end = meeting_start + timedelta(minutes=db_meeting.duration_minutes or 60)
    
    # Get all other meetings that overlap in time
    overlapping_query = select(Meeting).options(
        selectinload(Meeting.participants).selectinload(MeetingParticipant.user),
        selectinload(Meeting.twg)
    ).where(
        Meeting.id != meeting_id,
        Meeting.scheduled_at < meeting_end,
        (Meeting.scheduled_at + timedelta(minutes=60)) > meeting_start  # Approximate end time
    )
    
    overlapping_result = await db.execute(overlapping_query)
    overlapping_meetings = overlapping_result.scalars().all()
    
    # Build list of participant emails/IDs for this meeting
    this_meeting_participants = set()
    for p in db_meeting.participants:
        if p.user_id:
            this_meeting_participants.add(str(p.user_id))
        if p.email:
            this_meeting_participants.add(p.email.lower())
    
    for other_meeting in overlapping_meetings:
        # Check 1: Venue conflicts
        if db_meeting.location and other_meeting.location:
            if db_meeting.location.lower().strip() == other_meeting.location.lower().strip():
                conflicts.append({
                    "type": "venue_conflict",
                    "severity": "high",
                    "message": f"Venue '{db_meeting.location}' is already booked",
                    "conflicting_meeting": {
                        "id": str(other_meeting.id),
                        "title": other_meeting.title,
                        "time": other_meeting.scheduled_at.isoformat() if other_meeting.scheduled_at else None,
                        "twg": other_meeting.twg.name if other_meeting.twg else None
                    }
                })
        
        # Check 2: Participant double-booking
        other_participants = set()
        for p in other_meeting.participants:
            if p.user_id:
                other_participants.add(str(p.user_id))
            if p.email:
                other_participants.add(p.email.lower())
        
        overlapping_people = this_meeting_participants & other_participants
        if overlapping_people:
            # Determine if any are VIPs (for now, treat all as important)
            for person_id in overlapping_people:
                # Try to find the name
                person_name = person_id
                for p in db_meeting.participants:
                    if str(p.user_id) == person_id or (p.email and p.email.lower() == person_id):
                        person_name = p.user.full_name if p.user else (p.name or p.email)
                        break
                
                conflicts.append({
                    "type": "participant_conflict",
                    "severity": "high",
                    "message": f"'{person_name}' is scheduled for another meeting at this time",
                    "conflicting_meeting": {
                        "id": str(other_meeting.id),
                        "title": other_meeting.title,
                        "time": other_meeting.scheduled_at.isoformat() if other_meeting.scheduled_at else None,
                        "twg": other_meeting.twg.name if other_meeting.twg else None
                    }
                })
    
    return {
        "meeting_id": str(meeting_id),
        "conflicts": conflicts,
        "has_conflicts": len(conflicts) > 0,
        "can_proceed": True,  # Allow override with acknowledgment
        "message": f"Found {len(conflicts)} potential conflict(s)" if conflicts else "No conflicts detected"
    }

@router.post("/{meeting_id}/participants", response_model=List[MeetingParticipantRead])
async def add_participants(
    meeting_id: uuid.UUID,
    participants: List[MeetingParticipantCreate],
    current_user: User = Depends(require_facilitator),
    db: AsyncSession = Depends(get_db)
):
    """
    Add participants (users or external guests) to a meeting.
    """
    # Verify meeting exists
    result = await db.execute(select(Meeting).where(Meeting.id == meeting_id))
    db_meeting = result.scalar_one_or_none()
    
    if not db_meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
        
    if not has_twg_access(current_user, db_meeting.twg_id):
        raise HTTPException(status_code=403, detail="Access denied")

    new_participants = []
    
    # 1. Identify emails that need lookup (no user_id provided)
    print(f"DEBUG: add_participants payload: {participants}")
    emails_to_lookup = [
        p.email.lower() for p in participants 
        if not p.user_id and p.email
    ]
    
    # 2. Batch query users
    email_to_userid_map = {}
    if emails_to_lookup:
        res = await db.execute(select(User).where(User.email.in_(emails_to_lookup)))
        found_users = res.scalars().all()
        for u in found_users:
            email_to_userid_map[u.email.lower()] = u.id

    # 3. Check for EXISTING participants to avoid duplicates
    existing_query = select(MeetingParticipant).where(MeetingParticipant.meeting_id == meeting_id)
    existing_res = await db.execute(existing_query)
    existing_participants = existing_res.scalars().all()
    
    existing_user_ids = {p.user_id for p in existing_participants if p.user_id}
    existing_emails = {p.email.lower() for p in existing_participants if p.email}

    for p_in in participants:
         # Determine User ID: Provided > Looked Up > None
         final_user_id = p_in.user_id
         if not final_user_id and p_in.email:
             final_user_id = email_to_userid_map.get(p_in.email.lower())

         # Check Duplicates
         if final_user_id and final_user_id in existing_user_ids:
             continue # Skip
         if p_in.email and p_in.email.lower() in existing_emails:
             continue # Skip

         db_p = MeetingParticipant(
             meeting_id=meeting_id,
             user_id=final_user_id,
             email=p_in.email,
             name=p_in.name,
             rsvp_status=RsvpStatus.PENDING
         )
         db.add(db_p)
         new_participants.append(db_p)
         
    await db.commit()
    
    # Sync to Google Calendar
    try:
        from app.services.calendar_service import calendar_service
        # Get DB meeting to check type
        if db_meeting.meeting_type == 'virtual' or db_meeting.meeting_type == 'hybrid': # Assume virtual/hybrid have links
             emails_to_add = [p.email for p in new_participants if p.email]
             if emails_to_add:
                 calendar_service.add_attendees_to_event(str(meeting_id), emails_to_add)
    except Exception as e:
        # Don't fail the request if sync fails
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to sync participants to GCal: {e}")
    
    # Refresh to return
    for p in new_participants:
        await db.refresh(p)
        
    return new_participants

@router.post("/{meeting_id}/agenda", response_model=AgendaRead)
async def upsert_agenda(
    meeting_id: uuid.UUID,
    agenda_in: AgendaCreate,
    current_user: User = Depends(require_facilitator),
    db: AsyncSession = Depends(get_db)
):
    """
    Create or Update meeting agenda.
    """
    # Verify meeting
    result = await db.execute(select(Meeting).where(Meeting.id == meeting_id))
    db_meeting = result.scalar_one_or_none()
    if not db_meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
        
    if not has_twg_access(current_user, db_meeting.twg_id):
        raise HTTPException(status_code=403, detail="Access denied")

    # Check existing
    result = await db.execute(select(Agenda).where(Agenda.meeting_id == meeting_id))
    db_agenda = result.scalar_one_or_none()
    
    if db_agenda:
        db_agenda.content = agenda_in.content
    else:
        db_agenda = Agenda(meeting_id=meeting_id, content=agenda_in.content)
        db.add(db_agenda)
        
    await db.commit()
    await db.refresh(db_agenda)
    return db_agenda


@router.post("/{meeting_id}/agenda/generate")
async def generate_agenda(
    meeting_id: uuid.UUID,
    current_user: User = Depends(require_facilitator),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate a draft agenda using the Supervisor AI agent.
    The Supervisor coordinates the specific TWG agent to draft the content.
    """
    from app.agents.langgraph_base_agent import create_langgraph_agent
    
    # Get meeting with TWG info
    result = await db.execute(
        select(Meeting)
        .options(selectinload(Meeting.twg))
        .where(Meeting.id == meeting_id)
    )
    db_meeting = result.scalar_one_or_none()
    
    if not db_meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    
    if not has_twg_access(current_user, db_meeting.twg_id):
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Use Supervisor Agent ("Secretariat AI")
    agent = create_langgraph_agent(agent_id="supervisor", session_id=str(meeting_id))
    
    pillar_name = db_meeting.twg.pillar.value if db_meeting.twg else "Unspecified"
    
    # Prompt Supervisor to coordinate the task
    prompt = f"""Act as the Summit Secretariat Supervisor. Instruct the {pillar_name} TWG Agent to draft a professional meeting agenda for the following session.

Meeting Details:
- Title: {db_meeting.title}
- Date: {db_meeting.scheduled_at.strftime('%Y-%m-%d %H:%M UTC') if db_meeting.scheduled_at else 'TBD'}
- Duration: {db_meeting.duration_minutes} minutes
- Location: {db_meeting.location or 'Virtual'}
- TWG Pillar: {pillar_name}

INSTRUCTIONS:
1. Generate the agenda CONTENT ONLY.
2. Use the strict MARKDOWN structure below.
3. DO NOT include any conversational text (e.g., "Here is the agenda...").
4. DO NOT simulate sending emails or calling tools.
5. The output must be PURE MARKDOWN.

STRUCTURE:

# Meeting Agenda: {db_meeting.title}

## 1. Opening & Welcome (5 min)
- Introduction by the Chair
- Meeting objectives overview

## 2. Review of Previous Action Items (10 min)
- Status updates
- Outstanding items

## 3. Main Discussion Topics
Discussion topics relevant to the {pillar_name} pillar:
- **Topic 1**: [description based on context]
- **Topic 2**: [description based on context]

## 4. Action Items & Next Steps
- New assignments
- Deadlines

## 5. Closing Remarks (5 min)
- Summary
- Adjournment"""

    generated_content = await agent.chat(prompt)
    
    return {"generated_agenda": generated_content}


@router.put("/{meeting_id}/participants/{participant_id}/rsvp", response_model=MeetingParticipantRead)
async def update_participant_rsvp(
    meeting_id: uuid.UUID,
    participant_id: uuid.UUID,
    rsvp_in: MeetingParticipantUpdate, # Just status
    current_user: User = Depends(require_facilitator), # Facilitator override aka "Fallback"
    db: AsyncSession = Depends(get_db)
):
    """
    Manually update a participant's RSVP status (RSVP Fallback).
    """
    # Verify meeting
    result = await db.execute(select(Meeting).where(Meeting.id == meeting_id))
    db_meeting = result.scalar_one_or_none()
    if not db_meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
        
    if not has_twg_access(current_user, db_meeting.twg_id):
        raise HTTPException(status_code=403, detail="Access denied")
        
    # Get participant
    result = await db.execute(select(MeetingParticipant).where(MeetingParticipant.id == participant_id))
    db_p = result.scalar_one_or_none()
    
    if not db_p:
        raise HTTPException(status_code=404, detail="Participant not found")
        
    if db_p.meeting_id != meeting_id:
        raise HTTPException(status_code=400, detail="Participant does not belong to this meeting")
        
    if rsvp_in.rsvp_status:
        db_p.rsvp_status = rsvp_in.rsvp_status
        
    await db.commit()
    await db.refresh(db_p)
    return db_p


# ==================== AGENDA ENDPOINTS ====================

@router.get("/{meeting_id}/agenda", response_model=AgendaRead)
async def get_meeting_agenda(
    meeting_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get the agenda for a specific meeting."""
    result = await db.execute(select(Meeting).where(Meeting.id == meeting_id))
    db_meeting = result.scalar_one_or_none()
    
    if not db_meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
        
    if not has_twg_access(current_user, db_meeting.twg_id):
        raise HTTPException(status_code=403, detail="Access denied")
    
    result = await db.execute(select(Agenda).where(Agenda.meeting_id == meeting_id))
    agenda = result.scalar_one_or_none()
    
    if not agenda:
        raise HTTPException(status_code=404, detail="Agenda not found")
        
    return agenda


@router.post("/{meeting_id}/agenda", response_model=AgendaRead)
async def create_or_update_agenda(
    meeting_id: uuid.UUID,
    agenda_in: AgendaCreate,
    current_user: User = Depends(require_facilitator),
    db: AsyncSession = Depends(get_db)
):
    """Create or update the agenda for a meeting."""
    result = await db.execute(select(Meeting).where(Meeting.id == meeting_id))
    db_meeting = result.scalar_one_or_none()
    
    if not db_meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
        
    if not has_twg_access(current_user, db_meeting.twg_id):
        raise HTTPException(status_code=403, detail="Access denied")
    
    result = await db.execute(select(Agenda).where(Agenda.meeting_id == meeting_id))
    existing_agenda = result.scalar_one_or_none()
    
    if existing_agenda:
        existing_agenda.content = agenda_in.content
        await db.commit()
        await db.refresh(existing_agenda)
        return existing_agenda
    else:
        db_agenda = Agenda(meeting_id=meeting_id, content=agenda_in.content)
        db.add(db_agenda)
        await db.commit()
        await db.refresh(db_agenda)
        return db_agenda


# ==================== MINUTES ENDPOINTS ====================

@router.get("/{meeting_id}/minutes", response_model=MinutesRead)
async def get_meeting_minutes(
    meeting_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get the minutes for a specific meeting."""
    result = await db.execute(select(Meeting).where(Meeting.id == meeting_id))
    db_meeting = result.scalar_one_or_none()
    
    if not db_meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
        
    if not has_twg_access(current_user, db_meeting.twg_id):
        raise HTTPException(status_code=403, detail="Access denied")
    
    result = await db.execute(select(Minutes).where(Minutes.meeting_id == meeting_id))
    minutes = result.scalar_one_or_none()
    
    if not minutes:
        raise HTTPException(status_code=404, detail="Minutes not found")
        
    return minutes


@router.post("/{meeting_id}/minutes", response_model=MinutesRead)
async def create_or_update_minutes(
    meeting_id: uuid.UUID,
    minutes_in: MinutesCreate,
    current_user: User = Depends(require_facilitator),
    db: AsyncSession = Depends(get_db)
):
    """Create or update the minutes for a meeting."""
    result = await db.execute(select(Meeting).where(Meeting.id == meeting_id))
    db_meeting = result.scalar_one_or_none()
    
    if not db_meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
        
    if not has_twg_access(current_user, db_meeting.twg_id):
        raise HTTPException(status_code=403, detail="Access denied")
    
    result = await db.execute(select(Minutes).where(Minutes.meeting_id == meeting_id))
    existing_minutes = result.scalar_one_or_none()
    
    if existing_minutes:
        existing_minutes.content = minutes_in.content
        if minutes_in.status:
            existing_minutes.status = minutes_in.status
        await db.commit()
        await db.refresh(existing_minutes)
        return existing_minutes
    else:
        db_minutes = Minutes(
            meeting_id=meeting_id,
            content=minutes_in.content,
            status=minutes_in.status if minutes_in.status else MinutesStatus.DRAFT
        )
        db.add(db_minutes)
        await db.commit()
        await db.refresh(db_minutes)
        return db_minutes


@router.post("/{meeting_id}/minutes/generate")
async def generate_minutes(
    meeting_id: uuid.UUID,
    current_user: User = Depends(require_facilitator),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate draft meeting minutes using the Supervisor AI agent.
    The Supervisor coordinates the specific TWG agent (Rapporteur Mode) to draft the minutes.
    """
    from app.agents.langgraph_base_agent import create_langgraph_agent
    
    # Get meeting with TWG and agenda info
    result = await db.execute(
        select(Meeting)
        .options(selectinload(Meeting.twg), selectinload(Meeting.agenda))
        .where(Meeting.id == meeting_id)
    )
    db_meeting = result.scalar_one_or_none()
    
    if not db_meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    
    if not has_twg_access(current_user, db_meeting.twg_id):
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Use Supervisor Agent ("Secretariat AI")
    agent = create_langgraph_agent(agent_id="supervisor", session_id=str(meeting_id))
    
    pillar_name = db_meeting.twg.pillar.value if db_meeting.twg else "Unspecified"
    
    # Use transcript if available, otherwise use agenda
    context = db_meeting.transcript if db_meeting.transcript else ""
    agenda_content = db_meeting.agenda.content if db_meeting.agenda else ""
    
    # RAG: Retrieve context from Summit Knowledge Repository
    from app.core.knowledge_base import get_knowledge_base
    kb = get_knowledge_base()
    search_query = f"{db_meeting.title} {agenda_content[:100]}"
    try:
        # Search global namespace for general policy (Vision 2050 etc)
        rag_results = kb.search(query=search_query, namespace="global", top_k=3)
        
        # Also search TWG namespace for continuity
        if db_meeting.twg_id:
             twg_results = kb.search(query=search_query, namespace=f"twg-{db_meeting.twg_id}", top_k=2)
             rag_results.extend(twg_results)
             
        rag_context = "\n".join([f"- {r['metadata'].get('file_name', 'Doc')}: {r['text'][:300]}..." for r in rag_results])
    except Exception as e:
        print(f"RAG Retrieval failed: {e}")
        rag_context = "No specific policy context available."

    prompt = f"""Act as the Summit Secretariat Supervisor. Instruct the {pillar_name} TWG Agent to draft professional meeting minutes for the following session.

Meeting Details:
- Title: {db_meeting.title}
- Date: {db_meeting.scheduled_at.strftime('%Y-%m-%d %H:%M UTC') if db_meeting.scheduled_at else 'TBD'}
- Duration: {db_meeting.duration_minutes} minutes
- Location: {db_meeting.location or 'Virtual'}
- TWG Pillar: {pillar_name}

Reference Context (Knowledge Repository):
{rag_context}

Context (Agenda/Transcript):
{agenda_content}

{f"Transcript/Notes:{chr(10)}{context}" if context else "No transcript available. WARNING: Cannot generate minutes without a source record."}

INSTRUCTIONS:
1. **Strict Adherence**: You are a Court Stenographer, not an author. Rely EXCLUSIVELY on the provided Transcript/Notes. Do NOT hallucinate, simulate, or invent details.
2. **Policy Verification**: Cross-reference facts against the Reference Context. 
   - If a claim matches the Reference, cite it (e.g., "Aligned with Vision 2050").
   - If the Reference Context is empty or the claim cannot be verified, DO NOT invent a verification. 
3. **Gap Flagging**: If the transcript is unclear or context is missing for a section, explicitly mark it as `[DRAFT - REQUIRES HUMAN INPUT]`.
4. **Playbook Structure**: Follow the format below exactly.
5. **Output Format**: PURE MARKDOWN only.

STRUCTURE:

# ECOWAS Technical Working Group Meeting Minutes

## Meeting Details
- **Title:** {db_meeting.title}
- **Date:** {db_meeting.scheduled_at.strftime('%Y-%m-%d') if db_meeting.scheduled_at else 'TBD'}
- **Location:** {db_meeting.location or 'Virtual'}
- **Pillar:** {pillar_name}

## Pillar Alignment
[Analyze alignment with Vision 2050 using Reference Context. IF Reference Context is empty, state: "Reference documents unavailable for alignment verification."]

## Executive Summary & Discussion
[Comprehensive summary based ONLY on the transcript. Do not embellish.]

## Decisions Made
[Clearly highlighted points of consensus]
1. ...
2. ...

## Action Items
| Owner | Task | Due Date |
|-------|------|----------|
| [Name/Title] | [Specific Task] | [Date or TBD] |

## Next Steps
[Brief summary of immediate next steps]

## Closing
[Closing remarks]"""

    generated_content = agent.chat(prompt)
    
    # Persist headers
    result_min = await db.execute(select(Minutes).where(Minutes.meeting_id == meeting_id))
    existing_minutes = result_min.scalar_one_or_none()
    
    if existing_minutes:
        existing_minutes.content = generated_content
        existing_minutes.status = MinutesStatus.DRAFT
    else:
        new_minutes = Minutes(
            meeting_id=meeting_id,
            content=generated_content,
            status=MinutesStatus.DRAFT
        )
        db.add(new_minutes)
    
    await db.commit()
    
    return {"generated_minutes": generated_content}


@router.post("/{meeting_id}/minutes/submit-for-approval")
async def submit_minutes_for_approval(
    meeting_id: uuid.UUID,
    current_user: User = Depends(require_facilitator),
    db: AsyncSession = Depends(get_db)
):
    """
    Submit minutes for approval. Changes status from DRAFT to PENDING_APPROVAL.
    Human oversight gate: Nothing is finalized until explicitly approved.
    """
    print(f"DEBUG: submit_minutes called for {meeting_id}")
    # Get meeting and minutes
    try:
        result = await db.execute(
            select(Meeting)
            .options(
                selectinload(Meeting.minutes),
                selectinload(Meeting.participants).selectinload(MeetingParticipant.user),
                selectinload(Meeting.twg)
            )
            .where(Meeting.id == meeting_id)
        )
    except Exception as e:
        import traceback
        print(f"DEBUG: DB Load Failed: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"DB Load Failed: {e}")
        
    print(f"DEBUG: submit_minutes query executed")
    db_meeting = result.scalar_one_or_none()
    
    if not db_meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    
    if not has_twg_access(current_user, db_meeting.twg_id):
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not db_meeting.minutes:
        raise HTTPException(status_code=400, detail="No minutes to submit")
    
    print("DEBUG: Checking current status")
    # Get current status safely (could be string or Enum due to schema relaxation)
    current_status = db_meeting.minutes.status
    if hasattr(current_status, 'value'):
        current_status_val = current_status.value
    else:
        current_status_val = str(current_status)

    if current_status_val not in [MinutesStatus.DRAFT.value, MinutesStatus.REVIEW.value, "draft", "review"]:
        raise HTTPException(
            status_code=400, 
            detail=f"Minutes must be in DRAFT or REVIEW status to submit. Current: {current_status_val}"
        )
    
    # Update status
    # Use the Enum object explicitly for SQLAlchemy
    db_meeting.minutes.status = MinutesStatus.PENDING_APPROVAL
    
    # Clear rejection info on resubmission
    if db_meeting.minutes.rejection_reason:
        db_meeting.minutes.rejected_at = None
        db_meeting.minutes.rejection_reason = None
        
    print(f"DEBUG: Committing status update to: {db_meeting.minutes.status}", flush=True)
    
    # Debug: Check object state
    try:
        from sqlalchemy import inspect
        insp = inspect(db_meeting.minutes)
        print(f"DEBUG: Minutes object state: transient={insp.transient}, pending={insp.pending}, persistent={insp.persistent}, detached={insp.detached}", flush=True)
    except Exception as e:
        print(f"DEBUG: Failed to inspect object: {e}", flush=True)

    try:
        # 1. Set a short lock timeout
        try:
            await db.execute(text("SET lock_timeout = '2s'"))
        except Exception as e:
            print(f"DEBUG: Failed to set lock_timeout: {type(e).__name__}: {e}", flush=True)
            # Potentially unrecoverable if DB is unhappy, but let's try to proceed or re-raise
            # If we assume this is the cause, we should re-raise
            raise e
        
        # 2. Flush first - WRAPPED
        print("DEBUG: Flushing changes...", flush=True)
        try:
            await db.flush()
            print("DEBUG: Flush successful, now committing...", flush=True)
        except Exception as e:
            print(f"DEBUG: FATAL ERROR DURING FLUSH: {type(e).__name__}: {e}", flush=True)
            import traceback
            traceback.print_exc()
            await db.rollback()
            raise HTTPException(status_code=500, detail=f"Database Flush Error: {str(e)}")

        # 3. Commit with timeout safety
        import asyncio
        try:
            await asyncio.wait_for(db.commit(), timeout=5.0)
            print("DEBUG: Commit successful", flush=True)
        except asyncio.TimeoutError:
            print("DEBUG: Commit timed out!", flush=True)
            await db.rollback()
            raise HTTPException(status_code=503, detail="Database is busy (timeout). Please try again.")
        except Exception as e:
            print(f"DEBUG: FATAL ERROR DURING COMMIT: {type(e).__name__}: {e}", flush=True)
            await db.rollback()
            raise HTTPException(status_code=500, detail=f"Database Commit Error: {str(e)}")
            
        await db.refresh(db_meeting.minutes)
        print("DEBUG: Refresh successful", flush=True)
        
    except HTTPException:
        raise
    except Exception as e:
        # Check for lock timeout error in broader scope
        error_str = str(e).lower()
        print(f"DEBUG: Outer Exception Caught: {type(e).__name__}: {e}", flush=True)
        
        if "lock" in error_str or "timeout" in error_str:
            print(f"DEBUG: Lock acquisition failed (caught in outer): {e}", flush=True)
            await db.rollback()
            raise HTTPException(
                status_code=503, 
                detail="System is busy processing this meeting. Please wait 5 seconds and try again."
            )
        
        import traceback
        traceback.print_exc()
        raise e
        
        import traceback
        import sys
        import traceback
        import sys
        error_details = {
            "error_type": type(e).__name__,
            "error_message": str(e),
            "traceback": traceback.format_exc(),
            "minutes_id": str(db_meeting.minutes.id) if db_meeting.minutes else None,
            "current_status_type": type(db_meeting.minutes.status).__name__ if db_meeting.minutes else None,
            "current_status_value": str(db_meeting.minutes.status) if db_meeting.minutes else None
        }
        print(f"DEBUG: DB Commit Failed - Full Error Details:")
        print(f"  Type: {error_details['error_type']}")
        print(f"  Message: {error_details['error_message']}")
        print(f"  Status Type: {error_details['current_status_type']}")
        print(f"  Status Value: {error_details['current_status_value']}")
        print(f"  Traceback:\n{error_details['traceback']}")
        logger.error(f"DB Commit Failed during minutes submission: {e}")
        logger.error(traceback.format_exc())
        # Rollback to clean state
        await db.rollback()
        raise HTTPException(
            status_code=500, 
            detail=f"Database error during submission: {error_details['error_type']} - {error_details['error_message']}"
        )

    # --- Notification Logic ---
    print("DEBUG: Starting notification logic")
    try:
        from app.models.models import Notification, NotificationType
        
        # Notify ALL Admins and Secretariat Leads
        result = await db.execute(select(User).where(User.role.in_([UserRole.ADMIN, UserRole.SECRETARIAT_LEAD])))
        reviewers = result.scalars().all()
        
        # If no high-level reviewers, fallback to TWG Technical Lead
        if not reviewers:
            if db_meeting.twg and db_meeting.twg.technical_lead_id:
                reviewer = await db.execute(select(User).where(User.id == db_meeting.twg.technical_lead_id))
                user = reviewer.scalar_one_or_none()
                if user:
                    reviewers.append(user)

        # Create notifications
        if reviewers:
            for reviewer in reviewers:
                notification = Notification(
                    user_id=reviewer.id,
                    type=NotificationType.TASK,
                    title="Minutes Approval Required",
                    content=f"Minutes for '{db_meeting.title}' submitted by {current_user.full_name}. Please review and approve.",
                    link=f"/meetings/{meeting_id}"
                )
                db.add(notification)
            await db.commit()
    except Exception as e:
        logger.error(f"Failed to send approval notifications: {e}")
        # Non-blocking, proceed

    
    return {
        "message": "Minutes submitted for approval",
        "status": db_meeting.minutes.status.value if hasattr(db_meeting.minutes.status, 'value') else str(db_meeting.minutes.status),
        "meeting_id": str(meeting_id),
        "approved_by": current_user.full_name
    }


@router.post("/{meeting_id}/minutes/approve")
async def approve_minutes(
    meeting_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(require_facilitator),
    db: AsyncSession = Depends(get_db)
):
    """
    Approve minutes. Changes status from PENDING_APPROVAL to APPROVED.
    Triggers: PDF Generation, Email Distribution, KB Indexing, Audit Logging.
    """
    # Get meeting and minutes
    result = await db.execute(
        select(Meeting)
        .options(
            selectinload(Meeting.minutes),
            selectinload(Meeting.participants).selectinload(MeetingParticipant.user),
            selectinload(Meeting.twg)
        )
        .where(Meeting.id == meeting_id)
    )
    db_meeting = result.scalar_one_or_none()
    
    if not db_meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    
    if not has_twg_access(current_user, db_meeting.twg_id):
        raise HTTPException(status_code=403, detail="Access denied")
        
    # Enforce Secretariat Lead (or Admin) approval
    if current_user.role not in [UserRole.SECRETARIAT_LEAD, UserRole.ADMIN]:
        raise HTTPException(
            status_code=403, 
            detail="Only Secretariat Leads can approve minutes. Please submit for approval instead."
        )
    
    if not db_meeting.minutes:
        raise HTTPException(status_code=400, detail="No minutes to approve")
    
    # Handle both Enum and string status values (PostgreSQL vs SQLite difference)
    current_status_val = db_meeting.minutes.status.value if hasattr(db_meeting.minutes.status, 'value') else str(db_meeting.minutes.status)
    if current_status_val != MinutesStatus.PENDING_APPROVAL.value:
        raise HTTPException(status_code=400, detail=f"Minutes must be PENDING_APPROVAL to approve. Current: {current_status_val}")
    
    # Approve
    db_meeting.minutes.status = MinutesStatus.APPROVED
    await db.commit()
    await db.refresh(db_meeting.minutes)
    
    # --- Post-Approval Workflows ---
    
    # 1. Generate Official PDF
    pdf_bytes = None
    try:
        from app.services.pdf_service import pdf_service
        
        pillar_display = db_meeting.twg.pillar.value.replace("_", " ").title() if db_meeting.twg else "General"
        pdf_context = {
            "pillar_name": pillar_display,
            "meeting_title": db_meeting.title,
            "meeting_date": db_meeting.scheduled_at.strftime('%Y-%m-%d') if db_meeting.scheduled_at else "TBD",
            "meeting_time": db_meeting.scheduled_at.strftime('%H:%M') if db_meeting.scheduled_at else "",
            "location": db_meeting.location or "Virtual",
        }
        pdf_bytes = pdf_service.generate_minutes_pdf(
            minutes_markdown=db_meeting.minutes.content,
            template_context=pdf_context
        )
    except Exception as e:
        print(f"PDF Gen Failure: {e}")
        # Log warning but don't crash, the status is already updated
    
    # 2. Index to Knowledge Base (RAG)
    try:
        from app.core.knowledge_base import get_knowledge_base
        kb = get_knowledge_base()
        kb.add_document(
            content=db_meeting.minutes.content,
            metadata={
                "source": "official_minutes",
                "meeting_id": str(db_meeting.id),
                "date": db_meeting.scheduled_at.isoformat() if db_meeting.scheduled_at else None,
                "pillar": db_meeting.twg.pillar.value if db_meeting.twg else "unknown",
                "status": "approved",
                "file_name": f"Minutes - {db_meeting.title}"
            },
            namespace=f"twg-{db_meeting.twg_id}" if db_meeting.twg_id else "global"
        )
    except Exception as e:
        print(f"KB Indexing Failed: {e}")

    # 3. Send Emails to Participants
    recipients = set()
    
    for p in db_meeting.participants:
        # 1. Registered User Email
        if p.user and p.user.email:
            recipients.add(p.user.email)
        # 2. Guest Email (stored directly on participant record)
        elif p.email:
            recipients.add(p.email)
            
    recipient_list = list(recipients)
    
    if pdf_bytes and recipient_list:
        try:
             email_context = {
                 "recipient_name": "Colleague", 
                 "meeting_title": db_meeting.title,
                 "date_str": db_meeting.scheduled_at.strftime('%Y-%m-%d') if db_meeting.scheduled_at else "TBD",
                 "pillar_name": pillar_display,
                 "dashboard_url": f"{settings.FRONTEND_URL}/meetings/{db_meeting.id}"
             }
             await email_service.send_minutes_published_email(
                 to_emails=recipient_list,
                 template_context=email_context,
                 pdf_content=pdf_bytes,
                 pdf_filename="minutes.pdf"
             )
        except Exception as e:
            print(f"Email Sending Failed: {e}")
            # Non-blocking

    # --- Audit Log ---
    from app.services.audit_service import audit_service
    
    await audit_service.log_activity(
        db,
        user_id=current_user.id,
        action="MEETING_MINUTES_APPROVED",
        resource_type="meeting",
        resource_id=meeting_id,
        details={
            "meeting_title": db_meeting.title,
            "actions": "generated_pdf, sent_email, indexed_kb",
            "recipients": recipient_list  # Explicitly log who got it
        },
        ip_address=request.client.host if request.client else None
    )
    
    return {
        "message": "Minutes approved and published",
        "status": db_meeting.minutes.status.value if hasattr(db_meeting.minutes.status, 'value') else str(db_meeting.minutes.status),
        "workflows_triggered": ["pdf", "email", "audit", "kb_indexing"] 
    }


@router.get("/{meeting_id}/minutes/pdf")
async def download_minutes_pdf(
    meeting_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Download meeting minutes as PDF.
    Available for APPROVED or FINAL status only.
    """
    from fastapi.responses import Response
    from app.services.pdf_service import pdf_service
    
    # Get meeting with minutes and TWG
    result = await db.execute(
        select(Meeting)
        .options(selectinload(Meeting.minutes), selectinload(Meeting.twg))
        .where(Meeting.id == meeting_id)
    )
    db_meeting = result.scalar_one_or_none()
    
    if not db_meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    
    if not has_twg_access(current_user, db_meeting.twg_id):
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not db_meeting.minutes:
        raise HTTPException(status_code=404, detail="No minutes found for this meeting")
    
    # Allow download for APPROVED and FINAL status (also DRAFT for preview)
    allowed_status_values = [MinutesStatus.APPROVED.value, MinutesStatus.FINAL.value, MinutesStatus.DRAFT.value, MinutesStatus.PENDING_APPROVAL.value]
    current_pdf_status = db_meeting.minutes.status.value if hasattr(db_meeting.minutes.status, 'value') else str(db_meeting.minutes.status)
    if current_pdf_status not in allowed_status_values:
        raise HTTPException(
            status_code=400, 
            detail=f"Minutes must be in APPROVED, FINAL, DRAFT, or PENDING_APPROVAL status. Current: {current_pdf_status}"
        )
    
    # Generate PDF
    pillar_display = db_meeting.twg.pillar.value.replace("_", " ").title() if db_meeting.twg else "General"
    pdf_context = {
        "pillar_name": pillar_display,
        "meeting_title": db_meeting.title,
        "meeting_date": db_meeting.scheduled_at.strftime('%Y-%m-%d') if db_meeting.scheduled_at else "TBD",
        "meeting_time": db_meeting.scheduled_at.strftime('%H:%M') if db_meeting.scheduled_at else "",
        "location": db_meeting.location or "Virtual",
    }
    
    try:
        pdf_bytes = pdf_service.generate_minutes_pdf(
            minutes_markdown=db_meeting.minutes.content,
            template_context=pdf_context
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate PDF: {str(e)}")
    
    # Create safe filename
    safe_title = "".join(c if c.isalnum() or c in " -_" else "_" for c in db_meeting.title)[:50]
    filename = f"Minutes_{safe_title}.pdf"
    
    # Add watermark for non-approved minutes
    status_label = ""
    pdf_status_check = db_meeting.minutes.status.value if hasattr(db_meeting.minutes.status, 'value') else str(db_meeting.minutes.status)
    if pdf_status_check == MinutesStatus.DRAFT.value:
        status_label = "DRAFT_"
    elif pdf_status_check == MinutesStatus.PENDING_APPROVAL.value:
        status_label = "PENDING_"
    
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={status_label}{filename}"
        }
    )


@router.post("/{meeting_id}/minutes/reject")
async def reject_minutes(
    meeting_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(require_facilitator),
    db: AsyncSession = Depends(get_db)
):
    """
    Reject minutes and send back for revision.
    Changes status from PENDING_APPROVAL to REVIEW.
    Stores rejection reason and notifies the TWG lead.
    """
    from datetime import datetime
    from app.models.models import Notification, NotificationType
    
    # Parse body
    body = await request.json()
    rejection_reason = body.get("reason", "No reason provided")
    suggested_changes = body.get("suggested_changes", "")
    
    # Get meeting and minutes
    result = await db.execute(
        select(Meeting)
        .options(
            selectinload(Meeting.minutes),
            selectinload(Meeting.twg).selectinload(TWG.technical_lead)
        )
        .where(Meeting.id == meeting_id)
    )
    db_meeting = result.scalar_one_or_none()
    
    if not db_meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    
    if not has_twg_access(current_user, db_meeting.twg_id):
        raise HTTPException(status_code=403, detail="Access denied")
        
    # Enforce Secretariat Lead (or Admin) rejection
    if current_user.role not in [UserRole.SECRETARIAT_LEAD, UserRole.ADMIN]:
        raise HTTPException(
            status_code=403, 
            detail="Only Secretariat Leads can reject minutes. Please contact support if you need to revert status."
        )
    
    if not db_meeting.minutes:
        raise HTTPException(status_code=400, detail="No minutes to reject")
    
    # Handle both Enum and string status values (PostgreSQL vs SQLite difference)
    current_reject_status = db_meeting.minutes.status.value if hasattr(db_meeting.minutes.status, 'value') else str(db_meeting.minutes.status)
    if current_reject_status != MinutesStatus.PENDING_APPROVAL.value:
        raise HTTPException(
            status_code=400, 
            detail=f"Minutes must be PENDING_APPROVAL to reject. Current: {current_reject_status}"
        )
    
    # Update status to REVIEW
    db_meeting.minutes.status = MinutesStatus.REVIEW
    
    # Store rejection reason in key_decisions field (or add metadata)
    # We'll prepend a rejection note to the key_decisions field
    rejection_note = f"[REJECTION - {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}]\nReason: {rejection_reason}"
    if suggested_changes:
        rejection_note += f"\nSuggested Changes: {suggested_changes}"
    rejection_note += "\n---\n"
    
    if db_meeting.minutes.key_decisions:
        db_meeting.minutes.key_decisions = rejection_note + db_meeting.minutes.key_decisions
    else:
        db_meeting.minutes.key_decisions = rejection_note
    
    await db.commit()
    await db.refresh(db_meeting.minutes)
    
    # Create notification for TWG lead
    if db_meeting.twg and db_meeting.twg.technical_lead:
        notification = Notification(
            user_id=db_meeting.twg.technical_lead.id,
            type=NotificationType.ALERT,
            title="Minutes Rejected",
            content=f"Minutes for '{db_meeting.title}' were rejected. Reason: {rejection_reason}",
            link=f"/meetings/{meeting_id}"
        )
        db.add(notification)
        await db.commit()
    
    # Audit log
    await audit_service.log_activity(
        db=db,
        user_id=current_user.id,
        action="MEETING_MINUTES_REJECTED",
        resource_type="meeting",
        resource_id=meeting_id,
        details={
            "meeting_title": db_meeting.title,
            "reason": rejection_reason,
            "suggested_changes": suggested_changes
        },
        ip_address=request.client.host if request.client else None
    )
    
    return {
        "message": "Minutes rejected and sent back for revision",
        "status": db_meeting.minutes.status.value if hasattr(db_meeting.minutes.status, 'value') else str(db_meeting.minutes.status),
        "reason": rejection_reason
    }


# ==================== ACTION ITEMS ENDPOINTS ====================

@router.get("/{meeting_id}/action-items", response_model=List[dict])
async def get_meeting_action_items(
    meeting_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all action items for a specific meeting."""
    result = await db.execute(select(Meeting).where(Meeting.id == meeting_id))
    db_meeting = result.scalar_one_or_none()
    
    if not db_meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
        
    if not has_twg_access(current_user, db_meeting.twg_id):
        raise HTTPException(status_code=403, detail="Access denied")
    
    result = await db.execute(
        select(ActionItem)
        .options(selectinload(ActionItem.owner))
        .where(ActionItem.meeting_id == meeting_id)
    )
    action_items = result.scalars().all()
    
    return [
        {
            "id": str(item.id),
            "description": item.description,
            "owner": {
                "name": item.owner.full_name if item.owner else "Unassigned",
                "avatar": item.owner.full_name[0] if item.owner and item.owner.full_name else "U"
            },
            "dueDate": item.due_date.strftime("%b %d, %Y") if item.due_date else None,
            "status": item.status.value if item.status else "pending"
        }
        for item in action_items
    ]


@router.post("/{meeting_id}/action-items", response_model=dict)
async def create_action_item(
    meeting_id: uuid.UUID,
    action_data: dict,
    current_user: User = Depends(require_facilitator),
    db: AsyncSession = Depends(get_db)
):
    """Create a new action item for a meeting."""
    from datetime import datetime
    
    result = await db.execute(select(Meeting).where(Meeting.id == meeting_id))
    db_meeting = result.scalar_one_or_none()
    
    if not db_meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
        
    if not has_twg_access(current_user, db_meeting.twg_id):
        raise HTTPException(status_code=403, detail="Access denied")
    
    db_action = ActionItem(
        twg_id=db_meeting.twg_id,
        meeting_id=meeting_id,
        description=action_data.get("description"),
        owner_id=uuid.UUID(action_data.get("owner_id")) if action_data.get("owner_id") else current_user.id,
        due_date=datetime.fromisoformat(action_data.get("due_date")) if action_data.get("due_date") else datetime.utcnow(),
        status=action_data.get("status", "PENDING")
    )
    
    db.add(db_action)
    await db.commit()
    await db.refresh(db_action, ["owner"])
    
    return {
        "id": str(db_action.id),
        "description": db_action.description,
        "owner": {
            "name": db_action.owner.full_name if db_action.owner else "Unassigned",
            "avatar": db_action.owner.full_name[0] if db_action.owner and db_action.owner.full_name else "U"
        },
        "dueDate": db_action.due_date.strftime("%b %d, %Y") if db_action.due_date else None,
        "status": db_action.status.value if db_action.status else "pending"
    }


@router.post("/{meeting_id}/extract-actions")
async def extract_action_items(
    meeting_id: uuid.UUID,
    current_user: User = Depends(require_facilitator),
    db: AsyncSession = Depends(get_db)
):
    """
    Use AI to extract action items from meeting minutes and create ActionItem records.
    """
    
    # Get meeting with minutes
    result = await db.execute(
        select(Meeting)
        .options(selectinload(Meeting.twg), selectinload(Meeting.minutes))
        .where(Meeting.id == meeting_id)
    )
    db_meeting = result.scalar_one_or_none()
    
    if not db_meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    
    if not has_twg_access(current_user, db_meeting.twg_id):
        raise HTTPException(status_code=403, detail="Access denied")
    
    minutes_content = ""
    if db_meeting.minutes:
        minutes_content = db_meeting.minutes.content
    elif db_meeting.transcript:
        minutes_content = db_meeting.transcript
    
    if not minutes_content:
        raise HTTPException(status_code=400, detail="No minutes or transcript available to extract actions from")
    
    # Use DocumentSynthesizer to extract action items
    synthesizer = DocumentSynthesizer(llm_client=llm_service)
    pillar_name = db_meeting.twg.pillar.value if db_meeting.twg else "energy_infrastructure"
    
    import asyncio
    try:
        extracted_items = await asyncio.to_thread(
            synthesizer.extract_action_items,
            minutes_content,
            pillar_name
        )
    except Exception as e:
        return {"extracted_actions": [], "error": str(e), "message": "Failed to extract action items"}
    
    # Auto-create ActionItem records
    # Deduplication: Fetch existing actions first
    try:
        existing_result = await db.execute(select(ActionItem).where(ActionItem.meeting_id == meeting_id))
        existing_actions = existing_result.scalars().all()
        existing_descriptions = {a.description.strip().lower() for a in existing_actions}
    except Exception as e:
        print(f"DEDUPE ERROR: {e}")
        # Fallback to empty to allow proceed
        existing_descriptions = set()

    created_items = []
    for item in extracted_items:
        # Check duplicate
        desc = item.get("description", "").strip()
        if not desc or desc.lower() in existing_descriptions:
            continue

        try:
            from datetime import datetime, timedelta
            
            # Parse due date or default to 2 weeks from now
            due_date = None
            if item.get("due_date"):
                try:
                    due_date = datetime.fromisoformat(item["due_date"])
                except:
                    due_date = datetime.utcnow() + timedelta(days=14)
            else:
                due_date = datetime.utcnow() + timedelta(days=14)
            
            db_action = ActionItem(
                twg_id=db_meeting.twg_id,
                meeting_id=meeting_id,
                description=item.get("description", ""),
                owner_id=current_user.id,  # Default to current user, can be reassigned
                due_date=due_date,
                status=ActionItemStatus.PENDING # Ensure using Enum
            )
            db.add(db_action)
            created_items.append({
                "description": item.get("description"),
                "owner": item.get("owner", "TBD"),
                "due_date": due_date.isoformat() if due_date else None,
                "created": True
            })
        except Exception as e:
            created_items.append({
                "description": item.get("description"),
                "error": str(e),
                "created": False
            })
    
    await db.commit()
    
    return {
        "extracted_actions": extracted_items,
        "created_items": created_items,
        "meeting_id": str(meeting_id),
        "message": f"Created {len([i for i in created_items if i.get('created')])} action items"
    }


# ==================== DOCUMENTS ENDPOINTS ====================

@router.get("/{meeting_id}/documents", response_model=List[dict])
async def get_meeting_documents(
    meeting_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all documents for a specific meeting."""
    result = await db.execute(select(Meeting).where(Meeting.id == meeting_id))
    db_meeting = result.scalar_one_or_none()
    
    if not db_meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
        
    if not has_twg_access(current_user, db_meeting.twg_id):
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Find docs linked to this meeting via metadata_json OR the meeting_id column
    result = await db.execute(
        select(Document).where(
            or_(
                Document.meeting_id == meeting_id,
                and_(
                    Document.twg_id == db_meeting.twg_id,
                    Document.metadata_json.isnot(None),
                )
            )
        )
    )
    documents = result.scalars().all()

    meeting_docs = [
        doc for doc in documents
        if doc.meeting_id == meeting_id
        or (doc.metadata_json and doc.metadata_json.get("meeting_id") == str(meeting_id))
    ]

    return [
        {
            "id": str(doc.id),
            "file_name": doc.file_name,
            "file_type": doc.file_type,
            "document_type": doc.document_type,
            "file_size": doc.metadata_json.get("file_size") if doc.metadata_json else None,
            "created_at": doc.created_at.isoformat()
        }
        for doc in meeting_docs
    ]


@router.post("/{meeting_id}/documents")
async def upload_meeting_document(
    meeting_id: uuid.UUID,
    file: UploadFile = File(...),
    current_user: User = Depends(require_facilitator),
    db: AsyncSession = Depends(get_db)
):
    """Upload a document for a meeting."""
    import os
    import shutil
    
    result = await db.execute(select(Meeting).where(Meeting.id == meeting_id))
    db_meeting = result.scalar_one_or_none()
    
    if not db_meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
        
    if not has_twg_access(current_user, db_meeting.twg_id):
        raise HTTPException(status_code=403, detail="Access denied")
    
    upload_dir = "uploads/meetings"
    try:
        os.makedirs(upload_dir, exist_ok=True)
        
        file_extension = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = os.path.join(upload_dir, unique_filename)
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        file_size = os.path.getsize(file_path)
    except Exception as e:
        import traceback
        print(f"File Upload Error: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
    
    db_document = Document(
        twg_id=db_meeting.twg_id,
        meeting_id=meeting_id, # Link to meeting!
        file_name=file.filename,
        file_path=file_path,
        file_type=file.content_type or "application/octet-stream",
        uploaded_by_id=current_user.id,
        metadata_json={
            "meeting_id": str(meeting_id),
            "file_size": file_size
        }
    )
    
    db.add(db_document)
    await db.commit()
    await db.refresh(db_document)
    
    return {
        "id": str(db_document.id),
        "file_name": db_document.file_name,
        "file_type": db_document.file_type,
        "file_size": file_size,
        "created_at": db_document.created_at.isoformat()
    }


@router.get("/documents/{document_id}/download")
async def download_document(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Download a document."""
    from fastapi.responses import FileResponse
    import os
    
    result = await db.execute(select(Document).where(Document.id == document_id))
    document = result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Check TWG access
    if document.twg_id and not has_twg_access(current_user, document.twg_id):
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Check if file exists
    if not os.path.exists(document.file_path):
        raise HTTPException(status_code=404, detail="File not found on server")
    
    return FileResponse(
        path=document.file_path,
        filename=document.file_name,
        media_type=document.file_type
    )


@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: uuid.UUID,
    current_user: User = Depends(require_facilitator),
    db: AsyncSession = Depends(get_db)
):
    """Delete a document."""
    import os
    
    result = await db.execute(select(Document).where(Document.id == document_id))
    document = result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Check TWG access
    if document.twg_id and not has_twg_access(current_user, document.twg_id):
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Delete file from filesystem
    if os.path.exists(document.file_path):
        os.remove(document.file_path)
    
    # Delete from database
    await db.delete(document)
    await db.commit()
    
    return {"message": "Document deleted successfully"}


# ==================== MEETING PACK ENDPOINTS ====================

@router.post("/{meeting_id}/meeting-pack")
async def compile_meeting_pack(
    meeting_id: uuid.UUID,
    current_user: User = Depends(require_facilitator),
    db: AsyncSession = Depends(get_db)
):
    """
    Compile a meeting pack containing:
    1. Agenda PDF (on summit letterhead)
    2. Previous meeting minutes (if available)
    3. Attached pre-read documents
    
    Returns a ZIP file with all materials.
    """
    import zipfile
    import io
    import os
    from fastapi.responses import StreamingResponse
    from app.services.format_service import format_service
    
    # Get meeting with all related data
    result = await db.execute(
        select(Meeting)
        .options(
            selectinload(Meeting.twg),
            selectinload(Meeting.agenda),
            selectinload(Meeting.minutes)
        )
        .where(Meeting.id == meeting_id)
    )
    db_meeting = result.scalar_one_or_none()
    
    if not db_meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    
    if not has_twg_access(current_user, db_meeting.twg_id):
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Create ZIP buffer
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        files_added = []
        
        # 1. Generate Agenda PDF with letterhead
        if db_meeting.agenda and db_meeting.agenda.content:
            pillar = db_meeting.twg.pillar.value if db_meeting.twg else "energy_infrastructure"
            
            pdf_bytes, pdf_filename = format_service.generate_agenda_pdf(
                twg_pillar=pillar,
                meeting_title=db_meeting.title,
                meeting_date=db_meeting.scheduled_at,
                meeting_location=db_meeting.location or "Virtual",
                agenda_content=db_meeting.agenda.content,
                duration_minutes=db_meeting.duration_minutes
            )
            
            zip_file.writestr(pdf_filename, pdf_bytes)
            files_added.append(pdf_filename)
        
        # 2. Get previous meeting minutes (if any exist for this TWG)
        prev_meetings_result = await db.execute(
            select(Meeting)
            .options(selectinload(Meeting.minutes))
            .where(
                Meeting.twg_id == db_meeting.twg_id,
                Meeting.scheduled_at < db_meeting.scheduled_at,
                Meeting.id != db_meeting.id
            )
            .order_by(Meeting.scheduled_at.desc())
            .limit(1)
        )
        prev_meeting = prev_meetings_result.scalar_one_or_none()
        
        if prev_meeting and prev_meeting.minutes and prev_meeting.minutes.content:
            prev_date = prev_meeting.scheduled_at.strftime('%Y-%m-%d') if prev_meeting.scheduled_at else "previous"
            pillar_short = db_meeting.twg.pillar.value.split("_")[0].title() if db_meeting.twg else "TWG"
            minutes_filename = f"{pillar_short}TWG_Minutes_{prev_date}.txt"
            zip_file.writestr(minutes_filename, prev_meeting.minutes.content)
            files_added.append(minutes_filename)
        
        # 3. Get attached documents for this meeting
        docs_result = await db.execute(
            select(Document).where(Document.twg_id == db_meeting.twg_id)
        )
        documents = docs_result.scalars().all()
        
        for doc in documents[:5]:  # Limit to 5 pre-read docs
            if os.path.exists(doc.file_path):
                with open(doc.file_path, 'rb') as f:
                    zip_file.writestr(f"prereads/{doc.file_name}", f.read())
                    files_added.append(f"prereads/{doc.file_name}")
    
    zip_buffer.seek(0)
    
    # Generate pack filename
    pillar_short = db_meeting.twg.pillar.value.split("_")[0].title() if db_meeting.twg else "TWG"
    date_str = db_meeting.scheduled_at.strftime('%Y-%m-%d') if db_meeting.scheduled_at else "draft"
    pack_filename = f"{pillar_short}TWG_MeetingPack_{date_str}.zip"
    
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={pack_filename}"}
    )


# ==================== NEXT-MEETING AUTOMATION ====================

@router.post("/{meeting_id}/propose-next")
async def propose_next_meeting(
    meeting_id: uuid.UUID,
    current_user: User = Depends(require_facilitator),
    db: AsyncSession = Depends(get_db)
):
    """
    Use AI to propose the next meeting date based on:
    - Current meeting date
    - TWG's typical cadence (defaults to bi-weekly)
    - Avoids weekends
    
    Optionally creates a draft meeting record.
    """
    from datetime import timedelta
    from app.agents.langgraph_base_agent import create_langgraph_agent
    
    # Get current meeting
    result = await db.execute(
        select(Meeting)
        .options(selectinload(Meeting.twg))
        .where(Meeting.id == meeting_id)
    )
    db_meeting = result.scalar_one_or_none()
    
    if not db_meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    
    if not has_twg_access(current_user, db_meeting.twg_id):
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Calculate proposed date (default: 2 weeks from current meeting)
    current_date = db_meeting.scheduled_at
    proposed_date = current_date + timedelta(weeks=2)
    
    # Adjust to avoid weekends (push to Monday if needed)
    while proposed_date.weekday() >= 5:  # 5 = Saturday, 6 = Sunday
        proposed_date += timedelta(days=1)
    
    # Get AI to suggest title and confirm
    pillar = db_meeting.twg.pillar.value if db_meeting.twg else "energy_infrastructure"
    agent_id = pillar.split("_")[0]
    agent = create_langgraph_agent(agent_id=agent_id, session_id=str(meeting_id))
    
    prompt = f"""Based on the previous meeting titled "{db_meeting.title}" for the {pillar.replace('_', ' ').title()} TWG, 
suggest a concise title for the follow-up meeting scheduled for {proposed_date.strftime('%A, %d %B %Y')}.

Return only the meeting title, nothing else. Keep it under 80 characters.
Example: "Energy TWG Session 2: Infrastructure Assessment Review"
"""
    
    suggested_title = agent.chat(prompt).strip().strip('"')
    
    # Create draft meeting (status will be SCHEDULED by default, but not yet finalized)
    draft_meeting = Meeting(
        twg_id=db_meeting.twg_id,
        title=suggested_title or f"Follow-up: {db_meeting.title}",
        scheduled_at=proposed_date,
        duration_minutes=db_meeting.duration_minutes,
        location=db_meeting.location,
        status=MeetingStatus.SCHEDULED,
        meeting_type=db_meeting.meeting_type
    )
    db.add(draft_meeting)
    await db.commit()
    await db.refresh(draft_meeting)
    
    return {
        "proposed_date": proposed_date.isoformat(),
        "proposed_title": suggested_title or f"Follow-up: {db_meeting.title}",
        "draft_meeting_id": str(draft_meeting.id),
        "message": "Draft meeting created. Review and finalize using the scheduling endpoint.",
        "based_on_meeting": str(meeting_id)
    }

@router.websocket("/{meeting_id}/live")
async def live_meeting_websocket(
    websocket: WebSocket,
    meeting_id: str,
    token: Optional[str] = Query(None)
):
    # 1. ALWAYS ACCEPT FIRST
    # This prevents the browser from thinking the connection was rejected
    await websocket.accept()
    
    # 2. Authenticate
    user_id = "anonymous"
    ws_token = token or websocket.query_params.get("token")
    
    if ws_token:
        try:
            payload = verify_token(ws_token, "access")
            if payload:
                user_id = payload.get("sub", "anonymous")
        except Exception:
            pass
    
    print(f"WS LIVE: user={user_id} meeting={meeting_id}")
    
    # Register connection
    if user_id not in ws_manager.active_connections:
        ws_manager.active_connections[user_id] = []
    ws_manager.active_connections[user_id].append(websocket)
    
    # 2. Setup Redis Subscription
    r = None
    pubsub = None
    try:
        # Connect to Redis for real-time stream
        try:
            if settings.REDIS_URL:
                r = redis.from_url(settings.REDIS_URL)
            elif settings.REDIS_HOST:
                r = redis.Redis(
                    host=settings.REDIS_HOST, 
                    port=settings.REDIS_PORT, 
                    db=settings.REDIS_DB, 
                    password=settings.REDIS_PASSWORD
                )
        except Exception as re:
            print(f"WS REDIS CONNECTION FAILED: {re}")
        
        if r:
            pubsub = r.pubsub()
            pubsub.subscribe("live_meeting_stream")
            
        # 3. Handle connection
        await websocket.send_json({
            "type": "connected", 
            "meeting_id": str(meeting_id),
            "status": "ready"
        })

        # 4. Load History from Redis
        if r:
            try:
                # lrange returns bytes, reversed to send oldest first
                history_bytes = r.lrange(f"live_updates:{meeting_id}", 0, -1)
                for msg_bytes in reversed(history_bytes):
                    try:
                        await websocket.send_json(json.loads(msg_bytes.decode('utf-8')))
                    except Exception as je:
                        print(f"WS History Parse error: {je}")
            except Exception as he:
                print(f"WS History load error: {he}")
        
        # Start a background task to listen to Redis
        async def redis_listener():
            if not pubsub:
                return
            try:
                # Use a separate thread for the synchronous pubsub blocking calls
                def get_redis_msg():
                    try:
                        return pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                    except Exception:
                        return None

                while True:
                    message = await asyncio.to_thread(get_redis_msg)
                    if message:
                        try:
                            data = json.loads(message['data'])
                            # Filter by meeting_id to ensure privacy
                            if data.get("meeting_id") == str(meeting_id):
                                await websocket.send_json(data)
                        except Exception as je:
                            print(f"Error parsing Redis message: {je}")
                    await asyncio.sleep(0.1)
            except asyncio.CancelledError:
                pass
            except Exception as e:
                print(f"Redis listener error for {meeting_id}: {e}")

        listener_task = asyncio.create_task(redis_listener())
        
        try:
            while True:
                # Keep connection alive and receive incoming pings/commands
                try:
                    raw_data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                    if raw_data == "ping":
                        await websocket.send_text("pong")
                        continue
                    
                    # Handle JSON commands from Martin Command Center
                    try:
                        msg_json = json.loads(raw_data)
                        if msg_json.get("type") == "live_command":
                            question = msg_json.get("command")
                            print(f"Manual command received for {meeting_id}: {question}")
                            async with get_db_session_context() as db:
                                await VexaService()._handle_live_command(str(meeting_id), question, db)
                        
                        elif msg_json.get("type") == "request_insight":
                            print(f"Manual insight request for {meeting_id}")
                            # Trigger a proactive scan using current transcript
                            async with get_db_session_context() as db:
                                res_m = await db.execute(select(Meeting).where(Meeting.id == meeting_id))
                                meeting_obj = res_m.scalar_one_or_none()
                                if meeting_obj and meeting_obj.transcript:
                                    # Use analyze_live_chunk on the existing transcript (or just a fresh scan)
                                    # For manual, we can treat the whole transcript as a 'chunk' or just the last bit.
                                    # Let's use the last 2000 chars for a quick manual scan.
                                    chunk = meeting_obj.transcript[-2000:]
                                    await VexaService().analyze_live_chunk(str(meeting_id), chunk, db)
                    except Exception as je:
                        # Not a valid JSON or other parse error, ignore or log
                        pass

                except asyncio.TimeoutError:
                    # Heartbeat
                    try:
                        await websocket.send_json({"type": "heartbeat", "status": "alive"})
                    except:
                        break
        except WebSocketDisconnect:
            pass
        finally:
            listener_task.cancel()
            if pubsub:
                try:
                    pubsub.unsubscribe("live_meeting_stream")
                    pubsub.close()
                except:
                    pass
                
    except Exception as e:
        print(f"WebSocket error for meeting {meeting_id}: {e}")
    finally:
        ws_manager.disconnect(websocket, user_id)
# Add these endpoints after upsert_minutes in meetings.py

@router.get("/{meeting_id}/minutes/versions", response_model=List[MinutesVersionRead])
async def list_minutes_versions(
    meeting_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List all versions of meeting minutes.
    Returns versions in reverse chronological order (newest first).
    """
    from app.models.models import Minutes, MinutesVersion
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    
    # Get minutes ID
    result = await db.execute(select(Minutes).where(Minutes.meeting_id == meeting_id))
    db_minutes = result.scalar_one_or_none()
    
    if not db_minutes:
        raise HTTPException(status_code=404, detail="Minutes not found")
    
    # Get all versions
    stmt = (
        select(MinutesVersion)
        .where(MinutesVersion.minutes_id == db_minutes.id)
        .options(selectinload(MinutesVersion.author))
        .order_by(MinutesVersion.version_number.desc())
    )
    result = await db.execute(stmt)
    versions = result.scalars().all()
    
    return versions


@router.get("/{meeting_id}/minutes/versions/{version_number}", response_model=MinutesVersionRead)
async def get_minutes_version(
    meeting_id: uuid.UUID,
    version_number: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific version of meeting minutes.
    """
    from app.models.models import Minutes, MinutesVersion
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    
    # Get minutes ID
    result = await db.execute(select(Minutes).where(Minutes.meeting_id == meeting_id))
    db_minutes = result.scalar_one_or_none()
    
    if not db_minutes:
        raise HTTPException(status_code=404, detail="Minutes not found")
    
    # Get specific version
    stmt = (
        select(MinutesVersion)
        .where(
            MinutesVersion.minutes_id == db_minutes.id,
            MinutesVersion.version_number == version_number
        )
        .options(selectinload(MinutesVersion.author))
    )
    result = await db.execute(stmt)
    version = result.scalar_one_or_none()
    
    if not version:
        raise HTTPException(status_code=404, detail=f"Version {version_number} not found")
    
    return version


@router.post("/{meeting_id}/minutes/versions/{version_number}/restore", response_model=MinutesRead)
async def restore_minutes_version(
    meeting_id: uuid.UUID,
    version_number: int,
    current_user: User = Depends(require_facilitator),
    db: AsyncSession = Depends(get_db)
):
    """
    Restore minutes to a previous version.
    Creates a new version with the content from the specified version.
    """
    from app.models.models import Minutes, MinutesVersion, ActionItem, ActionItemStatus, ActionItemPriority
    from sqlalchemy import select, delete
    from datetime import datetime
    
    # Get minutes
    result = await db.execute(select(Minutes).where(Minutes.meeting_id == meeting_id))
    db_minutes = result.scalar_one_or_none()
    
    if not db_minutes:
        raise HTTPException(status_code=404, detail="Minutes not found")
    
    # Get version to restore
    stmt = select(MinutesVersion).where(
        MinutesVersion.minutes_id == db_minutes.id,
        MinutesVersion.version_number == version_number
    )
    result = await db.execute(stmt)
    version_to_restore = result.scalar_one_or_none()
    
    if not version_to_restore:
        raise HTTPException(status_code=404, detail=f"Version {version_number} not found")
    
    # --- Create snapshot of current state before restoring ---
    # Snapshot Action Items
    stmt = select(ActionItem).where(ActionItem.meeting_id == meeting_id)
    ai_result = await db.execute(stmt)
    current_actions = ai_result.scalars().all()
    
    actions_snapshot = [
        {
            "description": item.description,
            "owner_id": str(item.owner_id) if item.owner_id else None,
            "due_date": item.due_date.isoformat() if item.due_date else None,
            "status": item.status.value if item.status else "pending",
            "priority": item.priority.value if hasattr(item, 'priority') and item.priority else "medium"
        }
        for item in current_actions
    ]

    current_snapshot = MinutesVersion(
        minutes_id=db_minutes.id,
        version_number=db_minutes.current_version,
        content=db_minutes.content,
        key_decisions=db_minutes.key_decisions,
        change_summary=f"Auto-saved before restoring to v{version_number}",
        action_items_snapshot=actions_snapshot,
        created_by=current_user.id,
        created_at=datetime.utcnow()
    )
    db.add(current_snapshot)
    
    # --- Restore content using snapshot if available ---
    db_minutes.content = version_to_restore.content
    db_minutes.key_decisions = version_to_restore.key_decisions
    
    # Restore Action Items if snapshot exists
    if version_to_restore.action_items_snapshot:
        # Fetch TWG ID from meeting
        from app.models.models import Meeting
        m_result = await db.execute(select(Meeting.twg_id).where(Meeting.id == meeting_id))
        twg_id = m_result.scalar_one()

        # Delete current items
        await db.execute(delete(ActionItem).where(ActionItem.meeting_id == meeting_id))
        
        # Recreate from snapshot
        for item in version_to_restore.action_items_snapshot:
             # Handle Enums safely
            try:
                status_enum = ActionItemStatus(item.get("status", "pending"))
            except:
                status_enum = ActionItemStatus.PENDING
                
            try:
                priority_enum = ActionItemPriority(item.get("priority", "medium"))
            except:
                priority_enum = ActionItemPriority.MEDIUM

            new_action = ActionItem(
                meeting_id=meeting_id,
                twg_id=twg_id,
                description=item["description"],
                owner_id=uuid.UUID(item["owner_id"]) if item["owner_id"] else None,
                due_date=datetime.fromisoformat(item["due_date"]).date() if item["due_date"] else None,
                status=status_enum,
                priority=priority_enum
            )
            db.add(new_action)
            
    db_minutes.current_version += 1
    db_minutes.last_edited_by = current_user.id
    db_minutes.last_edited_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(db_minutes)
    
    return db_minutes
