from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.deps.auth import get_current_app_user
from app.api.routes import reports as reports_route
from app.db.session import get_db
from app.main import app
from app.models.report import SafetyReport
from app.models.user import AppUser
from app.schemas.reports import SafetyReportResponse


class FakeAsyncSession:
    def __init__(self) -> None:
        self.reports: dict[UUID, SafetyReport] = {}

    def add(self, item: Any) -> None:
        now = datetime.now(UTC)
        if hasattr(item, "id") and getattr(item, "id", None) is None:
            setattr(item, "id", uuid4())
        if hasattr(item, "created_at") and getattr(item, "created_at", None) is None:
            setattr(item, "created_at", now)

        if isinstance(item, SafetyReport):
            location = getattr(item, "location", {})
            if isinstance(location, dict):
                item.latitude = float(location["latitude"])
                item.longitude = float(location["longitude"])
            self.reports[item.id] = item

    async def commit(self) -> None:
        return None

    async def refresh(self, item: Any) -> None:
        return None

    async def execute(self, stmt: Any) -> Any:
        # Check if it's a select for SafetyReport
        if hasattr(stmt, "column_descriptions") and stmt.column_descriptions:
            entity = stmt.column_descriptions[0].get("entity")
            if entity is SafetyReport:
                report = next(iter(self.reports.values())) if self.reports else None
                class MockResult:
                    def __init__(self, item): self.item = item
                    def scalars(self): return self
                    def first(self): return self.item
                    def all(self): return [self.item] if self.item else []
                    def __iter__(self): return iter([self.item] if self.item else [])
                return MockResult(report)

        class MockResult:
            def scalars(self): return self
            def first(self): return None
            def all(self): return []
            def __iter__(self): return iter([])
        return MockResult()

    async def get(self, model: type[Any], item_id: UUID) -> Any | None:
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


def _user() -> AppUser:
    return AppUser(
        id=uuid4(),
        clerk_user_id="clerk_user_1",
        display_name="Test User",
        created_at=datetime.now(UTC),
    )


def _patch_geometry_helpers(monkeypatch: pytest.MonkeyPatch) -> None:
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
