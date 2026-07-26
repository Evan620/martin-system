"""Full-stack contracts for the generated capability HTTP surface.

These tests deliberately send responses through the real FastAPI application and
httpx's ASGI transport.  Calling generated endpoints directly would bypass the
response serializer and would not catch ORM response serialization regressions.
"""

from __future__ import annotations

import smtplib
import uuid
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from fastapi import APIRouter

from app.api.deps import get_current_active_user
from app.api.routes import agents
from app.capabilities import CAPABILITIES, load_all_capabilities
from app.capabilities.emit_http import mount_capability_routes
from app.core.config import settings
from app.core.database import get_db
from app.main import app
from app.models.models import DFIInstrumentType, DFIWindow, UserRole
from app.services import email_service, whatsapp_service
from app.tools import _rbac


READ_CAPABILITIES = (
    "registry_list_twg_members",
    "registry_list_buyer_matches",
    "registry_list_dfi_matches",
    "registry_list_dfi_windows",
    "registry_get_pipeline_settings",
    "registry_get_meeting_agenda",
    "registry_list_notifications",
    "registry_get_recurring_meeting",
)

WRITE_CAPABILITIES = (
    "registry_create_action_item",
    "registry_ingest_document",
    "registry_create_project",
    "registry_approve_meeting_minutes",
    "registry_mark_all_notifications_read",
)

ALL_CAPABILITIES = READ_CAPABILITIES + WRITE_CAPABILITIES
TEST_ID = uuid.UUID("11111111-1111-4111-8111-111111111111")
RELATED_ID = uuid.UUID("22222222-2222-4222-8222-222222222222")
NOW = datetime(2026, 7, 26, 12, 0)


def _payload_for(name: str) -> dict:
    payloads = {
        "registry_list_twg_members": {"twg_id": str(TEST_ID)},
        "registry_create_action_item": {
            "twg_id": str(TEST_ID),
            "description": "Prepare the corridor brief",
        },
        "registry_ingest_document": {"doc_id": str(TEST_ID)},
        "registry_create_project": {
            "twg_id": str(TEST_ID),
            "name": "Test solar corridor",
            "description": "Serializer regression fixture",
            "investment_size": "12000000",
            "readiness_score": 6,
            "strategic_alignment_score": 8,
        },
        "registry_list_buyer_matches": {"project_id": str(TEST_ID)},
        "registry_list_dfi_matches": {"project_id": str(TEST_ID)},
        "registry_list_dfi_windows": {},
        "registry_get_pipeline_settings": {},
        "registry_get_meeting_agenda": {"meeting_id": str(TEST_ID)},
        "registry_approve_meeting_minutes": {"meeting_id": str(TEST_ID)},
        "registry_list_notifications": {"skip": 0, "limit": 20},
        "registry_mark_all_notifications_read": {},
        "registry_get_recurring_meeting": {"recurring_meeting_id": str(TEST_ID)},
    }
    return payloads[name]


def _dfi_window() -> DFIWindow:
    """Return the same kind of ORM value that exposed the production 500."""

    return DFIWindow(
        id=TEST_ID,
        name="Regional Climate Facility",
        institution="Generic DFI",
        instrument_type=DFIInstrumentType.BLENDED,
        sectors=["energy"],
        geographies=["ECOWAS"],
        min_size_usd=1_000_000,
        max_size_usd=25_000_000,
        eligible_stages=["DRAFT"],
        gender_focus=True,
        climate_focus=True,
        description="Local serializer fixture",
        url="https://example.invalid/facility",
        is_active=True,
    )


def _read_result_for(name: str):
    window = _dfi_window()
    results = {
        # This legacy endpoint has no response model and explicitly emits
        # primitive dictionaries, so its stub mirrors that contract.
        "registry_list_twg_members": [
            {
                "name": "Generic Tester",
                "email": "generic.tester@example.invalid",
                "role": UserRole.ADMIN.value,
            }
        ],
        "registry_list_buyer_matches": [
            SimpleNamespace(
                match_id=str(TEST_ID),
                buyer=SimpleNamespace(id=RELATED_ID, name="Generic Buyer"),
                score=87,
                status="identified",
                match_rationale="Mandate and ticket size align",
            )
        ],
        "registry_list_dfi_matches": [
            SimpleNamespace(
                match_id=str(TEST_ID),
                dfi_window=window,
                fit_score=91,
                fit_rationale="Climate mandate aligns",
                status="identified",
                notes=None,
            )
        ],
        # A real unsaved SQLAlchemy model is intentional: without a declared
        # response contract FastAPI raises PydanticSerializationError here.
        "registry_list_dfi_windows": [window],
        "registry_get_pipeline_settings": {"incubation_graduation_threshold": "7.5"},
        "registry_get_meeting_agenda": SimpleNamespace(
            id=RELATED_ID,
            meeting_id=TEST_ID,
            content="Corridor financing update",
            created_at=NOW,
        ),
        "registry_list_notifications": [
            SimpleNamespace(
                id=RELATED_ID,
                user_id=TEST_ID,
                type="info",
                title="Agenda published",
                content="The meeting agenda is ready.",
                link="/meetings/example",
                is_read=False,
                created_at=NOW,
            )
        ],
        "registry_get_recurring_meeting": SimpleNamespace(
            id=TEST_ID,
            twg_id=RELATED_ID,
            title_template="Weekly Energy TWG",
            duration_minutes=60,
            location="Virtual",
            meeting_type="virtual",
            frequency="weekly",
            interval_weeks=1,
            day_of_week=2,
            start_date=NOW,
            start_time="12:00",
            timezone="Africa/Nairobi",
            end_type="never",
            end_date=None,
            max_occurrences=None,
            status="active",
            occurrences_created=4,
            created_at=NOW,
            created_by_id=TEST_ID,
            upcoming_instances=[],
        ),
    }
    return results[name]


@pytest.fixture
def generated_capability_app(monkeypatch):
    """Mount enabled generated routes on the real app without running lifespan."""

    original_routes = list(app.router.routes)
    original_openapi = app.openapi_schema
    original_overrides = dict(app.dependency_overrides)
    original_capabilities = dict(CAPABILITIES)

    agents._pending_actions.clear()
    _rbac._pending_actions.clear()
    monkeypatch.setattr(settings, "CAPABILITY_REGISTRY_ENABLED", True)

    # Fail closed if a regression reaches a transmit chokepoint.
    monkeypatch.setattr(
        smtplib,
        "SMTP",
        MagicMock(side_effect=AssertionError("SMTP transport called")),
    )
    monkeypatch.setattr(
        email_service.EmailService,
        "_send_via_resend",
        AsyncMock(side_effect=AssertionError("Resend transport called")),
    )
    monkeypatch.setattr(
        email_service.EmailService,
        "_send_via_smtp",
        AsyncMock(side_effect=AssertionError("SMTP sender called")),
    )
    monkeypatch.setattr(
        whatsapp_service.WhatsAppService,
        "send_text",
        AsyncMock(side_effect=AssertionError("WhatsApp sender called")),
    )

    CAPABILITIES.clear()
    load_all_capabilities()
    original_handlers = {
        name: declaration.handler for name, declaration in CAPABILITIES.items()
    }

    capability_router = APIRouter(tags=["Capabilities"])
    mount_capability_routes(capability_router)
    app.include_router(capability_router, prefix=settings.API_V1_STR)

    user = SimpleNamespace(
        id=TEST_ID,
        role=UserRole.ADMIN,
        is_active=True,
        twgs=[],
    )

    async def override_current_user():
        return user

    async def override_db():
        yield object()

    app.dependency_overrides[get_current_active_user] = override_current_user
    app.dependency_overrides[get_db] = override_db

    yield app

    for name, handler in original_handlers.items():
        object.__setattr__(CAPABILITIES[name], "handler", handler)
    app.router.routes[:] = original_routes
    app.openapi_schema = original_openapi
    app.dependency_overrides.clear()
    app.dependency_overrides.update(original_overrides)
    CAPABILITIES.clear()
    CAPABILITIES.update(original_capabilities)
    agents._pending_actions.clear()
    _rbac._pending_actions.clear()


def _stub_handler(name: str, result) -> AsyncMock:
    handler = AsyncMock(return_value=result)
    object.__setattr__(CAPABILITIES[name], "handler", handler)
    return handler


def _route_for(name: str) -> tuple[str, str]:
    declaration = CAPABILITIES[name]
    assert declaration.http is not None
    method, path = declaration.http
    return method, f"{settings.API_V1_STR}{path}"


def test_all_thirteen_capabilities_mount_their_declared_http_routes(
    generated_capability_app,
):
    assert set(CAPABILITIES) == set(ALL_CAPABILITIES)
    assert all(CAPABILITIES[name].http is not None for name in ALL_CAPABILITIES)

    mounted = {
        (method, route.path): route
        for route in generated_capability_app.routes
        for method in getattr(route, "methods", set())
    }
    for name in ALL_CAPABILITIES:
        route = mounted[_route_for(name)]
        declaration = CAPABILITIES[name]
        if declaration.output_model is not None:
            assert route.response_model == declaration.output_model


@pytest.mark.parametrize("name", READ_CAPABILITIES)
@pytest.mark.asyncio
async def test_read_capabilities_serialize_through_fastapi(
    generated_capability_app,
    name,
):
    _stub_handler(name, _read_result_for(name))
    method, path = _route_for(name)

    transport = httpx.ASGITransport(app=generated_capability_app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.request(method, path, json=_payload_for(name))

    assert response.status_code == 200, response.text
    assert isinstance(response.json(), (dict, list))


@pytest.mark.parametrize("name", WRITE_CAPABILITIES)
@pytest.mark.asyncio
async def test_write_capabilities_return_confirmation_without_execution(
    generated_capability_app,
    name,
):
    handler = _stub_handler(name, {"unexpected": True})
    method, path = _route_for(name)

    transport = httpx.ASGITransport(app=generated_capability_app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.request(method, path, json=_payload_for(name))

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "confirmation_required"
    handler.assert_not_awaited()


@pytest.mark.parametrize("name", ALL_CAPABILITIES)
@pytest.mark.asyncio
async def test_generated_routes_reject_unauthenticated_calls_before_handlers(
    generated_capability_app,
    name,
):
    handler = _stub_handler(
        name, _read_result_for(name) if name in READ_CAPABILITIES else {}
    )
    generated_capability_app.dependency_overrides.pop(get_current_active_user)
    method, path = _route_for(name)

    transport = httpx.ASGITransport(app=generated_capability_app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.request(method, path, json=_payload_for(name))

    assert response.status_code in {401, 403}, response.text
    handler.assert_not_awaited()
