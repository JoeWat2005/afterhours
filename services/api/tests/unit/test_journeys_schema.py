import pytest
from pydantic import ValidationError

from app.schemas.journeys import JourneyCreate


def _ranked_route(candidate_id: str, score: float, geometry_geojson: dict | None) -> dict:
    return {
        "candidate_id": candidate_id,
        "label": f"{candidate_id} label",
        "provider": "mapbox",
        "rank": 1,
        "meets_requirements": True,
        "unmet_requirements": [],
        "is_fallback": False,
        "score": score,
        "distance_metres": 1200,
        "duration_seconds": 900,
        "geometry_geojson": geometry_geojson,
        "component_scores": {
            "safety": 0.8,
            "lighting": 0.8,
            "accessibility": 0.8,
            "transport": 0.8,
            "efficiency": 0.8,
            "places": 0.8,
        },
        "explanation": {
            "summary": "Well lit route",
            "reasons": [],
            "warnings": [],
        },
    }


def test_journey_create_resolves_selected_ranked_route() -> None:
    payload = JourneyCreate.model_validate(
        {
            "origin_label": "Old Joe",
            "destination_label": "QE Hospital",
            "selected_route_id": "route-b",
            "ranked_routes": [
                _ranked_route(
                    "route-a",
                    67.2,
                    {
                        "type": "LineString",
                        "coordinates": [[-1.95, 52.45], [-1.94, 52.46]],
                    },
                ),
                _ranked_route(
                    "route-b",
                    91.4,
                    {
                        "type": "LineString",
                        "coordinates": [[-1.96, 52.47], [-1.93, 52.48]],
                    },
                ),
            ],
        }
    )

    assert payload.resolved_score() == 91.4
    assert payload.resolved_route_geojson() == {
        "type": "LineString",
        "coordinates": [[-1.96, 52.47], [-1.93, 52.48]],
    }


def test_journey_create_rejects_unknown_selected_route_id() -> None:
    with pytest.raises(ValidationError) as exc:
        JourneyCreate.model_validate(
            {
                "origin_label": "Old Joe",
                "destination_label": "QE Hospital",
                "selected_route_id": "route-z",
                "ranked_routes": [
                    _ranked_route(
                        "route-a",
                        67.2,
                        {
                            "type": "LineString",
                            "coordinates": [[-1.95, 52.45], [-1.94, 52.46]],
                        },
                    )
                ],
            }
        )

    assert "selected_route_id was not found in ranked_routes" in str(exc.value)


def test_journey_create_accepts_selected_route_object() -> None:
    payload = JourneyCreate.model_validate(
        {
            "origin_label": "Old Joe",
            "destination_label": "QE Hospital",
            "selected_route": _ranked_route(
                "route-b",
                91.4,
                {
                    "type": "LineString",
                    "coordinates": [[-1.96, 52.47], [-1.93, 52.48]],
                },
            ),
        }
    )

    assert payload.resolved_score() == 91.4
    assert payload.resolved_route_geojson() == {
        "type": "LineString",
        "coordinates": [[-1.96, 52.47], [-1.93, 52.48]],
    }


def test_journey_create_direct_payload_accepts_geometry_geojson_alias() -> None:
    payload = JourneyCreate.model_validate(
        {
            "origin_label": "Old Joe",
            "destination_label": "QE Hospital",
            "score": 88.5,
            "geometry_geojson": {
                "type": "LineString",
                "coordinates": [[-1.95, 52.45], [-1.94, 52.46]],
            },
        }
    )

    assert payload.resolved_score() == 88.5
    assert payload.resolved_route_geojson() == {
        "type": "LineString",
        "coordinates": [[-1.95, 52.45], [-1.94, 52.46]],
    }
