"""Read-only pipeline tools — no confirm protocol, just return data."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from sqlalchemy import and_, func, select

from app.core.database import AsyncSessionLocal
from app.models.models import (
    ActionItem, Meeting, Project, ProjectStatus,
)
from app.models.models import UserRole


# Threshold below which an Incubation project counts as "close to graduation".
_NEAR_GRAD_GAP = 5


async def pipeline_summary(
    user_id: str,
    user_role: UserRole,
    scope: str = "all",        # "all" | "twg" | "mine"
    period: str = "week",      # "week" | "month"
    twg_id: Optional[str] = None,
) -> dict:
    """Counts by stage + total investment + period delta. Scope 'twg' / 'mine'
    requires twg_id (caller's TWG) — enforced upstream by the dispatcher."""
    if scope not in {"all", "twg", "mine"}:
        return {"status": "invalid_input", "reason": "scope must be all/twg/mine"}
    if period not in {"week", "month"}:
        return {"status": "invalid_input", "reason": "period must be week/month"}

    window_days = 7 if period == "week" else 30
    since = datetime.utcnow() - timedelta(days=window_days)

    async with AsyncSessionLocal() as db:
        q = select(Project.status, func.count(Project.id), func.coalesce(func.sum(Project.investment_size), 0))
        if scope in {"twg", "mine"} and twg_id:
            q = q.where(Project.twg_id == UUID(twg_id))
        rows = (await db.execute(q.group_by(Project.status))).all()

        # Period delta = projects whose updated_at fell into the window.
        delta_q = select(func.count(Project.id)).where(Project.updated_at >= since)
        if scope in {"twg", "mine"} and twg_id:
            delta_q = delta_q.where(Project.twg_id == UUID(twg_id))
        moved = (await db.execute(delta_q)).scalar_one()

    by_stage = [
        {
            "stage": (s.value if hasattr(s, "value") else str(s)),
            "count": int(c),
            "value": float(v),
        }
        for s, c, v in rows
    ]
    total = sum(item["count"] for item in by_stage)
    total_value = sum(item["value"] for item in by_stage)
    return {
        "status": "ok",
        "scope": scope,
        "period": period,
        "total_projects": total,
        "total_investment": total_value,
        "by_stage": by_stage,
        "moved_in_window": int(moved),
    }


async def at_risk_projects(
    user_id: str,
    user_role: UserRole,
    twg_id: Optional[str] = None,
) -> dict:
    """Projects pending AI review > 3d OR missing gender/youth signals."""
    cutoff = datetime.utcnow() - timedelta(days=3)
    async with AsyncSessionLocal() as db:
        q = select(Project).where(
            (Project.afcen_score.is_(None) & (Project.created_at < cutoff))
            | (Project.gender_intentional.is_(None))
            | (Project.youth_focused.is_(None))
        )
        if twg_id:
            q = q.where(Project.twg_id == UUID(twg_id))
        rows = (await db.execute(q.limit(50))).scalars().all()
    projects = [
        {
            "id": str(p.id),
            "name": p.name,
            "stage": p.status.value if p.status else None,
            "investment": float(p.investment_size or 0),
            "missing_afcen": p.afcen_score is None,
            "missing_gender_signal": p.gender_intentional is None,
            "missing_youth_signal": p.youth_focused is None,
        }
        for p in rows
    ]
    return {"status": "ok", "count": len(projects), "projects": projects}


async def incubation_close_to_graduation(
    user_id: str,
    user_role: UserRole,
    twg_id: Optional[str] = None,
) -> dict:
    """Incubation projects with AfCEN within _NEAR_GRAD_GAP of the threshold (default 40)."""
    threshold = 40  # default graduation threshold; the UI also allows overrides
    async with AsyncSessionLocal() as db:
        q = select(Project).where(
            Project.status == ProjectStatus.INCUBATION,
            Project.afcen_score.is_not(None),
            Project.afcen_score >= (threshold - _NEAR_GRAD_GAP),
        )
        if twg_id:
            q = q.where(Project.twg_id == UUID(twg_id))
        rows = (await db.execute(q.limit(50))).scalars().all()
    return {
        "status": "ok",
        "threshold": threshold,
        "count": len(rows),
        "projects": [
            {
                "id": str(p.id),
                "name": p.name,
                "afcen_score": float(p.afcen_score or 0),
                "gap_to_graduation": threshold - float(p.afcen_score or 0),
            }
            for p in rows
        ],
    }


async def my_action_items(
    user_id: str,
    user_role: UserRole,
    status: Optional[str] = None,   # PENDING / IN_PROGRESS / COMPLETED / OVERDUE
) -> dict:
    """Action items assigned to this user."""
    async with AsyncSessionLocal() as db:
        q = select(ActionItem).where(ActionItem.owner_id == UUID(user_id))
        if status:
            q = q.where(ActionItem.status == status)
        rows = (await db.execute(q.order_by(ActionItem.due_date.asc()).limit(100))).scalars().all()
    return {
        "status": "ok",
        "count": len(rows),
        "items": [
            {
                "id": str(it.id),
                "description": it.description,
                "due_date": it.due_date.isoformat() if it.due_date else None,
                "priority": getattr(it, "priority", None),
                "status": it.status,
            }
            for it in rows
        ],
    }


async def next_deadlines(
    user_id: str,
    user_role: UserRole,
    window: str = "7d",
) -> dict:
    """Combined upcoming meetings + action items in the next window."""
    try:
        days = int(window.rstrip("d"))
    except ValueError:
        return {"status": "invalid_input", "reason": "window must be like '7d'"}
    horizon = datetime.utcnow() + timedelta(days=days)

    async with AsyncSessionLocal() as db:
        meetings = (await db.execute(
            select(Meeting).where(
                Meeting.scheduled_at >= datetime.utcnow(),
                Meeting.scheduled_at <= horizon,
            ).order_by(Meeting.scheduled_at.asc()).limit(20)
        )).scalars().all()

        items = (await db.execute(
            select(ActionItem).where(
                ActionItem.owner_id == UUID(user_id),
                ActionItem.due_date.is_not(None),
                ActionItem.due_date <= horizon,
            ).order_by(ActionItem.due_date.asc()).limit(20)
        )).scalars().all()

    return {
        "status": "ok",
        "window_days": days,
        "meetings": [
            {"id": str(m.id), "title": m.title, "when": m.scheduled_at.isoformat()}
            for m in meetings
        ],
        "action_items": [
            {"id": str(it.id), "description": it.description,
             "due_date": it.due_date.isoformat() if it.due_date else None}
            for it in items
        ],
    }
