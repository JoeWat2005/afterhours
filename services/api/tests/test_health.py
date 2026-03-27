from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_healthcheck_returns_ok() -> None:
    response = client.get("/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "afterhours-api"}
