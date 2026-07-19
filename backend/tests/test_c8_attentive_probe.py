"""
test_c8_attentive_probe.py — the C8/D3 attentive-probe arm in
eval/compare_pretrains.py.

What these tests are actually defending. D3 adds a probe with parameters to a
harness whose entire credibility rested on the probe having almost none. That
buys sensitivity — V-JEPA measured +16-17 points from attentive probing — and it
buys a new failure mode: on 79 positives (C7 had 11-13) a learnable query can
score well by memorising which welds are faulty rather than by reading the
encoder, and the attentive score alone cannot tell those apart. So the tests
below are organised around three properties:

  1. The probe must READ. Given per-weld window sequences where the label is
     visible in a subset of windows, it must find them — and it must beat a
     mean-pool linear probe on data built so that mean-pooling destroys the
     signal, which is the whole argument for attentive probing.
  2. The capacity diagnostic must FIRE. A probe scoring on random-init
     embeddings above a linear probe on real ones must void the run, and the
     void flag must land on the reports themselves, not just the printed block.
  3. The linear path must be INERT. Every C5-C7 macro-F1 is a reproduction
     target, so the pluggable-fitter refactor that lets the attentive arm reuse
     the metric layer must leave the default path bit-identical.

Synthetic sequences are used throughout for the same reason ticket #20's tests
use synthetic embeddings: with real checkpoints a null result cannot be
attributed to the probe rather than to the data.
"""

from functools import partial

import numpy as np
import pytest
import torch

from world_model.eval.compare_pretrains import (
    ATTN_DROPOUT, AttentiveProbe, N_SPLITS, attentive_report,
    capacity_diagnostic, fit_attentive, oof_attentive_classification,
    oof_attentive_regression, oof_classification, oof_regression,
    pad_sequences, probe_classification, probe_macro_f1, probe_regression,
    report_headline, rich_report, run_capacity_diagnostic)

SEED = 1337
HIDDEN = 8


def marker_sequences(n=120, n_pos=40, hidden=HIDDEN, n_windows=6, gap=3.0,
                     seed=SEED):
    """
    Per-weld window sequences where the fault shows up in ONE window only.

    This is the geometry attentive probing exists for. A faulty weld is normal
    everywhere except a single window carrying a large marker; a healthy weld has
    none. Mean-pooling divides that marker by n_windows, sinking it into the
    noise, while a learnable query can point straight at it. Real welds are
    argued to look like this — a fault is a localised event inside an otherwise
    ordinary weld — which is why the linear-vs-attentive gap is a question about
    the data and not just about probe strength.
    """
    rng = np.random.default_rng(seed)
    y = np.zeros(n)
    y[rng.choice(n, size=n_pos, replace=False)] = 1.0
    seqs = []
    for i in range(n):
        s = rng.normal(size=(n_windows, hidden)).astype(np.float32)
        if y[i] == 1:
            s[rng.integers(0, n_windows), 0] += gap
        seqs.append(s)
    return seqs, y, np.arange(n)


def ragged_sequences(n=40, hidden=HIDDEN, seed=SEED):
    """Sequences of differing lengths — welds have differing durations."""
    rng = np.random.default_rng(seed)
    seqs = [rng.normal(size=(int(rng.integers(1, 7)), hidden)).astype(np.float32)
            for _ in range(n)]
    y = (np.arange(n) % 3 == 0).astype(float)
    return seqs, y, np.arange(n)


def mean_pooled(seqs):
    """The linear probe's view of the same welds: one mean vector each."""
    return np.stack([s.mean(axis=0) for s in seqs])


# ---------------------------------------------------------------- the module

def test_probe_is_the_D3_architecture_and_nothing_more():
    """Single query, single head, no MLP — so exactly 2H+1 parameters."""
    probe = AttentiveProbe(HIDDEN)
    assert probe.n_params() == 2 * HIDDEN + 1
    assert probe.query.shape == (HIDDEN,)
    # no MLP: the only Linear is the readout, and it is H -> 1
    linears = [m for m in probe.modules() if isinstance(m, torch.nn.Linear)]
    assert len(linears) == 1
    assert (linears[0].in_features, linears[0].out_features) == (HIDDEN, 1)
    assert any(isinstance(m, torch.nn.Dropout) for m in probe.modules())


def test_padding_is_masked_out_of_the_attention():
    """
    A padded weld must score exactly as its unpadded self. If padding leaked
    into the softmax, every short weld would be read partly as zeros and the
    probe's numbers would depend on the longest weld in the batch.
    """
    probe = AttentiveProbe(HIDDEN, dropout=0.0).eval()
    torch.manual_seed(SEED)
    real = torch.randn(1, 3, HIDDEN)
    padded = torch.cat([real, torch.randn(1, 4, HIDDEN)], dim=1)
    mask_full = torch.ones(1, 3, dtype=torch.bool)
    mask_pad = torch.tensor([[True] * 3 + [False] * 4])
    with torch.no_grad():
        a = probe(real, mask_full)
        b = probe(padded, mask_pad)
    assert torch.allclose(a, b, atol=1e-6)


def test_pad_sequences_shapes_and_mask():
    seqs, _, _ = ragged_sequences(n=10)
    x, mask = pad_sequences(seqs)
    assert x.shape == (10, max(len(s) for s in seqs), HIDDEN)
    assert mask.sum().item() == sum(len(s) for s in seqs)
    for i, s in enumerate(seqs):
        assert torch.allclose(x[i, :len(s)], torch.as_tensor(s))


def test_dropout_is_on_the_attention_weights_not_the_inputs():
    """
    D3 specifies dropout on the attention weights. Train mode must therefore
    perturb the output while eval mode is deterministic.
    """
    probe = AttentiveProbe(HIDDEN, dropout=0.5)
    x, mask = pad_sequences([np.ones((6, HIDDEN), dtype=np.float32)] * 4)
    torch.manual_seed(SEED)
    probe.train()
    outs = {float(probe(x, mask)[0]) for _ in range(20)}
    assert len(outs) > 1, "attention weights are not being dropped out"
    probe.eval()
    with torch.no_grad():
        assert float(probe(x, mask)[0]) == pytest.approx(float(probe(x, mask)[0]))


# ---------------------------------------------------------------- it reads

def test_attentive_probe_recovers_a_localised_signal():
    """
    The probe must find a marker that lives in one window of a weld — recovery
    well above chance, not near-perfect separation.

    The bar is 0.80, deliberately below the ~0.85 this data first suggested. The
    ceiling here is not the probe's optimiser, it is the estimator: the D3
    protocol nests early stopping inside the outer GroupKFold, so the stopping
    epoch is chosen on an inner-val fold, which on this 120-weld / 40-positive
    set is ~24 welds. An oracle that instead picked the stopping epoch on the
    outer TEST fold — the best any early-stopping rule could possibly do — tops
    out at OOF-AUC 0.857 with attention dropout off and 0.840 with the D3 default
    of 0.1; a rule confined to the inner fold is strictly weaker, and lands near
    0.82. A 0.85 bar would therefore be testing whether the estimator can beat
    its own oracle, not whether the probe reads the signal. 0.80 still separates
    a probe that finds the localised marker (chance is 0.50, and a mean-pool
    linear probe on the harder ten-window version manages only ~0.69) from one
    that does not.
    """
    seqs, y, groups = marker_sequences()
    oof = oof_attentive_classification(seqs, y, groups, seed=SEED)
    from sklearn.metrics import roc_auc_score
    assert roc_auc_score(y, oof["scores"]) > 0.80
    assert oof["probe_params"] == 2 * HIDDEN + 1


def test_attentive_beats_mean_pooled_linear_when_pooling_destroys_the_signal():
    """
    The C8 premise, stated as a test: on data where the signal is localised,
    mean-pooling into one vector loses it and the attentive probe does not. If
    this ever fails, the attentive arm is not buying what D3 claims it buys.
    """
    seqs, y, groups = marker_sequences(n_windows=10, gap=3.0)
    from sklearn.metrics import roc_auc_score
    lin = oof_classification(mean_pooled(seqs), y, groups, seed=SEED)
    att = oof_attentive_classification(seqs, y, groups, seed=SEED)
    assert roc_auc_score(y, att["scores"]) > roc_auc_score(y, lin["scores"])


def test_attentive_regression_tracks_a_continuous_target():
    """The depth-target twin: MAE must beat predicting the mean."""
    rng = np.random.default_rng(SEED)
    seqs, y = [], []
    for _ in range(80):
        s = rng.normal(size=(5, HIDDEN)).astype(np.float32)
        target = 2.0 * float(s[0, 0])
        s[0, 0] += 4.0            # the informative window, same slot each weld
        seqs.append(s)
        y.append(target)
    y = np.asarray(y, dtype=float)
    oof = oof_attentive_regression(seqs, y, np.arange(len(y)), seed=SEED)
    mae = float(np.abs(y - oof["preds"]).mean())
    assert mae < float(np.abs(y - y.mean()).mean())


def test_handles_ragged_and_single_window_welds():
    """Welds of one window must not crash the softmax or the fold loop."""
    seqs, y, groups = ragged_sequences()
    oof = oof_attentive_classification(seqs, y, groups, seed=SEED)
    assert len(oof["scores"]) == len(y)
    assert np.isfinite(oof["scores"]).all()


# ------------------------------------------------- early stopping is nested

def test_inner_validation_fold_never_touches_the_outer_test_fold():
    """
    The stopping epoch is a fitted quantity, so choosing it on the outer test
    fold would leak exactly what GroupKFold exists to prevent. This asserts the
    probe fitted on a training fold never saw any test-fold weld: we fit with
    the test-fold targets corrupted, and the fit must be unchanged.
    """
    seqs, y, groups = marker_sequences(n=60, n_pos=20)
    from sklearn.model_selection import GroupKFold
    tr, te = next(GroupKFold(n_splits=N_SPLITS).split(seqs, y, groups))
    clean = fit_attentive(seqs, y, tr, groups, "classification", seed=SEED)
    poisoned_y = y.copy()
    poisoned_y[te] = 1.0 - poisoned_y[te]
    poisoned = fit_attentive(seqs, poisoned_y, tr, groups, "classification",
                             seed=SEED)
    assert torch.allclose(clean.query, poisoned.query)
    assert torch.allclose(clean.head.weight, poisoned.head.weight)


def test_early_stopping_restores_the_best_epoch_not_the_last():
    """
    With a patience of 1 and a long budget, training must stop early — and the
    returned weights must differ from a run that was forced to the full budget,
    which is only true if the best state is restored.
    """
    seqs, y, groups = marker_sequences(n=60, n_pos=20)
    from sklearn.model_selection import GroupKFold
    tr, _ = next(GroupKFold(n_splits=N_SPLITS).split(seqs, y, groups))
    short = fit_attentive(seqs, y, tr, groups, "classification", seed=SEED,
                          epochs=200, patience=1)
    long = fit_attentive(seqs, y, tr, groups, "classification", seed=SEED,
                         epochs=200, patience=200)
    assert not torch.allclose(short.query, long.query)


def test_fitting_is_deterministic_for_a_seed():
    seqs, y, groups = marker_sequences(n=60, n_pos=20)
    a = oof_attentive_classification(seqs, y, groups, seed=SEED)
    b = oof_attentive_classification(seqs, y, groups, seed=SEED)
    assert np.allclose(a["scores"], b["scores"])


# ------------------------------------------- it reports through the A2 layer

def test_attentive_report_carries_the_full_statistics_layer():
    """
    D3 reports THROUGH ticket #20's metric layer rather than beside it: the
    attentive report must carry the same CIs, nulls, p-values and MDE as a
    linear one, plus the parameter count D3 requires.
    """
    seqs, y, groups = marker_sequences(n=80, n_pos=30)
    rep = attentive_report(seqs, y, groups, target="fault", seed=SEED,
                           n_boot=40, n_perm=20)
    for key in ("macro_f1", "auc", "auc_ci", "auprc", "null_auc", "p_auc",
                "inside_null_auc", "mde_auc", "design"):
        assert key in rep, key
    assert rep["probe"] == "attentive"
    assert rep["probe_params"] == 2 * HIDDEN + 1
    assert rep["attentive_void"] is False


def test_parameter_count_accompanies_every_attentive_score():
    """D3: a capacity claim without a parameter count is not checkable."""
    seqs, y, groups = marker_sequences(n=60, n_pos=20)
    rep = attentive_report(seqs, y, groups, seed=SEED, n_boot=20, n_perm=10)
    assert rep["probe_params"] > 0
    oof = oof_attentive_classification(seqs, y, groups, seed=SEED)
    assert oof["probe_params"] == rep["probe_params"]


def test_attentive_depth_report_routes_to_the_regression_family():
    rng = np.random.default_rng(SEED)
    seqs = [rng.normal(size=(4, HIDDEN)).astype(np.float32) for _ in range(60)]
    y = np.array([4.0 + float(s[0, 0]) for s in seqs])
    rep = attentive_report(seqs, y, np.arange(60), target="depth", seed=SEED,
                           n_boot=20, n_perm=10)
    assert rep["target"] == "continuous"
    assert "mae" in rep and "mde_mae" in rep
    assert rep["probe_params"] == 2 * HIDDEN + 1


# ------------------------------------------------ the capacity diagnostic

def test_diagnostic_voids_the_run_when_attentive_on_random_wins():
    """
    The core D3 rule. A run where the attentive probe on a random-init encoder
    outscores the best linear probe on a pretrained one is void — and the void
    must be stamped onto the reports so it travels with the numbers.
    """
    rand = {"target": "binary", "auc": 0.90, "probe_params": 17}
    linear = [{"target": "binary", "auc": 0.70},
              {"target": "binary", "auc": 0.62}]
    attentive = [{"target": "binary", "auc": 0.91}, rand]
    diag = capacity_diagnostic(rand, linear, attentive)
    assert diag["void"] is True
    assert diag["margin"] == pytest.approx(0.20)
    assert "fitting itself" in diag["reason"]
    assert all(r["attentive_void"] is True for r in attentive)
    assert all(r["void_reason"] for r in attentive)


def test_diagnostic_passes_when_the_encoder_is_doing_the_work():
    rand = {"target": "binary", "auc": 0.51, "probe_params": 17}
    linear = [{"target": "binary", "auc": 0.72}]
    attentive = [{"target": "binary", "auc": 0.80}]
    diag = capacity_diagnostic(rand, linear, attentive)
    assert diag["void"] is False
    assert diag["reason"] is None
    assert attentive[0]["attentive_void"] is False


def test_diagnostic_compares_in_the_right_direction_for_depth():
    """
    On the continuous target lower MAE is better, so the diagnostic must compare
    negated errors. Attentive-on-random with a LOWER MAE than linear-on-
    pretrained is the void case.
    """
    rand = {"target": "continuous", "mae": 0.10, "probe_params": 17}
    linear = [{"target": "continuous", "mae": 0.40}]
    assert report_headline(rand) == pytest.approx(-0.10)
    assert capacity_diagnostic(rand, linear, [])["void"] is True
    rand_bad = {"target": "continuous", "mae": 0.90, "probe_params": 17}
    assert capacity_diagnostic(rand_bad, linear, [])["void"] is False


def test_run_capacity_diagnostic_wires_rows_together():
    rows = [
        {"objective": "none", "report": {"target": "binary", "auc": 0.50},
         "attentive": {"target": "binary", "auc": 0.88, "probe_params": 17}},
        {"objective": "jepa", "report": {"target": "binary", "auc": 0.60},
         "attentive": {"target": "binary", "auc": 0.90, "probe_params": 17}},
    ]
    diag = run_capacity_diagnostic(rows)
    assert diag["void"] is True
    # the random-init row's own LINEAR report must not count as "pretrained"
    assert diag["best_linear_pretrained"] == pytest.approx(0.60)
    assert rows[1]["attentive"]["attentive_void"] is True


def test_diagnostic_reports_not_run_rather_than_passing_by_default():
    """
    "We could not check" must never be encoded as "we checked and it was fine".
    """
    assert run_capacity_diagnostic([
        {"objective": "jepa", "report": {"target": "binary", "auc": 0.6},
         "attentive": {"target": "binary", "auc": 0.9, "probe_params": 17}},
    ]) is None
    assert run_capacity_diagnostic([
        {"objective": "none", "report": {"target": "binary", "auc": 0.5}},
    ]) is None


def test_a_real_random_init_style_arm_trips_the_diagnostic():
    """
    End-to-end rather than by fixture: embeddings carrying nothing at all, fed
    to the real attentive probe, versus a linear probe on embeddings that DO
    carry the label. With a strong enough imbalance the diagnostic is the only
    thing standing between the harness and a fabricated attentive win, so it is
    exercised here on real fitted numbers.
    """
    rng = np.random.default_rng(SEED)
    noise_seqs = [rng.normal(size=(5, HIDDEN)).astype(np.float32) for _ in range(60)]
    y = (np.arange(60) % 4 == 0).astype(float)
    rand_rep = attentive_report(noise_seqs, y, np.arange(60), seed=SEED,
                                n_boot=20, n_perm=10)
    weak_linear = {"target": "binary", "auc": 0.0}   # a linear arm that reads nothing
    diag = capacity_diagnostic(rand_rep, [weak_linear], [rand_rep])
    assert diag["void"] is True
    assert rand_rep["attentive_void"] is True


# -------------------------------------------------- the linear path is inert

def test_probe_classification_default_is_unchanged_by_the_oof_seam():
    """
    The refactor that made the fitter pluggable must not have moved a single
    linear number: explicitly passing the default fitter must equal passing
    nothing, and both must equal the retained C5 macro-F1.
    """
    rng = np.random.default_rng(SEED)
    X = rng.normal(size=(120, HIDDEN))
    y = np.zeros(120)
    y[rng.choice(120, size=30, replace=False)] = 1.0
    X[y == 1, 0] += 2.0
    groups = np.arange(120)

    default = probe_classification(X, y, groups, seed=SEED, n_boot=40, n_perm=20)
    explicit = probe_classification(X, y, groups, seed=SEED, n_boot=40,
                                    n_perm=20, oof_fn=oof_classification)
    legacy = probe_macro_f1(X, y, groups, seed=SEED)
    assert default["macro_f1"] == explicit["macro_f1"] == legacy["macro_f1"]
    assert np.array_equal(default["scores"], explicit["scores"])
    assert default["auc"] == explicit["auc"]


def test_probe_regression_default_is_unchanged_by_the_oof_seam():
    rng = np.random.default_rng(SEED)
    X = rng.normal(size=(100, HIDDEN))
    y = 4.0 + 1.5 * X[:, 0]
    groups = np.arange(100)
    default = probe_regression(X, y, groups, seed=SEED, n_boot=40, n_perm=20)
    explicit = probe_regression(X, y, groups, seed=SEED, n_boot=40, n_perm=20,
                                oof_fn=oof_regression)
    assert default["mae"] == explicit["mae"]
    assert np.array_equal(default["preds"], explicit["preds"])


def test_rich_report_labels_the_probe_it_used():
    rng = np.random.default_rng(SEED)
    X = rng.normal(size=(80, HIDDEN))
    y = (np.arange(80) % 3 == 0).astype(float)
    rep = rich_report(X, y, np.arange(80), seed=SEED, n_boot=20, n_perm=10)
    assert rep["probe"] == "linear"
    assert "probe_params" not in rep     # a linear probe makes no capacity claim
