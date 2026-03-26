from app.services.safety_reports import validate_report


def test_validate_report_accepts_valid_payload() -> None:
    result = validate_report(
        {
            "summary": "Poor lighting near stop",
            "description": "The alley by the bus stop is very dark after 9pm.",
            "latitude": 52.4862,
            "longitude": -1.8904,
        }
    )

    assert result == {
        "accepted": True,
        "moderation_flags": [],
        "severity": "low",
    }


def test_validate_report_flags_short_summary() -> None:
    result = validate_report(
        {
            "summary": "Too dim",
            "description": "There is almost no lighting on this stretch of road.",
            "latitude": 52.4862,
            "longitude": -1.8904,
        }
    )

    assert result["accepted"] is False
    assert "summary_too_short" in result["moderation_flags"]


def test_validate_report_flags_short_description() -> None:
    result = validate_report(
        {
            "summary": "Unsafe crossing point",
            "description": "Too dark here.",
            "latitude": 52.4862,
            "longitude": -1.8904,
        }
    )

    assert result["accepted"] is False
    assert "description_too_short" in result["moderation_flags"]


def test_validate_report_flags_out_of_range_coordinates() -> None:
    result = validate_report(
        {
            "summary": "Unsafe crossing point",
            "description": "Cars drive too fast here and there is poor visibility.",
            "latitude": 120.0,
            "longitude": -200.0,
        }
    )

    assert result["accepted"] is False
    assert "invalid_coordinates" in result["moderation_flags"]


def test_validate_report_flags_non_numeric_coordinates() -> None:
    result = validate_report(
        {
            "summary": "Unsafe crossing point",
            "description": "Cars drive too fast here and there is poor visibility.",
            "latitude": "not-a-number",
            "longitude": "still-not-a-number",
        }
    )

    assert result["accepted"] is False
    assert "invalid_coordinates" in result["moderation_flags"]


def test_validate_report_handles_missing_fields_gracefully() -> None:
    result = validate_report({})

    assert result["accepted"] is False
    assert "summary_too_short" in result["moderation_flags"]
    assert "description_too_short" in result["moderation_flags"]
    assert "invalid_coordinates" in result["moderation_flags"]