import pytest

from worker.jobs import ingest_transport_feeds, schedule_notifications


@pytest.mark.asyncio
async def test_ingest_transport_feeds_stub(monkeypatch) -> None:
    class MockResponse:
        status_code = 200

    class MockClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def get(self, path: str) -> MockResponse:
            assert path == "/v1/health"
            return MockResponse()

    monkeypatch.setattr("worker.jobs.httpx.AsyncClient", lambda **kwargs: MockClient())

    result = await ingest_transport_feeds({})

    assert result["job"] == "ingest_transport_feeds"
    assert result["status"] == "stubbed"


@pytest.mark.asyncio
async def test_schedule_notifications_stub() -> None:
    result = await schedule_notifications({})

    assert result["job"] == "schedule_notifications"
    assert result["batch_size"] == 100
