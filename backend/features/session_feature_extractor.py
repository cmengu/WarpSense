# backend/features/session_feature_extractor.py
#
# Feature set is designed around Lack of Fusion / Lack of Penetration (LOF/LOP) —
# the defect class invisible to X-ray, visual, and dye penetrant inspection.
# Source: Amirafshari & Kolios, International Journal of Fatigue, 2022.
#
# LOF/LOP causal parameters:
#   1. Sustained low heat input (insufficient to melt base metal)
#   2. Torch angle deviation (misdirected heat away from joint root)
#   3. Sudden heat input drops at stitch transitions
#
# Required working directory for import: run from backend/ (cd backend) or
# ensure backend/ is on PYTHONPATH. All callers must use this convention.

import numpy as np
import pandas as pd
from dataclasses import dataclass, asdict
from typing import List, Optional

WINDOW_1S = 100          # 100 frames × 10ms = 1 second
OPTIMAL_ANGLE_DEG = 55.0  # Optimal work angle for aluminum MIG


@dataclass
class SessionFeatures:
    session_id: str

    # --- Heat input features (primary LOF/LOP predictor) ---
    heat_input_mean: float
    # Mean of (volts × amps) across arc-on frames.
    # Baseline signal — low mean = chronic under-heating.

    heat_input_min_rolling: float
    # Minimum value of the 1s rolling mean of heat input.
    # Catches cold windows even when overall mean looks acceptable.
    # This is the key LOF/LOP signal: a weld can pass on mean but
    # contain a 2-second cold window that caused fusion failure.

    heat_input_drop_severity: float
    # Max single-window decrease: max(rolling_mean[t-1] - rolling_mean[t]).
    # Captures sudden heat drops at stitch start/stop transitions —
    # the highest-risk moments for LOF at the weld root.

    heat_input_cv: float
    # Coefficient of variation of heat input across arc-on frames.
    # Captures chronic instability distinct from single-window drops.

    # --- Torch angle features (secondary LOF/LOP predictor) ---
    angle_deviation_mean: float
    # Mean of |angle_degrees - OPTIMAL_ANGLE_DEG| across arc-on frames.
    # Causal: off-angle directs heat to weld surface, not joint root.

    angle_max_drift_1s: float
    # Max (window_max - window_min) of angle within any 1s window.
    # Captures unstable torch handling mid-weld.

    # --- Arc stability features ---
    voltage_cv: float
    # Coefficient of variation of volts across arc-on frames.
    # Voltage instability = changing arc length = inconsistent penetration depth.

    amps_cv: float
    # Coefficient of variation of amps.
    # Spiky current = inconsistent heat delivery.

    # --- Thermal dissipation features ---
    heat_diss_mean: float
    # Mean heat_dissipation_rate_celsius_per_sec (nullable → fillna(0)).
    # Proxy for how fast the workpiece is cooling between inputs.

    heat_diss_max_spike: float
    # Max 1s rolling std of heat dissipation rate.
    # Captures thermal instability windows.

    # --- Session structure ---
    arc_on_ratio: float
    # Arc-on frames / total frames.
    # For stitch welds: lower ratio = more inter-stitch gaps = more LOF risk points.

    # --- Label ---
    quality_label: Optional[str] = None
    # GOOD / MARGINAL / DEFECTIVE. None at inference time.

    def to_vector(self) -> dict:
        """Flat dict for XGBoost. Excludes session_id and quality_label."""
        d = asdict(self)
        d.pop("session_id")
        d.pop("quality_label")
        return d

    @property
    def feature_count(self) -> int:
        return len(self.to_vector())


class SessionFeatureExtractor:
    """
    Converts a list of raw sensor frames into a SessionFeatures instance.
    All features have a direct causal link to LOF/LOP risk.
    """

    def extract(
        self,
        session_id: str,
        frames: List[dict],
        quality_label: Optional[str] = None,
    ) -> SessionFeatures:

        df = pd.DataFrame(frames)

        # Validate expected columns
        required = {
            "volts",
            "amps",
            "angle_degrees",
            "heat_dissipation_rate_celsius_per_sec",
        }
        missing = required - set(df.columns)
        if missing:
            raise ValueError(
                f"Session {session_id}: missing columns {missing}. "
                f"Found: {list(df.columns)}"
            )

        total_frames = len(df)

        # Arc-on filter: exclude dead arc frames (startup noise, inter-stitch gaps)
        arc_on = df[(df["volts"] > 5) & (df["amps"] > 5)].copy().reset_index(drop=True)

        if len(arc_on) < WINDOW_1S:
            raise ValueError(
                f"Session {session_id}: only {len(arc_on)} arc-on frames "
                f"(minimum {WINDOW_1S} required for rolling features)."
            )

        # Nullable field: heat_dissipation_rate is None for frame 0
        arc_on["heat_dissipation_rate_celsius_per_sec"] = (
            arc_on["heat_dissipation_rate_celsius_per_sec"].fillna(0.0)
        )

        # Derived signal: heat input per frame
        arc_on["heat_input"] = arc_on["volts"] * arc_on["amps"]

        # Rolling 1s mean of heat input
        rolling_heat_mean = arc_on["heat_input"].rolling(WINDOW_1S).mean()

        # Heat input drop: max decrease between consecutive rolling windows
        rolling_deltas = rolling_heat_mean.diff()
        heat_input_drop_severity = float(
            (-rolling_deltas).clip(lower=0).max()
        )

        # Torch angle deviation from optimal
        arc_on["angle_deviation"] = (
            arc_on["angle_degrees"] - OPTIMAL_ANGLE_DEG
        ).abs()

        # Arc stability
        voltage_mean = arc_on["volts"].mean()
        amps_mean = arc_on["amps"].mean()
        voltage_cv = (
            arc_on["volts"].std() / voltage_mean if voltage_mean > 0 else 0.0
        )
        amps_cv = arc_on["amps"].std() / amps_mean if amps_mean > 0 else 0.0

        # Heat input CV
        heat_input_mean = arc_on["heat_input"].mean()
        heat_input_cv = (
            arc_on["heat_input"].std() / heat_input_mean
            if heat_input_mean > 0
            else 0.0
        )

        return SessionFeatures(
            session_id=session_id,
            quality_label=quality_label,
            heat_input_mean=float(heat_input_mean),
            heat_input_min_rolling=float(rolling_heat_mean.min()),
            heat_input_drop_severity=float(heat_input_drop_severity),
            heat_input_cv=float(heat_input_cv),
            angle_deviation_mean=float(arc_on["angle_deviation"].mean()),
            angle_max_drift_1s=float(
                arc_on["angle_degrees"]
                .rolling(WINDOW_1S)
                .apply(lambda x: x.max() - x.min(), raw=True)
                .max()
            ),
            voltage_cv=float(voltage_cv),
            amps_cv=float(amps_cv),
            heat_diss_mean=float(
                arc_on["heat_dissipation_rate_celsius_per_sec"].mean()
            ),
            heat_diss_max_spike=float(
                arc_on["heat_dissipation_rate_celsius_per_sec"]
                .rolling(WINDOW_1S)
                .std()
                .max()
            ),
            arc_on_ratio=float(len(arc_on) / total_frames),
        )


def generate_feature_dataset() -> List[SessionFeatures]:
    """
    Returns SessionFeatures for all mock sessions.
    Quality labels inferred from archetype:
      stitch_expert       → GOOD
      continuous_novice   → MARGINAL
    Caller must run from backend/ or have backend/ on PYTHONPATH.
    """
    # Local import: this utility is only called during training.
    # Caller must run from cd backend or have backend/ on PYTHONPATH.
    from data.mock_sessions import (
        _generate_stitch_expert_frames,
        _generate_continuous_novice_frames,
    )

    def to_dicts(frames):
        f0 = frames[0]
        if hasattr(f0, "model_dump"):
            return [f.model_dump() for f in frames]
        if isinstance(f0, dict):
            return list(frames)
        return [vars(f) for f in frames]

    ARCHETYPES = [
        ("stitch_expert", _generate_stitch_expert_frames, "GOOD", 4),
        ("continuous_novice", _generate_continuous_novice_frames, "MARGINAL", 6),
    ]

    extractor = SessionFeatureExtractor()
    dataset: List[SessionFeatures] = []

    for arc_type, generator_fn, label, n_sessions in ARCHETYPES:
        for i in range(n_sessions):
            session_id = f"sess_{arc_type}_{i+1:03d}"
            frames = generator_fn(i, 1500)
            frames_as_dicts = to_dicts(frames)
            features = extractor.extract(session_id, frames_as_dicts, label)
            dataset.append(features)

    return dataset
