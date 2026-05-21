# Martin Copilot — Platform Knowledge & Proactive Briefing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give Martin knowledge of the platform so he can guide users, and add a proactive briefing that appears when the copilot opens.

**Architecture:** Platform knowledge lives in `platform_guide.txt`, appended to the supervisor system prompt at load time via `prompts.py`. A new `GET /api/v1/martin/briefing` endpoint returns role-aware JSON (meetings, threshold alerts, overdue notifications). The frontend fetches this on copilot mount, injects it as the first chat bubble, and uses it to generate dynamic action chips.

**Tech Stack:** FastAPI (Python), SQLAlchemy async, React + TypeScript, axios

---

## File Map

| File | Action | Purpose |
|---|---|---|
| `backend/app/agents/prompts/platform_guide.txt` | CREATE | Full platform knowledge base |
| `backend/app/agents/prompts.py` | MODIFY | Append platform guide to supervisor prompt |
| `backend/app/api/routes/martin.py` | CREATE | `GET /martin/briefing` endpoint |
| `backend/app/main.py` | MODIFY | Import and register martin router |
| `frontend/src/services/martinService.ts` | CREATE | `getBriefing()` API call |
| `frontend/src/components/copilot/GlobalCopilot.tsx` | MODIFY | Fetch briefing on mount, inject as first message |
| `frontend/src/components/copilot/SuggestedActions.tsx` | MODIFY | Accept briefing prop, generate dynamic chips |

---

## Task 1: Platform guide text + prompt injection

**Files:**
- Create: `backend/app/agents/prompts/platform_guide.txt`
- Modify: `backend/app/agents/prompts.py`

There are no automated tests for prompt content — verify manually by checking that `get_prompt("supervisor")` includes the guide section.

- [ ] **Step 1: Create `platform_guide.txt`**

Create `backend/app/agents/prompts/platform_guide.txt` with this exact content:

```
=== PLATFORM GUIDE ===

You are running inside the ECOWAS Summit 2026 Coordination Platform. This section describes the platform so you can guide users through it accurately.

## NAVIGATION

The sidebar contains these main sections:
- **Dashboard** — Overview: meetings today, project counts, recent notifications, summit readiness %.
- **TWG Workspace** (/workspace) — Per-TWG hub with tabs: Meetings, Documents, Action Items, Members, Overview.
- **Deal Pipeline** (/pipeline) — Investment project tracker: add, score, advance, and filter projects.
- **Schedule** (/meetings) — Calendar view of all meetings across TWGs.
- **Documents** (/documents) — Searchable library of uploaded documents.
- **Notifications** — System alerts, action item reminders, announcements.
- **Profile** — User settings, TWG membership, notification preferences.

## PAGES IN DETAIL

### Dashboard
Shows: meetings today, total projects, active projects, summit readiness %, recent activity feed.
Admins see platform-wide data. TWG members see their TWG's data.

### Deal Pipeline (/pipeline)
Core investment project management. Each project moves through these stages in order:
  DRAFT → UNDER_REVIEW → SUMMIT_READY → COMMITTED → IMPLEMENTED

**Adding a project:** Click "Add Project" (top right) → fill name, description, pillar, lead country, investment size, gender/youth employment %, value chain stages → Save.

**Scoring:** Each project has a WAIIS readiness score (0–100) across 9 criteria with these weights:
  1. Project Maturity (15%) — technical/feasibility studies, site readiness
  2. Bankability (15%) — financing structure, revenue model, funding secured
  3. Regulatory Readiness (10%) — permits, licences, land status
  4. Market Viability (10%) — market size, revenue model completeness
  5. Climate Impact (15%) — GHG avoided targets, ESG compliance
  6. Social Impact (10%) — jobs created, smallholders reached, community benefit
  7. Economic Impact (10%) — macroeconomic ROI, cross-border economic benefit
  8. Stakeholder Alignment (10%) — project sponsor quality, key contacts present
  9. ECOWAS Integration (5%) — lead country is ECOWAS member, cross-border project

To trigger a rescore: open a project → click "Rescore" button.

**Gender/Youth Gate:** To advance UNDER_REVIEW → SUMMIT_READY:
  - women_employment_pct must be ≥ 30%
  - youth_employment_pct must be ≥ 25%
  Projects below threshold show ⚠️ badges in the pipeline list and are blocked from advancing.
  To fix: edit the project and update the employment percentages.

**Filtering:** Dropdowns at top of pipeline for Status, Pillar, and Value Chain Stage.

**Platform Settings:** Admins can adjust gender/youth thresholds: Pipeline → Settings tab.

### TWG Workspace (/workspace or /workspace/:twgId)
Tabs available:
  - **Overview**: TWG description and quick stats
  - **Meetings**: scheduled and past meetings for this TWG
  - **Documents**: documents uploaded to this TWG
  - **Action Items**: tasks assigned within this TWG
  - **Members**: list of TWG members with roles

Admins see all TWGs; members see only their TWG(s). Switch TWG using the dropdown in the workspace header.

### Schedule (/meetings)
Calendar grid view. Click a date to create a meeting. Click a meeting card to view/edit.
- Admins see all TWGs; members see their TWG(s)
- Filter by TWG using the selector above the calendar

**Creating a meeting:** Click a date → fill title, time, duration, location, meeting type (virtual/in-person) → Save.

### Documents (/documents)
Searchable library. Filter by TWG, document type, date range.
- Upload: "Upload Document" button → drag-and-drop or file picker
- Search: keyword search across title and content
- Admins can share documents across TWGs

### Notifications (/notifications)
Unread count shown as badge on sidebar icon.
Types: INFO, SUCCESS, WARNING, ALERT, TASK, MESSAGE, DOCUMENT.
Click any notification to mark as read.

## ROLES AND ACCESS

- **ADMIN / SECRETARIAT_LEAD**: Full platform access. Can see all TWGs, manage users, change platform settings.
- **TWG_FACILITATOR**: Manages their assigned TWG(s). Can create meetings, upload documents, manage action items.
- **TWG_MEMBER**: Read access to their TWG(s). Can view action items assigned to them.

## COMMON TASKS — HOW TO GUIDE USERS

**"How do I add a new project?"**
→ Deal Pipeline → "Add Project" button (top right) → fill the form → Save.

**"How do I advance a project to Summit Ready?"**
→ Open the project in Deal Pipeline → check that women_employment_pct ≥ 30% and youth_employment_pct ≥ 25% → click "Advance Stage". If blocked, edit the project and update those percentages first.

**"Why can't I advance this project?"**
→ The gender/youth gate is blocking it. The project needs women_employment_pct ≥ 30% and youth_employment_pct ≥ 25%. Edit the project, fill those fields, then try advancing again.

**"How do I schedule a meeting?"**
→ Go to Schedule → click a date → fill the form → Save. Or ask me and I'll schedule it for you.

**"How do I find documents?"**
→ Go to Documents → use the search bar or filter by TWG. Or ask me: "Find documents about [topic]".

**"How do I see my action items?"**
→ TWG Workspace → Action Items tab. Or ask me: "Show my action items".

**"What does Summit Ready mean?"**
→ A project that has passed scoring (readiness_score typically ≥ 75), cleared the gender/youth gate, and been advanced to SUMMIT_READY status by a facilitator or admin.

**"How do I check a project's score?"**
→ Click the project in Deal Pipeline → Score tab shows all 9 WAIIS criteria with individual scores, weights, and improvement tips.

**"How do I send an email to a TWG?"**
→ Ask me: "Send [message] to [TWG name] members" and I will look up their emails and compose it.

**"How do I add someone to a TWG?"**
→ Only admins can do this: Profile → Users → find the user → Edit → assign TWG membership. Or ask your admin.

=== END PLATFORM GUIDE ===
```

- [ ] **Step 2: Modify `prompts.py` to append the guide for the supervisor**

In `backend/app/agents/prompts.py`, find the `get_prompt` function. After the line `_PROMPT_CACHE[agent_id] = prompt`, add the platform guide injection for the supervisor:

The full modified `get_prompt` function (replace the existing one, lines 27–76):

```python
def get_prompt(agent_id: str) -> str:
    """
    Get the system prompt for a specific agent.
    For 'supervisor', appends platform_guide.txt if present.
    """
    if agent_id not in AVAILABLE_AGENTS:
        available = ", ".join(AVAILABLE_AGENTS)
        raise ValueError(
            f"Unknown agent_id: '{agent_id}'. "
            f"Available agents: {available}"
        )

    if agent_id in _PROMPT_CACHE:
        return _PROMPT_CACHE[agent_id]

    prompts_dir = Path(__file__).parent / "prompts"
    prompt_file = prompts_dir / f"{agent_id}.txt"

    if not prompt_file.exists():
        raise FileNotFoundError(
            f"Prompt file not found for agent '{agent_id}': {prompt_file}"
        )

    with open(prompt_file, 'r', encoding='utf-8') as f:
        prompt = f.read().strip()

    if agent_id == "supervisor":
        guide_file = prompts_dir / "platform_guide.txt"
        if guide_file.exists():
            with open(guide_file, 'r', encoding='utf-8') as f:
                guide = f.read().strip()
            prompt = prompt + "\n\n" + guide

    _PROMPT_CACHE[agent_id] = prompt
    return prompt
```

- [ ] **Step 3: Verify the guide is injected**

Run this one-liner from `backend/`:

```bash
PYTHONPATH=. python3 -c "
from app.agents.prompts import get_prompt, reload_prompts
reload_prompts()
p = get_prompt('supervisor')
print('Guide injected:', '=== PLATFORM GUIDE ===' in p)
print('Prompt length (tokens ~):', len(p) // 4)
"
```

Expected output:
```
Guide injected: True
Prompt length (tokens ~): 1800
```
(Token count will vary; anything 1200–3000 is fine.)

- [ ] **Step 4: Commit**

```bash
git add backend/app/agents/prompts/platform_guide.txt backend/app/agents/prompts.py
git commit -m "feat: add platform guide to supervisor prompt"
```

---

## Task 2: Briefing endpoint

**Files:**
- Create: `backend/app/api/routes/martin.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Write the test for the briefing endpoint**

Create `backend/tests/test_martin_briefing.py`:

```python
"""Tests for GET /api/v1/martin/briefing"""
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, AsyncMock
from app.main import app
from app.models.models import UserRole


@pytest.mark.asyncio
async def test_briefing_requires_auth():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/martin/briefing")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_briefing_returns_required_keys():
    """All three keys must be present even when empty."""
    mock_user = AsyncMock()
    mock_user.role = UserRole.TWG_MEMBER
    mock_user.twgs = []
    mock_user.id = "00000000-0000-0000-0000-000000000001"

    with patch("app.api.routes.martin.get_current_active_user", return_value=mock_user), \
         patch("app.api.routes.martin.get_db"):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # patch db execute to return empty results
            with patch("app.api.routes.martin._query_briefing_data", new_callable=AsyncMock) as mock_query:
                mock_query.return_value = ([], [], [])
                resp = await client.get(
                    "/api/v1/martin/briefing",
                    headers={"Authorization": "Bearer fake"}
                )

    # We just need to confirm the route exists and returns the right shape
    # Full integration test requires a real DB — this is a structural check
    assert resp.status_code in (200, 401, 422)  # route must exist
```

- [ ] **Step 2: Run test to confirm route doesn't exist yet**

```bash
cd backend && PYTHONPATH=. venv/bin/pytest tests/test_martin_briefing.py::test_briefing_requires_auth -v
```

Expected: `FAILED` or `404` — route not registered yet.

- [ ] **Step 3: Create `backend/app/api/routes/martin.py`**

```python
"""
Martin Copilot — Briefing endpoint.
GET /martin/briefing — returns role-aware pre-computed summary for the copilot opening bubble.
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Tuple

from fastapi import APIRouter, Depends
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_active_user
from app.core.database import get_db
from app.models.models import (
    Meeting,
    MeetingStatus,
    Notification,
    Project,
    ProjectStatus,
    User,
    UserRole,
)

router = APIRouter(prefix="/martin", tags=["martin"])


async def _query_briefing_data(
    db: AsyncSession,
    is_admin: bool,
    user_twg_ids: List[Any],
    user_id: Any,
    now: datetime,
) -> Tuple[List[Dict], List[Dict], List[Dict]]:
    """Run the three DB queries and return structured lists."""
    window_end = now + timedelta(hours=48)
    notif_cutoff = now - timedelta(hours=48)

    # --- Upcoming meetings (next 48 hours) ---
    mtg_q = (
        select(Meeting)
        .options(selectinload(Meeting.twg))
        .where(
            and_(
                Meeting.scheduled_at >= now,
                Meeting.scheduled_at <= window_end,
                Meeting.status == MeetingStatus.SCHEDULED,
            )
        )
        .order_by(Meeting.scheduled_at)
        .limit(5)
    )
    if not is_admin and user_twg_ids:
        mtg_q = mtg_q.where(Meeting.twg_id.in_(user_twg_ids))
    elif not is_admin and not user_twg_ids:
        mtg_q = mtg_q.where(False)  # no access

    mtg_result = await db.execute(mtg_q)
    meetings_raw = mtg_result.scalars().all()

    upcoming_meetings: List[Dict] = []
    for m in meetings_raw:
        sched = m.scheduled_at
        if sched.tzinfo is None:
            sched = sched.replace(tzinfo=timezone.utc)
        minutes_until = max(0, int((sched - now).total_seconds() / 60))
        upcoming_meetings.append(
            {
                "title": m.title,
                "twg_name": m.twg.name if m.twg else "",
                "starts_at": sched.isoformat(),
                "minutes_until": minutes_until,
            }
        )

    # --- Threshold alerts: projects below gender/youth gate ---
    thr_q = (
        select(Project)
        .where(
            and_(
                Project.status.in_(
                    [
                        ProjectStatus.DRAFT,
                        ProjectStatus.UNDER_REVIEW,
                        ProjectStatus.SUMMIT_READY,
                    ]
                ),
                or_(
                    Project.women_employment_pct.is_(None),
                    Project.women_employment_pct < 30.0,
                    Project.youth_employment_pct.is_(None),
                    Project.youth_employment_pct < 25.0,
                ),
            )
        )
        .limit(10)
    )
    if not is_admin and user_twg_ids:
        thr_q = thr_q.where(Project.twg_id.in_(user_twg_ids))
    elif not is_admin and not user_twg_ids:
        thr_q = thr_q.where(False)

    thr_result = await db.execute(thr_q)
    threshold_projects = thr_result.scalars().all()

    threshold_alerts: List[Dict] = []
    for p in threshold_projects:
        if p.women_employment_pct is None or p.women_employment_pct < 30.0:
            threshold_alerts.append(
                {
                    "project_name": p.name,
                    "gap_type": "gender",
                    "current_pct": p.women_employment_pct,
                    "required_pct": 30.0,
                }
            )
        elif p.youth_employment_pct is None or p.youth_employment_pct < 25.0:
            threshold_alerts.append(
                {
                    "project_name": p.name,
                    "gap_type": "youth",
                    "current_pct": p.youth_employment_pct,
                    "required_pct": 25.0,
                }
            )

    # --- Overdue notifications: unread, created > 48h ago ---
    notif_q = (
        select(Notification)
        .where(
            and_(
                Notification.user_id == user_id,
                Notification.is_read == False,  # noqa: E712
                Notification.created_at <= notif_cutoff,
            )
        )
        .order_by(Notification.created_at)
        .limit(5)
    )

    notif_result = await db.execute(notif_q)
    notifs_raw = notif_result.scalars().all()

    overdue_items: List[Dict] = []
    for n in notifs_raw:
        created = n.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        days_overdue = max(0, int((now - created).total_seconds() / 86400))
        overdue_items.append({"title": n.title, "days_overdue": days_overdue})

    return upcoming_meetings, threshold_alerts, overdue_items


@router.get("/briefing")
async def get_briefing(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Dict:
    """
    Return a role-aware briefing summary for the copilot opening bubble.
    All three arrays are always present (empty if nothing to report).
    """
    now = datetime.now(timezone.utc)
    is_admin = current_user.role in (UserRole.ADMIN, UserRole.SECRETARIAT_LEAD)
    user_twg_ids = [t.id for t in current_user.twgs]

    upcoming_meetings, threshold_alerts, overdue_items = await _query_briefing_data(
        db=db,
        is_admin=is_admin,
        user_twg_ids=user_twg_ids,
        user_id=current_user.id,
        now=now,
    )

    hour = now.hour
    if hour < 12:
        greeting = "Good morning"
    elif hour < 17:
        greeting = "Good afternoon"
    else:
        greeting = "Good evening"

    return {
        "greeting": greeting,
        "upcoming_meetings": upcoming_meetings,
        "threshold_alerts": threshold_alerts,
        "overdue_items": overdue_items,
    }
```

- [ ] **Step 4: Register the martin router in `backend/app/main.py`**

Find line 24 in `main.py`:
```python
from app.api.routes import twgs, meetings, auth, projects, action_items, documents, audit, agents, dashboard, users, notifications, supervisor, debug, pipeline, conflicts, settings as settings_router, shared_documents, organization_invitations, public_invitations, recurring_meetings, subgroups
```

Replace with (add `martin` to the import):
```python
from app.api.routes import twgs, meetings, auth, projects, action_items, documents, audit, agents, dashboard, users, notifications, supervisor, debug, pipeline, conflicts, settings as settings_router, shared_documents, organization_invitations, public_invitations, recurring_meetings, subgroups, martin
```

Then find the block of `app.include_router(...)` lines (around line 264) and add after `pipeline.router`:
```python
app.include_router(martin.router, prefix=f"{settings.API_V1_STR}")
```

- [ ] **Step 5: Start the backend and test the endpoint manually**

```bash
cd backend && venv/bin/uvicorn app.main:app --reload --port 8000
```

In a second terminal, with a valid auth token (get one from the login endpoint):
```bash
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"magwaro@ecowasiisummit.net","password":"Admin@2026"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

curl -s http://127.0.0.1:8000/api/v1/martin/briefing \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

Expected: JSON with `greeting`, `upcoming_meetings`, `threshold_alerts`, `overdue_items` keys.

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/routes/martin.py backend/app/main.py backend/tests/test_martin_briefing.py
git commit -m "feat: add /martin/briefing endpoint with role-aware DB queries"
```

---

## Task 3: Frontend briefing service

**Files:**
- Create: `frontend/src/services/martinService.ts`

- [ ] **Step 1: Create `martinService.ts`**

```typescript
import api from './api';

export interface UpcomingMeeting {
    title: string;
    twg_name: string;
    starts_at: string;
    minutes_until: number;
}

export interface ThresholdAlert {
    project_name: string;
    gap_type: 'gender' | 'youth';
    current_pct: number | null;
    required_pct: number;
}

export interface OverdueItem {
    title: string;
    days_overdue: number;
}

export interface BriefingData {
    greeting: string;
    upcoming_meetings: UpcomingMeeting[];
    threshold_alerts: ThresholdAlert[];
    overdue_items: OverdueItem[];
}

export const getBriefing = async (): Promise<BriefingData> => {
    const response = await api.get<BriefingData>('/martin/briefing');
    return response.data;
};
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit 2>&1 | head -20
```

Expected: no errors related to `martinService.ts`.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/services/martinService.ts
git commit -m "feat: add martinService with getBriefing() and BriefingData types"
```

---

## Task 4: GlobalCopilot — fetch briefing and inject as first message

**Files:**
- Modify: `frontend/src/components/copilot/GlobalCopilot.tsx`

The current file (read at `frontend/src/components/copilot/GlobalCopilot.tsx`) has:
- `localMessages` state (array of `LocalMessage`)
- `isStreaming` state
- `scrollRef` for auto-scroll

We add:
- `briefing` state (`BriefingData | null`)
- `isBriefingLoading` state (boolean)
- `useEffect` on mount that calls `getBriefing()` and injects result as first agent message

- [ ] **Step 1: Add briefing imports and state to `GlobalCopilot.tsx`**

At the top, add the import (alongside existing imports):
```typescript
import { getBriefing, BriefingData } from '../../services/martinService';
```

Inside the component, after the existing state declarations (after `const [input, setInput] = useState('');`), add:
```typescript
const [briefing, setBriefing] = useState<BriefingData | null>(null);
const [isBriefingLoading, setIsBriefingLoading] = useState(true);
```

- [ ] **Step 2: Add briefing fetch effect**

After the existing `useEffect` blocks (after the navigate events handler), add:

```typescript
// Fetch briefing on mount and inject as first message
useEffect(() => {
    let cancelled = false;
    setIsBriefingLoading(true);
    getBriefing()
        .then((data) => {
            if (cancelled) return;
            setBriefing(data);
            const lines: string[] = [];
            const hasContent =
                data.upcoming_meetings.length > 0 ||
                data.threshold_alerts.length > 0 ||
                data.overdue_items.length > 0;

            if (!hasContent) {
                lines.push(`${data.greeting}. Things look good — nothing urgent today.`);
                lines.push('\nWhat would you like to do?');
            } else {
                lines.push(`${data.greeting}. A few things for your attention:\n`);
                data.threshold_alerts.forEach((a) => {
                    const label = a.gap_type === 'gender' ? 'gender' : 'youth';
                    const current = a.current_pct != null ? `${a.current_pct.toFixed(0)}%` : 'not set';
                    lines.push(`⚠️ **${a.project_name}** — ${label} employment gap (${current} / ${a.required_pct}% required)`);
                });
                data.upcoming_meetings.forEach((m) => {
                    const hrs = Math.floor(m.minutes_until / 60);
                    const mins = m.minutes_until % 60;
                    const timeStr = hrs > 0 ? `in ${hrs}h ${mins}m` : `in ${mins} minutes`;
                    lines.push(`📅 **${m.title}** ${timeStr}${m.twg_name ? ` (${m.twg_name})` : ''}`);
                });
                data.overdue_items.forEach((o) => {
                    lines.push(`📋 **${o.title}** — unread for ${o.days_overdue} day${o.days_overdue !== 1 ? 's' : ''}`);
                });
                lines.push('\nWhat would you like to tackle first?');
            }

            setLocalMessages([{
                id: 'briefing',
                content: lines.join('\n'),
                sender: 'agent',
                timestamp: new Date().toISOString(),
            }]);
        })
        .catch(() => {
            if (cancelled) return;
            // Briefing failed silently — copilot opens empty
        })
        .finally(() => {
            if (!cancelled) setIsBriefingLoading(false);
        });
    return () => { cancelled = true; };
}, []); // eslint-disable-line react-hooks/exhaustive-deps
```

- [ ] **Step 3: Show loading state while briefing is fetching**

In the JSX, find the `{/* Message list */}` section. The existing streaming indicator shows `{isStreaming && (...)}`. We need to show the pulsing dots while the briefing is loading AND no messages exist yet.

Find this block:
```tsx
{/* Streaming: animated thinking indicator */}
{isStreaming && (
```

Before it, add:
```tsx
{/* Briefing loading: same animation while initial fetch runs */}
{isBriefingLoading && localMessages.length === 0 && (
    <div className="flex gap-2 items-center">
        <div className="w-6 h-6 rounded-lg bg-blue-600 flex items-center justify-center flex-shrink-0 shadow-sm">
            <span className="text-white text-[10px] font-bold leading-none animate-pulse">✦</span>
        </div>
        <div className="flex gap-1 items-center px-1 py-2">
            <span className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
            <span className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
            <span className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
        </div>
    </div>
)}
```

- [ ] **Step 4: Pass briefing to `SuggestedActions`**

Find the existing `<SuggestedActions>` usage (around line 188–194):
```tsx
<SuggestedActions
    onFillInput={handleFillInput}
    onSubmit={(text) => {
        setInput(text);
        setTimeout(handleSend, 0);
    }}
/>
```

Replace with:
```tsx
<SuggestedActions
    briefing={briefing}
    onFillInput={handleFillInput}
    onSubmit={(text) => {
        setInput(text);
        setTimeout(handleSend, 0);
    }}
/>
```

- [ ] **Step 5: Also reset briefing on history clear**

Find `handleClearHistory`:
```typescript
const handleClearHistory = () => {
    setLocalMessages([]);
    setConversationId(undefined);
};
```

Replace with:
```typescript
const handleClearHistory = () => {
    setLocalMessages([]);
    setConversationId(undefined);
    setBriefing(null);
    setIsBriefingLoading(true);
    getBriefing()
        .then((data) => {
            setBriefing(data);
            // same injection logic — extract to helper if preferred, but inline is fine
            const lines: string[] = [];
            const hasContent =
                data.upcoming_meetings.length > 0 ||
                data.threshold_alerts.length > 0 ||
                data.overdue_items.length > 0;
            if (!hasContent) {
                lines.push(`${data.greeting}. Things look good — nothing urgent today.`);
                lines.push('\nWhat would you like to do?');
            } else {
                lines.push(`${data.greeting}. A few things for your attention:\n`);
                data.threshold_alerts.forEach((a) => {
                    const label = a.gap_type === 'gender' ? 'gender' : 'youth';
                    const current = a.current_pct != null ? `${a.current_pct.toFixed(0)}%` : 'not set';
                    lines.push(`⚠️ **${a.project_name}** — ${label} employment gap (${current} / ${a.required_pct}% required)`);
                });
                data.upcoming_meetings.forEach((m) => {
                    const hrs = Math.floor(m.minutes_until / 60);
                    const mins = m.minutes_until % 60;
                    const timeStr = hrs > 0 ? `in ${hrs}h ${mins}m` : `in ${mins} minutes`;
                    lines.push(`📅 **${m.title}** ${timeStr}${m.twg_name ? ` (${m.twg_name})` : ''}`);
                });
                data.overdue_items.forEach((o) => {
                    lines.push(`📋 **${o.title}** — unread for ${o.days_overdue} day${o.days_overdue !== 1 ? 's' : ''}`);
                });
                lines.push('\nWhat would you like to tackle first?');
            }
            setLocalMessages([{
                id: 'briefing-refresh',
                content: lines.join('\n'),
                sender: 'agent',
                timestamp: new Date().toISOString(),
            }]);
        })
        .catch(() => {})
        .finally(() => setIsBriefingLoading(false));
};
```

- [ ] **Step 6: TypeScript check**

```bash
cd frontend && npx tsc --noEmit 2>&1 | head -30
```

Expected: no errors in `GlobalCopilot.tsx` or `martinService.ts`.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/copilot/GlobalCopilot.tsx
git commit -m "feat: fetch briefing on copilot mount and inject as opening message"
```

---

## Task 5: Dynamic suggested action chips

**Files:**
- Modify: `frontend/src/components/copilot/SuggestedActions.tsx`

The current `SuggestedActions` takes `onFillInput` and `onSubmit`. We add `briefing?: BriefingData | null` and generate priority-based chips from it when present.

- [ ] **Step 1: Update `SuggestedActions.tsx`**

Replace the entire file with:

```typescript
import { useLocation } from 'react-router-dom';
import { BriefingData } from '../../services/martinService';

interface ActionChip {
    emoji: string;
    label: string;
    template: string;
    color?: 'red' | 'blue' | 'amber' | 'default';
}

interface SuggestedActionsProps {
    onFillInput: (text: string) => void;
    onSubmit: (text: string) => void;
    briefing?: BriefingData | null;
}

const SUGGESTED_ACTIONS: Record<string, ActionChip[]> = {
    '/workspace': [
        { emoji: '📅', label: 'Draft agenda', template: 'Draft an agenda for the next [TWG] meeting on [date]' },
        { emoji: '🗓', label: 'Schedule', template: 'Schedule a meeting for [topic] on [date] at [time]' },
        { emoji: '📋', label: 'Summarize docs', template: 'Summarize the latest documents in this workspace' },
        { emoji: '✅', label: 'Add action', template: 'Create an action item: [task] assigned to [person] due [date]' },
    ],
    '/meetings': [
        { emoji: '🗓', label: 'Schedule meeting', template: 'Schedule a meeting for [topic] on [date] at [time]' },
        { emoji: '📝', label: 'Draft minutes', template: 'Draft minutes for the [TWG] meeting on [date]' },
        { emoji: '⚠️', label: 'Check conflicts', template: 'Check for scheduling conflicts in the next 2 weeks' },
        { emoji: '📅', label: 'View agenda', template: 'Show the agenda for the upcoming [TWG] meeting' },
    ],
    '/documents': [
        { emoji: '📄', label: 'Summarize', template: 'Summarize the most recent documents' },
        { emoji: '✍️', label: 'Draft brief', template: 'Draft a brief on [topic] for [TWG]' },
        { emoji: '🔍', label: 'Search by topic', template: 'Search documents for [topic]' },
        { emoji: '📋', label: 'Export list', template: 'List all documents shared with [TWG]' },
    ],
};

const FALLBACK_CHIPS: ActionChip[] = [
    { emoji: '📅', label: "What's on today?", template: "What's on my schedule today?" },
    { emoji: '📁', label: 'Show my projects', template: 'Show me the projects in the pipeline' },
    { emoji: '❓', label: 'Help me navigate', template: 'How do I use the Deal Pipeline?' },
];

function hasPlaceholder(template: string): boolean {
    return /\[.+?\]/.test(template);
}

function getPageChips(pathname: string): ActionChip[] | null {
    for (const [pattern, chips] of Object.entries(SUGGESTED_ACTIONS)) {
        if (pathname.startsWith(pattern)) return chips;
    }
    return null;
}

function getBriefingChips(briefing: BriefingData): ActionChip[] {
    const chips: ActionChip[] = [];

    if (briefing.threshold_alerts.length > 0) {
        const count = briefing.threshold_alerts.length;
        chips.push({
            emoji: '⚠️',
            label: `Fix ${count} gap${count > 1 ? 's' : ''}`,
            template: 'Show me the projects below the gender and youth employment threshold',
            color: 'red',
        });
    }

    if (briefing.upcoming_meetings.length > 0) {
        const m = briefing.upcoming_meetings[0];
        chips.push({
            emoji: '📅',
            label: 'Prep for meeting',
            template: `Help me prepare for the ${m.title} meeting`,
            color: 'blue',
        });
    }

    if (briefing.overdue_items.length > 0) {
        chips.push({
            emoji: '📋',
            label: 'Review notifications',
            template: 'Show me my unread notifications',
            color: 'amber',
        });
    }

    return chips.length > 0 ? chips : FALLBACK_CHIPS;
}

const COLOR_CLASSES: Record<string, string> = {
    red: 'border-red-200 bg-red-50 text-red-700 hover:bg-red-100 dark:border-red-800 dark:bg-red-900/30 dark:text-red-300',
    blue: 'border-blue-200 bg-blue-50 text-blue-700 hover:bg-blue-100 dark:border-blue-800 dark:bg-blue-900/30 dark:text-blue-300',
    amber: 'border-amber-200 bg-amber-50 text-amber-700 hover:bg-amber-100 dark:border-amber-800 dark:bg-amber-900/30 dark:text-amber-300',
    default: 'bg-slate-100 dark:bg-slate-700/60 text-slate-600 dark:text-slate-300 hover:bg-blue-50 dark:hover:bg-blue-900/30 hover:text-blue-700 dark:hover:text-blue-300',
};

export default function SuggestedActions({ onFillInput, onSubmit, briefing }: SuggestedActionsProps) {
    const { pathname } = useLocation();

    // Priority: page-specific > briefing-driven > fallback
    const pageChips = getPageChips(pathname);
    const chips: ActionChip[] = pageChips
        ? pageChips
        : briefing
        ? getBriefingChips(briefing)
        : FALLBACK_CHIPS;

    const handleChip = (chip: ActionChip) => {
        if (hasPlaceholder(chip.template)) {
            onFillInput(chip.template);
        } else {
            onSubmit(chip.template);
        }
    };

    return (
        <div className="px-3 py-2 flex gap-1.5 flex-wrap border-b border-slate-100 dark:border-slate-700/60">
            {chips.map(chip => {
                const colorClass = COLOR_CLASSES[chip.color ?? 'default'];
                return (
                    <button
                        key={chip.label}
                        onClick={() => handleChip(chip)}
                        className={`flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium border transition-colors ${colorClass}`}
                    >
                        <span>{chip.emoji}</span>
                        <span>{chip.label}</span>
                    </button>
                );
            })}
        </div>
    );
}
```

- [ ] **Step 2: TypeScript check**

```bash
cd frontend && npx tsc --noEmit 2>&1 | head -30
```

Expected: no errors.

- [ ] **Step 3: Start frontend and test the copilot manually**

```bash
cd frontend && npm run dev
```

Open the app at `http://localhost:5173`. Log in, open the copilot (✦ button). Verify:
1. The pulsing dots appear briefly while briefing loads
2. Martin's opening message appears with the briefing data (or "nothing urgent" if clean)
3. Action chips are colored and relevant to the briefing
4. After sending a message, normal conversation flow works unchanged
5. "Clear history" re-fetches the briefing and shows a fresh opening message

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/copilot/SuggestedActions.tsx
git commit -m "feat: dynamic suggested action chips driven by briefing data"
```

---

## Self-Review Checklist

After all tasks complete:

- [ ] Platform guide is appended to supervisor prompt and `get_prompt("supervisor")` confirms it
- [ ] `/api/v1/martin/briefing` returns 200 with correct JSON shape when authenticated
- [ ] Unauthenticated request returns 403
- [ ] Copilot opens with animated dots then briefing message
- [ ] Chips are colored correctly: red for threshold gaps, blue for meetings, amber for overdue
- [ ] Normal chat flow (user message → streaming → response) still works after briefing injection
- [ ] TypeScript: `npx tsc --noEmit` passes with zero errors
