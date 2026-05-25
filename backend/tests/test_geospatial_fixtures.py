from app.services.geospatial_fixtures import lookup, FIXTURE_COORDS


def test_lookup_known_fixture_bouake():
    payload, source = lookup(7.69, -5.03)
    assert source == "fixture"
    assert 0.0 <= payload["ndvi"] <= 1.0
    assert payload["water_proximity_km"] >= 0
    assert payload["land_use_description"]
    assert 0 <= payload["land_use_smallholder_pct"] <= 100
    assert payload["deforestation_risk"] in {"low", "medium", "high"}


def test_lookup_within_tolerance_bouake():
    # 0.005 degree difference rounds to the same 2dp key
    payload, source = lookup(7.694, -5.027)
    assert source == "fixture"


def test_lookup_outside_tolerance_falls_through():
    # Coordinates nowhere near a fixture → deterministic synthetic
    payload, source = lookup(1.0, 1.0)
    assert source == "stub"
    # Two calls with same coords must be deterministic
    payload2, source2 = lookup(1.0, 1.0)
    assert payload == payload2
    assert source2 == "stub"


def test_all_five_fixtures_present():
    assert len(FIXTURE_COORDS) == 5
    expected_cities = {"Bouake", "Korhogo", "Bondoukou", "Tamale", "Accra"}
    actual_cities = {fx["city"] for fx in FIXTURE_COORDS.values()}
    assert actual_cities == expected_cities


def test_fixture_payload_shape():
    for (lat, lon), fx in FIXTURE_COORDS.items():
        payload = fx["payload"]
        assert set(payload.keys()) == {
            "ndvi", "water_proximity_km", "land_use_description",
            "land_use_smallholder_pct", "deforestation_risk",
        }
        assert payload["deforestation_risk"] in {"low", "medium", "high"}
