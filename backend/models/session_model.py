"""
Pydantic models for welding session data structures.
Will match TypeScript interfaces for type safety.
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
    """Complete welding session model"""

    meta: SessionMeta
    heat_map: Optional[List[HeatMapPoint]] = None
    torch_angle_deg: Optional[List[float]] = None
    score: Optional[SessionScore] = None
