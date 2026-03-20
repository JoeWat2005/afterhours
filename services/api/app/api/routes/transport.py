from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from geoalchemy2.shape import to_shape
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.transport_arrival import TransportArrival
from app.models.transport_service import TransportService
from app.models.transport_stop import TransportStop
from app.schemas.transport import (
    NearbyStopsResponse,
    StopArrivalsResponse,
    TransportArrivalCreate,
    TransportArrivalResponse,
    TransportServiceCreate,
    TransportServiceResponse,
    TransportStopCreate,
    TransportStopResponse,
)

# Create a router instance for transport-related endpoints
router = APIRouter()


def _stop_to_response(stop: TransportStop) -> TransportStopResponse:
    """
    Helper function to convert a TransportStop ORM model into a response schema.

    Purpose:
    - Converts PostGIS geometry into latitude/longitude.
    - Keeps route handlers clean and reusable.

    Returns:
    - TransportStopResponse object
    """
    point = to_shape(stop.location)

    return TransportStopResponse(
        id=stop.id,
        name=stop.name,
        stop_code=stop.stop_code,
        mode=stop.mode,
        latitude=point.y,
        longitude=point.x,
        created_at=stop.created_at,
    )


def _arrival_to_response(arrival: TransportArrival) -> TransportArrivalResponse:
    """
    Helper function to convert a TransportArrival ORM model into a response schema.

    Purpose:
    - Standardises how arrival data is returned to clients.

    Returns:
    - TransportArrivalResponse object
    """
    return TransportArrivalResponse(
        id=arrival.id,
        stop_id=arrival.stop_id,
        service_id=arrival.service_id,
        expected_at=arrival.expected_at,
        status=arrival.status,
        created_at=arrival.created_at,
    )


@router.post("/stops", response_model=TransportStopResponse, status_code=status.HTTP_201_CREATED)
async def create_stop(
    payload: TransportStopCreate,
    db: AsyncSession = Depends(get_db),
) -> TransportStopResponse:
    """
    Create a new transport stop.

    Purpose:
    - Stores a transport stop (e.g., bus stop, train station) with location data.

    Request Body:
    - payload (TransportStopCreate):
        Contains name, stop_code, mode (bus/train/etc), latitude, longitude.

    Process:
    - Convert latitude/longitude into PostGIS geometry.
    - Insert stop into database.
    - Refresh to retrieve generated fields.

    Returns:
    - The created stop as a TransportStopResponse.
    """

    # Create TransportStop ORM object with geographic location
    stop = TransportStop(
        name=payload.name,
        stop_code=payload.stop_code,
        mode=payload.mode,
        location=func.ST_SetSRID(
            func.ST_MakePoint(payload.longitude, payload.latitude), 4326
        ),
    )

    # Persist to database
    db.add(stop)
    await db.commit()
    await db.refresh(stop)

    # Convert to response format
    return _stop_to_response(stop)


@router.get("/stops/nearby", response_model=NearbyStopsResponse)
async def nearby_stops(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    radius_metres: int = Query(1000, gt=0, le=10000),
    mode: str | None = None,
    limit: int = Query(20, gt=0, le=100),
    db: AsyncSession = Depends(get_db),
) -> NearbyStopsResponse:
    """
    Retrieve nearby transport stops based on a geographic location.

    Purpose:
    - Finds stops within a specified radius.
    - Optionally filters by transport mode (e.g., bus, train).
    - Orders results by proximity.

    Query Parameters:
    - latitude, longitude: origin point
    - radius_metres: search radius (default 1000m)
    - mode: optional filter (e.g., "bus")
    - limit: max results

    Returns:
    - NearbyStopsResponse with list of nearby stops.
    """

    # Create origin point
    origin = func.ST_SetSRID(func.ST_MakePoint(longitude, latitude), 4326)

    # Base query: stops within radius
    stmt = select(TransportStop).where(
        func.ST_DWithin(
            func.Geography(TransportStop.location),
            func.Geography(origin),
            radius_metres,
        )
    )

    # Optional filter by transport mode
    if mode:
        stmt = stmt.where(TransportStop.mode == mode)

    # Order by distance and limit results
    stmt = stmt.order_by(
        func.ST_Distance(
            func.Geography(TransportStop.location),
            func.Geography(origin),
        )
    ).limit(limit)

    # Execute query
    result = await db.execute(stmt)
    items = result.scalars().all()

    return NearbyStopsResponse(
        items=[_stop_to_response(item) for item in items]
    )


@router.post("/services", response_model=TransportServiceResponse, status_code=status.HTTP_201_CREATED)
async def create_service(
    payload: TransportServiceCreate,
    db: AsyncSession = Depends(get_db),
) -> TransportServiceResponse:
    """
    Create a new transport service.

    Purpose:
    - Stores service information (e.g., bus route, train line).

    Request Body:
    - payload (TransportServiceCreate):
        Contains service details (e.g., name, line, operator).

    Returns:
    - The created service as a TransportServiceResponse.
    """

    # Create and persist service
    service = TransportService(**payload.model_dump())
    db.add(service)
    await db.commit()
    await db.refresh(service)

    return TransportServiceResponse.model_validate(service)


@router.post("/arrivals", response_model=TransportArrivalResponse, status_code=status.HTTP_201_CREATED)
async def create_arrival(
    payload: TransportArrivalCreate,
    db: AsyncSession = Depends(get_db),
) -> TransportArrivalResponse:
    """
    Create a new transport arrival record.

    Purpose:
    - Stores expected arrival times for services at stops.

    Request Body:
    - payload (TransportArrivalCreate):
        Contains stop_id, service_id, expected arrival time, status.

    Returns:
    - The created arrival as a TransportArrivalResponse.
    """

    # Create and persist arrival
    arrival = TransportArrival(**payload.model_dump())
    db.add(arrival)
    await db.commit()
    await db.refresh(arrival)

    return _arrival_to_response(arrival)


@router.get("/stops/{stop_id}/arrivals", response_model=StopArrivalsResponse)
async def get_stop_arrivals(
    stop_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> StopArrivalsResponse:
    """
    Retrieve all arrivals for a specific transport stop.

    Purpose:
    - Provides upcoming arrivals for a given stop.
    - Useful for real-time transport displays.

    Path Parameters:
    - stop_id:
        UUID of the transport stop.

    Process:
    - Query arrivals by stop_id.
    - Order by expected arrival time (soonest first).

    Returns:
    - StopArrivalsResponse with list of arrivals.
    """

    # Query arrivals for the stop, ordered by time
    stmt = (
        select(TransportArrival)
        .where(TransportArrival.stop_id == stop_id)
        .order_by(TransportArrival.expected_at.asc())
    )

    result = await db.execute(stmt)
    items = result.scalars().all()

    return StopArrivalsResponse(
        items=[_arrival_to_response(item) for item in items]
    )