# R6 Buyer / Offtake Matching Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a buyer/offtake matching system to the deal pipeline — parallel to the existing investor matching — including a `buyers` database, a scoring algorithm, API routes, and a "Buyer / Offtake" sub-tab in ProjectDetails.

**Architecture:** Additive in-place. New `buyers` and `project_buyer_matches` tables via Alembic. New `BuyerMatchingService` mirroring `InvestorMatchingService`. New routes added to `pipeline.py` (static `/buyers/` routes placed BEFORE `/{project_id}` to avoid FastAPI routing clash). Frontend adds a Buyer sub-tab inside the existing Matches tab and a new admin `BuyerDatabase.tsx` page.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2 async, Alembic, PostgreSQL, React 18, TypeScript.

---

## File Map

| File | Action | Purpose |
|------|--------|---------|
| `backend/alembic/versions/r6_buyer_match_20260522.py` | Create | DB migration: buyers + project_buyer_matches tables |
| `backend/app/models/models.py` | Modify | Add `BuyerMatchStatus` enum, `Buyer` model, `ProjectBuyerMatch` model |
| `backend/app/schemas/pipeline_schemas.py` | Modify | Add `BuyerCreate`, `BuyerRead`, `BuyerMatchRead`, `BuyerMatchUpdate` schemas |
| `backend/app/services/buyer_matching_service.py` | Create | Matching algorithm, get_matches, update_status |
| `backend/app/api/routes/pipeline.py` | Modify | Add `/buyers/` CRUD and `/{project_id}/buyer-matches` + `/{project_id}/buyer-match` routes |
| `frontend/src/types/pipeline.ts` | Modify | Add `Buyer`, `BuyerMatch`, `BuyerMatchStatus` types |
| `frontend/src/services/pipelineService.ts` | Modify | Add `getBuyerMatches`, `triggerBuyerMatching`, `updateBuyerMatchStatus`, `listBuyers`, `createBuyer` |
| `frontend/src/pages/ProjectDetails.tsx` | Modify | Add Buyer/Offtake sub-tab inside Matches tab |
| `frontend/src/pages/BuyerDatabase.tsx` | Create | Admin page to manage buyer records (role-gated) |
| `frontend/src/App.tsx` | Modify | Register `/buyer-database` route |

---

## Task 1: Alembic Migration

**Files:**
- Create: `backend/alembic/versions/r6_buyer_match_20260522.py`

- [ ] **Step 1: Create the migration file**

```python
# backend/alembic/versions/r6_buyer_match_20260522.py
"""r6 buyer offtake matching tables

Revision ID: r6_buy3r_m4tch
Revises: r5_1nc0bat10n
Create Date: 2026-05-22
"""
from alembic import op
import sqlalchemy as sa

revision = 'r6_buy3r_m4tch'
down_revision = 'r5_1nc0bat10n'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE buyermatchstatus AS ENUM (
                'DETECTED', 'CONTACTED', 'INTERESTED', 'NEGOTIATING', 'COMMITTED'
            );
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS buyers (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name TEXT NOT NULL,
            commodity_types JSONB,
            volume_mt_per_year FLOAT,
            contract_term_years INT,
            price_floor_usd FLOAT,
            geographic_focus JSONB,
            notes TEXT,
            deleted_at TIMESTAMP,
            created_by UUID REFERENCES users(id) ON DELETE SET NULL,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        );
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS project_buyer_matches (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            buyer_id UUID NOT NULL REFERENCES buyers(id) ON DELETE CASCADE,
            match_score INT NOT NULL DEFAULT 0,
            status buyermatchstatus NOT NULL DEFAULT 'DETECTED',
            match_rationale TEXT,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        );
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS project_buyer_matches;")
    op.execute("DROP TABLE IF EXISTS buyers;")
    op.execute("DROP TYPE IF EXISTS buyermatchstatus;")
```

- [ ] **Step 2: Run the migration**

```bash
cd backend
venv/bin/alembic upgrade head
```

Expected output ends with: `Running upgrade r5_1nc0bat10n -> r6_buy3r_m4tch`

- [ ] **Step 3: Verify tables exist**

```bash
venv/bin/python -c "
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.config import settings

async def check():
    engine = create_async_engine(settings.DATABASE_URL)
    async with engine.connect() as conn:
        for t in ['buyers', 'project_buyer_matches']:
            r = await conn.execute(text(f\"SELECT COUNT(*) FROM information_schema.tables WHERE table_name='{t}'\"))
            print(t, r.scalar())

asyncio.run(check())
"
```

Expected: `buyers 1` and `project_buyer_matches 1`

---

## Task 2: SQLAlchemy Models

**Files:**
- Modify: `backend/app/models/models.py`

Add after the `InvestorMatchStatus` enum and after the `ProjectInvestorMatch` class.

- [ ] **Step 1: Add `BuyerMatchStatus` enum** — place after `InvestorMatchStatus` (around line 128)

```python
class BuyerMatchStatus(str, enum.Enum):
    DETECTED = "DETECTED"
    CONTACTED = "CONTACTED"
    INTERESTED = "INTERESTED"
    NEGOTIATING = "NEGOTIATING"
    COMMITTED = "COMMITTED"
```

- [ ] **Step 2: Add `Buyer` model** — place after the `ProjectInvestorMatch` class (after line ~843)

```python
class Buyer(Base):
    __tablename__ = "buyers"
    __table_args__ = {'extend_existing': True}

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255))
    commodity_types: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    volume_mt_per_year: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    contract_term_years: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    price_floor_usd: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    geographic_focus: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    buyer_matches: Mapped[List["ProjectBuyerMatch"]] = relationship(back_populates="buyer", cascade="all, delete-orphan")


class ProjectBuyerMatch(Base):
    __tablename__ = "project_buyer_matches"
    __table_args__ = {'extend_existing': True}

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("projects.id", ondelete="CASCADE"))
    buyer_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("buyers.id", ondelete="CASCADE"))
    match_score: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[BuyerMatchStatus] = mapped_column(Enum(BuyerMatchStatus), default=BuyerMatchStatus.DETECTED)
    match_rationale: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project: Mapped["Project"] = relationship(back_populates="buyer_matches")
    buyer: Mapped["Buyer"] = relationship(back_populates="buyer_matches")
```

- [ ] **Step 3: Add `buyer_matches` relationship to the `Project` model**

Find the `Project` class and add alongside the existing `investor_matches` relationship:

```python
buyer_matches: Mapped[List["ProjectBuyerMatch"]] = relationship(back_populates="project", cascade="all, delete-orphan")
```

- [ ] **Step 4: Verify models import cleanly**

```bash
cd backend && venv/bin/python -c "from app.models.models import Buyer, ProjectBuyerMatch, BuyerMatchStatus; print('OK')"
```

Expected: `OK`

---

## Task 3: Pydantic Schemas

**Files:**
- Modify: `backend/app/schemas/pipeline_schemas.py`

- [ ] **Step 1: Add buyer schemas** — append to the end of the file

```python
class BuyerCreate(BaseModel):
    name: str
    commodity_types: Optional[List[str]] = None
    volume_mt_per_year: Optional[float] = None
    contract_term_years: Optional[int] = None
    price_floor_usd: Optional[float] = None
    geographic_focus: Optional[List[str]] = None
    notes: Optional[str] = None


class BuyerRead(BaseModel):
    id: UUID
    name: str
    commodity_types: Optional[List[str]] = None
    volume_mt_per_year: Optional[float] = None
    contract_term_years: Optional[int] = None
    price_floor_usd: Optional[float] = None
    geographic_focus: Optional[List[str]] = None
    notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class BuyerMatchUpdate(BaseModel):
    status: str
    notes: Optional[str] = None


class BuyerMatchRead(BaseModel):
    match_id: str
    buyer: BuyerRead
    score: int
    status: str
    match_rationale: Optional[str] = None
```

- [ ] **Step 2: Verify schemas import cleanly**

```bash
cd backend && venv/bin/python -c "from app.schemas.pipeline_schemas import BuyerCreate, BuyerRead, BuyerMatchRead, BuyerMatchUpdate; print('OK')"
```

Expected: `OK`

---

## Task 4: BuyerMatchingService

**Files:**
- Create: `backend/app/services/buyer_matching_service.py`

- [ ] **Step 1: Create the service file**

```python
# backend/app/services/buyer_matching_service.py
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.models import Buyer, BuyerMatchStatus, Project, ProjectBuyerMatch


class BuyerMatchingService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # Matching
    # ------------------------------------------------------------------

    async def match_buyers(self, project_id: uuid.UUID) -> Dict[str, Any]:
        """Run matching algorithm for a project against all active buyers."""
        result = await self.db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        if not project:
            return {"error": "Project not found"}

        buyers_result = await self.db.execute(
            select(Buyer).where(Buyer.deleted_at.is_(None))
        )
        buyers = buyers_result.scalars().all()

        new_matches = 0
        updated_matches = 0

        for buyer in buyers:
            score, rationale = self._calculate_match_score(project, buyer)
            if score >= 50:
                outcome = await self._upsert_match(project, buyer, score, rationale)
                if outcome == "created":
                    new_matches += 1
                elif outcome == "updated":
                    updated_matches += 1

        await self.db.commit()
        return {
            "project_id": str(project_id),
            "new_matches": new_matches,
            "updated_matches": updated_matches,
            "total_buyers_scanned": len(buyers),
        }

    def _calculate_match_score(self, project: Project, buyer: Buyer) -> tuple[int, str]:
        """Score a project-buyer pair. Returns (score 0-100, rationale string)."""
        score = 0
        reasons: List[str] = []

        # +40: commodity type overlaps with project value_chain_stages
        project_stages = {s.upper() for s in (project.value_chain_stages or [])}
        buyer_commodities = {c.upper() for c in (buyer.commodity_types or [])}
        if project_stages & buyer_commodities:
            score += 40
            overlap = ", ".join(project_stages & buyer_commodities)
            reasons.append(f"Commodity match: {overlap}")

        # +25: buyer volume fits project (proxy: project investment >= $10M)
        if buyer.volume_mt_per_year is None or (
            project.investment_amount and float(project.investment_amount) >= 10_000_000
        ):
            score += 25
            reasons.append("Production capacity can meet buyer volume")

        # +20: buyer geographic focus includes project lead_country
        buyer_geo = {g.upper() for g in (buyer.geographic_focus or [])}
        if project.lead_country and (
            project.lead_country.upper() in buyer_geo
            or "ECOWAS" in buyer_geo
            or "WEST AFRICA" in buyer_geo
        ):
            score += 20
            reasons.append(f"Geographic match: {project.lead_country}")

        # +15: ECOWAS cross-border signal (buyer has ECOWAS focus)
        if "ECOWAS" in buyer_geo and project.lead_country:
            score += 15
            reasons.append("ECOWAS regional alignment")

        rationale = " · ".join(reasons) if reasons else "No specific match signals"
        return min(score, 100), rationale

    async def _upsert_match(
        self,
        project: Project,
        buyer: Buyer,
        score: int,
        rationale: str,
    ) -> str:
        result = await self.db.execute(
            select(ProjectBuyerMatch).where(
                ProjectBuyerMatch.project_id == project.id,
                ProjectBuyerMatch.buyer_id == buyer.id,
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            if existing.match_score != score:
                existing.match_score = score
                existing.match_rationale = rationale
                return "updated"
            return "skipped"

        self.db.add(ProjectBuyerMatch(
            project_id=project.id,
            buyer_id=buyer.id,
            match_score=score,
            status=BuyerMatchStatus.DETECTED,
            match_rationale=rationale,
        ))
        return "created"

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    async def get_matches_for_project(self, project_id: uuid.UUID) -> List[Dict[str, Any]]:
        result = await self.db.execute(
            select(ProjectBuyerMatch)
            .where(ProjectBuyerMatch.project_id == project_id)
            .options(selectinload(ProjectBuyerMatch.buyer))
            .order_by(ProjectBuyerMatch.match_score.desc())
        )
        matches = result.scalars().all()
        return [
            {
                "match_id": str(m.id),
                "buyer": m.buyer,
                "score": m.match_score,
                "status": m.status.value,
                "match_rationale": m.match_rationale,
            }
            for m in matches
        ]

    async def update_match_status(
        self,
        match_id: uuid.UUID,
        new_status: str,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        result = await self.db.execute(
            select(ProjectBuyerMatch)
            .where(ProjectBuyerMatch.id == match_id)
            .options(selectinload(ProjectBuyerMatch.buyer))
        )
        match = result.scalar_one_or_none()
        if not match:
            return {"error": "Match not found"}

        match.status = BuyerMatchStatus(new_status.upper())
        if notes is not None:
            match.match_rationale = notes
        await self.db.commit()
        return {"match_id": str(match.id), "status": match.status.value}


def get_buyer_matching_service(db: AsyncSession) -> BuyerMatchingService:
    return BuyerMatchingService(db)
```

- [ ] **Step 2: Verify service imports cleanly**

```bash
cd backend && venv/bin/python -c "from app.services.buyer_matching_service import BuyerMatchingService, get_buyer_matching_service; print('OK')"
```

Expected: `OK`

---

## Task 5: API Routes

**Files:**
- Modify: `backend/app/api/routes/pipeline.py`

> **IMPORTANT:** The `/buyers/` static routes MUST be placed BEFORE the `/{project_id}` parametric route, otherwise FastAPI will try to parse "buyers" as a UUID and return 422. Place them in the same block as the existing `/settings` routes.

- [ ] **Step 1: Add imports at the top of the route file**

Find the existing imports block and add:

```python
from app.models.models import Buyer, BuyerMatchStatus, ProjectBuyerMatch
from app.schemas.pipeline_schemas import BuyerCreate, BuyerRead, BuyerMatchRead, BuyerMatchUpdate
from app.services.buyer_matching_service import get_buyer_matching_service
```

- [ ] **Step 2: Add buyer CRUD routes — place in the static routes block (after `/settings` PATCH, before `/{project_id} GET`)**

```python
# ---------------------------------------------------------------------------
# Buyer database endpoints — MUST be before /{project_id}
# ---------------------------------------------------------------------------

@router.get("/buyers/", response_model=List[BuyerRead])
async def list_buyers(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all active (non-deleted) buyers."""
    result = await db.execute(select(Buyer).where(Buyer.deleted_at.is_(None)).order_by(Buyer.name))
    return result.scalars().all()


@router.post("/buyers/", response_model=BuyerRead)
async def create_buyer(
    payload: BuyerCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Create a new buyer. Admin only."""
    buyer = Buyer(**payload.model_dump(), created_by=current_user.id)
    db.add(buyer)
    await db.commit()
    await db.refresh(buyer)
    return buyer


@router.patch("/buyers/{buyer_id}", response_model=BuyerRead)
async def update_buyer(
    buyer_id: uuid.UUID,
    payload: BuyerCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Update buyer details. Admin only."""
    result = await db.execute(select(Buyer).where(Buyer.id == buyer_id, Buyer.deleted_at.is_(None)))
    buyer = result.scalar_one_or_none()
    if not buyer:
        raise HTTPException(status_code=404, detail="Buyer not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(buyer, k, v)
    await db.commit()
    await db.refresh(buyer)
    return buyer


@router.delete("/buyers/{buyer_id}", response_model=dict)
async def delete_buyer(
    buyer_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Soft-delete a buyer. Admin only."""
    from datetime import datetime
    result = await db.execute(select(Buyer).where(Buyer.id == buyer_id, Buyer.deleted_at.is_(None)))
    buyer = result.scalar_one_or_none()
    if not buyer:
        raise HTTPException(status_code=404, detail="Buyer not found")
    buyer.deleted_at = datetime.utcnow()
    await db.commit()
    return {"deleted": str(buyer_id)}
```

- [ ] **Step 3: Add buyer-match routes — place after `/{project_id}/readiness-gap` and before the end of the file**

```python
@router.get("/{project_id}/buyer-matches", response_model=List[BuyerMatchRead])
async def get_project_buyer_matches(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get buyer/offtake matches for a project."""
    service = get_buyer_matching_service(db)
    matches = await service.get_matches_for_project(project_id)
    return [
        BuyerMatchRead(
            match_id=m["match_id"],
            buyer=m["buyer"],
            score=m["score"],
            status=m["status"],
            match_rationale=m["match_rationale"],
        )
        for m in matches
    ]


@router.post("/{project_id}/buyer-match", response_model=dict)
async def trigger_buyer_matching(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_facilitator),
):
    """Manually trigger buyer matching for a project."""
    service = get_buyer_matching_service(db)
    result = await service.match_buyers(project_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.patch("/buyer-matches/{match_id}", response_model=dict)
async def update_buyer_match_status(
    match_id: uuid.UUID,
    payload: BuyerMatchUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_facilitator),
):
    """Update buyer match status."""
    service = get_buyer_matching_service(db)
    result = await service.update_match_status(
        match_id=match_id,
        new_status=payload.status,
        notes=payload.notes,
    )
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result
```

- [ ] **Step 4: Restart backend and verify routes load**

```bash
pkill -f "uvicorn app.main:app"
cd backend && venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 >> /tmp/martin-backend.log 2>&1 &
sleep 5 && curl -s http://localhost:8000/api/v1/pipeline/buyers/ -H "Authorization: Bearer <token>" | head -5
```

Expected: `[]` (empty list — no buyers yet)

---

## Task 6: Frontend TypeScript Types

**Files:**
- Modify: `frontend/src/types/pipeline.ts`

- [ ] **Step 1: Add buyer types** — append after the existing `InvestorMatch` interface

```typescript
export enum BuyerMatchStatus {
  DETECTED = "DETECTED",
  CONTACTED = "CONTACTED",
  INTERESTED = "INTERESTED",
  NEGOTIATING = "NEGOTIATING",
  COMMITTED = "COMMITTED",
}

export interface Buyer {
  id: string;
  name: string;
  commodity_types?: string[];
  volume_mt_per_year?: number;
  contract_term_years?: number;
  price_floor_usd?: number;
  geographic_focus?: string[];
  notes?: string;
}

export interface BuyerMatch {
  match_id: string;
  buyer: Buyer;
  score: number;
  status: BuyerMatchStatus;
  match_rationale?: string;
}

export interface UpdateBuyerMatchStatusDTO {
  status: BuyerMatchStatus;
  notes?: string;
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit 2>&1 | head -20
```

Expected: no errors

---

## Task 7: Frontend Service Methods

**Files:**
- Modify: `frontend/src/services/pipelineService.ts`

- [ ] **Step 1: Add buyer service methods** — append to the `pipelineService` object

```typescript
getBuyerMatches: async (projectId: string): Promise<BuyerMatch[]> => {
  const response = await api.get(`/pipeline/${projectId}/buyer-matches`);
  return response.data;
},

triggerBuyerMatching: async (projectId: string): Promise<any> => {
  const response = await api.post(`/pipeline/${projectId}/buyer-match`);
  return response.data;
},

updateBuyerMatchStatus: async (matchId: string, data: UpdateBuyerMatchStatusDTO): Promise<any> => {
  const response = await api.patch(`/pipeline/buyer-matches/${matchId}`, data);
  return response.data;
},

listBuyers: async (): Promise<Buyer[]> => {
  const response = await api.get('/pipeline/buyers/');
  return response.data;
},

createBuyer: async (data: Omit<Buyer, 'id'>): Promise<Buyer> => {
  const response = await api.post('/pipeline/buyers/', data);
  return response.data;
},
```

- [ ] **Step 2: Add the import** at the top of `pipelineService.ts` (if not already there):

```typescript
import { Buyer, BuyerMatch, UpdateBuyerMatchStatusDTO } from '../types/pipeline';
```

- [ ] **Step 3: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit 2>&1 | head -20
```

Expected: no errors

---

## Task 8: ProjectDetails — Buyer/Offtake Sub-tab

**Files:**
- Modify: `frontend/src/pages/ProjectDetails.tsx`

The existing Matches tab shows investor matches. Add a sub-tab toggle ("Investor Matches" / "Buyer / Offtake") inside it.

- [ ] **Step 1: Add state and fetch logic** — add after the existing `matches` state

```typescript
const [buyerMatches, setBuyerMatches] = useState<BuyerMatch[]>([]);
const [loadingBuyerMatches, setLoadingBuyerMatches] = useState(false);
const [triggeringBuyerMatch, setTriggeringBuyerMatch] = useState(false);
const [matchSubTab, setMatchSubTab] = useState<'investors' | 'buyers'>('investors');
```

Add the fetch in `useEffect` (alongside existing `fetchMatches` call):

```typescript
const fetchBuyerMatches = async (id: string) => {
  setLoadingBuyerMatches(true);
  try {
    const data = await pipelineService.getBuyerMatches(id);
    setBuyerMatches(data);
  } catch (e) {
    console.error('Failed to load buyer matches', e);
  } finally {
    setLoadingBuyerMatches(false);
  }
};

// Add to existing useEffect that runs on projectId change:
fetchBuyerMatches(projectId);
```

- [ ] **Step 2: Add trigger handler**

```typescript
const handleTriggerBuyerMatch = async () => {
  if (!projectId) return;
  setTriggeringBuyerMatch(true);
  try {
    await pipelineService.triggerBuyerMatching(projectId);
    await fetchBuyerMatches(projectId);
  } catch (e) {
    console.error('Failed to trigger buyer matching', e);
  } finally {
    setTriggeringBuyerMatch(false);
  }
};

const handleUpdateBuyerMatchStatus = async (matchId: string, newStatus: BuyerMatchStatus) => {
  try {
    await pipelineService.updateBuyerMatchStatus(matchId, { status: newStatus });
    setBuyerMatches(prev => prev.map(m => m.match_id === matchId ? { ...m, status: newStatus } : m));
  } catch (e) {
    console.error('Failed to update buyer match status', e);
  }
};
```

- [ ] **Step 3: Replace the Matches tab content** with sub-tabbed version

Find the section that renders the matches tab (`activeTab === 'matches'`) and replace it with:

```tsx
{activeTab === 'matches' && (
  <div>
    {/* Sub-tab toggle */}
    <div style={{ display: 'flex', gap: 8, marginBottom: 20 }}>
      {(['investors', 'buyers'] as const).map(st => (
        <button
          key={st}
          onClick={() => setMatchSubTab(st)}
          style={{
            padding: '6px 14px', fontSize: 12, borderRadius: 6, cursor: 'pointer',
            fontFamily: 'inherit', fontWeight: matchSubTab === st ? 600 : 400,
            background: matchSubTab === st ? 'var(--accent)' : 'var(--surface)',
            color: matchSubTab === st ? 'white' : 'var(--ink-600)',
            border: `1px solid ${matchSubTab === st ? 'var(--accent)' : 'var(--border)'}`,
          }}
        >
          {st === 'investors' ? '💼 Investor Matches' : '🤝 Buyer / Offtake'}
        </button>
      ))}
    </div>

    {/* Investor Matches sub-tab (existing content) */}
    {matchSubTab === 'investors' && (
      <div>
        <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 16 }}>
          <button onClick={() => { /* existing trigger matching handler */ }}
            style={{ padding: '6px 14px', fontSize: 12, background: 'var(--accent)', color: 'white', border: 'none', borderRadius: 6, cursor: 'pointer', fontFamily: 'inherit' }}>
            {triggeringMatch ? 'Running…' : 'Run matching engine'}
          </button>
        </div>
        {loadingMatches ? (
          <div style={{ fontSize: 12, color: 'var(--ink-400)' }}>Loading investor matches…</div>
        ) : matches.length === 0 ? (
          <div style={{ fontSize: 12, color: 'var(--ink-400)' }}>No investor matches yet. Run the matching engine to find potential investors.</div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {matches.map((m: any) => (
              <div key={m.match_id} style={{ padding: 14, background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 8, display: 'flex', alignItems: 'center', gap: 16 }}>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--ink-900)' }}>{m.investor?.name}</div>
                  <div style={{ fontSize: 11, color: 'var(--ink-500)', marginTop: 2 }}>
                    {m.investor?.sector_preferences?.join(', ')} · {m.investor?.geographic_focus?.join(', ')}
                  </div>
                </div>
                <div style={{ fontSize: 20, fontWeight: 800, color: 'var(--accent)', minWidth: 48, textAlign: 'right' }}>{m.score}%</div>
                <select
                  value={m.status}
                  onChange={e => handleUpdateMatchStatus(m.match_id, e.target.value as any)}
                  style={{ fontSize: 11, padding: '4px 8px', border: '1px solid var(--border)', borderRadius: 4, background: 'var(--surface)', color: 'var(--ink-700)', fontFamily: 'inherit' }}
                >
                  {['DETECTED','CONTACTED','INTERESTED','NEGOTIATING','COMMITTED'].map(s => (
                    <option key={s} value={s}>{s}</option>
                  ))}
                </select>
              </div>
            ))}
          </div>
        )}
      </div>
    )}

    {/* Buyer / Offtake sub-tab */}
    {matchSubTab === 'buyers' && (
      <div>
        <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 16 }}>
          <button
            onClick={handleTriggerBuyerMatch}
            disabled={triggeringBuyerMatch}
            style={{ padding: '6px 14px', fontSize: 12, background: 'var(--accent)', color: 'white', border: 'none', borderRadius: 6, cursor: 'pointer', fontFamily: 'inherit' }}
          >
            {triggeringBuyerMatch ? 'Running…' : 'Run buyer matching'}
          </button>
        </div>
        {loadingBuyerMatches ? (
          <div style={{ fontSize: 12, color: 'var(--ink-400)' }}>Loading buyer matches…</div>
        ) : buyerMatches.length === 0 ? (
          <div style={{ fontSize: 12, color: 'var(--ink-400)' }}>No buyer matches yet. Run the buyer matching engine to find potential offtakers.</div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {buyerMatches.map(m => (
              <div key={m.match_id} style={{ padding: 14, background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 8 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 8 }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--ink-900)' }}>{m.buyer.name}</div>
                    <div style={{ fontSize: 11, color: 'var(--ink-500)', marginTop: 2 }}>
                      {m.buyer.commodity_types?.join(', ')}
                      {m.buyer.volume_mt_per_year ? ` · ${m.buyer.volume_mt_per_year.toLocaleString()} MT/yr` : ''}
                      {m.buyer.contract_term_years ? ` · ${m.buyer.contract_term_years}yr contract` : ''}
                    </div>
                  </div>
                  <div style={{ fontSize: 20, fontWeight: 800, color: 'var(--accent)', minWidth: 48, textAlign: 'right' }}>{m.score}%</div>
                  <select
                    value={m.status}
                    onChange={e => handleUpdateBuyerMatchStatus(m.match_id, e.target.value as BuyerMatchStatus)}
                    style={{ fontSize: 11, padding: '4px 8px', border: '1px solid var(--border)', borderRadius: 4, background: 'var(--surface)', color: 'var(--ink-700)', fontFamily: 'inherit' }}
                  >
                    {Object.values(BuyerMatchStatus).map(s => (
                      <option key={s} value={s}>{s}</option>
                    ))}
                  </select>
                </div>
                {m.match_rationale && (
                  <div style={{ fontSize: 10, color: 'var(--ink-400)', paddingTop: 6, borderTop: '1px solid var(--border)' }}>
                    {m.match_rationale}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    )}
  </div>
)}
```

- [ ] **Step 4: Add import for new types** at the top of ProjectDetails.tsx

```typescript
import { BuyerMatch, BuyerMatchStatus } from '../types/pipeline';
```

- [ ] **Step 5: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit 2>&1 | head -20
```

Expected: no errors

---

## Task 9: BuyerDatabase Admin Page

**Files:**
- Create: `frontend/src/pages/BuyerDatabase.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Create BuyerDatabase.tsx**

```tsx
import React, { useEffect, useState } from 'react';
import pipelineService from '../services/pipelineService';
import { Buyer } from '../types/pipeline';

const BuyerDatabase: React.FC = () => {
  const [buyers, setBuyers] = useState<Buyer[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    name: '',
    commodity_types: '',
    volume_mt_per_year: '',
    contract_term_years: '',
    price_floor_usd: '',
    geographic_focus: '',
    notes: '',
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    try {
      const data = await pipelineService.listBuyers();
      setBuyers(data);
    } catch {
      setError('Failed to load buyers');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await pipelineService.createBuyer({
        name: form.name,
        commodity_types: form.commodity_types ? form.commodity_types.split(',').map(s => s.trim()) : [],
        volume_mt_per_year: form.volume_mt_per_year ? Number(form.volume_mt_per_year) : undefined,
        contract_term_years: form.contract_term_years ? Number(form.contract_term_years) : undefined,
        price_floor_usd: form.price_floor_usd ? Number(form.price_floor_usd) : undefined,
        geographic_focus: form.geographic_focus ? form.geographic_focus.split(',').map(s => s.trim()) : [],
        notes: form.notes || undefined,
      });
      setForm({ name: '', commodity_types: '', volume_mt_per_year: '', contract_term_years: '', price_floor_usd: '', geographic_focus: '', notes: '' });
      setShowForm(false);
      load();
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Failed to create buyer');
    } finally {
      setSaving(false);
    }
  };

  const inputStyle: React.CSSProperties = {
    width: '100%', padding: '6px 10px', fontSize: 12, borderRadius: 6,
    border: '1px solid var(--border)', background: 'var(--surface)',
    color: 'var(--ink-900)', fontFamily: 'inherit', boxSizing: 'border-box',
  };

  return (
    <div style={{ padding: '32px 40px', maxWidth: 900 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <div>
          <div style={{ fontSize: 20, fontWeight: 700, color: 'var(--ink-900)' }}>Buyer Database</div>
          <div style={{ fontSize: 12, color: 'var(--ink-500)', marginTop: 2 }}>Manage offtake buyers for project matching</div>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          style={{ padding: '8px 16px', fontSize: 12, background: 'var(--accent)', color: 'white', border: 'none', borderRadius: 6, cursor: 'pointer', fontWeight: 600, fontFamily: 'inherit' }}
        >
          + Add buyer
        </button>
      </div>

      {error && <div style={{ marginBottom: 16, padding: 10, background: '#fef2f2', border: '1px solid #fecaca', borderRadius: 6, fontSize: 12, color: '#b91c1c' }}>{error}</div>}

      {showForm && (
        <form onSubmit={handleSubmit} style={{ marginBottom: 24, padding: 20, background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 8 }}>
          <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 16, color: 'var(--ink-900)' }}>New buyer</div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 12 }}>
            <div>
              <label style={{ fontSize: 11, color: 'var(--ink-600)', display: 'block', marginBottom: 4 }}>Name *</label>
              <input style={inputStyle} required value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} />
            </div>
            <div>
              <label style={{ fontSize: 11, color: 'var(--ink-600)', display: 'block', marginBottom: 4 }}>Commodity types (comma-separated)</label>
              <input style={inputStyle} placeholder="e.g. PROCESSING, INPUTS" value={form.commodity_types} onChange={e => setForm(f => ({ ...f, commodity_types: e.target.value }))} />
            </div>
            <div>
              <label style={{ fontSize: 11, color: 'var(--ink-600)', display: 'block', marginBottom: 4 }}>Volume (MT/yr)</label>
              <input style={inputStyle} type="number" min={0} value={form.volume_mt_per_year} onChange={e => setForm(f => ({ ...f, volume_mt_per_year: e.target.value }))} />
            </div>
            <div>
              <label style={{ fontSize: 11, color: 'var(--ink-600)', display: 'block', marginBottom: 4 }}>Contract term (years)</label>
              <input style={inputStyle} type="number" min={1} value={form.contract_term_years} onChange={e => setForm(f => ({ ...f, contract_term_years: e.target.value }))} />
            </div>
            <div>
              <label style={{ fontSize: 11, color: 'var(--ink-600)', display: 'block', marginBottom: 4 }}>Price floor (USD/MT)</label>
              <input style={inputStyle} type="number" min={0} value={form.price_floor_usd} onChange={e => setForm(f => ({ ...f, price_floor_usd: e.target.value }))} />
            </div>
            <div>
              <label style={{ fontSize: 11, color: 'var(--ink-600)', display: 'block', marginBottom: 4 }}>Geographic focus (comma-separated)</label>
              <input style={inputStyle} placeholder="e.g. Nigeria, ECOWAS" value={form.geographic_focus} onChange={e => setForm(f => ({ ...f, geographic_focus: e.target.value }))} />
            </div>
          </div>
          <div style={{ marginBottom: 12 }}>
            <label style={{ fontSize: 11, color: 'var(--ink-600)', display: 'block', marginBottom: 4 }}>Notes</label>
            <textarea style={{ ...inputStyle, resize: 'vertical', minHeight: 60 }} value={form.notes} onChange={e => setForm(f => ({ ...f, notes: e.target.value }))} />
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button type="submit" disabled={saving} style={{ padding: '7px 16px', fontSize: 12, background: 'var(--accent)', color: 'white', border: 'none', borderRadius: 6, cursor: 'pointer', fontFamily: 'inherit', fontWeight: 600 }}>
              {saving ? 'Saving…' : 'Save buyer'}
            </button>
            <button type="button" onClick={() => setShowForm(false)} style={{ padding: '7px 16px', fontSize: 12, background: 'var(--surface)', color: 'var(--ink-600)', border: '1px solid var(--border)', borderRadius: 6, cursor: 'pointer', fontFamily: 'inherit' }}>
              Cancel
            </button>
          </div>
        </form>
      )}

      {loading ? (
        <div style={{ fontSize: 12, color: 'var(--ink-400)' }}>Loading…</div>
      ) : buyers.length === 0 ? (
        <div style={{ fontSize: 12, color: 'var(--ink-400)' }}>No buyers yet. Add the first buyer to enable offtake matching.</div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {buyers.map(b => (
            <div key={b.id} style={{ padding: '12px 16px', background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 8, display: 'flex', alignItems: 'center', gap: 16 }}>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--ink-900)' }}>{b.name}</div>
                <div style={{ fontSize: 11, color: 'var(--ink-500)', marginTop: 2 }}>
                  {b.commodity_types?.join(', ')}
                  {b.volume_mt_per_year ? ` · ${b.volume_mt_per_year.toLocaleString()} MT/yr` : ''}
                  {b.contract_term_years ? ` · ${b.contract_term_years}yr` : ''}
                  {b.geographic_focus?.length ? ` · ${b.geographic_focus.join(', ')}` : ''}
                </div>
              </div>
              {b.price_floor_usd != null && (
                <div style={{ fontSize: 11, color: 'var(--ink-600)' }}>Floor: ${b.price_floor_usd}/MT</div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default BuyerDatabase;
```

- [ ] **Step 2: Register route in App.tsx**

Find the admin routes section (near `InvestorDatabase`) and add:

```tsx
import BuyerDatabase from './pages/BuyerDatabase';

// Inside <Routes>:
<Route path="/buyer-database" element={<ProtectedRoute><BuyerDatabase /></ProtectedRoute>} />
```

- [ ] **Step 3: Add nav link in sidebar** — find where `InvestorDatabase` or `Deal Pipeline` nav items are listed in `ModernLayout.tsx` or equivalent layout file, and add:

```tsx
{ path: '/buyer-database', label: 'Buyer Database', icon: '🤝', adminOnly: true },
```

- [ ] **Step 4: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit 2>&1 | head -20
```

Expected: no errors

---

## Task 10: End-to-End Smoke Test

- [ ] **Step 1: Create a test buyer via API**

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"magwaro@ecowasiisummit.net","password":"Admin@2026"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

curl -s -X POST http://localhost:8000/api/v1/pipeline/buyers/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "West Africa Grain Corp",
    "commodity_types": ["PROCESSING", "PRODUCTION"],
    "volume_mt_per_year": 50000,
    "contract_term_years": 5,
    "geographic_focus": ["Nigeria", "ECOWAS"]
  }' | python3 -m json.tool
```

Expected: buyer JSON with `id` field

- [ ] **Step 2: Trigger matching on an existing project**

```bash
# Get a project id from the pipeline list
PROJECT_ID=$(curl -s http://localhost:8000/api/v1/pipeline/ \
  -H "Authorization: Bearer $TOKEN" | python3 -c "import sys,json; print(json.load(sys.stdin)[0]['id'])")

curl -s -X POST http://localhost:8000/api/v1/pipeline/$PROJECT_ID/buyer-match \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

Expected: `{"project_id": "...", "new_matches": N, "total_buyers_scanned": 1}`

- [ ] **Step 3: Fetch buyer matches**

```bash
curl -s http://localhost:8000/api/v1/pipeline/$PROJECT_ID/buyer-matches \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

Expected: array of match objects with `match_id`, `buyer`, `score`, `status`, `match_rationale`

- [ ] **Step 4: Open ProjectDetails in Chrome and verify the Buyer / Offtake sub-tab appears in the Matches tab**

Navigate to the project in the UI and click the Matches tab. Confirm:
- "Investor Matches" and "Buyer / Offtake" sub-tab buttons appear
- Buyer/Offtake tab shows the match from Step 2
- Status dropdown is functional

- [ ] **Step 5: Commit**

```bash
git add \
  backend/alembic/versions/r6_buyer_match_20260522.py \
  backend/app/models/models.py \
  backend/app/schemas/pipeline_schemas.py \
  backend/app/services/buyer_matching_service.py \
  backend/app/api/routes/pipeline.py \
  frontend/src/types/pipeline.ts \
  frontend/src/services/pipelineService.ts \
  frontend/src/pages/ProjectDetails.tsx \
  frontend/src/pages/BuyerDatabase.tsx \
  frontend/src/App.tsx

git commit -m "feat(r6): buyer/offtake matching — buyers DB, scoring, sub-tab, admin page"
```
