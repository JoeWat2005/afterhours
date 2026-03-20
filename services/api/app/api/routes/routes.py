from fastapi import APIRouter

from app.schemas.routes import (
    RouteScoreRequest,
    RouteScoreResponse,
    SafetyReportRequest,
    SafetyReportValidationResponse,
)
from app.services.route_scoring import score_route
from app.services.safety_reports import validate_report

# Create a router instance for route scoring and safety validation endpoints
router = APIRouter()


@router.post("/score", response_model=RouteScoreResponse)
async def score_candidate_route(payload: RouteScoreRequest) -> RouteScoreResponse:
    """
    Score a candidate route based on safety factors.

    Purpose:
    - Evaluates a proposed route and assigns a safety score.
    - Provides an explanation of how the score was determined.

    Request Body:
    - payload (RouteScoreRequest):
        Contains route data (e.g., coordinates, segments, or features).

    Process:
    - Convert the request payload into a dictionary.
    - Pass it to the route scoring service.
    - Receive a numerical score and explanation.

    Returns:
    - RouteScoreResponse containing:
        - score: numeric safety score
        - explanation: breakdown or reasoning behind the score
    """

    # Call service layer to compute route score
    score, explanation = score_route(payload.model_dump())

    # Return structured response
    return RouteScoreResponse(score=score, explanation=explanation)


@router.post("/reports/validate", response_model=SafetyReportValidationResponse)
async def validate_safety_report(
    payload: SafetyReportRequest,
) -> SafetyReportValidationResponse:
    """
    Validate a safety report before submission or processing.

    Purpose:
    - Checks whether a safety report is valid and meets required criteria.
    - Can be used for moderation, spam detection, or data quality checks.

    Request Body:
    - payload (SafetyReportRequest):
        Contains report data (e.g., category, description, location).

    Process:
    - Convert payload into a dictionary.
    - Pass it to the validation service.
    - Receive validation results (e.g., valid/invalid, reasons).

    Returns:
    - SafetyReportValidationResponse containing validation outcome and details.
    """

    # Call service layer to validate the report
    result = validate_report(payload.model_dump())

    # Return response by unpacking result dictionary
    return SafetyReportValidationResponse(**result)