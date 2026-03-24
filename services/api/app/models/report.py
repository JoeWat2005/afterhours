from datetime import datetime
from uuid import UUID, uuid4

from geoalchemy2 import Geometry
from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SafetyReport(Base):
    """
    Database model representing a user-submitted safety report.

    Purpose:
    - Captures incidents or safety concerns reported by users.
    - Includes location data for spatial analysis and mapping.
    - Used to inform heatmaps, alerts, and route safety scoring.
    """

    __tablename__ = "safety_reports"

    # Unique identifier for the report
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # Optional reference to the user who submitted the report
    # - Foreign key to app_users table
    # - SET NULL if user is deleted (preserves report data)
    user_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("app_users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Category chosen for the user-submitted report, keeps the raw app-facing report type for filtering and aggregation
    category: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    # Shared severity level derived from the user report category
    severity: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
    )

    # Short summary of the report (brief description)
    summary: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    # Detailed description of the report
    # - Can include more context or incident details
    details: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    # Geographic location of the incident (PostGIS POINT)
    # - Stored as longitude/latitude
    # - SRID 4326: standard WGS84 coordinate system
    location: Mapped[str] = mapped_column(
        Geometry("POINT", srid=4326),
        nullable=False,
    )

    # Timestamp when the report was created
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )
