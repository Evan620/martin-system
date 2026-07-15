
// Project Status Enum
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
    ARCHIVED = "ARCHIVED",
}

// R5 — Incubation checklist
export interface IncubationChecklistItem {
    code: string;
    label: string;
    completed: boolean;
    document_id: string | null;
}

export interface IncubationChecklist {
    items: IncubationChecklistItem[];
    completed_count: number;
    total_count: number;
}

// Investor Match Status Enum
export enum InvestorMatchStatus {
    DETECTED = "detected",
    CONTACTED = "contacted",
    INTERESTED = "interested",
    NEGOTIATING = "negotiating",
    COMMITTED = "committed",
    DECLINED = "declined"
}

// Interfaces
export interface Project {
    id: string;
    name: string;
    description: string;
    investment_size: number;
    currency: string;
    readiness_score: number;
    status: ProjectStatus;
    pillar?: string;
    lead_country?: string;
    afcen_score?: number;
    strategic_alignment_score?: number;
    regional_impact_score?: number; // Optional, computed only if available
    assigned_agent?: string;
    updated_at: string;

    funding_secured_usd?: number;
    is_flagship?: boolean;
    deal_room_priority?: number;

    // Section A — Basic Project Information
    subsector?: string;
    project_sponsor?: string;
    is_cross_border?: boolean;
    key_contact_name?: string;
    key_contact_email?: string;

    // Section B — Project Development Status
    technical_studies?: string;
    permits_licences?: string;
    land_status?: string;

    // Section C — Investment Profile
    financing_structure?: string;
    investment_stage_label?: string;
    revenue_model?: string;
    macroeconomic_roi?: string;

    // Section D — Climate & Social Impact
    climate_impact?: string;
    esg_compliance?: string;
    ghg_avoided_target?: string;
    jobs_construction?: string;
    jobs_om?: string;
    electricity_connections?: string;
    digital_connections?: string;
    smallholder_farmers_reached?: string;

    // Submission
    submitted_by?: string;

    // Section A — Classification (Phase 1)
    value_chain_stages?: string[];
    sector_details?: Record<string, any>;
    women_employment_pct?: number;
    youth_employment_pct?: number;

    // R2 — Gender & Youth intentional design flags
    gender_intentional?: boolean;
    gender_justification?: string;
    youth_focused?: boolean;
    youth_justification?: string;

    // R8 — Site coordinates for geospatial analysis
    site_lat?: number;
    site_lon?: number;
    site_location_name?: string;

    // Metadata from backend API
    days_in_stage?: number;
    is_stalled?: boolean;
    allowed_transitions?: string[];
    metadata_json?: Record<string, any>;
}

export interface ScoringCriteria {
    id: string;
    criterion_name: string;
    criterion_type: string;
    weight: number;
    description?: string;
}

export interface ProjectScoreDetail {
    id: string;
    criterion: ScoringCriteria;
    score: number;
    notes?: string;
    scored_date: string;
}

export interface Investor {
    id: string;
    name: string;
    sector_preferences?: string[];
    ticket_size_min?: number;
    ticket_size_max?: number;
    geographic_focus?: string[];
    investment_instruments?: string[];
    investor_type?: string;
    contact_name?: string;
    contact_email?: string;
    total_commitments_usd?: number;
}

export interface InvestorMatch {
    match_id: string;
    investor: Investor;
    investor_name?: string; // Legacy/Fallback
    score: number;
    status: InvestorMatchStatus;
    notes?: string;
}

export interface PipelineStats {
    total_projects: number;
    healthy_projects: number;
    stalled_projects: any[]; // Define more specifically if needed
    by_stage: Record<string, { total: number; stalled: number }>;
    checked_at: string;
}

// DTOs
export interface ProjectIngestDTO {
    twg_id: string;
    name: string;
    description: string;
    investment_size: number;
    readiness_score: number;
    strategic_alignment_score: number;
    pillar?: string;
    lead_country?: string;
    assigned_agent?: string;
}

export interface UpdateMatchStatusDTO {
    status: InvestorMatchStatus;
    notes?: string;
}

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

export interface FinancingTranche {
    label: string;
    dfi_window_name?: string | null;
    instrument_type: 'GRANT' | 'CONCESSIONAL_LOAN' | 'EQUITY' | 'BLENDED';
    amount_usd: number;
    tenor_years?: number | null;
    coupon_pct?: number | null;
    seniority: number;  // 1 = most senior, larger = more junior
    is_first_loss: boolean;
    notes?: string | null;
}

export interface FinancingMemo {
    project_id: string;
    project_name: string;
    source?: 'llm' | 'default_fallback';
    error_class?: string | null;
    recommended_structure: string;
    grant_component_pct: number;
    concessional_component_pct: number;
    commercial_component_pct: number;
    tranches?: FinancingTranche[];
    priority_windows: string[];
    key_risks: string[];
    next_steps: string[];
    full_memo: string;
}

// R8 — AI-scouted coordinates (not persisted until user confirms)
export interface ScoutedCoordinates {
    lat: number;
    lon: number;
    place_name: string;
    confidence: number;
    reasoning: string;
    project_id: string;
}

// R8 — Geospatial site analysis
export interface ProjectGeospatial {
    id: string;
    project_id: string;
    ndvi: number;
    water_proximity_km: number;
    land_use_description: string;
    land_use_smallholder_pct: number;
    deforestation_risk: 'low' | 'medium' | 'high';
    geo_score_boost: number;
    source: 'copernicus' | 'fixture' | 'stub';
    is_demo: boolean;
    analysed_at: string;
}

// R9 — Post-commitment impact monitoring
export interface ImpactLogEntry {
    id: string;
    project_id: string;
    period_label: string;
    period_start: string;  // ISO date
    period_end: string;
    jobs_created?: number | null;
    ghg_avoided_tco2?: number | null;
    smallholders_reached?: number | null;
    women_jobs_actual?: number | null;
    youth_jobs_actual?: number | null;
    investment_deployed_usd?: number | string | null;
    notes?: string | null;
    logged_by_id: string;
    logged_at: string;
}

export interface ImpactLogEntryCreate {
    period_label: string;
    period_start: string;
    period_end: string;
    jobs_created?: number | null;
    ghg_avoided_tco2?: number | null;
    smallholders_reached?: number | null;
    women_jobs_actual?: number | null;
    youth_jobs_actual?: number | null;
    investment_deployed_usd?: number | null;
    notes?: string | null;
}

export interface ImpactSummary {
    project_id: string;
    target_jobs?: number | null;
    target_ghg_tco2?: number | null;
    target_smallholders?: number | null;
    target_investment_usd?: number | string | null;
    actual_jobs: number;
    actual_ghg_tco2: number;
    actual_smallholders: number;
    actual_women_jobs: number;
    actual_youth_jobs: number;
    actual_investment_deployed: number | string;
    entry_count: number;
}
