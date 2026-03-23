from app.core.config import get_settings

# we want to calculate the scores for each route, and then find a way to rank it

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

# safety ranking session
def rank_routes(route_candidates: list[dict[str, float]]) -> list[tuple[float, dict[str, float], list[str]]]:
    scored_routes = []
    for route in route_candidates:
        score, explanation = score_route(route)
        scored_routes.append((score, route, explanation))
    scored_routes.sort(key=lambda x: x[0], reverse=True)  # sort by score descending
    return scored_routes

# need ranking for scores and different types 
