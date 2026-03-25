import httpx
import math
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.integrations.mapbox_directions_client import fetch_mapbox_route_candidates
from app.schemas.routes import (
    RoutePlanRequest,
    RouteScoreRequest,
    RouteScoreResponse,
    SafetyReportRequest,
    SafetyReportValidationResponse,
)
from app.services.route_candidate_enricher import enrich_and_score_routes
from app.services.safety_reports import validate_report

router = APIRouter()
MAX_LOCAL_WALK_DISTANCE_METRES = 50_000


def _haversine_metres(
    origin_latitude: float,
    origin_longitude: float,
    destination_latitude: float,
    destination_longitude: float,
) -> float:
    earth_radius = 6_371_000
    lat1 = math.radians(origin_latitude)
    lat2 = math.radians(destination_latitude)
    delta_lat = math.radians(destination_latitude - origin_latitude)
    delta_lon = math.radians(destination_longitude - origin_longitude)
    sin_lat = math.sin(delta_lat / 2)
    sin_lon = math.sin(delta_lon / 2)
    haversine = sin_lat * sin_lat + math.cos(lat1) * math.cos(lat2) * sin_lon * sin_lon
    return 2 * earth_radius * math.asin(math.sqrt(haversine))


@router.post("/score", response_model=RouteScoreResponse)
async def score_candidate_route(
    payload: RouteScoreRequest,
    db: AsyncSession = Depends(get_db),
) -> RouteScoreResponse:
    return await enrich_and_score_routes(payload, db=db)


@router.post("/plan", response_model=RouteScoreResponse)
async def plan_and_score_routes(
    payload: RoutePlanRequest,
    db: AsyncSession = Depends(get_db),
) -> RouteScoreResponse:
    beeline_distance = _haversine_metres(
        payload.origin.latitude,
        payload.origin.longitude,
        payload.destination.latitude,
        payload.destination.longitude,
    )
    if beeline_distance > MAX_LOCAL_WALK_DISTANCE_METRES:
        raise HTTPException(
            status_code=422,
            detail=(
                "Origin and destination are too far apart for local walking routes. "
                "Check emulator location and destination."
            ),
        )

    try:
        route_candidates = await fetch_mapbox_route_candidates(
            origin_latitude=payload.origin.latitude,
            origin_longitude=payload.origin.longitude,
            destination_latitude=payload.destination.latitude,
            destination_longitude=payload.destination.longitude,
            alternatives=payload.alternatives,
        )
    except httpx.HTTPStatusError as exc:
        detail = "Route provider rejected this route request."
        try:
            payload_json = exc.response.json()
            if isinstance(payload_json, dict):
                detail = (
                    payload_json.get("message")
                    or payload_json.get("detail")
                    or detail
                )
        except Exception:
            detail = str(exc)

        raise HTTPException(
            status_code=exc.response.status_code,
            detail=detail,
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    score_payload = RouteScoreRequest(
        origin=payload.origin,
        destination=payload.destination,
        depart_at=payload.depart_at,
        bias_mode=payload.bias_mode,
        requirements=payload.requirements,
        preferences=payload.preferences,
        route_candidates=route_candidates,
    )

    return await enrich_and_score_routes(
        score_payload,
        db=db,
        crime_date=payload.crime_date,
        crime_category=payload.crime_category,
    )


@router.post("/reports/validate", response_model=SafetyReportValidationResponse)
async def validate_safety_report(
    payload: SafetyReportRequest,
) -> SafetyReportValidationResponse:
    result = validate_report(payload.model_dump())
    return SafetyReportValidationResponse(**result)
