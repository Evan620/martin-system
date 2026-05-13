# Deal Pipeline Lifecycle Design

**Date:** 2026-05-13
**Status:** Approved

## Problem

The existing deal pipeline uses internal stage names (Draft, Pipeline, Under Review, Summit Ready, Featured, Negotiation, Committed) that don't match the terminology TWG facilitators use in their investment template spreadsheets. Carren Mwanzia (Agriculture TWG lead) uses: Concept, Pre-feasibility, Feasibility, Bankable. The platform needs to speak the same language as its users.

Additionally, the pipeline mixes two distinct workflows — project development (TWG-owned) and deal making (Secretariat-owned) — without a clear handoff point.

## Design

### Two-Phase Lifecycle

#### Phase 1 — Project Development (owned by TWG Facilitator)

| Stage | Meaning | Maps from import |
|---|---|---|
| **Concept** | Idea submitted, no studies done | `Concept` |
| **Pre-feasibility** | Early studies underway | `Pre-feasibility` |
| **Feasibility** | Feasibility / ESIA studies complete | `Feasibility`, `Feasibility / Investment-ready` |
| **Bankable** | Investment-ready, seeking financing | `Bankable`, `Feasibility / Bankable projects` |

TWG Facilitators can advance projects freely within Phase 1. They can also submit projects via Excel import or the New Project form.

#### Secretariat Gate

When a project reaches **Bankable**, it enters the secretariat's review queue. The secretariat makes a simple yes/no decision: select it for the summit or leave it in Bankable. No scoring required at this stage (can be added later).

#### Phase 2 — Deal Making (owned by Secretariat / AfCEN)

| Stage | Meaning |
|---|---|
| **Summit Featured** | Selected for the summit. Visible in Deal Room. |
| **In Negotiation** | Investor engaged, term sheet in progress. |
| **Committed** | Deal signed, finance committed. |

Only users with Secretariat/Admin role can advance a project from Bankable → Summit Featured or beyond.

### What Changes

1. **Stage names** — rename all 7 stages in the DB enum and frontend display to match the terminology above (Concept, Pre-feasibility, Feasibility, Bankable, Summit Featured, In Negotiation, Committed)
2. **Stage tracker UI** — show phase labels ("Project Development" / "Deal Making") on the pipeline progress bar
3. **Advance Stage permissions** — restrict advancement past Bankable to Secretariat/Admin role only
4. **Excel import mapping** — update `_STAGE_MAP` to map all Carren's stage variants correctly (already partially done)
5. **Re-import** — delete and re-import Carren's 21 projects with corrected stage mappings

### What Stays the Same

- All 7 investment template fields (subsector, project_sponsor, is_cross_border, land_status, revenue_model, climate_impact, esg_compliance)
- Excel import flow and column mapping logic
- Project detail page structure and tabs
- AI Agent Insight panel
- AfCEN score and readiness score (kept for future use, not prominently surfaced yet)
- Deal Room / Investor DB tabs

### Out of Scope (for this iteration)

- Scoring criteria configuration per TWG
- Secretariat review UI (queue view of all Bankable projects)
- Investor-facing Deal Room enhancements
- Back-and-forth between secretariat and TWG to fill gaps before summit selection

## Stage Enum Mapping (old → new)

| Old enum value | New enum value | Display name |
|---|---|---|
| `DRAFT` | `CONCEPT` | Concept |
| `PIPELINE` | `PRE_FEASIBILITY` | Pre-feasibility |
| `UNDER_REVIEW` | `FEASIBILITY` | Feasibility |
| `SUMMIT_READY` | `BANKABLE` | Bankable |
| `DEAL_ROOM_FEATURED` | `SUMMIT_FEATURED` | Summit Featured |
| `IN_NEGOTIATION` | `IN_NEGOTIATION` | In Negotiation |
| `COMMITTED` | `COMMITTED` | Committed |

> Note: `IMPLEMENTED` stage is dropped — out of scope for summit context.

## Actors

| Actor | Role in pipeline |
|---|---|
| TWG Facilitator (e.g. Carren) | Submits and manages projects through Phase 1 |
| Secretariat / AfCEN Admin | Reviews Bankable projects, selects for summit, manages Phase 2 |
| Investor | Browses Deal Room (Phase 2 only) |
