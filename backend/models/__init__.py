"""
Models package exports for canonical time-series contract.
"""

import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "models_root", Path(__file__).parent.parent / "models.py"
)
models_root = importlib.util.module_from_spec(spec)
spec.loader.exec_module(models_root)
DashboardData = models_root.DashboardData

from .comparison import FrameDelta, TemperatureDelta, ThermalDelta
from .frame import Frame
from .scoring import ScoreRule, SessionScore
from .session import Session, SessionStatus
from .thermal import TemperaturePoint, ThermalSnapshot

__all__ = [
    "DashboardData",
    "Frame",
    "FrameDelta",
    "Session",
    "SessionScore",
    "SessionStatus",
    "ScoreRule",
    "TemperatureDelta",
    "TemperaturePoint",
    "ThermalDelta",
    "ThermalSnapshot",
]
