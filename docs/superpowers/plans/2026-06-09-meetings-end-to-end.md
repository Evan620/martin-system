# Meetings (Member App) End-to-End — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. *(This plan is being executed via a dynamic Workflow at the user's request; the same task order + gates apply.)*

**Goal:** Make the member app's Meetings page real and working end-to-end against the live platform — list, detail, Join (Google Meet), and member RSVP (Going/Maybe/No) via both tap-buttons and Martin.

**Architecture:** Backend adds a `TENTATIVE` RSVP state, a member self-RSVP REST route, and the `rsvp_meeting` Martin tool — all writing the *same* `MeetingParticipant.rsvp_status` via one shared helper. The Flutter app mirrors the existing auth feature (Dio + bearer interceptor, Riverpod `NotifierProvider`, repository→model, manual `fromJson`, sealed states) to wire the existing glass UI to live data.

**Tech Stack:** Backend — FastAPI, SQLAlchemy 2.0 (async), Alembic, pytest/httpx. App — Flutter/Dart, flutter_riverpod, dio, go_router, url_launcher, intl, mocktail.

**Spec:** `docs/superpowers/specs/2026-06-09-meetings-end-to-end-design.md`

**Pre-existing work this plan builds on (verified):**
- `RsvpStatus` enum: `app/models/models.py:37` and `app/schemas/schemas.py:35` (two definitions — both must change).
- `MeetingParticipant` model `app/models/models.py:217` (fields `id, meeting_id, user_id, rsvp_status, attended, name, email`).
- List/detail routes already member-scoped: `app/api/routes/meetings.py:367` (`GET /meetings/`), `:408` (`GET /meetings/{id}`).
- Facilitator-only RSVP route to mirror: `meetings.py:1923` (`require_facilitator`).
- `MEMBER_TOOLS` already lists `rsvp_meeting` (`app/tools/tool_registry.py:116`); the `"member"` agent gate is at `tool_registry.py:533`.
- The agent loop auto-injects `user_id`/`user_role` into any tool whose signature declares them (`app/agents/agent_loop.py:237-245`); the registry injects `twg_id`/`user_timezone` (`tool_registry.py:687-692`).
- **`tests/test_member_tools.py` already contains 3 red `rsvp_meeting` tests (uncommitted)** that pin the contract: `app.tools.member_tools.rsvp_meeting(meeting_id, response, user_id, user_role)` returning `{"success": True, "rsvp_status": "ACCEPTED"}` or `{"error": ...}`, opening a module-level `AsyncSessionLocal` (monkeypatchable). **`member_tools.py` does not exist yet.**
- Flutter conventions: `core/network/api_client.dart::buildAuthInterceptedDio`, providers in `features/auth/application/auth_controller.dart` (`dioProvider`, `authControllerProvider`), repository `features/auth/data/auth_repository.dart`, models `auth_models.dart` (manual `fromJson`), package name `member_app`, tests use `mocktail`.

**Auth model for RSVP (decided during planning):** authorization is **"you are a participant"** — the shared helper finds the caller's own `MeetingParticipant` by `(meeting_id, user_id)`; if absent → not authorized (404 / error). This keeps the REST route and the Martin tool identical and matches the existing tool tests (which set up only a participant row, no TWG membership). This refines the spec's "has_twg_access → 403" to "not a participant → 404."

---

## Part A — Backend

### Task B1: Add `TENTATIVE` to `RsvpStatus` + migration

**Files:**
- Modify: `backend/app/models/models.py:37-40`
- Modify: `backend/app/schemas/schemas.py:35-38`
- Create: `backend/alembic/versions/r9_rsvp_tentative_20260609.py`
- Test: `backend/tests/test_rsvp_tentative.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_rsvp_tentative.py
"""TENTATIVE ('Maybe') is a first-class RSVP state in both the model + schema enums."""
from app.models.models import RsvpStatus as ModelRsvp
from app.schemas.schemas import RsvpStatus as SchemaRsvp
from app.schemas.schemas import MeetingParticipantUpdate


def test_model_enum_has_tentative():
    assert ModelRsvp.TENTATIVE.value == "TENTATIVE"


def test_schema_enum_has_tentative():
    assert SchemaRsvp.TENTATIVE.value == "TENTATIVE"


def test_participant_update_accepts_tentative():
    upd = MeetingParticipantUpdate(rsvp_status="TENTATIVE")
    assert upd.rsvp_status == SchemaRsvp.TENTATIVE
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd backend && python -m pytest tests/test_rsvp_tentative.py -v`
Expected: FAIL (`AttributeError: TENTATIVE` / validation error).

- [ ] **Step 3: Add the enum value in both files**

In `backend/app/models/models.py` (the `RsvpStatus` at line 37):
```python
class RsvpStatus(str, enum.Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    DECLINED = "DECLINED"
    TENTATIVE = "TENTATIVE"
```
In `backend/app/schemas/schemas.py` (the `RsvpStatus` at line 35) — add the identical `TENTATIVE = "TENTATIVE"` line.

- [ ] **Step 4: Create the Alembic migration**

Find the current head: `cd backend && alembic heads`. Set `down_revision` to that id.

```python
# backend/alembic/versions/r9_rsvp_tentative_20260609.py
"""add TENTATIVE to rsvpstatus enum

Revision ID: r9_rsvp_tentative_20260609
Revises: <CURRENT_HEAD_ID>
Create Date: 2026-06-09
"""
from alembic import op

revision = "r9_rsvp_tentative_20260609"
down_revision = "<CURRENT_HEAD_ID>"  # replace with `alembic heads`
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ALTER TYPE ... ADD VALUE cannot run inside a transaction block.
    # Commit the migration's implicit transaction first, then add the value.
    op.execute("COMMIT")
    op.execute("ALTER TYPE rsvpstatus ADD VALUE IF NOT EXISTS 'TENTATIVE'")


def downgrade() -> None:
    # Postgres cannot DROP a value from an enum; downgrade is a no-op.
    pass
```
Note: confirm the enum type name with `\dT` in psql if unsure — SQLAlchemy names it from the Python class (`rsvpstatus`).

- [ ] **Step 5: Run the test to verify it passes**

Run: `cd backend && python -m pytest tests/test_rsvp_tentative.py -v`
Expected: PASS (3 passed). *(The migration is validated separately when run against the DB; these tests cover the enum/schema.)*

- [ ] **Step 6: Commit**

```bash
git add backend/app/models/models.py backend/app/schemas/schemas.py backend/alembic/versions/r9_rsvp_tentative_20260609.py backend/tests/test_rsvp_tentative.py
git commit -m "feat(meetings): add TENTATIVE rsvp state + migration"
```

---

### Task B2: Shared RSVP helper

**Files:**
- Create: `backend/app/services/rsvp_service.py`
- Test: `backend/tests/test_rsvp_service.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_rsvp_service.py
"""apply_member_rsvp updates the caller's own participant row; None when absent."""
import uuid
from datetime import datetime
import pytest
from app.models.models import Meeting, MeetingParticipant, RsvpStatus, TWG, TWGPillar, User, UserRole
from app.services.rsvp_service import apply_member_rsvp


@pytest.mark.asyncio
async def test_apply_updates_own_participant(db_session):
    twg = TWG(id=uuid.uuid4(), name="Energy", pillar=TWGPillar.energy_infrastructure)
    meeting = Meeting(id=uuid.uuid4(), title="Sync", twg_id=twg.id, scheduled_at=datetime(2026, 6, 10, 10, 0))
    uid = uuid.uuid4()
    user = User(id=uid, full_name="M", email=f"m-{uid}@x.org", hashed_password="x", role=UserRole.TWG_MEMBER)
    part = MeetingParticipant(id=uuid.uuid4(), meeting_id=meeting.id, user_id=uid, rsvp_status=RsvpStatus.PENDING)
    db_session.add_all([twg, meeting, user, part])
    await db_session.flush()

    result = await apply_member_rsvp(db_session, meeting.id, uid, RsvpStatus.TENTATIVE)
    assert result is not None
    assert result.rsvp_status == RsvpStatus.TENTATIVE


@pytest.mark.asyncio
async def test_apply_returns_none_when_not_participant(db_session):
    result = await apply_member_rsvp(db_session, uuid.uuid4(), uuid.uuid4(), RsvpStatus.ACCEPTED)
    assert result is None
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd backend && python -m pytest tests/test_rsvp_service.py -v`
Expected: FAIL (`ModuleNotFoundError: app.services.rsvp_service`).

- [ ] **Step 3: Implement the helper**

```python
# backend/app/services/rsvp_service.py
"""Shared member-RSVP write logic, used by both the REST route and the Martin tool
so the two paths update MeetingParticipant.rsvp_status identically."""
import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import MeetingParticipant, RsvpStatus


async def apply_member_rsvp(
    session: AsyncSession,
    meeting_id: uuid.UUID,
    user_id: uuid.UUID,
    status: RsvpStatus,
) -> Optional[MeetingParticipant]:
    """Set the caller's own RSVP on a meeting.

    Finds the MeetingParticipant row for (meeting_id, user_id) — being a
    participant IS the authorization. Returns the updated row, or None if the
    user is not a participant of that meeting. Commits on success.
    """
    result = await session.execute(
        select(MeetingParticipant).where(
            MeetingParticipant.meeting_id == meeting_id,
            MeetingParticipant.user_id == user_id,
        )
    )
    participant = result.scalar_one_or_none()
    if participant is None:
        return None
    participant.rsvp_status = status
    await session.commit()
    await session.refresh(participant)
    return participant
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd backend && python -m pytest tests/test_rsvp_service.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/rsvp_service.py backend/tests/test_rsvp_service.py
git commit -m "feat(meetings): shared member-rsvp helper"
```

---

### Task B3: Implement the `rsvp_meeting` Martin tool (green the existing tests)

**Files:**
- Create: `backend/app/tools/member_tools.py`
- Test: `backend/tests/test_member_tools.py` (ALREADY WRITTEN, currently red — do not rewrite)

- [ ] **Step 1: Run the existing tests to confirm they fail**

Run: `cd backend && python -m pytest tests/test_member_tools.py -v`
Expected: the 3 `rsvp_meeting` tests ERROR/FAIL (`ModuleNotFoundError: app.tools.member_tools`); `test_reminder_model_persists` passes.

- [ ] **Step 2: Implement `member_tools.py`**

Contract pinned by the tests: `rsvp_meeting(meeting_id, response, user_id, user_role)` → dict; opens module-level `AsyncSessionLocal`; `response="ACCEPTED"` succeeds; unknown response → `{"error"}`; non-participant → `{"error"}`.

```python
# backend/app/tools/member_tools.py
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
```

- [ ] **Step 3: Run the tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_member_tools.py -v`
Expected: PASS (4 passed — reminder model + 3 rsvp_meeting tests).

- [ ] **Step 4: Commit**

```bash
git add backend/app/tools/member_tools.py backend/tests/test_member_tools.py
git commit -m "feat(meetings): implement rsvp_meeting member tool"
```

---

### Task B4: Register `rsvp_meeting` in the tool registry

**Files:**
- Modify: `backend/app/tools/tool_registry.py` (add `_register_member_tools`, call it in `register_all`)
- Test: `backend/tests/test_member_rsvp_registration.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_member_rsvp_registration.py
"""rsvp_meeting is registered and granted to the member agent, denied to a random agent."""
from app.tools.tool_registry import ToolAccessDenied
import pytest


def test_rsvp_meeting_registered(fresh_registry):
    assert "rsvp_meeting" in fresh_registry.list_tools()


def test_member_agent_granted_rsvp(fresh_registry):
    assert fresh_registry.validate_tool_access("rsvp_meeting", agent_id="member") is True


def test_other_agent_denied_rsvp(fresh_registry):
    with pytest.raises(ToolAccessDenied):
        fresh_registry.validate_tool_access("rsvp_meeting", agent_id="energy")
```
Note: `rsvp_meeting` is in `MEMBER_TOOLS` (granted to `"member"`). For non-member agents it falls through to the "unknown tool → allow by default" branch *unless* added elsewhere — so to make `test_other_agent_denied_rsvp` meaningful, **also add `"rsvp_meeting"` to `MEMBER_ONLY_TOOLS`** (define such a set if absent) and add a guard, OR assert it's simply *not* in a non-member's granted tool map via `get_tools_for_agent`. Prefer the latter if a `MEMBER_ONLY` concept doesn't exist:
```python
def test_other_agent_denied_rsvp(fresh_registry):
    _defs, tool_map = fresh_registry.get_tools_for_agent(agent_id="energy", twg_id="x")
    assert "rsvp_meeting" not in tool_map
```
Use whichever matches the registry's actual filtering (`get_tools_for_agent` calls `validate_tool_access` per tool and skips denied ones). Verify by reading `get_tools_for_agent` (`tool_registry.py:609`).

- [ ] **Step 2: Run it to verify it fails**

Run: `cd backend && python -m pytest tests/test_member_rsvp_registration.py -v`
Expected: FAIL (`rsvp_meeting` not in `list_tools()`).

- [ ] **Step 3: Add `_register_member_tools` + call it**

In `tool_registry.py`, add after `_register_calendar_tools` (around line 261):
```python
    def _register_member_tools(self) -> None:
        """Register member personal-action tools."""
        from app.tools.member_tools import RSVP_MEETING_TOOL_DEF, rsvp_meeting

        func_def = RSVP_MEETING_TOOL_DEF["function"]
        self.register(
            name=func_def["name"],
            description=func_def["description"],
            parameters=func_def["parameters"].get("properties", {}),
            handler=rsvp_meeting,
            required_params=func_def["parameters"].get("required", []),
        )
```
In `register_all` (after `self._register_calendar_tools()`, line 211):
```python
        self._register_member_tools()
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd backend && python -m pytest tests/test_member_rsvp_registration.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/tools/tool_registry.py backend/tests/test_member_rsvp_registration.py
git commit -m "feat(meetings): register rsvp_meeting in tool registry"
```

---

### Task B5: Member self-RSVP REST route

**Files:**
- Modify: `backend/app/schemas/schemas.py` (add `MyRsvpRequest`)
- Modify: `backend/app/api/routes/meetings.py` (add `PUT /{meeting_id}/my-rsvp`)
- Test: `backend/tests/test_member_rsvp_route.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_member_rsvp_route.py
"""Member can self-RSVP their own participant row; 404 when not a participant."""
import uuid
from datetime import datetime, timedelta
import pytest
from app.models.models import Meeting, MeetingParticipant, RsvpStatus, TWG, TWGPillar, MeetingStatus


async def _make_meeting_with_participant(db_session, user_id):
    twg = TWG(id=uuid.uuid4(), name="Energy", pillar=TWGPillar.energy_infrastructure)
    meeting = Meeting(
        id=uuid.uuid4(), title="Energy Sync", twg_id=twg.id,
        scheduled_at=datetime.utcnow() + timedelta(days=2),
        duration_minutes=60, status=MeetingStatus.SCHEDULED, meeting_type="virtual",
    )
    part = MeetingParticipant(id=uuid.uuid4(), meeting_id=meeting.id, user_id=user_id, rsvp_status=RsvpStatus.PENDING)
    db_session.add_all([twg, meeting, part])
    await db_session.commit()
    return meeting


@pytest.mark.asyncio
@pytest.mark.parametrize("value", ["ACCEPTED", "DECLINED", "TENTATIVE"])
async def test_member_can_self_rsvp(client, db_session, test_user, normal_user_token_headers, value):
    meeting = await _make_meeting_with_participant(db_session, test_user.id)
    resp = await client.put(
        f"/api/v1/meetings/{meeting.id}/my-rsvp",
        headers=normal_user_token_headers,
        json={"rsvp_status": value},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["rsvp_status"] == value


@pytest.mark.asyncio
async def test_non_participant_gets_404(client, db_session, test_user, normal_user_token_headers):
    # A meeting the member is NOT a participant of.
    twg = TWG(id=uuid.uuid4(), name="Other", pillar=TWGPillar.digital_economy_transformation)
    meeting = Meeting(id=uuid.uuid4(), title="Other", twg_id=twg.id, scheduled_at=datetime.utcnow())
    db_session.add_all([twg, meeting])
    await db_session.commit()
    resp = await client.put(
        f"/api/v1/meetings/{meeting.id}/my-rsvp",
        headers=normal_user_token_headers,
        json={"rsvp_status": "ACCEPTED"},
    )
    assert resp.status_code == 404
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd backend && python -m pytest tests/test_member_rsvp_route.py -v`
Expected: FAIL (404/405 — route doesn't exist).

- [ ] **Step 3: Add the request schema**

In `backend/app/schemas/schemas.py`, near `MeetingParticipantUpdate` (line 326):
```python
class MyRsvpRequest(SchemaBase):
    rsvp_status: RsvpStatus
```

- [ ] **Step 4: Add the route**

In `backend/app/api/routes/meetings.py` — import the helper + schema at the top (extend the existing `from app.schemas.schemas import (...)` block to include `MyRsvpRequest`, and add `from app.services.rsvp_service import apply_member_rsvp`). Add this route (place it near the facilitator RSVP route, ~line 1958):
```python
@router.put("/{meeting_id}/my-rsvp", response_model=MeetingParticipantRead)
async def set_my_rsvp(
    meeting_id: uuid.UUID,
    rsvp_in: MyRsvpRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """A member sets their OWN RSVP on a meeting they participate in."""
    participant = await apply_member_rsvp(db, meeting_id, current_user.id, rsvp_in.rsvp_status)
    if participant is None:
        raise HTTPException(status_code=404, detail="You are not a participant of this meeting.")
    return participant
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `cd backend && python -m pytest tests/test_member_rsvp_route.py -v`
Expected: PASS (4 passed: 3 parametrized + non-participant).

- [ ] **Step 6: Run the full backend RSVP suite + commit**

Run: `cd backend && python -m pytest tests/test_rsvp_tentative.py tests/test_rsvp_service.py tests/test_member_tools.py tests/test_member_rsvp_registration.py tests/test_member_rsvp_route.py -v`
Expected: all pass.
```bash
git add backend/app/schemas/schemas.py backend/app/api/routes/meetings.py backend/tests/test_member_rsvp_route.py
git commit -m "feat(meetings): member self-rsvp REST route"
```

---

## Part B — Flutter app

All app commands run from `mobile/`. Run tests with `flutter test <path>` and analyze with `flutter analyze <path>`. Imports use `package:member_app/...`.

### Task F1: Add dependencies

**Files:** Modify `mobile/pubspec.yaml`

- [ ] **Step 1: Add packages** under `dependencies:` (after `local_auth: ^3.0.1`):
```yaml
  url_launcher: ^6.3.0
  intl: ^0.20.2
```
- [ ] **Step 2: Fetch** — Run: `cd mobile && flutter pub get` → Expected: `Got dependencies!`
- [ ] **Step 3: Commit**
```bash
git add mobile/pubspec.yaml mobile/pubspec.lock
git commit -m "chore(mobile): add url_launcher + intl for meetings"
```

---

### Task F2: Meetings models

**Files:**
- Create: `mobile/lib/features/meetings/data/meetings_models.dart`
- Test: `mobile/test/features/meetings/meetings_models_test.dart`

- [ ] **Step 1: Write the failing test**

```dart
// test/features/meetings/meetings_models_test.dart
import 'package:flutter_test/flutter_test.dart';
import 'package:member_app/features/meetings/data/meetings_models.dart';

void main() {
  group('MeetingRsvp', () {
    test('parses api names + maps to api', () {
      expect(MeetingRsvpX.fromApi('ACCEPTED'), MeetingRsvp.going);
      expect(MeetingRsvpX.fromApi('TENTATIVE'), MeetingRsvp.maybe);
      expect(MeetingRsvpX.fromApi('DECLINED'), MeetingRsvp.no);
      expect(MeetingRsvpX.fromApi('PENDING'), MeetingRsvp.pending);
      expect(MeetingRsvp.going.toApi, 'ACCEPTED');
      expect(MeetingRsvp.maybe.toApi, 'TENTATIVE');
      expect(MeetingRsvp.no.toApi, 'DECLINED');
    });
  });

  test('Meeting.fromJson parses fields + derives myRsvp by user id', () {
    final json = {
      'id': 'm1',
      'title': 'Energy Sync',
      'scheduled_at': '2026-06-10T14:00:00Z',
      'duration_minutes': 60,
      'status': 'SCHEDULED',
      'meeting_type': 'virtual',
      'location': 'Virtual',
      'video_link': 'https://meet.example/abc',
      'twg': {'id': 't1', 'name': 'Energy TWG'},
      'participants': [
        {'id': 'p1', 'user_id': 'u1', 'rsvp_status': 'ACCEPTED'},
        {'id': 'p2', 'user_id': 'u2', 'rsvp_status': 'PENDING'},
      ],
    };
    final m = Meeting.fromJson(json);
    expect(m.id, 'm1');
    expect(m.title, 'Energy Sync');
    expect(m.twgName, 'Energy TWG');
    expect(m.videoLink, 'https://meet.example/abc');
    expect(m.scheduledAt.isUtc, isFalse); // converted to local
    expect(m.myRsvp('u1'), MeetingRsvp.going);
    expect(m.isParticipant('u1'), isTrue);
    expect(m.myRsvp('u2'), MeetingRsvp.pending);
    expect(m.isParticipant('zzz'), isFalse);
  });
}
```

- [ ] **Step 2: Run it to verify it fails** — Run: `cd mobile && flutter test test/features/meetings/meetings_models_test.dart` → Expected: FAIL (file not found / undefined).

- [ ] **Step 3: Implement the models**

```dart
// lib/features/meetings/data/meetings_models.dart
//
// Meetings data models — manual fromJson (mirrors features/auth/data/auth_models.dart).
// MeetingRsvp maps the member UI states (Going/Maybe/No) to the backend
// RsvpStatus enum (ACCEPTED/TENTATIVE/DECLINED, plus PENDING = no response).

enum MeetingRsvp { going, maybe, no, pending }

extension MeetingRsvpX on MeetingRsvp {
  /// Backend RsvpStatus value for this UI state.
  String get toApi => switch (this) {
        MeetingRsvp.going => 'ACCEPTED',
        MeetingRsvp.maybe => 'TENTATIVE',
        MeetingRsvp.no => 'DECLINED',
        MeetingRsvp.pending => 'PENDING',
      };

  static MeetingRsvp fromApi(String? raw) => switch (raw) {
        'ACCEPTED' => MeetingRsvp.going,
        'TENTATIVE' => MeetingRsvp.maybe,
        'DECLINED' => MeetingRsvp.no,
        _ => MeetingRsvp.pending,
      };
}

class MeetingParticipant {
  const MeetingParticipant({
    required this.id,
    required this.userId,
    required this.name,
    required this.rsvp,
  });

  final String id;
  final String? userId;
  final String? name;
  final MeetingRsvp rsvp;

  factory MeetingParticipant.fromJson(Map<String, dynamic> j) => MeetingParticipant(
        id: j['id'].toString(),
        userId: j['user_id']?.toString(),
        name: (j['name'] ?? (j['user'] as Map?)?['full_name'])?.toString(),
        rsvp: MeetingRsvpX.fromApi(j['rsvp_status'] as String?),
      );
}

class Meeting {
  const Meeting({
    required this.id,
    required this.title,
    required this.scheduledAt,
    required this.durationMinutes,
    required this.status,
    required this.meetingType,
    required this.location,
    required this.videoLink,
    required this.twgName,
    required this.participants,
  });

  final String id;
  final String title;
  final DateTime scheduledAt; // local time
  final int durationMinutes;
  final String status;
  final String meetingType;
  final String? location;
  final String? videoLink;
  final String? twgName;
  final List<MeetingParticipant> participants;

  bool get isPast => scheduledAt.isBefore(DateTime.now());
  bool get hasVideo => (videoLink ?? '').isNotEmpty;

  MeetingParticipant? _me(String userId) {
    for (final p in participants) {
      if (p.userId == userId) return p;
    }
    return null;
  }

  bool isParticipant(String userId) => _me(userId) != null;
  MeetingRsvp myRsvp(String userId) => _me(userId)?.rsvp ?? MeetingRsvp.pending;

  factory Meeting.fromJson(Map<String, dynamic> json) => Meeting(
        id: json['id'].toString(),
        title: json['title'] as String,
        scheduledAt: DateTime.parse(json['scheduled_at'] as String).toLocal(),
        durationMinutes: (json['duration_minutes'] as int?) ?? 60,
        status: (json['status'] ?? 'SCHEDULED').toString(),
        meetingType: (json['meeting_type'] ?? 'virtual').toString(),
        location: json['location']?.toString(),
        videoLink: json['video_link']?.toString(),
        twgName: (json['twg'] as Map?)?['name']?.toString(),
        participants: ((json['participants'] as List?) ?? const [])
            .map((e) => MeetingParticipant.fromJson(e as Map<String, dynamic>))
            .toList(),
      );
}
```

- [ ] **Step 4: Run the test to verify it passes** — Run: `cd mobile && flutter test test/features/meetings/meetings_models_test.dart` → Expected: PASS.
- [ ] **Step 5: Commit**
```bash
git add mobile/lib/features/meetings/data/meetings_models.dart mobile/test/features/meetings/meetings_models_test.dart
git commit -m "feat(mobile): meetings data models"
```

---

### Task F3: Meetings repository

**Files:**
- Create: `mobile/lib/features/meetings/data/meetings_repository.dart`
- Test: `mobile/test/features/meetings/meetings_repository_test.dart`

- [ ] **Step 1: Write the failing test** (mirrors `auth_repository_test.dart`, mocked Dio)

```dart
// test/features/meetings/meetings_repository_test.dart
import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:member_app/features/meetings/data/meetings_models.dart';
import 'package:member_app/features/meetings/data/meetings_repository.dart';

class _MockDio extends Mock implements Dio {}

void main() {
  late _MockDio dio;
  late MeetingsRepository repo;

  setUp(() {
    dio = _MockDio();
    repo = MeetingsRepository(dio: dio);
  });

  Response<T> _resp<T>(T data, {int code = 200}) =>
      Response<T>(data: data, statusCode: code, requestOptions: RequestOptions(path: '/'));

  test('listMeetings parses a list', () async {
    when(() => dio.get('/meetings/')).thenAnswer((_) async => _resp<List<dynamic>>([
          {'id': 'm1', 'title': 'Sync', 'scheduled_at': '2026-06-10T14:00:00Z', 'status': 'SCHEDULED',
           'meeting_type': 'virtual', 'participants': []},
        ]));
    final list = await repo.listMeetings();
    expect(list, isA<List<Meeting>>());
    expect(list.single.title, 'Sync');
  });

  test('setMyRsvp PUTs the api value', () async {
    when(() => dio.put('/meetings/m1/my-rsvp', data: any(named: 'data')))
        .thenAnswer((_) async => _resp<Map<String, dynamic>>({'id': 'p1', 'rsvp_status': 'TENTATIVE'}));
    await repo.setMyRsvp('m1', MeetingRsvp.maybe);
    verify(() => dio.put('/meetings/m1/my-rsvp', data: {'rsvp_status': 'TENTATIVE'})).called(1);
  });

  test('throws MeetingException on Dio error', () async {
    when(() => dio.get('/meetings/')).thenThrow(
      DioException(requestOptions: RequestOptions(path: '/meetings/'), response:
        Response(statusCode: 500, requestOptions: RequestOptions(path: '/meetings/'))),
    );
    expect(() => repo.listMeetings(), throwsA(isA<MeetingException>()));
  });
}
```

- [ ] **Step 2: Run it to verify it fails** — Run: `cd mobile && flutter test test/features/meetings/meetings_repository_test.dart` → Expected: FAIL.

- [ ] **Step 3: Implement the repository**

```dart
// lib/features/meetings/data/meetings_repository.dart
import 'package:dio/dio.dart';
import 'meetings_models.dart';

class MeetingException implements Exception {
  MeetingException(this.message);
  final String message;
  @override
  String toString() => message;
}

class MeetingsRepository {
  MeetingsRepository({required Dio dio}) : _dio = dio;
  final Dio _dio;

  Future<List<Meeting>> listMeetings() async {
    try {
      final res = await _dio.get('/meetings/');
      final data = (res.data as List).cast<Map<String, dynamic>>();
      return data.map(Meeting.fromJson).toList();
    } on DioException {
      throw MeetingException('Could not load meetings. Check your connection and try again.');
    }
  }

  Future<Meeting> meetingDetail(String id) async {
    try {
      final res = await _dio.get('/meetings/$id');
      return Meeting.fromJson(res.data as Map<String, dynamic>);
    } on DioException {
      throw MeetingException('Could not open this meeting.');
    }
  }

  Future<void> setMyRsvp(String meetingId, MeetingRsvp rsvp) async {
    try {
      await _dio.put('/meetings/$meetingId/my-rsvp', data: {'rsvp_status': rsvp.toApi});
    } on DioException catch (e) {
      if (e.response?.statusCode == 404) {
        throw MeetingException("You're not on this meeting's invite list.");
      }
      throw MeetingException('Could not save your RSVP. Try again.');
    }
  }
}
```

- [ ] **Step 4: Run the test to verify it passes** — Run: `cd mobile && flutter test test/features/meetings/meetings_repository_test.dart` → Expected: PASS.
- [ ] **Step 5: Commit**
```bash
git add mobile/lib/features/meetings/data/meetings_repository.dart mobile/test/features/meetings/meetings_repository_test.dart
git commit -m "feat(mobile): meetings repository"
```

---

### Task F4: Meetings controller (providers + optimistic RSVP)

**Files:**
- Create: `mobile/lib/features/meetings/application/meetings_controller.dart`
- Test: `mobile/test/features/meetings/meetings_controller_test.dart`

- [ ] **Step 1: Write the failing test**

```dart
// test/features/meetings/meetings_controller_test.dart
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:mocktail/mocktail.dart';
import 'package:member_app/features/meetings/application/meetings_controller.dart';
import 'package:member_app/features/meetings/data/meetings_models.dart';
import 'package:member_app/features/meetings/data/meetings_repository.dart';

class _MockRepo extends Mock implements MeetingsRepository {}

Meeting _m(String id, {String rsvp = 'PENDING'}) => Meeting.fromJson({
      'id': id, 'title': 'M$id', 'scheduled_at': '2026-06-10T14:00:00Z', 'status': 'SCHEDULED',
      'meeting_type': 'virtual',
      'participants': [{'id': 'p', 'user_id': 'me', 'rsvp_status': rsvp}],
    });

void main() {
  setUpAll(() => registerFallbackValue(MeetingRsvp.going));

  test('load -> data; empty -> empty', () async {
    final repo = _MockRepo();
    when(() => repo.listMeetings()).thenAnswer((_) async => [_m('1')]);
    final container = ProviderContainer(overrides: [
      meetingsRepositoryProvider.overrideWithValue(repo),
    ]);
    addTearDown(container.dispose);

    await container.read(meetingsControllerProvider.notifier).load();
    expect(container.read(meetingsControllerProvider), isA<MeetingsData>());
  });

  test('setRsvp is optimistic and rolls back on error', () async {
    final repo = _MockRepo();
    when(() => repo.listMeetings()).thenAnswer((_) async => [_m('1', rsvp: 'PENDING')]);
    when(() => repo.setMyRsvp(any(), any())).thenThrow(MeetingException('nope'));
    final container = ProviderContainer(overrides: [
      meetingsRepositoryProvider.overrideWithValue(repo),
    ]);
    addTearDown(container.dispose);
    final ctrl = container.read(meetingsControllerProvider.notifier);
    await ctrl.load();

    await ctrl.setRsvp('1', MeetingRsvp.going, 'me');
    final state = container.read(meetingsControllerProvider) as MeetingsData;
    // rolled back to PENDING after the failure
    expect(state.meetings.single.myRsvp('me'), MeetingRsvp.pending);
  });
}
```

- [ ] **Step 2: Run it to verify it fails** — Run: `cd mobile && flutter test test/features/meetings/meetings_controller_test.dart` → Expected: FAIL.

- [ ] **Step 3: Implement the controller**

```dart
// lib/features/meetings/application/meetings_controller.dart
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../auth/application/auth_controller.dart';
import '../data/meetings_models.dart';
import '../data/meetings_repository.dart';

sealed class MeetingsState {
  const MeetingsState();
}
class MeetingsLoading extends MeetingsState { const MeetingsLoading(); }
class MeetingsEmpty extends MeetingsState { const MeetingsEmpty(); }
class MeetingsError extends MeetingsState {
  const MeetingsError(this.message);
  final String message;
}
class MeetingsData extends MeetingsState {
  const MeetingsData(this.meetings);
  final List<Meeting> meetings;
}

final meetingsRepositoryProvider = Provider<MeetingsRepository>(
  (ref) => MeetingsRepository(dio: ref.watch(dioProvider)),
);

class MeetingsController extends Notifier<MeetingsState> {
  @override
  MeetingsState build() => const MeetingsLoading();

  MeetingsRepository get _repo => ref.read(meetingsRepositoryProvider);

  Future<void> load() async {
    state = const MeetingsLoading();
    try {
      final list = await _repo.listMeetings();
      state = list.isEmpty ? const MeetingsEmpty() : MeetingsData(list);
    } on MeetingException catch (e) {
      state = MeetingsError(e.message);
    }
  }

  /// Optimistically flip the RSVP, then persist; roll back on failure.
  Future<void> setRsvp(String meetingId, MeetingRsvp rsvp, String userId) async {
    final current = state;
    if (current is! MeetingsData) return;
    final previous = current.meetings;

    // Optimistic: rebuild the list with the new local rsvp for this meeting.
    state = MeetingsData(_withRsvp(previous, meetingId, rsvp, userId));
    try {
      await _repo.setMyRsvp(meetingId, rsvp);
    } on MeetingException {
      state = MeetingsData(previous); // rollback
      rethrow;
    }
  }

  List<Meeting> _withRsvp(List<Meeting> list, String meetingId, MeetingRsvp rsvp, String userId) {
    return [
      for (final m in list)
        if (m.id == meetingId)
          Meeting(
            id: m.id, title: m.title, scheduledAt: m.scheduledAt,
            durationMinutes: m.durationMinutes, status: m.status, meetingType: m.meetingType,
            location: m.location, videoLink: m.videoLink, twgName: m.twgName,
            participants: [
              for (final p in m.participants)
                if (p.userId == userId)
                  MeetingParticipant(id: p.id, userId: p.userId, name: p.name, rsvp: rsvp)
                else
                  p,
            ],
          )
        else
          m,
    ];
  }
}

final meetingsControllerProvider =
    NotifierProvider<MeetingsController, MeetingsState>(MeetingsController.new);

/// Convenience: the current member's user id (empty if not authed).
final currentUserIdProvider = Provider<String>((ref) {
  final s = ref.watch(authControllerProvider);
  return s is AuthAuthenticated ? s.user.id : '';
});
```
Note on the rollback test: `setRsvp` rethrows after rolling back, so the test should wrap the call: change the test's `await ctrl.setRsvp(...)` to `await expectLater(ctrl.setRsvp('1', MeetingRsvp.going, 'me'), throwsA(isA<MeetingException>()));` then assert the rolled-back state. Adjust the test accordingly in Step 1.

- [ ] **Step 4: Run the test to verify it passes** — Run: `cd mobile && flutter test test/features/meetings/meetings_controller_test.dart` → Expected: PASS.
- [ ] **Step 5: Commit**
```bash
git add mobile/lib/features/meetings/application/meetings_controller.dart mobile/test/features/meetings/meetings_controller_test.dart
git commit -m "feat(mobile): meetings controller with optimistic rsvp"
```

---

### Task F5: Wire the Meetings list screen to live data

**Files:**
- Modify: `mobile/lib/features/meetings/presentation/meetings_screen.dart`
- Test: `mobile/test/features/meetings/meetings_screen_test.dart`

The current file is a `StatelessWidget` with seed data + reusable private widgets `_MeetingCard`, `_JoinPill`, `_RsvpChip`, `_SectionLabel`. Reuse those visuals; replace seed/data plumbing.

- [ ] **Step 1: Rewrite the screen** to a `ConsumerStatefulWidget`:
  - In `initState`, `ref.read(meetingsControllerProvider.notifier).load()` (post-frame).
  - `build` watches `meetingsControllerProvider` and renders by state:
    - `MeetingsLoading` → centered `CircularProgressIndicator(color: SovereignColors.gold)`.
    - `MeetingsError` → glass message + a "Retry" `TextButton` calling `load()`.
    - `MeetingsEmpty` → designed empty state ("No meetings scheduled yet").
    - `MeetingsData` → header (keep "Meetings" serif title; replace the hard-coded "ENERGY TWG"/"Amina" with the member's TWG name from `authControllerProvider` / a neutral subtitle), then an **Upcoming | Past** segmented toggle (a `StatefulWidget`-local `bool _showPast`), then the filtered+sorted cards.
  - Filter: `final shown = data.meetings.where((m) => _showPast ? m.isPast : !m.isPast).toList()..sort((a,b)=> _showPast ? b.scheduledAt.compareTo(a.scheduledAt) : a.scheduledAt.compareTo(b.scheduledAt));`
  - Each card: reuse a `_MeetingCard`-style widget taking a real `Meeting`. Format time with `intl`: `DateFormat('EEE d MMM · HH:mm').format(m.scheduledAt)`; relative hint via a small helper (`_relative(m.scheduledAt)` → "in 2h"/"Tomorrow"/"" — optional).
  - **Join pill**: show only if `m.hasVideo`; `onTap` → `launchUrl(Uri.parse(m.videoLink!), mode: LaunchMode.externalApplication)` (import `package:url_launcher/url_launcher.dart`).
  - **RSVP chips**: show only if `m.isParticipant(userId)` (where `userId = ref.watch(currentUserIdProvider)`); selected = `m.myRsvp(userId)`; `onTap` → `ref.read(meetingsControllerProvider.notifier).setRsvp(m.id, rsvp, userId)` wrapped in try/catch to show a `SnackBar` on `MeetingException`.
  - **Tap card body** → `context.push('/meetings/${m.id}')` (added in Task F6).
  - Keep `bottom: false` SafeArea + `EdgeInsets.fromLTRB(20,16,20,104)` so the floating nav clears content.

  Reuse `GlassCard`, `GlassSurface.inner`, `_SectionLabel`, the gold `_JoinPill` look, and the `_RsvpChip` selected/unselected styling already in the file. Convert `_RsvpChip` to accept an `onTap` and `_MeetingCard` to take a `Meeting` + callbacks.

- [ ] **Step 2: Write a widget test**

```dart
// test/features/meetings/meetings_screen_test.dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:mocktail/mocktail.dart';
import 'package:member_app/features/meetings/application/meetings_controller.dart';
import 'package:member_app/features/meetings/data/meetings_models.dart';
import 'package:member_app/features/meetings/data/meetings_repository.dart';
import 'package:member_app/features/meetings/presentation/meetings_screen.dart';

class _MockRepo extends Mock implements MeetingsRepository {}

void main() {
  testWidgets('shows a meeting title from live data', (tester) async {
    final repo = _MockRepo();
    when(() => repo.listMeetings()).thenAnswer((_) async => [
          Meeting.fromJson({
            'id': 'm1', 'title': 'Energy Sync',
            'scheduled_at': '2031-06-10T14:00:00Z', 'status': 'SCHEDULED', 'meeting_type': 'virtual',
            'participants': const [],
          }),
        ]);
    await tester.pumpWidget(ProviderScope(
      overrides: [meetingsRepositoryProvider.overrideWithValue(repo)],
      child: const MaterialApp(home: MeetingsScreen()),
    ));
    await tester.pump(); // post-frame load()
    await tester.pump(const Duration(milliseconds: 50));
    expect(find.text('Energy Sync'), findsOneWidget);
  });
}
```

- [ ] **Step 3: Run + verify** — `cd mobile && flutter test test/features/meetings/meetings_screen_test.dart` → PASS; then `flutter analyze lib/features/meetings` → no errors.
- [ ] **Step 4: Commit**
```bash
git add mobile/lib/features/meetings/presentation/meetings_screen.dart mobile/test/features/meetings/meetings_screen_test.dart
git commit -m "feat(mobile): wire meetings list to live data + rsvp/join"
```

---

### Task F6: Meeting detail screen + route

**Files:**
- Create: `mobile/lib/features/meetings/presentation/meeting_detail_screen.dart`
- Modify: `mobile/lib/routing/app_router.dart` (add `/meetings/:id`)
- Test: `mobile/test/features/meetings/meeting_detail_screen_test.dart`

- [ ] **Step 1: Add the route** in `app_router.dart` `routes:` list:
```dart
import '../features/meetings/presentation/meeting_detail_screen.dart';
// ...
      GoRoute(
        path: '/meetings/:id',
        builder: (_, st) => MeetingDetailScreen(meetingId: st.pathParameters['id']!),
      ),
```
Note: confirm the redirect (`redirectFor`) still allows `/meetings/:id` when authenticated — it does (only `/login` is special-cased).

- [ ] **Step 2: Implement the detail screen** — a `ConsumerStatefulWidget` that:
  - Holds a `Future<Meeting>` from `ref.read(meetingsRepositoryProvider).meetingDetail(widget.meetingId)` (kick off in `initState`), rendered with a `FutureBuilder<Meeting>`:
    - waiting → spinner; error (`MeetingException`) → message + Retry; data → the detail body.
  - Body (glass): a back affordance (`AppBar` is fine, or a glass back button), serif title, time (`intl` `DateFormat('EEEE, d MMMM · HH:mm').format(m.scheduledAt)` + duration), location, **Join** pill (if `m.hasVideo`, `launchUrl`), an **Agenda** section if present (fetch `GET /meetings/{id}/agenda` is optional this pass — if you include it, add `meetingAgenda(id)` to the repo returning `content`; otherwise omit), an **Attendees** list (`m.participants` → name + their `MeetingRsvp` as a small chip), and the member's **RSVP** control (only if `m.isParticipant(userId)`), reusing the same `setRsvp` flow (call the controller so the list stays in sync; after success, also refresh local detail state).
  - Use `currentUserIdProvider` for `userId`.

- [ ] **Step 3: Write a widget test** (mock repo returns one meeting; expect the title shows):
```dart
// test/features/meetings/meeting_detail_screen_test.dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:mocktail/mocktail.dart';
import 'package:member_app/features/meetings/application/meetings_controller.dart';
import 'package:member_app/features/meetings/data/meetings_models.dart';
import 'package:member_app/features/meetings/data/meetings_repository.dart';
import 'package:member_app/features/meetings/presentation/meeting_detail_screen.dart';

class _MockRepo extends Mock implements MeetingsRepository {}

void main() {
  testWidgets('renders meeting detail title', (tester) async {
    final repo = _MockRepo();
    when(() => repo.meetingDetail('m1')).thenAnswer((_) async => Meeting.fromJson({
          'id': 'm1', 'title': 'Steering Committee',
          'scheduled_at': '2031-06-10T10:00:00Z', 'status': 'SCHEDULED', 'meeting_type': 'virtual',
          'participants': const [],
        }));
    await tester.pumpWidget(ProviderScope(
      overrides: [meetingsRepositoryProvider.overrideWithValue(repo)],
      child: const MaterialApp(home: MeetingDetailScreen(meetingId: 'm1')),
    ));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 50));
    expect(find.text('Steering Committee'), findsOneWidget);
  });
}
```

- [ ] **Step 4: Run + verify** — `cd mobile && flutter test test/features/meetings/ && flutter analyze lib` → all pass, no errors. Also run `flutter test test/routing/app_router_test.dart` to confirm the router still passes.
- [ ] **Step 5: Commit**
```bash
git add mobile/lib/features/meetings/presentation/meeting_detail_screen.dart mobile/lib/routing/app_router.dart mobile/test/features/meetings/meeting_detail_screen_test.dart
git commit -m "feat(mobile): meeting detail screen + route"
```

---

## Final verification

- [ ] Backend: `cd backend && python -m pytest tests/test_rsvp_tentative.py tests/test_rsvp_service.py tests/test_member_tools.py tests/test_member_rsvp_registration.py tests/test_member_rsvp_route.py -v` → all green.
- [ ] App: `cd mobile && flutter analyze` → no errors (pre-existing info-lints OK); `flutter test` → all green.
- [ ] Manual on device: open Meetings → see live meetings → toggle Upcoming/Past → open one → Join opens Meet → RSVP Going/Maybe/No persists (re-open confirms) → "ask Martin to RSVP" updates the same record.

## Notes / known follow-ups (out of scope, per spec §9)
- Martin RSVP **end-to-end** requires the member chat session to run under the `"member"` agent id (so `rsvp_meeting` lands in the agent tool-map and `user_id` is injected) and to register the thread→user mapping via `_rbac`. The tool + registration + unit tests are delivered here; confirm/wire the member chat agent id when building the Home/Martin chat slice.
- Deferred: offline caching, RSVP→Google-Calendar write-back, 401 silent-refresh, `set_reminder`/`get_notifications` tools, agenda/minutes inside detail (optional in F6).
