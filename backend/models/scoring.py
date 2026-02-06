"""
Scoring models for rule-based evaluation.
This code models a session’s rule-based scoring: each rule has a threshold and pass/fail, and SessionScore aggregates them into a total score plus detailed per-rule results.
"""

from typing import List

from pydantic import BaseModel


class ScoreRule(BaseModel):
    """Individual scoring rule result."""

    rule_id: str
    threshold: float
    passed: bool


class SessionScore(BaseModel):
    """Session scoring result."""

    total: int
    rules: List[ScoreRule]
