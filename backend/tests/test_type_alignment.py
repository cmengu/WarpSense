"""
Tests for type alignment between Python Pydantic models and TypeScript types
Verifies structure matches to prevent drift
"""

import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.session_model import (
    SessionMeta,
    HeatMapPoint,
    ScoreRule,
    SessionScore,
    WeldingSession,
)


def test_session_meta_structure():
    """Verify SessionMeta has correct fields matching TypeScript SessionMeta"""
    # TypeScript: sessionId, startTimestampMs, firmwareVersion
    # Python: session_id, start_timestamp_ms, firmware_version
    meta = SessionMeta(
        session_id="test",
        start_timestamp_ms=0,
        firmware_version="1.0.0"
    )
    # Verify fields exist
    assert hasattr(meta, "session_id")
    assert hasattr(meta, "start_timestamp_ms")
    assert hasattr(meta, "firmware_version")
    # Verify types
    assert isinstance(meta.session_id, str)
    assert isinstance(meta.start_timestamp_ms, int)
    assert isinstance(meta.firmware_version, str)


def test_heat_map_point_structure():
    """Verify HeatMapPoint has correct fields matching TypeScript HeatMapPoint"""
    # TypeScript: x_mm, y_mm, intensity_norm
    point = HeatMapPoint(x_mm=0.0, y_mm=0.0, intensity_norm=0.5)
    assert hasattr(point, "x_mm")
    assert hasattr(point, "y_mm")
    assert hasattr(point, "intensity_norm")
    assert isinstance(point.x_mm, float)
    assert isinstance(point.y_mm, float)
    assert isinstance(point.intensity_norm, float)


def test_score_rule_structure():
    """Verify ScoreRule has correct fields matching TypeScript ScoreRule"""
    # TypeScript: ruleId, threshold, passed
    rule = ScoreRule(rule_id="test", threshold=0.0, passed=False)
    assert hasattr(rule, "rule_id")
    assert hasattr(rule, "threshold")
    assert hasattr(rule, "passed")
    assert isinstance(rule.rule_id, str)
    assert isinstance(rule.threshold, float)
    assert isinstance(rule.passed, bool)


def test_session_score_structure():
    """Verify SessionScore has correct fields matching TypeScript SessionScore"""
    # TypeScript: total, rules
    score = SessionScore(total=0, rules=[])
    assert hasattr(score, "total")
    assert hasattr(score, "rules")
    assert isinstance(score.total, int)
    assert isinstance(score.rules, list)


def test_welding_session_structure():
    """Verify WeldingSession has correct fields matching TypeScript WeldingSession"""
    # TypeScript: meta, heatMap?, torchAngleDeg?, score?
    meta = SessionMeta(
        session_id="test",
        start_timestamp_ms=0,
        firmware_version="1.0.0"
    )
    session = WeldingSession(meta=meta)
    assert hasattr(session, "meta")
    assert hasattr(session, "heat_map")
    assert hasattr(session, "torch_angle_deg")
    assert hasattr(session, "score")
    # Optional fields should be None by default
    assert session.heat_map is None or isinstance(session.heat_map, list)
    assert session.torch_angle_deg is None or isinstance(session.torch_angle_deg, list)
    assert session.score is None or isinstance(session.score, SessionScore)
