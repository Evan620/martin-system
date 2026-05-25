"""R8 geospatial fixtures + deterministic synthetic fallback.

Five pre-recorded West African fixtures (representative Copernicus snapshots)
keyed by lat/lon rounded to 2 decimals (~1 km tolerance). Unknown coordinates
fall through to a deterministic synthesiser seeded by the coordinates so the
same inputs always produce the same outputs."""
from __future__ import annotations

import random
from typing import Any, Dict, Tuple


FIXTURE_COORDS: Dict[Tuple[float, float], Dict[str, Any]] = {
    (7.69, -5.03): {
        "city": "Bouake",
        "country": "Cote d'Ivoire",
        "payload": {
            "ndvi": 0.62,
            "water_proximity_km": 4.2,
            "land_use_description": "Mixed cropland and grassland",
            "land_use_smallholder_pct": 68.0,
            "deforestation_risk": "low",
        },
    },
    (9.45, -5.63): {
        "city": "Korhogo",
        "country": "Cote d'Ivoire",
        "payload": {
            "ndvi": 0.41,
            "water_proximity_km": 12.5,
            "land_use_description": "Savanna with rainfed cropland",
            "land_use_smallholder_pct": 72.0,
            "deforestation_risk": "medium",
        },
    },
    (8.04, -2.79): {
        "city": "Bondoukou",
        "country": "Cote d'Ivoire",
        "payload": {
            "ndvi": 0.71,
            "water_proximity_km": 3.1,
            "land_use_description": "Forest-edge tree crops (cocoa)",
            "land_use_smallholder_pct": 58.0,
            "deforestation_risk": "high",
        },
    },
    (9.40, -0.84): {
        "city": "Tamale",
        "country": "Ghana",
        "payload": {
            "ndvi": 0.48,
            "water_proximity_km": 22.0,
            "land_use_description": "Rainfed cropland",
            "land_use_smallholder_pct": 81.0,
            "deforestation_risk": "low",
        },
    },
    (5.62, -0.21): {
        "city": "Accra",
        "country": "Ghana",
        "payload": {
            "ndvi": 0.34,
            "water_proximity_km": 1.8,
            "land_use_description": "Peri-urban mosaic",
            "land_use_smallholder_pct": 24.0,
            "deforestation_risk": "medium",
        },
    },
}


_LAND_USE_PROFILES = [
    "Mixed cropland and grassland",
    "Rainfed cropland with sparse settlement",
    "Smallholder-dominated agroforestry",
    "Irrigated lowland rice belt",
    "Pastoral / grazing land",
    "Tree-crop plantation (cocoa / oil palm)",
]


def lookup(lat: float, lon: float) -> Tuple[Dict[str, Any], str]:
    """Return (payload, source) for the given coordinates.

    source is "fixture" if (round(lat,2), round(lon,2)) matches a known
    fixture, otherwise "stub" from a deterministic synthesiser."""
    key = (round(lat, 2), round(lon, 2))
    if key in FIXTURE_COORDS:
        return dict(FIXTURE_COORDS[key]["payload"]), "fixture"

    return _synthesise(lat, lon), "stub"


def _synthesise(lat: float, lon: float) -> Dict[str, Any]:
    """Deterministic synthetic metrics seeded by coordinates."""
    seed = int(round(lat * 1000 + lon * 1000))
    rng = random.Random(seed)

    ndvi = round(rng.uniform(0.2, 0.85), 3)
    water_proximity_km = round(rng.uniform(0.5, 8.0), 2)
    land_use_smallholder_pct = round(rng.uniform(30, 90), 1)
    land_use_description = rng.choice(_LAND_USE_PROFILES)

    if ndvi > 0.5:
        deforestation_risk = "low"
    elif ndvi > 0.35:
        deforestation_risk = "medium"
    else:
        deforestation_risk = "high"

    return {
        "ndvi": ndvi,
        "water_proximity_km": water_proximity_km,
        "land_use_description": land_use_description,
        "land_use_smallholder_pct": land_use_smallholder_pct,
        "deforestation_risk": deforestation_risk,
    }
