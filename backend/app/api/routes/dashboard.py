from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, or_, and_
from typing import List, Dict, Any
import datetime

from app.core.database import get_db
from app.models.models import Meeting, ActionItem, Document, TWG, MeetingStatus, ActionItemStatus
from app.api.deps import get_current_active_user
# from app.components.audit import log_audit # Optional

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

@router.get("/stats", response_model=Dict[str, Any])
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    Get aggregated statistics for the Command Center dashboard.
    """
    # 1. Meeting Stats
    total_meetings_res = await db.execute(select(func.count(Meeting.id)))
    total_meetings = total_meetings_res.scalar() or 0
    
    completed_res = await db.execute(select(func.count(Meeting.id)).where(Meeting.status == MeetingStatus.COMPLETED))
    completed_meetings = completed_res.scalar() or 0
    
    upcoming_res = await db.execute(select(func.count(Meeting.id)).where(Meeting.status == MeetingStatus.SCHEDULED))
    upcoming_meetings = upcoming_res.scalar() or 0
    
    # 2. Action Item Stats
    total_items_res = await db.execute(select(func.count(ActionItem.id)))
    total_items = total_items_res.scalar() or 0
    
    completed_items_res = await db.execute(select(func.count(ActionItem.id)).where(ActionItem.status == ActionItemStatus.COMPLETED))
    completed_items = completed_items_res.scalar() or 0
    
    overdue_items_res = await db.execute(select(func.count(ActionItem.id)).where(ActionItem.status == ActionItemStatus.OVERDUE))
    overdue_items = overdue_items_res.scalar() or 0
    
    # 3. Document Stats
    total_docs_res = await db.execute(select(func.count(Document.id)))
    total_docs = total_docs_res.scalar() or 0
    
    # 4. TWG Summary
    twgs_res = await db.execute(select(TWG))
    twgs = twgs_res.scalars().all()
    twg_stats = []
    
    cutoff_date = datetime.datetime.utcnow() - datetime.timedelta(days=14)
    
    for twg in twgs:
        # Check for activity (last meeting)
        last_meeting_res = await db.execute(
            select(Meeting)
            .where(
                Meeting.twg_id == twg.id,
                Meeting.status == MeetingStatus.COMPLETED
            )
            .order_by(desc(Meeting.scheduled_at))
            .limit(1)
        )
        last_meeting = last_meeting_res.scalar_one_or_none()
        
        is_stalled = False
        if last_meeting and last_meeting.scheduled_at < cutoff_date:
            is_stalled = True
        elif not last_meeting:
            # Check if any future meeting exists
            future_meeting_res = await db.execute(
                select(Meeting)
                .where(
                    Meeting.twg_id == twg.id,
                    Meeting.status == MeetingStatus.SCHEDULED
                )
                .limit(1)
            )
            if not future_meeting_res.scalar_one_or_none():
                 is_stalled = True # No past meetings and no future meetings
            
        pending_items_res = await db.execute(
            select(func.count(ActionItem.id))
            .where(
                ActionItem.twg_id == twg.id,
                ActionItem.status == ActionItemStatus.PENDING
            )
        )
        pending_items = pending_items_res.scalar() or 0
        
        twg_stats.append({
            "name": twg.name,
            "status": "stalled" if is_stalled else "active",
            "pending_items": pending_items,
            "last_active": last_meeting.scheduled_at if last_meeting else None
        })
        
    return {
        "meetings": {
            "total": total_meetings,
            "completed": completed_meetings,
            "upcoming": upcoming_meetings
        },
        "action_items": {
            "total": total_items,
            "completed": completed_items,
            "overdue": overdue_items,
            "completion_rate": round(completed_items / total_items * 100, 1) if total_items > 0 else 0
        },
        "documents": {
            "total": total_docs
        },
        "twg_health": twg_stats
    }

@router.get("/timeline", response_model=List[Dict[str, Any]])
async def get_global_timeline(
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    Get a unified timeline of recent and upcoming events.
    """
    # Fetch upcoming meetings
    meetings_res = await db.execute(
        select(Meeting)
        .options() # Add eager loading if needed, e.g. selectinload(Meeting.twg)
        .order_by(desc(Meeting.scheduled_at))
        .limit(limit)
    )
    meetings = meetings_res.scalars().all()
    
    # IMPORTANT: We need eager loading for TWG names or do separate query.
    # To keep it simple, let's load TWG names.
    # Or optimize later. For now, accessing m.twg will fail in async unless eager loaded.
    
    # Let's fix eager load
    from sqlalchemy.orm import selectinload
    
    meetings_res = await db.execute(
        select(Meeting)
        .options(selectinload(Meeting.twg))
        .order_by(desc(Meeting.scheduled_at))
        .limit(limit)
    )
    meetings = meetings_res.scalars().all()
    
    timeline = []
    for m in meetings:
        timeline.append({
            "type": "meeting",
            "date": m.scheduled_at,
            "title": m.title,
            "twg": m.twg.name if m.twg else "Unknown",
            "status": m.status
        })
        
    # Sort by date descending
    timeline.sort(key=lambda x: x["date"], reverse=True)
    
    return timeline[:limit]

# --- WebSocket Manager ---

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                # Handle broken pipe
                pass

manager = ConnectionManager()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
