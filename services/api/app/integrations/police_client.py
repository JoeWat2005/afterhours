import asyncio
from typing import Any, TypedDict
from app.services.route_geometry import route_length_metres

import httpx

from app.core.route_enrichment_config import (
    DEFAULT_CATEGORY,
    DEFAULT_MAX_ROUTE_FETCH_POINTS,
    DEFAULT_ROUTE_SAMPLE_SPACING_METRES,
    DEFAULT_TIMEOUT,
    HTTP_RETRY_ATTEMPTS,
    HTTP_RETRY_BASE_DELAY_SECONDS,
    POLICE_API_BASE_URL,
)
from app.services.route_geometry import (
    iter_route_points,
    sample_route_points_by_distance,
)


class CrimePoint(TypedDict):
    crime_id: str
    category: str
    month: str
    latitude: float
    longitude: float
    location_label: str | None
    source: str


class RouteCrimeResponse(TypedDict):
    schema_version: str
    route_id: str | None
    crime_source: str
    crime_month: str
    route_geometry_geojson: dict[str, Any]
    points: list[CrimePoint]
    point_count: int
    warnings: list[str]


RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


def _is_retryable_status(status_code: int) -> bool:
    return status_code in RETRYABLE_STATUS_CODES


def _retry_delay_seconds(attempt_index: int) -> float:
    return HTTP_RETRY_BASE_DELAY_SECONDS * (2**attempt_index)


async def _request_with_retries(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    **kwargs: Any,
) -> httpx.Response:
    last_error: Exception | None = None

    for attempt in range(HTTP_RETRY_ATTEMPTS):
        try:
            response = await client.request(method, url, **kwargs)
            response.raise_for_status()
            return response
        except httpx.HTTPStatusError as exc:
            last_error = exc
            if (
                not _is_retryable_status(exc.response.status_code)
                or attempt == HTTP_RETRY_ATTEMPTS - 1
            ):
                raise
        except httpx.RequestError as exc:
            last_error = exc
            if attempt == HTTP_RETRY_ATTEMPTS - 1:
                raise

        await asyncio.sleep(_retry_delay_seconds(attempt))

    if last_error is not None:
        raise last_error
    raise RuntimeError("HTTP request failed unexpectedly")


async def get_latest_crime_month(client: httpx.AsyncClient | None = None) -> str:
    owns_client = client is None
    if owns_client:
        client = httpx.AsyncClient(
            base_url=POLICE_API_BASE_URL,
            timeout=DEFAULT_TIMEOUT,
        )

    try:
        response = await _request_with_retries(client, "GET", "/crimes-street-dates")
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
    from app.core.cache import cache_get, cache_set

    # round coords so nearby points share cache
    cache_key = {"lat": round(lat, 3), "lng": round(lng, 3), "date": date, "cat": category}
    cached = await cache_get("police_crimes", cache_key)
    if cached is not None:
        return cached

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

        response = await _request_with_retries(
            client,
            "GET",
            f"/crimes-street/{category}",
            params=params,
        )

        payload = response.json()
        if not isinstance(payload, list):
            raise RuntimeError("Unexpected Police API response format")

        # crime data is monthly so cache for 24h
        await cache_set("police_crimes", cache_key, payload, ttl_seconds=86400)
        return payload
    finally:
        if owns_client:
            await client.aclose()


def _crime_identity(raw_crime: dict[str, Any]) -> str:
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
    route_geometry_geojson: dict[str, Any] | None,
    route_id: str | None = None,
    date: str | None = None,
    category: str = DEFAULT_CATEGORY,
    sample_spacing_metres: float = DEFAULT_ROUTE_SAMPLE_SPACING_METRES,
    max_route_points: int = DEFAULT_MAX_ROUTE_FETCH_POINTS,
) -> RouteCrimeResponse:
    if not route_geometry_geojson:
        return RouteCrimeResponse(
            schema_version="1.0",
            route_id=route_id,
            crime_source="uk_police",
            crime_month=date or "unknown",
            route_geometry_geojson={},
            points=[],
            point_count=0,
            warnings=["missing_route_geometry", "no_crime_data_found"],
        )

    route_points = iter_route_points(route_geometry_geojson)

    if not route_points:
        return RouteCrimeResponse(
            schema_version="1.0",
            route_id=route_id,
            crime_source="uk_police",
            crime_month=date or "unknown",
            route_geometry_geojson=route_geometry_geojson,
            points=[],
            point_count=0,
            warnings=["empty_route_geometry", "no_crime_data_found"],
        )

    sampled_points = sample_route_points_by_distance(
        route_points,
        spacing_metres=sample_spacing_metres,
        max_points=max_route_points,
    )

    warnings: list[str] = []
    deduped_raw_crimes: dict[str, dict[str, Any]] = {}

    async with httpx.AsyncClient(
        base_url=POLICE_API_BASE_URL,
        timeout=DEFAULT_TIMEOUT,
    ) as client:
        if date:
            resolved_month = date
        else:
            try:
                resolved_month = await get_latest_crime_month(client)
            except (httpx.HTTPError, RuntimeError):
                resolved_month = "unknown"
                warnings.append("police_api_month_lookup_failed")

        failed_point_fetches = 0
        for lat, lng in sampled_points:
            try:
                raw_crimes = await fetch_street_crimes_for_location(
                    lat=lat,
                    lng=lng,
                    date=None if resolved_month == "unknown" else resolved_month,
                    category=category,
                    client=client,
                )
            except (httpx.HTTPError, RuntimeError):
                failed_point_fetches += 1
                continue

            for raw_crime in raw_crimes:
                deduped_raw_crimes[_crime_identity(raw_crime)] = raw_crime

    if failed_point_fetches:
        if failed_point_fetches == len(sampled_points):
            warnings.append("police_api_unavailable")
        else:
            warnings.append("police_api_partial_failure")

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
    if len(sampled_points) >= max_route_points:
        warnings.append("route_sampling_capped")

    return RouteCrimeResponse(
        schema_version="1.0",
        route_id=route_id,
        crime_source="uk_police",
        crime_month=resolved_month,
        route_geometry_geojson=route_geometry_geojson,
        points=normalized_points,
        point_count=len(normalized_points),
        warnings=sorted(set(warnings)),
    )
