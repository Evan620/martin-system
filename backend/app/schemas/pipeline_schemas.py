"""
Pipeline Schemas

Pydantic models for the Deal Pipeline API.
"""
from pydantic import BaseModel, Field, condecimal
from typing import Optional, List, Any, Dict
from datetime import datetime
from uuid import UUID
from decimal import Decimal

from app.models.models import ProjectStatus, InvestorMatchStatus

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

    # R2 — Gender & Youth intentional design flags
    gender_intentional: Optional[bool] = None
    gender_justification: Optional[str] = None
    youth_focused: Optional[bool] = None
    youth_justification: Optional[str] = None

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
    women_employment_pct: Optional[float] = None
    youth_employment_pct: Optional[float] = None

    # R2 — Gender & Youth intentional design flags
    gender_intentional: Optional[bool] = None
    gender_justification: Optional[str] = None
    youth_focused: Optional[bool] = None
    youth_justification: Optional[str] = None

    # Lifecycle Config
    allowed_transitions: List[str] = []

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
