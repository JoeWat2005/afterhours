from typing import Any

from app.services.police_api import (
    fetch_route_crime_points,
    iter_route_points,
    route_length_metres,
)
from app.services.police_api_config import (
    DEFAULT_ROUTE_CORRIDOR_HALF_WIDTH_METRES,
    DEFAULT_RUNTIME_CELL_SIZE_METRES,
    RouteCrimeAggregationInput,
    RouteSafetyMetrics,
)


def compute_route_safety_metrics(
    payload: RouteCrimeAggregationInput,
) -> RouteSafetyMetrics:
    """
    Stable middle layer between police_api.py and route_scoring.py.

    This file is intentionally the extension point for future heatmap work.

    Current responsibility:
    - accept normalized police crime points for a route
    - return route-level safety metrics in a stable shape

    Future responsibility for heatmap implementation:
    - filter crime points to a route corridor
    - snap crimes into runtime grid cells
    - compute incident_density
    - compute report_density
    - populate heatmap_cells
    """

    geometry = payload["route_geometry_geojson"]
    points = iter_route_points(geometry)
    length_metres = route_length_metres(points)
    length_km = max(length_metres / 1000.0, 0.001)

    warnings = list(payload["route_crime_response"]["warnings"])

    if length_metres <= 0:
        warnings.append("invalid_route_geometry")

    # Placeholder values until heatmap/corridor logic is implemented.
    # This keeps the contract stable for callers and future development.
    # SAYED THIS IS FOR YOU!!!
    return RouteSafetyMetrics(
        incident_density=None,
        report_density=None,
        warnings=sorted(set(warnings)),
        route_length_metres=length_metres,
        route_length_km=length_km,
        corridor_half_width_metres=payload["corridor_half_width_metres"],
        cell_size_metres=payload["cell_size_metres"],
        heatmap_cells=[],
    )


async def enrich_route_candidate_safety(
    *,
    route_geometry_geojson: dict[str, Any],
    route_id: str | None = None,
    date: str | None = None,
    corridor_half_width_metres: float = DEFAULT_ROUTE_CORRIDOR_HALF_WIDTH_METRES,
    cell_size_metres: float = DEFAULT_RUNTIME_CELL_SIZE_METRES,
) -> RouteSafetyMetrics:
    """
    Single entry point that callers should use.

    The rest of the app should call this function, not the future heatmap code directly.
    That way the internal implementation can evolve later without changing call sites.
    """
    route_crime_response = await fetch_route_crime_points(
        route_geometry_geojson=route_geometry_geojson,
        route_id=route_id,
        date=date,
    )

    return compute_route_safety_metrics(
        RouteCrimeAggregationInput(
            route_id=route_id,
            route_geometry_geojson=route_geometry_geojson,
            route_crime_response=route_crime_response,
            corridor_half_width_metres=corridor_half_width_metres,
            cell_size_metres=cell_size_metres,
        )
    )