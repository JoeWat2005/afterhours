from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from time import monotonic
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.route_enrichment_config import (
    DEFAULT_MAX_ROUTE_FETCH_POINTS,
    DEFAULT_ROUTE_SAMPLE_SPACING_METRES,
)
from app.integrations.overpass_client import fetch_route_transit_overlays
from app.schemas.routes import (
    RouteOverlayInclude,
    RouteOverlayItem,
    RouteOverlayType,
    RouteOverlaysRequest,
    RouteOverlaysResponse,
)
from app.services.emergency_services import BIRMINGHAM_SERVICE_SEEDS
from app.services.route_geometry import iter_route_points, sample_route_points_by_distance
from app.services.route_safety import list_unique_reports_along_route, point_to_route_distance

_STATIC_CACHE_TTL_SECONDS = 600
_DYNAMIC_CACHE_TTL_SECONDS = 45
_MAX_CACHE_ENTRIES = 256
_CACHE_ROUNDING_DECIMALS = 5

_static_cache: dict[str, tuple[float, list[RouteOverlayItem], list[str]]] = {}
_dynamic_cache: dict[str, tuple[float, list[RouteOverlayItem], list[str]]] = {}


def clear_route_overlay_cache() -> None:
    _static_cache.clear()
    _dynamic_cache.clear()


def _normalize_geometry_for_cache(value: Any) -> Any:
    if isinstance(value, float):
        return round(value, _CACHE_ROUNDING_DECIMALS)
    if isinstance(value, list):
        return [_normalize_geometry_for_cache(item) for item in value]
    if isinstance(value, dict):
        return {key: _normalize_geometry_for_cache(val) for key, val in sorted(value.items())}
    return value


def _cache_key(
    *,
    request: RouteOverlaysRequest,
    include: set[RouteOverlayInclude],
) -> str:
    payload = {
        "geometry": _normalize_geometry_for_cache(request.route_geometry_geojson),
        "include": sorted(item.value for item in include),
        "near_route_radius_metres": request.near_route_radius_metres,
        "limit_per_type": request.limit_per_type,
        "report_max_age_days": request.report_max_age_days,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _prune_cache(
    cache: dict[str, tuple[float, list[RouteOverlayItem], list[str]]],
    *,
    now: float,
) -> None:
    expired = [key for key, (expires_at, _, _) in cache.items() if expires_at <= now]
    for key in expired:
        cache.pop(key, None)

    if len(cache) <= _MAX_CACHE_ENTRIES:
        return

    oldest = sorted(cache.items(), key=lambda item: item[1][0])
    for key, _ in oldest[: max(0, len(cache) - _MAX_CACHE_ENTRIES)]:
        cache.pop(key, None)


def _copy_cached_items(items: list[RouteOverlayItem]) -> list[RouteOverlayItem]:
    return [item.model_copy(deep=True) for item in items]


async def _fetch_transit_items(
    request: RouteOverlaysRequest,
) -> tuple[list[RouteOverlayItem], list[str]]:
    response = await fetch_route_transit_overlays(
        route_geometry_geojson=request.route_geometry_geojson,
        near_route_radius_metres=float(request.near_route_radius_metres),
        limit=request.limit_per_type,
    )

    warnings = list(response.get("warnings") or [])
    items: list[RouteOverlayItem] = []
    for raw_item in response.get("items", []) or []:
        metadata = raw_item.get("metadata")
        if not isinstance(metadata, dict):
            metadata = {}

        items.append(
            RouteOverlayItem(
                id=str(raw_item.get("id") or ""),
                overlay_type=RouteOverlayType.TRANSIT,
                subtype=str(raw_item.get("subtype") or "unknown"),
                name=raw_item.get("name"),
                latitude=float(raw_item.get("latitude")),
                longitude=float(raw_item.get("longitude")),
                distance_from_route_metres=float(raw_item.get("distance_from_route_metres", 0)),
                source=str(raw_item.get("source") or "overpass"),
                metadata=metadata,
            )
        )

    return items[: request.limit_per_type], warnings


async def _fetch_report_items(
    request: RouteOverlaysRequest,
    *,
    route_points: list[tuple[float, float]],
    db: AsyncSession | None,
) -> tuple[list[RouteOverlayItem], list[str]]:
    if db is None:
        return [], ["reports_unavailable_without_db"]

    sampled_points = sample_route_points_by_distance(
        route_points,
        spacing_metres=DEFAULT_ROUTE_SAMPLE_SPACING_METRES,
        max_points=DEFAULT_MAX_ROUTE_FETCH_POINTS,
    )
    reports = await list_unique_reports_along_route(
        db,
        sampled_points=sampled_points,
        radius_metres=float(request.near_route_radius_metres),
        per_point_limit=request.limit_per_type,
        max_age_days=request.report_max_age_days,
    )

    items: list[tuple[float, str, RouteOverlayItem]] = []
    for report in reports:
        latitude = getattr(report, "latitude", None)
        longitude = getattr(report, "longitude", None)
        if not isinstance(latitude, (int, float)) or not isinstance(longitude, (int, float)):
            continue

        distance = point_to_route_distance(
            (float(latitude), float(longitude)),
            route_points=route_points,
        )
        if distance > request.near_route_radius_metres:
            continue

        created_at = getattr(report, "created_at", None)
        created_at_iso: str | None = None
        created_at_sort = ""
        if isinstance(created_at, datetime):
            created_at_iso = created_at.astimezone(timezone.utc).isoformat()
            created_at_sort = created_at_iso

        item = RouteOverlayItem(
            id=f"report-{getattr(report, 'id', 'unknown')}",
            overlay_type=RouteOverlayType.REPORT,
            subtype=str(getattr(report, "category", "other")),
            name=str(getattr(report, "summary", "") or "").strip() or None,
            latitude=float(latitude),
            longitude=float(longitude),
            distance_from_route_metres=round(float(distance), 2),
            source="report_db",
            metadata={
                "severity": str(getattr(report, "severity", "") or "").strip() or None,
                "created_at": created_at_iso,
            },
        )
        items.append((distance, created_at_sort, item))

    items.sort(key=lambda row: (row[0], row[1]), reverse=False)
    return [row[2] for row in items[: request.limit_per_type]], []


async def _fetch_service_items(
    request: RouteOverlaysRequest,
    *,
    route_points: list[tuple[float, float]],
) -> tuple[list[RouteOverlayItem], list[str]]:
    candidates: list[RouteOverlayItem] = []
    for seed in BIRMINGHAM_SERVICE_SEEDS:
        distance = point_to_route_distance(
            (seed.latitude, seed.longitude),
            route_points=route_points,
        )
        if distance > request.near_route_radius_metres:
            continue

        candidates.append(
            RouteOverlayItem(
                id=f"service-{seed.id}",
                overlay_type=RouteOverlayType.SERVICE,
                subtype=seed.category.value,
                name=seed.name,
                latitude=seed.latitude,
                longitude=seed.longitude,
                distance_from_route_metres=round(float(distance), 2),
                source="seed",
                metadata={"address": seed.address},
            )
        )

    candidates.sort(
        key=lambda item: (
            float(item.distance_from_route_metres or 0.0),
            item.name or "",
            item.id,
        )
    )
    return candidates[: request.limit_per_type], []


async def _load_static_items(
    request: RouteOverlaysRequest,
    *,
    route_points: list[tuple[float, float]],
    include: set[RouteOverlayInclude],
) -> tuple[list[RouteOverlayItem], list[str]]:
    items: list[RouteOverlayItem] = []
    warnings: list[str] = []

    if RouteOverlayInclude.TRANSIT in include:
        try:
            transit_items, transit_warnings = await _fetch_transit_items(request)
            items.extend(transit_items)
            warnings.extend(transit_warnings)
        except Exception:
            warnings.append("transit_overlay_fetch_failed")

    if RouteOverlayInclude.SERVICES in include:
        try:
            service_items, service_warnings = await _fetch_service_items(
                request,
                route_points=route_points,
            )
            items.extend(service_items)
            warnings.extend(service_warnings)
        except Exception:
            warnings.append("services_overlay_fetch_failed")

    return items, warnings


async def _load_dynamic_items(
    request: RouteOverlaysRequest,
    *,
    route_points: list[tuple[float, float]],
    include: set[RouteOverlayInclude],
    db: AsyncSession | None,
) -> tuple[list[RouteOverlayItem], list[str]]:
    items: list[RouteOverlayItem] = []
    warnings: list[str] = []

    if RouteOverlayInclude.REPORTS in include:
        try:
            report_items, report_warnings = await _fetch_report_items(
                request,
                route_points=route_points,
                db=db,
            )
            items.extend(report_items)
            warnings.extend(report_warnings)
        except Exception:
            warnings.append("reports_overlay_fetch_failed")

    return items, warnings


async def get_route_overlays(
    request: RouteOverlaysRequest,
    *,
    db: AsyncSession | None,
) -> RouteOverlaysResponse:
    route_points = iter_route_points(request.route_geometry_geojson)
    include = set(request.include)
    now = monotonic()

    static_items: list[RouteOverlayItem] = []
    static_warnings: list[str] = []
    static_include = include & {RouteOverlayInclude.TRANSIT, RouteOverlayInclude.SERVICES}
    if static_include:
        static_key = _cache_key(request=request, include=static_include)
        cached_static = _static_cache.get(static_key)
        if cached_static and cached_static[0] > now:
            static_items = _copy_cached_items(cached_static[1])
            static_warnings = list(cached_static[2])
        else:
            static_items, static_warnings = await _load_static_items(
                request,
                route_points=route_points,
                include=static_include,
            )
            _static_cache[static_key] = (
                now + _STATIC_CACHE_TTL_SECONDS,
                _copy_cached_items(static_items),
                list(static_warnings),
            )
            _prune_cache(_static_cache, now=now)

    dynamic_items: list[RouteOverlayItem] = []
    dynamic_warnings: list[str] = []
    dynamic_include = include & {RouteOverlayInclude.REPORTS}
    if dynamic_include:
        dynamic_key = _cache_key(request=request, include=dynamic_include)
        cached_dynamic = _dynamic_cache.get(dynamic_key)
        if cached_dynamic and cached_dynamic[0] > now:
            dynamic_items = _copy_cached_items(cached_dynamic[1])
            dynamic_warnings = list(cached_dynamic[2])
        else:
            dynamic_items, dynamic_warnings = await _load_dynamic_items(
                request,
                route_points=route_points,
                include=dynamic_include,
                db=db,
            )
            _dynamic_cache[dynamic_key] = (
                now + _DYNAMIC_CACHE_TTL_SECONDS,
                _copy_cached_items(dynamic_items),
                list(dynamic_warnings),
            )
            _prune_cache(_dynamic_cache, now=now)

    all_items = static_items + dynamic_items
    all_items.sort(
        key=lambda item: (
            float(item.distance_from_route_metres if item.distance_from_route_metres is not None else 10_000_000),
            item.overlay_type.value,
            item.subtype,
            item.id,
        )
    )

    return RouteOverlaysResponse(
        items=all_items,
        warnings=sorted(set(static_warnings + dynamic_warnings)),
        generated_at=datetime.now(timezone.utc),
    )
