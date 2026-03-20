from datetime import datetime
from uuid import UUID, uuid4

from geoalchemy2 import Geometry
from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Journey(Base):
    """
    Database model representing a user journey/route.

    Purpose:
    - Stores routes taken or evaluated by users.
    - Includes metadata such as origin/destination labels and a safety score.
    - Stores the route geometry for mapping and spatial analysis.
    """

    __tablename__ = "journeys"

    # Unique identifier for the journey
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # Optional reference to the user who created the journey
    # - Uses foreign key to app_users table
    # - SET NULL if user is deleted (preserves journey data)
    user_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("app_users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Human-readable label for the journey starting point
    origin_label: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )

    # Human-readable label for the journey destination
    destination_label: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )

    # Safety score assigned to the journey
    # - Typically computed by a scoring algorithm
    # - Can be used to compare route safety
    score: Mapped[float] = mapped_column(nullable=False)

    # Geometry representing the route path (PostGIS LINESTRING)
    # - SRID 4326: standard lat/lon coordinate system
    # - Stores the full path of the journey
    route_geometry: Mapped[str] = mapped_column(
        Geometry("LINESTRING", srid=4326),
        nullable=False,
    )

    # Timestamp when the journey was created
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )