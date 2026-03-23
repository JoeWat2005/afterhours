from datetime import UTC, datetime

import httpx

from worker.config import get_settings


async def ingest_transport_feeds(ctx: dict[str, object]) -> dict[str, object]:
    settings = get_settings()
    async with httpx.AsyncClient(base_url=settings.api_base_url, timeout=10.0) as client:
        await client.get("/v1/health")
    return {"job": "ingest_transport_feeds", "status": "stubbed", "at": datetime.now(UTC).isoformat()}


async def aggregate_heatmaps(ctx: dict[str, object]) -> dict[str, object]:
    """
    Fetches crime data from the UK Police API, scores it using HeatmapEngine,
    and upserts the resulting cells into the heatmap_cells table via the API.

    Centre point and grid size are hardcoded to Birmingham city centre for now;
    extend ctx or settings to make these configurable per-job.
    """
    # Inline import keeps the optional dependency isolated to this job
    from app.services.heatmap_engine import HeatmapEngine  # type: ignore[import]

    settings = get_settings()
    engine = HeatmapEngine()

    # Default centre: Birmingham city centre
    center_lat: float = float(ctx.get("center_lat", 52.4862))  # type: ignore[arg-type]
    center_lng: float = float(ctx.get("center_lng", -1.8904))  # type: ignore[arg-type]
    grid_size: int = int(ctx.get("grid_size", 30))  # type: ignore[arg-type]

    grid = engine.generate_empty_grid(center_lat, center_lng, size=grid_size)

    # ------------------------------------------------------------------
    # Fetch crimes from the UK Police API
    # ------------------------------------------------------------------
    police_api = "https://data.police.uk/api"
    crimes: list[dict] = []

    async with httpx.AsyncClient(base_url=police_api, timeout=30.0) as police:
        # The Police API accepts lat/lng and returns crimes within 1 mile
        resp = await police.get(
            "/crimes-street/all-crime",
            params={"lat": center_lat, "lng": center_lng},
        )
        if resp.status_code == 200:
            for entry in resp.json():
                try:
                    crimes.append(
                        {
                            "type": entry["category"],
                            "lat": float(entry["location"]["latitude"]),
                            "lng": float(entry["location"]["longitude"]),
                        }
                    )
                except (KeyError, TypeError, ValueError):
                    continue  # skip malformed entries

    # Lighting data not yet available — pass an empty set
    lighting_data: set[str] = set()

    scored_grid = engine.populate_grid(grid, crimes, lighting_data)

    # ------------------------------------------------------------------
    # POST scored cells to the API's ingest endpoint
    # ------------------------------------------------------------------
    cells_payload = [
        {
            "cell_geometry_wkt": square["cell_geometry_wkt"],
            "risk_score": square["risk_score"],
            "source_count": square["source_count"],
        }
        for square in scored_grid
    ]

    cells_updated = 0
    async with httpx.AsyncClient(base_url=settings.api_base_url, timeout=30.0) as client:
        resp = await client.post("/v1/heatmap/ingest", json={"cells": cells_payload})
        if resp.status_code == 204:
            cells_updated = sum(1 for c in cells_payload if c["risk_score"] > 0)

    return {
        "job": "aggregate_heatmaps",
        "status": "ok",
        "crimes_fetched": len(crimes),
        "cells_updated": cells_updated,
        "at": datetime.now(UTC).isoformat(),
    }


async def schedule_notifications(ctx: dict[str, object]) -> dict[str, object]:
    settings = get_settings()
    return {
        "job": "schedule_notifications",
        "status": "stubbed",
        "batch_size": settings.notification_batch_size,
    }

