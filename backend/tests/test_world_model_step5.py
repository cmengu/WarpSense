"""
Step 5 tests (STEPS.md): the observability-ceiling machinery must window
sessions correctly, keep GroupKFold leak-free by session, and produce a
sane ceiling on a small corpus. The GATE number comes from the full
1000-session CLI run, not from these tests.
"""

import numpy as np

from world_model.eval.probes import make_windows, oracle_ceiling
from world_model.simulator.weld_sim import sample_params, simulate_session


def _corpus(n=6):
    return [simulate_session(sample_params(1000 + i)) for i in range(n)]


def test_make_windows_shapes_and_alignment():
    sessions = _corpus(3)
    X, y, groups = make_windows(sessions, window=100, stride=50)
    per_session = (sessions[0].T - 100) // 50 + 1
    assert X.shape == (3 * per_session, 600)
    assert y.shape == groups.shape == (3 * per_session,)
    # alignment contract: label is depth at the window's LAST frame
    d0 = sessions[0].meta["fusion_depth_mm"]
    assert y[0] == np.float32(d0[99])
    assert y[1] == np.float32(d0[149])


def test_groups_identify_sessions():
    X, y, groups = make_windows(_corpus(4), window=100, stride=50)
    assert set(groups) == {0, 1, 2, 3}
    # equal-length sessions → equal window counts per group
    counts = np.bincount(groups)
    assert (counts == counts[0]).all()


def test_oracle_ceiling_small_corpus():
    result = oracle_ceiling(n_sessions=24, n_splits=3, seed=7, verbose=False)
    assert result["n_sessions"] == 24
    assert np.isfinite(result["ceiling_mae_mm"])
    assert result["verdict"] in ("PASS", "KILL")
    # depth is a (lagged) function of the sensed controls, so even on a tiny
    # corpus the oracle must beat predicting the mean — if it can't, the
    # windowing or grouping is broken
    assert result["ceiling_mae_mm"] < result["baseline_mae_mm"]
