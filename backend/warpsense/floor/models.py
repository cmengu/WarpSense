"""
AWS D1.2 decomposition scoring models. Schema only — no business logic.
"""

from typing import Dict, List, Tuple

from pydantic import BaseModel, Field


class ExcursionEvent(BaseModel):
    """Single excursion event: parameter outside allowed range for a duration."""

    timestamp_ms: float
    parameter: str  # e.g. "travel_angle_degrees", "heat_input_kj_per_mm"
    value: float
    threshold: float
    duration_ms: float


class ScoreComponent(BaseModel):
    """One AWS D1.2-relevant score component (heat input, torch angle, etc.)."""

    name: str
    passed: bool
    score: float  # 0.0–1.0
    excursions: List[ExcursionEvent] = Field(default_factory=list)
    summary: str


class DecomposedSessionScore(BaseModel):
    """
    AWS D1.2 decomposed session score. Canonical output for new scoring.
    Replaces abstract single-number score with structured components.
    """

    session_id: str
    overall_score: float  # weighted mean of component scores
    passed: bool  # all critical components passed
    components: Dict[str, ScoreComponent] = Field(default_factory=dict)
    frame_count: int
    arc_on_frame_count: int
    computed_at_ms: float = 0.0
    wps_range_kj_per_mm: Tuple[float, float] = (0.9, 1.5)
