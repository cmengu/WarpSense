"""
Prototype: ScoreRule → MetricScore mapping for trajectory feature.
Tests: Can we derive MetricScore (value 0–100) from ScoreRule (passed, actual_value)?
"""
from models.scoring import ScoreRule, SessionScore
from models.shared_enums import WeldMetric
from schemas.shared import MetricScore, make_metric_score

# Rule IDs from scoring/rule_based.py (exact strings)
RULE_TO_METRIC = {
    "angle_consistency": WeldMetric.ANGLE_CONSISTENCY,
    "thermal_symmetry": WeldMetric.THERMAL_SYMMETRY,
    "amps_stability": WeldMetric.AMPS_STABILITY,
    "volts_stability": WeldMetric.VOLTS_STABILITY,
    "heat_diss_consistency": WeldMetric.HEAT_DISS_CONSISTENCY,
}

def extract_metric_scores_option_a(score: SessionScore) -> list[MetricScore]:
    """Option A: passed ? 100 : 0 — binary per-metric score."""
    result = []
    for rule in score.rules:
        metric = RULE_TO_METRIC.get(rule.rule_id)
        if metric:
            val = 100.0 if rule.passed else 0.0
            result.append(make_metric_score(metric, val))
    return result

def extract_metric_scores_option_b(score: SessionScore) -> list[MetricScore]:
    """Option B: passed ? 20 : 0 — aligns with total = passed_count * 20."""
    result = []
    for rule in score.rules:
        metric = RULE_TO_METRIC.get(rule.rule_id)
        if metric:
            val = 20.0 if rule.passed else 0.0
            result.append(make_metric_score(metric, val))
    return result

# Simulate a SessionScore: 3 passed, 2 failed → total 60
rules = [
    ScoreRule(rule_id="amps_stability", threshold=5.0, passed=True, actual_value=3.2),
    ScoreRule(rule_id="angle_consistency", threshold=5.0, passed=True, actual_value=4.1),
    ScoreRule(rule_id="thermal_symmetry", threshold=60.0, passed=False, actual_value=72.0),
    ScoreRule(rule_id="heat_diss_consistency", threshold=40.0, passed=True, actual_value=28.0),
    ScoreRule(rule_id="volts_stability", threshold=1.0, passed=False, actual_value=1.5),
]
session_score = SessionScore(total=60, rules=rules)

print("Option A (passed ? 100 : 0):")
for m in extract_metric_scores_option_a(session_score):
    print(f"  {m.metric.value}: {m.value}")

print("\nOption B (passed ? 20 : 0):")
for m in extract_metric_scores_option_b(session_score):
    print(f"  {m.metric.value}: {m.value}")

# Validate both pass MetricScore.value 0–100
assert all(0 <= m.value <= 100 for m in extract_metric_scores_option_a(session_score))
assert all(0 <= m.value <= 100 for m in extract_metric_scores_option_b(session_score))
print("\n✅ Both options pass MetricScore validation (0–100).")
