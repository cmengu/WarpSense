"""
test_c8_probe_metrics.py — the C8/A2 statistics layer in eval/compare_pretrains.py.

What these tests are actually defending. C7 published nine macro-F1 numbers and a
verdict, and the numbers turned out to be noise: the untrained random-init floor
scored inside the same band as the pretrained arms, and the harness never
computed the band that would have shown it. Ticket #20 adds the machinery that
makes that class of mistake visible — CIs, permutation nulls, paired between-arm
differences, and a minimum detectable effect — so the tests below are organised
around the two properties that machinery must have:

  1. It must be CORRECT on inputs whose answer is known independently. Pure
     signal must come out significant; pure noise must come out inside the null;
     the MDE must shrink as n grows and grow as the design gets weaker.
  2. It must be INERT by default. Every C5-C7 number is a reproduction target,
     so the tests assert the retained macro-F1 path is bit-identical to what it
     was before the statistics were bolted on.

Synthetic fixtures are used deliberately: a test that needs real checkpoints
cannot say whether a wide CI came from the statistic or from the data. The
end-to-end reproduction against C7's six real checkpoints is a separate, slow
verification run, recorded in the ticket rather than asserted here.
"""

import numpy as np
import pytest
from sklearn.metrics import f1_score, roc_auc_score

from world_model.eval.compare_pretrains import (
    N_SPLITS, Z_ALPHA, Z_POWER, bootstrap_ci, evaluation_design_mde,
    hanley_mcneil_se, inside_null, mde_auc, mde_mae, null_p_value,
    oof_classification, paired_auc_diff, paired_mae_diff, permutation_null,
    permutation_null_multi, probe_classification, probe_macro_f1,
    probe_regression, symlog_depth, weld_target)

SEED = 1337


def separable_data(n=160, dim=8, n_pos=40, gap=2.5, seed=SEED):
    """Embeddings where the fault bit IS linearly readable — the signal case."""
    rng = np.random.default_rng(seed)
    X = rng.normal(size=(n, dim))
    y = np.zeros(n)
    y[rng.choice(n, size=n_pos, replace=False)] = 1.0
    X[y == 1, 0] += gap
    return X, y, np.arange(n)


def noise_data(n=160, dim=8, n_pos=40, seed=SEED):
    """Embeddings carrying nothing about the label — the C7 case."""
    X, y, g = separable_data(n=n, dim=dim, n_pos=n_pos, gap=0.0, seed=seed)
    return X, y, g


def depth_data(n=160, dim=8, noise=0.2, seed=SEED):
    """Continuous depth linearly readable from the embedding, plus noise."""
    rng = np.random.default_rng(seed)
    X = rng.normal(size=(n, dim))
    y = 4.0 + 1.5 * X[:, 0] + noise * rng.normal(size=n)
    return X, y, np.arange(n)


# --------------------------------------------------------------------------
# 1. Continuity: the retained macro-F1 must not have moved.
# --------------------------------------------------------------------------

def test_macro_f1_identical_to_legacy_computation():
    """The C5-C7 number, recomputed from the shared OOF pass, is bit-identical."""
    X, y, g = separable_data()
    legacy = probe_macro_f1(X, y, g, seed=SEED)
    oof = oof_classification(X, y, g, seed=SEED)
    assert legacy["macro_f1"] == float(
        f1_score(y, oof["preds"], average="macro", zero_division=0))


def test_rich_report_macro_f1_matches_legacy_bit_for_bit():
    """Turning the C8 statistics on cannot move the retained metric."""
    X, y, g = separable_data()
    legacy = probe_macro_f1(X, y, g, seed=SEED)
    rich = probe_classification(X, y, g, seed=SEED, n_boot=50, n_perm=20)
    assert rich["macro_f1"] == legacy["macro_f1"]
    assert rich["fold_f1_std"] == legacy["fold_f1_std"]
    assert rich["fold_f1"] == legacy["fold_f1"]


def test_adding_scores_does_not_change_fold_structure():
    X, y, g = separable_data()
    assert (probe_macro_f1(X, y, g, seed=SEED)["test_groups_per_fold"]
            == oof_classification(X, y, g, seed=SEED)["test_groups_per_fold"])


def test_probe_macro_f1_is_deterministic():
    X, y, g = separable_data()
    assert (probe_macro_f1(X, y, g, seed=SEED)["macro_f1"]
            == probe_macro_f1(X, y, g, seed=SEED)["macro_f1"])


# --------------------------------------------------------------------------
# 2. Classification path: AUC, AUPRC, CIs.
# --------------------------------------------------------------------------

def test_auc_and_auprc_high_on_separable_data():
    rep = probe_classification(*separable_data(), seed=SEED, n_boot=200, n_perm=50)
    assert rep["auc"] > 0.9
    assert rep["auprc"] > 0.8


def test_auc_near_chance_on_noise():
    rep = probe_classification(*noise_data(), seed=SEED, n_boot=200, n_perm=50)
    assert 0.3 < rep["auc"] < 0.7


def test_auc_ci_brackets_point_estimate_and_is_ordered():
    rep = probe_classification(*separable_data(), seed=SEED, n_boot=300, n_perm=20)
    lo, hi = rep["auc_ci"]
    assert lo < hi
    assert lo <= rep["auc"] <= hi


def test_ci_narrows_as_sample_grows():
    """More welds ⇒ a tighter interval. The property C7 had no way to observe.

    `gap` is kept small on purpose: with a wide gap the AUC saturates at 1.0 and
    both intervals collapse against the ceiling, which would make this test pass
    for the wrong reason (or fail for one).
    """
    small = probe_classification(*separable_data(n=80, n_pos=20, gap=0.8),
                                 seed=SEED, n_boot=300, n_perm=10)
    large = probe_classification(*separable_data(n=400, n_pos=100, gap=0.8),
                                 seed=SEED, n_boot=300, n_perm=10)
    width = lambda r: r["auc_ci"][1] - r["auc_ci"][0]   # noqa: E731
    assert width(large) < width(small)


def test_auprc_respects_prevalence_floor():
    """AUPRC of an uninformative probe sits near the positive rate, not 0.5."""
    X, y, g = noise_data(n=200, n_pos=20)
    rep = probe_classification(X, y, g, seed=SEED, n_boot=100, n_perm=20)
    assert rep["auprc"] < 0.4          # prevalence is 0.10
    assert rep["auc"] < 0.8


# --------------------------------------------------------------------------
# 3. Regression path: the continuous depth target.
# --------------------------------------------------------------------------

def test_regression_recovers_readable_depth():
    X, y, g = depth_data()
    rep = probe_regression(X, symlog_depth(y), g, seed=SEED, n_boot=100, n_perm=20)
    assert rep["r2"] > 0.8
    assert rep["mae"] < 0.2


def test_regression_r2_collapses_on_unreadable_depth():
    rng = np.random.default_rng(SEED)
    X = rng.normal(size=(160, 8))
    y = rng.normal(loc=4.0, scale=1.0, size=160)
    rep = probe_regression(X, symlog_depth(y), np.arange(160), seed=SEED,
                           n_boot=100, n_perm=20)
    assert rep["r2"] < 0.3


def test_regression_ci_ordered_and_brackets_mae():
    X, y, g = depth_data()
    rep = probe_regression(X, symlog_depth(y), g, seed=SEED, n_boot=300, n_perm=10)
    lo, hi = rep["mae_ci"]
    assert lo < hi
    assert lo <= rep["mae"] <= hi


def test_symlog_depth_is_monotone_and_compressive():
    raw = np.array([0.0, 1.0, 5.0, 50.0], dtype=float)
    out = symlog_depth(raw)
    assert np.all(np.diff(out) > 0)
    assert out[-1] < raw[-1]
    assert abs(float(out[0])) < 1e-6


def test_weld_target_scalar_unchanged_and_array_mean_reduced():
    assert weld_target({"fault": 1}, "fault") == 1.0
    assert weld_target({"fusion_depth_mm": [1.0, 3.0]}, "fusion_depth_mm") == 2.0
    with_nan = {"fusion_depth_mm": np.array([2.0, np.nan, 4.0])}
    assert weld_target(with_nan, "fusion_depth_mm") == 3.0


# --------------------------------------------------------------------------
# 4. Permutation null — the piece C7 was missing.
# --------------------------------------------------------------------------

def test_noise_arm_lands_inside_its_own_null():
    """The C7 diagnosis, reproduced on synthetic data."""
    rep = probe_classification(*noise_data(), seed=SEED, n_boot=50, n_perm=100)
    assert rep["inside_null_auc"]
    assert rep["p_auc"] > 0.05


def test_signal_arm_escapes_the_null():
    rep = probe_classification(*separable_data(), seed=SEED, n_boot=50, n_perm=100)
    assert not rep["inside_null_auc"]
    assert rep["p_auc"] < 0.05


def test_null_auc_centres_on_chance():
    rep = probe_classification(*noise_data(), seed=SEED, n_boot=20, n_perm=150)
    assert abs(rep["null_auc"]["mean"] - 0.5) < 0.08


def test_regression_null_detects_unreadable_depth():
    rng = np.random.default_rng(SEED)
    X = rng.normal(size=(140, 8))
    y = symlog_depth(rng.normal(loc=4.0, scale=1.0, size=140))
    rep = probe_regression(X, y, np.arange(140), seed=SEED, n_boot=20, n_perm=100)
    assert rep["inside_null_mae"]
    assert rep["p_mae"] > 0.05


def test_regression_null_cleared_by_readable_depth():
    X, y, g = depth_data()
    rep = probe_regression(X, symlog_depth(y), g, seed=SEED, n_boot=20, n_perm=100)
    assert not rep["inside_null_mae"]
    assert rep["p_mae"] < 0.05


def test_p_value_never_zero_phipson_smyth():
    """The +1 correction: p is bounded below by 1/(1+n_perm), never 0."""
    nulls = np.zeros(99)
    assert null_p_value(1.0, nulls) == pytest.approx(1 / 100)


def test_permutation_null_band_is_ordered_and_reproducible():
    y = np.array([0.0] * 100 + [1.0] * 20)
    refit = lambda yp: float(yp[:20].mean())    # noqa: E731
    a = permutation_null(refit, y, n_perm=60, seed=SEED)
    b = permutation_null(refit, y, n_perm=60, seed=SEED)
    assert a["lo"] <= a["mean"] <= a["hi"]
    assert a["mean"] == b["mean"] and a["lo"] == b["lo"]


def test_permutation_null_multi_scores_the_same_permuted_worlds():
    """One permutation loop, several metrics — and they must agree pairwise."""
    y = np.arange(60, dtype=float)
    got = permutation_null_multi(lambda yp: {"a": yp[:10].mean(),
                                             "b": 2 * yp[:10].mean()},
                                 y, ["a", "b"], n_perm=40, seed=SEED)
    assert got["b"]["mean"] == pytest.approx(2 * got["a"]["mean"])
    assert np.allclose(got["b"]["values"], 2 * got["a"]["values"])


def test_permutation_null_multi_matches_single_metric_helper():
    y = np.arange(60, dtype=float)
    single = permutation_null(lambda yp: yp[:10].mean(), y, n_perm=40, seed=SEED)
    multi = permutation_null_multi(lambda yp: {"a": yp[:10].mean()}, y, ["a"],
                                   n_perm=40, seed=SEED)["a"]
    assert multi["mean"] == pytest.approx(single["mean"])
    assert np.allclose(multi["values"], single["values"])


def test_inside_null_boundary_inclusive():
    null = {"lo": 0.4, "hi": 0.6, "mean": 0.5}
    assert inside_null(0.4, null) and inside_null(0.6, null)
    assert not inside_null(0.61, null)


# --------------------------------------------------------------------------
# 5. Paired between-arm difference (Hanley & McNeil 1983).
# --------------------------------------------------------------------------

def test_identical_arms_have_zero_paired_difference():
    X, y, g = separable_data()
    s = oof_classification(X, y, g, seed=SEED)["scores"]
    d = paired_auc_diff(s, s, y, n_boot=100, seed=SEED)
    assert d["delta_auc"] == 0.0
    assert not d["excludes_zero"]
    assert d["r"] == pytest.approx(1.0, abs=1e-6)
    assert d["hm_se"] == pytest.approx(0.0, abs=1e-9)


def test_clearly_better_arm_has_ci_excluding_zero():
    X, y, g = separable_data(n=300, n_pos=90)
    good = oof_classification(X, y, g, seed=SEED)["scores"]
    rng = np.random.default_rng(SEED)
    bad = rng.normal(size=len(y))
    d = paired_auc_diff(good, bad, y, n_boot=400, seed=SEED)
    assert d["delta_auc"] > 0
    assert d["excludes_zero"]
    assert d["boot_lo"] > 0


def test_two_noise_arms_ci_includes_zero():
    rng = np.random.default_rng(SEED)
    y = np.array([0.0] * 120 + [1.0] * 40)
    d = paired_auc_diff(rng.normal(size=160), rng.normal(size=160), y,
                        n_boot=400, seed=SEED)
    assert not d["excludes_zero"]
    assert d["boot_lo"] < 0 < d["boot_hi"]


def test_paired_difference_is_antisymmetric():
    X, y, g = separable_data()
    good = oof_classification(X, y, g, seed=SEED)["scores"]
    rng = np.random.default_rng(SEED)
    bad = rng.normal(size=len(y))
    ab = paired_auc_diff(good, bad, y, n_boot=50, seed=SEED)
    ba = paired_auc_diff(bad, good, y, n_boot=50, seed=SEED)
    assert ab["delta_auc"] == pytest.approx(-ba["delta_auc"])


def test_correlated_arms_get_tighter_hm_interval_than_independent_ones():
    """The whole point of the PAIRED formula: shared cases buy precision."""
    rng = np.random.default_rng(SEED)
    y = np.array([0.0] * 120 + [1.0] * 40)
    base = rng.normal(size=160) + y
    corr = base + 0.05 * rng.normal(size=160)      # nearly the same ranking
    indep = rng.normal(size=160) + y               # same AUC, unrelated ranking
    d_corr = paired_auc_diff(base, corr, y, n_boot=50, seed=SEED)
    d_indep = paired_auc_diff(base, indep, y, n_boot=50, seed=SEED)
    assert d_corr["r"] > d_indep["r"]
    assert d_corr["hm_se"] < d_indep["hm_se"]


def test_hanley_mcneil_se_shrinks_with_more_cases():
    assert hanley_mcneil_se(0.75, 10, 100) > hanley_mcneil_se(0.75, 100, 1000)


def test_hanley_mcneil_se_maximal_near_chance():
    assert hanley_mcneil_se(0.5, 40, 200) > hanley_mcneil_se(0.95, 40, 200)


def test_paired_mae_difference_sign_favours_lower_error():
    y = np.linspace(0.0, 1.0, 100)
    accurate, sloppy = y + 0.01, y + 0.30
    d = paired_mae_diff(y, accurate, sloppy, n_boot=200, seed=SEED)
    assert d["delta_mae"] > 0            # positive ⇒ arm A better
    assert d["excludes_zero"]
    assert d["mae_a"] < d["mae_b"]


def test_paired_mae_difference_of_identical_arms_is_zero():
    y = np.linspace(0.0, 1.0, 100)
    d = paired_mae_diff(y, y + 0.1, y + 0.1, n_boot=100, seed=SEED)
    assert d["delta_mae"] == 0.0
    assert not d["excludes_zero"]


# --------------------------------------------------------------------------
# 6. Minimum detectable effect — what Gate C8-0 consumes.
# --------------------------------------------------------------------------

def test_mde_auc_shrinks_with_more_positives():
    assert mde_auc(11, 297) > mde_auc(79, 1897)


def test_mde_auc_shrinks_as_arms_become_more_correlated():
    """Paired designs on correlated arms detect smaller gaps."""
    assert mde_auc(79, 1897, r=0.9) < mde_auc(79, 1897, r=0.1)


def test_c7_design_is_underpowered_for_th1():
    """C7's actual design — 11 positives, 297 negatives — cannot see +0.05 AUC."""
    assert mde_auc(11, 297) > 0.05


def test_mde_mae_shrinks_with_more_welds():
    rng = np.random.default_rng(SEED)
    small = np.abs(rng.normal(scale=0.5, size=50))
    large = np.abs(rng.normal(scale=0.5, size=5000))
    assert mde_mae(large) < mde_mae(small)


def test_mde_mae_grows_with_error_spread():
    rng = np.random.default_rng(SEED)
    tight = np.abs(rng.normal(scale=0.1, size=500))
    wide = np.abs(rng.normal(scale=1.0, size=500))
    assert mde_mae(wide) > mde_mae(tight)


def test_mde_mae_matches_closed_form():
    rng = np.random.default_rng(SEED)
    e = np.abs(rng.normal(scale=0.4, size=400))
    expected = ((Z_ALPHA + Z_POWER) * e.std(ddof=1) * np.sqrt(2 * (1 - 0.5))
                / np.sqrt(len(e)))
    assert mde_mae(e, r=0.5) == pytest.approx(expected)


def test_design_flags_thresholds_below_the_mde_as_underpowered():
    rep = probe_classification(*noise_data(n=120, n_pos=8), seed=SEED,
                               n_boot=20, n_perm=10)
    design = evaluation_design_mde(rep)
    assert design["metric"] == "delta_auc"
    assert design["underpowered"]          # a 8-positive design sees nothing
    assert set(design["underpowered"]) <= set(design["thresholds"])


def test_design_powered_and_underpowered_partition_the_thresholds():
    rep = probe_classification(*separable_data(n=400, n_pos=200), seed=SEED,
                               n_boot=20, n_perm=10)
    d = evaluation_design_mde(rep)
    assert set(d["powered"]) | set(d["underpowered"]) == set(d["thresholds"])
    assert not set(d["powered"]) & set(d["underpowered"])


def test_regression_design_uses_delta_mae_thresholds():
    X, y, g = depth_data()
    rep = probe_regression(X, symlog_depth(y), g, seed=SEED, n_boot=20, n_perm=10)
    d = evaluation_design_mde(rep)
    assert d["metric"] == "delta_mae"
    assert set(d["thresholds"]) == {"TH1", "TH2", "TH3"}


# --------------------------------------------------------------------------
# 6b. End-to-end on real simulated welds — the depth target actually exists.
# --------------------------------------------------------------------------

def test_depth_target_reads_off_real_simulated_sessions():
    """
    `weld_target` must pull a usable scalar out of the simulator's PER-FRAME
    `fusion_depth_mm`, and the resulting targets must actually vary between
    welds — a constant target would make every regression number meaningless
    while still "passing" a shape check.
    """
    from world_model.eval.compare_pretrains import DEPTH_KEY
    from world_model.simulator.weld_sim import sample_params, simulate_session

    sessions = [simulate_session(sample_params(seed=s)) for s in range(12)]
    assert all(DEPTH_KEY in s.meta for s in sessions)
    y = np.array([weld_target(s.meta, DEPTH_KEY) for s in sessions])
    assert np.isfinite(y).all()
    assert y.std() > 0
    assert (y > 0).all()


def test_rich_report_routes_depth_to_the_regression_family():
    """The router picks the metric family from the target, not from a flag."""
    from world_model.eval.compare_pretrains import rich_report

    X, y, g = depth_data(n=100)
    rep = rich_report(X, y, g, target="depth", seed=SEED, n_boot=20, n_perm=10)
    assert rep["target"] == "continuous"
    assert "mae" in rep and "auc" not in rep
    assert rep["design"]["metric"] == "delta_mae"

    Xc, yc, gc = separable_data(n=100, n_pos=30)
    repc = rich_report(Xc, yc, gc, target="fault", seed=SEED, n_boot=20, n_perm=10)
    assert repc["target"] == "binary"
    assert "auc" in repc and "mae" not in repc
    assert repc["design"]["metric"] == "delta_auc"


# --------------------------------------------------------------------------
# 7. Bootstrap helper.
# --------------------------------------------------------------------------

def test_bootstrap_ci_recovers_a_known_mean():
    rng = np.random.default_rng(SEED)
    x = rng.normal(loc=3.0, scale=1.0, size=500)
    lo, hi, se = bootstrap_ci(lambda idx: x[idx].mean(), len(x), n_boot=500,
                              seed=SEED)
    assert lo < 3.0 < hi
    assert se == pytest.approx(1.0 / np.sqrt(500), rel=0.3)


def test_bootstrap_ci_is_reproducible_under_seed():
    x = np.arange(100, dtype=float)
    a = bootstrap_ci(lambda i: x[i].mean(), 100, n_boot=100, seed=SEED)
    b = bootstrap_ci(lambda i: x[i].mean(), 100, n_boot=100, seed=SEED)
    assert a == b


def test_bootstrap_ci_skips_unusable_resamples():
    """Resamples the statistic rejects (None) are dropped, not counted as zero."""
    x = np.ones(50)
    calls = {"n": 0}

    def stat(idx):
        calls["n"] += 1
        return None if calls["n"] % 2 else x[idx].mean()

    lo, hi, _ = bootstrap_ci(stat, 50, n_boot=40, seed=SEED)
    assert lo == hi == 1.0


def test_bootstrap_ci_all_rejected_returns_nan():
    lo, hi, se = bootstrap_ci(lambda idx: None, 10, n_boot=5, seed=SEED)
    assert np.isnan(lo) and np.isnan(hi) and np.isnan(se)


# --------------------------------------------------------------------------
# 8. Degenerate and edge designs must not crash the harness.
# --------------------------------------------------------------------------

def test_single_class_target_reports_nan_auc_not_a_crash():
    rng = np.random.default_rng(SEED)
    X = rng.normal(size=(40, 6))
    y = np.zeros(40)
    rep = probe_classification(X, y, np.arange(40), seed=SEED, n_boot=10, n_perm=5)
    assert np.isnan(rep["auc"]) and np.isnan(rep["auprc"])
    assert np.isfinite(rep["macro_f1"])


def test_degenerate_fold_scores_are_constant_not_missing():
    """One positive across five folds: every fold still yields a score vector."""
    rng = np.random.default_rng(SEED)
    X = rng.normal(size=(40, 6))
    y = np.zeros(40)
    y[0] = 1.0
    oof = oof_classification(X, y, np.arange(40), seed=SEED)
    assert oof["scores"].shape == y.shape
    assert np.isfinite(oof["scores"]).all()


def test_n_splits_clamped_to_available_groups():
    X, y, _ = separable_data(n=12, n_pos=4)
    groups = np.repeat(np.arange(3), 4)
    rep = probe_classification(X, y, groups, seed=SEED, n_boot=10, n_perm=5)
    assert rep["n_splits"] == 3 <= N_SPLITS


def test_auc_matches_sklearn_on_the_reported_scores():
    """No hidden re-ranking between the reported AUC and the reported scores."""
    X, y, g = separable_data()
    rep = probe_classification(X, y, g, seed=SEED, n_boot=10, n_perm=5)
    assert rep["auc"] == roc_auc_score(rep["labels"], rep["scores"])
