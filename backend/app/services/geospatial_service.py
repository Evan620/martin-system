"""R8 — Geospatial analysis service.

Dispatches between live Copernicus and offline fixtures based on whether
COPERNICUS_CLIENT_ID is set in the environment. Persists a single
ProjectGeospatialData row per project (DELETE-then-INSERT) so analysed_at
advances on every call."""
from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any, Dict, Tuple

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Project, ProjectGeospatialData
from app.services import geospatial_fixtures
from app.services.copernicus_client import CopernicusClient, CopernicusAuthError
from app.services.geospatial_scoring import compute_boost

logger = logging.getLogger(__name__)


class GeospatialService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def analyse_project(self, project_id: uuid.UUID) -> Dict[str, Any]:
        result = await self.db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        if project is None:
            return {"error": "project_not_found"}
        if project.site_lat is None or project.site_lon is None:
            return {
                "error": "no_coordinates",
                "message": "Project has no site coordinates set. Update site_lat and site_lon on the project, then retry.",
            }

        lat, lon = float(project.site_lat), float(project.site_lon)
        payload, source = await self._collect_signals(lat, lon)
        boost = compute_boost(
            payload.get("ndvi"),
            payload.get("water_proximity_km"),
            payload.get("land_use_smallholder_pct"),
            payload.get("deforestation_risk"),
        )

        await self.db.execute(
            delete(ProjectGeospatialData).where(ProjectGeospatialData.project_id == project_id)
        )
        row = ProjectGeospatialData(
            project_id=project_id,
            ndvi=payload.get("ndvi") or 0.0,
            water_proximity_km=payload.get("water_proximity_km") or 0.0,
            land_use_description=payload.get("land_use_description") or "Unknown",
            land_use_smallholder_pct=payload.get("land_use_smallholder_pct") or 0.0,
            deforestation_risk=payload.get("deforestation_risk") or "high",
            geo_score_boost=boost,
            source=source,
            is_demo=(source != "copernicus"),
            raw_response={"source": source, "lat": lat, "lon": lon, "raw": payload},
        )
        self.db.add(row)
        await self.db.commit()
        await self.db.refresh(row)

        return {
            "id": str(row.id),
            "project_id": str(row.project_id),
            "ndvi": row.ndvi,
            "water_proximity_km": row.water_proximity_km,
            "land_use_description": row.land_use_description,
            "land_use_smallholder_pct": row.land_use_smallholder_pct,
            "deforestation_risk": row.deforestation_risk,
            "geo_score_boost": row.geo_score_boost,
            "source": row.source,
            "is_demo": row.is_demo,
            "analysed_at": row.analysed_at.isoformat() if row.analysed_at else None,
        }

    async def _collect_signals(self, lat: float, lon: float) -> Tuple[Dict[str, Any], str]:
        """Live Copernicus when configured; fall back to fixtures otherwise
        or when 3+ signals fail."""
        if not CopernicusClient.is_configured():
            return geospatial_fixtures.lookup(lat, lon)

        try:
            client = CopernicusClient()
            # CopernicusClient uses sync httpx — run it off the event loop so a
            # slow live call doesn't block other requests.
            live = await asyncio.to_thread(client.compute_signals, lat, lon)
        except CopernicusAuthError as e:
            logger.warning("Copernicus auth failed, falling back to fixtures: %s", e)
            return geospatial_fixtures.lookup(lat, lon)

        failed = sum(1 for v in live.values() if v is None)
        if failed >= 3:
            logger.warning("Copernicus returned %d nulls; falling back to fixtures", failed)
            return geospatial_fixtures.lookup(lat, lon)

        return live, "copernicus"


def get_geospatial_service(db: AsyncSession) -> GeospatialService:
    return GeospatialService(db)
