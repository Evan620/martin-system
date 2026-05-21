"""
Martin Copilot — Briefing endpoint.
GET /martin/briefing — returns role-aware pre-computed summary for the copilot opening bubble.
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Tuple

from fastapi import APIRouter, Depends
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_active_user
from app.core.database import get_db
from app.models.models import (
    Meeting,
    MeetingStatus,
    Notification,
    Project,
    ProjectStatus,
    User,
    UserRole,
)

router = APIRouter(prefix="/martin", tags=["martin"])


async def _query_briefing_data(
    db: AsyncSession,
    is_admin: bool,
    user_twg_ids: List[Any],
    user_id: Any,
    now: datetime,
) -> Tuple[List[Dict], List[Dict], List[Dict]]:
    """Run the three DB queries and return structured lists."""
    window_end = now + timedelta(hours=48)
    notif_cutoff = now - timedelta(hours=48)

    # --- Upcoming meetings (next 48 hours) ---
    mtg_q = (
        select(Meeting)
        .options(selectinload(Meeting.twg))
        .where(
            and_(
                Meeting.scheduled_at >= now,
                Meeting.scheduled_at <= window_end,
                Meeting.status == MeetingStatus.SCHEDULED,
            )
        )
        .order_by(Meeting.scheduled_at)
        .limit(5)
    )
    if not is_admin and user_twg_ids:
        mtg_q = mtg_q.where(Meeting.twg_id.in_(user_twg_ids))
    elif not is_admin and not user_twg_ids:
        mtg_q = mtg_q.where(False)  # no access

    mtg_result = await db.execute(mtg_q)
    meetings_raw = mtg_result.scalars().all()

    upcoming_meetings: List[Dict] = []
    for m in meetings_raw:
        sched = m.scheduled_at
        if sched.tzinfo is None:
            sched = sched.replace(tzinfo=timezone.utc)
        minutes_until = max(0, int((sched - now).total_seconds() / 60))
        upcoming_meetings.append(
            {
                "title": m.title,
                "twg_name": m.twg.name if m.twg else "",
                "starts_at": sched.isoformat(),
                "minutes_until": minutes_until,
            }
        )

    # --- Threshold alerts: projects below gender/youth gate ---
    thr_q = (
        select(Project)
        .where(
            and_(
                Project.status.in_(
                    [
                        ProjectStatus.DRAFT,
                        ProjectStatus.UNDER_REVIEW,
                        ProjectStatus.SUMMIT_READY,
                    ]
                ),
                or_(
                    Project.women_employment_pct.is_(None),
                    Project.women_employment_pct < 30.0,
                    Project.youth_employment_pct.is_(None),
                    Project.youth_employment_pct < 25.0,
                ),
            )
        )
        .limit(10)
    )
    if not is_admin and user_twg_ids:
        thr_q = thr_q.where(Project.twg_id.in_(user_twg_ids))
    elif not is_admin and not user_twg_ids:
        thr_q = thr_q.where(False)

    thr_result = await db.execute(thr_q)
    threshold_projects = thr_result.scalars().all()

    threshold_alerts: List[Dict] = []
    for p in threshold_projects:
        if p.women_employment_pct is None or p.women_employment_pct < 30.0:
            threshold_alerts.append(
                {
                    "project_name": p.name,
                    "gap_type": "gender",
                    "current_pct": p.women_employment_pct,
                    "required_pct": 30.0,
                }
            )
        elif p.youth_employment_pct is None or p.youth_employment_pct < 25.0:
            threshold_alerts.append(
                {
                    "project_name": p.name,
                    "gap_type": "youth",
                    "current_pct": p.youth_employment_pct,
                    "required_pct": 25.0,
                }
            )

    # --- Overdue notifications: unread, created > 48h ago ---
    notif_q = (
        select(Notification)
        .where(
            and_(
                Notification.user_id == user_id,
                Notification.is_read == False,  # noqa: E712
                Notification.created_at <= notif_cutoff,
            )
        )
        .order_by(Notification.created_at)
        .limit(5)
    )

    notif_result = await db.execute(notif_q)
    notifs_raw = notif_result.scalars().all()

    overdue_items: List[Dict] = []
    for n in notifs_raw:
        created = n.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        days_overdue = max(0, int((now - created).total_seconds() / 86400))
        overdue_items.append({"title": n.title, "days_overdue": days_overdue})

    return upcoming_meetings, threshold_alerts, overdue_items


@router.get("/briefing")
async def get_briefing(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Dict:
    """
    Return a role-aware briefing summary for the copilot opening bubble.
    All three arrays are always present (empty if nothing to report).
    """
    now = datetime.now(timezone.utc)
    is_admin = current_user.role in (UserRole.ADMIN, UserRole.SECRETARIAT_LEAD)
    user_twg_ids = [t.id for t in current_user.twgs]

    upcoming_meetings, threshold_alerts, overdue_items = await _query_briefing_data(
        db=db,
        is_admin=is_admin,
        user_twg_ids=user_twg_ids,
        user_id=current_user.id,
        now=now,
    )

    hour = now.hour
    if hour < 12:
        greeting = "Good morning"
    elif hour < 17:
        greeting = "Good afternoon"
    else:
        greeting = "Good evening"

    return {
        "greeting": greeting,
        "upcoming_meetings": upcoming_meetings,
        "threshold_alerts": threshold_alerts,
        "overdue_items": overdue_items,
    }
