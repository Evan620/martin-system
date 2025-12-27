from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List, Optional
import uuid

from app.core.database import get_db
from app.models.models import AuditLog, User
from app.schemas.schemas import AuditLogRead
from app.api.deps import require_admin

router = APIRouter(prefix="/audit-logs", tags=["Audit Logs"])

@router.get("/", response_model=List[AuditLogRead])
async def list_audit_logs(
    skip: int = 0,
    limit: int = 100,
    user_id: Optional[uuid.UUID] = None,
    resource_type: Optional[str] = None,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    List system audit logs.
    
    Requires ADMIN role.
    """
    query = select(AuditLog).order_by(desc(AuditLog.created_at)).offset(skip).limit(limit)
    
    if user_id:
        query = query.where(AuditLog.user_id == user_id)
    if resource_type:
        query = query.where(AuditLog.resource_type == resource_type)
        
    result = await db.execute(query)
    return result.scalars().all()

async def log_action(
    db: AsyncSession,
    user_id: Optional[uuid.UUID],
    action: str,
    resource_type: str,
    resource_id: Optional[uuid.UUID] = None,
    details: Optional[dict] = None,
    request: Request = None
):
    """
    Utility function to log an action.
    """
    ip_address = None
    if request:
        ip_address = request.client.host
        
    db_log = AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details,
        ip_address=ip_address
    )
    db.add(db_log)
    await db.commit()
    return db_log
