from app.schemas.routes import RouteCandidateInput, RouteRequirements
from app.services.route_requirements import get_unmet_requirements


def make_candidate(
    candidate_id: str = "route-a",
    *,
    stairs_present: bool | None = False,
    step_free_ratio: float | None = 1.0,
    lift_coverage_ratio: float | None = 1.0,
    ramp_coverage_ratio: float | None = 1.0,
    escalator_coverage_ratio: float | None = 1.0,
    safe_waiting_area_count: int | None = 2,
    well_lit_waiting_area_count: int | None = 2,
    wifi_access_point_count: int | None = 1,
    staffed_venue_count: int | None = 1,
    open_venue_count: int | None = 1,
    waiting_areas_in_safe_areas_ratio: float | None = 0.75,
) -> RouteCandidateInput:
    return RouteCandidateInput.model_validate(
        {
            "candidate_id": candidate_id,
            "label": candidate_id.replace("-", " ").title(),
            "provider": "mapbox",
            "distance_metres": 1000,
            "duration_seconds": 800,
            "features": {
                "accessibility": {
                    "stairs_present": stairs_present,
                    "step_free_ratio": step_free_ratio,
                    "lift_coverage_ratio": lift_coverage_ratio,
                    "ramp_coverage_ratio": ramp_coverage_ratio,
                    "escalator_coverage_ratio": escalator_coverage_ratio,
                },
                "waiting_areas": {
                    "safe_waiting_area_count": safe_waiting_area_count,
                    "well_lit_waiting_area_count": well_lit_waiting_area_count,
                    "wifi_access_point_count": wifi_access_point_count,
                    "staffed_venue_count": staffed_venue_count,
                    "open_venue_count": open_venue_count,
                    "waiting_areas_in_safe_areas_ratio": waiting_areas_in_safe_areas_ratio,
                },
                "safety": {},
                "transport": {},
            },
        }
    )


def make_requirements(
    *,
    avoid_stairs: bool = False,
    step_free_access: bool = False,
    lifts_available: bool = False,
    ramps_available: bool = False,
    escalators_available: bool = False,
    safe_waiting_areas: bool = False,
    well_lit_waiting_areas: bool = False,
    wifi_nearby: bool = False,
    staffed_venues_nearby: bool = False,
    open_venues_nearby: bool = False,
    safe_areas_nearby: bool = False,
) -> RouteRequirements:
    return RouteRequirements.model_validate(
        {
            "accessibility": {
                "avoid_stairs": avoid_stairs,
                "step_free_access": step_free_access,
                "lifts_available": lifts_available,
                "ramps_available": ramps_available,
                "escalators_available": escalators_available,
            },
            "waiting_areas": {
                "safe_waiting_areas": safe_waiting_areas,
                "well_lit_waiting_areas": well_lit_waiting_areas,
                "wifi_nearby": wifi_nearby,
                "staffed_venues_nearby": staffed_venues_nearby,
                "open_venues_nearby": open_venues_nearby,
                "safe_areas_nearby": safe_areas_nearby,
            },
        }
    )


def test_avoid_stairs_requirement_fails_when_stairs_are_present() -> None:
    candidate = make_candidate(stairs_present=True)
    requirements = make_requirements(avoid_stairs=True)

    result = get_unmet_requirements(candidate, requirements)

    assert result == ["avoid_stairs"]


def test_avoid_stairs_requirement_passes_when_stairs_are_not_present() -> None:
    candidate = make_candidate(stairs_present=False)
    requirements = make_requirements(avoid_stairs=True)

    result = get_unmet_requirements(candidate, requirements)

    assert result == []


def test_step_free_access_requirement_fails_when_ratio_is_too_low() -> None:
    candidate = make_candidate(step_free_ratio=0.20)
    requirements = make_requirements(step_free_access=True)

    result = get_unmet_requirements(candidate, requirements)

    assert result == ["step_free_access"]


def test_step_free_access_requirement_passes_when_ratio_is_high_enough() -> None:
    candidate = make_candidate(step_free_ratio=1.0)
    requirements = make_requirements(step_free_access=True)

    result = get_unmet_requirements(candidate, requirements)

    assert result == []


def test_lifts_ramps_and_escalators_requirements_fail_when_missing() -> None:
    candidate = make_candidate(
        lift_coverage_ratio=0.0,
        ramp_coverage_ratio=0.0,
        escalator_coverage_ratio=0.0,
    )
    requirements = make_requirements(
        lifts_available=True,
        ramps_available=True,
        escalators_available=True,
    )

    result = get_unmet_requirements(candidate, requirements)

    assert result == [
        "lifts_available",
        "ramps_available",
        "escalators_available",
    ]


def test_waiting_area_count_requirements_fail_when_counts_are_too_low() -> None:
    candidate = make_candidate(
        safe_waiting_area_count=0,
        well_lit_waiting_area_count=0,
        wifi_access_point_count=0,
        staffed_venue_count=0,
        open_venue_count=0,
    )
    requirements = make_requirements(
        safe_waiting_areas=True,
        well_lit_waiting_areas=True,
        wifi_nearby=True,
        staffed_venues_nearby=True,
        open_venues_nearby=True,
    )

    result = get_unmet_requirements(candidate, requirements)

    assert result == [
        "safe_waiting_areas",
        "well_lit_waiting_areas",
        "wifi_nearby",
        "staffed_venues_nearby",
        "open_venues_nearby",
    ]


def test_safe_areas_requirement_fails_when_ratio_is_too_low() -> None:
    candidate = make_candidate(waiting_areas_in_safe_areas_ratio=0.10)
    requirements = make_requirements(safe_areas_nearby=True)

    result = get_unmet_requirements(candidate, requirements)

    assert result == ["safe_areas_nearby"]


def test_multiple_unmet_requirements_are_returned_together() -> None:
    candidate = make_candidate(
        stairs_present=True,
        step_free_ratio=0.20,
        safe_waiting_area_count=0,
        waiting_areas_in_safe_areas_ratio=0.10,
    )
    requirements = make_requirements(
        avoid_stairs=True,
        step_free_access=True,
        safe_waiting_areas=True,
        safe_areas_nearby=True,
    )

    result = get_unmet_requirements(candidate, requirements)

    assert result == [
        "avoid_stairs",
        "step_free_access",
        "safe_waiting_areas",
        "safe_areas_nearby",
    ]


def test_no_unmet_requirements_returns_empty_list() -> None:
    candidate = make_candidate()
    requirements = make_requirements(
        avoid_stairs=True,
        step_free_access=True,
        lifts_available=True,
        ramps_available=True,
        escalators_available=True,
        safe_waiting_areas=True,
        well_lit_waiting_areas=True,
        wifi_nearby=True,
        staffed_venues_nearby=True,
        open_venues_nearby=True,
        safe_areas_nearby=True,
    )

    result = get_unmet_requirements(candidate, requirements)

    assert result == []