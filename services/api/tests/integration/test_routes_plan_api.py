from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.routes import routes as routes_route
from app.db.session import get_db
from app.main import app
from app.schemas.routes import RouteScoreResponse


class FakeAsyncSession:
    async def commit(self) -> None:
        return None

    async def execute(self, stmt: Any) -> Any:
        class MockResult:
            def scalars(self):
                return self

            def first(self):
                return None

            def all(self):
                return []

            def __iter__(self):
                return iter([])

        return MockResult()

    async def get(self, model: type[Any], item_id: UUID) -> Any | None:
        return None

    async def refresh(self, item: Any) -> None:
        return None


@pytest.fixture()
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _override_db(fake_db: FakeAsyncSession):
    async def _dependency():
        yield fake_db

    return _dependency


def test_routes_plan_endpoint(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    async def _mock_fetch_mapbox_route_candidates(**kwargs):
        _ = kwargs
        return [
            {
                "candidate_id": "route-a",
                "provider": "mapbox",
                "label": "Route A",
                "distance_metres": 900,
                "duration_seconds": 700,
                "geometry_geojson": {
                    "type": "LineString",
                    "coordinates": [[-0.12, 51.5], [-0.11, 51.51]],
                },
                "navigation": {
                    "provider": "mapbox",
                    "steps": [
                        {
                            "step_index": 0,
                            "distance_metres": 350,
                            "duration_seconds": 300,
                            "instruction": "Head north-east",
                            "street_name": "Example Street",
                            "maneuver_type": "depart",
                            "maneuver_modifier": "straight",
                            "maneuver_location": {
                                "latitude": 51.5,
                                "longitude": -0.12,
                            },
                            "geometry_geojson": {
                                "type": "LineString",
                                "coordinates": [[-0.12, 51.5], [-0.115, 51.505]],
                            },
                        }
                    ],
                },
                "features": {
                    "safety": {"incident_density": 0.2, "lighting_score": 0.8, "report_density": 0.2},
                    "accessibility": {},
                    "transport": {},
                    "waiting_areas": {},
                },
            }
        ]

    async def _mock_enrich_and_score_routes(*args, **kwargs):
        _ = args, kwargs
        return RouteScoreResponse.model_validate(
            {
                "selected_route_id": "route-a",
                "requirements_applied": False,
                "requirement_matches_found": True,
                "selected_route_is_fallback": False,
                "ranked_routes": [
                    {
                        "candidate_id": "route-a",
                        "label": "Route A",
                        "provider": "mapbox",
                        "rank": 1,
                        "meets_requirements": True,
                        "unmet_requirements": [],
                        "is_fallback": False,
                        "score": 85.0,
                        "distance_metres": 900,
                        "duration_seconds": 700,
                        "geometry_geojson": {
                            "type": "LineString",
                            "coordinates": [[-0.12, 51.5], [-0.11, 51.51]],
                        },
                        "navigation": {
                            "provider": "mapbox",
                            "steps": [
                                {
                                    "step_index": 0,
                                    "distance_metres": 350,
                                    "duration_seconds": 300,
                                    "instruction": "Head north-east",
                                    "street_name": "Example Street",
                                    "maneuver_type": "depart",
                                    "maneuver_modifier": "straight",
                                    "maneuver_location": {
                                        "latitude": 51.5,
                                        "longitude": -0.12,
                                    },
                                    "geometry_geojson": {
                                        "type": "LineString",
                                        "coordinates": [[-0.12, 51.5], [-0.115, 51.505]],
                                    },
                                }
                            ],
                        },
                        "component_scores": {
                            "safety": 0.8,
                            "lighting": 0.8,
                            "accessibility": 0.8,
                            "transport": 0.8,
                            "efficiency": 0.8,
                            "places": 0.8,
                        },
                        "explanation": {
                            "summary": "Good route",
                            "reasons": [],
                            "warnings": [],
                        },
                    }
                ],
                "warnings": [],
            }
        )

    app.dependency_overrides[get_db] = _override_db(FakeAsyncSession())
    monkeypatch.setattr(routes_route, "fetch_mapbox_route_candidates", _mock_fetch_mapbox_route_candidates)
    monkeypatch.setattr(routes_route, "enrich_and_score_routes", _mock_enrich_and_score_routes)

    response = client.post(
        "/v1/routes/plan",
        json={
            "origin": {"latitude": 51.5, "longitude": -0.12},
            "destination": {"latitude": 51.51, "longitude": -0.11},
            "depart_at": "2026-03-25T21:30:00+00:00",
            "alternatives": 1,
        },
    )

    assert response.status_code == 200
    assert response.json()["selected_route_id"] == "route-a"
    assert response.json()["ranked_routes"][0]["navigation"]["steps"][0]["instruction"] == "Head north-east"
