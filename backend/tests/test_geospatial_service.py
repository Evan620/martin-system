"""R8 — GeospatialService dispatch tests.

NOTE: These tests depend on a `sample_project_factory` fixture that is not yet
defined in `backend/tests/conftest.py` (only `db_session` exists). They will
ERROR on collection until that factory is added. The file is committed now as
a placeholder so the test surface tracks alongside the service refactor —
wiring the factory is a separate task.

Coverage:
- Missing site coordinates → returns no_coordinates error
- Known fixture coords (Bouaké, CI) → source=fixture, is_demo=True, boost 0..15
- Unknown coords → source=stub, is_demo=True
- Repeated calls → upsert (single row per project)
"""
import os
import uuid
import pytest
from sqlalchemy import select

from app.models.models import Project, ProjectGeospatialData
from app.services.geospatial_service import GeospatialService


@pytest.fixture(autouse=True)
def _unset_copernicus_creds(monkeypatch):
    monkeypatch.delenv("COPERNICUS_CLIENT_ID", raising=False)
    monkeypatch.delenv("COPERNICUS_CLIENT_SECRET", raising=False)


@pytest.mark.asyncio
async def test_analyse_project_returns_error_without_coords(db_session, sample_project_factory):
    project = await sample_project_factory(site_lat=None, site_lon=None)
    svc = GeospatialService(db_session)
    result = await svc.analyse_project(project.id)
    assert result.get("error") == "no_coordinates"


@pytest.mark.asyncio
async def test_analyse_project_uses_fixture_for_bouake(db_session, sample_project_factory):
    project = await sample_project_factory(site_lat=7.69, site_lon=-5.03)
    svc = GeospatialService(db_session)
    result = await svc.analyse_project(project.id)
    assert result["source"] == "fixture"
    assert result["is_demo"] is True
    assert 0 <= result["geo_score_boost"] <= 15


@pytest.mark.asyncio
async def test_analyse_project_uses_stub_for_unknown_coords(db_session, sample_project_factory):
    project = await sample_project_factory(site_lat=1.0, site_lon=1.0)
    svc = GeospatialService(db_session)
    result = await svc.analyse_project(project.id)
    assert result["source"] == "stub"
    assert result["is_demo"] is True


@pytest.mark.asyncio
async def test_analyse_project_upserts_row(db_session, sample_project_factory):
    project = await sample_project_factory(site_lat=7.69, site_lon=-5.03)
    svc = GeospatialService(db_session)
    await svc.analyse_project(project.id)
    await svc.analyse_project(project.id)
    rows = (await db_session.execute(
        select(ProjectGeospatialData).where(ProjectGeospatialData.project_id == project.id)
    )).scalars().all()
    assert len(rows) == 1
