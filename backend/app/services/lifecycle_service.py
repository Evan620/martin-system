from datetime import datetime
from uuid import UUID
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException

from app.models.models import Project, ProjectStatus, ProjectStatusHistory, User, UserRole

class LifecycleService:
    """
    Manages the Deal Pipeline Lifecycle logic, enforcing transition rules
    and recording status history.
    """

    ALLOWED_TRANSITIONS = {
        (ProjectStatus.CONCEPT, ProjectStatus.PRE_FEASIBILITY): {
            "roles": [UserRole.TWG_FACILITATOR, UserRole.ADMIN, UserRole.SECRETARIAT_LEAD],
            "description": "Submit for early studies"
        },
        (ProjectStatus.PRE_FEASIBILITY, ProjectStatus.FEASIBILITY): {
            "roles": [UserRole.TWG_FACILITATOR, UserRole.ADMIN, UserRole.SECRETARIAT_LEAD],
            "description": "Advance to feasibility stage"
        },
        (ProjectStatus.FEASIBILITY, ProjectStatus.DECLINED): {
            "roles": [UserRole.ADMIN, UserRole.SECRETARIAT_LEAD],
            "description": "Decline project"
        },
        (ProjectStatus.FEASIBILITY, ProjectStatus.NEEDS_REVISION): {
            "roles": [UserRole.ADMIN, UserRole.SECRETARIAT_LEAD],
            "description": "Request revision"
        },
        (ProjectStatus.FEASIBILITY, ProjectStatus.BANKABLE): {
            "roles": [UserRole.TWG_FACILITATOR, UserRole.ADMIN, UserRole.SECRETARIAT_LEAD],
            "description": "Mark as bankable / investment-ready"
        },
        (ProjectStatus.NEEDS_REVISION, ProjectStatus.FEASIBILITY): {
            "roles": [UserRole.TWG_FACILITATOR, UserRole.ADMIN, UserRole.SECRETARIAT_LEAD],
            "description": "Resubmit after revision"
        },
        (ProjectStatus.BANKABLE, ProjectStatus.SUMMIT_FEATURED): {
            "roles": [UserRole.ADMIN, UserRole.SECRETARIAT_LEAD],
            "description": "Select for summit"
        },
        (ProjectStatus.SUMMIT_FEATURED, ProjectStatus.IN_NEGOTIATION): {
            "roles": [UserRole.ADMIN, UserRole.SECRETARIAT_LEAD],
            "description": "Investor engaged"
        },
        (ProjectStatus.IN_NEGOTIATION, ProjectStatus.COMMITTED): {
            "roles": [UserRole.ADMIN, UserRole.SECRETARIAT_LEAD],
            "description": "Deal committed"
        },
    }

    # Keep TRANSITION_RULES as an alias so existing callers don't break
    TRANSITION_RULES = ALLOWED_TRANSITIONS

    STAGE_DURATION_THRESHOLDS = {
        ProjectStatus.CONCEPT: 14,
        ProjectStatus.PRE_FEASIBILITY: 30,
        ProjectStatus.FEASIBILITY: 30,
        ProjectStatus.BANKABLE: 30,
        ProjectStatus.SUMMIT_FEATURED: 30,
        ProjectStatus.IN_NEGOTIATION: 60,
        ProjectStatus.COMMITTED: 90,
    }

    @staticmethod
    def get_allowed_transitions(current_status: ProjectStatus, role: Optional[UserRole] = None) -> List[str]:
        """
        Get list of allowed next statuses.
        """
        allowed = []
        for (src, dst), rule in LifecycleService.ALLOWED_TRANSITIONS.items():
            if src == current_status:
                roles_key = rule.get("roles") or rule.get("allowed_roles", [])
                if role:
                    if role in roles_key or role == UserRole.ADMIN:
                        allowed.append(dst.value)
                else:
                    # If no role specified, return all possible
                    allowed.append(dst.value)

        # Add generics if appropriate (simplification)
        return allowed


    @staticmethod
    async def transition_project_status(
        db: AsyncSession,
        project_id: UUID,
        new_status: ProjectStatus,
        changed_by_user: User,
        reason: Optional[str] = None,
        notes: Optional[str] = None,
        is_automated: bool = False
    ) -> Project:
        """
        Transitions a project to a new status if rules are met.
        """
        result = await db.execute(select(Project).where(Project.id == project_id))
        project = result.scalars().first()
        
        if not project:
             raise HTTPException(status_code=404, detail="Project not found")

        current_status = project.status
        
        # 1. Check if change is actual
        if current_status == new_status:
            return project

        # 2. Check Transition Rules
        rule = LifecycleService.ALLOWED_TRANSITIONS.get((current_status, new_status))

        if not rule:
            # Check for generic "Archived" or "On Hold"
            if new_status in [ProjectStatus.ARCHIVED, ProjectStatus.ON_HOLD]:
                if changed_by_user.role not in [UserRole.ADMIN, UserRole.SECRETARIAT_LEAD]:
                     raise HTTPException(status_code=403, detail="Insufficient permissions to archive/hold project")
            elif changed_by_user.role != UserRole.ADMIN:
                 raise HTTPException(status_code=400, detail=f"Invalid status transition from {current_status} to {new_status}")
        else:
            roles_key = rule.get("roles") or rule.get("allowed_roles", [])
            if changed_by_user.role not in roles_key and changed_by_user.role != UserRole.ADMIN:
                 raise HTTPException(status_code=403, detail="Insufficient permissions for this status change")

            if "min_score" in rule:
                min_score = rule["min_score"]
                current_score = project.afcen_score or 0
                if current_score < min_score:
                     raise HTTPException(status_code=400, detail=f"Project score {current_score} is below minimum {min_score} required for {new_status}")

        # 3. Apply Change
        project.status = new_status
        
        # 4. Record History
        history = ProjectStatusHistory(
            project_id=project.id,
            previous_status=current_status,
            new_status=new_status,
            changed_by_id=changed_by_user.id,
            change_date=datetime.utcnow(),
            reason=reason,
            notes=notes,
            is_automated=is_automated
        )
        db.add(history)
        await db.commit()
        await db.refresh(project)
        
        return project

    @staticmethod
    def get_available_transitions(current_status: ProjectStatus, user_role: UserRole) -> List[ProjectStatus]:
        """
        Returns list of allowed status transitions for a user.
        """
        allowed = []
        for (from_s, to_s), rule in LifecycleService.ALLOWED_TRANSITIONS.items():
            if from_s == current_status:
                roles_key = rule.get("roles") or rule.get("allowed_roles", [])
                if user_role in roles_key or user_role == UserRole.ADMIN:
                    allowed.append(to_s)
        
        # Add generic transitions allowed for admins/leads
        if user_role in [UserRole.ADMIN, UserRole.SECRETARIAT_LEAD]:
            if ProjectStatus.ARCHIVED not in allowed and current_status != ProjectStatus.ARCHIVED:
                allowed.append(ProjectStatus.ARCHIVED)
            if ProjectStatus.ON_HOLD not in allowed and current_status != ProjectStatus.ON_HOLD:
                allowed.append(ProjectStatus.ON_HOLD)
                
        return allowed
