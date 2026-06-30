"""
Due-soon reminder job for action items (Requirement R3).

Mirrors the existing meeting reminder job
(`app.jobs.reminder_jobs.send_upcoming_meeting_reminders`):

- async, opens its own `AsyncSessionLocal`
- looks at a forward-looking time window
- uses the same notification mechanism the action-item routes use
  (`app.services.notification_service.create_notification`, which both
  persists a `Notification` row and broadcasts it over the WebSocket)
- de-duplicates via an `AuditLog` row so the same item is not nudged
  repeatedly across runs (exactly how the meeting reminder /
  minutes-nudge jobs avoid re-notifying).

This module deliberately only exposes the job FUNCTION. Registration with
the scheduler is handled separately by the integration stage.
"""
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.models import (
    ActionItem,
    ActionItemStatus,
    AuditLog,
    NotificationType,
)
from app.services.notification_service import create_notification

logger = logging.getLogger(__name__)

# AuditLog action string used to de-duplicate due-soon nudges, matching the
# naming convention of MEETING_REMINDER_SENT / MINUTES_NUDGE_SENT.
DUE_SOON_REMINDER_ACTION = "ACTION_ITEM_DUE_SOON_REMINDER_SENT"

# How far ahead an item must be due to qualify as "due soon".
DUE_SOON_MIN_HOURS = 24
DUE_SOON_MAX_HOURS = 48


async def send_due_soon_action_item_reminders():
    """
    Notify owners of action items that are due in the next 24-48 hours,
    are not yet overdue, and are not yet done.

    De-duplicated per item via an AuditLog row so each item is only nudged
    once for its upcoming due date (across repeated scheduler runs).
    """
    logger.info("Running send_due_soon_action_item_reminders job")

    async with AsyncSessionLocal() as db:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        # Window: due between +24h and +48h from now. Lower bound at +24h keeps
        # items that are already overdue or due within the next day out of scope
        # (those are handled by check_overdue_action_items); upper bound at +48h
        # gives owners a couple of days of lead time.
        window_start = now + timedelta(hours=DUE_SOON_MIN_HOURS)
        window_end = now + timedelta(hours=DUE_SOON_MAX_HOURS)

        query = select(ActionItem).where(
            ActionItem.due_date.is_not(None),
            ActionItem.due_date >= window_start,
            ActionItem.due_date <= window_end,
            # Not yet done and not already flagged overdue.
            ActionItem.status.in_([
                ActionItemStatus.PENDING,
                ActionItemStatus.IN_PROGRESS,
            ]),
            # Only items with an assigned owner can be nudged.
            ActionItem.owner_id.is_not(None),
        )

        result = await db.execute(query)
        items = result.scalars().all()

        if not items:
            logger.info("No due-soon action items found")
            return

        nudged = 0
        for item in items:
            # Skip if a due-soon reminder has already been logged for this item.
            audit_query = select(AuditLog).where(
                AuditLog.resource_id == item.id,
                AuditLog.action == DUE_SOON_REMINDER_ACTION,
            )
            audit_result = await db.execute(audit_query)
            if audit_result.scalar_one_or_none():
                continue  # Already nudged for this item.

            try:
                due_str = item.due_date.strftime("%Y-%m-%d") if item.due_date else "soon"
                await create_notification(
                    db=db,
                    user_id=item.owner_id,
                    type=NotificationType.TASK,
                    title="Action Item Due Soon",
                    content=f"'{item.description[:80]}' is due {due_str}",
                    link="/actions",
                )

                # Log the nudge so we don't repeat it on the next run (System User).
                audit = AuditLog(
                    action=DUE_SOON_REMINDER_ACTION,
                    resource_type="action_item",
                    resource_id=item.id,
                    details={
                        "owner_id": str(item.owner_id),
                        "due_date": item.due_date.isoformat() if item.due_date else None,
                    },
                    ip_address="127.0.0.1",  # System
                )
                db.add(audit)
                await db.commit()
                nudged += 1
                logger.info(f"Sent due-soon reminder for action item {item.id}")
            except Exception as e:
                logger.error(
                    f"Failed to send due-soon reminder for action item {item.id}: {e}"
                )

        logger.info(f"Sent {nudged} due-soon action item reminder(s)")
