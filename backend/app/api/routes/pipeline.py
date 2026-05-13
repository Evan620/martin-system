"""
Deal Pipeline API Routes
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Path as PathParam, UploadFile, File, Form
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone
UTC = timezone.utc
import uuid
import io
import re

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.models import User, Project, ProjectStatus
from app.services.project_pipeline_service import ProjectPipelineService
from app.services.investor_matching_service import get_investor_matching_service
from app.schemas.pipeline_schemas import (
    ProjectIngest, ProjectUpdate, ProjectPipelineRead, ProjectAdvanceStage, 
    InvestorMatchRead, PipelineStats, InvestorMatchUpdate, InvestorRead,
    ProjectScoreDetailRead, ScoringCriteriaRead
)
from app.models.models import ProjectScoreDetail, ScoringCriteria
from app.services.lifecycle_service import LifecycleService
from app.services.project_insights_service import insights_service

router = APIRouter(prefix="/pipeline", tags=["deal-pipeline"])


def _project_to_read(p: "Project", current_user: "User") -> ProjectPipelineRead:
    """Convert a Project ORM object to ProjectPipelineRead schema."""
    return ProjectPipelineRead(
        id=p.id,
        name=p.name,
        description=p.description,
        status=p.status,
        investment_size=p.investment_size,
        currency=p.currency,
        readiness_score=p.readiness_score,
        afcen_score=p.afcen_score,
        strategic_alignment_score=p.strategic_alignment_score,
        lead_country=p.lead_country,
        pillar=p.pillar,
        assigned_agent=p.assigned_agent,
        updated_at=getattr(p, 'created_at', datetime.now(UTC)),
        is_flagship=p.is_flagship,
        funding_secured_usd=p.funding_secured_usd or 0,
        deal_room_priority=p.deal_room_priority,
        # Section A
        subsector=p.subsector,
        project_sponsor=p.project_sponsor,
        is_cross_border=p.is_cross_border or False,
        key_contact_name=p.key_contact_name,
        key_contact_email=p.key_contact_email,
        # Section B
        technical_studies=p.technical_studies,
        permits_licences=p.permits_licences,
        land_status=p.land_status,
        # Section C
        financing_structure=p.financing_structure,
        investment_stage_label=p.investment_stage_label,
        revenue_model=p.revenue_model,
        macroeconomic_roi=p.macroeconomic_roi,
        # Section D
        climate_impact=p.climate_impact,
        esg_compliance=p.esg_compliance,
        ghg_avoided_target=p.ghg_avoided_target,
        jobs_construction=p.jobs_construction,
        jobs_om=p.jobs_om,
        electricity_connections=p.electricity_connections,
        digital_connections=p.digital_connections,
        smallholder_farmers_reached=p.smallholder_farmers_reached,
        submitted_by=p.submitted_by,
        allowed_transitions=LifecycleService.get_allowed_transitions(p.status, current_user.role),
    )


@router.get("/", response_model=List[ProjectPipelineRead])
async def list_pipeline_projects(
    stage: Optional[ProjectStatus] = None,
    pillar: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List projects in the deal pipeline with optional filtering.
    """
    query = select(Project)
    
    if stage:
        query = query.where(Project.status == stage)
    if pillar:
        # Case-insensitive pillar filter
        query = query.where(Project.pillar.ilike(f"%{pillar}%"))
        
    result = await db.execute(query)
    projects = result.scalars().all()
    
    return [_project_to_read(p, current_user) for p in projects]

@router.post("/ingest", response_model=ProjectPipelineRead)
async def ingest_project(
    data: ProjectIngest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Ingest a new project proposal and calculate initial scores.
    """
    service = ProjectPipelineService(db)
    
    result = await service.ingest_project_proposal(
        data=data.model_dump(),
        submitted_by_user_id=current_user.id
    )
    
    p = result["project"]
    return _project_to_read(p, current_user)

@router.get("/{project_id}", response_model=ProjectPipelineRead)
async def get_project_details(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get detailed project view.
    """
    result = await db.execute(select(Project).where(Project.id == project_id))
    p = result.scalars().first()

    if not p:
        raise HTTPException(status_code=404, detail="Project not found")

    return _project_to_read(p, current_user)

@router.patch("/{project_id}", response_model=ProjectPipelineRead)
async def update_project(
    project_id: uuid.UUID,
    payload: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update project details.
    """
    service = ProjectPipelineService(db)
    result = await service.update_project(
        project_id=project_id,
        data=payload.model_dump(exclude_unset=True),
        updated_by_user_id=current_user.id
    )

    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    p = result["project"]
    return _project_to_read(p, current_user)

@router.post("/{project_id}/advance", response_model=ProjectPipelineRead)
async def advance_project_stage(
    project_id: uuid.UUID,
    payload: ProjectAdvanceStage,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Advance a project to the next stage.
    """
    service = ProjectPipelineService(db)
    
    result = await service.advance_project_stage(
        project_id=project_id,
        new_stage=payload.new_stage,
        advanced_by_user_id=current_user.id,
        notes=payload.notes
    )
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
        
    p = result["project"]
    return _project_to_read(p, current_user)

@router.get("/{project_id}/matches", response_model=List[InvestorMatchRead])
async def get_project_matches(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get investor matches for a project.
    """
    service = get_investor_matching_service(db)
    matches = await service.get_matches_for_project(project_id)
    
    return [
        InvestorMatchRead(
            match_id=m["match_id"],
            investor=InvestorRead(
                id=m["investor"].id,
                name=m["investor"].name,
                sector_preferences=m["investor"].sector_preferences,
                ticket_size_min=m["investor"].ticket_size_min,
                ticket_size_max=m["investor"].ticket_size_max,
                geographic_focus=m["investor"].geographic_focus,
                investment_instruments=m["investor"].investment_instruments
            ),
            score=m["score"],
            status=m["status"],
            notes=m["notes"]
        ) for m in matches
    ]

@router.patch("/matches/{match_id}", response_model=dict)
async def update_match_status(
    match_id: uuid.UUID,
    payload: InvestorMatchUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update match status (e.g. to INTERESTED to trigger Protocol Agent).
    """
    service = get_investor_matching_service(db)
    result = await service.update_match_status(
        match_id=match_id,
        new_status=payload.status,
        notes=payload.notes,
        updated_by_user_id=current_user.id
    )
    
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
        
    return result

@router.post("/{project_id}/match", response_model=dict)
async def trigger_investor_matching(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Manually trigger investor matching for a project.
    """
    service = get_investor_matching_service(db)
    result = await service.match_investors(project_id)
    return result

@router.get("/dashboard/stats", response_model=PipelineStats)
async def get_pipeline_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get high-level pipeline statistics.
    """
    service = ProjectPipelineService(db)
    stats = await service.check_pipeline_health()
    return PipelineStats(**stats)

@router.get("/{project_id}/score-details", response_model=List[ProjectScoreDetailRead])
async def get_project_score_details(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get detailed breakdown of project scores.
    """
    # Join with Criteria
    stmt = (
        select(ProjectScoreDetail, ScoringCriteria)
        .join(ScoringCriteria, ProjectScoreDetail.criterion_id == ScoringCriteria.id)
        .where(ProjectScoreDetail.project_id == project_id)
    )
    result = await db.execute(stmt)
    rows = result.all()
    
    return [
        ProjectScoreDetailRead(
            id=d.id,
            criterion=ScoringCriteriaRead(
                id=c.id,
                criterion_name=c.criterion_name,
                criterion_type=c.criterion_type,
                weight=c.weight,
                description=c.description
            ),
            score=float(d.score),
            notes=d.notes,
            scored_date=d.scored_date
        )
        for d, c in rows
    ]



@router.get("/{project_id}/insights")
async def get_project_insights(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get AI-powered insights and recommendations for a project.
    Uses LLM to analyze project status, scores, and generate actionable next steps.
    """
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    insights = await insights_service.generate_project_insights(project, db)
    
    return {
        "project_id": str(project_id),
        "insight": insights["insight"],
        "recommendation": insights["recommendation"],
        "generated_at": datetime.now(UTC).isoformat()
    }


@router.get("/{project_id}/history")
async def get_project_history(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get project status change history timeline.
    Returns chronological list of all status changes.
    """
    from app.models.models import ProjectStatusHistory, User as UserModel
    
    # Verify project exists
    project_result = await db.execute(select(Project).where(Project.id == project_id))
    project = project_result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Fetch status history with user info
    stmt = (
        select(ProjectStatusHistory, UserModel)
        .outerjoin(UserModel, ProjectStatusHistory.changed_by_id == UserModel.id)
        .where(ProjectStatusHistory.project_id == project_id)
        .order_by(ProjectStatusHistory.change_date.desc())
    )
    
    result = await db.execute(stmt)
    history_records = result.all()
    
    # Format response
    history = []
    for record, user in history_records:
        history.append({
            "id": str(record.id),
            "previous_status": record.previous_status.value if record.previous_status else None,
            "new_status": record.new_status.value,
            "change_date": record.change_date.isoformat(),
            "changed_by": {
                "id": str(user.id) if user else None,
                "name": user.full_name if user else "System",
                "email": user.email if user else None
            } if user else {"name": "System"},
            "notes": record.notes
        })
    
    return {
        "project_id": str(project_id),
        "history": history,
        "total_changes": len(history)
    }


@router.post("/{project_id}/feature")
async def toggle_project_flagship(
    project_id: uuid.UUID,
    is_flagship: bool = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Toggle the 'is_flagship' status of a project.
    """
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalars().first()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    project.is_flagship = is_flagship
    await db.commit()
    
    return {"status": "success", "is_flagship": is_flagship}


@router.post("/{project_id}/rescore")
async def rescore_project(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Manually trigger AfCEN scoring assessment for a project.
    Useful when automatic Celery scoring is unavailable.
    """
    # Verify project exists
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Run scoring synchronously
    service = ProjectPipelineService(db)
    try:
        score = await service.assess_project_readiness(project_id)

        return {
            "status": "success",
            "project_id": str(project_id),
            "afcen_score": float(score),
            "message": f"Project rescored successfully. New AfCEN score: {score:.2f}"
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Scoring failed: {str(e)}"
        )


# ---------------------------------------------------------------------------
# Excel Import helpers
# ---------------------------------------------------------------------------

from app.models.models import TWGPillar


_PILLAR_KEYWORDS: dict[str, TWGPillar] = {
    "energy": TWGPillar.energy_infrastructure,
    "agriculture": TWGPillar.agriculture_food_systems,
    "agribusiness": TWGPillar.agriculture_food_systems,
    "food": TWGPillar.agriculture_food_systems,
    "mineral": TWGPillar.critical_minerals_industrialization,
    "industrial": TWGPillar.critical_minerals_industrialization,
    "digital": TWGPillar.digital_economy_transformation,
    "protocol": TWGPillar.protocol_logistics,
    "logistics": TWGPillar.protocol_logistics,
    "resource": TWGPillar.resource_mobilization,
    "mobilization": TWGPillar.resource_mobilization,
}

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


def _match_pillar(raw: str) -> TWGPillar:
    """Map a free-text sector string to the nearest TWGPillar enum value."""
    lowered = raw.strip().lower()
    for keyword, pillar in _PILLAR_KEYWORDS.items():
        if keyword in lowered:
            return pillar
    return TWGPillar.digital_economy_transformation


def _map_status(raw: str) -> ProjectStatus:
    """Map a stage string to ProjectStatus; defaults to CONCEPT."""
    lowered = raw.strip().lower()
    for key, status in _STAGE_MAP.items():
        if key in lowered:
            return status
    return ProjectStatus.CONCEPT


def _parse_investment(raw: str) -> Optional[float]:
    """Parse investment value from strings like '$50M', '50–100 million', 'USD 100-150 million'."""
    if not raw:
        return None
    cleaned = str(raw).replace("$", "").replace(",", "").replace("USD", "").strip().lower()
    multiplier = 1_000_000 if any(x in cleaned for x in ("m", "million")) else 1
    # Handle ranges like "100–150" or "50-100" — take the lower bound
    range_match = re.search(r"(\d+(?:\.\d+)?)\s*[–\-]\s*(\d+(?:\.\d+)?)", cleaned)
    if range_match:
        low, high = float(range_match.group(1)), float(range_match.group(2))
        return ((low + high) / 2) * multiplier
    cleaned = re.sub(r"[^0-9.]", "", cleaned)
    try:
        return float(cleaned) * multiplier if cleaned else None
    except (ValueError, TypeError):
        return None


def _col_matches(header: str, *patterns: str) -> bool:
    """Case-insensitive partial match of a header against any of the patterns."""
    lowered = header.strip().lower()
    return any(p in lowered for p in patterns)


def _find_header_row(ws):
    """
    Scan rows until one contains a cell with 'project name' or 'project/programme name'.
    Returns (row_index_1based, col_map) where col_map maps field names to 0-based col indices.
    Returns (None, None) if not found.
    """
    for row_idx, row in enumerate(ws.iter_rows(values_only=True), start=1):
        cells = [str(c).strip() if c is not None else "" for c in row]
        header_cells_lower = [c.lower() for c in cells]
        is_header = any(
            "project name" in cell or "project/programme name" in cell or "project title" in cell
            for cell in header_cells_lower
        )
        if not is_header:
            continue
        col_map: dict[str, int] = {}
        for col_idx, header in enumerate(header_cells_lower):
            if not header:
                continue
            if _col_matches(header, "project name", "project/programme name", "project title"):
                col_map.setdefault("name", col_idx)
            elif _col_matches(header, "country") and "lead country" not in header:
                col_map.setdefault("lead_country", col_idx)
            elif _col_matches(header, "cross-border", "national or cross-border", "cross border", "regional dimension"):
                col_map.setdefault("is_cross_border", col_idx)
            elif _col_matches(header, "sector") and "subsector" not in header:
                col_map.setdefault("pillar", col_idx)
            elif _col_matches(header, "subsector"):
                col_map.setdefault("subsector", col_idx)
            elif _col_matches(header, "project sponsor", "sponsor"):
                col_map.setdefault("project_sponsor", col_idx)
            elif _col_matches(header, "name of key contact", "key contact"):
                col_map.setdefault("key_contact_name", col_idx)
            elif _col_matches(header, "email of key contact", "email of key", "contact email"):
                col_map.setdefault("key_contact_email", col_idx)
            elif _col_matches(header, "stage of development"):
                col_map.setdefault("status", col_idx)
            elif _col_matches(header, "technical studies", "completed studies"):
                col_map.setdefault("technical_studies", col_idx)
            elif _col_matches(header, "permits", "licences", "licenses"):
                col_map.setdefault("permits_licences", col_idx)
            elif _col_matches(header, "land status", "land_status"):
                col_map.setdefault("land_status", col_idx)
            elif _col_matches(header, "investment size", "estimated investment", "capital required"):
                col_map.setdefault("investment_size", col_idx)
            elif _col_matches(header, "financing structure"):
                col_map.setdefault("financing_structure", col_idx)
            elif _col_matches(header, "investment stage"):
                col_map.setdefault("investment_stage_label", col_idx)
            elif _col_matches(header, "revenue model", "revenue_model"):
                col_map.setdefault("revenue_model", col_idx)
            elif _col_matches(header, "macroeconomic roi", "macro", "economic roi"):
                col_map.setdefault("macroeconomic_roi", col_idx)
            elif _col_matches(header, "climate", "esg"):
                col_map.setdefault("climate_impact", col_idx)
            elif _col_matches(header, "ghg", "tco2", "emissions"):
                col_map.setdefault("ghg_avoided_target", col_idx)
            elif _col_matches(header, "jobs", "construction") and "o&m" not in header and "ongoing" not in header:
                col_map.setdefault("jobs_construction", col_idx)
            elif _col_matches(header, "jobs", "o&m") or _col_matches(header, "jobs", "ongoing"):
                col_map.setdefault("jobs_om", col_idx)
            elif _col_matches(header, "electricity connect"):
                col_map.setdefault("electricity_connections", col_idx)
            elif _col_matches(header, "digital connect", "smes digitized"):
                col_map.setdefault("digital_connections", col_idx)
            elif _col_matches(header, "smallholder", "farmers reached"):
                col_map.setdefault("smallholder_farmers_reached", col_idx)
            elif _col_matches(header, "submitted by"):
                col_map.setdefault("submitted_by", col_idx)
        return row_idx, col_map
    return None, None


def _cell(row: tuple, col_map: dict, field: str) -> str:
    """Safely get a cell value as a stripped string, or empty string."""
    idx = col_map.get(field)
    if idx is None or idx >= len(row):
        return ""
    val = row[idx]
    return str(val).strip() if val is not None else ""


@router.post("/import-excel")
async def import_projects_from_excel(
    file: UploadFile = File(...),
    twg_id: str = Form(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Bulk-import projects from an .xlsx file.
    Skips instruction rows before the header; maps columns by partial header name.
    Returns counts of imported, skipped, and per-row errors.
    """
    import openpyxl

    if not file.filename or not file.filename.lower().endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="Only .xlsx files are supported.")

    try:
        parsed_twg_id = uuid.UUID(twg_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="twg_id must be a valid UUID.")

    raw_bytes = await file.read()
    try:
        wb = openpyxl.load_workbook(io.BytesIO(raw_bytes), data_only=True)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Cannot parse Excel file: {exc}")

    # Try "Investment Opportunities" tab first, then fall back to scanning all sheets
    target_sheet_names = ["Investment Opportunities", "Projects", "Pipeline"]
    ws = None
    for sheet_name in target_sheet_names:
        if sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
            break
    if ws is None:
        ws = wb.active

    header_row_idx, col_map = _find_header_row(ws)

    # If not found in preferred sheet, scan all sheets
    if header_row_idx is None:
        for sheet_name in wb.sheetnames:
            candidate = wb[sheet_name]
            header_row_idx, col_map = _find_header_row(candidate)
            if header_row_idx is not None:
                ws = candidate
                break

    if header_row_idx is None:
        raise HTTPException(
            status_code=422,
            detail="Could not find a header row containing 'Project Name' or 'Project Title'.",
        )

    imported = 0
    skipped = 0
    errors: list[str] = []

    rows = list(ws.iter_rows(values_only=True))
    data_rows = rows[header_row_idx:]  # slice past the header row (0-based)

    for row_offset, row in enumerate(data_rows, start=header_row_idx + 2):
        name = _cell(row, col_map, "name")
        if not name:
            skipped += 1
            continue
        # Skip template description/example rows and footer instructions
        name_lower = name.lower()
        if any(x in name_lower for x in ("full name of the project", "add further rows", "↓", "copy formatting")):
            skipped += 1
            continue

        try:
            raw_pillar = _cell(row, col_map, "pillar")
            pillar = _match_pillar(raw_pillar).value if raw_pillar else TWGPillar.digital_economy_transformation.value

            raw_status = _cell(row, col_map, "status")
            status = _map_status(raw_status) if raw_status else ProjectStatus.CONCEPT

            raw_investment = _cell(row, col_map, "investment_size")
            investment_size = _parse_investment(raw_investment) if raw_investment else 0.0

            raw_cross = _cell(row, col_map, "is_cross_border").lower()
            is_cross_border = "cross" in raw_cross

            def _get(field: str) -> Optional[str]:
                v = _cell(row, col_map, field)
                return v if v and v.upper() not in ("TBC", "N/A", "NA", "NONE", "-") else None

            project = Project(
                id=uuid.uuid4(),
                twg_id=parsed_twg_id,
                name=name,
                description="",
                investment_size=investment_size or 0,
                currency="USD",
                status=status,
                pillar=pillar,
                # Section A
                lead_country=_cell(row, col_map, "lead_country") or None,
                subsector=_get("subsector"),
                project_sponsor=_get("project_sponsor"),
                is_cross_border=is_cross_border,
                key_contact_name=_get("key_contact_name"),
                key_contact_email=_get("key_contact_email"),
                # Section B
                technical_studies=_get("technical_studies"),
                permits_licences=_get("permits_licences"),
                land_status=_get("land_status"),
                # Section C
                financing_structure=_get("financing_structure"),
                investment_stage_label=_get("investment_stage_label"),
                revenue_model=_get("revenue_model"),
                macroeconomic_roi=_get("macroeconomic_roi"),
                # Section D
                climate_impact=_get("climate_impact"),
                esg_compliance=None,
                ghg_avoided_target=_get("ghg_avoided_target"),
                jobs_construction=_get("jobs_construction"),
                jobs_om=_get("jobs_om"),
                electricity_connections=_get("electricity_connections"),
                digital_connections=_get("digital_connections"),
                smallholder_farmers_reached=_get("smallholder_farmers_reached"),
                # Metadata
                submitted_by=_get("submitted_by"),
            )
            db.add(project)
            imported += 1
        except Exception as exc:
            errors.append(f"Row {row_offset}: {exc}")
            skipped += 1

    try:
        await db.commit()
    except Exception as exc:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Database commit failed: {exc}")

    return {"imported": imported, "skipped": skipped, "errors": errors}

