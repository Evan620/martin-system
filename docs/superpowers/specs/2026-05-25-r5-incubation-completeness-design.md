# R5 Incubation Completeness — Design Spec

**Date:** 2026-05-25
**Source handoff:** `docs/handoffs/r5-incubation-completeness.md`
**Status:** Approved for implementation
**Scope:** Phase 2 of WAIIS gap roadmap. Single branch / single PR. Independent of R6.

---

## TL;DR

Flesh out the existing `INCUBATION` project status from a label into a real on-ramp: a downloadable XLSX financial-model template, a six-item document checklist endpoint + UI, a 90-day auto-expiry handler with a new `ARCHIVED` status, and a dedicated `/deal-pipeline/incubation` workspace. Extend existing services — do not refactor the enum, the lifecycle, the readiness-gap LLM endpoint, or the graduation-threshold gate.

---

## Architecture

One backend module extended (`pipeline.py`) + one new constants file + one method on `LifecycleService` + one APScheduler job + one new React page. No new tables. Enum gains one value (`ARCHIVED`) via Alembic migration.

```
Template download endpoint ──► generated XLSX (openpyxl, in-memory)
Checklist endpoint         ──► Document rows by project_id + (canonical_code OR alias)
Archive method             ──► LifecycleService.archive_stalled_incubation_projects()
                              ↳ APScheduler daily 02:00 UTC (gated by DISABLE_IN_APP_MONITOR)
                              ↳ also via scripts/archive_stalled_incubation.py (Railway guard)
Incubation workspace       ──► /deal-pipeline/incubation, surfaced from /deal-pipeline
```

---

## Sub-deliverable 1 — Financial-model XLSX template

**Endpoint:** `GET /api/v1/pipeline/templates/financial-model` — any authenticated user.

**Generation:** build in-memory with `openpyxl`, return as `StreamingResponse` with
`Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
and `Content-Disposition: attachment; filename="waiis_financial_model_template.xlsx"`.

**Sheets:**
1. `Sources & Uses` — DFI tranches, equity, grant, commercial debt (parameterised rows)
2. `5Y P&L` — revenue, COGS, opex, EBITDA (years 1–5)
3. `Capex Schedule` — construction-phase line items
4. `Sensitivity` — IRR / NPV at three commodity-price scenarios
5. `Currency Exposure` — USD vs local % for revenue and costs
6. `ESIA Costs` — explicit environmental-compliance budget
7. `Social Impact` — jobs (construction + O&M), smallholders reached, women %, youth %

Header style (bold + accent fill), no formulas (sponsors fill in). Each sheet has a brief instruction row at top.

**Frontend:** "Download financial-model template" button on `ProjectDetails` overview tab when project is in INCUBATION.

---

## Sub-deliverable 2 — Six-item checklist

**Constants** in `backend/app/core/constants.py`:

```python
INCUBATION_CHECKLIST_ITEMS = [
    ("FEASIBILITY",     "Preliminary Feasibility Study"),
    ("LAND_RIGHTS",     "Land Rights / Site Control"),
    ("GOV_SUPPORT",     "Government Support Letter"),
    ("ENV_ASSESSMENT",  "Environmental Pre-Assessment"),
    ("FINANCIAL_MODEL", "Financial Model"),
    ("CORE_TEAM",       "Core Project Team Identified"),
]
DOC_TYPE_ALIASES: dict[str, set[str]] = {
    "FEASIBILITY":     {"feasibility_study", "feasibility"},
    "LAND_RIGHTS":     {"land_rights", "site_control"},
    "GOV_SUPPORT":     {"government_letter", "noc", "gov_support"},
    "ENV_ASSESSMENT":  {"esia_screening", "environmental_assessment", "env_assessment"},
    "FINANCIAL_MODEL": {"financial_model"},
    "CORE_TEAM":       {"team", "org_chart", "core_team"},
}
```

**Endpoint:** `GET /api/v1/pipeline/{project_id}/incubation-checklist`

Auth: caller role must be in `INCUBATION_VISIBLE_ROLES`. 404 if not found. 400 if status ≠ INCUBATION.

Response:
```json
{
  "items": [
    {"code": "FEASIBILITY", "label": "...", "completed": true, "document_id": "uuid"},
    ...
  ],
  "completed_count": 2,
  "total_count": 6
}
```

Matching logic: case-insensitive. A `Document` with `document_type` equal to the canonical code **or** any of its aliases ticks the slot. If multiple match, pick the most recently uploaded.

**No new table.** Reuse `Document` model exactly as it is.

**UI:** above the existing tabs in `ProjectDetails.tsx`, render a 6-pill strip (green check / grey circle). Each pill is clickable and opens the existing upload modal with the document-type dropdown pre-selected to that canonical code. Upload-modal dropdown adds the six canonical codes alongside legacy entries.

---

## Sub-deliverable 3 — 90-day auto-expiry → ARCHIVED

**Enum:** `ProjectStatus.ARCHIVED = "ARCHIVED"` added after `ON_HOLD` in `backend/app/models/models.py`. Alembic migration appends the value to the existing Postgres enum.

**Lifecycle:**
- `ALLOWED_TRANSITIONS[(INCUBATION, ARCHIVED)] = {"roles": [UserRole.ADMIN], "description": "Auto-archive stalled Incubation project"}`
- New method:

```python
@staticmethod
async def archive_stalled_incubation_projects(
    db: AsyncSession,
    system_user: User,
    dry_run: bool = False,
) -> list[dict]:
    """Find INCUBATION projects older than STAGE_DURATION_THRESHOLDS[INCUBATION] (90d)
    and transition to ARCHIVED. Returns [{project_id, project_name, days_stalled, action_taken}]."""
```

`days_stalled` computed from `created_at`. Action taken: `"archived"` or `"would_archive"` (dry run) or `"skipped:<reason>"`.

**Scheduler:** `scheduler.py` adds:
```python
self.scheduler.add_job(
    archive_stalled_incubation_projects_job,
    trigger=CronTrigger(hour=2, minute=0),
    id="archive_stalled_incubation",
    replace_existing=True,
)
```
Existing `DISABLE_IN_APP_MONITOR` gate ensures local mirror is safe.

**Script:** `backend/scripts/archive_stalled_incubation.py` with `--dry-run` flag and the Railway-URL guard:
```python
db_url = settings.DATABASE_URL
if "railway.internal" in db_url or "rlwy.net" in db_url:
    print("REFUSING TO RUN against production")
    sys.exit(2)
```

**Frontend:** ARCHIVED hidden from default `/deal-pipeline` view. A new "Show archived" toggle mirrors the existing "Show incubation" toggle. Status badge color: dim grey.

---

## Sub-deliverable 4 — Dedicated Incubation workspace

**Route:** `/deal-pipeline/incubation` (sub-route of the pipeline area). Registered in `App.tsx`.

**Access:** roles in `INCUBATION_VISIBLE_ROLES` only. Non-privileged → redirect to `/dashboard` with toast "Not authorised for the Incubation Track".

**Entry point:** a header link/button on `/deal-pipeline` reading "⚗ Incubation Track →", visible to privileged roles. The existing `showIncubation` toggle stays — admins may still want to see incubation projects in the main pipeline.

**Page layout:**
- Heading + count badge.
- Grid of project cards. Each card shows:
  - Name · lead country · investment ask (formatted)
  - Checklist progress bar: e.g. "2 / 6 documents" with mini segmented bar
  - Days remaining until 90-day expiry — `90 - days_since(created_at)`. Badge amber when ≤30d, red when ≤7d, neutral otherwise
  - AfCEN score with graduation delta — "AfCEN 35 · need +5 to graduate" (threshold pulled from `platform_settings` via existing endpoint or computed client-side from a settings fetch)
  - "View readiness gap report" link → existing `/{id}/readiness-gap` route

Per-card data: page issues one list call to `/pipeline/?stage=INCUBATION`, then per-project fetches `/incubation-checklist` in parallel. Cap concurrency to 6 via a simple promise pool to avoid spamming.

---

## Errors & edge cases

- Template endpoint: catches XLSX-gen exceptions, returns 500 with `{"detail": "Template generation failed: ..."}`.
- Checklist endpoint: idempotent; returns `completed_count=0` when no docs; case-insensitive type match.
- Archive method: idempotent (filtered by status); skips projects with null `created_at` and logs a warning.
- Incubation page: empty state when no INCUBATION projects ("No projects currently in incubation").
- Frontend access gate uses the existing user role from Redux store; SSR not applicable.

---

## Testing

Backend (`pytest` async, mirror existing patterns in `backend/tests/`):

1. `test_template_download.py` — 200, content-type, non-zero bytes, openpyxl re-opens successfully, expected sheet names present.
2. `test_incubation_checklist.py` —
   - Empty checklist on a new INCUBATION project (all `completed=false`, count 0/6).
   - Upload canonical-code doc (`FEASIBILITY`) → that slot ticks.
   - Upload legacy code (`feasibility_study`) → same slot ticks via alias.
   - Non-INCUBATION project → 400.
   - TWG_MEMBER role → 403.
3. `test_archive_stalled.py` —
   - Backdate `created_at` to 95d ago → `archive_stalled_incubation_projects(dry_run=False)` returns `action_taken="archived"`, project status is `ARCHIVED`, a `ProjectStatusHistory` row exists with the reason.
   - 80d-old project → not touched.
   - `dry_run=True` returns `action_taken="would_archive"` and leaves status unchanged.

Frontend smoke (per handoff verification protocol):
- Curl template download as admin.
- Curl checklist endpoint on a seeded INCUBATION project.
- Open `/deal-pipeline/incubation` as `admin@local.dev` and as `member@local.dev`.

---

## File touch list

| Layer | Path | Action |
|---|---|---|
| Constants | `backend/app/core/constants.py` | **Create** — `INCUBATION_CHECKLIST_ITEMS`, `DOC_TYPE_ALIASES` |
| Enum | `backend/app/models/models.py` | Add `ProjectStatus.ARCHIVED` |
| Migration | `backend/alembic/versions/<new>_add_archived_status.py` | **Create** — ALTER TYPE … ADD VALUE 'ARCHIVED' |
| Lifecycle | `backend/app/services/lifecycle_service.py` | Add transition row; add `archive_stalled_incubation_projects` |
| Pipeline routes | `backend/app/api/routes/pipeline.py` | Add template-download + checklist endpoints; archived visibility filter |
| Scheduler | `backend/app/services/scheduler.py` | Add daily archive job |
| Script | `backend/scripts/archive_stalled_incubation.py` | **Create** — CLI, --dry-run, Railway guard |
| Tests | `backend/tests/test_template_download.py`, `test_incubation_checklist.py`, `test_archive_stalled.py` | **Create** |
| Schemas | `backend/app/schemas/pipeline_schemas.py` | Add `IncubationChecklistRead`, `IncubationChecklistItem` |
| Page | `frontend/src/pages/Incubation.tsx` | **Create** |
| Routes | `frontend/src/App.tsx` | Register `/deal-pipeline/incubation` |
| Pipeline page | `frontend/src/pages/DealPipeline.tsx` | Add "Incubation Track" link; add "Show archived" toggle; hide ARCHIVED by default |
| Project details | `frontend/src/pages/ProjectDetails.tsx` | Render 6-pill checklist + template-download button (INCUBATION only); pre-select doc-type from pill click |
| Document service | `frontend/src/services/documentService.ts` (or relevant) | Add canonical codes to type dropdown |
| Types | `frontend/src/types/pipeline.ts` | Add `IncubationChecklist` types; add `ARCHIVED` to `ProjectStatus` |

---

## Out of scope (do not touch)

- Separate `readiness_projects` / `readiness_checklist_items` tables (May-21 spec). Stay on the status-enum-on-projects path.
- Graduation-threshold logic (already configurable via `platform_settings`).
- LLM readiness-gap report (leave as-is).
- Notifications for the 90-day countdown (Phase 4 follow-on).
- R6 (Buyer / Offtake) — parallel session.

---

## Success criteria

1. New project ingested with `start_in_incubation=true` lands in INCUBATION with a 0/6 checklist, working template download, 90-day countdown, visible only to privileged roles on `/deal-pipeline/incubation`.
2. Uploading all six required docs + raising AfCEN ≥ 40 → existing graduation gate accepts INCUBATION → DRAFT.
3. Project backdated to 95d → archive script transitions it to ARCHIVED with a status-history row.
4. No regressions in: pipeline list, readiness-gap report, `INCUBATION_VISIBLE_ROLES` gate, WAIIS scoring.

---

## Verification

Per `docs/handoffs/r5-incubation-completeness.md` "Verification protocol" section — paste curl outputs + screenshot of `/deal-pipeline/incubation`.

Update `docs/superpowers/specs/2026-05-25-waiis-gap-roadmap.md` Phase 2 section: mark R5-flesh items ✅.
