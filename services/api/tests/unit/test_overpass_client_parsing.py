import pytest
from app.integrations.overpass_client import (
    _is_staffed,
    _is_well_lit,
    _safe_waiting_place,
)

@pytest.mark.parametrize(
    "tags, expected",
    [
        ({"staffed": "yes"}, True),
        ({"staffed": "limited"}, True),
        ({"amenity": "cafe"}, True),
        ({"shop": "supermarket"}, True),
        ({"railway": "station"}, True),
        ({"staffed": "no"}, False),
        ({"amenity": "bench"}, False),
        ({}, False),
    ],
)
def test_is_staffed_logic(tags, expected):
    assert _is_staffed(tags) == expected

@pytest.mark.parametrize(
    "tags, expected",
    [
        ({"lit": "yes"}, True),
        ({"lit": "automatic"}, True),
        ({"lit": "limited"}, True),
        ({"lit": "no"}, False),
        ({"lit": "disused"}, False),
        ({}, False),
    ],
)
def test_is_well_lit_logic(tags, expected):
    assert _is_well_lit(tags) == expected

@pytest.mark.parametrize(
    "tags, expected",
    [
        ({"amenity": "pub"}, True),
        ({"amenity": "police"}, True),
        ({"shop": "kiosk"}, True),
        ({"public_transport": "station"}, True),
        ({"railway": "station"}, True),
        ({"highway": "bus_stop"}, True),
        ({"amenity": "grave_yard"}, False),
        ({"highway": "residential"}, False),
        ({}, False),
    ],
)
def test_safe_waiting_place_logic(tags, expected):
    assert _safe_waiting_place(tags) == expected
