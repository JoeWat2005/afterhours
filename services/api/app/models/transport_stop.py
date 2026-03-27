from datetime import datetime
from uuid import uuid4

from geoalchemy2 import Geometry
from sqlalchemy import DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TransportStop(Base):
    __tablename__ = "transport_stops"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    stop_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    mode: Mapped[str] = mapped_column(String(32), nullable=False)  # bus, train, tram
    location: Mapped[str] = mapped_column(
        Geometry("POINT", srid=4326),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )