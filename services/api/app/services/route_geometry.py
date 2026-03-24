from math import asin, cos, radians, sin, sqrt
from typing import Any


def iter_route_points(geometry_geojson: dict[str, Any]) -> list[tuple[float, float]]:
    """
    Extract route points as (lat, lng) tuples from GeoJSON.
    Supports LineString and MultiLineString.
    GeoJSON coordinates are [lng, lat].
    """
    geometry_type = geometry_geojson.get("type")
    coordinates = geometry_geojson.get("coordinates")

    if geometry_type not in {"LineString", "MultiLineString"}:
        raise ValueError("route_geometry_geojson must be a LineString or MultiLineString")

    if coordinates is None:
        raise ValueError("route_geometry_geojson is missing coordinates")

    points: list[tuple[float, float]] = []

    if geometry_type == "LineString":
        for pair in coordinates:
            if not isinstance(pair, (list, tuple)) or len(pair) < 2:
                continue
            lng, lat = pair[0], pair[1]
            points.append((float(lat), float(lng)))
    else:
        for line in coordinates:
            for pair in line:
                if not isinstance(pair, (list, tuple)) or len(pair) < 2:
                    continue
                lng, lat = pair[0], pair[1]
                points.append((float(lat), float(lng)))

    if not points:
        raise ValueError("route_geometry_geojson contains no usable points")

    return points


def haversine_metres(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat1, lng1 = a
    lat2, lng2 = b

    earth_radius_metres = 6_371_000.0
    dlat = radians(lat2 - lat1)
    dlng = radians(lng2 - lng1)

    lat1_rad = radians(lat1)
    lat2_rad = radians(lat2)

    h = (
        sin(dlat / 2) ** 2
        + cos(lat1_rad) * cos(lat2_rad) * sin(dlng / 2) ** 2
    )
    return 2 * earth_radius_metres * asin(sqrt(h))


def route_length_metres(points: list[tuple[float, float]]) -> float:
    if len(points) < 2:
        return 0.0

    return sum(
        haversine_metres(points[i], points[i + 1])
        for i in range(len(points) - 1)
    )


def sample_route_points_by_distance(
    points: list[tuple[float, float]],
    *,
    spacing_metres: float,
    max_points: int,
) -> list[tuple[float, float]]:
    """
    Distance-based route sampling.
    Always keeps first and last point.
    """
    if not points:
        return []

    if len(points) <= 2:
        return points

    if spacing_metres <= 0:
        raise ValueError("spacing_metres must be greater than zero")

    if max_points < 2:
        max_points = 2

    sampled: list[tuple[float, float]] = [points[0]]
    distance_since_last_sample = 0.0

    for i in range(1, len(points)):
        segment_distance = haversine_metres(points[i - 1], points[i])
        distance_since_last_sample += segment_distance

        if distance_since_last_sample >= spacing_metres:
            if points[i] != sampled[-1]:
                sampled.append(points[i])
            distance_since_last_sample = 0.0

        if len(sampled) >= max_points - 1:
            break

    if sampled[-1] != points[-1]:
        sampled.append(points[-1])

    if len(sampled) > max_points:
        thinned: list[tuple[float, float]] = []
        step = (len(sampled) - 1) / (max_points - 1)
        seen: set[tuple[float, float]] = set()

        for i in range(max_points):
            idx = round(i * step)
            point = sampled[idx]
            if point not in seen:
                thinned.append(point)
                seen.add(point)

        if points[-1] not in seen:
            thinned.append(points[-1])

        sampled = thinned[:max_points]

    return sampled