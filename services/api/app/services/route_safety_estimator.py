# Empirical Bayes safety estimator. 
# Shrinks observed crime/report densities toward an existing mean so that routes with sparse data don't get wildly over or under scored. 
# Uses a gamma poisson conjugate, a bit more reflective than raw averages.

import math
from typing import TypedDict

from app.core import route_risk_config as risk_config


class SafetyEstimate(TypedDict):
    expected_harm_rate: float
    serious_incident_probability: float
    safety_score: float
    shrinkage_factor: float


def estimate_route_safety(
    *,
    incident_density: float | None,
    report_density: float | None,
    route_length_km: float,
    lighting_score: float | None = None,
    depart_hour: int | None = None,
) -> SafetyEstimate:
    # Compute a shrinkage adjusted harm rate estimate for a route. When data is thin the prior does the heavy lifting, when there's plenty of evidence the observations dominate.
    route_km = max(route_length_km, 0.001)

    prior_mean = risk_config.PRIOR_MEAN_HARM_RATE
    prior_strength = risk_config.PRIOR_OBSERVATION_STRENGTH

    # gamma prior params
    alpha_0 = prior_mean * prior_strength
    beta_0 = prior_strength

    # fold in whatever evidence we actually have
    observed_harm = 0.0
    effective_exposure = 0.0

    if incident_density is not None:
        w = risk_config.POLICE_DATA_RELIABILITY
        observed_harm += w * incident_density * route_km
        effective_exposure += w * route_km

    if report_density is not None:
        w = risk_config.USER_REPORT_RELIABILITY
        observed_harm += w * report_density * route_km
        effective_exposure += w * route_km

    # updated estimate: Gamma(alpha_0 + observed, beta_0 + exposure)
    alpha_updated = alpha_0 + observed_harm
    beta_updated = beta_0 + effective_exposure
    estimated_mean = alpha_updated / beta_updated

    # 1.0 = fully prior, 0.0 = fully data driven
    shrinkage = beta_0 / beta_updated

    # contextual adjustments
    adjusted = estimated_mean * _time_multiplier(depart_hour) * _lighting_modifier(lighting_score)

    # P(at least one serious incident) via poisson
    serious_lambda = adjusted * risk_config.SERIOUS_RATE_FACTOR * route_km
    serious_prob = 1.0 - math.exp(-serious_lambda)

    # higher harm means lower safety score (exponential decay)
    safety_score = math.exp(-risk_config.HARM_RATE_DECAY * adjusted)

    return SafetyEstimate(
        expected_harm_rate=round(adjusted, 4),
        serious_incident_probability=round(min(serious_prob, 1.0), 4),
        safety_score=round(_clamp(safety_score), 4),
        shrinkage_factor=round(shrinkage, 4),
    )


def _time_multiplier(hour: int | None) -> float:
    # risk multiplier look up for the departure hour
    if hour is None:
        return 1.0
    h = hour % 24
    for start, end, mult in risk_config.TIME_RISK_MULTIPLIERS:
        if start <= h < end:
            return mult
    return 1.0


def _lighting_modifier(score: float | None) -> float:
    # map a 0-1 lighting score to a risk modifier, missing data gets a slight penalty, can't just assume it's fine
    if score is None:
        return risk_config.LIGHTING_MODIFIER_UNKNOWN

    if score >= risk_config.LIGHTING_WELL_LIT_THRESHOLD:
        return risk_config.LIGHTING_MODIFIER_WELL_LIT
    if score <= risk_config.LIGHTING_POOR_THRESHOLD:
        return risk_config.LIGHTING_MODIFIER_POOR

    # in between, linearly interpolate from poor modifier down to well lit modifier
    t = (score - risk_config.LIGHTING_POOR_THRESHOLD) / (
        risk_config.LIGHTING_WELL_LIT_THRESHOLD - risk_config.LIGHTING_POOR_THRESHOLD
    )
    return risk_config.LIGHTING_MODIFIER_POOR + t * (
        risk_config.LIGHTING_MODIFIER_WELL_LIT - risk_config.LIGHTING_MODIFIER_POOR
    )


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))
