import pytest
from app.models.user import AppUser
from app.models.report import SafetyReport
from app.models.journey import Journey


# Test creating a user object and checking fields
def test_create_user_object() -> None:
    user = AppUser(
        clerk_user_id="test_user_123",
        display_name="Test User",
    )

    assert user.clerk_user_id == "test_user_123"
    assert user.display_name == "Test User"


# Test creating a safety report object and checking fields
def test_create_report_object() -> None:
    report = SafetyReport(
        user_id=None,
        category="theft",
        severity="medium",
        summary="Test summary",
        details="Test details",
        location="POINT(0 0)",
    )

    assert report.category == "theft"
    assert report.severity == "medium"
    assert report.summary == "Test summary"


# Test creating a journey object and checking fields
def test_create_journey_object() -> None:
    journey = Journey(
        user_id=None,
        origin_label="A",
        destination_label="B",
        score=0.75,
        route_geometry="LINESTRING(0 0, 1 1)",
    )

    assert journey.origin_label == "A"
    assert journey.destination_label == "B"
    assert journey.score == 0.75