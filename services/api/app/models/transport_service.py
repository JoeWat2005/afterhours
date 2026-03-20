from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TransportService(Base):
    """
    Database model representing a transport service.

    Purpose:
    - Stores information about transport lines/services (e.g., bus routes, train lines).
    - Used in conjunction with stops and arrivals to model transport systems.
    """

    __tablename__ = "transport_services"

    # Unique identifier for the transport service
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # Name of the service (e.g., "Bus 42", "Northern Line")
    service_name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )

    # Mode of transport (e.g., "bus", "train", "tram")
    # - Useful for filtering and grouping services
    mode: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )

    # Name of the operator running the service (e.g., "TfL", "National Rail")
    # - Optional field
    operator_name: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
    )

    # Active hours of the service (e.g., "05:00-23:30")
    # - Stored as string; could be structured in future
    active_hours: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
    )

    # Timestamp when the service record was created
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )