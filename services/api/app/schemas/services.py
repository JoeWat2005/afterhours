from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class ServiceCategory(str, Enum):
    hospital = "hospital"
    police = "police"
    fire_station = "fire_station"
    ambulance = "ambulance"


class NearbyService(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    category: ServiceCategory
    address: str | None = None
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    distance_metres: int = Field(ge=0)
    source: str = "seed"


class NearbyServicesResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[NearbyService]
