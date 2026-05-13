from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Any, Dict
import uuid
from datetime import datetime

from app.core.database import get_db_session_context
from app.api.deps import get_current_user
from app.models.models import User, Conflict, ConflictType, Project, ProjectStatus, ConflictStatus, ConflictSeverity
from pydantic import BaseModel

router = APIRouter(prefix="/conflicts", tags=["conflicts"])

# --- Schemas ---

class ConflictResolutionRequest(BaseModel):
    action: str  # MERGE_PROJECTS, ADJUST_TIMELINE, DISMISS, RESOLVE
    project_id: Optional[str] = None
    keep_project_id: Optional[str] = None
    merge_project_id: Optional[str] = None
    new_start_date: Optional[str] = None
    reason: Optional[str] = None

class ConflictResponse(BaseModel):
    id: uuid.UUID
    conflict_type: ConflictType
    severity: ConflictSeverity
    description: str
    agents_involved: List[str]
    conflicting_positions: Dict[str, Any]
    metadata_json: Optional[Dict[str, Any]]
    status: ConflictStatus
    detected_at: datetime
    
    class Config:
        from_attributes = True

# --- Routes ---

@router.get("/project-dependencies", response_model=List[ConflictResponse])
async def get_project_dependencies(
    current_user: User = Depends(get_current_user)
):
    """Get all active dependency conflicts"""
    async with get_db_session_context() as db:
        result = await db.execute(
            select(Conflict).where(
                and_(
                    Conflict.conflict_type == ConflictType.PROJECT_DEPENDENCY_CONFLICT,
                    Conflict.status.in_([ConflictStatus.DETECTED, ConflictStatus.NEGOTIATING, ConflictStatus.ESCALATED])
                )
            ).order_by(Conflict.detected_at.desc())
        )
        return result.scalars().all()

@router.get("/duplicates", response_model=List[ConflictResponse])
async def get_duplicate_projects(
    current_user: User = Depends(get_current_user)
):
    """Get all potential duplicate projects"""
    async with get_db_session_context() as db:
        result = await db.execute(
            select(Conflict).where(
                and_(
                    Conflict.conflict_type == ConflictType.DUPLICATE_PROJECT_CONFLICT,
                    Conflict.status.in_([ConflictStatus.DETECTED, ConflictStatus.ESCALATED])
                )
            ).order_by(Conflict.detected_at.desc())
        )
        return result.scalars().all()

@router.post("/{conflict_id}/resolve")
async def resolve_conflict(
    conflict_id: str,
    resolution: ConflictResolutionRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Manually resolve a conflict. 
    Handles basic project merges (marking one as merged/cancelled) and timeline adjustments.
    """
    async with get_db_session_context() as db:
        # Fetch conflict
        result = await db.execute(select(Conflict).where(Conflict.id == uuid.UUID(conflict_id)))
        conflict = result.scalars().first()
        
        if not conflict:
            raise HTTPException(status_code=404, detail="Conflict not found")
            
        # Execute Resolution Logic
        if resolution.action == "MERGE_PROJECTS":
            if not resolution.keep_project_id or not resolution.merge_project_id:
                raise HTTPException(status_code=400, detail="Missing keep_project_id or merge_project_id")
            
            # Fetch projects
            keep_res = await db.execute(select(Project).where(Project.id == uuid.UUID(resolution.keep_project_id)))
            merge_res = await db.execute(select(Project).where(Project.id == uuid.UUID(resolution.merge_project_id)))
            keep_proj = keep_res.scalars().first()
            merge_proj = merge_res.scalars().first()
            
            if not keep_proj or not merge_proj:
                raise HTTPException(status_code=404, detail="Projects not found")
                
            # Perform Merge (Basic Prototype)
            # 1. Update Merge Project status
            merge_proj.status = ProjectStatus.ARCHIVED
            # Archived = merged/superseded; metadata captures the merge target
            
            merge_proj.metadata_json = {
                **(merge_proj.metadata_json or {}),
                "merged_into": str(keep_proj.id),
                "merged_at": datetime.utcnow().isoformat(),
                "merged_by": str(current_user.id)
            }
            
            # 2. Update Keep Project description/metadata
            keep_proj.description += f"\n\n[Merged Scope from {merge_proj.name}]: {merge_proj.description}"
            keep_proj.metadata_json = {
                **(keep_proj.metadata_json or {}),
                "absorbed_projects": (keep_proj.metadata_json or {}).get("absorbed_projects", []) + [str(merge_proj.id)]
            }
            
            # 3. Resolve Conflict
            conflict.status = ConflictStatus.RESOLVED
            conflict.resolution_log = (conflict.resolution_log or []) + [{
                "action": "MERGE_PROJECTS",
                "kept": str(keep_proj.id),
                "merged": str(merge_proj.id),
                "by": str(current_user.id),
                "at": datetime.utcnow().isoformat()
            }]
            
        elif resolution.action == "ADJUST_TIMELINE":
            if not resolution.project_id or not resolution.new_start_date:
                raise HTTPException(status_code=400, detail="Missing project_id or new_start_date")
                
            proj_res = await db.execute(select(Project).where(Project.id == uuid.UUID(resolution.project_id)))
            project = proj_res.scalars().first()
            
            if not project:
                raise HTTPException(status_code=404, detail="Project not found")
                
            # Update Timeline (Metadata for now)
            project.metadata_json = {
                **(project.metadata_json or {}),
                "planned_start": resolution.new_start_date,
                "schedule_adjustment_reason": resolution.reason
            }
            
            conflict.status = ConflictStatus.RESOLVED
            conflict.resolution_log = (conflict.resolution_log or []) + [{
                "action": "ADJUST_TIMELINE",
                "project": str(project.id),
                "new_date": resolution.new_start_date,
                "by": str(current_user.id)
            }]
            
        elif resolution.action == "DISMISS":
            conflict.status = ConflictStatus.DISMISSED
             
        elif resolution.action == "RESOLVE":
             conflict.status = ConflictStatus.RESOLVED
             
        else:
            raise HTTPException(status_code=400, detail="Invalid action")
            
        # Common updates
        conflict.resolved_at = datetime.utcnow()
        db.add(conflict)
        await db.commit()
        
        return {"status": "success", "conflict_status": conflict.status}
