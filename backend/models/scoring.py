"""
Scoring models for rule-based evaluation.
This code models a session’s rule-based scoring: each rule has a threshold and pass/fail, and SessionScore aggregates them into a total score plus detailed per-rule results.
"""

from typing import List, Optional

from pydantic import BaseModel


class ScoreRule(BaseModel):
    """Individual scoring rule result."""

    rule_id: str
    threshold: float
    passed: bool
    actual_value: Optional[float] = None


class SessionScore(BaseModel):
    """Session scoring result."""

    total: int
    rules: List[ScoreRule]
    wqi_timeline: Optional[List[dict]] = None
    mean_wqi: Optional[float] = None
    median_wqi: Optional[float] = None
    min_wqi: Optional[int] = None
    max_wqi: Optional[int] = None
    wqi_trend: Optional[str] = None
