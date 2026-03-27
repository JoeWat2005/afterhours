import pytest
from app.services.route_safety_estimator import estimate_route_safety

@pytest.mark.parametrize(
    "incident_density, report_density, route_length_km, lighting_score, depart_hour, expected_safety_range",
    [
        # 1. No data: should return prior-driven score (~0.9997)
        (None, None, 1.0, None, 12, (0.9, 1.0)),
        
        # 2. High crime density, day
        (50.0, 10.0, 1.0, 0.8, 12, (0.9, 1.0)),
        
        # 3. High crime density, night
        (50.0, 10.0, 1.0, 0.8, 2, (0.9, 1.0)),
        
        # 4. Low crime, well lit
        (0.1, 0.05, 1.0, 0.9, 12, (0.98, 1.0)),
        
        # 5. Low crime, poorly lit
        (0.1, 0.05, 1.0, 0.1, 12, (0.98, 1.0)),
        
        # 6. High exposure (long route) with high crime
        (10.0, 5.0, 10.0, 0.5, 12, (0.9, 1.0)),
        
        # 7. Low exposure (short route) with high crime
        (10.0, 5.0, 0.1, 0.5, 12, (0.9, 1.0)),
        
        # 8. Report-only evidence
        (None, 5.0, 1.0, 0.5, 12, (0.9, 1.0)),
        
        # 9. Extreme crime density: adjusted harm gets large, score starts to drop
        (5000.0, 2000.0, 2.0, 0.1, 3, (0.5, 0.95)),
        
        # 10. Day vs Night comparison
        (5.0, 2.0, 1.0, 0.5, 14, (0.9, 1.0)),
    ],
)
def test_bayesian_safety_estimator_math(
    incident_density,
    report_density,
    route_length_km,
    lighting_score,
    depart_hour,
    expected_safety_range,
):
    result = estimate_route_safety(
        incident_density=incident_density,
        report_density=report_density,
        route_length_km=route_length_km,
        lighting_score=lighting_score,
        depart_hour=depart_hour,
    )
    
    score = result["safety_score"]
    assert expected_safety_range[0] <= score <= expected_safety_range[1]
    
    # Verify probability P(S|D) trend: higher crime -> higher serious probability
    if incident_density is not None and incident_density > 100:
        assert result["serious_incident_probability"] > 0.5

    
    # Additional verification for trends
    if incident_density is None and report_density is None:
        assert result["shrinkage_factor"] == 1.0
    
    if route_length_km > 5.0 and incident_density is not None:
        # High exposure means data dominates
        assert result["shrinkage_factor"] < 0.6

def test_day_night_trend_comparison():
    # Helper test for specific comparison
    day = estimate_route_safety(
        incident_density=5.0,
        report_density=2.0,
        route_length_km=1.0,
        lighting_score=0.5,
        depart_hour=14, # Day
    )
    night = estimate_route_safety(
        incident_density=5.0,
        report_density=2.0,
        route_length_km=1.0,
        lighting_score=0.5,
        depart_hour=2, # Night
    )
    assert night["safety_score"] < day["safety_score"]

def test_lighting_interpolation_logic():
    # Test that score scales with lighting between 0.3 and 0.65
    poor = estimate_route_safety(incident_density=1.0, report_density=1.0, route_length_km=1.0, lighting_score=0.2)
    mid = estimate_route_safety(incident_density=1.0, report_density=1.0, route_length_km=1.0, lighting_score=0.45)
    well = estimate_route_safety(incident_density=1.0, report_density=1.0, route_length_km=1.0, lighting_score=0.8)
    
    # Use harm rate as it has more variance than the rounded 0-1 safety score
    assert poor["expected_harm_rate"] > mid["expected_harm_rate"] > well["expected_harm_rate"]
