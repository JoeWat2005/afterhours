import pytest

from app.integrations.mapbox_directions_client import fetch_mapbox_route_candidates


@pytest.mark.asyncio
async def test_fetch_mapbox_route_candidates_multiple_routes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EXPO_PUBLIC_MAPBOX_ACCESS_TOKEN", "fake-token")

    class MockResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {
                "routes": [
                    {
                        "distance": 1500,
                        "duration": 900,
                        "geometry": {
                            "type": "LineString",
                            "coordinates": [[-0.12, 51.5], [-0.11, 51.51]],
                        },
                        "legs": [],
                    },
                    {
                        "distance": 1600,
                        "duration": 950,
                        "geometry": {
                            "type": "LineString",
                            "coordinates": [[-0.12, 51.5], [-0.10, 51.52]],
                        },
                        "legs": [],
                    },
                ]
            }

    class MockClient:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def get(self, url, params, **kwargs):
            assert "alternatives" in params
            assert params["alternatives"] == "true"
            return MockResponse()

    monkeypatch.setattr("app.integrations.mapbox_directions_client.httpx.AsyncClient", MockClient)

    candidates = await fetch_mapbox_route_candidates(
        origin_latitude=51.5,
        origin_longitude=-0.12,
        destination_latitude=51.51,
        destination_longitude=-0.11,
        alternatives=2,
    )

    assert len(candidates) == 2
    assert candidates[0].candidate_id == "mapbox-1"
    assert candidates[0].distance_metres == 1500
    assert candidates[1].candidate_id == "mapbox-2"
    assert candidates[1].distance_metres == 1600


@pytest.mark.asyncio
async def test_fetch_mapbox_route_candidates_missing_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("EXPO_PUBLIC_MAPBOX_ACCESS_TOKEN", raising=False)

    with pytest.raises(RuntimeError, match="EXPO_PUBLIC_MAPBOX_ACCESS_TOKEN is not configured"):
        await fetch_mapbox_route_candidates(
            origin_latitude=51.5,
            origin_longitude=-0.12,
            destination_latitude=51.51,
            destination_longitude=-0.11,
        )


@pytest.mark.asyncio
async def test_fetch_mapbox_route_candidates_no_routes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EXPO_PUBLIC_MAPBOX_ACCESS_TOKEN", "fake-token")

    class MockResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"routes": []}

    class MockClient:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def get(self, *args, **kwargs):
            return MockResponse()

    monkeypatch.setattr("app.integrations.mapbox_directions_client.httpx.AsyncClient", MockClient)

    with pytest.raises(ValueError, match="Mapbox returned no routes"):
        await fetch_mapbox_route_candidates(
            origin_latitude=51.5,
            origin_longitude=-0.12,
            destination_latitude=51.51,
            destination_longitude=-0.11,
        )
