"""
Investor Matching Service

Matches projects with potential investors based on:
1. Sector alignment (Project Pillar vs Investor Preferences)
2. Ticket size (Project Investment Size within Investor Range)
3. Geographic focus (Project Lead Country within Investor Focus)
"""

from typing import List, Dict, Any, Optional
from decimal import Decimal
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
import uuid
from datetime import datetime, timezone
UTC = timezone.utc

from app.models.models import (
    Project, Investor, ProjectInvestorMatch, 
    InvestorMatchStatus, TWGPillar, TWG, ActionItem, ActionItemStatus, ActionItemPriority
)
from app.services.audit_service import audit_service


class InvestorMatchingService:
    """
    Service for matching projects with investors.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db

    async def match_investors(
        self, 
        project_id: uuid.UUID
    ) -> Dict[str, Any]:
        """
        Run matching algorithm for a specific project.
        
        Args:
            project_id: ID of the project to match
            
        Returns:
            Summary of matches found and created
        """
        # 1. Get Project
        result = await self.db.execute(select(Project).where(Project.id == project_id))
        project = result.scalars().first()
        
        if not project:
            return {"error": "Project not found"}
            
        # 2. Get All Investors
        result = await self.db.execute(select(Investor))
        investors = result.scalars().all()
        
        new_matches = 0
        updated_matches = 0
        
        for investor in investors:
            score = self._calculate_match_score(project, investor)
            
            if score > 0:
                # Check implementation of upsert logic
                match_result = await self._upsert_match(project, investor, score)
                if match_result == "created":
                    new_matches += 1
                elif match_result == "updated":
                    updated_matches += 1
                    
        await self.db.commit()
        
        logger.info(f"Matching run for {project.name}: {new_matches} new, {updated_matches} updated")
        
        return {
            "project_id": str(project.id),
            "new_matches": new_matches,
            "updated_matches": updated_matches,
            "total_investors_scanned": len(investors)
        }
        
    def _calculate_match_score(self, project: Project, investor: Investor) -> Decimal:
        """
        Calculate match score (0-100) based on criteria.
        
        Scoring Breakdown:
        - Sector Match: 30 pts
        - Ticket Size: 30 pts  
        - Geography: 15 pts
        - Investment Instrument: 15 pts
        - AfCEN Score (Readiness): 20 pts
        - Commitment Capability: +5 pts bonus
        """
        # Minimum threshold: Only match projects with AfCEN score >= 40
        if project.afcen_score and float(project.afcen_score) < 40:
            return Decimal("0.0")
        
        score = 0.0
        
        # Criterion 1: Sector Match (30 pts)
        # Assuming project.pillar (string) matches one of the investor.sector_preferences (list)
        project_sector = project.pillar
        investor_sectors = investor.sector_preferences or []
        
        # Normalize for comparison
        if project_sector and any(s.lower() in project_sector.lower() for s in investor_sectors):
            score += 30.0
        elif not project_sector:
            # If project has no sector yet, partial credit? No, strict matching.
            pass
            
        # Criterion 2: Ticket Size Match (30 pts)
        inv_size = float(project.investment_size)
        min_size = float(investor.ticket_size_min or 0)
        max_size = float(investor.ticket_size_max or float('inf'))
        
        if min_size <= inv_size <= max_size:
            score += 30.0
        elif inv_size < min_size:
            # Too small - partial credit if close?
            if inv_size >= min_size * 0.8:
                score += 15.0
        elif inv_size > max_size:
            # Too large - partial credit if close?
            if inv_size <= max_size * 1.2:
                score += 15.0
                
        # Criterion 3: Geography Match (15 pts)
        project_country = project.lead_country
        investor_regions = investor.geographic_focus or []
        
        if project_country and any(r.lower() in project_country.lower() or project_country.lower() in r.lower() for r in investor_regions):
            score += 15.0
            
        # Criterion 4: Investment Instrument (15 pts)
        # Check metadata for instrument_needed (e.g. "Equity", "Debt")
        project_instruments = (project.metadata_json or {}).get("instrument_needed", [])
        if isinstance(project_instruments, str):
            project_instruments = [project_instruments]
            
        investor_instruments = investor.investment_instruments or []
        
        if project_instruments and investor_instruments:
             if any(i.lower() in [pi.lower() for pi in project_instruments] for i in investor_instruments):
                 score += 15.0
        elif not project_instruments:
             # Neutral if undefined
             score += 7.5
        
        # Criterion 5: AfCEN Score / Project Readiness (20 pts)
        # Higher AfCEN score = more attractive to investors
        if project.afcen_score:
            afcen = float(project.afcen_score)
            if afcen >= 70:
                score += 20.0  # Highly ready
            elif afcen >= 60:
                score += 15.0  # Ready
            elif afcen >= 50:
                score += 10.0  # Moderately ready
            elif afcen >= 40:
                score += 5.0   # Minimum threshold
             
        # Boost: High Commitment Capability (+5 max)
        if investor.total_commitments_usd and investor.total_commitments_usd > 100000000: # >100M
            score += 5.0
            
        return Decimal(f"{min(100.0, score):.2f}")
        
    async def _upsert_match(
        self, 
        project: Project, 
        investor: Investor, 
        score: Decimal
    ) -> str:
        """
        Create or update a match record.
        """
        # Check existing match
        result = await self.db.execute(
            select(ProjectInvestorMatch).where(
                and_(
                    ProjectInvestorMatch.project_id == project.id,
                    ProjectInvestorMatch.investor_id == investor.id
                )
            )
        )
        existing_match = result.scalars().first()
        
        if existing_match:
            # Update score if changed significantly
            if existing_match.match_score != score:
                existing_match.match_score = score
                # Don't reset status if already progressing
                return "updated"
            return "skipped"
        else:
            # Create new match
            new_match = ProjectInvestorMatch(
                project_id=project.id,
                investor_id=investor.id,
                match_score=score,
                status=InvestorMatchStatus.DETECTED,
                notes=f"Auto-matched with score {score}"
            )
            self.db.add(new_match)
            return "created"

    async def get_matches_for_project(
        self, 
        project_id: uuid.UUID
    ) -> List[Dict[str, Any]]:
        """
        Get all matches for a project, sorted by score.
        """
        result = await self.db.execute(
            select(ProjectInvestorMatch, Investor)
            .join(Investor, ProjectInvestorMatch.investor_id == Investor.id)
            .where(ProjectInvestorMatch.project_id == project_id)
            .order_by(ProjectInvestorMatch.match_score.desc())
        )
        
        matches = []
        for match, investor in result:
            matches.append({
                "match_id": str(match.id),
                "investor": investor,  # Pass the full SQLAlchmey object
                "score": float(match.match_score or 0),
                "status": match.status.value,
                "notes": match.notes
            })
            
        return matches

    async def update_match_status(
        self,
        match_id: uuid.UUID,
        new_status: InvestorMatchStatus,
        notes: Optional[str] = None,
        updated_by_user_id: Optional[uuid.UUID] = None
    ) -> Dict[str, Any]:
        """
        Update the status of an investor match and trigger workflows.
        
        Triggers:
        - If status -> INTERESTED: Create Protocol Agent task for scheduling.
        """
        result = await self.db.execute(
            select(ProjectInvestorMatch).where(ProjectInvestorMatch.id == match_id)
        )
        match = result.scalars().first()
        
        if not match:
            return {"error": "Match not found"}
            
        old_status = match.status
        match.status = new_status
        if notes:
            match.notes = (match.notes or "") + f"\n[{datetime.now(UTC).isoformat()}] {notes}"
            
        # Trigger Protocol Agent logic
        action_item = None
        if new_status == InvestorMatchStatus.INTERESTED and old_status != InvestorMatchStatus.INTERESTED:
            action_item = await self._create_protocol_task(match)
            
        await self.db.commit()
        await self.db.refresh(match)
        
        if updated_by_user_id:
             await audit_service.log_activity(
                db=self.db,
                user_id=updated_by_user_id,
                action="investor_match_updated",
                resource_type="project_investor_match",
                resource_id=match.id,
                details={
                    "old_status": old_status.value,
                    "new_status": new_status.value,
                    "protocol_task_created": bool(action_item)
                }
            )
            
        return {
            "match": match,
            "status": "updated",
            "protocol_task_id": str(action_item.id) if action_item else None
        }

    async def _create_protocol_task(self, match: ProjectInvestorMatch) -> Optional[ActionItem]:
        """
        Create a task for the Protocol TWG to schedule a meeting.
        """
        # Get Project and Investor details
        project_result = await self.db.execute(select(Project).where(Project.id == match.project_id))
        project = project_result.scalars().first()
        
        investor_result = await self.db.execute(select(Investor).where(Investor.id == match.investor_id))
        investor = investor_result.scalars().first()
        
        # Get Protocol TWG
        twg_result = await self.db.execute(
            select(TWG).where(TWG.pillar == TWGPillar.protocol_logistics)
        )
        protocol_twg = twg_result.scalars().first()
        
        if not protocol_twg:
            logger.warning("Protocol & Logistics TWG not found, cannot create task")
            return None
            
        owner_id = protocol_twg.technical_lead_id or protocol_twg.political_lead_id
        if not owner_id:
            logger.warning("Protocol TWG has no lead assigned")
            return None
            
        # Create Action Item
        description = (
            f"Schedule Investor Meeting: {investor.name} for {project.name}\n\n"
            f"Investor {investor.name} has expressed interest in {project.name}.\n"
            f"Please coordinate with the investor's team to schedule an initial discussion.\n"
            f"Match Score: {match.match_score}"
        )
        
        action_item = ActionItem(
            twg_id=protocol_twg.id,
            description=description,
            owner_id=owner_id,
            status=ActionItemStatus.PENDING,
            priority=ActionItemPriority.HIGH,
            due_date=datetime.now(UTC) # Due immediately/soon
        )
        
        self.db.add(action_item)
        await self.db.flush() 
        
        logger.info(f"Created Protocol task {action_item.id} for match {match.id}")
        return action_item

def get_investor_matching_service(db: AsyncSession) -> InvestorMatchingService:
    return InvestorMatchingService(db)
