BASE_COMPONENT_WEIGHTS = {
    "safety": 0.30,
    "lighting": 0.20,
    "accessibility": 0.20,
    "transport": 0.10,
    "efficiency": 0.10,
    "places": 0.10,
}

PREFERENCE_WEIGHT_BOOSTS = {
    "accessibility": 0.15,
    "transport": 0.10,
    "places": 0.10,
}

DEFAULT_COMPONENT_SCORE = 0.50
COMPONENT_GOOD_THRESHOLD = 0.70
ACCESSIBLE_ROUTE_MIN = 0.70
COMPONENT_INPUT_CAP = 1.0

COMPONENT_PRECISION = 4
OUTPUT_SCALE = 100.0
OUTPUT_PRECISION = 2
