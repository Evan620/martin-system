"""
Supervisor Global State Service

Provides centralized state management for the Supervisor Agent.
Maintains real-time view of all TWG activities, documents, and projects.

Event-driven updates ensure state is always current.
"""

from typing import Dict, List, Optional
from datetime import datetime, timezone
UTC = timezone.utc
from uuid import UUID
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload
from collections import defaultdict

from app.models.models import (
    TWG, Meeting, Document, Project, Conflict, User, Dependency,
    MeetingStatus, ProjectStatus, ConflictStatus
)
from app.schemas.supervisor import (
    SupervisorStateSnapshot, MeetingSnapshot, DocumentSnapshot,
    ProjectSnapshot, TWGSummary, ConflictSnapshot, DependencySnapshot,
    GlobalCalendarResponse, DocumentRegistryResponse, ProjectPipelineResponse
)


class SupervisorGlobalState:
    """
    Centralized state manager for Supervisor Agent.
    
    Provides birds-eye view of entire summit including:
    - Global calendar (all TWG meetings)
    - Document registry (all documents)
    - Project pipeline (all projects)
    - Cross-TWG dependencies
    - Active conflicts
    """
    
    def __init__(self):
        """Initialize empty state"""
        self._state: Optional[SupervisorStateSnapshot] = None
        self._last_refresh: Optional[datetime] = None
        logger.info("SupervisorGlobalState initialized")
    
    async def refresh_state(self, db: AsyncSession) -> SupervisorStateSnapshot:
        """
        Refresh global state from database.
        
        This is the core aggregation logic that fetches all summit data
        and builds a unified view.
        
        Args:
            db: Database session
            
        Returns:
            Updated state snapshot
        """
        logger.info("Refreshing supervisor global state...")
        start_time = datetime.now(UTC)
        
        # Fetch all TWGs with relationships
        twgs_result = await db.execute(
            select(TWG).options(
                selectinload(TWG.meetings),
                selectinload(TWG.documents),
                selectinload(TWG.projects)
            )
        )
        twgs = twgs_result.scalars().all()
        
        # Fetch all meetings with participants
        meetings_result = await db.execute(
            select(Meeting).options(
                selectinload(Meeting.twg),
                selectinload(Meeting.participants)
            ).order_by(Meeting.scheduled_at)
        )
        all_meetings = meetings_result.scalars().all()
        
        # Fetch all documents with uploader info and versions
        documents_result = await db.execute(
            select(Document).options(
                selectinload(Document.twg),
                selectinload(Document.uploaded_by),
                selectinload(Document.versions)
            ).order_by(Document.created_at.desc())
        )
        all_documents = documents_result.scalars().all()
        
        # Fetch all projects
        projects_result = await db.execute(
            select(Project).options(
                selectinload(Project.twg)
            ).order_by(Project.status, Project.readiness_score.desc())
        )
        all_projects = projects_result.scalars().all()
        
        # Fetch active conflicts
        conflicts_result = await db.execute(
            select(Conflict).where(
                Conflict.status.in_([
                    ConflictStatus.DETECTED,
                    ConflictStatus.NEGOTIATING,
                    ConflictStatus.ESCALATED
                ])
            ).order_by(Conflict.detected_at.desc())
        )
        active_conflicts = conflicts_result.scalars().all()
        
        # Build conflict lookup for meetings
        conflict_meeting_ids = set()
        for conflict in active_conflicts:
            # Extract meeting IDs from conflict description if present
            # This is a simplified approach - in production, conflicts should
            # have explicit meeting_id references
            pass
        
        # Build calendar snapshots
        calendar = []
        for meeting in all_meetings:
            calendar.append(MeetingSnapshot(
                id=meeting.id,
                twg_id=meeting.twg_id,
                twg_name=meeting.twg.name if meeting.twg else "Unknown",
                title=meeting.title,
                scheduled_at=meeting.scheduled_at,
                duration_minutes=meeting.duration_minutes,
                location=meeting.location,
                status=meeting.status,
                participant_count=len(meeting.participants),
                has_conflicts=meeting.id in conflict_meeting_ids
            ))
        
        # Build document snapshots
        documents = []
        for doc in all_documents:
            documents.append(DocumentSnapshot(
                id=doc.id,
                twg_id=doc.twg_id,
                twg_name=doc.twg.name if doc.twg else None,
                file_name=doc.file_name,
                file_type=doc.file_type,
                created_at=doc.created_at,
                is_confidential=doc.is_confidential,
                uploaded_by_name=doc.uploaded_by.full_name if doc.uploaded_by else "Unknown",
                version=doc.version,
                parent_document_id=doc.parent_document_id,
                has_newer_version=len(doc.versions) > 0
            ))
        
        # Build project snapshots
        projects = []
        for project in all_projects:
            projects.append(ProjectSnapshot(
                id=project.id,
                twg_id=project.twg_id,
                twg_name=project.twg.name if project.twg else "Unknown",
                name=project.name,
                description=project.description,
                investment_size=project.investment_size,
                currency=project.currency,
                readiness_score=project.readiness_score,
                status=project.status
            ))
        
        # Build conflict snapshots
        conflict_snapshots = []
        for conflict in active_conflicts:
            conflict_snapshots.append(ConflictSnapshot(
                id=conflict.id,
                conflict_type=conflict.conflict_type.value,
                severity=conflict.severity,
                description=conflict.description,
                agents_involved=[str(a) for a in conflict.agents_involved if a is not None] if conflict.agents_involved else [],
                status=conflict.status,
                detected_at=conflict.detected_at
            ))
        
        # Build TWG summaries
        twg_summaries = {}
        for twg in twgs:
            # Count meetings by status
            total_meetings = len(twg.meetings)
            upcoming = len([m for m in twg.meetings if m.status == MeetingStatus.SCHEDULED])
            completed = len([m for m in twg.meetings if m.status == MeetingStatus.COMPLETED])
            
            # Count projects by status
            projects_by_status = defaultdict(int)
            for project in twg.projects:
                projects_by_status[project.status.value] += 1
            
            # Find last activity
            last_activity = None
            if twg.meetings:
                completed_meetings = [m for m in twg.meetings if m.status == MeetingStatus.COMPLETED]
                if completed_meetings:
                    last_activity = max(m.scheduled_at for m in completed_meetings)
            
            # Count conflicts involving this TWG
            twg_conflicts = len([
                c for c in active_conflicts 
                if twg.name in c.agents_involved
            ])
            
            twg_summaries[str(twg.id)] = TWGSummary(
                twg_id=twg.id,
                twg_name=twg.name,
                pillar=twg.pillar,
                status=twg.status,
                total_meetings=total_meetings,
                upcoming_meetings=upcoming,
                completed_meetings=completed,
                total_documents=len(twg.documents),
                total_projects=len(twg.projects),
                active_conflicts=twg_conflicts,
                last_activity=last_activity,
                projects_by_status=dict(projects_by_status)
            )
        
        # Build state snapshot

        # Fetch cross-TWG dependencies
        dependencies_result = await db.execute(
            select(Dependency).options(
                selectinload(Dependency.source_twg),
                selectinload(Dependency.target_twg)
            ).order_by(Dependency.created_at.desc())
        )
        all_dependencies = dependencies_result.scalars().all()
        
        # Build dependency snapshots
        dependency_snapshots = []
        for dep in all_dependencies:
            dependency_snapshots.append(DependencySnapshot(
                id=dep.id,
                source_twg_id=dep.source_twg_id,
                source_twg_name=dep.source_twg.name if dep.source_twg else "Unknown",
                target_twg_id=dep.target_twg_id,
                target_twg_name=dep.target_twg.name if dep.target_twg else "Unknown",
                description=dep.description,
                status=dep.status.value if hasattr(dep.status, 'value') else str(dep.status),
                created_at=dep.created_at
            ))

        # Build state snapshot
        self._state = SupervisorStateSnapshot(
            calendar=calendar,
            documents=documents,
            projects=projects,
            twg_summaries=twg_summaries,
            active_conflicts=conflict_snapshots,
            dependencies=dependency_snapshots,
            last_refresh=datetime.now(UTC),
            total_twgs=len(twgs),
            total_meetings=len(all_meetings),
            total_documents=len(all_documents),
            total_projects=len(all_projects)
        )
        
        self._last_refresh = self._state.last_refresh
        
        elapsed = (datetime.now(UTC) - start_time).total_seconds()
        logger.info(
            f"✓ State refreshed in {elapsed:.2f}s: "
            f"{len(twgs)} TWGs, {len(all_meetings)} meetings, "
            f"{len(all_documents)} documents, {len(all_projects)} projects"
        )
        
        return self._state
    
    def get_state(self) -> Optional[SupervisorStateSnapshot]:
        """Get current state snapshot"""
        return self._state
    
    def get_global_calendar(self) -> GlobalCalendarResponse:
        """Get unified calendar view"""
        if not self._state:
            raise ValueError("State not initialized. Call refresh_state() first.")
        
        upcoming = len([
            m for m in self._state.calendar 
            if m.status == MeetingStatus.SCHEDULED
        ])
        
        conflicts = len([
            m for m in self._state.calendar 
            if m.has_conflicts
        ])
        
        return GlobalCalendarResponse(
            meetings=self._state.calendar,
            total_meetings=len(self._state.calendar),
            upcoming_meetings=upcoming,
            conflicts_detected=conflicts,
            last_refresh=self._state.last_refresh
        )
    
    def get_document_registry(self) -> DocumentRegistryResponse:
        """Get document registry view"""
        if not self._state:
            raise ValueError("State not initialized. Call refresh_state() first.")
        
        # Count documents by TWG
        by_twg = defaultdict(int)
        for doc in self._state.documents:
            if doc.twg_name:
                by_twg[doc.twg_name] += 1
        
        return DocumentRegistryResponse(
            documents=self._state.documents,
            total_documents=len(self._state.documents),
            by_twg=dict(by_twg),
            last_refresh=self._state.last_refresh
        )
    
    def get_project_pipeline(self) -> ProjectPipelineResponse:
        """Get project pipeline view"""
        if not self._state:
            raise ValueError("State not initialized. Call refresh_state() first.")
        
        # Count by status
        by_status = defaultdict(int)
        by_twg = defaultdict(int)
        total_investment = 0
        
        for project in self._state.projects:
            by_status[project.status.value] += 1
            by_twg[project.twg_name] += 1
            total_investment += float(project.investment_size)
        
        return ProjectPipelineResponse(
            projects=self._state.projects,
            total_projects=len(self._state.projects),
            by_status=dict(by_status),
            by_twg=dict(by_twg),
            total_investment=total_investment,
            last_refresh=self._state.last_refresh
        )
    
    def get_twg_summary(self, twg_id: UUID) -> Optional[TWGSummary]:
        """Get summary for specific TWG"""
        if not self._state:
            raise ValueError("State not initialized. Call refresh_state() first.")
        
        return self._state.twg_summaries.get(str(twg_id))


# Singleton instance
_global_state: Optional[SupervisorGlobalState] = None


def get_supervisor_state() -> SupervisorGlobalState:
    """Get or create supervisor global state singleton"""
    global _global_state
    if _global_state is None:
        _global_state = SupervisorGlobalState()
    return _global_state
