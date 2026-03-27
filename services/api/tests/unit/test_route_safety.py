import pytest

from app.services import route_safety


def _sample_geometry() -> dict:
    return {
        "type": "LineString",
        "coordinates": [
            [-0.1278, 51.5074],
            [-0.1268, 51.5094],
            [-0.1258, 51.5114],
        ],
    }


def _sample_crime_response(route_geometry_geojson: dict) -> dict:
    return {
        "schema_version": "1.0",
        "route_id": "test-route",
        "crime_source": "uk_police",
        "crime_month": "2026-01",
        "route_geometry_geojson": route_geometry_geojson,
        "points": [
            {
                "crime_id": "crime-1",
                "category": "robbery",
                "month": "2026-01",
                "latitude": 51.5090,
                "longitude": -0.1269,
                "location_label": "Example Street",
                "source": "uk_police",
            },
            {
                "crime_id": "crime-2",
                "category": "violent-crime",
                "month": "2026-01",
                "latitude": 51.5100,
                "longitude": -0.1262,
                "location_label": "Example Street",
                "source": "uk_police",
            },
        ],
        "point_count": 2,
        "warnings": [],
    }


def test_compute_route_safety_metrics_builds_heatmap_without_report_density() -> None:
    geometry = _sample_geometry()
    payload = route_safety.RouteCrimeAggregationInput(
        route_id="test-route",
        route_geometry_geojson=geometry,
        route_crime_response=_sample_crime_response(geometry),
        corridor_half_width_metres=100.0,
        cell_size_metres=75.0,
    )

    metrics = route_safety.compute_route_safety_metrics(payload)

    assert metrics["incident_density"] is not None
    assert metrics["heatmap_cells"]
    # Report density should only come from DB safety reports.
    assert metrics["report_density"] is None


@pytest.mark.asyncio
async def test_enrich_route_candidate_safety_keeps_report_density_none_without_reports(
    monkeypatch,
) -> None:
    geometry = _sample_geometry()

    async def mock_fetch_route_crime_points(**kwargs) -> dict:
        return _sample_crime_response(kwargs["route_geometry_geojson"])

    async def mock_list_unique_reports_along_route(*args, **kwargs) -> list:
        return []

    monkeypatch.setattr(
        route_safety,
        "fetch_route_crime_points",
        mock_fetch_route_crime_points,
    )
    monkeypatch.setattr(
        route_safety,
        "list_unique_reports_along_route",
        mock_list_unique_reports_along_route,
    )

    metrics = await route_safety.enrich_route_candidate_safety(
        route_geometry_geojson=geometry,
        route_id="test-route",
        db=object(),  # mocked report query ignores DB instance
    )

    assert metrics["heatmap_cells"]
    assert metrics["report_density"] is None
    assert "no_report_data_found" in metrics["warnings"]
