"""R8 — Geospatial analysis service.

Dispatches between live satellite (Microsoft Planetary Computer) and offline
fixtures based on the `LIVE_GEOSPATIAL_ENABLED` env var. Persists a single
ProjectGeospatialData row per project (DELETE-then-INSERT) so analysed_at
advances on every call."""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Project, ProjectGeospatialData
from app.services import geospatial_fixtures
from app.services.mpc_client import MPCClient
from app.services.geospatial_scoring import compute_boost

logger = logging.getLogger(__name__)

CACHE_TTL_DAYS = 30
COORD_TOLERANCE = 1e-4  # ~11m at the equator — beyond float-rounding noise


class GeospatialService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def analyse_project(
        self, project_id: uuid.UUID, force: bool = False
    ) -> Dict[str, Any]:
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

        # Cache check: skip live query if we have a fresh row for these coords.
        if not force:
            cached = await self._fresh_cache(project_id, lat, lon)
            if cached is not None:
                logger.info(
                    "Geospatial cache hit for %s (analysed %s)", project_id, cached.analysed_at
                )
                return self._row_to_dict(cached)

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

        return self._row_to_dict(row)

    @staticmethod
    def _row_to_dict(row: ProjectGeospatialData) -> Dict[str, Any]:
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

    async def _fresh_cache(
        self, project_id: uuid.UUID, lat: float, lon: float
    ) -> Optional[ProjectGeospatialData]:
        """Return the cached row if it's within CACHE_TTL_DAYS AND its
        coords match the project's current coords. Otherwise None.

        A coord change always invalidates the cache — the previous analysis
        was about a different point on the ground."""
        result = await self.db.execute(
            select(ProjectGeospatialData).where(ProjectGeospatialData.project_id == project_id)
        )
        row = result.scalar_one_or_none()
        if row is None or row.analysed_at is None:
            return None

        if datetime.utcnow() - row.analysed_at > timedelta(days=CACHE_TTL_DAYS):
            return None

        raw = row.raw_response or {}
        cached_lat = raw.get("lat")
        cached_lon = raw.get("lon")
        if cached_lat is None or cached_lon is None:
            return None  # Pre-cache rows have no coord stamp — treat as stale
        if abs(cached_lat - lat) > COORD_TOLERANCE or abs(cached_lon - lon) > COORD_TOLERANCE:
            return None

        return row

    async def _collect_signals(self, lat: float, lon: float) -> Tuple[Dict[str, Any], str]:
        """Live MPC satellite query when LIVE_GEOSPATIAL_ENABLED=1; fall back
        to fixtures otherwise or when 3+ signals fail."""
        if not MPCClient.is_configured():
            return geospatial_fixtures.lookup(lat, lon)

        # MPC client is sync (rasterio + STAC); run off the event loop so
        # the per-tile reads don't block other requests.
        live = await asyncio.to_thread(MPCClient().compute_signals, lat, lon)

        failed = sum(1 for v in live.values() if v is None)
        if failed >= 3:
            logger.warning("MPC returned %d nulls; falling back to fixtures", failed)
            return geospatial_fixtures.lookup(lat, lon)

        return live, "copernicus"


def get_geospatial_service(db: AsyncSession) -> GeospatialService:
    return GeospatialService(db)
