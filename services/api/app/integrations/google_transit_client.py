from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from html import unescape
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

GOOGLE_DIRECTIONS_URL = "https://maps.googleapis.com/maps/api/directions/json"
DEFAULT_ALTERNATIVES = 3
DEFAULT_TIMEOUT_SECONDS = 20.0
_HTML_TAG_PATTERN = re.compile(r"<[^>]+>")


def _build_candidate_label(index: int) -> str:
    return f"Transit Route {index}"


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


def _strip_html_instruction(value: str | None) -> str | None:
    text = unescape(_HTML_TAG_PATTERN.sub("", value or "")).strip()
    return text or None


def _decode_polyline(encoded: str) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    index = 0
    latitude = 0
    longitude = 0

    while index < len(encoded):
        result = 0
        shift = 0
        while True:
            chunk = ord(encoded[index]) - 63
            index += 1
            result |= (chunk & 0x1F) << shift
            shift += 5
            if chunk < 0x20:
                break
        delta_latitude = ~(result >> 1) if (result & 1) else (result >> 1)
        latitude += delta_latitude

        result = 0
        shift = 0
        while True:
            chunk = ord(encoded[index]) - 63
            index += 1
            result |= (chunk & 0x1F) << shift
            shift += 5
            if chunk < 0x20:
                break
        delta_longitude = ~(result >> 1) if (result & 1) else (result >> 1)
        longitude += delta_longitude

        points.append((latitude / 1e5, longitude / 1e5))

    return points


def _to_linestring(points: list[tuple[float, float]]) -> dict[str, Any] | None:
    unique: list[tuple[float, float]] = []
    for point in points:
        if not unique or unique[-1] != point:
            unique.append(point)

    if len(unique) < 2:
        return None

    return {
        "type": "LineString",
        "coordinates": [[longitude, latitude] for latitude, longitude in unique],
    }


def _iso_utc_from_unix(value: Any) -> str | None:
    try:
        timestamp = int(value)
    except (TypeError, ValueError):
        return None
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()


def _parse_maneuver_location(raw_step: dict[str, Any]) -> dict[str, float] | None:
    start_location = raw_step.get("start_location")
    if (
        isinstance(start_location, dict)
        and isinstance(start_location.get("lat"), (int, float))
        and isinstance(start_location.get("lng"), (int, float))
    ):
        return {
            "latitude": float(start_location["lat"]),
            "longitude": float(start_location["lng"]),
        }
    return None


def _parse_step_geometry(raw_step: dict[str, Any]) -> dict[str, Any] | None:
    raw_polyline = raw_step.get("polyline")
    if not isinstance(raw_polyline, dict):
        return None
    encoded = raw_polyline.get("points")
    if not isinstance(encoded, str) or not encoded:
        return None
    try:
        return _to_linestring(_decode_polyline(encoded))
    except Exception:
        return None


def _parse_navigation_steps(
    route: dict[str, Any],
) -> tuple[RouteNavigationMetadata, RouteTransportFeatures]:
    parsed_steps: list[RouteNavigationStep] = []
    step_index = 0
    transit_leg_count = 0
    late_service_available = False

    for leg in route.get("legs", []) or []:
        if not isinstance(leg, dict):
            continue

        for raw_step in leg.get("steps", []) or []:
            if not isinstance(raw_step, dict):
                continue

            travel_mode = str(raw_step.get("travel_mode") or "").strip().upper()
            transit_details = raw_step.get("transit_details")
            line_name: str | None = None
            from_stop: str | None = None
            to_stop: str | None = None
            depart_at: str | None = None
            arrive_at: str | None = None

            if isinstance(transit_details, dict):
                transit_leg_count += 1
                line = transit_details.get("line")
                if isinstance(line, dict):
                    line_name = str(line.get("short_name") or line.get("name") or "").strip() or None

                departure_stop = transit_details.get("departure_stop")
                if isinstance(departure_stop, dict):
                    from_stop = str(departure_stop.get("name") or "").strip() or None

                arrival_stop = transit_details.get("arrival_stop")
                if isinstance(arrival_stop, dict):
                    to_stop = str(arrival_stop.get("name") or "").strip() or None

                departure_time = transit_details.get("departure_time")
                if isinstance(departure_time, dict):
                    depart_at = _iso_utc_from_unix(departure_time.get("value"))

                arrival_time = transit_details.get("arrival_time")
                if isinstance(arrival_time, dict):
                    arrive_at = _iso_utc_from_unix(arrival_time.get("value"))

                if depart_at is not None:
                    hour = datetime.fromisoformat(depart_at).hour
                    if hour >= 22 or hour < 5:
                        late_service_available = True

            instruction = _strip_html_instruction(
                str(raw_step.get("html_instructions") or raw_step.get("instructions") or "")
            )

            distance_raw = raw_step.get("distance") if isinstance(raw_step.get("distance"), dict) else {}
            duration_raw = raw_step.get("duration") if isinstance(raw_step.get("duration"), dict) else {}

            maneuver = str(raw_step.get("maneuver") or "").strip() or None
            geometry_geojson = _parse_step_geometry(raw_step)
            maneuver_location = _parse_maneuver_location(raw_step)

            parsed_steps.append(
                RouteNavigationStep(
                    step_index=step_index,
                    distance_metres=int(round(float(distance_raw.get("value", 0.0)))),
                    duration_seconds=int(round(float(duration_raw.get("value", 0.0)))),
                    instruction=instruction,
                    street_name=line_name,
                    maneuver_type=maneuver,
                    maneuver_modifier=None,
                    maneuver_location=maneuver_location,
                    geometry_geojson=geometry_geojson,
                    mode=travel_mode.lower() or None,
                    line=line_name,
                    from_stop=from_stop,
                    to_stop=to_stop,
                    depart_at=depart_at,
                    arrive_at=arrive_at,
                )
            )
            step_index += 1

    transfer_count: int | None = None
    if transit_leg_count > 0:
        transfer_count = max(0, transit_leg_count - 1)

    night_transport_score: float | None = None
    if transfer_count is not None:
        score = 0.85 - (0.15 * transfer_count)
        if late_service_available:
            score += 0.1
        night_transport_score = round(max(0.0, min(1.0, score)), 4)

    return (
        RouteNavigationMetadata(provider="google_transit", steps=parsed_steps),
        RouteTransportFeatures(
            night_transport_score=night_transport_score,
            transfer_count=transfer_count,
            late_service_available=late_service_available if transfer_count is not None else None,
        ),
    )


def _parse_route_geometry(route: dict[str, Any], navigation: RouteNavigationMetadata) -> dict[str, Any]:
    overview_polyline = route.get("overview_polyline")
    if isinstance(overview_polyline, dict):
        encoded = overview_polyline.get("points")
        if isinstance(encoded, str) and encoded:
            try:
                geometry = _to_linestring(_decode_polyline(encoded))
                if geometry is not None:
                    return geometry
            except Exception:
                pass

    merged_points: list[tuple[float, float]] = []
    for step in navigation.steps:
        geometry = step.geometry_geojson
        if not isinstance(geometry, dict) or geometry.get("type") != "LineString":
            continue
        coordinates = geometry.get("coordinates")
        if not isinstance(coordinates, list):
            continue
        for pair in coordinates:
            if not isinstance(pair, list) or len(pair) < 2:
                continue
            longitude, latitude = pair[0], pair[1]
            if not isinstance(latitude, (int, float)) or not isinstance(longitude, (int, float)):
                continue
            merged_points.append((float(latitude), float(longitude)))

    geometry = _to_linestring(merged_points)
    if geometry is None:
        raise ValueError("Google transit route is missing usable geometry")
    return geometry


def _route_distance_and_duration(route: dict[str, Any]) -> tuple[int, int]:
    total_distance = 0
    total_duration = 0
    for leg in route.get("legs", []) or []:
        if not isinstance(leg, dict):
            continue
        leg_distance = leg.get("distance") if isinstance(leg.get("distance"), dict) else {}
        leg_duration = leg.get("duration") if isinstance(leg.get("duration"), dict) else {}
        total_distance += int(round(float(leg_distance.get("value", 0.0))))
        total_duration += int(round(float(leg_duration.get("value", 0.0))))

    if total_distance <= 0 or total_duration <= 0:
        raise ValueError("Google transit route is missing distance or duration")

    return total_distance, total_duration


def _google_route_to_candidate(route: dict[str, Any], *, index: int) -> RouteCandidateInput:
    navigation, transport = _parse_navigation_steps(route)
    geometry_geojson = _parse_route_geometry(route, navigation)
    distance_metres, duration_seconds = _route_distance_and_duration(route)
    features = _build_empty_features()
    features.transport = transport

    return RouteCandidateInput(
        candidate_id=f"google-transit-{index}",
        label=_build_candidate_label(index),
        provider="google_transit",
        distance_metres=distance_metres,
        duration_seconds=duration_seconds,
        geometry_geojson=geometry_geojson,
        navigation=navigation,
        features=features,
    )


def _parse_google_directions_payload(
    payload: dict[str, Any],
    *,
    alternatives: int,
) -> list[RouteCandidateInput]:
    status = str(payload.get("status") or "").strip().upper()
    if status != "OK":
        if status == "ZERO_RESULTS":
            raise ValueError("Google transit returned no routes")
        message = str(payload.get("error_message") or "").strip() or "Google transit provider error"
        if status:
            message = f"{message} ({status})"
        raise RuntimeError(message)

    routes = payload.get("routes")
    if not isinstance(routes, list) or not routes:
        raise ValueError("Google transit returned no routes")

    return [
        _google_route_to_candidate(route, index=index)
        for index, route in enumerate(routes[: max(1, alternatives)], start=1)
    ]


async def fetch_google_transit_route_candidates(
    *,
    origin_latitude: float,
    origin_longitude: float,
    destination_latitude: float,
    destination_longitude: float,
    depart_at: datetime,
    alternatives: int = DEFAULT_ALTERNATIVES,
) -> list[RouteCandidateInput]:
    api_key = os.getenv("GOOGLE_MAPS_API_KEY") or os.getenv("EXPO_PUBLIC_GOOGLE_MAPS_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_MAPS_API_KEY is not configured")

    params = {
        "origin": f"{origin_latitude},{origin_longitude}",
        "destination": f"{destination_latitude},{destination_longitude}",
        "mode": "transit",
        "alternatives": "true" if alternatives > 1 else "false",
        "departure_time": str(int(depart_at.timestamp())),
        "key": api_key,
    }

    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT_SECONDS) as client:
        response = await client.get(GOOGLE_DIRECTIONS_URL, params=params)
        response.raise_for_status()
        payload = response.json()

    if not isinstance(payload, dict):
        raise RuntimeError("Google transit provider returned an invalid response")

    return _parse_google_directions_payload(payload, alternatives=alternatives)
