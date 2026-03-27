from app.core.config import get_settings

# we want to calculate the scores for each route, and then find a way to rank it

#this scores safety, speed and accessibility
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

#-- must requirements - must be met for user
def must_requirements(route_candidate: dict[str, float], requirements: dict[str, bool],) -> tuple[bool, list[str]]:
    failures = []
    if requirements.get("step_free") and route_candidate["step_free_ratio"] < 1.0:
        failures.append(f"Route is not step-free.")
    if requirements.get("avoid_incidents") and route_candidate["incident_density"] > 0:
        failures.append(f"Route has incidents.")
    return len(failures) == 0, failures # creates a failure string


#-- making weights to avoid 
def make_weights(preferneces: dict[str, bool]) -> tuple[float, float, float]:
    settings = get_settings()
    weight_safety = settings.route_score_weight_safety
    weight_speed = settings.route_score_weight_speed
    weight_accessibility = settings.route_score_weight_accessibility

    boost = 0.1
    if preferneces.get("prefer_avoid_incidents"):
        weight_safety += boost
    if preferneces.get("prefer_speed"): 
        weight_speed += boost
    if preferneces.get("prefer_accessibility"):
        weight_accessibility += boost

    total_weight = weight_safety + weight_speed + weight_accessibility
    return weight_safety / total_weight, weight_speed / total_weight, weight_accessibility / total_weight

def rank_routes(route_candidates: list[dict[str, float]], requirements: dict[str, bool], preferences: dict[str, bool]) -> list[tuple[float, dict[str, float], list[str]]]:
    ranked_routes = []
    excluded_routes = [] # routes that fail, may not need to be saved

    for route in route_candidates:
        passed, failed = must_requirements(route, requirements)
        if not passed:
            excluded_routes.append((route, failed))
            continue
        score, explanation = score_route(route)
        ranked_routes.append((score, route, explanation))

    ranked_routes.sort(key=lambda x: x[0], reverse=True)  # sort
    return ranked_routes, excluded_routes










