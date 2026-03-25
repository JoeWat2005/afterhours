from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.route_risk_config import ReportSeverity
from app.schemas.common import LonLat


class RouteLocation(LonLat):
    model_config = ConfigDict(extra="forbid")

    label: str | None = Field(default=None, min_length=1, max_length=128)


class RouteBiasMode(str, Enum):
    MAXIMUM_SAFETY = "maximum_safety"
    BALANCED = "balanced"
    MOST_EFFICIENCY = "most_efficiency"


class RouteAccessibilityChoices(BaseModel):
    model_config = ConfigDict(extra="forbid")

    avoid_stairs: bool = False
    step_free_access: bool = False
    lifts_available: bool = False
    ramps_available: bool = False
    escalators_available: bool = False

    @property
    def enabled(self) -> bool:
        return any(
            (
                self.avoid_stairs,
                self.step_free_access,
                self.lifts_available,
                self.ramps_available,
                self.escalators_available,
            )
        )


class RouteWaitingAreaChoices(BaseModel):
    model_config = ConfigDict(extra="forbid")

    safe_waiting_areas: bool = False
    well_lit_waiting_areas: bool = False
    wifi_nearby: bool = False
    staffed_venues_nearby: bool = False
    open_venues_nearby: bool = False
    safe_areas_nearby: bool = False

    @property
    def enabled(self) -> bool:
        return any(
            (
                self.safe_waiting_areas,
                self.well_lit_waiting_areas,
                self.wifi_nearby,
                self.staffed_venues_nearby,
                self.open_venues_nearby,
                self.safe_areas_nearby,
            )
        )


class RouteRequirements(BaseModel):
    model_config = ConfigDict(extra="forbid")

    accessibility: RouteAccessibilityChoices = Field(
        default_factory=RouteAccessibilityChoices
    )
    waiting_areas: RouteWaitingAreaChoices = Field(
        default_factory=RouteWaitingAreaChoices
    )

    @property
    def enabled(self) -> bool:
        return self.accessibility.enabled or self.waiting_areas.enabled


class RoutePreferences(BaseModel):
    model_config = ConfigDict(extra="forbid")

    accessibility: RouteAccessibilityChoices = Field(
        default_factory=RouteAccessibilityChoices
    )
    waiting_areas: RouteWaitingAreaChoices = Field(
        default_factory=RouteWaitingAreaChoices
    )


class RouteSafetyFeatures(BaseModel):
    model_config = ConfigDict(extra="forbid")

    incident_density: float | None = Field(default=None, ge=0)
    lighting_score: float | None = Field(default=None, ge=0, le=1)
    report_density: float | None = Field(default=None, ge=0)
    warnings: list[str] = Field(default_factory=list)


class RouteAccessibilityFeatures(BaseModel):
    model_config = ConfigDict(extra="forbid")

    step_free_ratio: float | None = Field(default=None, ge=0, le=1)
    stairs_present: bool | None = None
    lift_coverage_ratio: float | None = Field(default=None, ge=0, le=1)
    ramp_coverage_ratio: float | None = Field(default=None, ge=0, le=1)
    escalator_coverage_ratio: float | None = Field(default=None, ge=0, le=1)


class RouteTransportFeatures(BaseModel):
    model_config = ConfigDict(extra="forbid")

    night_transport_score: float | None = Field(default=None, ge=0, le=1)
    transfer_count: int | None = Field(default=None, ge=0)
    late_service_available: bool | None = None


class RouteWaitingAreaFeatures(BaseModel):
    model_config = ConfigDict(extra="forbid")

    safe_waiting_area_count: int | None = Field(default=None, ge=0)
    well_lit_waiting_area_count: int | None = Field(default=None, ge=0)
    wifi_access_point_count: int | None = Field(default=None, ge=0)
    staffed_venue_count: int | None = Field(default=None, ge=0)
    open_venue_count: int | None = Field(default=None, ge=0)
    waiting_areas_in_safe_areas_ratio: float | None = Field(
        default=None,
        ge=0,
        le=1,
    )
    max_gap_between_safe_waiting_areas_metres: int | None = Field(default=None, ge=0)


class RouteCandidateFeatures(BaseModel):
    model_config = ConfigDict(extra="forbid")

    safety: RouteSafetyFeatures = Field(default_factory=RouteSafetyFeatures)
    accessibility: RouteAccessibilityFeatures = Field(
        default_factory=RouteAccessibilityFeatures
    )
    transport: RouteTransportFeatures = Field(default_factory=RouteTransportFeatures)
    waiting_areas: RouteWaitingAreaFeatures = Field(
        default_factory=RouteWaitingAreaFeatures
    )


class RouteNavigationStep(BaseModel):
    model_config = ConfigDict(extra="forbid")

    step_index: int = Field(ge=0)
    distance_metres: int = Field(ge=0)
    duration_seconds: int = Field(ge=0)
    instruction: str | None = None
    street_name: str | None = None
    maneuver_type: str | None = None
    maneuver_modifier: str | None = None
    maneuver_location: LonLat | None = None
    geometry_geojson: dict | None = None


class RouteNavigationMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: str | None = None
    steps: list[RouteNavigationStep] = Field(default_factory=list)


class RouteCandidateInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_id: str = Field(min_length=1, max_length=64)
    label: str | None = Field(default=None, min_length=1, max_length=128)
    provider: str | None = Field(default=None, min_length=1, max_length=64)
    distance_metres: int = Field(gt=0)
    duration_seconds: int = Field(gt=0)
    geometry_geojson: dict | None = None
    navigation: RouteNavigationMetadata | None = None
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
    meets_requirements: bool = True
    unmet_requirements: list[str] = Field(default_factory=list)
    is_fallback: bool = False
    score: float = Field(ge=0, le=100)
    distance_metres: int = Field(gt=0)
    duration_seconds: int = Field(gt=0)
    geometry_geojson: dict | None = None
    navigation: RouteNavigationMetadata | None = None
    component_scores: RouteComponentScores
    explanation: RouteExplanation


class RouteScoreRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    origin: RouteLocation
    destination: RouteLocation
    depart_at: datetime
    bias_mode: RouteBiasMode = RouteBiasMode.BALANCED
    requirements: RouteRequirements = Field(default_factory=RouteRequirements)
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
    requirements_applied: bool = False
    requirement_matches_found: bool = True
    selected_route_is_fallback: bool = False
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
    severity: ReportSeverity


class RoutePlanRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    origin: RouteLocation
    destination: RouteLocation
    depart_at: datetime
    bias_mode: RouteBiasMode = RouteBiasMode.BALANCED
    requirements: RouteRequirements = Field(default_factory=RouteRequirements)
    preferences: RoutePreferences = Field(default_factory=RoutePreferences)
    alternatives: int = Field(default=3, ge=1, le=5)
    crime_date: str | None = None
    crime_category: str = "all-crime"

    @field_validator("depart_at")
    @classmethod
    def check_depart_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
            raise ValueError("depart_at must include a timezone offset")
        return value
