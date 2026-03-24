from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timedelta, timezone
from typing import Any, TypedDict
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.route_enrichment_config import (
    DEFAULT_CATEGORY,
    DEFAULT_MAX_ROUTE_FETCH_POINTS,
    DEFAULT_PER_POINT_REPORT_LIMIT,
    DEFAULT_REPORT_MAX_AGE_DAYS,
    DEFAULT_ROUTE_CORRIDOR_HALF_WIDTH_METRES,
    DEFAULT_ROUTE_SAMPLE_SPACING_METRES,
    DEFAULT_RUNTIME_CELL_SIZE_METRES,
)
from app.core.route_risk_config import (
    DEFAULT_POLICE_CRIME_SEVERITY,
    POLICE_CRIME_CATEGORY_SEVERITY,
    ReportSeverity,
    SEVERITY_WEIGHTS,
)
from app.integrations.police_client import RouteCrimeResponse, fetch_route_crime_points
from app.models.report import SafetyReport
from app.services.safety_reports import get_severity_weight
from app.services.route_geometry import (
    iter_route_points,
    route_length_metres,
    sample_route_points_by_distance,
)

class HeatmapCell(TypedDict, total=False):
    cell_id: str
    center_latitude: float
    center_longitude: float
    risk_score: float
    source_count: int
    bounds: dict[str, float]


class RouteSafetyMetrics(TypedDict):
    incident_density: float | None
    report_density: float | None
    warnings: list[str]
    route_length_metres: float
    route_length_km: float
    corridor_half_width_metres: float
    cell_size_metres: float
    heatmap_cells: list[HeatmapCell]


class RouteCrimeAggregationInput(TypedDict):
    route_id: str | None
    route_geometry_geojson: dict[str, Any]
    route_crime_response: RouteCrimeResponse
    corridor_half_width_metres: float
    cell_size_metres: float


def normalize_police_crime_category(category: str | None) -> str:
    if not category:
        return "other-crime"
    return category.strip().lower().replace(" ", "-")


def get_police_crime_severity(category: str | None) -> ReportSeverity:
    normalized_category = normalize_police_crime_category(category)
    return POLICE_CRIME_CATEGORY_SEVERITY.get(
        normalized_category,
        DEFAULT_POLICE_CRIME_SEVERITY,
    )


def get_crime_weight(category: str | None) -> int:
    return SEVERITY_WEIGHTS[get_police_crime_severity(category)]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


async def list_nearby_reports(
    db: AsyncSession,
    *,
    latitude: float,
    longitude: float,
    radius_metres: float,
    limit: int = 100,
    created_after: datetime | None = None,
) -> list[SafetyReport]:
    origin = func.ST_SetSRID(func.ST_MakePoint(longitude, latitude), 4326)

    stmt = select(SafetyReport).where(
        func.ST_DWithin(
            func.Geography(SafetyReport.location),
            func.Geography(origin),
            radius_metres,
        )
    )

    if created_after is not None:
        stmt = stmt.where(SafetyReport.created_at >= created_after)

    stmt = stmt.order_by(
        func.ST_Distance(
            func.Geography(SafetyReport.location),
            func.Geography(origin),
        )
    ).limit(limit)

    result = await db.execute(stmt)
    return list(result.scalars().all())


async def list_unique_reports_along_route(
    db: AsyncSession,
    *,
    sampled_points: Iterable[tuple[float, float]],
    radius_metres: float,
    per_point_limit: int = DEFAULT_PER_POINT_REPORT_LIMIT,
    max_age_days: int | None = DEFAULT_REPORT_MAX_AGE_DAYS,
) -> list[SafetyReport]:
    created_after: datetime | None = None
    if max_age_days is not None:
        created_after = utc_now() - timedelta(days=max_age_days)

    seen_ids: set[UUID] = set()
    unique_reports: list[SafetyReport] = []

    for latitude, longitude in sampled_points:
        reports = await list_nearby_reports(
            db,
            latitude=latitude,
            longitude=longitude,
            radius_metres=radius_metres,
            limit=per_point_limit,
            created_after=created_after,
        )

        for report in reports:
            if report.id in seen_ids:
                continue
            seen_ids.add(report.id)
            unique_reports.append(report)

    return unique_reports


def compute_report_density(
    *,
    reports: Iterable[SafetyReport],
    route_length_metres: float,
) -> float | None:
    if route_length_metres <= 0:
        return None

    route_length_km = route_length_metres / 1000.0
    if route_length_km <= 0:
        return None

    reports_list = list(reports)
    if not reports_list:
        return None

    weighted_total = sum(
        get_severity_weight(report.severity) for report in reports_list
    )
    return round(weighted_total / route_length_km, 4)


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
    category: str = DEFAULT_CATEGORY,
    db: AsyncSession | None = None,
    corridor_half_width_metres: float = DEFAULT_ROUTE_CORRIDOR_HALF_WIDTH_METRES,
    cell_size_metres: float = DEFAULT_RUNTIME_CELL_SIZE_METRES,
    report_max_age_days: int | None = DEFAULT_REPORT_MAX_AGE_DAYS,
    sample_spacing_metres: float = DEFAULT_ROUTE_SAMPLE_SPACING_METRES,
    max_route_points: int = DEFAULT_MAX_ROUTE_FETCH_POINTS,
    per_point_report_limit: int = DEFAULT_PER_POINT_REPORT_LIMIT,
) -> RouteSafetyMetrics:
    route_crime_response = await fetch_route_crime_points(
        route_geometry_geojson=route_geometry_geojson,
        route_id=route_id,
        date=date,
        category=category,
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
