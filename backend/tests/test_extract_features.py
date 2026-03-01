"""
Step 8 verification test for extract_features.

Verification result (when PASS):
  - all_keys_present: Returns dict with amps_stddev, angle_max_deviation,
    north_south_delta_avg, heat_diss_stddev, volts_range
  - expert_non_zero: Expert session yields non-zero features
  - novice_non_zero: Novice session yields non-zero features
  - expert_less_than_novice_on_amps: Expert amps_stddev < novice amps_stddev
  - expert_less_than_novice_on_angle: Expert angle_max_deviation < novice angle_max_deviation
  - empty_session_returns_zeros: Empty session yields all zeros
  - single_frame_returns_zero_stddev: Single-frame session yields 0 for *_stddev features

Action: Call extract_features(generate_expert_session()) and extract_features(generate_novice_session())
Expected: Expert has low amps_stddev, low angle_max_deviation; novice higher.
Pass Criteria: Non-zero features; expert < novice on amps_stddev, angle_max_deviation.

If FAIL: Wrong field names → run validate_frame_fields.py; check f.amps, f.angle_degrees, f.has_thermal_data.
"""

import pytest

from data.mock_sessions import generate_expert_session, generate_novice_session
from features.extractor import extract_features, extract_features_for_frames


FEATURE_KEYS = frozenset({
    "amps_stddev",
    "angle_max_deviation",
    "north_south_delta_avg",
    "heat_diss_stddev",
    "volts_range",
})


class TestExtractFeaturesStep8:
    """Step 8 verification: extract_features returns correct features for scoring."""

    def test_all_keys_present(self) -> None:
        """Returns dict with all 5 required feature keys."""
        session = generate_expert_session()
        result = extract_features(session)
        keys = set(result.keys())
        assert FEATURE_KEYS <= keys, f"Missing keys: {FEATURE_KEYS - keys}"

    def test_expert_non_zero(self) -> None:
        """Expert session yields non-zero values for features."""
        session = generate_expert_session()
        result = extract_features(session)
        # At least amps, angle, volts should be non-zero for a real session
        assert result["amps_stddev"] >= 0
        assert result["angle_max_deviation"] >= 0
        assert result["volts_range"] >= 0
        # Expert has many frames → amps_stddev should be small but non-zero (noise)
        assert result["amps_stddev"] > 0 or result["angle_max_deviation"] > 0

    def test_novice_non_zero(self) -> None:
        """Novice session yields non-zero values for features."""
        session = generate_novice_session()
        result = extract_features(session)
        assert result["amps_stddev"] >= 0
        assert result["angle_max_deviation"] >= 0
        assert result["volts_range"] >= 0
        # Novice has spiky amps and drifting angle → clearly non-zero
        assert result["amps_stddev"] > 0
        assert result["angle_max_deviation"] > 0

    def test_expert_less_than_novice_on_amps(self) -> None:
        """Expert amps_stddev < novice amps_stddev (stable vs erratic)."""
        expert_result = extract_features(generate_expert_session())
        novice_result = extract_features(generate_novice_session())
        assert expert_result["amps_stddev"] < novice_result["amps_stddev"], (
            f"Expert amps_stddev={expert_result['amps_stddev']:.2f} should be < "
            f"novice amps_stddev={novice_result['amps_stddev']:.2f}"
        )

    def test_expert_less_than_novice_on_angle(self) -> None:
        """Expert angle_max_deviation < novice angle_max_deviation (flat vs drift)."""
        expert_result = extract_features(generate_expert_session())
        novice_result = extract_features(generate_novice_session())
        assert expert_result["angle_max_deviation"] < novice_result["angle_max_deviation"], (
            f"Expert angle_max_deviation={expert_result['angle_max_deviation']:.2f} should be < "
            f"novice angle_max_deviation={novice_result['angle_max_deviation']:.2f}"
        )

    def test_north_south_delta_present_for_thermal_sessions(self) -> None:
        """Expert and novice have thermal data → north_south_delta_avg computed."""
        expert_result = extract_features(generate_expert_session())
        novice_result = extract_features(generate_novice_session())
        # Both have thermal frames; expert symmetric (~0), novice asymmetric (>0)
        assert "north_south_delta_avg" in expert_result
        assert "north_south_delta_avg" in novice_result
        assert expert_result["north_south_delta_avg"] >= 0
        assert novice_result["north_south_delta_avg"] >= 0

    def test_heat_diss_stddev_present(self) -> None:
        """heat_diss_stddev computed (expert smooth, novice erratic)."""
        expert_result = extract_features(generate_expert_session())
        novice_result = extract_features(generate_novice_session())
        assert "heat_diss_stddev" in expert_result
        assert "heat_diss_stddev" in novice_result
        # Novice has erratic dissipation → higher stddev
        assert novice_result["heat_diss_stddev"] >= expert_result["heat_diss_stddev"]


class TestExtractFeaturesEdgeCases:
    """Edge cases: empty session, minimal data."""

    def test_empty_session_returns_zeros(self) -> None:
        """Empty session yields all zeros."""
        from datetime import datetime, timezone

        from models.session import Session, SessionStatus

        empty = Session(
            session_id="empty",
            operator_id="op",
            start_time=datetime.now(timezone.utc),
            weld_type="mild_steel",
            thermal_sample_interval_ms=100,
            thermal_directions=["center", "north", "south", "east", "west"],
            thermal_distance_interval_mm=10.0,
            sensor_sample_rate_hz=100,
            frames=[],
            status=SessionStatus.COMPLETE,
            frame_count=0,
            expected_frame_count=0,
            last_successful_frame_index=-1,
            completed_at=datetime.now(timezone.utc),
        )
        result = extract_features(empty)
        assert result["amps_stddev"] == 0.0
        assert result["angle_max_deviation"] == 0.0
        assert result["north_south_delta_avg"] == 0.0
        assert result["heat_diss_stddev"] == 0.0
        assert result["volts_range"] == 0.0

    def test_single_frame_returns_zero_stddev(self) -> None:
        """Single-frame session yields 0 for *_stddev (stdev needs len>1)."""
        from datetime import datetime, timezone

        from models.frame import Frame
        from models.session import Session, SessionStatus

        single = Session(
            session_id="single",
            operator_id="op",
            start_time=datetime.now(timezone.utc),
            weld_type="mild_steel",
            thermal_sample_interval_ms=100,
            thermal_directions=["center", "north", "south", "east", "west"],
            thermal_distance_interval_mm=10.0,
            sensor_sample_rate_hz=100,
            frames=[
                Frame(
                    timestamp_ms=0,
                    volts=22.0,
                    amps=150.0,
                    angle_degrees=45.0,
                    thermal_snapshots=[],
                )
            ],
            status=SessionStatus.COMPLETE,
            frame_count=1,
            expected_frame_count=1,
            last_successful_frame_index=0,
            completed_at=datetime.now(timezone.utc),
        )
        result = extract_features(single)
        assert result["amps_stddev"] == 0.0
        assert result["heat_diss_stddev"] == 0.0
        # angle_max_deviation and volts_range can still be computed from single value
        assert result["angle_max_deviation"] == 0.0  # 45 - 45 = 0
        assert result["volts_range"] == 0.0  # single value


def test_extract_features_for_frames_equals_extract_features() -> None:
    """extract_features_for_frames(s.frames, 45) must equal extract_features(s, 45)."""
    session = generate_expert_session()
    from_frames = extract_features_for_frames(session.frames, 45)
    from_session = extract_features(session, 45)
    assert from_frames == from_session, (
        f"Mismatch: extract_features_for_frames vs extract_features"
    )
