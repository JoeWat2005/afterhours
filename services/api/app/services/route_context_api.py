from __future__ import annotations

from typing import Any

import httpx

from app.services.police_api import (
    iter_route_points,
    sample_route_points_by_distance,
)

OVERPASS_API_URL = "https://overpass-api.de/api/interpreter"
OVERPASS_TIMEOUT = 30.0


def _clamp_01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _build_bbox(
    points: list[tuple[float, float]],
    *,
    pad_degrees: float = 0.0015,
) -> tuple[float, float, float, float]:
    lats = [p[0] for p in points]
    lngs = [p[1] for p in points]
    return (
        min(lats) - pad_degrees,  # south
        min(lngs) - pad_degrees,  # west
        max(lats) + pad_degrees,  # north
        max(lngs) + pad_degrees,  # east
    )


def _build_overpass_query(
    *,
    south: float,
    west: float,
    north: float,
    east: float,
) -> str:
    # MVP query for:
    # - lighting
    # - stairs / lifts / ramps / escalators
    # - wheelchair accessibility
    # - waiting-area-ish places
    # - wifi/opening hours/staffed heuristics
    return f"""
    [out:json][timeout:25];
    (
      way["highway"]["lit"]({south},{west},{north},{east});
      node["highway"="street_lamp"]({south},{west},{north},{east});

      way["highway"="steps"]({south},{west},{north},{east});
      node["highway"="elevator"]({south},{west},{north},{east});
      way["ramp"]({south},{west},{north},{east});
      node["ramp"]({south},{west},{north},{east});
      way["conveying"]({south},{west},{north},{east});
      node["conveying"]({south},{west},{north},{east});

      way["wheelchair"]({south},{west},{north},{east});
      node["wheelchair"]({south},{west},{north},{east});

      node["amenity"]({south},{west},{north},{east});
      way["amenity"]({south},{west},{north},{east});

      node["shop"]({south},{west},{north},{east});
      way["shop"]({south},{west},{north},{east});

      node["public_transport"]({south},{west},{north},{east});
      way["public_transport"]({south},{west},{north},{east});

      node["railway"="station"]({south},{west},{north},{east});
      node["highway"="bus_stop"]({south},{west},{north},{east});
    );
    out tags center;
    """


def _get_center_lat_lng(el: dict[str, Any]) -> tuple[float, float] | None:
    if "lat" in el and "lon" in el:
        return float(el["lat"]), float(el["lon"])

    center = el.get("center")
    if isinstance(center, dict) and "lat" in center and "lon" in center:
        return float(center["lat"]), float(center["lon"])

    return None


def _approx_distance_metres(a: tuple[float, float], b: tuple[float, float]) -> float:
    # light-weight approximation for short route-corridor checks
    lat1, lon1 = a
    lat2, lon2 = b
    dx = (lon2 - lon1) * 111_320.0
    dy = (lat2 - lat1) * 110_540.0
    return (dx * dx + dy * dy) ** 0.5


def _is_near_route(
    lat: float,
    lon: float,
    sampled_points: list[tuple[float, float]],
    *,
    radius_metres: float,
) -> bool:
    target = (lat, lon)
    return any(
        _approx_distance_metres(target, route_point) <= radius_metres
        for route_point in sampled_points
    )


def _safe_waiting_place(tags: dict[str, Any]) -> bool:
    amenity = str(tags.get("amenity") or "").strip().lower()
    shop = str(tags.get("shop") or "").strip().lower()
    public_transport = str(tags.get("public_transport") or "").strip().lower()
    railway = str(tags.get("railway") or "").strip().lower()
    highway = str(tags.get("highway") or "").strip().lower()

    return any(
        [
            amenity in {
                "cafe",
                "restaurant",
                "fast_food",
                "pub",
                "bar",
                "library",
                "community_centre",
                "community_center",
                "police",
                "hospital",
                "pharmacy",
                "bank",
                "fuel",
            },
            shop != "",
            public_transport in {"platform", "stop_position", "station"},
            railway == "station",
            highway == "bus_stop",
        ]
    )


def _is_staffed(tags: dict[str, Any]) -> bool:
    staffed = str(tags.get("staffed") or "").strip().lower()
    amenity = str(tags.get("amenity") or "").strip().lower()
    shop = str(tags.get("shop") or "").strip().lower()
    railway = str(tags.get("railway") or "").strip().lower()

    if staffed in {"yes", "limited"}:
        return True

    return any(
        [
            amenity in {
                "cafe",
                "restaurant",
                "fast_food",
                "pub",
                "bar",
                "police",
                "hospital",
                "pharmacy",
                "bank",
                "fuel",
            },
            shop != "",
            railway == "station",
        ]
    )


def _is_open_ish(tags: dict[str, Any]) -> bool:
    # MVP heuristic: if opening_hours exists and is not obviously closed/off, count it.
    opening_hours = str(tags.get("opening_hours") or "").strip().lower()
    if not opening_hours:
        return False
    return opening_hours not in {"off", "closed"}


def _has_wifi(tags: dict[str, Any]) -> bool:
    internet_access = str(tags.get("internet_access") or "").strip().lower()
    return internet_access in {"wlan", "yes", "terminal", "service"}


def _is_well_lit(tags: dict[str, Any]) -> bool:
    lit = str(tags.get("lit") or "").strip().lower()
    return lit in {"yes", "automatic", "limited"}


async def fetch_route_context_features(
    *,
    route_geometry_geojson: dict[str, Any],
    sample_spacing_metres: float = 300.0,
    max_route_points: int = 24,
    near_route_radius_metres: float = 150.0,
    client: httpx.AsyncClient | None = None,
) -> dict[str, Any]:
    """
    Returns a dict with:
    - safety.lighting_score
    - accessibility feature estimates
    - waiting-area feature estimates
    - warnings

    This is heuristic MVP enrichment from OSM/Overpass.
    """
    warnings: list[str] = []

    try:
        route_points = iter_route_points(route_geometry_geojson)
    except ValueError:
        return {
            "lighting_score": None,
            "accessibility": {},
            "waiting_areas": {},
            "warnings": ["invalid_route_geometry"],
        }

    sampled_points = sample_route_points_by_distance(
        route_points,
        spacing_metres=sample_spacing_metres,
        max_points=max_route_points,
    )
    if not sampled_points:
        return {
            "lighting_score": None,
            "accessibility": {},
            "waiting_areas": {},
            "warnings": ["invalid_route_geometry"],
        }

    south, west, north, east = _build_bbox(sampled_points)
    query = _build_overpass_query(
        south=south,
        west=west,
        north=north,
        east=east,
    )

    owns_client = client is None
    if owns_client:
        client = httpx.AsyncClient(timeout=OVERPASS_TIMEOUT)

    try:
        response = await client.post(
            OVERPASS_API_URL,
            content=query,
            headers={"Content-Type": "text/plain"},
        )
        response.raise_for_status()
        payload = response.json()
    except Exception:
        return {
            "lighting_score": None,
            "accessibility": {},
            "waiting_areas": {},
            "warnings": ["route_context_api_unavailable"],
        }
    finally:
        if owns_client:
            await client.aclose()

    elements = payload.get("elements")
    if not isinstance(elements, list):
        return {
            "lighting_score": None,
            "accessibility": {},
            "waiting_areas": {},
            "warnings": ["route_context_api_invalid_response"],
        }

    lit_way_count = 0
    partial_lit_way_count = 0
    street_lamp_count = 0

    stairs_count = 0
    elevator_count = 0
    ramp_count = 0
    escalator_count = 0

    wheelchair_yes_count = 0
    wheelchair_limited_count = 0
    wheelchair_no_count = 0

    safe_waiting_area_count = 0
    well_lit_waiting_area_count = 0
    wifi_access_point_count = 0
    staffed_venue_count = 0
    open_venue_count = 0

    for el in elements:
        if not isinstance(el, dict):
            continue

        tags = el.get("tags") or {}
        center = _get_center_lat_lng(el)
        if center is None:
            continue

        lat, lon = center
        if not _is_near_route(
            lat,
            lon,
            sampled_points,
            radius_metres=near_route_radius_metres,
        ):
            continue

        el_type = str(el.get("type") or "").strip().lower()
        lit_value = str(tags.get("lit") or "").strip().lower()
        highway = str(tags.get("highway") or "").strip().lower()
        wheelchair = str(tags.get("wheelchair") or "").strip().lower()
        ramp = str(tags.get("ramp") or "").strip().lower()
        conveying = str(tags.get("conveying") or "").strip().lower()

        # Lighting
        if el_type == "way":
            if lit_value == "yes":
                lit_way_count += 1
            elif lit_value in {"automatic", "limited"}:
                partial_lit_way_count += 1

        if highway == "street_lamp":
            street_lamp_count += 1

        # Accessibility
        if highway == "steps":
            stairs_count += 1

        if highway == "elevator":
            elevator_count += 1

        if ramp in {"yes", "both"}:
            ramp_count += 1

        if conveying in {"yes", "forward", "backward", "reversible"}:
            escalator_count += 1

        if wheelchair == "yes":
            wheelchair_yes_count += 1
        elif wheelchair == "limited":
            wheelchair_limited_count += 1
        elif wheelchair == "no":
            wheelchair_no_count += 1

        # Waiting areas / places
        if _safe_waiting_place(tags):
            safe_waiting_area_count += 1

            if _is_well_lit(tags) or highway == "street_lamp":
                well_lit_waiting_area_count += 1

            if _has_wifi(tags):
                wifi_access_point_count += 1

            if _is_staffed(tags):
                staffed_venue_count += 1

            if _is_open_ish(tags):
                open_venue_count += 1

    lighting_evidence = lit_way_count + partial_lit_way_count + street_lamp_count
    if lighting_evidence == 0:
        warnings.append("no_lighting_data_found")
        lighting_score = None
    else:
        raw_lighting_score = (
            (lit_way_count * 1.0)
            + (partial_lit_way_count * 0.6)
            + (street_lamp_count * 0.08)
        )
        lighting_score = round(_clamp_01(raw_lighting_score / 12.0), 4)

    wheelchair_total = (
        wheelchair_yes_count + wheelchair_limited_count + wheelchair_no_count
    )
    if wheelchair_total > 0:
        step_free_ratio = round(
            _clamp_01(
                (wheelchair_yes_count + (0.5 * wheelchair_limited_count)) / wheelchair_total
            ),
            4,
        )
    else:
        # fallback heuristic: if stairs found and no accessibility evidence, assume poor step-free
        if stairs_count > 0:
            step_free_ratio = 0.0
        else:
            step_free_ratio = None
            warnings.append("no_accessibility_data_found")

    route_sample_count = max(len(sampled_points), 1)

    lift_coverage_ratio = round(_clamp_01(elevator_count / route_sample_count), 4)
    ramp_coverage_ratio = round(_clamp_01(ramp_count / route_sample_count), 4)
    escalator_coverage_ratio = round(_clamp_01(escalator_count / route_sample_count), 4)

    if safe_waiting_area_count > 0:
        waiting_areas_in_safe_areas_ratio = 1.0
    else:
        waiting_areas_in_safe_areas_ratio = 0.0
        warnings.append("no_waiting_area_data_found")

    return {
        "lighting_score": lighting_score,
        "accessibility": {
            "stairs_present": stairs_count > 0,
            "step_free_ratio": step_free_ratio,
            "lift_coverage_ratio": lift_coverage_ratio,
            "ramp_coverage_ratio": ramp_coverage_ratio,
            "escalator_coverage_ratio": escalator_coverage_ratio,
        },
        "waiting_areas": {
            "safe_waiting_area_count": safe_waiting_area_count,
            "well_lit_waiting_area_count": well_lit_waiting_area_count,
            "wifi_access_point_count": wifi_access_point_count,
            "staffed_venue_count": staffed_venue_count,
            "open_venue_count": open_venue_count,
            "waiting_areas_in_safe_areas_ratio": waiting_areas_in_safe_areas_ratio,
        },
        "warnings": sorted(set(warnings)),
    }