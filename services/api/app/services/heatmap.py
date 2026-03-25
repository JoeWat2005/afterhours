from __future__ import annotations

import asyncio
from dataclasses import dataclass
from math import floor, sqrt
from time import monotonic
from typing import Any, TypedDict

import httpx

from app.core.route_enrichment_config import DEFAULT_CATEGORY, DEFAULT_TIMEOUT, POLICE_API_BASE_URL
from app.integrations import police_client
from app.services.route_safety import (
    get_crime_weight,
    to_latitude_longitude,
    to_xy_metre_coordinates,
)


_CACHE_TTL_SECONDS = 300
_MAX_CACHE_ENTRIES = 128
_SAMPLING_SPACING_METRES = 2500.0
_MAX_CONCURRENT_POLICE_REQUESTS = 16


class HeatmapCellBounds(TypedDict):
    min_latitude: float
    min_longitude: float
    max_latitude: float
    max_longitude: float


class HeatmapCell(TypedDict):
    cell_id: str
    center_latitude: float
    center_longitude: float
    risk_score: float
    source_count: int
    bounds: HeatmapCellBounds


@dataclass(frozen=True)
class HeatmapQuery:
    latitude: float
    longitude: float
    radius_metres: int
    cell_size_metres: int
    category: str = DEFAULT_CATEGORY
    date: str | None = None


@dataclass(frozen=True)
class HeatmapResult:
    latitude: float
    longitude: float
    radius_metres: int
    cell_size_metres: int
    category: str
    date: str | None
    items: list[HeatmapCell]


_cache: dict[str, tuple[float, HeatmapResult]] = {}


def clear_heatmap_cache() -> None:
    _cache.clear()


def _cache_key(query: HeatmapQuery) -> str:
    return "|".join(
        [
            str(round(query.latitude, 4)),
            str(round(query.longitude, 4)),
            str(query.radius_metres),
            str(query.cell_size_metres),
            query.category,
            query.date or "latest",
        ]
    )


def _prune_cache(now: float) -> None:
    expired_keys = [key for key, (expires_at, _) in _cache.items() if expires_at <= now]
    for key in expired_keys:
        _cache.pop(key, None)

    if len(_cache) <= _MAX_CACHE_ENTRIES:
        return

    oldest_keys = sorted(_cache.items(), key=lambda item: item[1][0])
    for key, _ in oldest_keys[: max(0, len(_cache) - _MAX_CACHE_ENTRIES)]:
        _cache.pop(key, None)


def _generate_sample_points(
    *,
    latitude: float,
    longitude: float,
    radius_metres: int,
) -> list[tuple[float, float]]:
    if radius_metres <= 0:
        return [(latitude, longitude)]

    origin = (latitude, longitude)
    offsets: list[tuple[float, float]] = [(0.0, 0.0)]

    y = -float(radius_metres)
    while y <= float(radius_metres):
        max_x = sqrt(max(0.0, float(radius_metres * radius_metres) - (y * y)))
        x = -max_x
        while x <= max_x:
            offsets.append((x, y))
            x += _SAMPLING_SPACING_METRES
        y += _SAMPLING_SPACING_METRES

    points: list[tuple[float, float]] = []
    seen: set[tuple[float, float]] = set()
    for x_metres, y_metres in offsets:
        point_latitude, point_longitude = to_latitude_longitude(
            x_metres,
            y_metres,
            origin=origin,
        )
        key = (round(point_latitude, 6), round(point_longitude, 6))
        if key in seen:
            continue
        seen.add(key)
        points.append((point_latitude, point_longitude))

    return points


async def _fetch_deduped_crimes(
    *,
    sample_points: list[tuple[float, float]],
    category: str,
    date: str | None,
) -> tuple[list[dict[str, Any]], str | None]:
    if not sample_points:
        return [], date

    semaphore = asyncio.Semaphore(_MAX_CONCURRENT_POLICE_REQUESTS)
    deduped: dict[str, dict[str, Any]] = {}

    async with httpx.AsyncClient(base_url=POLICE_API_BASE_URL, timeout=DEFAULT_TIMEOUT) as client:
        resolved_date = date
        if resolved_date is None:
            try:
                resolved_date = await police_client.get_latest_crime_month(client)
            except (httpx.HTTPError, RuntimeError):
                resolved_date = None

        async def fetch_point(point: tuple[float, float]) -> list[dict[str, Any]]:
            point_latitude, point_longitude = point
            async with semaphore:
                try:
                    return await police_client.fetch_street_crimes_for_location(
                        lat=point_latitude,
                        lng=point_longitude,
                        date=resolved_date,
                        category=category,
                        client=client,
                    )
                except (httpx.HTTPError, RuntimeError):
                    return []

        results = await asyncio.gather(*(fetch_point(point) for point in sample_points))

    for crimes in results:
        for raw_crime in crimes:
            deduped[police_client._crime_identity(raw_crime)] = raw_crime

    return list(deduped.values()), resolved_date


def _build_heatmap_cells(
    *,
    crimes: list[dict[str, Any]],
    query: HeatmapQuery,
) -> list[HeatmapCell]:
    origin = (query.latitude, query.longitude)
    cells: dict[tuple[int, int], dict[str, float | int]] = {}
    radius_squared = float(query.radius_metres * query.radius_metres)

    for raw_crime in crimes:
        normalized = police_client._normalize_crime(raw_crime)
        if normalized is None:
            continue

        latitude = normalized["latitude"]
        longitude = normalized["longitude"]
        x_metres, y_metres = to_xy_metre_coordinates(
            (latitude, longitude),
            origin=origin,
        )

        if (x_metres * x_metres) + (y_metres * y_metres) > radius_squared:
            continue

        row = floor(y_metres / query.cell_size_metres)
        col = floor(x_metres / query.cell_size_metres)
        key = (row, col)

        data = cells.setdefault(key, {"risk_score": 0.0, "source_count": 0})
        data["risk_score"] = float(data["risk_score"]) + float(
            get_crime_weight(normalized.get("category"))
        )
        data["source_count"] = int(data["source_count"]) + 1

    items: list[HeatmapCell] = []
    for (row, col), data in cells.items():
        min_x = col * query.cell_size_metres
        max_x = (col + 1) * query.cell_size_metres
        min_y = row * query.cell_size_metres
        max_y = (row + 1) * query.cell_size_metres

        center_latitude, center_longitude = to_latitude_longitude(
            (min_x + max_x) / 2.0,
            (min_y + max_y) / 2.0,
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

        items.append(
            HeatmapCell(
                cell_id=f"{row}:{col}",
                center_latitude=round(center_latitude, 7),
                center_longitude=round(center_longitude, 7),
                risk_score=round(float(data["risk_score"]), 2),
                source_count=int(data["source_count"]),
                bounds=HeatmapCellBounds(
                    min_latitude=round(min_latitude, 7),
                    min_longitude=round(min_longitude, 7),
                    max_latitude=round(max_latitude, 7),
                    max_longitude=round(max_longitude, 7),
                ),
            )
        )

    items.sort(
        key=lambda item: (
            item["risk_score"],
            item["source_count"],
        ),
        reverse=True,
    )
    return items


async def get_on_demand_heatmap(query: HeatmapQuery) -> HeatmapResult:
    key = _cache_key(query)
    now = monotonic()
    cached = _cache.get(key)
    if cached and cached[0] > now:
        return cached[1]

    sample_points = _generate_sample_points(
        latitude=query.latitude,
        longitude=query.longitude,
        radius_metres=query.radius_metres,
    )
    crimes, resolved_date = await _fetch_deduped_crimes(
        sample_points=sample_points,
        category=query.category,
        date=query.date,
    )
    items = _build_heatmap_cells(crimes=crimes, query=query)

    result = HeatmapResult(
        latitude=query.latitude,
        longitude=query.longitude,
        radius_metres=query.radius_metres,
        cell_size_metres=query.cell_size_metres,
        category=query.category,
        date=resolved_date,
        items=items,
    )

    _cache[key] = (now + _CACHE_TTL_SECONDS, result)
    _prune_cache(now)
    return result
