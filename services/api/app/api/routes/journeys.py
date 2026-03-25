import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps.auth import get_current_app_user
from app.db.session import get_db
from app.models.journey import Journey
from app.models.user import AppUser
from app.schemas.journeys import JourneyCreate, JourneyResponse

router = APIRouter()


def _journey_to_response(journey: Journey, route_geojson: dict) -> JourneyResponse:
    return JourneyResponse(
        id=journey.id,
        user_id=journey.user_id,
        origin_label=journey.origin_label,
        destination_label=journey.destination_label,
        score=journey.score,
        route_geojson=route_geojson,
        created_at=journey.created_at,
    )


@router.post("", response_model=JourneyResponse, status_code=status.HTTP_201_CREATED)
async def create_journey(
    payload: JourneyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: AppUser = Depends(get_current_app_user),
) -> JourneyResponse:
    if payload.user_id is not None and payload.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token subject does not match journey user_id",
        )

    resolved_route_geojson = payload.resolved_route_geojson()
    resolved_score = payload.resolved_score()

    route_geometry = func.ST_SetSRID(
        func.ST_GeomFromGeoJSON(json.dumps(resolved_route_geojson)),
        4326,
    )

    journey = Journey(
        user_id=current_user.id,
        origin_label=payload.origin_label,
        destination_label=payload.destination_label,
        score=resolved_score,
        route_geometry=route_geometry,
    )

    db.add(journey)
    await db.commit()
    await db.refresh(journey)

    return _journey_to_response(journey, resolved_route_geojson)


@router.get("/{journey_id}", response_model=JourneyResponse)
async def get_journey(
    journey_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: AppUser = Depends(get_current_app_user),
) -> JourneyResponse:
    stmt = select(
        Journey,
        func.ST_AsGeoJSON(Journey.route_geometry).label("route_geojson"),
    ).where(Journey.id == journey_id)

    result = await db.execute(stmt)
    row = result.first()

    if not row:
        raise HTTPException(status_code=404, detail="Journey not found")

    journey, route_geojson = row
    if journey.user_id and journey.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this journey",
        )

    return _journey_to_response(journey, json.loads(route_geojson))
