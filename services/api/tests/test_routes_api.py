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
            "preferences": {
                "accessible_routes": True,
                "transport_tonight": True,
                "nearby_safe_places": True,
            },
            "route_candidates": [
                {
                    "candidate_id": "route-a",
                    "provider": "mapbox",
                    "label": "Campus walkway",
                    "distance_metres": 900,
                    "duration_seconds": 720,
                    "features": {
                        "incident_density": 0.28,
                        "lighting_score": 0.35,
                        "step_free_ratio": 0.40,
                        "night_transport_score": 0.10,
                        "open_safe_places_count": 0,
                        "report_density": 0.24,
                    },
                },
                {
                    "candidate_id": "route-b",
                    "provider": "mapbox",
                    "label": "Main road route",
                    "distance_metres": 1150,
                    "duration_seconds": 870,
                    "features": {
                        "incident_density": 0.16,
                        "lighting_score": 0.84,
                        "step_free_ratio": 1.00,
                        "night_transport_score": 0.75,
                        "open_safe_places_count": 3,
                        "report_density": 0.12,
                    },
                },
            ],
        },
    )

    assert response.status_code == 200

    body = response.json()
    assert body["selected_route_id"] == "route-b"
    assert len(body["ranked_routes"]) == 2
    assert body["ranked_routes"][0]["rank"] == 1
    assert body["ranked_routes"][0]["candidate_id"] == "route-b"
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
