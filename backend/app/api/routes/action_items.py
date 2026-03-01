from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from datetime import datetime, timedelta
import uuid
import logging

from app.core.database import get_db
from app.models.models import ActionItem, ActionItemStatus, User, UserRole, NotificationType
from app.schemas.schemas import ActionItemCreate, ActionItemUpdate, ActionItemRead
from app.api.deps import get_current_active_user, require_facilitator, has_twg_access
from app.core.action_item_constants import VALID_STATUS_TRANSITIONS
from app.services.notification_service import create_notification

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/action-items", tags=["Action Items"])

@router.post("/", response_model=ActionItemRead, status_code=status.HTTP_201_CREATED)
async def create_action_item(
    item_in: ActionItemCreate,
    current_user: User = Depends(require_facilitator),
    db: AsyncSession = Depends(get_db)
):
    """
    Create/Assign an action item.

    Requires FACILITATOR or ADMIN role.
    Must have access to the TWG.
    """
    if not has_twg_access(current_user, item_in.twg_id):
        raise HTTPException(status_code=403, detail="You do not have access to this TWG")

    db_item = ActionItem(**item_in.model_dump())
    db.add(db_item)
    await db.commit()
    await db.refresh(db_item)

    # Notify the assigned owner (if not self-assigning)
    if item_in.owner_id != current_user.id:
        try:
            await create_notification(
                db=db,
                user_id=item_in.owner_id,
                type=NotificationType.TASK,
                title="New Action Item Assigned",
                content=f"You have been assigned: {db_item.description[:100]}",
                link="/actions"
            )
        except Exception as e:
            logger.warning(f"Failed to send assignment notification: {e}")

    return db_item

@router.get("/summary")
async def get_action_items_summary(
    twg_id: Optional[uuid.UUID] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get summary stats for action items.
    Returns counts by status and items due this week.
    """
    base_query = select(ActionItem)

    if twg_id:
        if current_user.role not in [UserRole.ADMIN, UserRole.SECRETARIAT_LEAD] and not has_twg_access(current_user, twg_id):
            raise HTTPException(status_code=403, detail="Access denied to this TWG")
        base_query = base_query.where(ActionItem.twg_id == twg_id)
    elif current_user.role not in [UserRole.ADMIN, UserRole.SECRETARIAT_LEAD]:
        user_twg_ids = [twg.id for twg in current_user.twgs]
        base_query = base_query.where(ActionItem.twg_id.in_(user_twg_ids))

    result = await db.execute(base_query)
    items = result.scalars().all()

    now = datetime.utcnow()
    end_of_week = now + timedelta(days=(6 - now.weekday()))

    counts = {"pending": 0, "in_progress": 0, "completed": 0, "overdue": 0}
    due_this_week = 0
    completed_this_week = 0

    for item in items:
        status_key = item.status.value.lower()
        if status_key in counts:
            counts[status_key] += 1
        if item.due_date and item.due_date <= end_of_week and item.status not in (ActionItemStatus.COMPLETED,):
            due_this_week += 1
        if item.status == ActionItemStatus.COMPLETED and item.completed_at and item.completed_at >= (now - timedelta(days=7)):
            completed_this_week += 1

    return {
        **counts,
        "due_this_week": due_this_week,
        "completed_this_week": completed_this_week,
    }

@router.get("/", response_model=List[ActionItemRead])
async def list_action_items(
    skip: int = 0,
    limit: int = 100,
    twg_id: Optional[uuid.UUID] = None,
    mine_only: bool = False,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List action items.

    - mine_only=true: Returns items owned by current user.
    - twg_id: Filter by TWG (Access checked).
    - status: Filter by status (PENDING, IN_PROGRESS, COMPLETED, OVERDUE).
    """
    query = select(ActionItem).offset(skip).limit(limit)

    if mine_only:
        query = query.where(ActionItem.owner_id == current_user.id)

    if twg_id:
         query = query.where(ActionItem.twg_id == twg_id)
         if current_user.role not in [UserRole.ADMIN, UserRole.SECRETARIAT_LEAD] and not has_twg_access(current_user, twg_id):
              raise HTTPException(status_code=403, detail="Access denied to this TWG's items")
    elif not mine_only and current_user.role not in [UserRole.ADMIN, UserRole.SECRETARIAT_LEAD]:
        user_twg_ids = [twg.id for twg in current_user.twgs]
        query = query.where(ActionItem.twg_id.in_(user_twg_ids))

    if status:
        try:
            status_enum = ActionItemStatus(status.upper())
            query = query.where(ActionItem.status == status_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

    query = query.order_by(ActionItem.created_at.desc())

    result = await db.execute(query)
    return result.scalars().all()

@router.patch("/{item_id}", response_model=ActionItemRead)
async def update_action_item(
    item_id: uuid.UUID,
    item_in: ActionItemUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update action item with status transition validation.

    Owner can update their own items.
    Facilitator/Admin can update any item in their TWG.
    COMPLETED is a terminal state — cannot transition out of it.
    """
    result = await db.execute(select(ActionItem).where(ActionItem.id == item_id))
    db_item = result.scalar_one_or_none()
    if not db_item:
        raise HTTPException(status_code=404, detail="Action item not found")

    # Permission check
    is_owner = db_item.owner_id == current_user.id
    is_facilitator = current_user.role in [UserRole.TWG_FACILITATOR, UserRole.ADMIN, UserRole.SECRETARIAT_LEAD] and has_twg_access(current_user, db_item.twg_id)

    if not (is_owner or is_facilitator):
        raise HTTPException(status_code=403, detail="Not authorized to update this item")

    old_status = db_item.status

    # Status transition validation
    if item_in.status is not None and item_in.status != old_status:
        allowed = VALID_STATUS_TRANSITIONS.get(old_status, set())
        if item_in.status not in allowed:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid status transition: {old_status.value} → {item_in.status.value}"
            )

    update_data = item_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_item, key, value)

    # Auto-set completed_at when transitioning to COMPLETED
    if item_in.status == ActionItemStatus.COMPLETED and old_status != ActionItemStatus.COMPLETED:
        db_item.completed_at = datetime.utcnow()

    await db.commit()
    await db.refresh(db_item)

    # Notify owner on status change
    if item_in.status is not None and item_in.status != old_status:
        try:
            await create_notification(
                db=db,
                user_id=db_item.owner_id,
                type=NotificationType.TASK,
                title=f"Action Item {item_in.status.value.replace('_', ' ').title()}",
                content=f"'{db_item.description[:80]}' status changed to {item_in.status.value}",
                link="/actions"
            )
        except Exception as e:
            logger.warning(f"Failed to send status change notification: {e}")

    return db_item


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_action_item(
    item_id: uuid.UUID,
    current_user: User = Depends(require_facilitator),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete an action item.
    """
    result = await db.execute(select(ActionItem).where(ActionItem.id == item_id))
    db_item = result.scalar_one_or_none()

    if not db_item:
        raise HTTPException(status_code=404, detail="Action item not found")

    if not has_twg_access(current_user, db_item.twg_id):
        raise HTTPException(status_code=403, detail="Access denied")

    await db.delete(db_item)
    await db.commit()
    return None
