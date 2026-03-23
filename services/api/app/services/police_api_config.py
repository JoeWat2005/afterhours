from typing import Any, TypedDict


POLICE_API_BASE_URL = "https://data.police.uk/api"
DEFAULT_TIMEOUT = 20.0
DEFAULT_CATEGORY = "all-crime"

# Route crime fetch defaults
DEFAULT_ROUTE_SAMPLE_SPACING_METRES = 100.0
DEFAULT_MAX_ROUTE_FETCH_POINTS = 24

# Route crime aggregation defaults
DEFAULT_ROUTE_CORRIDOR_HALF_WIDTH_METRES = 50
DEFAULT_RUNTIME_CELL_SIZE_METRES = 75


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