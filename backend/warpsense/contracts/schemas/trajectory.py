"""
Trajectory schemas — longitudinal score history for welders.
"""
from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel

from .shared import MetricScore


class TrajectoryPoint(BaseModel):
    """Score data for a single session in a welder's history."""

    session_id: str
    session_date: datetime
    score_total: float  # Must be finite; NaN rejected by validator
    metrics: List[MetricScore]
    session_index: int  # 1-based contiguous index (no gaps; skips produce contiguous display indices)


class WelderTrajectory(BaseModel):
    welder_id: str
    points: List[TrajectoryPoint]
    trend_slope: Optional[float] = None  # positive = improving
    projected_next_score: Optional[float] = None
    skipped_sessions_count: Optional[int] = None  # sessions skipped when get_session_score raised


class TrajectoryProjection(BaseModel):
    """Linear extrapolation from last 5 sessions. Optional for future use; unused in MVP."""

    current_score: float
    projected_next: float
    sessions_to_target: Optional[int] = None
    target_score: float = 80.0
