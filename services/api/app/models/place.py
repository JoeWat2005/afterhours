from datetime import datetime
from uuid import UUID, uuid4

from geoalchemy2 import Geometry
from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Place(Base):
    """
    Database model representing a place or point of interest.

    Purpose:
    - Stores locations such as venues, businesses, or landmarks.
    - Supports spatial queries (e.g., nearby search).
    - Can be used for features like recommendations or safety-aware routing.
    """

    __tablename__ = "places"

    # Unique identifier for the place
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # Name of the place (e.g., "Central Cafe", "Main Station")
    name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )

    # Category of the place (e.g., "cafe", "bar", "station")
    # - Useful for filtering and grouping
    category: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    # Geographic location of the place (PostGIS POINT)
    # - Stored as longitude/latitude
    # - SRID 4326: standard WGS84 coordinate system
    location: Mapped[str] = mapped_column(
        Geometry("POINT", srid=4326),
        nullable=False,
    )

    # Indicates whether the place is open late (e.g., nightlife, late services)
    # - Useful for filtering in nighttime or safety contexts
    is_open_late: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # Timestamp when the place was created
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )