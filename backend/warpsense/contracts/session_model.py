"""
Legacy Pydantic models for old welding session format (meta, heat_map, torch_angle_deg, score).
DEPRECATED: Use models.session.Session with Frame[] for canonical time-series contract.
Kept for backwards compatibility with session_001.json-style data only.
"""

from typing import List, Optional
from pydantic import BaseModel


class SessionMeta(BaseModel):
    """Session metadata"""

    session_id: str
    start_timestamp_ms: int
    firmware_version: str


class HeatMapPoint(BaseModel):
    """Heat map data point"""

    x_mm: float
    y_mm: float
    intensity_norm: float


class ScoreRule(BaseModel):
    """Individual scoring rule result"""

    rule_id: str
    threshold: float
    passed: bool


class SessionScore(BaseModel):
    """Session scoring result"""

    total: int
    rules: List[ScoreRule]


class WeldingSession(BaseModel):
    """DEPRECATED. Use models.session.Session for canonical time-series format."""

    meta: SessionMeta
    heat_map: Optional[List[HeatMapPoint]] = None
    torch_angle_deg: Optional[List[float]] = None
    score: Optional[SessionScore] = None
