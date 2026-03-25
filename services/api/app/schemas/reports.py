from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.core.route_risk_config import ReportSeverity


class SafetyReportCreate(BaseModel):
    """
    Schema for creating a new safety report.

    Purpose:
    - Validates incoming user-submitted safety reports.
    - Ensures proper formatting and constraints for text and coordinates.

    Fields:
    - user_id: ID of the user submitting the report
    - category: Type of report (1–64 chars)
    - summary: Short description (1–280 chars)
    - details: Detailed description (1–2000 chars)
    - latitude: Geographic latitude (-90 to 90)
    - longitude: Geographic longitude (-180 to 180)
    """

    # ID of the user submitting the report
    user_id: UUID

    # User-facing category for the submitted report
    category: str = Field(min_length=1, max_length=64)

    # Short summary of the issue
    summary: str = Field(min_length=1, max_length=280)

    # Detailed description of the issue
    details: str = Field(min_length=1, max_length=2000)

    # Latitude coordinate (validated range)
    latitude: float = Field(ge=-90, le=90)

    # Longitude coordinate (validated range)
    longitude: float = Field(ge=-180, le=180)


class SafetyReportResponse(BaseModel):
    """
    Schema representing a safety report in API responses.

    Purpose:
    - Standardises how safety reports are returned to clients.
    - Supports ORM-to-schema conversion.

    Fields:
    - id: Unique report identifier
    - user_id: User who submitted the report
    - category: Report category
    - summary: Short description
    - details: Full description
    - latitude: Latitude coordinate
    - longitude: Longitude coordinate
    - created_at: Timestamp of creation
    """

    # Enable ORM compatibility (e.g., SQLAlchemy models)
    model_config = ConfigDict(from_attributes=True)

    # Unique identifier for the report
    id: UUID

    # User who submitted the report
    user_id: UUID

    # User-facing report category
    category: str

    # Severity level worked out from the category
    severity: ReportSeverity

    # Short summary
    summary: str

    # Detailed description
    details: str

    # Latitude coordinate
    latitude: float

    # Longitude coordinate
    longitude: float

    # Timestamp when the report was created
    created_at: datetime


class NearbyReportsResponse(BaseModel):
    """
    Schema representing a collection of nearby safety reports.

    Purpose:
    - Wraps multiple SafetyReportResponse objects.
    - Used for endpoints returning geographically filtered reports.

    Fields:
    - items: List of nearby safety reports
    """

    # List of nearby safety reports
    items: list[SafetyReportResponse]
