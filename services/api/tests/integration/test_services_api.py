from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.deps.auth import get_current_app_user
from app.main import app
from app.models.user import AppUser


@pytest.fixture()
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _user() -> AppUser:
    return AppUser(
        id=uuid4(),
        clerk_user_id="clerk_user_1",
        display_name="Test User",
        created_at=datetime.now(UTC),
    )


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
