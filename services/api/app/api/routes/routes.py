from fastapi import APIRouter

from app.schemas.routes import (
    RouteScoreRequest,
    RouteScoreResponse,
    SafetyReportRequest,
    SafetyReportValidationResponse,
)
from app.services.route_scoring import score_route_request
from app.services.safety_reports import validate_report

router = APIRouter()


@router.post("/score", response_model=RouteScoreResponse)
async def score_candidate_route(payload: RouteScoreRequest) -> RouteScoreResponse:
    return score_route_request(payload)


@router.post("/reports/validate", response_model=SafetyReportValidationResponse)
async def validate_safety_report(
    payload: SafetyReportRequest,
) -> SafetyReportValidationResponse:
    result = validate_report(payload.model_dump())
    return SafetyReportValidationResponse(**result)
