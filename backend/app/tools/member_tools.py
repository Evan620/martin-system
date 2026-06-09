"""Member personal-action tools (member toolset). Today: rsvp_meeting.

These run under the 'member' agent scope (tool_registry.MEMBER_TOOLS). The agent
loop auto-injects user_id/user_role from the authenticated session into any tool
that declares them (see app/agents/agent_loop.py), so rsvp_meeting always acts on
the *calling* member's own participant row.
"""
import uuid
from typing import Optional

# Imported at module level so tests can monkeypatch AsyncSessionLocal.
from app.core.database import AsyncSessionLocal
from app.models.models import RsvpStatus, UserRole
from app.services.rsvp_service import apply_member_rsvp

# Accept both the canonical enum names and friendly synonyms Martin might pass.
_RSVP_MAP = {
    "ACCEPTED": RsvpStatus.ACCEPTED, "GOING": RsvpStatus.ACCEPTED, "YES": RsvpStatus.ACCEPTED,
    "DECLINED": RsvpStatus.DECLINED, "NO": RsvpStatus.DECLINED, "DECLINE": RsvpStatus.DECLINED,
    "TENTATIVE": RsvpStatus.TENTATIVE, "MAYBE": RsvpStatus.TENTATIVE,
}

RSVP_MEETING_TOOL_DEF = {
    "type": "function",
    "function": {
        "name": "rsvp_meeting",
        "description": (
            "RSVP to a meeting on behalf of the current member (Going / Maybe / No). "
            "Use the meeting_id returned by get_schedule."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "meeting_id": {"type": "string", "description": "The meeting's UUID (from get_schedule)."},
                "response": {
                    "type": "string",
                    "enum": ["GOING", "MAYBE", "NO"],
                    "description": "The member's RSVP: Going, Maybe, or No.",
                },
            },
            "required": ["meeting_id", "response"],
        },
    },
}


async def rsvp_meeting(
    meeting_id: str,
    response: str,
    user_id: Optional[str] = None,
    user_role: Optional[UserRole] = None,
) -> dict:
    """Set the calling member's RSVP on a meeting. Returns a result/error dict."""
    status = _RSVP_MAP.get((response or "").strip().upper())
    if status is None:
        return {"error": f"Unknown RSVP response '{response}'. Use Going, Maybe, or No."}
    if not user_id:
        return {"error": "Could not identify the current member. Please retry from the app."}
    try:
        m_uuid = uuid.UUID(str(meeting_id))
        u_uuid = uuid.UUID(str(user_id))
    except (ValueError, TypeError):
        return {"error": "Invalid meeting or user id."}

    async with AsyncSessionLocal() as session:
        participant = await apply_member_rsvp(session, m_uuid, u_uuid, status)

    if participant is None:
        return {"error": "You are not a participant of this meeting."}
    return {"success": True, "meeting_id": str(meeting_id), "rsvp_status": status.value}
