from enum import Enum
from typing import Final


class ReportSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


RISK_MODEL_NAME: Final[str] = "estimated_observed_risk"

RISK_MODEL_OUTPUTS: Final[dict[str, str]] = {
    "expected_harm_rate": (
        "Expected severity-weighted harm for one person passing through a place."
    ),
    "serious_incident_probability": (
        "Estimated chance of at least one serious incident in that place and time."
    ),
}

SEVERITY_WEIGHTS: Final[dict[ReportSeverity, int]] = {
    ReportSeverity.LOW: 1,
    ReportSeverity.MEDIUM: 3,
    ReportSeverity.HIGH: 6,
    ReportSeverity.CRITICAL: 10,
}

DEFAULT_USER_REPORT_SEVERITY: Final[ReportSeverity] = ReportSeverity.LOW
DEFAULT_POLICE_CRIME_SEVERITY: Final[ReportSeverity] = ReportSeverity.LOW

USER_REPORT_CATEGORY_SEVERITY: Final[dict[str, ReportSeverity]] = {
    "assault": ReportSeverity.CRITICAL,
    "robbery": ReportSeverity.CRITICAL,
    "harassment": ReportSeverity.HIGH,
    "theft": ReportSeverity.MEDIUM,
    "suspicious activity": ReportSeverity.MEDIUM,
    "unsafe crossing": ReportSeverity.MEDIUM,
    "poor lighting": ReportSeverity.LOW,
    "hazard": ReportSeverity.LOW,
    "other": ReportSeverity.LOW,
}

POLICE_CRIME_CATEGORY_SEVERITY: Final[dict[str, ReportSeverity]] = {
    "violent-crime": ReportSeverity.CRITICAL,
    "sexual-offences": ReportSeverity.CRITICAL,
    "possession-of-weapons": ReportSeverity.CRITICAL,
    "robbery": ReportSeverity.HIGH,
    "theft-from-the-person": ReportSeverity.HIGH,
    "public-order": ReportSeverity.MEDIUM,
    "drugs": ReportSeverity.MEDIUM,
    "burglary": ReportSeverity.MEDIUM,
    "criminal-damage-arson": ReportSeverity.MEDIUM,
    "anti-social-behaviour": ReportSeverity.LOW,
    "vehicle-crime": ReportSeverity.LOW,
    "shoplifting": ReportSeverity.LOW,
    "bicycle-theft": ReportSeverity.LOW,
    "other-theft": ReportSeverity.LOW,
    "other-crime": ReportSeverity.LOW,
}


# empirical bayes estimator config, gamma prior: mean = PRIOR_MEAN_HARM_RATE, pseudo exposure = PRIOR_OBSERVATION_STRENGTH km, so alpha = mean * strength, beta = strength
PRIOR_MEAN_HARM_RATE: Final[float] = 3.0
PRIOR_OBSERVATION_STRENGTH: Final[float] = 8.0

# how much we trust each data source (police is the reference)
POLICE_DATA_RELIABILITY: Final[float] = 1.0
USER_REPORT_RELIABILITY: Final[float] = 0.6

# rough conversion from weighted harm rate to serious incidents/km, not claiming this is perfect but it gives sensible probabilities
SERIOUS_RATE_FACTOR: Final[float] = 0.12

# exponential decay for harm rate to 0-1 safety score
HARM_RATE_DECAY: Final[float] = 0.0001

# time of day risk multipliers (start hour inclusive, end hour exclusive, multiplier)
TIME_RISK_MULTIPLIERS: Final[list[tuple[int, int, float]]] = [
    (0, 5, 1.4),
    (5, 7, 1.1),
    (7, 18, 0.85),
    (18, 21, 1.0),
    (21, 24, 1.25),
]

# lighting score thresholds and the modifier each band applies
LIGHTING_WELL_LIT_THRESHOLD: Final[float] = 0.65
LIGHTING_POOR_THRESHOLD: Final[float] = 0.30
LIGHTING_MODIFIER_WELL_LIT: Final[float] = 0.85
LIGHTING_MODIFIER_POOR: Final[float] = 1.20
LIGHTING_MODIFIER_UNKNOWN: Final[float] = 1.10
