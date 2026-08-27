from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
UTC = timezone.utc
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
import uuid
from decimal import Decimal

from app.models.models import (
    Project, ProjectStatus, DealRoomMeeting, Investor, ProjectInvestorMatch
)
from app.services.audit_service import audit_service

class DealRoomService:
    """
    Service for managing the Deal Room (Summit Week) experience.
    Handles curation of "Featured Projects" and scheduling of meetings.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_featured_projects(self, limit: int = 20, max_tier: int = 2) -> List[Dict[str, Any]]:
        """
        Get the Deal Room selection, surfaced by the readiness continuum.

        Returns the Boardroom (tier 1) and Deal Room (tier 2) tiers by default,
        ordered most-ready first (flagship, then AfCEN score within tier). Pass a
        higher ``max_tier`` to widen the lens toward Preparation / Early-stage.
        """
        from app.services.deal_room_tier import DEAL_ROOM_TIERS

        stmt = (
            select(Project)
            .where(
                Project.deleted_at.is_(None),
                Project.deal_room_priority.isnot(None),
                Project.deal_room_priority <= max_tier,
            )
            .order_by(
                Project.deal_room_priority.asc(),
                Project.is_flagship.desc(),
                Project.afcen_score.desc(),
            )
            .limit(limit)
        )

        result = await self.db.execute(stmt)
        projects = result.scalars().all()

        return [
            {
                "id": str(p.id),
                "name": p.name,
                "pillar": p.pillar,
                "country": p.lead_country,
                "score": float(p.afcen_score or 0),
                "is_flagship": p.is_flagship,
                "status": p.status.value if hasattr(p.status, "value") else str(p.status),
                "investment_size": float(p.investment_size or 0),
                "tier_rank": p.deal_room_priority,
                "tier": (p.investment_stage_label
                         or DEAL_ROOM_TIERS.get(p.deal_room_priority, (None,))[0]),
            }
            for p in projects
        ]

    async def schedule_meeting(
        self,
        project_id: uuid.UUID,
        investor_id: uuid.UUID,
        scheduled_by_id: uuid.UUID,
        start_time: datetime,
        duration_minutes: int = 30,
        location: Optional[str] = "Deal Room A"
    ) -> Dict[str, Any]:
        """
        Schedule a specific 1:1 meeting for the Deal Room.
        """
        # Basic conflict check (omitted for MVP speed, assume Scheduler UI handles valid slots)
        
        meeting = DealRoomMeeting(
            project_id=project_id,
            investor_id=investor_id,
            meeting_datetime=start_time,
            duration_minutes=duration_minutes,
            location=location,
            scheduled_by_id=scheduled_by_id,
            meeting_status="scheduled"
        )
        
        self.db.add(meeting)
        await self.db.flush()
        
        # Log
        await audit_service.log_activity(
            self.db, 
            scheduled_by_id, 
            "deal_room_meeting_scheduled", 
            "deal_room_meeting", 
            meeting.id,
            {"project_id": str(project_id), "investor_id": str(investor_id), "time": start_time.isoformat()}
        )
        await self.db.commit()
        
        return {"status": "success", "meeting_id": str(meeting.id)}
