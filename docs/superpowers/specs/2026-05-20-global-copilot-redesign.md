# Martin Global Copilot — Design Spec
**Date:** 2026-05-20  
**Status:** Approved for implementation  
**Scope:** Full execution copilot — Meetings (A), Documents (B), Action Items (C)  
**Deferred:** Communications (D), Pipeline (E) — see memory/project_copilot_backlog.md

---

## 1. Goals

Transform the per-workspace `CopilotChat` component into a single, globally accessible Martin Copilot panel that:

1. Is available on every page via a persistent toggle in the nav bar
2. Derives TWG context automatically from the current route and user role
3. Shows every tool call and agent step visibly (fully transparent execution)
4. Executes real actions (schedule meetings, create action items, draft documents) with a confirm-before-execute flow for high-stakes operations
5. Offers slash commands and context-aware suggested action chips
6. Respects role-based access — admins see cross-TWG supervisor, members see only their TWGs

---

## 2. Architecture

### 2.1 Panel Location

The copilot moves from `TwgWorkspace.tsx` into `ModernLayout.tsx` as a persistent right panel.

```
ModernLayout
├── NavSidebar (210px, existing)
├── Main Content (flex-1, all existing pages unchanged)
└── GlobalCopilot (380px, collapsible, new)
```

Toggle state persisted in `localStorage` key `copilot_open`. Default: open on workspace pages, closed elsewhere.

The per-workspace `CopilotChat` component and its expansion logic are removed from `TwgWorkspace.tsx`. The right-panel width adjustment in that file is also removed.

### 2.2 New File Structure

```
frontend/src/components/copilot/
├── GlobalCopilot.tsx          # Main orchestrator (replaces CopilotChat.tsx)
├── CopilotHeader.tsx          # Avatar, status, TWG selector, controls
├── SuggestedActions.tsx       # Context-aware chip bar
├── CopilotMessageList.tsx     # Message + tool step rendering
├── ToolStepRow.tsx            # Single collapsible tool execution row
├── ActionConfirmCard.tsx      # Structured confirm/edit/cancel card
├── SlashCommandPalette.tsx    # /command floating menu
└── CopilotInput.tsx           # Input bar (preserves @mention logic)
```

`useAgentStream.ts` is unchanged — it is the transport layer.

### 2.3 Context Resolution

Priority order for determining which TWG the copilot operates on:

| Condition | Context used |
|-----------|-------------|
| URL matches `/workspace/:twgId` | That TWG ID, silent |
| User has exactly 1 TWG membership | Their TWG, silent |
| User has multiple TWG memberships | TWG selector shown in header |
| User is Admin or Secretariat Lead | Full supervisor, optional TWG filter |

The resolved `twgId` (or `undefined` for admin global mode) is passed to `sendMessage` in `useAgentStream` as it is today.

---

## 3. UI Components

### 3.1 CopilotHeader

- **Left**: Blue `✦` avatar (24px), "Martin" label, context chip showing active TWG name with `▾` dropdown if multiple TWGs or admin
- **Right**: Green pulsing status dot + "Live" label, collapse button `[✕]`, clear history button
- TWG selector dropdown (when applicable): lists only the user's TWGs; admins see all TWGs plus "All TWGs (Supervisor mode)"

### 3.2 SuggestedActions

Four chips rendered below the header. Chips are derived from `SUGGESTED_ACTIONS` map keyed by route pattern:

| Route | Chips |
|-------|-------|
| `/workspace/:id` | 📅 Draft agenda · 🗓 Schedule · 📋 Summarize docs · ✅ Add action |
| `/meetings` | 🗓 Schedule meeting · 📝 Draft minutes · ⚠️ Check conflicts |
| `/documents` | 📄 Summarize · ✍️ Draft brief · 🔍 Search by topic |
| `*` (default) | 💬 Ask a question · 📝 Draft report · 📅 Check schedule · ✅ Add task |

Clicking a chip pre-fills the input with a natural language template and focuses the input. The user completes any `[placeholder]` values and presses Enter to send. Chips with no placeholders (e.g. "Summarize docs") submit immediately.

### 3.3 CopilotMessageList

Renders three distinct row types in chronological order:

**Tool Step Rows** (from `routing`, `agent`, `tool_call`, `tool_result` events):
- Compact single-line row: `[icon] Label · Xms [▾] [✓|spinner]`
- Icons: 🔍 routing, ⚡ agent, 🗄️ tool_call, ✅ tool_result
- Click to expand → monospace block showing args (tool_call) or result preview (tool_result, truncated to 300 chars)
- Grouped under a collapsible "X steps" summary header after the stream completes

**Message Bubbles** (from `token`/`done` events):
- User: right-aligned blue bubble (unchanged from current)
- Agent: left-aligned, glass-card styling, ReactMarkdown rendered (unchanged)

**Action Confirm Cards** (from `action_required` event):
- Rendered inline in the message list where the event arrived
- See Section 3.4

### 3.4 ActionConfirmCard

Rendered when the backend emits an `action_required` event. Structure:

```
┌─────────────────────────────────────────┐
│ 📅 SCHEDULE MEETING              [card] │
│ ──────────────────────────────────────  │
│ Title:    Energy TWG Alignment          │
│ Date:     Thu 22 May 2026 · 09:00       │
│ Duration: 60 minutes                    │
│ TWG:      Energy Trade & Industrial     │
│ Invitees: 8 members                     │
│ ──────────────────────────────────────  │
│  [✓ Confirm]   [✎ Edit]   [✕ Cancel]  │
└─────────────────────────────────────────┘
```

- **Confirm**: POSTs to `/api/v1/agents/execute` with `{ action_id, confirmed: true }`. Card transitions to a success state ("✓ Meeting scheduled").
- **Edit**: Expands inline form fields within the card. User edits values, then Confirms with `{ action_id, confirmed: true, edits: {...} }`.
- **Cancel**: POSTs `{ action_id, confirmed: false }`. Card shows "Cancelled" state. No action taken.
- Cards expire after 10 minutes (TTL matches backend action store). Expired cards show "This action has expired."

**Action types and their card fields:**

| Type | Fields shown |
|------|-------------|
| `schedule_meeting` | title, date, duration, TWG, invitee count |
| `create_action_item` | title, assignee, due date, TWG, priority |
| `draft_document` | title, type, TWG — shows preview of draft text |

`draft_document` is low-stakes: the card shows the draft and a "Save to Library" button, no confirm gate required.

### 3.5 SlashCommandPalette

Triggers when input starts with `/`. Floating panel above the input:

| Command | Description | Template inserted |
|---------|-------------|-------------------|
| `/schedule` | Schedule a TWG meeting | `Schedule a meeting for [topic] on [date] at [time]` |
| `/draft` | Draft meeting minutes | `Draft minutes for the [TWG] meeting on [date]` |
| `/action` | Create an action item | `Create an action item: [task] assigned to [person] due [date]` |
| `/summarize` | Summarize recent activity | `Summarize the last [N] meetings for [TWG]` |
| `/search` | Search documents | `Search documents for [topic]` |
| `/agenda` | Generate meeting agenda | `Generate an agenda for [TWG] meeting on [date]` |

Arrow keys navigate, Enter selects, Escape dismisses. Typing after `/` filters live.

### 3.6 CopilotInput

- Single-line input, `⌘+Enter` or `Enter` to send
- Send button `→` (disabled while streaming)
- Cancel button `■` (shown only while streaming, calls `useAgentStream.cancel()`)
- `@` triggers existing TWG mention popup (logic preserved from current implementation)
- `/` triggers SlashCommandPalette

---

## 4. Backend Changes

### 4.1 New SSE Event: `action_required`

Added to `StreamEventType` in both backend and `useAgentStream.ts`:

```typescript
export interface ActionRequiredEvent {
    type: 'action_required';
    action_id: string;           // short UUID, TTL 10min in backend store
    action_type: 'schedule_meeting' | 'create_action_item' | 'draft_document';
    payload: Record<string, unknown>;  // action-specific fields
    confirm_endpoint: string;    // always "/api/v1/agents/execute"
}
```

The LangGraph supervisor emits this event when it resolves a meeting/action/document intent during its tool execution phase, before the final `done` event.

### 4.2 New Endpoint: `POST /api/v1/agents/execute`

```python
class ExecuteActionRequest(BaseModel):
    action_id: str
    confirmed: bool
    edits: dict = {}

POST /api/v1/agents/execute
→ 200: { "success": true, "resource_id": "...", "message": "Meeting scheduled." }
→ 400: { "detail": "Action expired or not found" }
→ 403: { "detail": "Action does not belong to this user" }
```

**Backend action store** — module-level dict in `agents.py`:
```python
_pending_actions: dict[str, dict] = {}  # action_id → {payload, user_id, expires_at}
```
Entries expire after 10 minutes. No Redis or DB required.

**Execution handlers** per action type:
- `schedule_meeting` → calls existing `meetings` service (`create_meeting`)
- `create_action_item` → calls existing `action_items` service
- `draft_document` → saves to documents with status `draft`

### 4.3 Agent Intent Detection

In `langgraph_supervisor.py`, add an intent classification step after tool results are collected. If the resolved intent maps to a known action type and sufficient data was extracted, emit `action_required` instead of immediately executing.

The supervisor's system prompt is updated with a section explaining when to propose vs. execute directly.

---

## 5. Access Control

| Role | Copilot behaviour |
|------|------------------|
| ADMIN / SECRETARIAT_LEAD | Full supervisor agent. TWG selector shows all TWGs + "Supervisor mode". |
| FACILITATOR | Scoped to their assigned TWGs. Selector shows assigned TWGs only. |
| MEMBER (1 TWG) | Scoped silently to their TWG. No selector shown. |
| MEMBER (multi-TWG) | TWG selector shows their TWGs. Must select one before first message. |

The `twg_id` access check on `POST /agents/execute` verifies the user is a member or admin of the target TWG before executing any action.

---

## 6. Files Changed Summary

**Frontend:**
- `src/layouts/ModernLayout.tsx` — add `GlobalCopilot` panel + toggle button in navbar
- `src/pages/workspace/TwgWorkspace.tsx` — remove `CopilotChat`, remove expansion state
- `src/components/workspace/CopilotChat.tsx` — deleted (replaced)
- `src/components/copilot/` — all new files (7 components listed in §2.2)
- `src/hooks/useAgentStream.ts` — add `ActionRequiredEvent` type only

**Backend:**
- `app/api/routes/agents.py` — add `POST /agents/execute`, add `_pending_actions` store, emit `action_required` from stream
- `app/agents/langgraph_supervisor.py` — add intent classification + `action_required` emission
- `app/agents/prompts/supervisor.txt` — update with propose-vs-execute instructions

---

## 7. Out of Scope (This Version)

- Communications: email blast / broadcast notifications (Phase 2)
- Pipeline: project status updates from copilot (Phase 2)
- Copilot history persistence across sessions (future)
- Mobile / responsive layout for copilot panel (future)
- Voice input (future)
