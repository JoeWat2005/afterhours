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



def test_lighting_modifier_affects_score() -> None:
    # Base scenario
    base = estimate_route_safety(
        incident_density=2.0,
        report_density=1.0,
        route_length_km=1.0,
        lighting_score=None,
        depart_hour=14,  # daytime
    )

    # Well lit route
    well_lit = estimate_route_safety(
        incident_density=2.0,
        report_density=1.0,
        route_length_km=1.0,
        lighting_score=0.9,
        depart_hour=14,
    )

    # Poorly lit route
    poorly_lit = estimate_route_safety(
        incident_density=2.0,
        report_density=1.0,
        route_length_km=1.0,
        lighting_score=0.1,
        depart_hour=14,
    )

    assert well_lit["safety_score"] > poorly_lit["safety_score"]
    assert well_lit["expected_harm_rate"] < poorly_lit["expected_harm_rate"]


def test_time_multiplier_increases_risk_at_night() -> None:
    day_result = estimate_route_safety(
        incident_density=1.0,
        report_density=0.0,
        route_length_km=2.0,
        lighting_score=0.5,
        depart_hour=14,  # 2 PM
    )

    night_result = estimate_route_safety(
        incident_density=1.0,
        report_density=0.0,
        route_length_km=2.0,
        lighting_score=0.5,
        depart_hour=2,   # 2 AM
    )

    # Nighttime multiplier should increase harm and lower safety score
    assert night_result["safety_score"] < day_result["safety_score"]
    assert night_result["expected_harm_rate"] > day_result["expected_harm_rate"]


def test_high_density_lowers_safety_score() -> None:
    low_crime = estimate_route_safety(
        incident_density=0.1,
        report_density=0.0,
        route_length_km=1.0,
        lighting_score=0.8,
        depart_hour=14,
    )

    high_crime = estimate_route_safety(
        incident_density=50.0,
        report_density=10.0,
        route_length_km=1.0,
        lighting_score=0.8,
        depart_hour=14,
    )

    assert high_crime["safety_score"] < low_crime["safety_score"]
    assert high_crime["expected_harm_rate"] > low_crime["expected_harm_rate"]
    assert high_crime["serious_incident_probability"] > low_crime["serious_incident_probability"]
