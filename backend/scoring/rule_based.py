"""
Rule-based scoring logic for welding sessions.

5 rules map to 5 features from extract_features. Each rule passes if
actual_value <= threshold. Total = (passed_count) * 20 → max 100.

DRAFT thresholds: tuned for mock expert/novice sessions; may need adjustment
for real sensor data. Use WeldTypeThresholds when provided; fallback to constants.
"""

from typing import Any, Dict, Optional

from models.scoring import ScoreRule, SessionScore
from models.session import Session
from models.thresholds import WeldTypeThresholds


# Fallback thresholds for tests/callers that don't pass thresholds
AMPS_STABILITY_THRESHOLD = 5.0
ANGLE_CONSISTENCY_THRESHOLD = 5.0
THERMAL_SYMMETRY_THRESHOLD = 60.0
HEAT_DISS_CONSISTENCY_THRESHOLD = 40.0
VOLTS_STABILITY_THRESHOLD = 1.0


def score_session(
    session: Session,
    features: Dict[str, Any],
    thresholds: Optional[WeldTypeThresholds] = None,
) -> SessionScore:
    """
    Score a welding session using 5 rule-based checks.

    Args:
        session: Session to score (unused; features carry all needed data)
        features: Output from extract_features (amps_stddev, angle_max_deviation,
                  north_south_delta_avg, heat_diss_stddev, volts_range)

    Returns:
        SessionScore with total (0–100) and rules; each rule has actual_value set.
    """
    t = thresholds
    rules = [
        _check_amps_stability(features, t),
        _check_angle_consistency(features, t),
        _check_thermal_symmetry(features, t),
        _check_heat_diss_consistency(features, t),
        _check_volts_stability(features, t),
    ]
    passed_count = sum(1 for r in rules if r.passed)
    total = passed_count * 20
    return SessionScore(total=total, rules=rules)


def _check_amps_stability(
    features: Dict[str, Any], t: Optional[WeldTypeThresholds]
) -> ScoreRule:
    """Amps stability: lower stddev = better."""
    actual = features.get("amps_stddev", 0.0)
    th = t.amps_stability_warning if t else AMPS_STABILITY_THRESHOLD
    return ScoreRule(
        rule_id="amps_stability",
        threshold=th,
        passed=actual <= th,
        actual_value=actual,
    )


def _check_angle_consistency(
    features: Dict[str, Any], t: Optional[WeldTypeThresholds]
) -> ScoreRule:
    """Angle consistency: max deviation from target should be low."""
    actual = features.get("angle_max_deviation", 0.0)
    th = t.angle_warning_margin if t else ANGLE_CONSISTENCY_THRESHOLD
    return ScoreRule(
        rule_id="angle_consistency",
        threshold=th,
        passed=actual <= th,
        actual_value=actual,
    )


def _check_thermal_symmetry(
    features: Dict[str, Any], t: Optional[WeldTypeThresholds]
) -> ScoreRule:
    """Thermal symmetry: north/south temp delta should be low."""
    actual = features.get("north_south_delta_avg", 0.0)
    th = t.thermal_symmetry_warning_celsius if t else THERMAL_SYMMETRY_THRESHOLD
    return ScoreRule(
        rule_id="thermal_symmetry",
        threshold=th,
        passed=actual <= th,
        actual_value=actual,
    )


def _check_heat_diss_consistency(
    features: Dict[str, Any], t: Optional[WeldTypeThresholds]
) -> ScoreRule:
    """Heat dissipation consistency: lower stddev = smoother cooling."""
    actual = features.get("heat_diss_stddev", 0.0)
    th = t.heat_diss_consistency if t else HEAT_DISS_CONSISTENCY_THRESHOLD
    return ScoreRule(
        rule_id="heat_diss_consistency",
        threshold=th,
        passed=actual <= th,
        actual_value=actual,
    )


def _check_volts_stability(
    features: Dict[str, Any], t: Optional[WeldTypeThresholds]
) -> ScoreRule:
    """Volts stability: smaller range = more stable arc."""
    actual = features.get("volts_range", 0.0)
    th = t.volts_stability_warning if t else VOLTS_STABILITY_THRESHOLD
    return ScoreRule(
        rule_id="volts_stability",
        threshold=th,
        passed=actual <= th,
        actual_value=actual,
    )
