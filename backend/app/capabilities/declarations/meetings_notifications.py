"""Capability declarations for meetings and caller-owned notifications."""

from __future__ import annotations

import uuid
from typing import Any

from pydantic import BaseModel, Field

from app.capabilities.spec import CapabilityContext, capability
from app.models.models import UserRole
from app.schemas.schemas import AgendaRead, NotificationRead, RecurringMeetingRead
from app.services import (
    meeting_capability_service,
    notification_service,
    recurring_meeting_service,
)


_AGENT_SCOPES = [
    "member",
    "supervisor",
    "supervisor_v1",
    "twg_*",
    "energy",
    "agriculture",
    "minerals",
    "digital",
    "protocol",
    "resource_mobilization",
]
_ALL_USER_ROLES = [role.value for role in UserRole]
_APPROVAL_SCOPES = [
    "supervisor",
    "supervisor_v1",
    UserRole.ADMIN.value,
    UserRole.SECRETARIAT_LEAD.value,
]


class GetMeetingAgendaInput(BaseModel):
    meeting_id: uuid.UUID = Field(
        description="UUID of the meeting whose agenda should be retrieved"
    )


class ApproveMeetingMinutesInput(BaseModel):
    meeting_id: uuid.UUID = Field(
        description="UUID of the meeting with minutes awaiting approval"
    )


class ListNotificationsInput(BaseModel):
    skip: int = Field(
        default=0,
        description="Number of the caller's newest notifications to skip",
    )
    limit: int = Field(
        default=50,
        description="Maximum number of the caller's notifications to return",
    )


class MarkAllNotificationsReadInput(BaseModel):
    pass


class GetRecurringMeetingInput(BaseModel):
    recurring_meeting_id: uuid.UUID = Field(
        description="UUID of the recurring meeting series to retrieve"
    )


@capability(
    name="registry_get_meeting_agenda",
    description=(
        "Retrieve the agenda for one meeting the authenticated user can access. "
        "Use this when the user asks what will be discussed in a known meeting; "
        "use a schedule tool instead when they have not identified a meeting. "
        "Example: if the user asks 'What is on the agenda for meeting "
        "8d86b8b4-9a50-4f0d-9aba-8bf975f62ac7?', call this capability with "
        "meeting_id='8d86b8b4-9a50-4f0d-9aba-8bf975f62ac7'."
    ),
    danger="read",
    input_model=GetMeetingAgendaInput,
    scopes=[*_AGENT_SCOPES, *_ALL_USER_ROLES],
    summary_template="Get agenda for meeting {meeting_id}",
)
async def registry_get_meeting_agenda(
    payload: GetMeetingAgendaInput,
    context: CapabilityContext,
) -> dict[str, Any]:
    agenda = await meeting_capability_service.get_meeting_agenda(
        payload.meeting_id,
        context.user,
        context.db,
    )
    return AgendaRead.model_validate(agenda).model_dump(mode="json")


@capability(
    name="registry_approve_meeting_minutes",
    description=(
        "Propose approving and publishing minutes that are already pending "
        "approval. Use this only when an authorized Secretariat Lead or Admin "
        "explicitly asks to approve a known meeting's minutes. Confirmation is "
        "required because approval can generate a PDF, email participants, index "
        "the minutes, and emit an approved public summary. Example: if the user "
        "says 'Approve the minutes for meeting "
        "8d86b8b4-9a50-4f0d-9aba-8bf975f62ac7', call with that meeting_id, then "
        "wait for human confirmation."
    ),
    danger="write",
    input_model=ApproveMeetingMinutesInput,
    scopes=_APPROVAL_SCOPES,
    summary_template="Approve and publish minutes for meeting {meeting_id}",
)
async def registry_approve_meeting_minutes(
    payload: ApproveMeetingMinutesInput,
    context: CapabilityContext,
) -> dict[str, Any]:
    return await meeting_capability_service.approve_meeting_minutes(
        payload.meeting_id,
        context.user,
        context.db,
        client_ip=None,
    )


@capability(
    name="registry_list_notifications",
    description=(
        "List the authenticated user's own in-app notifications, newest first. "
        "Use this when the user asks about alerts, unread updates, or recent "
        "notifications, and paginate with skip and limit when needed. Example: "
        "for 'Show my 20 most recent notifications', call with skip=0 and "
        "limit=20."
    ),
    danger="read",
    input_model=ListNotificationsInput,
    scopes=[*_AGENT_SCOPES, *_ALL_USER_ROLES],
    summary_template="List notifications with skip {skip} and limit {limit}",
)
async def registry_list_notifications(
    payload: ListNotificationsInput,
    context: CapabilityContext,
) -> list[dict[str, Any]]:
    notifications = await notification_service.list_notifications(
        context.db,
        context.user,
        skip=payload.skip,
        limit=payload.limit,
    )
    return [
        NotificationRead.model_validate(notification).model_dump(mode="json")
        for notification in notifications
    ]


@capability(
    name="registry_mark_all_notifications_read",
    description=(
        "Propose marking every in-app notification owned by the authenticated "
        "user as read. Use this only when the user explicitly asks to clear or "
        "mark all of their notifications read; confirmation is required. "
        "Example: for 'Mark all my notifications as read', call this capability "
        "with no arguments and wait for human confirmation."
    ),
    danger="write",
    input_model=MarkAllNotificationsReadInput,
    scopes=[*_AGENT_SCOPES, *_ALL_USER_ROLES],
    summary_template="Mark all of your notifications as read",
)
async def registry_mark_all_notifications_read(
    payload: MarkAllNotificationsReadInput,
    context: CapabilityContext,
) -> dict[str, Any]:
    return await notification_service.mark_all_notifications_read(
        context.db,
        context.user,
    )


@capability(
    name="registry_get_recurring_meeting",
    description=(
        "Retrieve one recurring meeting series the authenticated user can access, "
        "including up to its next 10 non-cancelled instances. Use this when the "
        "user asks for the cadence, configuration, or upcoming dates of a known "
        "series. Example: if the user asks 'When does recurring series "
        "5ab241f0-bd31-4573-9d5b-3227a5a3ff1e meet next?', call with "
        "recurring_meeting_id='5ab241f0-bd31-4573-9d5b-3227a5a3ff1e'."
    ),
    danger="read",
    input_model=GetRecurringMeetingInput,
    scopes=[*_AGENT_SCOPES, *_ALL_USER_ROLES],
    summary_template="Get recurring meeting {recurring_meeting_id}",
)
async def registry_get_recurring_meeting(
    payload: GetRecurringMeetingInput,
    context: CapabilityContext,
) -> dict[str, Any]:
    recurring = await recurring_meeting_service.get_recurring_meeting_details(
        context.db,
        payload.recurring_meeting_id,
        context.user,
    )
    return RecurringMeetingRead.model_validate(recurring).model_dump(mode="json")
