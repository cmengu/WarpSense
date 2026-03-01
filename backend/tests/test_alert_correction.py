"""
Tests for alert correction enrichment.

All tests use plain dicts for frame data. No FrameModel. No database.
Threshold-adjacent values are derived from TEST_CFG, never hardcoded.
"""

from pathlib import Path

from realtime.alert_engine import load_thresholds
from realtime.alert_models import AlertPayload
from services.alert_service import _enrich_alerts_with_correction

# Path from backend/tests/ to backend/config/
TEST_CFG = load_thresholds(
    str(Path(__file__).resolve().parent.parent / "config" / "alert_thresholds.json")
)

# Derived from TEST_CFG
NS_IN_RANGE = float(TEST_CFG["thermal_ns_warning"]) - 1
NS_OUT_OF_RANGE = float(TEST_CFG["thermal_ns_warning"]) + 1
ANGLE_IN_RANGE = float(TEST_CFG["nominal_travel_angle"])
ANGLE_OUT_OF_RANGE = (
    float(TEST_CFG["nominal_travel_angle"])
    + float(TEST_CFG["angle_deviation_warning"])
    + 1
)


def _thermal_frame(ts_ms: float, ns: float) -> dict:
    """Build frame dict with north-minus-south = ns. north=ns, south=0."""
    return {
        "timestamp_ms": ts_ms,
        "thermal_snapshots": [
            {
                "readings": [
                    {"direction": "north", "temp_celsius": ns},
                    {"direction": "south", "temp_celsius": 0},
                ]
            }
        ],
    }


def test_rule1_corrected_when_subsequent_frame_in_range():
    """Alert at t=100, frame at t=200 with ns in-range -> corrected=True."""
    alert = AlertPayload(
        frame_index=0,
        rule_triggered="rule1",
        severity="warning",
        message="x",
        correction="y",
        timestamp_ms=100.0,
    )
    frame_items = [(200.0, _thermal_frame(200, NS_IN_RANGE))]
    _enrich_alerts_with_correction([alert], frame_items, TEST_CFG)
    assert alert.corrected is True
    assert alert.corrected_in_seconds == 0.1


def test_rule2_corrected_when_angle_returns_to_nominal():
    """Alert at t=100, frame at t=150 with angle in range -> corrected=True."""
    alert = AlertPayload(
        frame_index=0,
        rule_triggered="rule2",
        severity="warning",
        message="x",
        correction="y",
        timestamp_ms=100.0,
    )
    frame_items = [
        (150.0, {"timestamp_ms": 150, "travel_angle_degrees": ANGLE_IN_RANGE})
    ]
    _enrich_alerts_with_correction([alert], frame_items, TEST_CFG)
    assert alert.corrected is True
    assert alert.corrected_in_seconds == 0.05


def test_rule1_not_corrected_when_no_subsequent_in_range():
    """Alert at t=100, all later frames out of range -> corrected=False."""
    alert = AlertPayload(
        frame_index=0,
        rule_triggered="rule1",
        severity="warning",
        message="x",
        correction="y",
        timestamp_ms=100.0,
    )
    frame_items = [
        (200.0, _thermal_frame(200, NS_OUT_OF_RANGE)),
        (300.0, _thermal_frame(300, NS_OUT_OF_RANGE)),
    ]
    _enrich_alerts_with_correction([alert], frame_items, TEST_CFG)
    assert alert.corrected is False
    assert alert.corrected_in_seconds is None


def test_alert_on_last_frame_no_crash():
    """Alert on last frame; no subsequent frames -> corrected=False, no crash."""
    alert = AlertPayload(
        frame_index=0,
        rule_triggered="rule1",
        severity="warning",
        message="x",
        correction="y",
        timestamp_ms=500.0,
    )
    # No frames with ts > 500
    frame_items = [
        (100.0, _thermal_frame(100, NS_IN_RANGE)),
        (200.0, _thermal_frame(200, NS_IN_RANGE)),
    ]
    _enrich_alerts_with_correction([alert], frame_items, TEST_CFG)
    assert alert.corrected is False
    assert alert.corrected_in_seconds is None


def test_rules_3_to_11_always_false():
    """Rules 3–11 remain corrected=False regardless of frames."""
    for rule in ["rule3", "porosity", "arc_instability", "oxide_inclusion"]:
        alert = AlertPayload(
            frame_index=0,
            rule_triggered=rule,
            severity="critical",
            message="x",
            correction="y",
            timestamp_ms=100.0,
        )
        frame_items = [
            (200.0, _thermal_frame(200, NS_IN_RANGE)),
            (300.0, {"timestamp_ms": 300, "travel_angle_degrees": ANGLE_IN_RANGE}),
        ]
        _enrich_alerts_with_correction([alert], frame_items, TEST_CFG)
        assert alert.corrected is False, f"rule {rule} should stay corrected=False"
        assert alert.corrected_in_seconds is None
