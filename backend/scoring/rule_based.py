"""
Rule-based scoring logic for welding sessions.

5 rules map to 5 features from extract_features. Each rule passes if
actual_value <= threshold. Total = (passed_count) * 20 → max 100.

DRAFT thresholds: tuned for mock expert/novice sessions; may need adjustment
for real sensor data.
"""

from typing import Any, Dict

from models.scoring import ScoreRule, SessionScore
from models.session import Session


# DRAFT thresholds — tuned for mock expert/novice; may need adjustment for real data
# Lower feature value = better. Expert passes all 5 → 100; novice passes 2 → 40.
AMPS_STABILITY_THRESHOLD = 5.0       # amps_stddev: expert 1.2, novice 12.1
ANGLE_CONSISTENCY_THRESHOLD = 5.0   # angle_max_deviation (°): expert 1.0, novice 20.8
THERMAL_SYMMETRY_THRESHOLD = 60.0   # north_south_delta_avg (°C): expert 0.006, novice 56.9
HEAT_DISS_CONSISTENCY_THRESHOLD = 40.0  # heat_diss_stddev: expert 3.6, novice 38.1
VOLTS_STABILITY_THRESHOLD = 1.0     # volts_range (V): expert 0.35, novice 5.96


def score_session(session: Session, features: Dict[str, Any]) -> SessionScore:
    """
    Score a welding session using 5 rule-based checks.

    Args:
        session: Session to score (unused; features carry all needed data)
        features: Output from extract_features (amps_stddev, angle_max_deviation,
                  north_south_delta_avg, heat_diss_stddev, volts_range)

    Returns:
        SessionScore with total (0–100) and rules; each rule has actual_value set.
    """
    rules = [
        _check_amps_stability(features),
        _check_angle_consistency(features),
        _check_thermal_symmetry(features),
        _check_heat_diss_consistency(features),
        _check_volts_stability(features),
    ]
    passed_count = sum(1 for r in rules if r.passed)
    total = passed_count * 20
    return SessionScore(total=total, rules=rules)


def _check_amps_stability(features: Dict[str, Any]) -> ScoreRule:
    """Amps stability: lower stddev = better."""
    actual = features.get("amps_stddev", 0.0)
    passed = actual <= AMPS_STABILITY_THRESHOLD
    return ScoreRule(
        rule_id="amps_stability",
        threshold=AMPS_STABILITY_THRESHOLD,
        passed=passed,
        actual_value=actual,
    )


def _check_angle_consistency(features: Dict[str, Any]) -> ScoreRule:
    """Angle consistency: max deviation from 45° should be low."""
    actual = features.get("angle_max_deviation", 0.0)
    passed = actual <= ANGLE_CONSISTENCY_THRESHOLD
    return ScoreRule(
        rule_id="angle_consistency",
        threshold=ANGLE_CONSISTENCY_THRESHOLD,
        passed=passed,
        actual_value=actual,
    )


def _check_thermal_symmetry(features: Dict[str, Any]) -> ScoreRule:
    """Thermal symmetry: north/south temp delta should be low."""
    actual = features.get("north_south_delta_avg", 0.0)
    passed = actual <= THERMAL_SYMMETRY_THRESHOLD
    return ScoreRule(
        rule_id="thermal_symmetry",
        threshold=THERMAL_SYMMETRY_THRESHOLD,
        passed=passed,
        actual_value=actual,
    )


def _check_heat_diss_consistency(features: Dict[str, Any]) -> ScoreRule:
    """Heat dissipation consistency: lower stddev = smoother cooling."""
    actual = features.get("heat_diss_stddev", 0.0)
    passed = actual <= HEAT_DISS_CONSISTENCY_THRESHOLD
    return ScoreRule(
        rule_id="heat_diss_consistency",
        threshold=HEAT_DISS_CONSISTENCY_THRESHOLD,
        passed=passed,
        actual_value=actual,
    )


def _check_volts_stability(features: Dict[str, Any]) -> ScoreRule:
    """Volts stability: smaller range = more stable arc."""
    actual = features.get("volts_range", 0.0)
    passed = actual <= VOLTS_STABILITY_THRESHOLD
    return ScoreRule(
        rule_id="volts_stability",
        threshold=VOLTS_STABILITY_THRESHOLD,
        passed=passed,
        actual_value=actual,
    )
