from pydantic import BaseModel, Field


class HeatmapCellBounds(BaseModel):
    min_latitude: float
    min_longitude: float
    max_latitude: float
    max_longitude: float


class HeatmapCellResponse(BaseModel):
    cell_id: str
    center_latitude: float
    center_longitude: float
    risk_score: float
    source_count: int
    bounds: HeatmapCellBounds


class CrimePinResponse(BaseModel):
    crime_id: str
    category: str
    month: str
    latitude: float
    longitude: float
    location_label: str | None = None


class HeatmapResponse(BaseModel):
    latitude: float
    longitude: float
    radius_metres: int
    cell_size_metres: int
    category: str
    date: str | None = Field(default=None)
    items: list[HeatmapCellResponse]
    crime_pins: list[CrimePinResponse] = Field(default_factory=list)
