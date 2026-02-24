"""
Benchmark schemas — per-metric percentile rankings for welders.
Population: all welders' most recent complete session with a score.
"""
from pydantic import BaseModel
from typing import List

from models.shared_enums import WeldMetric


class MetricBenchmark(BaseModel):
    """Single-metric benchmark: welder value vs population stats."""

    metric: WeldMetric
    label: str
    welder_value: float
    population_mean: float
    population_min: float
    population_max: float
    population_std: float
    percentile: float  # 0–100
    tier: str  # "top" | "mid" | "bottom"


class WelderBenchmarks(BaseModel):
    """Full benchmark comparison for one welder vs population."""

    welder_id: str
    population_size: int
    metrics: List[MetricBenchmark]
    overall_percentile: float
