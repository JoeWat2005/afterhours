from __future__ import annotations

from typing import Any

import pytest

from app.integrations import police_client
from app.services import heatmap as heatmap_service
from app.services.route_safety import to_latitude_longitude


def _crime(
    *,
    persistent_id: str,
    category: str,
    latitude: float,
    longitude: float,
    month: str = "2026-02",
) -> dict[str, Any]:
    return {
        "category": category,
        "month": month,
        "persistent_id": persistent_id,
        "location": {
            "latitude": f"{latitude}",
            "longitude": f"{longitude}",
            "street": {"name": "Example Street"},
        },
    }


@pytest.fixture(autouse=True)
def _clear_cache() -> None:
    heatmap_service.clear_heatmap_cache()


@pytest.mark.asyncio
async def test_heatmap_dedupes_crimes_and_bins_into_cells(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    origin = (51.5, -0.12)
    east_lat, east_lng = to_latitude_longitude(300.0, 0.0, origin=origin)

    monkeypatch.setattr(
        heatmap_service,
        "_generate_sample_points",
        lambda **kwargs: [origin, (east_lat, east_lng)],
    )

    async def _mock_fetch_street_crimes_for_location(
        *,
        lat: float,
        lng: float,
        date: str | None = None,
        category: str = "all-crime",
        client=None,
    ) -> list[dict[str, Any]]:
        _ = lat, date, category, client
        if abs(lng - origin[1]) < 1e-6:
            return [
                _crime(
                    persistent_id="shared-crime",
                    category="robbery",
                    latitude=origin[0],
                    longitude=origin[1],
                ),
                _crime(
                    persistent_id="origin-only",
                    category="burglary",
                    latitude=origin[0],
                    longitude=origin[1],
                ),
            ]

        return [
            _crime(
                persistent_id="shared-crime",
                category="robbery",
                latitude=origin[0],
                longitude=origin[1],
            ),
            _crime(
                persistent_id="east-only",
                category="violent-crime",
                latitude=east_lat,
                longitude=east_lng,
            ),
        ]

    monkeypatch.setattr(
        police_client,
        "fetch_street_crimes_for_location",
        _mock_fetch_street_crimes_for_location,
    )

    result = await heatmap_service.get_on_demand_heatmap(
        heatmap_service.HeatmapQuery(
            latitude=origin[0],
            longitude=origin[1],
            radius_metres=1000,
            cell_size_metres=250,
            category="all-crime",
            date="2026-02",
        )
    )

    assert sum(item["source_count"] for item in result.items) == 3
    assert {item["cell_id"] for item in result.items} == {"0:0", "0:1"}


@pytest.mark.asyncio
async def test_heatmap_cache_expires_after_ttl(monkeypatch: pytest.MonkeyPatch) -> None:
    now = {"value": 1000.0}
    calls = {"fetch": 0}
    origin = (51.5, -0.12)

    monkeypatch.setattr(heatmap_service, "monotonic", lambda: now["value"])
    monkeypatch.setattr(
        heatmap_service,
        "_generate_sample_points",
        lambda **kwargs: [origin],
    )

    async def _mock_fetch_street_crimes_for_location(
        *,
        lat: float,
        lng: float,
        date: str | None = None,
        category: str = "all-crime",
        client=None,
    ) -> list[dict[str, Any]]:
        _ = lat, lng, date, category, client
        calls["fetch"] += 1
        return [
            _crime(
                persistent_id=f"crime-{calls['fetch']}",
                category="robbery",
                latitude=origin[0],
                longitude=origin[1],
            )
        ]

    monkeypatch.setattr(
        police_client,
        "fetch_street_crimes_for_location",
        _mock_fetch_street_crimes_for_location,
    )

    query = heatmap_service.HeatmapQuery(
        latitude=origin[0],
        longitude=origin[1],
        radius_metres=1000,
        cell_size_metres=250,
        date="2026-02",
    )

    await heatmap_service.get_on_demand_heatmap(query)
    now["value"] = 1200.0
    await heatmap_service.get_on_demand_heatmap(query)
    now["value"] = 1401.0
    await heatmap_service.get_on_demand_heatmap(query)

    assert calls["fetch"] == 2


@pytest.mark.asyncio
async def test_heatmap_cache_key_rounds_nearby_coordinates(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"fetch": 0}

    monkeypatch.setattr(
        heatmap_service,
        "_generate_sample_points",
        lambda **kwargs: [(kwargs["latitude"], kwargs["longitude"])],
    )

    async def _mock_fetch_street_crimes_for_location(
        *,
        lat: float,
        lng: float,
        date: str | None = None,
        category: str = "all-crime",
        client=None,
    ) -> list[dict[str, Any]]:
        _ = lat, lng, date, category, client
        calls["fetch"] += 1
        return [
            _crime(
                persistent_id=f"crime-{calls['fetch']}",
                category="robbery",
                latitude=51.5,
                longitude=-0.12,
            )
        ]

    monkeypatch.setattr(
        police_client,
        "fetch_street_crimes_for_location",
        _mock_fetch_street_crimes_for_location,
    )

    base = {
        "radius_metres": 1000,
        "cell_size_metres": 250,
        "category": "all-crime",
        "date": "2026-02",
    }

    await heatmap_service.get_on_demand_heatmap(
        heatmap_service.HeatmapQuery(latitude=51.500041, longitude=-0.120041, **base)
    )
    await heatmap_service.get_on_demand_heatmap(
        heatmap_service.HeatmapQuery(latitude=51.500049, longitude=-0.120049, **base)
    )
    await heatmap_service.get_on_demand_heatmap(
        heatmap_service.HeatmapQuery(latitude=51.50021, longitude=-0.12021, **base)
    )

    assert calls["fetch"] == 2


def test_prune_cache_removes_expired_entries(monkeypatch: pytest.MonkeyPatch) -> None:
    # Directly inject entries into the cache dict and confirm _prune_cache evicts
    # the ones whose expiry timestamp is in the past.
    cache = heatmap_service._cache

    stub_result = heatmap_service.HeatmapResult(
        latitude=51.5,
        longitude=-0.12,
        radius_metres=1000,
        cell_size_metres=250,
        category="all-crime",
        date="2026-02",
        items=[],
    )

    now = 2000.0
    cache["expired-a"] = (1000.0, stub_result)   # expired: expires_at < now
    cache["expired-b"] = (1999.9, stub_result)   # expired: expires_at < now
    cache["live-a"] = (2001.0, stub_result)      # still valid
    cache["live-b"] = (9999.0, stub_result)      # still valid

    heatmap_service._prune_cache(now)

    assert "expired-a" not in cache
    assert "expired-b" not in cache
    assert "live-a" in cache
    assert "live-b" in cache

