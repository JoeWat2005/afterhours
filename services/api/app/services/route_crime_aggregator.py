from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.crime_weights import get_crime_weight
from app.services.police_api import (
    fetch_route_crime_points,
    iter_route_points,
    route_length_metres,
    sample_route_points_by_distance,
)
from app.services.police_api_config import (
    DEFAULT_MAX_ROUTE_FETCH_POINTS,
    DEFAULT_ROUTE_CORRIDOR_HALF_WIDTH_METRES,
    DEFAULT_ROUTE_SAMPLE_SPACING_METRES,
    DEFAULT_RUNTIME_CELL_SIZE_METRES,
    RouteCrimeAggregationInput,
    RouteSafetyMetrics,
)
from app.services.report_proximity import (
    compute_report_density,
    list_unique_reports_along_route,
)


def _compute_incident_density(
    *,
    payload: RouteCrimeAggregationInput,
    route_length_metres: float,
) -> float | None:
    if route_length_metres <= 0:
        return None

    route_length_km = max(route_length_metres / 1000.0, 0.001)
    points = payload["route_crime_response"]["points"]

    if not points:
        return None

    weighted_total = sum(get_crime_weight(point.get("category")) for point in points)
    return round(weighted_total / route_length_km, 4)


def compute_route_safety_metrics(
    payload: RouteCrimeAggregationInput,
) -> RouteSafetyMetrics:
    """
    Stable middle layer between police_api.py and route_scoring.py.

    Current responsibility:
    - accept normalized police crime points for a route
    - compute route-level safety metrics
    - leave heatmap generation for later
    """
    geometry = payload["route_geometry_geojson"]
    points = iter_route_points(geometry)
    length_metres = route_length_metres(points)
    length_km = max(length_metres / 1000.0, 0.001)

    warnings = list(payload["route_crime_response"]["warnings"])

    if length_metres <= 0:
        warnings.append("invalid_route_geometry")

    incident_density = _compute_incident_density(
        payload=payload,
        route_length_metres=length_metres,
    )

    if incident_density is None:
        warnings.append("no_crime_data_found")

    return RouteSafetyMetrics(
        incident_density=incident_density,
        report_density=None,
        warnings=sorted(set(warnings)),
        route_length_metres=length_metres,
        route_length_km=length_km,
        corridor_half_width_metres=payload["corridor_half_width_metres"],
        cell_size_metres=payload["cell_size_metres"],
        heatmap_cells=[],
    )


async def enrich_route_candidate_safety(
    *,
    route_geometry_geojson: dict[str, Any],
    route_id: str | None = None,
    date: str | None = None,
    db: AsyncSession | None = None,
    corridor_half_width_metres: float = DEFAULT_ROUTE_CORRIDOR_HALF_WIDTH_METRES,
    cell_size_metres: float = DEFAULT_RUNTIME_CELL_SIZE_METRES,
    report_max_age_days: int | None = 90,
    sample_spacing_metres: float = DEFAULT_ROUTE_SAMPLE_SPACING_METRES,
    max_route_points: int = DEFAULT_MAX_ROUTE_FETCH_POINTS,
    per_point_report_limit: int = 100,
) -> RouteSafetyMetrics:
    """
    Single entry point callers should use.

    - Always computes police-based incident_density
    - Computes DB-backed report_density when a DB session is provided
    - Deliberately does not generate heatmap cells yet
    """
    route_crime_response = await fetch_route_crime_points(
        route_geometry_geojson=route_geometry_geojson,
        route_id=route_id,
        date=date,
        sample_spacing_metres=sample_spacing_metres,
        max_route_points=max_route_points,
    )

    metrics = compute_route_safety_metrics(
        RouteCrimeAggregationInput(
            route_id=route_id,
            route_geometry_geojson=route_geometry_geojson,
            route_crime_response=route_crime_response,
            corridor_half_width_metres=corridor_half_width_metres,
            cell_size_metres=cell_size_metres,
        )
    )

    if db is None:
        return metrics

    route_points = iter_route_points(route_geometry_geojson)
    sampled_points = sample_route_points_by_distance(
        route_points,
        spacing_metres=sample_spacing_metres,
        max_points=max_route_points,
    )

    warnings = list(metrics["warnings"])
    if len(sampled_points) >= max_route_points:
        warnings.append("route_sampling_capped")

    unique_reports = await list_unique_reports_along_route(
        db,
        sampled_points=sampled_points,
        radius_metres=corridor_half_width_metres,
        per_point_limit=per_point_report_limit,
        max_age_days=report_max_age_days,
    )

    report_density = compute_report_density(
        reports=unique_reports,
        route_length_metres=metrics["route_length_metres"],
    )

    if report_density is None:
        warnings.append("no_report_data_found")

    return RouteSafetyMetrics(
        incident_density=metrics["incident_density"],
        report_density=report_density,
        warnings=sorted(set(warnings)),
        route_length_metres=metrics["route_length_metres"],
        route_length_km=metrics["route_length_km"],
        corridor_half_width_metres=metrics["corridor_half_width_metres"],
        cell_size_metres=metrics["cell_size_metres"],
        heatmap_cells=[],
    )