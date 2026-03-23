from __future__ import annotations

import json
import os
from pathlib import Path

import httpx
import pytest


RUN_LIVE = os.getenv("RUN_LIVE_ROUTE_TEST", "0") == "1"
API_BASE_URL = os.getenv("ROUTE_TEST_BASE_URL", "http://127.0.0.1:8000")
PAYLOAD_PATH = (
    Path(__file__).resolve().parent / "manual" / "route_score_live_payload.json"
)


pytestmark = pytest.mark.skipif(
    not RUN_LIVE,
    reason=(
        "Set RUN_LIVE_ROUTE_TEST=1 to run live route E2E tests "
        "against a running local API."
    ),
)


@pytest.mark.asyncio
async def test_live_route_scoring_enrichment_and_ranking() -> None:
    payload = json.loads(PAYLOAD_PATH.read_text(encoding="utf-8"))

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{API_BASE_URL}/v1/routes/score",
            json=payload,
        )

    assert response.status_code == 200, response.text
    body = response.json()

    candidate_ids = {
        candidate["candidate_id"] for candidate in payload["route_candidates"]
    }
    ranked_routes = body["ranked_routes"]

    assert body["selected_route_id"] in candidate_ids
    assert len(ranked_routes) >= 3
    assert [route["rank"] for route in ranked_routes] == list(
        range(1, len(ranked_routes) + 1)
    )

    for route in ranked_routes:
        assert route["candidate_id"] in candidate_ids
        assert 0 <= route["score"] <= 100

        component_scores = route["component_scores"]
        for key in (
            "safety",
            "lighting",
            "accessibility",
            "transport",
            "efficiency",
            "places",
        ):
            assert key in component_scores
            assert 0 <= component_scores[key] <= 1

        explanation = route["explanation"]
        assert isinstance(explanation["summary"], str)
        assert isinstance(explanation["reasons"], list)
        assert isinstance(explanation["warnings"], list)

    # Ensure live enrichment had some effect on at least one non-transport signal.
    # Transport is currently expected to be fallback in this codebase.
    non_default_enrichment_present = any(
        (
            route["component_scores"]["safety"] != 0.5
            or route["component_scores"]["lighting"] != 0.5
            or route["component_scores"]["places"] != 0.5
            or route["component_scores"]["accessibility"] != 0.5
        )
        for route in ranked_routes
    )
    assert non_default_enrichment_present, (
        "All enrichment-driven component scores are fallback defaults. "
        "Check upstream Police/Overpass availability."
    )
