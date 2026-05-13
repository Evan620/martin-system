
// Project Status Enum
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

    // New fields (migration 2026)
    subsector?: string;
    project_sponsor?: string;
    is_cross_border?: boolean;
    land_status?: string;
    revenue_model?: string;
    climate_impact?: string;
    esg_compliance?: string;

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
