"""Document and pipeline capability contracts, with all transmit paths blocked."""

from __future__ import annotations

import smtplib
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
import resend
from pydantic import BaseModel, TypeAdapter

from app.api.routes import agents, documents, pipeline
from app.capabilities.declarations import documents_pipeline as declarations
from app.capabilities.emit_tool import tool_definition
from app.capabilities.gate import execute_confirmed_capability, invoke_capability
from app.capabilities.spec import (
    CAPABILITIES,
    Capability,
    CapabilityAccessDenied,
    CapabilityContext,
)
from app.core.config import settings
from app.models.models import UserRole
from app.tools import _rbac


CAPABILITY_NAMES = (
    "registry_ingest_document",
    "registry_create_project",
    "registry_list_buyer_matches",
    "registry_list_dfi_matches",
    "registry_list_dfi_windows",
    "registry_get_pipeline_settings",
)
CAPABILITIES_UNDER_TEST = {
    name: getattr(getattr(declarations, name), "__capability__")
    for name in CAPABILITY_NAMES
}

PROJECT_INPUT_PROPERTIES = {
    "twg_id",
    "name",
    "description",
    "investment_size",
    "currency",
    "readiness_score",
    "strategic_alignment_score",
    "pillar",
    "lead_country",
    "assigned_agent",
    "metadata_json",
    "status",
    "start_in_incubation",
    "value_chain_stages",
    "sector_details",
    "is_cross_border",
    "gender_intentional",
    "gender_justification",
    "youth_focused",
    "youth_justification",
    "site_lat",
    "site_lon",
    "site_location_name",
    "financing_structure",
}


def _blocked_mock(name: str, *, async_call: bool = False):
    message = f"Outbound transport unexpectedly reached: {name}"
    mock_type = AsyncMock if async_call else MagicMock
    return mock_type(side_effect=AssertionError(message))


@pytest.fixture(autouse=True)
def isolated_registry_and_blocked_transports(monkeypatch):
    """Keep registry state isolated and make every send/network path fail closed."""

    original_capabilities = dict(CAPABILITIES)
    CAPABILITIES.update(CAPABILITIES_UNDER_TEST)
    agents._pending_actions.clear()
    _rbac._pending_actions.clear()
    _rbac._user_ctx.set(None)
    monkeypatch.setattr(settings, "CAPABILITY_REGISTRY_ENABLED", True)

    from app.services import email_service as email_service_module
    from app.services import resend_service, whatsapp_service
    from app.tools import email_tools, whatsapp_tools
    from app.utils import email_guard

    blocked = {
        "smtp": _blocked_mock("smtplib.SMTP"),
        "resend_sdk": _blocked_mock("resend.Emails.send"),
        "http_client": _blocked_mock("httpx.AsyncClient"),
        "email_resend": _blocked_mock(
            "EmailService._send_via_resend", async_call=True
        ),
        "email_smtp": _blocked_mock(
            "EmailService._send_via_smtp", async_call=True
        ),
        "resend_service": _blocked_mock("ResendService.send_message"),
        "resend_factory": _blocked_mock("get_resend_service"),
        "email_guard": _blocked_mock("email_guard.redirect_recipients"),
        "email_tool": _blocked_mock("email_tools.send_email", async_call=True),
        "email_template_tool": _blocked_mock(
            "email_tools.send_email_from_template", async_call=True
        ),
        "email_draft_tool": _blocked_mock(
            "email_tools.create_email_draft", async_call=True
        ),
        "whatsapp_person_tool": _blocked_mock(
            "whatsapp_tools.send_whatsapp_message", async_call=True
        ),
        "whatsapp_group_tool": _blocked_mock(
            "whatsapp_tools.send_whatsapp_to_group", async_call=True
        ),
        "whatsapp_client": _blocked_mock("WhatsAppService._client"),
        "whatsapp_send": _blocked_mock(
            "WhatsAppService.send_text", async_call=True
        ),
        "confirmed_whatsapp_send": _blocked_mock(
            "agents._execute_send_whatsapp", async_call=True
        ),
    }

    monkeypatch.setattr(smtplib, "SMTP", blocked["smtp"])
    monkeypatch.setattr(resend.Emails, "send", blocked["resend_sdk"])
    monkeypatch.setattr(httpx, "AsyncClient", blocked["http_client"])
    monkeypatch.setattr(
        email_service_module.EmailService,
        "_send_via_resend",
        blocked["email_resend"],
    )
    monkeypatch.setattr(
        email_service_module.EmailService,
        "_send_via_smtp",
        blocked["email_smtp"],
    )
    monkeypatch.setattr(
        resend_service.ResendService,
        "send_message",
        blocked["resend_service"],
    )
    monkeypatch.setattr(
        resend_service,
        "get_resend_service",
        blocked["resend_factory"],
    )
    monkeypatch.setattr(agents, "get_resend_service", blocked["resend_factory"])
    monkeypatch.setattr(
        email_guard,
        "redirect_recipients",
        blocked["email_guard"],
    )
    monkeypatch.setattr(email_tools, "send_email", blocked["email_tool"])
    monkeypatch.setattr(
        email_tools,
        "send_email_from_template",
        blocked["email_template_tool"],
    )
    monkeypatch.setattr(
        email_tools,
        "create_email_draft",
        blocked["email_draft_tool"],
    )
    monkeypatch.setattr(
        whatsapp_tools,
        "send_whatsapp_message",
        blocked["whatsapp_person_tool"],
    )
    monkeypatch.setattr(
        whatsapp_tools,
        "send_whatsapp_to_group",
        blocked["whatsapp_group_tool"],
    )
    monkeypatch.setattr(
        whatsapp_service.WhatsAppService,
        "_client",
        blocked["whatsapp_client"],
    )
    monkeypatch.setattr(
        whatsapp_service.WhatsAppService,
        "send_text",
        blocked["whatsapp_send"],
    )
    monkeypatch.setattr(
        agents,
        "_execute_send_whatsapp",
        blocked["confirmed_whatsapp_send"],
    )

    yield

    for transport in blocked.values():
        transport.assert_not_called()
    CAPABILITIES.clear()
    CAPABILITIES.update(original_capabilities)
    agents._pending_actions.clear()
    _rbac._pending_actions.clear()
    _rbac._user_ctx.set(None)


@pytest.fixture
def admin_user():
    return SimpleNamespace(
        id=uuid.uuid4(),
        role=UserRole.ADMIN,
        is_active=True,
    )


def _project_payload() -> dict:
    return {
        "twg_id": str(uuid.uuid4()),
        "name": "Keta Solar",
        "description": "A utility-scale solar project",
        "investment_size": "12000000",
        "readiness_score": 6,
        "strategic_alignment_score": 8,
    }


@pytest.mark.parametrize(
    ("name", "properties", "required"),
    [
        ("registry_ingest_document", {"doc_id"}, {"doc_id"}),
        (
            "registry_create_project",
            PROJECT_INPUT_PROPERTIES,
            {
                "twg_id",
                "name",
                "description",
                "investment_size",
                "readiness_score",
                "strategic_alignment_score",
            },
        ),
        ("registry_list_buyer_matches", {"project_id"}, {"project_id"}),
        ("registry_list_dfi_matches", {"project_id"}, {"project_id"}),
        ("registry_list_dfi_windows", set(), set()),
        ("registry_get_pipeline_settings", set(), set()),
    ],
)
def test_generated_tool_schemas_have_exact_parameters_and_required_fields(
    name,
    properties,
    required,
):
    declaration = CAPABILITIES_UNDER_TEST[name]
    generated = tool_definition(declaration)["function"]

    assert generated["name"] == name
    assert set(generated["parameters"]["properties"]) == properties
    assert set(generated["parameters"]["required"]) == required
    assert "Example:" in generated["description"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("name", "route_name", "payload", "agent_id"),
    [
        (
            "registry_list_buyer_matches",
            "get_buyer_matches",
            {"project_id": str(uuid.uuid4())},
            "resource_mobilization",
        ),
        (
            "registry_list_dfi_matches",
            "get_dfi_matches",
            {"project_id": str(uuid.uuid4())},
            "resource_mobilization",
        ),
        (
            "registry_list_dfi_windows",
            "list_dfi_windows",
            {},
            "resource_mobilization",
        ),
        (
            "registry_get_pipeline_settings",
            "get_platform_settings",
            {},
            "supervisor",
        ),
    ],
)
async def test_read_capabilities_return_legacy_route_data_without_side_effects(
    monkeypatch,
    admin_user,
    name,
    route_name,
    payload,
    agent_id,
):
    declaration = CAPABILITIES_UNDER_TEST[name]
    window = {
        "id": str(uuid.uuid4()),
        "name": "Regional Climate Facility",
        "institution": "Generic DFI",
        "instrument_type": "BLENDED",
    }
    route_results = {
        "registry_list_buyer_matches": [
            {
                "match_id": str(uuid.uuid4()),
                "buyer": {"id": str(uuid.uuid4()), "name": "Generic Buyer"},
                "score": 87,
                "status": "identified",
                "match_rationale": "Mandate aligns",
            }
        ],
        "registry_list_dfi_matches": [
            {
                "match_id": str(uuid.uuid4()),
                "dfi_window": window,
                "fit_score": 91,
                "status": "identified",
            }
        ],
        "registry_list_dfi_windows": [window],
        "registry_get_pipeline_settings": {"source": route_name},
    }
    route_result = route_results[name]
    route_handler = AsyncMock(return_value=route_result)
    monkeypatch.setattr(pipeline, route_name, route_handler)
    db = object()

    result = await invoke_capability(
        declaration,
        payload,
        CapabilityContext(user=admin_user, db=db),
        agent_id=agent_id,
    )

    if declaration.output_model is None:
        assert result is route_result
    else:
        adapter = TypeAdapter(declaration.output_model)
        validated = adapter.validate_python(route_result, from_attributes=True)
        assert result == adapter.dump_python(validated, mode="json")
    assert agents._pending_actions == {}
    assert _rbac._pending_actions == {}
    if "project_id" in payload:
        route_handler.assert_awaited_once_with(
            project_id=uuid.UUID(payload["project_id"]),
            db=db,
            current_user=admin_user,
        )
    else:
        route_handler.assert_awaited_once_with(db=db, current_user=admin_user)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("name", "route_module", "route_name", "payload", "agent_id"),
    [
        (
            "registry_ingest_document",
            documents,
            "ingest_document",
            {"doc_id": str(uuid.uuid4())},
            "energy",
        ),
        (
            "registry_create_project",
            pipeline,
            "ingest_project",
            _project_payload(),
            "resource_mobilization",
        ),
    ],
)
async def test_write_capabilities_wait_for_confirmation_then_use_legacy_route(
    monkeypatch,
    admin_user,
    name,
    route_module,
    route_name,
    payload,
    agent_id,
):
    declaration = CAPABILITIES_UNDER_TEST[name]
    route_result = {"source": route_name}
    route_handler = AsyncMock(return_value=route_result)
    monkeypatch.setattr(route_module, route_name, route_handler)
    db = object()
    context = CapabilityContext(user=admin_user, db=db)

    card = await invoke_capability(
        declaration,
        payload,
        context,
        agent_id=agent_id,
    )

    assert card["status"] == "confirmation_required"
    assert card["type"] == "action_required"
    assert card["action_type"] == name
    assert card["irreversible"] is False
    assert card["confirm_endpoint"] == "/api/v1/agents/execute"
    route_handler.assert_not_awaited()

    result = await execute_confirmed_capability(
        declaration,
        card["payload"],
        context,
    )

    assert result is route_result
    if name == "registry_ingest_document":
        route_handler.assert_awaited_once_with(
            doc_id=uuid.UUID(payload["doc_id"]),
            current_user=admin_user,
            db=db,
        )
    else:
        submitted = route_handler.await_args.kwargs["data"]
        assert submitted.model_dump(mode="json") == card["payload"]
        assert route_handler.await_args.kwargs == {
            "data": submitted,
            "db": db,
            "current_user": admin_user,
        }


@pytest.mark.asyncio
@pytest.mark.parametrize("name", CAPABILITY_NAMES)
async def test_out_of_scope_agent_is_refused(name, admin_user):
    declaration = CAPABILITIES_UNDER_TEST[name]
    if name == "registry_ingest_document":
        payload = {"doc_id": str(uuid.uuid4())}
    elif name == "registry_create_project":
        payload = _project_payload()
    elif name in {"registry_list_buyer_matches", "registry_list_dfi_matches"}:
        payload = {"project_id": str(uuid.uuid4())}
    else:
        payload = {}

    with pytest.raises(CapabilityAccessDenied, match="outside capability"):
        await invoke_capability(
            declaration,
            payload,
            CapabilityContext(user=admin_user, db=object()),
            agent_id="unscoped_agent",
        )


@pytest.mark.asyncio
async def test_pipeline_settings_refuses_user_role_outside_scope():
    user = SimpleNamespace(
        id=uuid.uuid4(),
        role=UserRole.TWG_MEMBER,
        is_active=True,
    )

    with pytest.raises(CapabilityAccessDenied, match="Requires one of"):
        await invoke_capability(
            CAPABILITIES_UNDER_TEST["registry_get_pipeline_settings"],
            {},
            CapabilityContext(user=user, db=object()),
            agent_id="supervisor",
        )


@pytest.mark.asyncio
async def test_destructive_capability_is_agent_denied_by_default(admin_user):
    calls: list[str] = []

    class DestructiveInput(BaseModel):
        target_id: uuid.UUID

    async def destructive_handler(payload, context):
        calls.append(str(payload.target_id))

    declaration = Capability(
        name="documents_pipeline_destructive_probe",
        description="Test-only destructive default-deny probe.",
        danger="destructive",
        input_model=DestructiveInput,
        handler=destructive_handler,
        scopes=["resource_mobilization", UserRole.ADMIN.value],
        http=None,
    )

    assert declaration.agent_allowed is False
    with pytest.raises(CapabilityAccessDenied, match="not allowed"):
        await invoke_capability(
            declaration,
            {"target_id": str(uuid.uuid4())},
            CapabilityContext(user=admin_user, db=object()),
            agent_id="resource_mobilization",
        )
    assert calls == []
