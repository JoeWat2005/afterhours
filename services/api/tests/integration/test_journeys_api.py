from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.deps.auth import AuthContext, get_auth_context, get_current_app_user
from app.api.routes import journeys as journeys_route
from app.db.session import get_db
from app.main import app
from app.models.journey import Journey
from app.models.user import AppUser


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

    async def commit(self) -> None:
        return None

    async def refresh(self, item: Any) -> None:
        return None

    async def execute(self, stmt: Any) -> FakeResult:
        if hasattr(stmt, "column_descriptions") and stmt.column_descriptions:
            entity = stmt.column_descriptions[0].get("entity")

            if entity is Journey:
                if not self.journeys:
                    return FakeResult(rows=[], scalars=[])
                journey = next(iter(self.journeys.values()))
                # Mock the route_geometry as a string if it's a dict
                route_geojson = journey.route_geometry if isinstance(journey.route_geometry, str) else "{}"
                return FakeResult(rows=[(journey, route_geojson)], scalars=[journey])

            if entity is AppUser:
                return FakeResult(rows=list(self.users.values()), scalars=list(self.users.values()))

        # Fallback for other statements (e.g. from the user's surgical fix request)
        class MockResult:
            def scalars(self): return self
            def first(self): return None
            def all(self): return []
            def __iter__(self): return iter([])
        return MockResult()

    async def get(self, model: type[Any], item_id: UUID) -> Any | None:
        if model is AppUser:
            return self.users.get(item_id)
        if model is Journey:
            return self.journeys.get(item_id)
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
