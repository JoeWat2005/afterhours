import pytest

from app.services.route_safety_estimator import estimate_route_safety


def test_estimator_uses_prior_when_data_is_none() -> None:
    result = estimate_route_safety(
        incident_density=None,
        report_density=None,
        route_length_km=1.0,
        lighting_score=None,
        depart_hour=None,
    )

    # With no data, shrinkge should be completely prior-driven (1.0)
    assert result["shrinkage_factor"] == 1.0
    assert result["expected_harm_rate"] > 0
    assert 0.0 <= result["safety_score"] <= 1.0


def test_estimator_lowers_shrinkage_with_high_evidence() -> None:
    # A very long route with data means high effective exposure
    result = estimate_route_safety(
        incident_density=10.0,
        report_density=5.0,
        route_length_km=10.0,
        lighting_score=None,
        depart_hour=None,
    )

    # Shrinkage should drop significantly below 1.0 showing data dominance
    assert result["shrinkage_factor"] < 0.5


