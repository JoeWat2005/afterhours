"""
Database session setup using async SQLAlchemy.

Provides:
- Async engine
- Session factory
- FastAPI dependency (get_db)
"""

from collections.abc import AsyncGenerator
from functools import lru_cache

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings


def _to_async_database_url(database_url: str) -> str:
    """
    Convert sync DB URL to async driver.
    """
    return database_url.replace(
        "postgresql+psycopg://",
        "postgresql+psycopg_async://",
    )


@lru_cache(maxsize=1)
def get_engine() -> AsyncEngine:
    """
    Create async DB engine (cached).
    """
    settings = get_settings()

    return create_async_engine(
        _to_async_database_url(settings.database_url),
        echo=settings.environment == "development",
        pool_pre_ping=True,
    )


@lru_cache(maxsize=1)
def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """
    Create session factory (cached).
    """
    return async_sessionmaker(
        get_engine(),
        expire_on_commit=False,
    )


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for DB session.
    """
    session_factory = get_session_factory()

    async with session_factory() as session:
        yield session