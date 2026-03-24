import pytest

from app.integrations import police_client as police_api


# ----------------------------
# Unit tests (pure functions)
# ----------------------------

def test_iter_route_points_linestring():
    geometry = {
        "type": "LineString",
        "coordinates": [
            [-1.8904, 52.4862],
            [-1.8898, 52.4868],
        ],
    }

    points = police_api.iter_route_points(geometry)

    assert points == [
        (52.4862, -1.8904),
        (52.4868, -1.8898),
    ]


def test_iter_route_points_invalid_geometry():
    geometry = {
        "type": "Polygon",
        "coordinates": [],
    }

    with pytest.raises(ValueError):
        police_api.iter_route_points(geometry)


def test_sample_route_points_by_distance_keeps_edges():
    points = [
        (52.4862, -1.8904),
        (52.4864, -1.8902),
        (52.4866, -1.8900),
        (52.4868, -1.8898),
        (52.4870, -1.8896),
    ]

    sampled = police_api.sample_route_points_by_distance(
        points,
        spacing_metres=10,
        max_points=3,
    )

    assert sampled[0] == points[0]
    assert sampled[-1] == points[-1]
    assert len(sampled) <= 3


def test_route_length_metres_positive_for_simple_line():
    points = [
        (52.4862, -1.8904),
        (52.4868, -1.8898),
    ]

    result = police_api.route_length_metres(points)

    assert result > 0


def test_normalize_crime_valid():
    raw = {
        "category": "vehicle-crime",
        "month": "2024-01",
        "persistent_id": "abc123",
        "location": {
            "latitude": "52.4862",
            "longitude": "-1.8904",
            "street": {"name": "On or near Hill Street"},
        },
    }

    result = police_api._normalize_crime(raw)

    assert result == {
        "crime_id": "abc123",
        "category": "vehicle-crime",
        "month": "2024-01",
        "latitude": 52.4862,
        "longitude": -1.8904,
        "location_label": "On or near Hill Street",
        "source": "uk_police",
    }


def test_normalize_crime_missing_coordinates():
    raw = {
        "category": "vehicle-crime",
        "month": "2024-01",
        "location": {},
    }

    result = police_api._normalize_crime(raw)

    assert result is None


# ----------------------------
# Async tests (main function)
# ----------------------------

@pytest.mark.asyncio
async def test_fetch_route_crime_points_happy_path(monkeypatch):
    geometry = {
        "type": "LineString",
        "coordinates": [
            [-1.8904, 52.4862],
            [-1.8898, 52.4868],
        ],
    }

    async def mock_get_latest_crime_month(client=None):
        return "2024-01"

    async def mock_fetch_street_crimes_for_location(
        *,
        lat,
        lng,
        date=None,
        category="all-crime",
        client=None,
    ):
        return [
            {
                "category": "vehicle-crime",
                "month": "2024-01",
                "persistent_id": "crime-1",
                "location": {
                    "latitude": "52.4862",
                    "longitude": "-1.8904",
                    "street": {"name": "Hill Street"},
                },
            },
            {
                "category": "anti-social-behaviour",
                "month": "2024-01",
                "persistent_id": "crime-2",
                "location": {
                    "latitude": "52.4868",
                    "longitude": "-1.8898",
                    "street": {"name": "Broad Street"},
                },
            },
        ]

    monkeypatch.setattr(police_api, "get_latest_crime_month", mock_get_latest_crime_month)
    monkeypatch.setattr(
        police_api,
        "fetch_street_crimes_for_location",
        mock_fetch_street_crimes_for_location,
    )

    result = await police_api.fetch_route_crime_points(
        route_id="route_123",
        route_geometry_geojson=geometry,
    )

    assert result["schema_version"] == "1.0"
    assert result["route_id"] == "route_123"
    assert result["crime_month"] == "2024-01"
    assert result["point_count"] == 2
    assert len(result["points"]) == 2
    assert result["warnings"] == []


@pytest.mark.asyncio
async def test_fetch_route_crime_points_deduplicates(monkeypatch):
    geometry = {
        "type": "LineString",
        "coordinates": [
            [-1.8904, 52.4862],
            [-1.8898, 52.4868],
        ],
    }

    async def mock_get_latest_crime_month(client=None):
        return "2024-01"

    async def mock_fetch_street_crimes_for_location(**kwargs):
        return [
            {
                "category": "vehicle-crime",
                "month": "2024-01",
                "persistent_id": "same-id",
                "location": {
                    "latitude": "52.4862",
                    "longitude": "-1.8904",
                    "street": {"name": "Hill Street"},
                },
            }
        ]

    monkeypatch.setattr(police_api, "get_latest_crime_month", mock_get_latest_crime_month)
    monkeypatch.setattr(
        police_api,
        "fetch_street_crimes_for_location",
        mock_fetch_street_crimes_for_location,
    )

    result = await police_api.fetch_route_crime_points(
        route_id="route_dup",
        route_geometry_geojson=geometry,
    )

    assert result["point_count"] == 1
    assert len(result["points"]) == 1


@pytest.mark.asyncio
async def test_fetch_route_crime_points_empty(monkeypatch):
    geometry = {
        "type": "LineString",
        "coordinates": [
            [-1.8904, 52.4862],
            [-1.8898, 52.4868],
        ],
    }

    async def mock_get_latest_crime_month(client=None):
        return "2024-01"

    async def mock_fetch_street_crimes_for_location(**kwargs):
        return []

    monkeypatch.setattr(police_api, "get_latest_crime_month", mock_get_latest_crime_month)
    monkeypatch.setattr(
        police_api,
        "fetch_street_crimes_for_location",
        mock_fetch_street_crimes_for_location,
    )

    result = await police_api.fetch_route_crime_points(
        route_id="route_empty",
        route_geometry_geojson=geometry,
    )

    assert result["points"] == []
    assert result["point_count"] == 0
    assert "no_crime_data_found" in result["warnings"]
