from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.models import Buyer, BuyerMatchStatus, Project, ProjectBuyerMatch


class BuyerMatchingService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def match_buyers(self, project_id: uuid.UUID) -> Dict[str, Any]:
        """Run matching algorithm for a project against all active buyers."""
        result = await self.db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        if not project:
            return {"error": "Project not found"}

        buyers_result = await self.db.execute(
            select(Buyer).where(Buyer.deleted_at.is_(None))
        )
        buyers = buyers_result.scalars().all()

        new_matches = 0
        updated_matches = 0

        for buyer in buyers:
            score, rationale = self._calculate_match_score(project, buyer)
            if score >= 50:
                outcome = await self._upsert_match(project, buyer, score, rationale)
                if outcome == "created":
                    new_matches += 1
                elif outcome == "updated":
                    updated_matches += 1

        await self.db.commit()
        return {
            "project_id": str(project_id),
            "new_matches": new_matches,
            "updated_matches": updated_matches,
            "total_buyers_scanned": len(buyers),
        }

    def _calculate_match_score(self, project: Project, buyer: Buyer) -> tuple[int, str]:
        """Score a project-buyer pair. Returns (score 0-100, rationale string)."""
        score = 0
        reasons: List[str] = []

        # +40: commodity type overlaps with project value_chain_stages
        project_stages = {s.upper() for s in (project.value_chain_stages or [])}
        buyer_commodities = {c.upper() for c in (buyer.commodity_types or [])}
        if project_stages & buyer_commodities:
            score += 40
            overlap = ", ".join(project_stages & buyer_commodities)
            reasons.append(f"Commodity match: {overlap}")

        # +25: buyer volume fits project (proxy: project investment >= $10M)
        if buyer.volume_mt_per_year is None or (
            project.investment_size and float(project.investment_size) >= 10_000_000
        ):
            score += 25
            reasons.append("Production capacity can meet buyer volume")

        # +20: buyer geographic focus includes project lead_country
        buyer_geo = {g.upper() for g in (buyer.geographic_focus or [])}
        if project.lead_country and (
            project.lead_country.upper() in buyer_geo
            or "ECOWAS" in buyer_geo
            or "WEST AFRICA" in buyer_geo
        ):
            score += 20
            reasons.append(f"Geographic match: {project.lead_country}")

        # +15: ECOWAS cross-border signal (buyer has ECOWAS focus)
        if "ECOWAS" in buyer_geo and project.lead_country:
            score += 15
            reasons.append("ECOWAS regional alignment")

        rationale = " · ".join(reasons) if reasons else "No specific match signals"
        return min(score, 100), rationale

    async def _upsert_match(
        self,
        project: Project,
        buyer: Buyer,
        score: int,
        rationale: str,
    ) -> str:
        result = await self.db.execute(
            select(ProjectBuyerMatch).where(
                ProjectBuyerMatch.project_id == project.id,
                ProjectBuyerMatch.buyer_id == buyer.id,
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            if existing.match_score != score:
                existing.match_score = score
                existing.match_rationale = rationale
                return "updated"
            return "skipped"

        self.db.add(ProjectBuyerMatch(
            project_id=project.id,
            buyer_id=buyer.id,
            match_score=score,
            status=BuyerMatchStatus.DETECTED,
            match_rationale=rationale,
        ))
        return "created"

    async def get_matches_for_project(self, project_id: uuid.UUID) -> List[Dict[str, Any]]:
        result = await self.db.execute(
            select(ProjectBuyerMatch)
            .where(ProjectBuyerMatch.project_id == project_id)
            .options(selectinload(ProjectBuyerMatch.buyer))
            .order_by(ProjectBuyerMatch.match_score.desc())
        )
        matches = result.scalars().all()
        return [
            {
                "match_id": str(m.id),
                "buyer": m.buyer,
                "score": m.match_score,
                "status": m.status.value,
                "match_rationale": m.match_rationale,
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
            select(ProjectBuyerMatch)
            .where(ProjectBuyerMatch.id == match_id)
            .options(selectinload(ProjectBuyerMatch.buyer))
        )
        match = result.scalar_one_or_none()
        if not match:
            return {"error": "Match not found"}

        match.status = BuyerMatchStatus(new_status.upper())
        if notes is not None:
            match.match_rationale = notes
        await self.db.commit()
        return {"match_id": str(match.id), "status": match.status.value}


def get_buyer_matching_service(db: AsyncSession) -> BuyerMatchingService:
    return BuyerMatchingService(db)
