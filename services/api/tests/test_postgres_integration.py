from __future__ import annotations

import os
import urllib.parse
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from app.api.deps.auth import get_current_app_user
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.journey import Journey
from app.models.report import SafetyReport
from app.models.user import AppUser
from app.services.route_safety import list_nearby_reports


def _scoped_urls(base_sync_url: str, schema: str) -> tuple[str, str]:
    option = urllib.parse.quote(f"-csearch_path={schema},public")
    joiner = "&" if "?" in base_sync_url else "?"
    scoped_sync = f"{base_sync_url}{joiner}options={option}"
    scoped_async = scoped_sync.replace("postgresql+psycopg://", "postgresql+psycopg_async://")
    return scoped_sync, scoped_async


@pytest.fixture()
async def postgres_session_factory() -> async_sessionmaker[AsyncSession]:
    base_sync_url = os.getenv("TEST_POSTGRES_DATABASE_URL", "")
    if not base_sync_url.startswith("postgresql+psycopg://"):
        pytest.skip("Set TEST_POSTGRES_DATABASE_URL=postgresql+psycopg://... to run Postgres integration tests")

    schema = f"test_api_integration_{uuid4().hex[:10]}"
    scoped_sync_url, scoped_async_url = _scoped_urls(base_sync_url, schema)

    admin_engine = create_engine(base_sync_url, future=True)
    with admin_engine.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))

    async_engine = create_async_engine(scoped_async_url, future=True)
    try:
        async with async_engine.begin() as connection:
            await connection.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
            await connection.run_sync(Base.metadata.create_all)

        yield async_sessionmaker(async_engine, expire_on_commit=False, class_=AsyncSession)
    finally:
        async with async_engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)
        await async_engine.dispose()

        with admin_engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        admin_engine.dispose()


@pytest.mark.asyncio
async def test_postgres_nearby_reports_filters_by_radius(
    postgres_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with postgres_session_factory() as session:
        user = AppUser(clerk_user_id=f"clerk_{uuid4().hex[:8]}")
        session.add(user)
        await session.commit()
        await session.refresh(user)

        near_report = SafetyReport(
            user_id=user.id,
            category="robbery",
            summary="Near incident",
            details="Near details",
            location=func.ST_SetSRID(func.ST_MakePoint(-0.1200, 51.5000), 4326),
        )
        far_report = SafetyReport(
            user_id=user.id,
            category="robbery",
            summary="Far incident",
            details="Far details",
            location=func.ST_SetSRID(func.ST_MakePoint(-0.1600, 51.5400), 4326),
        )
        session.add_all([near_report, far_report])
        await session.commit()
        await session.refresh(near_report)
        await session.refresh(far_report)

        reports = await list_nearby_reports(
            session,
            latitude=51.5000,
            longitude=-0.1200,
            radius_metres=500,
            limit=20,
        )

    report_ids = {report.id for report in reports}
    assert near_report.id in report_ids
    assert far_report.id not in report_ids


@pytest.mark.asyncio
async def test_postgres_journey_ownership_enforced(
    postgres_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with postgres_session_factory() as session:
        user_a = AppUser(clerk_user_id=f"clerk_a_{uuid4().hex[:8]}")
        user_b = AppUser(clerk_user_id=f"clerk_b_{uuid4().hex[:8]}")
        session.add_all([user_a, user_b])
        await session.commit()
        await session.refresh(user_a)
        await session.refresh(user_b)

        journey_for_b = Journey(
            user_id=user_b.id,
            origin_label="Origin",
            destination_label="Destination",
            score=75.0,
            route_geometry=func.ST_SetSRID(
                func.ST_GeomFromText("LINESTRING(-0.12 51.5, -0.11 51.51)"),
                4326,
            ),
        )
        session.add(journey_for_b)
        await session.commit()
        await session.refresh(journey_for_b)
        journey_id = journey_for_b.id
        user_b_id = user_b.id

    async def _override_db():
        async with postgres_session_factory() as request_session:
            yield request_session

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_app_user] = lambda: AppUser(
        id=user_a.id,
        clerk_user_id=user_a.clerk_user_id,
        display_name=user_a.display_name,
        created_at=user_a.created_at,
    )

    try:
        with TestClient(app) as client:
            read_other_journey = client.get(f"/v1/journeys/{journey_id}")
            assert read_other_journey.status_code == 403

            create_for_other_user = client.post(
                "/v1/journeys",
                json={
                    "user_id": str(user_b_id),
                    "origin_label": "A",
                    "destination_label": "B",
                    "score": 90.0,
                    "route_geojson": {
                        "type": "LineString",
                        "coordinates": [[-0.12, 51.5], [-0.11, 51.51]],
                    },
                },
            )
            assert create_for_other_user.status_code == 403
    finally:
        app.dependency_overrides.clear()
