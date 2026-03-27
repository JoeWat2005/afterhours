from datetime import datetime
from uuid import uuid4

from geoalchemy2 import Geometry
from sqlalchemy import DateTime, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Journey(Base):
    __tablename__ = "journeys"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    user_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("app_users.id", ondelete="SET NULL"),
        nullable=True,
    )
    origin_label: Mapped[str] = mapped_column(String(128), nullable=False)
    destination_label: Mapped[str] = mapped_column(String(128), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    route_geometry: Mapped[str] = mapped_column(
        Geometry("LINESTRING", srid=4326),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )