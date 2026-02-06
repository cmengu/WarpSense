"""
Tests for model exports and import stability.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from models import (
    DashboardData,
    Frame,
    FrameDelta,
    ScoreRule,
    Session,
    SessionScore,
    SessionStatus,
    TemperatureDelta,
    TemperaturePoint,
    ThermalDelta,
    ThermalSnapshot,
)


def test_model_exports_available():
    assert DashboardData is not None
    assert Frame is not None
    assert FrameDelta is not None
    assert Session is not None
    assert SessionScore is not None
    assert SessionStatus is not None
    assert ScoreRule is not None
    assert TemperatureDelta is not None
    assert TemperaturePoint is not None
    assert ThermalDelta is not None
    assert ThermalSnapshot is not None
