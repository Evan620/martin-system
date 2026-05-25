"""
Project Pipeline Coordinator Service

Manages the investment project lifecycle through defined stages:
Identification -> Vetting -> Due Diligence -> Financing -> Deal Room -> Bankable -> Presented

Coordinates with TWG agents for vetting and provides pipeline health monitoring.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timezone, timedelta
UTC = timezone.utc
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid
from decimal import Decimal

from app.models.models import (
    Project, ProjectStatus, TWG, TWGPillar,
    ActionItem, ActionItemStatus, ActionItemPriority,
    ScoringCriteria, ProjectScoreDetail, Document, User
)
from app.services.audit_service import audit_service
from app.services.document_intelligence import DocumentIntelligenceService





class ProjectPipelineService:
    """
    Service for coordinating project lifecycle and pipeline health.
    
    Manages:
    - Stage transitions with validation
    - Automatic task delegation to Resource Mobilization agent
    - Pipeline health monitoring for stalled projects
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize project pipeline service.

        Args:
            db: Async database session
        """
        self.db = db
        self.doc_intelligence = DocumentIntelligenceService()

    async def _ensure_default_criteria(self):
        """Seed 9 WAIIS scoring criteria (Phase 1). Create-if-not-exists only —
        never overwrites weights an admin has already set."""
        from sqlalchemy import delete as sa_delete

        result = await self.db.execute(select(ScoringCriteria))
        existing = result.scalars().all()
        existing_names = {c.criterion_name for c in existing}

        TARGET_NAMES = {
            "Readiness", "Scale of Impact", "Country & Political Enablement",
            "Bankability", "Climate Impact", "Social Impact",
            "Economic Impact", "ECOWAS Integration", "Scalability/Replicability"
        }

        # Already on the 9-criteria set — nothing to do
        if TARGET_NAMES.issubset(existing_names):
            return

        # Remove stale criteria (includes legacy "Additionality" if present)
        if existing:
            for c in existing:
                await self.db.execute(
                    sa_delete(ProjectScoreDetail).where(ProjectScoreDetail.criterion_id == c.id)
                )
            await self.db.execute(sa_delete(ScoringCriteria))
            await self.db.commit()
            logger.info("Cleared legacy scoring criteria; re-seeding with 9-criteria WAIIS set")

        defaults = [
            {"name": "Readiness",                      "type": "readiness",    "weight": 0.18,
             "desc": "Technical and regulatory readiness (feasibility, ESIA, permits, site control)"},
            {"name": "Scale of Impact",                "type": "impact",       "weight": 0.13,
             "desc": "Investment size and cross-border reach"},
            {"name": "Country & Political Enablement", "type": "political",    "weight": 0.10,
             "desc": "Government support and policy/land enablement"},
            {"name": "Bankability",                    "type": "bankability",  "weight": 0.18,
             "desc": "Financial model quality, IRR, and revenue structure"},
            {"name": "Climate Impact",                 "type": "impact",       "weight": 0.10,
             "desc": "GHG reduction, renewable energy, climate resilience"},
            {"name": "Social Impact",                  "type": "impact",       "weight": 0.10,
             "desc": "Jobs, smallholder reach, gender and youth inclusion"},
            {"name": "Economic Impact",                "type": "impact",       "weight": 0.08,
             "desc": "ROI, revenue model, macroeconomic contribution"},
            {"name": "ECOWAS Integration",             "type": "regional",     "weight": 0.10,
             "desc": "Cross-border integration and ECOWAS regional footprint"},
            {"name": "Scalability/Replicability",      "type": "scalability",  "weight": 0.03,
             "desc": "Potential to scale or replicate across the region"},
        ]

        for d in defaults:
            self.db.add(ScoringCriteria(
                criterion_name=d["name"],
                criterion_type=d["type"],
                weight=Decimal(str(d["weight"])),
                description=d["desc"]
            ))

        await self.db.commit()
        logger.info("✓ Seeded 9 WAIIS scoring criteria (Phase 1 set)")

    async def assess_project_readiness(self, project_id: uuid.UUID) -> Decimal:
        """
        Score project against 6 WAIIS criteria (each 0-100) using hybrid
        field + document analysis. Returns composite AfCEN score (0-100).
        """
        await self._ensure_default_criteria()

        stmt = select(Project).where(Project.id == project_id)
        result = await self.db.execute(stmt)
        project = result.scalars().first()
        if not project:
            return Decimal("0.0")

        doc_stmt = select(Document).where(Document.project_id == project_id)
        doc_res = await self.db.execute(doc_stmt)
        documents = doc_res.scalars().all()

        from app.services.document_analyzer import get_document_analyzer
        analyzer = get_document_analyzer()
        all_analyses = []
        logger.info(f"Analyzing {len(documents)} documents for project {project_id}")
        for doc in documents:
            try:
                text = await self.doc_intelligence.extract_text_from_document(
                    doc.file_path, doc.file_type
                )
                analysis = await analyzer.analyze_document(text, doc.file_name)
                all_analyses.append(analysis)
                logger.info(f"✓ Analyzed {doc.file_name}: {analysis.get('document_type')}")
            except Exception as e:
                logger.error(f"Failed to analyze {doc.file_name}: {e}")

        agg = self._aggregate_document_analyses(all_analyses)
        # R6 — Offtake-agreement evidence (signed MOU / supply contract) is a
        # bankability signal independent of LLM doc analysis. Presence of any
        # document with type OFFTAKE_AGREEMENT counts.
        agg["has_offtake_agreement"] = any(
            (d.document_type or "").upper() == "OFFTAKE_AGREEMENT" for d in documents
        )

        # R8 — Pull geospatial boost from cached ProjectGeospatialData if present.
        # geo_score_boost (0–15) is added to Readiness in _compute_waiis_sub_scores.
        from app.models.models import ProjectGeospatialData
        geo_res = await self.db.execute(
            select(ProjectGeospatialData).where(ProjectGeospatialData.project_id == project_id)
        )
        geo_row = geo_res.scalar_one_or_none()
        if geo_row:
            agg["geo_score_boost"] = geo_row.geo_score_boost
            agg["geo_is_demo"] = geo_row.is_demo
            agg["geo_ndvi"] = geo_row.ndvi
            agg["geo_deforestation_risk"] = geo_row.deforestation_risk

        sub_scores = self._compute_waiis_sub_scores(project, agg)

        criteria_res = await self.db.execute(select(ScoringCriteria))
        all_criteria = criteria_res.scalars().all()
        criteria_map = {c.criterion_name: c for c in all_criteria}

        for name, raw_score in sub_scores.items():
            crit = criteria_map.get(name)
            if not crit:
                continue
            score = Decimal(f"{raw_score:.2f}")
            notes = self._build_score_notes(name, project, agg, raw_score)

            detail_stmt = select(ProjectScoreDetail).where(
                ProjectScoreDetail.project_id == project_id,
                ProjectScoreDetail.criterion_id == crit.id
            )
            det_res = await self.db.execute(detail_stmt)
            detail = det_res.scalars().first()
            if detail:
                detail.score = score
                detail.notes = notes
                detail.scored_date = datetime.utcnow()
            else:
                self.db.add(ProjectScoreDetail(
                    project_id=project_id,
                    criterion_id=crit.id,
                    score=score,
                    notes=notes
                ))

        weighted_sum = sum(
            sub_scores[name] * float(criteria_map[name].weight)
            for name in sub_scores
            if name in criteria_map
        )
        total_weight = sum(
            float(criteria_map[name].weight)
            for name in sub_scores
            if name in criteria_map
        )
        final_afcen = weighted_sum / total_weight if total_weight > 0 else 0.0
        afcen = Decimal(f"{final_afcen:.2f}")

        project.readiness_score = sub_scores.get("Readiness", 0.0)
        project.strategic_alignment_score = float(afcen) / 10.0
        project.afcen_score = afcen

        await self.db.flush()
        await self.db.commit()

        logger.info(
            f"✓ AfCEN scored: {afcen} | " +
            " | ".join(f"{k}: {v:.0f}" for k, v in sub_scores.items())
        )

        if float(afcen) >= 60:
            try:
                from app.services.scoring_tasks import match_investors_async
                match_investors_async.delay(str(project_id))
                logger.info(f"✓ Triggered investor matching for project {project_id} (AfCEN: {afcen})")
            except Exception as e:
                logger.warning(f"Could not trigger automatic investor matching: {e}")

        return afcen
    
    def _aggregate_document_analyses(self, analyses: list) -> dict:
        """
        Aggregate multiple document analyses into a single result.
        Uses OR logic: if ANY document has a feature, it's considered present.
        """
        aggregated = {
            "has_feasibility_study": False,
            "has_esia": False,
            "has_financial_model": False,
            "has_government_support": False,
            "has_permits": False,
            "has_site_control": False,
            "cross_border_impact": False,
            "esg_compliant": False,
            "irr_percentage": None,
            "npv_value": None
        }
        
        for analysis in analyses:
            # OR logic for boolean fields
            for key in ["has_feasibility_study", "has_esia", "has_financial_model", 
                       "has_government_support", "has_permits", "has_site_control",
                       "cross_border_impact", "esg_compliant"]:
                if analysis.get(key):
                    aggregated[key] = True
            
            # Take first non-null value for numeric fields
            if analysis.get("irr_percentage") and not aggregated["irr_percentage"]:
                aggregated["irr_percentage"] = analysis["irr_percentage"]
            if analysis.get("npv_value") and not aggregated["npv_value"]:
                aggregated["npv_value"] = analysis["npv_value"]
        
        return aggregated

    _ECOWAS_MEMBERS = {
        "benin", "burkina faso", "cabo verde", "cape verde", "cote d'ivoire",
        "côte d'ivoire", "ivory coast", "gambia", "ghana", "guinea",
        "guinea-bissau", "liberia", "mali", "mauritania", "niger",
        "nigeria", "senegal", "sierra leone", "togo"
    }

    def _compute_waiis_sub_scores(self, project, agg: dict) -> dict:
        """Compute 9 WAIIS sub-scores (0-100) from hybrid field + document signals."""

        # 1. READINESS
        doc_r = sum([
            25 if agg.get("has_feasibility_study") else 0,
            25 if agg.get("has_esia") else 0,
            25 if agg.get("has_permits") else 0,
            25 if agg.get("has_site_control") else 0,
        ])
        field_r = sum([
            34 if project.permits_licences and str(project.permits_licences).strip() else 0,
            33 if project.land_status and str(project.land_status).strip() else 0,
            33 if project.technical_studies and str(project.technical_studies).strip() else 0,
        ])
        readiness = (doc_r * 0.5) + (field_r * 0.5)
        # R8 — Geospatial boost. If a ProjectGeospatialData row exists for this
        # project, add geo_score_boost (0–15) to readiness. Capped at 100.
        geo_boost = int(agg.get("geo_score_boost") or 0)
        if geo_boost > 0:
            readiness = min(100.0, readiness + geo_boost)

        # 2. SCALE OF IMPACT
        inv = float(project.investment_size or 0)
        scale = 75.0 if inv >= 50_000_000 else (50.0 if inv >= 8_000_000 else (25.0 if inv > 0 else 0.0))
        if project.is_cross_border:
            scale += 25
        scale = min(100.0, scale)

        # 3. COUNTRY & POLITICAL ENABLEMENT
        doc_p = 50.0 if agg.get("has_government_support") else 0.0
        sponsor = str(project.project_sponsor or "").lower()
        land = str(project.land_status or "").lower()
        field_p = sum([
            25 if any(w in sponsor for w in ["government", "ministry", "public", "state", "federal"]) else 0,
            25 if any(w in land for w in ["government", "approved", "secured", "acquired", "granted"]) else 0,
        ])
        political = min(100.0, doc_p + field_p)

        # 4. BANKABILITY
        doc_b = 25.0 if agg.get("has_financial_model") else 0.0
        irr = agg.get("irr_percentage")
        if irr is not None:
            irr_f = float(irr)
            doc_b += 50 if irr_f >= 15 else (25 if irr_f >= 8 else 0)
        field_b = sum([
            25 if project.revenue_model and str(project.revenue_model).strip() else 0,
            25 if project.financing_structure and str(project.financing_structure).strip() else 0,
        ])
        # R6 — A signed offtake agreement / MOU substantially de-risks market exposure
        # and is a load-bearing signal for DFI investors. +10 pts when present.
        offtake_b = 10.0 if agg.get("has_offtake_agreement") else 0.0
        bankability = min(100.0, doc_b + field_b + offtake_b)

        # 5. CLIMATE IMPACT (replaces Additionality)
        climate_text = str(project.climate_impact or "").lower()
        ghg_text = str(project.ghg_avoided_target or "").lower()
        climate_keywords = ["solar", "wind", "renewable", "ghg", "carbon", "green", "climate",
                            "emissions", "photovoltaic", "biogas", "hydropower"]
        doc_climate = 40.0 if agg.get("esg_compliant") else 0.0
        field_climate = sum([
            30 if ghg_text.strip() else 0,
            30 if any(kw in climate_text for kw in climate_keywords) else 0,
        ])
        climate_impact = min(100.0, doc_climate + field_climate)

        # 6. SOCIAL IMPACT (replaces Additionality)
        import re
        jobs_text = str(project.jobs_construction or "") + " " + str(project.jobs_om or "")
        job_nums = re.findall(r'\d+', jobs_text)
        total_jobs = sum(int(n) for n in job_nums) if job_nums else 0

        smallholder_text = str(project.smallholder_farmers_reached or "")
        sh_nums = re.findall(r'\d+', smallholder_text)
        total_sh = sum(int(n) for n in sh_nums) if sh_nums else 0

        # Gender / youth signals use the canonical binary + justification model.
        # Score levels: 25 (intentional AND justified ≥50 chars), 12 (intentional but
        # justification thin), 0 (not intentional or undeclared). This rewards both
        # the design decision AND the rigor of the explanation that backs it up.
        def _score_inclusion_flag(flag: bool | None, justification: str | None) -> int:
            if not flag:
                return 0
            j = (justification or "").strip()
            if len(j) >= 50:
                return 25
            if j:
                return 12
            return 0

        gender_score = _score_inclusion_flag(project.gender_intentional, project.gender_justification)
        youth_score = _score_inclusion_flag(project.youth_focused, project.youth_justification)

        social_impact = sum([
            25 if total_jobs >= 100 else (12 if total_jobs > 0 else 0),
            25 if total_sh >= 500 else (12 if total_sh > 0 else 0),
            gender_score,
            youth_score,
        ])
        social_impact = min(100.0, float(social_impact))

        # 7. ECONOMIC IMPACT (replaces Additionality)
        roi_text = str(project.macroeconomic_roi or "").strip()
        economic_impact = sum([
            40 if agg.get("has_financial_model") else 0,
            30 if roi_text else 0,
            30 if inv >= 5_000_000 else (15 if inv > 0 else 0),
        ])
        economic_impact = min(100.0, float(economic_impact))

        # 8. ECOWAS INTEGRATION
        lead = str(project.lead_country or "").lower().strip()
        is_ecowas_country = lead in self._ECOWAS_MEMBERS
        # Base 20 pts for any lead country (project has regional presence)
        # Additional pts for ECOWAS membership, cross-border ops, doc evidence
        ecowas_score = sum([
            20 if lead else 0,
            20 if is_ecowas_country else 0,
            40 if project.is_cross_border else 0,
            25 if agg.get("cross_border_impact") else 0,
            15 if project.is_cross_border and is_ecowas_country else 0,
        ])
        ecowas_score = min(100.0, float(ecowas_score))

        # 9. SCALABILITY / REPLICABILITY
        scal = sum([
            34 if project.is_cross_border else 0,
            33 if project.climate_impact and str(project.climate_impact).strip() else 0,
            33 if inv >= 50_000_000 else (17 if inv >= 20_000_000 else 0),
        ])
        scalability = min(100.0, float(scal))

        return {
            "Readiness": readiness,
            "Scale of Impact": scale,
            "Country & Political Enablement": political,
            "Bankability": bankability,
            "Climate Impact": climate_impact,
            "Social Impact": social_impact,
            "Economic Impact": economic_impact,
            "ECOWAS Integration": ecowas_score,
            "Scalability/Replicability": scalability,
        }

    def _build_score_notes(self, criterion: str, project, agg: dict, score: float) -> str:
        """Generate human-readable scoring notes for a criterion."""
        notes = []
        if criterion == "Readiness":
            if agg.get("has_feasibility_study"): notes.append("feasibility study ✓")
            if agg.get("has_esia"):              notes.append("ESIA ✓")
            if agg.get("has_permits"):           notes.append("permits ✓")
            if agg.get("has_site_control"):      notes.append("site control ✓")
            if project.technical_studies:        notes.append("technical studies ✓")
            if project.permits_licences:         notes.append("permits field ✓")
            if project.land_status:              notes.append("land status ✓")
            gb = int(agg.get("geo_score_boost") or 0)
            if gb > 0:
                suffix = " (demo)" if agg.get("geo_is_demo") else ""
                notes.append(f"geo boost +{gb}{suffix}")
        elif criterion == "Scale of Impact":
            inv = float(project.investment_size or 0)
            notes.append(f"Investment: ${inv:,.0f}")
            if project.is_cross_border: notes.append("cross-border ✓")
        elif criterion == "Country & Political Enablement":
            if agg.get("has_government_support"): notes.append("gov support doc ✓")
            if project.project_sponsor:           notes.append(f"sponsor: {project.project_sponsor}")
            if project.land_status:               notes.append(f"land: {str(project.land_status)[:40]}")
        elif criterion == "Bankability":
            if agg.get("has_financial_model"): notes.append("financial model ✓")
            irr = agg.get("irr_percentage")
            if irr:                            notes.append(f"IRR: {irr}%")
            if project.revenue_model:          notes.append("revenue model ✓")
            if project.financing_structure:    notes.append("financing structure ✓")
            if agg.get("has_offtake_agreement"): notes.append("offtake agreement ✓ (+10)")
        elif criterion == "Climate Impact":
            if agg.get("esg_compliant"):          notes.append("ESG compliant (doc) ✓")
            if project.ghg_avoided_target:        notes.append(f"GHG target: {str(project.ghg_avoided_target)[:30]}")
            if project.climate_impact:            notes.append("climate impact ✓")
        elif criterion == "Social Impact":
            if project.jobs_construction or project.jobs_om: notes.append("jobs data ✓")
            if project.smallholder_farmers_reached:           notes.append("smallholders ✓")
            if project.women_employment_pct:                  notes.append(f"women: {project.women_employment_pct:.0f}%")
            if project.youth_employment_pct:                  notes.append(f"youth: {project.youth_employment_pct:.0f}%")
        elif criterion == "Economic Impact":
            if agg.get("has_financial_model"): notes.append("financial model ✓")
            if project.macroeconomic_roi:      notes.append("ROI data ✓")
            inv = float(project.investment_size or 0)
            if inv > 0: notes.append(f"${inv/1e6:.0f}M investment")
        elif criterion == "ECOWAS Integration":
            if project.is_cross_border: notes.append("cross-border ✓")
            if project.lead_country:    notes.append(f"country: {project.lead_country}")
            if agg.get("cross_border_impact"): notes.append("cross-border impact (doc) ✓")
        elif criterion == "Scalability/Replicability":
            if project.is_cross_border: notes.append("cross-border ✓")
            if project.climate_impact:  notes.append("climate impact ✓")
            inv = float(project.investment_size or 0)
            if inv >= 20_000_000:       notes.append(f"large-scale (${inv / 1e6:.0f}M)")
        return "; ".join(notes) if notes else f"Score: {score:.0f}/100"

    async def advance_project_stage(
        self,
        project_id: uuid.UUID,
        new_stage: ProjectStatus,
        advanced_by_user_id: Optional[uuid.UUID] = None,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Advance a project to a new stage with validation using LifecycleService.

        Args:
            project_id: ID of the project to advance
            new_stage: The target stage
            advanced_by_user_id: User performing the transition
            notes: Optional notes about the transition

        Returns:
            Dict with project and status, or error if invalid transition
        """
        # Fetch User
        user = None
        if advanced_by_user_id:
            user_res = await self.db.execute(select(User).where(User.id == advanced_by_user_id))
            user = user_res.scalars().first()
            
        if not user:
            # Fallback for system actions if allowed, or error?
            # For now, if no user provided, we might fail RBAC.
            # But let's assume system/admin if None? No, better to require user or mock system user.
            return {"error": "User required for status change"}

        from app.services.lifecycle_service import LifecycleService
        
        try:
            updated_project = await LifecycleService.transition_project_status(
                db=self.db,
                project_id=project_id,
                new_status=new_stage,
                changed_by_user=user,
                notes=notes,
                is_automated=False
            )
            # Refetch project to ensure it's fresh and attached
            project = updated_project 
            
            # Legacy fields update for backward compat if needed?
            # Metadata logging is handled by LifecycleService now (in history table).
            # But the 'stage_history' in metadata_json might be nice to keep in sync or just rely on new table.
            # We'll rely on the new table ProjectStatusHistory.
            
        except Exception as e:
             logger.error(f"Status transition failed: {e}")
             return {"error": str(e), "to_stage": new_stage.value}
             
        # Side Effects Triggers (retained from original logic)
        
        if new_stage == ProjectStatus.PIPELINE:
             # Prompt: "Notification sent to Resource Mob team", "Auto-trigger scoring"
             # For MVP, we log this auto-trigger. In prod, this would be a Celery task.
             logger.info(f"Auto-triggering scoring task for project {project_id}")
             pass

        if new_stage == ProjectStatus.UNDER_REVIEW:
             # If moving to UNDER_REVIEW, ensure vetting is requested if not exists.
             pass

        if new_stage == ProjectStatus.SUMMIT_READY:
             # Trigger investor matching via Celery for non-blocking execution
             try:
                 from app.services.scoring_tasks import match_investors_async
                 match_investors_async.delay(str(project_id))
                 logger.info(f"✓ Triggered investor matching for project {project_id} after advancing to SUMMIT_READY")
             except Exception as e:
                 logger.warning(f"Could not trigger automatic investor matching: {e}")

        # AUTOMATIC SCORING: Retrigger scoring after status change
        try:
            from app.services.scoring_tasks import rescore_project_async
            
            # Trigger background scoring via Celery
            rescore_project_async.delay(str(project_id))
            
            logger.info(f"✓ Triggered AfCEN rescoring for project {project_id} after status change to {new_stage.value}")
        except Exception as e:
            logger.warning(f"Could not trigger automatic scoring: {e}")

        return {
            "project": project,
            "status": "success",
            "from_stage": "unknown", # LifecycleService handles the transition but we don't grab old status here easily unless we queried before.
            "to_stage": new_stage.value
        }




    async def request_investment_vetting(
        self,
        project_id: uuid.UUID,
        requested_by_user_id: Optional[uuid.UUID] = None
    ) -> Dict[str, Any]:
        """
        Delegate a vetting task to the Resource Mobilization agent.

        Creates an ActionItem assigned to the Resource Mobilization TWG
        for conducting due diligence on the project.

        Args:
            project_id: ID of the project to vet
            requested_by_user_id: User requesting the vetting

        Returns:
            Dict with the created action item or error
        """
        result = await self.db.execute(
            select(Project).where(Project.id == project_id)
        )
        project = result.scalars().first()

        if not project:
            return {"error": "Project not found", "action_item": None}

        rm_twg_result = await self.db.execute(
            select(TWG).where(TWG.pillar == TWGPillar.resource_mobilization)
        )
        rm_twg = rm_twg_result.scalars().first()

        if not rm_twg:
            logger.warning("Resource Mobilization TWG not found")
            return {"error": "Resource Mobilization TWG not found", "action_item": None}

        owner_id = rm_twg.technical_lead_id or rm_twg.political_lead_id
        if not owner_id:
            return {"error": "Resource Mobilization TWG has no lead assigned", "action_item": None}

        action_item = ActionItem(
            twg_id=rm_twg.id,
            description=(
                f"Investment Vetting Required: {project.name}\n\n"
                f"Project Description: {project.description}\n"
                f"Investment Size: {project.currency} {project.investment_size:,.2f}\n"
                f"Current Readiness Score: {project.readiness_score}\n\n"
                f"Please conduct due diligence and update the project readiness assessment."
            ),
            owner_id=owner_id,
            due_date=datetime.now(UTC) + timedelta(days=14),
            status=ActionItemStatus.PENDING,
            priority=ActionItemPriority.HIGH
        )

        self.db.add(action_item)
        await self.db.flush()

        if requested_by_user_id:
            await audit_service.log_activity(
                db=self.db,
                user_id=requested_by_user_id,
                action="investment_vetting_requested",
                resource_type="action_item",
                resource_id=action_item.id,
                details={
                    "project_id": str(project_id),
                    "project_name": project.name,
                    "assigned_to_twg": rm_twg.name
                }
            )

        logger.info(
            f"✓ Vetting task created for project {project.name} -> "
            f"Resource Mobilization TWG (ActionItem: {action_item.id})"
        )

        return {
            "action_item": action_item,
            "status": "created",
            "assigned_to_twg": rm_twg.name
        }

    async def check_pipeline_health(self) -> Dict[str, Any]:
        """
        Identify stalled projects in the pipeline.

        Checks each project against stage-specific thresholds to detect
        projects that may need attention.

        Returns:
            Dict with:
                - stalled_projects: List of projects exceeding their stage threshold
                - healthy_projects: Count of projects within thresholds
                - by_stage: Breakdown by stage
        """
        result = await self.db.execute(select(Project))
        projects = result.scalars().all()

        stalled_projects = []
        healthy_count = 0
        by_stage: Dict[str, Dict[str, int]] = {}

        now = datetime.now(UTC)

        for project in projects:
            stage = project.status
            stage_key = stage.value

            if stage_key not in by_stage:
                by_stage[stage_key] = {"total": 0, "stalled": 0}
            by_stage[stage_key]["total"] += 1

            if stage == ProjectStatus.COMMITTED:
                healthy_count += 1
                continue

            last_change_str = (project.metadata_json or {}).get("last_stage_change")
            if last_change_str:
                try:
                    last_change = datetime.fromisoformat(last_change_str.replace('Z', '+00:00'))
                except (ValueError, AttributeError):
                    last_change = now
            else:
                last_change = now

            from app.services.lifecycle_service import LifecycleService
            threshold_days = LifecycleService.STAGE_DURATION_THRESHOLDS.get(stage, 30)
            days_in_stage = (now - last_change).days

            if days_in_stage > threshold_days:
                stalled_projects.append({
                    "project_id": str(project.id),
                    "name": project.name,
                    "stage": stage.value,
                    "days_in_stage": days_in_stage,
                    "threshold_days": threshold_days,
                    "overdue_by": days_in_stage - threshold_days
                })
                by_stage[stage_key]["stalled"] += 1
            else:
                healthy_count += 1

        logger.info(
            f"Pipeline health check: {healthy_count} healthy, "
            f"{len(stalled_projects)} stalled projects"
        )

        return {
            "stalled_projects": stalled_projects,
            "healthy_projects": healthy_count,
            "total_projects": len(projects),
            "by_stage": by_stage,
            "checked_at": datetime.now(UTC).isoformat()
        }

    async def get_project_stage_info(self, project_id: uuid.UUID) -> Dict[str, Any]:
        """
        Get information about a project's current stage and available transitions.

        Args:
            project_id: ID of the project

        Returns:
            Dict with current stage, history, and allowed transitions
        """
        result = await self.db.execute(
            select(Project).where(Project.id == project_id)
        )
        project = result.scalars().first()

        if not project:
            return {"error": "Project not found"}

        current_stage = project.status
        from app.services.lifecycle_service import LifecycleService
        allowed_transitions = LifecycleService.get_allowed_transitions(current_stage)

        return {
            "project_id": str(project.id),
            "name": project.name,
            "current_stage": current_stage.value,
            "allowed_transitions": allowed_transitions,
            "stage_history": (project.metadata_json or {}).get("stage_history", []),
            "last_stage_change": (project.metadata_json or {}).get("last_stage_change")
        }

    def calculate_afcen_score(
        self,
        readiness_score: float,
        strategic_alignment_score: float,
        regional_impact_score: Optional[float] = None
    ) -> Decimal:
        """
        Compute a preliminary AfCEN score (0-100) from 0-10 input fields.
        Used for initial estimates before document analysis runs.
        Full WAIIS scoring is done by assess_project_readiness().
        """
        r = max(0.0, min(10.0, float(readiness_score)))
        s = max(0.0, min(10.0, float(strategic_alignment_score)))
        i = max(0.0, min(10.0, float(regional_impact_score))) if regional_impact_score is not None else 5.0
        weighted = (r * 0.4) + (s * 0.3) + (i * 0.3)
        return Decimal(f"{weighted * 10:.2f}")

    async def ingest_project_proposal(
        self,
        data: Dict[str, Any],
        submitted_by_user_id: Optional[uuid.UUID] = None,
        start_in_incubation: bool = True,
    ) -> Dict[str, Any]:
        """
        Ingest a new project proposal and auto-calculate initial scores.
        
        Args:
            data: Project data dictionary
            submitted_by_user_id: User submitting the proposal
            
        Returns:
            Created Project object and status
        """
        # Calculate initial AfCEN score (Basic)
        readiness = data.get("readiness_score", 0.0)
        strategic_align = data.get("strategic_alignment_score", 0.0)
        
        afcen_score = self.calculate_afcen_score(
            readiness_score=readiness,
            strategic_alignment_score=strategic_align
        )
        
        # Determine initial status
        if data.get("status") and data["status"] not in ("identified", "DRAFT"):
            try:
                initial_status = ProjectStatus(data["status"])
            except ValueError:
                initial_status = ProjectStatus.INCUBATION if start_in_incubation else ProjectStatus.DRAFT
        elif start_in_incubation:
            initial_status = ProjectStatus.INCUBATION
        else:
            initial_status = ProjectStatus.DRAFT

        # Create Project
        project = Project(
            twg_id=uuid.UUID(data["twg_id"]),
            name=data["name"],
            description=data["description"],
            investment_size=data["investment_size"],
            currency=data.get("currency", "USD"),
            readiness_score=readiness,
            status=initial_status,
            pillar=data.get("pillar"),
            lead_country=data.get("lead_country"),
            afcen_score=afcen_score,
            strategic_alignment_score=Decimal(str(strategic_align)),
            assigned_agent=data.get("assigned_agent"),
            is_flagship=data.get("is_flagship", False),
            # Phase 1 classification fields
            value_chain_stages=data.get("value_chain_stages"),
            women_employment_pct=data.get("women_employment_pct"),
            youth_employment_pct=data.get("youth_employment_pct"),
            # R2 — Gender & Youth intentional design flags
            gender_intentional=data.get("gender_intentional"),
            gender_justification=data.get("gender_justification"),
            youth_focused=data.get("youth_focused"),
            youth_justification=data.get("youth_justification"),
            metadata_json={
                **(data.get("metadata_json") or {}), # Merge payload metadata
                "source": "ingestion_api",
                "submitted_at": datetime.now(UTC).isoformat(),
                "submitted_by": str(submitted_by_user_id) if submitted_by_user_id else None
            }
        )
        
        self.db.add(project)
        await self.db.flush()
        
        # Run detailed assessment after creation to populate score details
        detailed_afcen = await self.assess_project_readiness(project.id)
        
        # If detailed assessment yields a different score (likely 0 if no docs), 
        # do we overwrite the manual input?
        # For now, let's TRUST the manual input if provided, 
        # but `assess_project_readiness` updates the project in DB.
        # So we should re-fetch or use the result.
        # IMPORTANT: assess_project_readiness pulls from DB. logic above sets 0-10 check.
        # If no docs, assess_project_readiness returns 0.
        # We might want to keep the manual score as an 'override' or 'initial estimate'.
        # Let's keep the manual score for now if the automated one is 0.
        
        if detailed_afcen > 0:
            afcen_score = detailed_afcen
        
        if submitted_by_user_id:
            await audit_service.log_activity(
                db=self.db,
                user_id=submitted_by_user_id,
                action="project_ingested",
                resource_type="project",
                resource_id=project.id,
                details={
                    "name": project.name,
                    "afcen_score": str(afcen_score)
                }
            )
            
        await self.db.commit()
        await self.db.refresh(project)
        
        logger.info(f"✓ Project ingested: {project.name} (AfCEN Score: {afcen_score})")
        
        return {
            "project": project,
            "status": "created",
            "afcen_score": afcen_score
        }

    async def update_project(
        self,
        project_id: uuid.UUID,
        data: Dict[str, Any],
        updated_by_user_id: Optional[uuid.UUID] = None
    ) -> Dict[str, Any]:
        """
        Update project details.
        """
        result = await self.db.execute(select(Project).where(Project.id == project_id))
        project = result.scalars().first()
        
        if not project:
            return {"error": "Project not found"}
            
        # Apply all updatable scalar fields
        _UPDATABLE = {
            "name", "description", "investment_size", "currency", "pillar",
            "lead_country", "assigned_agent", "is_flagship",
            # Section A
            "subsector", "project_sponsor", "is_cross_border",
            "key_contact_name", "key_contact_email", "submitted_by",
            # Section B
            "technical_studies", "permits_licences", "land_status",
            # Section C
            "financing_structure", "investment_stage_label", "revenue_model", "macroeconomic_roi",
            # Section D
            "climate_impact", "esg_compliance", "ghg_avoided_target",
            "jobs_construction", "jobs_om", "electricity_connections",
            "digital_connections", "smallholder_farmers_reached",
            # Phase 1 classification fields
            "value_chain_stages", "women_employment_pct", "youth_employment_pct",
            # R2 — Gender & Youth intentional design flags
            "gender_intentional", "gender_justification", "youth_focused", "youth_justification",
            # R8 — Site coordinates for geospatial analysis
            "site_lat", "site_lon", "site_location_name",
        }
        for field in _UPDATABLE:
            if field in data and data[field] is not None:
                setattr(project, field, data[field])

        # Merge metadata
        if data.get("metadata_json"):
            current_meta = project.metadata_json or {}
            project.metadata_json = {**current_meta, **data["metadata_json"]}
            
        if updated_by_user_id:
            project.updated_by = updated_by_user_id

        # Invalidate readiness gap cache when project is updated
        if project.metadata_json and "readiness_gap_report" in project.metadata_json:
            meta = dict(project.metadata_json)
            del meta["readiness_gap_report"]
            project.metadata_json = meta

        await self.db.commit()
        await self.db.refresh(project)
        
        # AUTOMATIC SCORING: Retrigger scoring after project update
        try:
            from app.services.scoring_tasks import rescore_project_async
            
            # Trigger background scoring via Celery
            rescore_project_async.delay(str(project_id))
            
            logger.info(f"✓ Triggered AfCEN rescoring for project {project_id} after update")
        except Exception as e:
            logger.warning(f"Could not trigger automatic scoring: {e}")
        
        return {"project": project, "status": "updated"}
