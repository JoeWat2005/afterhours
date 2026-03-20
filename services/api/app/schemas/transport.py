from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TransportStopCreate(BaseModel):
    """
    Schema for creating a transport stop.

    Purpose:
    - Validates incoming data when adding a new stop.
    - Ensures correct formatting and coordinate ranges.

    Fields:
    - name: Stop name (1–128 chars)
    - stop_code: Unique identifier for the stop (1–64 chars)
    - mode: Transport mode (e.g., bus, train)
    - latitude: Geographic latitude (-90 to 90)
    - longitude: Geographic longitude (-180 to 180)
    """

    name: str = Field(min_length=1, max_length=128)
    stop_code: str = Field(min_length=1, max_length=64)
    mode: str = Field(min_length=1, max_length=32)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class TransportStopResponse(BaseModel):
    """
    Schema representing a transport stop in API responses.

    Purpose:
    - Standardises how stop data is returned to clients.
    - Supports ORM-to-schema conversion.

    Fields:
    - id: Unique stop ID
    - name: Stop name
    - stop_code: Unique stop code
    - mode: Transport mode
    - latitude/longitude: Coordinates
    - created_at: Timestamp of creation
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    stop_code: str
    mode: str
    latitude: float
    longitude: float
    created_at: datetime


class TransportServiceCreate(BaseModel):
    """
    Schema for creating a transport service.

    Purpose:
    - Validates service data such as route/line information.

    Fields:
    - service_name: Name of the service (1–128 chars)
    - mode: Transport mode (e.g., bus, train)
    - operator_name: Optional operator name
    - active_hours: Optional service hours
    """

    service_name: str = Field(min_length=1, max_length=128)
    mode: str = Field(min_length=1, max_length=32)
    operator_name: str | None = None
    active_hours: str | None = None


class TransportServiceResponse(BaseModel):
    """
    Schema representing a transport service in API responses.

    Purpose:
    - Standardises how service data is returned.
    - Supports ORM-to-schema conversion.

    Fields:
    - id: Service ID
    - service_name: Name of the service
    - mode: Transport mode
    - operator_name: Optional operator
    - active_hours: Optional hours
    - created_at: Timestamp
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    service_name: str
    mode: str
    operator_name: str | None
    active_hours: str | None
    created_at: datetime


class TransportArrivalCreate(BaseModel):
    """
    Schema for creating a transport arrival record.

    Purpose:
    - Validates incoming arrival data for a stop/service.

    Fields:
    - stop_id: Associated stop
    - service_id: Associated service
    - expected_at: Expected arrival time
    - status: Arrival status (1–32 chars)
    """

    stop_id: UUID
    service_id: UUID
    expected_at: datetime
    status: str = Field(min_length=1, max_length=32)


class TransportArrivalResponse(BaseModel):
    """
    Schema representing a transport arrival in API responses.

    Purpose:
    - Standardises how arrival data is returned.
    - Supports ORM-to-schema conversion.

    Fields:
    - id: Arrival ID
    - stop_id: Associated stop
    - service_id: Associated service
    - expected_at: Expected arrival time
    - status: Arrival status
    - created_at: Timestamp
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    stop_id: UUID
    service_id: UUID
    expected_at: datetime
    status: str
    created_at: datetime


class NearbyStopsResponse(BaseModel):
    """
    Schema representing nearby transport stops.

    Purpose:
    - Wraps a list of nearby stops for API responses.

    Fields:
    - items: List of TransportStopResponse
    """

    items: list[TransportStopResponse]


class StopArrivalsResponse(BaseModel):
    """
    Schema representing arrivals for a specific stop.

    Purpose:
    - Wraps a list of arrival records.
    - Used for endpoints returning stop-specific arrivals.

    Fields:
    - items: List of TransportArrivalResponse
    """

    items: list[TransportArrivalResponse]