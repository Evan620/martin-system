# Deal Pipeline — AfCEN Priority Gaps Implementation Spec
**Date:** 2026-05-21  
**Author:** Brainstorming session with AI  
**Source:** Carren Mwanzia benchmark analysis (AGRF / Africa Investment Forum / FAO Hand-in-Hand)  
**Scope:** All 9 priority gaps (R1–R9) across 4 implementation phases

---

## Overview

The AfCEN Deal Pipeline currently has 11 project statuses, 6 WAIIS scoring criteria, an investor matching system, and a 4-section investment template. This spec adds 9 priority gaps identified in Carren's benchmark analysis, organized into 4 delivery phases aligned to the WAIIS 2026 Summit deadlines.

**Architecture decision:** Additive in-place (Approach A) — extend existing models, services, and tables. No new service files for phases 1–2; phases 3–4 add service files where functional separation is warranted.

---

## Phase 1 — Scoring & Classification (June 2026)
*Covers: R1, R2, R3, R4*

### R1 — Value Chain Sub-classification

**What:** Every project must be tagged with the agri-value-chain stage(s) it operates in.

**Data model:**
- New column on `projects`: `value_chain_stages text[]` (nullable, multi-select)
- Valid values: `INPUTS`, `PRODUCTION`, `PROCESSING`, `LOGISTICS`, `RETAIL`

**Frontend:**
- Multi-select chip group in `NewProject.tsx` and `EditProject.tsx`, Section A (Classification)
- Tags rendered as coloured badges on pipeline list rows
- Filterable in pipeline list (add to pillar/status filter row)

**Backend:** No scoring logic — purely classification and filtering. Expose as filter param on `GET /pipeline/`.

---

### R2 — Gender & Youth Mandatory Tags

**What:** Projects must declare the percentage of women and youth (18–35) employed. Missing or below-threshold values block pipeline advancement.

**Data model:**
- New columns on `projects`: `women_employment_pct float`, `youth_employment_pct float` (both nullable)
- New admin config table `platform_settings` (key/value): `gender_threshold_pct` (default 30), `youth_threshold_pct` (default 25)

**Frontend:**
- Two numeric inputs in project form, Section A (Classification), with inline helper text
- Warning banner on project form if below threshold
- Yellow `⚠️ Gender gap` / `⚠️ Youth gap` badge on pipeline list row if below threshold
- Admin settings page: editable threshold values

**Stage gate:**
- `LifecycleService.validate_transition()`: block `UNDER_REVIEW → SUMMIT_READY` if either field is null or below threshold
- Error message returned to frontend with specific field causing the block

**Scoring:**
- `women_employment_pct` and `youth_employment_pct` feed into the Social Impact criterion score (Phase 1 R3)

---

### R3 — Impact Score Split (3 sub-scores)

**What:** Replace the existing "Additionality" criterion with three independent scoring criteria: Climate Impact, Social Impact, and Economic Impact. Admins configure weights for each.

**ScoringCriteria changes:**
- Remove seed entry: `Additionality`
- Add seed entries:
  - `Climate Impact` — default weight 10%
  - `Social Impact` — default weight 10%
  - `Economic Impact` — default weight 8%
- Existing criteria default weights reduced to fit 8-criterion 100% total:
  - Readiness: 18%, Scale of Impact: 13%, Country Enablement: 15%, Bankability: 18%, Scalability: 3%
  - (Was: Readiness 20%, Scale 15%, Country 20%, Bankability 25%, Scalability 5% across 6 criteria)
- Total criteria after R3 + R4: 8 (weights must sum to 100%)
- Seed logic is **create-if-not-exists only** — never overwrites weights that an admin has already set

**Scoring logic in `ProjectPipelineService.assess_project_readiness()`:**

| Criterion | Inputs | Score logic |
|-----------|--------|-------------|
| Climate Impact | `ghg_avoided_target`, `climate_impact` text, renewable energy indicators in docs | 40 pts doc analysis + 30 pts GHG target > 0 + 30 pts keyword match (solar/wind/GHG/renewable) |
| Social Impact | `jobs_construction + jobs_om`, `smallholder_farmers_reached`, `women_employment_pct`, `youth_employment_pct` | 25 pts jobs > 100 + 25 pts smallholders > 500 + 25 pts women ≥ threshold + 25 pts youth ≥ threshold |
| Economic Impact | `macroeconomic_roi`, `revenue_model`, investment size | 40 pts financial model present + 30 pts ROI text + 30 pts investment > $5M |

**Migration:** Existing `ProjectScoreDetail` rows with `criterion_name = 'Additionality'` are migrated: set `criterion_name = 'Climate Impact'` and duplicate the row twice more for Social and Economic, each with the same original score divided by 3 (rounded). This preserves history without losing data.

---

### R4 — ECOWAS Regional Integration Criterion

**What:** Add an 8th scoring criterion measuring cross-border integration within the ECOWAS region.

**ScoringCriteria changes:**
- Add seed entry: `ECOWAS Integration` — default weight 5%

**Scoring logic:**

| Input | Points |
|-------|--------|
| `is_cross_border = true` | +40 pts |
| Lead country is ECOWAS member state | +20 pts |
| Document mentions ECOWAS / regional integration | +25 pts (LLM doc analysis) |
| Multiple ECOWAS beneficiary countries mentioned | +15 pts |

**ECOWAS member states list** (hardcoded in service): Benin, Burkina Faso, Cape Verde, Côte d'Ivoire, Gambia, Ghana, Guinea, Guinea-Bissau, Liberia, Mali, Mauritania, Niger, Nigeria, Senegal, Sierra Leone, Togo.

**Default weight set to 5%** — lower than other criteria to reflect it being a bonus criterion, not a core bankability factor. Configurable by admin.

---

### Phase 1 — Schema migration

One Alembic migration (`add_classification_scoring_phase1`):
```
ALTER TABLE projects ADD COLUMN value_chain_stages text[];
ALTER TABLE projects ADD COLUMN women_employment_pct float;
ALTER TABLE projects ADD COLUMN youth_employment_pct float;
CREATE TABLE platform_settings (key text PRIMARY KEY, value text, updated_at timestamp);
INSERT INTO platform_settings VALUES ('gender_threshold_pct', '30', now());
INSERT INTO platform_settings VALUES ('youth_threshold_pct', '25', now());
```
Scoring criteria table is updated via service seed logic (idempotent upsert on startup).

---

## Phase 2 — Stage 0 Readiness Track (July 2026)
*Covers: R5*

### R5 — Pre-Pipeline Investment Readiness Track

**What:** A separate lightweight track for early-stage projects not yet ready for the main pipeline. Lives as a new "🌱 Readiness Track" tab inside the Deal Pipeline page. Projects graduate to the main pipeline (DRAFT status) when all checklist items are complete.

**Data model — two new tables:**

`readiness_projects`:
```
id uuid PK
name text NOT NULL
pillar text
lead_country text
contact_name text
contact_email text
created_by uuid FK users
created_at timestamp
graduated_at timestamp (null until graduated)
pipeline_project_id uuid FK projects (null until graduated)
```

`readiness_checklist_items`:
```
id uuid PK
readiness_project_id uuid FK readiness_projects
item_key text (enum: FEASIBILITY, LAND_RIGHTS, GOV_SUPPORT, ENV_ASSESSMENT, FINANCIAL_MODEL, CORE_TEAM)
completed boolean DEFAULT false
completed_at timestamp
document_id uuid FK documents (optional — for uploaded evidence)
notes text
```

**Checklist items (6, fixed):**
1. `FEASIBILITY` — Preliminary feasibility study
2. `LAND_RIGHTS` — Land rights / site control evidence
3. `GOV_SUPPORT` — Government support / no-objection letter
4. `ENV_ASSESSMENT` — Environmental pre-assessment (ESIA screening)
5. `FINANCIAL_MODEL` — Preliminary financial model
6. `CORE_TEAM` — Core project team identified

**Graduate action (`POST /pipeline/readiness/{id}/graduate`):**
1. Verify all 6 checklist items are `completed = true`
2. Create a new `Project` record in `DRAFT` status, copying `name`, `pillar`, `lead_country`, `key_contact_name`, `key_contact_email`
3. Set `readiness_projects.graduated_at = now()` and `pipeline_project_id = new_project.id`
4. Return the new project ID for frontend redirect

**Routes:**
- `GET /pipeline/readiness/` — list all readiness projects
- `POST /pipeline/readiness/` — create new readiness project
- `GET /pipeline/readiness/{id}` — get with checklist items
- `PATCH /pipeline/readiness/{id}/checklist/{item_key}` — mark item complete/incomplete
- `POST /pipeline/readiness/{id}/graduate` — graduate to pipeline

**Frontend:**
- New tab "🌱 Readiness Track" in `DealPipeline.tsx` tab bar with unread count badge
- Project list cards with 6-segment progress bar
- Detail modal/page with checklist items, upload slots, "Martin review" button (calls AI insights)
- "Graduate to Pipeline →" CTA button shown only when all 6 items are complete
- Graduated projects shown as greyed out with a link to the created pipeline project

**Alembic migration:** `add_readiness_track_phase2` — creates both tables.

---

## Phase 3 — Matching & Finance (August 2026)
*Covers: R6, R7*

### R6 — Buyer / Offtake Matching

**What:** Match projects to potential buyers/offtakers in addition to investors. Parallel infrastructure to the existing investor matching system.

**Data model:**

`buyers`:
```
id uuid PK
name text NOT NULL
commodity_types text[]
volume_mt_per_year float
contract_term_years int
price_floor_usd float
geographic_focus text[]
notes text
created_by uuid FK users
created_at timestamp
```

`project_buyer_matches`:
```
id uuid PK
project_id uuid FK projects
buyer_id uuid FK buyers
match_score int (0–100)
status text (DETECTED | CONTACTED | INTERESTED | NEGOTIATING | COMMITTED)
match_rationale text
created_at timestamp
updated_at timestamp
```

**Matching logic (`BuyerMatchingService.match_project_to_buyers()`):**

| Signal | Points |
|--------|--------|
| Commodity type overlaps with `value_chain_stages` | +40 pts |
| Buyer volume fits project production capacity | +25 pts |
| Buyer geographic focus includes project `lead_country` | +20 pts |
| Project is ECOWAS cross-border and buyer has ECOWAS focus | +15 pts |

Score threshold for a match to appear: ≥ 50 pts.

**Frontend:**
- "Matches" tab in `ProjectDetails.tsx` gets two sub-tabs: "Investor Matches" (existing) and "Buyer / Offtake" (new)
- New admin page `BuyerDatabase.tsx` (role-gated: ADMIN, SECRETARIAT_LEAD) — same pattern as `InvestorDatabase.tsx`
- Match cards show: buyer name, commodity, volume, contract terms, match score, match rationale chips, status badge, "Contact buyer" button

**Routes:**
- `GET /pipeline/buyers/` — list buyers
- `POST /pipeline/buyers/` — create buyer (admin only)
- `PATCH /pipeline/buyers/{id}` — update buyer
- `DELETE /pipeline/buyers/{id}` — soft delete
- `GET /pipeline/{id}/buyer-matches` — get matches for project
- `POST /pipeline/{id}/buyer-match` — trigger matching run

---

### R7 — Blended Finance Structuring Module

**What:** AI-generated grant/concessional/commercial split recommendation based on project profile. Displayed in the project Financials tab. User can adjust and save.

**Data model:**

`blended_finance_recommendations`:
```
id uuid PK
project_id uuid FK projects
grant_pct float
concessional_pct float
commercial_pct float
rationale text
generated_at timestamp
saved boolean DEFAULT false
saved_at timestamp
saved_by uuid FK users
```

**Generation logic (`ProjectPipelineService._generate_blended_finance()`):**

Rule-based starting point (then refined by LLM rationale):

| Project signal | Adjustment |
|----------------|------------|
| Bankability score < 60 | +10% grant, -5% commercial |
| Agriculture sector | +5% concessional (AfDB MSME eligibility) |
| Cross-border ECOWAS | +5% concessional (AfDB regional window) |
| GHG target > 0 | +5% grant (GCF eligibility) |
| Investment < $10M | +5% grant (AGRA/smallholder funds) |

Default structure: 15% grant / 35% concessional / 50% commercial. Adjustments applied, then renormalized to sum to 100%.

LLM call: pass project summary + rule-based percentages → generate 2–3 sentence rationale naming specific facilities (AGRA, GCF, AfDB) relevant to this project.

**Frontend:**
- New "Blended Finance" panel at bottom of Financials tab in `ProjectDetails.tsx`
- Stacked horizontal bar showing grant/concessional/commercial percentages
- Martin rationale text below bar
- Three editable number inputs for manual adjustment
- "Save structure to project" button
- "Re-analyse" button triggers fresh LLM call
- Dollar amounts computed from `investment_size` × percentages

**Routes:**
- `GET /pipeline/{id}/blended-finance` — get saved recommendation (null if not yet generated)
- `POST /pipeline/{id}/blended-finance/generate` — generate new recommendation
- `PATCH /pipeline/{id}/blended-finance/{rec_id}` — update percentages + save

**Alembic migration:** `add_buyer_blended_finance_phase3` — creates `buyers`, `project_buyer_matches`, `blended_finance_recommendations`.

---

## Phase 4 — Geo Intelligence & Impact Monitoring (Sept–Nov 2026)
*Covers: R8, R9*

### R8 — Geospatial / Sentinel-2 Land Analysis

**What:** Optional GPS coordinates on a project trigger a Sentinel-2 satellite analysis that augments the Readiness criterion score. Analysis shown in a site panel on the project Overview tab.

**Data model:**
- New columns on `projects`: `site_lat float`, `site_lon float`
- New table `project_geospatial_data`:
  ```
  id uuid PK
  project_id uuid FK projects
  ndvi float
  water_proximity_km float
  land_use_description text
  land_use_smallholder_pct float
  geo_score_boost int (0–15)
  analysed_at timestamp
  raw_response jsonb
  ```

**GeoSpatialService:**
- Calls Copernicus Open Access Hub API (requires free account registration at dataspace.copernicus.eu — no paid tier needed for Sentinel-2 basic tiles)
- Fetches latest Sentinel-2 tile for lat/lon bounding box
- Computes NDVI from NIR/Red bands
- Classifies land use using band ratios
- Derives water proximity from Landsat water mask
- Result cached 30 days (re-fetched on rescore if >30 days old)
- Geo score boost added to Readiness criterion raw score (capped so total criterion doesn't exceed 100)
- Graceful fallback: if API unreachable or coords outside coverage, geo boost = 0, no error surfaced to user

| Signal | Boost |
|--------|-------|
| NDVI > 0.5 (good vegetation) | +5 pts |
| Water within 2 km | +5 pts |
| Smallholder land use detected | +5 pts |

**Frontend:**
- `site_lat` / `site_lon` fields in project form (Section A)
- "Site Analysis" panel in project Overview tab (visible when coordinates exist)
- Pseudo-satellite tile (coloured div representing NDVI gradient) + metrics grid
- "Geo score boost: +N pts applied to Readiness" label

**Routes:**
- Coordinates saved via existing `PATCH /pipeline/{project_id}`
- `POST /pipeline/{project_id}/rescore` — already triggers geo analysis if coords present

---

### R9 — Post-Commitment Impact Monitoring

**What:** Quarterly actual-vs-target tracking for projects in COMMITTED or IMPLEMENTED status. New "Impact Monitoring" tab in project detail.

**Data model:**

`impact_log_entries`:
```
id uuid PK
project_id uuid FK projects
period_label text (e.g. "Q1 2026")
period_start date
period_end date
jobs_created int
ghg_avoided_tco2 float
smallholders_reached int
women_jobs_actual int
youth_jobs_actual int
investment_deployed_usd float
notes text
logged_by uuid FK users
logged_at timestamp
```

Targets come from existing Project columns: `jobs_construction + jobs_om`, `ghg_avoided_target`, `smallholder_farmers_reached`, `investment_size`.

**Frontend:**
- "Impact Monitoring" tab in `ProjectDetails.tsx` — visible only when `status IN (COMMITTED, IMPLEMENTED)`
- 4 metric cards with actual / target + progress bar (Jobs, GHG, Smallholders, $ Deployed)
- Historical table: one row per quarter
- "+ Log Q[N] actuals" button opens a simple form modal
- Women and youth actual job counts tracked separately for gender/youth reporting

**Routes:**
- `GET /pipeline/{id}/impact-log` — list entries
- `POST /pipeline/{id}/impact-log` — create entry (SECRETARIAT_LEAD, ADMIN only)
- `DELETE /pipeline/{id}/impact-log/{entry_id}` — remove entry (ADMIN only)

**Alembic migration:** `add_geo_impact_monitoring_phase4` — alters `projects` for coordinates, creates `project_geospatial_data`, `impact_log_entries`.

---

## Summary Table

| Gap | Description | Phase | Deadline | DB changes | Service changes | UI changes |
|-----|-------------|-------|----------|-----------|-----------------|------------|
| R1 | Value chain sub-classification | 1 | Jun 2026 | `projects.value_chain_stages[]` | Filter logic | Form chips, list badges, filter |
| R2 | Gender & youth mandatory tags | 1 | Jun 2026 | `projects.women/youth_pct`, `platform_settings` | Stage gate in LifecycleService | Form fields, warning badge, admin settings |
| R3 | Impact score split (3 criteria) | 1 | Jun 2026 | ScoringCriteria seed update, score migration | 3 new scoring functions | Score breakdown panel |
| R4 | ECOWAS integration criterion | 1 | Jul 2026 | ScoringCriteria seed | 1 new scoring function | Score breakdown panel |
| R5 | Stage 0 readiness track | 2 | Jul 2026 | `readiness_projects`, `readiness_checklist_items` | Graduate action | New tab, checklist view, progress bar |
| R6 | Buyer / offtake matching | 3 | Aug 2026 | `buyers`, `project_buyer_matches` | BuyerMatchingService | Matches sub-tab, Buyer DB page |
| R7 | Blended finance structuring | 3 | Aug 2026 | `blended_finance_recommendations` | LLM generation + rule engine | Finance panel with stacked bar |
| R8 | Geospatial / Sentinel-2 | 4 | Sep 2026 | `projects.site_lat/lon`, `project_geospatial_data` | GeoSpatialService (Copernicus API) | Site analysis panel, coord fields |
| R9 | Post-commitment monitoring | 4 | Nov 2026 | `impact_log_entries` | Log CRUD | Impact Monitoring tab |

## Migrations (one per phase)
1. `add_classification_scoring_phase1`
2. `add_readiness_track_phase2`
3. `add_buyer_blended_finance_phase3`
4. `add_geo_impact_monitoring_phase4`

## Out of scope
- Public-facing investor portal
- Automated government data feeds
- Real-time co-investment syndication
- Mobile app
