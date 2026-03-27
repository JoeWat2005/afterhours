import pytest

from app.integrations import overpass_client


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


@pytest.mark.asyncio
async def test_fetch_route_transit_overlays_filters_dedupes_and_sorts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = {
        "elements": [
            {
                "type": "node",
                "id": 101,
                "lat": 51.5004,
                "lon": -0.1196,
                "tags": {"highway": "bus_stop", "name": "Stop A"},
            },
            {
                "type": "node",
                "id": 101,
                "lat": 51.5008,
                "lon": -0.1192,
                "tags": {"highway": "bus_stop", "name": "Stop A duplicate farther"},
            },
            {
                "type": "node",
                "id": 202,
                "lat": 51.5006,
                "lon": -0.1194,
                "tags": {"railway": "station", "name": "Station B"},
            },
            {
                "type": "node",
                "id": 303,
                "lat": 51.5200,
                "lon": -0.0900,
                "tags": {"highway": "bus_stop", "name": "Far Away Stop"},
            },
        ]
    }

    async def _mock_request(*args, **kwargs):
        _ = args, kwargs
        return _FakeResponse(payload)

    monkeypatch.setattr(overpass_client, "_request_with_retries", _mock_request)

    result = await overpass_client.fetch_route_transit_overlays(
        route_geometry_geojson={
            "type": "LineString",
            "coordinates": [[-0.12, 51.5], [-0.11, 51.51]],
        },
        near_route_radius_metres=150,
        limit=10,
        client=object(),  # avoid creating a real HTTP client
    )

    assert result["warnings"] == []
    items = result["items"]
    assert len(items) == 2
    assert {item["id"] for item in items} == {"overpass-node-101", "overpass-node-202"}
    assert items[0]["distance_from_route_metres"] <= items[1]["distance_from_route_metres"]
    assert all(item["distance_from_route_metres"] <= 150 for item in items)
    assert {item["subtype"] for item in items} == {"bus_stop", "station"}


@pytest.mark.asyncio
async def test_fetch_route_transit_overlays_handles_invalid_geometry() -> None:
    result = await overpass_client.fetch_route_transit_overlays(
        route_geometry_geojson={"type": "Point", "coordinates": [-0.12, 51.5]},
        client=object(),
    )
    assert result["items"] == []
    assert result["warnings"] == ["invalid_route_geometry"]
