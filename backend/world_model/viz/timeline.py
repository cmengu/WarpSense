"""
Dev visualization (STEPS.md Step 2, D10) — matplotlib timeline for any
SessionTensor from any loader. Built EARLY so every artifact (mock, Polito,
Goldak, real) gets eyeballed from Step 3 onward.

CLI:  python -m world_model.viz.timeline --source mock  --kind al_cold --index 0
      python -m world_model.viz.timeline --source polito --index 3

D10 hard rule reminder: this is a DEV tool. Risk bands only in any user-facing
surface — no mm figures in any UI until Gate 5. The depth overlay here is for
developer eyes on synthetic/validated data.
"""

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless — never require a display
import matplotlib.pyplot as plt
import numpy as np

from world_model.config import CHANNELS, EXPERIMENTS_DIR, SENSOR_HZ
from world_model.data.schema import SessionTensor

PLOTS_DIR = EXPERIMENTS_DIR / "plots"

RISK_COLORS = {0: "#2e7d32", 1: "#f9a825", 2: "#c62828"}  # green / yellow / red


def _grey_out_masked(ax, t, present: np.ndarray):
    """Shade contiguous mask-False spans so missing data is VISIBLY missing (D4)."""
    absent = ~present
    if not absent.any():
        return
    edges = np.flatnonzero(np.diff(absent.astype(np.int8)))
    starts = ([0] if absent[0] else []) + [int(e) + 1 for e in edges if absent[int(e) + 1]]
    ends = [int(e) + 1 for e in edges if absent[int(e)]] + ([len(absent)] if absent[-1] else [])
    for s, e in zip(starts, ends):
        ax.axvspan(t[s], t[min(e, len(t) - 1)], color="0.85", zorder=0)


def plot_session(st: SessionTensor, extra: dict | None = None,
                 out_dir: Path = PLOTS_DIR) -> Path:
    """
    Render a session: 6 stacked channel subplots (masked spans greyed out),
    plus optional overlay rows from `extra`:
      depth_hat [T]        — predicted fusion depth curve (dev only, see D10)
      depth_std [T]        — ± band around depth_hat
      depth_true [T]       — ground-truth depth (Goldak corpus)
      z_phys    [T, 4]     — grounded latent traces
      risk      [T] ∈{0,1,2} — green/yellow/red band strip
    Returns the written PNG path: experiments/plots/{session_id}.png
    """
    extra = extra or {}
    n_extra = sum(k in extra for k in ("depth_hat", "z_phys", "risk"))
    if "depth_true" in extra and "depth_hat" not in extra:
        n_extra += 1
    n_rows = len(CHANNELS) + n_extra

    t = np.arange(st.T) / SENSOR_HZ  # seconds
    fig, axes = plt.subplots(n_rows, 1, figsize=(12, 1.4 * n_rows),
                             sharex=True, constrained_layout=True)
    axes = np.atleast_1d(axes)

    for c, name in enumerate(CHANNELS):
        ax = axes[c]
        present = st.mask[:, c]
        _grey_out_masked(ax, t, present)
        if present.any():
            y = np.where(present, st.x[:, c], np.nan)  # gaps break the line
            ax.plot(t, y, lw=0.7, color="#1565c0")
        else:
            ax.text(0.5, 0.5, "channel absent", transform=ax.transAxes,
                    ha="center", va="center", color="0.5", fontsize=9)
        ax.set_ylabel(name.replace("_", "\n"), fontsize=7, rotation=0,
                      ha="right", va="center")

    row = len(CHANNELS)
    if "depth_hat" in extra or "depth_true" in extra:
        ax = axes[row]; row += 1
        if "depth_true" in extra:
            ax.plot(t, extra["depth_true"], lw=0.9, color="0.3", label="depth true")
        if "depth_hat" in extra:
            d = np.asarray(extra["depth_hat"])
            ax.plot(t, d, lw=0.9, color="#6a1b9a", label="depth ĥat")
            if "depth_std" in extra:
                s = np.asarray(extra["depth_std"])
                ax.fill_between(t, d - s, d + s, color="#6a1b9a", alpha=0.2)
        ax.legend(fontsize=6, loc="upper right")
        ax.set_ylabel("depth\nmm (dev)", fontsize=7, rotation=0, ha="right", va="center")
    if "z_phys" in extra:
        ax = axes[row]; row += 1
        for k in range(np.asarray(extra["z_phys"]).shape[1]):
            ax.plot(t, extra["z_phys"][:, k], lw=0.7, label=f"z_phys[{k}]")
        ax.legend(fontsize=6, ncols=4, loc="upper right")
        ax.set_ylabel("z_phys", fontsize=7, rotation=0, ha="right", va="center")
    if "risk" in extra:
        ax = axes[row]; row += 1
        risk = np.asarray(extra["risk"])
        for level, color in RISK_COLORS.items():
            where = risk == level
            if where.any():
                ax.fill_between(t, 0, 1, where=where, color=color, step="mid")
        ax.set_yticks([])
        ax.set_ylabel("risk", fontsize=7, rotation=0, ha="right", va="center")

    axes[-1].set_xlabel("time (s)")
    fig.suptitle(f"{st.session_id}  ·  source={st.meta['source']}  ·  T={st.T}",
                 fontsize=10)
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{st.session_id}.png"
    fig.savefig(out, dpi=110)
    plt.close(fig)
    return out


def main():
    p = argparse.ArgumentParser(description="Render a SessionTensor timeline PNG")
    p.add_argument("--source", choices=["mock", "polito"], required=True)
    p.add_argument("--kind", default="stitch_expert",
                   help="mock only: stitch_expert | continuous_novice | al_* parametric")
    p.add_argument("--index", type=int, default=0)
    p.add_argument("--out-dir", type=Path, default=PLOTS_DIR)
    args = p.parse_args()

    if args.source == "mock":
        from world_model.data.loader_mock import load_mock_session
        st = load_mock_session(args.kind, args.index)
    else:
        from world_model.data.loader_polito import load_polito_sessions
        st = load_polito_sessions(limit=args.index + 1)[args.index]
    print(plot_session(st, out_dir=args.out_dir))


if __name__ == "__main__":
    main()
