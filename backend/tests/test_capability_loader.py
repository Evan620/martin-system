"""Central capability loading and integrity validation contracts."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

import pytest
from pydantic import BaseModel

from app.capabilities import (
    load_all_capabilities,
    load_reference_capabilities,
    validate_registry,
)
from app.capabilities.loader import RegistryValidationError
from app.capabilities.spec import CAPABILITIES, Capability, CapabilityContext
from app.core.config import settings


class LoaderInput(BaseModel):
    value: str


async def async_handler(
    payload: LoaderInput,
    context: CapabilityContext,
) -> dict[str, str]:
    return {"value": payload.value}


def make_capability(
    name: str,
    *,
    danger: str = "read",
    http: tuple[str, str] | None = None,
    scopes: list[str] | None = None,
    summary_template: str = "Use {value}",
    agent_allowed: bool | None = None,
) -> Capability:
    return Capability(
        name=name,
        description=f"Test capability {name}",
        danger=danger,
        input_model=LoaderInput,
        handler=async_handler,
        scopes=["test_agent"] if scopes is None else scopes,
        http=http,
        summary_template=summary_template,
        agent_allowed=agent_allowed,
    )


def validation_error_codes(
    error: pytest.ExceptionInfo[RegistryValidationError],
) -> set[str]:
    return {issue.code for issue in error.value.report.errors}


@pytest.fixture(autouse=True)
def isolated_registry(monkeypatch):
    original_capabilities = dict(CAPABILITIES)
    CAPABILITIES.clear()
    monkeypatch.setattr(settings, "CAPABILITY_REGISTRY_ENABLED", True)
    yield
    CAPABILITIES.clear()
    CAPABILITIES.update(original_capabilities)


def test_double_load_is_idempotent_and_discovers_reference_capabilities():
    load_all_capabilities()
    first_load = dict(CAPABILITIES)

    load_all_capabilities()

    assert {
        "registry_approve_meeting_minutes",
        "registry_create_action_item",
        "registry_create_project",
        "registry_get_meeting_agenda",
        "registry_get_pipeline_settings",
        "registry_get_recurring_meeting",
        "registry_ingest_document",
        "registry_list_buyer_matches",
        "registry_list_dfi_matches",
        "registry_list_dfi_windows",
        "registry_list_twg_members",
        "registry_list_notifications",
        "registry_mark_all_notifications_read",
    }.issubset(CAPABILITIES)
    assert CAPABILITIES == first_load
    assert all(
        CAPABILITIES[name] is declaration
        for name, declaration in first_load.items()
    )
    assert validate_registry().valid is True


def test_reference_loader_remains_a_compatible_thin_wrapper():
    load_reference_capabilities()

    assert "registry_create_action_item" in CAPABILITIES
    assert "registry_list_twg_members" in CAPABILITIES


def test_flag_off_loader_is_a_no_op(monkeypatch):
    sentinel = make_capability("sentinel")
    CAPABILITIES[sentinel.name] = sentinel
    monkeypatch.setattr(settings, "CAPABILITY_REGISTRY_ENABLED", False)

    load_all_capabilities()

    assert CAPABILITIES == {"sentinel": sentinel}


def test_validate_registry_reports_duplicate_capability_names():
    declaration = make_capability("duplicate_name")
    CAPABILITIES["first_key"] = declaration
    CAPABILITIES["second_key"] = replace(declaration)

    with pytest.raises(RegistryValidationError) as error:
        validate_registry(existing_routes=[])

    assert "duplicate_capability_name" in validation_error_codes(error)


def test_validate_registry_reports_destructive_agent_exception_without_failing():
    declaration = make_capability(
        "audited_destructive",
        danger="destructive",
        agent_allowed=True,
    )
    CAPABILITIES[declaration.name] = declaration

    report = validate_registry(existing_routes=[])

    assert report.valid is True
    assert report.errors == ()
    assert report.destructive_agent_exceptions == ("audited_destructive",)
    assert report.as_dict()["destructive_agent_exceptions"] == [
        "audited_destructive"
    ]


def test_validate_registry_rejects_capability_http_path_collisions():
    first = make_capability("first_path_owner", http=("GET", "/same/path"))
    second = make_capability("second_path_owner", http=("POST", "/same/path/"))
    CAPABILITIES[first.name] = first
    CAPABILITIES[second.name] = second

    with pytest.raises(RegistryValidationError) as error:
        validate_registry(existing_routes=[])

    assert "capability_http_path_collision" in validation_error_codes(error)


def test_validate_registry_rejects_existing_route_path_collision():
    declaration = make_capability(
        "legacy_route_collision",
        http=("GET", "/action-items/"),
    )
    CAPABILITIES[declaration.name] = declaration

    with pytest.raises(RegistryValidationError) as error:
        validate_registry()

    assert "existing_http_path_collision" in validation_error_codes(error)


def test_bad_summary_template_is_caught_before_runtime():
    declaration = make_capability(
        "bad_summary",
        summary_template="Use {missing_field}",
    )
    CAPABILITIES[declaration.name] = declaration

    with pytest.raises(RegistryValidationError) as error:
        validate_registry(existing_routes=[])

    assert "invalid_summary_template" in validation_error_codes(error)
    assert "missing_field" in str(error.value)


def test_validate_registry_rejects_non_pydantic_model_and_sync_handler():
    invalid_model = make_capability("invalid_model")
    object.__setattr__(invalid_model, "input_model", object)

    sync_handler = make_capability("sync_handler")

    def handler(payload: LoaderInput, context: CapabilityContext) -> Any:
        return payload

    object.__setattr__(sync_handler, "handler", handler)
    CAPABILITIES[invalid_model.name] = invalid_model
    CAPABILITIES[sync_handler.name] = sync_handler

    with pytest.raises(RegistryValidationError) as error:
        validate_registry(existing_routes=[])

    assert {"invalid_input_model", "handler_not_async"}.issubset(
        validation_error_codes(error)
    )


def test_validate_registry_rejects_empty_scopes():
    declaration = make_capability("empty_scopes", scopes=[])
    CAPABILITIES[declaration.name] = declaration

    with pytest.raises(RegistryValidationError) as error:
        validate_registry(existing_routes=[])

    assert "empty_scopes" in validation_error_codes(error)
