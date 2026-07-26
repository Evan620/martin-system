"""Martin capability registry."""

from app.capabilities.spec import (
    CAPABILITIES,
    Capability,
    CapabilityAccessDenied,
    CapabilityContext,
    capability,
    get_capability,
)
from app.capabilities.loader import (
    RegistryValidationError,
    RegistryValidationIssue,
    RegistryValidationReport,
    load_all_capabilities,
    validate_registry,
)


def load_reference_capabilities() -> None:
    """Backward-compatible wrapper for the central declaration loader."""

    load_all_capabilities()


__all__ = [
    "CAPABILITIES",
    "Capability",
    "CapabilityAccessDenied",
    "CapabilityContext",
    "RegistryValidationError",
    "RegistryValidationIssue",
    "RegistryValidationReport",
    "capability",
    "get_capability",
    "load_all_capabilities",
    "load_reference_capabilities",
    "validate_registry",
]
