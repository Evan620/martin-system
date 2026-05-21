# R5 — Stage 0: Incubation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a pre-pipeline INCUBATION status with a Readiness tab (WAIIS checklist + AI gap report) and a configurable graduation gate that promotes projects to DRAFT when their AfCEN score ≥ threshold.

**Architecture:** New `INCUBATION` enum value sits before `DRAFT`. Backend adds Alembic migration, LifecycleService transition rule with score gate, and a new `readiness-gap` endpoint that invokes the LLM service. Frontend adds incubation toggle in NewProject, purple row styles in DealPipeline, a new ReadinessTab component in ProjectDetails, and threshold field in PlatformSettings.

**Tech Stack:** FastAPI, SQLAlchemy async, Alembic (PostgreSQL), Pydantic v2, React + TypeScript, `llm_service.chat()`

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `backend/alembic/versions/r5_incubation_20260521.py` | Create | Add INCUBATION to postgres enum; seed `incubation_graduation_threshold = 40` |
| `backend/app/models/models.py` | Modify | Add `INCUBATION` to `ProjectStatus` enum |
| `backend/app/services/lifecycle_service.py` | Modify | Add `INCUBATION → DRAFT` transition with `min_score` gate; add to `STAGE_DURATION_THRESHOLDS` |
| `backend/app/schemas/pipeline_schemas.py` | Modify | Add `start_in_incubation` to `ProjectIngest`; add `ReadinessGapItem` + `ReadinessGapRead`; add `incubation_graduation_threshold` to ALLOWED_KEYS in route |
| `backend/app/api/routes/pipeline.py` | Modify | Filter INCUBATION from investor list; honour `start_in_incubation` in ingest; new `GET /{id}/readiness-gap` endpoint; add `incubation_graduation_threshold` to ALLOWED_KEYS in platform settings |
| `frontend/src/types/pipeline.ts` | Modify | Add `INCUBATION = "INCUBATION"` before `DRAFT` |
| `frontend/src/pages/DealPipeline.tsx` | Modify | Purple row styles, inline score bar, Graduate chip, Show/Hide Incubation filter |
| `frontend/src/pages/NewProject.tsx` | Modify | Add `startInIncubation` toggle (default true); pass `start_in_incubation` to API |
| `frontend/src/pages/ProjectDetails.tsx` | Modify | Add `readiness` tab type; show Readiness tab entry when `project.status === INCUBATION` |
| `frontend/src/components/pipeline/ReadinessTab.tsx` | Create | Checklist + score bar + graduation button + gap report panel |
| `frontend/src/services/api.ts` | Modify | Add `getReadinessGap(projectId)` and `getPlatformSettings()` calls |

---

## Task 1: Alembic Migration — Add INCUBATION Enum Value + Seed Setting

**Files:**
- Create: `backend/alembic/versions/r5_incubation_20260521.py`

- [ ] **Step 1: Write the migration file**

```python
"""r5 incubation stage 0

Revision ID: r5_1nc0bat10n
Revises: r4_ecowas_w8ght
Create Date: 2026-05-21
"""
from alembic import op
import sqlalchemy as sa

revision = 'r5_1nc0bat10n'
down_revision = 'r4_ecowas_w8ght'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add INCUBATION to the projectstatus enum BEFORE DRAFT
    op.execute("ALTER TYPE projectstatus ADD VALUE IF NOT EXISTS 'INCUBATION' BEFORE 'DRAFT'")

    # Seed incubation_graduation_threshold setting
    op.execute("""
        INSERT INTO platform_settings (key, value)
        VALUES ('incubation_graduation_threshold', '40')
        ON CONFLICT (key) DO NOTHING
    """)


def downgrade() -> None:
    # PostgreSQL does not support removing enum values — migration is one-way
    op.execute("""
        DELETE FROM platform_settings WHERE key = 'incubation_graduation_threshold'
    """)
```

- [ ] **Step 2: Run the migration**

```bash
cd /home/evan/Desktop/martin\ os\ v2/martin-system/backend
DATABASE_URL="postgresql+asyncpg://ecowas_user:ecowas_pass@localhost:5433/ecowas_summit_db" \
  venv/bin/alembic upgrade head
```

Expected output ends with: `Running upgrade r4_ecowas_w8ght -> r5_1nc0bat10n`

- [ ] **Step 3: Verify enum value exists in DB**

```bash
PGPASSWORD=ecowas_pass psql -h localhost -p 5433 -U ecowas_user -d ecowas_summit_db \
  -c "SELECT unnest(enum_range(NULL::projectstatus));"
```

Expected: `INCUBATION` appears in the list before `DRAFT`.

- [ ] **Step 4: Commit**

```bash
git add backend/alembic/versions/r5_incubation_20260521.py
git commit -m "feat(r5): add INCUBATION enum value migration + seed graduation threshold"
```

---

## Task 2: Backend Model — Add INCUBATION to ProjectStatus Enum

**Files:**
- Modify: `backend/app/models/models.py` (lines 61-81)

- [ ] **Step 1: Write the failing test**

Create test file `backend/tests/test_r5_incubation_model.py`:

```python
import pytest
from app.models.models import ProjectStatus

def test_incubation_enum_value_exists():
    assert hasattr(ProjectStatus, 'INCUBATION')
    assert ProjectStatus.INCUBATION.value == 'INCUBATION'

def test_incubation_is_str():
    assert isinstance(ProjectStatus.INCUBATION, str)
    assert ProjectStatus.INCUBATION == 'INCUBATION'
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /home/evan/Desktop/martin\ os\ v2/martin-system/backend
DATABASE_URL="postgresql+asyncpg://ecowas_user:ecowas_pass@localhost:5433/ecowas_summit_db" \
  venv/bin/pytest tests/test_r5_incubation_model.py -v
```

Expected: FAIL — `AttributeError: INCUBATION`

- [ ] **Step 3: Add INCUBATION to the enum**

In `backend/app/models/models.py` at line 61, the `ProjectStatus` class currently reads:

```python
class ProjectStatus(str, enum.Enum):
    # Submission Phase
    DRAFT = "DRAFT"
```

Change it to:

```python
class ProjectStatus(str, enum.Enum):
    # Pre-Pipeline
    INCUBATION = "INCUBATION"

    # Submission Phase
    DRAFT = "DRAFT"
```

- [ ] **Step 4: Run test to verify it passes**

```bash
DATABASE_URL="postgresql+asyncpg://ecowas_user:ecowas_pass@localhost:5433/ecowas_summit_db" \
  venv/bin/pytest tests/test_r5_incubation_model.py -v
```

Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/app/models/models.py backend/tests/test_r5_incubation_model.py
git commit -m "feat(r5): add INCUBATION to ProjectStatus enum"
```

---

## Task 3: LifecycleService — INCUBATION → DRAFT Transition with Score Gate

**Files:**
- Modify: `backend/app/services/lifecycle_service.py`

The `ALLOWED_TRANSITIONS` dict is at lines 17–58. The existing `min_score` gate pattern is at lines 133–137:

```python
if "min_score" in rule:
    min_score = rule["min_score"]
    current_score = project.afcen_score or 0
    if current_score < min_score:
        raise HTTPException(...)
```

The graduation threshold will be read from the `PlatformSetting` table at runtime (since it's configurable). The transition rule will use a sentinel key `"uses_graduation_threshold": True` that causes the gate code to look up `incubation_graduation_threshold` from the DB.

- [ ] **Step 1: Write the failing test**

```python
import pytest
from app.models.models import ProjectStatus, UserRole

def test_incubation_to_draft_in_allowed_transitions():
    from app.services.lifecycle_service import LifecycleService
    key = (ProjectStatus.INCUBATION, ProjectStatus.DRAFT)
    assert key in LifecycleService.ALLOWED_TRANSITIONS

def test_incubation_to_draft_roles():
    from app.services.lifecycle_service import LifecycleService
    rule = LifecycleService.ALLOWED_TRANSITIONS[(ProjectStatus.INCUBATION, ProjectStatus.DRAFT)]
    assert UserRole.TWG_FACILITATOR in rule["roles"]
    assert UserRole.ADMIN in rule["roles"]
    assert UserRole.SECRETARIAT_LEAD in rule["roles"]

def test_incubation_to_draft_has_graduation_threshold_flag():
    from app.services.lifecycle_service import LifecycleService
    rule = LifecycleService.ALLOWED_TRANSITIONS[(ProjectStatus.INCUBATION, ProjectStatus.DRAFT)]
    assert rule.get("uses_graduation_threshold") is True
```

Add these to `backend/tests/test_r5_incubation_model.py`.

- [ ] **Step 2: Run tests to verify they fail**

```bash
venv/bin/pytest tests/test_r5_incubation_model.py -v -k "transition or roles or graduation"
```

Expected: 3 FAIL.

- [ ] **Step 3: Add the transition rule to ALLOWED_TRANSITIONS**

In `backend/app/services/lifecycle_service.py`, find the `ALLOWED_TRANSITIONS` dict (starts at line 17). Add as the **first** entry (before the DRAFT→PIPELINE rule):

```python
ALLOWED_TRANSITIONS = {
    (ProjectStatus.INCUBATION, ProjectStatus.DRAFT): {
        "roles": [UserRole.TWG_FACILITATOR, UserRole.ADMIN, UserRole.SECRETARIAT_LEAD],
        "description": "Graduate from Incubation to Draft",
        "uses_graduation_threshold": True,
    },
    (ProjectStatus.DRAFT, ProjectStatus.PIPELINE): {
        ...
```

- [ ] **Step 4: Add the graduation gate to transition_project_status**

In `backend/app/services/lifecycle_service.py`, find the `transition_project_status` method. After the existing `min_score` gate block (around line 137), add the graduation threshold gate:

```python
            if rule.get("uses_graduation_threshold"):
                from app.models.models import PlatformSetting
                thresh_res = await db.execute(
                    select(PlatformSetting).where(PlatformSetting.key == "incubation_graduation_threshold")
                )
                thresh_setting = thresh_res.scalars().first()
                threshold = float(thresh_setting.value) if thresh_setting else 40.0
                current_score = float(project.afcen_score or 0)
                if current_score < threshold:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Project score {current_score:.1f} is below graduation threshold {threshold:.0f}. "
                               f"Need {threshold - current_score:.1f} more points."
                    )
```

Place this block immediately after the `if "min_score" in rule:` block.

- [ ] **Step 5: Add INCUBATION to STAGE_DURATION_THRESHOLDS**

In `backend/app/services/lifecycle_service.py`, find `STAGE_DURATION_THRESHOLDS` (around line 63). Add:

```python
    STAGE_DURATION_THRESHOLDS = {
        ProjectStatus.INCUBATION: 90,  # 3 months to work through readiness
        ProjectStatus.DRAFT: 14,
        ...
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
venv/bin/pytest tests/test_r5_incubation_model.py -v
```

Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/lifecycle_service.py backend/tests/test_r5_incubation_model.py
git commit -m "feat(r5): add INCUBATION→DRAFT lifecycle transition with graduation score gate"
```

---

## Task 4: Pipeline Schemas — start_in_incubation + ReadinessGapRead

**Files:**
- Modify: `backend/app/schemas/pipeline_schemas.py`

- [ ] **Step 1: Write the failing test**

```python
from app.schemas.pipeline_schemas import ProjectIngest, ReadinessGapItem, ReadinessGapRead

def test_project_ingest_has_start_in_incubation():
    schema = ProjectIngest(
        twg_id="123",
        name="Test",
        description="Test project",
        investment_size=1000000,
        readiness_score=5.0,
        strategic_alignment_score=5.0,
    )
    assert schema.start_in_incubation is True  # default

def test_project_ingest_start_in_incubation_false():
    schema = ProjectIngest(
        twg_id="123",
        name="Test",
        description="Test project",
        investment_size=1000000,
        readiness_score=5.0,
        strategic_alignment_score=5.0,
        start_in_incubation=False,
    )
    assert schema.start_in_incubation is False

def test_readiness_gap_read_structure():
    item = ReadinessGapItem(
        criterion="Bankability",
        weight="18%",
        issue="No financial model uploaded",
        action="Upload a financial model Excel or PDF"
    )
    read = ReadinessGapRead(gaps=[item], current_score=32.0, threshold=40.0)
    assert read.gaps[0].criterion == "Bankability"
    assert read.current_score == 32.0
```

Add to `backend/tests/test_r5_incubation_model.py`.

- [ ] **Step 2: Run tests to verify they fail**

```bash
venv/bin/pytest tests/test_r5_incubation_model.py -v -k "ingest or gap_read"
```

Expected: FAIL.

- [ ] **Step 3: Add the schema changes**

In `backend/app/schemas/pipeline_schemas.py`, update `ProjectIngest` (line 14) to add `start_in_incubation`:

```python
class ProjectIngest(BaseModel):
    """Schema for ingesting a project proposal"""
    twg_id: str
    name: str
    description: str
    investment_size: Decimal
    currency: str = "USD"
    readiness_score: float = Field(..., ge=0, le=10)
    strategic_alignment_score: float = Field(..., ge=0, le=10)
    pillar: Optional[str] = None
    lead_country: Optional[str] = None
    assigned_agent: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None
    status: Optional[str] = None
    start_in_incubation: bool = True  # new
```

After the existing `PipelineStats` class (around line 205), add the new readiness gap schemas:

```python
class ReadinessGapItem(BaseModel):
    criterion: str
    weight: str
    issue: str
    action: str

class ReadinessGapRead(BaseModel):
    gaps: List[ReadinessGapItem]
    current_score: float
    threshold: float
    cached: bool = False
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
venv/bin/pytest tests/test_r5_incubation_model.py -v
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/pipeline_schemas.py backend/tests/test_r5_incubation_model.py
git commit -m "feat(r5): add start_in_incubation to ProjectIngest and ReadinessGapRead schema"
```

---

## Task 5: Pipeline API Routes — Incubation Filter, Ingest Flag, Readiness-Gap Endpoint

**Files:**
- Modify: `backend/app/api/routes/pipeline.py`

This task has three changes:
1. Filter INCUBATION from investor-role list view
2. Honour `start_in_incubation` in the ingest endpoint
3. Add `GET /{project_id}/readiness-gap` endpoint
4. Allow `incubation_graduation_threshold` in platform settings PATCH

- [ ] **Step 1: Write the failing tests**

```python
import pytest
import httpx
from fastapi.testclient import TestClient

# These are integration-style smoke tests; run against the live local DB

def test_readiness_gap_endpoint_exists():
    """Verify the readiness-gap route is registered."""
    from app.main import app
    client = TestClient(app)
    routes = [r.path for r in app.routes]
    assert any("readiness-gap" in r for r in routes)
```

Add to `backend/tests/test_r5_incubation_model.py`.

- [ ] **Step 2: Run to verify it fails**

```bash
venv/bin/pytest tests/test_r5_incubation_model.py::test_readiness_gap_endpoint_exists -v
```

Expected: FAIL.

- [ ] **Step 3: Update the list endpoint to filter INCUBATION for investors**

In `backend/app/api/routes/pipeline.py`, find the `list_pipeline_projects` function (line 88). It currently builds `query = select(Project)` and applies optional filters. Add an INCUBATION visibility filter:

After the `query = select(Project)` line and before the existing `if stage:` block, add:

```python
    # Investors never see incubation projects
    from app.models.models import UserRole as _Role
    if current_user.role == _Role.INVESTOR:
        query = query.where(Project.status != ProjectStatus.INCUBATION)
```

- [ ] **Step 4: Honour start_in_incubation in the ingest endpoint**

In `backend/app/api/routes/pipeline.py`, find the `ingest_project` function (line 115). The `ingest_project_proposal` call at line 126 currently passes `data.model_dump()`. Change this to pass the incubation flag:

```python
    result = await service.ingest_project_proposal(
        data=data.model_dump(exclude={"start_in_incubation"}),
        submitted_by_user_id=current_user.id,
        start_in_incubation=data.start_in_incubation,
    )
```

Then update `project_pipeline_service.py`'s `ingest_project_proposal` signature to accept `start_in_incubation: bool = True` and use it:

Find `ingest_project_proposal` in `backend/app/services/project_pipeline_service.py`. It creates a `Project(...)` with `status="DRAFT"` or leaves it unset. Change:

```python
    async def ingest_project_proposal(
        self,
        data: dict,
        submitted_by_user_id: uuid.UUID,
        start_in_incubation: bool = True,
    ) -> dict:
```

Then find where the `Project` object is constructed (look for `Project(` with `name=data["name"]`, around line 748). Change the status assignment. Find the line that sets `status` (it's currently set via the data dict or defaults to DRAFT). Add:

```python
        initial_status = ProjectStatus.INCUBATION if start_in_incubation else ProjectStatus.DRAFT
        project = Project(
            ...
            status=initial_status,
            ...
        )
```

To do this precisely: find the `Project(` constructor call in `ingest_project_proposal`. Look for where `status=` is set in that constructor. Replace whatever is there with `status=initial_status`. If `status` comes from `data.get("status")`, replace that logic:

```python
        # Determine initial status
        if data.get("status") and data["status"] != "identified":
            initial_status = ProjectStatus(data["status"])
        elif start_in_incubation:
            initial_status = ProjectStatus.INCUBATION
        else:
            initial_status = ProjectStatus.DRAFT
```

- [ ] **Step 5: Add the readiness-gap endpoint**

In `backend/app/api/routes/pipeline.py`, add the new endpoint **before** the platform settings block (around line 496). Add the import at the top of the file (with the other schema imports at line 19):

```python
from app.schemas.pipeline_schemas import (
    ProjectIngest, ProjectUpdate, ProjectPipelineRead, ProjectAdvanceStage,
    InvestorMatchRead, PipelineStats, InvestorMatchUpdate, InvestorRead,
    ProjectScoreDetailRead, ScoringCriteriaRead, ScoringCriteriaWeightUpdate,
    ReadinessGapRead, ReadinessGapItem,  # new
)
```

Then add the endpoint:

```python
@router.get("/{project_id}/readiness-gap", response_model=ReadinessGapRead)
async def get_readiness_gap(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_facilitator),
):
    """
    Generate (or return cached) Martin gap report for an Incubation project.
    Calls LLM service with current WAIIS scores; caches result in project.metadata_json.
    """
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.status != ProjectStatus.INCUBATION:
        raise HTTPException(status_code=400, detail="Readiness gap report is only available for Incubation projects")

    # Get graduation threshold
    from app.models.models import PlatformSetting
    thresh_res = await db.execute(
        select(PlatformSetting).where(PlatformSetting.key == "incubation_graduation_threshold")
    )
    thresh_setting = thresh_res.scalars().first()
    threshold = float(thresh_setting.value) if thresh_setting else 40.0
    current_score = float(project.afcen_score or 0)

    # Return cached report if available and not stale
    meta = project.metadata_json or {}
    cached_report = meta.get("readiness_gap_report")
    if cached_report:
        return ReadinessGapRead(
            gaps=[ReadinessGapItem(**g) for g in cached_report["gaps"]],
            current_score=current_score,
            threshold=threshold,
            cached=True,
        )

    # Fetch per-criterion scores
    from app.models.models import ProjectScoreDetail as _PSD, ScoringCriteria as _SC
    score_rows = await db.execute(
        select(_PSD, _SC)
        .join(_SC, _PSD.criterion_id == _SC.id)
        .where(_PSD.project_id == project_id)
    )
    criterion_scores = {
        row._SC.criterion_name: {
            "score": float(row._PSD.score),
            "weight": float(row._SC.weight) * 10,  # weight is 0-9.99 scale; multiply for display
            "notes": row._PSD.notes or "",
        }
        for row in score_rows
    }

    # Build project summary for prompt
    project_fields = {
        "name": project.name,
        "description": project.description,
        "investment_size": str(project.investment_size),
        "lead_country": project.lead_country,
        "pillar": project.pillar,
        "project_sponsor": project.project_sponsor,
        "key_contact_name": project.key_contact_name,
        "financing_structure": project.financing_structure,
        "revenue_model": project.revenue_model,
        "technical_studies": project.technical_studies,
        "permits_licences": project.permits_licences,
        "land_status": project.land_status,
        "climate_impact": project.climate_impact,
        "esg_compliance": project.esg_compliance,
        "women_employment_pct": project.women_employment_pct,
        "youth_employment_pct": project.youth_employment_pct,
        "value_chain_stages": project.value_chain_stages,
        "is_cross_border": project.is_cross_border,
    }

    import json
    prompt = f"""You are analysing an investment project for the ECOWAS Summit deal pipeline.
The project is in Incubation (pre-pipeline stage). Your job is to identify
the 3-4 highest-impact gaps preventing this project from reaching the
graduation threshold of {threshold:.0f}/100.

Project data: {json.dumps(project_fields, default=str)}
Current WAIIS scores per criterion: {json.dumps(criterion_scores)}
Graduation threshold: {threshold:.0f}
Current score: {current_score:.1f}

For each gap, provide:
- Which criterion it affects and its weight as a percentage string (e.g. "18%")
- What specific data or document is missing
- What the facilitator should do to fix it (one concrete action, reference actual field names)

Be direct and specific. Output ONLY valid JSON in this exact shape:
{{"gaps": [{{"criterion": "...", "weight": "...", "issue": "...", "action": "..."}}]}}"""

    from app.services.llm_service import llm_service
    try:
        raw = llm_service.chat(prompt, max_tokens=800)
        # Strip markdown code fences if present
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        parsed = json.loads(raw.strip())
        gaps = [ReadinessGapItem(**g) for g in parsed["gaps"]]
    except Exception as e:
        # Fallback: return a simple gap based on zero-score criteria
        gaps = []
        for name, data in criterion_scores.items():
            if data["score"] == 0 and len(gaps) < 4:
                gaps.append(ReadinessGapItem(
                    criterion=name,
                    weight=f"{data['weight']:.0f}%",
                    issue=f"{name} score is 0 — no relevant data provided",
                    action=f"Fill in {name.lower()} fields or upload supporting documents",
                ))

    # Cache the result
    meta["readiness_gap_report"] = {"gaps": [g.model_dump() for g in gaps]}
    project.metadata_json = meta
    await db.commit()

    return ReadinessGapRead(gaps=gaps, current_score=current_score, threshold=threshold, cached=False)
```

- [ ] **Step 6: Add incubation_graduation_threshold to platform settings ALLOWED_KEYS**

In `backend/app/api/routes/pipeline.py`, find the `update_platform_settings` function (around line 512). Find:

```python
    ALLOWED_KEYS = {"gender_threshold_pct", "youth_threshold_pct"}
```

Change to:

```python
    ALLOWED_KEYS = {"gender_threshold_pct", "youth_threshold_pct", "incubation_graduation_threshold"}
```

- [ ] **Step 7: Invalidate readiness gap cache on project update**

In `backend/app/services/project_pipeline_service.py`, find the `update_project` method (look for the method that processes `_UPDATABLE` set and calls `db.commit()`). Add cache invalidation after the project fields are updated, before `db.commit()`:

```python
        # Invalidate readiness gap cache so the next readiness-gap request regenerates it
        if project.metadata_json and "readiness_gap_report" in project.metadata_json:
            meta = dict(project.metadata_json)
            del meta["readiness_gap_report"]
            project.metadata_json = meta
```

- [ ] **Step 8: Run the route test**

```bash
venv/bin/pytest tests/test_r5_incubation_model.py::test_readiness_gap_endpoint_exists -v
```

Expected: PASS.

- [ ] **Step 9: Manual smoke test**

Start the backend:
```bash
cd /home/evan/Desktop/martin\ os\ v2/martin-system/backend
DATABASE_URL="postgresql+asyncpg://ecowas_user:ecowas_pass@localhost:5433/ecowas_summit_db" \
  venv/bin/uvicorn app.main:app --reload --port 8000
```

Test with curl (replace TOKEN and PROJECT_ID):
```bash
curl -s -H "Authorization: Bearer TOKEN" \
  http://localhost:8000/pipeline/PROJECT_ID/readiness-gap | python3 -m json.tool
```

Expected: JSON with `gaps` array, `current_score`, `threshold`.

- [ ] **Step 10: Commit**

```bash
git add backend/app/api/routes/pipeline.py backend/app/services/project_pipeline_service.py
git commit -m "feat(r5): investor filter, start_in_incubation ingest, readiness-gap endpoint, threshold setting"
```

---

## Task 6: Frontend Types — Add INCUBATION to ProjectStatus

**Files:**
- Modify: `frontend/src/types/pipeline.ts`

- [ ] **Step 1: Add the enum value**

In `frontend/src/types/pipeline.ts` at line 3, the `ProjectStatus` enum currently starts with `DRAFT`. Add `INCUBATION` as the first value:

```typescript
export enum ProjectStatus {
    // Pre-Pipeline
    INCUBATION = "INCUBATION",

    // Submission Phase
    DRAFT = "DRAFT",
    PIPELINE = "PIPELINE",
    UNDER_REVIEW = "UNDER_REVIEW",

    // Decision Phase
    DECLINED = "DECLINED",
    NEEDS_REVISION = "NEEDS_REVISION",
    SUMMIT_READY = "SUMMIT_READY",

    // Deal Room Phase
    DEAL_ROOM_FEATURED = "DEAL_ROOM_FEATURED",
    IN_NEGOTIATION = "IN_NEGOTIATION",

    // Post-Deal Phase
    COMMITTED = "COMMITTED",
    IMPLEMENTED = "IMPLEMENTED",

    // Other
    ON_HOLD = "ON_HOLD",
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd /home/evan/Desktop/martin\ os\ v2/martin-system/frontend
npm run tsc -- --noEmit 2>&1 | head -20
```

Expected: no new errors related to ProjectStatus.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/types/pipeline.ts
git commit -m "feat(r5): add INCUBATION to frontend ProjectStatus enum"
```

---

## Task 7: DealPipeline.tsx — Incubation Row Styles, Score Bar, Graduate Chip, Filter

**Files:**
- Modify: `frontend/src/pages/DealPipeline.tsx`

The current file has:
- `STATUS_LABEL` map at lines 13–15
- `STATUS_DOT` map at lines 25
- `statusFilter` state at line 60
- Filter `<select>` for status at lines 480–493
- Row rendering loop starting around line 554, status dot at line 679

- [ ] **Step 1: Add INCUBATION to STATUS_LABEL and STATUS_DOT maps**

Find the `STATUS_LABEL` object (around line 13). Add `INCUBATION: '⚗ Incubation'`:

```typescript
const STATUS_LABEL: Record<string, string> = {
  INCUBATION: '⚗ Incubation',
  DRAFT: 'Draft',
  PIPELINE: 'Pipeline',
  UNDER_REVIEW: 'Under review',
  ...
```

Find the `STATUS_DOT` object (around line 25). Add `INCUBATION: '#7c3aed'` (purple):

```typescript
const STATUS_DOT: Record<string, string> = {
  INCUBATION: '#7c3aed',
  DECLINED: 'var(--terra)',
  ON_HOLD: 'var(--ink-400)',
  DRAFT: 'var(--ink-400)',
  ...
```

- [ ] **Step 2: Add showIncubation filter state**

Near the `statusFilter` state declaration (around line 60), add:

```typescript
const [showIncubation, setShowIncubation] = useState(true);
```

- [ ] **Step 3: Apply showIncubation to the filtered projects list**

Find the `filteredProjects` computed list (around line 188):

```typescript
const filteredProjects = projects.filter(p => {
```

Add a condition to optionally hide incubation projects:

```typescript
const filteredProjects = projects.filter(p => {
  if (!showIncubation && p.status === ProjectStatus.INCUBATION) return false;
  // ... existing filters ...
```

Also exclude INCUBATION from the default `statusFilter` dropdown unless the user explicitly selects it. The Show/Hide toggle handles visibility; INCUBATION will appear in the status dropdown naturally since it's in STATUS_LABEL.

- [ ] **Step 4: Add the Incubation filter dropdown to the filters bar**

Find the status filter `<select>` (around line 479). After it, add the incubation toggle dropdown:

```tsx
        {/* Incubation visibility filter */}
        <select
          value={showIncubation ? 'show' : 'hide'}
          onChange={e => { setShowIncubation(e.target.value === 'show'); setCurrentPage(1); }}
          style={{
            background: showIncubation ? '#f5f3ff' : 'var(--surface)',
            border: `1px solid ${showIncubation ? '#e9d5ff' : 'var(--border)'}`,
            color: showIncubation ? '#7c3aed' : 'var(--ink-700)',
            padding: '6px 10px', fontSize: 12,
            fontFamily: 'inherit', cursor: 'pointer', outline: 'none',
            fontWeight: showIncubation ? 600 : 400,
          }}
        >
          <option value="show">⚗ Show Incubation</option>
          <option value="hide">Hide Incubation</option>
        </select>
```

- [ ] **Step 5: Style Incubation rows differently in the row rendering loop**

Find the row rendering loop (around line 554). The row starts with a `<div>` that uses `background: 'var(--surface)'`. Add a conditional background for incubation rows:

```tsx
        const isIncubation = project.status === ProjectStatus.INCUBATION;
        // ... existing: const statusColor = STATUS_DOT[...] ...

        return (
          <div key={project.id}
            style={{
              display: 'grid',
              gridTemplateColumns: 'minmax(0, 2.4fr) 0.8fr 1.2fr 0.9fr 1.1fr 0.9fr',
              padding: '14px 24px',
              borderBottom: last ? 'none' : `1px solid ${isIncubation ? '#f3e8ff' : 'var(--border)'}`,
              background: isIncubation ? '#faf5ff' : 'var(--surface)',
              cursor: 'pointer',
              transition: 'background 0.1s',
            }}
            onClick={() => navigate(`/deal-pipeline/${project.id}`)}
          >
```

- [ ] **Step 6: Add incubation label chip and inline score bar to the project name cell**

Find where the project name chip/ID is rendered (around line 558–600). The current pattern shows an ID chip above the project name. For incubation rows, replace the ID chip with a purple ⚗ label, and add the inline score bar below the value chain stages:

Locate the block that renders the "name cell" (first column). After rendering `value_chain_stages` tags and gender/youth badges, add:

```tsx
                {/* Incubation inline score bar */}
                {isIncubation && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 4 }}>
                    <div style={{ width: 70, height: 3, background: '#e9d5ff', borderRadius: 2, overflow: 'hidden' }}>
                      <div style={{
                        width: `${Math.min(100, (score / (threshold || 40)) * 100)}%`,
                        height: '100%',
                        background: score >= (threshold || 40) ? '#16a34a' : '#7c3aed',
                        borderRadius: 2,
                      }} />
                    </div>
                    <span style={{ fontSize: 9, color: score >= (threshold || 40) ? '#059669' : '#7c3aed', fontWeight: 600 }}>
                      {score >= (threshold || 40) ? '✓ Ready to graduate' : `${score.toFixed(0)}/${threshold || 40} needed`}
                    </span>
                  </div>
                )}
```

Also, find the ID chip (the `#53678e3d` style chip). Wrap it in a condition so incubation rows show a purple ⚗ label instead:

```tsx
                {isIncubation ? (
                  <div style={{ fontSize: 9, color: '#7c3aed', fontWeight: 700, marginBottom: 2, letterSpacing: '0.05em' }}>⚗ INCUBATION</div>
                ) : (
                  <div style={{ fontSize: 9, color: 'var(--ink-400)', fontWeight: 600, marginBottom: 2, letterSpacing: '0.06em', fontFamily: "'Geist Mono', monospace" }}>
                    #{project.id.slice(0, 8)} ...
                  </div>
                )}
```

- [ ] **Step 7: Add Graduate chip to the status column for eligible incubation projects**

Find the status column rendering (around line 679):

```tsx
                <span style={{ width: 6, height: 6, ... }} />
                <span style={{ fontSize: 12, ... }}>{STATUS_LABEL[project.status]...}</span>
```

After this block, add the Graduate chip:

```tsx
                {isIncubation && score >= (threshold || 40) && (
                  <span
                    onClick={e => { e.stopPropagation(); navigate(`/deal-pipeline/${project.id}`); }}
                    style={{
                      fontSize: 9, background: '#dcfce7', color: '#16a34a',
                      padding: '1px 6px', borderRadius: 10, fontWeight: 700, cursor: 'pointer',
                      marginLeft: 4,
                    }}
                  >↑ Graduate</span>
                )}
```

- [ ] **Step 8: Add threshold state loaded from platform settings**

Near the top of the `DealPipeline` component function (after existing state declarations), add:

```tsx
  const [threshold, setThreshold] = useState<number>(40);

  useEffect(() => {
    api.get('/pipeline/settings').then(r => {
      const t = Number(r.data?.incubation_graduation_threshold);
      if (!isNaN(t)) setThreshold(t);
    }).catch(() => {});
  }, []);
```

- [ ] **Step 9: Verify TypeScript compiles**

```bash
cd /home/evan/Desktop/martin\ os\ v2/martin-system/frontend
npm run tsc -- --noEmit 2>&1 | head -30
```

Expected: no new errors.

- [ ] **Step 10: Commit**

```bash
git add frontend/src/pages/DealPipeline.tsx
git commit -m "feat(r5): incubation row styles, score bar, graduate chip, show/hide filter in DealPipeline"
```

---

## Task 8: NewProject.tsx — Start in Incubation Toggle

**Files:**
- Modify: `frontend/src/pages/NewProject.tsx`

- [ ] **Step 1: Add startInIncubation state**

In `frontend/src/pages/NewProject.tsx`, find the `useState` block for `formData` (line 11). After it, add:

```tsx
  const [startInIncubation, setStartInIncubation] = useState(true);
```

- [ ] **Step 2: Pass start_in_incubation to the API payload**

Find the `projectData` object construction in `handleSubmit` (around line 152). Add:

```tsx
      const projectData: any = {
        ...
        start_in_incubation: startInIncubation,
      };
```

- [ ] **Step 3: Add the toggle UI to the form**

Find the opening `<form>` tag (around line 276). The form starts with the project name field. Add the toggle **as the very first element inside the form**, before the name field:

```tsx
        {/* Stage toggle */}
        <div style={{ padding: '16px 24px', borderBottom: '1px solid var(--border-light)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: startInIncubation ? '#faf5ff' : undefined }}>
          <div>
            <div style={{ fontSize: 13, fontWeight: 600, color: startInIncubation ? '#7c3aed' : 'var(--ink-900)' }}>
              {startInIncubation ? '⚗ Start in Incubation (Stage 0)' : '✏ Start as Draft'}
            </div>
            <div style={{ fontSize: 11, color: 'var(--ink-500)', marginTop: 2 }}>
              {startInIncubation
                ? 'Project will be hidden from investors until AfCEN score reaches graduation threshold.'
                : 'Project enters the pipeline immediately as a Draft.'}
            </div>
          </div>
          <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={startInIncubation}
              onChange={e => setStartInIncubation(e.target.checked)}
              style={{ width: 16, height: 16, cursor: 'pointer', accentColor: '#7c3aed' }}
            />
          </label>
        </div>
```

- [ ] **Step 4: Verify TypeScript compiles**

```bash
cd /home/evan/Desktop/martin\ os\ v2/martin-system/frontend
npm run tsc -- --noEmit 2>&1 | head -20
```

Expected: no new errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/NewProject.tsx
git commit -m "feat(r5): add Start in Incubation toggle to New Project form"
```

---

## Task 9: ReadinessTab Component + ProjectDetails Wiring

**Files:**
- Create: `frontend/src/components/pipeline/ReadinessTab.tsx`
- Modify: `frontend/src/pages/ProjectDetails.tsx`

- [ ] **Step 1: Create ReadinessTab.tsx**

Create `frontend/src/components/pipeline/ReadinessTab.tsx`:

```tsx
import React, { useEffect, useState } from 'react';
import api from '../../services/api';
import { Project, ProjectScoreDetail } from '../../types/pipeline';

interface GapItem {
  criterion: string;
  weight: string;
  issue: string;
  action: string;
}

interface ReadinessGapResponse {
  gaps: GapItem[];
  current_score: number;
  threshold: number;
  cached: boolean;
}

interface Props {
  project: Project;
  scoreDetails: ProjectScoreDetail[];
  onGraduate: () => void;
  canEdit: boolean;
}

const CRITERION_COLORS: Record<string, { bg: string; border: string; text: string; icon: string }> = {
  green: { bg: '#f0fdf4', border: '#bbf7d0', text: '#15803d', icon: '✓' },
  amber: { bg: '#fffbeb', border: '#fde68a', text: '#b45309', icon: '!' },
  red: { bg: '#fef2f2', border: '#fecaca', text: '#b91c1c', icon: '✕' },
};

function getCriterionColor(score: number): 'green' | 'amber' | 'red' {
  if (score >= 50) return 'green';
  if (score >= 20) return 'amber';
  return 'red';
}

const ReadinessTab: React.FC<Props> = ({ project, scoreDetails, onGraduate, canEdit }) => {
  const [gapReport, setGapReport] = useState<ReadinessGapResponse | null>(null);
  const [loadingGap, setLoadingGap] = useState(false);
  const [gapError, setGapError] = useState<string | null>(null);
  const [graduating, setGraduating] = useState(false);
  const [threshold, setThreshold] = useState(40);

  useEffect(() => {
    // Load threshold from platform settings
    api.get('/pipeline/settings').then(r => {
      const t = Number(r.data?.incubation_graduation_threshold);
      if (!isNaN(t)) setThreshold(t);
    }).catch(() => {});
  }, []);

  useEffect(() => {
    if (!project.id) return;
    setLoadingGap(true);
    setGapError(null);
    api.get(`/pipeline/${project.id}/readiness-gap`)
      .then(r => setGapReport(r.data))
      .catch(e => setGapError(e?.response?.data?.detail || 'Failed to load gap report'))
      .finally(() => setLoadingGap(false));
  }, [project.id]);

  const currentScore = Number(project.afcen_score ?? 0);
  const scorePercent = Math.min(100, (currentScore / threshold) * 100);
  const canGraduate = currentScore >= threshold;

  const handleGraduate = async () => {
    if (!canGraduate || !canEdit) return;
    setGraduating(true);
    try {
      await api.post(`/pipeline/${project.id}/advance`, { new_stage: 'DRAFT' });
      onGraduate();
    } catch (e: any) {
      alert(e?.response?.data?.detail || 'Failed to graduate project');
    } finally {
      setGraduating(false);
    }
  };

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 320px', gap: 24 }}>
      {/* Left: Checklist */}
      <div>
        {/* Score bar */}
        <div style={{ background: '#f5f3ff', border: '1px solid #e9d5ff', borderRadius: 8, padding: 16, marginBottom: 20, display: 'flex', alignItems: 'center', gap: 16 }}>
          <div style={{ textAlign: 'center', minWidth: 56 }}>
            <div style={{ fontSize: 28, fontWeight: 800, color: '#7c3aed', lineHeight: 1 }}>{currentScore.toFixed(0)}</div>
            <div style={{ fontSize: 9, color: '#7c3aed', fontWeight: 600 }}>/100</div>
          </div>
          <div style={{ flex: 1 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, color: '#6b7280', marginBottom: 4 }}>
              <span>AfCEN Readiness Score</span>
              <span style={{ color: '#7c3aed', fontWeight: 600 }}>Need {threshold} to graduate</span>
            </div>
            <div style={{ height: 8, background: '#e9d5ff', borderRadius: 4, overflow: 'hidden' }}>
              <div style={{ width: `${scorePercent}%`, height: '100%', background: 'linear-gradient(90deg,#7c3aed,#a855f7)', borderRadius: 4, transition: 'width 0.4s' }} />
            </div>
            <div style={{ fontSize: 10, color: '#6b7280', marginTop: 4 }}>
              {canGraduate
                ? 'Score meets graduation threshold — ready to graduate.'
                : `${(threshold - currentScore).toFixed(1)} points needed to unlock graduation`}
            </div>
          </div>
        </div>

        {/* WAIIS checklist */}
        <div style={{ fontSize: 11, fontWeight: 700, color: '#374151', marginBottom: 10, textTransform: 'uppercase', letterSpacing: '0.06em' }}>WAIIS Criteria Checklist</div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          {scoreDetails.length === 0 ? (
            <div style={{ fontSize: 12, color: 'var(--ink-400)', padding: 12 }}>
              No scores yet — the project needs to be scored first. Upload documents or fill in project fields.
            </div>
          ) : scoreDetails.map(detail => {
            const colorKey = getCriterionColor(detail.score);
            const c = CRITERION_COLORS[colorKey];
            const criterionName = (detail as any).criterion?.criterion_name ?? 'Unknown';
            const weight = (detail as any).criterion?.weight ?? '?';
            return (
              <div key={detail.id} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '10px 12px', background: c.bg, border: `1px solid ${c.border}`, borderRadius: 8 }}>
                <div style={{ width: 20, height: 20, borderRadius: '50%', background: colorKey === 'green' ? '#16a34a' : colorKey === 'amber' ? '#d97706' : '#dc2626', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                  <span style={{ color: 'white', fontSize: colorKey === 'red' ? 10 : 11 }}>{c.icon}</span>
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 11, fontWeight: 600, color: c.text }}>{criterionName} · {Number(weight) * 10:.0f}%</div>
                  <div style={{ fontSize: 10, color: '#6b7280' }}>{detail.notes || 'No notes'}</div>
                </div>
                <div style={{ fontSize: 11, fontWeight: 700, color: c.text }}>{detail.score.toFixed(0)}</div>
              </div>
            );
          })}
        </div>

        {/* Graduation button */}
        <div style={{ marginTop: 16, padding: 12, background: canGraduate ? '#f0fdf4' : '#f3f4f6', border: `1px dashed ${canGraduate ? '#86efac' : '#d1d5db'}`, borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          {canGraduate ? (
            <div style={{ fontSize: 11, color: '#15803d' }}>Score <strong>{currentScore.toFixed(0)}</strong> meets the graduation threshold of <strong>{threshold}</strong>.</div>
          ) : (
            <div style={{ fontSize: 11, color: '#6b7280' }}>Score must reach <strong>{threshold}</strong> to graduate. Currently <strong style={{ color: '#7c3aed' }}>{currentScore.toFixed(0)}</strong>.</div>
          )}
          <button
            onClick={handleGraduate}
            disabled={!canGraduate || !canEdit || graduating}
            style={{
              background: canGraduate && canEdit ? '#16a34a' : '#e5e7eb',
              color: canGraduate && canEdit ? 'white' : '#9ca3af',
              border: 'none', padding: '7px 16px', borderRadius: 6, fontSize: 11,
              fontWeight: 600, cursor: canGraduate && canEdit ? 'pointer' : 'not-allowed',
              fontFamily: 'inherit',
            }}
          >
            {graduating ? 'Graduating…' : 'Graduate to Draft ↑'}
          </button>
        </div>
      </div>

      {/* Right: AI Gap Report */}
      <div>
        <div style={{ background: '#1e1b4b', borderRadius: 10, padding: 16, minHeight: 200 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
            <div style={{ width: 22, height: 22, borderRadius: 6, background: '#7c3aed', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <span style={{ color: 'white', fontSize: 11, fontWeight: 700 }}>✦</span>
            </div>
            <div style={{ fontSize: 11, fontWeight: 700, color: 'white' }}>Martin's Gap Report</div>
            {gapReport?.cached && <span style={{ fontSize: 9, color: '#818cf8' }}>(cached)</span>}
          </div>

          {loadingGap ? (
            <div style={{ fontSize: 10, color: '#c4b5fd' }}>Analysing project gaps…</div>
          ) : gapError ? (
            <div style={{ fontSize: 10, color: '#f87171' }}>{gapError}</div>
          ) : gapReport ? (
            <div style={{ fontSize: 10, color: '#c4b5fd', lineHeight: 1.7 }}>
              {gapReport.gaps.map((gap, i) => (
                <div key={i} style={{ marginBottom: 8, paddingLeft: 8, borderLeft: '2px solid #7c3aed' }}>
                  <div style={{ fontWeight: 700, color: '#a78bfa', marginBottom: 2 }}>
                    {gap.criterion} <span style={{ color: '#818cf8', fontWeight: 400 }}>· {gap.weight}</span>
                  </div>
                  <div style={{ marginBottom: 2 }}>{gap.issue}</div>
                  <div style={{ color: 'white', fontWeight: 600 }}>→ {gap.action}</div>
                </div>
              ))}
              <div style={{ marginTop: 10, fontSize: 9, color: '#818cf8' }}>
                Addressing the gaps above should push your score past {gapReport.threshold}.
              </div>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
};

export default ReadinessTab;
```

Note: The `{Number(weight) * 10:.0f}%` template expression is pseudo-code for the plan — actual TypeScript syntax would be `{(Number(weight) * 10).toFixed(0)}%`.

- [ ] **Step 2: Wire Readiness tab into ProjectDetails.tsx**

In `frontend/src/pages/ProjectDetails.tsx`:

**2a. Add import at the top:**
```tsx
import ReadinessTab from '../components/pipeline/ReadinessTab';
```

**2b. Extend the activeTab type** (line 15):
```tsx
const [activeTab, setActiveTab] = useState<'overview' | 'financials' | 'documents' | 'history' | 'matches' | 'readiness'>('overview');
```

**2c. Add Readiness tab entry** in the tab array (around line 443):
```tsx
          {[
            { key: 'overview', label: 'Overview' },
            { key: 'matches', label: 'Investor matches' },
            { key: 'financials', label: 'Financials' },
            { key: 'documents', label: 'Documents' },
            { key: 'history', label: 'History' },
            // Readiness tab only visible for incubation projects
            ...(project.status === ProjectStatus.INCUBATION
              ? [{ key: 'readiness', label: '⚗ Readiness' }]
              : []),
          ].map(({ key, label }) => {
```

Make the Readiness tab label purple when active. Add special styling for the readiness tab button: after the `on` variable assignment, wrap it:

```tsx
            const isReadiness = key === 'readiness';
            return (
              <button key={key} onClick={() => setActiveTab(key as any)} style={{
                fontSize: 13,
                color: on ? (isReadiness ? '#7c3aed' : 'var(--ink-900)') : 'var(--ink-500)',
                fontWeight: on ? 500 : 400,
                padding: '10px 0',
                borderTop: 'none', borderLeft: 'none', borderRight: 'none',
                borderBottom: on ? `2px solid ${isReadiness ? '#7c3aed' : 'var(--accent)'}` : '2px solid transparent',
                marginBottom: -1, cursor: 'pointer',
                background: 'none', fontFamily: 'inherit',
              }}>
```

**2d. Add Readiness tab content** at the end of the tab content section (around line 791, after the `history` block):

```tsx
          {activeTab === 'readiness' && project && (
            <ReadinessTab
              project={project}
              scoreDetails={scoreDetails}
              canEdit={!!canEdit}
              onGraduate={() => {
                // Reload project data after graduation
                if (projectId) {
                  pipelineService.getProject(projectId).then(setProject);
                  setActiveTab('overview');
                }
              }}
            />
          )}
```

- [ ] **Step 3: Verify TypeScript compiles**

```bash
cd /home/evan/Desktop/martin\ os\ v2/martin-system/frontend
npm run tsc -- --noEmit 2>&1 | head -30
```

Expected: no new errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/pipeline/ReadinessTab.tsx frontend/src/pages/ProjectDetails.tsx
git commit -m "feat(r5): ReadinessTab component with WAIIS checklist + AI gap report + graduation button"
```

---

## Task 10: PlatformSettings.tsx — Graduation Threshold Field

**Files:**
- Modify: `frontend/src/pages/PlatformSettings.tsx` (or wherever admin platform settings are rendered)

First, verify the file exists and find its structure:

```bash
find /home/evan/Desktop/martin\ os\ v2/martin-system/frontend/src -name "PlatformSettings*" | head -5
```

If the file doesn't exist yet, check if there's an admin settings page:

```bash
grep -rn "platform.setting\|gender_threshold\|PlatformSetting" /home/evan/Desktop/martin\ os\ v2/martin-system/frontend/src --include="*.tsx" | head -10
```

- [ ] **Step 1: Find or create the settings page**

If a settings page exists, add the field to it. If not, add the field to the admin section of the existing settings page (likely in `frontend/src/pages/profile/UserProfile.tsx` or a dedicated admin page). The field is admin-only.

**Find the existing settings save pattern.** Look for where `gender_threshold_pct` is saved — it will show how the API call is made.

- [ ] **Step 2: Add the graduation threshold field**

Add a new settings field with this shape:

```tsx
{/* Incubation Graduation Threshold */}
<div style={{ marginBottom: 20 }}>
  <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--ink-700)', marginBottom: 4 }}>
    Incubation Graduation Threshold
  </label>
  <div style={{ fontSize: 11, color: 'var(--ink-500)', marginBottom: 8 }}>
    Minimum AfCEN score (0–100) required for a project to graduate from Incubation to Draft.
  </div>
  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
    <input
      type="number"
      min={0}
      max={100}
      value={graduationThreshold}
      onChange={e => setGraduationThreshold(Number(e.target.value))}
      style={{ width: 80, padding: '6px 10px', border: '1px solid var(--border)', borderRadius: 6, fontSize: 13, fontWeight: 700 }}
    />
    <span style={{ fontSize: 11, color: 'var(--ink-500)' }}>/ 100</span>
  </div>
</div>
```

**State and save:**

```tsx
const [graduationThreshold, setGraduationThreshold] = useState(40);

// On load:
useEffect(() => {
  api.get('/pipeline/settings').then(r => {
    const t = Number(r.data?.incubation_graduation_threshold);
    if (!isNaN(t)) setGraduationThreshold(t);
  }).catch(() => {});
}, []);

// On save (add to existing save handler):
await api.patch('/pipeline/settings', {
  ...existingPayload,
  incubation_graduation_threshold: graduationThreshold,
});
```

- [ ] **Step 3: Verify TypeScript compiles**

```bash
npm run tsc -- --noEmit 2>&1 | head -20
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/PlatformSettings.tsx  # (or whichever file was modified)
git commit -m "feat(r5): add graduation threshold field to platform settings"
```

---

## Task 11: End-to-End Smoke Test

- [ ] **Step 1: Start local backend**

```bash
cd /home/evan/Desktop/martin\ os\ v2/martin-system/backend
DATABASE_URL="postgresql+asyncpg://ecowas_user:ecowas_pass@localhost:5433/ecowas_summit_db" \
  venv/bin/uvicorn app.main:app --reload --port 8000
```

- [ ] **Step 2: Start local frontend**

```bash
cd /home/evan/Desktop/martin\ os\ v2/martin-system/frontend
npm run dev
```

- [ ] **Step 3: Test the full flow**

1. Log in as `magwaro@ecowasiisummit.net` / `Admin@2026`
2. Navigate to Deal Pipeline → click **+ New Project**
3. Verify the **⚗ Start in Incubation (Stage 0)** toggle is visible and checked by default
4. Submit a new project — verify it appears in the list with a purple ⚗ badge and status dot
5. Verify the project does **not** show a Deal Room badge or investor-facing status
6. Click the project row — verify the **⚗ Readiness** tab appears in the tab bar
7. Click the Readiness tab — verify WAIIS checklist rows load and the AI gap report panel shows
8. Navigate to Admin → Platform Settings — verify **Incubation Graduation Threshold** field exists and saves
9. On the pipeline list, verify the **⚗ Show Incubation** filter is present and toggles visibility

- [ ] **Step 4: Run all backend tests**

```bash
cd /home/evan/Desktop/martin\ os\ v2/martin-system/backend
DATABASE_URL="postgresql+asyncpg://ecowas_user:ecowas_pass@localhost:5433/ecowas_summit_db" \
  venv/bin/pytest tests/ -v --tb=short 2>&1 | tail -30
```

Expected: all tests pass, including the new `test_r5_incubation_model.py` tests.

- [ ] **Step 5: Final commit**

```bash
git add -A
git commit -m "test(r5): end-to-end smoke test checklist complete"
```

---

## Spec Coverage Check

| Spec requirement | Task |
|---|---|
| INCUBATION enum before DRAFT | Task 1 (migration) + Task 2 (model) |
| INCUBATION → DRAFT with score gate | Task 3 |
| `start_in_incubation` on ingest | Task 4 (schema) + Task 5 (route + service) |
| Investor visibility filter | Task 5 |
| `GET /pipeline/{id}/readiness-gap` endpoint | Task 5 |
| LLM gap report with JSON output + cache | Task 5 |
| Cache invalidation on project update | Task 5 |
| `incubation_graduation_threshold` platform setting | Task 1 (migration seed) + Task 5 (ALLOWED_KEYS) |
| `INCUBATION` in frontend enum | Task 6 |
| Purple row + inline score bar + Graduate chip | Task 7 |
| Show/Hide Incubation filter in DealPipeline | Task 7 |
| Threshold loaded from API in DealPipeline | Task 7 |
| Start in Incubation toggle in NewProject | Task 8 |
| Readiness tab in ProjectDetails | Task 9 |
| ReadinessTab WAIIS checklist + score bar | Task 9 |
| ReadinessTab AI gap report panel | Task 9 |
| Graduation button (locked until threshold) | Task 9 |
| Graduation threshold field in Platform Settings | Task 10 |
