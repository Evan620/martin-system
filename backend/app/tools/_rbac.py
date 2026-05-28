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
