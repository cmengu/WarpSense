"""Pydantic models for WWAD aggregate API response."""

from typing import Optional

from pydantic import BaseModel


class AggregateKPIs(BaseModel):
    """Aggregated KPIs for supervisor dashboard."""

    avg_score: Optional[float] = None  # None if no scored sessions
    session_count: int
    top_performer: Optional[str] = None  # operator_id with best avg
    rework_count: int  # sessions with score_total < 60


class TrendPoint(BaseModel):
    """Single point in score trend over time."""

    date: str  # YYYY-MM-DD
    value: float


class CalendarDay(BaseModel):
    """Sessions count for a calendar day."""

    date: str  # YYYY-MM-DD
    value: int


class SessionSummary(BaseModel):
    """Minimal session summary for CSV export."""

    session_id: str
    operator_id: str
    weld_type: str
    start_time: str  # ISO
    score_total: Optional[int] = None
    frame_count: int


class AggregateKPIResponse(BaseModel):
    """Full aggregate API response."""

    kpis: AggregateKPIs
    trend: list[TrendPoint]
    calendar: list[CalendarDay]
    sessions: Optional[list[SessionSummary]] = None
    sessions_truncated: bool = False
