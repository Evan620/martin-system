from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List, Optional
import uuid

from backend.app.core.database import get_db
from backend.app.models.models import Project, User, UserRole
from backend.app.schemas.schemas import ProjectCreate, ProjectRead
from backend.app.api.deps import get_current_active_user, require_facilitator, has_twg_access

router = APIRouter(prefix="/projects", tags=["Projects"])

@router.post("/", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_in: ProjectCreate,
    current_user: User = Depends(require_facilitator),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new investment project.
    
    Requires FACILITATOR or ADMIN role.
    User must have access to the TWG.
    """
    if not has_twg_access(current_user, project_in.twg_id):
        raise HTTPException(status_code=403, detail="You do not have access to this TWG")

    db_project = Project(**project_in.model_dump())
    db.add(db_project)
    await db.commit()
    await db.refresh(db_project)
    return db_project

@router.get("/", response_model=List[ProjectRead])
async def list_projects(
    skip: int = 0,
    limit: int = 100,
    twg_id: uuid.UUID = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    sort_by: Optional[str] = None # "score_desc", "date_desc"
):
    """
    List projects. Optional filter by TWG.
    Optional sorting by readiness_score (Top 20 logic).
    """
    query = select(Project).offset(skip).limit(limit)
    
    if twg_id:
        query = query.where(Project.twg_id == twg_id)
    
    if current_user.role != UserRole.ADMIN:
        # Filter to only show projects from TWGs the user belongs to
        user_twg_ids = [twg.id for twg in current_user.twgs]
        if twg_id:
            if twg_id not in user_twg_ids:
                 raise HTTPException(status_code=403, detail="Access denied to this TWG's projects")
        else:
            query = query.where(Project.twg_id.in_(user_twg_ids))
            
    # Sorting logic
    if sort_by == "score_desc":
        query = query.order_by(desc(Project.readiness_score))
    elif sort_by == "date_desc":
        query = query.order_by(desc(Project.created_at))
            
    result = await db.execute(query)
    return result.scalars().all()

@router.get("/{project_id}", response_model=ProjectRead)
async def get_project(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get project details.
    """
    result = await db.execute(select(Project).where(Project.id == project_id))
    db_project = result.scalar_one_or_none()
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    if not has_twg_access(current_user, db_project.twg_id):
         raise HTTPException(status_code=403, detail="Access denied")
         
    return db_project

@router.patch("/{project_id}", response_model=ProjectRead)
async def update_project(
    project_id: uuid.UUID,
    project_in: ProjectCreate, # Using Create schema for now, ideally Update schema
    current_user: User = Depends(require_facilitator),
    db: AsyncSession = Depends(get_db)
):
    """
    Update a project.
    """
    result = await db.execute(select(Project).where(Project.id == project_id))
    db_project = result.scalar_one_or_none()
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    if not has_twg_access(current_user, db_project.twg_id):
        raise HTTPException(status_code=403, detail="Access denied")
    
    update_data = project_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_project, key, value)
        
    await db.commit()
    await db.refresh(db_project)
    return db_project

@router.put("/{project_id}/score", response_model=ProjectRead)
async def update_project_score(
    project_id: uuid.UUID,
    score: float,
    current_user: User = Depends(require_facilitator),
    db: AsyncSession = Depends(get_db)
):
    """
    Update the readiness score of a project (AfCEN algorithm result).
    """
    result = await db.execute(select(Project).where(Project.id == project_id))
    db_project = result.scalar_one_or_none()
    
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    if not has_twg_access(current_user, db_project.twg_id):
        raise HTTPException(status_code=403, detail="Access denied")
        
    db_project.readiness_score = score
    
    # Auto-update status based on score thresholds (Example logic)
    if score >= 80.0:
        from backend.app.models.models import ProjectStatus
        db_project.status = ProjectStatus.BANKABLE
        
    await db.commit()
    await db.refresh(db_project)
    return db_project
