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
