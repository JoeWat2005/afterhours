from app.core.config import get_settings
from app.schemas.routes import (
    RankedRouteResult,
    RouteCandidateInput,
    RouteComponentScores,
    RouteExplanation,
    RoutePreferences,
    RouteScoreRequest,
    RouteScoreResponse,
)


DEFAULT_SCORE = 0.5


def score_route_request(payload: RouteScoreRequest) -> RouteScoreResponse:
    weights = _get_weights(payload.preferences)
    distance_values = [candidate.distance_metres for candidate in payload.route_candidates]
    duration_values = [candidate.duration_seconds for candidate in payload.route_candidates]
    place_values = [
        candidate.features.open_safe_places_count
        for candidate in payload.route_candidates
        if candidate.features.open_safe_places_count is not None
    ]

    ranked_routes: list[RankedRouteResult] = []

    for candidate in payload.route_candidates:
        features = candidate.features
        warnings: list[str] = []

        safety_inputs: list[float] = []
        if features.incident_density is not None:
            safety_inputs.append(min(features.incident_density, 1.0))
        if features.report_density is not None:
            safety_inputs.append(min(features.report_density, 1.0))
        if safety_inputs:
            safety = round(1 - (sum(safety_inputs) / len(safety_inputs)), 4)
        else:
            safety = DEFAULT_SCORE
            warnings.append("missing_safety_data")

        if features.lighting_score is None:
            lighting = DEFAULT_SCORE
            warnings.append("missing_lighting_data")
        else:
            lighting = round(features.lighting_score, 4)

        if features.step_free_ratio is None:
            accessibility = DEFAULT_SCORE
            warnings.append("missing_accessibility_data")
        else:
            accessibility = round(features.step_free_ratio, 4)
            if payload.preferences.accessible_routes and accessibility < 0.7:
                warnings.append("not_fully_accessible")

        if features.night_transport_score is None:
            transport = DEFAULT_SCORE
            warnings.append("missing_transport_data")
        else:
            transport = round(features.night_transport_score, 4)

        if features.open_safe_places_count is None:
            places = DEFAULT_SCORE
            warnings.append("missing_safe_place_data")
        else:
            places = _relative_score(features.open_safe_places_count, place_values)

        distance_score = _relative_inverse_score(candidate.distance_metres, distance_values)
        duration_score = _relative_inverse_score(candidate.duration_seconds, duration_values)
        efficiency = round((distance_score + duration_score) / 2, 4)

        total_score = (
            safety * weights["safety"]
            + lighting * weights["lighting"]
            + accessibility * weights["accessibility"]
            + transport * weights["transport"]
            + efficiency * weights["efficiency"]
            + places * weights["places"]
        )

        reasons: list[str] = []
        if safety >= 0.7:
            reasons.append("lower safety risk")
        if lighting >= 0.7:
            reasons.append("better lighting")
        if accessibility >= 0.7:
            reasons.append("better step-free access")
        if transport >= 0.7:
            reasons.append("better late transport support")
        if places >= 0.7:
            reasons.append("more nearby safe places")
        if efficiency >= 0.7:
            reasons.append("shorter trip")
        if not reasons:
            reasons.append("fairly balanced overall")

        route_name = candidate.label or candidate.candidate_id
        summary = f"{route_name} scored best overall from the data provided."
        if warnings:
            summary = f"{route_name} scored best overall, but some data was missing."

        ranked_routes.append(
            RankedRouteResult(
                candidate_id=candidate.candidate_id,
                label=candidate.label,
                provider=candidate.provider,
                rank=1,
                score=round(total_score * 100, 2),
                distance_metres=candidate.distance_metres,
                duration_seconds=candidate.duration_seconds,
                geometry_geojson=candidate.geometry_geojson,
                component_scores=RouteComponentScores(
                    safety=safety,
                    lighting=lighting,
                    accessibility=accessibility,
                    transport=transport,
                    efficiency=efficiency,
                    places=places,
                ),
                explanation=RouteExplanation(
                    summary=summary,
                    reasons=reasons,
                    warnings=sorted(set(warnings)),
                ),
            )
        )

    ranked_routes.sort(
        key=lambda route: (
            -route.score,
            len(route.explanation.warnings),
            route.duration_seconds,
            route.distance_metres,
            route.candidate_id,
        )
    )

    for index, route in enumerate(ranked_routes, start=1):
        route.rank = index

    response_warnings = sorted(
        {
            warning
            for route in ranked_routes
            for warning in route.explanation.warnings
        }
    )

    return RouteScoreResponse(
        selected_route_id=ranked_routes[0].candidate_id,
        ranked_routes=ranked_routes,
        warnings=response_warnings,
    )


def _get_weights(preferences: RoutePreferences) -> dict[str, float]:
    settings = get_settings()
    weights = {
        "safety": settings.route_score_weight_safety,
        "lighting": settings.route_score_weight_lighting,
        "accessibility": settings.route_score_weight_accessibility,
        "transport": settings.route_score_weight_transport,
        "efficiency": settings.route_score_weight_efficiency,
        "places": settings.route_score_weight_amenity,
    }

    if preferences.accessible_routes:
        weights["accessibility"] += 0.15
    if preferences.transport_tonight:
        weights["transport"] += 0.10
    if preferences.nearby_safe_places:
        weights["places"] += 0.10

    total = sum(weights.values())
    for key in weights:
        weights[key] = weights[key] / total

    return weights


def _relative_score(value: int, values: list[int]) -> float:
    if not values:
        return DEFAULT_SCORE

    minimum = min(values)
    maximum = max(values)
    if minimum == maximum:
        return DEFAULT_SCORE

    return round((value - minimum) / (maximum - minimum), 4)


def _relative_inverse_score(value: int, values: list[int]) -> float:
    if not values:
        return DEFAULT_SCORE

    minimum = min(values)
    maximum = max(values)
    if minimum == maximum:
        return DEFAULT_SCORE

    return round(1 - ((value - minimum) / (maximum - minimum)), 4)
