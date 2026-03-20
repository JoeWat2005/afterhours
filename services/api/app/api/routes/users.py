from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import AppUser
from app.schemas.users import UserCreate, UserResponse, UserUpdate

# Create a router instance for user-related endpoints
router = APIRouter()


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(payload: UserCreate, db: AsyncSession = Depends(get_db)) -> UserResponse:
    """
    Create a new user.

    Purpose:
    - Registers a new user in the system.
    - Ensures that each user has a unique clerk_user_id (external auth provider ID).

    Request Body:
    - payload (UserCreate):
        Contains user details including clerk_user_id.

    Process:
    - Check if a user with the same clerk_user_id already exists.
    - If so, return a 409 Conflict error.
    - Otherwise, create and store the new user.

    Errors:
    - 409 if a user with the given clerk_user_id already exists.

    Returns:
    - The created user as a UserResponse.
    """

    # Check for existing user with same clerk_user_id
    stmt = select(AppUser).where(AppUser.clerk_user_id == payload.clerk_user_id)
    result = await db.execute(stmt)
    existing_user = result.scalars().first()

    if existing_user:
        raise HTTPException(
            status_code=409,
            detail="User with this clerk_user_id already exists",
        )

    # Create new user
    user = AppUser(**payload.model_dump())

    # Persist to database
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Convert to response schema
    return UserResponse.model_validate(user)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: UUID, db: AsyncSession = Depends(get_db)) -> UserResponse:
    """
    Retrieve a user by their internal UUID.

    Purpose:
    - Fetch user details using the system's primary identifier.

    Path Parameters:
    - user_id:
        UUID of the user.

    Errors:
    - 404 if the user does not exist.

    Returns:
    - UserResponse containing user details.
    """

    # Fetch user by primary key
    user = await db.get(AppUser, user_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return UserResponse.model_validate(user)


@router.get("/clerk/{clerk_user_id}", response_model=UserResponse)
async def get_user_by_clerk_id(
    clerk_user_id: str,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """
    Retrieve a user by their external Clerk ID.

    Purpose:
    - Allows lookup of users using an external authentication provider ID.

    Path Parameters:
    - clerk_user_id:
        Unique identifier from Clerk (or similar auth system).

    Errors:
    - 404 if the user does not exist.

    Returns:
    - UserResponse containing user details.
    """

    # Query user by clerk_user_id
    stmt = select(AppUser).where(AppUser.clerk_user_id == clerk_user_id)
    result = await db.execute(stmt)
    user = result.scalars().first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return UserResponse.model_validate(user)


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID,
    payload: UserUpdate,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """
    Update an existing user.

    Purpose:
    - Allows partial updates to user data (e.g., profile fields).

    Path Parameters:
    - user_id:
        UUID of the user to update.

    Request Body:
    - payload (UserUpdate):
        Contains fields to update (partial updates supported).

    Process:
    - Retrieve the user from the database.
    - If not found, return 404.
    - Update only the fields provided in the payload.
    - Commit changes and refresh the object.

    Errors:
    - 404 if the user does not exist.

    Returns:
    - Updated user as a UserResponse.
    """

    # Fetch user by ID
    user = await db.get(AppUser, user_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Apply partial updates (only provided fields)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(user, key, value)

    # Persist changes
    await db.commit()
    await db.refresh(user)

    return UserResponse.model_validate(user)