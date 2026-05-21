# R5 — Stage 0: Pre-Pipeline Investment Readiness Track

**Date:** 2026-05-21
**Status:** Approved
**Author:** Carren Mwanzia (requirement), Lazarus Magwaro (approval)
**Priority:** HIGH — July 2026

---

## Problem

The ECOWAS Summit deal pipeline currently starts at **Draft** — projects either qualify or they don't. In practice, many projects submitted by TWG facilitators are too early for investment consideration: missing financial models, no feasibility studies, incomplete contact details. These projects clog the **Under Review** stage and consume facilitator bandwidth without ever becoming investor-ready.

The AGRF Agribusiness Dealroom — the benchmark AfCEN is aligned to — solves this with year-round investment readiness support that runs *before* projects enter the main pipeline. Projects are mentored up to readiness, then released into the visible pipeline only when they are credible.

---

## Goal

Introduce a **Stage 0 (Incubation)** status that sits before Draft. Facilitators enter early-stage projects here, work through a structured readiness checklist, and the AI generates a gap report telling them exactly what to fix. When the project's AfCEN score crosses a configurable threshold (default: 40/100), the facilitator can graduate it to Draft and it enters the normal pipeline flow.

Incubation projects are **never visible to investors** — not in the Deal Room, not in investor-facing views.

---

## Architecture

### New Pipeline Status

Add `INCUBATION` to the `ProjectStatus` enum, positioned before `DRAFT`:

```
INCUBATION → DRAFT → PIPELINE → UNDER_REVIEW → SUMMIT_READY → ...
```

`INCUBATION` is a pre-pipeline status. Projects in this state:
- Are excluded from all investor-facing API endpoints and Deal Room views
- Are visible only to Admins, Secretariat Leads, and TWG Facilitators
- Appear in the main pipeline list with a purple ⚗ badge (filterable)

### Stage Transition

| From | To | Allowed Roles | Gate |
|---|---|---|---|
| *(new project)* | INCUBATION | Facilitator, Admin, Secretariat Lead | Toggle on New Project form |
| INCUBATION | DRAFT | Facilitator, Admin, Secretariat Lead | AfCEN score ≥ graduation threshold |

The graduation threshold is stored in `PlatformSetting` (key: `incubation_graduation_threshold`, default: `40`).

### Readiness Tab

A new **Readiness** tab appears on the project detail page only when `project.status == INCUBATION`. It sits alongside Overview, Financials, Documents, and History.

The tab has two panels:

**Left — WAIIS Criteria Checklist:**
- One row per WAIIS criterion (9 total)
- Each row shows: status indicator (✓ green / ! amber / ✕ red), criterion name + weight, current score (0–100), and a one-line reason for the status
- Status is derived from the existing AfCEN scoring engine — no new scoring logic
- A score progress bar at the top shows current score vs. graduation threshold
- When score ≥ threshold: "Graduate to Draft ↑" button activates; otherwise it is disabled with a message showing how many points are needed

**Right — Martin's Gap Report:**
- Dark panel with AI-generated readiness guidance
- Martin analyses the project's current data, identifies the top 3–4 highest-impact gaps, and writes specific actionable instructions (e.g. "Upload a financial model — Bankability is 18% of your score and currently zero")
- Generated on-demand via the existing AI agent pipeline when the Readiness tab loads
- Cached per project; invalidated when the project is updated

### Pipeline List Changes

**Pipeline list row (Incubation projects):**
- Purple ⚗ label above the project name instead of the normal ID chip
- Inline score progress bar below the value chain stages (showing x/40 needed)
- "↑ Graduate" green chip appears on the row when score ≥ threshold
- Status dot is purple

**New filter dropdown:** "Show Incubation / Hide Incubation" — defaults to Show for Facilitators/Admins, hidden from investor-role views entirely.

**New Project form toggle:**
- A toggle "Start in Incubation (Stage 0)" appears at the top of the New Project form
- Checked by default
- When unchecked, project is created as DRAFT (existing behaviour)

### Platform Settings

New field in the existing Platform Settings page:

| Setting Key | Label | Type | Default |
|---|---|---|---|
| `incubation_graduation_threshold` | Incubation Graduation Threshold | integer 0–100 | 40 |

Admin-only. Saved via the existing platform settings API.

---

## Data Model

No new database tables required. Changes:

1. **`ProjectStatus` enum** — add `INCUBATION` value
2. **Alembic migration** — add `INCUBATION` to the postgres enum type
3. **`PlatformSetting`** — seed `incubation_graduation_threshold = 40` in migration
4. **Investor visibility filter** — `GET /pipeline/` and all Deal Room endpoints exclude `status = INCUBATION` unless the caller has a facilitator/admin role

---

## API Changes

| Endpoint | Change |
|---|---|
| `GET /pipeline/` | Exclude INCUBATION for investor roles; include for facilitator/admin |
| `POST /pipeline/ingest` | Accept `start_in_incubation: bool = True` in request body; set status to INCUBATION if true |
| `POST /pipeline/{id}/advance` | Allow INCUBATION → DRAFT transition; enforce score gate |
| `GET /pipeline/{id}/readiness-gap` | **New** — trigger Martin gap report for this project; return structured gaps |
| `GET /platform-settings` | Return `incubation_graduation_threshold` |
| `PUT /platform-settings` | Accept and persist `incubation_graduation_threshold` |

---

## Frontend Changes

| File | Change |
|---|---|
| `frontend/src/types/pipeline.ts` | Add `INCUBATION` to `ProjectStatus` enum |
| `frontend/src/pages/DealPipeline.tsx` | Purple row style for INCUBATION; inline score bar; Graduate chip; Show/Hide filter |
| `frontend/src/pages/NewProject.tsx` | Add "Start in Incubation" toggle (default on) |
| `frontend/src/pages/ProjectDetails.tsx` | Show Readiness tab when status = INCUBATION |
| `frontend/src/components/pipeline/ReadinessTab.tsx` | **New** — checklist + graduation button + gap report panel |
| `frontend/src/pages/PlatformSettings.tsx` | Add graduation threshold field |
| `frontend/src/services/api.ts` | Add `getReadinessGap(projectId)` service call |

---

## Martin Gap Report — Prompt Design

When `GET /pipeline/{id}/readiness-gap` is called, the backend invokes the AI agent with a structured prompt:

```
You are analysing an investment project for the ECOWAS Summit deal pipeline.
The project is in Incubation (pre-pipeline stage). Your job is to identify
the 3-4 highest-impact gaps preventing this project from reaching the
graduation threshold of {threshold}/100.

Project data: {project_fields}
Current WAIIS scores per criterion: {criterion_scores}
Graduation threshold: {threshold}
Current score: {current_score}

For each gap, provide:
- Which criterion it affects and its weight
- What specific data or document is missing
- What the facilitator should do to fix it (one concrete action)

Be direct and specific. Reference actual field names where possible.
Output as JSON: { "gaps": [ { "criterion": "...", "weight": "...", "issue": "...", "action": "..." } ] }
```

The response is parsed and rendered in the Readiness tab gap report panel. Cached in `project.metadata_json["readiness_gap_report"]`; invalidated on project update.

---

## Out of Scope

- External project sponsor self-submission (R5b — August 2026)
- Email notifications when a project is ready to graduate
- Bulk-graduating multiple incubation projects
- Incubation-specific document templates (financial model Excel download)

---

## Success Criteria

- A facilitator can create a project in Incubation status using the existing New Project form
- The Readiness tab shows correct per-criterion status derived from existing scoring
- Martin's gap report loads and gives specific, actionable guidance
- "Graduate to Draft" is disabled until score ≥ threshold (default 40)
- Incubation projects do not appear in investor-facing Deal Room views
- Admin can adjust the graduation threshold in Platform Settings
- All existing pipeline tests continue to pass

---

## Files Changed

| File | Change |
|---|---|
| `backend/app/models/models.py` | Add `INCUBATION` to `ProjectStatus` enum |
| `backend/alembic/versions/r5_incubation_*.py` | New migration: add enum value + seed setting |
| `backend/app/services/lifecycle_service.py` | Add INCUBATION → DRAFT transition with score gate |
| `backend/app/services/project_pipeline_service.py` | `ingest_project_proposal` — honour `start_in_incubation` flag |
| `backend/app/api/routes/pipeline.py` | Role-filter INCUBATION; new `readiness-gap` endpoint; `advance` gate |
| `backend/app/schemas/pipeline_schemas.py` | Add `start_in_incubation` to `ProjectIngest`; add `ReadinessGapRead` schema |
| `frontend/src/types/pipeline.ts` | Add INCUBATION status |
| `frontend/src/pages/DealPipeline.tsx` | Incubation row styles + filter |
| `frontend/src/pages/NewProject.tsx` | Incubation toggle |
| `frontend/src/pages/ProjectDetails.tsx` | Readiness tab visibility |
| `frontend/src/components/pipeline/ReadinessTab.tsx` | New component |
| `frontend/src/pages/PlatformSettings.tsx` | Graduation threshold field |
| `frontend/src/services/api.ts` | `getReadinessGap` service |
