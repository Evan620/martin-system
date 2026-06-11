"""Member personal-action tools (member toolset).

Today: rsvp_meeting, set_reminder, add_meeting_to_calendar, get_project_brief.

These run under the 'member' agent scope (tool_registry.MEMBER_TOOLS). The agent
loop auto-injects user_id/user_role from the authenticated session into any tool
that declares them (see app/agents/agent_loop.py), so every tool here always acts
on the *calling* member's own data (own RSVP / reminders / calendar invite).
twg_id is auto-injected the same way (registry/agent loop), scoping reads like
get_project_brief to the caller's own TWG deal room.
"""
import difflib
import uuid
from datetime import datetime, timezone
from typing import Optional

import pytz
from sqlalchemy import or_, select

# Imported at module level so tests can monkeypatch AsyncSessionLocal.
from app.core.database import AsyncSessionLocal
from app.models.models import (
    Meeting,
    MeetingParticipant,
    Project,
    ProjectStatus,
    Reminder,
    RsvpStatus,
    TWG,
    User,
    UserRole,
)
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


# ---------------------------------------------------------------------------
# set_reminder
# ---------------------------------------------------------------------------

SET_REMINDER_TOOL_DEF = {
    "type": "function",
    "function": {
        "name": "set_reminder",
        "description": (
            "Set a personal reminder for the current member ('remind me to X at Y'). "
            "Stores the reminder so the member is notified at the given time. "
            "remind_at_iso MUST be an ISO 8601 datetime (e.g. '2026-06-15T09:00:00'); "
            "give it in the member's LOCAL time — do NOT convert to UTC."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "What to remind the member about (their own words).",
                },
                "remind_at_iso": {
                    "type": "string",
                    "description": (
                        "When to remind, as an ISO 8601 datetime in the member's local "
                        "time, e.g. '2026-06-15T09:00:00'."
                    ),
                },
            },
            "required": ["message", "remind_at_iso"],
        },
    },
}


def _parse_remind_at_utc(remind_at_iso: str, user_timezone: Optional[str]) -> Optional[datetime]:
    """Parse an ISO 8601 datetime to NAIVE UTC (the reminders.remind_at convention).

    A naive input is interpreted in the member's timezone (auto-injected by the
    registry/agent loop) and falls back to UTC when no/invalid timezone is given.
    Returns None when the string doesn't parse.
    """
    raw = (remind_at_iso or "").strip()
    if not raw:
        return None
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None
    if dt.tzinfo is None:
        tz = None
        if user_timezone:
            try:
                tz = pytz.timezone(user_timezone)
            except Exception:
                tz = None
        dt = tz.localize(dt) if tz else dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


async def set_reminder(
    message: str,
    remind_at_iso: str,
    user_id: Optional[str] = None,
    user_role: Optional[UserRole] = None,
    user_timezone: Optional[str] = None,
) -> dict:
    """Create a Reminder row for the calling member. Returns a result/error dict."""
    text = (message or "").strip()
    if not text:
        return {"error": "The reminder message is empty — what should I remind you about?"}
    if not user_id:
        return {"error": "Could not identify the current member. Please retry from the app."}
    try:
        u_uuid = uuid.UUID(str(user_id))
    except (ValueError, TypeError):
        return {"error": "Invalid user id."}

    remind_at = _parse_remind_at_utc(remind_at_iso, user_timezone)
    if remind_at is None:
        return {
            "error": (
                f"I couldn't understand the reminder time '{remind_at_iso}'. "
                "Please use an ISO 8601 datetime like '2026-06-15T09:00:00'."
            )
        }
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
    if remind_at <= now_utc:
        return {"error": "That time is already in the past — please pick a future time for the reminder."}

    reminder = Reminder(
        user_id=u_uuid,
        message=text[:500],  # reminders.message is String(500)
        remind_at=remind_at,
        is_sent=False,
    )
    async with AsyncSessionLocal() as session:
        session.add(reminder)
        await session.commit()
        await session.refresh(reminder)

    return {
        "success": True,
        "reminder_id": str(reminder.id),
        "remind_at_utc": remind_at.isoformat() + "Z",
        "message": (
            f'Done — I\'ll remind you to "{text}" at '
            f"{_format_member_local(remind_at, user_timezone)}."
        ),
    }


# ---------------------------------------------------------------------------
# add_meeting_to_calendar
# ---------------------------------------------------------------------------

ADD_MEETING_TO_CALENDAR_TOOL_DEF = {
    "type": "function",
    "function": {
        "name": "add_meeting_to_calendar",
        "description": (
            "Email the current member a calendar invite (.ics attachment) for a meeting "
            "they participate in, so they can add it to their own calendar. "
            "Use the meeting_id returned by get_schedule."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "meeting_id": {
                    "type": "string",
                    "description": "The meeting's UUID (from get_schedule).",
                },
            },
            "required": ["meeting_id"],
        },
    },
}


def _format_member_local(dt_utc_naive: datetime, user_timezone: Optional[str]) -> str:
    """Format a naive-UTC datetime in the member's timezone (best-effort)."""
    aware = dt_utc_naive.replace(tzinfo=timezone.utc)
    if user_timezone:
        try:
            aware = aware.astimezone(pytz.timezone(user_timezone))
        except Exception:
            pass
    return aware.strftime("%A, %B %d, %Y at %I:%M %p %Z")


async def add_meeting_to_calendar(
    meeting_id: str,
    user_id: Optional[str] = None,
    user_role: Optional[UserRole] = None,
    user_timezone: Optional[str] = None,
) -> dict:
    """Send the calling member the .ics invite for a meeting they participate in.

    Being a participant IS the authorization — non-participants are denied.
    Reuses email_service.send_meeting_invite (Resend + .ics), no Google auth needed.
    """
    if not user_id:
        return {"error": "Could not identify the current member. Please retry from the app."}
    try:
        m_uuid = uuid.UUID(str(meeting_id))
        u_uuid = uuid.UUID(str(user_id))
    except (ValueError, TypeError):
        return {"error": "Invalid meeting or user id."}

    async with AsyncSessionLocal() as session:
        participant = (
            await session.execute(
                select(MeetingParticipant).where(
                    MeetingParticipant.meeting_id == m_uuid,
                    MeetingParticipant.user_id == u_uuid,
                )
            )
        ).scalar_one_or_none()
        if participant is None:
            return {"error": "You are not a participant of this meeting, so I can't send you its invite."}

        meeting = await session.get(Meeting, m_uuid)
        if meeting is None:
            return {"error": "Meeting not found."}

        user = await session.get(User, u_uuid)
        member_email = (user.email if user else None) or participant.email
        if not member_email:
            return {"error": "No email address on file for your account — please update your profile first."}

        twg = await session.get(TWG, meeting.twg_id) if meeting.twg_id else None
        twg_name = twg.name if twg else "TWG"
        title = meeting.title
        start_utc = meeting.scheduled_at  # naive UTC by convention
        duration = meeting.duration_minutes or 60
        location = meeting.location
        video_link = meeting.video_link

    from app.services.email_service import email_service

    try:
        await email_service.send_meeting_invite(
            to_emails=[member_email],
            subject=f"Meeting Invitation: {title}",
            template_name="meeting_invite.html",
            template_context={
                "title": title,
                "scheduled_time": _format_member_local(start_utc, user_timezone),
                "duration_minutes": duration,
                "twg_name": twg_name,
                "location": location,
                "video_link": video_link,
            },
            meeting_details={
                "title": title,
                "meeting_id": str(m_uuid),
                "start_time": start_utc,
                "duration": duration,
                "location": video_link or location,
            },
        )
    except Exception as e:
        return {"error": f"Could not send the calendar invite: {e}"}

    return {
        "success": True,
        "meeting_id": str(m_uuid),
        "message": (
            f'Calendar invite for "{title}" sent to {member_email} — '
            "open the attached invite.ics to add it to your calendar."
        ),
    }


# ---------------------------------------------------------------------------
# get_project_brief
# ---------------------------------------------------------------------------

GET_PROJECT_BRIEF_TOOL_DEF = {
    "type": "function",
    "function": {
        "name": "get_project_brief",
        "description": (
            "Get a concise brief of a project in the member's own TWG deal room: "
            "name, stage, sector, value, readiness score, location and a short "
            "description. Accepts the project's UUID or a (partial) project name, "
            "e.g. 'Bagre solar'."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "project": {
                    "type": "string",
                    "description": "The project's UUID or its (partial) name.",
                },
            },
            "required": ["project"],
        },
    },
}

# Identical for cross-TWG and nonexistent projects so the tool is not an
# existence oracle for other TWGs' deal flow (mirrors the 404-not-403 rule
# of /pipeline/{id}/interest).
_PROJECT_NOT_FOUND_MSG = (
    "I couldn't find a project matching '{project}' in your TWG's deal room. "
    "It may belong to another TWG, or the name may be spelled differently."
)


async def _resolve_member_twg_uuid(session, twg_id: str) -> Optional[uuid.UUID]:
    """Resolve the injected twg_id (UUID string, or a name like 'energy') to a UUID."""
    try:
        return uuid.UUID(str(twg_id))
    except (ValueError, TypeError):
        pass
    twg = (
        await session.execute(select(TWG).where(TWG.name.ilike(f"%{twg_id}%")))
    ).scalars().first()
    return twg.id if twg else None


async def _member_twg_pillar_value(session, twg_uuid: uuid.UUID) -> Optional[str]:
    """The caller's TWG pillar as a plain value string (enum-or-str safe).

    TWG.pillar is an Enum(TWGPillar) whose .value strings match Project.pillar
    strings (e.g. 'agriculture_food_systems').
    """
    twg = await session.get(TWG, twg_uuid)
    pillar = getattr(twg, "pillar", None) if twg else None
    if pillar is None:
        return None
    return pillar.value if hasattr(pillar, "value") else str(pillar)


def _project_in_member_scope(p: Project, twg_uuid: uuid.UUID, pillar_value: Optional[str]) -> bool:
    """Member visibility = TWG link OR TWG-pillar match — the SAME rule as
    GET /pipeline/member. PROD DATA REALITY: projects are systematically linked
    to the wrong TWG row, so the twg_id link alone hides the caller's own deals."""
    if p.twg_id == twg_uuid:
        return True
    return pillar_value is not None and p.pillar == pillar_value


def _humanize_label(raw: Optional[str]) -> Optional[str]:
    """'SUMMIT_READY' / 'energy_infrastructure' → 'Summit ready' / 'Energy infrastructure'."""
    if not raw:
        return None
    return raw.replace("_", " ").strip().capitalize()


def _short_description(text: Optional[str], max_sentences: int = 2, max_chars: int = 320) -> Optional[str]:
    """First 1-2 sentences of the description, capped for a concise brief."""
    cleaned = " ".join((text or "").split())
    if not cleaned:
        return None
    sentences, rest = [], cleaned
    for _ in range(max_sentences):
        head, dot, rest = rest.partition(". ")
        sentences.append(head if (dot or head.endswith(".")) else head)
        if not rest:
            break
    short = " ".join(s if s.endswith(".") else f"{s}." for s in sentences if s)
    return short[: max_chars - 1].rstrip() + "…" if len(short) > max_chars else short


def _build_project_brief(p: Project) -> str:
    """Concise member-safe text brief — NO key contacts / financing internals."""
    stage = _humanize_label(p.status.value if p.status else None)
    header = f"{p.name} — {stage}" if stage else p.name

    meta = []
    sector = _humanize_label(p.pillar)
    if sector:
        meta.append(f"Sector: {sector}")
    if p.investment_size is not None:
        meta.append(f"Value: {p.currency or 'USD'} {p.investment_size:,.0f}")
    if p.readiness_score is not None:
        meta.append(f"Readiness score: {p.readiness_score:g}")
    location = p.lead_country or p.site_location_name
    if location:
        meta.append(f"Location: {location}")

    lines = [header]
    if meta:
        lines.append(" · ".join(meta))
    description = _short_description(p.description)
    if description:
        lines.append(description)
    return "\n".join(lines)


async def get_project_brief(
    project: str,
    twg_id: Optional[str] = None,
    user_id: Optional[str] = None,
    user_role: Optional[UserRole] = None,
) -> dict:
    """Return a concise brief for a project in the CALLER's TWG deal room.

    `project` is a UUID or a fuzzy (partial) name; resolution is strictly scoped
    to the injected twg_id, so cross-TWG and unknown projects are indistinguishable
    (same friendly not-found message — no leak).
    """
    query = (project or "").strip()
    if not query:
        return {"error": "Which project? Give me its name (or id) and I'll pull up the brief."}
    if not twg_id:
        return {"error": "Could not determine your TWG scope. Please retry from the app."}

    async with AsyncSessionLocal() as session:
        twg_uuid = await _resolve_member_twg_uuid(session, twg_id)
        if twg_uuid is None:
            return {"error": "Could not determine your TWG scope. Please retry from the app."}
        pillar_value = await _member_twg_pillar_value(session, twg_uuid)

        # 1) Exact id — must ALSO be in the caller's scope (twg link OR twg
        #    pillar, same rule as /pipeline/member; else: generic not-found).
        try:
            project_uuid = uuid.UUID(query)
        except (ValueError, TypeError):
            project_uuid = None
        if project_uuid is not None:
            p = await session.get(Project, project_uuid)
            if (
                p is None
                or not _project_in_member_scope(p, twg_uuid, pillar_value)
                or p.status == ProjectStatus.ARCHIVED
            ):
                return {"error": _PROJECT_NOT_FOUND_MSG.format(project=query)}
            return {"success": True, "project_id": str(p.id), "brief": _build_project_brief(p)}

        # 2) Fuzzy name — searched ONLY within the caller's scope (twg-or-pillar).
        scope_clause = Project.twg_id == twg_uuid
        if pillar_value is not None:
            scope_clause = or_(scope_clause, Project.pillar == pillar_value)
        candidates = (
            await session.execute(
                select(Project).where(
                    scope_clause,
                    Project.status != ProjectStatus.ARCHIVED,
                )
            )
        ).scalars().all()

        matches = [p for p in candidates if query.lower() in (p.name or "").lower()]
        if not matches:
            by_name = {p.name: p for p in candidates if p.name}
            close = difflib.get_close_matches(query, list(by_name), n=1, cutoff=0.6)
            matches = [by_name[close[0]]] if close else []
        if not matches:
            return {"error": _PROJECT_NOT_FOUND_MSG.format(project=query)}
        if len(matches) > 1:
            exact = [p for p in matches if (p.name or "").lower() == query.lower()]
            if len(exact) == 1:
                matches = exact
            else:
                names = ", ".join(sorted(p.name for p in matches)[:5])
                return {"error": f"I found several projects matching '{query}': {names}. Which one do you mean?"}

        p = matches[0]
        return {"success": True, "project_id": str(p.id), "brief": _build_project_brief(p)}
