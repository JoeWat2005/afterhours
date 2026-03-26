from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.deps.auth import AuthContext, get_auth_context, get_current_app_user
from app.api.routes import heatmap as heatmap_route
from app.api.routes import journeys as journeys_route
from app.api.routes import reports as reports_route
from app.api.routes import routes as routes_route
from app.db.session import get_db
from app.main import app
from app.models.journey import Journey
from app.models.report import SafetyReport
from app.models.user import AppUser
from app.schemas.reports import SafetyReportResponse
from app.schemas.routes import RouteScoreResponse
from app.services import heatmap as heatmap_service


class FakeScalarResult:
    def __init__(self, items: list[Any]) -> None:
        self._items = items

    def first(self) -> Any | None:
        return self._items[0] if self._items else None

    def all(self) -> list[Any]:
        return list(self._items)


class FakeResult:
    def __init__(self, *, rows: list[Any] | None = None, scalars: list[Any] | None = None) -> None:
        self._rows = rows or []
        self._scalars = scalars or []

    def first(self) -> Any | None:
        return self._rows[0] if self._rows else None

    def scalars(self) -> FakeScalarResult:
        return FakeScalarResult(self._scalars)


class FakeAsyncSession:
    def __init__(self) -> None:
        self.users: dict[UUID, AppUser] = {}
        self.journeys: dict[UUID, Journey] = {}
        self.reports: dict[UUID, SafetyReport] = {}

    def add(self, item: Any) -> None:
        now = datetime.now(UTC)
        if hasattr(item, "id") and getattr(item, "id", None) is None:
            setattr(item, "id", uuid4())
        if hasattr(item, "created_at") and getattr(item, "created_at", None) is None:
            setattr(item, "created_at", now)

        if isinstance(item, AppUser):
            self.users[item.id] = item
        elif isinstance(item, Journey):
            self.journeys[item.id] = item
        elif isinstance(item, SafetyReport):
            location = getattr(item, "location", {})
            if isinstance(location, dict):
                item.latitude = float(location["latitude"])
                item.longitude = float(location["longitude"])
            self.reports[item.id] = item

    async def commit(self) -> None:
        return None

    async def refresh(self, item: Any) -> None:
        return None

    async def execute(self, stmt: Any) -> FakeResult:
        entity = stmt.column_descriptions[0].get("entity")

        if entity is Journey:
            if not self.journeys:
                return FakeResult(rows=[], scalars=[])
            journey = next(iter(self.journeys.values()))
            route_geojson = journey.route_geometry if isinstance(journey.route_geometry, str) else "{}"
            return FakeResult(rows=[(journey, route_geojson)], scalars=[journey])

        if entity is SafetyReport:
            if not self.reports:
                return FakeResult(rows=[], scalars=[])
            report = next(iter(self.reports.values()))
            return FakeResult(rows=[report], scalars=[report])

        if entity is AppUser:
            return FakeResult(rows=list(self.users.values()), scalars=list(self.users.values()))

        return FakeResult(rows=[], scalars=[])

    async def get(self, model: type[Any], item_id: UUID) -> Any | None:
        if model is AppUser:
            return self.users.get(item_id)
        if model is Journey:
            return self.journeys.get(item_id)
        if model is SafetyReport:
            return self.reports.get(item_id)
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


def _user(
    *,
    user_id: UUID | None = None,
    clerk_user_id: str = "clerk_user_1",
    display_name: str | None = "Test User",
) -> AppUser:
    return AppUser(
        id=user_id or uuid4(),
        clerk_user_id=clerk_user_id,
        display_name=display_name,
        created_at=datetime.now(UTC),
    )


def _patch_geometry_helpers(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(journeys_route.func, "ST_GeomFromGeoJSON", lambda geojson: geojson)
    monkeypatch.setattr(journeys_route.func, "ST_SetSRID", lambda geometry, srid: geometry)
    monkeypatch.setattr(
        reports_route.func,
        "ST_MakePoint",
        lambda longitude, latitude: {"longitude": longitude, "latitude": latitude},
    )
    monkeypatch.setattr(reports_route.func, "ST_SetSRID", lambda point, srid: point)

    def _report_to_response(report: Any) -> SafetyReportResponse:
        return SafetyReportResponse(
            id=report.id,
            user_id=report.user_id,
            category=report.category,
            severity=report.severity,
            summary=report.summary,
            details=report.details,
            latitude=float(report.latitude),
            longitude=float(report.longitude),
            created_at=report.created_at,
        )

    monkeypatch.setattr(reports_route, "_report_to_response", _report_to_response)


def test_missing_token_returns_401(client: TestClient) -> None:
    response = client.get("/v1/heatmap", params={"latitude": 51.5, "longitude": -0.12})
    assert response.status_code == 401


def test_invalid_token_returns_401(client: TestClient) -> None:
    response = client.get(
        "/v1/heatmap",
        params={"latitude": 51.5, "longitude": -0.12},
        headers={"Authorization": "Bearer invalid.token"},
    )
    assert response.status_code == 401


def test_subject_mismatch_returns_403_on_journey_create(client: TestClient) -> None:
    fake_db = FakeAsyncSession()
    current_user = _user()

    app.dependency_overrides[get_db] = _override_db(fake_db)
    app.dependency_overrides[get_current_app_user] = lambda: current_user

    response = client.post(
        "/v1/journeys",
        json={
            "user_id": str(uuid4()),
            "origin_label": "A",
            "destination_label": "B",
            "score": 80.0,
            "route_geojson": {
                "type": "LineString",
                "coordinates": [[-0.12, 51.5], [-0.11, 51.51]],
            },
        },
    )

    assert response.status_code == 403


def test_journeys_create_and_get_by_id(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_db = FakeAsyncSession()
    current_user = _user()
    _patch_geometry_helpers(monkeypatch)

    app.dependency_overrides[get_db] = _override_db(fake_db)
    app.dependency_overrides[get_current_app_user] = lambda: current_user

    create_response = client.post(
        "/v1/journeys",
        json={
            "origin_label": "University",
            "destination_label": "Station",
            "score": 91.2,
            "route_geojson": {
                "type": "LineString",
                "coordinates": [[-0.12, 51.5], [-0.11, 51.51]],
            },
        },
    )
    assert create_response.status_code == 201
    created = create_response.json()
    assert created["user_id"] == str(current_user.id)

    get_response = client.get(f"/v1/journeys/{created['id']}")
    assert get_response.status_code == 200
    fetched = get_response.json()
    assert fetched["id"] == created["id"]


def test_journeys_get_returns_404_when_missing(client: TestClient) -> None:
    fake_db = FakeAsyncSession()
    app.dependency_overrides[get_db] = _override_db(fake_db)
    app.dependency_overrides[get_current_app_user] = lambda: _user()

    response = client.get(f"/v1/journeys/{uuid4()}")
    assert response.status_code == 404


def test_reports_create_nearby_and_get_by_id(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_db = FakeAsyncSession()
    current_user = _user()
    _patch_geometry_helpers(monkeypatch)

    async def _mock_nearby(*args, **kwargs) -> list[SafetyReport]:
        return list(fake_db.reports.values())

    monkeypatch.setattr(reports_route, "list_nearby_reports", _mock_nearby)

    app.dependency_overrides[get_db] = _override_db(fake_db)
    app.dependency_overrides[get_current_app_user] = lambda: current_user

    create_response = client.post(
        "/v1/reports",
        json={
            "category": "theft",
            "summary": "Phone snatch",
            "details": "Near station entrance",
            "latitude": 51.5,
            "longitude": -0.12,
        },
    )
    assert create_response.status_code == 201
    created = create_response.json()

    nearby_response = client.get(
        "/v1/reports/nearby",
        params={
            "latitude": 51.5,
            "longitude": -0.12,
            "radius_metres": 500,
            "limit": 10,
        },
    )
    assert nearby_response.status_code == 200
    assert nearby_response.json()["items"]

    get_response = client.get(f"/v1/reports/{created['id']}")
    assert get_response.status_code == 200
    assert get_response.json()["id"] == created["id"]


def test_reports_get_returns_404_when_missing(client: TestClient) -> None:
    fake_db = FakeAsyncSession()
    app.dependency_overrides[get_db] = _override_db(fake_db)
    app.dependency_overrides[get_current_app_user] = lambda: _user()

    response = client.get(f"/v1/reports/{uuid4()}")
    assert response.status_code == 404


def test_users_me_and_compatibility_endpoints(client: TestClient) -> None:
    fake_db = FakeAsyncSession()
    current_user = _user(display_name="Original")

    app.dependency_overrides[get_db] = _override_db(fake_db)
    app.dependency_overrides[get_current_app_user] = lambda: current_user

    me_response = client.get("/v1/users/me")
    assert me_response.status_code == 200
    assert me_response.json()["id"] == str(current_user.id)

    patch_response = client.patch("/v1/users/me", json={"display_name": "Updated"})
    assert patch_response.status_code == 200
    assert patch_response.json()["display_name"] == "Updated"

    compat_response = client.get(f"/v1/users/{current_user.id}")
    assert compat_response.status_code == 200

    mismatch_response = client.get(f"/v1/users/{uuid4()}")
    assert mismatch_response.status_code == 403

    clerk_response = client.get(f"/v1/users/clerk/{current_user.clerk_user_id}")
    assert clerk_response.status_code == 200


def test_heatmap_endpoint_response_shape(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    async def _mock_heatmap(query: heatmap_service.HeatmapQuery) -> heatmap_service.HeatmapResult:
        _ = query
        return heatmap_service.HeatmapResult(
            latitude=51.5,
            longitude=-0.12,
            radius_metres=20000,
            cell_size_metres=250,
            category="all-crime",
            date="2026-02",
            items=[
                {
                    "cell_id": "0:0",
                    "center_latitude": 51.5,
                    "center_longitude": -0.12,
                    "risk_score": 5.0,
                    "source_count": 2,
                    "bounds": {
                        "min_latitude": 51.499,
                        "min_longitude": -0.121,
                        "max_latitude": 51.501,
                        "max_longitude": -0.119,
                    },
                }
            ],
        )

    app.dependency_overrides[get_auth_context] = lambda: AuthContext(
        subject="clerk_user_1",
        claims={},
    )
    monkeypatch.setattr(heatmap_route, "get_on_demand_heatmap", _mock_heatmap)

    response = client.get("/v1/heatmap", params={"latitude": 51.5, "longitude": -0.12})
    assert response.status_code == 200
    body = response.json()
    assert body["radius_metres"] == 20000
    assert body["items"][0]["cell_id"] == "0:0"


def test_heatmap_endpoint_rejects_invalid_date(client: TestClient) -> None:
    app.dependency_overrides[get_auth_context] = lambda: AuthContext(
        subject="clerk_user_1",
        claims={},
    )

    response = client.get(
        "/v1/heatmap",
        params={"latitude": 51.5, "longitude": -0.12, "date": "2026-2"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_heatmap_service_cache_hit(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"fetch": 0}
    heatmap_service.clear_heatmap_cache()

    async def _mock_fetch(*, sample_points, category, date):
        _ = sample_points, category, date
        calls["fetch"] += 1
        return (
            [
                {
                    "category": "robbery",
                    "month": "2026-02",
                    "persistent_id": "crime-1",
                    "location": {
                        "latitude": "51.5",
                        "longitude": "-0.12",
                        "street": {"name": "Main Street"},
                    },
                }
            ],
            "2026-02",
        )

    monkeypatch.setattr(
        heatmap_service,
        "_generate_sample_points",
        lambda **kwargs: [(51.5, -0.12)],
    )
    monkeypatch.setattr(heatmap_service, "_fetch_deduped_crimes", _mock_fetch)

    query = heatmap_service.HeatmapQuery(
        latitude=51.5,
        longitude=-0.12,
        radius_metres=20000,
        cell_size_metres=250,
        category="all-crime",
        date="2026-02",
    )

    first = await heatmap_service.get_on_demand_heatmap(query)
    second = await heatmap_service.get_on_demand_heatmap(query)

    assert calls["fetch"] == 1
    assert first.items == second.items


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


def test_services_nearby_endpoint_filters_and_orders(client: TestClient) -> None:
    app.dependency_overrides[get_current_app_user] = lambda: _user()

    response = client.get(
        "/v1/services/nearby",
        params={
            "latitude": 52.4862,
            "longitude": -1.8904,
            "category": "police",
            "radius_metres": 5000,
            "limit": 3,
        },
    )

    assert response.status_code == 200
    items = response.json()["items"]
    assert 0 < len(items) <= 3
    assert all(item["category"] == "police" for item in items)
    distances = [item["distance_metres"] for item in items]
    assert distances == sorted(distances)


def test_services_nearby_endpoint_validates_radius_and_limit(client: TestClient) -> None:
    app.dependency_overrides[get_current_app_user] = lambda: _user()

    response = client.get(
        "/v1/services/nearby",
        params={
            "latitude": 52.4862,
            "longitude": -1.8904,
            "radius_metres": 25000,
            "limit": 0,
        },
    )
    assert response.status_code == 422


def test_openapi_excludes_removed_endpoints_and_marks_compat_users_deprecated(
    client: TestClient,
) -> None:
    response = client.get("/openapi.json")
    assert response.status_code == 200
    paths = response.json()["paths"]

    assert all(not path.startswith("/v1/notifications") for path in paths)
    assert all(not path.startswith("/v1/places") for path in paths)
    assert all(not path.startswith("/v1/transport") for path in paths)
    assert "/v1/heatmap/ingest" not in paths

    assert paths["/v1/users/{user_id}"]["get"]["deprecated"] is True
    assert paths["/v1/users/{user_id}"]["patch"]["deprecated"] is True
    assert paths["/v1/users/clerk/{clerk_user_id}"]["get"]["deprecated"] is True
