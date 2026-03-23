"""
HeatmapEngine
~~~~~~~~~~~~~
Generates a scored lat/lng grid used to populate the heatmap_cells table.

Cell output is aligned to the HeatmapCell DB model:
  - bounds expressed as a WKT POLYGON string (SRID 4326) -> cell_geometry
  - totalPoints used as the raw risk_score float
  - source_count derived from the number of crimes mapped to the cell
"""

from app.services.pathfinding import CRIME_SCORING


class HeatmapEngine:
    # GPS constants for the UK (~50 m steps)
    lat_step: float = 0.00045
    lng_step: float = 0.00073

    def __init__(self) -> None:
        self.crimeScoring = CRIME_SCORING

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _normalise_crime_type(self, crime_type: str) -> str:
        """Normalises crime type strings from the UK Police API to scoring keys."""
        return crime_type.strip().lower().replace(" ", "-")

    @staticmethod
    def _bounds_to_wkt(north: float, south: float, west: float, east: float) -> str:
        """Converts a bounding box to a WKT POLYGON string (SRID 4326)."""
        return (
            f"SRID=4326;POLYGON(("
            f"{west} {south}, {east} {south}, "
            f"{east} {north}, {west} {north}, "
            f"{west} {south}"
            f"))"
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_empty_grid(self, center_lat: float, center_lng: float, size: int = 30) -> list[dict]:
        """
        Creates a size × size grid of squares centred on (center_lat, center_lng).
        Default 30×30 covers roughly 1.5 km × 1.5 km.
        """
        if size <= 0:
            raise ValueError("Grid size must be a positive integer.")

        grid: list[dict] = []
        half = size // 2  # integer division avoids floating-point drift
        start_lat = center_lat + (half * self.lat_step)
        start_lng = center_lng - (half * self.lng_step)

        for row in range(size):
            current_lat = start_lat - (row * self.lat_step)
            for col in range(size):
                current_lng = start_lng + (col * self.lng_step)
                north = current_lat
                south = current_lat - self.lat_step
                west = current_lng
                east = current_lng + self.lng_step

                square: dict = {
                    "id": f"{row}_{col}",
                    "bounds": {
                        "north": north,
                        "south": south,
                        "west": west,
                        "east": east,
                    },
                    # DB-aligned fields
                    "cell_geometry_wkt": self._bounds_to_wkt(north, south, west, east),
                    "risk_score": 0.0,
                    "source_count": 0,
                    # Internal working fields (not persisted)
                    "crimes_list": [],
                }
                grid.append(square)

        return grid

    def score_grid_square(self, crimes_in_square: list[str], is_low_light: bool) -> dict:
        """
        Calculates the risk score for a single grid square and returns it along
        with colour/pattern metadata for accessibility overlays.

        Returns a dict with: risk_score (float), color (str), pattern (str).
        """
        total_points = 0
        for crime_type in crimes_in_square:
            normalised = self._normalise_crime_type(crime_type)
            total_points += self.crimeScoring.get(normalised, 1)

        if is_low_light:
            total_points += 5

        if total_points == 0:
            return {"risk_score": 0.0, "color": "clear", "pattern": "none"}
        elif total_points <= 5:
            return {"risk_score": float(total_points), "color": "yellow", "pattern": "dots"}
        elif total_points <= 15:
            return {"risk_score": float(total_points), "color": "orange", "pattern": "diagonal-lines"}
        else:
            return {"risk_score": float(total_points), "color": "red", "pattern": "crosshatch"}

    def find_square_for_point(self, grid: list[dict], lat: float, lng: float) -> dict | None:
        """
        Finds the grid square that contains (lat, lng).
        Returns None if the point falls outside the grid.

        Uses half-open intervals [south, north) and [west, east) to avoid
        double-counting points on shared cell boundaries.
        """
        for square in grid:
            b = square["bounds"]
            if b["south"] <= lat < b["north"] and b["west"] <= lng < b["east"]:
                return square
        return None

    def populate_grid(
        self,
        grid: list[dict],
        crimes: list[dict],
        lighting_data: set[str],
    ) -> list[dict]:
        """
        Maps crimes onto grid squares and scores each square.

        Crime object format:
            {"type": "violent-crime", "lat": 52.4862, "lng": -1.8904}

        lighting_data is a set of square IDs (e.g. {"12_4", "3_17"})
        that are considered low-light.

        Returns the grid with risk_score, source_count, and WKT geometry
        populated — ready to be upserted into heatmap_cells.
        """
        # Map crimes onto squares (empty crimes list is valid — returns unscored grid)
        for crime in crimes:
            square = self.find_square_for_point(grid, crime["lat"], crime["lng"])
            if square is None:
                continue  # crime falls outside the current window
            square["crimes_list"].append(crime["type"])

        # Score every square
        for square in grid:
            is_low_light = square["id"] in lighting_data
            result = self.score_grid_square(square["crimes_list"], is_low_light)
            square["risk_score"] = result["risk_score"]
            square["source_count"] = len(square["crimes_list"])
            # Keep colour/pattern on the dict for callers that want it
            square["color"] = result["color"]
            square["pattern"] = result["pattern"]

        return grid
