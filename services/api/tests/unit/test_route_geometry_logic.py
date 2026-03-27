import pytest
from app.services.route_geometry import (
    iter_route_points,
    haversine_metres,
    route_length_metres,
    sample_route_points_by_distance,
)

def test_iter_route_points_linestring():
    geojson = {
        "type": "LineString",
        "coordinates": [[-1.8904, 52.4862], [-1.8905, 52.4863]]
    }
    points = iter_route_points(geojson)
    assert len(points) == 2
    assert points[0] == (52.4862, -1.8904)
    assert points[1] == (52.4863, -1.8905)

def test_iter_route_points_multilinestring():
    geojson = {
        "type": "MultiLineString",
        "coordinates": [
            [[-1.8904, 52.4862], [-1.8905, 52.4863]],
            [[-1.8906, 52.4864], [-1.8907, 52.4865]]
        ]
    }
    points = iter_route_points(geojson)
    assert len(points) == 4
    assert points[0] == (52.4862, -1.8904)
    assert points[-1] == (52.4865, -1.8907)

def test_iter_route_points_invalid_type():
    with pytest.raises(ValueError, match="LineString or MultiLineString"):
        iter_route_points({"type": "Point", "coordinates": [0, 0]})

def test_haversine_metres_zero_distance():
    a = (52.4862, -1.8904)
    assert haversine_metres(a, a) == 0.0

def test_route_length_metres():
    points = [
        (52.4530, -1.9367),
        (52.4894, -1.9401)
    ]
    # This was ~4.06 km in our earlier hospital test
    length = route_length_metres(points)
    assert 4000 < length < 4200

def test_sample_route_points_by_distance_basic():
    # 3 points, spacing 2000m, total ~4060m
    points = [
        (52.4530, -1.9367),
        (52.4712, -1.9384), # midway
        (52.4894, -1.9401)
    ]
    sampled = sample_route_points_by_distance(points, spacing_metres=2000, max_points=10)
    # Should keep first, approximately midway, and last
    assert len(sampled) >= 3
    assert sampled[0] == points[0]
    assert sampled[-1] == points[-1]

def test_sample_route_points_by_distance_max_limit():
    points = [(i*0.01, i*0.01) for i in range(100)]
    sampled = sample_route_points_by_distance(points, spacing_metres=1, max_points=10)
    assert len(sampled) <= 10
    assert sampled[0] == points[0]
    assert sampled[-1] == points[-1]
