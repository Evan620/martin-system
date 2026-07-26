"""Document and deal-pipeline capability declarations."""

from __future__ import annotations

import uuid
from typing import Any

from pydantic import BaseModel, Field

from app.capabilities.spec import CapabilityContext, capability
from app.models.models import UserRole
from app.schemas.pipeline_schemas import (
    BuyerMatchRead,
    DFIMatchRead,
    DFIWindowRead,
    ProjectIngest,
)


_STAFF_AGENT_SCOPES = [
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
_SETTINGS_AGENT_SCOPES = ["supervisor", "supervisor_v1"]
_SETTINGS_USER_ROLES = [
    UserRole.ADMIN.value,
    UserRole.SECRETARIAT_LEAD.value,
]


class DocumentReferenceInput(BaseModel):
    doc_id: uuid.UUID = Field(
        description="UUID of a document already uploaded to Martin"
    )


class ProjectReferenceInput(BaseModel):
    project_id: uuid.UUID = Field(description="Deal-pipeline project UUID")


class ListDFIWindowsInput(BaseModel):
    """No filters are supported by the existing DFI-window endpoint."""


class GetPipelineSettingsInput(BaseModel):
    """The existing settings endpoint accepts no parameters."""


@capability(
    name="registry_ingest_document",
    description=(
        "Ingest an existing uploaded document into Martin's searchable knowledge "
        "base after confirmation. Use this when the user asks to index or make an "
        "already-uploaded file searchable; do not use it to upload file bytes. "
        "Example: the user says 'Make the feasibility study searchable' and the "
        "document registry returned its UUID -> call registry_ingest_document("
        "doc_id='2f60c0d0-1c5d-4a9b-8c7e-123456789abc')."
    ),
    danger="write",
    input_model=DocumentReferenceInput,
    scopes=[*_STAFF_AGENT_SCOPES, *_ALL_USER_ROLES],
    http=("POST", "/capabilities/documents/ingest"),
    summary_template="Ingest document {doc_id}",
)
async def registry_ingest_document(
    payload: DocumentReferenceInput,
    context: CapabilityContext,
) -> Any:
    from app.api.routes import documents

    return await documents.ingest_document(
        doc_id=payload.doc_id,
        current_user=context.user,
        db=context.db,
    )


@capability(
    name="registry_create_project",
    description=(
        "Create a new proposal in the deal pipeline after confirmation. Use this "
        "only when the user explicitly asks to submit or add a project and you "
        "have collected every required intake field. Example: 'Add the Keta solar "
        "project for the Energy TWG, USD 12 million, readiness 6 and alignment 8' "
        "-> call registry_create_project with the TWG ID, name, description, "
        "investment_size=12000000, currency='USD', readiness_score=6, and "
        "strategic_alignment_score=8."
    ),
    danger="write",
    input_model=ProjectIngest,
    scopes=[*_STAFF_AGENT_SCOPES, *_ALL_USER_ROLES],
    http=("POST", "/capabilities/pipeline/projects"),
    summary_template='Create pipeline project: "{name}"',
)
async def registry_create_project(
    payload: ProjectIngest,
    context: CapabilityContext,
) -> Any:
    from app.api.routes import pipeline

    return await pipeline.ingest_project(
        data=payload,
        db=context.db,
        current_user=context.user,
    )


@capability(
    name="registry_list_buyer_matches",
    description=(
        "List the scored buyer matches already generated for one pipeline project. "
        "Use this when the user asks which buyers fit a project, their match scores, "
        "or match status; this does not run matching. Example: 'Show buyer matches "
        "for the Keta solar project' after resolving its UUID -> call "
        "registry_list_buyer_matches(project_id="
        "'72ab6d64-24fb-4f10-9066-123456789abc')."
    ),
    danger="read",
    input_model=ProjectReferenceInput,
    output_model=list[BuyerMatchRead],
    scopes=[*_STAFF_AGENT_SCOPES, *_ALL_USER_ROLES],
    http=("POST", "/capabilities/pipeline/buyer-matches/query"),
    summary_template="List buyer matches for project {project_id}",
)
async def registry_list_buyer_matches(
    payload: ProjectReferenceInput,
    context: CapabilityContext,
) -> Any:
    from app.api.routes import pipeline

    return await pipeline.get_buyer_matches(
        project_id=payload.project_id,
        db=context.db,
        current_user=context.user,
    )


@capability(
    name="registry_list_dfi_matches",
    description=(
        "List the scored development-finance institution funding-window matches "
        "already generated for one pipeline project. Use this when the user asks "
        "which DFI or climate-finance windows fit a project; this does not run the "
        "matching engine. Example: 'Which DFI windows match the Keta solar "
        "project?' after resolving its UUID -> call registry_list_dfi_matches("
        "project_id='72ab6d64-24fb-4f10-9066-123456789abc')."
    ),
    danger="read",
    input_model=ProjectReferenceInput,
    output_model=list[DFIMatchRead],
    scopes=[*_STAFF_AGENT_SCOPES, *_ALL_USER_ROLES],
    http=("POST", "/capabilities/pipeline/dfi-matches/query"),
    summary_template="List DFI matches for project {project_id}",
)
async def registry_list_dfi_matches(
    payload: ProjectReferenceInput,
    context: CapabilityContext,
) -> Any:
    from app.api.routes import pipeline

    return await pipeline.get_dfi_matches(
        project_id=payload.project_id,
        db=context.db,
        current_user=context.user,
    )


@capability(
    name="registry_list_dfi_windows",
    description=(
        "List every active DFI and climate-finance funding window in Martin's "
        "catalogue. Use this for broad funding-window discovery when no project "
        "match is required. Example: 'What active climate-finance windows are "
        "available?' -> call registry_list_dfi_windows()."
    ),
    danger="read",
    input_model=ListDFIWindowsInput,
    output_model=list[DFIWindowRead],
    scopes=[*_STAFF_AGENT_SCOPES, *_ALL_USER_ROLES],
    http=("POST", "/capabilities/pipeline/dfi-windows/query"),
    summary_template="List active DFI windows",
)
async def registry_list_dfi_windows(
    payload: ListDFIWindowsInput,
    context: CapabilityContext,
) -> Any:
    from app.api.routes import pipeline

    return await pipeline.list_dfi_windows(
        db=context.db,
        current_user=context.user,
    )


@capability(
    name="registry_get_pipeline_settings",
    description=(
        "Get the deal-pipeline scoring and incubation settings for an authorized "
        "administrator or Secretariat lead. Use this when that user asks for the "
        "current pipeline thresholds; never use it to change them. Example: 'What "
        "is the current incubation graduation threshold?' -> call "
        "registry_get_pipeline_settings()."
    ),
    danger="read",
    input_model=GetPipelineSettingsInput,
    scopes=[*_SETTINGS_AGENT_SCOPES, *_SETTINGS_USER_ROLES],
    http=("POST", "/capabilities/pipeline/settings/query"),
    summary_template="Get pipeline settings",
)
async def registry_get_pipeline_settings(
    payload: GetPipelineSettingsInput,
    context: CapabilityContext,
) -> Any:
    from app.api.routes import pipeline

    return await pipeline.get_platform_settings(
        db=context.db,
        current_user=context.user,
    )
