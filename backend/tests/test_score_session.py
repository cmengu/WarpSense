"""
Step 9 verification test for score_session.

Verification result (when PASS):
  - expert_total_100: Expert session → total 100
  - expert_all_rules_passed: Expert passes all 5 rules
  - novice_total_approx_40: Novice total ~40 (2 rules pass, 3 fail)
  - novice_fails_three_rules: Novice fails amps_stability, angle_consistency, volts_stability
  - all_rules_have_actual_value: Every rule has actual_value set
  - total_is_passed_times_20: total = sum(r.passed for r in rules) * 20

Action: Call score_session(session, extract_features(session)) with expert and novice.
Expected: Expert 100/100, 5 ✓; novice ~40/100, 2 ✓, 3 ✗.
Pass Criteria: Expert 100/100; novice <50; each rule has actual_value set.

If FAIL: Thresholds too strict — adjust DRAFT constants in rule_based.py.
"""

import sys
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

import pytest

from data.mock_sessions import generate_expert_session, generate_novice_session
from features.extractor import extract_features, extract_features_for_frames
from models.thresholds import WeldTypeThresholds
from scoring.rule_based import score_frames_windowed, score_session
from services.threshold_service import ALUMINUM_THRESHOLDS


class TestScoreSessionStep9:
    """Step 9 verification: score_session returns correct totals and rules."""

    def test_expert_total_100(self) -> None:
        """Expert session → total 100."""
        session = generate_expert_session()
        features = extract_features(session)
        score = score_session(session, features)
        assert score.total == 100, f"Expert should score 100, got {score.total}"

    def test_expert_all_rules_passed(self) -> None:
        """Expert passes all 5 rules."""
        session = generate_expert_session()
        features = extract_features(session)
        score = score_session(session, features)
        passed = [r for r in score.rules if r.passed]
        assert len(passed) == 5, f"Expert should pass all 5 rules, passed {len(passed)}"

    def test_novice_total_approx_40(self) -> None:
        """Novice total ~40 (2 rules pass, 3 fail)."""
        session = generate_novice_session()
        features = extract_features(session)
        score = score_session(session, features)
        assert 30 <= score.total <= 60, (
            f"Novice should score ~40 (2 rules), got {score.total}"
        )

    def test_novice_fails_three_rules(self) -> None:
        """Novice fails amps_stability, angle_consistency, volts_stability."""
        session = generate_novice_session()
        features = extract_features(session)
        score = score_session(session, features)
        failed = [r for r in score.rules if not r.passed]
        rule_ids = {r.rule_id for r in failed}
        assert "amps_stability" in rule_ids
        assert "angle_consistency" in rule_ids
        assert "volts_stability" in rule_ids
        assert len(failed) >= 3

    def test_all_rules_have_actual_value(self) -> None:
        """Every rule has actual_value set."""
        for session in [generate_expert_session(), generate_novice_session()]:
            features = extract_features(session)
            score = score_session(session, features)
            for rule in score.rules:
                assert rule.actual_value is not None, (
                    f"Rule {rule.rule_id} must have actual_value set"
                )

    def test_total_is_passed_times_20(self) -> None:
        """total = sum(r.passed for r in rules) * 20."""
        session = generate_expert_session()
        features = extract_features(session)
        score = score_session(session, features)
        expected = sum(1 for r in score.rules if r.passed) * 20
        assert score.total == expected

    def test_five_rules_present(self) -> None:
        """Score has exactly 5 rules."""
        session = generate_expert_session()
        features = extract_features(session)
        score = score_session(session, features)
        assert len(score.rules) == 5
        rule_ids = {r.rule_id for r in score.rules}
        expected = {
            "amps_stability",
            "angle_consistency",
            "thermal_symmetry",
            "heat_diss_consistency",
            "volts_stability",
        }
        assert rule_ids == expected


class TestScoreFramesWindowed:
    """Step 2 verification: score_frames_windowed returns windowed WQI timeline."""

    def test_result_has_frame_start_end_wqi(self) -> None:
        """Result entries have frame_start, frame_end, wqi."""
        session = generate_expert_session()
        frames = session.frames
        metadata = {
            "weld_type": session.weld_type,
            "thermal_sample_interval_ms": session.thermal_sample_interval_ms,
            "thermal_directions": session.thermal_directions,
            "thermal_distance_interval_mm": session.thermal_distance_interval_mm,
            "sensor_sample_rate_hz": session.sensor_sample_rate_hz,
        }
        result = score_frames_windowed(frames, None, metadata, window_size=50)
        assert len(result) > 0
        for entry in result:
            assert "frame_start" in entry
            assert "frame_end" in entry
            assert "wqi" in entry
            assert isinstance(entry["wqi"], int)
            assert 0 <= entry["wqi"] <= 100

    def test_empty_frames_returns_empty(self) -> None:
        """Empty frames returns empty list."""
        metadata = {"weld_type": "mig", "thermal_sample_interval_ms": 100}
        assert score_frames_windowed([], None, metadata) == []

    def test_rule_set_parity_with_aluminum_thresholds(self) -> None:
        """First window uses same rule set as full score_session (aluminum thresholds)."""
        session = generate_novice_session()
        session = session.model_copy(update={"weld_type": "aluminum"})
        thresholds = WeldTypeThresholds(**ALUMINUM_THRESHOLDS)
        features_full = extract_features(session)
        full = score_session(session, features_full, thresholds)
        metadata = {
            "weld_type": session.weld_type,
            "thermal_sample_interval_ms": session.thermal_sample_interval_ms,
            "thermal_directions": session.thermal_directions,
            "thermal_distance_interval_mm": session.thermal_distance_interval_mm,
            "sensor_sample_rate_hz": session.sensor_sample_rate_hz,
        }
        frames = session.frames
        result = score_frames_windowed(frames, thresholds, metadata, window_size=50)
        assert len(result) > 0
        # First window: extract features and score via score_session
        w = frames[:50]
        f = extract_features_for_frames(w, thresholds.angle_target_degrees)
        from models.session import Session
        from datetime import datetime, timezone
        dummy = Session(
            session_id="__window__",
            operator_id="",
            start_time=datetime.now(timezone.utc),
            weld_type=session.weld_type,
            thermal_sample_interval_ms=session.thermal_sample_interval_ms,
            thermal_directions=session.thermal_directions,
            thermal_distance_interval_mm=session.thermal_distance_interval_mm,
            sensor_sample_rate_hz=session.sensor_sample_rate_hz,
            frames=w,
            frame_count=len(w),
            disable_sensor_continuity_checks=True,
        )
        sw = score_session(dummy, f, thresholds)
        assert len(sw.rules) == len(full.rules), "Window and full must use same rule set"
