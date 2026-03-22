from app.core.route_scoring_config import (
    ACCESSIBLE_ROUTE_MIN,
    BASE_COMPONENT_WEIGHTS,
    COMPONENT_GOOD_THRESHOLD,
    COMPONENT_INPUT_CAP,
    COMPONENT_PRECISION,
    DEFAULT_COMPONENT_SCORE,
    OUTPUT_PRECISION,
    OUTPUT_SCALE,
    PREFERENCE_WEIGHT_BOOSTS,
)
from app.schemas.routes import (
    RankedRouteResult,
    RouteCandidateInput,
    RouteComponentScores,
    RouteExplanation,
    RoutePreferences,
    RouteScoreRequest,
    RouteScoreResponse,
)

def score_route_request(payload: RouteScoreRequest) -> RouteScoreResponse:
    weights = _get_weights(payload.preferences)
    distance_values = [candidate.distance_metres for candidate in payload.route_candidates]
    duration_values = [candidate.duration_seconds for candidate in payload.route_candidates]
    place_values = [
        candidate.features.open_safe_places_count
        for candidate in payload.route_candidates
        if candidate.features.open_safe_places_count is not None
    ]

    ranked_routes: list[RankedRouteResult] = [
        _score_candidate(
            candidate,
            preferences=payload.preferences,
            weights=weights,
            distance_values=distance_values,
            duration_values=duration_values,
            place_values=place_values,
        )
        for candidate in payload.route_candidates
    ]

    # If scores match, prefer the option with fewer gaps, then the quicker one.
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


def _score_candidate(
    candidate: RouteCandidateInput,
    *,
    preferences: RoutePreferences,
    weights: dict[str, float],
    distance_values: list[int],
    duration_values: list[int],
    place_values: list[int],
) -> RankedRouteResult:
    features = candidate.features
    warnings: list[str] = []

    safety_inputs: list[float] = []
    if features.incident_density is not None:
        safety_inputs.append(min(features.incident_density, COMPONENT_INPUT_CAP))
    if features.report_density is not None:
        safety_inputs.append(min(features.report_density, COMPONENT_INPUT_CAP))
    if safety_inputs:
        safety = round(
            1 - (sum(safety_inputs) / len(safety_inputs)),
            COMPONENT_PRECISION,
        )
    else:
        safety = DEFAULT_COMPONENT_SCORE
        warnings.append("missing_safety_data")

    lighting = _read_score(
        features.lighting_score,
        missing_warning="missing_lighting_data",
        warnings=warnings,
    )
    transport = _read_score(
        features.night_transport_score,
        missing_warning="missing_transport_data",
        warnings=warnings,
    )

    if features.step_free_ratio is None:
        accessibility = DEFAULT_COMPONENT_SCORE
        warnings.append("missing_accessibility_data")
    else:
        accessibility = round(
            features.step_free_ratio,
            COMPONENT_PRECISION,
        )
        if preferences.accessible_routes and accessibility < ACCESSIBLE_ROUTE_MIN:
            warnings.append("not_fully_accessible")

    if features.open_safe_places_count is None:
        places = DEFAULT_COMPONENT_SCORE
        warnings.append("missing_safe_place_data")
    else:
        places = _relative_score(
            features.open_safe_places_count,
            place_values,
        )

    distance_score = _relative_inverse_score(
        candidate.distance_metres,
        distance_values,
    )
    duration_score = _relative_inverse_score(
        candidate.duration_seconds,
        duration_values,
    )
    efficiency = round(
        (distance_score + duration_score) / 2,
        COMPONENT_PRECISION,
    )

    total_score = (
        safety * weights["safety"]
        + lighting * weights["lighting"]
        + accessibility * weights["accessibility"]
        + transport * weights["transport"]
        + efficiency * weights["efficiency"]
        + places * weights["places"]
    )

    component_scores = RouteComponentScores(
        safety=safety,
        lighting=lighting,
        accessibility=accessibility,
        transport=transport,
        efficiency=efficiency,
        places=places,
    )
    clean_warnings = sorted(set(warnings))

    return RankedRouteResult(
        candidate_id=candidate.candidate_id,
        label=candidate.label,
        provider=candidate.provider,
        rank=1,
        score=round(
            total_score * OUTPUT_SCALE,
            OUTPUT_PRECISION,
        ),
        distance_metres=candidate.distance_metres,
        duration_seconds=candidate.duration_seconds,
        geometry_geojson=candidate.geometry_geojson,
        component_scores=component_scores,
        explanation=RouteExplanation(
            summary=_build_summary(candidate.label or candidate.candidate_id, clean_warnings),
            reasons=_build_reasons(component_scores),
            warnings=clean_warnings,
        ),
    )


def _get_weights(preferences: RoutePreferences) -> dict[str, float]:
    weights = dict(BASE_COMPONENT_WEIGHTS)

    # These are small nudges rather than massive overrides.
    if preferences.accessible_routes:
        weights["accessibility"] += PREFERENCE_WEIGHT_BOOSTS["accessibility"]
    if preferences.nearby_safe_places:
        weights["places"] += PREFERENCE_WEIGHT_BOOSTS["places"]

    total = sum(weights.values())
    for key in weights:
        weights[key] = weights[key] / total

    return weights


def _read_score(
    value: float | None,
    *,
    missing_warning: str,
    warnings: list[str],
) -> float:
    if value is None:
        warnings.append(missing_warning)
        return DEFAULT_COMPONENT_SCORE
    return round(value, COMPONENT_PRECISION)


def _build_reasons(component_scores: RouteComponentScores) -> list[str]:
    reasons: list[str] = []

    if component_scores.safety >= COMPONENT_GOOD_THRESHOLD:
        reasons.append("lower safety risk")
    if component_scores.lighting >= COMPONENT_GOOD_THRESHOLD:
        reasons.append("better lighting")
    if component_scores.accessibility >= COMPONENT_GOOD_THRESHOLD:
        reasons.append("better step-free access")
    if component_scores.transport >= COMPONENT_GOOD_THRESHOLD:
        reasons.append("better late transport support")
    if component_scores.places >= COMPONENT_GOOD_THRESHOLD:
        reasons.append("more nearby safe places")
    if component_scores.efficiency >= COMPONENT_GOOD_THRESHOLD:
        reasons.append("shorter trip")

    if not reasons:
        reasons.append("fairly balanced overall")

    return reasons


def _build_summary(route_name: str, warnings: list[str]) -> str:
    if warnings:
        return f"{route_name} looks reasonable, but some of the route data is missing."
    return f"{route_name} looks strong from the data provided."


def _relative_score(value: int, values: list[int]) -> float:
    if not values:
        return DEFAULT_COMPONENT_SCORE

    minimum = min(values)
    maximum = max(values)
    if minimum == maximum:
        return DEFAULT_COMPONENT_SCORE

    return round(
        (value - minimum) / (maximum - minimum),
        COMPONENT_PRECISION,
    )


def _relative_inverse_score(value: int, values: list[int]) -> float:
    if not values:
        return DEFAULT_COMPONENT_SCORE

    minimum = min(values)
    maximum = max(values)
    if minimum == maximum:
        return DEFAULT_COMPONENT_SCORE

    return round(
        1 - ((value - minimum) / (maximum - minimum)),
        COMPONENT_PRECISION,
    )
