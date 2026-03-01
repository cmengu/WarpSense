"""
Canonical enums shared across all WarpSense services.
Import from here — never redefine these enums elsewhere.
"""

from enum import Enum


class WeldMetric(str, Enum):
    ANGLE_CONSISTENCY = "angle_consistency"
    THERMAL_SYMMETRY = "thermal_symmetry"
    AMPS_STABILITY = "amps_stability"
    VOLTS_STABILITY = "volts_stability"
    HEAT_DISS_CONSISTENCY = "heat_diss_consistency"


class RiskLevel(str, Enum):
    OK = "ok"
    WARNING = "warning"
    CRITICAL = "critical"


class AnnotationType(str, Enum):
    DEFECT_CONFIRMED = "defect_confirmed"
    NEAR_MISS = "near_miss"
    TECHNIQUE_ERROR = "technique_error"
    EQUIPMENT_ISSUE = "equipment_issue"


class CoachingStatus(str, Enum):
    ACTIVE = "active"
    COMPLETE = "complete"
    OVERDUE = "overdue"


class CertificationStatus(str, Enum):
    NOT_STARTED = "not_started"
    ON_TRACK = "on_track"
    AT_RISK = "at_risk"
    CERTIFIED = "certified"
