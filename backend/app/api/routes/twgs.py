from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
import uuid

from backend.app.core.database import get_db
from backend.app.models.models import TWG, User, UserRole
from backend.app.schemas.schemas import TWGCreate, TWGRead, TWGUpdate
from backend.app.api.deps import get_current_active_user, require_admin, require_facilitator

router = APIRouter(prefix="/twgs", tags=["TWGs"])

@router.post("/", response_model=TWGRead, status_code=status.HTTP_201_CREATED)
async def create_twg(
    twg_in: TWGCreate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new TWG.
    
    Requires ADMIN role.
    """
    db_twg = TWG(**twg_in.model_dump())
    db.add(db_twg)
    await db.commit()
    await db.refresh(db_twg)
    return db_twg

@router.get("/", response_model=List[TWGRead])
async def list_twgs(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List all TWGs.
    
    Accessible to all active users.
    """
    result = await db.execute(select(TWG).offset(skip).limit(limit))
    return result.scalars().all()

@router.get("/{twg_id}", response_model=TWGRead)
async def get_twg(
    twg_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get TWG details by ID.
    
    Accessible to all active users.
    """
    result = await db.execute(select(TWG).where(TWG.id == twg_id))
    db_twg = result.scalar_one_or_none()
    if not db_twg:
        raise HTTPException(status_code=404, detail="TWG not found")
    return db_twg

@router.patch("/{twg_id}", response_model=TWGRead)
async def update_twg(
    twg_id: uuid.UUID,
    twg_in: TWGUpdate,
    current_user: User = Depends(require_facilitator),
    db: AsyncSession = Depends(get_db)
):
    """
    Update TWG details.
    
    Requires ADMIN or FACILITATOR role.
    If FACILITATOR, ideally should check if assigned to this TWG (logic can be added).
    """
    result = await db.execute(select(TWG).where(TWG.id == twg_id))
    db_twg = result.scalar_one_or_none()
    if not db_twg:
        raise HTTPException(status_code=404, detail="TWG not found")
    
    # Additional check: If facilitator, ensure they are the lead?
    # For now, allow generic facilitator access as per simplified reqs.
    # Admins can edit anything.
    
    update_data = twg_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_twg, key, value)
    
    await db.commit()
    await db.refresh(db_twg)
    return db_twg
