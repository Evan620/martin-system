from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
import uuid

from backend.app.core.database import get_db
from backend.app.models.models import Meeting, Agenda, Minutes
from backend.app.schemas.schemas import MeetingCreate, MeetingRead

router = APIRouter()

@router.post("/", response_model=MeetingRead, status_code=status.HTTP_201_CREATED)
async def create_meeting(meeting_in: MeetingCreate, db: AsyncSession = Depends(get_db)):
    db_meeting = Meeting(**meeting_in.model_dump())
    db.add(db_meeting)
    await db.commit()
    await db.refresh(db_meeting)
    return db_meeting

@router.get("/", response_model=List[MeetingRead])
async def list_meetings(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Meeting).offset(skip).limit(limit))
    return result.scalars().all()

@router.get("/{meeting_id}", response_model=MeetingRead)
async def get_meeting(meeting_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Meeting).where(Meeting.id == meeting_id))
    db_meeting = result.scalar_one_or_none()
    if not db_meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return db_meeting

@router.get("/{meeting_id}/agenda")
async def get_meeting_agenda(meeting_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Agenda).where(Agenda.meeting_id == meeting_id))
    db_agenda = result.scalar_one_or_none()
    if not db_agenda:
        raise HTTPException(status_code=404, detail="Agenda not found")
    return db_agenda

@router.get("/{meeting_id}/minutes")
async def get_meeting_minutes(meeting_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Minutes).where(Minutes.meeting_id == meeting_id))
    db_minutes = result.scalar_one_or_none()
    if not db_minutes:
        raise HTTPException(status_code=404, detail="Minutes not found")
    return db_minutes
