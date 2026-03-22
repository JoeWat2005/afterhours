from app.schemas.routes import RouteScoreRequest
from app.services.route_scoring import score_route_request


def build_request(*, accessibility_required: bool = False) -> RouteScoreRequest:
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
                "accessible_routes": accessibility_required,
                "transport_tonight": False,
                "nearby_safe_places": False,
            },
            "route_candidates": [
                {
                    "candidate_id": "stairs-shortcut",
                    "label": "Stairs shortcut",
                    "provider": "mapbox",
                    "distance_metres": 900,
                    "duration_seconds": 720,
                    "features": {
                        "incident_density": 0.10,
                        "lighting_score": 0.90,
                        "step_free_ratio": 0.20,
                        "night_transport_score": 0.20,
                        "open_safe_places_count": 1,
                        "report_density": 0.08,
                    },
                },
                {
                    "candidate_id": "step-free-main-road",
                    "label": "Step-free main road",
                    "provider": "mapbox",
                    "distance_metres": 1100,
                    "duration_seconds": 860,
                    "features": {
                        "incident_density": 0.45,
                        "lighting_score": 0.62,
                        "step_free_ratio": 1.00,
                        "night_transport_score": 0.30,
                        "open_safe_places_count": 1,
                        "report_density": 0.42,
                    },
                },
            ],
        }
    )


def test_accessibility_requirement_changes_selected_route() -> None:
    default_result = score_route_request(build_request(accessibility_required=False))
    accessible_result = score_route_request(build_request(accessibility_required=True))

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
