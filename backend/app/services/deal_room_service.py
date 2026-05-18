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

    async def get_featured_projects(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get the automated 'Deal Room Selection'.
        Criteria:
        1. Flagship projects (manual override)
        2. High AfCEN Score (>80)
        3. Diversity of Pillars (ensure representation)
        """
        # Logic: 
        # Select * from projects where status = DEAL_ROOM or (status = FINANCING and score > 80)
        # Order by is_flagship desc, afcen_score desc
        
        stmt = (
            select(Project)
            .where(
                or_(
                    Project.status == ProjectStatus.SUMMIT_READY,
                    and_(Project.status == ProjectStatus.DEAL_ROOM_FEATURED, Project.readiness_score >= 7.0)
                )
            )
            .order_by(Project.is_flagship.desc(), Project.afcen_score.desc())
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
                "status": p.status.value,
                "investment_size": float(p.investment_size)
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
