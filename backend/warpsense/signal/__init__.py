"""
signal/ — the ONE home for signal truth.

Physical facts about the sensor stream: is the arc lit, null-safe statistics,
thermal geometry, window sizes. Nothing here encodes a quality judgment —
no GOOD/MARGINAL, no pass/fail, no WQI weights. If a constant answers
"is this weld acceptable?" it belongs in floor/ or classifier/, not here.

realtime/ deliberately does NOT import this package: its alert thresholds
are latency-tuned and versioned separately (see realtime/alert_engine.py).
"""

from warpsense.signal.arc import (
    ARC_ON_MIN_AMPS,
    ARC_ON_MIN_VOLTS,
    df_arc_mask,
    is_arc_on,
)
from warpsense.signal.stats import (
    mean,
    population_std,
    safe_float,
    sample_std,
    value_range,
)
from warpsense.signal.thermal import (
    latest_center_temp,
    north_south_mean_delta,
    nsew_asymmetry,
)
from warpsense.signal.windows import (
    POROSITY_WINDOW_FRAMES,
    WINDOW_1S_FRAMES,
    WQI_WINDOW_FRAMES,
)

__all__ = [
    "ARC_ON_MIN_AMPS",
    "ARC_ON_MIN_VOLTS",
    "POROSITY_WINDOW_FRAMES",
    "WINDOW_1S_FRAMES",
    "WQI_WINDOW_FRAMES",
    "df_arc_mask",
    "is_arc_on",
    "latest_center_temp",
    "mean",
    "north_south_mean_delta",
    "nsew_asymmetry",
    "population_std",
    "safe_float",
    "sample_std",
    "value_range",
]
