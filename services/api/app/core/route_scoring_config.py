from typing import Final

from app.schemas.routes import RouteBiasMode

RouteWeightProfile = dict[str, float]


BIAS_MODE_WEIGHT_PROFILES: Final[dict[RouteBiasMode, RouteWeightProfile]] = {
    RouteBiasMode.MAXIMUM_SAFETY: {
        "safety": 0.35,
        "lighting": 0.22,
        "accessibility": 0.16,
        "transport": 0.07,
        "efficiency": 0.06,
        "places": 0.14,
    },
    RouteBiasMode.BALANCED: {
        "safety": 0.30,
        "lighting": 0.20,
        "accessibility": 0.20,
        "transport": 0.10,
        "efficiency": 0.10,
        "places": 0.10,
    },
    RouteBiasMode.MOST_EFFICIENCY: {
        "safety": 0.20,
        "lighting": 0.10,
        "accessibility": 0.15,
        "transport": 0.10,
        "efficiency": 0.35,
        "places": 0.10,
    },
}

# Soft preferences only nudge the ranking.
SOFT_PREFERENCE_BOOSTS: Final[dict[str, RouteWeightProfile]] = {
    "accessibility": {
        "accessibility": 0.15,
    },
    "waiting_areas": {
        "places": 0.10,
    },
}

ROUTE_REQUIREMENT_THRESHOLDS: Final[dict[str, float]] = {
    "minimum_step_free_ratio": 0.70,
    "minimum_lift_coverage_ratio": 0.50,
    "minimum_ramp_coverage_ratio": 0.50,
    "minimum_escalator_coverage_ratio": 0.50,
    "minimum_safe_waiting_area_count": 1,
    "minimum_well_lit_waiting_area_count": 1,
    "minimum_wifi_access_point_count": 1,
    "minimum_staffed_venue_count": 1,
    "minimum_open_venue_count": 1,
    "minimum_waiting_area_safe_ratio": 0.70,
}

ROUTE_SCORING_DEFAULTS: Final[dict[str, float | int]] = {
    "default_component_score": 0.50,
    "component_good_threshold": 0.70,
    "component_input_cap": 1.0,
    "component_precision": 4,
    "output_scale": 100.0,
    "output_precision": 2,
}

ROUTE_TIE_BREAK_ORDER: Final[tuple[str, ...]] = (
    "warning_count",
    "duration_seconds",
    "distance_metres",
    "candidate_id",
)
