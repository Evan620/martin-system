"""Member personal-action tools (member toolset).

Today: rsvp_meeting, set_reminder, add_meeting_to_calendar, get_project_brief,
list_my_deals.

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
from sqlalchemy import desc, or_, select

# Imported at module level so tests can monkeypatch AsyncSessionLocal.
from app.core.database import AsyncSessionLocal
from app.models.models import (
    Meeting,
    MeetingParticipant,
    Project,
    ProjectScoreDetail,
    ProjectStatus,
    Reminder,
    RsvpStatus,
    ScoringCriteria,
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
            "name, stage, sector, value, readiness score, location, a short "
            "description, plus — when on file — subsector, investment stage, "
            "sponsor, financing structure, climate impact, smallholder reach and "
            "technical studies. Accepts the project's UUID or a (partial) project "
            "name, e.g. 'Bagre solar'. Set include_scores=true for the "
            "per-criterion score breakdown."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "project": {
                    "type": "string",
                    "description": "The project's UUID or its (partial) name.",
                },
                "include_scores": {
                    "type": "boolean",
                    "description": (
                        "Set true to append the per-criterion score breakdown "
                        "(criterion, weight, score)."
                    ),
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


def _one_line(text: Optional[str], max_chars: int = 200) -> Optional[str]:
    """Collapse a (possibly long, multi-line) text field to one ~200-char line."""
    cleaned = " ".join((text or "").split())
    if not cleaned:
        return None
    return cleaned[: max_chars - 1].rstrip() + "…" if len(cleaned) > max_chars else cleaned


async def _member_score_lines(session, project_id: uuid.UUID) -> list:
    """Member-safe score breakdown lines: 'Criterion (weight%): score', weight
    desc — criterion/weight/score ONLY, mirroring ProjectMemberDetail's
    score_breakdown. ProjectScoreDetail.notes and the scorer's identity are
    facilitator-only and are NEVER selected here."""
    rows = (
        await session.execute(
            select(ScoringCriteria.criterion_name, ScoringCriteria.weight, ProjectScoreDetail.score)
            .join(ScoringCriteria, ProjectScoreDetail.criterion_id == ScoringCriteria.id)
            .where(ProjectScoreDetail.project_id == project_id)
            .order_by(desc(ScoringCriteria.weight))
        )
    ).all()
    lines = []
    for name, weight, score in rows:
        w = float(weight or 0)
        pct = w * 100 if w <= 1 else w  # weights stored as fractions (0.18) or points (2.0)
        lines.append(f"- {name} ({pct:g}%): {float(score):g}")
    return lines


def _build_project_brief(p: Project, score_lines: Optional[list] = None) -> str:
    """Concise member-safe text brief — NO key contacts / financing internals
    (never key_contact_*, assigned_agent, metadata_json, approval fields,
    deal_room_priority, site coords, revenue_model, macroeconomic_roi,
    funding_secured_usd). score_lines: None = not requested; [] = unscored."""
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

    # Member-safe extras (same set ProjectMemberDetail exposes) — only when on
    # file, each capped to one ~200-char line so the brief stays well under the
    # agent loop's 3000-char tool-result cap.
    for label, value in (
        ("Subsector", _one_line(p.subsector)),
        ("Investment stage", _one_line(p.investment_stage_label)),
        ("Sponsor", _one_line(p.project_sponsor)),
        ("Financing structure", _one_line(p.financing_structure)),
        ("Climate impact", _one_line(p.climate_impact)),
        ("Smallholder farmers reached", _one_line(p.smallholder_farmers_reached)),
        ("Technical studies", _one_line(p.technical_studies)),
    ):
        if value:
            lines.append(f"{label}: {value}")

    if score_lines is not None:
        if score_lines:
            lines.append("Score breakdown:")
            lines.extend(score_lines)
        else:
            lines.append("Score breakdown: not yet scored.")
    return "\n".join(lines)


def _coerce_bool(value) -> bool:
    """LLMs sometimes pass booleans as strings — accept 'true'/'1'/'yes'."""
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "y"}
    return bool(value)


async def get_project_brief(
    project: str,
    include_scores: bool = False,
    twg_id: Optional[str] = None,
    user_id: Optional[str] = None,
    user_role: Optional[UserRole] = None,
) -> dict:
    """Return a concise brief for a project in the CALLER's TWG deal room.

    `project` is a UUID or a fuzzy (partial) name; resolution is strictly scoped
    to the injected twg_id, so cross-TWG and unknown projects are indistinguishable
    (same friendly not-found message — no leak). include_scores appends the
    member-safe per-criterion breakdown (criterion/weight/score — never notes
    or scorer identity).
    """
    query = (project or "").strip()
    want_scores = _coerce_bool(include_scores)
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
            score_lines = await _member_score_lines(session, p.id) if want_scores else None
            return {"success": True, "project_id": str(p.id), "brief": _build_project_brief(p, score_lines)}

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
        score_lines = await _member_score_lines(session, p.id) if want_scores else None
        return {"success": True, "project_id": str(p.id), "brief": _build_project_brief(p, score_lines)}


# ---------------------------------------------------------------------------
# list_my_deals
# ---------------------------------------------------------------------------

LIST_MY_DEALS_TOOL_DEF = {
    "type": "function",
    "function": {
        "name": "list_my_deals",
        "description": (
            "List and count the projects in the member's own TWG deal room: the "
            "total, counts per stage, and a compact row per deal (name, stage, "
            "sector, value, score, location). Optionally filter by stage "
            "(fuzzy — e.g. 'summit ready', 'pipeline', 'in negotiation') and cap "
            "the number of rows. Use get_project_brief for one project's detail."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "stage": {
                    "type": "string",
                    "description": (
                        "Optional stage filter, fuzzy — e.g. 'summit ready', "
                        "'pipeline', 'incubation', 'in negotiation'."
                    ),
                },
                "limit": {
                    "type": "integer",
                    "description": "Max deal rows to list (default 20, max 30).",
                },
            },
            "required": [],
        },
    },
}

_LIST_DEALS_DEFAULT_LIMIT = 20
_LIST_DEALS_MAX_LIMIT = 30
# Keep the whole payload comfortably under the agent loop's 3000-char cap.
_LIST_DEALS_CHAR_BUDGET = 2600


def _match_stage(stage: str) -> Optional[ProjectStatus]:
    """Fuzzy stage resolution: 'summit ready' / 'Summit-Ready' / 'SUMMIT_READY'
    → ProjectStatus.SUMMIT_READY. Returns None when nothing matches."""
    raw = " ".join((stage or "").replace("_", " ").replace("-", " ").lower().split())
    if not raw:
        return None
    by_label = {s.value.lower().replace("_", " "): s for s in ProjectStatus}
    if raw in by_label:
        return by_label[raw]
    close = difflib.get_close_matches(raw, list(by_label), n=1, cutoff=0.6)
    return by_label[close[0]] if close else None


def _deal_row(p: Project) -> str:
    """One compact member-safe row: name — stage · sector · value · score · location."""
    stage = _humanize_label(p.status.value if p.status else None) or "Unknown stage"
    parts = [f"{(p.name or '')[:60]} — {stage}"]
    sector = _humanize_label(p.pillar)
    if sector:
        parts.append(sector)
    if p.investment_size is not None:
        parts.append(f"{p.currency or 'USD'} {p.investment_size:,.0f}")
    score = p.afcen_score if p.afcen_score is not None else p.readiness_score
    if score is not None:
        parts.append(f"Score {float(score):g}")
    location = p.lead_country or p.site_location_name
    if location:
        parts.append(location)
    return " · ".join(parts)


async def list_my_deals(
    stage: Optional[str] = None,
    limit: Optional[int] = None,
    twg_id: Optional[str] = None,
    user_id: Optional[str] = None,
    user_role: Optional[UserRole] = None,
) -> dict:
    """List/count the CALLER's TWG deal room (the same per-request member binding
    and TWG-link-OR-TWG-pillar scope as get_project_brief; ARCHIVED excluded —
    no cross-TWG leakage). Returns total, per-stage counts and compact rows."""
    if not twg_id:
        return {"error": "Could not determine your TWG scope. Please retry from the app."}

    stage_filter = None
    if stage is not None and str(stage).strip():
        stage_filter = _match_stage(str(stage))
        if stage_filter is None:
            labels = ", ".join(
                _humanize_label(s.value) for s in ProjectStatus if s != ProjectStatus.ARCHIVED
            )
            return {"error": f"I don't recognise the stage '{stage}'. Stages I know: {labels}."}

    try:
        limit_n = int(limit) if limit is not None else _LIST_DEALS_DEFAULT_LIMIT
    except (TypeError, ValueError):
        limit_n = _LIST_DEALS_DEFAULT_LIMIT
    limit_n = max(1, min(limit_n, _LIST_DEALS_MAX_LIMIT))

    async with AsyncSessionLocal() as session:
        twg_uuid = await _resolve_member_twg_uuid(session, twg_id)
        if twg_uuid is None:
            return {"error": "Could not determine your TWG scope. Please retry from the app."}
        pillar_value = await _member_twg_pillar_value(session, twg_uuid)

        # SAME scope as get_project_brief / GET /pipeline/member: TWG link OR
        # TWG pillar (prod twg links are mis-assigned), ARCHIVED excluded.
        scope_clause = Project.twg_id == twg_uuid
        if pillar_value is not None:
            scope_clause = or_(scope_clause, Project.pillar == pillar_value)
        projects = (
            await session.execute(
                select(Project)
                .where(scope_clause, Project.status != ProjectStatus.ARCHIVED)
                .order_by(Project.name)
            )
        ).scalars().all()

    total = len(projects)
    if total == 0:
        return {"success": True, "total": 0, "deals": "Your TWG deal room has no projects yet."}

    stage_counts: dict = {}
    for p in projects:
        label = _humanize_label(p.status.value if p.status else None) or "Unknown stage"
        stage_counts[label] = stage_counts.get(label, 0) + 1

    rows_src = projects
    if stage_filter is not None:
        rows_src = [p for p in projects if p.status == stage_filter]
        stage_label = _humanize_label(stage_filter.value)
        lines = [
            f"Your TWG deal room: {total} projects total; "
            f"{len(rows_src)} in stage '{stage_label}'."
        ]
    else:
        lines = [f"Your TWG deal room: {total} projects."]
    lines.append(
        "By stage: " + " · ".join(f"{label}: {n}" for label, n in sorted(stage_counts.items()))
    )

    shown = 0
    used = sum(len(line) + 1 for line in lines)
    for p in rows_src[:limit_n]:
        row = f"{shown + 1}. {_deal_row(p)}"
        if used + len(row) + 1 > _LIST_DEALS_CHAR_BUDGET:
            break
        lines.append(row)
        used += len(row) + 1
        shown += 1
    remaining = len(rows_src) - shown
    if remaining > 0:
        lines.append(f"(+{remaining} more — filter by stage or ask about a project by name.)")

    result = {"success": True, "total": total, "deals": "\n".join(lines)}
    if stage_filter is not None:
        result["matched"] = len(rows_src)
    return result
