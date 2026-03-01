"""
Shared constants for action item status transitions.

Used by the API layer and agent tools to enforce consistent state machine rules.
"""
from app.models.models import ActionItemStatus

PENDING = ActionItemStatus.PENDING
IN_PROGRESS = ActionItemStatus.IN_PROGRESS
COMPLETED = ActionItemStatus.COMPLETED
OVERDUE = ActionItemStatus.OVERDUE

VALID_STATUS_TRANSITIONS = {
    PENDING: {IN_PROGRESS, COMPLETED, OVERDUE},
    IN_PROGRESS: {COMPLETED, PENDING, OVERDUE},
    OVERDUE: {IN_PROGRESS, COMPLETED},
    COMPLETED: set(),  # Terminal state
}
