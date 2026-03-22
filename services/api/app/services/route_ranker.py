from app.core import route_scoring_config as scoring_config
from app.schemas.routes import RankedRouteResult


def rank_routes(
    routes: list[RankedRouteResult],
    *,
    requirements_applied: bool,
) -> tuple[list[RankedRouteResult], bool]:
    if not requirements_applied:
        ranked_routes = sorted(routes, key=_route_sort_key)
        return ranked_routes, True

    matching_routes = [route for route in routes if route.meets_requirements]
    fallback_routes = [route for route in routes if not route.meets_requirements]

    if matching_routes:
        ranked_routes = sorted(matching_routes, key=_route_sort_key) + sorted(
            fallback_routes,
            key=_route_sort_key,
        )
        for route in ranked_routes:
            route.is_fallback = not route.meets_requirements
        return ranked_routes, True

    ranked_routes = sorted(routes, key=_route_sort_key)
    for route in ranked_routes:
        route.is_fallback = True

    return ranked_routes, False


def _route_sort_key(route: RankedRouteResult) -> tuple:
    values = {
        "warning_count": len(route.explanation.warnings),
        "duration_seconds": route.duration_seconds,
        "distance_metres": route.distance_metres,
        "candidate_id": route.candidate_id,
    }

    return (-route.score, *(values[key] for key in scoring_config.ROUTE_TIE_BREAK_ORDER))
