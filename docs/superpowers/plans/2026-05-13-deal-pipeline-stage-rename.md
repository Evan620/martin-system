# Deal Pipeline Stage Rename Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rename all deal pipeline stage names to match Carren's TWG template terminology (Concept, Pre-feasibility, Feasibility, Bankable, Summit Featured, In Negotiation, Committed), add two-phase labels to the stage tracker, and restrict advancement past Bankable to Secretariat/Admin role.

**Architecture:** The rename touches the PostgreSQL enum type (via a migration that converts the column to text, remaps values, and recreates the enum), all backend service/route files that reference `ProjectStatus`, and frontend type + component files. No new tables or API endpoints needed.

**Tech Stack:** PostgreSQL (asyncpg), SQLAlchemy/Alembic, FastAPI, React/TypeScript

---

## Stage Mapping Reference

| Old enum value (DB) | New enum value (DB) | Display label |
|---|---|---|
| `DRAFT` | `CONCEPT` | Concept |
| `PIPELINE` | `PRE_FEASIBILITY` | Pre-feasibility |
| `UNDER_REVIEW` | `FEASIBILITY` | Feasibility |
| `SUMMIT_READY` | `BANKABLE` | Bankable |
| `DEAL_ROOM_FEATURED` | `SUMMIT_FEATURED` | Summit Featured |
| `IN_NEGOTIATION` | `IN_NEGOTIATION` | In Negotiation *(unchanged)* |
| `COMMITTED` | `COMMITTED` | Committed *(unchanged)* |
| `IDENTIFIED` | *(dropped)* | — |
| `IMPLEMENTED` | *(dropped)* | — |

Keep as-is (system states, not displayed in pipeline): `DECLINED`, `NEEDS_REVISION`, `ON_HOLD`, `ARCHIVED`.

---

## File Map

**Backend — modify:**
- `backend/app/models/models.py` — `ProjectStatus` enum, default value on `Project.status`
- `backend/alembic/versions/<new>.py` — Migration: convert column to text, remap data, recreate enum
- `backend/app/services/lifecycle_service.py` — Transition map keys + duration thresholds
- `backend/app/services/project_pipeline_service.py` — Stage-specific side-effects (was PIPELINE, UNDER_REVIEW, etc.)
- `backend/app/services/project_insights_service.py` — `project.status` comparisons
- `backend/app/services/deal_room_service.py` — `ProjectStatus.DEAL_ROOM` → `ProjectStatus.SUMMIT_FEATURED`
- `backend/app/api/routes/pipeline.py` — `_STAGE_MAP`, advance-stage role check
- `backend/app/api/routes/dashboard.py` — Any status filter queries
- `backend/app/api/routes/conflicts.py` — Any status filter queries
- `backend/app/api/routes/projects.py` — Any status filter queries
- `backend/app/schemas/schemas.py` — `ProjectStatus` enum import (if re-exported)

**Frontend — modify:**
- `frontend/src/types/pipeline.ts` — `ProjectStatus` enum values
- `frontend/src/components/pipeline/ProjectLifecycleTimeline.tsx` — Stage labels + phase dividers
- `frontend/src/pages/DealPipeline.tsx` — Filter dropdown options
- `frontend/src/pages/ProjectDetails.tsx` — `getStatusColor()` switch cases

---

## Task 1: Update `ProjectStatus` enum in models.py

**Files:**
- Modify: `backend/app/models/models.py`

- [ ] **Step 1: Update the enum class**

In `backend/app/models/models.py`, replace the `ProjectStatus` class (currently around line 61) with:

```python
class ProjectStatus(str, enum.Enum):
    # Phase 1 — Project Development (TWG Facilitator)
    CONCEPT = "CONCEPT"
    PRE_FEASIBILITY = "PRE_FEASIBILITY"
    FEASIBILITY = "FEASIBILITY"
    BANKABLE = "BANKABLE"

    # Phase 2 — Deal Making (Secretariat)
    SUMMIT_FEATURED = "SUMMIT_FEATURED"
    IN_NEGOTIATION = "IN_NEGOTIATION"
    COMMITTED = "COMMITTED"

    # System states
    DECLINED = "DECLINED"
    NEEDS_REVISION = "NEEDS_REVISION"
    ON_HOLD = "ON_HOLD"
    ARCHIVED = "ARCHIVED"
```

Also update the `Project` model default (around line 547):

```python
status: Mapped[ProjectStatus] = mapped_column(Enum(ProjectStatus), default=ProjectStatus.CONCEPT)
```

- [ ] **Step 2: Verify Python parses correctly**

```bash
cd backend && source ../venv/bin/activate 2>/dev/null || source ../.venv/bin/activate
python3 -c "from app.models.models import ProjectStatus; print([s.value for s in ProjectStatus])"
```

Expected output: `['CONCEPT', 'PRE_FEASIBILITY', 'FEASIBILITY', 'BANKABLE', 'SUMMIT_FEATURED', 'IN_NEGOTIATION', 'COMMITTED', 'DECLINED', 'NEEDS_REVISION', 'ON_HOLD', 'ARCHIVED']`

- [ ] **Step 3: Commit**

```bash
git add backend/app/models/models.py
git commit -m "feat: rename ProjectStatus enum values to match TWG template terminology"
```

---

## Task 2: Database migration — remap enum values

**Files:**
- Create: `backend/alembic/versions/<hash>_rename_project_status_enum.py`

The PostgreSQL enum type can't have values removed, so the safest approach is: convert column to text → remap data → drop old type → create new type → convert back.

- [ ] **Step 1: Generate an empty migration**

```bash
cd backend && source ../venv/bin/activate 2>/dev/null || source ../.venv/bin/activate
alembic revision -m "rename_project_status_enum"
```

Note the generated filename (e.g. `abc123_rename_project_status_enum.py`).

- [ ] **Step 2: Write the migration**

Open the generated file and replace its `upgrade()` and `downgrade()` with:

```python
def upgrade() -> None:
    # 1. Convert status column to plain text so we can remap values freely
    op.execute("ALTER TABLE projects ALTER COLUMN status TYPE VARCHAR(50)")

    # 2. Remap old values to new
    op.execute("""
        UPDATE projects SET status = CASE status
            WHEN 'DRAFT'              THEN 'CONCEPT'
            WHEN 'PIPELINE'           THEN 'PRE_FEASIBILITY'
            WHEN 'UNDER_REVIEW'       THEN 'FEASIBILITY'
            WHEN 'NEEDS_REVISION'     THEN 'FEASIBILITY'
            WHEN 'SUMMIT_READY'       THEN 'BANKABLE'
            WHEN 'DEAL_ROOM_FEATURED' THEN 'SUMMIT_FEATURED'
            WHEN 'IN_NEGOTIATION'     THEN 'IN_NEGOTIATION'
            WHEN 'COMMITTED'          THEN 'COMMITTED'
            WHEN 'IMPLEMENTED'        THEN 'COMMITTED'
            WHEN 'IDENTIFIED'         THEN 'CONCEPT'
            WHEN 'VETTING'            THEN 'PRE_FEASIBILITY'
            WHEN 'DUE_DILIGENCE'      THEN 'FEASIBILITY'
            WHEN 'FINANCING'          THEN 'BANKABLE'
            WHEN 'BANKABLE'           THEN 'BANKABLE'
            WHEN 'PRESENTED'          THEN 'SUMMIT_FEATURED'
            ELSE status
        END
    """)

    # 3. Also remap project_status_history if it exists
    op.execute("""
        UPDATE project_status_history SET new_status = CASE new_status
            WHEN 'DRAFT'              THEN 'CONCEPT'
            WHEN 'PIPELINE'           THEN 'PRE_FEASIBILITY'
            WHEN 'UNDER_REVIEW'       THEN 'FEASIBILITY'
            WHEN 'NEEDS_REVISION'     THEN 'FEASIBILITY'
            WHEN 'SUMMIT_READY'       THEN 'BANKABLE'
            WHEN 'DEAL_ROOM_FEATURED' THEN 'SUMMIT_FEATURED'
            WHEN 'IN_NEGOTIATION'     THEN 'IN_NEGOTIATION'
            WHEN 'COMMITTED'          THEN 'COMMITTED'
            WHEN 'IMPLEMENTED'        THEN 'COMMITTED'
            WHEN 'IDENTIFIED'         THEN 'CONCEPT'
            WHEN 'VETTING'            THEN 'PRE_FEASIBILITY'
            WHEN 'DUE_DILIGENCE'      THEN 'FEASIBILITY'
            WHEN 'FINANCING'          THEN 'BANKABLE'
            WHEN 'BANKABLE'           THEN 'BANKABLE'
            WHEN 'PRESENTED'          THEN 'SUMMIT_FEATURED'
            ELSE new_status
        END
        WHERE new_status IS NOT NULL
    """)
    op.execute("""
        UPDATE project_status_history SET old_status = CASE old_status
            WHEN 'DRAFT'              THEN 'CONCEPT'
            WHEN 'PIPELINE'           THEN 'PRE_FEASIBILITY'
            WHEN 'UNDER_REVIEW'       THEN 'FEASIBILITY'
            WHEN 'NEEDS_REVISION'     THEN 'FEASIBILITY'
            WHEN 'SUMMIT_READY'       THEN 'BANKABLE'
            WHEN 'DEAL_ROOM_FEATURED' THEN 'SUMMIT_FEATURED'
            WHEN 'IN_NEGOTIATION'     THEN 'IN_NEGOTIATION'
            WHEN 'COMMITTED'          THEN 'COMMITTED'
            WHEN 'IMPLEMENTED'        THEN 'COMMITTED'
            WHEN 'IDENTIFIED'         THEN 'CONCEPT'
            WHEN 'VETTING'            THEN 'PRE_FEASIBILITY'
            WHEN 'DUE_DILIGENCE'      THEN 'FEASIBILITY'
            WHEN 'FINANCING'          THEN 'BANKABLE'
            WHEN 'BANKABLE'           THEN 'BANKABLE'
            WHEN 'PRESENTED'          THEN 'SUMMIT_FEATURED'
            ELSE old_status
        END
        WHERE old_status IS NOT NULL
    """)

    # 4. Drop old enum type
    op.execute("DROP TYPE IF EXISTS projectstatus")

    # 5. Create new enum type with new values
    op.execute("""
        CREATE TYPE projectstatus AS ENUM (
            'CONCEPT', 'PRE_FEASIBILITY', 'FEASIBILITY', 'BANKABLE',
            'SUMMIT_FEATURED', 'IN_NEGOTIATION', 'COMMITTED',
            'DECLINED', 'NEEDS_REVISION', 'ON_HOLD', 'ARCHIVED'
        )
    """)

    # 6. Convert column back to enum
    op.execute("""
        ALTER TABLE projects
        ALTER COLUMN status TYPE projectstatus
        USING status::projectstatus
    """)


def downgrade() -> None:
    # Convert back to text
    op.execute("ALTER TABLE projects ALTER COLUMN status TYPE VARCHAR(50)")

    # Remap new values back to old
    op.execute("""
        UPDATE projects SET status = CASE status
            WHEN 'CONCEPT'          THEN 'DRAFT'
            WHEN 'PRE_FEASIBILITY'  THEN 'PIPELINE'
            WHEN 'FEASIBILITY'      THEN 'UNDER_REVIEW'
            WHEN 'BANKABLE'         THEN 'SUMMIT_READY'
            WHEN 'SUMMIT_FEATURED'  THEN 'DEAL_ROOM_FEATURED'
            WHEN 'IN_NEGOTIATION'   THEN 'IN_NEGOTIATION'
            WHEN 'COMMITTED'        THEN 'COMMITTED'
            ELSE status
        END
    """)

    # Drop new type
    op.execute("DROP TYPE IF EXISTS projectstatus")

    # Recreate old type
    op.execute("""
        CREATE TYPE projectstatus AS ENUM (
            'DRAFT', 'PIPELINE', 'UNDER_REVIEW', 'SUMMIT_READY',
            'DEAL_ROOM_FEATURED', 'IN_NEGOTIATION', 'COMMITTED',
            'IMPLEMENTED', 'DECLINED', 'NEEDS_REVISION', 'ON_HOLD', 'ARCHIVED',
            'IDENTIFIED', 'VETTING', 'DUE_DILIGENCE', 'FINANCING', 'BANKABLE', 'PRESENTED'
        )
    """)

    op.execute("""
        ALTER TABLE projects
        ALTER COLUMN status TYPE projectstatus
        USING status::projectstatus
    """)
```

- [ ] **Step 3: Apply the migration**

```bash
cd backend && source ../venv/bin/activate 2>/dev/null || source ../.venv/bin/activate
alembic upgrade head
```

Expected: `Running upgrade ... -> <hash>, rename_project_status_enum`

- [ ] **Step 4: Verify data**

```bash
cd backend && source ../venv/bin/activate 2>/dev/null || source ../.venv/bin/activate
python3 -c "
import asyncio
from app.core.database import AsyncSessionLocal
from sqlalchemy import text

async def check():
    async with AsyncSessionLocal() as db:
        result = await db.execute(text('SELECT DISTINCT status FROM projects'))
        print('Distinct statuses in DB:', [r[0] for r in result.fetchall()])

asyncio.run(check())
"
```

Expected: only values from the new set (CONCEPT, PRE_FEASIBILITY, FEASIBILITY, BANKABLE, etc.)

- [ ] **Step 5: Commit**

```bash
git add backend/alembic/versions/
git commit -m "feat: migrate ProjectStatus enum values to TWG terminology"
```

---

## Task 3: Update lifecycle_service.py transition map

**Files:**
- Modify: `backend/app/services/lifecycle_service.py`

- [ ] **Step 1: Replace all ProjectStatus references**

In `backend/app/services/lifecycle_service.py`, replace the `ALLOWED_TRANSITIONS` dict (around line 26) and `STAGE_DURATION_THRESHOLDS` (around line 96):

```python
ALLOWED_TRANSITIONS = {
    (ProjectStatus.CONCEPT, ProjectStatus.PRE_FEASIBILITY): {
        "roles": [UserRole.TWG_FACILITATOR, UserRole.ADMIN, UserRole.SECRETARIAT_LEAD],
        "description": "Submit for early studies"
    },
    (ProjectStatus.PRE_FEASIBILITY, ProjectStatus.FEASIBILITY): {
        "roles": [UserRole.TWG_FACILITATOR, UserRole.ADMIN, UserRole.SECRETARIAT_LEAD],
        "description": "Advance to feasibility stage"
    },
    (ProjectStatus.FEASIBILITY, ProjectStatus.DECLINED): {
        "roles": [UserRole.ADMIN, UserRole.SECRETARIAT_LEAD],
        "description": "Decline project"
    },
    (ProjectStatus.FEASIBILITY, ProjectStatus.NEEDS_REVISION): {
        "roles": [UserRole.ADMIN, UserRole.SECRETARIAT_LEAD],
        "description": "Request revision"
    },
    (ProjectStatus.FEASIBILITY, ProjectStatus.BANKABLE): {
        "roles": [UserRole.TWG_FACILITATOR, UserRole.ADMIN, UserRole.SECRETARIAT_LEAD],
        "description": "Mark as bankable / investment-ready"
    },
    (ProjectStatus.NEEDS_REVISION, ProjectStatus.FEASIBILITY): {
        "roles": [UserRole.TWG_FACILITATOR, UserRole.ADMIN, UserRole.SECRETARIAT_LEAD],
        "description": "Resubmit after revision"
    },
    # Secretariat gate — only ADMIN / SECRETARIAT_LEAD can advance past Bankable
    (ProjectStatus.BANKABLE, ProjectStatus.SUMMIT_FEATURED): {
        "roles": [UserRole.ADMIN, UserRole.SECRETARIAT_LEAD],
        "description": "Select for summit"
    },
    (ProjectStatus.SUMMIT_FEATURED, ProjectStatus.IN_NEGOTIATION): {
        "roles": [UserRole.ADMIN, UserRole.SECRETARIAT_LEAD],
        "description": "Investor engaged"
    },
    (ProjectStatus.IN_NEGOTIATION, ProjectStatus.COMMITTED): {
        "roles": [UserRole.ADMIN, UserRole.SECRETARIAT_LEAD],
        "description": "Deal committed"
    },
}

STAGE_DURATION_THRESHOLDS = {
    ProjectStatus.CONCEPT: 14,
    ProjectStatus.PRE_FEASIBILITY: 30,
    ProjectStatus.FEASIBILITY: 30,
    ProjectStatus.BANKABLE: 30,
    ProjectStatus.SUMMIT_FEATURED: 30,
    ProjectStatus.IN_NEGOTIATION: 60,
    ProjectStatus.COMMITTED: 90,
}
```

Also update `get_allowed_transitions()` and `transition_project_status()` — replace any remaining old status references (search for `DRAFT`, `PIPELINE`, `UNDER_REVIEW`, `SUMMIT_READY`, `DEAL_ROOM_FEATURED`).

- [ ] **Step 2: Search and replace remaining old status names in the file**

```bash
grep -n "DRAFT\|PIPELINE\|UNDER_REVIEW\|SUMMIT_READY\|DEAL_ROOM_FEATURED\|IMPLEMENTED\|IDENTIFIED" \
  backend/app/services/lifecycle_service.py
```

Fix any hits by mapping to the new enum values from the reference table at the top of this plan.

- [ ] **Step 3: Verify backend starts without errors**

```bash
cd backend && source ../venv/bin/activate 2>/dev/null || source ../.venv/bin/activate
python3 -c "from app.services.lifecycle_service import LifecycleService; print('OK')"
```

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/lifecycle_service.py
git commit -m "feat: update lifecycle transition map to new stage names"
```

---

## Task 4: Update remaining backend service/route files

**Files:**
- Modify: `backend/app/services/project_pipeline_service.py`
- Modify: `backend/app/services/project_insights_service.py`
- Modify: `backend/app/services/deal_room_service.py`
- Modify: `backend/app/api/routes/pipeline.py`
- Modify: `backend/app/api/routes/dashboard.py`
- Modify: `backend/app/api/routes/conflicts.py`
- Modify: `backend/app/api/routes/projects.py`

- [ ] **Step 1: Find all old status references across backend**

```bash
grep -rn "ProjectStatus\.DRAFT\|ProjectStatus\.PIPELINE\|ProjectStatus\.UNDER_REVIEW\|ProjectStatus\.SUMMIT_READY\|ProjectStatus\.DEAL_ROOM_FEATURED\|ProjectStatus\.IMPLEMENTED\|ProjectStatus\.IDENTIFIED" \
  backend/app/ --include="*.py"
```

- [ ] **Step 2: Replace in project_pipeline_service.py**

Apply the mapping:
- `ProjectStatus.PIPELINE` → `ProjectStatus.PRE_FEASIBILITY`
- `ProjectStatus.UNDER_REVIEW` → `ProjectStatus.FEASIBILITY`
- `ProjectStatus.SUMMIT_READY` → `ProjectStatus.BANKABLE`
- `ProjectStatus.DEAL_ROOM_FEATURED` → `ProjectStatus.SUMMIT_FEATURED`
- `ProjectStatus.DRAFT` → `ProjectStatus.CONCEPT`
- `ProjectStatus.IMPLEMENTED` → `ProjectStatus.COMMITTED` (or remove)
- `ProjectStatus.IDENTIFIED` → `ProjectStatus.CONCEPT`
- `ProjectStatus.PRESENTED` → `ProjectStatus.SUMMIT_FEATURED`

- [ ] **Step 3: Replace in project_insights_service.py**

Same mapping as Step 2. This file has comparisons like `if project.status == ProjectStatus.DRAFT:` — update each one.

- [ ] **Step 4: Replace in deal_room_service.py**

```bash
grep -n "ProjectStatus\." backend/app/services/deal_room_service.py
```

Update `ProjectStatus.DEAL_ROOM` → `ProjectStatus.BANKABLE` and `ProjectStatus.FINANCING` → `ProjectStatus.BANKABLE`.

- [ ] **Step 5: Update _STAGE_MAP and import filter in pipeline.py**

In `backend/app/api/routes/pipeline.py`, the `_STAGE_MAP` already has correct target values but they reference old enum members. Update all `ProjectStatus.DRAFT` etc. references:

```python
_STAGE_MAP: dict[str, ProjectStatus] = {
    "early-stage commercialisation": ProjectStatus.PRE_FEASIBILITY,
    "early-stage commercialization": ProjectStatus.PRE_FEASIBILITY,
    "feasibility / investment-ready": ProjectStatus.BANKABLE,
    "feasibility / bankable": ProjectStatus.BANKABLE,
    "pre-feasibility": ProjectStatus.PRE_FEASIBILITY,
    "prefeasibility": ProjectStatus.PRE_FEASIBILITY,
    "feasibility": ProjectStatus.FEASIBILITY,
    "bankable": ProjectStatus.BANKABLE,
    "investment-ready": ProjectStatus.BANKABLE,
    "investment ready": ProjectStatus.BANKABLE,
    "concept": ProjectStatus.CONCEPT,
    "early stage": ProjectStatus.PRE_FEASIBILITY,
}
```

- [ ] **Step 6: Replace in dashboard.py, conflicts.py, projects.py**

```bash
grep -n "ProjectStatus\." backend/app/api/routes/dashboard.py \
  backend/app/api/routes/conflicts.py \
  backend/app/api/routes/projects.py
```

Apply the same mapping for any hits.

- [ ] **Step 7: Verify backend starts and passes a quick smoke test**

```bash
cd backend && source ../venv/bin/activate 2>/dev/null || source ../.venv/bin/activate
python3 -c "
from app.api.routes.pipeline import router
from app.services.lifecycle_service import LifecycleService
from app.models.models import ProjectStatus
print('Allowed from BANKABLE:', LifecycleService.get_allowed_transitions(ProjectStatus.BANKABLE, None))
print('Allowed from CONCEPT:', LifecycleService.get_allowed_transitions(ProjectStatus.CONCEPT, None))
print('OK')
"
```

Expected: `BANKABLE` shows no transitions (no role) and `CONCEPT` shows `['PRE_FEASIBILITY']`.

- [ ] **Step 8: Commit**

```bash
git add backend/app/services/project_pipeline_service.py \
        backend/app/services/project_insights_service.py \
        backend/app/services/deal_room_service.py \
        backend/app/api/routes/pipeline.py \
        backend/app/api/routes/dashboard.py \
        backend/app/api/routes/conflicts.py \
        backend/app/api/routes/projects.py
git commit -m "feat: update all backend stage references to new TWG terminology"
```

---

## Task 5: Update frontend types and components

**Files:**
- Modify: `frontend/src/types/pipeline.ts`
- Modify: `frontend/src/components/pipeline/ProjectLifecycleTimeline.tsx`
- Modify: `frontend/src/pages/DealPipeline.tsx`
- Modify: `frontend/src/pages/ProjectDetails.tsx`

- [ ] **Step 1: Update ProjectStatus enum in types/pipeline.ts**

Replace the `ProjectStatus` enum (lines 3–35):

```typescript
export enum ProjectStatus {
    // Phase 1 — Project Development (TWG Facilitator)
    CONCEPT = "CONCEPT",
    PRE_FEASIBILITY = "PRE_FEASIBILITY",
    FEASIBILITY = "FEASIBILITY",
    BANKABLE = "BANKABLE",

    // Phase 2 — Deal Making (Secretariat)
    SUMMIT_FEATURED = "SUMMIT_FEATURED",
    IN_NEGOTIATION = "IN_NEGOTIATION",
    COMMITTED = "COMMITTED",

    // System states
    DECLINED = "DECLINED",
    NEEDS_REVISION = "NEEDS_REVISION",
    ON_HOLD = "ON_HOLD",
    ARCHIVED = "ARCHIVED",
}
```

- [ ] **Step 2: Update ProjectLifecycleTimeline.tsx — stage list + phase dividers**

Replace the entire file content with:

```typescript
import React from 'react';
import { Project, ProjectStatus } from '../../types/pipeline';
import {
    LightBulbIcon,
    ClockIcon,
    MagnifyingGlassIcon,
    CheckBadgeIcon,
    StarIcon,
    CurrencyDollarIcon,
    TrophyIcon,
    XCircleIcon,
    ExclamationTriangleIcon
} from '@heroicons/react/24/outline';

interface Props {
    project: Project;
}

const PHASE1 = [
    { key: ProjectStatus.CONCEPT, label: 'Concept', icon: LightBulbIcon },
    { key: ProjectStatus.PRE_FEASIBILITY, label: 'Pre-feasibility', icon: ClockIcon },
    { key: ProjectStatus.FEASIBILITY, label: 'Feasibility', icon: MagnifyingGlassIcon },
    { key: ProjectStatus.BANKABLE, label: 'Bankable', icon: CheckBadgeIcon },
];

const PHASE2 = [
    { key: ProjectStatus.SUMMIT_FEATURED, label: 'Summit Featured', icon: StarIcon },
    { key: ProjectStatus.IN_NEGOTIATION, label: 'In Negotiation', icon: CurrencyDollarIcon },
    { key: ProjectStatus.COMMITTED, label: 'Committed', icon: TrophyIcon },
];

const ALL_STAGES = [...PHASE1, ...PHASE2];

export const ProjectLifecycleTimeline: React.FC<Props> = ({ project }) => {
    const currentStatus = project.status;
    const isDeclined = currentStatus === ProjectStatus.DECLINED;
    const isRevision = currentStatus === ProjectStatus.NEEDS_REVISION;

    let activeIndex = ALL_STAGES.findIndex(s => s.key === currentStatus);
    if (activeIndex === -1) {
        if (isDeclined || isRevision) activeIndex = ALL_STAGES.findIndex(s => s.key === ProjectStatus.FEASIBILITY);
        else activeIndex = 0;
    }

    const renderStage = (stage: typeof ALL_STAGES[0], index: number, isFirst: boolean) => {
        const isCompleted = index < activeIndex;
        const isActive = index === activeIndex;
        const Icon = stage.icon;

        let statusColor = 'bg-gray-200 text-gray-400';
        if (isCompleted) statusColor = 'bg-green-500 text-white';
        else if (isActive) {
            if (isDeclined) statusColor = 'bg-red-500 text-white';
            else if (isRevision) statusColor = 'bg-amber-500 text-white';
            else statusColor = 'bg-blue-600 text-white';
        }

        return (
            <div key={stage.key} className="relative flex flex-col items-center flex-1 group">
                {!isFirst && (
                    <div className={`absolute top-5 right-[50%] w-full h-[2px] -translate-y-1/2 ${index <= activeIndex ? 'bg-green-500' : 'bg-gray-200'}`} />
                )}
                <div className={`relative z-10 flex items-center justify-center w-10 h-10 rounded-full transition-all duration-300 ${statusColor} shadow-sm border-2 border-white`}>
                    {isActive && isDeclined ? <XCircleIcon className="w-6 h-6" /> :
                     isActive && isRevision ? <ExclamationTriangleIcon className="w-6 h-6" /> :
                     <Icon className="w-5 h-5" />}
                </div>
                <div className="mt-3 text-center">
                    <p className={`text-xs font-semibold ${isActive ? 'text-gray-900' : 'text-gray-500'}`}>
                        {stage.label}
                    </p>
                    {isActive && (
                        <span className="text-[10px] text-gray-400 font-medium">
                            {isDeclined ? 'Declined' : isRevision ? 'Needs Revision' : 'Current Stage'}
                        </span>
                    )}
                </div>
            </div>
        );
    };

    return (
        <div className="w-full py-6 overflow-x-auto">
            <div className="px-4 min-w-[800px]">
                {/* Phase 1 */}
                <div className="mb-1">
                    <span className="text-[10px] font-bold uppercase tracking-widest text-blue-500 ml-2">
                        Phase 1 — Project Development
                    </span>
                </div>
                <div className="flex items-center justify-between">
                    {PHASE1.map((stage, i) => renderStage(stage, i, i === 0))}
                </div>

                {/* Phase divider */}
                <div className="flex items-center gap-3 my-3 px-2">
                    <div className="flex-1 border-t border-dashed border-orange-300" />
                    <span className="text-[10px] text-orange-500 font-semibold whitespace-nowrap">Secretariat selects for summit</span>
                    <div className="flex-1 border-t border-dashed border-orange-300" />
                </div>

                {/* Phase 2 */}
                <div className="mb-1">
                    <span className="text-[10px] font-bold uppercase tracking-widest text-purple-500 ml-2">
                        Phase 2 — Deal Making
                    </span>
                </div>
                <div className="flex items-center justify-between">
                    {PHASE2.map((stage, i) => renderStage(stage, PHASE1.length + i, i === 0))}
                </div>
            </div>
        </div>
    );
};
```

- [ ] **Step 3: Update DealPipeline.tsx filter dropdown**

Find the status filter `<select>` (around line 406) and replace its options:

```tsx
<option value="">All Stages</option>
<option value={ProjectStatus.CONCEPT}>Concept</option>
<option value={ProjectStatus.PRE_FEASIBILITY}>Pre-feasibility</option>
<option value={ProjectStatus.FEASIBILITY}>Feasibility</option>
<option value={ProjectStatus.BANKABLE}>Bankable</option>
<option value={ProjectStatus.SUMMIT_FEATURED}>Summit Featured</option>
<option value={ProjectStatus.IN_NEGOTIATION}>In Negotiation</option>
<option value={ProjectStatus.COMMITTED}>Committed</option>
```

- [ ] **Step 4: Update getStatusColor() in ProjectDetails.tsx**

Replace the `getStatusColor` switch (lines 251–261):

```typescript
const getStatusColor = (status: string) => {
    switch (status) {
        case 'CONCEPT':         return 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-200 border-blue-200 dark:border-blue-800';
        case 'PRE_FEASIBILITY': return 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-200 border-purple-200 dark:border-purple-800';
        case 'FEASIBILITY':     return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-200 border-yellow-200 dark:border-yellow-800';
        case 'BANKABLE':        return 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-200 border-green-200 dark:border-green-800';
        case 'SUMMIT_FEATURED': return 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-200 border-orange-200 dark:border-orange-800';
        case 'IN_NEGOTIATION':  return 'bg-pink-100 text-pink-800 dark:bg-pink-900/30 dark:text-pink-200 border-pink-200 dark:border-pink-800';
        case 'COMMITTED':       return 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-200 border-emerald-200 dark:border-emerald-800';
        case 'DECLINED':        return 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-200 border-red-200 dark:border-red-800';
        case 'NEEDS_REVISION':  return 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-200 border-amber-200 dark:border-amber-800';
        default:                return 'bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-200 border-slate-200 dark:border-slate-700';
    }
};
```

- [ ] **Step 5: Check TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit 2>&1 | head -30
```

Expected: no errors (or only pre-existing unrelated errors).

- [ ] **Step 6: Commit**

```bash
git add frontend/src/types/pipeline.ts \
        frontend/src/components/pipeline/ProjectLifecycleTimeline.tsx \
        frontend/src/pages/DealPipeline.tsx \
        frontend/src/pages/ProjectDetails.tsx
git commit -m "feat: update frontend stage names and lifecycle timeline to TWG terminology"
```

---

## Task 6: Re-import Carren's projects with corrected stage mappings

Now that the stage mapping is correct and the DB has been migrated, delete the existing imported projects and re-import clean.

**Files:** none (data operation only)

- [ ] **Step 1: Delete existing imported projects**

```bash
TOKEN=$(curl -s -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"olivia.robinson@africacen.org","password":"Test123"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Get all project IDs for the Agribusiness TWG
curl -s "http://localhost:8000/api/v1/pipeline/?twg_id=2918418a-b1fa-4470-af5b-d45c3bdf6eda&limit=50" \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -c "
import sys, json
projects = json.load(sys.stdin)
print(f'Found {len(projects)} projects to delete:')
for p in projects:
    print(f'  {p[\"id\"]} | {p[\"name\"][:50]}')
"
```

Then delete via psql (direct DB access is faster than one-by-one API calls):

```bash
PGPASSWORD=testpass psql -h localhost -p 5434 -U postgres -d martin_test -c \
  "DELETE FROM projects WHERE twg_id = '2918418a-b1fa-4470-af5b-d45c3bdf6eda';"
```

Expected: `DELETE 20`

- [ ] **Step 2: Re-import**

```bash
TOKEN=$(curl -s -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"olivia.robinson@africacen.org","password":"Test123"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

curl -s -X POST "http://localhost:8000/api/v1/pipeline/import-excel" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@carren_template.xlsx" \
  -F "twg_id=2918418a-b1fa-4470-af5b-d45c3bdf6eda" \
  | python3 -m json.tool
```

Expected: `{"imported": 20, "skipped": ..., "errors": []}`

- [ ] **Step 3: Verify stage distribution**

```bash
TOKEN=$(curl -s -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"olivia.robinson@africacen.org","password":"Test123"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

curl -s "http://localhost:8000/api/v1/pipeline/?twg_id=2918418a-b1fa-4470-af5b-d45c3bdf6eda&limit=50" \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -c "
import sys, json
from collections import Counter
projects = json.load(sys.stdin)
counts = Counter(p['status'] for p in projects)
print('Stage distribution:')
for stage, n in sorted(counts.items()):
    print(f'  {stage}: {n}')
"
```

Expected distribution (from Carren's sheet):
- `CONCEPT`: 1 (Cabo Verde — Praia)
- `PRE_FEASIBILITY`: 2 (Office du Niger, Maradi)
- `FEASIBILITY`: 10 (majority)
- `BANKABLE`: 4 (Feed Ghana, West Africa Food System, PROS, Hybrid Rice)

- [ ] **Step 4: Open browser and verify visually**

Navigate to `http://localhost:5173/deal-pipeline` — confirm stage labels show "Concept", "Pre-feasibility", "Feasibility", "Bankable" in the filter and the project rows show correct status badges.

Open one Bankable project detail page — confirm the lifecycle timeline shows Phase 1 / Phase 2 divider and the stage tracker labels are correct.

---

## Self-Review

**Spec coverage check:**
- ✅ Rename stages to Carren's terminology — Tasks 1, 2, 4, 5
- ✅ Stage tracker shows phase labels — Task 5 (ProjectLifecycleTimeline)
- ✅ Advance past Bankable restricted to Secretariat/Admin — Task 3 (lifecycle_service roles)
- ✅ Import re-maps to new stage names — Task 4 (_STAGE_MAP update)
- ✅ Re-import Carren's 21 projects — Task 6

**Placeholder scan:** No TBD/TODO found. All code blocks are complete. ✅

**Type consistency:** `ProjectStatus.CONCEPT`, `ProjectStatus.PRE_FEASIBILITY`, `ProjectStatus.FEASIBILITY`, `ProjectStatus.BANKABLE`, `ProjectStatus.SUMMIT_FEATURED` used consistently across Tasks 1–5. ✅
