from typing import TypedDict, Any

POLICE_API_BASE_URL = "https://data.police.uk/api"
DEFAULT_TIMEOUT = 20.0
DEFAULT_CATEGORY = "all-crime"


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