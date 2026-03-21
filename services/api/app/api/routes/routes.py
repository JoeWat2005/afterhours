from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.services.route_scoring import score_route
from app.services.safety_reports import validate_report

router = APIRouter()


class RouteScoreRequest(BaseModel):
    distance_metres: int = Field(gt=0)
    incident_density: float = Field(ge=0)
    lighting_score: float = Field(ge=0, le=1)
    step_free_ratio: float = Field(ge=0, le=1)


class RouteScoreResponse(BaseModel):
    score: float
    explanation: list[str]


class SafetyReportRequest(BaseModel):
    category: str
    summary: str
    description: str
    latitude: float
    longitude: float


class SafetyReportValidationResponse(BaseModel):
    accepted: bool
    moderation_flags: list[str]


@router.post("/score", response_model=RouteScoreResponse)
async def score_candidate_route(payload: RouteScoreRequest) -> RouteScoreResponse:
    score, explanation = score_route(payload.model_dump())
    return RouteScoreResponse(score=score, explanation=explanation)


@router.post("/reports/validate", response_model=SafetyReportValidationResponse)
async def validate_safety_report(payload: SafetyReportRequest) -> SafetyReportValidationResponse:
    result = validate_report(payload.model_dump())
    return SafetyReportValidationResponse(**result)
