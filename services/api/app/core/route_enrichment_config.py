from typing import Final


POLICE_API_BASE_URL: Final[str] = "https://data.police.uk/api"
OVERPASS_API_URL: Final[str] = "https://overpass-api.de/api/interpreter"

DEFAULT_TIMEOUT: Final[float] = 20.0
OVERPASS_TIMEOUT: Final[float] = 30.0

DEFAULT_CATEGORY: Final[str] = "all-crime"

# Route sampling defaults
DEFAULT_ROUTE_SAMPLE_SPACING_METRES: Final[float] = 250.0
DEFAULT_MAX_ROUTE_FETCH_POINTS: Final[int] = 24

# Safety/report corridor defaults
DEFAULT_ROUTE_CORRIDOR_HALF_WIDTH_METRES: Final[float] = 100.0
DEFAULT_RUNTIME_CELL_SIZE_METRES: Final[float] = 75.0

# OSM / context enrichment defaults
DEFAULT_CONTEXT_NEAR_ROUTE_RADIUS_METRES: Final[float] = 150.0
DEFAULT_BBOX_PAD_DEGREES: Final[float] = 0.0015

# Report query defaults
DEFAULT_REPORT_MAX_AGE_DAYS: Final[int] = 90
DEFAULT_PER_POINT_REPORT_LIMIT: Final[int] = 100