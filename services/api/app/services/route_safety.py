from __future__ import annotations
from collections.abc import Iterable
from datetime import datetime, timedelta, timezone
from math import cos, floor, radians
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
from app.integrations.police_client import RouteCrimeResponse, fetch_route_crime_points
from app.models.report import SafetyReport
from app.services.route_geometry import (
    iter_route_points,
    route_length_metres,
    sample_route_points_by_distance,
)


CRIME_SCORING: dict[str, int] = {
    "violent-crime": 10,
    "sexual-offences": 10,
    "possession-of-weapons": 10,
    "robbery": 5,
    "theft-from-the-person": 5,
    "public-order": 3,
    "drugs": 3,
    "anti-social-behaviour": 2,
    "burglary": 2,
    "vehicle-crime": 2,
    "criminal-damage-arson": 2,
    "shoplifting": 1,
    "bicycle-theft": 1,
    "other-theft": 1,
    "other-crime": 1,
}


REPORT_CATEGORY_WEIGHTS: dict[str, int] = {
    "assault": 4,
    "robbery": 4,
    "harassment": 3,
    "theft": 3,
    "suspicious activity": 2,
    "poor lighting": 2,
    "unsafe crossing": 2,
    "hazard": 1,
    "other": 1,
}


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


def normalize_crime_category(category: str | None) -> str:
    if not category:
        return "other-crime"
    return category.strip().lower().replace(" ", "-")


def get_crime_weight(category: str | None) -> int:
    return CRIME_SCORING.get(normalize_crime_category(category), 1)


def normalize_report_category(category: str | None) -> str:
    if not category:
        return "other"
    return category.strip().lower()


def get_report_weight(category: str | None) -> int:
    return REPORT_CATEGORY_WEIGHTS.get(normalize_report_category(category), 1)


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

    weighted_total = sum(get_report_weight(report.category) for report in reports_list)
    return round(weighted_total / route_length_km, 4)


def metres_per_latitude() -> float:
    return 111320.0


def metres_per_longitude(latitude: float) -> float:
    return max(111320.0 * cos(radians(latitude)), 1e-6)


def to_xy_metre_coordinates(
    point: tuple[float, float],
    *,
    origin: tuple[float, float],
) -> tuple[float, float]:
    latitude, longitude = point
    origin_latitude, origin_longitude = origin
    x = (longitude - origin_longitude) * metres_per_longitude(origin_latitude)
    y = (latitude - origin_latitude) * metres_per_latitude()
    return x, y


def to_latitude_longitude(
    x: float,
    y: float,
    *,
    origin: tuple[float, float],
) -> tuple[float, float]:
    origin_latitude, origin_longitude = origin
    latitude = origin_latitude + (y / metres_per_latitude())
    longitude = origin_longitude + (x / metres_per_longitude(origin_latitude))
    return latitude, longitude


def point_to_segment_distance(
    point_xy: tuple[float, float],
    segment_start_xy: tuple[float, float],
    segment_end_xy: tuple[float, float],
) -> float:
    point_x, point_y = point_xy
    start_x, start_y = segment_start_xy
    end_x, end_y = segment_end_xy
    segment_x = end_x - start_x
    segment_y = end_y - start_y
    point_start_x = point_x - start_x
    point_start_y = point_y - start_y
    segment_length_squared = (segment_x * segment_x) + (segment_y * segment_y)

    if segment_length_squared == 0:
        distance_x = point_x - start_x
        distance_y = point_y - start_y
        return (distance_x * distance_x + distance_y * distance_y) ** 0.5

    closest_point_on_segment = (
        (point_start_x * segment_x) + (point_start_y * segment_y)
    ) / segment_length_squared
    closest_point_on_segment = max(0.0, min(1.0, closest_point_on_segment))
    closest_x = start_x + (closest_point_on_segment * segment_x)
    closest_y = start_y + (closest_point_on_segment * segment_y)
    distance_x = point_x - closest_x
    distance_y = point_y - closest_y
    return (distance_x * distance_x + distance_y * distance_y) ** 0.5


def point_to_route_distance(
    point: tuple[float, float],
    *,
    route_points: list[tuple[float, float]],
) -> float:
    if not route_points:
        return float("inf")

    origin = route_points[0]
    point_xy = to_xy_metre_coordinates(point, origin=origin)

    if len(route_points) == 1:
        route_xy = to_xy_metre_coordinates(route_points[0], origin=origin)
        distance_x = point_xy[0] - route_xy[0]
        distance_y = point_xy[1] - route_xy[1]
        return (distance_x * distance_x + distance_y * distance_y) ** 0.5

    min_distance = float("inf")
    for index in range(len(route_points) - 1):
        start_xy = to_xy_metre_coordinates(route_points[index], origin=origin)
        end_xy = to_xy_metre_coordinates(route_points[index + 1], origin=origin)
        distance = point_to_segment_distance(point_xy, start_xy, end_xy)
        if distance < min_distance:
            min_distance = distance
    return min_distance


def build_heatmap_cells(
    *,
    crime_points: Iterable[dict[str, Any]],
    route_points: list[tuple[float, float]],
    corridor_half_width_metres: float,
    cell_size_metres: float,
) -> list[HeatmapCell]:
    if not route_points or cell_size_metres <= 0:
        return []

    origin = route_points[0]
    cells_data: dict[tuple[int, int], dict[str, float | int]] = {}

    for point in crime_points:
        latitude_raw = point.get("latitude")
        longitude_raw = point.get("longitude")
        if latitude_raw is None or longitude_raw is None:
            continue

        try:
            latitude = float(latitude_raw)
            longitude = float(longitude_raw)
        except (TypeError, ValueError):
            continue

        distance_to_route = point_to_route_distance(
            (latitude, longitude),
            route_points=route_points,
        )
        if distance_to_route > corridor_half_width_metres:
            continue

        x_metres, y_metres = to_xy_metre_coordinates(
            (latitude, longitude),
            origin=origin,
        )
        row = floor(y_metres / cell_size_metres)
        col = floor(x_metres / cell_size_metres)
        cell_key = (row, col)

        cell_data = cells_data.setdefault(
            cell_key,
            {
                "risk_score": 0.0,
                "source_count": 0,
            },
        )
        cell_data["risk_score"] = float(cell_data["risk_score"]) + float(
            get_crime_weight(point.get("category"))
        )
        cell_data["source_count"] = int(cell_data["source_count"]) + 1

    heatmap_cells: list[HeatmapCell] = []
    for (row, col), cell_data in cells_data.items():
        min_x = col * cell_size_metres
        max_x = (col + 1) * cell_size_metres
        min_y = row * cell_size_metres
        max_y = (row + 1) * cell_size_metres

        center_x = (min_x + max_x) / 2.0
        center_y = (min_y + max_y) / 2.0
        center_latitude, center_longitude = to_latitude_longitude(
            center_x,
            center_y,
            origin=origin,
        )
        min_latitude, min_longitude = to_latitude_longitude(
            min_x,
            min_y,
            origin=origin,
        )
        max_latitude, max_longitude = to_latitude_longitude(
            max_x,
            max_y,
            origin=origin,
        )

        heatmap_cells.append(
            HeatmapCell(
                cell_id=f"{row}:{col}",
                center_latitude=round(center_latitude, 7),
                center_longitude=round(center_longitude, 7),
                risk_score=round(float(cell_data["risk_score"]), 2),
                source_count=int(cell_data["source_count"]),
                bounds={
                    "min_latitude": round(min_latitude, 7),
                    "min_longitude": round(min_longitude, 7),
                    "max_latitude": round(max_latitude, 7),
                    "max_longitude": round(max_longitude, 7),
                },
            )
        )

    heatmap_cells.sort(
        key=lambda cell: (
            float(cell["risk_score"]),
            int(cell["source_count"]),
        ),
        reverse=True,
    )
    return heatmap_cells


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
    warnings = list(payload["route_crime_response"]["warnings"])

    if not geometry:
        route_points = []
        length_metres = 0.0
        length_km = 0.001
        warnings.append("missing_route_geometry")
    else:
        try:
            route_points = iter_route_points(geometry)
        except ValueError:
            route_points = []
            length_metres = 0.0
            length_km = 0.001
            warnings.append("invalid_route_geometry")
        else:
            length_metres = route_length_metres(route_points)
            length_km = max(length_metres / 1000.0, 0.001)
            if length_metres <= 0:
                warnings.append("invalid_route_geometry")

    incident_density = _compute_incident_density(
        payload=payload,
        route_length_metres=length_metres,
    )

    if incident_density is None:
        warnings.append("no_crime_data_found")

    heatmap_cells = build_heatmap_cells(
        crime_points=payload["route_crime_response"]["points"],
        route_points=route_points,
        corridor_half_width_metres=payload["corridor_half_width_metres"],
        cell_size_metres=payload["cell_size_metres"],
    )

    return RouteSafetyMetrics(
        incident_density=incident_density,
        report_density=None,
        warnings=sorted(set(warnings)),
        route_length_metres=length_metres,
        route_length_km=length_km,
        corridor_half_width_metres=payload["corridor_half_width_metres"],
        cell_size_metres=payload["cell_size_metres"],
        heatmap_cells=heatmap_cells,
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

    if db is None or not route_geometry_geojson:
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
<<<<<<< HEAD
        heatmap_cells=metrics["heatmap_cells"],
=======
        heatmap_cells=[],
>>>>>>> feat/updates
    )
