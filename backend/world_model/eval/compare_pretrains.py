"""
compare_pretrains.py — C5: the ruler every pretraining contender is measured with.

For newcomers — what "linear probe" means and why it's the fair test:
  A pretrained encoder claims to have learned something about weld dynamics.
  To measure THAT claim (and not a classifier's cleverness), we freeze the
  encoder, turn each weld into one fixed vector, and ask the simplest possible
  model — logistic regression, a single linear layer — to predict the fault
  bit from it. If the information isn't already laid out in the embedding,
  a linear model can't dig it out. A stronger probe would blur the question.

  The pipeline, identical for every contender (C4-C7 spec, issue #18):
    load transfer checkpoint → freeze encoder → embed ProbeWindows
    → mean-pool per weld → linear probe → macro-F1, GroupKFold by session.

  Per-window vector = the GRU hidden state at the LAST frame (the trunk's
  summary of the window — the same summary the Step 6 fault head consumed);
  per-weld vector = the mean of its window vectors. GroupKFold by session is
  load-bearing for the same reason as Gate 1.5: neighbouring windows overlap,
  so any split that lets one weld's windows straddle folds leaks. Pooling per
  weld BEFORE splitting makes that structural — one row per weld — and the
  grouped split stays anyway as belt-and-braces.

  A randomly-initialised (untrained) encoder is scored alongside as the floor:
  a pretrained encoder that only matches it has learned nothing the probe can
  see. "probe ≈ baseline" is also the pre-registered too-short-window symptom.

This file is deliberately a RULER, not a verdict: C6 (ablations) and C7 (the
head-to-head) are this harness applied repeatedly. Model selection runs on
--split val; the decisive C7 comparison runs on --split test, untouched until
the entrant is chosen.

CLI (from backend/):
  python -m world_model.eval.compare_pretrains CKPT [CKPT ...] --tiny
  python -m world_model.eval.compare_pretrains \
      experiments/checkpoints/jepa_pretrain_*.pt \
      experiments/checkpoints/masked_recon_windows_*.pt --split val
"""

import argparse
from pathlib import Path

import numpy as np
import torch
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score
from sklearn.model_selection import GroupKFold

from world_model.architecture.trunk import StemTrunkEncoder
from world_model.config import SEED, TINY
from world_model.data.schema import SessionTensor
from world_model.data.windows import ProbeWindows
from world_model.pretraining.masked_recon import PRETRAIN_CHANNELS

WINDOW = 300   # the C4-C7 diet; C6 sweeps this
STRIDE = 50
LABEL_KEY = "fault"
N_SPLITS = 5


@torch.no_grad()
def embed_welds(encoder: StemTrunkEncoder, sessions: list[SessionTensor],
                label_key: str = LABEL_KEY, window: int = WINDOW,
                stride: int = STRIDE, batch_size: int = 64,
                device: str = "cpu") -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Frozen encoder → one mean-pooled vector per weld.
    Returns (X [n_welds, hidden], y [n_welds] labels, groups [n_welds]).
    Welds shorter than one window contribute no rows and are dropped.
    """
    ds = ProbeWindows(sessions, label_keys=[label_key], window=window,
                      stride=stride, channels=PRETRAIN_CHANNELS)
    encoder = encoder.to(device).eval()
    sums = torch.zeros(len(sessions), encoder.hidden_dim)
    counts = torch.zeros(len(sessions))
    for i in range(0, len(ds), batch_size):
        items = [ds[j] for j in range(i, min(i + batch_size, len(ds)))]
        x = torch.stack([it[0] for it in items]).to(device)
        mask = torch.stack([it[1] for it in items]).to(device)
        vec = encoder(x, mask)[:, -1].cpu()   # GRU summary of each window
        for v, it in zip(vec, items):
            sums[it[3]] += v
            counts[it[3]] += 1
    keep = (counts > 0).numpy()
    X = (sums / counts.clamp(min=1).unsqueeze(-1)).numpy()[keep]
    y = np.array([float(s.meta[label_key]) for s in sessions])[keep]
    groups = np.arange(len(sessions))[keep]
    return X, y, groups


def probe_macro_f1(X: np.ndarray, y: np.ndarray, groups: np.ndarray,
                   n_splits: int = N_SPLITS, seed: int = SEED) -> dict:
    """
    Linear probe under GroupKFold: fit on train folds, predict the held-out
    fold, pool all held-out predictions, score macro-F1 once. Pooling (rather
    than averaging per-fold F1) keeps the number stable when the positive
    class is rare enough that some folds hold none of it (79/1976 faults).
    """
    n_splits = min(n_splits, len(np.unique(groups)))
    if y.sum() < n_splits:
        print(f"WARNING: only {int(y.sum())} positive welds across {n_splits} "
              f"folds — the probe is under-powered at this data size")
    preds = np.zeros_like(y)
    fold_f1, test_groups_per_fold = [], []
    for tr, te in GroupKFold(n_splits=n_splits).split(X, y, groups):
        if len(np.unique(y[tr])) < 2:
            preds[te] = y[tr][0]   # degenerate fold: constant prediction
            fold_f1.append(f1_score(y[te], preds[te], average="macro",
                                    zero_division=0))
            test_groups_per_fold.append(set(groups[te].tolist()))
            continue
        clf = LogisticRegression(max_iter=2000, class_weight="balanced",
                                 random_state=seed)
        clf.fit(X[tr], y[tr])
        preds[te] = clf.predict(X[te])
        fold_f1.append(f1_score(y[te], preds[te], average="macro", zero_division=0))
        test_groups_per_fold.append(set(groups[te].tolist()))
    return {
        "macro_f1": float(f1_score(y, preds, average="macro", zero_division=0)),
        "fold_f1": [float(f) for f in fold_f1],
        "fold_f1_std": float(np.std(fold_f1)),
        "n_splits": n_splits,
        "test_groups_per_fold": test_groups_per_fold,
    }


def score_checkpoint(path: Path, sessions: list[SessionTensor],
                     label_key: str = LABEL_KEY, window: int = WINDOW,
                     stride: int = STRIDE, device: str = "cpu",
                     seed: int = SEED) -> dict:
    """One comparable row per contract checkpoint — the C5 seam."""
    from world_model.pretraining.common import build_encoder, load_transfer_checkpoint
    ckpt = load_transfer_checkpoint(Path(path))
    X, y, groups = embed_welds(build_encoder(ckpt), sessions, label_key=label_key,
                               window=window, stride=stride, device=device)
    probe = probe_macro_f1(X, y, groups, seed=seed)
    return {
        "checkpoint": Path(path).name,
        "objective": ckpt["objective"],
        "macro_f1": probe["macro_f1"],
        "fold_f1_std": probe["fold_f1_std"],
        "n_welds": int(len(y)),
        "n_positive": int(y.sum()),
    }


def score_random_floor(sessions: list[SessionTensor], label_key: str = LABEL_KEY,
                       window: int = WINDOW, stride: int = STRIDE,
                       device: str = "cpu", seed: int = SEED) -> dict:
    """The untrained-encoder floor every contender must clear."""
    torch.manual_seed(seed)
    encoder = StemTrunkEncoder(PRETRAIN_CHANNELS)
    X, y, groups = embed_welds(encoder, sessions, label_key=label_key,
                               window=window, stride=stride, device=device)
    probe = probe_macro_f1(X, y, groups, seed=seed)
    return {
        "checkpoint": "(random init)",
        "objective": "none",
        "macro_f1": probe["macro_f1"],
        "fold_f1_std": probe["fold_f1_std"],
        "n_welds": int(len(y)),
        "n_positive": int(y.sum()),
    }


def main():
    from world_model.data.loader_polito import load_polito_sessions
    from world_model.data.splits import split_sessions
    from world_model.eval.eval_world_model import append_run

    p = argparse.ArgumentParser(
        description="C5: apples-to-apples linear-probe comparison of "
                    "pretraining checkpoints")
    p.add_argument("checkpoints", nargs="+", help="transfer checkpoints to score")
    p.add_argument("--tiny", action="store_true", help=f"dev preset: {TINY}")
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--split", default="val", choices=["val", "test"],
                   help="val = model selection; test = the C7 decision ONLY")
    p.add_argument("--window", type=int, default=WINDOW)
    p.add_argument("--stride", type=int, default=STRIDE)
    p.add_argument("--device", default="cpu", choices=["cpu", "mps", "cuda"])
    p.add_argument("--seed", type=int, default=SEED)
    p.add_argument("--no-random", action="store_true",
                   help="skip the random-init floor row")
    args = p.parse_args()
    limit = TINY["n_sessions"] if args.tiny else args.limit

    sessions = split_sessions(load_polito_sessions(limit=limit),
                              seed=args.seed)[args.split]
    n_fault = sum(int(s.meta[LABEL_KEY]) for s in sessions)
    print(f"probing on {args.split}: {len(sessions)} welds "
          f"({n_fault} faulty)  window={args.window} stride={args.stride}")

    rows = [] if args.no_random else [
        score_random_floor(sessions, window=args.window, stride=args.stride,
                           device=args.device, seed=args.seed)]
    rows += [score_checkpoint(c, sessions, window=args.window, stride=args.stride,
                              device=args.device, seed=args.seed)
             for c in args.checkpoints]

    print(f"\n{'objective':<14} {'macro-F1':>9} {'±fold':>7}  checkpoint")
    for r in rows:
        print(f"{r['objective']:<14} {r['macro_f1']:>9.4f} "
              f"{r['fold_f1_std']:>7.4f}  {r['checkpoint']}")

    config = dict(model="probe_compare", split=args.split, limit=limit,
                  window=args.window, stride=args.stride, seed=args.seed)
    for r in rows:
        # note stays comma-free (runs.csv is comma-joined)
        append_run("probe_compare", {**config, "checkpoint": r["checkpoint"]},
                   args.seed, split=args.split,
                   metrics=dict(n=r["n_welds"], quality_f1_macro=r["macro_f1"],
                                fusion_mae_mm=None, per_class_recall=None),
                   note=(f"linear probe; objective={r['objective']} "
                         f"ckpt={r['checkpoint']} fold_std={r['fold_f1_std']:.4f} "
                         f"positives={r['n_positive']}/{r['n_welds']}"))


if __name__ == "__main__":
    main()
