"""
Global Scheduling Service

Manages cross-TWG scheduling to prevent overlaps, ensure proper sequencing,
and coordinate VIP engagements across multiple TWGs using the centralized Database.
"""

from typing import Dict, List, Optional, Any, Set, Tuple, Union
from datetime import datetime, timedelta
from loguru import logger
from enum import Enum
from uuid import UUID, uuid4
from pydantic import BaseModel, Field
import asyncio
from app.services.gcal_executor import gcal_executor as _gcal_executor

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import selectinload

from app.core.database import get_db_session_context
from app.models.models import (
    Meeting, MeetingStatus, MeetingParticipant,
    VipProfile, Dependency, DependencyStatus,
    Conflict, ConflictType, ConflictSeverity, ConflictStatus,
    User, TWG
)
from app.services.calendar_service import calendar_service


class EventPriority(str, Enum):
    """Event priority levels"""
    CRITICAL = "critical"  # Ministerial, VIP
    HIGH = "high"          # Multi-TWG coordination
    MEDIUM = "medium"      # Single TWG meetings
    LOW = "low"            # Optional sessions

class ScheduleConflict(BaseModel):
    """A detected scheduling conflict"""
    conflict_id: UUID = Field(default_factory=uuid4)
    conflict_type: ConflictType
    severity: ConflictSeverity  # using Enum for consistency
    
    # Involved events
    event_ids: List[UUID] = Field(default_factory=list)
    event_titles: List[str] = Field(default_factory=list)

    # Description
    description: str
    impact: str

    # Resolution
    suggested_resolution: Optional[str] = None
    requires_manual_resolution: bool = False

class GlobalScheduler:
    """Service for managing global scheduling across all TWGs"""

    def __init__(self):
        """Initialize global scheduler"""
        # No more in-memory state
        pass

    async def request_booking(
        self,
        twg_id: UUID,
        title: str,
        start_time: datetime,
        duration_minutes: int,
        priority: EventPriority = EventPriority.MEDIUM,
        description: Optional[str] = None,
        vip_attendee_ids: Optional[List[UUID]] = None,
        location: Optional[str] = None,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        Request a new meeting booking. Performs proactive conflict detection.

        Args:
            twg_id: Requesting TWG
            title: Meeting title
            start_time: Start time
            duration_minutes: Duration
            priority: Priority level
            vip_attendee_ids: List of User IDs for VIPs
            location: Physical location or 'virtual'
            db: Optional DB session

        Returns:
            Dict with status, meeting_id (if success), or conflicts (if failed)
        """
        end_time = start_time + timedelta(minutes=duration_minutes)
        vip_attendee_ids = vip_attendee_ids or []
        
        async with self._get_session(db) as session:
            # 1. Detect Conflicts
            conflicts = await self._detect_conflicts(
                session, twg_id, start_time, end_time, vip_attendee_ids, location
            )
            
            critical_conflicts = [c for c in conflicts if c.severity in [ConflictSeverity.CRITICAL, ConflictSeverity.HIGH]]
            
            if critical_conflicts:
                logger.warning(f"⚠️ Booking denied for '{title}': {len(critical_conflicts)} critical conflicts")
                return {
                    "status": "denied",
                    "reason": "Critical conflicts detected",
                    "conflicts": [c.model_dump() for c in critical_conflicts],
                    "alternatives": await self._suggest_alternatives(
                        session, twg_id, start_time, duration_minutes, vip_attendee_ids
                    )
                }

            # 2. Create Meeting (REQUESTED or SCHEDULED based on conflicts)
            # If only low/medium conflicts, we might still allow it but flag it
            status = MeetingStatus.SCHEDULED
            if conflicts:
                status = MeetingStatus.REQUESTED # Require explicit approval if minor conflicts exist
            
            new_meeting = Meeting(
                id=uuid4(),
                twg_id=twg_id,
                title=title,
                scheduled_at=start_time,
                duration_minutes=duration_minutes,
                location=location,
                status=status,
                meeting_type="in-person" if location and location.lower() != "virtual" else "virtual"
            )
            
            session.add(new_meeting)
            
            # Add Participants (VIPs)
            for vip_id in vip_attendee_ids:
                part = MeetingParticipant(
                    meeting_id=new_meeting.id,
                    user_id=vip_id,
                    rsvp_status="pending"
                )
                session.add(part)
                
            # Persist Conflicts if any
            for c in conflicts:
                db_conflict = Conflict(
                    conflict_type=c.conflict_type,
                    severity=c.severity,
                    description=c.description,
                    agents_involved=[str(twg_id)], # Simplified
                    conflicting_positions={"new_meeting": title},
                    status=ConflictStatus.DETECTED
                )
                session.add(db_conflict)

            await session.commit()
            
            # 3. Create Google Calendar Event (if scheduled)
            if status == MeetingStatus.SCHEDULED:
                try:
                    # Get participant emails
                    # We need to query them again or use the IDs we have. 
                    # For simplicity, we'll fetch VIP emails.
                    vip_emails = []
                    if vip_attendee_ids:
                        stmt_users = select(User.email).where(User.id.in_(vip_attendee_ids))
                        res_users = await session.execute(stmt_users)
                        vip_emails = list(res_users.scalars().all())

                    loop = asyncio.get_running_loop()
                    _title = title
                    _start = start_time
                    _dur = duration_minutes
                    _desc = description or ""
                    _emails = vip_emails
                    _mid = str(new_meeting.id)
                    gcal_event = await loop.run_in_executor(
                        _gcal_executor,
                        lambda: calendar_service.create_meeting_event(
                            title=_title,
                            start_time=_start,
                            duration_minutes=_dur,
                            description=_desc,
                            attendees=_emails,
                            meeting_id=_mid
                        )
                    )
                    
                    if gcal_event and 'htmlLink' in gcal_event:
                        # Update meeting with video link if available
                        new_meeting.video_link = gcal_event.get('hangoutLink')
                        # We need to merge/add updates
                        session.add(new_meeting)
                        await session.commit()
                        logger.info(f"Google Calendar event created: {gcal_event.get('htmlLink')}")
                        
                except Exception as e:
                    logger.error(f"Failed to create Google Calendar event: {e}")
                    # Don't fail the booking, just log error

            logger.info(f"✓ Booking created: '{title}' ({status})")
            
            return {
                "status": status.value,
                "meeting_id": str(new_meeting.id),
                "conflicts": [c.model_dump() for c in conflicts]
            }

    async def _detect_conflicts(
        self,
        session: AsyncSession,
        twg_id: UUID,
        start_time: datetime,
        end_time: datetime,
        vip_ids: List[UUID],
        location: Optional[str]
    ) -> List[ScheduleConflict]:
        """Run all conflict checks"""
        conflicts = []
        
        # 1. VIP Availability
        if vip_ids:
            conflicts.extend(await self._check_vip_conflicts(session, start_time, end_time, vip_ids))
            
        # 2. Dependency Checks
        conflicts.extend(await self._check_dependency_conflicts(session, twg_id, start_time))
        
        # 3. Location/Resource Checks
        if location and location.lower() != 'virtual':
            conflicts.extend(await self._check_location_conflicts(session, start_time, end_time, location))
            
        return conflicts

    async def _check_vip_conflicts(
        self, session: AsyncSession, start: datetime, end: datetime, vip_ids: List[UUID]
    ) -> List[ScheduleConflict]:
        conflicts = []
        
        # Find meetings where these VIPs are participants that overlap time
        # We need to join MeetingParticipant -> Meeting
        
        # Let's simple query all meetings for these VIPs in a range (e.g. +/- 1 day) and filter in python
        # for robust correctness without DB-specific date math functions
        
        broad_start = start - timedelta(days=1)
        broad_end = end + timedelta(days=1)
        
        stmt = select(MeetingParticipant).join(Meeting).where(
            and_(
                MeetingParticipant.user_id.in_(vip_ids),
                Meeting.status.in_([MeetingStatus.SCHEDULED, MeetingStatus.REQUESTED]),
                Meeting.scheduled_at >= broad_start,
                Meeting.scheduled_at <= broad_end
            )
        ).options(selectinload(MeetingParticipant.user), selectinload(MeetingParticipant.meeting))
        
        result = await session.execute(stmt)
        participations = result.scalars().all()
        
        for p in participations:
            m_start = p.meeting.scheduled_at
            m_end = m_start + timedelta(minutes=p.meeting.duration_minutes)
            
            if m_start < end and m_end > start:
                # Overlap!
                vip_name = p.user.full_name if p.user else "Unknown VIP"
                conflicts.append(ScheduleConflict(
                    conflict_type=ConflictType.VIP_AVAILABILITY,
                    severity=ConflictSeverity.CRITICAL,
                    description=f"VIP {vip_name} is already booked for '{p.meeting.title}'",
                    impact="VIP Double Booking",
                    event_ids=[p.meeting.id],
                    suggested_resolution="Reschedule or find delegate"
                ))
                
        return conflicts

    async def _check_dependency_conflicts(
        self, session: AsyncSession, twg_id: UUID, start_time: datetime
    ) -> List[ScheduleConflict]:
        """Check if this TWG has satisfied incoming dependencies"""
        conflicts = []
        
        # Find dependencies where target_twg_id == this twg
        # And status is != SATISFIED
        stmt = select(Dependency).where(
            and_(
                Dependency.target_twg_id == twg_id,
                Dependency.status != DependencyStatus.SATISFIED
            )
        )
        result = await session.execute(stmt)
        dependencies = result.scalars().all()
        
        for dep in dependencies:
            # Check if this meeting relies on a blocked dependency
            # Ideally dependency model links to specific meeting types/topics
            # For now, we assume ALL meetings of target TWG are blocked if critical dependency is pending
            # This is a strict "Stop the Line" logic.
             conflicts.append(ScheduleConflict(
                conflict_type=ConflictType.DEPENDENCY_BLOCKER,
                severity=ConflictSeverity.HIGH,
                description=f"Blocked by dependency: {dep.description}",
                impact="Prerequisite not met",
                suggested_resolution="Resolve dependency with Source TWG first"
            ))
            
        return conflicts

    async def _check_location_conflicts(
        self, session: AsyncSession, start: datetime, end: datetime, location: str
    ) -> List[ScheduleConflict]:
        conflicts = []
        stmt = select(Meeting).where(
            and_(
                Meeting.location == location,
                Meeting.status.in_([MeetingStatus.SCHEDULED]),
                Meeting.scheduled_at >= start - timedelta(days=1), # Filter optimization
                Meeting.scheduled_at <= end + timedelta(days=1)
            )
        )
        result = await session.execute(stmt)
        meetings = result.scalars().all()
        
        for m in meetings:
            m_end = m.scheduled_at + timedelta(minutes=m.duration_minutes)
            if m.scheduled_at < end and m_end > start:
                conflicts.append(ScheduleConflict(
                    conflict_type=ConflictType.RESOURCE_CONSTRAINT,
                    severity=ConflictSeverity.MEDIUM,
                    description=f"Location '{location}' is occupied by '{m.title}'",
                    impact="Room double booking",
                    event_ids=[m.id],
                    suggested_resolution="Choose different room or time"
                ))
        return conflicts

    async def _suggest_alternatives(
        self, session: AsyncSession, twg_id: UUID, original_start: datetime, duration: int, vip_ids: List[UUID]
    ) -> List[datetime]:
        """Suggest next 3 available slots"""
        alternatives = []
        search_time = original_start + timedelta(hours=1)
        
        # Limit search to 10 attempts
        for _ in range(10):
            conflicts = await self._detect_conflicts(
                session, twg_id, search_time, search_time + timedelta(minutes=duration), vip_ids, None
            )
            critical = [c for c in conflicts if c.severity in [ConflictSeverity.CRITICAL, ConflictSeverity.HIGH]]
            if not critical:
                alternatives.append(search_time)
                if len(alternatives) >= 3:
                    break
            search_time += timedelta(hours=1)
            
        return alternatives

    def _get_session(self, db: Optional[AsyncSession]):
        if db:
            class NoOpContextText:
                async def __aenter__(self): return db
                async def __aexit__(self, exc_type, exc_val, exc_tb): pass
            return NoOpContextText()
        return get_db_session_context()

    async def check_availability(
        self,
        start_time: datetime,
        duration_minutes: int,
        vip_ids: List[UUID],
        twg_id: Optional[UUID] = None,
        db: Optional[AsyncSession] = None
    ) -> List[ScheduleConflict]:
        """
        Public method to check availability without booking.
        """
        end_time = start_time + timedelta(minutes=duration_minutes)
        async with self._get_session(db) as session:
            conflicts = []
            if vip_ids:
                conflicts.extend(await self._check_vip_conflicts(session, start_time, end_time, vip_ids))
            
            if twg_id:
                conflicts.extend(await self._check_dependency_conflicts(session, twg_id, start_time))
                
            return conflicts

    async def get_twg_schedule(
        self,
        twg_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        db: Optional[AsyncSession] = None
    ) -> List[Meeting]:
        """Get schedule for a specific TWG from DB"""
        async with self._get_session(db) as session:
            stmt = select(Meeting).where(
                Meeting.twg_id == twg_id,
                Meeting.status != MeetingStatus.CANCELLED
            )

            if start_date:
                stmt = stmt.where(Meeting.scheduled_at >= start_date)
            if end_date:
                stmt = stmt.where(Meeting.scheduled_at <= end_date)

            stmt = stmt.order_by(Meeting.scheduled_at)

            result = await session.execute(stmt)
            return result.scalars().all()

    async def get_global_schedule(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        db: Optional[AsyncSession] = None
    ) -> List[Meeting]:
        """Get global schedule across all TWGs from DB"""
        async with self._get_session(db) as session:
            stmt = select(Meeting).where(Meeting.status != MeetingStatus.CANCELLED)

            if start_date:
                stmt = stmt.where(Meeting.scheduled_at >= start_date)
            if end_date:
                stmt = stmt.where(Meeting.scheduled_at <= end_date)

            stmt = stmt.order_by(Meeting.scheduled_at)
            
            result = await session.execute(stmt)
            return result.scalars().all()

# Global Instance
global_scheduler = GlobalScheduler()
