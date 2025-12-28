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

from backend.app.core.database import AsyncSessionLocal
from backend.app.models.models import TWG, Meeting, ActionItem, Project, User

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
    duration: int = 60
) -> Dict[str, Any]:
    """
    Create a new meeting entry in the database.
    """
    async with AsyncSessionLocal() as session:
        new_meeting = Meeting(
            twg_id=twg_id,
            title=title,
            scheduled_at=scheduled_at,
            location=location,
            duration_minutes=duration
        )
        session.add(new_meeting)
        await session.commit()
        await session.refresh(new_meeting)
        
        return {
            "meeting_id": str(new_meeting.id),
            "status": "created",
            "invite_text_hint": f"Invitation for {title} on {scheduled_at.strftime('%Y-%m-%d %H:%M')}"
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
            "duration": "Duration in minutes (default: 60)"
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
