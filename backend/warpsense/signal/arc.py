"""
Arc state detection — the single definition of "the arc is lit".

Canonical thresholds: volts > 5 AND amps > 5. A welding arc cannot sustain
below ~14 V / ~40 A, so 5/5 sits well above sensor noise and well below any
real arc; it classifies startup noise, inter-stitch gaps, and accidental
breaks as arc-off. This is the definition the weld classifier was trained
with (session_feature_extractor), adopted as canonical because the trained
GBDT artifact is frozen against it.

History (unified in PR 2): features/extractor used volts > 1 with amps
truthy; floor/scorer and the interpass component used amps > 1 alone.

Exclusions:
  - realtime/ keeps its own latency-tuned thresholds on purpose.
  - floor/heat_input.py's per-frame gate is data availability
    (amps, volts AND travel speed present), not arc state — it must keep
    skipping arc-on frames whose speed sensor dropped out.
"""

from typing import Optional

ARC_ON_MIN_VOLTS = 5.0
ARC_ON_MIN_AMPS = 5.0


def is_arc_on(volts: Optional[float], amps: Optional[float]) -> bool:
    """True when both volts and amps are present and above the arc floor."""
    return (
        volts is not None
        and amps is not None
        and volts > ARC_ON_MIN_VOLTS
        and amps > ARC_ON_MIN_AMPS
    )


def df_arc_mask(df):
    """Boolean arc-on mask for a frames DataFrame with volts/amps columns.

    Same comparison as is_arc_on; NaN compares False on both sides, so
    frames with missing volts or amps are arc-off, matching the scalar form.
    """
    return (df["volts"] > ARC_ON_MIN_VOLTS) & (df["amps"] > ARC_ON_MIN_AMPS)
