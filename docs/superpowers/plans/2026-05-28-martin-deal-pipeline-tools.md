# Martin Deal-Pipeline Tools Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give Martin a confirm-then-execute write surface on the deal pipeline (advance, decline, mark flagship, rescore, graduate, create action items) plus the cross-cutting reads users keep asking for (pipeline summary, my action items, at-risk, next deadlines, near-graduation).

**Architecture:** New tools live in `backend/app/tools/pipeline_write_tools.py` and `backend/app/tools/pipeline_read_tools.py`. RBAC enforced via a new `app/tools/_rbac.py` helper that mirrors the frontend `canEdit` / `canAccessInvestorDB` groups. The existing `/agents/execute` endpoint (already dispatching `schedule_meeting` / `create_action_item`) is extended with the new pipeline `action_type`s. A new nullable `agent_audit_log` table records every executed write.

**Tech Stack:** FastAPI + SQLAlchemy (backend); existing `_pending_actions` dict in `agents.py` (10-min TTL); React + TypeScript (frontend chat card UI).

Reference spec: `docs/superpowers/specs/2026-05-28-martin-deal-pipeline-tools-design.md`

---

## File Structure

- **Create** `backend/app/tools/_rbac.py` — role groups + `require_role` helper + `propose_action` factory that returns the standard `confirmation_required` payload.
- **Create** `backend/app/tools/pipeline_write_tools.py` — `advance_project_stage`, `decline_project`, `mark_flagship`, `rescore_project`, `graduate_from_incubation`, `create_action_item`, `bulk_create_action_items`.
- **Create** `backend/app/tools/pipeline_read_tools.py` — `pipeline_summary`, `at_risk_projects`, `incubation_close_to_graduation`, `my_action_items`, `next_deadlines`.
- **Modify** `backend/app/models/models.py` — add `AgentAuditLog` model.
- **Create** `backend/alembic/versions/r8_agent_audit_log_20260528.py` — migration for `agent_audit_log` table.
- **Modify** `backend/app/tools/tool_registry.py` — register new tools; new `PIPELINE_WRITE_TOOLS` / `PIPELINE_READ_TOOLS` groups; expose to supervisor agent.
- **Modify** `backend/app/api/routes/agents.py` — extend `/execute` dispatcher with the seven new write action types; ensure `user_role` / `user_id` flow into tool invocations.
- **Modify** `frontend/src/components/copilot/GlobalCopilot.tsx` — render `confirmation_required` and `forbidden` messages as inline cards with `Confirm`/`Cancel` buttons; on confirm, POST to `/api/v1/agents/execute`.

---

## Task 1: RBAC helper + `propose_action` factory

**Files:**
- Create: `backend/app/tools/_rbac.py`
- Test: `backend/tests/test_tools_rbac.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_tools_rbac.py
import pytest
from app.tools._rbac import (
    EDIT_ROLES, INVESTOR_ROLES, SECRETARIAT_ONLY,
    require_role, propose_action,
)
from app.types.auth import UserRole  # only used for the enum

def test_edit_roles_membership():
    assert UserRole.ADMIN in EDIT_ROLES
    assert UserRole.SECRETARIAT_LEAD in EDIT_ROLES
    assert UserRole.FACILITATOR in EDIT_ROLES
    assert UserRole.TWG_MEMBER not in EDIT_ROLES

def test_require_role_passes_for_allowed():
    err = require_role(UserRole.ADMIN, EDIT_ROLES)
    assert err is None

def test_require_role_returns_forbidden_for_disallowed():
    err = require_role(UserRole.TWG_MEMBER, EDIT_ROLES)
    assert err == {
        "status": "forbidden",
        "reason": "Requires one of: ADMIN, SECRETARIAT_LEAD, FACILITATOR",
    }

def test_propose_action_shape():
    out = propose_action(
        action_type="advance_project_stage",
        summary="Advance \"X\" to SUMMIT_READY.",
        payload={"project_id": "abc", "target_stage": "SUMMIT_READY"},
        irreversible=False,
    )
    assert out["status"] == "confirmation_required"
    assert out["action_type"] == "advance_project_stage"
    assert out["summary"].startswith("Advance")
    assert out["payload"]["project_id"] == "abc"
    assert "action_id" in out and len(out["action_id"]) >= 8
    assert out["confirm_endpoint"] == "/api/v1/agents/execute"
    assert out["irreversible"] is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_tools_rbac.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.tools._rbac'`.

- [ ] **Step 3: Implement `_rbac.py`**

Create `backend/app/tools/_rbac.py`:
```python
"""Role gates + confirm-then-execute payload factory for Martin write tools."""
from __future__ import annotations

import uuid as _uuid
from typing import Iterable, Optional, Set

from app.types.auth import UserRole

# Mirrors frontend RBAC groups so the agent's writes match what the UI allows.
EDIT_ROLES: Set[UserRole] = {
    UserRole.ADMIN, UserRole.SECRETARIAT_LEAD, UserRole.FACILITATOR,
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_tools_rbac.py -v`
Expected: 4 PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/tools/_rbac.py backend/tests/test_tools_rbac.py
git commit -m "feat(agent): RBAC helper + propose_action factory for confirm-then-execute"
```

---

## Task 2: `AgentAuditLog` model + Alembic migration

**Files:**
- Modify: `backend/app/models/models.py` (append a new class at the end of the models module)
- Create: `backend/alembic/versions/r8_agent_audit_log_20260528.py`

- [ ] **Step 1: Append the model**

Open `backend/app/models/models.py` and append at the end of the file (after the last existing model class):
```python
class AgentAuditLog(Base):
    """One row per Martin-executed write. Pairs with project_status_history
    for stage moves but is the catch-all for everything else."""
    __tablename__ = "agent_audit_log"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    user_role: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    action_id: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, index=True)
    tool_name: Mapped[str] = mapped_column(String(80), nullable=False)
    target_type: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    target_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    before_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    after_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
```

(All referenced types — `Mapped`, `mapped_column`, `uuid`, `datetime`, `String`, `Text`, `JSON`, `DateTime`, `Uuid`, `ForeignKey`, `Optional`, `Base` — are already imported at the top of this file.)

- [ ] **Step 2: Smoke-test the model import**

Run: `cd backend && source .venv/bin/activate && python -c "from app.models.models import AgentAuditLog; print(AgentAuditLog.__tablename__)"`
Expected: prints `agent_audit_log`.

- [ ] **Step 3: Create the Alembic migration**

Create `backend/alembic/versions/r8_agent_audit_log_20260528.py`:
```python
"""add agent_audit_log table

Revision ID: r8_agent_audit
Revises: r8_s3ct0r_d3t
Create Date: 2026-05-28
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = 'r8_agent_audit'
down_revision = 'r8_s3ct0r_d3t'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Idempotent: prod has historically been schema-modified out-of-band.
    op.execute("""
        CREATE TABLE IF NOT EXISTS agent_audit_log (
            id            UUID PRIMARY KEY,
            created_at    TIMESTAMP NOT NULL DEFAULT now(),
            user_id       UUID REFERENCES users(id) ON DELETE SET NULL,
            user_role     VARCHAR(50),
            action_id     VARCHAR(32),
            tool_name     VARCHAR(80) NOT NULL,
            target_type   VARCHAR(40),
            target_id     VARCHAR(64),
            before_json   JSONB,
            after_json    JSONB,
            summary       TEXT
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_agent_audit_log_created_at ON agent_audit_log (created_at)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_agent_audit_log_action_id ON agent_audit_log (action_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS agent_audit_log")
```

- [ ] **Step 4: Apply locally**

Run: `cd backend && source .venv/bin/activate && set -a && source .env && set +a && alembic upgrade head 2>&1 | tail -3`
Expected: completes without error.

- [ ] **Step 5: Verify table exists**

Run: `cd backend && source .venv/bin/activate && set -a && source .env && set +a && python -c "from sqlalchemy import create_engine, inspect; import os; e = create_engine(os.environ['DATABASE_URL']); print('agent_audit_log' in inspect(e).get_table_names())"`
Expected: prints `True`.

- [ ] **Step 6: Commit**

```bash
git add backend/app/models/models.py backend/alembic/versions/r8_agent_audit_log_20260528.py
git commit -m "feat(agent): AgentAuditLog model + migration for Martin write trail"
```

---

## Task 3: `advance_project_stage` tool

**Files:**
- Create: `backend/app/tools/pipeline_write_tools.py`
- Test: `backend/tests/test_pipeline_write_tools.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_pipeline_write_tools.py
import pytest
from app.tools.pipeline_write_tools import advance_project_stage
from app.types.auth import UserRole

@pytest.mark.asyncio
async def test_advance_returns_forbidden_for_twg_member():
    result = await advance_project_stage(
        project_id="bogus", target_stage="SUMMIT_READY",
        user_id="u1", user_role=UserRole.TWG_MEMBER, confirmed=False, action_id=None,
    )
    assert result["status"] == "forbidden"
    assert "FACILITATOR" in result["reason"]

@pytest.mark.asyncio
async def test_advance_returns_confirmation_required_for_facilitator():
    # Note: needs a real project_id; use the smoke-test fixture if your test DB has
    # any seeded projects, otherwise this assertion only requires the proposal shape.
    result = await advance_project_stage(
        project_id="00000000-0000-0000-0000-000000000000",
        target_stage="SUMMIT_READY",
        user_id="u1", user_role=UserRole.FACILITATOR, confirmed=False, action_id=None,
    )
    # Either project not found OR confirmation_required:
    assert result["status"] in {"confirmation_required", "not_found"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_pipeline_write_tools.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.tools.pipeline_write_tools'`.

- [ ] **Step 3: Implement `pipeline_write_tools.py` with `advance_project_stage`**

Create `backend/app/tools/pipeline_write_tools.py`:
```python
"""Confirm-then-execute write tools for the deal pipeline."""
from __future__ import annotations

from typing import Optional
from uuid import UUID

from sqlalchemy import select
from app.core.database import async_session_maker
from app.models.models import Project, ProjectStatus
from app.tools._rbac import (
    EDIT_ROLES, INVESTOR_ROLES, propose_action, require_role,
)
from app.types.auth import UserRole

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
    async with async_session_maker() as db:
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_pipeline_write_tools.py -v`
Expected: 2 PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/tools/pipeline_write_tools.py backend/tests/test_pipeline_write_tools.py
git commit -m "feat(agent): advance_project_stage tool with role gate + proposal payload"
```

---

## Task 4: `decline_project`, `mark_flagship`, `rescore_project`, `graduate_from_incubation` tools

**Files:**
- Modify: `backend/app/tools/pipeline_write_tools.py` (append)
- Modify: `backend/tests/test_pipeline_write_tools.py` (append tests)

- [ ] **Step 1: Append the four tools**

Open `backend/app/tools/pipeline_write_tools.py` and append:
```python
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

    async with async_session_maker() as db:
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

    async with async_session_maker() as db:
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

    async with async_session_maker() as db:
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

    async with async_session_maker() as db:
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
```

- [ ] **Step 2: Append tests**

In `backend/tests/test_pipeline_write_tools.py` append:
```python
from app.tools.pipeline_write_tools import (
    decline_project, mark_flagship, rescore_project, graduate_from_incubation,
)

@pytest.mark.asyncio
async def test_decline_requires_reason():
    result = await decline_project(
        project_id="00000000-0000-0000-0000-000000000000", reason="",
        user_id="u1", user_role=UserRole.SECRETARIAT_LEAD,
    )
    assert result["status"] == "invalid_input"

@pytest.mark.asyncio
async def test_mark_flagship_forbidden_for_facilitator():
    # Facilitator can edit but not toggle flagship.
    result = await mark_flagship(
        project_id="00000000-0000-0000-0000-000000000000", is_flagship=True,
        user_id="u1", user_role=UserRole.FACILITATOR,
    )
    assert result["status"] == "forbidden"

@pytest.mark.asyncio
async def test_rescore_allowed_for_facilitator():
    result = await rescore_project(
        project_id="00000000-0000-0000-0000-000000000000",
        user_id="u1", user_role=UserRole.FACILITATOR,
    )
    assert result["status"] in {"confirmation_required", "not_found"}

@pytest.mark.asyncio
async def test_graduate_forbidden_for_member():
    result = await graduate_from_incubation(
        project_id="00000000-0000-0000-0000-000000000000",
        user_id="u1", user_role=UserRole.TWG_MEMBER,
    )
    assert result["status"] == "forbidden"
```

- [ ] **Step 3: Run tests**

Run: `cd backend && pytest tests/test_pipeline_write_tools.py -v`
Expected: 6 PASS (2 from Task 3 + 4 new).

- [ ] **Step 4: Commit**

```bash
git add backend/app/tools/pipeline_write_tools.py backend/tests/test_pipeline_write_tools.py
git commit -m "feat(agent): decline/mark_flagship/rescore/graduate tools + RBAC tests"
```

---

## Task 5: `create_action_item` + `bulk_create_action_items` tools

**Files:**
- Modify: `backend/app/tools/pipeline_write_tools.py` (append)
- Modify: `backend/tests/test_pipeline_write_tools.py` (append tests)

- [ ] **Step 1: Append both tools**

In `backend/app/tools/pipeline_write_tools.py`, add the imports at the top (next to existing imports) if missing:
```python
from datetime import date, datetime
from typing import List
```
And append at the bottom of the file:
```python
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
```

- [ ] **Step 2: Append tests**

```python
from app.tools.pipeline_write_tools import create_action_item, bulk_create_action_items

@pytest.mark.asyncio
async def test_create_action_item_requires_description():
    result = await create_action_item(
        description="", user_id="u1", user_role=UserRole.FACILITATOR,
    )
    assert result["status"] == "invalid_input"

@pytest.mark.asyncio
async def test_create_action_item_proposes():
    result = await create_action_item(
        description="Get permits for Project X",
        user_id="u1", user_role=UserRole.FACILITATOR,
        due_date="2026-06-15", priority="high",
    )
    assert result["status"] == "confirmation_required"
    assert result["action_type"] == "create_action_item"
    assert result["payload"]["due_date"] == "2026-06-15"

@pytest.mark.asyncio
async def test_bulk_create_caps_at_50():
    result = await bulk_create_action_items(
        meeting_id="m1",
        items=[{"description": f"task {i}"} for i in range(51)],
        user_id="u1", user_role=UserRole.FACILITATOR,
    )
    assert result["status"] == "invalid_input"
    assert "max 50" in result["reason"]
```

- [ ] **Step 3: Run tests**

Run: `cd backend && pytest tests/test_pipeline_write_tools.py -v`
Expected: 9 PASS.

- [ ] **Step 4: Commit**

```bash
git add backend/app/tools/pipeline_write_tools.py backend/tests/test_pipeline_write_tools.py
git commit -m "feat(agent): create_action_item + bulk_create_action_items tools"
```

---

## Task 6: Read-only pipeline tools

**Files:**
- Create: `backend/app/tools/pipeline_read_tools.py`
- Test: `backend/tests/test_pipeline_read_tools.py`

- [ ] **Step 1: Write the file**

Create `backend/app/tools/pipeline_read_tools.py`:
```python
"""Read-only pipeline tools — no confirm protocol, just return data."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from sqlalchemy import and_, func, select

from app.core.database import async_session_maker
from app.models.models import (
    ActionItem, Meeting, Project, ProjectStatus,
)
from app.types.auth import UserRole


# Threshold below which an Incubation project counts as "close to graduation".
_NEAR_GRAD_GAP = 5


async def pipeline_summary(
    user_id: str,
    user_role: UserRole,
    scope: str = "all",        # "all" | "twg" | "mine"
    period: str = "week",      # "week" | "month"
    twg_id: Optional[str] = None,
) -> dict:
    """Counts by stage + total investment + period delta. Scope 'twg' / 'mine'
    requires twg_id (caller's TWG) — enforced upstream by the dispatcher."""
    if scope not in {"all", "twg", "mine"}:
        return {"status": "invalid_input", "reason": "scope must be all/twg/mine"}
    if period not in {"week", "month"}:
        return {"status": "invalid_input", "reason": "period must be week/month"}

    window_days = 7 if period == "week" else 30
    since = datetime.utcnow() - timedelta(days=window_days)

    async with async_session_maker() as db:
        q = select(Project.status, func.count(Project.id), func.coalesce(func.sum(Project.investment_size), 0))
        if scope in {"twg", "mine"} and twg_id:
            q = q.where(Project.twg_id == UUID(twg_id))
        rows = (await q.group_by(Project.status)).all()

        # Period delta = projects whose updated_at fell into the window.
        delta_q = select(func.count(Project.id)).where(Project.updated_at >= since)
        if scope in {"twg", "mine"} and twg_id:
            delta_q = delta_q.where(Project.twg_id == UUID(twg_id))
        moved = (await db.execute(delta_q)).scalar_one()

    by_stage = [
        {
            "stage": (s.value if hasattr(s, "value") else str(s)),
            "count": int(c),
            "value": float(v),
        }
        for s, c, v in rows
    ]
    total = sum(item["count"] for item in by_stage)
    total_value = sum(item["value"] for item in by_stage)
    return {
        "status": "ok",
        "scope": scope,
        "period": period,
        "total_projects": total,
        "total_investment": total_value,
        "by_stage": by_stage,
        "moved_in_window": int(moved),
    }


async def at_risk_projects(
    user_id: str,
    user_role: UserRole,
    twg_id: Optional[str] = None,
) -> dict:
    """Projects pending AI review > 3d OR missing gender/youth signals."""
    cutoff = datetime.utcnow() - timedelta(days=3)
    async with async_session_maker() as db:
        q = select(Project).where(
            (Project.afcen_score.is_(None) & (Project.created_at < cutoff))
            | (Project.gender_intentional.is_(None))
            | (Project.youth_focused.is_(None))
        )
        if twg_id:
            q = q.where(Project.twg_id == UUID(twg_id))
        rows = (await db.execute(q.limit(50))).scalars().all()
    projects = [
        {
            "id": str(p.id),
            "name": p.name,
            "stage": p.status.value if p.status else None,
            "investment": float(p.investment_size or 0),
            "missing_afcen": p.afcen_score is None,
            "missing_gender_signal": p.gender_intentional is None,
            "missing_youth_signal": p.youth_focused is None,
        }
        for p in rows
    ]
    return {"status": "ok", "count": len(projects), "projects": projects}


async def incubation_close_to_graduation(
    user_id: str,
    user_role: UserRole,
    twg_id: Optional[str] = None,
) -> dict:
    """Incubation projects with AfCEN within _NEAR_GRAD_GAP of the threshold (default 40)."""
    threshold = 40  # default graduation threshold; the UI also allows overrides
    async with async_session_maker() as db:
        q = select(Project).where(
            Project.status == ProjectStatus.INCUBATION,
            Project.afcen_score.is_not(None),
            Project.afcen_score >= (threshold - _NEAR_GRAD_GAP),
        )
        if twg_id:
            q = q.where(Project.twg_id == UUID(twg_id))
        rows = (await db.execute(q.limit(50))).scalars().all()
    return {
        "status": "ok",
        "threshold": threshold,
        "count": len(rows),
        "projects": [
            {
                "id": str(p.id),
                "name": p.name,
                "afcen_score": float(p.afcen_score or 0),
                "gap_to_graduation": threshold - float(p.afcen_score or 0),
            }
            for p in rows
        ],
    }


async def my_action_items(
    user_id: str,
    user_role: UserRole,
    status: Optional[str] = None,   # PENDING / IN_PROGRESS / COMPLETED / OVERDUE
) -> dict:
    """Action items assigned to this user."""
    async with async_session_maker() as db:
        q = select(ActionItem).where(ActionItem.owner_id == UUID(user_id))
        if status:
            q = q.where(ActionItem.status == status)
        rows = (await db.execute(q.order_by(ActionItem.due_date.asc()).limit(100))).scalars().all()
    return {
        "status": "ok",
        "count": len(rows),
        "items": [
            {
                "id": str(it.id),
                "description": it.description,
                "due_date": it.due_date.isoformat() if it.due_date else None,
                "priority": getattr(it, "priority", None),
                "status": it.status,
            }
            for it in rows
        ],
    }


async def next_deadlines(
    user_id: str,
    user_role: UserRole,
    window: str = "7d",
) -> dict:
    """Combined upcoming meetings + action items in the next window."""
    try:
        days = int(window.rstrip("d"))
    except ValueError:
        return {"status": "invalid_input", "reason": "window must be like '7d'"}
    horizon = datetime.utcnow() + timedelta(days=days)

    async with async_session_maker() as db:
        meetings = (await db.execute(
            select(Meeting).where(
                Meeting.scheduled_at >= datetime.utcnow(),
                Meeting.scheduled_at <= horizon,
            ).order_by(Meeting.scheduled_at.asc()).limit(20)
        )).scalars().all()

        items = (await db.execute(
            select(ActionItem).where(
                ActionItem.owner_id == UUID(user_id),
                ActionItem.due_date.is_not(None),
                ActionItem.due_date <= horizon.date(),
            ).order_by(ActionItem.due_date.asc()).limit(20)
        )).scalars().all()

    return {
        "status": "ok",
        "window_days": days,
        "meetings": [
            {"id": str(m.id), "title": m.title, "when": m.scheduled_at.isoformat()}
            for m in meetings
        ],
        "action_items": [
            {"id": str(it.id), "description": it.description,
             "due_date": it.due_date.isoformat() if it.due_date else None}
            for it in items
        ],
    }
```

- [ ] **Step 2: Write the test**

```python
# backend/tests/test_pipeline_read_tools.py
import pytest
from app.tools.pipeline_read_tools import (
    pipeline_summary, my_action_items, next_deadlines,
)
from app.types.auth import UserRole

@pytest.mark.asyncio
async def test_pipeline_summary_rejects_bad_scope():
    r = await pipeline_summary(user_id="u", user_role=UserRole.ADMIN, scope="weird")
    assert r["status"] == "invalid_input"

@pytest.mark.asyncio
async def test_pipeline_summary_returns_shape():
    r = await pipeline_summary(user_id="u", user_role=UserRole.ADMIN, scope="all", period="week")
    assert r["status"] == "ok"
    assert "by_stage" in r and "total_projects" in r and "moved_in_window" in r

@pytest.mark.asyncio
async def test_next_deadlines_rejects_bad_window():
    r = await next_deadlines(user_id="00000000-0000-0000-0000-000000000000",
                             user_role=UserRole.ADMIN, window="7days")
    assert r["status"] == "invalid_input"
```

- [ ] **Step 3: Run tests**

Run: `cd backend && pytest tests/test_pipeline_read_tools.py -v`
Expected: 3 PASS.

- [ ] **Step 4: Commit**

```bash
git add backend/app/tools/pipeline_read_tools.py backend/tests/test_pipeline_read_tools.py
git commit -m "feat(agent): read-only pipeline tools (summary, at_risk, near_grad, mine, deadlines)"
```

---

## Task 7: Register new tools in `tool_registry`

**Files:**
- Modify: `backend/app/tools/tool_registry.py`

- [ ] **Step 1: Add two new tool groups near the existing groups (around line 27)**

Open `backend/app/tools/tool_registry.py` and after the existing `DEAL_PIPELINE_TOOLS` set (around line 65), add:
```python
# Pipeline write tools — gated by user role (not by agent id). Exposed on the supervisor agent.
PIPELINE_WRITE_TOOLS: Set[str] = {
    "advance_project_stage",
    "decline_project",
    "mark_flagship",
    "rescore_project",
    "graduate_from_incubation",
    "create_action_item",
    "bulk_create_action_items",
}

# Pipeline read tools — no role gate beyond TWG scoping where applicable.
PIPELINE_READ_TOOLS: Set[str] = {
    "pipeline_summary",
    "at_risk_projects",
    "incubation_close_to_graduation",
    "my_action_items",
    "next_deadlines",
}
```

- [ ] **Step 2: Register them in `register_all`**

Inside `ToolRegistry.register_all` (around line 154), after the existing `from app.tools.deal_pipeline_tools import DEAL_PIPELINE_TOOLS as DP_TOOLS` block, add:
```python
        # Pipeline write tools (Tier 1)
        from app.tools.pipeline_write_tools import (
            advance_project_stage, decline_project, mark_flagship, rescore_project,
            graduate_from_incubation, create_action_item, bulk_create_action_items,
        )
        for fn, name in [
            (advance_project_stage, "advance_project_stage"),
            (decline_project, "decline_project"),
            (mark_flagship, "mark_flagship"),
            (rescore_project, "rescore_project"),
            (graduate_from_incubation, "graduate_from_incubation"),
            (create_action_item, "create_action_item"),
            (bulk_create_action_items, "bulk_create_action_items"),
        ]:
            self._tools[name] = fn

        # Pipeline read tools (Tier 1)
        from app.tools.pipeline_read_tools import (
            pipeline_summary, at_risk_projects, incubation_close_to_graduation,
            my_action_items, next_deadlines,
        )
        for fn, name in [
            (pipeline_summary, "pipeline_summary"),
            (at_risk_projects, "at_risk_projects"),
            (incubation_close_to_graduation, "incubation_close_to_graduation"),
            (my_action_items, "my_action_items"),
            (next_deadlines, "next_deadlines"),
        ]:
            self._tools[name] = fn
```

(If the existing registration code uses a different storage pattern — e.g. registering descriptions alongside — open the file and follow that pattern. The above assumes `self._tools` is a `name → callable` dict, matching the read of the file earlier.)

- [ ] **Step 3: Allow these tool names through `validate_tool_access`**

In `validate_tool_access` (around line 389), after the existing `DEAL_PIPELINE_TOOLS` branch (around line 431), add:
```python
        if tool_name in PIPELINE_WRITE_TOOLS or tool_name in PIPELINE_READ_TOOLS:
            # User-role gating is enforced inside each tool body via _rbac.require_role.
            # Only the supervisor agent is allowed to invoke them.
            if agent_id and agent_id != "supervisor_v1" and not agent_id.startswith("twg_"):
                return False
            return True
```

- [ ] **Step 4: Sanity-check the registry loads**

Run: `cd backend && source .venv/bin/activate && python -c "from app.tools.tool_registry import ToolRegistry; r = ToolRegistry(); r.register_all(); print(sorted(r._tools.keys()))" 2>&1 | tail -3`
Expected: prints a list that includes `advance_project_stage`, `pipeline_summary`, etc.

- [ ] **Step 5: Commit**

```bash
git add backend/app/tools/tool_registry.py
git commit -m "feat(agent): register PIPELINE_WRITE/READ tool groups on supervisor"
```

---

## Task 8: Wire `user_role` / `user_id` into tool invocations + extend `/execute` dispatcher

**Files:**
- Modify: `backend/app/api/routes/agents.py`

- [ ] **Step 1: Pass `user_role` / `user_id` into the tool-invocation kwargs**

Find the spot in `agents.py` where the agent invokes a tool (search for `validate_tool_access` and `_tools[`). At that call site, add `user_id=str(current_user.id), user_role=current_user.role` to the kwargs passed into the tool function. If the agent loop builds a `tool_kwargs` dict, mutate it there; if it calls `await tool_fn(**args)`, merge in those two keys.

- [ ] **Step 2: Add new `action_type` handlers to `/execute`**

In `agents.py`, locate the `@router.post("/execute")` block (around line 1310) and the dispatcher switch on `action_type`. After the existing `schedule_meeting` and `create_action_item` branches add seven new branches calling new helper functions:

```python
        elif action_type == "advance_project_stage":
            return await _execute_advance_project_stage(payload, current_user, db, request.action_id)
        elif action_type == "decline_project":
            return await _execute_decline_project(payload, current_user, db, request.action_id)
        elif action_type == "mark_flagship":
            return await _execute_mark_flagship(payload, current_user, db, request.action_id)
        elif action_type == "rescore_project":
            return await _execute_rescore_project(payload, current_user, db, request.action_id)
        elif action_type == "graduate_from_incubation":
            return await _execute_graduate_from_incubation(payload, current_user, db, request.action_id)
        elif action_type == "bulk_create_action_items":
            return await _execute_bulk_create_action_items(payload, current_user, db, request.action_id)
```

(The existing `create_action_item` branch already handles single-item creation, but our new `pipeline_write_tools.create_action_item` proposes the same `action_type`. Verify both paths produce the same DB write; if the existing branch already creates the row, no new code is needed for `create_action_item`.)

- [ ] **Step 3: Add the helpers at the bottom of `agents.py`**

Append (after the existing `_execute_create_action_item` helper):
```python
from app.models.models import (
    AgentAuditLog, ActionItem, Project, ProjectStatus, ProjectStatusHistory,
)
from app.services.project_pipeline_service import ProjectPipelineService


async def _audit(db, *, user, action_id, tool_name, target_id, before, after, summary):
    db.add(AgentAuditLog(
        user_id=user.id, user_role=user.role.value if hasattr(user.role, "value") else str(user.role),
        action_id=action_id, tool_name=tool_name,
        target_type="project", target_id=str(target_id) if target_id else None,
        before_json=before, after_json=after, summary=summary,
    ))


async def _execute_advance_project_stage(payload, current_user, db, action_id):
    from uuid import UUID
    pid = UUID(payload["project_id"])
    target = ProjectStatus(payload["target_stage"])
    row = (await db.execute(select(Project).where(Project.id == pid))).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Project not found")
    before_stage = row.status.value if row.status else None
    row.status = target
    db.add(ProjectStatusHistory(
        project_id=pid, previous_stage=before_stage, new_stage=target.value,
        changed_by_id=current_user.id, notes=payload.get("notes") or "",
    ))
    await _audit(db, user=current_user, action_id=action_id, tool_name="advance_project_stage",
                 target_id=pid, before={"status": before_stage}, after={"status": target.value},
                 summary=f"advance {before_stage} -> {target.value}")
    await db.commit()
    return {"status": "ok", "project_id": str(pid), "stage": target.value}


async def _execute_decline_project(payload, current_user, db, action_id):
    from uuid import UUID
    pid = UUID(payload["project_id"])
    row = (await db.execute(select(Project).where(Project.id == pid))).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Project not found")
    before_stage = row.status.value if row.status else None
    row.status = ProjectStatus.DECLINED
    db.add(ProjectStatusHistory(
        project_id=pid, previous_stage=before_stage, new_stage=ProjectStatus.DECLINED.value,
        changed_by_id=current_user.id, notes=payload.get("reason", ""),
    ))
    await _audit(db, user=current_user, action_id=action_id, tool_name="decline_project",
                 target_id=pid, before={"status": before_stage}, after={"status": "DECLINED"},
                 summary=f"declined: {payload.get('reason', '')[:140]}")
    await db.commit()
    return {"status": "ok", "project_id": str(pid)}


async def _execute_mark_flagship(payload, current_user, db, action_id):
    from uuid import UUID
    pid = UUID(payload["project_id"])
    row = (await db.execute(select(Project).where(Project.id == pid))).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Project not found")
    before = bool(getattr(row, "is_flagship", False))
    row.is_flagship = bool(payload["is_flagship"])
    await _audit(db, user=current_user, action_id=action_id, tool_name="mark_flagship",
                 target_id=pid, before={"is_flagship": before}, after={"is_flagship": row.is_flagship},
                 summary=f"flagship {before} -> {row.is_flagship}")
    await db.commit()
    return {"status": "ok", "project_id": str(pid), "is_flagship": row.is_flagship}


async def _execute_rescore_project(payload, current_user, db, action_id):
    from uuid import UUID
    pid = UUID(payload["project_id"])
    service = ProjectPipelineService(db)
    result = await service.score_project(pid)  # uses existing scoring code path
    await _audit(db, user=current_user, action_id=action_id, tool_name="rescore_project",
                 target_id=pid, before=None, after={"afcen_score": result.get("afcen_score")},
                 summary=f"rescored -> {result.get('afcen_score')}")
    await db.commit()
    return {"status": "ok", "project_id": str(pid), "score": result}


async def _execute_graduate_from_incubation(payload, current_user, db, action_id):
    from uuid import UUID
    pid = UUID(payload["project_id"])
    row = (await db.execute(select(Project).where(Project.id == pid))).scalar_one_or_none()
    if not row or row.status != ProjectStatus.INCUBATION:
        raise HTTPException(status_code=409, detail="Project is not in Incubation")
    row.status = ProjectStatus.DRAFT
    db.add(ProjectStatusHistory(
        project_id=pid, previous_stage=ProjectStatus.INCUBATION.value,
        new_stage=ProjectStatus.DRAFT.value, changed_by_id=current_user.id,
        notes="Graduated from Incubation via Martin.",
    ))
    await _audit(db, user=current_user, action_id=action_id, tool_name="graduate_from_incubation",
                 target_id=pid, before={"status": "INCUBATION"}, after={"status": "DRAFT"},
                 summary="incubation -> draft")
    await db.commit()
    return {"status": "ok", "project_id": str(pid)}


async def _execute_bulk_create_action_items(payload, current_user, db, action_id):
    from uuid import UUID
    meeting_id = UUID(payload["meeting_id"])
    created = []
    for it in payload["items"]:
        ai = ActionItem(
            description=it["description"].strip(),
            meeting_id=meeting_id,
            owner_id=UUID(it["owner_user_id"]) if it.get("owner_user_id") else None,
            due_date=it.get("due_date"),
            priority=it.get("priority", "medium"),
            status="PENDING",
        )
        db.add(ai)
        created.append(ai)
    await db.flush()
    await _audit(db, user=current_user, action_id=action_id, tool_name="bulk_create_action_items",
                 target_id=meeting_id, before=None,
                 after={"count": len(created)}, summary=f"created {len(created)} action items")
    await db.commit()
    return {"status": "ok", "count": len(created), "ids": [str(a.id) for a in created]}
```

(If the existing `_execute_create_action_item` body in `agents.py` uses different ActionItem field names than `description`/`owner_id`/`due_date`/`priority`/`status`, open it and copy the same field assignments verbatim into `_execute_bulk_create_action_items`.)

- [ ] **Step 4: Restart backend + smoke import**

Run: `cd backend && source .venv/bin/activate && python -c "import app.api.routes.agents; print('agents.py imports cleanly')"`
Expected: prints the message with no traceback.

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/routes/agents.py
git commit -m "feat(agent): /execute dispatcher for 6 new pipeline write actions + audit"
```

---

## Task 9: Frontend confirm-card rendering in `GlobalCopilot`

**Files:**
- Modify: `frontend/src/components/copilot/GlobalCopilot.tsx`

- [ ] **Step 1: Detect confirmation_required + forbidden agent messages**

Open `frontend/src/components/copilot/GlobalCopilot.tsx`. Find where assistant/agent messages are rendered (the `localMessages.map(...)` loop you wrote during the editorial migration). Inside that map, before rendering the standard markdown bubble, parse the message content for a JSON envelope. If the message text begins with `{` and parses as JSON with `status === 'confirmation_required'`, render a confirm card instead. Add this helper right above the JSX return (next to existing helpers like `monogram`):
```tsx
type ConfirmCard = {
    status: 'confirmation_required';
    type?: string;
    action_id: string;
    action_type: string;
    summary: string;
    payload: Record<string, any>;
    irreversible?: boolean;
    confirm_endpoint: string;
};

function tryParseConfirm(content: string): ConfirmCard | null {
    const trimmed = content.trim();
    if (!trimmed.startsWith('{')) return null;
    try {
        const j = JSON.parse(trimmed);
        if (j && j.status === 'confirmation_required' && j.action_id && j.confirm_endpoint) return j as ConfirmCard;
    } catch { /* not JSON */ }
    return null;
}

async function executeConfirm(card: ConfirmCard): Promise<string> {
    const resp = await fetch(card.confirm_endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ action_id: card.action_id, action_type: card.action_type, payload: card.payload }),
    });
    const data = await resp.json().catch(() => ({}));
    if (!resp.ok) return `Action failed: ${data.detail || resp.statusText}`;
    return data.status === 'ok' ? 'Done.' : JSON.stringify(data);
}
```

- [ ] **Step 2: Render the card inside the message map**

Replace the rendering of an assistant message body (the inner branch where `msg.sender !== 'user'`) so that it first checks for a confirm card:
```tsx
{msg.sender !== 'user' && (() => {
    const card = tryParseConfirm(msg.content);
    if (card) {
        return (
            <div style={{
                padding: 12, border: '1px solid var(--border)', background: 'var(--ink-50)',
                fontFamily: "'Geist', 'Inter', system-ui, sans-serif",
            }}>
                <div style={{
                    fontSize: 10, letterSpacing: '0.14em', textTransform: 'uppercase',
                    fontWeight: 600, color: card.irreversible ? 'var(--terra)' : 'var(--accent)', marginBottom: 8,
                }}>
                    {card.irreversible ? 'Irreversible action' : 'Confirm action'}
                </div>
                <div style={{ fontSize: 13, color: 'var(--ink-900)', marginBottom: 12 }}>{card.summary}</div>
                <div style={{ display: 'flex', gap: 8 }}>
                    <button
                        onClick={async () => {
                            const result = await executeConfirm(card);
                            setLocalMessages(prev => [
                                ...prev,
                                { id: `r_${card.action_id}`, sender: 'agent', content: result, timestamp: new Date().toISOString() },
                            ]);
                        }}
                        style={{
                            background: 'var(--accent)', border: '1px solid var(--accent)', color: 'var(--accent-ink)',
                            padding: '7px 14px', fontSize: 12, fontWeight: 500, cursor: 'pointer', fontFamily: 'inherit',
                        }}
                    >Confirm</button>
                    <button
                        onClick={() => {
                            setLocalMessages(prev => [
                                ...prev,
                                { id: `c_${card.action_id}`, sender: 'agent', content: 'Cancelled.', timestamp: new Date().toISOString() },
                            ]);
                        }}
                        style={{
                            background: 'transparent', border: '1px solid var(--border)', color: 'var(--ink-700)',
                            padding: '7px 14px', fontSize: 12, fontWeight: 500, cursor: 'pointer', fontFamily: 'inherit',
                        }}
                    >Cancel</button>
                </div>
            </div>
        );
    }
    // …existing markdown / forbidden rendering stays here…
    return null;  // (leave the existing JSX for the default case in its current spot)
})()}
```

(In practice, do not delete the existing default JSX — wrap the `tryParseConfirm` branch as an early return *before* the existing markdown render so the rest of the bubble logic stays unchanged.)

- [ ] **Step 3: Typecheck**

Run: `cd frontend && npx tsc --noEmit -p tsconfig.json 2>&1 | grep GlobalCopilot`
Expected: no output.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/copilot/GlobalCopilot.tsx
git commit -m "feat(copilot): inline Confirm/Cancel card for agent confirmation_required messages"
```

---

## Task 10: End-to-end smoke + push

- [ ] **Step 1: Backend tests pass**

Run: `cd backend && pytest tests/test_tools_rbac.py tests/test_pipeline_write_tools.py tests/test_pipeline_read_tools.py -v`
Expected: all tests green (≥ 12 passing).

- [ ] **Step 2: Frontend typecheck clean**

Run: `cd frontend && npx tsc --noEmit -p tsconfig.json`
Expected: exit 0.

- [ ] **Step 3: Manual smoke (one prompt per category)**

Start backend + frontend (`uvicorn app.main:app --reload` and `npm run dev`). In the chat as an admin user, send each of these prompts. Each should either produce a confirm card or return data:

- "Move project X to Summit Ready." → expect a card with Confirm / Cancel.
- "Decline project Y because the financials are unverified." → card with red `Irreversible action` header.
- "Mark project Z as flagship." → card.
- "Re-score project X." → card.
- "Graduate project A from Incubation." → card.
- "Create an action item: get permits for project X due 2026-06-30 high priority." → card.
- "Summarise the pipeline this week." → data response, no card.
- "What's at risk?" → data response.
- "Show projects close to graduation." → data response.
- "What's on my plate this week?" → data response.

Click Confirm on one card; verify the project record changes in the DB and an `agent_audit_log` row was written.

- [ ] **Step 4: Push**

```bash
git push origin main
```

---

## Notes for the implementer
- **Idempotency** — every `_execute_*` helper relies on the existing `_get_action(action_id, user_id)` in `agents.py`: a confirmed `action_id` is consumed (removed from the dict) before the handler runs. The shipped pattern already prevents double-execution; don't re-implement it.
- **Audit** — always commit the `AgentAuditLog` row in the same transaction as the actual write. The provided helpers do this via the `_audit(...)` call followed by `await db.commit()`.
- **Don't gate by agent id** for the new tools — gate by `user_role` inside each tool body via `_rbac.require_role`. The registry-side `validate_tool_access` only checks that the tool runs from the supervisor agent.
- **Tier 2 / Tier 3 tools** (project CRUD, scoring weights, minutes approval, invitations) are explicitly out of scope for this plan — they get their own spec + plan when prioritised.
