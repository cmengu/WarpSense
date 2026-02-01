"""
Models package for welding session data structures
"""

# Import from root models.py for backward compatibility
import importlib.util
from pathlib import Path
spec = importlib.util.spec_from_file_location("models_root", Path(__file__).parent.parent / "models.py")
models_root = importlib.util.module_from_spec(spec)
spec.loader.exec_module(models_root)
DashboardData = models_root.DashboardData

from .session_model import (
    SessionMeta,
    HeatMapPoint,
    ScoreRule,
    SessionScore,
    WeldingSession,
)

__all__ = [
    "DashboardData",
    "SessionMeta",
    "HeatMapPoint",
    "ScoreRule",
    "SessionScore",
    "WeldingSession",
]
