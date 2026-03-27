from datetime import datetime, timezone

import pytest

from app.schemas.routes import (
    RouteOverlayInclude,
    RouteOverlayItem,
    RouteOverlayType,
    RouteOverlaysRequest,
)
from app.services import route_overlays


def _make_request(include: list[RouteOverlayInclude]) -> RouteOverlaysRequest:
    return RouteOverlaysRequest.model_validate(
        {
            "route_geometry_geojson": {
                "type": "LineString",
                "coordinates": [[-0.12, 51.5], [-0.11, 51.51]],
            },
            "include": [item.value for item in include],
            "near_route_radius_metres": 150,
            "limit_per_type": 20,
        }
    )


def _overlay_item(item_id: str, overlay_type: RouteOverlayType) -> RouteOverlayItem:
    return RouteOverlayItem(
        id=item_id,
        overlay_type=overlay_type,
        subtype="test",
        latitude=51.5,
        longitude=-0.12,
        distance_from_route_metres=10.0,
        source="test",
        metadata={},
    )


@pytest.mark.asyncio
async def test_route_overlays_static_cache_hits(monkeypatch: pytest.MonkeyPatch) -> None:
    route_overlays.clear_route_overlay_cache()
    calls = {"transit": 0, "services": 0}

    async def _mock_fetch_transit_items(request):
        _ = request
        calls["transit"] += 1
        return [_overlay_item("transit-1", RouteOverlayType.TRANSIT)], []

    async def _mock_fetch_service_items(request, *, route_points):
        _ = request, route_points
        calls["services"] += 1
        return [_overlay_item("service-1", RouteOverlayType.SERVICE)], []

    monkeypatch.setattr(route_overlays, "_fetch_transit_items", _mock_fetch_transit_items)
    monkeypatch.setattr(route_overlays, "_fetch_service_items", _mock_fetch_service_items)

    request = _make_request([RouteOverlayInclude.TRANSIT, RouteOverlayInclude.SERVICES])
    first = await route_overlays.get_route_overlays(request, db=None)
    second = await route_overlays.get_route_overlays(request, db=None)

    assert calls["transit"] == 1
    assert calls["services"] == 1
    assert len(first.items) == 2
    assert len(second.items) == 2
    assert first.warnings == []
    assert second.warnings == []


@pytest.mark.asyncio
async def test_route_overlays_reports_cache_ttl(monkeypatch: pytest.MonkeyPatch) -> None:
    route_overlays.clear_route_overlay_cache()
    now = {"value": 1_000.0}
    calls = {"reports": 0}

    async def _mock_fetch_report_items(request, *, route_points, db):
        _ = request, route_points, db
        calls["reports"] += 1
        return [_overlay_item("report-1", RouteOverlayType.REPORT)], []

    monkeypatch.setattr(route_overlays, "_fetch_report_items", _mock_fetch_report_items)
    monkeypatch.setattr(route_overlays, "monotonic", lambda: now["value"])

    request = _make_request([RouteOverlayInclude.REPORTS])
    await route_overlays.get_route_overlays(request, db=object())
    now["value"] += 20
    await route_overlays.get_route_overlays(request, db=object())
    now["value"] += 60
    await route_overlays.get_route_overlays(request, db=object())

    assert calls["reports"] == 2


@pytest.mark.asyncio
async def test_route_overlays_partial_failure_adds_warning(monkeypatch: pytest.MonkeyPatch) -> None:
    route_overlays.clear_route_overlay_cache()

    async def _mock_fetch_transit_items(request):
        _ = request
        raise RuntimeError("boom")

    async def _mock_fetch_report_items(request, *, route_points, db):
        _ = request, route_points, db
        return [
            RouteOverlayItem(
                id="report-1",
                overlay_type=RouteOverlayType.REPORT,
                subtype="theft",
                name="Phone snatch",
                latitude=51.5,
                longitude=-0.12,
                distance_from_route_metres=12.0,
                source="report_db",
                metadata={"created_at": datetime.now(timezone.utc).isoformat()},
            )
        ], []

    monkeypatch.setattr(route_overlays, "_fetch_transit_items", _mock_fetch_transit_items)
    monkeypatch.setattr(route_overlays, "_fetch_report_items", _mock_fetch_report_items)

    request = _make_request([RouteOverlayInclude.TRANSIT, RouteOverlayInclude.REPORTS])
    result = await route_overlays.get_route_overlays(request, db=object())

    assert len(result.items) == 1
    assert result.items[0].overlay_type == RouteOverlayType.REPORT
    assert "transit_overlay_fetch_failed" in result.warnings
