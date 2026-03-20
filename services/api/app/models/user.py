from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AppUser(Base):
    """
    Database model representing an application user.

    Purpose:
    - Stores user records linked to an external authentication provider (e.g., Clerk).
    - Holds minimal profile information for use within the application.
    - Acts as a reference for other entities (e.g., journeys, reports, subscriptions).
    """

    __tablename__ = "app_users"

    # Unique internal identifier for the user (UUID)
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # Unique identifier from external authentication provider (e.g., Clerk)
    # - Used to link authenticated users to internal records
    # - Must be unique across all users
    clerk_user_id: Mapped[str] = mapped_column(
        String(128),
        unique=True,
        nullable=False,
    )

    # Optional display name for the user
    # - Can be shown in UI (e.g., profile, reports)
    display_name: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
    )

    # Timestamp when the user was created
    # - Useful for auditing and tracking user lifecycle
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )