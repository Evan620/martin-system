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
        (ProjectStatus.INCUBATION, ProjectStatus.DRAFT): {
            "roles": [UserRole.TWG_FACILITATOR, UserRole.ADMIN, UserRole.SECRETARIAT_LEAD],
            "description": "Graduate from Incubation to Draft",
            "uses_graduation_threshold": True,
        },
        (ProjectStatus.DRAFT, ProjectStatus.PIPELINE): {
            "roles": [UserRole.TWG_FACILITATOR, UserRole.ADMIN, UserRole.SECRETARIAT_LEAD],
            "description": "Submit for early studies"
        },
        (ProjectStatus.PIPELINE, ProjectStatus.UNDER_REVIEW): {
            "roles": [UserRole.TWG_FACILITATOR, UserRole.ADMIN, UserRole.SECRETARIAT_LEAD],
            "description": "Advance to feasibility stage"
        },
        (ProjectStatus.UNDER_REVIEW, ProjectStatus.DECLINED): {
            "roles": [UserRole.ADMIN, UserRole.SECRETARIAT_LEAD],
            "description": "Decline project"
        },
        (ProjectStatus.UNDER_REVIEW, ProjectStatus.NEEDS_REVISION): {
            "roles": [UserRole.ADMIN, UserRole.SECRETARIAT_LEAD],
            "description": "Request revision"
        },
        (ProjectStatus.UNDER_REVIEW, ProjectStatus.SUMMIT_READY): {
            "roles": [UserRole.TWG_FACILITATOR, UserRole.ADMIN, UserRole.SECRETARIAT_LEAD],
            "description": "Mark as summit-ready / investment-ready"
        },
        (ProjectStatus.NEEDS_REVISION, ProjectStatus.UNDER_REVIEW): {
            "roles": [UserRole.TWG_FACILITATOR, UserRole.ADMIN, UserRole.SECRETARIAT_LEAD],
            "description": "Resubmit after revision"
        },
        (ProjectStatus.SUMMIT_READY, ProjectStatus.DEAL_ROOM_FEATURED): {
            "roles": [UserRole.ADMIN, UserRole.SECRETARIAT_LEAD],
            "description": "Select for summit"
        },
        (ProjectStatus.DEAL_ROOM_FEATURED, ProjectStatus.IN_NEGOTIATION): {
            "roles": [UserRole.ADMIN, UserRole.SECRETARIAT_LEAD],
            "description": "Investor engaged"
        },
        (ProjectStatus.IN_NEGOTIATION, ProjectStatus.COMMITTED): {
            "roles": [UserRole.ADMIN, UserRole.SECRETARIAT_LEAD],
            "description": "Deal committed"
        },
        (ProjectStatus.COMMITTED, ProjectStatus.IMPLEMENTED): {
            "roles": [UserRole.ADMIN, UserRole.SECRETARIAT_LEAD],
            "description": "Deal implemented"
        },
    }

    # Keep TRANSITION_RULES as an alias so existing callers don't break
    TRANSITION_RULES = ALLOWED_TRANSITIONS

    STAGE_DURATION_THRESHOLDS = {
        ProjectStatus.INCUBATION: 90,
        ProjectStatus.DRAFT: 14,
        ProjectStatus.PIPELINE: 30,
        ProjectStatus.UNDER_REVIEW: 30,
        ProjectStatus.SUMMIT_READY: 30,
        ProjectStatus.DEAL_ROOM_FEATURED: 30,
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
            if new_status in [ProjectStatus.ON_HOLD]:
                if changed_by_user.role not in [UserRole.ADMIN, UserRole.SECRETARIAT_LEAD]:
                     raise HTTPException(status_code=403, detail="Insufficient permissions to hold project")
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

            if rule.get("uses_graduation_threshold"):
                from app.models.models import PlatformSetting
                thresh_res = await db.execute(
                    select(PlatformSetting).where(PlatformSetting.key == "incubation_graduation_threshold")
                )
                thresh_setting = thresh_res.scalars().first()
                threshold = float(thresh_setting.value) if thresh_setting else 40.0
                current_score = float(project.afcen_score or 0)
                if current_score < threshold:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Project score {current_score:.1f} is below graduation threshold {threshold:.0f}. "
                               f"Need {threshold - current_score:.1f} more points."
                    )

            # Gender/youth gate: UNDER_REVIEW → SUMMIT_READY requires fields filled and above threshold
            if current_status == ProjectStatus.UNDER_REVIEW and new_status == ProjectStatus.SUMMIT_READY:
                GENDER_THRESHOLD = 30.0
                YOUTH_THRESHOLD = 25.0

                women_pct = project.women_employment_pct
                youth_pct = project.youth_employment_pct

                if women_pct is None:
                    raise HTTPException(
                        status_code=400,
                        detail="Cannot advance to Summit Ready: women employment % is required (field: women_employment_pct)"
                    )
                if youth_pct is None:
                    raise HTTPException(
                        status_code=400,
                        detail="Cannot advance to Summit Ready: youth employment % is required (field: youth_employment_pct)"
                    )
                if women_pct < GENDER_THRESHOLD:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Cannot advance to Summit Ready: women employment {women_pct:.0f}% is below required 30%"
                    )
                if youth_pct < YOUTH_THRESHOLD:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Cannot advance to Summit Ready: youth employment {youth_pct:.0f}% is below required 25%"
                    )

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
            if ProjectStatus.ON_HOLD not in allowed and current_status != ProjectStatus.ON_HOLD:
                allowed.append(ProjectStatus.ON_HOLD)
                
        return allowed
