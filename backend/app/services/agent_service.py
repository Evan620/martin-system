from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import List, Dict, Any, Optional
import uuid

from app.models.models import TWG, Meeting, ActionItem, Conflict, Project, MeetingStatus, ActionItemStatus, ProjectStatus, WeeklyPacket

class AgentService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def generate_twg_packet(self, twg_id: uuid.UUID, week_start: datetime, week_end: datetime) -> WeeklyPacket:
        """
        Simulates a TWG Sub-Agent generating its Weekly Packet.
        Gathering data from:
        - Meetings (Proposed Sessions)
        - Action Items & Projects (Accomplishments)
        - Conflicts (Risks)
        - Cross-referencing inputs (Dependencies)
        """
        
        # 1. Fetch Proposed Sessions (Meetings rescheduled or planned for next week)
        # For simplicity, we look at meetings scheduled for the *upcoming* week (assuming week_end is the end of 'this' week)
        next_week_start = week_end
        next_week_end = next_week_start + timedelta(days=7)
        
        upcoming_meetings_res = await self.db.execute(
            select(Meeting).where(
                Meeting.twg_id == twg_id,
                Meeting.scheduled_at >= next_week_start,
                Meeting.scheduled_at < next_week_end,
                Meeting.status == MeetingStatus.SCHEDULED
            )
        )
        upcoming_meetings = upcoming_meetings_res.scalars().all()
        
        proposed_sessions = []
        for m in upcoming_meetings:
            proposed_sessions.append({
                "title": m.title,
                "date": m.scheduled_at.isoformat(),
                "location": m.location or "TBD"
            })
            
        # 2. Accomlishments (Completed Items this week)
        completed_actions_res = await self.db.execute(
            select(ActionItem).where(
                ActionItem.twg_id == twg_id,
                ActionItem.status == ActionItemStatus.COMPLETED,
                ActionItem.due_date >= week_start, # Approximate "completed at" by using due_date or we'd need a completed_at field
            )
        )
        completed_actions = completed_actions_res.scalars().all()
        
        accomplishments = [f"Completed task: {a.description}" for a in completed_actions]
        
        # Add 'Signed' or 'Bankable' projects as accomplishments
        projects_res = await self.db.execute(
            select(Project).where(
                Project.twg_id == twg_id,
                Project.status.in_([ProjectStatus.BANKABLE, ProjectStatus.PRESENTED])
            )
        )
        projects = projects_res.scalars().all()
        for p in projects:
             accomplishments.append(f"Project '{p.name}' reached {p.status.value} status.")

        if not accomplishments:
             accomplishments.append("No major milestones recorded this week.")

        # 3. Risks & Blockers
        # Overdue items
        overdue_res = await self.db.execute(
            select(ActionItem).where(
                ActionItem.twg_id == twg_id,
                ActionItem.status == ActionItemStatus.OVERDUE
            )
        )
        overdue_items = overdue_res.scalars().all()
        
        risks = []
        for item in overdue_items:
            risks.append({
                "type": "Overdue Action",
                "description": f"Overdue: {item.description}",
                "severity": "medium"
            })

        # Stalled Projects (Status = Identified for long time? - Logic simplified here)
        stalled_projects_res = await self.db.execute(
            select(Project).where(Project.twg_id == twg_id, Project.status == ProjectStatus.VETTING)
        )
        stalled_projects = stalled_projects_res.scalars().all()
        for p in stalled_projects:
             risks.append({
                "type": "Stalled Negotiation",
                "description": f"Project '{p.name}' stuck in vetting.",
                "severity": "high"
             })

        # 4. Dependencies (Mock Analysis for now, real logic would scan project descriptions)
        # We can simulate this by looking for keywords of other Pillars in this TWG's docs
        dependencies = []
        # Placeholder logic: if "Energy" TWG has a project with "Agriculture" in description
        # For now, return empty or static placeholder if needed, but better to keep empty until real logic exists
        
        # Create and Persistence
        packet = WeeklyPacket(
            twg_id=twg_id,
            week_start_date=week_start,
            proposed_sessions=proposed_sessions,
            dependencies=dependencies,
            accomplishments=accomplishments,
            risks_and_blockers=risks,
            status="submitted"
        )
        
        self.db.add(packet)
        await self.db.commit()
        await self.db.refresh(packet)
        
        return packet

    async def approve_document_creation(self, approval_request_id: str, final_title: str, final_content: str, document_type: str, file_name: str, tags: List[str], user_id: uuid.UUID, twg_id: Optional[uuid.UUID] = None) -> Dict[str, Any]:
        """
        Finalize a document creation after human approval.
        1. Save to Document Registry.
        2. Resume Agent Graph.
        """
        from app.models.models import Document
        
        # 1. Create the Document
        # In a real system, we might upload to S3/Blob storage and save the URL.
        # Here we simulate by saving content to a file or just DB metadata + text link.
        # For simplicity, we assume we store the text or a placeholder path.
        
        import os
        
        # Simulate file path
        safe_filename = "".join([c for c in file_name if c.isalnum() or c in "._-"])
        file_path = f"twg_docs/{safe_filename}"
        
        new_doc = Document(
            twg_id=twg_id,
            file_name=final_title, # Using title as display name
            file_path=file_path,
            file_type="markdown",
            uploaded_by_id=user_id,
            metadata_json={
                "content_preview": final_content[:500], # Store preview
                "full_content_store": final_content, # Ideally this is a link
                "tags": tags,
                "document_type": document_type,
                "approval_request_id": approval_request_id,
                "created_via": "agent_approval"
            }
        )
        
        self.db.add(new_doc)
        await self.db.commit()
        await self.db.refresh(new_doc)
        
        # 2. Resume the Agent Graph
        # We need to find the thread/graph associated with this request.
        # Currently, our system simplifies this by assuming the Frontend holds the thread_id/resume logic
        # OR we use the LangGraph `Command(resume=...)`.
        # For this prototype, we return the success payload, and the Frontend calls the GENERIC resume endpoint with this payload.
        
        return {
            "document_id": str(new_doc.id),
            "status": "approved",
            "file_path": file_path
        }

