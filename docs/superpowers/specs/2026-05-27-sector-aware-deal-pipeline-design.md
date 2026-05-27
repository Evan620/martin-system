# Sector-aware Deal Pipeline — Design

_Date: 2026-05-27_

## Problem

The deal pipeline, project intake, and project cards leak **agribusiness-specific**
content into every TWG sector. The platform serves four sectors but the UI and
some data fields assume agriculture:

- Pipeline tabs list only 3 sectors (`Infrastructure / Energy / Agriculture`);
  Minerals and Digital are missing, and the labels don't match the real pillars.
- Value-chain stages (`Inputs & Seeds`, `Post-Harvest`, `Cold Chain`,
  `Digital Agri-Platform`) are shown in the intake form **and** on project cards
  for every sector, regardless of pillar.
- `smallholder_farmers_reached` and agri `certifications_held` live on the shared
  Project model and surface for all sectors.
- The Buyer/Offtake database and its matching algorithm are 100% commodity-based;
  a Digital or Energy project scores 0 and the feature is meaningless for them.
- `NewProject.tsx` has no branching on the selected pillar.

What is already multi-sector and must stay untouched:

- Backend `TWGPillar` enum contains all sectors; every project links to a sector
  via `twg_id`.
- WAIIS / AfCEN scoring (9 criteria) is sector-neutral.
- Core intake fields (country, sponsor, investment, financing) are generic.

## Goal

**Sector-aware fields** with a single shared pipeline and shared scoring. The
intake form, project cards, and pipeline tabs adapt to the project's sector. Agri
keeps its existing fields; Energy, Minerals, and Digital get their own relevant
fields. Buyer/offtake matching is gated to Agribusiness. No data migration of
existing rows; one additive column only.

## The four sectors

Canonical pillars (from backend `TWGPillar`, human-readable names used in the form):

| Key (backend enum)                        | Display label                                   |
|-------------------------------------------|-------------------------------------------------|
| `agriculture_food_systems`                | Agribusiness & Food Systems Transformation      |
| `energy_infrastructure`                   | Energy Trade & Industrial Growth                |
| `critical_minerals_industrialization`     | Strategic Minerals & Natural Resource Development |
| `digital_economy_transformation`          | Digital Transformation                          |

(`protocol_logistics` and `resource_mobilization` exist in the enum but are not
investment-project sectors and are already hidden elsewhere; they remain excluded
from the pipeline sector tabs.)

## Architecture — config-driven registry + one JSON column

### Frontend: `frontend/src/config/sectorConfig.ts` (new)

Single source of truth. Exported map keyed by pillar:

```ts
type FieldType = 'text' | 'number' | 'select' | 'multiselect' | 'toggle';

interface FieldDef {
  key: string;            // stored under sector_details[key] (non-agri) or mapped column (agri)
  label: string;
  type: FieldType;
  options?: string[];     // for select / multiselect
  optional?: boolean;
  card?: boolean;         // show in the 1-line project-card summary
}

interface SectorConfig {
  pillarKey: string;              // backend enum value
  label: string;                  // display name
  usesOfftake: boolean;           // gates Buyer DB + offtake matching
  legacyAgri?: boolean;           // true only for agriculture_food_systems
  fields: FieldDef[];             // sector-specific intake fields
}

export const SECTORS: SectorConfig[] = [ /* the four entries below */ ];
export const sectorByPillar = (pillar?: string): SectorConfig | undefined => ...
```

- **Agribusiness** is marked `legacyAgri: true` and `usesOfftake: true`. Its
  bespoke fields continue to read/write the existing typed columns
  (`value_chain_stages`, `smallholder_farmers_reached`, `certifications_held`,
  employment %). The config describes them for display/branching but the form
  keeps its current persistence path — no behavior change for agri.
- **Energy / Minerals / Digital** have `usesOfftake: false` and their fields
  persist to the new `sector_details` JSON blob.

### Backend: one additive migration

- Add nullable `sector_details JSONB` (default `NULL`) to the `Project` table.
- `ProjectCreate` / `ProjectUpdate` schemas accept optional `sector_details: dict`.
- Create/update endpoints persist it verbatim. No validation of inner keys in v1
  (the frontend config is the contract); store as-is.
- Scoring service, buyer matching, and all existing columns are unchanged.

## Per-sector field sets

### Universal (all sectors — unchanged behavior)
pillar, lead country, company, subsector, project sponsor, cross-border toggle,
investment amount, financing structure, **gender-intentional**, **youth-focused**,
plus a universal **jobs / beneficiaries created** (number).

### Agribusiness & Food Systems — existing, unchanged
value-chain stages, smallholder farmers reached, women/youth employment %,
certifications, offtake buyers (Buyer DB).

### Energy Trade & Industrial Growth → `sector_details`
- `asset_type` — select: Solar · Hydro · Wind · Gas · Transmission · Industrial plant *(card)*
- `capacity_mw` — number, "Installed / planned capacity (MW)" *(card)*
- `offtake_status` — select: PPA signed · Under negotiation · None *(card)*
- `grid_connection` — select: On-grid · Mini-grid · Off-grid
- `annual_output_gwh` — number, optional

### Strategic Minerals & Natural Resource Development → `sector_details`
- `mineral_types` — multiselect: Lithium · Bauxite · Gold · Iron ore · … (+ free entry) *(card)*
- `project_stage` — select: Exploration · Feasibility · Development · Production *(card)*
- `reserve_estimate` — text, "Estimated reserves / resource size"
- `processing_level` — select: Raw export · Beneficiation · Refining *(card)*
- `permits_esg` — text, "Key permits & ESG status (EIA, mining licence)"

### Digital Transformation → `sector_details`
- `solution_type` — select: Platform · Infrastructure / data centre · Connectivity · Fintech · E-gov *(card)*
- `target_users` — number, "Target users / beneficiaries" *(card)*
- `infrastructure_tier` — select: Software-only · Cloud · Physical infra
- `data_regulatory` — text, "Data & regulatory posture (residency, licences)"
- `cross_border_dpi` — toggle, "Cross-border digital public infrastructure"

## UI / code changes

1. **`sectorConfig.ts`** — new canonical config (above).
2. **Pipeline tabs** (`DealPipeline.tsx`) — replace the hardcoded 3-entry
   `PILLAR_TABS` with `All projects` + the four sectors derived from `SECTORS`.
   Each tab sends a lowercase substring token the backend `ilike` pillar filter
   matches against the stored human-readable pillar name: `agribusiness`,
   `energy`, `mineral`, `digital`. (`SECTORS` carries this `filterToken` per entry.)
3. **Intake form** (`NewProject.tsx`) — always render universal fields; render the
   selected pillar's `fields` group dynamically below them. The value-chain block
   renders **only** when pillar is Agribusiness. Energy/Minerals/Digital field
   groups read/write `formData.sector_details`.
4. **Project cards** (`DealPipeline.tsx`) — the value-chain row renders only for
   agri. Other sectors render a single summary line built from the `card: true`
   fields in their config (e.g. `120 MW · Solar · PPA signed`).
5. **Buyer DB / matching** — the `Buyers` view-mode tab and offtake matching are
   shown only when `usesOfftake` applies (agri). For non-agri context the tab is
   hidden, or shows the note "Offtake matching applies to Agribusiness projects."
6. **Backend** — add nullable `sector_details JSONB`; accept/persist it in
   create/update. Scoring untouched.

## Out of scope (explicitly not in this iteration)
- Per-sector scoring weights (scoring stays shared).
- Per-sector offtaker databases for Energy/Digital (only agri offtake in v1).
- Migrating existing agri columns into `sector_details` (agri keeps its columns).
- SQL-level filtering on `sector_details` values.

## Risks & mitigations
- **Pillar key mismatch** between frontend tabs and backend `ilike` filter — use a
  stable mapping in `sectorConfig.ts` and verify each tab returns the right rows.
- **Existing agri projects** must render unchanged — agri persistence path is left
  exactly as-is; only non-agri sectors use the new JSON column.
- **RBAC** — new form fields sit inside the same `canEdit` guards; counts of guards
  must not change.
