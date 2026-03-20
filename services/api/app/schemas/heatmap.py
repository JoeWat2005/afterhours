from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class HeatmapCellResponse(BaseModel):
    """
    Schema representing a single heatmap cell in API responses.

    Purpose:
    - Encapsulates risk data for a geographic area.
    - Used to render heatmaps on the frontend (e.g., map overlays).

    Fields:
    - id: Unique identifier of the heatmap cell
    - risk_score: Calculated risk level for the area
    - source_count: Number of data points contributing to the score
    - cell_geojson: GeoJSON representation of the cell polygon
    - updated_at: Timestamp of last update
    """

    # Unique identifier for the heatmap cell
    id: UUID

    # Risk score for this cell (higher = more risky)
    risk_score: float

    # Number of sources contributing to the score
    source_count: int

    # GeoJSON representation of the polygon geometry
    # - Typically used directly by frontend mapping libraries
    cell_geojson: dict

    # Timestamp when this cell was last updated
    updated_at: datetime


class HeatmapResponse(BaseModel):
    """
    Schema representing a collection of heatmap cells.

    Purpose:
    - Wraps multiple HeatmapCellResponse objects.
    - Provides a consistent API response format.

    Fields:
    - items: List of heatmap cells
    """

    # List of heatmap cell responses
    items: list[HeatmapCellResponse]