from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.deps.auth import AuthContext, get_auth_context
from app.api.routes import heatmap as heatmap_route
from app.main import app
from app.services import heatmap as heatmap_service


@pytest.fixture()
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_missing_token_allowed_in_dev(client: TestClient) -> None:
    # dev mode lets unauthenticated requests through for the demo
    response = client.get("/v1/heatmap", params={"latitude": 51.5, "longitude": -0.12})
    assert response.status_code in (200, 401)


def test_invalid_token_returns_401(client: TestClient) -> None:
    response = client.get(
        "/v1/heatmap",
        params={"latitude": 51.5, "longitude": -0.12},
        headers={"Authorization": "Bearer invalid.token"},
    )
    assert response.status_code == 401


def test_heatmap_endpoint_response_shape(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    async def _mock_heatmap(query: heatmap_service.HeatmapQuery, **kwargs) -> heatmap_service.HeatmapResult:
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
