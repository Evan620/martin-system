# Martin Deal-Pipeline Tools — Design

_Date: 2026-05-28_

## Problem

The Martin copilot can answer questions about the deal pipeline but cannot
**do** anything to it. Today (per audit of `backend/app/tools/`) Martin has
five pipeline tools — all read-only or compute-only:

- `get_project_details`, `list_flagship_projects`, `analyze_project_documents`,
  `generate_investment_memo`, `trigger_investor_matching`.

There are no tools for: advance stage, decline, mark flagship, rescore,
graduate from incubation, archive, create/edit project, create/assign action
items, assign a matched investor, schedule a follow-up meeting from a match,
approve minutes, send/resend/revoke invitations, change scoring weights, or
pull cross-cutting reads like "pipeline summary" or "my action items."

Two structural constraints to fix at the same time:

1. **Role gating** today happens at the agent-id layer
   (`tool_registry.py` SUPERVISOR_ONLY / TWG_SCOPED / DEAL_PIPELINE_TOOLS lists).
   It does not see the calling user's role. New write tools must be gated by
   `current_user.role` to mirror the UI's RBAC.
2. **Audit** of agent-driven writes does not exist as a category. Every new
   write must record `actor = "Martin"` plus `acted_on_behalf_of = user.id`.

## Goal

Give Martin a focused set of write tools that mirror the deal-pipeline actions
already available in the UI, gated by the same RBAC, behind a single
**confirm-then-execute** protocol so high-impact writes always show a
confirmation card in the chat before they run. Ship in three tiers; tier 1
covers ~80% of expected prompts.

## Design

### 1. The confirm-then-execute protocol

Every write tool returns one of two shapes:

```jsonc
// Pending confirmation (first call, no confirmation token)
{
  "status": "confirmation_required",
  "action_id": "act_a1b2c3",          // server-generated, opaque
  "summary": "Advance \"Northern Nigeria Staple Crop Corridor\" to Summit Ready.",
  "details": { "project_id": "...", "from": "DRAFT", "to": "SUMMIT_READY" },
  "irreversible": false                // hint for UI styling
}

// Executed (second call, with confirmation token)
{ "status": "ok", "result": { ... } }
```

- First call: tool validates inputs + role, then returns
  `confirmation_required` with a server-issued `action_id` (stored in Redis
  with 10-minute TTL and the bound arguments).
- Frontend renders a confirm card inline in the chat (`Confirm` / `Cancel`).
- On `Confirm`, the frontend re-invokes the tool with the same arguments **plus**
  `confirmed=True` and the `action_id`. Tool verifies the `action_id` exists,
  un-spent, and the bound args match; then executes, marks the `action_id`
  spent, and returns `ok`.
- Idempotent: a duplicate confirm with the same `action_id` returns the cached
  result instead of running twice.

Read-only tools (e.g. `pipeline_summary`, `my_action_items`, `at_risk_projects`,
`next_deadlines`, `incubation_close_to_graduation`) **do not** use the confirm
protocol — they return data directly. The protocol is for writes only. A
future option to auto-confirm low-impact writes based on a user preference is
out of scope; in v1 every write shows the confirm card.

### 2. Role gating

A new helper `require_role(user, allowed: list[UserRole])` lives in
`backend/app/tools/_rbac.py` and is called at the top of every write tool.
The user's role flows in via the dispatcher already: `agents.py` already pulls
`current_user`; we extend the kwargs passed to each tool call with
`user_id` and `user_role`. Mirror groups from the frontend:

- `EDIT_ROLES = {ADMIN, SECRETARIAT_LEAD, FACILITATOR}` — project edits, stage
  moves up to Summit Ready, action items.
- `INVESTOR_ROLES = {ADMIN, SECRETARIAT_LEAD}` — flagship, investor/buyer/DFI
  assignment, scoring weights, decline, advance past Summit Ready.
- `SECRETARIAT_ONLY = {ADMIN, SECRETARIAT_LEAD}` — approve minutes, override
  scores, archive.

If the user lacks the role, the tool returns
`{ "status": "forbidden", "reason": "Requires SECRETARIAT_LEAD" }` and never
issues an `action_id`.

### 3. Audit trail

Every write writes one row to `project_status_history` (for stage moves) or a
new generic `agent_audit_log` table for non-stage writes:

```
agent_audit_log(
  id, created_at, user_id, user_role, action_id, tool_name,
  target_type, target_id, before_json, after_json, summary
)
```

`actor = "Martin"` is implicit (table name). One row per executed write.

### 4. Tool catalogue (tier 1 — ship first)

All tools below register against the supervisor agent (the one the global
chat uses) so any role can call them, with `require_role` checking the gate.

| Tool | Role | Notes |
|---|---|---|
| `advance_project_stage(project_id, target_stage, notes?)` | EDIT_ROLES for moves up to SUMMIT_READY; INVESTOR_ROLES beyond | Writes `project_status_history` |
| `decline_project(project_id, reason)` | INVESTOR_ROLES | Sets status = DECLINED |
| `mark_flagship(project_id, is_flagship)` | INVESTOR_ROLES | Toggles `is_flagship` |
| `rescore_project(project_id)` | EDIT_ROLES | Re-runs WAIIS scoring against current data |
| `graduate_from_incubation(project_id)` | EDIT_ROLES | Verifies AfCEN ≥ threshold, then `advance_project_stage` to DRAFT |
| `create_action_item({project_id?, meeting_id?, description, owner_user_id?, due_date, priority})` | EDIT_ROLES | Returns the new item id |
| `bulk_create_action_items(meeting_id, items[])` | EDIT_ROLES | Common minutes-extraction flow |
| `pipeline_summary(scope='all'|'twg'|'mine', period='week'|'month')` | none (TWG-scoped if scope='twg' or 'mine') | Read-only; totals by stage, deltas, value, top movers, projects-at-risk count |
| `at_risk_projects()` | none (TWG-scoped) | Pending AI review > 3d, gender/youth gaps, no recent meeting > 30d |
| `incubation_close_to_graduation()` | none (TWG-scoped) | AfCEN ≥ threshold − 5 |
| `my_action_items(status?)` | any role | The currently missing "what's mine" view |
| `next_deadlines(window='7d')` | any role | Meetings + action-item due dates |

### 5. Tier-2 catalogue (next round)

- `override_score(project_id, field, value, justification)` — SECRETARIAT_ONLY,
  audited verbatim.
- `archive_project(project_id, reason)` — SECRETARIAT_ONLY.
- `create_project_draft({name, pillar, lead_country, investment_size, sector_details?})` — EDIT_ROLES.
- `update_project_field(project_id, field, value)` — EDIT_ROLES; `field` must be in an allow-list (description, project_sponsor, climate_impact, esg_compliance, financing_structure, lead_country, lead_company, subsector).
- `set_sector_details(project_id, details)` — EDIT_ROLES.
- `assign_match(project_id, counterparty_id, counterparty_type, status='proposed')` — INVESTOR_ROLES.
- `start_negotiation(project_id, investor_id)` — already exists as
  `start_negotiation_tool` (supervisor-only); rebind to INVESTOR_ROLES and expose in this catalogue.
- `schedule_match_meeting(project_id, counterparty_id, when, attendees[])` — EDIT_ROLES; chains to existing meeting-create tool.

### 6. Tier-3 catalogue (later)

- `submit_minutes_for_approval(meeting_id)` — EDIT_ROLES.
- `approve_minutes(meeting_id)` — SECRETARIAT_ONLY.
- `send_invitations(meeting_id, mode='email'|'calendar_only')`,
  `resend_invitation(invitation_id)`, `revoke_invitation(invitation_id)` —
  EDIT_ROLES.
- `get_scoring_weights()` / `update_scoring_weights(weights)` —
  SECRETARIAT_ONLY, audited verbatim, confirm-then-execute.

### 7. Frontend changes

- `GlobalCopilot.tsx` / `MessageList`: recognise messages with
  `{ status: "confirmation_required" }` and render a confirm card inline with
  `Confirm` and `Cancel` buttons plus the `summary` text. Confirm dispatches
  the same tool call with `confirmed: true` + `action_id`.
- `Forbidden` status renders a small inline note ("Requires Secretariat Lead")
  rather than a card.

### 8. Backend wiring

- Extend `/agents/chat` dispatcher to include `user_id`, `user_role` in the
  agent context. Every new tool reads them via the standard agent-context
  injection.
- `_rbac.py` exports `require_role`, the role group constants, and a small
  `pending_action` Redis helper (`reserve_action_id`, `consume_action_id`).
- New tools registered under a `pipeline_write_tools` module, added to the
  ToolRegistry the same way `deal_pipeline_tools` are today.
- New table `agent_audit_log` via Alembic migration (idempotent ADD COLUMN /
  CREATE TABLE pattern per the project's recently-fixed migration convention).

## Out of scope

- Tier 2 and Tier 3 are documented for context but **not implemented** in the
  first plan. They get their own specs/plans when prioritised.
- Auto-confirm based on user preference (always show card in v1).
- Multi-step "workflows" (e.g. "advance and notify investors") — caller can
  chain individual tool calls; we don't build composite tools yet.
- Anything mutating Investor / DFI / Buyer master records — the catalogue
  only assigns existing ones to projects.

## Risks & mitigations

| Risk | Mitigation |
|---|---|
| Confirm card stale (user confirms a 2-hour-old proposal) | 10-minute Redis TTL on `action_id`; expired token returns `expired`, UI prompts re-issue. |
| Same user double-clicks Confirm | `action_id` marked spent on first execute; second call returns cached result. |
| Tool reads `user_role` from a stale session | Re-resolve role from DB inside `require_role` before gating (cheap; one query). |
| Agent hallucinates a project_id | Every tool validates the id exists + the caller has TWG access before issuing an `action_id`. |
| Audit row missing on partial failure | Wrap execute + audit-write in one DB transaction. |
| Tools accidentally exposed to wrong agent | New tools register under a single `PIPELINE_WRITE_TOOLS` group in `tool_registry`, only added to supervisor's allowed set. |
