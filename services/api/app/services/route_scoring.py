from app.core.config import get_settings


def score_route(route_candidate: dict[str, float]) -> tuple[float, list[str]]:
    settings = get_settings()

    safety_component = (1 - min(route_candidate["incident_density"], 1.0)) * settings.route_score_weight_safety
    speed_component = min(1_000 / route_candidate["distance_metres"], 1.0) * settings.route_score_weight_speed
    accessibility_component = route_candidate["step_free_ratio"] * settings.route_score_weight_accessibility

    score = round((safety_component + speed_component + accessibility_component) * 100, 2)
    explanation = [
        f"Safety weighting applied at {settings.route_score_weight_safety:.0%}.",
        f"Speed weighting applied at {settings.route_score_weight_speed:.0%}.",
        f"Accessibility weighting applied at {settings.route_score_weight_accessibility:.0%}.",
    ]
    return score, explanation
