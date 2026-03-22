from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.common import LonLat


class RouteLocation(LonLat):
    model_config = ConfigDict(extra="forbid")

    label: str | None = Field(default=None, min_length=1, max_length=128)


class RoutePreferences(BaseModel):
    model_config = ConfigDict(extra="forbid")

    accessible_routes: bool = False
    transport_tonight: bool = False
    nearby_safe_places: bool = False


class RouteCandidateFeatures(BaseModel):
    model_config = ConfigDict(extra="forbid")

    incident_density: float | None = Field(default=None, ge=0)
    lighting_score: float | None = Field(default=None, ge=0, le=1)
    step_free_ratio: float | None = Field(default=None, ge=0, le=1)
    night_transport_score: float | None = Field(default=None, ge=0, le=1)
    open_safe_places_count: int | None = Field(default=None, ge=0)
    report_density: float | None = Field(default=None, ge=0)


class RouteCandidateInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_id: str = Field(min_length=1, max_length=64)
    label: str | None = Field(default=None, min_length=1, max_length=128)
    provider: str | None = Field(default=None, min_length=1, max_length=64)
    distance_metres: int = Field(gt=0)
    duration_seconds: int = Field(gt=0)
    geometry_geojson: dict | None = None
    features: RouteCandidateFeatures


class RouteComponentScores(BaseModel):
    model_config = ConfigDict(extra="forbid")

    safety: float = Field(ge=0, le=1)
    lighting: float = Field(ge=0, le=1)
    accessibility: float = Field(ge=0, le=1)
    transport: float = Field(ge=0, le=1)
    efficiency: float = Field(ge=0, le=1)
    places: float = Field(ge=0, le=1)


class RouteExplanation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str
    reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class RankedRouteResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_id: str
    label: str | None = None
    provider: str | None = None
    rank: int = Field(gt=0)
    score: float = Field(ge=0, le=100)
    distance_metres: int = Field(gt=0)
    duration_seconds: int = Field(gt=0)
    geometry_geojson: dict | None = None
    component_scores: RouteComponentScores
    explanation: RouteExplanation


class RouteScoreRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    origin: RouteLocation
    destination: RouteLocation
    depart_at: datetime
    preferences: RoutePreferences = Field(default_factory=RoutePreferences)
    route_candidates: list[RouteCandidateInput] = Field(min_length=1)

    @field_validator("depart_at")
    @classmethod
    def check_depart_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
            raise ValueError("depart_at must include a timezone offset")
        return value

    @model_validator(mode="after")
    def check_candidate_ids(self) -> "RouteScoreRequest":
        candidate_ids = [candidate.candidate_id for candidate in self.route_candidates]
        if len(candidate_ids) != len(set(candidate_ids)):
            raise ValueError("route candidate ids must be unique")
        return self


class RouteScoreResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    selected_route_id: str
    ranked_routes: list[RankedRouteResult] = Field(min_length=1)
    warnings: list[str] = Field(default_factory=list)


class SafetyReportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: str
    summary: str
    description: str
    latitude: float
    longitude: float


class SafetyReportValidationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    accepted: bool
    moderation_flags: list[str]
