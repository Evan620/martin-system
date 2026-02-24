"""
Database Tools for AI Agents

This module provides tools for AI agents to interact with the relational database,
allowing them to manage TWGs, meetings, action items, and the deal pipeline.
"""

import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
import logging
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
import pytz

from app.core.database import AsyncSessionLocal
from app.models.models import TWG, Meeting, ActionItem, Project, User, Document, Minutes
from sqlalchemy.orm import selectinload

logger = logging.getLogger(__name__)

async def get_twg_info(twg_id: uuid.UUID) -> Dict[str, Any]:
    """
    Fetch comprehensive details about a specific Technical Working Group.
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(TWG).where(TWG.id == twg_id))
        twg = result.scalar_one_or_none()
        if not twg:
            return {"error": "TWG not found"}
        
        return {
            "id": str(twg.id),
            "name": twg.name,
            "pillar": twg.pillar,
            "status": twg.status,
            "member_count": len(twg.members)
        }

async def get_twg_members(twg_id: uuid.UUID) -> List[Dict[str, Any]]:
    """
    Fetch all members of a specific Technical Working Group with their names and email addresses.
    Use this tool when you need to send emails to TWG members or look up who belongs to a TWG.
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(TWG).where(TWG.id == twg_id).options(selectinload(TWG.members))
        )
        twg = result.scalar_one_or_none()
        if not twg:
            return [{"error": "TWG not found"}]

        members = []
        for user in twg.members:
            members.append({
                "name": user.full_name,
                "email": user.email,
                "role": user.role.value if hasattr(user.role, 'value') else str(user.role),
            })

        # Also include leads if assigned
        if twg.political_lead_id:
            lead_result = await session.execute(select(User).where(User.id == twg.political_lead_id))
            lead = lead_result.scalar_one_or_none()
            if lead and not any(m["email"] == lead.email for m in members):
                members.append({"name": lead.full_name, "email": lead.email, "role": "political_lead"})

        if twg.technical_lead_id:
            lead_result = await session.execute(select(User).where(User.id == twg.technical_lead_id))
            lead = lead_result.scalar_one_or_none()
            if lead and not any(m["email"] == lead.email for m in members):
                members.append({"name": lead.full_name, "email": lead.email, "role": "technical_lead"})

        return members


async def list_twg_meetings(twg_id: uuid.UUID) -> List[Dict[str, Any]]:
    """
    Retrieve a timeline of meetings for a specific TWG.
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Meeting)
            .where(Meeting.twg_id == twg_id)
            .order_by(Meeting.scheduled_at.desc())
        )
        meetings = result.scalars().all()
        return [
            {
                "id": str(m.id),
                "title": m.title,
                "scheduled_at": m.scheduled_at.isoformat(),
                "status": m.status
            } for m in meetings
        ]

async def create_meeting_invite(
    twg_id: uuid.UUID,
    title: str,
    scheduled_at: datetime,
    location: str = "Virtual",
    duration: int = 60,
    timezone: str = "Africa/Lagos" # Default to ECOWAS HQ
) -> Dict[str, Any]:
    """
    Create a new meeting entry in the database.
    Converts local time (based on 'timezone' param) to UTC for storage.
    """
    async with AsyncSessionLocal() as session:
        # 1. Timezone Handling: Input -> Local -> UTC
        try:
            local_tz = pytz.timezone(timezone)
            if scheduled_at.tzinfo is None:
                # Assume input is in local_tz if naive
                local_dt = local_tz.localize(scheduled_at)
            else:
                local_dt = scheduled_at.astimezone(local_tz)
            
            # Convert to UTC for storage (Naive UTC)
            utc_dt = local_dt.astimezone(pytz.UTC).replace(tzinfo=None)
        except Exception as e:
            logger.error(f"Timezone conversion error: {e}")
            utc_dt = scheduled_at if scheduled_at.tzinfo is None else scheduled_at.astimezone(pytz.UTC).replace(tzinfo=None)

        # Intelligent URL extraction for video links
        video_link = None
        cleaned_location = location
        
        # Check for common video conference patterns or raw URLs
        if location and any(x in location.lower() for x in ['http', 'meet.google', 'zoom.us', 'teams.microsoft']):
            potential_link = location.strip()
            if ' ' not in potential_link and '.' in potential_link:
                if not potential_link.startswith(('http://', 'https://')):
                    video_link = f"https://{potential_link}"
                else:
                    video_link = potential_link
                if location.lower() == 'virtual':
                    cleaned_location = location
                
        new_meeting = Meeting(
            twg_id=twg_id,
            title=title,
            scheduled_at=utc_dt, # Store as UTC
            location=cleaned_location,
            duration_minutes=duration,
            video_link=video_link
        )
        session.add(new_meeting)
        await session.commit()
        await session.refresh(new_meeting)
        
        return {
            "meeting_id": str(new_meeting.id),
            "status": "created",
            "video_link": video_link,
            "scheduled_utc": utc_dt.isoformat(),
            "invite_text_hint": f"Invitation for {title} on {local_dt.strftime('%Y-%m-%d %H:%M %Z')}"
        }

async def update_action_items_from_minutes(
    twg_id: uuid.UUID,
    meeting_id: uuid.UUID,
    items: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Log or update tasks extracted from meeting minutes.
    'items' should be a list of dicts with: description, owner_email, due_date
    """
    async with AsyncSessionLocal() as session:
        created_count = 0
        for item in items:
            # Try to find user by email
            user_result = await session.execute(select(User).where(User.email == item['owner_email']))
            user = user_result.scalar_one_or_none()
            
            if user:
                new_item = ActionItem(
                    twg_id=twg_id,
                    meeting_id=meeting_id,
                    description=item['description'],
                    owner_id=user.id,
                    due_date=datetime.fromisoformat(item['due_date']) if isinstance(item['due_date'], str) else item['due_date']
                )
                session.add(new_item)
                created_count += 1
        
        await session.commit()
        return {"action_items_created": created_count}

async def get_deal_pipeline(twg_id: Optional[uuid.UUID] = None) -> List[Dict[str, Any]]:
    """
    Fetch current investment projects in the pipeline.
    """
    async with AsyncSessionLocal() as session:
        query = select(Project)
        if twg_id:
            query = query.where(Project.twg_id == twg_id)
        
        result = await session.execute(query)
        projects = result.scalars().all()
        return [
            {
                "id": str(p.id),
                "name": p.name,
                "investment_size": float(p.investment_size),
                "readiness_score": p.readiness_score,
                "status": p.status
            } for p in projects
        ]

async def search_documents(
    twg_id: Optional[uuid.UUID] = None,
    query: Optional[str] = None,
    document_type: Optional[str] = None,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Search the document registry for documents matching the given criteria.
    Filters by TWG, keyword (file_name), and document_type.
    """
    async with AsyncSessionLocal() as session:
        stmt = select(Document).where(Document.is_confidential == False)

        if twg_id:
            stmt = stmt.where(Document.twg_id == twg_id)

        if query:
            stmt = stmt.where(Document.file_name.ilike(f"%{query}%"))

        if document_type:
            stmt = stmt.where(Document.document_type == document_type)

        stmt = stmt.order_by(Document.created_at.desc()).limit(limit)

        result = await session.execute(stmt)
        docs = result.scalars().all()

        return [
            {
                "id": str(d.id),
                "file_name": d.file_name,
                "document_type": d.document_type or "general",
                "category": d.category,
                "created_at": d.created_at.isoformat() if d.created_at else None,
                "version": d.version,
            }
            for d in docs
        ]


async def get_meeting_minutes(
    twg_id: Optional[uuid.UUID] = None,
    meeting_id: Optional[str] = None,
    limit: int = 5
) -> List[Dict[str, Any]]:
    """
    Retrieve meeting minutes. Can fetch minutes for a specific meeting
    or list recent minutes for the TWG.
    """
    async with AsyncSessionLocal() as session:
        stmt = (
            select(Minutes)
            .join(Meeting, Minutes.meeting_id == Meeting.id)
            .options(selectinload(Minutes.meeting))
        )

        if meeting_id:
            try:
                mid = uuid.UUID(meeting_id)
                stmt = stmt.where(Minutes.meeting_id == mid)
            except ValueError:
                return [{"error": f"Invalid meeting_id: {meeting_id}"}]

        if twg_id:
            stmt = stmt.where(Meeting.twg_id == twg_id)

        stmt = stmt.order_by(Meeting.scheduled_at.desc()).limit(limit)

        result = await session.execute(stmt)
        minutes_list = result.scalars().all()

        output = []
        for m in minutes_list:
            content_preview = (m.content[:500] + "...") if m.content and len(m.content) > 500 else (m.content or "")
            output.append({
                "meeting_id": str(m.meeting_id),
                "meeting_title": m.meeting.title if m.meeting else "Unknown",
                "scheduled_at": m.meeting.scheduled_at.isoformat() if m.meeting and m.meeting.scheduled_at else None,
                "minutes_status": m.status.value if hasattr(m.status, 'value') else str(m.status),
                "content_preview": content_preview,
                "key_decisions": m.key_decisions or "",
            })
        return output


# Tool definitions for Agent integration
DATABASE_TOOLS = [
    {
        "name": "get_twg_info",
        "description": "Fetch details about a specific Technical Working Group including its pillar and status.",
        "parameters": {
            "twg_id": "UUID of the TWG"
        },
        "coroutine": get_twg_info
    },
    {
        "name": "get_twg_members",
        "description": "Fetch all members of a TWG with their names and email addresses. Use this when you need to send emails to TWG members or check who belongs to a working group.",
        "parameters": {
            "twg_id": "UUID of the TWG"
        },
        "coroutine": get_twg_members
    },
    {
        "name": "list_twg_meetings",
        "description": "Retrieve a list of past and upcoming meetings for a TWG.",
        "parameters": {
            "twg_id": "UUID of the TWG"
        },
        "coroutine": list_twg_meetings
    },
    {
        "name": "create_meeting_invite",
        "description": "Schedule a new meeting for a TWG and record it in the database.",
        "parameters": {
            "twg_id": "UUID of the TWG",
            "title": "Meeting title",
            "scheduled_at": "ISO formatted datetime string",
            "location": "Optional location or meeting link",
            "duration": "Duration in minutes (default: 60)",
            "timezone": "Timezone string (default: Africa/Lagos)"
        },
        "coroutine": create_meeting_invite
    },
    {
        "name": "update_action_items_from_minutes",
        "description": "Log new action items extracted from meeting minutes into the database.",
        "parameters": {
            "twg_id": "UUID of the TWG",
            "meeting_id": "UUID of the meeting",
            "items": "List of dicts with description, owner_email, and due_date"
        },
        "coroutine": update_action_items_from_minutes
    },
    {
        "name": "get_deal_pipeline",
        "description": "Retrieve a list of investment projects for a specific TWG or the entire summit.",
        "parameters": {
            "twg_id": "Optional UUID of the TWG to filter by"
        },
        "coroutine": get_deal_pipeline
    }
]

# === Document & Minutes Search Tool Definitions (OpenAI format) ===

SEARCH_DOCUMENTS_TOOL_DEF = {
    "type": "function",
    "function": {
        "name": "search_documents",
        "description": "Search the document registry for files uploaded to the system. Use this whenever users ask about documents, reports, or files.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Keyword to search for in file names (optional)"
                },
                "document_type": {
                    "type": "string",
                    "description": "Filter by document type: 'minutes', 'brief', 'policy', 'memo', 'financial_model', 'esia', or leave empty for all"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results (default: 10)"
                }
            },
            "required": []
        }
    }
}

GET_MEETING_MINUTES_TOOL_DEF = {
    "type": "function",
    "function": {
        "name": "get_meeting_minutes",
        "description": "Retrieve meeting minutes from the database. Can fetch minutes for a specific meeting or list recent minutes for your TWG.",
        "parameters": {
            "type": "object",
            "properties": {
                "meeting_id": {
                    "type": "string",
                    "description": "UUID of a specific meeting to get minutes for (optional)"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results (default: 5)"
                }
            },
            "required": []
        }
    }
}
