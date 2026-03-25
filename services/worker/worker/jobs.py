from datetime import UTC, datetime

import httpx

from worker.config import get_settings


async def ingest_transport_feeds(ctx: dict[str, object]) -> dict[str, object]:
    settings = get_settings()
    async with httpx.AsyncClient(base_url=settings.api_base_url, timeout=10.0) as client:
        await client.get("/v1/health")
    return {
        "job": "ingest_transport_feeds",
        "status": "stubbed",
        "at": datetime.now(UTC).isoformat(),
    }


async def schedule_notifications(ctx: dict[str, object]) -> dict[str, object]:
    settings = get_settings()
    return {
        "job": "schedule_notifications",
        "status": "stubbed",
        "batch_size": settings.notification_batch_size,
    }
