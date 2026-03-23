# Route Crime Heatmap: developer notes for Sayed

This module does **not** generate a heatmap by itself. It fetches and normalizes **crime points** along a route. Your heatmap layer should consume the returned `points` list and decide how to aggregate, weight, and render those points.

Relevant source files:
- `police_api.py`
- `police_api_config.py`
- `test_police_api.py`

## What this service returns

The main entry point is:

```python
await fetch_route_crime_points(
    route_geometry_geojson=..., 
    route_id="...",
    date="2024-01",          # optional
    category="all-crime",    # optional
    max_route_points=12        # optional
)
```

It returns a `RouteCrimeResponse` shaped like:

```python
{
    "schema_version": "1.0",
    "route_id": "route_123",
    "crime_source": "uk_police",
    "crime_month": "2024-01",
    "route_geometry_geojson": {...},
    "points": [
        {
            "crime_id": "abc123",
            "category": "vehicle-crime",
            "month": "2024-01",
            "latitude": 52.4862,
            "longitude": -1.8904,
            "location_label": "On or near Hill Street",
            "source": "uk_police"
        }
    ],
    "point_count": 1,
    "warnings": []
}
```

## Heatmap flow

The current pipeline is:

1. **Receive a route GeoJSON**
   - Supported geometry types: `LineString` and `MultiLineString`
   - GeoJSON coordinates come in as `[lng, lat]`

2. **Extract route coordinates**
   - `_iter_route_points()` converts them into `(lat, lng)` tuples
   - This keeps the rest of the code consistent with the Police API query params

3. **Downsample the route**
   - `_sample_route_points()` reduces the route to at most `max_route_points` samples
   - It always tries to keep the first and last route point
   - This exists to avoid making too many Police API calls

4. **Query crimes near each sampled point**
   - `fetch_street_crimes_for_location()` calls the UK Police street crime endpoint
   - If no `date` is provided, `get_latest_crime_month()` resolves the latest available month first

5. **Deduplicate crimes across route samples**
   - The same crime may be returned for multiple nearby sampled route points
   - `_crime_identity()` prefers `persistent_id`
   - If no `persistent_id` exists, it builds a fallback composite key from category/month/id/street/lat/lng

6. **Normalize into a stable point schema**
   - `_normalize_crime()` converts raw Police API records into `CrimePoint`
   - Records with missing or invalid coordinates are skipped

7. **Return point data**
   - The function returns clean, deduplicated points
   - Your heatmap code should build the visual density layer from those points

## Important design detail

This service is deliberately split into two layers:

- **data-fetching layer**: `fetch_route_crime_points()`
- **visualization / aggregation layer**: your heatmap code

That is good separation. It means you can reuse this service for:
- a frontend heatmap
- a backend grid aggregation
- crime clustering
- category-specific weighting
- route risk scoring

## What Sayed should do next for a crime heatmap

For a crime heatmap, use `response["points"]` as the raw inputs.

### Simplest version

If the mapping library supports point-based heatmaps directly, pass each point as:

```python
[
    {"lat": p["latitude"], "lng": p["longitude"], "weight": 1}
    for p in response["points"]
]
```

### Better version: weighted heatmap

Give different crime categories different weights. Example:

```python
CRIME_WEIGHTS = {
    "violent-crime": 3,
    "robbery": 3,
    "burglary": 2,
    "vehicle-crime": 2,
    "anti-social-behaviour": 1,
}

weight = CRIME_WEIGHTS.get(point["category"], 1)
```

That lets the heatmap reflect severity instead of just raw counts.

### Alternative version: build grid cells first

If you want more control, bin points into cells before rendering.

Example idea:

1. round lat/lng into a small cell size
2. group crimes by cell
3. sum count or weighted score per cell
4. render each cell as intensity

Pseudo-code:

```python
from collections import defaultdict

cell_size = 0.001
cells = defaultdict(int)

for point in response["points"]:
    cell_lat = round(point["latitude"] / cell_size) * cell_size
    cell_lng = round(point["longitude"] / cell_size) * cell_size
    cells[(cell_lat, cell_lng)] += 1
```

Use that if you need a stable backend-friendly heatmap representation.

## Warnings you should respect

The response may contain warnings:

- `some_crimes_missing_coordinates`
  - some API records were skipped because they could not be mapped
- `no_crime_data_found`
  - no valid points were returned for that route/month/category

Your heatmap code should handle both without failing.

## Current test coverage

The existing tests cover these basics well:

### Covered

- `LineString` extraction in `_iter_route_points()`
- invalid geometry type rejection
- route sampling keeps first and last points
- crime normalization for valid input
- crime normalization skips missing coordinates
- happy path for `fetch_route_crime_points()`
- deduplication across multiple route samples
- empty result behavior and warning emission

## Are the tests adequate?

They are a **solid start**, but not fully adequate if this code is going to be relied on in production.

### Why they are decent

They verify the core behavior of the module:
- geometry parsing
- sampling
- normalization
- deduplication
- empty/happy-path output contract

That means the main shape of the logic is protected.

### What is still missing

#### 1. `MultiLineString` is not tested

The implementation supports `MultiLineString`, but there is no test for it.

Add a test to verify:
- points from all lines are flattened in order
- invalid nested coordinates are skipped correctly

#### 2. Missing coordinates in geometry are not tested

There is a code path that raises when coordinates are missing or no usable points exist.

Add tests for:
- `{"type": "LineString"}` with no `coordinates`
- `{"type": "LineString", "coordinates": []}`
- malformed coordinate pairs

#### 3. Sampling edge cases are not covered

`_sample_route_points()` has behavior that should be pinned down more tightly.

Add tests for:
- `len(points) <= max_points`
- `max_points < 2`
- duplicate route points
- very long routes to confirm size never grows unexpectedly

#### 4. `_crime_identity()` fallback behavior is untested

This matters because deduplication depends on it.

Add tests for:
- using `persistent_id` when present
- falling back when `persistent_id` is blank or missing
- producing stable keys from partial raw crime records

#### 5. Invalid numeric coordinates from Police API are not tested

`_normalize_crime()` catches bad lat/lng parsing.

Add tests where:
- latitude is `"abc"`
- longitude is `None`
- location is malformed

#### 6. Warning path for skipped crimes is not tested

You test `no_crime_data_found`, but not the case where some crimes are skipped and others succeed.

Add a test where:
- one crime is valid
- one crime is missing coordinates
- result contains points plus `some_crimes_missing_coordinates`

#### 7. API failure behavior is untested

There are no tests for upstream HTTP or payload failures.

Add tests for:
- `get_latest_crime_month()` receiving an empty list
- invalid month format
- `fetch_street_crimes_for_location()` receiving a non-list payload
- HTTP errors bubbling up

#### 8. The test file may not run as uploaded

Right now the uploaded test imports this:

```python
from app.services import police_api
```

But as uploaded here, the files are not inside an `app/services` package, so test discovery fails unless the package structure exists in the real project.

If this path is correct in the real repo, that is fine. If not, the import should be changed.

## Suggested extra tests

A good next set would be:

```python
def test_iter_route_points_multilinestring(): ...
def test_iter_route_points_missing_coordinates(): ...
def test_iter_route_points_no_usable_points(): ...
def test_sample_route_points_small_max_points(): ...
def test_crime_identity_falls_back_without_persistent_id(): ...
def test_normalize_crime_invalid_latitude(): ...

@pytest.mark.asyncio
async def test_fetch_route_crime_points_warns_on_partial_skips(...): ...

@pytest.mark.asyncio
async def test_get_latest_crime_month_invalid_payload(...): ...

@pytest.mark.asyncio
async def test_fetch_street_crimes_for_location_invalid_payload(...): ...
```

## Practical advice for the crime heatmap

For Sayed's next step:

- Treat `points` as the source of truth
- Do not query the Police API directly from the heatmap layer
- Keep heatmap weighting separate from fetching
- Preserve `category` in case product wants per-crime filtering later
- Consider exposing both:
  - raw points
  - aggregated heatmap cells

That gives flexibility for both frontend and backend consumers.

## Bottom line

- The current service is a good foundation for a crime heatmap
- The existing tests are **good but not sufficient** for production confidence
- The biggest gaps are `MultiLineString`, fallback dedupe identity, partial-skip warnings, and upstream failure handling
- Sayed can safely build the next heatmap layer on top of the returned `points`
