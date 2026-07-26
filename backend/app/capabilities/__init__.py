"""Martin capability registry."""

from app.capabilities.spec import (
    CAPABILITIES,
    Capability,
    CapabilityAccessDenied,
    CapabilityContext,
    capability,
    get_capability,
)


def load_reference_capabilities() -> None:
    """Import the initial declarations once, triggering their decorators."""

    from app.capabilities import reference  # noqa: F401


__all__ = [
    "CAPABILITIES",
    "Capability",
    "CapabilityAccessDenied",
    "CapabilityContext",
    "capability",
    "get_capability",
    "load_reference_capabilities",
]
