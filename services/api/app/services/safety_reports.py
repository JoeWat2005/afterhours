def validate_report(report_payload: dict[str, str | float | int | None]) -> dict[str, bool | list[str]]:
    flags: list[str] = []

    summary = str(report_payload.get("summary", "") or "").strip()
    description = str(report_payload.get("description", "") or "").strip()

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

    return {
        "accepted": not flags,
        "moderation_flags": flags,
    }