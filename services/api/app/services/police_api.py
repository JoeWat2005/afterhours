from app.services.police_api_config import CrimePoint, RouteCrimeResponse, DEFAULT_CATEGORY, DEFAULT_TIMEOUT, POLICE_API_BASE_URL
from typing import Any
import httpx


async def get_latest_crime_month(client: httpx.AsyncClient | None = None) -> str:
    owns_client = client is None
    if owns_client:
        client = httpx.AsyncClient(
            base_url=POLICE_API_BASE_URL,
            timeout=DEFAULT_TIMEOUT,
        )

    try:
        response = await client.get("/crimes-street-dates")
        response.raise_for_status()
        payload = response.json()

        if not isinstance(payload, list) or not payload:
            raise RuntimeError("Police API returned no available crime months")

        latest = payload[0].get("date")
        if not isinstance(latest, str) or len(latest) != 7:
            raise RuntimeError("Police API returned an invalid crime month")

        return latest
    finally:
        if owns_client:
            await client.aclose()


async def fetch_street_crimes_for_location(
    *,
    lat: float,
    lng: float,
    date: str | None = None,
    category: str = DEFAULT_CATEGORY,
    client: httpx.AsyncClient | None = None,
) -> list[dict[str, Any]]:
    owns_client = client is None
    if owns_client:
        client = httpx.AsyncClient(
            base_url=POLICE_API_BASE_URL,
            timeout=DEFAULT_TIMEOUT,
        )

    try:
        params: dict[str, Any] = {"lat": lat, "lng": lng}
        if date:
            params["date"] = date

        response = await client.get(f"/crimes-street/{category}", params=params)
        response.raise_for_status()

        payload = response.json()
        if not isinstance(payload, list):
            raise RuntimeError("Unexpected Police API response format")

        return payload
    finally:
        if owns_client:
            await client.aclose()


def _iter_route_points(geometry_geojson: dict[str, Any]) -> list[tuple[float, float]]:
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


def _sample_route_points(
    points: list[tuple[float, float]],
    *,
    max_points: int = 12,
) -> list[tuple[float, float]]:
    """
    Downsample route points so we don't make too many API calls.
    Always keeps the first and last point.
    """
    if len(points) <= max_points:
        return points

    if max_points < 2:
        max_points = 2

    sampled: list[tuple[float, float]] = []
    seen: set[tuple[float, float]] = set()

    step = (len(points) - 1) / (max_points - 1)
    for i in range(max_points):
        idx = round(i * step)
        point = points[idx]
        if point not in seen:
            sampled.append(point)
            seen.add(point)

    if points[-1] not in seen:
        sampled.append(points[-1])

    return sampled


def _crime_identity(raw_crime: dict[str, Any]) -> str:
    """
    Prefer persistent_id for deduping.
    Fall back to a composite key when it isn't present.
    """
    persistent_id = str(raw_crime.get("persistent_id") or "").strip()
    if persistent_id:
        return persistent_id

    location = raw_crime.get("location") or {}
    street = location.get("street") or {}

    return "|".join(
        [
            str(raw_crime.get("category") or ""),
            str(raw_crime.get("month") or ""),
            str(raw_crime.get("id") or ""),
            str(street.get("id") or ""),
            str(location.get("latitude") or ""),
            str(location.get("longitude") or ""),
        ]
    )


def _normalize_crime(raw_crime: dict[str, Any]) -> CrimePoint | None:
    """
    Convert the Police API crime record into our stable internal point shape.
    """
    location = raw_crime.get("location") or {}
    street = location.get("street") or {}

    lat_raw = location.get("latitude")
    lng_raw = location.get("longitude")

    if lat_raw is None or lng_raw is None:
        return None

    try:
        latitude = float(lat_raw)
        longitude = float(lng_raw)
    except (TypeError, ValueError):
        return None

    crime_id = str(
        raw_crime.get("persistent_id")
        or raw_crime.get("id")
        or _crime_identity(raw_crime)
    )

    return CrimePoint(
        crime_id=crime_id,
        category=str(raw_crime.get("category") or "unknown"),
        month=str(raw_crime.get("month") or ""),
        latitude=latitude,
        longitude=longitude,
        location_label=street.get("name"),
        source="uk_police",
    )


async def fetch_route_crime_points(
    *,
    route_geometry_geojson: dict[str, Any],
    route_id: str | None = None,
    date: str | None = None,
    category: str = DEFAULT_CATEGORY,
    max_route_points: int = 12,
) -> RouteCrimeResponse:
    """
    Fetch police crimes near a route and return a stable point-based response.

    This function does not build heatmap cells.
    It only returns normalized point data that another service or developer
    can use to build a heatmap.
    """
    route_points = _iter_route_points(route_geometry_geojson)
    sampled_points = _sample_route_points(route_points, max_points=max_route_points)

    warnings: list[str] = []
    deduped_raw_crimes: dict[str, dict[str, Any]] = {}

    async with httpx.AsyncClient(
        base_url=POLICE_API_BASE_URL,
        timeout=DEFAULT_TIMEOUT,
    ) as client:
        resolved_month = date or await get_latest_crime_month(client)

        for lat, lng in sampled_points:
            raw_crimes = await fetch_street_crimes_for_location(
                lat=lat,
                lng=lng,
                date=resolved_month,
                category=category,
                client=client,
            )
            for raw_crime in raw_crimes:
                deduped_raw_crimes[_crime_identity(raw_crime)] = raw_crime

    normalized_points: list[CrimePoint] = []
    skipped_count = 0

    for raw_crime in deduped_raw_crimes.values():
        point = _normalize_crime(raw_crime)
        if point is None:
            skipped_count += 1
            continue
        normalized_points.append(point)

    if skipped_count:
        warnings.append("some_crimes_missing_coordinates")
    if not normalized_points:
        warnings.append("no_crime_data_found")

    return RouteCrimeResponse(
        schema_version="1.0",
        route_id=route_id,
        crime_source="uk_police",
        crime_month=resolved_month,
        route_geometry_geojson=route_geometry_geojson,
        points=normalized_points,
        point_count=len(normalized_points),
        warnings=warnings,
    )