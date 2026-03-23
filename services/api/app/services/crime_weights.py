CRIME_SCORING: dict[str, int] = {
    "violent-crime": 10,
    "sexual-offences": 10,
    "possession-of-weapons": 10,
    "robbery": 5,
    "theft-from-the-person": 5,
    "public-order": 3,
    "drugs": 3,
    "anti-social-behaviour": 2,
    "burglary": 2,
    "vehicle-crime": 2,
    "criminal-damage-arson": 2,
    "shoplifting": 1,
    "bicycle-theft": 1,
    "other-theft": 1,
    "other-crime": 1,
}


def normalize_crime_category(category: str | None) -> str:
    if not category:
        return "other-crime"
    return category.strip().lower().replace(" ", "-")


def get_crime_weight(category: str | None) -> int:
    return CRIME_SCORING.get(normalize_crime_category(category), 1)