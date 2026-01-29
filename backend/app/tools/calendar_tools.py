from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import json
from app.services.calendar_service import calendar_service


async def get_schedule(days: int = 7, twg_id: Optional[str] = None) -> str:
    """
    Fetch the calendar schedule for the next N days from the internal database.
    
    Args:
        days: Number of days to look ahead (default: 7)
        twg_id: Optional TWG ID to filter meetings by.
        
    Returns:
        JSON string of calendar events
    """
    from app.core.database import AsyncSessionLocal
    from app.models.models import Meeting
    from sqlalchemy import select, and_
    import uuid
    
    try:
        # Calculate time range
        # Use timezone-aware for accurate "today/tomorrow" labels
        from zoneinfo import ZoneInfo
        user_tz = ZoneInfo("Africa/Nairobi")
        now_tz = datetime.now(user_tz)
        
        # Convert to naive datetime for DB comparison (DB stores naive UTC datetimes)
        # But we still use now_tz for date label comparisons
        now = datetime.utcnow()
        end_date = now + timedelta(days=days)
        
        async with AsyncSessionLocal() as session:
            # Build query with optional TWG filter
            conditions = [
                Meeting.scheduled_at >= now,
                Meeting.scheduled_at <= end_date
            ]
            
            if twg_id:
                try:
                    # Validate UUID format
                    twg_uuid = uuid.UUID(twg_id)
                    conditions.append(Meeting.twg_id == twg_uuid)
                except ValueError:
                    return json.dumps({"error": f"Invalid TWG ID format: {twg_id}"})
            
            query = select(Meeting).where(and_(*conditions)).order_by(Meeting.scheduled_at)
            
            result = await session.execute(query)
            meetings = result.scalars().all()
            
            if not meetings:
                msg = "No upcoming meetings found"
                if twg_id:
                    msg += " for your TWG"
                return json.dumps({"message": msg + "."})
            
            # Fetch TWG names for better UX
            from app.models.models import TWG
            twg_names = {}
            if meetings:
                twg_ids = list(set([m.twg_id for m in meetings if m.twg_id]))
                if twg_ids:
                    twg_result = await session.execute(select(TWG).where(TWG.id.in_(twg_ids)))
                    twgs = twg_result.scalars().all()
                    for twg in twgs:
                        twg_names[str(twg.id)] = twg.name
            
            formatted_events = []
            # Use timezone-aware date for accurate today/tomorrow in user's timezone
            today = now_tz.date()
            tomorrow = today + timedelta(days=1)
            
            for meeting in meetings:
                # Determine human-readable date label
                # CRITICAL: meeting.scheduled_at is stored as naive UTC, convert to user TZ
                meeting_dt = meeting.scheduled_at
                if meeting_dt.tzinfo is None:
                    # Naive datetime - it's stored as UTC, so add UTC timezone
                    from datetime import timezone as tz
                    meeting_dt = meeting_dt.replace(tzinfo=tz.utc)
                
                # Convert to user timezone for comparison and display
                meeting_local = meeting_dt.astimezone(user_tz)
                meeting_date = meeting_local.date()
                    
                if meeting_date == today:
                    date_label = "TODAY"
                elif meeting_date == tomorrow:
                    date_label = "TOMORROW"
                else:
                    date_label = meeting_date.strftime("%A, %B %d")
                
                formatted_events.append({
                    "id": str(meeting.id),
                    "summary": meeting.title,
                    "date_label": date_label,
                    "start": meeting_local.strftime("%Y-%m-%d %I:%M %p EAT"),  # e.g. "2026-01-27 11:18 AM EAT"
                    "end": (meeting_local + timedelta(minutes=meeting.duration_minutes)).strftime("%I:%M %p EAT"),
                    "status": meeting.status.value if hasattr(meeting.status, 'value') else meeting.status,
                    "meet_link": meeting.video_link,
                    "location": meeting.location,
                    "twg_name": twg_names.get(str(meeting.twg_id), "Unknown TWG")
                })
            
            return json.dumps(formatted_events, indent=2)

    except Exception as e:
        return json.dumps({"error": f"Failed to fetch schedule from DB: {str(e)}"})

# Tool definition for LLM
GET_SCHEDULE_TOOL_DEF = {
    "type": "function",
    "function": {
        "name": "get_schedule",
        "description": "Get the calendar schedule and events for the upcoming days. Use this to answer questions about availability or agenda.",
        "parameters": {
            "type": "object",
            "properties": {
                "days": {
                    "type": "integer",
                    "description": "Number of days to look ahead (default 7)",
                    "default": 7
                },
                "twg_id": {
                    "type": "string",
                    "description": "Optional TWG UUID to filter meetings by. If not provided, returns all meetings (Supervisor only)."
                }
            },
            "required": []
        }
    }
}


async def get_past_meetings(days: int = 30, limit: int = 10, twg_id: Optional[str] = None) -> str:
    """
    Fetch past meetings from the internal database.
    
    Args:
        days: Number of days to look back (default: 30)
        limit: Maximum number of meetings to return (default: 10)
        twg_id: Optional TWG ID to filter meetings by.
        
    Returns:
        JSON string of past meeting events
    """
    from app.core.database import AsyncSessionLocal
    from app.models.models import Meeting
    from sqlalchemy import select, and_
    import uuid
    
    try:
        # Calculate time range
        from zoneinfo import ZoneInfo
        user_tz = ZoneInfo("Africa/Nairobi")
        now_tz = datetime.now(user_tz)
        
        # Convert to naive datetime for DB comparison
        now = datetime.utcnow()
        start_date = now - timedelta(days=days)
        
        async with AsyncSessionLocal() as session:
            # Build query with optional TWG filter
            conditions = [
                Meeting.scheduled_at < now,
                Meeting.scheduled_at >= start_date
            ]
            
            if twg_id:
                try:
                    # Validate UUID format
                    twg_uuid = uuid.UUID(twg_id)
                    conditions.append(Meeting.twg_id == twg_uuid)
                except ValueError:
                    return json.dumps({"error": f"Invalid TWG ID format: {twg_id}"})
            
            query = select(Meeting).where(and_(*conditions)).order_by(Meeting.scheduled_at.desc()).limit(limit)
            
            result = await session.execute(query)
            meetings = result.scalars().all()
            
            if not meetings:
                msg = f"No past meetings found in the last {days} days"
                if twg_id:
                    msg += " for your TWG"
                return json.dumps({"message": msg + "."})
            
            # Fetch TWG names for better UX
            from app.models.models import TWG
            twg_names = {}
            if meetings:
                twg_ids = list(set([m.twg_id for m in meetings if m.twg_id]))
                if twg_ids:
                    twg_result = await session.execute(select(TWG).where(TWG.id.in_(twg_ids)))
                    twgs = twg_result.scalars().all()
                    for twg in twgs:
                        twg_names[str(twg.id)] = twg.name
            
            formatted_events = []
            
            for meeting in meetings:
                # Determine human-readable date label
                meeting_dt = meeting.scheduled_at
                if meeting_dt.tzinfo is None:
                    from datetime import timezone as tz
                    meeting_dt = meeting_dt.replace(tzinfo=tz.utc)
                
                # Convert to user timezone for display
                meeting_local = meeting_dt.astimezone(user_tz)
                meeting_date = meeting_local.date()
                
                # Calculate days ago
                days_ago = (now_tz.date() - meeting_date).days
                if days_ago == 0:
                    date_label = "TODAY (earlier)"
                elif days_ago == 1:
                    date_label = "YESTERDAY"
                else:
                    date_label = f"{days_ago} days ago ({meeting_date.strftime('%A, %B %d')})"
                
                formatted_events.append({
                    "id": str(meeting.id),
                    "summary": meeting.title,
                    "date_label": date_label,
                    "start": meeting_local.strftime("%Y-%m-%d %I:%M %p EAT"),
                    "end": (meeting_local + timedelta(minutes=meeting.duration_minutes)).strftime("%I:%M %p EAT"),
                    "status": meeting.status.value if hasattr(meeting.status, 'value') else meeting.status,
                    "meet_link": meeting.video_link,
                    "location": meeting.location,
                    "twg_name": twg_names.get(str(meeting.twg_id), "Unknown TWG")
                })
            
            return json.dumps(formatted_events, indent=2)

    except Exception as e:
        return json.dumps({"error": f"Failed to fetch past meetings from DB: {str(e)}"})


GET_PAST_MEETINGS_TOOL_DEF = {
    "type": "function",
    "function": {
        "name": "get_past_meetings",
        "description": "Get past meetings and their history. Use this to answer questions about previous meetings, what was discussed, or meeting history.",
        "parameters": {
            "type": "object",
            "properties": {
                "days": {
                    "type": "integer",
                    "description": "Number of days to look back (default 30)",
                    "default": 30
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of meetings to return (default 10)",
                    "default": 10
                },
                "twg_id": {
                    "type": "string",
                    "description": "Optional TWG UUID to filter meetings by. If not provided, returns all meetings (Supervisor only)."
                }
            },
            "required": []
        }
    }
}



def update_meeting(
    meeting_id: str,
    new_title: Optional[str] = None,
    new_location: Optional[str] = None,
    is_virtual: Optional[bool] = None,
    new_time_iso: Optional[str] = None,
    new_duration: Optional[int] = None
) -> str:
    """
    Update an existing meeting in the database.
    
    Args:
        meeting_id: ID of the meeting to update (from calendar)
        new_title: New title (optional)
        new_location: New venue (e.g. "Virtual (Google Meet)" or "Conference Room 1")
        is_virtual: Whether it should be a virtual meeting (generates link if True)
        new_time_iso: New start time ISO 8601 (optional) (e.g. "2026-03-15T14:00:00")
        new_duration: New duration in minutes (optional)
        
    Returns:
        Status message indicating success or failure
    """
    from app.core.database import get_sync_db_session
    from app.models.models import Meeting
    from sqlalchemy import select
    import random
    import string
    from loguru import logger

    try:
        session = get_sync_db_session()
        try:
            stmt = select(Meeting).where(Meeting.id == meeting_id)
            meeting = session.execute(stmt).scalars().first()
            
            if not meeting:
                return f"Error: Meeting ID {meeting_id} not found."
            
            changes = []
            
            if new_title:
                meeting.title = new_title
                changes.append(f"Title -> {new_title}")
                
            if new_time_iso:
                try:
                    dt = datetime.fromisoformat(new_time_iso)
                    meeting.scheduled_at = dt
                    changes.append(f"Time -> {new_time_iso}")
                except ValueError:
                    return "Error: Invalid ISO format for time. Use YYYY-MM-DDTHH:MM:SS"

            if new_duration:
                meeting.duration_minutes = new_duration
                changes.append(f"Duration -> {new_duration}m")

            # Location Logic - Extract video links from location text
            if new_location:
                import re
                # Check if location contains a video meeting link
                video_patterns = [
                    r'(meet\.google\.com/[a-zA-Z0-9\-]+)',
                    r'(zoom\.us/[a-zA-Z0-9/\?\=\-]+)',
                    r'(teams\.microsoft\.com/[a-zA-Z0-9/\?\=\-\_]+)'
                ]
                
                extracted_link = None
                for pattern in video_patterns:
                    match = re.search(pattern, new_location)
                    if match:
                        extracted_link = match.group(1)
                        # Add https:// if not present
                        if not extracted_link.startswith('http'):
                            extracted_link = f"https://{extracted_link}"
                        break
                
                if extracted_link:
                    # We found a link embedded in the location - extract it
                    meeting.video_link = extracted_link
                    meeting.meeting_type = "virtual"
                    meeting.location = "Virtual (Google Meet)"
                    is_virtual = True  # Force virtual mode
                    changes.append(f"Location -> Virtual (Google Meet)")
                    changes.append(f"Video Link -> {extracted_link}")
                else:
                    meeting.location = new_location
                    changes.append(f"Location -> {new_location}")
                
                # Auto-infer virtual from location keywords if is_virtual not specified
                if is_virtual is None:
                    virtual_keywords = ["virtual", "online", "zoom", "meet", "teams"]
                    if any(k in new_location.lower() for k in virtual_keywords):
                        is_virtual = True
                        meeting.meeting_type = "virtual"

            # Virtual/Link Logic
            if is_virtual is True:
                meeting.meeting_type = "virtual"
                if not meeting.video_link:
                    # Generate link if missing
                    part1 = ''.join(random.choices(string.ascii_lowercase, k=3))
                    part2 = ''.join(random.choices(string.ascii_lowercase, k=4))
                    part3 = ''.join(random.choices(string.ascii_lowercase, k=3))
                    meeting.video_link = f"https://meet.google.com/{part1}-{part2}-{part3}"
                    changes.append(f"Video Link -> Generated ({meeting.video_link})")
                
                # If location is ambiguous or generic "Virtual", standardize it
                if not meeting.location or meeting.location.strip().lower() == "virtual":
                    meeting.location = "Virtual (Google Meet)"
                    if "Location ->" not in str(changes):
                        changes.append("Location -> Virtual (Google Meet)")

            elif is_virtual is False:
                # Switching to physical -> Clear link
                meeting.meeting_type = "in-person"
                meeting.video_link = None
                changes.append("Video Link -> Removed (Physical meeting)")

            if not changes:
                return "No changes provided. Meeting unchanged."
                
            session.commit()
            logger.info(f"[UPDATE_MEETING] Updated meeting {meeting_id}: {changes}")
            return f"✅ Meeting Updated Successfully: {', '.join(changes)}"
            
        finally:
            session.close()
    except Exception as e:
        logger.error(f"[UPDATE_MEETING] Error: {e}")
        return f"Error updating meeting: {str(e)}"


UPDATE_MEETING_TOOL_DEF = {
    "type": "function",
    "function": {
        "name": "update_meeting",
        "description": "Update an existing meeting. Use this to change the location, title, time, or convert between virtual and in-person meetings. IMPORTANT: You MUST call this tool to make any changes - do not just say you updated it without calling this tool.",
        "parameters": {
            "type": "object",
            "properties": {
                "meeting_id": {
                    "type": "string",
                    "description": "The ID of the meeting to update (from get_schedule results)"
                },
                "new_title": {
                    "type": "string",
                    "description": "New title for the meeting (optional)"
                },
                "new_location": {
                    "type": "string",
                    "description": "New venue/location (e.g. 'Virtual (Google Meet)' or 'Conference Room 1')"
                },
                "is_virtual": {
                    "type": "boolean",
                    "description": "Set to true for virtual meeting (generates video link), false for in-person"
                },
                "new_time_iso": {
                    "type": "string",
                    "description": "New start time in ISO 8601 format (e.g. '2026-03-15T14:00:00')"
                },
                "new_duration": {
                    "type": "integer",
                    "description": "New duration in minutes"
                }
            },
            "required": ["meeting_id"]
        }
    }
}
