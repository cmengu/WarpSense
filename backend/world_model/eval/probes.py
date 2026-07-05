"""
probes.py — Gate 1.5: the observability-ceiling test (STEPS.md Step 5).

For newcomers — the question this file answers, and why it can kill the project:
  The world model's job is to recover fusion depth from the 6 sensor channels.
  But no architecture can extract information the sensors don't carry. So
  before building anything expensive, we measure the ceiling: inside the
  simulator, where depth is KNOWN at every frame, how well can a strong,
  assumption-free reference model recover it from the sensors alone?

  Method:
  - Simulate ~1000 randomised sessions (domain randomisation via
    sample_params — no defects needed; this is about information content).
  - Slice the 6-channel sensor streams into sliding windows of 100 frames
    (1 s) with stride 50; flatten each window to a 600-number feature row.
    Label = TRUE depth at the window's last frame ("alignment defined ONCE",
    per the plan).
  - Fit a HistGradientBoostingRegressor (a gradient-boosted-trees model:
    strong on tabular data, no architectural assumptions, cheap on CPU) and
    score it with GroupKFold BY SESSION: all windows of one session stay in
    the same fold. This is load-bearing — windows from the same session in
    both train and test would leak (neighbouring windows overlap) and report
    a fake, too-low ceiling: a false green light.

  Reading the number (Gate 1.5):
  - ceiling MAE <= ~1.0 mm → the sensors observably carry depth; proceed to
    the world model (Steps 6-8).
  - ceiling MAE  >  1.0 mm → 6 scalars are physically insufficient. STOP:
    add sensing (the 5x5 thermal snapshots already in the Frame model) and
    re-run this test BEFORE building any world model.
  A mean-predictor baseline MAE is reported alongside, so the oracle's skill
  is visible (oracle ~= baseline would mean the sensors say nothing at all).

  Caveat (D4/Gate 1): the simulator is uncalibrated until Step 9, so this
  ceiling is provisional — a necessary check, not a sufficient one. Result
  is logged to runs.csv (D11) and experiments/gate_status.md.

CLI (from backend/):
  python -m world_model.eval.probes --tiny          # ~1 min plumbing check
  python -m world_model.eval.probes                 # full 1000-session gate
"""

import argparse
import time

import numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.model_selection import GroupKFold

from world_model.config import EXPERIMENTS_DIR, SEED, TINY
from world_model.data.schema import SessionTensor
from world_model.eval.eval_world_model import append_run
from world_model.simulator.weld_sim import sample_params, simulate_session

GATE_STATUS_MD = EXPERIMENTS_DIR / "gate_status.md"
WINDOW = 100   # frames (1 s at 100 Hz)
STRIDE = 50    # frames; without striding the row count explodes
GATE_THRESHOLD_MM = 1.0


def make_windows(sessions: list[SessionTensor], window: int = WINDOW,
                 stride: int = STRIDE) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Sensor windows → (X [N, 6*window], y [N] depth at window end, groups [N]).
    groups carries an integer per session for GroupKFold.
    """
    xs, ys, gs = [], [], []
    for g, s in enumerate(sessions):
        depth = np.asarray(s.meta["fusion_depth_mm"])
        for start in range(0, s.T - window + 1, stride):
            end = start + window
            xs.append(s.x[start:end].reshape(-1))
            ys.append(depth[end - 1])   # alignment: depth at the LAST frame
            gs.append(g)
    return (np.asarray(xs, dtype=np.float32),
            np.asarray(ys, dtype=np.float32),
            np.asarray(gs))


def oracle_ceiling(n_sessions: int = 1000, window: int = WINDOW, stride: int = STRIDE,
                   n_splits: int = 5, seed: int = SEED, verbose: bool = True) -> dict:
    t0 = time.time()
    sessions = [simulate_session(sample_params(seed * 100_000 + i))
                for i in range(n_sessions)]
    X, y, groups = make_windows(sessions, window, stride)
    if verbose:
        print(f"simulated {n_sessions} sessions → {len(X)} windows "
              f"({X.shape[1]} features) in {time.time() - t0:.0f}s")

    fold_maes, fold_baseline_maes = [], []
    for k, (tr, te) in enumerate(GroupKFold(n_splits=n_splits).split(X, y, groups)):
        oracle = HistGradientBoostingRegressor(random_state=seed)
        oracle.fit(X[tr], y[tr])
        mae = float(np.abs(oracle.predict(X[te]) - y[te]).mean())
        baseline = float(np.abs(y[tr].mean() - y[te]).mean())  # predict-the-mean
        fold_maes.append(mae)
        fold_baseline_maes.append(baseline)
        if verbose:
            print(f"fold {k}: oracle MAE {mae:.3f} mm   (mean-baseline {baseline:.3f} mm)")

    result = {
        "ceiling_mae_mm": float(np.mean(fold_maes)),
        "ceiling_mae_std": float(np.std(fold_maes)),
        "baseline_mae_mm": float(np.mean(fold_baseline_maes)),
        "n_sessions": n_sessions, "n_windows": int(len(X)),
        "window": window, "stride": stride, "n_splits": n_splits, "seed": seed,
        "gate_threshold_mm": GATE_THRESHOLD_MM,
        "verdict": "PASS" if np.mean(fold_maes) <= GATE_THRESHOLD_MM else "KILL",
        "runtime_s": round(time.time() - t0, 1),
    }
    return result


def record_gate(result: dict) -> None:
    """Append the Gate 1.5 outcome to experiments/gate_status.md (D11)."""
    GATE_STATUS_MD.parent.mkdir(parents=True, exist_ok=True)
    new = not GATE_STATUS_MD.exists()
    with open(GATE_STATUS_MD, "a") as f:
        if new:
            f.write("# Gate status (D11 — number vs threshold, or it didn't happen)\n\n")
        from datetime import date
        f.write(
            f"## Gate 1.5 — observability ceiling ({date.today().isoformat()})\n"
            f"- oracle ceiling MAE: **{result['ceiling_mae_mm']:.3f} mm** "
            f"(± {result['ceiling_mae_std']:.3f} across {result['n_splits']} "
            f"session-grouped folds) vs threshold {result['gate_threshold_mm']:.1f} mm "
            f"→ **{result['verdict']}**\n"
            f"- mean-predictor baseline: {result['baseline_mae_mm']:.3f} mm; "
            f"{result['n_sessions']} sessions / {result['n_windows']} windows "
            f"(w={result['window']}, stride={result['stride']}), seed {result['seed']}\n"
            f"- caveat: pre-Gate-1 simulator — ceiling is provisional until "
            f"calibration vs sectioned coupons (Step 9)\n\n"
        )


def main():
    p = argparse.ArgumentParser(description="Gate 1.5: sensor observability ceiling")
    p.add_argument("--tiny", action="store_true", help=f"dev preset: {TINY['n_sessions']} sessions")
    p.add_argument("--n-sessions", type=int, default=1000)
    p.add_argument("--seed", type=int, default=SEED)
    args = p.parse_args()
    n = TINY["n_sessions"] if args.tiny else args.n_sessions

    result = oracle_ceiling(n_sessions=n, seed=args.seed)
    print(result)
    metrics = {"n": result["n_windows"], "fusion_mae_mm": result["ceiling_mae_mm"]}
    append_run("oracle_ceiling_gbdt", result, args.seed, split="groupkfold",
               metrics=metrics,
               note=f"gate1.5 {result['verdict']}" + (" tiny" if args.tiny else ""))
    if not args.tiny:   # only a full run is a gate outcome
        record_gate(result)
        print(f"gate outcome recorded → {GATE_STATUS_MD}")


if __name__ == "__main__":
    main()
