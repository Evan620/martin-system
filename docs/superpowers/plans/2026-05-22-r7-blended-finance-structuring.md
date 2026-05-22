# R7 Blended Finance Structuring Module — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a DFI window database and rule-based matching engine that scores each project against 15 seeded DFI/climate-finance instruments, plus an LLM-generated blended finance memo — surfaced as a "DFI Windows" sub-tab inside the ProjectDetails Matches panel.

**Architecture:** Three new backend tables (`dfi_windows` seeded with 15 instruments, `project_dfi_matches` for scored match records), a matching service mirroring the buyer-matching pattern, and one LLM endpoint for a structured financing memo. Frontend adds a third sub-tab (`dfi`) to the existing investor/buyer sub-tab switcher in ProjectDetails.

**Tech Stack:** FastAPI, SQLAlchemy async, Alembic, PostgreSQL, React + TypeScript (Vite), existing `llm_service.chat()` for memo generation.

---

## File Map

| File | Action | Purpose |
|------|--------|---------|
| `backend/alembic/versions/r7_dfi_w1nd0ws_20260522.py` | Create | Schema migration: dfi_windows + project_dfi_matches + seed data |
| `backend/app/models/models.py` | Modify | Add `DFIMatchStatus` enum, `DFIWindow` model, `ProjectDFIMatch` model |
| `backend/app/schemas/pipeline_schemas.py` | Modify | Add `DFIWindowRead`, `DFIMatchRead`, `DFIMatchStatusUpdate`, `FinancingMemoResponse` |
| `backend/app/services/dfi_matching_service.py` | Create | Rule-based DFI scoring engine + financing memo via LLM |
| `backend/app/api/routes/pipeline.py` | Modify | 5 new endpoints (list windows, match, get matches, update status, memo) |
| `frontend/src/types/pipeline.ts` | Modify | Add `DFIWindow`, `DFIMatch`, `DFIMatchStatus`, `FinancingMemo` types |
| `frontend/src/services/pipelineService.ts` | Modify | Add `getDFIMatches`, `triggerDFIMatch`, `updateDFIMatchStatus`, `getFinancingMemo`, `listDFIWindows` |
| `frontend/src/pages/ProjectDetails.tsx` | Modify | Add `dfi` sub-tab alongside investor/buyer; financing memo button + modal |

---

## Task 1: Alembic Migration

**Files:**
- Create: `backend/alembic/versions/r7_dfi_w1nd0ws_20260522.py`

- [ ] **Step 1: Write the migration file**

```python
"""r7 blended finance — dfi windows + project_dfi_matches

Revision ID: r7_dfi_w1nd0ws
Revises: r6_buy3r_m4tch
Create Date: 2026-05-22
"""
from alembic import op
import sqlalchemy as sa

revision = 'r7_dfi_w1nd0ws'
down_revision = 'r6_buy3r_m4tch'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE dfimatchstatus AS ENUM (
                'IDENTIFIED', 'APPROACHED', 'IN_REVIEW', 'SUBMITTED', 'APPROVED', 'REJECTED'
            );
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)

    op.execute("""
        DO $$ BEGIN
            CREATE TYPE dfiinstrumenttype AS ENUM (
                'GRANT', 'CONCESSIONAL_LOAN', 'EQUITY', 'BLENDED'
            );
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS dfi_windows (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name TEXT NOT NULL,
            institution TEXT NOT NULL,
            instrument_type dfiinstrumenttype NOT NULL DEFAULT 'BLENDED',
            sectors JSONB,
            geographies JSONB,
            min_size_usd FLOAT,
            max_size_usd FLOAT,
            eligible_stages JSONB,
            gender_focus BOOLEAN DEFAULT FALSE,
            climate_focus BOOLEAN DEFAULT FALSE,
            description TEXT,
            url TEXT,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        );
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS project_dfi_matches (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            dfi_window_id UUID NOT NULL REFERENCES dfi_windows(id) ON DELETE CASCADE,
            fit_score INT NOT NULL DEFAULT 0,
            fit_rationale TEXT,
            status dfimatchstatus NOT NULL DEFAULT 'IDENTIFIED',
            notes TEXT,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        );
    """)

    # Seed 15 DFI windows
    op.execute("""
        INSERT INTO dfi_windows (name, institution, instrument_type, sectors, geographies,
            min_size_usd, max_size_usd, eligible_stages, gender_focus, climate_focus, description, url)
        VALUES
        (
            'Readiness & Preparatory Support',
            'Green Climate Fund (GCF)',
            'GRANT',
            '["Energy", "Agriculture", "Cross-Sector"]',
            '["GLOBAL"]',
            300000, 3000000,
            '["Concept", "Feasibility"]',
            true, true,
            'Readiness support for countries and direct access entities to develop bankable climate projects.',
            'https://www.greenclimate.fund/projects/readiness'
        ),
        (
            'Project Finance Window',
            'Green Climate Fund (GCF)',
            'BLENDED',
            '["Energy", "Agriculture"]',
            '["GLOBAL"]',
            10000000, NULL,
            '["Development", "Construction"]',
            true, true,
            'Large-scale climate mitigation and adaptation financing through grants, concessional loans, and equity.',
            'https://www.greenclimate.fund/projects/submit'
        ),
        (
            'Agriculture & Agro-industry Development Policy Programme (ADPP)',
            'African Development Bank (AfDB)',
            'CONCESSIONAL_LOAN',
            '["Agriculture"]',
            '["ECOWAS", "West Africa"]',
            5000000, 50000000,
            '["Development", "Construction", "Operational"]',
            false, false,
            'Policy-based lending for agricultural transformation in ECOWAS member states.',
            'https://www.afdb.org/en/topics-and-sectors/sectors/agriculture-agro-industry'
        ),
        (
            'Affirmative Finance Action for Women in Africa (AFAWA)',
            'African Development Bank (AfDB)',
            'BLENDED',
            '["Agriculture", "Energy", "Cross-Sector"]',
            '["Africa"]',
            500000, 10000000,
            '["Concept", "Feasibility", "Development"]',
            true, false,
            'Gender-smart blended finance to increase access to finance for women entrepreneurs across Africa.',
            'https://www.afdb.org/en/the-high-5/afawa-affirmative-finance-action-for-women-in-africa'
        ),
        (
            'Agribusiness & Infrastructure Investment',
            'International Finance Corporation (IFC)',
            'BLENDED',
            '["Agriculture", "Energy", "Minerals", "Digital"]',
            '["Africa"]',
            10000000, NULL,
            '["Development", "Construction", "Operational"]',
            false, false,
            'Direct equity and debt investment in private sector agribusiness, energy, and infrastructure.',
            'https://www.ifc.org/en/what-we-do/sector-expertise/agribusiness-forestry'
        ),
        (
            'Agrofinance Programme',
            'PROPARCO (AFD Group)',
            'BLENDED',
            '["Agriculture"]',
            '["Africa", "West Africa"]',
            5000000, 100000000,
            '["Development", "Construction", "Operational"]',
            false, true,
            'French DFI financing for agribusiness value chains including processing, inputs, and smallholder finance.',
            'https://www.proparco.fr/en/sectors/agribusiness'
        ),
        (
            'Agribusiness & Energy Investment',
            'British International Investment (BII)',
            'BLENDED',
            '["Agriculture", "Energy", "Digital"]',
            '["West Africa", "Africa"]',
            5000000, NULL,
            '["Development", "Construction", "Operational"]',
            true, true,
            'UK DFI providing equity and debt to private sector projects in Sub-Saharan Africa.',
            'https://www.bii.co.uk/en/our-investments/'
        ),
        (
            'Agribusiness & Renewable Energy Financing',
            'FMO (Dutch Development Bank)',
            'BLENDED',
            '["Agriculture", "Energy", "Cross-Sector"]',
            '["Africa"]',
            5000000, NULL,
            '["Development", "Construction", "Operational"]',
            true, true,
            'Dutch DFI providing senior debt, mezzanine, and equity to private sector projects in emerging markets.',
            'https://www.fmo.nl/sectors'
        ),
        (
            'Private Sector Financing Programme (PSFP)',
            'IFAD',
            'BLENDED',
            '["Agriculture"]',
            '["GLOBAL"]',
            2000000, 20000000,
            '["Feasibility", "Development", "Construction"]',
            true, false,
            'Blended finance for private sector investments that benefit smallholder farmers and rural populations.',
            'https://www.ifad.org/en/private-sector'
        ),
        (
            'Infrastructure & Agriculture Financing',
            'Islamic Development Bank (IsDB)',
            'CONCESSIONAL_LOAN',
            '["Agriculture", "Energy", "Infrastructure"]',
            '["ECOWAS", "West Africa"]',
            3000000, NULL,
            '["Feasibility", "Development", "Construction"]',
            false, false,
            'Concessional financing and technical assistance for IsDB member country development projects.',
            'https://www.isdb.org/sectors'
        ),
        (
            'Development Financing',
            'Arab Bank for Economic Development in Africa (BADEA)',
            'CONCESSIONAL_LOAN',
            '["Agriculture", "Energy", "Infrastructure"]',
            '["Africa"]',
            1000000, 30000000,
            '["Feasibility", "Development", "Construction"]',
            false, false,
            'Arab-African development cooperation through concessional loans and grants.',
            'https://www.badea.org'
        ),
        (
            'Agricultural Transformation Grants',
            'AGRA (Alliance for a Green Revolution in Africa)',
            'GRANT',
            '["Agriculture"]',
            '["West Africa", "Africa"]',
            100000, 5000000,
            '["Concept", "Feasibility", "Development"]',
            true, false,
            'Grant funding for agricultural transformation including input systems, market development, and policy.',
            'https://agra.org/grant-funding/'
        ),
        (
            'Private Sector Development Finance',
            'DEG (German Development Finance)',
            'BLENDED',
            '["Agriculture", "Energy", "Minerals"]',
            '["Africa"]',
            5000000, NULL,
            '["Development", "Construction", "Operational"]',
            false, true,
            'German DFI providing long-term loans, equity, and mezzanine to private sector development projects.',
            'https://www.deginvest.de/en'
        ),
        (
            'Infrastructure & Natural Resources',
            'Africa Finance Corporation (AFC)',
            'BLENDED',
            '["Energy", "Minerals", "Agriculture", "Infrastructure"]',
            '["Africa"]',
            20000000, NULL,
            '["Development", "Construction", "Operational"]',
            false, false,
            'Pan-African DFI specializing in infrastructure, natural resources, and heavy industry.',
            'https://www.africafc.org/investments'
        ),
        (
            'Scaling Up Renewable Energy Programme (SREP)',
            'Climate Investment Funds (CIF)',
            'BLENDED',
            '["Energy"]',
            '["ECOWAS", "West Africa", "Africa"]',
            5000000, NULL,
            '["Feasibility", "Development", "Construction"]',
            false, true,
            'Concessional finance to pilot low-carbon technologies and scale up renewable energy in developing countries.',
            'https://www.climateinvestmentfunds.org/topics/energy'
        );
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS project_dfi_matches;")
    op.execute("DROP TABLE IF EXISTS dfi_windows;")
    op.execute("DROP TYPE IF EXISTS dfimatchstatus;")
    op.execute("DROP TYPE IF EXISTS dfiinstrumenttype;")
```

- [ ] **Step 2: Verify the migration file is syntactically correct**

```bash
cd /home/evan/Desktop/martin\ os\ v2/martin-system/backend
python -c "import py_compile; py_compile.compile('alembic/versions/r7_dfi_w1nd0ws_20260522.py', doraise=True); print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/alembic/versions/r7_dfi_w1nd0ws_20260522.py
git commit -m "feat(r7): migration — dfi_windows + project_dfi_matches + 15 seeded instruments"
```

---

## Task 2: ORM Models

**Files:**
- Modify: `backend/app/models/models.py` (after `ProjectBuyerMatch` class, around line 890)

- [ ] **Step 1: Add enums and models**

After the `ProjectBuyerMatch` class (around line 889), insert:

```python
class DFIMatchStatus(str, enum.Enum):
    IDENTIFIED = "IDENTIFIED"
    APPROACHED = "APPROACHED"
    IN_REVIEW = "IN_REVIEW"
    SUBMITTED = "SUBMITTED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class DFIInstrumentType(str, enum.Enum):
    GRANT = "GRANT"
    CONCESSIONAL_LOAN = "CONCESSIONAL_LOAN"
    EQUITY = "EQUITY"
    BLENDED = "BLENDED"


class DFIWindow(Base):
    __tablename__ = "dfi_windows"
    __table_args__ = {'extend_existing': True}

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255))
    institution: Mapped[str] = mapped_column(String(255))
    instrument_type: Mapped[DFIInstrumentType] = mapped_column(Enum(DFIInstrumentType), default=DFIInstrumentType.BLENDED)
    sectors: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    geographies: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    min_size_usd: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    max_size_usd: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    eligible_stages: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    gender_focus: Mapped[bool] = mapped_column(Boolean, default=False)
    climate_focus: Mapped[bool] = mapped_column(Boolean, default=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    dfi_matches: Mapped[List["ProjectDFIMatch"]] = relationship(back_populates="dfi_window", cascade="all, delete-orphan")


class ProjectDFIMatch(Base):
    __tablename__ = "project_dfi_matches"
    __table_args__ = {'extend_existing': True}

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("projects.id", ondelete="CASCADE"))
    dfi_window_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("dfi_windows.id", ondelete="CASCADE"))
    fit_score: Mapped[int] = mapped_column(Integer, default=0)
    fit_rationale: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[DFIMatchStatus] = mapped_column(Enum(DFIMatchStatus), default=DFIMatchStatus.IDENTIFIED)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project: Mapped["Project"] = relationship(back_populates="dfi_matches")
    dfi_window: Mapped["DFIWindow"] = relationship(back_populates="dfi_matches")
```

Also add `dfi_matches` relationship to the `Project` class. Find the existing relationships block in `Project` (look for `buyer_matches`) and add:

```python
    dfi_matches: Mapped[List["ProjectDFIMatch"]] = relationship(back_populates="project", cascade="all, delete-orphan")
```

- [ ] **Step 2: Verify models import cleanly**

```bash
cd /home/evan/Desktop/martin\ os\ v2/martin-system/backend
venv/bin/python -c "from app.models.models import DFIWindow, ProjectDFIMatch, DFIMatchStatus, DFIInstrumentType; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/models/models.py
git commit -m "feat(r7): ORM models — DFIWindow, ProjectDFIMatch, DFIMatchStatus, DFIInstrumentType"
```

---

## Task 3: Pydantic Schemas

**Files:**
- Modify: `backend/app/schemas/pipeline_schemas.py` (append at end of file)

- [ ] **Step 1: Add schemas at the end of `pipeline_schemas.py`**

```python
class DFIWindowRead(BaseModel):
    id: UUID
    name: str
    institution: str
    instrument_type: str
    sectors: Optional[List[str]] = None
    geographies: Optional[List[str]] = None
    min_size_usd: Optional[float] = None
    max_size_usd: Optional[float] = None
    eligible_stages: Optional[List[str]] = None
    gender_focus: bool = False
    climate_focus: bool = False
    description: Optional[str] = None
    url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class DFIMatchRead(BaseModel):
    match_id: str
    dfi_window: DFIWindowRead
    fit_score: int
    fit_rationale: Optional[str] = None
    status: str
    notes: Optional[str] = None


class DFIMatchStatusUpdate(BaseModel):
    status: str
    notes: Optional[str] = None


class FinancingMemoResponse(BaseModel):
    project_id: str
    project_name: str
    recommended_structure: str
    grant_component_pct: int
    concessional_component_pct: int
    commercial_component_pct: int
    priority_windows: List[str]
    key_risks: List[str]
    next_steps: List[str]
    full_memo: str
```

- [ ] **Step 2: Verify schemas import**

```bash
cd /home/evan/Desktop/martin\ os\ v2/martin-system/backend
venv/bin/python -c "from app.schemas.pipeline_schemas import DFIWindowRead, DFIMatchRead, DFIMatchStatusUpdate, FinancingMemoResponse; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/schemas/pipeline_schemas.py
git commit -m "feat(r7): Pydantic schemas — DFIWindowRead, DFIMatchRead, FinancingMemoResponse"
```

---

## Task 4: DFI Matching Service

**Files:**
- Create: `backend/app/services/dfi_matching_service.py`

- [ ] **Step 1: Write the matching service**

```python
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.models import (
    DFIInstrumentType, DFIMatchStatus, DFIWindow, Project, ProjectDFIMatch,
)
from app.services.llm_service import llm_service


# Map ProjectStatus values to stage labels used in DFI window eligible_stages
_STAGE_MAP: Dict[str, str] = {
    "INCUBATION": "Concept",
    "DRAFT": "Concept",
    "PIPELINE": "Concept",
    "UNDER_REVIEW": "Feasibility",
    "SUMMIT_READY": "Feasibility",
    "DEAL_ROOM_FEATURED": "Development",
    "IN_NEGOTIATION": "Development",
    "COMMITTED": "Construction",
    "NEEDS_REVISION": "Feasibility",
    "DECLINED": "Concept",
}

# Map pillar names to normalized sector labels
_SECTOR_NORMALISE: Dict[str, str] = {
    "ENERGY": "Energy",
    "AGRICULTURE": "Agriculture",
    "DIGITAL": "Digital",
    "MINERALS": "Minerals",
    "STRATEGIC MINERALS": "Minerals",
    "RESOURCE_MOBILIZATION": "Cross-Sector",
    "CROSS-SECTOR": "Cross-Sector",
    "CROSS_SECTOR": "Cross-Sector",
    "INDUSTRIALISATION": "Cross-Sector",
}


class DFIMatchingService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def match_dfi_windows(self, project_id: uuid.UUID) -> Dict[str, Any]:
        """Score project against all active DFI windows and upsert matches ≥ 40."""
        result = await self.db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        if not project:
            return {"error": "Project not found"}

        windows_result = await self.db.execute(
            select(DFIWindow).where(DFIWindow.is_active.is_(True))
        )
        windows = windows_result.scalars().all()

        new_matches = 0
        updated_matches = 0

        for window in windows:
            score, rationale = self._score_project_window(project, window)
            if score >= 40:
                outcome = await self._upsert_match(project, window, score, rationale)
                if outcome == "created":
                    new_matches += 1
                elif outcome == "updated":
                    updated_matches += 1

        await self.db.commit()
        return {
            "project_id": str(project_id),
            "new_matches": new_matches,
            "updated_matches": updated_matches,
            "windows_scanned": len(windows),
        }

    def _score_project_window(self, project: Project, window: DFIWindow) -> Tuple[int, str]:
        """Rule-based scoring of a project against one DFI window. Returns (score 0-100, rationale)."""
        score = 0
        reasons: List[str] = []

        # +35: sector overlap
        project_sectors: set[str] = set()
        if project.pillar:
            normalised = _SECTOR_NORMALISE.get(project.pillar.upper(), project.pillar.title())
            project_sectors.add(normalised)
        for stage in (project.value_chain_stages or []):
            normalised = _SECTOR_NORMALISE.get(stage.upper(), stage.title())
            project_sectors.add(normalised)

        window_sectors = set(window.sectors or [])
        if "ALL" in window_sectors or (project_sectors & window_sectors):
            score += 35
            overlap = project_sectors & window_sectors
            reasons.append(f"Sector match: {', '.join(overlap) if overlap else 'cross-sector window'}")

        # +25: geography coverage
        window_geos = {g.upper() for g in (window.geographies or [])}
        geo_match = (
            (project.lead_country and project.lead_country.upper() in window_geos)
            or "ECOWAS" in window_geos
            or "WEST AFRICA" in window_geos
            or "AFRICA" in window_geos
            or "GLOBAL" in window_geos
        )
        if geo_match:
            score += 25
            reasons.append(f"Geographic coverage includes {project.lead_country or 'ECOWAS region'}")

        # +20: investment size within range
        if project.investment_size:
            size_usd = float(project.investment_size)
            min_ok = window.min_size_usd is None or size_usd >= window.min_size_usd
            max_ok = window.max_size_usd is None or size_usd <= window.max_size_usd
            if min_ok and max_ok:
                score += 20
                reasons.append(f"Investment size (${size_usd:,.0f}) fits window range")

        # +10: development stage eligible
        project_stage = _STAGE_MAP.get(
            (project.status.value if hasattr(project.status, 'value') else str(project.status)).upper(),
            ""
        )
        eligible = window.eligible_stages or []
        if project_stage and project_stage in eligible:
            score += 10
            reasons.append(f"Stage eligible: {project_stage}")

        # +5: gender bonus
        if window.gender_focus and project.gender_intentional:
            score += 5
            reasons.append("Gender-intentional project matches gender-focused window")

        # +5: climate bonus
        if window.climate_focus and project.ghg_avoided_target:
            score += 5
            reasons.append("Climate impact target aligns with climate-focused window")

        rationale = " · ".join(reasons) if reasons else "No strong match signals"
        return min(score, 100), rationale

    async def _upsert_match(
        self, project: Project, window: DFIWindow, score: int, rationale: str
    ) -> str:
        result = await self.db.execute(
            select(ProjectDFIMatch).where(
                ProjectDFIMatch.project_id == project.id,
                ProjectDFIMatch.dfi_window_id == window.id,
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            if existing.fit_score != score:
                existing.fit_score = score
                existing.fit_rationale = rationale
                return "updated"
            return "skipped"
        self.db.add(ProjectDFIMatch(
            project_id=project.id,
            dfi_window_id=window.id,
            fit_score=score,
            status=DFIMatchStatus.IDENTIFIED,
            fit_rationale=rationale,
        ))
        return "created"

    async def get_matches_for_project(self, project_id: uuid.UUID) -> List[Dict[str, Any]]:
        result = await self.db.execute(
            select(ProjectDFIMatch)
            .where(ProjectDFIMatch.project_id == project_id)
            .options(selectinload(ProjectDFIMatch.dfi_window))
            .order_by(ProjectDFIMatch.fit_score.desc())
        )
        matches = result.scalars().all()
        return [
            {
                "match_id": str(m.id),
                "dfi_window": m.dfi_window,
                "fit_score": m.fit_score,
                "fit_rationale": m.fit_rationale,
                "status": m.status.value,
                "notes": m.notes,
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
            select(ProjectDFIMatch).where(ProjectDFIMatch.id == match_id)
        )
        match = result.scalar_one_or_none()
        if not match:
            return {"error": "Match not found"}
        match.status = DFIMatchStatus(new_status.upper())
        if notes is not None:
            match.notes = notes
        await self.db.commit()
        return {"match_id": str(match.id), "status": match.status.value}

    async def generate_financing_memo(self, project_id: uuid.UUID) -> Dict[str, Any]:
        """Generate a structured blended finance memo for a project using LLM."""
        result = await self.db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        if not project:
            return {"error": "Project not found"}

        # Fetch top-scored DFI matches
        matches_result = await self.db.execute(
            select(ProjectDFIMatch)
            .where(ProjectDFIMatch.project_id == project_id)
            .options(selectinload(ProjectDFIMatch.dfi_window))
            .order_by(ProjectDFIMatch.fit_score.desc())
            .limit(5)
        )
        top_matches = matches_result.scalars().all()
        window_list = "\n".join(
            f"- {m.dfi_window.name} ({m.dfi_window.institution}) — fit score {m.fit_score}/100, instrument: {m.dfi_window.instrument_type.value}"
            for m in top_matches
        ) if top_matches else "No DFI windows matched yet — run matching engine first."

        prompt = f"""
Project: {project.name}
Sector / Pillar: {project.pillar}
Country: {project.lead_country or 'West Africa'}
Investment Size: ${float(project.investment_size):,.0f} USD
Funding Secured: ${float(project.funding_secured_usd or 0):,.0f} USD
Development Stage: {project.status}
Gender-Intentional: {project.gender_intentional or False}
Climate Impact Target: {project.ghg_avoided_target or 'Not specified'}
Value Chain Stages: {', '.join(project.value_chain_stages or []) or 'Not specified'}

Top Matching DFI Windows:
{window_list}

Produce a blended finance structuring memo in exactly this JSON format (no markdown, raw JSON):
{{
  "recommended_structure": "<1 sentence describing the capital stack>",
  "grant_component_pct": <0-100 integer>,
  "concessional_component_pct": <0-100 integer>,
  "commercial_component_pct": <0-100 integer>,
  "priority_windows": ["<window name>", "<window name>", "<window name>"],
  "key_risks": ["<risk 1>", "<risk 2>", "<risk 3>"],
  "next_steps": ["<step 1>", "<step 2>", "<step 3>"],
  "full_memo": "<3-4 paragraph financing rationale>"
}}
"""
        system_prompt = (
            "You are a blended finance structuring expert for the ECOWAS Investment Summit. "
            "Produce concise, accurate financing memos grounded in the project data provided. "
            "The three percentage components must sum to 100. Respond with raw JSON only."
        )

        try:
            raw = llm_service.chat(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.4,
                max_tokens=800,
            )
            import json
            # Strip markdown fences if present
            clean = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
            memo = json.loads(clean)
        except Exception:
            memo = {
                "recommended_structure": "60% concessional / 30% commercial / 10% grant pending LLM availability",
                "grant_component_pct": 10,
                "concessional_component_pct": 60,
                "commercial_component_pct": 30,
                "priority_windows": [m.dfi_window.name for m in top_matches[:3]] if top_matches else [],
                "key_risks": ["LLM memo generation unavailable", "Run matching engine first if no windows shown"],
                "next_steps": ["Review top-matched DFI windows", "Prepare concept note for lead DFI", "Schedule stakeholder consultation"],
                "full_memo": "Financing memo could not be generated. Ensure the matching engine has been run and the LLM service is available.",
            }

        return {
            "project_id": str(project_id),
            "project_name": project.name,
            **memo,
        }


def get_dfi_matching_service(db: AsyncSession) -> DFIMatchingService:
    return DFIMatchingService(db)
```

- [ ] **Step 2: Verify service imports**

```bash
cd /home/evan/Desktop/martin\ os\ v2/martin-system/backend
venv/bin/python -c "from app.services.dfi_matching_service import get_dfi_matching_service; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/dfi_matching_service.py
git commit -m "feat(r7): DFI matching service — rule-based scoring + LLM financing memo"
```

---

## Task 5: API Routes

**Files:**
- Modify: `backend/app/api/routes/pipeline.py`

These 5 routes must be placed **before** the `/{project_id}` parametric routes (above the `list_pipeline_projects` endpoint is fine, or above the `/{project_id}` block). The static prefixes `dfi-windows`, `dfi-matches/`, and `/{project_id}/dfi-` won't clash.

- [ ] **Step 1: Add import at the top of `pipeline.py`**

Find the imports block and add:
```python
from app.services.dfi_matching_service import get_dfi_matching_service
from app.schemas.pipeline_schemas import (
    # existing imports...,
    DFIWindowRead, DFIMatchRead, DFIMatchStatusUpdate, FinancingMemoResponse,
)
from app.models.models import (
    # existing models...,
    DFIWindow, ProjectDFIMatch, DFIMatchStatus,
)
```

- [ ] **Step 2: Add the 5 endpoints**

Add these routes to `pipeline.py`. Place them **before** the `/{project_id}` endpoint block (before the first route that uses `/{project_id: uuid.UUID}` as a path parameter):

```python
# ── DFI Windows ──────────────────────────────────────────────────────────────

@router.get("/dfi-windows", response_model=List[DFIWindowRead])
async def list_dfi_windows(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all active DFI/climate-finance windows."""
    result = await db.execute(
        select(DFIWindow).where(DFIWindow.is_active.is_(True)).order_by(DFIWindow.institution)
    )
    return result.scalars().all()


@router.patch("/dfi-matches/{match_id}", response_model=dict)
async def update_dfi_match_status(
    match_id: uuid.UUID,
    payload: DFIMatchStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update the status (and optional notes) of a DFI window match."""
    svc = get_dfi_matching_service(db)
    result = await svc.update_match_status(match_id, payload.status, payload.notes)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result
```

And add 3 more routes in the section that handles `/{project_id}` paths (after the existing buyer-match routes, or just before the final `/{project_id}` catch-all):

```python
@router.get("/{project_id}/dfi-matches", response_model=List[DFIMatchRead])
async def get_dfi_matches(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve scored DFI window matches for a project."""
    svc = get_dfi_matching_service(db)
    return await svc.get_matches_for_project(project_id)


@router.post("/{project_id}/dfi-match", response_model=dict)
async def trigger_dfi_matching(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Run the DFI matching engine for a project."""
    svc = get_dfi_matching_service(db)
    result = await svc.match_dfi_windows(project_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/{project_id}/financing-memo", response_model=FinancingMemoResponse)
async def get_financing_memo(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate a blended finance structuring memo for a project (LLM-powered)."""
    svc = get_dfi_matching_service(db)
    result = await svc.generate_financing_memo(project_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result
```

- [ ] **Step 3: Verify backend starts without errors**

```bash
cd /home/evan/Desktop/martin\ os\ v2/martin-system/backend
pkill -f "uvicorn app.main" 2>/dev/null; sleep 2
venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload &
sleep 5
curl -s http://localhost:8001/health | python3 -c "import sys,json; d=json.load(sys.stdin); print('healthy' if d.get('status')=='healthy' else 'FAIL')"
```

Expected: `healthy`

- [ ] **Step 4: Run migration**

```bash
cd /home/evan/Desktop/martin\ os\ v2/martin-system/backend
venv/bin/alembic upgrade r7_dfi_w1nd0ws
```

Expected: no errors, tables created and seeded.

- [ ] **Step 5: Quick API smoke test**

```bash
TOKEN=$(curl -s -X POST http://localhost:8001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"magwaro@ecowasiisummit.net","password":"Admin@2026"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

curl -s -H "Authorization: Bearer $TOKEN" \
  http://localhost:8001/api/pipeline/dfi-windows | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'{len(d)} windows returned')"
```

Expected: `15 windows returned`

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/routes/pipeline.py
git commit -m "feat(r7): API routes — DFI windows list, match trigger, get matches, status update, financing memo"
```

---

## Task 6: Frontend Types + Service

**Files:**
- Modify: `frontend/src/types/pipeline.ts`
- Modify: `frontend/src/services/pipelineService.ts`

- [ ] **Step 1: Add TypeScript types to `pipeline.ts`**

Append at the end of `frontend/src/types/pipeline.ts`:

```typescript
export enum DFIMatchStatus {
    IDENTIFIED = "IDENTIFIED",
    APPROACHED = "APPROACHED",
    IN_REVIEW = "IN_REVIEW",
    SUBMITTED = "SUBMITTED",
    APPROVED = "APPROVED",
    REJECTED = "REJECTED",
}

export enum DFIInstrumentType {
    GRANT = "GRANT",
    CONCESSIONAL_LOAN = "CONCESSIONAL_LOAN",
    EQUITY = "EQUITY",
    BLENDED = "BLENDED",
}

export interface DFIWindow {
    id: string;
    name: string;
    institution: string;
    instrument_type: DFIInstrumentType;
    sectors?: string[];
    geographies?: string[];
    min_size_usd?: number;
    max_size_usd?: number;
    eligible_stages?: string[];
    gender_focus: boolean;
    climate_focus: boolean;
    description?: string;
    url?: string;
}

export interface DFIMatch {
    match_id: string;
    dfi_window: DFIWindow;
    fit_score: number;
    fit_rationale?: string;
    status: DFIMatchStatus;
    notes?: string;
}

export interface UpdateDFIMatchStatusDTO {
    status: DFIMatchStatus;
    notes?: string;
}

export interface FinancingMemo {
    project_id: string;
    project_name: string;
    recommended_structure: string;
    grant_component_pct: number;
    concessional_component_pct: number;
    commercial_component_pct: number;
    priority_windows: string[];
    key_risks: string[];
    next_steps: string[];
    full_memo: string;
}
```

- [ ] **Step 2: Add service methods to `pipelineService.ts`**

In the `pipelineService` object, after the `createBuyer` method, add:

```typescript
    // DFI / Blended Finance
    getDFIMatches: async (projectId: string): Promise<DFIMatch[]> => {
        const response = await api.get(`/pipeline/${projectId}/dfi-matches`);
        return response.data;
    },

    triggerDFIMatching: async (projectId: string): Promise<any> => {
        const response = await api.post(`/pipeline/${projectId}/dfi-match`);
        return response.data;
    },

    updateDFIMatchStatus: async (matchId: string, data: UpdateDFIMatchStatusDTO): Promise<any> => {
        const response = await api.patch(`/pipeline/dfi-matches/${matchId}`, data);
        return response.data;
    },

    getFinancingMemo: async (projectId: string): Promise<FinancingMemo> => {
        const response = await api.post(`/pipeline/${projectId}/financing-memo`);
        return response.data;
    },

    listDFIWindows: async (): Promise<DFIWindow[]> => {
        const response = await api.get('/pipeline/dfi-windows');
        return response.data;
    },
```

Also add the new types to the import from `../types/pipeline` at the top of `pipelineService.ts`. Find the existing import line and add `DFIMatch, DFIWindow, UpdateDFIMatchStatusDTO, FinancingMemo`.

- [ ] **Step 3: Verify TypeScript compiles**

```bash
cd /home/evan/Desktop/martin\ os\ v2/martin-system/frontend
npm run build 2>&1 | tail -5
```

Expected: build exits 0 (no type errors).

- [ ] **Step 4: Commit**

```bash
git add frontend/src/types/pipeline.ts frontend/src/services/pipelineService.ts
git commit -m "feat(r7): frontend types and service methods for DFI matching + financing memo"
```

---

## Task 7: ProjectDetails DFI Sub-Tab

**Files:**
- Modify: `frontend/src/pages/ProjectDetails.tsx`

This task adds a third sub-tab `dfi` alongside the existing `investor` and `buyer` sub-tabs. It also includes a "Generate financing memo" button that opens a modal with structured memo output.

- [ ] **Step 1: Add state variables**

After the existing `matchSubTab` state declaration (around line 33), add:

```typescript
const [dfiMatches, setDFIMatches] = useState<DFIMatch[]>([]);
const [loadingDFIMatches, setLoadingDFIMatches] = useState(false);
const [triggeringDFIMatch, setTriggeringDFIMatch] = useState(false);
const [generatingMemo, setGeneratingMemo] = useState(false);
const [financingMemo, setFinancingMemo] = useState<FinancingMemo | null>(null);
const [showMemoModal, setShowMemoModal] = useState(false);
```

Change the `matchSubTab` type to include `'dfi'`:
```typescript
const [matchSubTab, setMatchSubTab] = useState<'investor' | 'buyer' | 'dfi'>('investor');
```

- [ ] **Step 2: Add imports at top of file**

Add to the existing import from `../../services/pipelineService` (or wherever it's imported):
- `DFIMatch`, `FinancingMemo`, `DFIMatchStatus` from `../../types/pipeline`

- [ ] **Step 3: Add fetchDFIMatches call in useEffect**

Find the `useEffect` that calls `fetchBuyerMatches` and add after it:

```typescript
    if (projectId) {
        fetchDFIMatches(projectId);
    }
```

- [ ] **Step 4: Add fetchDFIMatches and handler functions**

After the existing `handleUpdateBuyerMatchStatus` function, add:

```typescript
const fetchDFIMatches = async (id: string) => {
    setLoadingDFIMatches(true);
    try {
        const data = await pipelineService.getDFIMatches(id);
        setDFIMatches(data);
    } catch (e) {
        console.error('Failed to load DFI matches', e);
    } finally {
        setLoadingDFIMatches(false);
    }
};

const handleTriggerDFIMatch = async () => {
    if (!projectId || triggeringDFIMatch) return;
    setTriggeringDFIMatch(true);
    try {
        await pipelineService.triggerDFIMatching(projectId);
        await fetchDFIMatches(projectId);
    } catch (e) {
        console.error('DFI matching failed', e);
    } finally {
        setTriggeringDFIMatch(false);
    }
};

const handleUpdateDFIMatchStatus = async (matchId: string, newStatus: DFIMatchStatus) => {
    try {
        await pipelineService.updateDFIMatchStatus(matchId, { status: newStatus });
        if (projectId) await fetchDFIMatches(projectId);
    } catch (e) {
        console.error('Failed to update DFI match status', e);
    }
};

const handleGenerateMemo = async () => {
    if (!projectId || generatingMemo) return;
    setGeneratingMemo(true);
    try {
        const memo = await pipelineService.getFinancingMemo(projectId);
        setFinancingMemo(memo);
        setShowMemoModal(true);
    } catch (e) {
        console.error('Failed to generate financing memo', e);
    } finally {
        setGeneratingMemo(false);
    }
};
```

- [ ] **Step 5: Update matches tab badge**

Find the line that computes the badge count for the matches tab (currently `matches.length + buyerMatches.length`) and change to:

```typescript
matches.length + buyerMatches.length + dfiMatches.length
```

- [ ] **Step 6: Add the DFI sub-tab button to the sub-tab switcher**

Find the array of sub-tab items (around line 673) and add a third entry:

```tsx
{ key: 'dfi' as const, label: 'DFI Windows', count: dfiMatches.length },
```

So it becomes:
```tsx
{([
  { key: 'investor' as const, label: 'Investor matches', count: matches.length },
  { key: 'buyer' as const, label: 'Buyer / Offtake', count: buyerMatches.length },
  { key: 'dfi' as const, label: 'DFI Windows', count: dfiMatches.length },
]).map(({ key, label, count }) => { ... })}
```

- [ ] **Step 7: Add DFI sub-tab content panel**

After the `{matchSubTab === 'buyer' && (…)}` block, add:

```tsx
{matchSubTab === 'dfi' && (
  <>
    <div style={sectionHeadStyle}>
      <h2 style={sectionTitleStyle}>DFI / Blended Finance Windows</h2>
      <div style={{ display: 'flex', gap: 8 }}>
        <button onClick={handleGenerateMemo} disabled={generatingMemo} style={{
          display: 'inline-flex', alignItems: 'center', gap: 6,
          background: 'none', border: '1px solid var(--border)', color: 'var(--ink-700)',
          padding: '7px 14px', fontSize: 12, fontWeight: 500,
          cursor: generatingMemo ? 'default' : 'pointer', fontFamily: 'inherit',
          opacity: generatingMemo ? 0.7 : 1,
        }}>
          <span className="material-symbols-outlined" style={{ fontSize: 16 }}>description</span>
          {generatingMemo ? 'Generating…' : 'Financing memo'}
        </button>
        <button onClick={handleTriggerDFIMatch} disabled={triggeringDFIMatch} style={{
          display: 'inline-flex', alignItems: 'center', gap: 6,
          background: 'var(--accent)', border: 'none', color: 'var(--accent-ink)',
          padding: '7px 14px', fontSize: 12, fontWeight: 500,
          cursor: triggeringDFIMatch ? 'default' : 'pointer', fontFamily: 'inherit',
          opacity: triggeringDFIMatch ? 0.7 : 1,
        }}>
          <span className="material-symbols-outlined" style={{ fontSize: 16 }}>restart_alt</span>
          {triggeringDFIMatch ? 'Running…' : 'Run DFI matching'}
        </button>
      </div>
    </div>

    <div style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
      {loadingDFIMatches ? (
        <div style={{ padding: '32px 24px', textAlign: 'center', fontSize: 13, color: 'var(--ink-500)' }}>
          Loading DFI windows…
        </div>
      ) : dfiMatches.length === 0 ? (
        <div style={{ padding: '48px 24px', textAlign: 'center', fontSize: 13, color: 'var(--ink-400)' }}>
          No DFI windows matched yet. Run the matching engine to find suitable instruments.
        </div>
      ) : dfiMatches.map((match, i) => {
        const INSTRUMENT_COLOR: Record<string, string> = {
          GRANT: 'var(--sage)',
          CONCESSIONAL_LOAN: 'var(--navy)',
          BLENDED: 'var(--accent)',
          EQUITY: 'var(--terra)',
        };
        const instrColor = INSTRUMENT_COLOR[match.dfi_window.instrument_type] || 'var(--ink-500)';

        return (
          <div key={match.match_id} style={{
            padding: '16px 20px',
            borderBottom: i < dfiMatches.length - 1 ? '1px solid var(--border)' : 'none',
          }}>
            <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 16 }}>
              <div style={{ flex: 1 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                  <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--ink-900)' }}>
                    {match.dfi_window.name}
                  </span>
                  <span style={{
                    fontSize: 10, padding: '2px 6px', letterSpacing: '0.08em',
                    textTransform: 'uppercase', color: instrColor,
                    border: `1px solid ${instrColor}`,
                  }}>
                    {match.dfi_window.instrument_type.replace('_', ' ')}
                  </span>
                  {match.dfi_window.gender_focus && (
                    <span style={{ fontSize: 10, padding: '2px 6px', letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--sage)', border: '1px solid var(--sage)' }}>
                      Gender
                    </span>
                  )}
                  {match.dfi_window.climate_focus && (
                    <span style={{ fontSize: 10, padding: '2px 6px', letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--navy)', border: '1px solid var(--navy)' }}>
                      Climate
                    </span>
                  )}
                </div>
                <div style={{ fontSize: 12, color: 'var(--ink-500)', marginBottom: 4 }}>
                  {match.dfi_window.institution}
                </div>
                {match.fit_rationale && (
                  <div style={{ fontSize: 11, color: 'var(--ink-400)', lineHeight: 1.5 }}>
                    {match.fit_rationale}
                  </div>
                )}
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexShrink: 0 }}>
                <div style={{ textAlign: 'right' }}>
                  <div style={{
                    fontSize: 20, fontWeight: 700, fontFamily: "'Geist Mono', monospace",
                    color: match.fit_score >= 70 ? 'var(--sage)' : match.fit_score >= 50 ? 'var(--accent)' : 'var(--ink-500)',
                  }}>
                    {match.fit_score}
                  </div>
                  <div style={{ fontSize: 10, color: 'var(--ink-400)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>fit score</div>
                </div>
                <select
                  value={match.status}
                  onChange={(e) => handleUpdateDFIMatchStatus(match.match_id, e.target.value as DFIMatchStatus)}
                  style={{
                    fontSize: 11, padding: '4px 8px',
                    background: 'var(--surface)', border: '1px solid var(--border)',
                    color: 'var(--ink-700)', fontFamily: 'inherit', cursor: 'pointer',
                  }}
                >
                  {Object.values(DFIMatchStatus).map(s => (
                    <option key={s} value={s}>{s.replace('_', ' ')}</option>
                  ))}
                </select>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  </>
)}
```

- [ ] **Step 8: Add financing memo modal**

Inside the return block, after the main content area but before the final closing `</div>`, add:

```tsx
{/* Financing Memo Modal */}
{showMemoModal && financingMemo && (
  <div style={{
    position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)',
    display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 50,
  }}>
    <div style={{
      background: 'var(--surface)', border: '1px solid var(--border)',
      width: '100%', maxWidth: 640, margin: 16, maxHeight: '90vh', overflowY: 'auto',
    }}>
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '20px 24px', borderBottom: '1px solid var(--border)', position: 'sticky', top: 0, background: 'var(--surface)',
      }}>
        <div>
          <div style={{ fontSize: 10, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--ink-400)', marginBottom: 4 }}>
            Blended Finance Memo
          </div>
          <h3 style={{ fontSize: 16, fontWeight: 600, color: 'var(--ink-900)', margin: 0 }}>
            {financingMemo.project_name}
          </h3>
        </div>
        <button onClick={() => setShowMemoModal(false)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--ink-400)' }}>
          <span className="material-symbols-outlined">close</span>
        </button>
      </div>

      <div style={{ padding: '20px 24px' }}>
        {/* Capital Stack */}
        <div style={{ marginBottom: 20 }}>
          <div style={{ fontSize: 11, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--ink-500)', marginBottom: 8 }}>Recommended Capital Structure</div>
          <div style={{ fontSize: 13, color: 'var(--ink-800)', marginBottom: 12 }}>{financingMemo.recommended_structure}</div>
          <div style={{ display: 'flex', gap: 0, height: 8, borderRadius: 2, overflow: 'hidden' }}>
            <div style={{ flex: financingMemo.grant_component_pct, background: 'var(--sage)' }} title={`Grant: ${financingMemo.grant_component_pct}%`} />
            <div style={{ flex: financingMemo.concessional_component_pct, background: 'var(--navy)' }} title={`Concessional: ${financingMemo.concessional_component_pct}%`} />
            <div style={{ flex: financingMemo.commercial_component_pct, background: 'var(--accent)' }} title={`Commercial: ${financingMemo.commercial_component_pct}%`} />
          </div>
          <div style={{ display: 'flex', gap: 16, marginTop: 6 }}>
            {[
              { label: 'Grant', pct: financingMemo.grant_component_pct, color: 'var(--sage)' },
              { label: 'Concessional', pct: financingMemo.concessional_component_pct, color: 'var(--navy)' },
              { label: 'Commercial', pct: financingMemo.commercial_component_pct, color: 'var(--accent)' },
            ].map(({ label, pct, color }) => (
              <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                <div style={{ width: 8, height: 8, borderRadius: '50%', background: color }} />
                <span style={{ fontSize: 11, color: 'var(--ink-500)' }}>{label}: {pct}%</span>
              </div>
            ))}
          </div>
        </div>

        {/* Priority Windows */}
        <div style={{ marginBottom: 16 }}>
          <div style={{ fontSize: 11, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--ink-500)', marginBottom: 8 }}>Priority DFI Windows</div>
          {financingMemo.priority_windows.map((w, i) => (
            <div key={i} style={{ fontSize: 12, color: 'var(--ink-700)', padding: '4px 0', borderBottom: '1px solid var(--border)' }}>
              {i + 1}. {w}
            </div>
          ))}
        </div>

        {/* Risks */}
        <div style={{ marginBottom: 16 }}>
          <div style={{ fontSize: 11, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--ink-500)', marginBottom: 8 }}>Key Risks</div>
          {financingMemo.key_risks.map((r, i) => (
            <div key={i} style={{ fontSize: 12, color: 'var(--ink-600)', padding: '3px 0' }}>• {r}</div>
          ))}
        </div>

        {/* Next Steps */}
        <div style={{ marginBottom: 16 }}>
          <div style={{ fontSize: 11, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--ink-500)', marginBottom: 8 }}>Next Steps</div>
          {financingMemo.next_steps.map((s, i) => (
            <div key={i} style={{ fontSize: 12, color: 'var(--ink-700)', padding: '3px 0' }}>
              <span style={{ fontFamily: "'Geist Mono', monospace", fontSize: 10, color: 'var(--accent)', marginRight: 6 }}>{String(i+1).padStart(2,'0')}</span>
              {s}
            </div>
          ))}
        </div>

        {/* Full memo narrative */}
        <div>
          <div style={{ fontSize: 11, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--ink-500)', marginBottom: 8 }}>Financing Rationale</div>
          <div style={{ fontSize: 12, color: 'var(--ink-700)', lineHeight: 1.7 }}>{financingMemo.full_memo}</div>
        </div>
      </div>
    </div>
  </div>
)}
```

- [ ] **Step 9: TypeScript compile check**

```bash
cd /home/evan/Desktop/martin\ os\ v2/martin-system/frontend
npm run build 2>&1 | tail -10
```

Expected: exit 0, no type errors.

- [ ] **Step 10: Commit**

```bash
git add frontend/src/pages/ProjectDetails.tsx
git commit -m "feat(r7): DFI sub-tab in ProjectDetails — match cards, status dropdown, financing memo modal"
```

---

## Task 8: Smoke Test

- [ ] **Step 1: Confirm migration has been run and 15 windows exist**

```bash
cd /home/evan/Desktop/martin\ os\ v2/martin-system/backend
venv/bin/alembic current
```

Expected: `r7_dfi_w1nd0ws (head)`

```bash
TOKEN=$(curl -s -X POST http://localhost:8001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"magwaro@ecowasiisummit.net","password":"Admin@2026"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8001/api/pipeline/dfi-windows \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'{len(d)} windows'); [print(f'  {w[\"institution\"]} — {w[\"name\"]}') for w in d]"
```

Expected: 15 windows listed.

- [ ] **Step 2: Trigger DFI matching on a real project**

```bash
# Get first project ID
PROJECT_ID=$(curl -s -H "Authorization: Bearer $TOKEN" \
  http://localhost:8001/api/pipeline/ | python3 -c "import sys,json; d=json.load(sys.stdin); print(d[0]['id']) if d else print('no projects')")

curl -s -X POST -H "Authorization: Bearer $TOKEN" \
  http://localhost:8001/api/pipeline/$PROJECT_ID/dfi-match \
  | python3 -m json.tool
```

Expected: JSON with `new_matches`, `updated_matches`, `windows_scanned: 15`.

- [ ] **Step 3: Retrieve matches**

```bash
curl -s -H "Authorization: Bearer $TOKEN" \
  http://localhost:8001/api/pipeline/$PROJECT_ID/dfi-matches \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'{len(d)} matches'); [print(f'  {m[\"dfi_window\"][\"institution\"]} — score {m[\"fit_score\"]}') for m in d[:5]]"
```

Expected: 1-15 matches listed with scores.

- [ ] **Step 4: Generate financing memo**

```bash
curl -s -X POST -H "Authorization: Bearer $TOKEN" \
  http://localhost:8001/api/pipeline/$PROJECT_ID/financing-memo \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('recommended_structure','NO MEMO'))"
```

Expected: A sentence describing the recommended capital structure.

- [ ] **Step 5: Open the UI and verify**

1. Start the frontend dev server: `cd frontend && npm run dev`
2. Log in at `http://localhost:5173`
3. Navigate to any project in the deal pipeline
4. Click the "Matches" tab
5. Verify three sub-tabs appear: "Investor matches", "Buyer / Offtake", "DFI Windows"
6. Click "DFI Windows"
7. Verify match cards show up (or empty-state if not yet run)
8. Click "Run DFI matching" and confirm the cards populate
9. Click "Financing memo" and confirm the modal opens with capital stack, priority windows, risks, next steps

- [ ] **Step 6: Final commit**

```bash
git add -A
git commit -m "feat(r7): smoke test passed — blended finance structuring module complete"
```

---

## Self-Review

**Spec coverage:**
- [x] DFI window database with 15 seeded instruments — Task 1
- [x] Instrument types (GRANT, CONCESSIONAL_LOAN, EQUITY, BLENDED) — Task 1 + Task 2
- [x] Rule-based scoring (sector +35, geography +25, size +20, stage +10, gender/climate +5/5) — Task 4
- [x] Upsert match records, threshold ≥40 — Task 4
- [x] LLM financing memo with capital stack percentages — Task 4
- [x] API endpoints: list windows, trigger match, get matches, update status, generate memo — Task 5
- [x] Frontend DFI sub-tab with match cards + status dropdowns — Task 7
- [x] Financing memo modal with stacked bar chart, priority windows, risks, next steps — Task 7
- [x] Fallback memo if LLM unavailable — Task 4 (graceful degradation in `generate_financing_memo`)

**Type consistency check:**
- `DFIMatch.dfi_window` (frontend) → backend returns `DFIMatchRead.dfi_window: DFIWindowRead` ✓
- `DFIMatch.fit_score` matches `DFIMatchRead.fit_score` ✓
- `DFIMatchStatus` enum values match between model, schema, and frontend ✓
- `FinancingMemoResponse` / `FinancingMemo` field names align ✓
- `get_dfi_matching_service` imported in routes ✓

**Placeholder scan:** No TBD, no "add appropriate error handling", no "similar to Task N" — all code blocks are complete.
