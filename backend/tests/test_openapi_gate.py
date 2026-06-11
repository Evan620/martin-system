"""P1-7: /docs, /redoc and the OpenAPI schema must not be exposed in production.

Each case rebuilds the FastAPI app by reloading ``app.core.config`` and
``app.main`` after monkeypatching the environment, so the app is constructed
exactly as it would be at process start under that environment.
"""
import importlib

import pytest
from httpx import ASGITransport, AsyncClient


def _reload_app_module():
    import app.core.config as config_module
    import app.main as main_module

    importlib.reload(config_module)
    return importlib.reload(main_module)


@pytest.fixture
def build_app(monkeypatch):
    """Factory that rebuilds the app under a controlled environment."""

    def _build(**env):
        monkeypatch.delenv("ENVIRONMENT", raising=False)
        monkeypatch.delenv("RAILWAY_ENVIRONMENT", raising=False)
        for key, value in env.items():
            monkeypatch.setenv(key, value)
        return _reload_app_module().app

    yield _build

    # Restore the ambient environment first, then rebuild module state so the
    # rest of the suite sees the original app/settings singletons.
    monkeypatch.undo()
    _reload_app_module()


async def _get(app, path: str):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.get(path)


async def test_dev_default_serves_docs_and_openapi(build_app):
    app = build_app()
    assert (await _get(app, "/docs")).status_code == 200
    # openapi_url is customized to live under the API prefix in this app
    assert (await _get(app, "/api/v1/openapi.json")).status_code == 200


async def test_production_env_disables_docs_and_openapi(build_app):
    app = build_app(ENVIRONMENT="production")
    assert (await _get(app, "/docs")).status_code == 404
    assert (await _get(app, "/redoc")).status_code == 404
    assert (await _get(app, "/openapi.json")).status_code == 404
    assert (await _get(app, "/api/v1/openapi.json")).status_code == 404


async def test_railway_environment_presence_treated_as_production(build_app):
    # Safer default: Railway always injects RAILWAY_ENVIRONMENT, so its mere
    # presence gates the docs even if ENVIRONMENT was never set.
    app = build_app(RAILWAY_ENVIRONMENT="production")
    assert (await _get(app, "/docs")).status_code == 404
    assert (await _get(app, "/api/v1/openapi.json")).status_code == 404


async def test_production_keeps_health_endpoint(build_app):
    app = build_app(ENVIRONMENT="production")
    assert (await _get(app, "/health")).status_code == 200
