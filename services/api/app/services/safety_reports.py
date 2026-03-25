from typing import TypedDict

from app.core.route_risk_config import (
    DEFAULT_USER_REPORT_SEVERITY,
    ReportSeverity,
    SEVERITY_WEIGHTS,
    USER_REPORT_CATEGORY_SEVERITY,
)


class ReportValidationResult(TypedDict):
    accepted: bool
    moderation_flags: list[str]
    severity: str


def normalize_user_report_category(category: str | None) -> str:
    if not category:
        return "other"
    return category.strip().lower()


def get_user_report_severity(category: str | None) -> ReportSeverity:
    normalized_category = normalize_user_report_category(category)
    return USER_REPORT_CATEGORY_SEVERITY.get(
        normalized_category,
        DEFAULT_USER_REPORT_SEVERITY,
    )


def get_severity_weight(severity: ReportSeverity | str | None) -> int:
    if isinstance(severity, str):
        try:
            severity = ReportSeverity(severity.strip().lower())
        except ValueError:
            severity = DEFAULT_USER_REPORT_SEVERITY

    if severity is None:
        severity = DEFAULT_USER_REPORT_SEVERITY

    return SEVERITY_WEIGHTS[severity]


def get_user_report_weight(category: str | None) -> int:
    return get_severity_weight(get_user_report_severity(category))


def validate_report(
    report_payload: dict[str, str | float | int | None],
) -> ReportValidationResult:
    flags: list[str] = []

    summary = str(report_payload.get("summary", "") or "").strip()
    description = str(
        report_payload.get("description", report_payload.get("details", "")) or ""
    ).strip()

    if len(summary) < 8:
        flags.append("summary_too_short")

    if len(description) < 20:
        flags.append("description_too_short")

    latitude_raw = report_payload.get("latitude")
    longitude_raw = report_payload.get("longitude")

    try:
        latitude = float(latitude_raw)  # type: ignore[arg-type]
        longitude = float(longitude_raw)  # type: ignore[arg-type]
        if abs(latitude) > 90 or abs(longitude) > 180:
            flags.append("invalid_coordinates")
    except (TypeError, ValueError):
        flags.append("invalid_coordinates")

    severity = get_user_report_severity(str(report_payload.get("category", "") or ""))

    return {
        "accepted": not flags,
        "moderation_flags": flags,
        "severity": severity.value,
    }
