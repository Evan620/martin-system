"""Danger-tier execution and confirm-then-execute behavior."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, TypeAdapter

from app.capabilities.spec import (
    Capability,
    CapabilityAccessDenied,
    CapabilityContext,
)
from app.models.models import UserRole
from app.tools._rbac import propose_action, require_role


def validate_input(
    capability: Capability, payload: BaseModel | dict[str, Any]
) -> BaseModel:
    """Validate a raw payload with the declaration's sole input schema."""

    if isinstance(payload, capability.input_model):
        return payload
    return capability.input_model.model_validate(payload)


def serialize_output(capability: Capability, result: Any) -> Any:
    """Coerce a handler result through its shared HTTP/tool output contract."""

    if capability.output_model is None:
        return result
    adapter = TypeAdapter(capability.output_model)
    validated = adapter.validate_python(result, from_attributes=True)
    return adapter.dump_python(validated, mode="json")


def _role_scopes(capability: Capability) -> set[UserRole]:
    roles: set[UserRole] = set()
    for scope in capability.scopes:
        normalized = scope.strip().upper()
        try:
            roles.add(UserRole[normalized])
        except KeyError:
            try:
                roles.add(UserRole(normalized))
            except ValueError:
                continue
    return roles


def _ensure_user_role(capability: Capability, context: CapabilityContext) -> None:
    roles = _role_scopes(capability)
    if not roles:
        raise CapabilityAccessDenied(
            f"Capability '{capability.name}' has no user-role scope for HTTP access"
        )
    denied = require_role(context.user.role, roles)
    if denied:
        raise CapabilityAccessDenied(denied["reason"])


def _ensure_confirmation_role(
    capability: Capability,
    context: CapabilityContext,
) -> None:
    """Re-check declared user roles when a stored action is confirmed."""

    roles = _role_scopes(capability)
    if not roles:
        # Agent-only declarations were already checked before their action was
        # stored. Ownership is re-checked by /agents/execute.
        return
    denied = require_role(context.user.role, roles)
    if denied:
        raise CapabilityAccessDenied(denied["reason"])


def _render_summary(capability: Capability, validated: BaseModel) -> str:
    values = validated.model_dump(mode="json")
    try:
        return capability.summary_template.format(**values)
    except (KeyError, IndexError, ValueError) as exc:
        raise ValueError(
            f"Invalid summary_template for capability '{capability.name}': {exc}"
        ) from exc


async def invoke_capability(
    capability: Capability,
    payload: BaseModel | dict[str, Any],
    context: CapabilityContext,
    *,
    agent_id: str,
) -> Any:
    """Invoke a capability from an agent, applying scope and danger gates."""

    from app.capabilities.emit_tool import ensure_agent_access

    ensure_agent_access(capability, agent_id, context.user.role)
    validated = validate_input(capability, payload)

    if capability.danger == "read":
        result = await capability.handler(validated, context)
        return serialize_output(capability, result)

    envelope = propose_action(
        action_type=capability.name,
        summary=_render_summary(capability, validated),
        payload=validated.model_dump(mode="json"),
        irreversible=capability.danger == "destructive",
    )

    # This is the existing route-level pending-action store consumed first by
    # /agents/execute. Import lazily to avoid a capabilities <-> routes cycle.
    from app.api.routes.agents import _store_action

    _store_action(
        envelope["action_id"],
        str(context.user.id),
        capability.name,
        envelope["payload"],
    )
    return envelope


async def invoke_http_capability(
    capability: Capability,
    payload: BaseModel | dict[str, Any],
    context: CapabilityContext,
) -> Any:
    """Invoke a generated authenticated HTTP surface."""

    _ensure_user_role(capability, context)
    validated = validate_input(capability, payload)
    if capability.danger == "read":
        result = await capability.handler(validated, context)
        return serialize_output(capability, result)

    envelope = propose_action(
        action_type=capability.name,
        summary=_render_summary(capability, validated),
        payload=validated.model_dump(mode="json"),
        irreversible=capability.danger == "destructive",
    )
    from app.api.routes.agents import _store_action

    _store_action(
        envelope["action_id"],
        str(context.user.id),
        capability.name,
        envelope["payload"],
    )
    return envelope


async def execute_confirmed_capability(
    capability: Capability,
    payload: BaseModel | dict[str, Any],
    context: CapabilityContext,
) -> Any:
    """Run a previously approved write/destructive capability exactly once."""

    if capability.danger == "read":
        raise ValueError(f"Read capability '{capability.name}' has no pending action")
    _ensure_confirmation_role(capability, context)
    validated = validate_input(capability, payload)
    result = await capability.handler(validated, context)
    return serialize_output(capability, result)
