"""
eval_world_model.py scores any model exposing predict(Batch) on macro-F1 and fusion MAE, appending every run to experiments/runs.csv so all reported numbers are reconstructible (STEPS.md Step 3, D11).

Scores the GRU baseline today and the world model at Gate 3 on the SAME code path
so numbers are comparable. Headline metric is MACRO F1: DEFECTIVE is the rare
class that matters — micro-F1/accuracy would hide it behind the GOOD majority.
Fusion MAE is computed only over sessions that carry depth labels (Goldak corpus;
mock has none).

For newcomers — this file is the referee:
  When the world model is compared against the GRU baseline (Gate 3), both
  must be scored by the SAME code, or the comparison is meaningless. So the
  harness is model-agnostic: anything with .predict(Batch) can be scored.

  Why macro-F1 and not accuracy: defective welds are rare. A lazy model that
  answers "GOOD" every time would score ~95% accuracy while missing every
  defect. F1 blends precision (of the welds flagged as class X, how many
  really were) with recall (of the real class-X welds, how many were caught);
  MACRO means each class's F1 counts equally in the average, so the rare
  DEFECTIVE class matters as much as the majority. Per-class recall is also
  reported so the number that matters most — fraction of defects caught — is
  visible directly.

  The runs.csv row (timestamp, seed, config hash — a fingerprint of the exact
  hyperparameters) enforces D11: every number ever quoted must be traceable
  to a logged run. No "I remember it got 0.86 once".
"""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from sklearn.metrics import f1_score, recall_score

from world_model.config import EXPERIMENTS_DIR, QUALITY_CLASSES
from world_model.data.batch import collate_sessions
from world_model.data.schema import SessionTensor

RUNS_CSV = EXPERIMENTS_DIR / "runs.csv"
RUNS_COLUMNS = ["timestamp_utc", "model", "config_hash", "seed", "split", "note",
                "n", "quality_f1_macro", "fusion_mae_mm", "per_class_recall"]


def evaluate(model, sessions: list[SessionTensor], batch_size: int = 16,
             device: str = "cpu") -> dict:
    y_true, y_pred = [], []
    depth_err = []
    for i in range(0, len(sessions), batch_size):
        chunk = sessions[i:i + batch_size]
        batch = collate_sessions(chunk).to(device)
        pred = model.predict(batch)
        labelled = batch.quality >= 0
        y_true += batch.quality[labelled].tolist()
        y_pred += pred["quality_probs"].argmax(dim=-1)[labelled].tolist()
        for b, s in enumerate(chunk):
            d_true = s.meta.get("fusion_depth_mm")
            if d_true is not None:
                # session-level MAE vs end-of-weld depth (per-frame comes with
                # the world model's trajectory head at Step 7)
                depth_err.append(abs(float(pred["depth_mm"][b]) - float(np.asarray(d_true)[-1])))

    labels = list(range(len(QUALITY_CLASSES)))
    result = {
        "n": len(sessions),
        "quality_f1_macro": float(f1_score(y_true, y_pred, labels=labels,
                                           average="macro", zero_division=0))
        if y_true else None,
        "fusion_mae_mm": float(np.mean(depth_err)) if depth_err else None,
        "per_class_recall": {
            name: float(r) for name, r in zip(
                QUALITY_CLASSES,
                recall_score(y_true, y_pred, labels=labels, average=None, zero_division=0),
            )
        } if y_true else None,
    }
    return result


def append_run(model_name: str, config: dict, seed: int, split: str,
               metrics: dict, note: str = "", runs_csv: Path = RUNS_CSV) -> str:
    """One row per evaluation (D11). Returns the config hash for cross-referencing."""
    config_hash = hashlib.sha256(
        json.dumps(config, sort_keys=True, default=str).encode()
    ).hexdigest()[:12]
    runs_csv.parent.mkdir(parents=True, exist_ok=True)
    new_file = not runs_csv.exists()
    with open(runs_csv, "a") as f:
        if new_file:
            f.write(",".join(RUNS_COLUMNS) + "\n")
        row = [
            datetime.now(timezone.utc).isoformat(timespec="seconds"),
            model_name, config_hash, str(seed), split, note,
            str(metrics.get("n", "")),
            f"{metrics['quality_f1_macro']:.4f}" if metrics.get("quality_f1_macro") is not None else "",
            f"{metrics['fusion_mae_mm']:.4f}" if metrics.get("fusion_mae_mm") is not None else "",
            json.dumps(metrics.get("per_class_recall") or {}).replace(",", ";"),
        ]
        f.write(",".join(row) + "\n")
    return config_hash
