from fastapi import APIRouter, Depends, Query, status
from geoalchemy2.shape import to_shape
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.place import Place
from app.schemas.places import NearbyPlacesResponse, PlaceCreate, PlaceResponse

# Create a router instance for place-related endpoints
router = APIRouter()


def _place_to_response(place: Place) -> PlaceResponse:
    """
    Helper function to convert a Place ORM model into a PlaceResponse schema.

    Purpose:
    - Transforms database geometry (PostGIS) into latitude/longitude values.
    - Keeps route handlers clean and avoids repeated transformation logic.

    Process:
    - Convert PostGIS geometry into a Shapely point using geoalchemy2.
    - Extract latitude (y) and longitude (x).

    Returns:
    - PlaceResponse object
    """
    point = to_shape(place.location)

    return PlaceResponse(
        id=place.id,
        name=place.name,
        category=place.category,
        latitude=point.y,
        longitude=point.x,
        is_open_late=place.is_open_late,
        created_at=place.created_at,
    )


@router.post("", response_model=PlaceResponse, status_code=status.HTTP_201_CREATED)
async def create_place(payload: PlaceCreate, db: AsyncSession = Depends(get_db)) -> PlaceResponse:
    """
    Create a new place.

    Purpose:
    - Stores a location (e.g., venue, point of interest) in the database.
    - Converts latitude/longitude into a PostGIS geometry.

    Request Body:
    - payload (PlaceCreate):
        Contains name, category, latitude, longitude, and open-late flag.

    Process:
    - Create a geographic point using ST_MakePoint (longitude, latitude).
    - Assign SRID 4326 (WGS84 coordinate system).
    - Insert the place into the database.
    - Refresh to retrieve generated fields (e.g., ID, timestamps).

    Returns:
    - The created place as a PlaceResponse.
    """

    # Create Place ORM object with PostGIS geometry
    place = Place(
        name=payload.name,
        category=payload.category,
        location=func.ST_SetSRID(
            func.ST_MakePoint(payload.longitude, payload.latitude), 4326
        ),
        is_open_late=payload.is_open_late,
    )

    # Persist to database
    db.add(place)
    await db.commit()
    await db.refresh(place)

    # Convert to response format
    return _place_to_response(place)


@router.get("/nearby", response_model=NearbyPlacesResponse)
async def nearby_places(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    radius_metres: int = Query(1000, gt=0, le=10000),
    open_late_only: bool = False,
    limit: int = Query(20, gt=0, le=100),
    db: AsyncSession = Depends(get_db),
) -> NearbyPlacesResponse:
    """
    Retrieve nearby places based on a geographic point.

    Purpose:
    - Finds places within a specified radius of a given location.
    - Supports filtering for places that are open late.
    - Orders results by distance (closest first).

    Query Parameters:
    - latitude:
        Latitude of the search origin (-90 to 90).
    - longitude:
        Longitude of the search origin (-180 to 180).
    - radius_metres:
        Search radius in metres (default: 1000, max: 10000).
    - open_late_only:
        If True, only return places that are open late.
    - limit:
        Maximum number of results (default: 20, max: 100).

    Process:
    - Create a geographic point from input coordinates.
    - Use ST_DWithin to filter places within the radius.
    - Optionally filter by is_open_late.
    - Order results by distance using ST_Distance.
    - Limit number of results.

    Returns:
    - NearbyPlacesResponse containing a list of nearby places.
    """

    # Create origin point (longitude, latitude) with SRID 4326
    origin = func.ST_SetSRID(func.ST_MakePoint(longitude, latitude), 4326)

    # Base query: find places within radius using geography (accurate distance in metres)
    stmt = select(Place).where(
        func.ST_DWithin(
            func.Geography(Place.location),
            func.Geography(origin),
            radius_metres,
        )
    )

    # Optional filter: only include places open late
    if open_late_only:
        stmt = stmt.where(Place.is_open_late.is_(True))

    # Order by distance (nearest first) and limit results
    stmt = stmt.order_by(
        func.ST_Distance(
            func.Geography(Place.location),
            func.Geography(origin),
        )
    ).limit(limit)

    # Execute query
    result = await db.execute(stmt)
    items = result.scalars().all()

    # Convert ORM models to response schemas
    return NearbyPlacesResponse(
        items=[_place_to_response(item) for item in items]
    )