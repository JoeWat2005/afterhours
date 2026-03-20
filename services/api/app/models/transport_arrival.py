from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TransportArrival(Base):
    """
    Database model representing a transport arrival event.

    Purpose:
    - Stores expected arrival times of transport services at specific stops.
    - Supports real-time or scheduled transport tracking.
    - Can be used for live boards, notifications, or journey planning.
    """

    __tablename__ = "transport_arrivals"

    # Unique identifier for the arrival record
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # Reference to the transport stop
    # - Foreign key to transport_stops table
    # - CASCADE delete ensures arrivals are removed if the stop is deleted
    stop_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("transport_stops.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Reference to the transport service (e.g., route/line)
    # - Foreign key to transport_services table
    # - CASCADE delete ensures arrivals are removed if the service is deleted
    service_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("transport_services.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Expected arrival time at the stop
    # - Stored with timezone awareness
    # - Used for ordering and real-time updates
    expected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    # Status of the arrival (e.g., "on_time", "delayed", "cancelled")
    # - Useful for real-time transport information
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )

    # Timestamp when this arrival record was created
    # - Useful for tracking freshness of data
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )