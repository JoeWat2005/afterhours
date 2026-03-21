from datetime import datetime
from uuid import uuid4

from geoalchemy2 import Geometry
from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SafetyReport(Base):
    __tablename__ = "safety_reports"

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
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    summary: Mapped[str] = mapped_column(String(255), nullable=False)
    details: Mapped[str] = mapped_column(Text, nullable=False)
    location: Mapped[str] = mapped_column(
        Geometry("POINT", srid=4326),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )