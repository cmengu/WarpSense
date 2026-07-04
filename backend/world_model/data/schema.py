"""
schema.py defines SessionTensor — the canonical [T, 6] sensor array plus availability mask that every loader must produce and every model must consume (STEPS.md D2/D3).

Every data source (mock, polito, esp32, goldak) maps into this; nothing
downstream sees raw formats. The availability mask is carried end-to-end:
masked entries hold 0.0 in x and False in mask — models must consume the mask,
never infer missingness from zeros (0.0 is a legal sensor value).

For newcomers — this is the first stage of the whole pipeline:

    raw per-frame sensor readings (noisy, source-specific formats)
        │  loader_mock / loader_polito / loader_esp32
        ▼
    SessionTensor  (one per weld session)          ← THIS FILE
        │  splits.py  (70/15/15 train/val/test, by session)
        ▼
    batch.py collation → torch tensors → model

A SessionTensor is three things:
  x    [T, 6] float32 — T time frames × 6 sensor channels (volts, amps, torch
       angle, travel angle, travel speed, heat dissipation). The time series.
  mask [T, 6] bool    — which values are ACTUALLY present. Needed because 0.0
       is a legal reading, so zeros can't mean "missing". Sensor absent →
       x=0.0, mask=False. Carried end-to-end; models must respect it.
  meta dict           — session_id, source, and labels when they exist
       (quality class, fault bit, per-frame fusion depth).

Why bother: every source (fake dev data, Polito CSVs, future real captures,
future simulator output) has a different raw shape. Converting all of them
into this one dataclass means every downstream module — splits, batching,
models, eval, viz — is written exactly once.
"""

from dataclasses import dataclass, field
from typing import Iterable

import numpy as np

from world_model.config import CHANNELS, N_CHANNELS

VALID_SOURCES = {"mock", "polito", "esp32", "goldak"}


@dataclass
class SessionTensor:
    x: np.ndarray     # [T, 6] float32; 0.0 where mask is False
    mask: np.ndarray  # [T, 6] bool; True where a real sensor value is present (D3)
    meta: dict        # session_id, source, labels if any (quality class, fault
                      # bit, per-frame fusion depth), source-specific extras
                      # (e.g. polito force series)

    def __post_init__(self):
        self.x = np.asarray(self.x, dtype=np.float32)
        self.mask = np.asarray(self.mask, dtype=bool)
        if self.x.ndim != 2 or self.x.shape[1] != N_CHANNELS:
            raise ValueError(f"x must be [T, {N_CHANNELS}], got {self.x.shape}")
        if self.mask.shape != self.x.shape:
            raise ValueError(f"mask shape {self.mask.shape} != x shape {self.x.shape}")
        if not np.isfinite(self.x).all():
            raise ValueError("x contains non-finite values; encode missing as mask=False, x=0.0")
        if (self.x[~self.mask] != 0.0).any():
            raise ValueError("masked entries must hold 0.0")
        if "session_id" not in self.meta:
            raise ValueError("meta must contain session_id")
        if self.meta.get("source") not in VALID_SOURCES:
            raise ValueError(f"meta.source must be one of {sorted(VALID_SOURCES)}")

    @property
    def T(self) -> int:
        return self.x.shape[0]

    @property
    def session_id(self) -> str:
        return self.meta["session_id"]


def frames_to_session_tensor(frames: Iterable, session_id: str, source: str,
                             extra_meta: dict | None = None) -> SessionTensor:
    """
    Convert a sequence of Frame objects (backend/models/frame.py) into a
    SessionTensor. Shared by loader_mock and (post-Gate 0) loader_esp32 —
    one conversion path, so mask semantics cannot drift between sources.

    A channel value of None on a frame → mask False, x 0.0. CHANNELS names
    equal Frame attribute names by construction (config.py D1).
    """
    frames = list(frames)
    T = len(frames)
    x = np.zeros((T, N_CHANNELS), dtype=np.float32)
    mask = np.zeros((T, N_CHANNELS), dtype=bool)
    for t, frame in enumerate(frames):
        for c, name in enumerate(CHANNELS):
            value = getattr(frame, name)
            if value is not None:
                x[t, c] = value
                mask[t, c] = True
    meta = {"session_id": session_id, "source": source, "n_frames": T}
    if extra_meta:
        meta.update(extra_meta)
    return SessionTensor(x=x, mask=mask, meta=meta)
