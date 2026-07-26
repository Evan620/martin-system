"""The two initial capabilities used to prove the registry end to end."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import has_twg_access
from app.api.routes.action_items import create_action_item
from app.capabilities.spec import CapabilityContext, capability
from app.models.models import TWG, User, UserRole
from app.schemas.schemas import ActionItemCreate


_TWG_AGENT_SCOPES = [
    "member",
    "twg_*",
    "energy",
    "agriculture",
    "minerals",
    "digital",
    "protocol",
    "resource_mobilization",
]
_WRITE_AGENT_SCOPES = ["supervisor", "supervisor_v1", *_TWG_AGENT_SCOPES[1:]]
_ALL_USER_ROLES = [role.value for role in UserRole]
_EDIT_USER_ROLES = [
    UserRole.ADMIN.value,
    UserRole.SECRETARIAT_LEAD.value,
    UserRole.TWG_FACILITATOR.value,
]


class ListTWGMembersInput(BaseModel):
    twg_id: uuid.UUID = Field(description="Technical Working Group UUID")


@capability(
    name="registry_list_twg_members",
    description=(
        "List the authenticated user's permitted TWG members with names, email "
        "addresses, and roles."
    ),
    danger="read",
    input_model=ListTWGMembersInput,
    scopes=[*_TWG_AGENT_SCOPES, *_ALL_USER_ROLES],
    http=("POST", "/capabilities/twg-members/query"),
    summary_template="List TWG members for {twg_id}",
)
async def registry_list_twg_members(
    payload: ListTWGMembersInput,
    context: CapabilityContext,
) -> list[dict[str, Any]]:
    if not has_twg_access(context.user, payload.twg_id):
        raise HTTPException(status_code=403, detail="Access denied to this TWG")

    twg = (
        await context.db.execute(
            select(TWG)
            .where(TWG.id == payload.twg_id)
            .options(selectinload(TWG.members))
        )
    ).scalar_one_or_none()
    if twg is None:
        raise HTTPException(status_code=404, detail="TWG not found")

    members = [
        {
            "name": member.full_name,
            "email": member.email,
            "role": member.role.value,
        }
        for member in twg.members
    ]
    existing_emails = {member["email"] for member in members}
    for lead_id, lead_role in (
        (twg.political_lead_id, "political_lead"),
        (twg.technical_lead_id, "technical_lead"),
    ):
        if lead_id is None:
            continue
        lead = (
            await context.db.execute(select(User).where(User.id == lead_id))
        ).scalar_one_or_none()
        if lead is not None and lead.email not in existing_emails:
            members.append(
                {"name": lead.full_name, "email": lead.email, "role": lead_role}
            )
            existing_emails.add(lead.email)
    return members


@capability(
    name="registry_create_action_item",
    description=(
        "Create an action item after explicit confirmation, using the same "
        "validation and business logic as the existing action-item endpoint."
    ),
    danger="write",
    input_model=ActionItemCreate,
    scopes=[*_WRITE_AGENT_SCOPES, *_EDIT_USER_ROLES],
    http=("POST", "/capabilities/action-items"),
    summary_template='Create action item: "{description}"',
)
async def registry_create_action_item(
    payload: ActionItemCreate,
    context: CapabilityContext,
) -> Any:
    return await create_action_item(payload, context.user, context.db)
