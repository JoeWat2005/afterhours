from app.schemas.routes import RankedRouteResult
from app.services.route_ranker import rank_routes


def make_ranked_route(
    candidate_id: str,
    *,
    score: float = 80.0,
    meets_requirements: bool = True,
    is_fallback: bool = False,
    warnings: list[str] | None = None,
    duration_seconds: int = 800,
    distance_metres: int = 1000,
) -> RankedRouteResult:
    return RankedRouteResult.model_validate(
        {
            "candidate_id": candidate_id,
            "label": candidate_id.replace("-", " ").title(),
            "provider": "mapbox",
            "rank": 1,
            "meets_requirements": meets_requirements,
            "unmet_requirements": [] if meets_requirements else ["step_free_access"],
            "is_fallback": is_fallback,
            "score": score,
            "distance_metres": distance_metres,
            "duration_seconds": duration_seconds,
            "component_scores": {
                "safety": 0.8,
                "lighting": 0.8,
                "accessibility": 0.8,
                "transport": 0.8,
                "efficiency": 0.8,
                "places": 0.8,
            },
            "explanation": {
                "summary": f"{candidate_id} summary",
                "reasons": ["fairly balanced overall"],
                "warnings": warnings or [],
            },
        }
    )


def test_rank_routes_without_requirements_sorts_by_score_descending() -> None:
    routes = [
        make_ranked_route("route-b", score=70.0),
        make_ranked_route("route-a", score=90.0),
    ]

    ranked_routes, requirement_matches_found = rank_routes(
        routes,
        requirements_applied=False,
    )

    assert requirement_matches_found is True
    assert [route.candidate_id for route in ranked_routes] == ["route-a", "route-b"]
    assert all(route.is_fallback is False for route in ranked_routes)


def test_matching_routes_rank_ahead_of_fallback_routes_when_requirements_apply() -> None:
    routes = [
        make_ranked_route(
            "fallback-better-score",
            score=95.0,
            meets_requirements=False,
        ),
        make_ranked_route(
            "matching-lower-score",
            score=80.0,
            meets_requirements=True,
        ),
    ]

    ranked_routes, requirement_matches_found = rank_routes(
        routes,
        requirements_applied=True,
    )

    assert requirement_matches_found is True
    assert [route.candidate_id for route in ranked_routes] == [
        "matching-lower-score",
        "fallback-better-score",
    ]
    assert ranked_routes[0].is_fallback is False
    assert ranked_routes[1].is_fallback is True


def test_when_no_routes_meet_requirements_all_routes_become_fallback() -> None:
    routes = [
        make_ranked_route("route-a", score=90.0, meets_requirements=False),
        make_ranked_route("route-b", score=80.0, meets_requirements=False),
    ]

    ranked_routes, requirement_matches_found = rank_routes(
        routes,
        requirements_applied=True,
    )

    assert requirement_matches_found is False
    assert [route.candidate_id for route in ranked_routes] == ["route-a", "route-b"]
    assert all(route.is_fallback is True for route in ranked_routes)
    assert all(route.meets_requirements is False for route in ranked_routes)


def test_tie_break_prefers_fewer_warnings() -> None:
    routes = [
        make_ranked_route(
            "more-warnings",
            score=85.0,
            warnings=["missing_lighting_data", "missing_transport_data"],
        ),
        make_ranked_route(
            "fewer-warnings",
            score=85.0,
            warnings=["missing_lighting_data"],
        ),
    ]

    ranked_routes, _ = rank_routes(routes, requirements_applied=False)

    assert [route.candidate_id for route in ranked_routes] == [
        "fewer-warnings",
        "more-warnings",
    ]


def test_tie_break_then_prefers_shorter_duration() -> None:
    routes = [
        make_ranked_route(
            "slower-route",
            score=85.0,
            warnings=[],
            duration_seconds=900,
            distance_metres=1000,
        ),
        make_ranked_route(
            "faster-route",
            score=85.0,
            warnings=[],
            duration_seconds=700,
            distance_metres=1000,
        ),
    ]

    ranked_routes, _ = rank_routes(routes, requirements_applied=False)

    assert [route.candidate_id for route in ranked_routes] == [
        "faster-route",
        "slower-route",
    ]


def test_tie_break_then_prefers_shorter_distance() -> None:
    routes = [
        make_ranked_route(
            "longer-route",
            score=85.0,
            warnings=[],
            duration_seconds=800,
            distance_metres=1200,
        ),
        make_ranked_route(
            "shorter-route",
            score=85.0,
            warnings=[],
            duration_seconds=800,
            distance_metres=900,
        ),
    ]

    ranked_routes, _ = rank_routes(routes, requirements_applied=False)

    assert [route.candidate_id for route in ranked_routes] == [
        "shorter-route",
        "longer-route",
    ]


def test_final_tie_break_is_candidate_id_for_stable_ordering() -> None:
    routes = [
        make_ranked_route(
            "route-b",
            score=85.0,
            warnings=[],
            duration_seconds=800,
            distance_metres=1000,
        ),
        make_ranked_route(
            "route-a",
            score=85.0,
            warnings=[],
            duration_seconds=800,
            distance_metres=1000,
        ),
    ]

    ranked_routes, _ = rank_routes(routes, requirements_applied=False)

    assert [route.candidate_id for route in ranked_routes] == [
        "route-a",
        "route-b",
    ]