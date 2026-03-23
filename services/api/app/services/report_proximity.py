from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.report import SafetyReport


REPORT_CATEGORY_WEIGHTS: dict[str, int] = {
    "assault": 4,
    "robbery": 4,
    "harassment": 3,
    "theft": 3,
    "suspicious activity": 2,
    "poor lighting": 2,
    "unsafe crossing": 2,
    "hazard": 1,
    "other": 1,
}


def normalize_report_category(category: str | None) -> str:
    if not category:
        return "other"
    return category.strip().lower()


def get_report_weight(category: str | None) -> int:
    return REPORT_CATEGORY_WEIGHTS.get(normalize_report_category(category), 1)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


async def list_nearby_reports(
    db: AsyncSession,
    *,
    latitude: float,
    longitude: float,
    radius_metres: float,
    limit: int = 100,
    created_after: datetime | None = None,
) -> list[SafetyReport]:
    origin = func.ST_SetSRID(func.ST_MakePoint(longitude, latitude), 4326)

    stmt = select(SafetyReport).where(
        func.ST_DWithin(
            func.Geography(SafetyReport.location),
            func.Geography(origin),
            radius_metres,
        )
    )

    if created_after is not None:
        stmt = stmt.where(SafetyReport.created_at >= created_after)

    stmt = stmt.order_by(
        func.ST_Distance(
            func.Geography(SafetyReport.location),
            func.Geography(origin),
        )
    ).limit(limit)

    result = await db.execute(stmt)
    return list(result.scalars().all())


async def list_unique_reports_along_route(
    db: AsyncSession,
    *,
    sampled_points: Iterable[tuple[float, float]],  # (lat, lon)
    radius_metres: float,
    per_point_limit: int = 100,
    max_age_days: int | None = 90,
) -> list[SafetyReport]:
    created_after: datetime | None = None
    if max_age_days is not None:
        created_after = utc_now() - timedelta(days=max_age_days)

    seen_ids: set[UUID] = set()
    unique_reports: list[SafetyReport] = []

    for latitude, longitude in sampled_points:
        reports = await list_nearby_reports(
            db,
            latitude=latitude,
            longitude=longitude,
            radius_metres=radius_metres,
            limit=per_point_limit,
            created_after=created_after,
        )

        for report in reports:
            if report.id in seen_ids:
                continue
            seen_ids.add(report.id)
            unique_reports.append(report)

    return unique_reports


def compute_report_density(
    *,
    reports: Iterable[SafetyReport],
    route_length_metres: float,
) -> float | None:
    if route_length_metres <= 0:
        return None

    route_length_km = route_length_metres / 1000.0
    if route_length_km <= 0:
        return None

    reports_list = list(reports)
    if not reports_list:
        return None

    weighted_total = sum(get_report_weight(report.category) for report in reports_list)
    return round(weighted_total / route_length_km, 4)