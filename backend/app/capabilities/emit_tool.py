"""Emit OpenAI-compatible tools and authenticated wrappers from capabilities."""

from __future__ import annotations

import fnmatch
import uuid
from typing import Any, Callable, Optional

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.capabilities.spec import (
    CAPABILITIES,
    Capability,
    CapabilityAccessDenied,
    CapabilityContext,
)
from app.core.config import settings
from app.models.models import User, UserRole
from app.tools._rbac import get_user_context, require_role


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


def _agent_scopes(capability: Capability) -> list[str]:
    role_names = {role.name for role in UserRole} | {role.value for role in UserRole}
    return [
        scope for scope in capability.scopes if scope.strip().upper() not in role_names
    ]


def ensure_agent_access(
    capability: Capability,
    agent_id: str,
    user_role: Optional[UserRole] = None,
) -> None:
    """Apply declaration scopes and destructive default-deny to an agent call."""

    if not capability.tool_exposed:
        raise CapabilityAccessDenied(
            f"Capability '{capability.name}' is not exposed as an agent tool"
        )
    if not capability.agent_allowed:
        raise CapabilityAccessDenied(
            f"Capability '{capability.name}' is not allowed for agent execution"
        )

    agent_scopes = _agent_scopes(capability)
    if agent_scopes and not any(
        fnmatch.fnmatchcase(agent_id, scope) for scope in agent_scopes
    ):
        raise CapabilityAccessDenied(
            f"Agent '{agent_id}' is outside capability '{capability.name}' scopes"
        )

    roles = _role_scopes(capability)
    if roles and user_role is not None:
        denied = require_role(user_role, roles)
        if denied:
            raise CapabilityAccessDenied(denied["reason"])

    if not agent_scopes and not roles:
        raise CapabilityAccessDenied(
            f"Capability '{capability.name}' has no permitted scopes"
        )
    if not agent_scopes and roles and user_role is None:
        raise CapabilityAccessDenied(
            f"Capability '{capability.name}' requires authenticated role context"
        )


def _inline_schema_refs(value: Any, definitions: dict[str, Any]) -> Any:
    if isinstance(value, list):
        return [_inline_schema_refs(item, definitions) for item in value]
    if not isinstance(value, dict):
        return value

    if "$ref" in value:
        ref_name = value["$ref"].rsplit("/", 1)[-1]
        resolved = dict(definitions.get(ref_name, {}))
        resolved.update({key: item for key, item in value.items() if key != "$ref"})
        return _inline_schema_refs(resolved, definitions)

    return {
        key: _inline_schema_refs(item, definitions)
        for key, item in value.items()
        if key not in {"$defs", "definitions"}
    }


def parameter_schema(input_model: type[BaseModel]) -> dict[str, Any]:
    """Return a self-contained JSON schema derived only from the input model."""

    raw = input_model.model_json_schema(mode="validation")
    definitions = raw.get("$defs", raw.get("definitions", {}))
    schema = _inline_schema_refs(raw, definitions)
    schema.pop("title", None)
    schema.setdefault("type", "object")
    schema.setdefault("properties", {})
    schema.setdefault("required", [])
    return schema


def tool_definition(capability: Capability) -> dict[str, Any]:
    """Emit the OpenAI tool shape consumed by AgentLoop."""

    return {
        "type": "function",
        "function": {
            "name": capability.name,
            "description": capability.description,
            "parameters": parameter_schema(capability.input_model),
        },
    }


async def _execute_tool_call(
    capability: Capability,
    agent_id: str,
    payload: dict[str, Any],
    injected_user_id: Optional[str] = None,
) -> Any:
    from app.core.database import get_db_session_context

    bound_context = get_user_context()
    user_id = bound_context[0] if bound_context is not None else injected_user_id
    if not user_id:
        raise CapabilityAccessDenied(
            f"Capability '{capability.name}' requires authenticated user context"
        )
    try:
        user_uuid = uuid.UUID(str(user_id))
    except (TypeError, ValueError) as exc:
        raise CapabilityAccessDenied(
            "Authenticated capability user id is invalid"
        ) from exc

    async with get_db_session_context() as db:
        user = (
            await db.execute(
                select(User)
                .where(User.id == user_uuid)
                .options(selectinload(User.twgs))
            )
        ).scalar_one_or_none()
        if user is None or not user.is_active:
            raise CapabilityAccessDenied("Authenticated capability user was not found")

        from app.capabilities.gate import invoke_capability

        return await invoke_capability(
            capability,
            payload,
            CapabilityContext(user=user, db=db),
            agent_id=agent_id,
        )


def build_tool_handler(capability: Capability, agent_id: str) -> Callable[..., Any]:
    """Bind an agent id while retaining AgentLoop's trusted user-id injection."""

    if "user_id" in capability.input_model.model_fields:
        # A capability may legitimately accept a target user_id. Never confuse
        # that field with authentication; use only the request ContextVar.
        async def handler(**kwargs: Any) -> Any:
            return await _execute_tool_call(capability, agent_id, kwargs)

    else:

        async def handler(user_id: Optional[str] = None, **kwargs: Any) -> Any:
            return await _execute_tool_call(
                capability,
                agent_id,
                kwargs,
                injected_user_id=user_id,
            )

    handler.__name__ = f"{capability.name}_tool_handler"
    handler.__doc__ = capability.description
    setattr(handler, "__capability_name__", capability.name)
    return handler


def registry_tools_for(
    agent_id: str,
) -> tuple[list[dict[str, Any]], dict[str, Callable[..., Any]]]:
    """Return capability tool definitions and handlers filtered for an agent."""

    if not settings.CAPABILITY_REGISTRY_ENABLED:
        return [], {}

    bound_context = get_user_context()
    user_role = bound_context[1] if bound_context is not None else None
    definitions: list[dict[str, Any]] = []
    handlers: dict[str, Callable[..., Any]] = {}
    for declaration in CAPABILITIES.values():
        try:
            ensure_agent_access(declaration, agent_id, user_role)
        except CapabilityAccessDenied:
            continue
        definitions.append(tool_definition(declaration))
        handlers[declaration.name] = build_tool_handler(declaration, agent_id)
    return definitions, handlers


def register_capability_tools(tool_registry: Any) -> None:
    """Add enabled capability declarations to the existing ToolRegistry."""

    if not settings.CAPABILITY_REGISTRY_ENABLED:
        return

    existing = set(tool_registry.list_tools())
    for declaration in CAPABILITIES.values():
        if not declaration.tool_exposed:
            continue
        if declaration.name in existing:
            registered = tool_registry._tools[declaration.name]
            if (
                getattr(registered.handler, "__capability_name__", None)
                == declaration.name
            ):
                continue
            raise ValueError(
                f"Capability tool name collides with existing tool: {declaration.name}"
            )
        schema = parameter_schema(declaration.input_model)
        tool_registry.register(
            name=declaration.name,
            description=declaration.description,
            parameters=schema.get("properties", {}),
            handler=build_tool_handler(declaration, ""),
            required_params=schema.get("required", []),
        )
        existing.add(declaration.name)


async def execute_registry_tool(
    capability: Capability,
    payload: dict[str, Any],
    agent_id: str,
) -> Any:
    """Secure execution entry used by ToolRegistry.execute_tool."""

    bound_context = get_user_context()
    role = bound_context[1] if bound_context is not None else None
    ensure_agent_access(capability, agent_id, role)
    return await _execute_tool_call(capability, agent_id, payload)
