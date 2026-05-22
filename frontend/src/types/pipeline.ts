
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
    women_employment_pct?: number;
    youth_employment_pct?: number;

    // R2 — Gender & Youth intentional design flags
    gender_intentional?: boolean;
    gender_justification?: string;
    youth_focused?: boolean;
    youth_justification?: string;

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
    sector_preferences: string[];
    ticket_size_min?: number;
    ticket_size_max?: number;
    geographic_focus?: string[];
    investment_instruments?: string[];
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
