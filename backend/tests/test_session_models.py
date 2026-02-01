"""
Tests for Pydantic session models
Verifies serialization/deserialization works correctly
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


def test_session_meta_serialization():
    """Test SessionMeta model serialization"""
    meta = SessionMeta(
        session_id="test-123",
        start_timestamp_ms=1704067200000,
        firmware_version="1.0.0"
    )
    assert meta.session_id == "test-123"
    assert meta.start_timestamp_ms == 1704067200000
    assert meta.firmware_version == "1.0.0"


def test_heat_map_point_serialization():
    """Test HeatMapPoint model serialization"""
    point = HeatMapPoint(x_mm=10.0, y_mm=20.0, intensity_norm=0.75)
    assert point.x_mm == 10.0
    assert point.y_mm == 20.0
    assert point.intensity_norm == 0.75


def test_score_rule_serialization():
    """Test ScoreRule model serialization"""
    rule = ScoreRule(rule_id="pressure", threshold=25.0, passed=True)
    assert rule.rule_id == "pressure"
    assert rule.threshold == 25.0
    assert rule.passed is True


def test_session_score_serialization():
    """Test SessionScore model serialization"""
    rules = [
        ScoreRule(rule_id="pressure", threshold=25.0, passed=True),
        ScoreRule(rule_id="temperature", threshold=1200.0, passed=True),
    ]
    score = SessionScore(total=20, rules=rules)
    assert score.total == 20
    assert len(score.rules) == 2
    assert score.rules[0].rule_id == "pressure"


def test_welding_session_serialization():
    """Test WeldingSession model serialization"""
    meta = SessionMeta(
        session_id="test-123",
        start_timestamp_ms=1704067200000,
        firmware_version="1.0.0"
    )
    session = WeldingSession(meta=meta)
    assert session.meta.session_id == "test-123"
    assert session.heat_map is None
    assert session.torch_angle_deg is None
    assert session.score is None


def test_welding_session_with_optional_fields():
    """Test WeldingSession with optional fields"""
    meta = SessionMeta(
        session_id="test-123",
        start_timestamp_ms=1704067200000,
        firmware_version="1.0.0"
    )
    heat_map = [HeatMapPoint(x_mm=10.0, y_mm=20.0, intensity_norm=0.75)]
    torch_angle = [45.0, 46.0, 45.5]
    score = SessionScore(total=30, rules=[])
    
    session = WeldingSession(
        meta=meta,
        heat_map=heat_map,
        torch_angle_deg=torch_angle,
        score=score
    )
    assert len(session.heat_map) == 1
    assert len(session.torch_angle_deg) == 3
    assert session.score.total == 30
