"""Confirm-then-execute write tools for the deal pipeline."""
from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.models import Project, ProjectStatus
from app.tools._rbac import (
    EDIT_ROLES, INVESTOR_ROLES, propose_action, require_role,
)
from app.models.models import UserRole

# Stage moves at or below SUMMIT_READY allowed for EDIT_ROLES; beyond requires INVESTOR_ROLES.
_HIGH_STAGE_GATE = {
    ProjectStatus.DEAL_ROOM_FEATURED,
    ProjectStatus.IN_NEGOTIATION,
    ProjectStatus.COMMITTED,
    ProjectStatus.IMPLEMENTED,
}


async def advance_project_stage(
    project_id: str,
    target_stage: str,
    user_id: str,
    user_role: UserRole,
    notes: Optional[str] = None,
    confirmed: bool = False,
    action_id: Optional[str] = None,
) -> dict:
    """Move a project to a new pipeline stage. Returns confirmation_required
    on first call; the /agents/execute endpoint completes the move on confirm."""

    # Parse target stage; reject unknown values immediately.
    try:
        new_stage = ProjectStatus(target_stage)
    except ValueError:
        return {"status": "invalid_input", "reason": f"Unknown stage: {target_stage}"}

    # Role gate — choose the stricter group if moving past SUMMIT_READY.
    allowed = INVESTOR_ROLES if new_stage in _HIGH_STAGE_GATE else EDIT_ROLES
    err = require_role(user_role, allowed)
    if err:
        return err

    # Validate the project exists + capture current stage for the summary.
    async with AsyncSessionLocal() as db:
        try:
            pid = UUID(project_id)
        except ValueError:
            return {"status": "invalid_input", "reason": "project_id is not a UUID"}
        row = (await db.execute(select(Project).where(Project.id == pid))).scalar_one_or_none()
        if not row:
            return {"status": "not_found", "reason": "Project not found"}
        current_stage = row.status.value if row.status else "UNKNOWN"
        project_name = row.name

    if confirmed:
        # Execution is performed by /agents/execute via the bound action_id —
        # this branch is only hit if the tool is called directly. The endpoint
        # re-imports and runs `_execute_advance_project_stage` below.
        return {"status": "ok", "result": "executed via /agents/execute"}

    summary = f'Advance "{project_name}" from {current_stage} to {new_stage.value}.'
    return propose_action(
        action_type="advance_project_stage",
        summary=summary,
        payload={
            "project_id": str(pid),
            "target_stage": new_stage.value,
            "notes": notes or "",
        },
        irreversible=False,
    )


async def decline_project(
    project_id: str,
    reason: str,
    user_id: str,
    user_role: UserRole,
    confirmed: bool = False,
    action_id: Optional[str] = None,
) -> dict:
    err = require_role(user_role, INVESTOR_ROLES)
    if err:
        return err
    if not reason or not reason.strip():
        return {"status": "invalid_input", "reason": "Decline reason is required"}

    async with AsyncSessionLocal() as db:
        try:
            pid = UUID(project_id)
        except ValueError:
            return {"status": "invalid_input", "reason": "project_id is not a UUID"}
        row = (await db.execute(select(Project).where(Project.id == pid))).scalar_one_or_none()
        if not row:
            return {"status": "not_found", "reason": "Project not found"}
        project_name = row.name

    if confirmed:
        return {"status": "ok", "result": "executed via /agents/execute"}
    return propose_action(
        action_type="decline_project",
        summary=f'Decline "{project_name}". Reason: {reason.strip()[:140]}',
        payload={"project_id": str(pid), "reason": reason.strip()},
        irreversible=True,
    )


async def mark_flagship(
    project_id: str,
    is_flagship: bool,
    user_id: str,
    user_role: UserRole,
    confirmed: bool = False,
    action_id: Optional[str] = None,
) -> dict:
    err = require_role(user_role, INVESTOR_ROLES)
    if err:
        return err

    async with AsyncSessionLocal() as db:
        try:
            pid = UUID(project_id)
        except ValueError:
            return {"status": "invalid_input", "reason": "project_id is not a UUID"}
        row = (await db.execute(select(Project).where(Project.id == pid))).scalar_one_or_none()
        if not row:
            return {"status": "not_found", "reason": "Project not found"}
        project_name = row.name
        currently = bool(getattr(row, "is_flagship", False))

    if confirmed:
        return {"status": "ok", "result": "executed via /agents/execute"}
    verb = "Mark" if is_flagship else "Unmark"
    if currently == bool(is_flagship):
        return {"status": "noop", "reason": f'"{project_name}" is already {"flagship" if currently else "not flagship"}.'}
    return propose_action(
        action_type="mark_flagship",
        summary=f'{verb} "{project_name}" as flagship.',
        payload={"project_id": str(pid), "is_flagship": bool(is_flagship)},
        irreversible=False,
    )


async def rescore_project(
    project_id: str,
    user_id: str,
    user_role: UserRole,
    confirmed: bool = False,
    action_id: Optional[str] = None,
) -> dict:
    err = require_role(user_role, EDIT_ROLES)
    if err:
        return err

    async with AsyncSessionLocal() as db:
        try:
            pid = UUID(project_id)
        except ValueError:
            return {"status": "invalid_input", "reason": "project_id is not a UUID"}
        row = (await db.execute(select(Project).where(Project.id == pid))).scalar_one_or_none()
        if not row:
            return {"status": "not_found", "reason": "Project not found"}
        project_name = row.name

    if confirmed:
        return {"status": "ok", "result": "executed via /agents/execute"}
    return propose_action(
        action_type="rescore_project",
        summary=f'Re-run WAIIS scoring for "{project_name}" using current data.',
        payload={"project_id": str(pid)},
        irreversible=False,
    )


async def graduate_from_incubation(
    project_id: str,
    user_id: str,
    user_role: UserRole,
    confirmed: bool = False,
    action_id: Optional[str] = None,
) -> dict:
    err = require_role(user_role, EDIT_ROLES)
    if err:
        return err

    async with AsyncSessionLocal() as db:
        try:
            pid = UUID(project_id)
        except ValueError:
            return {"status": "invalid_input", "reason": "project_id is not a UUID"}
        row = (await db.execute(select(Project).where(Project.id == pid))).scalar_one_or_none()
        if not row:
            return {"status": "not_found", "reason": "Project not found"}
        project_name = row.name
        if row.status != ProjectStatus.INCUBATION:
            return {"status": "invalid_state", "reason": f'"{project_name}" is not in Incubation.'}

    if confirmed:
        return {"status": "ok", "result": "executed via /agents/execute"}
    return propose_action(
        action_type="graduate_from_incubation",
        summary=f'Graduate "{project_name}" from Incubation to Draft.',
        payload={"project_id": str(pid)},
        irreversible=False,
    )


async def create_action_item(
    description: str,
    user_id: str,
    user_role: UserRole,
    project_id: Optional[str] = None,
    meeting_id: Optional[str] = None,
    owner_user_id: Optional[str] = None,
    due_date: Optional[str] = None,   # ISO date (YYYY-MM-DD)
    priority: str = "medium",
    confirmed: bool = False,
    action_id: Optional[str] = None,
) -> dict:
    err = require_role(user_role, EDIT_ROLES)
    if err:
        return err
    if not description or not description.strip():
        return {"status": "invalid_input", "reason": "Description is required"}
    if priority not in {"low", "medium", "high"}:
        return {"status": "invalid_input", "reason": "priority must be low/medium/high"}
    if due_date:
        try:
            date.fromisoformat(due_date)
        except ValueError:
            return {"status": "invalid_input", "reason": "due_date must be YYYY-MM-DD"}

    if confirmed:
        return {"status": "ok", "result": "executed via /agents/execute"}
    title = description.strip()[:80]
    return propose_action(
        action_type="create_action_item",
        summary=f'Create action item: "{title}"' + (f" (due {due_date})" if due_date else ""),
        payload={
            "description": description.strip(),
            "project_id": project_id,
            "meeting_id": meeting_id,
            "owner_user_id": owner_user_id,
            "due_date": due_date,
            "priority": priority,
        },
        irreversible=False,
    )


async def bulk_create_action_items(
    meeting_id: str,
    items: List[dict],
    user_id: str,
    user_role: UserRole,
    confirmed: bool = False,
    action_id: Optional[str] = None,
) -> dict:
    err = require_role(user_role, EDIT_ROLES)
    if err:
        return err
    if not items:
        return {"status": "invalid_input", "reason": "items list is empty"}
    if len(items) > 50:
        return {"status": "invalid_input", "reason": "max 50 items per bulk call"}
    for i, item in enumerate(items):
        if not item.get("description", "").strip():
            return {"status": "invalid_input", "reason": f"items[{i}] missing description"}

    if confirmed:
        return {"status": "ok", "result": "executed via /agents/execute"}
    return propose_action(
        action_type="bulk_create_action_items",
        summary=f"Create {len(items)} action item(s) tied to meeting {meeting_id[:8]}.",
        payload={"meeting_id": meeting_id, "items": items},
        irreversible=False,
    )
