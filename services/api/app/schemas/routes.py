from pydantic import BaseModel, Field


class RouteScoreRequest(BaseModel):
    """
    Schema for requesting a route safety score.

    Purpose:
    - Validates inputs used to calculate a safety score for a route.
    - Ensures all required metrics are within valid ranges.

    Fields:
    - distance_metres: Total route distance (must be > 0)
    - incident_density: Density of incidents along the route (>= 0)
    - lighting_score: Quality of lighting (0 to 1)
    - step_free_ratio: Accessibility metric (0 to 1)
    """

    # Total route distance in metres
    distance_metres: int = Field(gt=0)

    # Incident density (e.g., reports per unit distance)
    incident_density: float = Field(ge=0)

    # Lighting quality score (0 = poor, 1 = excellent)
    lighting_score: float = Field(ge=0, le=1)

    # Ratio of step-free accessibility (0 = none, 1 = fully accessible)
    step_free_ratio: float = Field(ge=0, le=1)


class RouteScoreResponse(BaseModel):
    """
    Schema representing the result of a route scoring operation.

    Purpose:
    - Returns a computed safety score along with explanation details.

    Fields:
    - score: Final computed safety score
    - explanation: List of factors contributing to the score
    """

    # Final safety score for the route
    score: float

    # Explanation of how the score was derived
    explanation: list[str]


class SafetyReportRequest(BaseModel):
    """
    Schema for validating a safety report before submission.

    Purpose:
    - Used for pre-validation or moderation checks.
    - Ensures required fields are present before processing.

    Fields:
    - category: Type of report
    - summary: Short description
    - description: Detailed description
    - latitude: Geographic latitude
    - longitude: Geographic longitude
    """

    # Category/type of the report
    category: str

    # Short summary of the report
    summary: str

    # Detailed description of the report
    description: str

    # Latitude coordinate
    latitude: float

    # Longitude coordinate
    longitude: float


class SafetyReportValidationResponse(BaseModel):
    """
    Schema representing the result of safety report validation.

    Purpose:
    - Indicates whether a report is accepted or flagged.
    - Provides moderation feedback.

    Fields:
    - accepted: Whether the report passed validation
    - moderation_flags: List of issues or flags (if any)
    """

    # Whether the report is accepted for further processing
    accepted: bool

    # List of moderation flags or issues (e.g., "spam", "incomplete")
    moderation_flags: list[str]