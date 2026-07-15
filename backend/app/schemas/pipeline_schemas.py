"""
Pipeline Schemas

Pydantic models for the Deal Pipeline API.
"""
from pydantic import BaseModel, ConfigDict, Field, condecimal, field_validator
from typing import Optional, List, Any, Dict
from datetime import datetime
from uuid import UUID
from decimal import Decimal

from app.models.models import ProjectStatus, InvestorMatchStatus

# R1 — Controlled vocabulary for value chain stages. Union of the original 5
# stages already in use + the 3 added per Carren Mwanzia's May 2026 benchmark
# analysis. Investors filter by these segments, so the set must be stable.
VALID_VALUE_CHAIN_STAGES = {
    "INPUTS",              # Inputs & Seeds
    "PRODUCTION",          # Primary Production
    "PROCESSING",          # Post-Harvest & Processing
    "LOGISTICS",           # Logistics & Cold Chain
    "RETAIL",              # Retail / Markets
    "DIGITAL_PLATFORM",    # Digital Agri-Platform
    "FINANCIAL_SERVICES",  # Financial Services for Agriculture
    "POLICY_ENABLING",     # Policy & Enabling Environment
}


def _validate_value_chain_stages(stages: Optional[List[str]]) -> Optional[List[str]]:
    """Reject entries outside the controlled vocabulary. None passes through."""
    if stages is None:
        return None
    invalid = [s for s in stages if s not in VALID_VALUE_CHAIN_STAGES]
    if invalid:
        valid_list = ", ".join(sorted(VALID_VALUE_CHAIN_STAGES))
        raise ValueError(
            f"value_chain_stages contains entries not in the controlled vocabulary: {invalid}. "
            f"Valid stages: {valid_list}"
        )
    return stages


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
    status: Optional[str] = None # Optional override, otherwise defaults to DRAFT
    start_in_incubation: bool = True

    # R1 — Value chain classification. Required at intake: every new project must
    # declare at least one stage so investors can filter by mandate.
    # Optional at intake — only agribusiness projects supply value-chain stages.
    # Other sectors persist their bespoke fields in sector_details instead.
    value_chain_stages: Optional[List[str]] = Field(
        default=None,
        description="Agribusiness stages from the controlled vocabulary (optional)",
    )
    # Sector-specific bespoke fields (energy / minerals / digital). Stored verbatim.
    sector_details: Optional[Dict[str, Any]] = None
    # R2 — Gender / youth signals (binary + justification). Optional on intake
    # because some early projects may not have decided yet; lifecycle stage gate
    # enforces them at UNDER_REVIEW → SUMMIT_READY.
    is_cross_border: Optional[bool] = None
    gender_intentional: Optional[bool] = None
    gender_justification: Optional[str] = None
    youth_focused: Optional[bool] = None
    youth_justification: Optional[str] = None

    # R8 — Site coordinates for geospatial analysis (from SiteLocationPicker on intake)
    site_lat: Optional[float] = None
    site_lon: Optional[float] = None
    site_location_name: Optional[str] = None

    # Optional funding structure note (prompt the submitter; never required) —
    # surfaces the existing projects.financing_structure column on intake.
    financing_structure: Optional[str] = None

    @field_validator("value_chain_stages")
    @classmethod
    def _check_value_chain_stages(cls, v):
        return _validate_value_chain_stages(v)

class ProjectUpdate(BaseModel):
    """Schema for updating a project"""
    name: Optional[str] = None
    description: Optional[str] = None
    investment_size: Optional[Decimal] = None
    currency: Optional[str] = None
    pillar: Optional[str] = None
    lead_country: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None
    assigned_agent: Optional[str] = None
    is_flagship: Optional[bool] = None

    # Section A
    subsector: Optional[str] = None
    project_sponsor: Optional[str] = None
    is_cross_border: Optional[bool] = None
    key_contact_name: Optional[str] = None
    key_contact_email: Optional[str] = None
    submitted_by: Optional[str] = None

    # Section B
    technical_studies: Optional[str] = None
    permits_licences: Optional[str] = None
    land_status: Optional[str] = None

    # Section C
    financing_structure: Optional[str] = None
    investment_stage_label: Optional[str] = None
    revenue_model: Optional[str] = None
    macroeconomic_roi: Optional[str] = None

    # Section D
    climate_impact: Optional[str] = None
    esg_compliance: Optional[str] = None
    ghg_avoided_target: Optional[str] = None
    jobs_construction: Optional[str] = None
    jobs_om: Optional[str] = None
    electricity_connections: Optional[str] = None
    digital_connections: Optional[str] = None
    smallholder_farmers_reached: Optional[str] = None

    # Section A — Classification (Phase 1)
    value_chain_stages: Optional[List[str]] = None
    women_employment_pct: Optional[float] = None
    youth_employment_pct: Optional[float] = None
    sector_details: Optional[Dict[str, Any]] = None

    # R2 — Gender & Youth intentional design flags
    gender_intentional: Optional[bool] = None
    gender_justification: Optional[str] = None
    youth_focused: Optional[bool] = None
    youth_justification: Optional[str] = None

    # R8 — Site coordinates for geospatial analysis
    site_lat: Optional[float] = None
    site_lon: Optional[float] = None
    site_location_name: Optional[str] = None

    @field_validator("value_chain_stages")
    @classmethod
    def _check_value_chain_stages(cls, v):
        return _validate_value_chain_stages(v)


class ProjectAdvanceStage(BaseModel):
    """Schema for advancing a project stage"""
    new_stage: ProjectStatus
    notes: Optional[str] = None

class InvestorMatchUpdate(BaseModel):
    """Schema for updating investor match status"""
    status: InvestorMatchStatus
    notes: Optional[str] = None


class InvestorRead(BaseModel):
    """Schema for investor details"""
    id: UUID
    name: str
    sector_preferences: Optional[List[str]] = None
    ticket_size_min: Optional[Decimal] = None
    ticket_size_max: Optional[Decimal] = None
    geographic_focus: Optional[List[str]] = None
    investment_instruments: Optional[List[str]] = None
    investor_type: Optional[str] = None
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    total_commitments_usd: Optional[Decimal] = None

    model_config = ConfigDict(from_attributes=True)


class InvestorCreate(BaseModel):
    """Schema for registering an investor in the Deal Pipeline."""
    name: str
    sector_preferences: Optional[List[str]] = None
    ticket_size_min: Optional[Decimal] = None
    ticket_size_max: Optional[Decimal] = None
    geographic_focus: Optional[List[str]] = None
    investment_instruments: Optional[List[str]] = None
    investor_type: Optional[str] = None
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    total_commitments_usd: Optional[Decimal] = None

class InvestorMatchRead(BaseModel):
    """Schema for investor match details"""
    match_id: str
    investor: InvestorRead
    score: float
    status: str
    notes: Optional[str] = None

class ProjectPipelineRead(BaseModel):
    """Schema for detailed project view in pipeline"""
    id: UUID
    name: str
    description: str
    status: ProjectStatus  # Changed from 'stage' to 'status'
    investment_size: Decimal
    currency: str = "USD"
    
    # Scores — must be float so JSON serializes as numbers, not strings
    readiness_score: float = 0.0
    afcen_score: Optional[float] = None
    strategic_alignment_score: Optional[float] = None
    regional_impact_score: Optional[float] = None
    
    # Metadata
    pillar: Optional[str] = None
    lead_country: Optional[str] = None
    assigned_agent: Optional[str] = None
    updated_at: datetime
    
    # Computed
    days_in_stage: Optional[int] = None
    is_stalled: bool = False
    
    # Financials
    funding_secured_usd: Decimal = 0
    funding_gap_usd: Optional[Decimal] = None # Calculated
    
    # Deal Room
    is_flagship: bool = False
    deal_room_priority: Optional[int] = None

    # Investment Template — Section A
    subsector: Optional[str] = None
    project_sponsor: Optional[str] = None
    is_cross_border: bool = False
    key_contact_name: Optional[str] = None
    key_contact_email: Optional[str] = None

    # Investment Template — Section B
    technical_studies: Optional[str] = None
    permits_licences: Optional[str] = None
    land_status: Optional[str] = None

    # Investment Template — Section C
    financing_structure: Optional[str] = None
    investment_stage_label: Optional[str] = None
    revenue_model: Optional[str] = None
    macroeconomic_roi: Optional[str] = None

    # Investment Template — Section D
    climate_impact: Optional[str] = None
    esg_compliance: Optional[str] = None
    ghg_avoided_target: Optional[str] = None
    jobs_construction: Optional[str] = None
    jobs_om: Optional[str] = None
    electricity_connections: Optional[str] = None
    digital_connections: Optional[str] = None
    smallholder_farmers_reached: Optional[str] = None

    # Submission metadata
    submitted_by: Optional[str] = None

    # Phase 1 — Classification fields
    value_chain_stages: Optional[List[str]] = None
    sector_details: Optional[Dict[str, Any]] = None
    women_employment_pct: Optional[float] = None
    youth_employment_pct: Optional[float] = None

    # R2 — Gender & Youth intentional design flags
    gender_intentional: Optional[bool] = None
    gender_justification: Optional[str] = None
    youth_focused: Optional[bool] = None
    youth_justification: Optional[str] = None

    # R8 — Geospatial site coordinates (optional)
    site_lat: Optional[float] = None
    site_lon: Optional[float] = None
    site_location_name: Optional[str] = None

    # Lifecycle Config
    allowed_transitions: List[str] = []


class ProjectMemberRead(BaseModel):
    """Member-safe Deal Room projection of a Project.

    EXACTLY these fields — no key contacts, no financing internals, no
    facilitator-only metadata. This is the contract the mobile Deal Room
    list/detail consumes (GET /pipeline/member).
    """
    id: UUID
    twg_id: UUID                          # owning TWG (multi-TWG Martin grounding)
    name: str
    sector: Optional[str] = None          # Project.pillar
    status: ProjectStatus
    investment_size: Decimal              # "value" of the deal
    currency: str = "USD"
    readiness_score: float = 0.0
    afcen_score: Optional[float] = None
    strategic_alignment_score: Optional[float] = None
    location: Optional[str] = None        # lead_country, else site_location_name
    description: str
    is_following: bool = False            # current user has expressed interest
    interest_count: int = 0               # total members following


class ScoreBreakdownItem(BaseModel):
    """One member-safe scoring row: criterion name, weight, score — NOTHING
    else (notes / scored_by are facilitator-only and stay server-side)."""
    criterion: str
    weight: float
    score: float


class ProjectMemberDetail(ProjectMemberRead):
    """Member-safe Deal Room DETAIL projection (GET /pipeline/member/{id}).

    ALL ProjectMemberRead fields PLUS exactly these member-safe extras.
    Still NO key contacts (key_contact_name/email), no assigned_agent,
    no metadata_json / approval fields / deal_room_priority, no site
    coordinates, no revenue_model / macroeconomic_roi / funding_secured_usd.
    """
    subsector: Optional[str] = None
    investment_stage_label: Optional[str] = None      # e.g. "Investment-ready"
    project_sponsor: Optional[str] = None             # org-level sponsor
    is_cross_border: Optional[bool] = None
    financing_structure: Optional[str] = None         # coarse label only
    technical_studies: Optional[str] = None
    land_status: Optional[str] = None
    permits_licences: Optional[str] = None
    climate_impact: Optional[str] = None
    smallholder_farmers_reached: Optional[str] = None
    submitted_by: Optional[str] = None                # org, e.g. "FAO"
    updated_at: Optional[datetime] = None
    score_breakdown: List[ScoreBreakdownItem] = []    # weight desc; [] when unscored


class ProjectInterestState(BaseModel):
    """Response of POST/DELETE /pipeline/{project_id}/interest."""
    project_id: UUID
    is_following: bool
    interest_count: int


class ScoringCriteriaRead(BaseModel):
    id: UUID
    criterion_name: str
    criterion_type: str
    weight: Decimal
    description: Optional[str] = None

class ScoringCriteriaWeightUpdate(BaseModel):
    weight: Decimal

class ProjectScoreDetailRead(BaseModel):
    id: UUID
    criterion: ScoringCriteriaRead
    score: float
    notes: Optional[str] = None
    scored_date: datetime

class PipelineStats(BaseModel):
    """Schema for pipeline dashboard stats"""
    total_projects: int
    healthy_projects: int
    stalled_projects: List[Any]
    by_stage: Dict[str, Any]
    checked_at: datetime

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


class FinancingTranche(BaseModel):
    """R7 — one layer of the blended finance capital stack."""
    label: str
    dfi_window_name: Optional[str] = None
    instrument_type: str  # GRANT | CONCESSIONAL_LOAN | EQUITY | BLENDED
    amount_usd: float
    tenor_years: Optional[int] = None
    coupon_pct: Optional[float] = None
    seniority: int = 1  # 1=most senior, higher=more junior / first-loss
    is_first_loss: bool = False
    notes: Optional[str] = None


class FinancingMemoResponse(BaseModel):
    project_id: str
    project_name: str
    source: str = "llm"  # "llm" for AI-generated, "default_fallback" when AI unavailable
    error_class: Optional[str] = None  # e.g. "TimeoutError", "RateLimitError" when source==default_fallback
    recommended_structure: str
    grant_component_pct: int
    concessional_component_pct: int
    commercial_component_pct: int
    # R7 — Structured capital-stack tranches; complements the high-level pct breakdown above.
    tranches: List[FinancingTranche] = Field(default_factory=list)
    priority_windows: List[str]
    key_risks: List[str]
    next_steps: List[str]
    full_memo: str


# ---------------------------------------------------------------------------
# R5 — Incubation checklist
# ---------------------------------------------------------------------------
class IncubationChecklistItem(BaseModel):
    code: str
    label: str
    completed: bool
    document_id: Optional[UUID] = None


class IncubationChecklistRead(BaseModel):
    items: List[IncubationChecklistItem]
    completed_count: int
    total_count: int


# ---------------------------------------------------------------------------
# R8 — Geospatial site analysis
# ---------------------------------------------------------------------------
class ProjectGeospatialRead(BaseModel):
    """One project's cached Sentinel-2-style site analysis. STUB DATA today —
    `is_demo: true` indicates synthetic values from the seeded local generator.
    Real Copernicus integration will set `is_demo: false`."""
    id: UUID
    project_id: UUID
    ndvi: float
    water_proximity_km: float
    land_use_description: str
    land_use_smallholder_pct: float
    deforestation_risk: str
    geo_score_boost: int
    source: str
    is_demo: bool
    analysed_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# R9 — Post-commitment impact monitoring
# ---------------------------------------------------------------------------
from datetime import date as _date  # local alias to avoid clashing with class members

class ImpactLogEntryCreate(BaseModel):
    period_label: str = Field(..., min_length=1, max_length=64)
    period_start: _date
    period_end: _date
    jobs_created: Optional[int] = None
    ghg_avoided_tco2: Optional[float] = None
    smallholders_reached: Optional[int] = None
    women_jobs_actual: Optional[int] = None
    youth_jobs_actual: Optional[int] = None
    investment_deployed_usd: Optional[Decimal] = None
    notes: Optional[str] = None


class ImpactLogEntryRead(ImpactLogEntryCreate):
    id: UUID
    project_id: UUID
    logged_by_id: UUID
    logged_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ImpactSummaryRead(BaseModel):
    """Cumulative actuals vs target — for the headline metric cards."""
    project_id: UUID
    # Targets parsed from project columns
    target_jobs: Optional[int] = None
    target_ghg_tco2: Optional[float] = None
    target_smallholders: Optional[int] = None
    target_investment_usd: Optional[Decimal] = None
    # Cumulative actuals across all log entries
    actual_jobs: int = 0
    actual_ghg_tco2: float = 0.0
    actual_smallholders: int = 0
    actual_women_jobs: int = 0
    actual_youth_jobs: int = 0
    actual_investment_deployed: Decimal = Decimal("0")
    entry_count: int = 0

