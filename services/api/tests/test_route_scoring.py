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
            "incident_density": incident_density,
            "lighting_score": lighting_score,
            "step_free_ratio": step_free_ratio,
            "night_transport_score": night_transport_score,
            "open_safe_places_count": open_safe_places_count,
            "report_density": report_density,
        },
    }


def make_request(
    candidates: list[dict],
    *,
    accessible_routes: bool = False,
    transport_tonight: bool = False,
    nearby_safe_places: bool = False,
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
            "preferences": {
                "accessible_routes": accessible_routes,
                "transport_tonight": transport_tonight,
                "nearby_safe_places": nearby_safe_places,
            },
            "route_candidates": candidates,
        }
    )


def test_accessibility_requirement_changes_selected_route() -> None:
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
        ]
    )
    accessible_request = make_request(
        request.model_dump()["route_candidates"],
        accessible_routes=True,
    )

    default_result = score_route_request(request)
    accessible_result = score_route_request(accessible_request)

    assert default_result.selected_route_id == "stairs-shortcut"
    assert accessible_result.selected_route_id == "step-free-main-road"
    assert "not_fully_accessible" in accessible_result.warnings


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


def test_transport_preference_can_change_ranking() -> None:
    request = make_request(
        [
            make_candidate("quick-walk", night_transport_score=0.10),
            make_candidate("night-bus-link", night_transport_score=0.95),
        ],
        transport_tonight=True,
    )

    result = score_route_request(request)

    assert result.selected_route_id == "night-bus-link"


def test_safe_place_preference_can_change_ranking() -> None:
    request = make_request(
        [
            make_candidate("quiet-street", open_safe_places_count=0),
            make_candidate("main-road", open_safe_places_count=4),
        ],
        nearby_safe_places=True,
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
