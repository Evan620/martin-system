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
        """Score project against all active DFI windows and upsert matches >= 40."""
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
        project_sectors: set = set()
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
