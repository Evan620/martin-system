"""Generate authenticated FastAPI routes from capability declarations."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user
from app.capabilities.gate import invoke_http_capability
from app.capabilities.spec import (
    CAPABILITIES,
    Capability,
    CapabilityAccessDenied,
    CapabilityContext,
)
from app.core.config import settings
from app.core.database import get_db
from app.models.models import User


def _endpoint_for(capability: Capability) -> Any:
    async def endpoint(
        payload: capability.input_model,
        current_user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db),
    ) -> Any:
        try:
            return await invoke_http_capability(
                capability,
                payload,
                CapabilityContext(user=current_user, db=db),
            )
        except CapabilityAccessDenied as exc:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(exc),
            ) from exc

    endpoint.__name__ = f"capability_{capability.name}"
    endpoint.__doc__ = capability.description
    return endpoint


def mount_capability_routes(router: APIRouter) -> None:
    """Mount one generated route for each enabled declaration with HTTP metadata."""

    if not settings.CAPABILITY_REGISTRY_ENABLED:
        return

    from app.capabilities import load_all_capabilities, validate_registry

    load_all_capabilities()
    validate_registry()
    mounted = {
        (method, route.path)
        for route in router.routes
        for method in getattr(route, "methods", set())
    }
    for declaration in CAPABILITIES.values():
        if declaration.http is None:
            continue
        method, path = declaration.http
        if (method, path) in mounted:
            continue
        router.add_api_route(
            path,
            _endpoint_for(declaration),
            methods=[method],
            name=declaration.name,
            summary=declaration.description,
        )
        mounted.add((method, path))
