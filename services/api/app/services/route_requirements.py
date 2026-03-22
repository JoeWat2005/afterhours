from app.core import route_scoring_config as scoring_config
from app.schemas.routes import RouteCandidateInput, RouteRequirements


def get_unmet_requirements(
    candidate: RouteCandidateInput,
    requirements: RouteRequirements,
) -> list[str]:
    unmet_requirements: list[str] = []

    accessibility = requirements.accessibility
    accessibility_features = candidate.features.accessibility
    waiting_areas = requirements.waiting_areas
    waiting_area_features = candidate.features.waiting_areas

    if accessibility.avoid_stairs and accessibility_features.stairs_present is not False:
        unmet_requirements.append("avoid_stairs")
    if (
        accessibility.step_free_access
        and not _meets_ratio_requirement(
            accessibility_features.step_free_ratio,
            scoring_config.ROUTE_REQUIREMENT_THRESHOLDS["minimum_step_free_ratio"],
        )
    ):
        unmet_requirements.append("step_free_access")
    if (
        accessibility.lifts_available
        and not _meets_ratio_requirement(
            accessibility_features.lift_coverage_ratio,
            scoring_config.ROUTE_REQUIREMENT_THRESHOLDS["minimum_lift_coverage_ratio"],
        )
    ):
        unmet_requirements.append("lifts_available")
    if (
        accessibility.ramps_available
        and not _meets_ratio_requirement(
            accessibility_features.ramp_coverage_ratio,
            scoring_config.ROUTE_REQUIREMENT_THRESHOLDS["minimum_ramp_coverage_ratio"],
        )
    ):
        unmet_requirements.append("ramps_available")
    if (
        accessibility.escalators_available
        and not _meets_ratio_requirement(
            accessibility_features.escalator_coverage_ratio,
            scoring_config.ROUTE_REQUIREMENT_THRESHOLDS["minimum_escalator_coverage_ratio"],
        )
    ):
        unmet_requirements.append("escalators_available")

    if (
        waiting_areas.safe_waiting_areas
        and not _meets_count_requirement(
            waiting_area_features.safe_waiting_area_count,
            scoring_config.ROUTE_REQUIREMENT_THRESHOLDS["minimum_safe_waiting_area_count"],
        )
    ):
        unmet_requirements.append("safe_waiting_areas")
    if (
        waiting_areas.well_lit_waiting_areas
        and not _meets_count_requirement(
            waiting_area_features.well_lit_waiting_area_count,
            scoring_config.ROUTE_REQUIREMENT_THRESHOLDS[
                "minimum_well_lit_waiting_area_count"
            ],
        )
    ):
        unmet_requirements.append("well_lit_waiting_areas")
    if (
        waiting_areas.wifi_nearby
        and not _meets_count_requirement(
            waiting_area_features.wifi_access_point_count,
            scoring_config.ROUTE_REQUIREMENT_THRESHOLDS["minimum_wifi_access_point_count"],
        )
    ):
        unmet_requirements.append("wifi_nearby")
    if (
        waiting_areas.staffed_venues_nearby
        and not _meets_count_requirement(
            waiting_area_features.staffed_venue_count,
            scoring_config.ROUTE_REQUIREMENT_THRESHOLDS["minimum_staffed_venue_count"],
        )
    ):
        unmet_requirements.append("staffed_venues_nearby")
    if (
        waiting_areas.open_venues_nearby
        and not _meets_count_requirement(
            waiting_area_features.open_venue_count,
            scoring_config.ROUTE_REQUIREMENT_THRESHOLDS["minimum_open_venue_count"],
        )
    ):
        unmet_requirements.append("open_venues_nearby")
    if (
        waiting_areas.safe_areas_nearby
        and not _meets_ratio_requirement(
            waiting_area_features.waiting_areas_in_safe_areas_ratio,
            scoring_config.ROUTE_REQUIREMENT_THRESHOLDS[
                "minimum_waiting_area_safe_ratio"
            ],
        )
    ):
        unmet_requirements.append("safe_areas_nearby")

    return unmet_requirements


def _meets_ratio_requirement(value: float | None, minimum: float) -> bool:
    return value is not None and value >= minimum


def _meets_count_requirement(value: int | None, minimum: float) -> bool:
    return value is not None and value >= minimum
