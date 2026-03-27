def validate_report(report_payload: dict[str, str | float]) -> dict[str, bool | list[str]]:
    flags: list[str] = []

    if len(str(report_payload["summary"]).strip()) < 8:
        flags.append("summary_too_short")

    if len(str(report_payload["description"]).strip()) < 20:
        flags.append("description_too_short")

    if abs(float(report_payload["latitude"])) > 90 or abs(float(report_payload["longitude"])) > 180:
        flags.append("invalid_coordinates")

    return {
        "accepted": not flags,
        "moderation_flags": flags,
    }
