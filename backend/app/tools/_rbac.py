"""Role gates + confirm-then-execute payload factory for Martin write tools."""
from __future__ import annotations

import uuid as _uuid
from contextvars import ContextVar
from typing import Iterable, Optional, Set, Tuple

from app.models.models import UserRole

# Per-request user context, set by the /chat endpoints. Tools that need
# user_id / user_role and aren't passed them as kwargs read this contextvar.
_user_ctx: ContextVar[Optional[Tuple[str, UserRole]]] = ContextVar(
    "agent_user_ctx", default=None
)


def set_user_context(user_id: str, user_role: UserRole) -> None:
    """Bind the calling user's id+role for the duration of the request."""
    _user_ctx.set((str(user_id), user_role))


def get_user_context() -> Optional[Tuple[str, UserRole]]:
    """Return (user_id, user_role) or None if not set."""
    return _user_ctx.get()


# Cross-task fallback: ContextVars don't always propagate across the supervisor's
# delegation hops (consult_twg_agents_tool spawns new task chains). Stash user
# context by chat thread_id, which the agent loop receives explicitly.
_user_by_thread: dict[str, Tuple[str, UserRole]] = {}
_MAX_THREADS = 256


def set_user_for_thread(thread_id: str, user_id: str, user_role: UserRole) -> None:
    """Stash user context keyed by chat thread_id for cross-task retrieval."""
    if not thread_id:
        return
    # Bounded — drop the oldest entry when full. Good enough; we don't expect
    # 256 concurrent active chats.
    if len(_user_by_thread) >= _MAX_THREADS:
        try:
            _user_by_thread.pop(next(iter(_user_by_thread)))
        except StopIteration:
            pass
    _user_by_thread[str(thread_id)] = (str(user_id), user_role)


def get_user_for_thread(thread_id: Optional[str]) -> Optional[Tuple[str, UserRole]]:
    """Resolve user context by thread_id, falling back to the ContextVar."""
    if thread_id:
        hit = _user_by_thread.get(str(thread_id))
        if hit is not None:
            return hit
    return _user_ctx.get()


# ---------------------------------------------------------------------------
# Pending-action store — shared between agent_loop (writes) and the /execute
# route (reads). Lives here to avoid a circular import: agent_loop is imported
# transitively by routes.agents, so agent_loop cannot import from there.
# ---------------------------------------------------------------------------
from datetime import datetime as _dt, timedelta as _td

_pending_actions: dict[str, dict] = {}
_ACTION_TTL_MINUTES = 10


def store_pending_action(action_id: str, user_id: str, action_type: str, payload: dict) -> None:
    _pending_actions[action_id] = {
        "action_id": action_id,
        "user_id": str(user_id),
        "action_type": action_type,
        "payload": payload,
        "expires_at": (_dt.utcnow() + _td(minutes=_ACTION_TTL_MINUTES)).isoformat(),
    }


def get_pending_action(action_id: str, user_id: str) -> Optional[dict]:
    entry = _pending_actions.get(action_id)
    if not entry:
        return None
    if _dt.utcnow() > _dt.fromisoformat(entry["expires_at"]):
        _pending_actions.pop(action_id, None)
        return None
    if entry["user_id"] != str(user_id):
        return None
    return entry


def drop_pending_action(action_id: str) -> None:
    _pending_actions.pop(action_id, None)

# Mirrors frontend RBAC groups so the agent's writes match what the UI allows.
EDIT_ROLES: Set[UserRole] = {
    UserRole.ADMIN, UserRole.SECRETARIAT_LEAD, UserRole.TWG_FACILITATOR,
}
INVESTOR_ROLES: Set[UserRole] = {UserRole.ADMIN, UserRole.SECRETARIAT_LEAD}
SECRETARIAT_ONLY: Set[UserRole] = {UserRole.ADMIN, UserRole.SECRETARIAT_LEAD}


def require_role(user_role: UserRole, allowed: Iterable[UserRole]) -> Optional[dict]:
    """Return a forbidden payload if the user's role is not in `allowed`, else None."""
    allowed_set = set(allowed)
    if user_role in allowed_set:
        return None
    names = ", ".join(sorted(r.name for r in allowed_set))
    return {"status": "forbidden", "reason": f"Requires one of: {names}"}


def propose_action(
    action_type: str,
    summary: str,
    payload: dict,
    irreversible: bool = False,
) -> dict:
    """Return the standard confirmation_required payload Martin tools must emit."""
    return {
        "status": "confirmation_required",
        "type": "action_required",
        "action_id": _uuid.uuid4().hex[:12],
        "action_type": action_type,
        "summary": summary,
        "payload": payload,
        "irreversible": irreversible,
        "confirm_endpoint": "/api/v1/agents/execute",
    }
