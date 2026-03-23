from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_route_score_endpoint_returns_ranked_route_response() -> None:
    response = client.post(
        "/v1/routes/score",
        json={
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
            "bias_mode": "maximum_safety",
            "requirements": {
                "accessibility": {
                    "avoid_stairs": True,
                    "step_free_access": True,
                    "lifts_available": True,
                }
            },
            "preferences": {
                "accessibility": {
                    "step_free_access": True,
                    "ramps_available": True,
                },
                "waiting_areas": {
                    "safe_waiting_areas": True,
                    "well_lit_waiting_areas": True,
                },
            },
            "route_candidates": [
                {
                    "candidate_id": "route-a",
                    "provider": "mapbox",
                    "label": "Campus walkway",
                    "distance_metres": 900,
                    "duration_seconds": 720,
                    "features": {
                        "safety": {
                            "incident_density": 0.28,
                            "lighting_score": 0.35,
                            "report_density": 0.24,
                        },
                        "accessibility": {
                            "step_free_ratio": 0.40,
                            "stairs_present": True,
                            "lift_coverage_ratio": 0.10,
                        },
                        "transport": {
                            "night_transport_score": 0.10,
                            "transfer_count": 1,
                        },
                        "waiting_areas": {
                            "safe_waiting_area_count": 0,
                            "well_lit_waiting_area_count": 0,
                        },
                    },
                },
                {
                    "candidate_id": "route-b",
                    "provider": "mapbox",
                    "label": "Main road route",
                    "distance_metres": 1150,
                    "duration_seconds": 870,
                    "features": {
                        "safety": {
                            "incident_density": 0.16,
                            "lighting_score": 0.84,
                            "report_density": 0.12,
                        },
                        "accessibility": {
                            "step_free_ratio": 1.00,
                            "stairs_present": False,
                            "lift_coverage_ratio": 1.00,
                            "ramp_coverage_ratio": 0.90,
                        },
                        "transport": {
                            "night_transport_score": 0.75,
                            "transfer_count": 1,
                            "late_service_available": True,
                        },
                        "waiting_areas": {
                            "safe_waiting_area_count": 3,
                            "well_lit_waiting_area_count": 2,
                            "open_venue_count": 2,
                            "waiting_areas_in_safe_areas_ratio": 0.9,
                        },
                    },
                },
            ],
        },
    )

    assert response.status_code == 200

    body = response.json()
    assert body["selected_route_id"] == "route-b"
    assert body["requirements_applied"] is True
    assert body["requirement_matches_found"] is True
    assert body["selected_route_is_fallback"] is False
    assert len(body["ranked_routes"]) == 2
    assert body["ranked_routes"][0]["rank"] == 1
    assert body["ranked_routes"][0]["candidate_id"] == "route-b"
    assert body["ranked_routes"][0]["meets_requirements"] is True
    assert body["ranked_routes"][0]["is_fallback"] is False
    assert body["ranked_routes"][0]["component_scores"]["lighting"] == 0.84
    assert "better lighting" in body["ranked_routes"][0]["explanation"]["reasons"]


def test_route_score_endpoint_rejects_duplicate_candidate_ids() -> None:
    response = client.post(
        "/v1/routes/score",
        json={
            "origin": {"latitude": 51.5, "longitude": -0.12},
            "destination": {"latitude": 51.51, "longitude": -0.11},
            "depart_at": "2026-03-22T22:30:00+00:00",
            "route_candidates": [
                {
                    "candidate_id": "duplicate-id",
                    "distance_metres": 900,
                    "duration_seconds": 700,
                    "features": {},
                },
                {
                    "candidate_id": "duplicate-id",
                    "distance_metres": 1000,
                    "duration_seconds": 900,
                    "features": {},
                },
            ],
        },
    )

    assert response.status_code == 422
    assert "route candidate ids must be unique" in response.text
