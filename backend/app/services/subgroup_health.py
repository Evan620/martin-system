"""
Sub-group Health Service
=========================

Computes an "effectiveness" health signal for TWG sub-groups (R4: "Ensure
sub-groups are running effectively").

This REUSES the proven TWG-level stalled/health pattern from
``app/api/routes/dashboard.py`` (the ~14-day last-activity cutoff plus a
completion-percentage signal) and extends it to signals that are now
attributable to a *sub-group* via the nullable ``subgroup_id`` FK added to the
Meeting and ActionItem models, plus the existing sub-group documents and
members relationships.

NOTHING here mutates existing behaviour. The compute function is pure/read
(it only reads ORM-loaded relationships); the scan job is additive and is NOT
registered anywhere by this module — see ``scan_stalled_subgroups`` for the
registration details the integration stage needs.

------------------------------------------------------------------------------
RUBRIC
------------------------------------------------------------------------------
Three signals are combined into a status of ``healthy`` / ``at_risk`` /
``stalled``:

1. Last-activity recency
   The most recent timestamp across the sub-group's COMPLETED meetings,
   action-item updates (updated_at / completed_at / created_at) and document
   ingestion. Mirrors the dashboard's 14-day cutoff.
     - active within  ACTIVE_CUTOFF_DAYS (14d)  -> recency healthy
     - within         STALLED_CUTOFF_DAYS (30d)  -> recency at-risk
     - older / none, AND no upcoming meeting     -> recency stalled

2. Action-item closure %
   completed action-items / total action-items attributed to the sub-group.
     - >= CLOSURE_HEALTHY_PCT (60%)             -> closure healthy
     - >= CLOSURE_ATRISK_PCT  (30%)             -> closure at-risk
     - below, with open items                   -> closure stalled

3. Meeting cadence
   Whether the sub-group has any upcoming (SCHEDULED) meeting on the books.
   A future meeting is a strong "running effectively" signal and can lift a
   sub-group out of "stalled" on recency alone (matches dashboard logic where
   a future meeting means "not stalled").

Overall status = worst of the contributing signals, EXCEPT a scheduled future
meeting prevents a pure-recency "stalled" from being reported as stalled
(it becomes at_risk instead), consistent with the dashboard heuristic.

Brand-new sub-groups (no meetings, no action items, no docs) are reported as
``at_risk`` rather than ``stalled`` if they were created within
ACTIVE_CUTOFF_DAYS — a freshly-created group has not yet had a chance to
stall.
"""

from __future__ import annotations

import datetime
import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.models import (
    SubGroup,
    Meeting,
    ActionItem,
    MeetingStatus,
    ActionItemStatus,
    Notification,
    NotificationType,
)

# --- Tunable rubric thresholds (module-level so they are easy to audit) ---
ACTIVE_CUTOFF_DAYS = 14      # mirrors dashboard.py TWG-health cutoff
STALLED_CUTOFF_DAYS = 30
CLOSURE_HEALTHY_PCT = 60
CLOSURE_ATRISK_PCT = 30

STATUS_HEALTHY = "healthy"
STATUS_AT_RISK = "at_risk"
STATUS_STALLED = "stalled"

# Ordering used to take the "worst" of several signals.
_SEVERITY = {STATUS_HEALTHY: 0, STATUS_AT_RISK: 1, STATUS_STALLED: 2}


def _worst(*statuses: str) -> str:
    """Return the most-severe status among the arguments."""
    valid = [s for s in statuses if s in _SEVERITY]
    if not valid:
        return STATUS_HEALTHY
    return max(valid, key=lambda s: _SEVERITY[s])


def _last_activity_at(
    meetings: List[Meeting],
    action_items: List[ActionItem],
    documents: List[Any],
) -> Optional[datetime.datetime]:
    """
    Most recent activity timestamp attributable to the sub-group.

    Considers COMPLETED meetings (by scheduled_at), action-item activity
    (completed_at / updated_at / created_at) and document ingestion/creation.
    """
    candidates: List[datetime.datetime] = []

    for m in meetings:
        if m.status == MeetingStatus.COMPLETED and m.scheduled_at:
            candidates.append(m.scheduled_at)

    for ai in action_items:
        for ts in (ai.completed_at, ai.updated_at, ai.created_at):
            if ts:
                candidates.append(ts)
                break

    for d in documents:
        ts = getattr(d, "ingested_at", None) or getattr(d, "created_at", None)
        if ts:
            candidates.append(ts)

    return max(candidates) if candidates else None


def _has_upcoming_meeting(meetings: List[Meeting], now: datetime.datetime) -> bool:
    """True if the sub-group has any SCHEDULED meeting in the future."""
    for m in meetings:
        if m.status == MeetingStatus.SCHEDULED and m.scheduled_at and m.scheduled_at >= now:
            return True
    return False


def compute_subgroup_health(
    subgroup: SubGroup,
    meetings: Optional[List[Meeting]] = None,
    action_items: Optional[List[ActionItem]] = None,
    documents: Optional[List[Any]] = None,
    now: Optional[datetime.datetime] = None,
) -> Dict[str, Any]:
    """
    Compute the health/effectiveness signal for a single sub-group.

    Parameters
    ----------
    subgroup:
        The SubGroup ORM object. ``subgroup.members`` is read if loaded.
    meetings / action_items / documents:
        Pre-fetched lists already filtered to this sub-group
        (``subgroup_id == subgroup.id``). Pass empty lists for "none".
        ``documents`` defaults to ``subgroup.documents`` if not supplied.
    now:
        Override for "current time" (testing). Defaults to ``utcnow()``.

    Returns
    -------
    dict with keys:
        status:            healthy | at_risk | stalled
        last_active_at:    ISO timestamp or None
        days_since_active: int or None
        meeting_count:     completed meetings considered
        upcoming_meetings: count of future SCHEDULED meetings
        open_action_items: int
        total_action_items:int
        closure_pct:       int (0-100), None if no action items
        member_count:      int
        signals:           per-signal breakdown for the detailed endpoint
    """
    now = now or datetime.datetime.utcnow()
    meetings = list(meetings or [])
    action_items = list(action_items or [])
    if documents is None:
        # Fall back to the loaded relationship if the caller did not pass docs.
        documents = list(getattr(subgroup, "documents", []) or [])
    else:
        documents = list(documents)

    active_cutoff = now - datetime.timedelta(days=ACTIVE_CUTOFF_DAYS)
    stalled_cutoff = now - datetime.timedelta(days=STALLED_CUTOFF_DAYS)

    # --- Signal 1: last-activity recency ---
    last_active = _last_activity_at(meetings, action_items, documents)
    has_upcoming = _has_upcoming_meeting(meetings, now)

    if last_active is None:
        # No activity at all. A brand-new group gets the benefit of the doubt.
        created_at = getattr(subgroup, "created_at", None)
        if created_at and created_at >= active_cutoff:
            recency_status = STATUS_AT_RISK
        elif has_upcoming:
            recency_status = STATUS_AT_RISK
        else:
            recency_status = STATUS_STALLED
        days_since_active = None
    else:
        days_since_active = (now - last_active).days
        if last_active >= active_cutoff:
            recency_status = STATUS_HEALTHY
        elif last_active >= stalled_cutoff:
            recency_status = STATUS_AT_RISK
        else:
            recency_status = STATUS_STALLED

    # A scheduled future meeting keeps a recency-stalled group from being
    # reported as fully stalled (matches dashboard "future_meetings" rule).
    if recency_status == STATUS_STALLED and has_upcoming:
        recency_status = STATUS_AT_RISK

    # --- Signal 2: action-item closure % ---
    total_ai = len(action_items)
    completed_ai = len([a for a in action_items if a.status == ActionItemStatus.COMPLETED])
    open_ai = total_ai - completed_ai
    if total_ai == 0:
        closure_pct: Optional[int] = None
        closure_status = STATUS_HEALTHY  # nothing overdue if nothing assigned
    else:
        closure_pct = int((completed_ai / total_ai) * 100)
        if closure_pct >= CLOSURE_HEALTHY_PCT:
            closure_status = STATUS_HEALTHY
        elif closure_pct >= CLOSURE_ATRISK_PCT:
            closure_status = STATUS_AT_RISK
        else:
            closure_status = STATUS_STALLED

    # --- Signal 3: meeting cadence ---
    completed_meeting_count = len(
        [m for m in meetings if m.status == MeetingStatus.COMPLETED]
    )
    upcoming_count = len(
        [
            m
            for m in meetings
            if m.status == MeetingStatus.SCHEDULED
            and m.scheduled_at
            and m.scheduled_at >= now
        ]
    )

    overall = _worst(recency_status, closure_status)

    member_count = len(getattr(subgroup, "members", []) or [])

    return {
        "status": overall,
        "last_active_at": last_active.isoformat() if last_active else None,
        "days_since_active": days_since_active,
        "meeting_count": completed_meeting_count,
        "upcoming_meetings": upcoming_count,
        "open_action_items": open_ai,
        "total_action_items": total_ai,
        "closure_pct": closure_pct,
        "member_count": member_count,
        "signals": {
            "recency": recency_status,
            "closure": closure_status,
            "has_upcoming_meeting": has_upcoming,
        },
    }


async def compute_subgroup_health_for_id(
    db: AsyncSession,
    subgroup: SubGroup,
    now: Optional[datetime.datetime] = None,
) -> Dict[str, Any]:
    """
    Async helper: fetch the meetings + action items attributed to ``subgroup``
    via the new ``subgroup_id`` FK, then compute health.

    ``subgroup.documents`` / ``subgroup.members`` are expected to be loaded by
    the caller (the subgroups routes already selectinload them); documents fall
    back to the relationship inside ``compute_subgroup_health``.
    """
    m_res = await db.execute(
        select(Meeting).where(Meeting.subgroup_id == subgroup.id)
    )
    meetings = m_res.scalars().all()

    ai_res = await db.execute(
        select(ActionItem).where(ActionItem.subgroup_id == subgroup.id)
    )
    action_items = ai_res.scalars().all()

    return compute_subgroup_health(
        subgroup,
        meetings=list(meetings),
        action_items=list(action_items),
        documents=None,
        now=now,
    )


# ---------------------------------------------------------------------------
# Scan job: find stalled sub-groups and alert their lead.
# ---------------------------------------------------------------------------
# De-duplication window: do not re-alert the same lead about the same
# sub-group more than once within this many hours.
ALERT_DEDUP_HOURS = 24


async def scan_stalled_subgroups(now: Optional[datetime.datetime] = None) -> int:
    """
    Background scan: locate sub-groups whose computed health is ``stalled`` and
    fire a de-duplicated ALERT notification to the sub-group lead (its
    facilitator). Returns the number of fresh alerts created.

    This function is SELF-CONTAINED: it opens its own DB session via
    ``get_db_session_context`` (the same context manager the existing
    ContinuousMonitor jobs use). It is NOT registered with any scheduler here;
    the integration stage must register it (see module docstring / the
    builder's schedulerRegistration output).

    De-duplication: an alert is skipped if an unread ALERT notification linking
    to the same sub-group already exists for that lead, OR if any such alert was
    created within ALERT_DEDUP_HOURS.

    NOTE: this is intentionally read-mostly. It only INSERTS new Notification
    rows (additive). It never updates/deletes sub-groups, meetings or action
    items, and it never changes a sub-group's stored ``status`` column.
    """
    # Imported lazily so importing this module never triggers DB/engine setup
    # (keeps the route import light and avoids import cycles).
    from app.core.database import get_db_session_context
    from app.services.notification_service import create_notification

    now = now or datetime.datetime.utcnow()
    dedup_cutoff = now - datetime.timedelta(hours=ALERT_DEDUP_HOURS)
    alerts_created = 0

    async with get_db_session_context() as db:
        sg_res = await db.execute(
            select(SubGroup).options(
                selectinload(SubGroup.members),
                selectinload(SubGroup.documents),
                selectinload(SubGroup.lead),
            )
        )
        subgroups = sg_res.scalars().all()

        for sg in subgroups:
            # Only sub-groups with an assignable lead can be alerted.
            if not sg.lead_id:
                continue

            health = await compute_subgroup_health_for_id(db, sg, now=now)
            if health["status"] != STATUS_STALLED:
                continue

            # Don't alert on a sub-group that has NO signal basis at all — no
            # meetings (past or upcoming), no action items, and no dated activity
            # (last_active_at is None also implies no documents). That's a "not
            # started yet" group, not a stalled one; alerting its lead would be
            # noise. Such a group can only become "stalled" worth flagging once
            # something is attributed to it (now possible via meeting/action
            # subgroup_id). Genuinely-stalled groups (had activity that lapsed,
            # or open items below closure threshold) still alert.
            if (
                health["last_active_at"] is None
                and health["total_action_items"] == 0
                and health["meeting_count"] == 0
                and health["upcoming_meetings"] == 0
            ):
                continue

            link = f"/twgs/{sg.twg_id}/subgroups/{sg.id}"

            # De-dup: skip if a recent / unread alert already points at this
            # sub-group for this lead.
            existing_res = await db.execute(
                select(Notification).where(
                    Notification.user_id == sg.lead_id,
                    Notification.type == NotificationType.ALERT,
                    Notification.link == link,
                    Notification.created_at >= dedup_cutoff,
                )
            )
            if existing_res.scalars().first() is not None:
                continue

            await create_notification(
                db=db,
                user_id=sg.lead_id,
                type=NotificationType.ALERT,
                title="Sub-group needs attention",
                content=(
                    f"Sub-group '{sg.name}' appears to be stalling: no recent "
                    f"activity and/or low action-item closure. Review and "
                    f"schedule a check-in to keep it running effectively."
                ),
                link=link,
            )
            alerts_created += 1

    return alerts_created
