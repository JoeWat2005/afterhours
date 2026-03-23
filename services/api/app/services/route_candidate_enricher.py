from __future__ import annotations

from copy import deepcopy

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.routes import (
    RouteCandidateInput,
    RouteScoreRequest,
    RouteScoreResponse,
)
from app.services.route_crime_aggregator import enrich_route_candidate_safety
from app.services.route_context_api import fetch_route_context_features
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

    safety_metrics = await enrich_route_candidate_safety(
        route_geometry_geojson=enriched.geometry_geojson,
        route_id=enriched.candidate_id,
        date=crime_date,
        category=crime_category,
        db=db,
    )

    context = await fetch_route_context_features(
        route_geometry_geojson=enriched.geometry_geojson,
    )

    # Safety features
    enriched.features.safety.incident_density = safety_metrics["incident_density"]
    enriched.features.safety.report_density = safety_metrics["report_density"]
    enriched.features.safety.lighting_score = context["lighting_score"]

    # Accessibility features
    accessibility = context["accessibility"]
    enriched.features.accessibility.stairs_present = accessibility.get("stairs_present")
    enriched.features.accessibility.step_free_ratio = accessibility.get("step_free_ratio")
    enriched.features.accessibility.lift_coverage_ratio = accessibility.get("lift_coverage_ratio")
    enriched.features.accessibility.ramp_coverage_ratio = accessibility.get("ramp_coverage_ratio")
    enriched.features.accessibility.escalator_coverage_ratio = accessibility.get("escalator_coverage_ratio")

    # Waiting-area features
    waiting = context["waiting_areas"]
    enriched.features.waiting_areas.safe_waiting_area_count = waiting.get("safe_waiting_area_count")
    enriched.features.waiting_areas.well_lit_waiting_area_count = waiting.get("well_lit_waiting_area_count")
    enriched.features.waiting_areas.wifi_access_point_count = waiting.get("wifi_access_point_count")
    enriched.features.waiting_areas.staffed_venue_count = waiting.get("staffed_venue_count")
    enriched.features.waiting_areas.open_venue_count = waiting.get("open_venue_count")
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
    enriched_candidates: list[RouteCandidateInput] = []

    for candidate in payload.route_candidates:
        enriched_candidate = await enrich_route_candidate(
            candidate,
            db=db,
            crime_date=crime_date,
            crime_category=crime_category,
        )
        enriched_candidates.append(enriched_candidate)

    enriched_payload = deepcopy(payload)
    enriched_payload.route_candidates = enriched_candidates

    return score_route_request(enriched_payload)