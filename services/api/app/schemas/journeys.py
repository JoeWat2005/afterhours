from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class JourneyCreate(BaseModel):
    """
    Schema for creating a new journey.

    Purpose:
    - Validates incoming data when a client submits a journey.
    - Ensures required fields and constraints are enforced.

    Fields:
    - user_id: Optional user associated with the journey
    - origin_label: Human-readable starting point (1–128 chars)
    - destination_label: Human-readable destination (1–128 chars)
    - score: Safety score assigned to the route
    - route_geojson: GeoJSON representation of the route path
    """

    # Optional user ID (can be anonymous journeys)
    user_id: UUID | None = None

    # Starting location label (validated length)
    origin_label: str = Field(min_length=1, max_length=128)

    # Destination label (validated length)
    destination_label: str = Field(min_length=1, max_length=128)

    # Safety score for the journey
    score: float

    # GeoJSON representing the route geometry
    route_geojson: dict


class JourneyResponse(BaseModel):
    """
    Schema representing a journey returned in API responses.

    Purpose:
    - Standardises how journey data is returned to clients.
    - Supports ORM-to-schema conversion using from_attributes.

    Fields:
    - id: Unique journey identifier
    - user_id: Associated user (if any)
    - origin_label: Starting location label
    - destination_label: Destination label
    - score: Safety score
    - route_geojson: Route geometry in GeoJSON format
    - created_at: Timestamp of creation
    """

    # Enable compatibility with ORM objects (e.g., SQLAlchemy models)
    model_config = ConfigDict(from_attributes=True)

    # Unique identifier for the journey
    id: UUID

    # Optional associated user
    user_id: UUID | None

    # Starting location label
    origin_label: str

    # Destination label
    destination_label: str

    # Safety score
    score: float

    # GeoJSON representation of the route
    route_geojson: dict

    # Timestamp when the journey was created
    created_at: datetime