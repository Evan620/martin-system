import pytest
from app.services.geospatial_scoring import compute_boost


@pytest.mark.parametrize(
    "ndvi,water,smallholder,defor,expected",
    [
        # Each component in isolation
        (0.6, 100.0, 0.0, "high", 5),       # NDVI top band only
        (0.4, 100.0, 0.0, "high", 3),       # NDVI mid band only
        (0.1, 100.0, 0.0, "high", 0),       # NDVI below threshold
        (0.0, 3.0, 0.0, "high", 4),         # Water close band
        (0.0, 10.0, 0.0, "high", 2),        # Water medium band
        (0.0, 30.0, 0.0, "high", 0),        # Water beyond threshold
        (0.0, 100.0, 35.0, "high", 3),      # Smallholder threshold met
        (0.0, 100.0, 29.0, "high", 0),      # Smallholder below threshold
        (0.0, 100.0, 0.0, "low", 3),        # Deforestation low
        (0.0, 100.0, 0.0, "medium", 1),     # Deforestation medium
        (0.0, 100.0, 0.0, "high", 0),       # Deforestation high

        # Combinations
        (0.6, 3.0, 35.0, "low", 15),        # All max → caps at 15
        (0.6, 3.0, 35.0, "medium", 13),     # All max except defor → 5+4+3+1 = 13
        (0.4, 10.0, 35.0, "medium", 9),     # All mid-band → 3+2+3+1 = 9

        # Boundary values
        (0.5, 5.0, 30.0, "low", 15),        # Inclusive boundaries
        (0.49999, 4.99999, 29.9999, "low", 3 + 4 + 0 + 3),  # Just under boundaries
    ],
)
def test_compute_boost(ndvi, water, smallholder, defor, expected):
    assert compute_boost(ndvi, water, smallholder, defor) == expected


def test_compute_boost_caps_at_15():
    assert compute_boost(1.0, 0.0, 100.0, "low") == 15


def test_compute_boost_handles_none_signals():
    assert compute_boost(None, None, None, None) == 0
