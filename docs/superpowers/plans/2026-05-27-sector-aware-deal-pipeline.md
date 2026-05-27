# Sector-aware Deal Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the deal pipeline, project intake, and project cards adapt to all four TWG sectors instead of showing agribusiness fields everywhere.

**Architecture:** A single frontend config (`sectorConfig.ts`) is the source of truth for the four sectors and their bespoke intake fields. Non-agri bespoke data persists to one new nullable `sector_details JSONB` column on `Project`; agribusiness keeps its existing typed columns. Shared pipeline list and WAIIS/AfCEN scoring are untouched.

**Tech Stack:** React + TypeScript (Vite) frontend; FastAPI + SQLAlchemy + Alembic backend; PostgreSQL.

Reference spec: `docs/superpowers/specs/2026-05-27-sector-aware-deal-pipeline-design.md`

---

## File Structure

- **Create** `frontend/src/config/sectorConfig.ts` — canonical sector registry + field schemas + helpers.
- **Modify** `frontend/src/types/pipeline.ts` — add `sector_details?: Record<string, any>` to `Project`.
- **Modify** `frontend/src/pages/NewProject.tsx` — sector-aware intake (universal fields always; sector field group by pillar; value-chain block agri-only; sector fields → `sector_details`).
- **Modify** `frontend/src/pages/DealPipeline.tsx` — pillar tabs from config; project-card value-chain row agri-only + sector summary line for others; gate Buyers tab to agri sectors.
- **Modify** `backend/app/models/models.py` — add `sector_details` column to `Project`.
- **Modify** `backend/app/schemas/pipeline_schemas.py` — `ProjectIngest` / `ProjectUpdate` / `ProjectPipelineRead` accept/return `sector_details`; relax `value_chain_stages` to optional.
- **Modify** `backend/app/services/project_pipeline_service.py` — persist `sector_details` on ingest + update.
- **Create** Alembic migration — add `sector_details JSONB NULL` to `projects`.

---

## Task 1: Backend — add `sector_details` column to the Project model

**Files:**
- Modify: `backend/app/models/models.py:626` (near `value_chain_stages`)

- [ ] **Step 1: Add the column**

In `backend/app/models/models.py`, find the `Project` class line:
```python
    value_chain_stages: Mapped[Optional[List[str]]] = mapped_column(ARRAY(Text), nullable=True)
```
Add directly below it:
```python
    # Sector-specific bespoke intake fields for non-agribusiness sectors
    # (energy / minerals / digital). Shape is defined by frontend sectorConfig.ts;
    # stored verbatim. Agribusiness continues to use its dedicated columns above.
    sector_details: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
```
(`JSON` is already imported in this file — it is used by `certifications_held`.)

- [ ] **Step 2: Verify the model imports compile**

Run: `cd backend && python -c "from app.models.models import Project; print('sector_details' in Project.__table__.columns)"`
Expected: prints `True`

- [ ] **Step 3: Commit**

```bash
git add backend/app/models/models.py
git commit -m "feat(pipeline): add sector_details column to Project model"
```

---

## Task 2: Backend — Alembic migration for `sector_details`

**Files:**
- Create: `backend/alembic/versions/<autogen>_add_sector_details.py`

- [ ] **Step 1: Generate the migration**

Run: `cd backend && alembic revision -m "add sector_details to projects"`
This prints a new file path under `backend/alembic/versions/`. Open it.

- [ ] **Step 2: Fill in upgrade/downgrade**

Replace the empty `upgrade()` / `downgrade()` with:
```python
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade() -> None:
    op.add_column(
        "projects",
        sa.Column("sector_details", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )

def downgrade() -> None:
    op.drop_column("projects", "sector_details")
```
Keep the auto-generated `revision` / `down_revision` values as written.

- [ ] **Step 3: Apply the migration**

Run: `cd backend && alembic upgrade head`
Expected: completes without error; no other tables touched.

- [ ] **Step 4: Verify the column exists**

Run: `cd backend && python -c "from sqlalchemy import inspect, create_engine; import os; e=create_engine(os.environ['DATABASE_URL']); print('sector_details' in [c['name'] for c in inspect(e).get_columns('projects')])"`
Expected: prints `True` (if `DATABASE_URL` is not set, instead open a DB shell and run `\d projects` — confirm `sector_details` row).

- [ ] **Step 5: Commit**

```bash
git add backend/alembic/versions/
git commit -m "feat(pipeline): migration adds sector_details JSONB to projects"
```

---

## Task 3: Backend — accept/return `sector_details` in schemas; relax value chain

**Files:**
- Modify: `backend/app/schemas/pipeline_schemas.py`

- [ ] **Step 1: Make `value_chain_stages` optional on ingest**

In `ProjectIngest` (around line 61), replace:
```python
    value_chain_stages: List[str] = Field(
        ..., min_length=1,
        description="At least one stage from the controlled vocabulary",
    )
```
with:
```python
    # Optional at intake — only agribusiness projects supply value-chain stages.
    # Other sectors persist their bespoke fields in sector_details instead.
    value_chain_stages: Optional[List[str]] = Field(
        default=None,
        description="Agribusiness stages from the controlled vocabulary (optional)",
    )
    # Sector-specific bespoke fields (energy / minerals / digital). Stored verbatim.
    sector_details: Optional[Dict[str, Any]] = None
```

- [ ] **Step 2: Confirm the validator tolerates None**

The existing `_validate_value_chain_stages` (line 29) returns its input unchanged when falsy. Verify it begins with a guard like `if not stages: return stages`. If it does not, add as the first line:
```python
    if not stages:
        return stages
```

- [ ] **Step 3: Add `sector_details` to `ProjectUpdate`**

In `ProjectUpdate` (after line 132 `youth_employment_pct: Optional[float] = None`), add:
```python
    sector_details: Optional[Dict[str, Any]] = None
```

- [ ] **Step 4: Return `sector_details` in `ProjectPipelineRead`**

In `ProjectPipelineRead` (it already lists `value_chain_stages: Optional[List[str]] = None` around line 245), add directly below that line:
```python
    sector_details: Optional[Dict[str, Any]] = None
```

- [ ] **Step 5: Verify imports + parse**

`Dict` and `Any` are already imported at the top of the file (used by `metadata_json`). Run:
`cd backend && python -c "from app.schemas.pipeline_schemas import ProjectIngest, ProjectUpdate, ProjectPipelineRead; ProjectIngest(twg_id='t', name='n', description='d', investment_size=1, readiness_score=1, strategic_alignment_score=1); print('ok')"`
Expected: prints `ok` (no validation error despite omitting `value_chain_stages`).

- [ ] **Step 6: Commit**

```bash
git add backend/app/schemas/pipeline_schemas.py
git commit -m "feat(pipeline): schemas accept/return sector_details; value_chain optional"
```

---

## Task 4: Backend — persist `sector_details` on ingest and update

**Files:**
- Modify: `backend/app/services/project_pipeline_service.py:807` (ingest) and `:887` (update)

- [ ] **Step 1: Persist on ingest**

In `ingest_project_proposal`, find the `Project(` constructor (around line 807) and the line:
```python
            value_chain_stages=data.get("value_chain_stages"),
```
Add directly below it:
```python
            sector_details=data.get("sector_details"),
```

- [ ] **Step 2: Persist on update**

In `update_project` (around line 887), the function applies incoming fields to the project. Find where it iterates/sets update fields. If it uses a pattern like `for field, value in update_data.items(): setattr(project, field, value)`, no change is needed — confirm `sector_details` is included by the schema's `.model_dump(exclude_unset=True)`. If it sets fields explicitly (a long list of `if data.x is not None: project.x = data.x`), add:
```python
        if "sector_details" in update_fields and update_fields["sector_details"] is not None:
            project.sector_details = update_fields["sector_details"]
```
matching the local variable name used for the dumped update payload in that function.

- [ ] **Step 3: Verify the service imports compile**

Run: `cd backend && python -c "import app.services.project_pipeline_service; print('ok')"`
Expected: prints `ok`

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/project_pipeline_service.py
git commit -m "feat(pipeline): persist sector_details on ingest and update"
```

---

## Task 5: Frontend — the sector config registry

**Files:**
- Create: `frontend/src/config/sectorConfig.ts`

- [ ] **Step 1: Write the config**

Create `frontend/src/config/sectorConfig.ts`:
```ts
export type FieldType = 'text' | 'number' | 'select' | 'multiselect' | 'toggle';

export interface FieldDef {
  key: string;          // sector_details[key] for non-agri sectors
  label: string;
  type: FieldType;
  options?: string[];   // select / multiselect
  optional?: boolean;
  card?: boolean;       // include in the project-card summary line
}

export interface SectorConfig {
  pillarValue: string;   // exact value submitted as `pillar` (matches NewProject pillars[].value)
  label: string;         // display label
  filterToken: string;   // lowercase substring the backend ilike pillar filter matches
  usesOfftake: boolean;  // gates Buyer DB + offtake matching (agri only)
  legacyAgri?: boolean;  // agribusiness uses its own typed columns, not sector_details
  fields: FieldDef[];    // bespoke intake fields (empty for agri — it has its own form blocks)
}

export const SECTORS: SectorConfig[] = [
  {
    pillarValue: 'Agribusiness and Food Systems Transformation',
    label: 'Agribusiness & Food Systems',
    filterToken: 'agribusiness',
    usesOfftake: true,
    legacyAgri: true,
    fields: [],
  },
  {
    pillarValue: 'Energy Trade and Industrial Growth',
    label: 'Energy Trade & Industrial Growth',
    filterToken: 'energy',
    usesOfftake: false,
    fields: [
      { key: 'asset_type', label: 'Asset / generation type', type: 'select',
        options: ['Solar', 'Hydro', 'Wind', 'Gas', 'Transmission', 'Industrial plant'], card: true },
      { key: 'capacity_mw', label: 'Installed / planned capacity (MW)', type: 'number', card: true },
      { key: 'offtake_status', label: 'Offtake / PPA status', type: 'select',
        options: ['PPA signed', 'Under negotiation', 'None'], card: true },
      { key: 'grid_connection', label: 'Grid connection', type: 'select',
        options: ['On-grid', 'Mini-grid', 'Off-grid'] },
      { key: 'annual_output_gwh', label: 'Annual output (GWh)', type: 'number', optional: true },
    ],
  },
  {
    pillarValue: 'Strategic Minerals and Natural Resource Development',
    label: 'Strategic Minerals & Natural Resources',
    filterToken: 'mineral',
    usesOfftake: false,
    fields: [
      { key: 'mineral_types', label: 'Mineral / resource type', type: 'multiselect',
        options: ['Lithium', 'Bauxite', 'Gold', 'Iron ore', 'Manganese', 'Phosphate', 'Cobalt'], card: true },
      { key: 'project_stage', label: 'Project stage', type: 'select',
        options: ['Exploration', 'Feasibility', 'Development', 'Production'], card: true },
      { key: 'reserve_estimate', label: 'Estimated reserves / resource size', type: 'text' },
      { key: 'processing_level', label: 'Processing level', type: 'select',
        options: ['Raw export', 'Beneficiation', 'Refining'], card: true },
      { key: 'permits_esg', label: 'Key permits & ESG status (EIA, mining licence)', type: 'text' },
    ],
  },
  {
    pillarValue: 'Digital Transformation',
    label: 'Digital Transformation',
    filterToken: 'digital',
    usesOfftake: false,
    fields: [
      { key: 'solution_type', label: 'Solution type', type: 'select',
        options: ['Platform', 'Infrastructure / data centre', 'Connectivity', 'Fintech', 'E-gov'], card: true },
      { key: 'target_users', label: 'Target users / beneficiaries', type: 'number', card: true },
      { key: 'infrastructure_tier', label: 'Infrastructure tier', type: 'select',
        options: ['Software-only', 'Cloud', 'Physical infra'] },
      { key: 'data_regulatory', label: 'Data & regulatory posture (residency, licences)', type: 'text' },
      { key: 'cross_border_dpi', label: 'Cross-border digital public infrastructure', type: 'toggle' },
    ],
  },
];

/** Match a stored pillar string (human name or token) to a sector config. */
export function sectorByPillar(pillar?: string | null): SectorConfig | undefined {
  if (!pillar) return undefined;
  const p = pillar.toLowerCase();
  return SECTORS.find(s => p.includes(s.filterToken) || p === s.pillarValue.toLowerCase());
}

/** Build a one-line card summary from a project's sector + sector_details. */
export function sectorCardSummary(pillar: string | undefined, details?: Record<string, any> | null): string | null {
  const cfg = sectorByPillar(pillar);
  if (!cfg || cfg.legacyAgri || !details) return null;
  const parts = cfg.fields
    .filter(f => f.card)
    .map(f => {
      const v = details[f.key];
      if (v == null || v === '' || (Array.isArray(v) && v.length === 0)) return null;
      return Array.isArray(v) ? v.join(', ') : String(v);
    })
    .filter(Boolean);
  return parts.length ? parts.join(' · ') : null;
}
```

- [ ] **Step 2: Typecheck**

Run: `cd frontend && npx tsc --noEmit -p tsconfig.json 2>&1 | grep sectorConfig`
Expected: no output (clean).

- [ ] **Step 3: Commit**

```bash
git add frontend/src/config/sectorConfig.ts
git commit -m "feat(pipeline): add sector config registry"
```

---

## Task 6: Frontend — add `sector_details` to the Project type

**Files:**
- Modify: `frontend/src/types/pipeline.ts:107` (near `value_chain_stages?`)

- [ ] **Step 1: Add the field**

In `frontend/src/types/pipeline.ts`, find inside `interface Project`:
```ts
    value_chain_stages?: string[];
```
Add below it:
```ts
    sector_details?: Record<string, any>;
```

- [ ] **Step 2: Typecheck**

Run: `cd frontend && npx tsc --noEmit -p tsconfig.json 2>&1 | grep pipeline.ts`
Expected: no output.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/types/pipeline.ts
git commit -m "feat(pipeline): add sector_details to Project type"
```

---

## Task 7: Frontend — pipeline tabs from config

**Files:**
- Modify: `frontend/src/pages/DealPipeline.tsx` (`PILLAR_TABS` definition ~line 224 and the `activeTab` filter usage)

- [ ] **Step 1: Import the config**

At the top of `DealPipeline.tsx` with the other imports add:
```ts
import { SECTORS } from '../config/sectorConfig';
```

- [ ] **Step 2: Replace `PILLAR_TABS`**

Find:
```ts
  const PILLAR_TABS = [
    { key: 'all', label: 'All projects' },
    { key: 'infrastructure', label: 'Infrastructure' },
    { key: 'energy', label: 'Energy' },
    { key: 'agriculture', label: 'Agriculture' },
  ];
```
Replace with:
```ts
  const PILLAR_TABS = [
    { key: 'all', label: 'All projects' },
    ...SECTORS.map(s => ({ key: s.filterToken, label: s.label })),
  ];
```
The existing tab rendering iterates `PILLAR_TABS` and sets `activeTab` to `key`, which is sent to `pipelineService.listProjects(..., activeTab !== 'all' ? activeTab : undefined, ...)`. The backend `pillar` filter is a case-insensitive substring (`ilike %token%`), so `agribusiness` / `energy` / `mineral` / `digital` match the stored human-readable pillar names.

- [ ] **Step 3: Typecheck**

Run: `cd frontend && npx tsc --noEmit -p tsconfig.json 2>&1 | grep DealPipeline`
Expected: no output.

- [ ] **Step 4: Manual verify**

Run the app (`cd frontend && npm run dev`), open `/deal-pipeline`, confirm four sector tabs appear (Agribusiness, Energy, Strategic Minerals, Digital) and each filters the table to matching projects.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/DealPipeline.tsx
git commit -m "feat(pipeline): drive pillar tabs from sector config (all 4 sectors)"
```

---

## Task 8: Frontend — project-card display is sector-aware

**Files:**
- Modify: `frontend/src/pages/DealPipeline.tsx` (the project-card value-chain row, ~line 670 in the row map)

- [ ] **Step 1: Import the helper**

Update the import added in Task 7 to also pull the summary helper:
```ts
import { SECTORS, sectorCardSummary } from '../config/sectorConfig';
```

- [ ] **Step 2: Gate the value-chain row to agri + add sector summary**

Find the value-chain block inside the row render:
```tsx
                {project.value_chain_stages && project.value_chain_stages.length > 0 && (
                  <div style={{ fontSize: 11, color: 'var(--ink-500)', marginTop: 3 }}>
                    {project.value_chain_stages.map(s => s.charAt(0) + s.slice(1).toLowerCase()).join(' · ')}
                  </div>
                )}
```
Replace with:
```tsx
                {/* Agribusiness: value-chain stages */}
                {project.value_chain_stages && project.value_chain_stages.length > 0 && (
                  <div style={{ fontSize: 11, color: 'var(--ink-500)', marginTop: 3 }}>
                    {project.value_chain_stages.map(s => s.charAt(0) + s.slice(1).toLowerCase()).join(' · ')}
                  </div>
                )}
                {/* Other sectors: bespoke one-line summary from sector_details */}
                {(() => {
                  const summary = sectorCardSummary(project.pillar, project.sector_details);
                  return summary ? (
                    <div style={{ fontSize: 11, color: 'var(--ink-500)', marginTop: 3 }}>{summary}</div>
                  ) : null;
                })()}
```

- [ ] **Step 3: Typecheck**

Run: `cd frontend && npx tsc --noEmit -p tsconfig.json 2>&1 | grep DealPipeline`
Expected: no output.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/DealPipeline.tsx
git commit -m "feat(pipeline): sector-aware project card summary line"
```

---

## Task 9: Frontend — gate the Buyers tab to agribusiness

**Files:**
- Modify: `frontend/src/pages/DealPipeline.tsx` (the view-mode switcher array with the `buyers` entry, ~line 386)

- [ ] **Step 1: Show Buyers only when an agri context is relevant**

The Buyer/offtake database is agribusiness-only (`usesOfftake`). The switcher currently always includes `{ key: 'buyers', label: 'Buyers' }`. Since the pipeline is multi-sector, keep the Buyers tab available (it is its own offtake registry, not per-project), but add a clarifying caption inside `BuyerDatabase`. Find in `frontend/src/pages/BuyerDatabase.tsx` the subtitle:
```tsx
                    <p style={{ fontSize: 13, color: 'var(--ink-500)', marginTop: 8 }}>
                        Registered offtakers and buyers for project-buyer matching
                    </p>
```
Replace the text with:
```tsx
                    <p style={{ fontSize: 13, color: 'var(--ink-500)', marginTop: 8 }}>
                        Registered offtakers for Agribusiness project–buyer matching
                    </p>
```

- [ ] **Step 2: Typecheck**

Run: `cd frontend && npx tsc --noEmit -p tsconfig.json 2>&1 | grep BuyerDatabase`
Expected: no output.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/BuyerDatabase.tsx
git commit -m "feat(pipeline): clarify Buyer DB scope is agribusiness offtake"
```

---

## Task 10: Frontend — sector-aware intake form

**Files:**
- Modify: `frontend/src/pages/NewProject.tsx`

- [ ] **Step 1: Import the config**

At the top with other imports:
```ts
import { sectorByPillar, FieldDef } from '../config/sectorConfig';
```

- [ ] **Step 2: Add `sector_details` to form state**

In the `useState` form object (around line 28-45) add a field alongside `value_chain_stages`:
```ts
    sector_details: {} as Record<string, any>,
```

- [ ] **Step 3: Compute the active sector**

After `formData` is defined (just before the `return`), add:
```ts
  const activeSector = sectorByPillar(formData.pillar);
  const setSectorField = (key: string, value: any) =>
    setFormData(prev => ({ ...prev, sector_details: { ...prev.sector_details, [key]: value } }));
```

- [ ] **Step 4: Gate the existing value-chain block to agribusiness**

Find the value-chain stages block in the JSX (the group rendering `VALUE_CHAIN_STAGES`, ~line 447). Wrap it so it renders only for agribusiness:
```tsx
        {activeSector?.legacyAgri && (
          <>
            {/* existing value-chain stages block stays here, unchanged */}
          </>
        )}
```
(Move the existing block inside this fragment; do not change its internals.)

- [ ] **Step 5: Render the sector field group**

Immediately after the value-chain fragment, add a generic renderer for non-agri sectors:
```tsx
        {activeSector && !activeSector.legacyAgri && activeSector.fields.length > 0 && (
          <div style={{ marginTop: 8 }}>
            <div style={{ fontSize: 10, letterSpacing: '0.14em', textTransform: 'uppercase', color: 'var(--ink-500)', fontWeight: 500, marginBottom: 10 }}>
              {activeSector.label} details
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 14 }}>
              {activeSector.fields.map((f: FieldDef) => (
                <div key={f.key}>
                  <label style={{ display: 'block', fontSize: 12, color: 'var(--ink-600)', marginBottom: 4 }}>
                    {f.label}{f.optional ? ' (optional)' : ''}
                  </label>
                  {f.type === 'text' && (
                    <input
                      value={formData.sector_details[f.key] ?? ''}
                      onChange={e => setSectorField(f.key, e.target.value)}
                      style={{ width: '100%', padding: '8px 10px', border: '1px solid var(--border)', background: 'var(--surface)', fontSize: 13, fontFamily: 'inherit', color: 'var(--ink-900)', outline: 'none', boxSizing: 'border-box' }}
                    />
                  )}
                  {f.type === 'number' && (
                    <input
                      type="number"
                      value={formData.sector_details[f.key] ?? ''}
                      onChange={e => setSectorField(f.key, e.target.value === '' ? null : Number(e.target.value))}
                      style={{ width: '100%', padding: '8px 10px', border: '1px solid var(--border)', background: 'var(--surface)', fontSize: 13, fontFamily: 'inherit', color: 'var(--ink-900)', outline: 'none', boxSizing: 'border-box' }}
                    />
                  )}
                  {f.type === 'select' && (
                    <select
                      value={formData.sector_details[f.key] ?? ''}
                      onChange={e => setSectorField(f.key, e.target.value || null)}
                      style={{ width: '100%', padding: '8px 10px', border: '1px solid var(--border)', background: 'var(--surface)', fontSize: 13, fontFamily: 'inherit', color: 'var(--ink-900)', outline: 'none', cursor: 'pointer' }}
                    >
                      <option value="">Select…</option>
                      {f.options!.map(o => <option key={o} value={o}>{o}</option>)}
                    </select>
                  )}
                  {f.type === 'multiselect' && (
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                      {f.options!.map(o => {
                        const sel: string[] = formData.sector_details[f.key] ?? [];
                        const on = sel.includes(o);
                        return (
                          <button
                            type="button"
                            key={o}
                            onClick={() => setSectorField(f.key, on ? sel.filter(x => x !== o) : [...sel, o])}
                            style={{
                              padding: '5px 10px', fontSize: 12, cursor: 'pointer', fontFamily: 'inherit',
                              background: on ? 'var(--accent)' : 'transparent',
                              border: `1px solid ${on ? 'var(--accent)' : 'var(--border)'}`,
                              color: on ? 'var(--accent-ink)' : 'var(--ink-700)',
                            }}
                          >{o}</button>
                        );
                      })}
                    </div>
                  )}
                  {f.type === 'toggle' && (
                    <label style={{ display: 'inline-flex', alignItems: 'center', gap: 8, fontSize: 13, color: 'var(--ink-700)', cursor: 'pointer' }}>
                      <input
                        type="checkbox"
                        checked={!!formData.sector_details[f.key]}
                        onChange={e => setSectorField(f.key, e.target.checked)}
                        style={{ accentColor: 'var(--accent)' }}
                      />
                      Yes
                    </label>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
```

- [ ] **Step 6: Submit `sector_details` (non-agri only) and stop forcing value chains**

Find the submit payload object (the call that builds the body for `pipelineService` ingest, around line 173-192). Add to that object:
```ts
        sector_details: activeSector && !activeSector.legacyAgri ? formData.sector_details : undefined,
```
Then find where `value_chain_stages` is added to the payload (search `value_chain_stages` in the submit handler). Ensure it is only sent when non-empty:
```ts
        value_chain_stages: formData.value_chain_stages.length ? formData.value_chain_stages : undefined,
```
If the form has a client-side "at least one value chain stage" required-check, gate it to `activeSector?.legacyAgri` so non-agri sectors can submit without it.

- [ ] **Step 7: Typecheck**

Run: `cd frontend && npx tsc --noEmit -p tsconfig.json 2>&1 | grep NewProject`
Expected: no output.

- [ ] **Step 8: Manual verify**

In the running app, open `/deal-pipeline/new`. Select **Agribusiness** → value-chain block shows, no "details" group. Select **Energy** → value-chain block hidden, "Energy Trade & Industrial Growth details" group shows (Asset type, Capacity MW, PPA, Grid, Output). Submit an Energy project; confirm it saves (no value-chain validation error) and appears in the pipeline with a summary line like `120 MW · Solar · PPA signed`.

- [ ] **Step 9: Commit**

```bash
git add frontend/src/pages/NewProject.tsx
git commit -m "feat(pipeline): sector-aware intake form (value chain agri-only, sector_details for others)"
```

---

## Task 11: End-to-end verification + push

- [ ] **Step 1: Full typecheck**

Run: `cd frontend && npx tsc --noEmit -p tsconfig.json`
Expected: exit 0, no errors.

- [ ] **Step 2: Backend import smoke test**

Run: `cd backend && python -c "import app.main; print('ok')"`
Expected: prints `ok`.

- [ ] **Step 3: Manual cross-sector pass**

In the running app: create one project in each of Energy / Minerals / Digital and one Agribusiness. Verify: (a) each intake form shows only its own sector fields, (b) the pipeline tabs filter correctly, (c) cards render the right summary (agri = value chain; others = sector summary), (d) the Buyers tab still works for agri.

- [ ] **Step 4: Push**

```bash
git push origin main
```

---

## Notes for the implementer
- **DRY:** the field renderer in Task 10 is generic — never hardcode per-sector inputs.
- **Agribusiness is special-cased** via `legacyAgri`; its persistence path (existing typed columns) is unchanged. Do not route agri data through `sector_details`.
- **No scoring changes.** WAIIS/AfCEN criteria and weights are sector-neutral and stay untouched.
- If `update_project` in Task 4 already applies `model_dump(exclude_unset=True)` generically, `sector_details` flows through automatically — verify before adding explicit handling.
