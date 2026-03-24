from fastapi import APIRouter, Depends, HTTPException, Query, status
from geoalchemy2.shape import to_shape
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.report import SafetyReport
from app.models.user import AppUser
from app.schemas.reports import (
    NearbyReportsResponse,
    SafetyReportCreate,
    SafetyReportResponse,
)
from app.services.route_safety import list_nearby_reports

router = APIRouter()


def _report_to_response(report: SafetyReport) -> SafetyReportResponse:
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
    user = await db.get(AppUser, payload.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

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

    db.add(report)
    await db.commit()
    await db.refresh(report)

    return _report_to_response(report)


@router.get("/nearby", response_model=NearbyReportsResponse)
async def nearby_reports(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    radius_metres: int = Query(1000, gt=0, le=10000),
    limit: int = Query(20, gt=0, le=100),
    db: AsyncSession = Depends(get_db),
) -> NearbyReportsResponse:
    items = await list_nearby_reports(
        db,
        latitude=latitude,
        longitude=longitude,
        radius_metres=radius_metres,
        limit=limit,
    )

    return NearbyReportsResponse(
        items=[_report_to_response(item) for item in items]
    )