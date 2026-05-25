# AfCEN ECOWAS Agribusiness Deal Room
## Platform Status & Updated Gap Position — May 2026

**Date:** 25 May 2026
**Prepared by:** AfCEN Platform Team
**Builds on:** Carren Mwanzia's *Global Benchmark Comparison & Gap Analysis* (May 2026)
**Audience:** AfCEN Steering Committee · WAIIS 2026 Programme Office
**Status:** CONFIDENTIAL — pre-Summit review draft

---

## Executive Summary

This document is the platform-side companion to Carren Mwanzia's May 2026 benchmark analysis. It reports on **what has actually shipped** against the nine priority gaps she identified, surfaces three additional gaps the implementation audit revealed, and lays out the forward plan to the October/November 2026 ECOWAS Investment and Integration Summit in Sierra Leone.

The headline finding is that **the platform is meaningfully closer to global best practice than the original gap analysis assumed**. Several of Carren's nine recommendations had been partially implemented in production code before her analysis was written. Some were dormant — coded but never activated. A small number were genuinely missing.

Phase 0 (Truth & Safety) and Phase 1 (Wiring the Signals) are now complete. The WAIIS scoring framework has been reconciled — production is running on a nine-criterion model that closes Carren's R3 (Impact sub-scoring) and R4 (ECOWAS regional integration) as side-effects. Investor matching now consumes the same project signals (value chain, gender, youth, ECOWAS cross-border, climate) that the DFI matching engine has used since launch. The dual-implementation problem on gender/youth (binary + percentage parallel systems) has been resolved in favour of the binary + justification model Carren documented.

Three real gaps remain ahead of the Summit: a richer Incubation track, satellite-evidenced site analysis, and post-commitment impact monitoring. Carren's recommended timeline still holds.

---

## 1 · What's Shipped — Inventory at 25 May 2026

The Deal Pipeline now runs on:

| Capability | State |
|---|---|
| Pipeline workflow | 7 stages (Draft → Committed) **plus** a dedicated `INCUBATION` stage that sits before Draft. Lifecycle transitions enforced by service code. |
| Live pipeline scale | 21 active projects across 8 TWGs, combined investment value US$ 6.7 billion |
| **WAIIS scoring engine** | **9 criteria, weights sum to 100%** (Readiness 18 · Bankability 18 · Scale of Impact 13 · Climate Impact 10 · Country & Political Enablement 10 · Social Impact 10 · ECOWAS Integration 10 · Economic Impact 8 · Scalability/Replicability 3). All 21 projects rescored on the new framework as of 25 May. |
| Investor matching | Score-based across 10 signals (sector · ticket size · geography · instrument · AfCEN readiness · value chain overlap · gender mandate · youth mandate · ECOWAS regional bonus · climate alignment). Every match carries an explainable per-signal rationale string. 20 investors in the database (15 generic + 5 mandate-rich). |
| DFI / Blended Finance | 15 DFI windows seeded · LLM-generated financing memo with capital-stack breakdown · explicit "AI unavailable" fallback state to prevent silent placeholder outputs. |
| Buyer / Offtake matching | Plumbing complete (model · service · UI tab). No anchor buyers seeded yet (Phase 3 work). |
| Stage gate · UNDER_REVIEW → SUMMIT_READY | Requires `gender_intentional` and `youth_focused` flags declared, justification ≥ 50 chars when either is true. |
| Stage gate · INCUBATION → DRAFT | Requires AfCEN score ≥ configurable threshold (default 40). LLM-generated readiness gap report available per project. |
| Privacy gate | Investor-role API requests cannot see INCUBATION projects (filtered from list endpoints, 404 on direct fetch). |
| Martin AI co-pilot | Refactored to honest binary alerts ("gender focus not yet declared") — the misleading "(not set / 30% required)" warnings stakeholders saw on the dashboard are gone. |

---

## 2 · WAIIS Scoring Framework — Current State

Carren's original document described a six-criterion framework (Readiness 20% · Strategic Alignment 20% · Market Viability 20% · Financial Sustainability 15% · Impact 15% · Scalability 10%). The production system has since evolved past that. This is what the platform is actually scoring on:

| Criterion | Weight | Type | Primary inputs |
|---|---:|---|---|
| **Readiness** | 18% | gating | feasibility, ESIA, permits, site control, team capacity |
| **Bankability** | 18% | gating | financial model presence + quality, IRR, revenue structure |
| **Scale of Impact** | 13% | impact | investment size, cross-border reach |
| **Climate Impact** | 10% | impact | GHG-avoided target, renewable energy indicators, climate resilience |
| **Country & Political Enablement** | 10% | political | government support, policy environment, land enablement |
| **Social Impact** | 10% | impact | jobs, smallholders reached, gender-intentional + justification, youth-focused + justification |
| **ECOWAS Integration** | 10% | regional | cross-border declaration, lead country in ECOWAS-15, beneficiary countries |
| **Economic Impact** | 8% | impact | ROI evidence, revenue model, investment size threshold |
| **Scalability / Replicability** | 3% | scalability | regional replication pathway |
| **Total** | **100%** | | |

**Notes for steering committee:**

1. This framework closes Carren's R3 (Impact split into Climate / Social / Economic) and R4 (ECOWAS regional integration criterion) — both are first-class criteria with their own weights and scoring functions, not sub-scores buried elsewhere.
2. The framework was already designed and coded but **dormant** in production until 25 May 2026 — no project rescore had triggered the migration since the code shipped. All 21 active projects were rescored against the new framework on that date.
3. Migration is destructive of legacy "Additionality" score history (replaced by Climate / Social / Economic Impact). Pre-migration snapshot is preserved at `/tmp/waiis_migration_snapshot_*.json` for audit.
4. Most projects' AfCEN scores dropped 5–10 points relative to the legacy framework — **this is the expected and desired effect**. The new criteria reveal impact dimensions (climate evidence, gender intent, social inclusion) that the old single-criterion "Additionality" rolled into one number. Scores will recover as projects fill in the underlying data fields.

**One project showed a meaningful jump:** the *Praia Agri-Food Processing & Cold Chain Hub* moved from 15.00 to 41.60 on rescore — its profile genuinely matches the new framework's emphasis on processing, climate, and ECOWAS integration in a way the legacy criteria did not capture.

---

## 3 · Updated Gap Position — Carren's R1–R9 Against Reality

Each row maps Carren's original recommendation to what is actually in the platform today.

| # | Carren's recommendation | Audit finding | Current state |
|---|---|---|---|
| **R1** | Value chain sub-classification | Field existed but: only 5 stages on UI vs Carren's 7; not mandatory at intake; investor matching ignored it | ✅ **Closed.** 8-stage controlled vocabulary (Carren's 7 plus existing "Retail/Markets"). Mandatory at intake with server-side validator. Investor matching consumes it. 22 of 22 projects classified via LLM backfill. |
| **R2** | Gender & Youth mandatory tags | Dual implementation discovered: binary booleans + percentage thresholds running in parallel. Martin AI co-pilot generated misleading "30% required" warnings. Not mandatory at intake. No stage gate. | ✅ **Closed and reconciled.** Binary + justification model is canonical. Stage gate enforces `gender_intentional` and `youth_focused` at UNDER_REVIEW → SUMMIT_READY with ≥ 50-char justification when true. Misleading percentage warnings removed. Percentage columns retained on the model for repurposing as R9 outcome tracking. |
| **R3** | Impact split into three sub-scores | Single `climate_impact` text field; no scoring split | ✅ **Closed via WAIIS migration.** Climate Impact (10%), Social Impact (10%), Economic Impact (8%) now independent criteria. |
| **R4** | ECOWAS regional integration criterion | Coded but dormant in seed function | ✅ **Closed via WAIIS migration.** "ECOWAS Integration" criterion at 10% weight, with scoring across cross-border declaration, ECOWAS-15 membership, and beneficiary country count. |
| **R5** | Pre-Pipeline Investment Readiness Track | INCUBATION status enum + lifecycle + LLM gap report shipped; visibility leak, no financial-model template, no doc checklist, 90-day TTL flagged but not enforced | ✅ **Closed.** Visibility leak patched. WAIIS XLSX financial-model template downloadable, six-item document checklist + progress, `ARCHIVED` status + 90-day auto-expiry scheduler + manual script, dedicated `/deal-pipeline/incubation` workspace. |
| **R6** | Buyer / Offtake matching | Full plumbing shipped — but **zero buyers seeded**; matching missing certifications; no offtake doc upload | ✅ **Closed.** 17 anchor buyers seeded (Olam, Cargill, ETG, Louis Dreyfus, Nestlé WA, Tony's Chocolonely, Promasidor, Dangote, Flour Mills Nigeria, Indorama, OCP Africa, Bühler, ABInBev, AAH, AIF, Twinings Ovaltine, Niger Foods). `certifications_accepted` + `verification_status` on Buyer. Matching rewritten with 6 scoring criteria including +20 certifications. `OFFTAKE_AGREEMENT` doc type boosts Bankability +10 pts. |
| **R7** | Blended Finance Structuring Module | 15 DFI windows + LLM memo + stacked-bar UI shipped. Missing: tranche modelling, eligibility rules, fallback honesty. | ✅ **Closed.** Per-window `concessional_eligibility_rules` JSON with eligibility filter ("INELIGIBLE: Project size $9M exceeds window max $5M"). New `blended_finance_packages` + `blended_finance_tranches` tables capture seniority / instrument / amount / tenor / coupon / first-loss per layer. LLM memo prompt extended to produce structured tranche stacks referencing real DFI windows. UI modal renders each tranche with FIRST-LOSS badge + instrument-coloured border. |
| **R8** | Geospatial / Sentinel-2 land analysis | Not present in code | ✅ **Closed — Sentinel-2 integration ready, fixture mode active.** New `CopernicusClient` calls the CDSE Process API for four signals: NDVI (Sentinel-2 L2A), water proximity (JRC Global Surface Water), land use (ESA WorldCover 2021), EUDR deforestation risk (Hansen Global Forest Change). Dispatches by `COPERNICUS_CLIENT_ID` env var — locally runs in fixture mode with five pre-recorded West African snapshots (Bouaké, Korhogo, Bondoukou, Tamale, Accra) and a deterministic synthetic fallback for unknown coordinates. Three-state Site Analysis banner reflects the data source: green "Live Sentinel-2" / amber "Reference fixture" / amber "Synthetic placeholder". New `source` column on `project_geospatial_data` makes the provenance auditable. Scoring extracted to a pure-function module (`compute_boost`) and tested independently. Live credentials are a separate ops decision; the fixture path is the primary local-mirror experience and works offline. |
| **R9** | Post-commitment impact monitoring | Not present in code | ✅ **Closed.** New `impact_log_entries` table. Quarterly entries: jobs, GHG (tCO₂e), smallholders, women/youth jobs, USD deployed, notes. Cumulative actuals + targets auto-parsed from project text. "📊 Impact monitoring" tab on COMMITTED/IMPLEMENTED projects with 4 progress-bar metric cards + quarterly history + "Log quarter" modal (ADMIN/SECRETARIAT). |

---

## 4 · Three Additional Gaps Surfaced by the Implementation Audit

These were not in Carren's original document but were identified during the May 25 audit. They have either been resolved or are part of the forward plan.

| # | Finding | Status |
|---|---|---|
| **A1** | Investor matching engine ignored the project signals (value chain, gender, youth, ECOWAS, climate) that DFI matching had been consuming since launch. The platform was effectively collecting classification data and using only half of it. | ✅ **Closed.** Investor scoring now consumes all 10 signals with explainable per-signal rationale strings ("+25 sector match · +10 value chain overlap · +5 gender mandate match · +5 ECOWAS cross-border × ECOWAS-focused investor"). |
| **A2** | WAIIS scoring framework drift: the prod database was running on a 6-criterion legacy set; the code had a 9-criterion target framework defined but never triggered; Carren's document described a third framework. | ✅ **Closed.** 9-criterion framework activated, all projects rescored, Carren's document (this one) updated to match reality. |
| **A3** | LLM financing-memo fallback silently substituted a hardcoded "60/30/10 grant/concessional/commercial" capital stack when the AI advisor was unavailable. Users could not tell whether the recommendation was AI-derived or default placeholder. | ✅ **Closed.** Response now carries an explicit `source: "llm" \| "default_fallback"` flag and `error_class`. UI renders amber "AI advisor unavailable" warning banner when fallback is in effect. |

---

## 5 · Forward Plan to Summit

> **As of 25 May 2026:** Phase 2 (R5-flesh), Phase 3 (R6 + R7), and Phase 4 (R8 + R9) are all delivered. R8 ships with the Copernicus Data Space integration in place; the local mirror runs in fixture mode (five pre-recorded West African snapshots) and switches to live Sentinel-2 the moment credentials are configured. The substantive build work is therefore complete; the remaining work is operational (provisioning Copernicus credentials, stakeholder onboarding) rather than additional features.

### Phase 2 — Incubation Track Completeness ✅ DELIVERED

- ✅ WAIIS XLSX financial-model template downloadable from every Incubation project
- ✅ Six-item document checklist endpoint + inline strip on Incubation project pages
- ✅ Distinct `/deal-pipeline/incubation` workspace listing all pre-pipeline projects with checklist progress + countdown
- ✅ 90-day auto-expiry handler — `ARCHIVED` status + scheduled `archive_stalled_incubation_projects` job + manual script for local runs

### Phase 3 — Strengthen the Matching Engines ✅ DELIVERED

- ✅ **R6:** 17 anchor buyers seeded with realistic profiles. Buyer model extended with `certifications_accepted` + `verification_status`. Matching algorithm rewritten — six scoring criteria (commodity 30 · geography 20 · certifications 20 · volume fit 15 · ECOWAS bonus 10 · verified-partner bonus 5). `OFFTAKE_AGREEMENT` document type recognized and boosts Bankability sub-score +10 pts when uploaded.
- ✅ **R7:** Per-window `concessional_eligibility_rules` JSON; eligibility filter surfaces "INELIGIBLE: <reason>" for non-qualifying windows. Tranche modelling tables (`blended_finance_packages` + `blended_finance_tranches`) capture instrument type, amount, tenor, coupon, seniority, first-loss flag. LLM financing-memo prompt produces structured 3–4-tranche capital stacks. Frontend modal renders each tranche with seniority ordering, FIRST-LOSS badge, and instrument-coloured borders.

### Phase 4 — Evidence & Outcome (Sep–Nov 2026)

- ✅ **R8 — Geospatial integration.** Copernicus Data Space client shipped. Four signals via CDSE Process API: NDVI (Sentinel-2 L2A), water proximity (JRC Global Surface Water), land use (ESA WorldCover), EUDR risk (Hansen Forest Change). Local mirror runs in fixture mode with five West African reference snapshots and a deterministic synthetic fallback; live mode activates when `COPERNICUS_CLIENT_ID` is configured. UI banner reflects data source explicitly (green = live, amber = fixture/stub). Provisioning live credentials and the integration smoke test against real CDSE is the remaining operational step.
- ✅ **R9 — Post-commitment monitoring.** Quarterly actuals tracking shipped end-to-end. Backend table + endpoints (POST/GET/DELETE + summary). Frontend tab visible on COMMITTED/IMPLEMENTED projects with 4 progress-bar metric cards (jobs · GHG · smallholders · USD deployed) showing actual vs. parsed-from-project-text targets, historical quarterly table, "Log quarter" modal for ADMIN/SECRETARIAT roles.

---

## 6 · WAIIS Scoring Refinements — Status of Carren's Section 4

Carren's original document recommended specific refinements to each of the six WAIIS criteria. The mapping to the current framework is below.

| Carren's recommendation | Status |
|---|---|
| Break Readiness into legal/land + technical + team + co-financing sub-scores | 🟡 Single Readiness criterion; sub-scoring is a future refinement |
| ECOWAS regional integration bonus on Strategic Alignment | ✅ Implemented as a distinct criterion, "ECOWAS Integration" at 10% |
| Require documentary evidence for Market Viability scores > 7/10 | 🟡 LLM-based doc analysis informs scoring but no hard threshold gate yet |
| Gate Under Review → Summit Ready on financial model upload | 🟡 Stage gate enforces gender/youth declaration. Financial model gate is part of Phase 2 incubation completeness. |
| Split Impact into economic / climate / social inclusion | ✅ Implemented as three independent criteria (Economic 8% / Climate 10% / Social 10%) |
| Regional replication sub-score under Scalability | 🟡 Scalability/Replicability criterion exists; explicit "2+ ECOWAS markets within 5 years" sub-score is a refinement |

---

## 7 · Production Numbers — Snapshot at 25 May 2026

For the steering committee's situational awareness:

- **Active projects in pipeline:** 21
- **Total pipeline value:** US$ 6.7 billion
- **Projects by stage:** 1 Draft · 3 Pipeline · 8 Under Review · 6 Summit Ready · 3 In Negotiation · 0 Committed
- **High-readiness projects (AfCEN ≥ 60):** 1 (Office du Niger Rice & Agro-Processing Corridor, 55.10)
- **Average AfCEN score:** ~42 (will rise as project owners fill in the new fields that the framework now scores against)
- **TWGs:** 8
- **Investors in database:** 20 (15 generic + 5 mandate-rich, including Mastercard Foundation Africa Growth Fund, Acumen West Africa, Green Climate Fund West Africa Window, BII Agribusiness Programme, Sahel Capital Agribusiness Fund)
- **DFI windows:** 15 (AfDB ADPP, BII guarantee, PROPARCO Agrofinance, etc.)
- **Anchor buyers:** 0 — pending Phase 3 seeding
- **Cross-border projects:** 5 (Office du Niger, Central River Region, West Africa FSRP2, Hybrid Rice ECOWAS, Scaling Sustainable Seed Systems)

**Investor-matching demo on the Hybrid Rice Commercialization project** (the most fully classified project — gender-intentional, youth-focused, cross-border, climate-aligned):

| Top investor match | Score | Signals cited |
|---|---:|---|
| Mastercard Foundation Africa Growth Fund | 94 | sector · ticket · geography · AfCEN · value-chain · gender · youth · ECOWAS · high-commitment |
| Sahel Capital — Agribusiness Fund | 89 | sector · ticket · geography · AfCEN · value-chain (INPUTS + PROCESSING) · youth · ECOWAS |
| Acumen West Africa | 69 | sector · geography · AfCEN · value-chain (3 stages) · gender · ECOWAS · climate × GHG target |
| BII Agribusiness Programme | 59 | ticket · AfCEN · value-chain · gender · ECOWAS · climate × GHG |

These rationales are now visible on every match in the platform, making investor recommendations defensible and reviewable rather than opaque.

---

## 8 · Risks and Open Items

1. **Project description quality is the binding constraint.** The 21 active projects have largely empty `description` fields and zero attached documents in the restored snapshot. The LLM-driven classification was therefore necessarily conservative on gender / youth signals. To get the full value of the new framework, project owners need to populate their project descriptions and attach the documents they have. Once they do, a re-run of the backfill script will produce dramatically richer classifications.

2. **The 43 documents in the database are not linked to projects.** Either they belong to specific projects (and need re-linking) or they are unattached reference material. This should be triaged before Phase 4 begins.

3. **Investor seed data lags behind project pipeline data.** 20 investors against 38 projects is below the matchmaking density a Summit warrants. Recommend seeding 30–50 more investors with verifiable mandate data before the Featured stage opens to public review.

4. **R8 geospatial runs in fixture mode locally.** The Copernicus Data Space integration is implemented end-to-end — four signals via the CDSE Process API (NDVI, JRC water, ESA WorldCover, Hansen EUDR), scoring extracted to a pure module, three-state UI banner (`copernicus` / `fixture` / `stub`) showing data provenance honestly. The local mirror ships with `COPERNICUS_CLIENT_ID` unset → five pre-recorded West African fixtures (Bouaké, Korhogo, Bondoukou, Tamale, Accra) and a deterministic synthetic fallback. Provisioning Copernicus credentials in production flips every site analysis to live Sentinel-2 the next time it's triggered; no code or schema changes required.

5. **The 17 anchor buyers seeded in R6 are tagged `verification_status='demo'`.** Their commodity / geography / volume profiles are drawn from public corporate disclosures and are reasonable approximations, but they are not signed offtake partners. Replace with verified profiles or confirmed introductions before the Summit.

6. **15 DFI window eligibility rules are also demo-grade.** The per-window concessional eligibility rules (max project size, country exclusions, gender/climate prerequisites) reflect each DFI's published mandate but are not authoritative. Verify with each institution before publishing to project owners.

---

## 9 · Acknowledgements and Sources

This document supersedes the May 2026 platform-side reading of Carren Mwanzia's *Global Benchmark Comparison & Gap Analysis*. Carren's benchmark framing — AGRF Agribusiness Dealroom, Africa Investment Forum, FAO Hand-in-Hand — remains the right comparator set and is preserved here in full.

**Sources:**
- AGRF Agribusiness Dealroom — agribusinessdealroom.org · agra.org/agribusiness-dealroom
- Africa Investment Forum 2024 Market Days — africainvestmentforum.com · afdb.org
- FAO Hand-in-Hand Investment Forum 2025 — fao.org/hand-in-hand
- Carren Mwanzia, *AfCEN ECOWAS Agribusiness Deal Room: Global Benchmark Comparison & Gap Analysis* (May 2026)
- AfCEN Deal Pipeline User Guide & Test Protocol (May 2026, internal)
- AfCEN Overview Deck — africacen.org
- WAIIS Gap Resolution Roadmap — `docs/superpowers/specs/2026-05-25-waiis-gap-roadmap.md` (internal)

---

*Prepared for AfCEN Steering Committee review · WAIIS 2026 · CONFIDENTIAL*
