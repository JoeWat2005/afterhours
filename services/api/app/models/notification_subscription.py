from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class NotificationSubscription(Base):
    """
    Database model representing a user's notification subscription.

    Purpose:
    - Stores user preferences for receiving notifications.
    - Supports different types of notifications (e.g., alerts, updates).
    - Allows enabling/disabling and optional configuration per subscription.
    """

    __tablename__ = "notification_subscriptions"

    # Unique identifier for the subscription
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # Reference to the user who owns this subscription
    # - Foreign key to app_users table
    # - CASCADE delete ensures subscriptions are removed if user is deleted
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("app_users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Type of notification (e.g., "safety_alert", "route_update")
    # - Used to differentiate notification categories
    type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    # Whether the subscription is currently enabled
    # - Allows users to toggle notifications on/off without deleting them
    enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    # Optional configuration for the subscription
    # - Can store JSON or structured data as text (e.g., preferences, thresholds)
    config: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Timestamp when the subscription was created
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )