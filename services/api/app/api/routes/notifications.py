from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.notification_subscription import NotificationSubscription
from app.schemas.notifications import (
    NotificationSubscriptionCreate,
    NotificationSubscriptionResponse,
    NotificationSubscriptionUpdate,
)

# Create a router instance for notification subscription endpoints
router = APIRouter()


@router.post("", response_model=NotificationSubscriptionResponse, status_code=status.HTTP_201_CREATED)
async def create_subscription(
    payload: NotificationSubscriptionCreate,
    db: AsyncSession = Depends(get_db),
) -> NotificationSubscriptionResponse:
    """
    Create a new notification subscription.

    Purpose:
    - Allows a user to subscribe to notifications (e.g., alerts, updates).
    - Stores subscription preferences in the database.

    Request Body:
    - payload (NotificationSubscriptionCreate):
        Contains the data required to create a subscription (e.g., user_id, type, settings).

    Process:
    - Convert incoming payload into a NotificationSubscription ORM object.
    - Save it to the database.
    - Refresh to retrieve generated fields (e.g., ID).

    Returns:
    - The created subscription as a response model.
    """

    # Create ORM object from request payload
    sub = NotificationSubscription(**payload.model_dump())

    # Persist to database
    db.add(sub)
    await db.commit()
    await db.refresh(sub)

    # Convert ORM model to response schema
    return NotificationSubscriptionResponse.model_validate(sub)


@router.get("/user/{user_id}", response_model=list[NotificationSubscriptionResponse])
async def list_subscriptions(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> list[NotificationSubscriptionResponse]:
    """
    Retrieve all notification subscriptions for a specific user.

    Purpose:
    - Allows clients to fetch all subscriptions associated with a user.
    - Useful for managing or displaying user notification preferences.

    Path Parameters:
    - user_id:
        UUID of the user whose subscriptions are being requested.

    Process:
    - Query the database for all subscriptions matching the user_id.
    - Convert ORM models into response schemas.

    Returns:
    - A list of NotificationSubscriptionResponse objects.
    """

    # Build query to fetch subscriptions for a given user
    stmt = select(NotificationSubscription).where(
        NotificationSubscription.user_id == user_id
    )

    # Execute query
    result = await db.execute(stmt)
    items = result.scalars().all()

    # Convert ORM models to response schemas
    return [
        NotificationSubscriptionResponse.model_validate(item)
        for item in items
    ]


@router.patch("/{subscription_id}", response_model=NotificationSubscriptionResponse)
async def update_subscription(
    subscription_id: UUID,
    payload: NotificationSubscriptionUpdate,
    db: AsyncSession = Depends(get_db),
) -> NotificationSubscriptionResponse:
    """
    Update an existing notification subscription.

    Purpose:
    - Allows partial updates to a subscription (e.g., enable/disable, change preferences).

    Path Parameters:
    - subscription_id:
        UUID of the subscription to update.

    Request Body:
    - payload (NotificationSubscriptionUpdate):
        Contains fields to update (partial updates supported).

    Process:
    - Retrieve the subscription from the database.
    - If not found, return 404.
    - Update only the fields provided in the payload.
    - Commit changes and refresh the object.

    Errors:
    - 404 if the subscription does not exist.

    Returns:
    - The updated subscription as a response model.
    """

    # Fetch subscription by ID
    sub = await db.get(NotificationSubscription, subscription_id)

    # Handle case where subscription does not exist
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")

    # Update only provided fields (partial update)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(sub, key, value)

    # Persist changes
    await db.commit()
    await db.refresh(sub)

    # Return updated object
    return NotificationSubscriptionResponse.model_validate(sub)