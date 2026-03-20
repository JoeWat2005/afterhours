from fastapi import APIRouter, Depends, HTTPException, Query, status
from geoalchemy2.shape import to_shape
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.report import SafetyReport
from app.models.user import AppUser
from app.schemas.reports import (
    NearbyReportsResponse,
    SafetyReportCreate,
    SafetyReportResponse,
)

# Create a router instance for safety report endpoints
router = APIRouter()


def _report_to_response(report: SafetyReport) -> SafetyReportResponse:
    """
    Helper function to convert a SafetyReport ORM model into a SafetyReportResponse schema.

    Purpose:
    - Transforms PostGIS geometry into latitude/longitude values.
    - Keeps route handlers clean and avoids repeated transformation logic.

    Process:
    - Convert geometry to a Shapely point using geoalchemy2.
    - Extract latitude (y) and longitude (x).

    Returns:
    - SafetyReportResponse object
    """
    point = to_shape(report.location)

    return SafetyReportResponse(
        id=report.id,
        user_id=report.user_id,
        category=report.category,
        summary=report.summary,
        details=report.details,
        latitude=point.y,
        longitude=point.x,
        created_at=report.created_at,
    )


@router.post("", response_model=SafetyReportResponse, status_code=status.HTTP_201_CREATED)
async def create_report(
    payload: SafetyReportCreate,
    db: AsyncSession = Depends(get_db),
) -> SafetyReportResponse:
    """
    Create a new safety report.

    Purpose:
    - Allows users to report safety-related incidents (e.g., hazards, suspicious activity).
    - Stores report details along with geographic location.

    Request Body:
    - payload (SafetyReportCreate):
        Contains user_id, category, summary, details, latitude, and longitude.

    Process:
    - Validate that the user exists.
    - Convert latitude/longitude into a PostGIS geometry.
    - Insert the report into the database.
    - Refresh to retrieve generated fields.

    Errors:
    - 404 if the user does not exist.

    Returns:
    - The created safety report as a SafetyReportResponse.
    """

    # Ensure the user submitting the report exists
    user = await db.get(AppUser, payload.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Create SafetyReport ORM object with geographic location
    report = SafetyReport(
        user_id=payload.user_id,
        category=payload.category,
        summary=payload.summary,
        details=payload.details,
        location=func.ST_SetSRID(
            func.ST_MakePoint(payload.longitude, payload.latitude),
            4326,
        ),
    )

    # Persist to database
    db.add(report)
    await db.commit()
    await db.refresh(report)

    # Convert to response format
    return _report_to_response(report)


@router.get("/nearby", response_model=NearbyReportsResponse)
async def nearby_reports(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    radius_metres: int = Query(1000, gt=0, le=10000),
    limit: int = Query(20, gt=0, le=100),
    db: AsyncSession = Depends(get_db),
) -> NearbyReportsResponse:
    """
    Retrieve nearby safety reports based on a geographic location.

    Purpose:
    - Finds safety reports within a specified radius of a given point.
    - Orders results by proximity (closest first).

    Query Parameters:
    - latitude:
        Latitude of the search origin (-90 to 90).
    - longitude:
        Longitude of the search origin (-180 to 180).
    - radius_metres:
        Search radius in metres (default: 1000, max: 10000).
    - limit:
        Maximum number of results (default: 20, max: 100).

    Process:
    - Create a geographic origin point.
    - Use ST_DWithin to filter reports within radius.
    - Order results by distance using ST_Distance.
    - Limit number of results.

    Returns:
    - NearbyReportsResponse containing a list of nearby safety reports.
    """

    # Create origin point (longitude, latitude) with SRID 4326
    origin = func.ST_SetSRID(func.ST_MakePoint(longitude, latitude), 4326)

    # Build query:
    # - Filter reports within radius using ST_DWithin
    # - Order by distance (nearest first)
    # - Limit results
    stmt = (
        select(SafetyReport)
        .where(
            func.ST_DWithin(
                func.Geography(SafetyReport.location),
                func.Geography(origin),
                radius_metres,
            )
        )
        .order_by(
            func.ST_Distance(
                func.Geography(SafetyReport.location),
                func.Geography(origin),
            )
        )
        .limit(limit)
    )

    # Execute query
    result = await db.execute(stmt)
    items = result.scalars().all()

    # Convert ORM models to response schemas
    return NearbyReportsResponse(
        items=[_report_to_response(item) for item in items]
    )