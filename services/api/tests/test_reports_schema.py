from app.schemas.reports import SafetyReportCreate


def _base_payload() -> dict:
    return {
        "category": "other",
        "summary": "Street feels unsafe",
        "description": "This area is dark and isolated late at night.",
        "latitude": 52.4862,
        "longitude": -1.8904,
    }


def test_report_schema_accepts_description_alias_for_details() -> None:
    payload = SafetyReportCreate.model_validate(_base_payload())

    assert payload.details == "This area is dark and isolated late at night."


def test_report_schema_normalizes_category_for_route_safety_weights() -> None:
    payload = SafetyReportCreate.model_validate(
        {
            **_base_payload(),
            "category": "Break-in / Burglary",
        }
    )

    assert payload.category == "theft"


def test_report_schema_maps_unknown_category_to_other() -> None:
    payload = SafetyReportCreate.model_validate(
        {
            **_base_payload(),
            "category": "Loud music",
        }
    )

    assert payload.category == "other"


def test_report_schema_allows_anonymous_reports() -> None:
    payload = SafetyReportCreate.model_validate(_base_payload())

    assert payload.user_id is None
