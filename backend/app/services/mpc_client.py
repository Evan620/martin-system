"""R8 satellite client backed by Microsoft Planetary Computer.

MPC has no authentication, no per-call quota, and exposes the four datasets
we need via a single STAC catalog. We read small windows directly from
Cloud-Optimised GeoTIFFs over HTTP — no tile downloads, no server-side
compute.

Datasets used:
- Sentinel-2 L2A          → NDVI from B04/B08
- JRC Global Surface Water → water proximity (occurrence > 50%)
- ESA WorldCover 2021     → land-use class + smallholder-likely share
- io-lulc-annual-v02 (Esri)→ EUDR risk via 2020 vs latest year comparison

Set environment variable LIVE_GEOSPATIAL_ENABLED=1 to dispatch to this
client; otherwise the service stays in fixture mode."""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional, Tuple

import numpy as np
import pystac_client
import planetary_computer
import rasterio
from rasterio.warp import transform_bounds
from rasterio.windows import from_bounds

logger = logging.getLogger(__name__)

_STAC_URL = "https://planetarycomputer.microsoft.com/api/stac/v1"
_BBOX_RADIUS_DEG = 0.0045  # ~500m at the equator


class MPCClient:
    """Live satellite client. Kept stateless; one instance per analysis call."""

    @classmethod
    def is_configured(cls) -> bool:
        """True if live mode is enabled via env. MPC itself needs no auth,
        but we still gate so the local mirror defaults to fixtures."""
        return os.environ.get("LIVE_GEOSPATIAL_ENABLED", "").lower() in ("1", "true", "yes")

    def __init__(self) -> None:
        self._catalog: Optional[pystac_client.Client] = None

    def _cat(self) -> pystac_client.Client:
        if self._catalog is None:
            self._catalog = pystac_client.Client.open(
                _STAC_URL, modifier=planetary_computer.sign_inplace
            )
        return self._catalog

    @staticmethod
    def _bbox(lat: float, lon: float, radius_deg: float = _BBOX_RADIUS_DEG) -> Tuple[float, float, float, float]:
        return (lon - radius_deg, lat - radius_deg, lon + radius_deg, lat + radius_deg)

    @staticmethod
    def _read_window(item, asset_name: str, bbox_4326: Tuple[float, float, float, float]) -> np.ndarray:
        """Read a tiny window from a COG asset, projecting the bbox to the
        asset's native CRS first."""
        href = item.assets[asset_name].href
        with rasterio.open(href) as ds:
            bbox_native = transform_bounds("EPSG:4326", ds.crs, *bbox_4326)
            win = from_bounds(*bbox_native, transform=ds.transform)
            return ds.read(1, window=win)

    def _safe(self, name: str, fn):
        try:
            return fn()
        except Exception as e:  # noqa: BLE001
            logger.warning("MPC %s failed: %s", name, e)
            return None

    def compute_signals(self, lat: float, lon: float) -> Dict[str, Any]:
        """Run the four signal queries. Per-signal failures return None."""
        ndvi = self._safe("ndvi", lambda: self._fetch_ndvi(lat, lon))
        water = self._safe("water", lambda: self._fetch_water_proximity(lat, lon))
        land = self._safe("land_use", lambda: self._fetch_land_use(lat, lon))
        defor = self._safe("eudr", lambda: self._fetch_eudr(lat, lon))

        return {
            "ndvi": ndvi,
            "water_proximity_km": water,
            "land_use_description": (land or {}).get("description") if land else None,
            "land_use_smallholder_pct": (land or {}).get("smallholder_pct") if land else None,
            "deforestation_risk": defor,
        }

    # --- Signal 1: NDVI from Sentinel-2 -----------------------------------

    def _fetch_ndvi(self, lat: float, lon: float) -> Optional[float]:
        """Most-recent low-cloud Sentinel-2 L2A scene over the last 60 days
        (180-day fallback). NDVI = (B08 - B04) / (B08 + B04)."""
        from datetime import datetime, timedelta, timezone
        now = datetime.now(timezone.utc)
        bbox = self._bbox(lat, lon)

        for window_days in (60, 180):
            start = (now - timedelta(days=window_days)).strftime("%Y-%m-%d")
            end = now.strftime("%Y-%m-%d")
            search = self._cat().search(
                collections=["sentinel-2-l2a"],
                bbox=bbox,
                datetime=f"{start}/{end}",
                query={"eo:cloud_cover": {"lt": 30}},
                max_items=1,
            )
            items = list(search.items())
            if not items:
                continue
            item = items[0]
            href_red = item.assets["B04"].href
            href_nir = item.assets["B08"].href
            with rasterio.open(href_red) as red, rasterio.open(href_nir) as nir:
                bbox_native = transform_bounds("EPSG:4326", red.crs, *bbox)
                win = from_bounds(*bbox_native, transform=red.transform)
                r = red.read(1, window=win).astype("float32")
                n = nir.read(1, window=win).astype("float32")
            valid = (n + r) > 0
            if not valid.any():
                continue
            ndvi = (n - r) / (n + r + 1e-9)
            return round(float(ndvi[valid].mean()), 3)
        return None

    # --- Signal 2: Water proximity (JRC Global Surface Water) -------------

    def _fetch_water_proximity(self, lat: float, lon: float) -> Optional[float]:
        """Progressive bbox expansion (1, 2, 5, 10, 25, 50 km) looking for
        any pixel with occurrence > 50%. Returns the first hit radius in km."""
        search = self._cat().search(
            collections=["jrc-gsw"], bbox=self._bbox(lat, lon), max_items=1
        )
        items = list(search.items())
        if not items:
            return None
        item = items[0]
        href = item.assets["occurrence"].href

        with rasterio.open(href) as ds:
            for radius_km in (1, 2, 5, 10, 25, 50):
                r = radius_km / 111.0
                bbox = (lon - r, lat - r, lon + r, lat + r)
                bbox_native = transform_bounds("EPSG:4326", ds.crs, *bbox)
                win = from_bounds(*bbox_native, transform=ds.transform)
                arr = ds.read(1, window=win)
                if int((arr > 50).sum()) > 0:
                    return float(radius_km)
        return 50.0

    # --- Signal 3: Land use (ESA WorldCover) ------------------------------

    _WORLDCOVER = {
        10: ("Tree cover", False),
        20: ("Shrubland", False),
        30: ("Grassland", True),
        40: ("Cropland", True),
        50: ("Built-up", False),
        60: ("Bare / sparse vegetation", False),
        70: ("Snow / ice", False),
        80: ("Permanent water bodies", False),
        90: ("Herbaceous wetland", False),
        95: ("Mangroves", False),
        100: ("Moss / lichen", False),
    }

    def _fetch_land_use(self, lat: float, lon: float) -> Optional[Dict[str, Any]]:
        """Majority WorldCover class + share of smallholder-likely classes
        (grassland + cropland)."""
        search = self._cat().search(
            collections=["esa-worldcover"], bbox=self._bbox(lat, lon), max_items=1
        )
        items = list(search.items())
        if not items:
            return None
        arr = self._read_window(items[0], "map", self._bbox(lat, lon))
        unique, counts = np.unique(arr, return_counts=True)
        if len(unique) == 0:
            return None
        total = int(counts.sum())
        majority = int(unique[int(counts.argmax())])
        smallholder = sum(int(c) for v, c in zip(unique.tolist(), counts.tolist())
                          if self._WORLDCOVER.get(int(v), (None, False))[1])
        label, _ = self._WORLDCOVER.get(majority, ("Unknown land cover", False))
        return {"description": label, "smallholder_pct": round(100.0 * smallholder / total, 1)}

    # --- Signal 4: EUDR risk (Esri io-lulc-annual-v02, 2020 vs latest) ---

    def _fetch_eudr(self, lat: float, lon: float) -> Optional[str]:
        """EUDR cutoff is 31 Dec 2020. Compare 2020 land cover (Esri 9-class)
        against the most recent year. If 2020 was Trees (class 2) and the
        latest is not Trees → high. If still Trees → low. Otherwise the
        signal isn't informative (low)."""
        bbox = self._bbox(lat, lon)

        def majority_class(year: int) -> Optional[int]:
            search = self._cat().search(
                collections=["io-lulc-annual-v02"],
                bbox=bbox,
                datetime=f"{year}-01-01/{year}-12-31",
                max_items=1,
            )
            items = list(search.items())
            if not items:
                return None
            arr = self._read_window(items[0], "data", bbox)
            unique, counts = np.unique(arr, return_counts=True)
            if len(unique) == 0:
                return None
            return int(unique[int(counts.argmax())])

        c_2020 = majority_class(2020)
        # Try most recent year first, fall back through 2024/2023
        c_latest = None
        for y in (2024, 2023, 2022):
            c_latest = majority_class(y)
            if c_latest is not None:
                break
        if c_2020 is None or c_latest is None:
            return "low"

        # Esri 9-class: 2 = Trees
        was_forest = c_2020 == 2
        is_forest_now = c_latest == 2
        if was_forest and not is_forest_now:
            return "high"
        if was_forest and is_forest_now:
            return "low"
        return "low"
