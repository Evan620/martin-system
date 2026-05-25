"""R8 Copernicus Data Space (CDSE) client.

Authenticates via OAuth2 client_credentials against the CDSE Keycloak realm
and runs Sentinel-Hub-compatible Process API requests. Tokens are cached
in-memory and refreshed proactively before expiry."""
from __future__ import annotations

import logging
import os
import time
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)


class CopernicusAuthError(RuntimeError):
    """Raised when Copernicus credentials are rejected or absent."""


class CopernicusClient:
    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        base_url: Optional[str] = None,
        auth_url: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
    ) -> None:
        self._client_id = client_id or os.environ.get("COPERNICUS_CLIENT_ID")
        self._client_secret = client_secret or os.environ.get("COPERNICUS_CLIENT_SECRET")
        self._base_url = (base_url or os.environ.get("COPERNICUS_BASE_URL")
                          or "https://sh.dataspace.copernicus.eu").rstrip("/")
        self._auth_url = (auth_url or os.environ.get("COPERNICUS_AUTH_URL")
                          or "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token")
        self._timeout = int(timeout_seconds or os.environ.get("COPERNICUS_TIMEOUT_SECONDS", "60"))

        self._token: Optional[str] = None
        self._token_expires_at: float = 0.0  # epoch seconds

    @classmethod
    def is_configured(cls) -> bool:
        """True iff client_id is set in env. Service uses this to dispatch."""
        return bool(os.environ.get("COPERNICUS_CLIENT_ID"))

    def _get_token(self) -> str:
        """Return a valid access token, refreshing if within 60s of expiry."""
        if self._token and time.time() < self._token_expires_at - 60:
            return self._token

        if not self._client_id or not self._client_secret:
            raise CopernicusAuthError("COPERNICUS_CLIENT_ID/SECRET not set")

        try:
            resp = httpx.post(
                self._auth_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                },
                timeout=self._timeout,
            )
        except httpx.HTTPError as e:
            raise CopernicusAuthError(f"auth request failed: {e}") from e

        if resp.status_code != 200:
            raise CopernicusAuthError(f"auth returned {resp.status_code}: {resp.text[:200]}")

        body = resp.json()
        self._token = body["access_token"]
        self._token_expires_at = time.time() + int(body.get("expires_in", 600))
        return self._token

    def _process_request(self, payload: Dict[str, Any]) -> bytes:
        """POST to the Process API. Returns raw response bytes.

        NOTE: The live request paths (dataset type identifiers, Process API vs
        Statistics API endpoint shape, BYOC collection wiring) are designed
        against the CDSE documentation but have not been verified against live
        credentials. When credentials are provisioned, the integration test in
        `tests/test_copernicus_client_integration.py` will exercise this end-to-end
        and any shape mismatches should surface there. The service layer treats
        any per-signal failure as `None` via `_safe_call` and degrades to fixture
        mode, so misconfiguration here cannot break the local mirror."""
        token = self._get_token()
        resp = httpx.post(
            f"{self._base_url}/api/v1/process",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
            timeout=self._timeout,
        )
        resp.raise_for_status()
        return resp.content

    _BBOX_RADIUS_DEG = 0.0045  # ~500m

    def _bbox(self, lat: float, lon: float) -> list[float]:
        r = self._BBOX_RADIUS_DEG
        return [lon - r, lat - r, lon + r, lat + r]

    def _safe_call(self, name: str, fn):
        """Run fn() and return its result, or None on any error (logged)."""
        try:
            return fn()
        except Exception as e:  # noqa: BLE001 — we genuinely want any failure → None
            logger.warning("Copernicus %s failed: %s", name, e)
            return None

    def compute_signals(self, lat: float, lon: float) -> Dict[str, Any]:
        """Call the four Process API queries and assemble a payload dict.

        Failures on individual signals return None for that field; the caller
        decides whether to degrade to fixture mode."""
        ndvi = self._safe_call("ndvi", lambda: self._fetch_ndvi(lat, lon))
        water_km = self._safe_call("water", lambda: self._fetch_water_proximity(lat, lon))
        land = self._safe_call("land_use", lambda: self._fetch_land_use(lat, lon))
        defor = self._safe_call("eudr", lambda: self._fetch_eudr(lat, lon))

        return {
            "ndvi": ndvi,
            "water_proximity_km": water_km,
            "land_use_description": (land or {}).get("description") if land else None,
            "land_use_smallholder_pct": (land or {}).get("smallholder_pct") if land else None,
            "deforestation_risk": defor,
        }

    def _fetch_ndvi(self, lat: float, lon: float, days: int = 60) -> Optional[float]:
        """Mean NDVI over a ~500m bbox over the last `days` days (cloud cover < 30%).
        Falls back to 180-day window if 60d returns nothing."""
        for window in (days, 180):
            payload = {
                "input": {
                    "bounds": {"bbox": self._bbox(lat, lon)},
                    "data": [{
                        "type": "sentinel-2-l2a",
                        "dataFilter": {
                            "timeRange": {
                                "from": _iso_days_ago(window),
                                "to": _iso_now(),
                            },
                            "maxCloudCoverage": 30,
                        },
                    }],
                },
                "output": {"width": 64, "height": 64, "responses": [{"identifier": "default", "format": {"type": "application/json"}}]},
                "evalscript": """//VERSION=3
function setup() { return { input: ["B04","B08","dataMask"], output: { id:"default", bands:1, sampleType:"FLOAT32" } }; }
function evaluatePixel(s) {
  if (s.dataMask === 0) return [NaN];
  return [(s.B08 - s.B04) / (s.B08 + s.B04 + 1e-9)];
}""",
            }
            try:
                body = self._process_request(payload)
                stats = _parse_json_stats(body)
                if stats is not None and stats.get("count", 0) > 0:
                    return round(float(stats["mean"]), 3)
            except httpx.HTTPStatusError as e:
                status = e.response.status_code
                if status == 429:
                    time.sleep(min(_parse_retry_after(e.response.headers.get("Retry-After")), 30))
                    continue
                if 500 <= status < 600:
                    time.sleep(2)
                    continue
                raise
        return None

    def _fetch_water_proximity(self, lat: float, lon: float) -> Optional[float]:
        """Distance in km to the nearest permanent-water pixel.

        Uses JRC Global Surface Water occurrence band; counts pixels with
        occurrence > 50. Bbox starts at ~1km, doubles each pass until any
        water pixel is seen or 50km cap is reached.

        Returns the radius (km) at the first hit, or 50.0 if none."""
        for radius_km in (1, 2, 5, 10, 25, 50):
            r = radius_km / 111.0  # rough deg per km
            payload = {
                "input": {
                    "bounds": {"bbox": [lon - r, lat - r, lon + r, lat + r]},
                    "data": [{"type": "byoc-jrc-water"}],
                },
                "output": {"width": 64, "height": 64, "responses": [{"identifier": "default", "format": {"type": "application/json"}}]},
                "evalscript": """//VERSION=3
function setup() { return { input:["occurrence"], output:{ id:"default", bands:1, sampleType:"FLOAT32" } }; }
function evaluatePixel(s) { return [s.occurrence > 50 ? 1 : 0]; }""",
            }
            stats = _parse_json_stats(self._process_request(payload))
            if stats is not None and stats.get("max", 0) >= 1:
                return float(radius_km)
        return 50.0

    _WORLDCOVER_CLASSES = {
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
        """Majority WorldCover class + share of smallholder-likely classes."""
        payload = {
            "input": {
                "bounds": {"bbox": self._bbox(lat, lon)},
                "data": [{"type": "esa-worldcover"}],
            },
            "output": {"width": 64, "height": 64, "responses": [{"identifier": "default", "format": {"type": "application/json"}}]},
            "evalscript": """//VERSION=3
function setup() { return { input:["Map"], output:{ id:"default", bands:1, sampleType:"UINT8" } }; }
function evaluatePixel(s) { return [s.Map]; }""",
        }
        stats = _parse_json_stats(self._process_request(payload))
        if stats is None or not stats.get("histogram"):
            return None

        hist = stats["histogram"]  # list of {value, count}
        total = sum(b["count"] for b in hist) or 1
        majority = max(hist, key=lambda b: b["count"])["value"]
        smallholder_count = sum(
            b["count"] for b in hist
            if self._WORLDCOVER_CLASSES.get(b["value"], (None, False))[1]
        )
        label, _ = self._WORLDCOVER_CLASSES.get(majority, ("Unknown land cover", False))
        return {
            "description": label,
            "smallholder_pct": round(100.0 * smallholder_count / total, 1),
        }

    def _fetch_eudr(self, lat: float, lon: float) -> Optional[str]:
        """Hansen Global Forest Change lossyear: any post-2020 loss → high,
        any pre-2020 loss → medium, otherwise low.

        Hansen encodes lossyear as years since 2000 (so 21 = year 2021)."""
        payload = {
            "input": {
                "bounds": {"bbox": self._bbox(lat, lon)},
                "data": [{"type": "byoc-hansen-gfc"}],
            },
            "output": {"width": 64, "height": 64, "responses": [{"identifier": "default", "format": {"type": "application/json"}}]},
            "evalscript": """//VERSION=3
function setup() { return { input:["lossyear"], output:{ id:"default", bands:1, sampleType:"UINT8" } }; }
function evaluatePixel(s) { return [s.lossyear]; }""",
        }
        stats = _parse_json_stats(self._process_request(payload))
        if stats is None or not stats.get("histogram"):
            return "low"
        recent = any(b["value"] > 20 and b["count"] > 0 for b in stats["histogram"])
        older = any(0 < b["value"] <= 20 and b["count"] > 0 for b in stats["histogram"])
        if recent:
            return "high"
        if older:
            return "medium"
        return "low"


def _iso_now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _iso_days_ago(days: int) -> str:
    from datetime import datetime, timedelta, timezone
    return (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_json_stats(raw: bytes) -> Optional[Dict[str, Any]]:
    """Process API returns either a TIFF, a PNG, or — when responses[0].format.type
    is application/json — a JSON blob with {min, max, mean, stDev, count, histogram?}.
    Returns the dict, or None if parsing fails."""
    import json
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    if isinstance(data, dict) and "bands" in data:
        bands = data["bands"]
        if bands:
            first = next(iter(bands.values()))
            stats = first.get("stats", {})
            histogram = first.get("histogram", {}).get("bins") if "histogram" in first else None
            if histogram:
                stats["histogram"] = [{"value": b.get("lowEdge", b.get("value")), "count": b["count"]} for b in histogram]
            return stats
    return data if isinstance(data, dict) else None


def _parse_retry_after(value: Optional[str]) -> int:
    """Parse the Retry-After header. RFC 7231 allows either a delta-seconds
    integer or an HTTP-date. Returns seconds; falls back to 5 on anything
    we can't parse."""
    if not value:
        return 5
    try:
        return int(value)
    except ValueError:
        return 5
