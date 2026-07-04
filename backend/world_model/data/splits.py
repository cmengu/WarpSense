"""
Session-level splits (STEPS.md Step 1, D9).

Rules this module enforces:
- Split by SESSION, never by frame. Frames from one weld are radically
  autocorrelated; frame-level splits leak and report fake numbers (the same
  failure mode Gate 1.5 guards with GroupKFold).
- Deterministic: assignment is a salted SHA-256 of the session_id, so it never
  changes across runs, machines, or corpus growth — adding sessions never moves
  an existing session between splits.
- OOD holdout: for the Goldak corpus, whole parameter-space regions are
  reserved via a meta predicate and NEVER enter train/val/test.
"""

import hashlib
from typing import Callable, Iterable

from world_model.config import SEED, SPLIT_FRACTIONS
from world_model.data.schema import SessionTensor

SPLITS = ("train", "val", "test")


def _bucket(session_id: str, seed: int) -> float:
    """Stable position in [0, 1) from session_id — independent of Python's hash()."""
    digest = hashlib.sha256(f"{seed}:{session_id}".encode()).digest()
    return int.from_bytes(digest[:8], "big") / 2**64


def split_sessions(
    sessions: Iterable[SessionTensor],
    seed: int = SEED,
    fractions: dict[str, float] = SPLIT_FRACTIONS,
    ood_predicate: Callable[[dict], bool] | None = None,
) -> dict[str, list[SessionTensor]]:
    """
    → {"train": [...], "val": [...], "test": [...], "ood": [...]}.

    ood_predicate(meta) → True routes the session to the "ood" split before
    any hashing (e.g. plate-thickness extremes of the Goldak corpus, D9).
    """
    if abs(sum(fractions[s] for s in SPLITS) - 1.0) > 1e-9:
        raise ValueError(f"fractions must sum to 1, got {fractions}")

    out: dict[str, list[SessionTensor]] = {s: [] for s in (*SPLITS, "ood")}
    train_hi = fractions["train"]
    val_hi = train_hi + fractions["val"]
    for session in sessions:
        if ood_predicate is not None and ood_predicate(session.meta):
            out["ood"].append(session)
            continue
        b = _bucket(session.session_id, seed)
        if b < train_hi:
            out["train"].append(session)
        elif b < val_hi:
            out["val"].append(session)
        else:
            out["test"].append(session)
    return out
