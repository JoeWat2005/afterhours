import pytest
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


def test_route_plan_endpoint_fetches_enriches_and_ranks_multiple_candidates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.schemas.routes import RouteCandidateInput, RouteNavigationMetadata

    # 1. Mock Mapbox returning 3 raw mock routes
    async def mock_fetch_mapbox(*args, **kwargs):
        return [
            RouteCandidateInput(
                candidate_id="route-1-dangerous",
                label="Route 1",
                provider="mapbox",
                distance_metres=10000,
                duration_seconds=5000,
                geometry_geojson={"type": "LineString", "coordinates": [[0, 0], [1, 1]]},
                navigation=RouteNavigationMetadata(provider="mapbox", steps=[]),
                features={},
            ),
            RouteCandidateInput(
                candidate_id="route-2-safest",
                label="Route 2",
                provider="mapbox",
                distance_metres=100,
                duration_seconds=80,
                geometry_geojson={"type": "LineString", "coordinates": [[0, 0], [2, 2]]},
                navigation=RouteNavigationMetadata(provider="mapbox", steps=[]),
                features={},
            ),
            RouteCandidateInput(
                candidate_id="route-3-moderate",
                label="Route 3",
                provider="mapbox",
                distance_metres=5000,
                duration_seconds=4000,
                geometry_geojson={"type": "LineString", "coordinates": [[0, 0], [3, 3]]},
                navigation=RouteNavigationMetadata(provider="mapbox", steps=[]),
                features={},
            ),
        ]

    monkeypatch.setattr("app.api.routes.routes.fetch_mapbox_route_candidates", mock_fetch_mapbox)

    # 2. Mock the safety enricher so they have distinct safety profiles
    async def mock_enrich_safety(route_geometry_geojson, route_id, **kwargs):
        if route_id == "route-2-safest":
            return {"incident_density": 0.0, "report_density": 0.0, "warnings": []}
        return {"incident_density": 1.0, "report_density": 0.0, "warnings": []}

    monkeypatch.setattr(
        "app.services.route_candidate_enricher.enrich_route_candidate_safety",
        mock_enrich_safety,
    )

    # 3. Mock the context enricher (lighting, accessibility)
    async def mock_context_features(*args, **kwargs):
        geom = kwargs.get("route_geometry_geojson") or (args[0] if args else {})
        # Route 2 geometry is [[0, 0], [2, 2]]
        if geom.get("coordinates") == [[0, 0], [2, 2]]:
            return {
                "lighting_score": 1.0,
                "accessibility": {"avoid_stairs": True},
                "waiting_areas": {},
                "transport": {},
                "warnings": [],
            }
        return {
            "lighting_score": 0.1,
            "accessibility": {"avoid_stairs": False},
            "waiting_areas": {},
            "transport": {},
            "warnings": [],
        }

    monkeypatch.setattr(
        "app.services.route_candidate_enricher.fetch_route_context_features",
        mock_context_features,
    )

    # Note: Using TestClient on an async endpoint automatically handles the event loop
    response = client.post(
        "/v1/routes/plan",
        json={
            "origin": {"latitude": 51.5072, "longitude": -0.1276},
            "destination": {"latitude": 51.5094, "longitude": -0.1183},
            "depart_at": "2026-03-22T22:30:00+00:00",
            "bias_mode": "maximum_safety",
            "alternatives": 3,
        },
    )

    assert response.status_code == 200
    body = response.json()

    # The backend should have fetched 3, scored 3, and ranked 3
    assert len(body["ranked_routes"]) == 3

    # The safest route (route-2) should be rank 1 and the selected route, despite being slightly longer
    assert body["selected_route_id"] == "route-2-safest"
    assert body["ranked_routes"][0]["candidate_id"] == "route-2-safest"
    assert body["ranked_routes"][0]["rank"] == 1

    # The moderately dangerous route should be rank 2
    assert body["ranked_routes"][1]["candidate_id"] == "route-3-moderate"
    assert body["ranked_routes"][1]["rank"] == 2

    # The completely dangerous route should fall to the bottom rank
    assert body["ranked_routes"][2]["candidate_id"] == "route-1-dangerous"
    assert body["ranked_routes"][2]["rank"] == 3
