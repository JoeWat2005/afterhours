from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps.auth import AuthContext, get_auth_context, get_current_app_user
from app.db.session import get_db
from app.models.user import AppUser
from app.schemas.users import UserCreate, UserResponse, UserUpdate

router = APIRouter()


def _forbidden_subject_mismatch() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Token subject does not match requested user",
    )


@router.get("/me", response_model=UserResponse)
async def get_my_user(
    current_user: AppUser = Depends(get_current_app_user),
) -> UserResponse:
    return UserResponse.model_validate(current_user)


@router.patch("/me", response_model=UserResponse)
async def update_my_user(
    payload: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: AppUser = Depends(get_current_app_user),
) -> UserResponse:
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(current_user, key, value)

    await db.commit()
    await db.refresh(current_user)

    return UserResponse.model_validate(current_user)


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    deprecated=True,
)
async def create_user(
    payload: UserCreate,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
) -> UserResponse:
    if payload.clerk_user_id != auth.subject:
        raise _forbidden_subject_mismatch()

    stmt = select(AppUser).where(AppUser.clerk_user_id == payload.clerk_user_id)
    result = await db.execute(stmt)
    existing_user = result.scalars().first()

    if existing_user:
        raise HTTPException(
            status_code=409,
            detail="User with this clerk_user_id already exists",
        )

    user = AppUser(**payload.model_dump())
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return UserResponse.model_validate(user)


@router.get("/{user_id}", response_model=UserResponse, deprecated=True)
async def get_user(
    user_id: UUID,
    current_user: AppUser = Depends(get_current_app_user),
) -> UserResponse:
    if current_user.id != user_id:
        raise _forbidden_subject_mismatch()

    return UserResponse.model_validate(current_user)


@router.get("/clerk/{clerk_user_id}", response_model=UserResponse, deprecated=True)
async def get_user_by_clerk_id(
    clerk_user_id: str,
    current_user: AppUser = Depends(get_current_app_user),
) -> UserResponse:
    if current_user.clerk_user_id != clerk_user_id:
        raise _forbidden_subject_mismatch()

    return UserResponse.model_validate(current_user)


@router.patch("/{user_id}", response_model=UserResponse, deprecated=True)
async def update_user(
    user_id: UUID,
    payload: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: AppUser = Depends(get_current_app_user),
) -> UserResponse:
    if current_user.id != user_id:
        raise _forbidden_subject_mismatch()

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(current_user, key, value)

    await db.commit()
    await db.refresh(current_user)

    return UserResponse.model_validate(current_user)
