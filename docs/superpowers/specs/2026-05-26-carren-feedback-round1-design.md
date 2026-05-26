# Carren feedback round 1 — intake form clarity

**Date:** 2026-05-26
**Status:** Approved, ready for implementation plan
**Source:** Carren Mwanzia comments on the Bagré PCB walkthrough doc (`1IaigSUx7DEHtJBw4NYX5cpLLfvVV7j5wHDffw_BPZmI`)

## Background

Carren reviewed the end-to-end walkthrough doc and left two comments on the intake-form table (Section 3.2):

1. On "Investment Amount $550M": *"We need to ask someone to specify funding structure if available. But don't make it a mandatory field"*
2. On "Gender-Intentional Design Yes": *"can we add pop up info that describes what this means? people may need to have a threshold to be able to inform how they select yes or no"*

Both are intake-form clarity issues. Neither requires schema changes to the database — the `financing_structure` Text column already exists on the `Project` model and on the `ProjectUpdate` / `ProjectPipelineRead` schemas. It is only missing from the `ProjectIngest` schema and the New Project form.

## Goals

- Make the existing `financing_structure` column reachable from the intake form, optional, with a sensible placeholder.
- Help submitters understand what "Yes" actually means for Gender-Intentional Design and Youth Employment Focus before they pick.
- No backend logic change, no migration, no scoring change.

## Non-goals

- No structured funding-tranche modelling (Carren's comment was a "prompt the submitter" note, not a feature ask). The existing free-text column is sufficient.
- No tooltip on other intake fields. YAGNI — extend the pattern only if reviewers ask for it.
- No change to the WAIIS scoring rubric or to the gender / youth justification text fields. Those stay.

## Part 1 — Surface `financing_structure` on intake

### Backend
- `backend/app/schemas/pipeline_schemas.py` — add `financing_structure: Optional[str] = None` to `ProjectIngest` (mirrors line in `ProjectUpdate`).
- No migration. The `projects.financing_structure` Text column already exists.
- `ingest_project_proposal()` in `project_pipeline_service.py` already reads `data.get(...)` style. Add `financing_structure=data.get("financing_structure")` to the `Project(...)` constructor block (same one we patched for `site_lat` / `site_lon` / `site_location_name`).

### Frontend
- `frontend/src/pages/NewProject.tsx`:
  - Add `financing_structure: ''` to `formData` initial state.
  - Add a 2-row textarea below Investment Amount, in the same Financials section.
  - Label: "Funding Structure" with " (optional)" suffix.
  - Placeholder: `e.g. 60% commercial debt + 40% concessional from DFIs; PPP with sovereign guarantee`.
  - Include the value in the submit payload: `financing_structure: formData.financing_structure || undefined`.

## Part 2 — Info-tooltips on Gender / Youth

### New component
- `frontend/src/components/InfoTooltip.tsx`:
  - Props: `{ text: string; ariaLabel?: string }`.
  - Renders a small `(i)` icon using the existing Material Symbols `info_outline` glyph (same icon family the rest of the app uses: `dashboard`, `calendar_month`, `arrow_back`, …).
  - Hover-to-show on desktop; tap-to-toggle on mobile.
  - Popover bubble: max-width ~320px, theme-tokenised background (use existing surface color), `role="tooltip"`, `aria-describedby` linkage.
  - Close on outside click and on Escape key.

### Placement
- Two instances on `NewProject.tsx`, one next to each label:
  - "Gender-Intentional Design *" → InfoTooltip
  - "Youth Employment Focus *" → InfoTooltip

### Copy (final, to be reviewed once shipped)

**Gender-Intentional Design — Yes if the project explicitly:**
- Targets women-led businesses or women as key beneficiaries, or
- Sets a measurable women-employment or women-ownership target of at least 30%, or
- Adopts a gender action plan as part of project design.

*Mark "No" if gender outcomes are incidental rather than designed in.*

**Youth Employment Focus — Yes if the project explicitly:**
- Targets under-35s as at least 30% of jobs created, or
- Includes a youth training, aggregator, or kiosk programme, or
- Has a dedicated youth entrepreneurship pipeline.

*Mark "No" if youth outcomes are incidental.*

(Thresholds align with the WAIIS scoring rubric's R2 sub-criterion.)

## Files touched

| File | Change | Lines (est.) |
|---|---|---|
| `backend/app/schemas/pipeline_schemas.py` | add `financing_structure` to `ProjectIngest` | 1 |
| `backend/app/services/project_pipeline_service.py` | wire `financing_structure` into the `Project(...)` constructor | 1 |
| `frontend/src/components/InfoTooltip.tsx` | new component | ~50 |
| `frontend/src/pages/NewProject.tsx` | new state key, new textarea, two `<InfoTooltip>` usages | ~12 |

No migration. No scoring change. No new dependencies.

## Testing

Manual smoke (same path as the Bagré bug-fix walkthrough we just ran):

1. `/deal-pipeline/new` — confirm Funding Structure textarea is present, optional.
2. Hover the `(i)` next to Gender → tooltip shows the criteria.
3. Hover the `(i)` next to Youth → tooltip shows the criteria.
4. Tap on mobile / narrow viewport → tooltip toggles on tap, closes on outside click.
5. Fill out a full intake with funding structure → submit → verify the value persists by hitting `GET /api/v1/pipeline/{id}` and checking `financing_structure`.
6. Submit intake leaving Funding Structure blank → should succeed (optional).

## Rollout

Single commit, single deploy. No data backfill. No feature flag.

## Open questions

None. Carren's comments are precise; both items are intake-only.

## Next step

Invoke `writing-plans` to produce the implementation plan.
