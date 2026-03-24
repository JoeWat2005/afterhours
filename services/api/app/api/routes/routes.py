from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.routes import (
    RouteScoreRequest,
    RouteScoreResponse,
    SafetyReportRequest,
    SafetyReportValidationResponse,
)
from app.services.route_candidate_enricher import enrich_and_score_routes
from app.services.safety_reports import validate_report

router = APIRouter()


@router.post("/score", response_model=RouteScoreResponse)
async def score_candidate_route(
    payload: RouteScoreRequest,
    db: AsyncSession = Depends(get_db),
) -> RouteScoreResponse:
    return await enrich_and_score_routes(payload, db=db)


@router.post("/reports/validate", response_model=SafetyReportValidationResponse)
async def validate_safety_report(
    payload: SafetyReportRequest,
) -> SafetyReportValidationResponse:
    result = validate_report(payload.model_dump())
    return SafetyReportValidationResponse(**result)
