"""Live Copernicus smoke test. Skipped unless COPERNICUS_CLIENT_ID is set.

Costs ~4 PUs per run (one Process call per signal)."""
import os
import pytest

from app.services.copernicus_client import CopernicusClient

pytestmark = pytest.mark.skipif(
    not os.environ.get("COPERNICUS_CLIENT_ID"),
    reason="COPERNICUS_CLIENT_ID not set",
)


def test_compute_signals_bouake():
    client = CopernicusClient()
    out = client.compute_signals(7.69, -5.03)
    # NDVI: 0..1 if present
    if out["ndvi"] is not None:
        assert 0.0 <= out["ndvi"] <= 1.0
    # Water proximity ≤ 50 km (the cap)
    if out["water_proximity_km"] is not None:
        assert 0 <= out["water_proximity_km"] <= 50
    # Land use description should be a string when present
    if out["land_use_description"] is not None:
        assert isinstance(out["land_use_description"], str)
        assert 0 <= out["land_use_smallholder_pct"] <= 100
    # EUDR is one of the three labels
    if out["deforestation_risk"] is not None:
        assert out["deforestation_risk"] in {"low", "medium", "high"}
