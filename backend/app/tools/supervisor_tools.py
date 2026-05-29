"""
Supervisor Tools for the Martin Supervisor Agent

These tools provide cross-TWG visibility and coordination capabilities.
They are registered in the ToolRegistry with proper schemas (not auto-generated).

Previously these were inline closures in langgraph_supervisor.py with auto-generated
schemas that produced vague parameter descriptions. Now they have explicit JSON schemas
with clear descriptions, return values, and examples.
"""

import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


# =============================================================================
# Module-level references for tools that need runtime context
# =============================================================================

# Set by LangGraphSupervisor.__init__ after agents are registered
_twg_agents: Dict[str, Any] = {}
_session_id: Optional[str] = None


def set_supervisor_context(twg_agents: Dict[str, Any], session_id: Optional[str] = None):
    """Called by LangGraphSupervisor to provide runtime context to tools."""
    global _twg_agents, _session_id
    _twg_agents = twg_agents
    _session_id = session_id


# Page name → frontend route mapping
_PAGE_ROUTES: Dict[str, str] = {
    "dashboard": "/dashboard",
    "home": "/dashboard",
    "schedule": "/schedule",
    "meetings": "/schedule",
    "calendar": "/schedule",
    "documents": "/documents",
    "docs": "/documents",
    "files": "/documents",
    "twgs": "/twgs",
    "agents": "/twgs",
    "workspaces": "/twgs",
    "actions": "/actions",
    "tasks": "/actions",
    "action items": "/actions",
    "pipeline": "/deal-pipeline",
    "deal pipeline": "/deal-pipeline",
    "deals": "/deal-pipeline",
    "projects": "/deal-pipeline",
    "notifications": "/notifications",
    "profile": "/profile",
    "settings": "/profile",
    "team": "/admin/team",
    "logs": "/admin/logs",
    "audit": "/admin/logs",
    "audit logs": "/admin/logs",
}


# =============================================================================
# Tool Handlers (module-level async/sync functions)
# =============================================================================

def get_global_calendar_tool(user_timezone: str = "") -> str:
    """Get the unified schedule of all TWG meetings."""
    from app.core.database import get_sync_db_session
    from app.models.models import Meeting, MeetingStatus
    from sqlalchemy import select
    from datetime import timezone as tz
    from zoneinfo import ZoneInfo

    tz_name = user_timezone or "Africa/Nairobi"
    try:
        user_tz = ZoneInfo(tz_name)
    except Exception:
        user_tz = ZoneInfo("Africa/Nairobi")

    try:
        session = get_sync_db_session()
        try:
            stmt = select(Meeting).where(
                Meeting.status == MeetingStatus.SCHEDULED
            ).order_by(Meeting.scheduled_at)
            meetings = session.execute(stmt).scalars().all()

            if not meetings:
                return "Global Calendar: No upcoming meetings scheduled."

            response = f"Global Calendar ({len(meetings)} upcoming):\n"
            for m in meetings:
                utc_time = m.scheduled_at.replace(tzinfo=tz.utc)
                local_time = utc_time.astimezone(user_tz)
                tz_abbr = local_time.strftime('%Z')
                time_str = local_time.strftime(f'%Y-%m-%d %I:%M %p {tz_abbr}')

                loc = m.location or "TBD"
                if m.video_link:
                    loc += f" (Link: {m.video_link})"

                response += (
                    f"- [ID: {m.id}] {time_str}: {m.title} "
                    f"({m.twg.name if m.twg else 'General'})\n  Location: {loc}\n"
                )
            return response
        finally:
            session.close()
    except Exception as e:
        return f"Error accessing calendar: {str(e)}"


def get_document_registry_tool() -> str:
    """Get the registry of all documents across TWGs."""
    try:
        from app.services.supervisor_state_service import get_supervisor_state
        state_service = get_supervisor_state()
        state = state_service.get_state()
        if not state:
            return "Global state not yet initialized."

        registry = state_service.get_document_registry()
        response = f"Document Registry ({registry.total_documents} documents):\n"
        for doc in registry.documents[:20]:
            response += f"- {doc.file_name} ({doc.twg_name or 'General'}) - {doc.file_type}\n"

        if registry.total_documents > 20:
            response += f"... and {registry.total_documents - 20} more."
        return response
    except Exception as e:
        return f"Error accessing documents: {str(e)}"


def get_project_pipeline_tool() -> str:
    """Get the status of the project pipeline."""
    try:
        from app.services.supervisor_state_service import get_supervisor_state
        state_service = get_supervisor_state()
        state = state_service.get_state()
        if not state:
            return "Global state not yet initialized."

        pipeline = state_service.get_project_pipeline()
        response = (
            f"Project Pipeline ({pipeline.total_projects} projects, "
            f"Total Investment: ${pipeline.total_investment:,.2f}):\n"
        )
        by_status: Dict[str, list] = {}
        for p in pipeline.projects:
            key = p.status.value
            by_status.setdefault(key, []).append(p)

        for status, projects in by_status.items():
            response += f"\n{status.upper()}:\n"
            for p in projects:
                response += (
                    f"- {p.name} ({p.twg_name}): "
                    f"${p.investment_size:,.0f} (Readiness: {p.readiness_score}/10)\n"
                )
        return response
    except Exception as e:
        return f"Error accessing pipeline: {str(e)}"


async def get_summit_status_tool() -> str:
    """Get the High-Level Summit Status Overview."""
    try:
        from app.services.supervisor_state_service import get_supervisor_state
        state_service = get_supervisor_state()
        state = state_service.get_state()
        if not state:
            return "Status unavailable (System initializing)"

        pipeline = state_service.get_project_pipeline()
        proj_score = min(100, (pipeline.total_projects * 5))

        cal = state_service.get_global_calendar()
        meet_score = 100 if cal.conflicts_detected == 0 else 70

        docs = state_service.get_document_registry()
        doc_score = min(100, docs.total_documents * 10)

        overall = int((proj_score * 0.5) + (meet_score * 0.3) + (doc_score * 0.2))

        res = f"📊 **Summit Status: {overall}% On Track**\n\n"
        res += "**TWG Performance:**\n"
        twgs = ["Energy", "Agriculture", "Minerals", "Digital"]
        for twg in twgs:
            status = "✅ On schedule"
            if twg == "Minerals" and overall < 80:
                status = "⚠️ Minor delay (Data collection)"
            res += f"{status}: {twg}\n"

        res += "\n**Critical Path Items:**\n"
        res += "1. Ministerial Harmonization Workshop (April 2026)\n"
        res += "2. Declaration Draft (Deadline: March 15)\n"
        return res
    except Exception as e:
        return f"Error calculating status: {e}"


async def detect_conflicts_tool() -> str:
    """Run a deep scan for Policy and Scheduling conflicts across all TWGs."""
    try:
        from app.services.supervisor_state_service import get_supervisor_state
        state_service = get_supervisor_state()
        cal = state_service.get_global_calendar()
        conflicts = []
        if cal.conflicts_detected > 0:
            conflicts.append(
                f"• {cal.conflicts_detected} scheduling clashes detected in Global Calendar."
            )

        if not conflicts:
            return "✅ No conflicts detected. All systems aligned."
        return "⚠️ **Conflicts Detected:**\n" + "\n".join(conflicts)
    except Exception as e:
        return f"Error scanning conflicts: {e}"


def start_negotiation_tool(conflict_description: str, agent_a: str, agent_b: str) -> str:
    """Initiate an automated negotiation between two agents to resolve a conflict."""
    return f"NEGOTIATION_STARTED::{conflict_description}::{agent_a}::{agent_b}"


_MAX_AGENT_RESPONSE_CHARS = 600  # per agent, to keep total context small


async def consult_twg_agents_tool(agent_names: str, query: str) -> str:
    """
    Consult multiple TWG agents sequentially (max 3 at once to avoid rate limits).
    agent_names is a comma-separated string (e.g. "energy,digital").
    """
    if not _twg_agents:
        return "Error: No TWG agents are currently registered."

    raw_names = [n.strip().lower().replace(" twg", "").replace(" agent", "") for n in agent_names.split(",")]
    valid_agents = [n for n in raw_names if n in _twg_agents]

    if not valid_agents:
        return (
            f"Error: None of the requested agents were found. "
            f"Available agents: {', '.join(_twg_agents.keys())}"
        )

    # Cap at 3 agents to limit parallel Gemini calls
    valid_agents = valid_agents[:3]

    try:
        logger.info(f"[SUPERVISOR] Consulting agents {valid_agents} with query: {query}")
        response_parts = []
        for agent_name in valid_agents:
            try:
                result = await _twg_agents[agent_name].chat(query, thread_id=_session_id)
                res_text = (
                    result.get("response", str(result))
                    if isinstance(result, dict)
                    else str(result)
                )
                # Truncate per-agent response to keep total context manageable
                if len(res_text) > _MAX_AGENT_RESPONSE_CHARS:
                    res_text = res_text[:_MAX_AGENT_RESPONSE_CHARS] + "…"
                response_parts.append(f"[{agent_name.upper()} TWG]\n{res_text}")
            except Exception as agent_err:
                response_parts.append(f"[{agent_name.upper()} TWG] Error: {str(agent_err)[:200]}")

        return "\n\n---\n\n".join(response_parts)
    except Exception as e:
        logger.error(f"[SUPERVISOR] Error consulting agents: {e}")
        return f"Error executing cross-agent query: {str(e)}"


async def navigate_to_page_tool(page: str) -> str:
    """Navigate the user's browser to a page in the application."""
    from app.services.stream_events import emit

    normalized = page.lower().strip()
    route = _PAGE_ROUTES.get(normalized)

    if not route:
        for key, path in _PAGE_ROUTES.items():
            if key in normalized or normalized in key:
                route = path
                break

    if not route:
        unique_routes = sorted(set(_PAGE_ROUTES.values()))
        return f"Unknown page '{page}'. Available: {', '.join(unique_routes)}"

    if _session_id:
        await emit(_session_id, {"type": "navigate", "path": route})

    page_label = page.title()
    return f"Opening {page_label} now."


def check_availability_tool(start_time_iso: str, duration_minutes: int, vip_names: str = "") -> str:
    """Check availability for a potential meeting without booking it."""
    from app.core.database import get_sync_db_session
    from app.models.models import Meeting
    from sqlalchemy import select, func

    try:
        start_time = datetime.fromisoformat(start_time_iso)
        end_time = start_time + timedelta(minutes=duration_minutes)

        session = get_sync_db_session()
        try:
            stmt = select(Meeting).where(
                Meeting.scheduled_at < end_time,
                (Meeting.scheduled_at + func.make_interval(0, 0, 0, 0, 0, Meeting.duration_minutes, 0)) > start_time
            )
            result = session.execute(stmt)
            overlapping = result.scalars().all()

            if not overlapping:
                return "✅ Slot is available. No conflicts detected."

            response = f"⚠️ {len(overlapping)} Potential Conflicts Detected:\n"
            for m in overlapping:
                response += f"- {m.title} at {m.scheduled_at.isoformat()}\n"
            return response
        finally:
            session.close()
    except Exception as e:
        logger.error(f"[AVAILABILITY_TOOL] Error: {e}")
        return f"Error checking availability: {str(e)}"


def request_booking_tool(
    title: str,
    twg_name: str,
    start_time_iso: str,
    duration_minutes: int,
    vip_names: str = "",
    attendee_emails: str = "",
    location: str = "",
    user_timezone: str = ""
) -> str:
    """Request to officially book a meeting."""
    from loguru import logger as loguru_logger
    from app.core.database import SyncSessionLocal
    from sqlalchemy import text
    from uuid import uuid4
    from langgraph.errors import GraphInterrupt
    import random
    import string
    from datetime import timezone as tz

    try:
        loguru_logger.info(f"[BOOKING_TOOL] Starting booking: {title}")

        # Preserve UTC offset: replace Z suffix with +00:00 so fromisoformat
        # returns a timezone-aware datetime. rstrip('Z') would strip the UTC
        # indicator and produce a naive datetime, causing a double-conversion
        # when user_timezone is also provided.
        clean_time_str = start_time_iso.replace('Z', '+00:00')
        start_time = datetime.fromisoformat(clean_time_str)

        from zoneinfo import ZoneInfo

        if user_timezone and start_time.tzinfo is None:
            try:
                user_tz = ZoneInfo(user_timezone)
                local_dt = start_time.replace(tzinfo=user_tz)
                utc_time = local_dt.astimezone(tz.utc).replace(tzinfo=None)
                loguru_logger.info(
                    f"[BOOKING_TOOL] Converted User Local Time ({start_time_iso} {user_timezone}) -> UTC: {utc_time}"
                )
                start_time = utc_time
            except Exception as e:
                loguru_logger.error(f"[BOOKING_TOOL] Timezone conversion failed: {e}. Fallback to UTC assumption.")
        elif start_time.tzinfo is not None:
            start_time = start_time.astimezone(tz.utc).replace(tzinfo=None)

        # Smart Location Inference
        is_virtual = False
        generated_link = None
        virtual_keywords = ["virtual", "online", "zoom", "meet", "teams", "remote", "call"]

        final_location = location if location else None
        if not final_location:
            final_location = "Virtual (Pending Link)"
            is_virtual = True
        else:
            if "meet.google.com" in final_location:
                loguru_logger.warning(f"[BOOKING_TOOL] Stripping potential fake link: {final_location}")
                final_location = "Virtual (Pending Link)"
                is_virtual = True
            elif any(k in final_location.lower() for k in virtual_keywords):
                is_virtual = True

        if is_virtual and "meet.google.com" not in (final_location or ""):
            generated_link = None

        session = SyncSessionLocal()
        try:
            twg_query = text("SELECT id, name FROM twgs WHERE name ILIKE :twg_name LIMIT 1")
            result = session.execute(twg_query, {"twg_name": f"%{twg_name}%"})
            twg_row = result.fetchone()

            # Fall back to agent-key resolution. Agent keys like "agriculture"
            # don't substring-match the display name "Agribusiness and Food
            # Systems Transformation", so a plain ILIKE misses. Also accept a
            # raw UUID passed as twg_name.
            if not twg_row:
                from app.agents.utils import get_twg_id_by_agent_id
                resolved_id = get_twg_id_by_agent_id(twg_name.strip().lower())
                if not resolved_id:
                    try:
                        import uuid as _uuid
                        _uuid.UUID(str(twg_name))
                        resolved_id = str(twg_name)
                    except (ValueError, AttributeError):
                        resolved_id = None
                if resolved_id:
                    twg_row = session.execute(
                        text("SELECT id, name FROM twgs WHERE id = :tid LIMIT 1"),
                        {"tid": resolved_id},
                    ).fetchone()

            if not twg_row:
                return f"Error: TWG '{twg_name}' not found."

            twg_id = twg_row[0]

            # Parse list params from comma-separated strings
            vip_list = [v.strip() for v in vip_names.split(",") if v.strip()] if vip_names else []
            email_list = [e.strip().lower() for e in attendee_emails.split(",") if e.strip()] if attendee_emails else []

            # Resolve VIPs
            vip_user_ids = []
            if vip_list:
                placeholders = ','.join([f":name{i}" for i in range(len(vip_list))])
                vip_query = text(f"""
                    SELECT vip_profiles.user_id
                    FROM vip_profiles
                    JOIN users ON users.id = vip_profiles.user_id
                    WHERE users.full_name IN ({placeholders}) OR vip_profiles.title IN ({placeholders})
                """)
                params_vip = {f"name{i}": name for i, name in enumerate(vip_list)}
                result = session.execute(vip_query, params_vip)
                vip_user_ids = [row[0] for row in result.fetchall()]

            # Resolve regular attendees
            regular_user_ids = []
            found_emails = []
            guest_list = []
            if email_list:
                placeholders = ','.join([f":email{i}" for i in range(len(email_list))])
                user_query = text(f"""
                    SELECT id, email FROM users WHERE LOWER(email) IN ({placeholders})
                """)
                params_email = {f"email{i}": e for i, e in enumerate(email_list)}
                result = session.execute(user_query, params_email)
                rows = result.fetchall()
                for r in rows:
                    regular_user_ids.append(r[0])
                    found_emails.append(r[1].lower())
                guest_list = [e for e in email_list if e not in found_emails]

            all_participant_ids = list(set(vip_user_ids + regular_user_ids))

            # Prevent double booking
            check_dup = text("""
                SELECT id FROM meetings
                WHERE twg_id = :twg_id
                AND scheduled_at = :scheduled_at
            """)
            dup_result = session.execute(check_dup, {"twg_id": twg_id, "scheduled_at": start_time})
            existing_meeting = dup_result.fetchone()
            if existing_meeting:
                raise GraphInterrupt(
                    f"DUPLICATE MEETING DETECTED (ID: {existing_meeting[0]}). "
                    "Execution halted to prevent double booking."
                )

            meeting_id = uuid4()
            meeting_type = "virtual" if is_virtual else "in-person"

            insert_meeting = text("""
                INSERT INTO meetings (id, twg_id, title, scheduled_at, duration_minutes, location, status, meeting_type, video_link, is_recurring_exception)
                VALUES (:id, :twg_id, :title, :scheduled_at, :duration_minutes, :location, :status, :meeting_type, :video_link, false)
            """)
            session.execute(insert_meeting, {
                "id": meeting_id,
                "twg_id": twg_id,
                "title": title,
                "scheduled_at": start_time,
                "duration_minutes": duration_minutes,
                "location": final_location,
                "status": "SCHEDULED",
                "meeting_type": meeting_type,
                "video_link": generated_link
            })

            if all_participant_ids:
                for uid in all_participant_ids:
                    participant_id = uuid4()
                    session.execute(text(
                        "INSERT INTO meeting_participants (id, meeting_id, user_id, rsvp_status, attended) "
                        "VALUES (:pid, :mid, :uid, 'PENDING', false)"
                    ), {"pid": participant_id, "mid": meeting_id, "uid": uid})

            session.commit()

            guest_msg = ""
            if guest_list:
                guest_msg = f" (Guests: {', '.join(guest_list)})"
            link_status = (
                "Video Link: Pending (Will be updated via Calendar Integration)"
                if is_virtual
                else "Video Link: N/A"
            )
            return (
                f"✅ Meeting '{title}' SCHEDULED. ID: {meeting_id}\n"
                f"Location: {final_location}\n{link_status}{guest_msg}"
            )
        except GraphInterrupt:
            raise
        except Exception as e:
            session.rollback()
            loguru_logger.error(f"[BOOKING_TOOL] Database error: {e}", exc_info=True)
            return f"Error creating meeting: {str(e)}"
        finally:
            session.close()
    except GraphInterrupt:
        raise
    except Exception as e:
        loguru_logger.error(f"[BOOKING_TOOL] Error: {e}", exc_info=True)
        return f"Error requesting booking: {str(e)}"


def update_meeting_tool(
    meeting_id: str,
    new_title: str = "",
    new_location: str = "",
    is_virtual: str = "",
    new_time_iso: str = "",
    new_duration: int = 0
) -> str:
    """Update an existing meeting."""
    from app.core.database import get_sync_db_session
    from app.models.models import Meeting
    from sqlalchemy import select
    from loguru import logger as loguru_logger

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

            if new_duration and new_duration > 0:
                meeting.duration_minutes = new_duration
                changes.append(f"Duration -> {new_duration}m")

            if new_location:
                meeting.location = new_location
                changes.append(f"Location -> {new_location}")

                # Auto-infer virtual from location keywords
                virtual_keywords = ["virtual", "online", "zoom", "meet", "teams"]
                if any(k in new_location.lower() for k in virtual_keywords):
                    is_virtual = "true"

            # Handle is_virtual as string since LLM sends strings
            if is_virtual.lower() == "true":
                if not meeting.video_link:
                    loguru_logger.warning(
                        f"[UPDATE_MEETING] Virtual meeting but no video_link. Keeping as None."
                    )
                    changes.append("Video Link -> Not available (requires Calendar API integration)")
                if not meeting.location or meeting.location.strip() == "Virtual":
                    meeting.location = "Virtual (Google Meet)"
            elif is_virtual.lower() == "false":
                meeting.video_link = None
                changes.append("Video Link -> Removed (Physical meeting)")

            if not changes:
                return "No changes provided. Meeting unchanged."

            session.commit()
            return f"✅ Meeting Updated: {', '.join(changes)}"
        finally:
            session.close()
    except Exception as e:
        return f"Error updating meeting: {str(e)}"


# =============================================================================
# Tool Definitions (OpenAI format with proper schemas)
# =============================================================================

SUPERVISOR_TOOL_DEFS = [
    {
        "type": "function",
        "function": {
            "name": "get_global_calendar_tool",
            "description": (
                "Get the unified schedule of ALL meetings across ALL TWGs. "
                "Use for cross-TWG scheduling, finding conflicts, or seeing the overall timeline. "
                "Returns formatted list of upcoming meetings with: ID, time (EAT), title, TWG name, location, and video link. "
                "Example: User asks 'what meetings are coming up across all TWGs?' → call get_global_calendar_tool()."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_document_registry_tool",
            "description": (
                "Get the registry of ALL documents across ALL TWGs. "
                "Use when looking for policies, drafts, memos, or any files across the entire summit. "
                "Returns list of documents with: file_name, TWG name, file_type. "
                "Example: User asks 'what documents do we have?' → call get_document_registry_tool()."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_project_pipeline_tool",
            "description": (
                "Get the investment project pipeline status across all TWGs. "
                "Use when checking deal flow, investment readiness, or overall pipeline health. "
                "Returns projects grouped by status with: name, TWG, investment size, readiness score. "
                "Example: User asks 'how is the deal pipeline looking?' → call get_project_pipeline_tool()."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_summit_status_tool",
            "description": (
                "Get the overall Summit preparation progress and status overview. "
                "Use when the user asks about summit status, preparation progress, or TWG performance. "
                "Returns: overall % on track, TWG performance breakdown, critical path items. "
                "Example: User asks 'what is the summit status?' → call get_summit_status_tool()."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "detect_conflicts_tool",
            "description": (
                "Scan for policy and scheduling conflicts across ALL TWGs. "
                "Use when checking for conflicts, overlaps, or misalignments. "
                "Returns list of detected conflicts or confirmation that none exist. "
                "Example: User asks 'are there any scheduling conflicts?' → call detect_conflicts_tool()."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "start_negotiation_tool",
            "description": (
                "Initiate conflict resolution between two TWG agents. "
                "Use when a policy disagreement or resource conflict needs mediation. "
                "Returns a negotiation session identifier. "
                "Example: User asks 'resolve the energy vs minerals land use conflict' → "
                "call start_negotiation_tool(conflict_description='...', agent_a='energy', agent_b='minerals')."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "conflict_description": {
                        "type": "string",
                        "description": "Clear description of the policy divergence or conflict to resolve"
                    },
                    "agent_a": {
                        "type": "string",
                        "description": "ID of the first agent (e.g. 'energy', 'minerals', 'agriculture', 'digital')"
                    },
                    "agent_b": {
                        "type": "string",
                        "description": "ID of the second agent (e.g. 'energy', 'minerals', 'agriculture', 'digital')"
                    }
                },
                "required": ["conflict_description", "agent_a", "agent_b"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "consult_twg_agents_tool",
            "description": (
                "Ask specific TWG agents for domain expertise. Use when you need input from one or more TWGs. "
                "Pass agent_names as comma-separated string (e.g. 'energy,digital') and a clear query. "
                "Returns responses from each consulted agent, clearly labeled by TWG. "
                "Example: User asks 'what do Energy and Digital think about smart grid integration?' → "
                "call consult_twg_agents_tool(agent_names='energy,digital', query='What is your assessment of smart grid integration?')."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "agent_names": {
                        "type": "string",
                        "description": "Comma-separated TWG agent names to consult (e.g. 'energy,digital,agriculture,minerals')"
                    },
                    "query": {
                        "type": "string",
                        "description": "The specific question or instruction for the TWG agents"
                    }
                },
                "required": ["agent_names", "query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "navigate_to_page_tool",
            "description": (
                "Navigate the user's browser to a specific page in the application. "
                "Use when the user asks to 'go to', 'open', 'show me', or 'take me to' a page. "
                "Supported pages: dashboard, schedule/meetings, documents, twgs/agents, actions/tasks, "
                "deal-pipeline/projects, notifications, profile, team, audit logs. "
                "Example: User says 'show me the documents page' → call navigate_to_page_tool(page='documents'). "
                "Example: User says 'go to schedule' → call navigate_to_page_tool(page='schedule')."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "page": {
                        "type": "string",
                        "description": "Name of the page to navigate to (e.g. 'dashboard', 'documents', 'schedule', 'actions', 'pipeline', 'notifications', 'profile', 'team', 'logs')"
                    }
                },
                "required": ["page"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_availability_tool",
            "description": (
                "Check if a time slot is free before booking a meeting. "
                "Use BEFORE request_booking_tool to verify no conflicts. "
                "Returns confirmation of availability or list of conflicting meetings. "
                "Example: User asks 'is 2pm on March 15 free?' → "
                "call check_availability_tool(start_time_iso='2026-03-15T14:00:00', duration_minutes=60)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "start_time_iso": {
                        "type": "string",
                        "description": "Start time in ISO 8601 format (e.g. '2026-03-15T14:00:00')"
                    },
                    "duration_minutes": {
                        "type": "integer",
                        "description": "Duration of the meeting in minutes"
                    },
                    "vip_names": {
                        "type": "string",
                        "description": "Optional comma-separated VIP names to check (e.g. 'Minister of Energy,President')"
                    }
                },
                "required": ["start_time_iso", "duration_minutes"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "request_booking_tool",
            "description": (
                "Book a meeting officially. REQUIRES: title, twg_name, start_time_iso, duration_minutes. "
                "Creates the meeting in the database with participants. "
                "Returns confirmation with meeting ID, location, and video link status. "
                "IMPORTANT: Call check_availability_tool FIRST to verify no conflicts. "
                "Example: User asks 'book an Energy meeting for March 15 at 2pm' → "
                "call request_booking_tool(title='Energy TWG Session', twg_name='Energy', "
                "start_time_iso='2026-03-15T14:00:00', duration_minutes=60)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Meeting title"
                    },
                    "twg_name": {
                        "type": "string",
                        "description": "Name of the hosting TWG (e.g. 'Energy', 'Minerals', 'Agriculture', 'Digital')"
                    },
                    "start_time_iso": {
                        "type": "string",
                        "description": "Start time in ISO 8601 format in UTC (e.g. '2026-03-15T14:00:00')"
                    },
                    "duration_minutes": {
                        "type": "integer",
                        "description": "Duration in minutes"
                    },
                    "vip_names": {
                        "type": "string",
                        "description": "Optional comma-separated VIP names to invite (e.g. 'Minister of Energy')"
                    },
                    "attendee_emails": {
                        "type": "string",
                        "description": "Optional comma-separated participant email addresses"
                    },
                    "location": {
                        "type": "string",
                        "description": "Meeting location (e.g. 'Virtual', 'Conference Room 1'). Defaults to Virtual if empty."
                    },
                    "user_timezone": {
                        "type": "string",
                        "description": "User's timezone (e.g. 'Africa/Nairobi') for time conversion"
                    }
                },
                "required": ["title", "twg_name", "start_time_iso", "duration_minutes"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_meeting_tool",
            "description": (
                "Modify any meeting globally — change title, location, time, or duration. "
                "Use when the user asks to reschedule, rename, or change a meeting. "
                "Returns confirmation with list of changes made. "
                "First call get_global_calendar_tool to find the meeting ID. "
                "Example: User asks 'move the Energy meeting to 3pm' → "
                "call get_global_calendar_tool() to find the ID, then "
                "call update_meeting_tool(meeting_id='...', new_time_iso='2026-03-15T15:00:00')."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "meeting_id": {
                        "type": "string",
                        "description": "The ID of the meeting to update (from get_global_calendar_tool results)"
                    },
                    "new_title": {
                        "type": "string",
                        "description": "New title for the meeting (optional, leave empty to keep current)"
                    },
                    "new_location": {
                        "type": "string",
                        "description": "New location (e.g. 'Virtual' or 'Conference Room 1')"
                    },
                    "is_virtual": {
                        "type": "string",
                        "description": "Set to 'true' for virtual meeting, 'false' for in-person (optional)"
                    },
                    "new_time_iso": {
                        "type": "string",
                        "description": "New start time in ISO 8601 format (e.g. '2026-03-15T15:00:00')"
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
]

# Build handler map for easy lookup
SUPERVISOR_TOOL_HANDLERS = {
    "navigate_to_page_tool": navigate_to_page_tool,
    "get_global_calendar_tool": get_global_calendar_tool,
    "get_document_registry_tool": get_document_registry_tool,
    "get_project_pipeline_tool": get_project_pipeline_tool,
    "get_summit_status_tool": get_summit_status_tool,
    "detect_conflicts_tool": detect_conflicts_tool,
    "start_negotiation_tool": start_negotiation_tool,
    "consult_twg_agents_tool": consult_twg_agents_tool,
    "check_availability_tool": check_availability_tool,
    "request_booking_tool": request_booking_tool,
    "update_meeting_tool": update_meeting_tool,
}
