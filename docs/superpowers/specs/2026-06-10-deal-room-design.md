# Deal Room — Design Spec (v1, interactive)

**Date:** 2026-06-10 · **Status:** Approved in brainstorm (member-TWG scope · all stages · filters · standard detail screen · Follow/Ask-Martin/Share).

## Goal

Replace the Phase-2 Deals placeholder with a working, interactive Deal Room: members see **projects linked to their TWG(s), at every stage**, filter by stage, open a standard detail screen, and act — **Follow / express interest**, **✦ Ask Martin about the deal**, **Share a brief**.

## Scope & access

- Projects scoped to the member's TWGs (server enforces — same `has_twg_access` model as meetings/docs). All lifecycle stages visible; client stage-filter chips.
- Out of scope v1: cross-pillar showcase, request-intro/meetings, deal documents tab, push alerts on stage change.

## Mobile (current v2 design kit throughout — no new visual language)

**List (Deals tab, replaces placeholder):**
- `HeaderCard` + `AppHeader('Deal Room', context_: TWG label)`.
- 3 `StatTile`s: Projects (count) · Summit-ready (count at SUMMIT_READY+) · Following (count followed by me).
- Stage filter chips (44px; All · Incubation · Draft/Pipeline · Under review · Summit-ready · Deal room · Committed/Implemented — collapse adjacent statuses into these member-friendly buckets).
- `RowGroup` of project rows: leading icon container, title = project name, meta = `sector · value · score N/100` (omit missing), trailing = compact stage chip (stage-bucket colored: muted→gold as stage advances). Tap → detail. Skeletons / refresh / cascade standard.

**Detail (`/deals/:id`, nested under the Deals branch, sovereignPage):**
- Back button above a `HeaderCard`: project name (19 w800), sector meta, trailing stage chip.
- Info chip row (like meeting detail): value · location · sponsor/lead (whichever fields the API has).
- **WAIIS score** card: big numeral + label; component breakdown rows when the API exposes components, else the single score.
- Description in a card-in-card section.
- Pinned action bar (like meeting detail): **Follow** = THE yellow action (toggles "Following ✓", optimistic), **✦ Ask Martin** (pushes `/martin?q=Tell me about the project <name>`), **Share** (system share sheet with name · sector · stage · value · score text brief).

## Backend (wf-a-backend branch; rides the pending deploy)

1. **Read**: reuse the existing projects/pipeline list endpoint if it supports TWG scoping for members; otherwise add `GET /projects/member` (TWG-scoped, all stages, fields: id, name, sector, status, value, score(+components if cheap), location, description). Member-safe serialization only.
2. **Interest**: `POST /projects/{id}/interest` + `DELETE /projects/{id}/interest` (member, TWG-checked) and interest state included in the member read (`is_following`, `interest_count`). **New table requires an authored Alembic migration** (project_interest: id, project_id FK, user_id FK, created_at; unique(project_id,user_id)) chained on current head.
3. **Martin tool**: `get_project_brief(project_name_or_id, twg_id, user_id)` in MEMBER_TOOLS — TWG-scoped, read-only brief (name/stage/score/value/sector/description) so Ask-Martin answers are grounded.
4. Tests: route gating (member sees own-TWG only; cross-TWG 403/404), interest toggle idempotency, tool in MEMBER_TOOLS + denied cross-TWG, migration from-scratch rehearsal.

## Testing (mobile)

Models fromJson; repo paths + params; controller best-effort; list renders rows + filters by stage; detail renders + Follow toggles via mocked repo; Ask-Martin pushes the seeded route. Full suite stays green.
