# Martin Copilot — Platform Knowledge & Proactive Briefing

**Date:** 2026-05-21  
**Status:** Approved

---

## Problem

Martin currently has no knowledge of the platform he lives in. He can answer general questions and call backend tools, but he cannot guide a user through navigation, explain what a page does, or tell someone how to advance a project through stages. When the copilot opens, the chat is empty — there is no opening context, no awareness of what needs attention, and no reason to engage.

---

## Goals

1. Martin knows the platform well enough to guide any user through any page or task.
2. When the copilot opens, Martin greets the user with a live briefing — what's coming up, what needs attention, what's below threshold.
3. Suggested action chips are driven by the briefing rather than hardcoded.

---

## Architecture

### A — Platform Knowledge (prompt enrichment)

Platform knowledge lives in `backend/app/agents/prompts/platform_guide.txt`. This file is loaded at supervisor initialisation and appended to the supervisor's system message as a `[PLATFORM GUIDE]` block — after existing instructions, not replacing them.

The guide covers:

- **Pages**: Dashboard, Deal Pipeline, TWG Workspace, Schedule, Documents, Notifications, Profile — what each does, who uses it, what actions are available
- **Navigation patterns**: how to get from A to B, how filters work, how to advance a project through lifecycle stages
- **Common tasks by role**: admin/secretariat vs TWG focal point vs TWG member
- **Key concepts**: WAIIS scoring criteria and weights, gender/youth stage gate (30% / 25% thresholds), Summit Readiness definition, Readiness Track (Stage 0), TWG structure and membership

The file is ~2,000–3,000 tokens. Anthropic caches system prompts above 1,024 tokens, so after the first message in a session the guide adds negligible latency.

**File:** `backend/app/agents/prompts/platform_guide.txt`  
**Loaded in:** `backend/app/agents/langgraph_supervisor.py` (system message construction)

---

### B — Briefing Endpoint (backend)

New route: `GET /api/martin/briefing`  
Auth-required. Returns in <300ms — pure DB reads, no agent pipeline involved.

**Role-aware queries:**

| Data | Admin / Secretariat Lead | TWG Member |
|---|---|---|
| Upcoming meetings (today + tomorrow) | All TWGs | Their TWG only |
| Projects below gender/youth threshold | All projects | Their TWG's projects |
| Overdue notifications (unread, created >48h ago) | All | Assigned to them |
| Projects with `readiness_score IS NULL` (never scored) | All | Their TWG |

**Response schema:**
```json
{
  "greeting": "Good morning",
  "upcoming_meetings": [
    { "title": "TWG Energy", "twg_name": "Energy", "starts_at": "2026-05-21T10:00:00Z", "minutes_until": 60 }
  ],
  "threshold_alerts": [
    { "project_name": "Sahel Solar", "gap_type": "gender", "current_pct": 18.0, "required_pct": 30.0 }
  ],
  "overdue_items": [
    { "title": "Review investment memo", "days_overdue": 5 }
  ]
}
```

All keys are always present; empty sections return `[]`. If all three arrays are empty, the frontend renders: "Things look good — nothing urgent today."

**File:** `backend/app/api/routes/martin.py` (new file)  
**Registered in:** `backend/app/main.py`

---

### C — Frontend Integration

**Opening briefing bubble (`GlobalCopilot.tsx`):**

On mount, `GlobalCopilot` calls `/api/martin/briefing`. While fetching, the existing pulsing ✦ + bouncing dots animation shows. On response, the briefing is injected as `localMessages[0]` — a synthetic `agent` message formatted from the JSON. It renders exactly like any other Martin response.

Briefing message format (assembled on the frontend from the JSON):
```
Good morning. A few things for your attention:

⚠️ **2 projects** are below the gender employment threshold
📅 **TWG Energy meeting** in 1 hour (10:00 AM)  
📋 **3 action items** overdue — oldest is 5 days

What would you like to tackle first?
```

The briefing is not sent to the agent — it does not enter conversation history. It is display-only. If the user asks a follow-up about something in the briefing ("show me those projects"), that message goes through the normal agent pipeline.

**Dynamic suggested actions (`SuggestedActions.tsx`):**

`SuggestedActions` receives the briefing JSON as a prop and generates chips from it:

| Briefing signal | Chip |
|---|---|
| `threshold_alerts` present | "Fix gender gaps" (red) |
| `upcoming_meetings` with `minutes_until < 120` | "Prep for meeting" (blue) |
| `overdue_items` present | "Review action items" (amber) |
| Briefing empty | "What's on today?", "Show my projects", "Help me navigate" (grey) |

**Briefing refresh:**
Fetched once per copilot open. Re-fetches if the user closes and reopens. No timer, no per-navigation refetch.

---

## Out of Scope

- Martin proactively pushing notifications outside the copilot panel
- A help-lookup tool for Martin to call at query time (Option C from brainstorm — deferred)
- Editing the platform guide via UI (file-based for now)
- Briefing for the page-aware greeting (Option C from greeting brainstorm — deferred)

---

## Files Changed

| File | Change |
|---|---|
| `backend/app/agents/prompts/platform_guide.txt` | NEW — full platform knowledge base |
| `backend/app/agents/langgraph_supervisor.py` | Load and append platform guide to system message |
| `backend/app/api/routes/martin.py` | NEW — `GET /martin/briefing` endpoint |
| `backend/app/main.py` | Register martin router |
| `frontend/src/components/copilot/GlobalCopilot.tsx` | Fetch briefing on mount, inject as first message |
| `frontend/src/components/copilot/SuggestedActions.tsx` | Accept briefing prop, generate dynamic chips |

---

## Success Criteria

- Martin can answer "how do I advance a project to Summit Ready?" with accurate step-by-step guidance
- Martin can answer "what does the Deal Pipeline page do?" without calling any tools
- Copilot opens with a role-correct briefing in <500ms
- Suggested chips reflect the user's actual current priorities
- No change to agent response latency after the first message in a session
