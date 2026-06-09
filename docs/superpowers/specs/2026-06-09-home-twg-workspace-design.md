# Home TWG + Workspace — Design Spec

**Date:** 2026-06-09
**Status:** Approved approach (brainstormed via visual companion) — pending spec review.

## Goal

Surface the member's **TWG membership(s)** on the Home screen and give each TWG a dedicated **Workspace** hub — a per-TWG home that aggregates that group's meetings, documents, tasks, members, and a TWG-scoped Martin. Maximize reuse of components and endpoints already in the app.

## Chosen approach (from brainstorm)

**B + multi-TWG**, decided against two alternatives (A: a Home card that only deep-links into the existing filtered tabs; C: a top-of-Home TWG switcher as the primary surface):

- **Home** keeps its existing **cross-TWG briefing** (Martin already aggregates meetings/tasks across *all* the member's TWGs — unchanged). Below it, a new **"Your TWGs"** section lists each membership.
  - **1 TWG** → a single "Your TWG" card.
  - **2+ TWGs** → a labelled list of TWG cards.
  - Each card → that TWG's Workspace.
- **Workspace** is a **per-TWG hub screen** reached from a Home card. Its header carries a **switcher** (rendered only when the member has 2+ TWGs) to hop between the member's workspaces without returning Home.

The briefing is **not** scoped per-TWG: Home stays the whole-life view; the Workspace is the deep dive.

## Architecture

Two units, both in the `mobile/` Flutter app. No backend changes required (all data exists; see Backend contracts).

### 1. Home addition — "Your TWGs" section

- A new presentation widget in the existing `features/home` feature, rendered in `_DataView` **below** the Martin briefing card (above the suggestion chips).
- **Source of truth:** `AppUser.twgs` (already in auth state from `/auth/me`) — **no new fetch** for the names. The Home cards stay lightweight: TWG name + pillar + a minimal pulse line. To avoid N per-TWG network calls on Home, the pulse is **derived from data already present** — the briefing's `nextMeeting` (matched to the TWG by name when available) — otherwise it falls back to a static "Open workspace". No per-TWG stats are fetched on Home.
- **0 TWGs:** the section is hidden (a member not yet assigned to a TWG sees the briefing only).
- Tap a card → `context.push('/home/workspace/<twgId>')`.

### 2. TWG Workspace screen

New feature folder `mobile/lib/features/workspace/`:

- **Route:** `GoRoute(path: 'workspace/:twgId', …)` **nested under the existing `/home` branch** → resolves to `/home/workspace/:twgId`, so the floating bottom nav persists (consistent with 4b's `/home/chat`). Rendered via `sovereignPage`.
- **Repository — `WorkspaceRepository`** (composition over duplication): injects the existing `MeetingsRepository`, `DocumentsRepository`, and `MeRepository`, plus its own `dio` for `GET /twgs/{id}`. Methods:
  - `twgDetail(twgId)` → `GET /twgs/{id}` → `TwgDetail` (name, pillar, status, members).
  - delegates scoped lists to the existing repos (see repo changes below).
- **Controller — `WorkspaceController`** as `NotifierProvider.family<WorkspaceController, WorkspaceState, String>` keyed by `twgId`. `load()` fans out: TWG detail + upcoming meetings (scoped) + recent documents (scoped) + your tasks (scoped, `mine_only`). Sealed `WorkspaceState = loading | error | data`. **Each section is best-effort** (try/catch per section, mirroring `me_controller`'s resilience) so a single failing endpoint never blanks the hub.
- **Screen — `WorkspaceScreen(twgId)`** (`ConsumerStatefulWidget`), Sovereign glass system, **glass-inside-glass** (outer section frame + inner rows — the same pattern as the reworked meeting detail). Sections, top→bottom:
  1. **Header** — back button + TWG name + pillar chip + **switcher** (only if `auth.twgs.length > 1`) + a member avatar row with count.
  2. **Next meeting** — the soonest scoped meeting as a compact tile + Join (reuses the meeting tile / Join pill).
  3. **Documents** — recent scoped documents (reuses the document row; tap → existing Documents preview).
  4. **Your tasks** — scoped action items assigned to the member (reuses the Me action-item row).
  5. **Ask Martin** — a glass card → opens the 4b chat **scoped to this `twgId`**.
- **Switcher** behavior: a header menu listing the member's *other* TWGs → `context.replace('/home/workspace/<otherId>')` (replace, not push, so Back returns to Home rather than stacking workspaces).

### Repository changes (small, backward-compatible)

- `MeetingsRepository.listMeetings({String? twgId})` → appends `?twg_id=` when provided (server-side filter, verified).
- `MeRepository.listActionItems({String? twgId})` → appends `&twg_id=` alongside `mine_only=true` (server-side filter, verified).
- Documents scoping: add `twgId` to the `Document` model (parse `json['twg']['id']`) and filter the existing `listDocuments()` result by `twgId` client-side (the list already returns the member's accessible docs). If the documents list route exposes a `twg_id` query, the plan should prefer that server-side filter.

## Component & endpoint reuse (the explicit ask)

- **Auth:** `AppUser.twgs` (names/ids, no fetch) and `currentUserIdProvider`.
- **Design system:** `GlassCard`, `GlassSurface`, `GlassSurface.inner`, `SovereignColors`, the ambient navy+gold backdrop.
- **Rows/tiles:** the meeting tile + Join pill, the document row, the action-item row — lifted from the meetings/documents/me screens into reusable widgets (extract the existing private widgets into `features/workspace/presentation/widgets/` or a shared location; prefer extracting over duplicating).
- **Repos:** `MeetingsRepository`, `DocumentsRepository`, `MeRepository` (with the optional `twgId` params).
- **Chat:** the 4b `MartinChatScreen` for Ask-Martin (scoped to the workspace `twgId`).

## Data flow

```
Home (_DataView)
  reads auth.twgs ──> renders "Your TWGs" card(s)   [no fetch]
  tap card ─────────> push /home/workspace/<twgId>

WorkspaceScreen(twgId)
  WorkspaceController(twgId).load()
    ├─ GET /twgs/{twgId}                         -> TwgDetail (name, pillar, members)
    ├─ MeetingsRepository.listMeetings(twgId)    -> GET /meetings/?twg_id=     (upcoming, take soonest)
    ├─ DocumentsRepository.listDocuments(twgId)  -> scoped recent docs
    └─ MeRepository.listActionItems(twgId)       -> GET /action-items/?twg_id=&mine_only=true
  Ask Martin ──> open MartinChatScreen scoped to twgId
  Switcher  ──> replace /home/workspace/<otherTwgId>
```

## Backend contracts (verified — no change needed)

- `GET /twgs/{id}` — any authenticated user; returns `TWGRead` incl. `members`. (Access is implicitly the member's own TWG.)
- `GET /meetings/?twg_id=<uuid>` — filters to the TWG; enforces `has_twg_access`. Without `twg_id`, scopes to the user's TWGs.
- `GET /action-items/?twg_id=<uuid>&mine_only=true` — filters to the TWG + the member's items; access-checked.
- Documents list — returns the member's accessible documents (each carries its `twg`); scope client-side by `twgId` unless a `twg_id` query is available.
- Martin chat (4b) — `POST /agents/chat/stream` takes a `twg_id`; Ask-Martin passes the workspace `twgId`.

## States & edge cases

- **Loading:** centered gold spinner.
- **Error (TWG detail fails):** glass message + Retry (reuse the existing error view pattern).
- **Per-section empty/failed:** each section renders its own empty state ("No upcoming meetings", "No documents yet", "No tasks for you here") and a section failure is swallowed (best-effort), never blanking the hub.
- **0 TWGs:** Home hides the "Your TWGs" section.
- **1 TWG:** section label is "Your TWG", single card; workspace switcher hidden.
- **2+ TWGs:** section label "Your TWGs", list of cards; switcher shown.

## Testing

- `workspace_models_test` — `TwgDetail`/`TwgMember.fromJson`.
- `workspace_controller_test` — mock the three repos + dio: loading → data; a section throwing still yields `data` with that section empty.
- `workspace_screen_test` — pump with overridden controller/repos: renders TWG name + each section; switcher present with 2 TWGs, absent with 1.
- `home_screen_test` (extend) — renders 1 card for a single-TWG user and N cards for multi; tapping a card pushes `/home/workspace/<id>`.

## Scope / YAGNI

- **In:** Your-TWGs section on Home; per-TWG Workspace with next meeting · documents · your tasks · members · Ask-Martin; the switcher.
- **Deferred (future):** TWG threshold/pipeline alerts on the workspace; full meeting-minutes view inside the workspace; per-TWG Home pulse stats that require extra fetches; reordering/pinning TWGs.

## Dependencies

- **4b (Martin chat)** must be merged — Ask-Martin reuses `MartinChatScreen` and needs it to accept a `twgId` override (currently it derives `twgId` from the member's first TWG). A small extension to 4b's chat entry: accept an optional `twgId` (via the `/home/chat?twg=` query or a constructor arg).
