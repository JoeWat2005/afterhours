from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_openapi_document_is_available() -> None:
    response = client.get("/openapi.json")
    assert response.status_code == 200
    assert response.json()["info"]["title"] == "AfterHours API"

    paths = response.json()["paths"]
    # Verify excluded paths
    assert all(not path.startswith("/v1/notifications") for path in paths)
    assert all(not path.startswith("/v1/places") for path in paths)
    assert all(not path.startswith("/v1/transport") for path in paths)
    assert "/v1/heatmap/ingest" not in paths

    # Verify deprecated paths
    assert paths["/v1/users/{user_id}"]["get"]["deprecated"] is True
    assert paths["/v1/users/{user_id}"]["patch"]["deprecated"] is True
    assert paths["/v1/users/clerk/{clerk_user_id}"]["get"]["deprecated"] is True

