from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
import uuid

from app.core.database import get_db
from app.models.models import Meeting, Agenda, Minutes, User, UserRole, MinutesStatus
from app.schemas.schemas import MeetingCreate, MeetingRead, MeetingUpdate, MinutesCreate, MinutesUpdate, MinutesRead
from app.api.deps import get_current_active_user, require_facilitator, require_twg_access, has_twg_access
from app.services.email_service import email_service
from sqlalchemy.orm import selectinload

router = APIRouter(prefix="/meetings", tags=["Meetings"])

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
    # Check if facilitator has access to this TWG
    if not has_twg_access(current_user, meeting_in.twg_id):
        raise HTTPException(status_code=403, detail="You do not have access to manage meetings for this TWG")

    db_meeting = Meeting(**meeting_in.model_dump())
    db.add(db_meeting)
    await db.commit()
    await db.refresh(db_meeting)
    return db_meeting

@router.get("/", response_model=List[MeetingRead])
async def list_meetings(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List all meetings visible to the user.
    """
    # If admin, show all. If member, show only their TWG meetings.
    query = select(Meeting).offset(skip).limit(limit)
    
    if current_user.role != UserRole.ADMIN:
        # Get IDs of TWGs user belongs to
        user_twg_ids = [twg.id for twg in current_user.twgs]
        query = query.where(Meeting.twg_id.in_(user_twg_ids))
        
    result = await db.execute(query)
    return result.scalars().all()

@router.get("/{meeting_id}", response_model=MeetingRead)
async def get_meeting(
    meeting_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get meeting details.
    """
    result = await db.execute(select(Meeting).where(Meeting.id == meeting_id))
    db_meeting = result.scalar_one_or_none()
    if not db_meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    
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
    result = await db.execute(select(Meeting).where(Meeting.id == meeting_id))
    db_meeting = result.scalar_one_or_none()
    
    if not db_meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
        
    if not has_twg_access(current_user, db_meeting.twg_id):
        raise HTTPException(status_code=403, detail="Access denied")
        
    update_data = meeting_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_meeting, key, value)
        
    await db.commit()
    await db.refresh(db_meeting)
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
    """
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
        # Update
        update_data = minutes_in.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_minutes, key, value)
    else:
        # Create
        if not minutes_in.content:
             raise HTTPException(status_code=400, detail="Content required for creating minutes")
             
        minutes_data = minutes_in.model_dump(exclude_unset=True)
        # partial update schema used for creation, ensure defaults or required
        db_minutes = Minutes(meeting_id=meeting_id, **minutes_data)
        db.add(db_minutes)
        
    await db.commit()
    await db.refresh(db_minutes)
    return db_minutes

@router.post("/{meeting_id}/schedule", status_code=status.HTTP_200_OK)
async def schedule_meeting_trigger(
    meeting_id: uuid.UUID,
    current_user: User = Depends(require_facilitator),
    db: AsyncSession = Depends(get_db)
):
    """
    Finalize and schedule a meeting. 
    Triggers automated email invitations and calendar invites.
    """
    # Verify meeting exists and access rights
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

    # Change status
    db_meeting.status = MeetingStatus.SCHEDULED
    
    # Send emails
    participant_emails = [u.email for u in db_meeting.participants]
    
    try:
        await email_service.send_meeting_invite(
            to_emails=participant_emails,
            subject=f"INVITATION: {db_meeting.title}",
            template_name="meeting_invite.html",
            template_context={
                "user_name": "Valued Participant", # Simplified
                "meeting_title": db_meeting.title,
                "meeting_date": db_meeting.scheduled_at.strftime("%Y-%m-%d"),
                "meeting_time": db_meeting.scheduled_at.strftime("%H:%M UTC"),
                "location": db_meeting.location or "Virtual",
                "pillar_name": db_meeting.twg.pillar.value,
                "portal_url": "https://summit.ecowas.int/twg/portal" # Placeholder
            },
            meeting_details={
                "title": db_meeting.title,
                "start_time": db_meeting.scheduled_at,
                "duration": db_meeting.duration_minutes,
                "location": db_meeting.location
            }
        )
    except Exception as e:
        # Log error but don't fail the whole request? 
        # Actually, for scheduling, we want to know if it failed.
        raise HTTPException(status_code=500, detail=f"Failed to send invitations: {str(e)}")

    await db.commit()
    return {"status": "successfully scheduled", "emails_sent": len(participant_emails)}
