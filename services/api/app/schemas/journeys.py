from datetime import datetime
from uuid import UUID

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, model_validator

from app.schemas.routes import RankedRouteResult


class JourneySelectedRoute(BaseModel):
    model_config = ConfigDict(extra="ignore")

    candidate_id: str | None = Field(default=None, min_length=1, max_length=64)
    score: float
    geometry_geojson: dict


class JourneyCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: UUID | None = None
    origin_label: str = Field(min_length=1, max_length=128)
    destination_label: str = Field(min_length=1, max_length=128)

    # New flow: select one route from RouteScoreResponse.ranked_routes.
    selected_route: JourneySelectedRoute | None = None
    selected_route_id: str | None = Field(default=None, min_length=1, max_length=64)
    ranked_routes: list[RankedRouteResult] | None = None

    # Backward-compatible direct payload shape.
    score: float | None = None
    route_geojson: dict | None = Field(
        default=None,
        validation_alias=AliasChoices("route_geojson", "geometry_geojson"),
    )

    @model_validator(mode="after")
    def validate_payload_shape(self) -> "JourneyCreate":
        if self.selected_route is not None:
            if self.selected_route.geometry_geojson is None:
                raise ValueError(
                    "selected route must include geometry_geojson for persistence"
                )
            return self

        has_selection_payload = (
            self.selected_route_id is not None or self.ranked_routes is not None
        )

        if has_selection_payload:
            if self.selected_route_id is None:
                raise ValueError(
                    "selected_route_id is required when ranked_routes is provided"
                )
            if not self.ranked_routes:
                raise ValueError(
                    "ranked_routes must include at least one route when "
                    "selected_route_id is provided"
                )

            selected_route = self.get_selected_route()
            if selected_route is None:
                raise ValueError("selected_route_id was not found in ranked_routes")
            if selected_route.geometry_geojson is None:
                raise ValueError(
                    "selected route must include geometry_geojson for persistence"
                )
            return self

        if self.score is None:
            raise ValueError(
                "score is required when using the direct route payload shape"
            )
        if self.route_geojson is None:
            raise ValueError(
                "route_geojson (or geometry_geojson) is required when using the "
                "direct route payload shape"
            )

        return self

    def get_selected_route(self) -> RankedRouteResult | None:
        if self.selected_route_id is None or not self.ranked_routes:
            return None

        return next(
            (
                route
                for route in self.ranked_routes
                if route.candidate_id == self.selected_route_id
            ),
            None,
        )

    def resolved_score(self) -> float:
        if self.selected_route is not None:
            return self.selected_route.score

        selected_route = self.get_selected_route()
        if selected_route is not None:
            return selected_route.score
        if self.score is None:
            raise ValueError("score could not be resolved from payload")
        return self.score

    def resolved_route_geojson(self) -> dict:
        if self.selected_route is not None:
            if self.selected_route.geometry_geojson is None:
                raise ValueError("selected route geometry is missing")
            return self.selected_route.geometry_geojson

        selected_route = self.get_selected_route()
        if selected_route is not None:
            if selected_route.geometry_geojson is None:
                raise ValueError("selected route geometry is missing")
            return selected_route.geometry_geojson
        if self.route_geojson is None:
            raise ValueError("route_geojson could not be resolved from payload")
        return self.route_geojson


class JourneyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID | None
    origin_label: str
    destination_label: str
    score: float
    route_geojson: dict
    created_at: datetime
