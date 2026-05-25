"""R8 geospatial boost scoring — pure function, no IO."""
from __future__ import annotations
from typing import Optional


def compute_boost(
    ndvi: Optional[float],
    water_proximity_km: Optional[float],
    smallholder_pct: Optional[float],
    deforestation_risk: Optional[str],
) -> int:
    """Map four geospatial signals to a 0..15 boost added to the Readiness sub-score.

    Bands are mutually exclusive within each signal. None values contribute 0.
    Total is capped at 15."""
    boost = 0

    if ndvi is not None:
        if ndvi >= 0.5:
            boost += 5
        elif ndvi >= 0.3:
            boost += 3

    if water_proximity_km is not None:
        if water_proximity_km <= 5:
            boost += 4
        elif water_proximity_km <= 15:
            boost += 2

    if smallholder_pct is not None and smallholder_pct >= 30:
        boost += 3

    if deforestation_risk == "low":
        boost += 3
    elif deforestation_risk == "medium":
        boost += 1

    return min(boost, 15)
