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
from app.models.models import TWG, Meeting, ActionItem, ActionItemStatus, Project, User, Document, Minutes, MeetingParticipant, RsvpStatus, UserRole, twg_members
from sqlalchemy import and_
from sqlalchemy.orm import selectinload

logger = logging.getLogger(__name__)

async def get_twg_info(twg_id: uuid.UUID) -> Dict[str, Any]:
    """
    Fetch comprehensive details about a specific Technical Working Group.
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(TWG).where(TWG.id == twg_id).options(selectinload(TWG.members))
        )
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

async def get_twg_members(twg_id: Optional[str] = None, twg_name: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Fetch all members of a specific Technical Working Group with their names and email addresses.
    Use this tool when you need to send emails to TWG members or look up who belongs to a TWG.
    Accepts either a twg_id (UUID) or twg_name (e.g. "energy", "agriculture") to find the TWG.
    """
    if not twg_id and not twg_name:
        return [{"error": "Provide either twg_id or twg_name"}]
    async with AsyncSessionLocal() as session:
        if twg_id:
            # Try UUID lookup first
            try:
                result = await session.execute(
                    select(TWG).where(TWG.id == uuid.UUID(twg_id)).options(selectinload(TWG.members))
                )
            except (ValueError, AttributeError):
                # twg_id wasn't a valid UUID — treat it as a name search
                result = await session.execute(
                    select(TWG).where(TWG.name.ilike(f"%{twg_id}%")).options(selectinload(TWG.members))
                )
        else:
            result = await session.execute(
                select(TWG).where(TWG.name.ilike(f"%{twg_name}%")).options(selectinload(TWG.members))
            )
        twg = result.scalars().first()
        if not twg:
            return [{"error": f"TWG not found. Use a name like 'energy', 'agriculture', 'minerals', 'digital', 'protocol', or 'resource'."}]

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
    twg_id: str,
    title: str,
    scheduled_at: str,
    location: str = "Virtual",
    duration: int = 60,
    timezone: str = "Africa/Nairobi"
) -> Dict[str, Any]:
    """
    [WHEN] User asks to create/schedule a meeting for a TWG.
    [WHAT] Creates meeting in DB, auto-adds TWG members as participants, returns meeting ID.
    [IMPORTANT] scheduled_at MUST be in the user's LOCAL time (e.g. '2026-03-02T16:00:00' for 4pm).
    The timezone param tells the system which timezone that time is in (default: Africa/Nairobi = EAT).
    Do NOT pre-convert to UTC — the tool handles conversion internally.
    twg_id can be a UUID or a TWG name like 'energy', 'agriculture', 'minerals', 'digital', 'protocol', 'resource_mobilization'.
    [EXAMPLE] create_meeting_invite(twg_id='energy', title='Weekly Sync', scheduled_at='2026-03-02T16:00:00', timezone='Africa/Nairobi')
    """
    # Resolve twg_id: accept UUID string or TWG name
    resolved_twg_id = None
    if isinstance(twg_id, str):
        try:
            resolved_twg_id = uuid.UUID(twg_id)
        except ValueError:
            # Not a UUID — try name lookup
            async with AsyncSessionLocal() as session:
                from app.models.models import TWG as TWGModel
                result = await session.execute(
                    select(TWGModel).where(TWGModel.name.ilike(f"%{twg_id}%"))
                )
                twg_obj = result.scalars().first()
                if twg_obj:
                    resolved_twg_id = twg_obj.id
                else:
                    return {"error": f"TWG '{twg_id}' not found. Use: energy, agriculture, minerals, digital, protocol, or resource_mobilization."}
    else:
        resolved_twg_id = twg_id

    twg_id = resolved_twg_id
    if isinstance(scheduled_at, str):
        from dateutil import parser as dateutil_parser
        scheduled_at = dateutil_parser.parse(scheduled_at)
    if isinstance(duration, str):
        duration = int(duration)

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

        # Auto-add SECRETARIAT_LEAD users as participants
        sec_result = await session.execute(
            select(User).where(and_(User.role == UserRole.SECRETARIAT_LEAD, User.is_active == True))
        )
        added_user_ids = set()
        for sec_user in sec_result.scalars().all():
            session.add(MeetingParticipant(
                id=uuid.uuid4(), meeting_id=new_meeting.id,
                user_id=sec_user.id, rsvp_status=RsvpStatus.ACCEPTED,
            ))
            added_user_ids.add(sec_user.id)

        # Auto-add TWG members as participants
        member_result = await session.execute(
            select(User).join(twg_members, twg_members.c.user_id == User.id).where(
                and_(twg_members.c.twg_id == twg_id, User.is_active == True)
            )
        )
        for member in member_result.scalars().all():
            if member.id not in added_user_ids:
                session.add(MeetingParticipant(
                    id=uuid.uuid4(), meeting_id=new_meeting.id,
                    user_id=member.id, rsvp_status=RsvpStatus.PENDING,
                ))

        await session.commit()

        # Auto-generate Google Meet link for virtual meetings
        # Gated by MEETING_AUTO_INVITES_ENABLED so testing doesn't create real
        # calendar events with attached attendees.
        from app.core.config import settings as _cfg
        if _cfg.MEETING_AUTO_INVITES_ENABLED and not video_link and cleaned_location and 'virtual' in cleaned_location.lower():
            try:
                import asyncio
                from app.services.calendar_service import calendar_service

                # Gather attendee emails
                all_participants = await session.execute(
                    select(User.email).join(
                        MeetingParticipant, MeetingParticipant.user_id == User.id
                    ).where(MeetingParticipant.meeting_id == new_meeting.id)
                )
                attendee_emails = [row[0] for row in all_participants.all() if row[0]]

                loop = asyncio.get_running_loop()
                event = await loop.run_in_executor(
                    None,
                    lambda: calendar_service.create_meeting_event(
                        title=title,
                        start_time=utc_dt,
                        duration_minutes=duration,
                        description=f"Generated by Martin AI. ID: {new_meeting.id}",
                        attendees=attendee_emails,
                        meeting_id=str(new_meeting.id)
                    )
                )
                if event and (event.get('hangoutLink') or event.get('htmlLink')):
                    video_link = event.get('hangoutLink') or event.get('htmlLink')
                    new_meeting.video_link = video_link
                    await session.commit()
                    logger.info(f"Auto-generated Meet link for meeting {new_meeting.id}: {video_link}")
            except Exception as e:
                logger.warning(f"Could not auto-generate Meet link: {e}. Background job will retry.")

        # Auto-send invitation emails to all participants
        # Gated by MEETING_AUTO_INVITES_ENABLED so testing doesn't email people.
        if not _cfg.MEETING_AUTO_INVITES_ENABLED:
            logger.info(f"[create_meeting_invite] MEETING_AUTO_INVITES_ENABLED=False — skipping invite emails for meeting {new_meeting.id}")
            return {
                "meeting_id": str(new_meeting.id),
                "status": "created",
                "video_link": video_link,
                "scheduled_utc": utc_dt.isoformat(),
                "scheduled_local": local_dt.strftime('%Y-%m-%d %H:%M %Z'),
                "invites_sent": 0,
                "invite_text_hint": f"(test mode) Would have invited participants to {title} on {local_dt.strftime('%Y-%m-%d %H:%M %Z')}",
            }
        try:
            from app.services.email_service import email_service

            # Get TWG name for the email
            twg_result = await session.execute(select(TWG).where(TWG.id == twg_id))
            twg_obj = twg_result.scalar_one_or_none()
            twg_display_name = twg_obj.name if twg_obj else "TWG"

            # Get all participant emails
            p_result = await session.execute(
                select(User.email).join(
                    MeetingParticipant, MeetingParticipant.user_id == User.id
                ).where(MeetingParticipant.meeting_id == new_meeting.id)
            )
            invite_emails = [row[0] for row in p_result.all() if row[0]]

            if invite_emails:
                await email_service.send_meeting_invite(
                    to_emails=invite_emails,
                    subject=f"Meeting Invitation: {title}",
                    template_name="meeting_invite.html",
                    template_context={
                        "title": title,
                        "scheduled_time": local_dt.strftime('%A, %B %d, %Y at %I:%M %p %Z'),
                        "duration_minutes": duration,
                        "twg_name": twg_display_name,
                        "location": cleaned_location,
                        "video_link": video_link,
                    },
                    meeting_details={
                        "title": title,
                        "meeting_id": str(new_meeting.id),
                        "start_time": utc_dt,
                        "duration": duration,
                        "location": video_link or cleaned_location,
                    }
                )
                logger.info(f"Sent meeting invites to {len(invite_emails)} participants for meeting {new_meeting.id}")
        except Exception as e:
            logger.warning(f"Could not send meeting invites: {e}")

        return {
            "meeting_id": str(new_meeting.id),
            "status": "created",
            "video_link": video_link,
            "scheduled_utc": utc_dt.isoformat(),
            "scheduled_local": local_dt.strftime('%Y-%m-%d %H:%M %Z'),
            "invites_sent": len(invite_emails) if 'invite_emails' in dir() else 0,
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

async def get_action_items(
    twg_id: Optional[str] = None,
    status: Optional[str] = None,
    owner_email: Optional[str] = None,
    limit: int = 20
) -> List[Dict[str, Any]]:
    """
    Query action items for a TWG. Supports filtering by status and owner email.
    """
    async with AsyncSessionLocal() as session:
        query = (
            select(ActionItem)
            .options(
                selectinload(ActionItem.owner),
                selectinload(ActionItem.meeting)
            )
        )

        if twg_id:
            try:
                query = query.where(ActionItem.twg_id == uuid.UUID(twg_id))
            except ValueError:
                return [{"error": f"Invalid twg_id: {twg_id}"}]

        if status:
            try:
                status_enum = ActionItemStatus(status.upper())
                query = query.where(ActionItem.status == status_enum)
            except ValueError:
                return [{"error": f"Invalid status: {status}. Use PENDING, IN_PROGRESS, COMPLETED, or OVERDUE"}]

        if owner_email:
            query = query.join(User, ActionItem.owner_id == User.id).where(User.email.ilike(f"%{owner_email}%"))

        query = query.order_by(ActionItem.created_at.desc()).limit(limit)

        result = await session.execute(query)
        items = result.scalars().all()

        return [
            {
                "id": str(item.id),
                "description": item.description,
                "owner": item.owner.full_name if item.owner else "Unassigned",
                "owner_email": item.owner.email if item.owner else None,
                "due_date": item.due_date.isoformat() if item.due_date else None,
                "status": item.status.value,
                "priority": item.priority.value if item.priority else "medium",
                "meeting_title": item.meeting.title if item.meeting else None,
                "created_at": item.created_at.isoformat() if item.created_at else None,
            }
            for item in items
        ]


async def update_action_item_status(
    action_item_id: str,
    status: str
) -> Dict[str, Any]:
    """
    Update the status of an action item with transition validation.
    """
    from app.core.action_item_constants import VALID_STATUS_TRANSITIONS

    async with AsyncSessionLocal() as session:
        try:
            item_uuid = uuid.UUID(action_item_id)
        except ValueError:
            return {"error": f"Invalid action_item_id: {action_item_id}"}

        result = await session.execute(select(ActionItem).where(ActionItem.id == item_uuid))
        item = result.scalar_one_or_none()

        if not item:
            return {"error": "Action item not found"}

        try:
            new_status = ActionItemStatus(status.upper())
        except ValueError:
            return {"error": f"Invalid status: {status}. Use PENDING, IN_PROGRESS, COMPLETED, or OVERDUE"}

        old_status = item.status
        allowed = VALID_STATUS_TRANSITIONS.get(old_status, set())
        if new_status not in allowed:
            return {"error": f"Invalid transition: {old_status.value} → {new_status.value}. Allowed: {[s.value for s in allowed]}"}

        item.status = new_status
        if new_status == ActionItemStatus.COMPLETED:
            item.completed_at = datetime.utcnow()

        await session.commit()

        return {
            "success": True,
            "action_item_id": str(item.id),
            "old_status": old_status.value,
            "new_status": new_status.value,
            "description": item.description[:100],
        }


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
    Searches TWG-scoped documents first, then includes global documents.
    """
    if isinstance(twg_id, str):
        try:
            twg_id = uuid.UUID(twg_id)
        except ValueError:
            twg_id = None

    async with AsyncSessionLocal() as session:
        from sqlalchemy import or_

        stmt = select(Document).where(Document.is_confidential == False)

        # Strict TWG scoping: agents only see their own TWG's documents
        if twg_id:
            stmt = stmt.where(Document.twg_id == twg_id)

        if query:
            stmt = stmt.where(
                or_(
                    Document.file_name.ilike(f"%{query}%"),
                    Document.category.ilike(f"%{query}%"),
                )
            )

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
                "twg_id": str(d.twg_id) if d.twg_id else "global",
                "created_at": d.created_at.isoformat() if d.created_at else None,
                "version": d.version,
            }
            for d in docs
        ]


async def retrieve_document_content(
    query: str,
    document_id: Optional[str] = None,
    twg_id: Optional[uuid.UUID] = None,
    top_k: int = 5
) -> Dict[str, Any]:
    """
    Retrieve actual document content from Pinecone vector store.
    Use when user asks about the contents/details of a specific document,
    or wants to know what a document says.
    """
    import asyncio
    from app.core.knowledge_base import get_knowledge_base

    try:
        kb = get_knowledge_base()
    except Exception as e:
        return {"error": f"Knowledge base unavailable: {e}"}

    # Determine namespace
    if twg_id:
        namespace = f"twg-{twg_id}"
    else:
        namespace = "twg-general"

    # Build metadata filter for specific document
    filter_dict = None
    if document_id:
        # Strip any UUID formatting issues
        doc_id_clean = str(document_id).strip()
        filter_dict = {"doc_id": doc_id_clean}

    try:
        results = await asyncio.to_thread(
            kb.search,
            query=query,
            namespace=namespace,
            top_k=top_k,
            filter=filter_dict
        )

        # If no results in TWG namespace and no specific twg_id was forced, try twg-general
        if not results and twg_id:
            results = await asyncio.to_thread(
                kb.search,
                query=query,
                namespace="twg-general",
                top_k=top_k,
                filter=filter_dict
            )

        if not results:
            return {
                "message": "No content found. The document may not have been ingested into the knowledge base yet.",
                "suggestion": "Use search_documents to check if the document exists in the registry, then ask an admin to ingest it."
            }

        # Format results with actual text content
        chunks = []
        for r in results:
            meta = r.get("metadata", {})
            chunks.append({
                "text": meta.get("text", ""),
                "source": meta.get("file_name", meta.get("filename", "Unknown")),
                "chunk_index": meta.get("chunk_index", 0),
                "total_chunks": meta.get("total_chunks", 0),
                "relevance": round(r.get("score", 0), 3),
            })

        # Sort by chunk_index for reading order (if from same doc)
        chunks.sort(key=lambda c: c["chunk_index"])

        return {
            "document_source": chunks[0]["source"] if chunks else "Unknown",
            "chunks_retrieved": len(chunks),
            "content": chunks,
        }

    except Exception as e:
        logger.error(f"retrieve_document_content error: {e}")
        return {"error": f"Failed to retrieve document content: {str(e)}"}


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
            if isinstance(twg_id, str):
                twg_id = uuid.UUID(twg_id)
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
        "description": "Search the document registry for files uploaded to the system. Use when the user asks about documents, reports, files, policies, or briefs. Returns JSON array of documents with: id, file_name, document_type, category, created_at, version. Example: User asks 'do we have any policy documents?' → call search_documents(document_type='policy'). User asks 'show me minutes' → call search_documents(document_type='minutes').",
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

RETRIEVE_DOCUMENT_CONTENT_TOOL_DEF = {
    "type": "function",
    "function": {
        "name": "retrieve_document_content",
        "description": "[WHEN] User asks what a document says, its contents, or details about a specific document. [WHAT] Searches Pinecone vector store and returns actual text content from ingested documents. [EXAMPLE] User asks 'what does the government support letter say?' → retrieve_document_content(query='government support letter'). User asks 'tell me about document b9ba3d0f...' → retrieve_document_content(query='government support letter', document_id='b9ba3d0f-...'). ALWAYS try this tool when user wants to READ a document, not just find it.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Describe what you want to find in the document (e.g. 'government support letter contents')"
                },
                "document_id": {
                    "type": "string",
                    "description": "Optional document UUID to retrieve specific document chunks"
                },
                "top_k": {
                    "type": "integer",
                    "description": "Number of text chunks to retrieve (default: 5, max: 10)"
                }
            },
            "required": ["query"]
        }
    }
}

GET_MEETING_MINUTES_TOOL_DEF = {
    "type": "function",
    "function": {
        "name": "get_meeting_minutes",
        "description": "Retrieve meeting minutes from the database. Use when the user asks about meeting minutes, decisions made, session records, or what was discussed. Returns JSON array with: meeting_id, meeting_title, scheduled_at, minutes_status, content_preview, key_decisions. Example: User asks 'show me the latest minutes' → call get_meeting_minutes(limit=3). User asks 'what was decided in the last Energy meeting?' → call get_meeting_minutes(meeting_id='...').",
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

GET_ACTION_ITEMS_TOOL_DEF = {
    "type": "function",
    "function": {
        "name": "get_action_items",
        "description": "Query action items for the TWG. Use when user asks about tasks, action items, to-dos, or what needs to be done. Returns JSON array with id, description, owner, due_date, status, priority. Example: User asks 'what are my pending tasks?' → call get_action_items(status='PENDING'). User asks 'show overdue items' → call get_action_items(status='OVERDUE').",
        "parameters": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "description": "Filter by status: PENDING, IN_PROGRESS, COMPLETED, OVERDUE (optional)"
                },
                "owner_email": {
                    "type": "string",
                    "description": "Filter by owner email address (optional)"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results (default: 20)"
                }
            },
            "required": []
        }
    }
}

UPDATE_ACTION_ITEM_STATUS_TOOL_DEF = {
    "type": "function",
    "function": {
        "name": "update_action_item_status",
        "description": "Update status of an action item. Use when user asks to mark a task as done/complete/in-progress. Valid transitions: PENDING→IN_PROGRESS, PENDING→COMPLETED, IN_PROGRESS→COMPLETED, OVERDUE→IN_PROGRESS, OVERDUE→COMPLETED. COMPLETED is terminal. ALWAYS call get_action_items first to get the action_item_id before updating.",
        "parameters": {
            "type": "object",
            "properties": {
                "action_item_id": {
                    "type": "string",
                    "description": "UUID of the action item to update"
                },
                "status": {
                    "type": "string",
                    "description": "New status: PENDING, IN_PROGRESS, COMPLETED"
                }
            },
            "required": ["action_item_id", "status"]
        }
    }
}
