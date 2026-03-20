import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.journey import Journey
from app.schemas.journeys import JourneyCreate, JourneyResponse

# Create a router instance for journey-related endpoints
router = APIRouter()


def _journey_to_response(journey: Journey, route_geojson: dict) -> JourneyResponse:
    """
    Helper function to convert a Journey database model into a JourneyResponse schema.

    Purpose:
    - Centralises transformation logic from DB model → API response.
    - Keeps route handlers cleaner and avoids duplication.

    Parameters:
    - journey: SQLAlchemy Journey model instance
    - route_geojson: Parsed GeoJSON representing the journey route

    Returns:
    - JourneyResponse object
    """
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
) -> JourneyResponse:
    """
    Create a new journey.

    Purpose:
    - Stores a user’s journey including origin, destination, score, and route geometry.
    - Converts incoming GeoJSON into a PostGIS geometry for storage.

    Request Body:
    - payload (JourneyCreate):
        Contains user_id, origin/destination labels, score, and route_geojson.

    Process:
    - Convert GeoJSON route into a PostGIS geometry using ST_GeomFromGeoJSON.
    - Assign SRID 4326 (WGS84 coordinate system).
    - Insert new Journey record into the database.
    - Commit and refresh to retrieve generated fields (e.g., ID, timestamps).

    Returns:
    - The created journey as a JourneyResponse.
    """

    # Convert GeoJSON into a PostGIS geometry with SRID 4326 (standard lat/lon)
    route_geometry = func.ST_SetSRID(
        func.ST_GeomFromGeoJSON(payload.route_geojson), 4326
    )

    # Create Journey ORM object
    journey = Journey(
        user_id=payload.user_id,
        origin_label=payload.origin_label,
        destination_label=payload.destination_label,
        score=payload.score,
        route_geometry=route_geometry,
    )

    # Persist to database
    db.add(journey)
    await db.commit()
    await db.refresh(journey)

    # Return response using original GeoJSON (no need to re-fetch)
    return _journey_to_response(journey, payload.route_geojson)


@router.get("/{journey_id}", response_model=JourneyResponse)
async def get_journey(
    journey_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> JourneyResponse:
    """
    Retrieve a journey by its ID.

    Purpose:
    - Fetch a single journey record along with its route geometry.
    - Converts stored PostGIS geometry back into GeoJSON for API response.

    Path Parameters:
    - journey_id:
        UUID of the journey to retrieve.

    Process:
    - Query the database for the journey.
    - Use ST_AsGeoJSON to convert geometry into GeoJSON string.
    - Parse GeoJSON string into Python dict.

    Errors:
    - Returns 404 if the journey does not exist.

    Returns:
    - JourneyResponse containing journey details and route geometry.
    """

    # Build query to fetch journey and convert geometry to GeoJSON
    stmt = select(
        Journey,
        func.ST_AsGeoJSON(Journey.route_geometry).label("route_geojson"),
    ).where(Journey.id == journey_id)

    # Execute query
    result = await db.execute(stmt)
    row = result.first()

    # Handle case where journey is not found
    if not row:
        raise HTTPException(status_code=404, detail="Journey not found")

    # Unpack result and parse GeoJSON string into dict
    journey, route_geojson = row

    return _journey_to_response(journey, json.loads(route_geojson))