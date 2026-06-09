import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.core.database import get_db
from app.api.deps import get_current_active_user
from app.models.models import User, Reminder
from app.schemas.schemas import ReminderCreate, ReminderRead

router = APIRouter(prefix="/reminders", tags=["Reminders"])


@router.get("/", response_model=List[ReminderRead])
async def list_my_reminders(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Reminder).where(Reminder.user_id == current_user.id).order_by(Reminder.remind_at)
    )
    return result.scalars().all()


@router.post("/", response_model=ReminderRead, status_code=201)
async def create_my_reminder(
    body: ReminderCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    reminder = Reminder(
        user_id=current_user.id,
        message=body.message,
        remind_at=body.remind_at,
        meeting_id=body.meeting_id,
        is_sent=False,
    )
    db.add(reminder)
    await db.commit()
    await db.refresh(reminder)
    return reminder


@router.delete("/{reminder_id}", status_code=204)
async def delete_my_reminder(
    reminder_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Reminder).where(Reminder.id == reminder_id, Reminder.user_id == current_user.id)
    )
    reminder = result.scalar_one_or_none()
    if reminder is None:
        raise HTTPException(status_code=404, detail="Reminder not found")
    await db.delete(reminder)
    await db.commit()
