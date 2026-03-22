from app.schemas.routes import RouteScoreRequest
from app.services.route_scoring import score_route_request


def make_candidate(
    candidate_id: str,
    *,
    distance_metres: int = 1000,
    duration_seconds: int = 800,
    incident_density: float | None = 0.2,
    lighting_score: float | None = 0.5,
    step_free_ratio: float | None = 0.5,
    night_transport_score: float | None = 0.5,
    open_safe_places_count: int | None = 1,
    report_density: float | None = 0.2,
) -> dict:
    return {
        "candidate_id": candidate_id,
        "label": candidate_id.replace("-", " ").title(),
        "provider": "mapbox",
        "distance_metres": distance_metres,
        "duration_seconds": duration_seconds,
        "features": {
            "safety": {
                "incident_density": incident_density,
                "lighting_score": lighting_score,
                "report_density": report_density,
            },
            "accessibility": {
                "step_free_ratio": step_free_ratio,
            },
            "transport": {
                "night_transport_score": night_transport_score,
            },
            "waiting_areas": {
                "safe_waiting_area_count": open_safe_places_count,
            },
        },
    }


def make_request(
    candidates: list[dict],
    *,
    bias_mode: str = "balanced",
    accessibility_preference: bool = False,
    nearby_safe_places_preference: bool = False,
    accessibility_requirement: bool = False,
) -> RouteScoreRequest:
    return RouteScoreRequest.model_validate(
        {
            "origin": {
                "latitude": 51.5072,
                "longitude": -0.1276,
                "label": "Campus Library",
            },
            "destination": {
                "latitude": 51.5094,
                "longitude": -0.1183,
                "label": "Night Bus Stop",
            },
            "depart_at": "2026-03-22T22:30:00+00:00",
            "bias_mode": bias_mode,
            "requirements": {
                "accessibility": {
                    "step_free_access": accessibility_requirement,
                }
            },
            "preferences": {
                "accessibility": {
                    "step_free_access": accessibility_preference,
                },
                "waiting_areas": {
                    "safe_waiting_areas": nearby_safe_places_preference,
                },
            },
            "route_candidates": candidates,
        }
    )


def test_route_request_accepts_new_requirement_and_preference_shapes() -> None:
    request = make_request(
        [
            make_candidate(
                "stairs-shortcut",
                distance_metres=900,
                duration_seconds=720,
                incident_density=0.10,
                lighting_score=0.90,
                step_free_ratio=0.20,
                night_transport_score=0.20,
                open_safe_places_count=1,
                report_density=0.08,
            ),
            make_candidate(
                "step-free-main-road",
                distance_metres=1100,
                duration_seconds=860,
                incident_density=0.45,
                lighting_score=0.62,
                step_free_ratio=1.00,
                night_transport_score=0.30,
                open_safe_places_count=1,
                report_density=0.42,
            ),
        ],
        bias_mode="maximum_safety",
        accessibility_requirement=True,
        accessibility_preference=True,
        nearby_safe_places_preference=True,
    )

    assert request.bias_mode.value == "maximum_safety"
    assert request.requirements.accessibility.step_free_access is True
    assert request.preferences.accessibility.step_free_access is True
    assert request.preferences.waiting_areas.safe_waiting_areas is True


def test_route_request_accepts_richer_waiting_area_details() -> None:
    request = RouteScoreRequest.model_validate(
        {
            "origin": {"latitude": 51.5, "longitude": -0.12},
            "destination": {"latitude": 51.51, "longitude": -0.11},
            "depart_at": "2026-03-22T23:00:00+00:00",
            "requirements": {
                "waiting_areas": {
                    "well_lit_waiting_areas": True,
                    "wifi_nearby": True,
                    "open_venues_nearby": True,
                    "safe_areas_nearby": True,
                }
            },
            "preferences": {
                "waiting_areas": {
                    "staffed_venues_nearby": True,
                }
            },
            "route_candidates": [
                {
                    "candidate_id": "route-a",
                    "distance_metres": 1000,
                    "duration_seconds": 800,
                    "features": {
                        "waiting_areas": {
                            "safe_waiting_area_count": 2,
                            "well_lit_waiting_area_count": 2,
                            "wifi_access_point_count": 1,
                            "staffed_venue_count": 1,
                            "open_venue_count": 2,
                            "waiting_areas_in_safe_areas_ratio": 0.75,
                        }
                    },
                }
            ],
        }
    )

    waiting_areas = request.route_candidates[0].features.waiting_areas

    assert request.requirements.waiting_areas.wifi_nearby is True
    assert request.requirements.waiting_areas.open_venues_nearby is True
    assert request.requirements.waiting_areas.safe_areas_nearby is True
    assert request.preferences.waiting_areas.staffed_venues_nearby is True
    assert waiting_areas.wifi_access_point_count == 1
    assert waiting_areas.open_venue_count == 2
    assert waiting_areas.waiting_areas_in_safe_areas_ratio == 0.75


def test_missing_route_data_creates_route_warnings() -> None:
    request = RouteScoreRequest.model_validate(
        {
            "origin": {"latitude": 51.5, "longitude": -0.12},
            "destination": {"latitude": 51.51, "longitude": -0.11},
            "depart_at": "2026-03-22T23:00:00+00:00",
            "route_candidates": [
                {
                    "candidate_id": "route-a",
                    "distance_metres": 1000,
                    "duration_seconds": 800,
                    "features": {},
                }
            ],
        }
    )

    result = score_route_request(request)

    assert result.selected_route_id == "route-a"
    assert result.warnings == [
        "missing_accessibility_data",
        "missing_lighting_data",
        "missing_safe_place_data",
        "missing_safety_data",
        "missing_transport_data",
    ]
    assert result.requirements_applied is False
    assert result.requirement_matches_found is True
    assert result.selected_route_is_fallback is False
    assert result.ranked_routes[0].explanation.warnings == result.warnings


def test_better_lighting_can_change_ranking() -> None:
    request = make_request(
        [
            make_candidate("darker-route", lighting_score=0.25),
            make_candidate("brighter-route", lighting_score=0.90),
        ]
    )

    result = score_route_request(request)

    assert result.selected_route_id == "brighter-route"


def test_bias_mode_can_change_selected_route() -> None:
    maximum_safety_request = make_request(
        [
            make_candidate(
                "safe-main-road",
                distance_metres=1400,
                duration_seconds=1100,
                incident_density=0.05,
                lighting_score=0.90,
                report_density=0.05,
            ),
            make_candidate(
                "fast-cut-through",
                distance_metres=700,
                duration_seconds=520,
                incident_density=0.45,
                lighting_score=0.30,
                report_density=0.40,
            ),
        ],
        bias_mode="maximum_safety",
    )
    most_efficiency_request = make_request(
        maximum_safety_request.model_dump()["route_candidates"],
        bias_mode="most_efficiency",
    )

    maximum_safety_result = score_route_request(maximum_safety_request)
    most_efficiency_result = score_route_request(most_efficiency_request)

    assert maximum_safety_result.selected_route_id == "safe-main-road"
    assert most_efficiency_result.selected_route_id == "fast-cut-through"


def test_requirement_matching_routes_rank_ahead_of_fallback_routes() -> None:
    request = make_request(
        [
            make_candidate(
                "stairs-shortcut",
                distance_metres=800,
                duration_seconds=650,
                step_free_ratio=0.20,
            ),
            make_candidate(
                "step-free-route",
                distance_metres=1100,
                duration_seconds=900,
                step_free_ratio=1.00,
            ),
        ],
        accessibility_requirement=True,
    )

    result = score_route_request(request)

    assert result.requirements_applied is True
    assert result.requirement_matches_found is True
    assert result.selected_route_id == "step-free-route"
    assert result.selected_route_is_fallback is False
    assert result.ranked_routes[0].meets_requirements is True
    assert result.ranked_routes[0].is_fallback is False
    assert result.ranked_routes[1].meets_requirements is False
    assert result.ranked_routes[1].is_fallback is True
    assert result.ranked_routes[1].unmet_requirements == ["step_free_access"]


def test_fallback_routes_are_returned_when_no_route_meets_requirements() -> None:
    request = make_request(
        [
            make_candidate("route-a", step_free_ratio=0.20),
            make_candidate("route-b", step_free_ratio=0.40),
        ],
        accessibility_requirement=True,
    )

    result = score_route_request(request)

    assert result.requirements_applied is True
    assert result.requirement_matches_found is False
    assert result.selected_route_is_fallback is True
    assert "no_routes_met_requirements" in result.warnings
    assert result.ranked_routes[0].is_fallback is True
    assert result.ranked_routes[0].meets_requirements is False
    assert "step_free_access" in result.ranked_routes[0].unmet_requirements


def test_safe_place_preference_can_change_ranking() -> None:
    request = make_request(
        [
            make_candidate("quiet-street", open_safe_places_count=0),
            make_candidate("main-road", open_safe_places_count=4),
        ],
        nearby_safe_places_preference=True,
    )

    result = score_route_request(request)

    assert result.selected_route_id == "main-road"


def test_equal_routes_use_a_stable_tie_break() -> None:
    request = make_request(
        [
            make_candidate("route-b"),
            make_candidate("route-a"),
        ]
    )

    result = score_route_request(request)

    assert result.selected_route_id == "route-a"
