from __future__ import annotations

import os
from typing import Any

import httpx

from app.schemas.routes import (
    RouteAccessibilityFeatures,
    RouteCandidateFeatures,
    RouteCandidateInput,
    RouteNavigationMetadata,
    RouteNavigationStep,
    RouteSafetyFeatures,
    RouteTransportFeatures,
    RouteWaitingAreaFeatures,
)

MAPBOX_DIRECTIONS_URL = "https://api.mapbox.com/directions/v5/mapbox/walking/{coordinates}"
DEFAULT_ALTERNATIVES = 3
DEFAULT_TIMEOUT_SECONDS = 20.0


def _build_candidate_label(index: int) -> str:
    return f"Route {index}"


def _build_empty_features() -> RouteCandidateFeatures:
    return RouteCandidateFeatures(
        safety=RouteSafetyFeatures(
            incident_density=None,
            report_density=None,
            lighting_score=None,
            warnings=[],
        ),
        accessibility=RouteAccessibilityFeatures(
            stairs_present=None,
            step_free_ratio=None,
            lift_coverage_ratio=None,
            ramp_coverage_ratio=None,
            escalator_coverage_ratio=None,
        ),
        waiting_areas=RouteWaitingAreaFeatures(
            safe_waiting_area_count=None,
            well_lit_waiting_area_count=None,
            wifi_access_point_count=None,
            staffed_venue_count=None,
            open_venue_count=None,
            waiting_areas_in_safe_areas_ratio=None,
            max_gap_between_safe_waiting_areas_metres=None,
        ),
        transport=RouteTransportFeatures(
            night_transport_score=None,
            transfer_count=None,
            late_service_available=None,
        ),
    )


def _coerce_linestring_geometry(route: dict[str, Any]) -> dict[str, Any]:
    geometry = route.get("geometry")

    if not isinstance(geometry, dict):
        raise ValueError("Mapbox route is missing GeoJSON geometry")

    geometry_type = geometry.get("type")
    if geometry_type not in {"LineString", "MultiLineString"}:
        raise ValueError("Mapbox route geometry must be LineString or MultiLineString")

    coordinates = geometry.get("coordinates")
    if coordinates is None:
        raise ValueError("Mapbox route geometry is missing coordinates")

    return geometry


def _parse_navigation_steps(route: dict[str, Any]) -> RouteNavigationMetadata:
    parsed_steps: list[RouteNavigationStep] = []

    step_index = 0
    for leg in route.get("legs", []) or []:
        if not isinstance(leg, dict):
            continue
        for raw_step in leg.get("steps", []) or []:
            if not isinstance(raw_step, dict):
                continue

            maneuver = raw_step.get("maneuver")
            if not isinstance(maneuver, dict):
                maneuver = {}

            maneuver_location: dict[str, float] | None = None
            raw_location = maneuver.get("location")
            if (
                isinstance(raw_location, list)
                and len(raw_location) >= 2
                and all(isinstance(value, (int, float)) for value in raw_location[:2])
            ):
                maneuver_location = {
                    "longitude": float(raw_location[0]),
                    "latitude": float(raw_location[1]),
                }

            raw_geometry = raw_step.get("geometry")
            geometry_geojson = (
                raw_geometry
                if isinstance(raw_geometry, dict)
                and raw_geometry.get("type") in {"LineString", "MultiLineString"}
                and raw_geometry.get("coordinates") is not None
                else None
            )

            parsed_steps.append(
                RouteNavigationStep(
                    step_index=step_index,
                    distance_metres=int(round(float(raw_step.get("distance", 0.0)))),
                    duration_seconds=int(round(float(raw_step.get("duration", 0.0)))),
                    instruction=str(maneuver.get("instruction") or "").strip() or None,
                    street_name=str(raw_step.get("name") or "").strip() or None,
                    maneuver_type=str(maneuver.get("type") or "").strip() or None,
                    maneuver_modifier=str(maneuver.get("modifier") or "").strip()
                    or None,
                    maneuver_location=maneuver_location,
                    geometry_geojson=geometry_geojson,
                )
            )
            step_index += 1

    return RouteNavigationMetadata(provider="mapbox", steps=parsed_steps)


def _mapbox_route_to_candidate(route: dict[str, Any], *, index: int) -> RouteCandidateInput:
    geometry_geojson = _coerce_linestring_geometry(route)
    navigation = _parse_navigation_steps(route)

    return RouteCandidateInput(
        candidate_id=f"mapbox-{index}",
        label=_build_candidate_label(index),
        provider="mapbox",
        distance_metres=int(round(float(route["distance"]))),
        duration_seconds=int(round(float(route["duration"]))),
        geometry_geojson=geometry_geojson,
        navigation=navigation,
        features=_build_empty_features(),
    )


async def fetch_mapbox_route_candidates(
    *,
    origin_latitude: float,
    origin_longitude: float,
    destination_latitude: float,
    destination_longitude: float,
    alternatives: int = DEFAULT_ALTERNATIVES,
) -> list[RouteCandidateInput]:
    access_token = os.getenv("EXPO_PUBLIC_MAPBOX_ACCESS_TOKEN")
    if not access_token:
        raise RuntimeError("EXPO_PUBLIC_MAPBOX_ACCESS_TOKEN is not configured")

    coordinates = (
        f"{origin_longitude},{origin_latitude};"
        f"{destination_longitude},{destination_latitude}"
    )

    url = MAPBOX_DIRECTIONS_URL.format(coordinates=coordinates)

    params = {
        "access_token": access_token,
        "alternatives": "true" if alternatives > 1 else "false",
        "geometries": "geojson",
        "overview": "full",
        "steps": "true",
    }

    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT_SECONDS) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        payload = response.json()

    raw_routes = payload.get("routes", [])
    if not raw_routes:
        raise ValueError("Mapbox returned no routes")

    limited_routes = raw_routes[: max(1, alternatives)]

    return [
        _mapbox_route_to_candidate(route, index=index)
        for index, route in enumerate(limited_routes, start=1)
    ]
