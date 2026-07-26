"""Capability declarations and the process-wide capability registry."""

from __future__ import annotations

import inspect
import re
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Literal, Optional

from pydantic import BaseModel


Danger = Literal["read", "write", "destructive"]
CapabilityHandler = Callable[[BaseModel, "CapabilityContext"], Awaitable[Any]]
_CAPABILITY_NAME = re.compile(r"^[a-z][a-z0-9_]*$")


class CapabilityAccessDenied(PermissionError):
    """Raised when an agent or user is outside a capability's declared scopes."""


@dataclass(frozen=True)
class CapabilityContext:
    """Authenticated execution context passed to every capability handler."""

    user: Any
    db: Any


@dataclass(frozen=True)
class Capability:
    """The single declaration from which Martin's capability surfaces are emitted."""

    name: str
    description: str
    danger: Danger
    input_model: type[BaseModel]
    handler: CapabilityHandler
    scopes: list[str]
    http: Optional[tuple[str, str]]
    output_model: Any = None
    tool_exposed: bool = True
    summary_template: str = ""
    # None is an internal declaration-time sentinel. __post_init__ resolves it
    # to a bool, defaulting destructive capabilities to agent-denied.
    agent_allowed: Optional[bool] = None

    def __post_init__(self) -> None:
        if not _CAPABILITY_NAME.fullmatch(self.name):
            raise ValueError(
                f"Capability name '{self.name}' must be a snake_case identifier"
            )
        if self.danger not in {"read", "write", "destructive"}:
            raise ValueError(f"Unsupported capability danger tier: {self.danger}")
        if not inspect.isclass(self.input_model) or not issubclass(
            self.input_model, BaseModel
        ):
            raise TypeError("input_model must be a Pydantic BaseModel subclass")
        if not inspect.iscoroutinefunction(self.handler):
            raise TypeError("Capability handlers must be async functions")
        if not self.description.strip():
            raise ValueError("Capability description must not be empty")
        if not all(isinstance(scope, str) and scope.strip() for scope in self.scopes):
            raise ValueError("Capability scopes must be non-empty strings")
        if self.http is not None:
            method, path = self.http
            if method.upper() not in {
                "GET",
                "POST",
                "PUT",
                "PATCH",
                "DELETE",
                "OPTIONS",
                "HEAD",
            }:
                raise ValueError(f"Unsupported capability HTTP method: {method}")
            if not path.startswith("/"):
                raise ValueError("Capability HTTP paths must start with '/'")
            object.__setattr__(self, "http", (method.upper(), path))

        if self.agent_allowed is None:
            object.__setattr__(
                self,
                "agent_allowed",
                self.danger != "destructive",
            )


CAPABILITIES: dict[str, Capability] = {}


def capability(
    *,
    name: str,
    description: str,
    danger: Danger,
    input_model: type[BaseModel],
    scopes: list[str],
    http: Optional[tuple[str, str]] = None,
    output_model: Any = None,
    tool_exposed: bool = True,
    summary_template: str = "",
    agent_allowed: Optional[bool] = None,
) -> Callable[[CapabilityHandler], CapabilityHandler]:
    """Declare and register a capability when its module is imported."""

    def decorator(handler: CapabilityHandler) -> CapabilityHandler:
        if name in CAPABILITIES:
            raise ValueError(f"Duplicate capability name: {name}")

        declaration = Capability(
            name=name,
            description=description,
            danger=danger,
            input_model=input_model,
            handler=handler,
            scopes=list(scopes),
            http=http,
            output_model=output_model,
            tool_exposed=tool_exposed,
            summary_template=summary_template,
            agent_allowed=agent_allowed,
        )
        CAPABILITIES[name] = declaration
        setattr(handler, "__capability__", declaration)
        return handler

    return decorator


def get_capability(name: str) -> Optional[Capability]:
    """Return a capability declaration by its tool/action name."""

    return CAPABILITIES.get(name)
