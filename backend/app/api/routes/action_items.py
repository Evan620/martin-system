from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
import uuid

from backend.app.core.database import get_db
from backend.app.models.models import ActionItem, User, UserRole
from backend.app.schemas.schemas import ActionItemCreate, ActionItemRead
from backend.app.api.deps import get_current_active_user, require_facilitator, has_twg_access

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

    # verify owner exists? (Skipping for now, FK constraint will handle it but less gracefully)
    
    db_item = ActionItem(**item_in.model_dump())
    db.add(db_item)
    await db.commit()
    await db.refresh(db_item)
    return db_item

@router.get("/", response_model=List[ActionItemRead])
async def list_action_items(
    skip: int = 0,
    limit: int = 100,
    twg_id: uuid.UUID = None,
    mine_only: bool = False,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List action items.
    
    - mine_only=true: Returns items owned by current user.
    - twg_id: Filter by TWG (Access checked).
    """
    query = select(ActionItem).offset(skip).limit(limit)
    
    if mine_only:
        query = query.where(ActionItem.owner_id == current_user.id)
    
    if twg_id:
         query = query.where(ActionItem.twg_id == twg_id)
         # Access check
         if current_user.role != UserRole.ADMIN and not has_twg_access(current_user, twg_id):
              raise HTTPException(status_code=403, detail="Access denied to this TWG's items")
    elif not mine_only and current_user.role != UserRole.ADMIN:
        # If not filtering by "mine" and not admin, must limit to TWGs user is in
        user_twg_ids = [twg.id for twg in current_user.twgs]
        query = query.where(ActionItem.twg_id.in_(user_twg_ids))

    result = await db.execute(query)
    return result.scalars().all()

@router.patch("/{item_id}", response_model=ActionItemRead)
async def update_action_item_status(
    item_id: uuid.UUID,
    item_in: ActionItemCreate, # Ideally valid update schema
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update action item.
    
    Owner can update their own items.
    Facilitator/Admin can update any item in their TWG.
    """
    result = await db.execute(select(ActionItem).where(ActionItem.id == item_id))
    db_item = result.scalar_one_or_none()
    if not db_item:
        raise HTTPException(status_code=404, detail="Action item not found")
        
    # Permission check
    is_owner = db_item.owner_id == current_user.id
    is_facilitator = current_user.role in [UserRole.TWG_FACILITATOR, UserRole.ADMIN] and has_twg_access(current_user, db_item.twg_id)
    
    if not (is_owner or is_facilitator):
        raise HTTPException(status_code=403, detail="Not authorized to update this item")
    
    # Check fields being updated
    # Members (owners) should only update status? 
    # For simplicity, allowing full update based on schema, but in practice restrict.
    
    update_data = item_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_item, key, value)
        
    await db.commit()
    await db.refresh(db_item)
    return db_item
