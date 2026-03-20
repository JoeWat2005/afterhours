from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PlaceCreate(BaseModel):
    """
    Schema for creating a new place.

    Purpose:
    - Validates incoming data when adding a new place.
    - Ensures required fields and geographic constraints are enforced.

    Fields:
    - name: Name of the place (1–128 chars)
    - category: Category/type of place (1–64 chars)
    - latitude: Geographic latitude (-90 to 90)
    - longitude: Geographic longitude (-180 to 180)
    - is_open_late: Whether the place operates late hours
    """

    # Name of the place
    name: str = Field(min_length=1, max_length=128)

    # Category/type (e.g., "cafe", "bar", "station")
    category: str = Field(min_length=1, max_length=64)

    # Latitude coordinate (validated range)
    latitude: float = Field(ge=-90, le=90)

    # Longitude coordinate (validated range)
    longitude: float = Field(ge=-180, le=180)

    # Indicates if the place is open late
    is_open_late: bool = False


class PlaceResponse(BaseModel):
    """
    Schema representing a place in API responses.

    Purpose:
    - Standardises how place data is returned to clients.
    - Supports ORM-to-schema conversion.

    Fields:
    - id: Unique identifier
    - name: Place name
    - category: Place category
    - latitude: Latitude coordinate
    - longitude: Longitude coordinate
    - is_open_late: Late opening flag
    - created_at: Timestamp of creation
    """

    # Enable ORM compatibility (e.g., SQLAlchemy models)
    model_config = ConfigDict(from_attributes=True)

    # Unique identifier for the place
    id: UUID

    # Name of the place
    name: str

    # Category/type of place
    category: str

    # Latitude coordinate
    latitude: float

    # Longitude coordinate
    longitude: float

    # Whether the place is open late
    is_open_late: bool

    # Timestamp when the place was created
    created_at: datetime


class NearbyPlacesResponse(BaseModel):
    """
    Schema representing a collection of nearby places.

    Purpose:
    - Wraps multiple PlaceResponse objects.
    - Used for endpoints that return nearby search results.

    Fields:
    - items: List of nearby places
    """

    # List of nearby places
    items: list[PlaceResponse]