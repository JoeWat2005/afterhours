import pytest

from worker.jobs import aggregate_heatmaps, schedule_notifications


@pytest.mark.asyncio
async def test_aggregate_heatmaps_stub() -> None:
    result = await aggregate_heatmaps({})

    assert result["job"] == "aggregate_heatmaps"
    assert result["status"] == "stubbed"


@pytest.mark.asyncio
async def test_schedule_notifications_stub() -> None:
    result = await schedule_notifications({})

    assert result["job"] == "schedule_notifications"
    assert result["batch_size"] == 100
