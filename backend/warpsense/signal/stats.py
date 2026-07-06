"""
Null-safe statistics with the codebase's established conventions.

Two standard deviations exist here on purpose:
  sample_std     — statistics.stdev, n-1 denominator. The floor's stability
                   features (amps_stddev, heat_diss_stddev) and the warp
                   predictor's angle_std/amps_std were defined with it.
  population_std — numpy std, n denominator. travel_speed_stddev, the
                   cyclogram ellipse, and porosity window sigma were defined
                   with it.
Collapsing them would silently shift every one of those features; callers
must keep using the variant their feature was calibrated with.
"""

import statistics
from typing import Optional, Sequence

import numpy as np


def sample_std(values: Sequence[float]) -> float:
    """statistics.stdev with the <2-samples guard; 0.0 when undefined."""
    return statistics.stdev(values) if len(values) > 1 else 0.0


def population_std(values: Sequence[float]) -> float:
    """float(np.std) with the <2-samples guard; 0.0 when undefined."""
    return float(np.std(values)) if len(values) > 1 else 0.0


def mean(values: Sequence[float], default: float = 0.0) -> float:
    """statistics.mean, or default for an empty sequence."""
    return statistics.mean(values) if values else default


def value_range(values: Sequence[float]) -> float:
    """max - min, or 0.0 for an empty sequence."""
    return max(values) - min(values) if values else 0.0


def safe_float(val, default: float = 0.0) -> float:
    """Coerce to float; return default on None/ValueError/TypeError.

    DB JSONB round-trips can yield ints, strings, or None for numeric fields.
    """
    if val is None:
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default
