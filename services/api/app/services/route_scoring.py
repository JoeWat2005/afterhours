from app.core import route_scoring_config as scoring_config
from app.schemas.routes import (
    RankedRouteResult,
    RouteCandidateInput,
    RouteBiasMode,
    RouteComponentScores,
    RouteExplanation,
    RoutePreferences,
    RouteScoreRequest,
    RouteScoreResponse,
)
from app.services.route_ranker import rank_routes
from app.services.route_requirements import get_unmet_requirements


def score_route_request(payload: RouteScoreRequest) -> RouteScoreResponse:
    weights = _get_weights(payload.bias_mode, payload.preferences)
    requirements_applied = payload.requirements.enabled
    distance_values = [candidate.distance_metres for candidate in payload.route_candidates]
    duration_values = [candidate.duration_seconds for candidate in payload.route_candidates]
    place_values = [
        candidate.features.waiting_areas.safe_waiting_area_count
        for candidate in payload.route_candidates
        if candidate.features.waiting_areas.safe_waiting_area_count is not None
    ]

    scored_routes: list[RankedRouteResult] = []
    for candidate in payload.route_candidates:
        route = _score_candidate(
            candidate,
            weights=weights,
            distance_values=distance_values,
            duration_values=duration_values,
            place_values=place_values,
        )
        unmet_requirements = (
            get_unmet_requirements(candidate, payload.requirements)
            if requirements_applied
            else []
        )
        route.meets_requirements = not unmet_requirements
        route.unmet_requirements = unmet_requirements
        scored_routes.append(route)

    ranked_routes, requirement_matches_found = rank_routes(
        scored_routes,
        requirements_applied=requirements_applied,
    )

    for index, route in enumerate(ranked_routes, start=1):
        route.rank = index

    response_warnings = {
        warning
        for route in ranked_routes
        for warning in route.explanation.warnings
    }
    if requirements_applied and not requirement_matches_found:
        response_warnings.add("no_routes_met_requirements")

    return RouteScoreResponse(
        selected_route_id=ranked_routes[0].candidate_id,
        requirements_applied=requirements_applied,
        requirement_matches_found=requirement_matches_found,
        selected_route_is_fallback=ranked_routes[0].is_fallback,
        ranked_routes=ranked_routes,
        warnings=sorted(response_warnings),
    )


def _score_candidate(
    candidate: RouteCandidateInput,
    *,
    weights: dict[str, float],
    distance_values: list[int],
    duration_values: list[int],
    place_values: list[int],
) -> RankedRouteResult:
    features = candidate.features
    warnings: list[str] = []

    safety_inputs: list[float] = []
    if features.safety.incident_density is not None:
        safety_inputs.append(
            min(
                features.safety.incident_density,
                _scoring_number("component_input_cap"),
            )
        )
    if features.safety.report_density is not None:
        safety_inputs.append(
            min(
                features.safety.report_density,
                _scoring_number("component_input_cap"),
            )
        )
    if safety_inputs:
        safety = round(
            1 - (sum(safety_inputs) / len(safety_inputs)),
            _scoring_precision("component_precision"),
        )
    else:
        safety = _scoring_number("default_component_score")
        warnings.append("missing_safety_data")

    lighting = _read_score(
        features.safety.lighting_score,
        missing_warning="missing_lighting_data",
        warnings=warnings,
    )
    transport = _read_score(
        features.transport.night_transport_score,
        missing_warning="missing_transport_data",
        warnings=warnings,
    )

    if features.accessibility.step_free_ratio is None:
        accessibility = _scoring_number("default_component_score")
        warnings.append("missing_accessibility_data")
    else:
        accessibility = round(
            features.accessibility.step_free_ratio,
            _scoring_precision("component_precision"),
        )

    if features.waiting_areas.safe_waiting_area_count is None:
        places = _scoring_number("default_component_score")
        warnings.append("missing_safe_place_data")
    else:
        places = _relative_score(
            features.waiting_areas.safe_waiting_area_count,
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
        _scoring_precision("component_precision"),
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
        meets_requirements=True,
        unmet_requirements=[],
        is_fallback=False,
        score=round(
            total_score * _scoring_number("output_scale"),
            _scoring_precision("output_precision"),
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


def _read_score(
    value: float | None,
    *,
    missing_warning: str,
    warnings: list[str],
) -> float:
    if value is None:
        warnings.append(missing_warning)
        return _scoring_number("default_component_score")
    return round(value, _scoring_precision("component_precision"))


def _build_reasons(component_scores: RouteComponentScores) -> list[str]:
    reasons: list[str] = []

    if component_scores.safety >= _scoring_number("component_good_threshold"):
        reasons.append("lower safety risk")
    if component_scores.lighting >= _scoring_number("component_good_threshold"):
        reasons.append("better lighting")
    if component_scores.accessibility >= _scoring_number("component_good_threshold"):
        reasons.append("better step-free access")
    if component_scores.transport >= _scoring_number("component_good_threshold"):
        reasons.append("better late transport support")
    if component_scores.places >= _scoring_number("component_good_threshold"):
        reasons.append("more nearby safe places")
    if component_scores.efficiency >= _scoring_number("component_good_threshold"):
        reasons.append("shorter trip")

    if not reasons:
        reasons.append("fairly balanced overall")

    return reasons


def _build_summary(route_name: str, warnings: list[str]) -> str:
    if warnings:
        return f"{route_name} looks reasonable, but some of the route data is missing."
    return f"{route_name} looks strong from the data provided."


def _get_weights(
    bias_mode: RouteBiasMode,
    preferences: RoutePreferences,
) -> dict[str, float]:
    weights = dict(scoring_config.BIAS_MODE_WEIGHT_PROFILES[bias_mode])

    if preferences.accessibility.enabled:
        _apply_weight_boosts(
            weights,
            scoring_config.SOFT_PREFERENCE_BOOSTS["accessibility"],
        )
    if preferences.waiting_areas.enabled:
        _apply_weight_boosts(
            weights,
            scoring_config.SOFT_PREFERENCE_BOOSTS["waiting_areas"],
        )

    total = sum(weights.values())
    for key in weights:
        weights[key] = weights[key] / total

    return weights


def _apply_weight_boosts(
    weights: dict[str, float],
    boosts: dict[str, float],
) -> None:
    for component, boost in boosts.items():
        weights[component] += boost


def _scoring_number(key: str) -> float:
    return float(scoring_config.ROUTE_SCORING_DEFAULTS[key])


def _scoring_precision(key: str) -> int:
    return int(scoring_config.ROUTE_SCORING_DEFAULTS[key])


def _relative_score(value: int, values: list[int]) -> float:
    if not values:
        return _scoring_number("default_component_score")

    minimum = min(values)
    maximum = max(values)
    if minimum == maximum:
        return _scoring_number("default_component_score")

    return round(
        (value - minimum) / (maximum - minimum),
        _scoring_precision("component_precision"),
    )


def _relative_inverse_score(value: int, values: list[int]) -> float:
    if not values:
        return _scoring_number("default_component_score")

    minimum = min(values)
    maximum = max(values)
    if minimum == maximum:
        return _scoring_number("default_component_score")

    return round(
        1 - ((value - minimum) / (maximum - minimum)),
        _scoring_precision("component_precision"),
    )