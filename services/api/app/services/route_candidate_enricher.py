from __future__ import annotations

import asyncio
from copy import deepcopy

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session_factory
from app.integrations.overpass_client import fetch_route_context_features
from app.schemas.routes import (
    RouteCandidateInput,
    RouteScoreRequest,
    RouteScoreResponse,
)
from app.services.route_safety import enrich_route_candidate_safety
from app.services.route_scoring import score_route_request


def _merge_safety_warnings(candidate: RouteCandidateInput, warnings: list[str]) -> None:
    existing = list(getattr(candidate.features.safety, "warnings", []) or [])
    candidate.features.safety.warnings = sorted(set(existing + warnings))


async def enrich_route_candidate(
    candidate: RouteCandidateInput,
    *,
    db: AsyncSession | None = None,
    crime_date: str | None = None,
    crime_category: str = "all-crime",
) -> RouteCandidateInput:
    enriched = deepcopy(candidate)

    # run safety and context enrichment concurrently
    safety_task = enrich_route_candidate_safety(
        route_geometry_geojson=enriched.geometry_geojson,
        route_id=enriched.candidate_id,
        date=crime_date,
        category=crime_category,
        db=db,
    )
    context_task = fetch_route_context_features(
        route_geometry_geojson=enriched.geometry_geojson,
    )
    safety_metrics, context = await asyncio.gather(safety_task, context_task)

    # Only fill missing safety values
    if enriched.features.safety.incident_density is None:
        enriched.features.safety.incident_density = safety_metrics["incident_density"]
    if enriched.features.safety.report_density is None:
        enriched.features.safety.report_density = safety_metrics["report_density"]
    if enriched.features.safety.lighting_score is None:
        enriched.features.safety.lighting_score = context["lighting_score"]

    accessibility = context["accessibility"]
    if (
        enriched.features.accessibility.stairs_present is None
        and accessibility.get("stairs_present") is not None
    ):
        enriched.features.accessibility.stairs_present = accessibility.get("stairs_present")

    if (
        enriched.features.accessibility.step_free_ratio is None
        and accessibility.get("step_free_ratio") is not None
    ):
        enriched.features.accessibility.step_free_ratio = accessibility.get("step_free_ratio")

    if (
        enriched.features.accessibility.lift_coverage_ratio is None
        and accessibility.get("lift_coverage_ratio") is not None
    ):
        enriched.features.accessibility.lift_coverage_ratio = accessibility.get("lift_coverage_ratio")

    if (
        enriched.features.accessibility.ramp_coverage_ratio is None
        and accessibility.get("ramp_coverage_ratio") is not None
    ):
        enriched.features.accessibility.ramp_coverage_ratio = accessibility.get("ramp_coverage_ratio")

    if (
        enriched.features.accessibility.escalator_coverage_ratio is None
        and accessibility.get("escalator_coverage_ratio") is not None
    ):
        enriched.features.accessibility.escalator_coverage_ratio = accessibility.get(
            "escalator_coverage_ratio"
        )

    waiting = context["waiting_areas"]
    if (
        enriched.features.waiting_areas.safe_waiting_area_count is None
        and waiting.get("safe_waiting_area_count") is not None
    ):
        enriched.features.waiting_areas.safe_waiting_area_count = waiting.get(
            "safe_waiting_area_count"
        )

    if (
        enriched.features.waiting_areas.well_lit_waiting_area_count is None
        and waiting.get("well_lit_waiting_area_count") is not None
    ):
        enriched.features.waiting_areas.well_lit_waiting_area_count = waiting.get(
            "well_lit_waiting_area_count"
        )

    if (
        enriched.features.waiting_areas.wifi_access_point_count is None
        and waiting.get("wifi_access_point_count") is not None
    ):
        enriched.features.waiting_areas.wifi_access_point_count = waiting.get(
            "wifi_access_point_count"
        )

    if (
        enriched.features.waiting_areas.staffed_venue_count is None
        and waiting.get("staffed_venue_count") is not None
    ):
        enriched.features.waiting_areas.staffed_venue_count = waiting.get(
            "staffed_venue_count"
        )

    if (
        enriched.features.waiting_areas.open_venue_count is None
        and waiting.get("open_venue_count") is not None
    ):
        enriched.features.waiting_areas.open_venue_count = waiting.get("open_venue_count")

    if (
        enriched.features.waiting_areas.waiting_areas_in_safe_areas_ratio is None
        and waiting.get("waiting_areas_in_safe_areas_ratio") is not None
    ):
        enriched.features.waiting_areas.waiting_areas_in_safe_areas_ratio = waiting.get(
            "waiting_areas_in_safe_areas_ratio"
        )

    _merge_safety_warnings(
        enriched,
        list(safety_metrics["warnings"]) + list(context["warnings"]),
    )

    return enriched


async def enrich_and_score_routes(
    payload: RouteScoreRequest,
    *,
    db: AsyncSession | None = None,
    crime_date: str | None = None,
    crime_category: str = "all-crime",
) -> RouteScoreResponse:
    async def enrich_with_own_session(candidate: RouteCandidateInput) -> RouteCandidateInput:
        # each route gets its own db session so they can run concurrently
        if db is not None:
            async with get_session_factory()() as own_db:
                return await enrich_route_candidate(
                    candidate, db=own_db,
                    crime_date=crime_date, crime_category=crime_category,
                )
        return await enrich_route_candidate(
            candidate, db=None,
            crime_date=crime_date, crime_category=crime_category,
        )

    enriched_candidates = await asyncio.gather(*(
        enrich_with_own_session(c) for c in payload.route_candidates
    ))

    enriched_payload = deepcopy(payload)
    enriched_payload.route_candidates = list(enriched_candidates)

    return score_route_request(enriched_payload)
