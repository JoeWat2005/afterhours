from pydantic import BaseModel, Field


class LonLat(BaseModel):
    """
    Schema representing a geographic coordinate (longitude, latitude).

    Purpose:
    - Standardises how coordinates are passed and validated across the API.
    - Ensures values fall within valid geographic ranges.

    Fields:
    - longitude:
        Must be between -180 and 180 degrees.
    - latitude:
        Must be between -90 and 90 degrees.
    """

    # Longitude value (east-west position)
    # - Valid range: -180 to 180
    longitude: float = Field(
        ge=-180,
        le=180,
    )

    # Latitude value (north-south position)
    # - Valid range: -90 to 90
    latitude: float = Field(
        ge=-90,
        le=90,
    )