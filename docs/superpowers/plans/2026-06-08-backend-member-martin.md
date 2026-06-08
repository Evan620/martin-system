# Plan #2 — Backend member-Martin

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to execute this plan. Work one task at a time, in order. Each task is a TDD cycle: write the failing test, run it (confirm it fails), implement, run it (confirm it passes), commit. Do NOT skip the "run it / confirm FAIL" step — a test that passes before implementation proves nothing. Steps use checkbox (- [ ]) syntax.

**Goal:** Expose a member-safe "Martin" through the existing zero-trust tool registry so that a `TWG_MEMBER` chatting via the mobile app receives ONLY the member toolset and is provably blocked from facilitator/admin tools.

**Architecture:** Introduce a new `agent_id="member"` scope inside the existing `ToolRegistry.validate_tool_access` (the single enforcement point), backed by a `MEMBER_TOOLS` allowlist. A new member chat endpoint binds the authenticated `TWG_MEMBER`'s `user_id`/`role`/`twg_id`, builds the existing `AgentLoop` with `registry.get_tools_for_agent("member", twg_id)`, and runs it — adding a new front door but no new security surface. Two missing member-personal-action tools (self-RSVP, set-reminder) are created with their own role-gated bodies and registered.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy async (`AsyncSessionLocal`), pytest / pytest-asyncio (run via `backend/.venv`), existing `ToolRegistry`, `AgentLoop`, `_rbac` (`require_role`, `set_user_context`, `set_user_for_thread`), `get_llm_service()`.

**Spec:** `docs/superpowers/specs/2026-06-08-member-mobile-app-design.md` — §5 (Member-Martin engine), §6 (member toolset contract), §3 (the safety line), §13 (testing approach).

---

## Member toolset contract (from spec §6, mapped to EXISTING tool names)

ALLOWED for `agent_id="member"` (`MEMBER_TOOLS`):
- `get_schedule`, `get_past_meetings` — my meetings / agenda / time / join link
- `search_documents`, `retrieve_document_content` — find + summarize docs for my TWG
- `get_meeting_minutes` — read meeting summaries / decisions
- `get_action_items`, `update_action_item_status` — my action items + mark my own done
- `search_knowledge_base`, `get_relevant_context`, `get_knowledge_base_stats` — knowledge base (already UNRESTRICTED)
- `rsvp_meeting` — RSVP myself (NEW tool, Task 4)
- `set_reminder` — set my own reminders/nudges (NEW tool, Task 5)
- `get_notifications` — read my notifications (NEW tool, Task 6)

BLOCKED for members (must NOT appear in a member session, must raise `ToolAccessDenied`):
- `create_meeting`, `create_recurring_meeting`, `create_meeting_invite`, `update_meeting` — create/schedule meetings for others
- `send_email`, `create_email_draft`, `request_document_approval_tool` — invite/email/broadcast
- `get_twg_members` — directory (facilitator capability; not in spec §6 allow-list)
- all `SUPERVISOR_ONLY_TOOLS`, all `DEAL_PIPELINE_TOOLS` (Phase 2 read-only deferred), all `PIPELINE_WRITE_TOOLS`, all `PIPELINE_READ_TOOLS`, all WhatsApp tools (`WHATSAPP_TOOL_NAMES`) — WhatsApp blocked as a plan-level interpretation of spec §6 *Never exposed* (broadcasts / invite people) + §29 (no outward communication); see Task 1's "Why WhatsApp tools are blocked" note

Note (KB tools are RAG-only today, NOT LLM-callable): `search_knowledge_base`,
`get_relevant_context`, and `get_knowledge_base_stats` are in `UNRESTRICTED_TOOLS`
but are NOT registered as callable tools by `register_all()`. Confirmed in
`tool_registry.py`: `register_all()` calls `_register_calendar_tools`,
`_register_email_tools`, `_register_document_tools`, `_register_database_tools`,
`_register_deal_pipeline_tools`, `_register_supervisor_tools`,
`_register_whatsapp_tools` — there is NO `_register_knowledge_tools`, and the
trailing comment in `register_all()` states "knowledge_tools are used for RAG in
`_process_query_node`, not as LLM-callable tools." So these three names will NOT
appear in `registry.list_tools()`. Because `get_tools_for_agent` only iterates
`self._tools` (the registered tools) and `validate_tool_access` is only ever
reached for registered names during retrieval, the member's GRANTED set is
`MEMBER_TOOLS ∩ registered`. The three KB names are listed in `MEMBER_TOOLS`
purely for forward-compat (if they are ever registered as callable tools, members
get them automatically); until then they are simply excluded from both sides of
every equality assertion. Tasks assert against the intersection, never against
tools that aren't registered.

---

## File Structure

| File | Action |
|---|---|
| `backend/app/tools/whatsapp_tools.py` | Modify — export `WHATSAPP_TOOL_NAMES` (derived from `WHATSAPP_TOOLS`) so the member-scope test imports the real WhatsApp tool names instead of hardcoding them |
| `backend/app/tools/tool_registry.py` | Modify — add `MEMBER_TOOLS` set immediately after the `UNRESTRICTED_TOOLS` set definition (the block ending `"get_knowledge_base_stats",\n}`) + a `member` branch in `validate_tool_access` (inserted as the FIRST check, immediately before the `if tool_name in PIPELINE_WRITE_TOOLS or tool_name in PIPELINE_READ_TOOLS:` block); register new member tools at the end of `_register_database_tools` |
| `backend/app/tools/member_tools.py` | Create — `rsvp_meeting`, `set_reminder`, `get_notifications` handlers + their OpenAI tool defs |
| `backend/app/models/models.py` | Modify — add `Reminder` model (for `set_reminder`) |
| `backend/app/agents/member_agent.py` | Create — `run_member_chat(...)` builds + runs an `AgentLoop` as `agent_id="member"` |
| `backend/app/api/routes/agents.py` | Modify — add `POST /api/v1/agents/member/chat` endpoint |
| `backend/tests/test_member_tool_scope.py` | Create — registry allowlist + denial proofs (Tasks 1, 4-6) |
| `backend/tests/test_member_tools.py` | Create — unit tests for the 3 new tools + role gating (Tasks 4-6) |
| `backend/tests/test_member_chat_endpoint.py` | Create — runner + endpoint scoping proof, plus the identity-injection security proof (Tasks 7-8) |

---

## Task 1 — Add `member` scope to the tool registry (allowlist + deny-everything-else)

**Files:**
- Modify: `backend/app/tools/whatsapp_tools.py` (export `WHATSAPP_TOOL_NAMES`, derived from `WHATSAPP_TOOLS`, so the test imports the real names instead of hardcoding them)
- Create: `backend/tests/test_member_tool_scope.py`
- Modify: `backend/app/tools/tool_registry.py` (add `MEMBER_TOOLS` immediately after the `UNRESTRICTED_TOOLS` set definition; add the `member` branch in `validate_tool_access` immediately after the pipeline `PIPELINE_WRITE_TOOLS`/`PIPELINE_READ_TOOLS` block and before the `if agent_id == "supervisor":` check — anchored on those exact code strings, never on line numbers)

> **Why WhatsApp tools are blocked for members (spec interpretation, recorded so plan and spec agree).** Spec §6 lists "Create/schedule meetings for others; invite or email people; broadcasts" in the *Never exposed* column but does NOT name WhatsApp explicitly. This plan treats the four WhatsApp tools (`send_whatsapp_message`, `send_whatsapp_to_group`, `list_whatsapp_groups`, `check_whatsapp_number`) as BLOCKED for members because they are an outward/broadcast communication channel: `send_whatsapp_to_group` is a literal broadcast and `send_whatsapp_message` is "invite or email people" by another transport — both squarely inside spec §6 *Never exposed*, and reinforced by the "no outward communication / no broadcasts" principle in spec §29. The two read-only WhatsApp tools (`list_whatsapp_groups`, `check_whatsapp_number`) are also blocked: they expose the org's WhatsApp directory, which is not in the spec §6 member allow-list. This is a deliberate plan-level interpretation, not a spec-mandated line item, and the blocking falls out automatically from the allowlist design (WhatsApp tools are simply absent from `MEMBER_TOOLS`).

### Steps

- [ ] FIRST, export the WhatsApp tool-name set from its source module so the test
imports the REAL names (never a hand-maintained copy that could drift). In
`backend/app/tools/whatsapp_tools.py`, add a derived constant immediately AFTER
the `WHATSAPP_TOOLS` list. Anchor on this exact text (the END of the file) and
append the new constant right after the list's closing `]`:

```python
WHATSAPP_TOOLS = [
    (SEND_WHATSAPP_MESSAGE_TOOL, send_whatsapp_message),
    (SEND_WHATSAPP_TO_GROUP_TOOL, send_whatsapp_to_group),
    (LIST_WHATSAPP_GROUPS_TOOL, list_whatsapp_groups),
    (CHECK_WHATSAPP_NUMBER_TOOL, check_whatsapp_number),
]
```

Append:

```python
# The exact tool names registered by ToolRegistry._register_whatsapp_tools (it
# iterates WHATSAPP_TOOLS). Derived from the single source of truth above so it
# can NEVER drift from the actually-registered names — tests import THIS instead
# of hardcoding the four strings.
WHATSAPP_TOOL_NAMES: set[str] = {
    tool_def["function"]["name"] for tool_def, _handler in WHATSAPP_TOOLS
}
```

(CONFIRMED: each entry in `WHATSAPP_TOOLS` is a `(tool_def, handler)` tuple whose
`tool_def["function"]["name"]` is the registered name — `_register_whatsapp_tools`
in `tool_registry.py` reads exactly `func_def["name"]` from the same structure.
The four names today are `send_whatsapp_message`, `send_whatsapp_to_group`,
`list_whatsapp_groups`, `check_whatsapp_number`.)

- [ ] Write the failing test `backend/tests/test_member_tool_scope.py`:

```python
"""
Proof that the `member` agent scope grants ONLY the member toolset and is
denied every facilitator/admin tool (spec 2026-06-08-member-mobile-app-design §3, §6).
"""
import pytest
from app.tools.tool_registry import (
    ToolRegistry,
    ToolAccessDenied,
    MEMBER_TOOLS,
    SUPERVISOR_ONLY_TOOLS,
    DEAL_PIPELINE_TOOLS,
    PIPELINE_WRITE_TOOLS,
    PIPELINE_READ_TOOLS,
)
# Import the WhatsApp tool names from their SOURCE module (derived from
# WHATSAPP_TOOLS) so this test can never drift from the actually-registered
# names. See Task 1's whatsapp_tools.py export step.
from app.tools.whatsapp_tools import WHATSAPP_TOOL_NAMES

MEMBER_TWG = "11111111-1111-1111-1111-111111111111"

# Tools a member must NEVER get, regardless of twg scope (spec §6 "Never exposed").
# These are the facilitator/admin write + directory tools that ARE registered as
# callable today, so they are the realistic leak vectors.
BLOCKED_FOR_MEMBER = {
    "create_meeting", "create_recurring_meeting", "create_meeting_invite",
    "update_meeting", "send_email", "create_email_draft",
    "request_document_approval_tool", "get_twg_members",
}

# WhatsApp tools — explicitly BLOCKED for members (spec §6 "Never exposed"
# interpretation + §29 no-broadcast principle; see the "Why WhatsApp tools are
# blocked" note above). They ARE registered today (_register_whatsapp_tools in
# tool_registry.py), so they are real leak vectors and CAN be asserted denied.
# WHATSAPP_TOOL_NAMES is imported above from app.tools.whatsapp_tools (derived
# from WHATSAPP_TOOLS) — do NOT redefine it here; that would reintroduce drift.

# The FULL set of names a member must never be granted — the explicit blocklist
# UNION every restricted policy group (including WhatsApp). Iterated by the
# leakage + denial tests so that ANY future tool added to these groups is
# automatically asserted absent from a member session.
FULL_BLOCKED_UNION = (
    BLOCKED_FOR_MEMBER
    | WHATSAPP_TOOL_NAMES
    | SUPERVISOR_ONLY_TOOLS
    | DEAL_PIPELINE_TOOLS
    | PIPELINE_WRITE_TOOLS
    | PIPELINE_READ_TOOLS
)


@pytest.fixture
def registry():
    reg = ToolRegistry()
    reg.register_all()
    return reg


def test_member_granted_only_allowlisted_registered_tools(registry):
    """A member session is granted exactly MEMBER_TOOLS ∩ registered tools — nothing else."""
    _defs, tool_map = registry.get_tools_for_agent("member", twg_id=MEMBER_TWG)
    granted = set(tool_map.keys())
    expected = MEMBER_TOOLS & set(registry.list_tools())
    assert granted == expected, (
        f"member granted unexpected extra tools: {granted - expected}; "
        f"member missing expected tools: {expected - granted}"
    )
    assert granted, "member must be granted at least the registered allowlist"


def test_member_denied_facilitator_and_admin_tools(registry):
    """Every registered blocked tool raises ToolAccessDenied for a member, even with a twg_id."""
    # We can only assert DENIAL for tools that are actually REGISTERED — a tool
    # not in `registry.list_tools()` is never offered to any agent, so it can't
    # leak to a member. The `& registered` intersection scopes the assertion to
    # registered blocked tools (the ones that could realistically appear).
    registered = set(registry.list_tools())
    checked = FULL_BLOCKED_UNION & registered
    assert checked, "expected at least one registered blocked tool to assert against"
    for tool_name in checked:
        with pytest.raises(ToolAccessDenied):
            registry.validate_tool_access(tool_name, "member", twg_id=MEMBER_TWG)


def test_member_denied_blocked_tools_appear_in_no_session(registry):
    """No tool from the FULL blocked union ever leaks into the member's granted tool map."""
    _defs, tool_map = registry.get_tools_for_agent("member", twg_id=MEMBER_TWG)
    leaked = FULL_BLOCKED_UNION & set(tool_map.keys())
    assert not leaked, f"blocked tools leaked into member session: {leaked}"


def test_member_denied_whatsapp_tools(registry):
    """WhatsApp tools are BLOCKED for members.

    Rationale (see Task 1's "Why WhatsApp tools are blocked" note): spec §6 lists
    "broadcasts" + "invite or email people" in *Never exposed*, and §29 states the
    no-outward-communication / no-broadcast principle. WhatsApp send/group are an
    outward broadcast channel and the two read tools expose the org WhatsApp
    directory (not in the §6 member allow-list) — so all four are blocked. This is
    a plan-level interpretation of the spec, not a spec-named line item.

    Dedicated proof for the WhatsApp tool names (imported via WHATSAPP_TOOL_NAMES).
    They are registered today, so we both (a) assert each registered WhatsApp tool
    raises ToolAccessDenied for a member and (b) assert none leak into the member's
    granted tool map. The denial works because WhatsApp tools are absent from
    MEMBER_TOOLS, so the member branch's catch-all `raise ToolAccessDenied` fires.
    """
    registered = set(registry.list_tools())
    checked = WHATSAPP_TOOL_NAMES & registered
    assert checked, "expected WhatsApp tools to be registered to assert against"
    for tool_name in checked:
        with pytest.raises(ToolAccessDenied):
            registry.validate_tool_access(tool_name, "member", twg_id=MEMBER_TWG)
    _defs, tool_map = registry.get_tools_for_agent("member", twg_id=MEMBER_TWG)
    assert not (WHATSAPP_TOOL_NAMES & set(tool_map.keys())), (
        "WhatsApp tools leaked into member session"
    )


def test_member_allowlist_tools_validate_true(registry):
    """Allowlisted, registered tools validate True for a member with a twg_id."""
    for tool_name in MEMBER_TOOLS & set(registry.list_tools()):
        assert registry.validate_tool_access(tool_name, "member", twg_id=MEMBER_TWG) is True
```

- [ ] Run it and confirm it FAILS (import of `MEMBER_TOOLS` does not exist yet):

```bash
cd /Users/evan/ravishing-presence/backend && .venv/bin/python -m pytest tests/test_member_tool_scope.py -v
```

Expected: `ImportError: cannot import name 'MEMBER_TOOLS'` / collection error.
(The `from app.tools.whatsapp_tools import WHATSAPP_TOOL_NAMES` import already
succeeds because the export was added in the first step; the only missing symbol
at this point is `MEMBER_TOOLS`.)

- [ ] Implement. In `backend/app/tools/tool_registry.py`, immediately AFTER the
`UNRESTRICTED_TOOLS` set definition, add the block below. Anchor on the closing
of that set — search for this exact text and insert the new set right after its
closing `}` (and before the blank line that precedes `class ToolAccessDenied`):

```python
UNRESTRICTED_TOOLS: Set[str] = {
    "search_knowledge_base",
    "get_relevant_context",
    "get_knowledge_base_stats",
}
```

Add:

```python
# Tools available to TWG_MEMBER sessions via the `member` agent scope.
# Spec §6: read everything relevant to the member + perform the member's PERSONAL
# actions only. Never facilitator/admin powers (create-for-others, email, broadcast,
# pipeline edits, investor matching, user mgmt). This set is the single source of
# truth for the member allowlist; validate_tool_access enforces it.
MEMBER_TOOLS: Set[str] = {
    # Read: my meetings / agenda / time / join link
    "get_schedule",
    "get_past_meetings",
    # Find + summarize documents shared with my TWG
    "search_documents",
    "retrieve_document_content",
    # Read meeting summaries / decisions
    "get_meeting_minutes",
    # My action items + mark my own done
    "get_action_items",
    "update_action_item_status",
    # Knowledge base (registered as RAG helpers today; listed for forward-compat)
    "search_knowledge_base",
    "get_relevant_context",
    "get_knowledge_base_stats",
    # Personal actions (created in this plan)
    "rsvp_meeting",
    "set_reminder",
    "get_notifications",
}
```

In `validate_tool_access`, insert the member branch as the **FIRST** check — at
the very top of the method body, BEFORE the pipeline block. Making it first means
a member's access is decided **entirely** by `MEMBER_TOOLS`: a member can never
fall through to a broader branch that grants something, and can never be wrongly
denied by an earlier branch (e.g. a tool that also lives in `PIPELINE_READ_TOOLS`,
like `my_action_items`). It is the single, self-contained safety line from spec §3.

Anchor (NOT line numbers — they drift): insert the member branch immediately
BEFORE this existing block, which is currently the first check in the method —
search for this exact text and place the member branch just above it:

```python
        # Pipeline write/read tools — checked first so supervisor + TWG agents both get them.
        # User-role gating happens inside each tool body via _rbac.require_role.
        if tool_name in PIPELINE_WRITE_TOOLS or tool_name in PIPELINE_READ_TOOLS:
```

Inserting before every other branch is safe for existing agents because the member
branch only triggers when `agent_id == "member"` — a value no other agent uses, so
supervisor / TWG / resource_mobilization behavior is unchanged (proven by Task 2).
Because the branch always `return`s or `raise`s, a member request never reaches the
pipeline / supervisor / default branches at all.

```python
        # Member scope: TWG_MEMBER app sessions. Strictly the member allowlist.
        # Anything not in MEMBER_TOOLS is denied here, before any broader branch
        # can grant it — this is the safety line from spec §3.
        if agent_id == "member":
            if tool_name in MEMBER_TOOLS:
                # TWG-scoped member reads still require a twg_id, mirroring the
                # general TWG_SCOPED_TOOLS rule below.
                if tool_name in TWG_SCOPED_TOOLS and not twg_id:
                    raise ToolAccessDenied(
                        f"Tool '{tool_name}' requires TWG scope for member sessions."
                    )
                return True
            raise ToolAccessDenied(
                f"Tool '{tool_name}' is not part of the member toolset. "
                f"Members cannot perform facilitator/admin actions."
            )
```

- [ ] Run it and confirm it PASSES:

```bash
cd /Users/evan/ravishing-presence/backend && .venv/bin/python -m pytest tests/test_member_tool_scope.py -v
```

Expected: 5 passed. (Note: at this point `rsvp_meeting`, `set_reminder`, `get_notifications` are NOT registered yet, so `MEMBER_TOOLS ∩ registered` excludes them — the equality test holds because both sides exclude them. They get added in Tasks 4-6, and the same test keeps passing. The WhatsApp-denial test passes immediately because WhatsApp tools are already registered and absent from `MEMBER_TOOLS`.)

- [ ] Commit:

```bash
cd /Users/evan/ravishing-presence && git checkout -b feat/backend-member-martin && git add backend/app/tools/whatsapp_tools.py backend/app/tools/tool_registry.py backend/tests/test_member_tool_scope.py && git commit -m "feat(member): add member agent scope + MEMBER_TOOLS allowlist to tool registry

Also export WHATSAPP_TOOL_NAMES from whatsapp_tools (derived from WHATSAPP_TOOLS)
so the member-scope test imports the real names instead of a drift-prone copy.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 2 — Prove the existing tool-registry suite still passes (no regression to other agents)

**Files:** (none modified — regression gate)

### Steps

- [ ] Run BOTH the pre-existing registry suite AND the new member-scope suite
together, and confirm BOTH pass (the new `member` branch must not change
supervisor / TWG / resource_mobilization behavior, and the member scope itself
must hold):

```bash
cd /Users/evan/ravishing-presence/backend && .venv/bin/python -m pytest tests/test_tool_registry.py tests/test_member_tool_scope.py -v
```

Expected: all 5 `test_member_tool_scope.py` tests pass. For `test_tool_registry.py`,
expect the SAME pre-existing baseline as a clean checkout — exactly **two** KNOWN
failures, `TestAccessControl::test_supervisor_has_full_access` and
`TestToolRetrieval::test_supervisor_gets_all_tools` (stale assertions against the
now-restrictive supervisor logic, UNRELATED to this change) — and **no other**
failures. The member branch only triggers when `agent_id == "member"` (a value no
existing test uses), so it cannot change any existing result. If ANY other
`test_tool_registry.py` test newly fails, STOP and use superpowers:systematic-debugging.

- [ ] If anything fails, STOP and use superpowers:systematic-debugging before proceeding. Do not edit tests to make them pass.

- [ ] No commit (read-only verification task).

---

## Task 3 — Add the `Reminder` model (storage for the member set-reminder tool)

**Files:**
- Modify: `backend/app/models/models.py` (add `Reminder` model near other user-owned models; reuse existing `Base`, `User`)
- Create: `backend/tests/test_member_tools.py` (first test only)

### Steps

- [ ] Write the failing test in `backend/tests/test_member_tools.py`:

```python
"""Unit tests for the member personal-action tools (rsvp_meeting, set_reminder, get_notifications)."""
import uuid
import pytest

from app.models.models import UserRole


@pytest.mark.asyncio
async def test_reminder_model_persists(db_session):
    """The Reminder model stores a member's personal reminder linked to user_id."""
    from app.models.models import Reminder

    rid = uuid.uuid4()
    uid = uuid.uuid4()
    reminder = Reminder(
        id=rid,
        user_id=uid,
        message="Prep notes for Energy TWG",
        remind_at=__import__("datetime").datetime(2026, 6, 10, 9, 0, 0),
    )
    db_session.add(reminder)
    await db_session.flush()

    fetched = await db_session.get(Reminder, rid)
    assert fetched is not None
    assert fetched.user_id == uid
    assert fetched.message == "Prep notes for Energy TWG"
    assert fetched.is_sent is False
```

- [ ] Run it and confirm it FAILS (no `Reminder` model):

```bash
cd /Users/evan/ravishing-presence/backend && .venv/bin/python -m pytest tests/test_member_tools.py::test_reminder_model_persists -v
```

Expected: `ImportError: cannot import name 'Reminder'`.

- [ ] Implement. In `backend/app/models/models.py`, add the `Reminder` class
immediately BEFORE the `# --- Models ---` separator comment (i.e. right after the
`MeetingParticipant` class body ends — its last lines are the `meeting:` and
`user:` relationship declarations). Anchor on this exact text and insert the new
class between the end of `MeetingParticipant` and the separator:

```python
    # Relationships
    meeting: Mapped["Meeting"] = relationship(back_populates="participants")
    user: Mapped[Optional["User"]] = relationship(back_populates="meeting_participations")

# --- Models ---
```

Match the existing `Mapped[...] = mapped_column(...)` style. The `datetime.utcnow`
default is the established pattern in this module (e.g. `User.created_at` at
`User.created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)`,
`Notification.created_at`, `AuditLog.created_at`).

```python
class Reminder(Base):
    __tablename__ = "reminders"
    __table_args__ = {'extend_existing': True}

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    message: Mapped[str] = mapped_column(String(500))
    remind_at: Mapped[datetime] = mapped_column(DateTime)
    meeting_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, ForeignKey("meetings.id", ondelete="SET NULL"), nullable=True)
    is_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

(CONFIRMED already imported at the top of `backend/app/models/models.py`:
`import uuid`, `from datetime import datetime, date`, `from typing import List,
Optional`, and `from sqlalchemy import String, DateTime, ..., ForeignKey, ...,
Boolean, ..., Uuid, ...` — plus `from sqlalchemy.orm import Mapped, mapped_column`.
All of `Mapped`, `mapped_column`, `Uuid`, `ForeignKey`, `String`, `DateTime`,
`Boolean`, `Optional`, `uuid`, `datetime` resolve at class-body evaluation. Do NOT
add duplicate imports.)

- [ ] Run it and confirm it PASSES:

```bash
cd /Users/evan/ravishing-presence/backend && .venv/bin/python -m pytest tests/test_member_tools.py::test_reminder_model_persists -v
```

Expected: 1 passed. (The test conftest `db_engine` fixture creates tables via `Base.metadata`, so the new table is created automatically.)

- [ ] Commit:

```bash
cd /Users/evan/ravishing-presence && git add backend/app/models/models.py backend/tests/test_member_tools.py && git commit -m "feat(member): add Reminder model for member personal reminders

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 4 — Create `rsvp_meeting` tool (member RSVPs themselves) + register it

**Files:**
- Create: `backend/app/tools/member_tools.py` (`rsvp_meeting` + `RSVP_MEETING_TOOL_DEF`)
- Modify: `backend/app/tools/tool_registry.py` (`_register_database_tools` — register `rsvp_meeting`)
- Modify: `backend/tests/test_member_tools.py` (add RSVP tests)

The existing REST RSVP path (`@router.put("/{meeting_id}/participants/{participant_id}/rsvp", ...)`
in `meetings.py`, decorated `Depends(require_facilitator)` and keyed by
`participant_id`) is facilitator-only and not self-service. Members need a
self-service path: resolve the caller's own `MeetingParticipant` row by `user_id`,
then set `rsvp_status`. The tool is role-gated to `TWG_MEMBER`-and-up via
`_rbac.require_role` as defense-in-depth.

### Steps

- [ ] Write failing tests — append to `backend/tests/test_member_tools.py`:

```python
@pytest.mark.asyncio
async def test_rsvp_meeting_updates_own_participant(db_session, monkeypatch):
    """rsvp_meeting sets the caller's own MeetingParticipant.rsvp_status to ACCEPTED."""
    from datetime import datetime
    from app.models.models import Meeting, MeetingParticipant, RsvpStatus, TWG, TWGPillar
    import app.tools.member_tools as member_tools

    # TWG.pillar is Mapped[TWGPillar] = mapped_column(Enum(TWGPillar)) — use the
    # enum, not a bare string (models.py: TWGPillar.energy_infrastructure, etc.).
    twg = TWG(id=uuid.uuid4(), name="Energy", pillar=TWGPillar.energy_infrastructure)
    meeting = Meeting(id=uuid.uuid4(), title="Energy Sync", twg_id=twg.id, scheduled_at=datetime(2026, 6, 10, 10, 0))
    uid = uuid.uuid4()
    part = MeetingParticipant(id=uuid.uuid4(), meeting_id=meeting.id, user_id=uid, rsvp_status=RsvpStatus.PENDING)
    db_session.add_all([twg, meeting, part])
    await db_session.flush()

    # Tool opens its own AsyncSessionLocal — point it at the test session factory.
    monkeypatch.setattr(member_tools, "AsyncSessionLocal", _session_factory(db_session))

    result = await member_tools.rsvp_meeting(
        meeting_id=str(meeting.id),
        response="ACCEPTED",
        user_id=str(uid),
        user_role=UserRole.TWG_MEMBER,
    )
    assert result["success"] is True
    assert result["rsvp_status"] == "ACCEPTED"


@pytest.mark.asyncio
async def test_rsvp_meeting_rejects_invalid_response(db_session, monkeypatch):
    """An unknown RSVP value returns an error dict, not a crash."""
    import app.tools.member_tools as member_tools
    monkeypatch.setattr(member_tools, "AsyncSessionLocal", _session_factory(db_session))
    result = await member_tools.rsvp_meeting(
        meeting_id=str(uuid.uuid4()),
        response="MAYBE_LATER",
        user_id=str(uuid.uuid4()),
        user_role=UserRole.TWG_MEMBER,
    )
    assert "error" in result


@pytest.mark.asyncio
async def test_rsvp_meeting_not_a_participant_returns_error(db_session, monkeypatch):
    """A member who is not a participant of the meeting cannot RSVP it."""
    import app.tools.member_tools as member_tools
    monkeypatch.setattr(member_tools, "AsyncSessionLocal", _session_factory(db_session))
    result = await member_tools.rsvp_meeting(
        meeting_id=str(uuid.uuid4()),
        response="ACCEPTED",
        user_id=str(uuid.uuid4()),
        user_role=UserRole.TWG_MEMBER,
    )
    assert "error" in result
```

Add this helper near the top of `backend/tests/test_member_tools.py` (below the imports):

```python
def _session_factory(session):
    """Return a zero-arg callable usable as `async with AsyncSessionLocal() as s`
    that yields the test's transactional session without closing it."""
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def _factory():
        yield session

    return _factory
```

- [ ] Run and confirm FAIL:

```bash
cd /Users/evan/ravishing-presence/backend && .venv/bin/python -m pytest tests/test_member_tools.py -k rsvp -v
```

Expected: `ModuleNotFoundError: No module named 'app.tools.member_tools'`.

- [ ] Implement `backend/app/tools/member_tools.py`:

```python
"""Member personal-action tools: self-RSVP, set-reminder, read-notifications.

These are the ONLY write/personal tools a TWG_MEMBER may invoke (spec §6). Each
body re-checks the caller's role via _rbac.require_role as defense-in-depth, so
even if the registry allowlist were bypassed the tool refuses non-members.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.models import (
    MeetingParticipant,
    Notification,
    Reminder,
    RsvpStatus,
    UserRole,
)
from app.tools._rbac import require_role

# Members and anyone above them may use these personal-action tools — they are
# harmless self-service (RSVP yourself, set your own reminder, read your own
# notifications) and touch only the caller's own rows. This set intentionally
# spans ALL FOUR UserRole values, so require_role here is a defense-in-depth
# guard that refuses only an UNRECOGNIZED role value (e.g. a forged/corrupted
# context that is not a real UserRole), NOT any legitimate role. The real scope
# restriction (members vs facilitators) lives at the registry + endpoint layer.
_MEMBER_ROLES = {
    UserRole.TWG_MEMBER,
    UserRole.TWG_FACILITATOR,
    UserRole.SECRETARIAT_LEAD,
    UserRole.ADMIN,
}

_RSVP_MAP = {
    "ACCEPTED": RsvpStatus.ACCEPTED,
    "DECLINED": RsvpStatus.DECLINED,
    "PENDING": RsvpStatus.PENDING,
}


def _error(message: str) -> Dict[str, Any]:
    """Standard error envelope for member tools.

    Mirrors the require_role forbidden shape ({"status": ..., "reason"/"error"})
    so every non-success return from a member tool is a dict with a "status" key
    and a human-readable string. Tests assert `"error" in result` for these.
    """
    return {"status": "error", "error": message}


async def rsvp_meeting(
    meeting_id: str,
    response: str,
    user_id: str,
    user_role: UserRole,
) -> Dict[str, Any]:
    """Set the calling member's own RSVP on a meeting they participate in."""
    # require_role is SYNCHRONOUS (returns Optional[dict] immediately) — do NOT await it.
    err = require_role(user_role, _MEMBER_ROLES)
    if err is not None:
        return err

    status = _RSVP_MAP.get((response or "").upper())
    if status is None:
        return _error(f"Invalid RSVP '{response}'. Use ACCEPTED, DECLINED, or PENDING.")

    try:
        meeting_uuid = uuid.UUID(meeting_id)
        user_uuid = uuid.UUID(user_id)
    except (ValueError, TypeError):
        return _error("Invalid meeting_id or user_id.")

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(MeetingParticipant).where(
                MeetingParticipant.meeting_id == meeting_uuid,
                MeetingParticipant.user_id == user_uuid,
            )
        )
        participant = result.scalar_one_or_none()
        if participant is None:
            return _error("You are not a participant of this meeting.")

        participant.rsvp_status = status
        await session.commit()
        return {
            "success": True,
            "meeting_id": meeting_id,
            "rsvp_status": status.value,
        }


async def set_reminder(
    message: str,
    remind_at_iso: str,
    user_id: str,
    user_role: UserRole,
    meeting_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a personal reminder for the calling member."""
    # require_role is SYNCHRONOUS (returns Optional[dict] immediately) — do NOT await it.
    err = require_role(user_role, _MEMBER_ROLES)
    if err is not None:
        return err

    try:
        user_uuid = uuid.UUID(user_id)
    except (ValueError, TypeError):
        return _error("Invalid user_id.")

    try:
        remind_at = datetime.fromisoformat(remind_at_iso)
    except (ValueError, TypeError):
        return _error("Invalid remind_at_iso. Use ISO 8601, e.g. 2026-06-10T09:00:00.")

    meeting_uuid: Optional[uuid.UUID] = None
    if meeting_id:
        try:
            meeting_uuid = uuid.UUID(meeting_id)
        except (ValueError, TypeError):
            return _error("Invalid meeting_id.")

    async with AsyncSessionLocal() as session:
        reminder = Reminder(
            user_id=user_uuid,
            message=message,
            remind_at=remind_at,
            meeting_id=meeting_uuid,
        )
        session.add(reminder)
        await session.commit()
        await session.refresh(reminder)
        return {
            "success": True,
            "reminder_id": str(reminder.id),
            "message": reminder.message,
            "remind_at": reminder.remind_at.isoformat(),
        }


async def get_notifications(
    user_id: str,
    user_role: UserRole,
    limit: int = 20,
) -> Dict[str, Any]:
    """Read the calling member's own notifications (most recent first)."""
    # require_role is SYNCHRONOUS (returns Optional[dict] immediately) — do NOT await it.
    err = require_role(user_role, _MEMBER_ROLES)
    if err is not None:
        return err

    try:
        user_uuid = uuid.UUID(user_id)
    except (ValueError, TypeError):
        return _error("Invalid user_id.")

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Notification)
            .where(Notification.user_id == user_uuid)
            .order_by(Notification.created_at.desc())
            .limit(limit)
        )
        rows = result.scalars().all()
        # Notification model fields (CONFIRMED `class Notification(Base)` in
        # backend/app/models/models.py) are `title` (String(255)) + `content`
        # (Text) — NOT `message` — plus `type` (NotificationType, default INFO),
        # `is_read` (bool), `created_at` (DateTime), `link` (Optional[str]).
        return {
            "count": len(rows),
            "notifications": [
                {
                    "id": str(n.id),
                    "title": n.title,
                    "content": n.content,
                    "type": n.type.value if getattr(n, "type", None) is not None else None,
                    "is_read": n.is_read,
                    "created_at": n.created_at.isoformat() if getattr(n, "created_at", None) else None,
                }
                for n in rows
            ],
        }


RSVP_MEETING_TOOL_DEF = {
    "type": "function",
    "function": {
        "name": "rsvp_meeting",
        "description": (
            "RSVP the current user to a meeting they are invited to. "
            "Use when the user says they will/won't attend a meeting. "
            "response must be ACCEPTED, DECLINED, or PENDING. "
            "Only affects the current user's own RSVP — never anyone else's."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "meeting_id": {"type": "string", "description": "UUID of the meeting to RSVP to."},
                "response": {
                    "type": "string",
                    "enum": ["ACCEPTED", "DECLINED", "PENDING"],
                    "description": "The user's attendance response.",
                },
            },
            "required": ["meeting_id", "response"],
        },
    },
}

SET_REMINDER_TOOL_DEF = {
    "type": "function",
    "function": {
        "name": "set_reminder",
        "description": (
            "Create a personal reminder/nudge for the current user. "
            "Use when the user asks to be reminded of something. "
            "remind_at_iso is ISO 8601 local time (e.g. 2026-06-10T09:00:00)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "message": {"type": "string", "description": "What to remind the user about."},
                "remind_at_iso": {"type": "string", "description": "ISO 8601 datetime to fire the reminder."},
                "meeting_id": {"type": "string", "description": "Optional meeting this reminder relates to."},
            },
            "required": ["message", "remind_at_iso"],
        },
    },
}

GET_NOTIFICATIONS_TOOL_DEF = {
    "type": "function",
    "function": {
        "name": "get_notifications",
        "description": (
            "Read the current user's own notifications, most recent first. "
            "Use when the user asks 'what did I miss', 'any updates', or about their alerts."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Max notifications to return (default 20).", "default": 20},
            },
            "required": [],
        },
    },
}
```

Register all three member tools in `tool_registry.py` `_register_database_tools`
at the END of that method. Anchor on the `get_twg_members` registration block,
which is the LAST statement of `_register_database_tools` — search for this exact
text and insert the new block immediately AFTER its closing `)`:

```python
            handler=get_twg_members,
            required_params=[],
        )
```

(The very next thing in the file is `def _register_deal_pipeline_tools(self) -> None:`
— the new block must sit BEFORE that `def`, i.e. still inside
`_register_database_tools`.)

The identity-injection contract is CONFIRMED in `agent_loop.py` `_execute_tools`:
it does `sig = inspect.signature(func)` and, if the handler's signature declares
`user_id` / `user_role`, injects them from `get_user_for_thread(thread_id)` (the
block guarded by `if "user_id" in sig.parameters or "user_role" in sig.parameters:`).
Therefore:
- The handler FUNCTIONS must declare `user_id: str` and `user_role: UserRole`
  parameters (they do — see the `async def rsvp_meeting(... user_id: str,
  user_role: UserRole)`, `set_reminder`, and `get_notifications` signatures in
  `member_tools.py`) so agent_loop can inject them.
- The LLM-VISIBLE schema must EXCLUDE them so the model never controls identity.
  The registration below passes `func_def["parameters"].get("properties", {})`,
  i.e. only the `properties` dict from each `*_TOOL_DEF`, which already omits
  `user_id`/`user_role` (and `required` omits them too). The `register()`
  signature is `register(self, name, description, parameters, handler,
  required_params=None)` (CONFIRMED in `tool_registry.py`), so this maps exactly.

The block below ALSO asserts the identity-injection contract at registration time
(MAJOR fix): for each member handler it (a) confirms the handler signature
declares BOTH `user_id` and `user_role` (so agent_loop will inject them), and
(b) confirms NEITHER appears in the LLM-visible `properties` NOR in
`required_params` (so the model can never set them). If either assertion fails
the registry refuses to start — a forged-identity escalation can't be shipped
silently. `inspect` is already imported at the top of `tool_registry.py`.

EVERY assertion message MUST name the offending tool via `func_def['name']`
(MAJOR fix — debuggability): the loop runs over all three member tools, so a bare
"member tool must declare user_id AND user_role" would not tell you whether
`rsvp_meeting`, `set_reminder`, or `get_notifications` tripped it. Each message
interpolates `{func_def['name']}` AND the offending value set (`handler_params`
for the signature check, `leaked=...` for the schema/required checks) so the
failure pinpoints both the tool and exactly what was wrong.

```python
        # Member personal-action tools (self-RSVP, set-reminder, read-notifications).
        # user_id/user_role are auto-injected by agent_loop (inspect.signature →
        # get_user_for_thread) and intentionally absent from the schemas below,
        # so the LLM never controls identity.
        from app.tools.member_tools import (
            RSVP_MEETING_TOOL_DEF, rsvp_meeting,
            SET_REMINDER_TOOL_DEF, set_reminder,
            GET_NOTIFICATIONS_TOOL_DEF, get_notifications,
        )
        for tool_def, handler in [
            (RSVP_MEETING_TOOL_DEF, rsvp_meeting),
            (SET_REMINDER_TOOL_DEF, set_reminder),
            (GET_NOTIFICATIONS_TOOL_DEF, get_notifications),
        ]:
            func_def = tool_def["function"]
            properties = func_def["parameters"].get("properties", {})
            required = func_def["parameters"].get("required", [])
            # Identity-injection contract guard (defense-in-depth):
            handler_params = set(inspect.signature(handler).parameters)
            assert {"user_id", "user_role"} <= handler_params, (
                f"member tool '{func_def['name']}' must declare user_id AND "
                f"user_role for agent_loop to inject identity; got {handler_params}"
            )
            assert not ({"user_id", "user_role"} & set(properties)), (
                f"member tool '{func_def['name']}' schema must NOT expose "
                f"user_id/user_role — the LLM must not control identity; "
                f"leaked={ {'user_id', 'user_role'} & set(properties) }"
            )
            assert not ({"user_id", "user_role"} & set(required)), (
                f"member tool '{func_def['name']}' must not require "
                f"user_id/user_role (they are auto-injected, not LLM-supplied); "
                f"leaked={ {'user_id', 'user_role'} & set(required) }"
            )
            self.register(
                name=func_def["name"],
                description=func_def["description"],
                parameters=properties,
                handler=handler,
                required_params=required,
            )
```

- [ ] Run and confirm PASS:

```bash
cd /Users/evan/ravishing-presence/backend && .venv/bin/python -m pytest tests/test_member_tools.py -k rsvp -v
```

Expected: 3 passed.

- [ ] Re-run Task 1's scope suite to confirm `rsvp_meeting` is now in the granted member set and the equality test still holds:

```bash
cd /Users/evan/ravishing-presence/backend && .venv/bin/python -m pytest tests/test_member_tool_scope.py -v
```

Expected: 5 passed.

- [ ] Commit:

```bash
cd /Users/evan/ravishing-presence && git add backend/app/tools/member_tools.py backend/app/tools/tool_registry.py backend/tests/test_member_tools.py && git commit -m "feat(member): add member personal-action tools (rsvp_meeting + set_reminder + get_notifications scaffolding) and register rsvp_meeting

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 5 — Cover `set_reminder` (member sets own reminder; role-gated)

**Files:**
- Modify: `backend/tests/test_member_tools.py` (add set_reminder tests)
- (Handler + registration already created in Task 4; this task locks behavior with tests.)

### Steps

- [ ] Write failing/uncovered tests — append to `backend/tests/test_member_tools.py`:

```python
@pytest.mark.asyncio
async def test_set_reminder_persists_for_member(db_session, monkeypatch):
    """A member can create a personal reminder; row is owned by their user_id."""
    import app.tools.member_tools as member_tools
    from app.models.models import Reminder

    monkeypatch.setattr(member_tools, "AsyncSessionLocal", _session_factory(db_session))
    uid = uuid.uuid4()
    result = await member_tools.set_reminder(
        message="Review Q3 docs",
        remind_at_iso="2026-06-10T09:00:00",
        user_id=str(uid),
        user_role=UserRole.TWG_MEMBER,
    )
    assert result["success"] is True
    stored = await db_session.get(Reminder, uuid.UUID(result["reminder_id"]))
    assert stored is not None
    assert stored.user_id == uid


@pytest.mark.asyncio
async def test_set_reminder_rejects_bad_datetime(db_session, monkeypatch):
    import app.tools.member_tools as member_tools
    monkeypatch.setattr(member_tools, "AsyncSessionLocal", _session_factory(db_session))
    result = await member_tools.set_reminder(
        message="x", remind_at_iso="not-a-date",
        user_id=str(uuid.uuid4()), user_role=UserRole.TWG_MEMBER,
    )
    assert "error" in result
```

- [ ] Run and confirm PASS (handler already implemented in Task 4):

```bash
cd /Users/evan/ravishing-presence/backend && .venv/bin/python -m pytest tests/test_member_tools.py -k reminder -v
```

Expected: `test_reminder_model_persists`, `test_set_reminder_persists_for_member`, `test_set_reminder_rejects_bad_datetime` all pass (3 passed).

- [ ] Commit:

```bash
cd /Users/evan/ravishing-presence && git add backend/tests/test_member_tools.py && git commit -m "test(member): cover set_reminder persistence and validation

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 6 — Cover `get_notifications`, non-member role refusal, and the identity-injection security gap (defense-in-depth)

**Files:**
- Modify: `backend/tests/test_member_tools.py` (add get_notifications + role-gate tests + the two SECURITY tests proving identity cannot be forged)

### Steps

- [ ] Write tests — append to `backend/tests/test_member_tools.py`:

```python
# A sentinel that simulates a FORGED / CORRUPTED role context — a value that
# reaches require_role but is NOT a real UserRole. We do NOT pass a bare string
# typed as a UserRole (that would violate the param's type contract); instead we
# use a distinct enum member from an unrelated enum so the value is genuinely
# "not a UserRole" while staying a real, hashable, comparable object. require_role
# does `if user_role in allowed_set`, so this value is simply absent from
# _MEMBER_ROLES and is refused without any isinstance/type assumption.
import enum as _enum


class _ForgedRole(_enum.Enum):
    OUTSIDER = "outsider"  # not a member of app.models.models.UserRole


@pytest.mark.asyncio
async def test_get_notifications_returns_only_callers(db_session, monkeypatch):
    """get_notifications returns the caller's own notifications and counts them."""
    import app.tools.member_tools as member_tools
    # Real Notification fields are title + content + type (NOT `message`):
    # see `class Notification(Base)` in backend/app/models/models.py.
    from app.models.models import Notification, NotificationType

    uid = uuid.uuid4()
    other = uuid.uuid4()
    db_session.add_all([
        Notification(id=uuid.uuid4(), user_id=uid, title="Test", content="Yours", type=NotificationType.INFO),
        Notification(id=uuid.uuid4(), user_id=other, title="Test", content="Not yours", type=NotificationType.INFO),
    ])
    await db_session.flush()

    monkeypatch.setattr(member_tools, "AsyncSessionLocal", _session_factory(db_session))
    result = await member_tools.get_notifications(user_id=str(uid), user_role=UserRole.TWG_MEMBER)
    assert result["count"] == 1
    assert result["notifications"][0]["content"] == "Yours"


@pytest.mark.asyncio
async def test_member_tools_refuse_unknown_role():
    """Defense-in-depth: a role outside the member set is refused by the tool body.

    _MEMBER_ROLES contains ALL FOUR UserRole enum values (TWG_MEMBER,
    TWG_FACILITATOR, SECRETARIAT_LEAD, ADMIN), so NO real UserRole is refused —
    that is intentional (members + everyone above them may use these harmless
    self-service tools). To exercise the refusal path we pass a FORGED/CORRUPTED
    role (`_ForgedRole.OUTSIDER`, which is not a UserRole). require_role returns
    {"status": "forbidden", "reason": "Requires one of: ..."} without crashing.
    The role gate runs BEFORE any DB access, so no session monkeypatch is needed.
    """
    import app.tools.member_tools as member_tools

    res = await member_tools.get_notifications(
        user_id=str(uuid.uuid4()), user_role=_ForgedRole.OUTSIDER
    )
    assert res.get("status") == "forbidden"
    assert "Requires one of" in res.get("reason", "")
```

Note (CONFIRMED against `class Notification(Base)` in
backend/app/models/models.py): the `Notification` model has fields `id`,
`user_id`, `type` (`NotificationType`, default `INFO`), `title` (`String(255)`),
`content` (`Text`), `link`, `is_read` (`bool`), `created_at`. There is NO
`message` column. Both the test (constructs with
`title=`/`content=`/`type=NotificationType.INFO`) and the `get_notifications`
projection (returns `title`/`content`/`type`/`is_read`/`created_at`) use these
real field names. Do NOT use `message`.

- [ ] SECURITY (spec §3/§13): prove a member CANNOT escalate by manipulating the
role/user context in a tool call. This has two halves: (a) the registered,
LLM-visible schema EXCLUDES `user_id`/`user_role`, so the model can never set
them; and (b) the agent loop injects the BOUND member identity from
`get_user_for_thread`, and that injected identity — not anything else — is what
the tool actually writes. Append both to `backend/tests/test_member_tools.py`:

> **Inter-task dependency (read before running):** both security tests below
> depend on Tasks 4–6 having REGISTERED all three member tools (`rsvp_meeting`,
> `set_reminder`, `get_notifications`) in `_register_database_tools`. If
> `test_member_tool_schemas_exclude_identity_params` is run BEFORE Task 4's
> registration block exists, `reg.get_tool_info(tool_name)` returns `None` and
> the test fails immediately at `assert info is not None` with "`rsvp_meeting`
> must be registered" — that is the EXPECTED red state for these tests until
> registration lands. They turn green only once Tasks 4–6 complete; the test
> then proves identity params are excluded from the registered schemas. (When
> executing tasks strictly in order this never bites, because these tests are
> authored in Task 6 AFTER Task 4 registers the tools — but the dependency is
> recorded here for anyone running tests out of order.)

```python
def test_member_tool_schemas_exclude_identity_params():
    """The LLM-visible schemas for member tools must NOT expose user_id/user_role.

    This is the structural guarantee that a member cannot escalate by supplying a
    forged identity in a tool call: the model literally has no parameter to set.
    Identity is auto-injected server-side by agent_loop from the bound member
    context (set_user_for_thread), never taken from the LLM.

    DEPENDS ON Tasks 4-6 registering rsvp_meeting/set_reminder/get_notifications.
    Run before registration, it fails at `assert info is not None` (expected red).
    """
    from app.tools.tool_registry import ToolRegistry

    reg = ToolRegistry()
    reg.register_all()
    for tool_name in ("rsvp_meeting", "set_reminder", "get_notifications"):
        info = reg.get_tool_info(tool_name)
        assert info is not None, f"{tool_name} must be registered"
        params = set(info["parameters"].keys())
        assert "user_id" not in params, f"{tool_name} schema leaks user_id to the LLM"
        assert "user_role" not in params, f"{tool_name} schema leaks user_role to the LLM"


@pytest.mark.asyncio
async def test_injected_member_identity_wins_over_llm_args(db_session, monkeypatch):
    """End-to-end through agent_loop: the tool writes the BOUND member's identity,
    not anyone the LLM could name.

    We bind a member via set_user_for_thread, then drive AgentLoop._execute_tools
    with a tool_call whose args match the real (identity-free) schema — exactly
    what the model can produce. The persisted Reminder must be owned by the bound
    member, proving identity comes from the injected context and is uncontrollable
    by the LLM. We also stash a DIFFERENT 'attacker' id under a different thread to
    show the bound thread's identity is the one used.
    """
    import app.tools.member_tools as member_tools
    from app.models.models import Reminder
    from app.agents.agent_loop import AgentLoop
    from app.tools._rbac import set_user_for_thread, _user_by_thread

    monkeypatch.setattr(member_tools, "AsyncSessionLocal", _session_factory(db_session))

    member_id = uuid.uuid4()
    attacker_id = uuid.uuid4()
    thread_id = f"member-thread-{uuid.uuid4()}"
    attacker_thread = f"attacker-thread-{uuid.uuid4()}"
    # Bind the real member to THIS thread; stash an attacker under another thread.
    set_user_for_thread(thread_id, str(member_id), UserRole.TWG_MEMBER)
    set_user_for_thread(attacker_thread, str(attacker_id), UserRole.TWG_MEMBER)

    loop = AgentLoop(
        agent_id="member",
        system_prompt="test",
        tools=[],
        tool_map={"set_reminder": member_tools.set_reminder},
        llm=object(),  # never called — we invoke _execute_tools directly
        twg_id=None,
    )
    # The tool_call args contain ONLY schema params (no user_id/user_role) — this
    # is the most an LLM could ever emit, because the schema excludes identity.
    tool_calls = [{
        "id": "call_1",
        "name": "set_reminder",
        "args": {"message": "Prep notes", "remind_at_iso": "2026-06-10T09:00:00"},
    }]
    results = await loop._execute_tools(tool_calls, thread_id=thread_id, user_timezone=None)
    name, _tc_id, result_str = results[0]
    payload = __import__("json").loads(result_str)
    assert payload.get("success") is True, result_str

    stored = await db_session.get(Reminder, uuid.UUID(payload["reminder_id"]))
    assert stored is not None
    # The reminder is owned by the BOUND member — never the attacker.
    assert stored.user_id == member_id
    assert stored.user_id != attacker_id

    _user_by_thread.pop(thread_id, None)
    _user_by_thread.pop(attacker_thread, None)
```

(CONFIRMED: `AgentLoop._execute_tools(self, tool_calls, thread_id, user_timezone)`
is an `async` method; when a handler's signature declares `user_id`/`user_role`
and the arg is ABSENT, it injects from `get_user_for_thread(thread_id)` — see the
`if "user_id" in sig.parameters or "user_role" in sig.parameters:` block in
`agent_loop.py`. `_user_by_thread` is the module-level dict in `app.tools._rbac`.)

- [ ] Run and confirm PASS:

```bash
cd /Users/evan/ravishing-presence/backend && .venv/bin/python -m pytest tests/test_member_tools.py -v
```

Expected: all member-tool tests pass (including the two SECURITY tests above).

- [ ] Re-run the scope suite — all three new tools must now be in the granted member set:

```bash
cd /Users/evan/ravishing-presence/backend && .venv/bin/python -m pytest tests/test_member_tool_scope.py -v
```

Expected: 5 passed (granted == `MEMBER_TOOLS ∩ registered`, now including all three new tools).

- [ ] Commit:

```bash
cd /Users/evan/ravishing-presence && git add backend/tests/test_member_tools.py && git commit -m "test(member): cover get_notifications scoping, non-member role refusal, and identity-injection security (schema excludes user_id/user_role; injected member identity wins)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 7 — `run_member_chat` runner (builds + runs AgentLoop as agent_id="member")

**Files:**
- Create: `backend/app/agents/member_agent.py`
- Modify: `backend/tests/test_member_chat_endpoint.py` (runner unit test — first test)

This mirrors how `AgentLoop` is already used (its `run(self, query, thread_id,
user_timezone=None, stream_callback=None)` method, and the constructor
`AgentLoop(agent_id, system_prompt, tools, tool_map, llm, twg_id=None, ...)`):
build tool defs + handler map from the registry for `agent_id="member"`, then run
the loop with the member's `twg_id`. User identity is bound via
`set_user_for_thread` so `agent_loop._execute_tools` auto-injects
`user_id`/`user_role` into the member tools (the
`if "user_id" in sig.parameters or "user_role" in sig.parameters:` block).

SECURITY (FATAL fix — no hardcoded role): `run_member_chat` must NOT hardcode
`UserRole.TWG_MEMBER` for the bound context. It accepts `user_role: UserRole` as a
parameter and binds THAT (the authenticated caller's real role, asserted to be
`TWG_MEMBER` by the endpoint in Task 8). Hardcoding the role would let a future or
misrouted caller of a different role run inside the member scope under a forged
member identity. The agent_id is still pinned to `"member"` so the registry
enforces the member toolset regardless.

### Steps

- [ ] Write the failing test `backend/tests/test_member_chat_endpoint.py`:

```python
"""Member-Martin runner + endpoint scoping proofs."""
import uuid
import pytest
from unittest.mock import AsyncMock, patch

from app.models.models import UserRole


@pytest.mark.asyncio
async def test_run_member_chat_uses_member_scope_and_member_tools():
    """run_member_chat builds the loop with agent_id='member' and only member tools."""
    from app.agents import member_agent

    captured = {}

    class _FakeLoop:
        def __init__(self, agent_id, system_prompt, tools, tool_map, llm, twg_id=None, **kw):
            captured["agent_id"] = agent_id
            captured["tool_names"] = set(tool_map.keys())
            captured["twg_id"] = twg_id

        async def run(self, query, thread_id, user_timezone=None, stream_callback=None):
            from app.agents.agent_loop import AgentResponse
            return AgentResponse(content="Here is your briefing.", agent_id="member")

    bound_uid = str(uuid.uuid4())
    bound_thread = str(uuid.uuid4())

    with patch.object(member_agent, "AgentLoop", _FakeLoop), \
         patch.object(member_agent, "get_llm_service", return_value=AsyncMock()):
        twg = str(uuid.uuid4())
        resp = await member_agent.run_member_chat(
            message="what are my meetings?",
            user_id=bound_uid,
            user_role=UserRole.TWG_MEMBER,
            twg_id=twg,
            thread_id=bound_thread,
        )

    from app.tools.tool_registry import MEMBER_TOOLS, get_tool_registry
    from app.tools._rbac import get_user_for_thread
    registered = set(get_tool_registry().list_tools())
    assert captured["agent_id"] == "member"
    assert captured["twg_id"] == twg
    # Granted tools must be a subset of the allowlist — nothing leaks in.
    assert captured["tool_names"] <= (MEMBER_TOOLS & registered)
    assert "create_meeting" not in captured["tool_names"]
    assert "send_email" not in captured["tool_names"]
    assert resp.content == "Here is your briefing."
    # The runner binds the PASSED user_id + role (not a hardcoded one) to the thread.
    bound = get_user_for_thread(bound_thread)
    assert bound is not None
    assert bound[0] == bound_uid
    assert bound[1] == UserRole.TWG_MEMBER
```

- [ ] Run and confirm FAIL:

```bash
cd /Users/evan/ravishing-presence/backend && .venv/bin/python -m pytest tests/test_member_chat_endpoint.py::test_run_member_chat_uses_member_scope_and_member_tools -v
```

Expected: `ModuleNotFoundError: No module named 'app.agents.member_agent'`.

- [ ] Implement `backend/app/agents/member_agent.py`:

```python
"""Member-Martin runner.

Runs the EXISTING AgentLoop scoped to agent_id="member", so a TWG_MEMBER gets
exactly the member toolset enforced by ToolRegistry. No new permissions live
here — the registry is the enforcement point (spec §5).
"""
from __future__ import annotations

from typing import Callable, Optional

from app.agents.agent_loop import AgentLoop, AgentResponse
from app.models.models import UserRole
from app.services.llm_service import get_llm_service
from app.tools._rbac import set_user_context, set_user_for_thread
from app.tools.tool_registry import get_tool_registry

MEMBER_AGENT_ID = "member"

MEMBER_SYSTEM_PROMPT = (
    "You are Martin, the AfCEN assistant inside the member mobile app. "
    "You help this TWG MEMBER with THEIR OWN tasks only: view their meetings, "
    "agenda and join links; find and summarize documents shared with their TWG; "
    "read and update their own action items; RSVP themselves to meetings; set "
    "their own reminders; read their notifications; and search the knowledge base. "
    "You CANNOT create meetings for others, email or invite people, send broadcasts, "
    "edit the deal pipeline or scores, run investor matching, generate memos, or "
    "manage users — those are not available to members. If the user asks for one of "
    "those, explain politely that it is handled by their facilitator on the web platform. "
    "Be concise, warm, and institutional."
)


async def run_member_chat(
    message: str,
    user_id: str,
    user_role: UserRole,
    twg_id: str,
    thread_id: str,
    user_timezone: Optional[str] = None,
    stream_callback: Optional[Callable] = None,
) -> AgentResponse:
    """Run a member-scoped Martin turn and return the AgentResponse.

    `user_role` is the authenticated caller's REAL role (the endpoint asserts it
    is TWG_MEMBER before calling). It is bound — never hardcoded — so the
    role-gated member tools see the true caller. The agent_id is pinned to
    "member", so the registry enforces the member toolset regardless of role.
    """
    # Bind identity so role-gated member tools see who's calling (auto-injected
    # by AgentLoop._execute_tools via get_user_for_thread).
    set_user_context(str(user_id), user_role)
    set_user_for_thread(str(thread_id), str(user_id), user_role)

    registry = get_tool_registry()
    tools, tool_map = registry.get_tools_for_agent(MEMBER_AGENT_ID, twg_id=str(twg_id))

    loop = AgentLoop(
        agent_id=MEMBER_AGENT_ID,
        system_prompt=MEMBER_SYSTEM_PROMPT,
        tools=tools,
        tool_map=tool_map,
        llm=get_llm_service(),
        twg_id=str(twg_id),
    )
    return await loop.run(
        query=message,
        thread_id=str(thread_id),
        user_timezone=user_timezone,
        stream_callback=stream_callback,
    )
```

Confirm `get_tool_registry` is the public accessor in `tool_registry.py` (the
module-level `def get_tool_registry() -> ToolRegistry:` singleton factory, also
used inside `agent_loop._execute_tools`); use that exact name.

- [ ] Run and confirm PASS:

```bash
cd /Users/evan/ravishing-presence/backend && .venv/bin/python -m pytest tests/test_member_chat_endpoint.py::test_run_member_chat_uses_member_scope_and_member_tools -v
```

Expected: 1 passed.

- [ ] Commit:

```bash
cd /Users/evan/ravishing-presence && git add backend/app/agents/member_agent.py backend/tests/test_member_chat_endpoint.py && git commit -m "feat(member): run_member_chat runner — AgentLoop scoped to agent_id=member

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 8 — `POST /api/v1/agents/member/chat` endpoint (member-only, twg-checked)

**Files:**
- Modify: `backend/app/api/routes/agents.py` (add endpoint; reuses existing `AgentChatRequest`/`AgentChatResponse` schemas, `get_current_active_user`, `has_twg_access`)
- Modify: `backend/tests/test_member_chat_endpoint.py` (add endpoint tests)

The endpoint (FATAL fix — assert role BEFORE calling): it requires an
authenticated `TWG_MEMBER`. It MUST assert `current_user.role ==
UserRole.TWG_MEMBER` and raise 403 for any other role (facilitators/admins keep
the web platform per spec §3) BEFORE calling `run_member_chat`. It requires +
verifies `twg_id`, then calls `run_member_chat` passing `current_user.id` AND
`current_user.role` through (never a hardcoded role).

### Steps

- [ ] Write failing endpoint tests — append to `backend/tests/test_member_chat_endpoint.py`:

Authentication in these tests follows the conftest convention (CONFIRMED in
`backend/tests/conftest.py`), NOT the login endpoint:
- The `/api/v1/auth/login` route takes a JSON `UserLogin` body `{email, password}`
  (`@router.post("/login", response_model=Token)` in `auth.py`, body type
  `UserLogin`) — it is NOT OAuth2 form-encoded, so there is no `username` field.
- `/api/v1/auth/register` is DISABLED — its decorator is
  `@router.post("/register", ..., status_code=status.HTTP_403_FORBIDDEN)` and the
  body always `raise HTTPException(status_code=403, ...)`. So it cannot mint
  tokens. (This is also why the pre-existing `tests/test_rbac.py` tests that POST
  to `/register` and expect 201 FAIL on a clean checkout — a KNOWN pre-existing
  failure, unrelated to this plan; see Task 9.)
- There is no `get_password_hash`; conftest fixtures create users directly with
  `hashed_password="hashed_secret"`.
- The right way to authenticate is `create_access_token(data={"sub": str(user.id)})`
  from `app.utils.security` (the exact helper conftest's `normal_user_token_headers`
  / `admin_token_headers` fixtures use). The `client` fixture overrides `get_db` to
  return THIS test's `db_session`, so a user added (and committed) on `db_session`
  is visible to the endpoint.

```python
@pytest.mark.asyncio
async def test_member_chat_endpoint_returns_reply_for_member(client, db_session, monkeypatch):
    """A TWG_MEMBER hitting /agents/member/chat gets Martin's reply scoped to them."""
    from app.models.models import TWG, TWGPillar, User, UserRole
    from app.utils.security import create_access_token
    from app.agents.agent_loop import AgentResponse
    import app.api.routes.agents as agents_routes

    twg = TWG(id=uuid.uuid4(), name="Energy", pillar=TWGPillar.energy_infrastructure)
    member = User(
        id=uuid.uuid4(), full_name="Member One", email=f"m1_{uuid.uuid4()}@africacen.org",
        hashed_password="hashed_secret", role=UserRole.TWG_MEMBER, is_active=True,
    )
    member.twgs.append(twg)
    db_session.add_all([twg, member])
    await db_session.commit()

    token = create_access_token(data={"sub": str(member.id)})

    async def _fake_run(**kwargs):
        # The endpoint must pass the caller's real id AND role through — never a
        # hardcoded role (FATAL privilege-escalation fix).
        assert kwargs["user_id"] == str(member.id)
        assert kwargs["user_role"] == UserRole.TWG_MEMBER
        assert kwargs["twg_id"] == str(twg.id)
        return AgentResponse(content="Your next meeting is the Energy Sync.", agent_id="member")

    monkeypatch.setattr(agents_routes, "run_member_chat", _fake_run)

    resp = await client.post(
        "/api/v1/agents/member/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"message": "what's next?", "twg_id": str(twg.id)},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["agent_id"] == "member"
    assert "Energy Sync" in body["response"]


@pytest.mark.asyncio
async def test_member_chat_endpoint_rejects_non_member(client, db_session):
    """A facilitator/admin is 403 on the member endpoint — they use the web platform."""
    from app.models.models import User, UserRole
    from app.utils.security import create_access_token

    admin = User(
        id=uuid.uuid4(), full_name="Boss", email=f"boss_{uuid.uuid4()}@africacen.org",
        hashed_password="hashed_secret", role=UserRole.ADMIN, is_active=True,
    )
    db_session.add(admin)
    await db_session.commit()
    token = create_access_token(data={"sub": str(admin.id)})

    resp = await client.post(
        "/api/v1/agents/member/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"message": "hi", "twg_id": str(uuid.uuid4())},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_member_chat_endpoint_requires_twg_id(client, db_session):
    """Missing twg_id returns 400 (member reads are TWG-scoped)."""
    from app.models.models import User, UserRole
    from app.utils.security import create_access_token

    m = User(
        id=uuid.uuid4(), full_name="M2", email=f"m2_{uuid.uuid4()}@africacen.org",
        hashed_password="hashed_secret", role=UserRole.TWG_MEMBER, is_active=True,
    )
    db_session.add(m)
    await db_session.commit()
    token = create_access_token(data={"sub": str(m.id)})

    resp = await client.post(
        "/api/v1/agents/member/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"message": "hi"},
    )
    assert resp.status_code == 400
```

Note: the auth mechanics above are CONFIRMED against `backend/tests/conftest.py`
(the `create_access_token(data={"sub": str(...id)})` token-minting pattern in the
`normal_user_token_headers` / `admin_token_headers` fixtures, and the `client`
fixture's `app.dependency_overrides[get_db] = override_get_db` returning the test
`db_session`) and `backend/app/utils/security.py`
(`def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str`).
Do NOT use the login/register endpoints or `get_password_hash` — neither matches
this codebase.

- [ ] Run and confirm FAIL:

```bash
cd /Users/evan/ravishing-presence/backend && .venv/bin/python -m pytest tests/test_member_chat_endpoint.py -k endpoint -v
```

Expected: 404 (route not registered) → assertions fail.

- [ ] Implement. In `backend/app/api/routes/agents.py`, add a module-level import
next to the other agent import. Anchor on this exact line and add the new import
immediately after it:

```python
from app.agents.supervisor_api_adapter import SupervisorWithTools
```

Add:

```python
from app.agents.member_agent import run_member_chat
```

Then add the endpoint immediately BEFORE the `/chat/enhanced` route. Anchor on
this exact decorator + signature (it is the route that follows `chat_with_martin`)
and insert the new endpoint just BEFORE it:

```python
@router.post("/chat/enhanced", response_model=EnhancedChatResponse)
async def enhanced_chat(
```

It reuses the existing `AgentChatRequest`/`AgentChatResponse` schemas (`schemas.py`;
CONFIRMED `class AgentChatRequest(SchemaBase)` has `message: str`,
`conversation_id: Optional[uuid.UUID]`, `twg_id: Optional[uuid.UUID]`, and
`class AgentChatResponse(SchemaBase)` has `response: str`,
`conversation_id: uuid.UUID`, `citations: List[dict] = []`, `agent_id: str`),
`get_current_active_user` (imported at the top of `agents.py` via
`from app.api.deps import get_current_active_user`), and the module's
`def has_twg_access(user: User, twg_id: uuid.UUID) -> bool` helper (defined in
`agents.py`). `HTTPException`, `Request`, `Depends`, `uuid`, and `User` are all
already imported at the top of `agents.py`.

NOTE on `response_model=AgentChatResponse`: the handler returns a plain dict;
FastAPI coerces it to `AgentChatResponse`. The returned dict supplies `response`
(str), `conversation_id` (a `uuid.UUID`), `citations` (the `AgentResponse.citations`
list, defaults to `[]`), and `agent_id` ("member"). The remaining
`AgentChatResponse` fields (`interrupted`, `interrupt_payload`, `thread_id`,
`suggestions`) all have defaults, so the dict validates cleanly.

Because `AgentChatRequest.twg_id` is typed `Optional[uuid.UUID]`, FastAPI parses
and validates it to a `uuid.UUID` (or rejects with 422) BEFORE the handler runs,
so `chat_in.twg_id` is already a real `uuid.UUID` when passed to `has_twg_access`
(which compares it against `current_user.twg_ids`, a `List[uuid.UUID]`). No manual
UUID coercion is needed.

```python
@router.post("/member/chat", response_model=AgentChatResponse)
async def member_chat(
    chat_in: AgentChatRequest,
    current_user: User = Depends(get_current_active_user),
    request: Request = None,
):
    """Member-only Martin. TWG_MEMBER sessions get exactly the member toolset.

    Facilitators/admins are 403 here — they continue to use the web platform
    (spec §3). twg_id is required because member reads are TWG-scoped.
    """
    from app.models.models import UserRole

    if current_user.role != UserRole.TWG_MEMBER:
        raise HTTPException(
            status_code=403,
            detail="The member assistant is for TWG members. Use the web platform.",
        )

    if not chat_in.twg_id:
        raise HTTPException(status_code=400, detail="twg_id is required for the member assistant.")

    if not has_twg_access(current_user, chat_in.twg_id):
        raise HTTPException(status_code=403, detail="You do not have access to this TWG.")

    conv_id = chat_in.conversation_id or uuid.uuid4()
    user_timezone = request.headers.get("X-User-Timezone") if request else None

    try:
        response = await run_member_chat(
            message=chat_in.message,
            user_id=str(current_user.id),
            user_role=current_user.role,  # real role (asserted TWG_MEMBER above) — never hardcoded
            twg_id=str(chat_in.twg_id),
            thread_id=str(conv_id),
            user_timezone=user_timezone,
        )
        return {
            "response": response.content,
            "conversation_id": conv_id,
            "citations": response.citations,
            "agent_id": "member",
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "response": f"I'm sorry, something went wrong: {str(e)}",
            "conversation_id": conv_id,
            "citations": [],
            "agent_id": "member",
        }
```

- [ ] Run and confirm PASS:

```bash
cd /Users/evan/ravishing-presence/backend && .venv/bin/python -m pytest tests/test_member_chat_endpoint.py -v
```

Expected: all tests pass (runner test + 3 endpoint tests).

- [ ] Commit:

```bash
cd /Users/evan/ravishing-presence && git add backend/app/api/routes/agents.py backend/tests/test_member_chat_endpoint.py && git commit -m "feat(member): POST /agents/member/chat — member-only, twg-checked Martin endpoint

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 9 — Full-suite regression + final verification

**Files:** (none modified)

### Steps

- [ ] Run the complete set of files this plan created/touched, plus the pre-existing registry suite:

```bash
cd /Users/evan/ravishing-presence/backend && .venv/bin/python -m pytest tests/test_member_tool_scope.py tests/test_member_tools.py tests/test_member_chat_endpoint.py tests/test_tool_registry.py -v
```

Expected: all `test_member_*` tests pass; `test_tool_registry.py` shows ONLY the two
known pre-existing failures (`test_supervisor_has_full_access`,
`test_supervisor_gets_all_tools`) and no new ones.

- [ ] Run the broader agent/tool tests to confirm no regression to other agents:

```bash
cd /Users/evan/ravishing-presence/backend && .venv/bin/python -m pytest tests/test_tools_rbac.py tests/test_agent_loop.py -v
```

Expected: all pass.

- [ ] (KNOWN pre-existing failure baseline) `tests/test_rbac.py` POSTs to the
DISABLED `/api/v1/auth/register` endpoint and expects 201/created — those tests
FAIL on a CLEAN checkout, independent of this work. Confirm the baseline BEFORE
attributing anything to this change by stashing and running on a clean tree:

```bash
cd /Users/evan/ravishing-presence && git stash && \
  backend/.venv/bin/python -m pytest backend/tests/test_rbac.py -v ; \
  git stash pop
```

Expected: the same register-based failures appear with and without this branch
(i.e. this plan introduces NO new failures in `test_rbac.py`). Do NOT "fix" those
tests as part of this plan — they are out of scope.

- [ ] Verify the safety line end-to-end with a single focused assertion run
(member blocked from facilitator/admin tools; non-members blocked from the member
endpoint; and identity cannot be forged through a tool call):

```bash
cd /Users/evan/ravishing-presence/backend && .venv/bin/python -m pytest \
  tests/test_member_tool_scope.py::test_member_denied_facilitator_and_admin_tools \
  tests/test_member_chat_endpoint.py::test_member_chat_endpoint_rejects_non_member \
  tests/test_member_tools.py::test_member_tool_schemas_exclude_identity_params \
  tests/test_member_tools.py::test_injected_member_identity_wins_over_llm_args -v
```

Expected: 4 passed — proves (1) a member is blocked from facilitator/admin tools,
(2) non-members are blocked from the member endpoint, (3) the LLM-visible member
tool schemas expose no identity params, and (4) the injected member identity is
what tools actually write.

- [ ] No commit (verification only). The branch `feat/backend-member-martin` is ready for PR.

---

## Scope notes & deliberately deferred (resolving spec-gap questions)

These are decisions made for THIS plan; they are out of scope for the tasks
above but recorded so reviewers know they were considered (grounded in the spec
at `docs/superpowers/specs/2026-06-08-member-mobile-app-design.md`):

- **Error messages never name facilitator tools.** The member endpoint's
  fallback (`except Exception`) returns a generic `"I'm sorry, something went
  wrong: ..."` string and `MEMBER_SYSTEM_PROMPT` is instructed to redirect
  unsupported requests with "that is handled by your facilitator on the web
  platform" — it does NOT enumerate facilitator/admin tool names. The registry
  `ToolAccessDenied` messages (e.g. "not part of the member toolset") are raised
  server-side and skipped silently by `get_tools_for_agent`; they are never
  surfaced to the member as suggestions.

- **Direct-API bypass is covered at the registry layer, not just the endpoint.**
  Even if a caller forged a request past the endpoint role check, a member
  session resolves tools through `ToolRegistry.validate_tool_access(... "member"
  ...)`, which raises `ToolAccessDenied` for `create_meeting` et al.
  (`test_member_denied_facilitator_and_admin_tools`). Identity-forgery through a
  tool call is now covered too: the member tool schemas exclude `user_id`/
  `user_role` (registry-asserted), and `test_injected_member_identity_wins_over_llm_args`
  drives the REAL `AgentLoop._execute_tools` to prove the injected member identity
  is what gets written. The registry-level + injection proofs are sufficient for the
  safety line in this plan.

- **Reminder retention/TTL is out of scope for Phase 1.** The `Reminder` row has
  `is_sent: bool` for a future "send and mark sent" sweep, but no auto-delete /
  TTL policy is defined here. Retention is a Phase-2 concern (spec §10/§11
  defer richer push + lifecycle); old reminders simply persist for now.

- **FCM / push-token registration is separate backend work (spec §9), not this
  plan.** Spec §7 scopes new backend work to "push (see §9) and confirming/
  defining the member tool scope" — this plan delivers ONLY the tool scope +
  member endpoint. The Phase-1 push trigger (meeting reminder ~30 min before;
  device-token storage + send) is a distinct task and is intentionally not
  built into `member_agent.py`.

- **"Add a meeting to my calendar" (spec §6) is a CLIENT-side device-calendar
  action, not a Martin tool.** The mobile app adds the meeting to the device
  calendar from the meeting data Martin already returns (`get_schedule`); there
  is no server tool for it. The only personal write tools this plan adds are
  `rsvp_meeting`, `set_reminder`, `get_notifications` — matching the "set my own
  reminders / nudges" half of §6.

---

## Done criteria (maps to spec §13)

- A member session (`agent_id="member"`) is granted EXACTLY `MEMBER_TOOLS ∩ registered tools` — proven by `test_member_granted_only_allowlisted_registered_tools`.
- Calling any facilitator/admin tool (e.g. `create_meeting`, `send_email`) as a member raises `ToolAccessDenied`, and NO tool from the FULL blocked union (`BLOCKED_FOR_MEMBER | WHATSAPP_TOOL_NAMES | SUPERVISOR_ONLY_TOOLS | DEAL_PIPELINE_TOOLS | PIPELINE_WRITE_TOOLS | PIPELINE_READ_TOOLS`) leaks into a member session — proven by `test_member_denied_facilitator_and_admin_tools` and `test_member_denied_blocked_tools_appear_in_no_session`.
- WhatsApp tools (`send_whatsapp_message`, `send_whatsapp_to_group`, `list_whatsapp_groups`, `check_whatsapp_number`) are denied to members as a plan-level interpretation of spec §6 *Never exposed* (broadcasts / invite people) + §29 (no outward communication), and the test imports `WHATSAPP_TOOL_NAMES` from `whatsapp_tools.py` so it can never drift from the real names — proven by the dedicated `test_member_denied_whatsapp_tools`.
- Member personal-action tools (`rsvp_meeting`, `set_reminder`, `get_notifications`) work, are role-gated as defense-in-depth (refusing a forged/unknown role), and touch only the caller's own rows — proven by `test_member_tools.py`.
- A member CANNOT escalate by forging identity in a tool call: the LLM-visible member tool schemas expose no `user_id`/`user_role`, the registry asserts this at registration, and the injected member identity (not any LLM-supplied value) is what tools write — proven by `test_member_tool_schemas_exclude_identity_params` and `test_injected_member_identity_wins_over_llm_args`.
- The member chat endpoint requires an authenticated `TWG_MEMBER`, asserts the role (403 for any other role) BEFORE running, passes the caller's real `user_id` AND `user_role` through (never hardcoded), rejects missing twg_id (400), and returns Martin's reply scoped to the member — proven by `test_member_chat_endpoint.py`.
- No regression to supervisor / TWG / resource_mobilization scopes — proven by the unchanged `test_tool_registry.py` passing (run together with the new scope suite in Task 2).
