"""
AI-Powered Project Insights Service

Generates contextual recommendations for investment projects using LLM analysis.
"""

from typing import Dict, List, Optional
from datetime import datetime, timezone
UTC = timezone.utc
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.models import Project, ProjectStatus
from app.services.llm_service import llm_service


class ProjectInsightsService:
    """Generate AI-powered insights and recommendations for projects"""
    
    @staticmethod
    async def generate_project_insights(
        project: Project,
        db: AsyncSession
    ) -> Dict[str, str]:
        """
        Generate AI-powered insights for a project.
        
        Returns:
            Dict with 'insight' and 'recommendation' keys
        """
        try:
            # Calculate days since project creation as a proxy for stage duration
            days_since_creation = 0
            created_at = getattr(project, 'created_at', None)
            
            if created_at:
                # Handle both offset-naive and offset-aware datetimes
                if created_at.tzinfo is None:
                    created_at = created_at.replace(tzinfo=UTC)
                days_since_creation = (datetime.now(UTC) - created_at).days
            
            # Build context for LLM
            context = f"""
Project Analysis Request:

Title: {project.name}
Status: {project.status}
AfCEN Score: {project.afcen_score or 'Not scored'}/100
Readiness Score: {project.readiness_score or 'Not assessed'}/100
Investment Size: ${project.investment_size:,.0f} USD
Sector: {project.pillar}
Days since creation: {days_since_creation}

Provide:
1. A brief insight (1 sentence) about the project's current state
2. One specific, actionable recommendation for the next step
"""

            system_prompt = """You are an expert investment pipeline advisor for the ECOWAS Commission. 
Provide concise, actionable insights for infrastructure and development projects.
Focus on practical next steps that move projects forward."""

            # Call LLM
            response = llm_service.chat(
                prompt=context,
                system_prompt=system_prompt,
                temperature=0.7,
                max_tokens=200
            )
            
            # Parse response (simple split on newlines)
            lines = [line.strip() for line in response.split('\n') if line.strip()]
            
            insight = lines[0] if len(lines) > 0 else "Project analysis in progress."
            recommendation = lines[1] if len(lines) > 1 else "Review project documentation and update scores."
            
            # Clean up formatting
            insight = insight.replace('1.', '').replace('Insight:', '').strip()
            recommendation = recommendation.replace('2.', '').replace('Recommendation:', '').strip()
            
            logger.info(f"Generated AI insights for project {project.id}")
            
            return {
                "insight": insight,
                "recommendation": recommendation
            }
            
        except Exception as e:
            logger.error(f"Error generating project insights: {e}")
            # Fallback to rule-based insights
            return ProjectInsightsService._fallback_insights(project, days_since_creation)
    
    @staticmethod
    def _fallback_insights(project: Project, days_in_stage: int) -> Dict[str, str]:
        """Fallback rule-based insights if LLM fails"""
        
        # Rule-based insight
        if project.afcen_score and project.afcen_score >= 80:
            insight = f"Strong AfCEN score of {project.afcen_score}/100 indicates excellent alignment with regional priorities."
        elif project.afcen_score and project.afcen_score >= 60:
            insight = f"Moderate AfCEN score of {project.afcen_score}/100 suggests room for improvement in project documentation."
        else:
            insight = f"AfCEN score needs attention to improve project competitiveness."
        
        # Rule-based recommendation
        if project.status == ProjectStatus.DRAFT:
            recommendation = "Complete project documentation and submit for early studies."
        elif project.status == ProjectStatus.PIPELINE:
            recommendation = "Progress pre-feasibility work and advance to full review stage."
        elif project.status == ProjectStatus.UNDER_REVIEW:
            if days_in_stage > 30:
                recommendation = f"Project has been under review for {days_in_stage} days. Follow up with TWG lead for status update."
            else:
                recommendation = "Await TWG technical review feedback."
        elif project.status == ProjectStatus.NEEDS_REVISION:
            recommendation = "Address reviewer feedback and resubmit for evaluation."
        elif project.status == ProjectStatus.SUMMIT_READY:
            recommendation = "Prepare pitch deck and schedule presentation for upcoming summit."
        elif project.status == ProjectStatus.DEAL_ROOM_FEATURED:
            recommendation = "Review pending investor matches and schedule introductory meetings."
        else:
            recommendation = "Continue monitoring project progress and update documentation as needed."
        
        return {
            "insight": insight,
            "recommendation": recommendation
        }


# Singleton instance
insights_service = ProjectInsightsService()
