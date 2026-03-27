from app.services.route_safety import get_crime_weight, normalize_crime_category


def test_normalize_crime_category_lowercases_and_hyphenates() -> None:
    assert normalize_crime_category("  Violent Crime  ") == "violent-crime"


def test_normalize_crime_category_returns_other_crime_for_none() -> None:
    assert normalize_crime_category(None) == "other-crime"


def test_get_crime_weight_returns_expected_weight_for_known_category() -> None:
    assert get_crime_weight("violent-crime") == 10
    assert get_crime_weight("robbery") == 6
    assert get_crime_weight("anti-social-behaviour") == 1


def test_get_crime_weight_normalizes_before_lookup() -> None:
    assert get_crime_weight(" Sexual Offences ") == 10


def test_get_crime_weight_defaults_to_one_for_unknown_category() -> None:
    assert get_crime_weight("totally-unknown-category") == 1


def test_get_crime_weight_returns_other_crime_weight_for_none() -> None:
    assert get_crime_weight(None) == 1