from datetime import datetime
from uuid import UUID, uuid4

from geoalchemy2 import Geometry
from sqlalchemy import DateTime, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TransportStop(Base):
    """
    Database model representing a transport stop.

    Purpose:
    - Stores locations where transport services stop (e.g., bus stops, train stations).
    - Supports spatial queries such as finding nearby stops.
    - Links to arrivals and services for transport tracking.
    """

    __tablename__ = "transport_stops"

    # Unique identifier for the transport stop
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # Name of the stop (e.g., "Central Station", "High Street Stop A")
    name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )

    # Unique stop code (e.g., official identifier from transport authority)
    # - Must be unique across all stops
    stop_code: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
    )

    # Mode of transport served at this stop (e.g., "bus", "train", "tram")
    # - Useful for filtering and categorisation
    mode: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )

    # Geographic location of the stop (PostGIS POINT)
    # - Stored as longitude/latitude
    # - SRID 4326: standard WGS84 coordinate system
    location: Mapped[str] = mapped_column(
        Geometry("POINT", srid=4326),
        nullable=False,
    )

    # Timestamp when the stop was created
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )