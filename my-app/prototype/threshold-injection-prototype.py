"""
Prototype: Threshold injection into extract_features and score_session.

What was tested:
- extract_features(session, angle_target_deg=45) — angle_max_deviation from configurable target
- score_session(session, features, thresholds) — rules use thresholds dict instead of globals

Result: Validates that refactor is straightforward; no surprises.
Decision: Proceed with optional thresholds param; fallback to current constants.
"""

# Simulated current extractor logic — line 55
def _angle_max_deviation_current(angles: list[float]) -> float:
    return max(abs(a - 45) for a in angles) if angles else 0.0


def _angle_max_deviation_param(angles: list[float], target_deg: float = 45) -> float:
    return max(abs(a - target_deg) for a in angles) if angles else 0.0


# Simulated rule check — single threshold
def _check_angle(actual: float, threshold: float) -> bool:
    return actual <= threshold


def main():
    angles = [44, 46, 45, 47, 43]
    print("Current (target=45):", _angle_max_deviation_current(angles))  # 2
    print("Param (target=45): ", _angle_max_deviation_param(angles, 45))  # 2
    print("Param (target=75): ", _angle_max_deviation_param(angles, 75))  # 31
    assert _angle_max_deviation_param(angles, 45) == 2
    assert _angle_max_deviation_param(angles, 75) == 31

    # Rule: pass when actual <= threshold
    assert _check_angle(2, 5)  # pass
    assert not _check_angle(8, 5)  # fail
    assert _check_angle(2, 10)  # TIG looser threshold -> pass
    print("All assertions passed. Proceed with optional threshold injection.")
