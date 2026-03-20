from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class NotificationSubscriptionCreate(BaseModel):
    """
    Schema for creating a notification subscription.

    Purpose:
    - Validates incoming data when a user subscribes to notifications.
    - Ensures required fields and constraints are enforced.

    Fields:
    - user_id: ID of the user creating the subscription
    - type: Type/category of notification (1–64 chars)
    - enabled: Whether the subscription is active (default: True)
    - config: Optional configuration data (e.g., preferences)
    """

    # ID of the user who owns the subscription
    user_id: UUID

    # Type of notification (validated length)
    type: str = Field(min_length=1, max_length=64)

    # Whether the subscription is enabled
    enabled: bool = True

    # Optional configuration (e.g., JSON string or settings)
    config: str | None = None


class NotificationSubscriptionUpdate(BaseModel):
    """
    Schema for updating a notification subscription.

    Purpose:
    - Supports partial updates to subscription settings.
    - Only provided fields will be updated.

    Fields:
    - enabled: Toggle subscription on/off
    - config: Update configuration data
    """

    # Optional enable/disable flag
    enabled: bool | None = None

    # Optional updated configuration
    config: str | None = None


class NotificationSubscriptionResponse(BaseModel):
    """
    Schema representing a notification subscription in API responses.

    Purpose:
    - Standardises how subscription data is returned to clients.
    - Supports ORM-to-schema conversion.

    Fields:
    - id: Unique subscription ID
    - user_id: Owner of the subscription
    - type: Notification type
    - enabled: Whether subscription is active
    - config: Optional configuration
    - created_at: Timestamp of creation
    """

    # Enable compatibility with ORM models (e.g., SQLAlchemy)
    model_config = ConfigDict(from_attributes=True)

    # Unique identifier for the subscription
    id: UUID

    # User who owns the subscription
    user_id: UUID

    # Type/category of notification
    type: str

    # Whether the subscription is enabled
    enabled: bool

    # Optional configuration data
    config: str | None

    # Timestamp when the subscription was created
    created_at: datetime