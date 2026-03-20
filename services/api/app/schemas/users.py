from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class UserCreate(BaseModel):
    """
    Schema for creating a new user.

    Purpose:
    - Validates incoming user registration data.
    - Ensures required fields (like clerk_user_id) are provided and valid.

    Fields:
    - clerk_user_id: External auth provider ID (required, unique)
    - display_name: Optional user display name
    """

    # External authentication provider ID (e.g., Clerk)
    clerk_user_id: str = Field(min_length=1, max_length=255)

    # Optional display name for the user
    display_name: str | None = Field(default=None, max_length=255)


class UserUpdate(BaseModel):
    """
    Schema for updating a user.

    Purpose:
    - Supports partial updates to user profile data.

    Fields:
    - display_name: Optional updated display name
    """

    # Optional updated display name
    display_name: str | None = Field(default=None, max_length=255)


class UserResponse(BaseModel):
    """
    Schema representing a user in API responses.

    Purpose:
    - Standardises how user data is returned to clients.
    - Supports ORM-to-schema conversion.

    Fields:
    - id: Internal user ID (UUID)
    - clerk_user_id: External auth provider ID
    - display_name: Optional display name
    - created_at: Timestamp of creation
    """

    # Enable ORM compatibility (e.g., SQLAlchemy models)
    model_config = ConfigDict(from_attributes=True)

    # Unique internal identifier for the user
    id: UUID

    # External authentication provider ID
    clerk_user_id: str

    # Optional display name
    display_name: str | None

    # Timestamp when the user was created
    created_at: datetime