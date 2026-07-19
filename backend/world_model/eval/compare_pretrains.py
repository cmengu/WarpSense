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

C8 update (A2) — the ruler grew error bars. C7 reported nine macro-F1 numbers
with no interval around any of them, and every one — including the untrained
random-init floor — later turned out to sit inside the permutation null. So
`--rich-metrics` now reports, beside every number: AUC and AUPRC with bootstrap
CIs (or MAE and R2 for the continuous depth target), the permutation null and
its p-value, the paired between-arm difference with a CI, and the MINIMUM
DETECTABLE EFFECT that Gate C8-0 consumes. macro-F1 is retained untouched, so
C5-C7 reproductions still print the same number they always did; every new
statistic is behind the new flag and nothing changes without it.

C8 update (D3) — the ruler grew a second, stronger probe, and a way to tell
whether to believe it. The paragraph above says a stronger probe would blur the
question; V-JEPA's authors, who wrote the linear-probe protocol in the first
place, later measured +16-17 points from attentive probing, so the linear number
may be understating a good encoder by more than C7's entire margin.
`--attentive-probe` therefore adds an arm with a single learnable query
cross-attending over the encoder's per-window hidden states — and, because that
query has parameters and 79 positives is not many, ALWAYS runs the same probe
against the random-init encoder as a capacity check. If the attentive probe beats
a linear probe without any encoder to read, it is scoring on its own parameters
and every attentive number in the run is marked void. Linear numbers are produced
by untouched code paths either way.

CLI (from backend/):
  python -m world_model.eval.compare_pretrains CKPT [CKPT ...] --tiny
  python -m world_model.eval.compare_pretrains \
      experiments/checkpoints/jepa_pretrain_*.pt \
      experiments/checkpoints/masked_recon_windows_*.pt --split val
  # C8: the same comparison, with the statistics that make it decidable
  python -m world_model.eval.compare_pretrains CKPT [CKPT ...] \
      --split test --rich-metrics
  # C8/D3: add the attentive arm and its mandatory capacity diagnostic
  python -m world_model.eval.compare_pretrains CKPT [CKPT ...] \
      --split val --rich-metrics --attentive-probe
"""

import argparse
from pathlib import Path

import numpy as np
import torch
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import (average_precision_score, f1_score,
                             mean_absolute_error, r2_score, roc_auc_score)
from sklearn.model_selection import GroupKFold

from world_model.architecture.trunk import StemTrunkEncoder
from world_model.config import SEED, TINY
from world_model.data.schema import SessionTensor
from world_model.data.windows import ProbeWindows
from world_model.pretraining.masked_recon import PRETRAIN_CHANNELS
from world_model.training.symlog import symlog

WINDOW = 300   # the C4-C7 diet; C6 sweeps this
STRIDE = 50
LABEL_KEY = "fault"
DEPTH_KEY = "fusion_depth_mm"   # C8 primary target: continuous, per-frame
N_SPLITS = 5

# C8/A2 statistics defaults. z for a two-sided 95% interval and for 80% power —
# the two constants every MDE in §7 is built from.
Z_ALPHA = 1.959963984540054
Z_POWER = 0.8416212335729143
N_BOOT = 1000    # bootstrap resamples for every CI
N_PERM = 200     # label permutations for every null


def weld_target(meta: dict, key: str) -> float:
    """
    One scalar target per weld from session meta.

    The C4-C7 label ("fault") is already a scalar per weld, and this returns it
    unchanged — the classification path is byte-identical to before. The C8
    primary target ("fusion_depth_mm") is a PER-FRAME array, and the probe's
    unit of analysis is the weld (embeddings are mean-pooled per weld), so the
    per-frame series is reduced the same way the embedding is: by its mean over
    the frames the sensors actually reported. Reducing the target with the same
    operator that reduced the input is the only choice that keeps the probe a
    fair reading of the embedding rather than a test of pooling.
    """
    v = meta[key]
    if np.ndim(v) == 0:
        return float(v)
    arr = np.asarray(v, dtype=float)
    finite = arr[np.isfinite(arr)]
    if finite.size == 0:
        raise ValueError(f"meta[{key!r}] has no finite entries")
    return float(finite.mean())


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
    y = np.array([weld_target(s.meta, label_key) for s in sessions])[keep]
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
    oof = oof_classification(X, y, groups, n_splits=n_splits, seed=seed,
                             warn=True)
    return {
        "macro_f1": float(f1_score(y, oof["preds"], average="macro",
                                   zero_division=0)),
        "fold_f1": [float(f) for f in oof["fold_f1"]],
        "fold_f1_std": float(np.std(oof["fold_f1"])),
        "n_splits": oof["n_splits"],
        "test_groups_per_fold": oof["test_groups_per_fold"],
    }


def oof_classification(X: np.ndarray, y: np.ndarray, groups: np.ndarray,
                       n_splits: int = N_SPLITS, seed: int = SEED,
                       warn: bool = False) -> dict:
    """
    The one GroupKFold pass every classification number is derived from:
    out-of-fold hard predictions AND out-of-fold continuous scores.

    Hard predictions are what macro-F1 has always consumed (C5-C7); the
    continuous scores are what C8 adds, and they are what AUC, AUPRC, the
    permutation null and the paired between-arm difference all need. Both come
    from the SAME fitted models in the SAME fold order, so adding the scores
    cannot move the retained macro-F1 by even a float ulp — the fitting code
    below is the C5 code, unedited, with one extra line reading
    `decision_function` off a classifier that was going to be fitted anyway.

    A degenerate fold (training side holds one class only) predicts that class
    as a constant, exactly as before; its "score" is that same constant, which
    is the honest encoding of "this fold ranked nothing".
    """
    n_splits = min(n_splits, len(np.unique(groups)))
    if warn and y.sum() < n_splits:
        print(f"WARNING: only {int(y.sum())} positive welds across {n_splits} "
              f"folds — the probe is under-powered at this data size")
    preds = np.zeros_like(y)
    scores = np.zeros_like(y, dtype=float)
    fold_f1, test_groups_per_fold = [], []
    for tr, te in GroupKFold(n_splits=n_splits).split(X, y, groups):
        if len(np.unique(y[tr])) < 2:
            preds[te] = y[tr][0]   # degenerate fold: constant prediction
            scores[te] = float(y[tr][0])
            fold_f1.append(f1_score(y[te], preds[te], average="macro",
                                    zero_division=0))
            test_groups_per_fold.append(set(groups[te].tolist()))
            continue
        clf = LogisticRegression(max_iter=2000, class_weight="balanced",
                                 random_state=seed)
        clf.fit(X[tr], y[tr])
        preds[te] = clf.predict(X[te])
        scores[te] = clf.decision_function(X[te])
        fold_f1.append(f1_score(y[te], preds[te], average="macro", zero_division=0))
        test_groups_per_fold.append(set(groups[te].tolist()))
    return {"preds": preds, "scores": scores, "fold_f1": fold_f1,
            "n_splits": n_splits, "test_groups_per_fold": test_groups_per_fold}


def oof_regression(X: np.ndarray, y: np.ndarray, groups: np.ndarray,
                   n_splits: int = N_SPLITS, seed: int = SEED,
                   alpha: float = 1.0) -> dict:
    """
    The regression twin of `oof_classification`, for the C8 PRIMARY target.

    Fusion depth is continuous, so the probe cannot be a logistic regression and
    the metric cannot be macro-F1 (§7: depth is scored by ΔMAE, the fault bit by
    ΔAUC). The probe stays as weak as its classification sibling — a linear
    model, `Ridge`, whose only addition is an L2 term that keeps a 64-dimensional
    fit from exploding on a few hundred welds. Ridge with the default solver is
    a closed-form fit: no randomness, no seed sensitivity.

    Targets are symlog-compressed (`training/symlog.py`), matching every other
    depth target in the repo, so an MAE here is an MAE in symlog-mm and the §7
    ΔMAE threshold is read in the same space the models were trained in.
    """
    n_splits = min(n_splits, len(np.unique(groups)))
    preds = np.zeros(len(y), dtype=float)
    fold_mae, test_groups_per_fold = [], []
    for tr, te in GroupKFold(n_splits=n_splits).split(X, y, groups):
        model = Ridge(alpha=alpha, random_state=seed)
        model.fit(X[tr], y[tr])
        preds[te] = model.predict(X[te])
        fold_mae.append(float(mean_absolute_error(y[te], preds[te])))
        test_groups_per_fold.append(set(groups[te].tolist()))
    return {"preds": preds, "fold_mae": fold_mae, "n_splits": n_splits,
            "test_groups_per_fold": test_groups_per_fold}


def symlog_depth(y_mm: np.ndarray) -> np.ndarray:
    """Depth targets in mm → symlog space, via the repo's canonical transform."""
    return symlog(torch.as_tensor(np.asarray(y_mm, dtype=np.float32))).numpy()


# --------------------------------------------------------------------------
# C8/A2 — the statistics layer: CIs, nulls, paired differences, MDE.
#
# Why this exists at all: C7 reported nine macro-F1 numbers with no interval
# around any of them, and every one of those numbers — including the untrained
# random-init floor — turned out to sit inside the permutation null. The verdict
# C7 issued was therefore a reading of noise. Everything below is the machinery
# that makes that failure impossible to repeat: no number is reported without
# (a) an interval saying how precisely it is known, (b) the null saying what
# score pure chance produces on this design, and (c) an MDE saying the smallest
# true effect this design could have detected in the first place.
# --------------------------------------------------------------------------

def bootstrap_ci(statistic, n: int, n_boot: int = N_BOOT, seed: int = SEED,
                 alpha: float = 0.05) -> tuple[float, float, float]:
    """
    Percentile bootstrap over the n rows of an evaluation, one row per weld.

    `statistic(idx)` receives an array of resampled row indices and returns the
    metric on that resample, or None if the resample is unusable (e.g. an AUC
    resample that happened to draw no positives). Returns (lo, hi, se).

    Resampling ROWS is the right unit here precisely because the probe already
    pooled each weld into one row: welds are the independent observations, and
    the within-weld correlation that would break a naive bootstrap was collapsed
    upstream by mean-pooling. This is the same reasoning that makes GroupKFold
    the right split.
    """
    rng = np.random.default_rng(seed)
    vals = []
    for _ in range(n_boot):
        v = statistic(rng.integers(0, n, size=n))
        if v is not None and np.isfinite(v):
            vals.append(float(v))
    if not vals:
        return (float("nan"), float("nan"), float("nan"))
    return (float(np.percentile(vals, 100 * alpha / 2)),
            float(np.percentile(vals, 100 * (1 - alpha / 2))),
            float(np.std(vals)))


def permutation_null(refit, y: np.ndarray, n_perm: int = N_PERM,
                     seed: int = SEED, alpha: float = 0.05) -> dict:
    """
    What score does this design produce when the labels mean nothing?

    Shuffles the target across welds and re-runs the ENTIRE cross-validated
    probe each time — not a reshuffle of stored predictions. Re-fitting is the
    only version that also absorbs the probe's own optimism, which is the term
    that bit C7: a 4%-positive target with 11 positives lets a linear model on
    64 dimensions post a respectable-looking macro-F1 on noise alone.

    `refit(y_permuted)` returns the metric under permuted labels. Returns the
    null mean, its central (1-alpha) band, and the one-sided p-value
    (1 + #{null >= observed}) / (1 + n_perm) — the +1 is Phipson & Smyth's
    correction, which keeps p from ever being reported as exactly zero.

    Direction is the caller's job: `refit` must return a metric where LARGER is
    better, so error metrics (MAE) are passed negated and the same upper tail
    applies to every family without a direction flag to get wrong.
    """
    rng = np.random.default_rng(seed + 1)
    vals = []
    for _ in range(n_perm):
        vals.append(float(refit(rng.permutation(y))))
    vals = np.asarray(vals)
    return {
        "mean": float(vals.mean()),
        "lo": float(np.percentile(vals, 100 * alpha / 2)),
        "hi": float(np.percentile(vals, 100 * (1 - alpha / 2))),
        "values": vals,
    }


def permutation_null_multi(refit_all, y: np.ndarray, names: list[str],
                           n_perm: int = N_PERM, seed: int = SEED,
                           alpha: float = 0.05) -> dict:
    """
    `permutation_null` for several metrics at once, off ONE set of permutations.

    Every metric in a report is read from the same cross-validated fit, so
    permuting once and scoring all of them is both 3x cheaper than looping per
    metric and more coherent: the AUC null and the AUPRC null then describe the
    same permuted worlds rather than two unrelated draws. `refit_all(y_perm)`
    returns a dict keyed by `names`.
    """
    rng = np.random.default_rng(seed + 1)
    cols = {k: [] for k in names}
    for _ in range(n_perm):
        got = refit_all(rng.permutation(y))
        for k in names:
            cols[k].append(float(got[k]))
    out = {}
    for k in names:
        vals = np.asarray(cols[k])
        out[k] = {"mean": float(np.nanmean(vals)),
                  "lo": float(np.nanpercentile(vals, 100 * alpha / 2)),
                  "hi": float(np.nanpercentile(vals, 100 * (1 - alpha / 2))),
                  "values": vals}
    return out


def null_p_value(observed: float, null_values: np.ndarray) -> float:
    """One-sided permutation p-value with the Phipson & Smyth +1 correction."""
    null_values = np.asarray(null_values)
    return float((1 + int((null_values >= observed).sum())) / (1 + len(null_values)))


def inside_null(observed: float, null: dict) -> bool:
    """True when a reported number is indistinguishable from chance — the C7 test."""
    return bool(null["lo"] <= observed <= null["hi"])


def hanley_mcneil_se(auc: float, n_pos: int, n_neg: int) -> float:
    """
    Standard error of a single ROC area (Hanley & McNeil 1982, eq. 1).

    Q1 = A/(2-A) and Q2 = 2A^2/(1+A) are the distribution-free estimates of the
    probabilities that two randomly drawn positives (resp. negatives) are both
    ranked above a randomly drawn case of the other class. The formula needs
    only the area and the two class counts, which is exactly what makes it
    usable BEFORE a run — Gate C8-0 needs an SE for a design that has not been
    executed yet, and no bootstrap can supply that.
    """
    if n_pos < 1 or n_neg < 1:
        return float("nan")
    a = float(np.clip(auc, 1e-6, 1 - 1e-6))
    q1 = a / (2 - a)
    q2 = 2 * a * a / (1 + a)
    var = (a * (1 - a) + (n_pos - 1) * (q1 - a * a)
           + (n_neg - 1) * (q2 - a * a)) / (n_pos * n_neg)
    return float(np.sqrt(max(var, 0.0)))


def paired_auc_correlation(scores_a: np.ndarray, scores_b: np.ndarray,
                           y: np.ndarray) -> float:
    """
    The r that Hanley & McNeil 1983 feeds into the paired variance: the average
    of the between-arm score correlations computed separately within positives
    and within negatives.

    H&M's paper reaches r through a published lookup table indexed by the
    average Kendall correlation and the average area. This repo does not ship
    that table, so the correlation is used directly in the variance formula
    below — the standard practical simplification. It is conservative in the
    direction that matters: two arms built from the same frozen-embedding
    pipeline are strongly correlated, so ignoring the table's mild shrinkage
    yields a slightly LARGER r, a smaller paired SE, and therefore an MDE that
    is optimistic rather than pessimistic. The bootstrap paired CI is reported
    alongside for exactly this reason and should be treated as primary.
    """
    def _corr(mask):
        a, b = scores_a[mask], scores_b[mask]
        if len(a) < 2 or np.std(a) == 0 or np.std(b) == 0:
            return 0.0
        return float(np.corrcoef(a, b)[0, 1])
    r_pos, r_neg = _corr(y == 1), _corr(y == 0)
    return float(np.clip((r_pos + r_neg) / 2, -1.0, 1.0))


def paired_auc_diff(scores_a: np.ndarray, scores_b: np.ndarray, y: np.ndarray,
                    n_boot: int = N_BOOT, seed: int = SEED) -> dict:
    """
    Between-arm ΔAUC on the SAME welds, with a CI — the §7 TH1/TH5 quantity.

    Two CIs are returned deliberately:
      hm_*        Hanley & McNeil 1983: SE(A1-A2) = sqrt(SE1^2 + SE2^2 - 2 r SE1 SE2).
                  Parametric, closed-form, and — crucially — projectable to a
                  design that has not been run, which is what Gate C8-0 needs.
      boot_*      Percentile bootstrap over welds. Nonparametric, makes no
                  binormal assumption, and is the one to quote in a verdict.
    They should agree; a large disagreement is itself a finding, and both are
    printed rather than one being silently chosen.
    """
    y = np.asarray(y)
    n_pos, n_neg = int((y == 1).sum()), int((y == 0).sum())
    auc_a = float(roc_auc_score(y, scores_a))
    auc_b = float(roc_auc_score(y, scores_b))
    delta = auc_a - auc_b
    se_a = hanley_mcneil_se(auc_a, n_pos, n_neg)
    se_b = hanley_mcneil_se(auc_b, n_pos, n_neg)
    r = paired_auc_correlation(scores_a, scores_b, y)
    se_d = float(np.sqrt(max(se_a ** 2 + se_b ** 2 - 2 * r * se_a * se_b, 0.0)))

    def _stat(idx):
        yy = y[idx]
        if len(np.unique(yy)) < 2:
            return None
        return roc_auc_score(yy, scores_a[idx]) - roc_auc_score(yy, scores_b[idx])

    boot_lo, boot_hi, boot_se = bootstrap_ci(_stat, len(y), n_boot=n_boot, seed=seed)
    return {
        "auc_a": auc_a, "auc_b": auc_b, "delta_auc": delta,
        "r": r, "hm_se": se_d,
        "hm_lo": delta - Z_ALPHA * se_d, "hm_hi": delta + Z_ALPHA * se_d,
        "boot_lo": boot_lo, "boot_hi": boot_hi, "boot_se": boot_se,
        "excludes_zero": bool(boot_lo > 0 or boot_hi < 0),
        "n_pos": n_pos, "n_neg": n_neg,
    }


def paired_mae_diff(y_true: np.ndarray, pred_a: np.ndarray, pred_b: np.ndarray,
                    n_boot: int = N_BOOT, seed: int = SEED) -> dict:
    """
    Between-arm ΔMAE on the same welds, with a CI — the §7 primary-target twin
    of `paired_auc_diff`. Sign convention: positive delta means arm A has the
    LOWER error, i.e. arm A is better, so that "delta >= threshold with a CI
    excluding zero" reads identically for both metric families.
    """
    err_a = np.abs(np.asarray(y_true) - np.asarray(pred_a))
    err_b = np.abs(np.asarray(y_true) - np.asarray(pred_b))
    d = err_b - err_a                      # >0 ⇒ A better
    delta = float(d.mean())
    se = float(d.std(ddof=1) / np.sqrt(len(d))) if len(d) > 1 else float("nan")
    boot_lo, boot_hi, boot_se = bootstrap_ci(
        lambda idx: d[idx].mean(), len(d), n_boot=n_boot, seed=seed)
    return {
        "mae_a": float(err_a.mean()), "mae_b": float(err_b.mean()),
        "delta_mae": delta, "se": se,
        "hm_lo": delta - Z_ALPHA * se, "hm_hi": delta + Z_ALPHA * se,
        "boot_lo": boot_lo, "boot_hi": boot_hi, "boot_se": boot_se,
        "excludes_zero": bool(boot_lo > 0 or boot_hi < 0),
        "n": int(len(d)),
    }


def mde_auc(n_pos: int, n_neg: int, auc_ref: float = 0.5, r: float = 0.5,
            alpha: float = 0.05, power: float = 0.8) -> float:
    """
    Minimum detectable ΔAUC for this evaluation design — the number Gate C8-0
    consumes.

    Read it as: "with n_pos positives, n_neg negatives, and two arms whose
    scores correlate r, the smallest true AUC gap this comparison has an
    `power` chance of calling significant at level `alpha`." Any §7 threshold
    that sits BELOW this value is underpowered in advance and must not be run
    as a decisive test.

    Solved by scanning delta upward until delta / SE_paired(delta) clears
    z_alpha + z_power. The scan (rather than an algebraic inversion) is used
    because SE itself depends on delta through the H&M variance — the equation
    is implicit, and 2000 grid points over [0, 0.5] resolve it to 0.00025,
    far finer than any threshold in §7.
    """
    z_sum = _z(alpha, power)
    for delta in np.linspace(0.0, 0.5, 2001)[1:]:
        a1 = min(auc_ref + delta, 0.999999)
        se1 = hanley_mcneil_se(a1, n_pos, n_neg)
        se0 = hanley_mcneil_se(auc_ref, n_pos, n_neg)
        se_d = np.sqrt(max(se1 ** 2 + se0 ** 2 - 2 * r * se1 * se0, 1e-12))
        if delta / se_d >= z_sum:
            return float(delta)
    return float("nan")


def mde_mae(abs_errors: np.ndarray, r: float = 0.5, alpha: float = 0.05,
            power: float = 0.8) -> float:
    """
    Minimum detectable ΔMAE (symlog-mm) for a paired depth comparison.

    Needs a scale for the per-weld errors, which is why it takes one arm's
    observed absolute errors: the paired difference of two arms with per-weld
    error SD s and correlation r has SD s*sqrt(2(1-r)), so the MDE is
    (z_alpha + z_power) * s * sqrt(2(1-r)) / sqrt(n). With r unknown before the
    run, 0.5 is the deliberately conservative placeholder — two arms sharing an
    encoder family usually correlate higher, which would only shrink this.
    """
    e = np.asarray(abs_errors, dtype=float)
    n = len(e)
    if n < 2:
        return float("nan")
    sd = float(e.std(ddof=1)) * np.sqrt(max(2 * (1 - r), 0.0))
    return float(_z(alpha, power) * sd / np.sqrt(n))


def _z(alpha: float, power: float) -> float:
    """z_{1-alpha/2} + z_{power}, the two-sided sample-size constant."""
    if (alpha, power) == (0.05, 0.8):
        return Z_ALPHA + Z_POWER      # the pre-registered §7 design
    from scipy.stats import norm
    return float(norm.ppf(1 - alpha / 2) + norm.ppf(power))


def probe_classification(X, y: np.ndarray, groups: np.ndarray,
                         n_splits: int = N_SPLITS, seed: int = SEED,
                         n_boot: int = N_BOOT, n_perm: int = N_PERM,
                         oof_fn=None) -> dict:
    """
    The full C8 classification report for one arm on the binary fault bit:
    retained macro-F1, plus AUC and AUPRC with bootstrap CIs, plus a permutation
    null and p-value for each of the three, plus the design's MDE.

    macro_f1 here is bit-identical to `probe_macro_f1` — same fold order, same
    fits — so C5-C7 continuity is preserved by construction rather than by
    convention.

    `oof_fn` (C8/D3) is the seam the attentive arm enters through. It defaults to
    `oof_classification`, the linear probe, and everything above this line stays
    exactly what it was; pass `oof_attentive_classification` (or a `partial` of
    it) and every statistic in this file — CIs, nulls, p-values, MDE — is
    computed over the attentive probe's out-of-fold scores instead, with no
    metric code duplicated. `X` is then whatever that fitter consumes: a matrix
    for the linear probe, a list of per-weld window sequences for the attentive
    one. The metric layer never inspects `X`; it only ever passes it back.
    """
    oof_fn = oof_fn or oof_classification
    y = np.asarray(y, dtype=float)
    oof = oof_fn(X, y, groups, n_splits=n_splits, seed=seed, warn=True)
    scores, preds = oof["scores"], oof["preds"]
    n_pos, n_neg = int((y == 1).sum()), int((y == 0).sum())
    two_class = n_pos > 0 and n_neg > 0

    macro_f1 = float(f1_score(y, preds, average="macro", zero_division=0))
    auc = float(roc_auc_score(y, scores)) if two_class else float("nan")
    auprc = float(average_precision_score(y, scores)) if two_class else float("nan")

    def _boot(metric):
        def _stat(idx):
            yy = y[idx]
            if len(np.unique(yy)) < 2:
                return None
            return metric(yy, scores[idx], preds[idx])
        return bootstrap_ci(_stat, len(y), n_boot=n_boot, seed=seed)

    ci_f1 = _boot(lambda yy, ss, pp: f1_score(yy, pp, average="macro", zero_division=0))
    ci_auc = _boot(lambda yy, ss, pp: roc_auc_score(yy, ss))
    ci_auprc = _boot(lambda yy, ss, pp: average_precision_score(yy, ss))

    def _refit_all(y_perm):
        o = oof_fn(X, y_perm, groups, n_splits=n_splits, seed=seed)
        if len(np.unique(y_perm)) < 2:
            return {k: float("nan") for k in ("macro_f1", "auc", "auprc")}
        return {
            "macro_f1": f1_score(y_perm, o["preds"], average="macro",
                                 zero_division=0),
            "auc": roc_auc_score(y_perm, o["scores"]),
            "auprc": average_precision_score(y_perm, o["scores"]),
        }

    nulls = permutation_null_multi(_refit_all, y, ["macro_f1", "auc", "auprc"],
                                   n_perm=n_perm, seed=seed)
    null_f1, null_auc, null_auprc = (nulls["macro_f1"], nulls["auc"],
                                     nulls["auprc"])

    return {
        "target": "binary",
        "macro_f1": macro_f1, "macro_f1_ci": ci_f1[:2],
        "auc": auc, "auc_ci": ci_auc[:2], "auc_se": ci_auc[2],
        "auprc": auprc, "auprc_ci": ci_auprc[:2],
        "fold_f1": [float(f) for f in oof["fold_f1"]],
        "fold_f1_std": float(np.std(oof["fold_f1"])),
        "null_macro_f1": null_f1, "null_auc": null_auc, "null_auprc": null_auprc,
        "p_macro_f1": null_p_value(macro_f1, null_f1["values"]),
        "p_auc": null_p_value(auc, null_auc["values"]),
        "p_auprc": null_p_value(auprc, null_auprc["values"]),
        "inside_null_macro_f1": inside_null(macro_f1, null_f1),
        "inside_null_auc": inside_null(auc, null_auc),
        "inside_null_auprc": inside_null(auprc, null_auprc),
        "mde_auc": mde_auc(n_pos, n_neg),
        "scores": scores, "preds": preds, "labels": y,
        "n": int(len(y)), "n_pos": n_pos, "n_neg": n_neg,
        "n_splits": oof["n_splits"],
    }


def probe_regression(X, y: np.ndarray, groups: np.ndarray,
                     n_splits: int = N_SPLITS, seed: int = SEED,
                     n_boot: int = N_BOOT, n_perm: int = N_PERM,
                     alpha_ridge: float = 1.0, oof_fn=None) -> dict:
    """
    The full C8 report for one arm on the CONTINUOUS depth target: MAE and R2
    with bootstrap CIs, a permutation null and p-value for each, and the
    design's MDE in ΔMAE.

    `y` is expected already in symlog space (see `symlog_depth`) so that MAE is
    directly comparable to the §7 ΔMAE thresholds. MAE is negated before it
    meets the null machinery — `permutation_null` scores a bigger-is-better
    quantity, and lower error is better — so `p_mae` reads the same direction as
    every other p-value here.

    `oof_fn` is the D3 seam described on `probe_classification`: it defaults to
    `oof_regression` (Ridge) and takes `oof_attentive_regression` for the
    attentive arm. `alpha_ridge` is ignored by fitters that have no L2 term.
    """
    oof_fn = oof_fn or oof_regression
    y = np.asarray(y, dtype=float)
    oof = oof_fn(X, y, groups, n_splits=n_splits, seed=seed,
                 alpha=alpha_ridge)
    preds = oof["preds"]
    mae = float(mean_absolute_error(y, preds))
    r2 = float(r2_score(y, preds))
    abs_err = np.abs(y - preds)

    ci_mae = bootstrap_ci(lambda idx: abs_err[idx].mean(), len(y),
                          n_boot=n_boot, seed=seed)
    ci_r2 = bootstrap_ci(
        lambda idx: (r2_score(y[idx], preds[idx]) if np.std(y[idx]) > 0 else None),
        len(y), n_boot=n_boot, seed=seed)

    def _refit_all(y_perm):
        o = oof_fn(X, y_perm, groups, n_splits=n_splits, seed=seed,
                   alpha=alpha_ridge)
        # MAE is negated so the null's upper tail means "better", as everywhere
        return {"neg_mae": -mean_absolute_error(y_perm, o["preds"]),
                "r2": r2_score(y_perm, o["preds"])}

    nulls = permutation_null_multi(_refit_all, y, ["neg_mae", "r2"],
                                   n_perm=n_perm, seed=seed)
    null_mae, null_r2 = nulls["neg_mae"], nulls["r2"]

    return {
        "target": "continuous",
        "mae": mae, "mae_ci": ci_mae[:2], "mae_se": ci_mae[2],
        "r2": r2, "r2_ci": ci_r2[:2],
        "fold_mae": oof["fold_mae"],
        "fold_mae_std": float(np.std(oof["fold_mae"])),
        "null_mae": null_mae, "null_r2": null_r2,
        "p_mae": null_p_value(-mae, null_mae["values"]),
        "p_r2": null_p_value(r2, null_r2["values"]),
        "inside_null_mae": inside_null(-mae, null_mae),
        "inside_null_r2": inside_null(r2, null_r2),
        "mde_mae": mde_mae(abs_err),
        "preds": preds, "y": y,
        "n": int(len(y)), "n_splits": oof["n_splits"],
    }


def evaluation_design_mde(report: dict) -> dict:
    """
    Gate C8-0's row for one evaluation design: what is the smallest effect this
    design could detect, and which §7 thresholds does that rule out?

    Returns the MDE plus the pre-registered thresholds it sits above. A
    threshold listed under "underpowered" must be declared exploratory, NOT run
    as a decisive test and reinterpreted afterwards (§7, and the specific C7
    mistake TH5 exists to name).
    """
    if report["target"] == "binary":
        mde, thresholds = report["mde_auc"], {"TH1": 0.05, "TH2": 0.03,
                                              "TH3": 0.03, "TH4": 0.05}
        metric = "delta_auc"
    else:
        mde, thresholds = report["mde_mae"], {"TH1": 0.02, "TH2": 0.01,
                                              "TH3": 0.01}
        metric = "delta_mae"
    underpowered = sorted(k for k, v in thresholds.items()
                          if not np.isfinite(mde) or v < mde)
    return {"metric": metric, "mde": mde, "n": report["n"],
            "thresholds": thresholds, "underpowered": underpowered,
            "powered": sorted(set(thresholds) - set(underpowered))}


def rich_report(X, y: np.ndarray, groups: np.ndarray,
                target: str = "fault", seed: int = SEED,
                n_boot: int = N_BOOT, n_perm: int = N_PERM,
                oof_cls=None, oof_reg=None) -> dict:
    """
    Route one arm's embeddings to the metric family its target demands: the
    binary fault bit to `probe_classification`, continuous fusion depth to
    `probe_regression` after symlog compression. Adds the Gate C8-0 MDE row.

    `oof_cls`/`oof_reg` (C8/D3) select WHICH probe is fitted inside that metric
    family; both default to the linear ones, so an unqualified call is the A2
    report unchanged. `attentive_report` is the only caller that passes them.
    """
    if target == DEPTH_KEY or target == "depth":
        rep = probe_regression(X, symlog_depth(y), groups, seed=seed,
                               n_boot=n_boot, n_perm=n_perm, oof_fn=oof_reg)
    else:
        rep = probe_classification(X, y, groups, seed=seed, n_boot=n_boot,
                                   n_perm=n_perm, oof_fn=oof_cls)
    rep["probe"] = "linear" if oof_cls is None and oof_reg is None else "attentive"
    rep["design"] = evaluation_design_mde(rep)
    return rep


# --------------------------------------------------------------------------
# C8/D3 — the attentive probe, and the diagnostic that decides whether to
# believe it.
#
# Why a second probe exists at all. C5 chose a linear probe on I-JEPA's own
# reasoning: freeze the encoder, ask the weakest possible model, and whatever it
# reads must have been laid out in the embedding rather than constructed by the
# classifier. The same authors abandoned that protocol for V-JEPA, reporting
# +16-17 points from attentive probing, on the grounds that there is no a priori
# reason for a good encoder to lay its information out in a LINEARLY separable
# subspace. A margin that size dwarfs the +0.033 C7 was adjudicating, so an
# encoder could be discarded here for holding its information in a form the
# linear probe cannot reach.
#
# Why the diagnostic is the point. A linear probe on a frozen embedding has
# nothing to memorise WITH beyond its own coefficients; an attentive probe adds
# a learnable query, and a query that picks which windows to look at can, on 79
# positives (or the 11-13 C7 actually had), score well by fitting itself rather
# than by reading the encoder. There is no way to tell those two apart from the
# attentive number alone. So the attentive probe is ALWAYS also run against the
# random-init encoder, which by construction contains nothing to read: if
# attentive-on-random beats linear-on-pretrained, the score is coming from the
# probe's parameters and every attentive number in that run is void. This is the
# same logic as the random-init floor in C5, applied one level up — there the
# floor tests the encoder, here it tests the probe.
# --------------------------------------------------------------------------

ATTN_DROPOUT = 0.1      # dropout on the attention weights (D3)
ATTN_EPOCHS = 300       # upper bound; early stopping almost always fires first
ATTN_PATIENCE = 50      # inner-val epochs without improvement before stopping
ATTN_LR = 5e-2


class AttentiveProbe(torch.nn.Module):
    """
    Single learnable query, single head, no MLP — the D3 probe, and no more.

    In words: the encoder turns each window of a weld into one hidden vector, so
    a weld arrives here as a SEQUENCE of window vectors rather than the single
    mean-pooled vector the linear probe sees. The probe holds one query vector,
    scores it against every window vector (a dot product, scaled by sqrt(H) as
    usual), softmaxes those scores into weights, and reads out the weighted sum.
    Learning the query means learning WHICH windows of a weld to look at —
    replacing the mean-pool's assumption that every window matters equally,
    which is exactly the assumption a weld with a localised fault violates.

    Deliberately absent, all per D3: no key or value projections (the hidden
    states are used as their own keys and values), no second head, no MLP after
    the readout. Every one of those would add parameters, and parameters are the
    thing under suspicion. What remains is the query (H) plus a linear readout
    (H + 1) = 2H + 1 parameters — reported beside every score by
    `attentive_report`, because a capacity claim without a parameter count is
    not checkable.

    Dropout is applied to the attention WEIGHTS rather than to the hidden states:
    it randomises which windows the probe is allowed to read on a given step, so
    the query cannot converge onto one memorised window per weld.
    """

    def __init__(self, hidden_dim: int, dropout: float = ATTN_DROPOUT):
        super().__init__()
        self.hidden_dim = hidden_dim
        self.query = torch.nn.Parameter(torch.zeros(hidden_dim))
        torch.nn.init.normal_(self.query, std=hidden_dim ** -0.5)
        self.dropout = torch.nn.Dropout(dropout)
        self.head = torch.nn.Linear(hidden_dim, 1)

    def n_params(self) -> int:
        """Trainable parameter count — 2H+1, reported beside every score."""
        return int(sum(p.numel() for p in self.parameters() if p.requires_grad))

    def forward(self, x: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
        """
        x    [B, W, H] padded window vectors; mask [B, W] True where real.
        Returns [B] logits (classification) or predictions (regression).
        """
        scores = (x @ self.query) / (self.hidden_dim ** 0.5)     # [B, W]
        scores = scores.masked_fill(~mask, float("-inf"))
        weights = self.dropout(torch.softmax(scores, dim=-1))
        pooled = torch.einsum("bw,bwh->bh", weights, x)          # [B, H]
        return self.head(pooled).squeeze(-1)


def pad_sequences(seqs: list[np.ndarray]) -> tuple[torch.Tensor, torch.Tensor]:
    """
    Ragged per-weld window sequences → a padded [N, W_max, H] batch plus its
    [N, W_max] validity mask. Welds have different durations and therefore
    different window counts; padding with a mask is the version that keeps the
    attention softmax over the real windows only.
    """
    hidden = seqs[0].shape[1]
    w_max = max(len(s) for s in seqs)
    x = torch.zeros(len(seqs), w_max, hidden)
    mask = torch.zeros(len(seqs), w_max, dtype=torch.bool)
    for i, s in enumerate(seqs):
        t = torch.as_tensor(np.asarray(s, dtype=np.float32))
        x[i, :len(t)] = t
        mask[i, :len(t)] = True
    return x, mask


def _inner_split(tr: np.ndarray, groups: np.ndarray, seed: int
                 ) -> tuple[np.ndarray, np.ndarray]:
    """
    Carve an inner validation fold out of an OUTER training fold, nested inside
    the existing GroupKFold and grouped the same way (D3).

    Early stopping needs data the probe is not fitted on, and taking it from the
    outer test fold would be the leak the whole GroupKFold design exists to
    prevent — the stopping epoch is a fitted quantity like any other. So the
    inner fold is drawn from the training side only, by session group, and the
    outer test fold is never touched until scoring. With too few groups to split,
    the training set doubles as its own validation set: early stopping degrades
    to "train the full budget", which is honest rather than leaky.
    """
    g = groups[tr]
    if len(np.unique(g)) < 2:
        return tr, tr
    n_inner = min(4, len(np.unique(g)))
    inner_tr, inner_va = next(GroupKFold(n_splits=n_inner).split(tr, groups=g))
    return tr[inner_tr], tr[inner_va]


def fit_attentive(seqs: list[np.ndarray], y: np.ndarray, tr: np.ndarray,
                  groups: np.ndarray, task: str, seed: int,
                  dropout: float = ATTN_DROPOUT, epochs: int = ATTN_EPOCHS,
                  patience: int = ATTN_PATIENCE, lr: float = ATTN_LR
                  ) -> AttentiveProbe:
    """
    Fit one AttentiveProbe on one outer training fold, early-stopping on the
    inner fold `_inner_split` carves out of it.

    Full-batch Adam: the probe has 2H+1 parameters and a few hundred welds, so
    minibatching would add stochasticity and a batch-size knob without buying
    anything. Classification uses BCE with `pos_weight = n_neg/n_pos`, the
    direct analogue of the linear probe's `class_weight="balanced"`, so the two
    arms are answering the same question about a 4%-positive target rather than
    two differently-weighted ones. Regression uses MSE on the symlog target.

    The returned probe carries the weights from the BEST inner-val epoch, not
    the last one — restoring the best state is the half of early stopping that
    is easy to omit and that makes the other half pointless.

    Early stopping is judged on the METRIC the arm is scored by, not on the
    training loss. This matters and was got wrong the obvious way first: a
    pos_weight-balanced BCE loss on the held-out inner fold *rises* as the probe
    grows confident and correct — a handful of hard inner-val welds dominate the
    weighted sum — so "stop when the val loss stops falling" restores a barely
    trained probe (its best val loss is at epoch zero) and the arm scores at
    chance. So for classification the criterion is inner-val AUC, the arm's own
    metric, with the (unweighted) val loss only as a tie-break between epochs
    that rank the fold identically; for regression it is negative inner-val MSE,
    which moves with the reported MAE. On a degenerate inner fold that holds one
    class the AUC is undefined, and the criterion falls back to the loss.
    """
    torch.manual_seed(seed)
    inner_tr, inner_va = _inner_split(tr, groups, seed)
    x_all, mask_all = pad_sequences(seqs)
    y_np = np.asarray(y, dtype=float)
    y_all = torch.as_tensor(y_np.astype(np.float32))

    probe = AttentiveProbe(x_all.shape[-1], dropout=dropout)
    opt = torch.optim.Adam(probe.parameters(), lr=lr)
    if task == "classification":
        n_pos = float((y_all[inner_tr] == 1).sum())
        n_neg = float((y_all[inner_tr] == 0).sum())
        pos_weight = torch.tensor(n_neg / max(n_pos, 1.0))
        loss_fn = torch.nn.BCEWithLogitsLoss(pos_weight=pos_weight)
        val_loss_fn = torch.nn.BCEWithLogitsLoss()   # unweighted: pure tie-break
    else:
        loss_fn = torch.nn.MSELoss()
        val_loss_fn = torch.nn.MSELoss()
    two_class_val = task == "classification" and len(np.unique(y_np[inner_va])) > 1

    best, best_state, waited = None, None, 0
    for _ in range(epochs):
        probe.train()
        opt.zero_grad()
        loss_fn(probe(x_all[inner_tr], mask_all[inner_tr]), y_all[inner_tr]).backward()
        opt.step()
        probe.eval()
        with torch.no_grad():
            va_out = probe(x_all[inner_va], mask_all[inner_va])
            va_loss = float(val_loss_fn(va_out, y_all[inner_va]))
        if two_class_val:
            metric = (roc_auc_score(y_np[inner_va], va_out.numpy()), -va_loss)
        else:
            metric = (-va_loss,)
        if best is None or metric > best:
            best, waited = metric, 0
            best_state = {k: v.detach().clone() for k, v in probe.state_dict().items()}
        else:
            waited += 1
            if waited >= patience:
                break
    if best_state is not None:
        probe.load_state_dict(best_state)
    probe.eval()
    return probe


@torch.no_grad()
def _attentive_predict(probe: AttentiveProbe, seqs: list[np.ndarray],
                       idx: np.ndarray) -> np.ndarray:
    x, mask = pad_sequences(seqs)
    return probe(x[idx], mask[idx]).numpy()


def oof_attentive_classification(seqs: list[np.ndarray], y: np.ndarray,
                                 groups: np.ndarray, n_splits: int = N_SPLITS,
                                 seed: int = SEED, warn: bool = False,
                                 dropout: float = ATTN_DROPOUT) -> dict:
    """
    The attentive twin of `oof_classification`, returning the same dict so the
    entire A2 statistics layer consumes it without knowing which probe ran.

    Same outer GroupKFold, same fold order, same "pool all held-out predictions
    and score once" convention. Scores are the probe's logits (the analogue of
    `decision_function`); hard predictions threshold them at zero, which for a
    pos_weight-balanced BCE is the balanced decision boundary, matching what
    `LogisticRegression(class_weight="balanced").predict` does.
    """
    n_splits = min(n_splits, len(np.unique(groups)))
    if warn and np.asarray(y).sum() < n_splits:
        print(f"WARNING: only {int(np.asarray(y).sum())} positive welds across "
              f"{n_splits} folds — the probe is under-powered at this data size")
    y = np.asarray(y, dtype=float)
    preds = np.zeros_like(y)
    scores = np.zeros_like(y, dtype=float)
    fold_f1, test_groups_per_fold, n_params = [], [], 0
    for k, (tr, te) in enumerate(GroupKFold(n_splits=n_splits).split(seqs, y, groups)):
        if len(np.unique(y[tr])) < 2:
            preds[te] = y[tr][0]        # degenerate fold: constant prediction
            scores[te] = float(y[tr][0])
        else:
            probe = fit_attentive(seqs, y, tr, groups, "classification",
                                  seed=seed + k, dropout=dropout)
            n_params = probe.n_params()
            scores[te] = _attentive_predict(probe, seqs, te)
            preds[te] = (scores[te] > 0).astype(float)
        fold_f1.append(f1_score(y[te], preds[te], average="macro", zero_division=0))
        test_groups_per_fold.append(set(groups[te].tolist()))
    return {"preds": preds, "scores": scores, "fold_f1": fold_f1,
            "n_splits": n_splits, "test_groups_per_fold": test_groups_per_fold,
            "probe_params": n_params}


def oof_attentive_regression(seqs: list[np.ndarray], y: np.ndarray,
                             groups: np.ndarray, n_splits: int = N_SPLITS,
                             seed: int = SEED, alpha: float = 1.0,
                             dropout: float = ATTN_DROPOUT) -> dict:
    """
    The attentive twin of `oof_regression`, for the C8 primary depth target.
    `alpha` exists only to match `oof_regression`'s signature — an attentive
    probe has no ridge term — and is accepted and ignored.
    """
    n_splits = min(n_splits, len(np.unique(groups)))
    y = np.asarray(y, dtype=float)
    preds = np.zeros(len(y), dtype=float)
    fold_mae, test_groups_per_fold, n_params = [], [], 0
    for k, (tr, te) in enumerate(GroupKFold(n_splits=n_splits).split(seqs, y, groups)):
        probe = fit_attentive(seqs, y, tr, groups, "regression",
                              seed=seed + k, dropout=dropout)
        n_params = probe.n_params()
        preds[te] = _attentive_predict(probe, seqs, te)
        fold_mae.append(float(mean_absolute_error(y[te], preds[te])))
        test_groups_per_fold.append(set(groups[te].tolist()))
    return {"preds": preds, "fold_mae": fold_mae, "n_splits": n_splits,
            "test_groups_per_fold": test_groups_per_fold,
            "probe_params": n_params}


@torch.no_grad()
def embed_weld_sequences(encoder: StemTrunkEncoder, sessions: list[SessionTensor],
                         label_key: str = LABEL_KEY, window: int = WINDOW,
                         stride: int = STRIDE, batch_size: int = 64,
                         device: str = "cpu"
                         ) -> tuple[list[np.ndarray], np.ndarray, np.ndarray]:
    """
    Frozen encoder → the SEQUENCE of window vectors per weld, unpooled.

    `embed_welds` mean-pools those same vectors into one row per weld; the
    attentive probe's whole purpose is to learn that pooling instead, so it needs
    them intact. Everything else is identical — same ProbeWindows, same channels,
    same last-frame GRU summary per window, same drop of welds too short for one
    window — which is what keeps the two probe arms a comparison of probes rather
    than of featurisations.

    Note this re-encodes rather than deriving the linear probe's X from these
    sequences. Summing in a different order would move the linear numbers in the
    last float bits, and C5-C7 macro-F1 values are reproduction targets; a second
    frozen forward pass is cheap insurance against that.
    """
    ds = ProbeWindows(sessions, label_keys=[label_key], window=window,
                      stride=stride, channels=PRETRAIN_CHANNELS)
    encoder = encoder.to(device).eval()
    per_weld: dict[int, list[np.ndarray]] = {}
    for i in range(0, len(ds), batch_size):
        items = [ds[j] for j in range(i, min(i + batch_size, len(ds)))]
        x = torch.stack([it[0] for it in items]).to(device)
        mask = torch.stack([it[1] for it in items]).to(device)
        vec = encoder(x, mask)[:, -1].cpu().numpy()
        for v, it in zip(vec, items):
            per_weld.setdefault(int(it[3]), []).append(v)
    keep = sorted(per_weld)
    seqs = [np.stack(per_weld[g]) for g in keep]
    y = np.array([weld_target(sessions[g].meta, label_key) for g in keep])
    return seqs, y, np.array(keep)


def attentive_report(seqs: list[np.ndarray], y: np.ndarray, groups: np.ndarray,
                     target: str = "fault", seed: int = SEED,
                     n_boot: int = N_BOOT, n_perm: int = N_PERM,
                     dropout: float = ATTN_DROPOUT) -> dict:
    """
    One arm's full C8 report with the attentive probe in place of the linear one.

    Identical statistics — the same CIs, nulls, p-values, paired differences and
    MDE — because this routes through `rich_report` and only swaps the fitter.
    Adds `probe_params`, the count D3 requires beside every attentive score, and
    `attentive_void`, which starts False and is stamped True by
    `capacity_diagnostic` if the probe turns out to be scoring on its own
    parameters.
    """
    from functools import partial
    rep = rich_report(seqs, y, groups, target=target, seed=seed, n_boot=n_boot,
                      n_perm=n_perm,
                      oof_cls=partial(oof_attentive_classification, dropout=dropout),
                      oof_reg=partial(oof_attentive_regression, dropout=dropout))
    # One extra fit purely to read the parameter count off a real probe rather
    # than recomputing 2H+1 by hand — a formula in a report can drift from the
    # module it claims to describe.
    hidden = seqs[0].shape[1]
    rep["probe_params"] = AttentiveProbe(hidden, dropout=dropout).n_params()
    rep["attentive_void"] = False
    rep["void_reason"] = None
    return rep


def report_headline(rep: dict) -> float:
    """
    The one bigger-is-better number a report is compared on: AUC for the binary
    fault bit, negated MAE for continuous depth. Used by the capacity diagnostic,
    which must compare a classification arm to a classification arm and a
    regression arm to a regression arm without a direction flag to get wrong.
    """
    return float(rep["auc"]) if rep["target"] == "binary" else -float(rep["mae"])


def capacity_diagnostic(attentive_random: dict, linear_pretrained: list[dict],
                        attentive_reports: list[dict] | None = None) -> dict:
    """
    The D3 mandatory diagnostic: is the attentive probe reading the encoder, or
    reading itself?

    The test is the one the spec names. Score the attentive probe on the
    RANDOM-INIT encoder — an encoder that by construction holds nothing about
    welds — and compare it to the best LINEAR probe on a PRETRAINED encoder. A
    probe with no information to read should not beat a probe that has some. If
    it does, the score is coming from the probe's 2H+1 parameters fitting 79
    positives, and every attentive number in the run is void: not "treat with
    caution", void, because there is no way to subtract the memorisation term
    from the pretrained arms' attentive scores and see what is left.

    Any report passed in `attentive_reports` is stamped in place with
    `attentive_void` and a reason, so a void verdict travels with the numbers
    rather than living only in the printed block a reader might skip.
    """
    rand = report_headline(attentive_random)
    lin = [report_headline(r) for r in linear_pretrained]
    best_linear = max(lin) if lin else float("-inf")
    void = bool(lin) and rand > best_linear
    reason = (f"attentive-on-random ({rand:.4f}) beats the best "
              f"linear-on-pretrained ({best_linear:.4f}): the probe is fitting "
              f"itself, not reading the encoder" if void else None)
    for rep in (attentive_reports or []):
        rep["attentive_void"] = void
        rep["void_reason"] = reason
    return {
        "attentive_random": rand,
        "best_linear_pretrained": best_linear if lin else float("nan"),
        "margin": rand - best_linear if lin else float("nan"),
        "void": void,
        "reason": reason,
        "probe_params": attentive_random.get("probe_params"),
        "metric": "auc" if attentive_random["target"] == "binary" else "neg_mae",
    }


def score_checkpoint(path: Path, sessions: list[SessionTensor],
                     label_key: str = LABEL_KEY, window: int = WINDOW,
                     stride: int = STRIDE, device: str = "cpu",
                     seed: int = SEED, rich: bool = False,
                     n_boot: int = N_BOOT, n_perm: int = N_PERM,
                     attentive: bool = False) -> dict:
    """
    One comparable row per contract checkpoint — the C5 seam.

    `rich=False` is the C5-C7 row, unchanged. `rich=True` additionally attaches
    the full C8 report under "report"; the legacy keys keep their exact values
    either way, so a C7 reproduction and a C8 run read the same macro-F1.
    `attentive=True` (C8/D3) attaches a SECOND report under "attentive", scored
    with the attentive probe on the same encoder; it adds a row, it never edits
    one, so the linear numbers are untouched by construction.
    """
    from world_model.pretraining.common import build_encoder, load_transfer_checkpoint
    ckpt = load_transfer_checkpoint(Path(path))
    encoder = build_encoder(ckpt)
    X, y, groups = embed_welds(encoder, sessions, label_key=label_key,
                               window=window, stride=stride, device=device)
    # The legacy macro-F1 row only exists for the binary target; the continuous
    # depth target has no hard labels to score and reports MAE/R2 instead.
    probe = ({"macro_f1": float("nan"), "fold_f1_std": float("nan")}
             if label_key == DEPTH_KEY else probe_macro_f1(X, y, groups, seed=seed))
    row = {
        "checkpoint": Path(path).name,
        "objective": ckpt["objective"],
        "macro_f1": probe["macro_f1"],
        "fold_f1_std": probe["fold_f1_std"],
        "n_welds": int(len(y)),
        "n_positive": 0 if label_key == DEPTH_KEY else int(y.sum()),
    }
    if rich:
        row["report"] = rich_report(X, y, groups, target=label_key, seed=seed,
                                    n_boot=n_boot, n_perm=n_perm)
    if attentive:
        seqs, y_seq, g_seq = embed_weld_sequences(
            encoder, sessions, label_key=label_key, window=window,
            stride=stride, device=device)
        row["attentive"] = attentive_report(seqs, y_seq, g_seq, target=label_key,
                                            seed=seed, n_boot=n_boot,
                                            n_perm=n_perm)
    return row


def score_random_floor(sessions: list[SessionTensor], label_key: str = LABEL_KEY,
                       window: int = WINDOW, stride: int = STRIDE,
                       device: str = "cpu", seed: int = SEED,
                       rich: bool = False, n_boot: int = N_BOOT,
                       n_perm: int = N_PERM, attentive: bool = False) -> dict:
    """
    The untrained-encoder floor every contender must clear.

    Under C8/D3 this row does double duty: with `attentive=True` its attentive
    report is the capacity diagnostic's left-hand side — the score an attentive
    probe posts with literally nothing to read. That is why the attentive run
    forces this row even under --no-random.

    Under C8 this row carries the heaviest evidential load in the file: if the
    floor's AUC also lands inside the permutation null — as every C7 number did
    — then the comparison has not measured pretraining, it has measured noise,
    and no arm's win is reportable.
    """
    torch.manual_seed(seed)
    encoder = StemTrunkEncoder(PRETRAIN_CHANNELS)
    X, y, groups = embed_welds(encoder, sessions, label_key=label_key,
                               window=window, stride=stride, device=device)
    # The legacy macro-F1 row only exists for the binary target; the continuous
    # depth target has no hard labels to score and reports MAE/R2 instead.
    probe = ({"macro_f1": float("nan"), "fold_f1_std": float("nan")}
             if label_key == DEPTH_KEY else probe_macro_f1(X, y, groups, seed=seed))
    row = {
        "checkpoint": "(random init)",
        "objective": "none",
        "macro_f1": probe["macro_f1"],
        "fold_f1_std": probe["fold_f1_std"],
        "n_welds": int(len(y)),
        "n_positive": 0 if label_key == DEPTH_KEY else int(y.sum()),
    }
    if rich:
        row["report"] = rich_report(X, y, groups, target=label_key, seed=seed,
                                    n_boot=n_boot, n_perm=n_perm)
    if attentive:
        seqs, y_seq, g_seq = embed_weld_sequences(
            encoder, sessions, label_key=label_key, window=window,
            stride=stride, device=device)
        row["attentive"] = attentive_report(seqs, y_seq, g_seq, target=label_key,
                                            seed=seed, n_boot=n_boot,
                                            n_perm=n_perm)
    return row


def run_capacity_diagnostic(rows: list[dict]) -> dict | None:
    """
    Apply D3 across a finished run: take the random-init row's attentive report
    as the left-hand side, every pretrained row's LINEAR report as the right, and
    stamp the verdict onto every attentive report in the run.

    Returns None when the diagnostic cannot be run — no random-init row, or no
    pretrained linear report to compare against. Returning None rather than a
    permissive pass is deliberate: "we could not check" and "we checked and it
    was fine" are different states, and the printer says so.
    """
    rand = next((r for r in rows if r["objective"] == "none"), None)
    if rand is None or "attentive" not in rand:
        return None
    linear = [r["report"] for r in rows
              if r["objective"] != "none" and "report" in r]
    if not linear:
        return None
    attentive = [r["attentive"] for r in rows if "attentive" in r]
    return capacity_diagnostic(rand["attentive"], linear, attentive)


def format_attentive_rows(rows: list[dict], diagnostic: dict | None) -> str:
    """
    Render the D3 block: every attentive score with its parameter count, then the
    capacity diagnostic, then — if it tripped — a VOID banner over the lot.

    The parameter count sits in the table rather than a footnote because it is
    the quantity that makes the score interpretable: 2H+1 parameters against 79
    positives is a ratio the reader has to see to judge the number beside it.
    """
    reps = [(r, r["attentive"]) for r in rows if "attentive" in r]
    if not reps:
        return ""
    out = ["\nattentive probe (D3) — single learnable query, single head, no MLP"]
    binary = reps[0][1]["target"] == "binary"
    if binary:
        out.append(f"{'objective':<14} {'macro-F1':>9} {'AUC':>8} "
                   f"{'AUC 95% CI':>18} {'p(AUC)':>8} {'params':>8}  verdict")
        for r, rep in reps:
            lo, hi = rep["auc_ci"]
            mark = "INSIDE-NULL" if rep["inside_null_auc"] else "outside null"
            out.append(f"{r['objective']:<14} {rep['macro_f1']:>9.4f} "
                       f"{rep['auc']:>8.4f} [{lo:>7.4f},{hi:>7.4f}] "
                       f"{rep['p_auc']:>8.3f} {rep['probe_params']:>8d}  {mark}")
    else:
        out.append(f"{'objective':<14} {'MAE':>9} {'MAE 95% CI':>18} {'R2':>8} "
                   f"{'p(MAE)':>8} {'params':>8}  verdict")
        for r, rep in reps:
            lo, hi = rep["mae_ci"]
            mark = "INSIDE-NULL" if rep["inside_null_mae"] else "outside null"
            out.append(f"{r['objective']:<14} {rep['mae']:>9.4f} "
                       f"[{lo:>7.4f},{hi:>7.4f}] {rep['r2']:>8.4f} "
                       f"{rep['p_mae']:>8.3f} {rep['probe_params']:>8d}  {mark}")

    if diagnostic is None:
        out.append("\nD3 capacity diagnostic: NOT RUN (needs a random-init row "
                   "and at least one pretrained linear report) — attentive "
                   "numbers above are unverified, not cleared")
        return "\n".join(out)
    out.append(f"\nD3 capacity diagnostic ({diagnostic['metric']}): "
               f"attentive-on-random {diagnostic['attentive_random']:.4f} vs "
               f"best linear-on-pretrained "
               f"{diagnostic['best_linear_pretrained']:.4f} "
               f"(margin {diagnostic['margin']:+.4f}, "
               f"probe params {diagnostic['probe_params']})")
    if diagnostic["void"]:
        out.append("  *** ATTENTIVE NUMBERS VOID *** " + diagnostic["reason"])
        out.append("  Every attentive score in this run is unusable: the probe "
                   "scores without an encoder to read, so its scores WITH one "
                   "cannot be attributed to the encoder.")
    else:
        out.append("  PASS — the attentive probe does not beat a linear probe "
                   "without an encoder to read; attentive numbers stand")
    return "\n".join(out)


def format_rich_rows(rows: list[dict]) -> str:
    """
    Render the C8 block: every arm's numbers, each with its CI, the null it must
    beat, its permutation p-value, and an explicit INSIDE-NULL marker. The MDE
    for the design and the pairwise between-arm differences follow.

    The INSIDE-NULL marker is the point of the whole ticket. C7's table looked
    like a result because nothing on it said "this number is what chance
    produces here". Here that sentence is printed next to every number, and a
    run in which the random-init floor is not marked INSIDE-NULL is itself a
    signal that something is wrong with the split.
    """
    reps = [(r, r["report"]) for r in rows if "report" in r]
    if not reps:
        return ""
    out = []
    binary = reps[0][1]["target"] == "binary"
    if binary:
        out.append(f"\n{'objective':<14} {'macro-F1':>9} {'AUC':>8} "
                   f"{'AUC 95% CI':>18} {'AUPRC':>8} {'p(AUC)':>8}  null(AUC)"
                   f"          verdict")
        for r, rep in reps:
            lo, hi = rep["auc_ci"]
            nl, nh = rep["null_auc"]["lo"], rep["null_auc"]["hi"]
            mark = "INSIDE-NULL" if rep["inside_null_auc"] else "outside null"
            out.append(f"{r['objective']:<14} {rep['macro_f1']:>9.4f} "
                       f"{rep['auc']:>8.4f} [{lo:>7.4f},{hi:>7.4f}] "
                       f"{rep['auprc']:>8.4f} {rep['p_auc']:>8.3f}  "
                       f"[{nl:.3f},{nh:.3f}]  {mark}")
    else:
        out.append(f"\n{'objective':<14} {'MAE':>9} {'MAE 95% CI':>18} "
                   f"{'R2':>8} {'p(MAE)':>8}  null(MAE)          verdict")
        for r, rep in reps:
            lo, hi = rep["mae_ci"]
            nl, nh = -rep["null_mae"]["hi"], -rep["null_mae"]["lo"]
            mark = "INSIDE-NULL" if rep["inside_null_mae"] else "outside null"
            out.append(f"{r['objective']:<14} {rep['mae']:>9.4f} "
                       f"[{lo:>7.4f},{hi:>7.4f}] {rep['r2']:>8.4f} "
                       f"{rep['p_mae']:>8.3f}  [{nl:.3f},{nh:.3f}]  {mark}")

    d = reps[0][1]["design"]
    out.append(f"\nGate C8-0 — minimum detectable effect ({d['metric']}): "
               f"{d['mde']:.4f} on n={d['n']}")
    if d["underpowered"]:
        out.append(f"  UNDERPOWERED IN ADVANCE (threshold < MDE): "
                   f"{', '.join(d['underpowered'])} — declare exploratory, "
                   f"do NOT run as decisive")
    if d["powered"]:
        out.append(f"  adequately powered: {', '.join(d['powered'])}")

    out.append("\npaired between-arm differences (bootstrap CI; H&M 1983 CI):")
    for i in range(len(reps)):
        for j in range(i + 1, len(reps)):
            (ra, repa), (rb, repb) = reps[i], reps[j]
            if binary:
                diff = paired_auc_diff(repa["scores"], repb["scores"],
                                       repa["labels"])
                val, name = diff["delta_auc"], "ΔAUC"
            else:
                diff = paired_mae_diff(repa["y"], repa["preds"], repb["preds"])
                val, name = diff["delta_mae"], "ΔMAE"
            lo, hi = diff["boot_lo"], diff["boot_hi"]
            hml, hmh = diff["hm_lo"], diff["hm_hi"]
            flag = "excludes 0" if diff["excludes_zero"] else "includes 0"
            out.append(f"  {ra['objective']}/{ra['checkpoint']} vs "
                       f"{rb['objective']}/{rb['checkpoint']}: {name}="
                       f"{val:+.4f} boot[{lo:+.4f},{hi:+.4f}] "
                       f"H&M[{hml:+.4f},{hmh:+.4f}] {flag}")
    return "\n".join(out)


# --------------------------------------------------------------------------
# C8/T1 — dual evaluation: the powered full-Polito real-domain score, and the
# sim/real pairing that keeps a simulated number from ever being read alone.
#
# The trap this exists for (spec §4/T1, the silent one). An encoder pretrained on
# Goldak-generated welds learns to invert *Goldak*, not physics. A held-out
# SIMULATED test set cannot detect that: it was produced by the same equations,
# so it inherits the same errors and rewards the same skill — the test shares the
# assumption it is meant to test. No statistic fixes this, because every simulated
# number has the property; the fix is structural. Two mechanics implement it here.
#
# 1. No simulated metric is ever reported alone. Every simulated number is bound
#    into a sim/real PAIR (`t1_result`) and stamped with `T1_CAVEAT`, so the caveat
#    travels with the number rather than living in a paragraph a reader might skip.
#    There is no code path that returns a bare simulated headline: `sim_headline`
#    hands back the real partner alongside it, by construction.
#
# 2. The real-domain score is finally powered, via a DELIBERATE asymmetry. Polito
#    was demoted from training set to evaluation set (spec §4), so arms pretrained
#    on Goldak or random — and the untrained floor — never saw ANY Polito and can
#    be scored on the ENTIRE corpus: 1,976 welds, 79 positives, ~7x the 11-13 that
#    a train/test split left and that made C7's real-domain ranking pure noise. The
#    Polito-PRETRAINED incumbent DID see the train split, so it must stay on its
#    held-out split (11-13 positives) or the number leaks. That asymmetry is not
#    hidden: `polito_eval_split` returns the eval-set name and it is printed beside
#    every arm, so a reader can see which arms got 79 positives and which got 11-13.
#
# The detector is a later ticket's job; this file only has to EXPOSE what it needs.
# `t1_rankings` ranks the sim-trained arms on both evaluation sets — the held-out
# simulated set and full Polito — so that ticket can compute the ranking
# disagreement between them, which is the Goldak-inversion signal.
# --------------------------------------------------------------------------

# The fixed caveat string, stamped onto every simulated report. Mirrors the one
# the spec requires in gate_status.md; kept here as the single source so a report
# and its caveat cannot drift apart.
T1_CAVEAT = ("SIMULATED — this number scores the ability to invert Goldak, not "
             "physics. A held-out simulated set shares the generator's assumptions "
             "and cannot detect that. Not reportable alone: read only beside its "
             "paired real-domain (Polito) number.")


def arm_corpus(ckpt: dict) -> str:
    """
    Which corpus an arm pretrained on, read from its transfer-checkpoint config.

    The Polito path adds NOTHING to a run config (that emptiness is the C4-C7
    hash invariant `load_corpus` protects), so a missing `corpus` key is exactly
    the Polito incumbent — the one arm that must not be scored on full Polito.
    Every simulated arm (goldak-wide/narrow, spectrum-random, supervised-on-sim)
    carries its corpus name here.
    """
    return str(ckpt.get("config", {}).get("corpus", "polito"))


def is_sim_trained(corpus: str) -> bool:
    """
    True for arms that never saw Polito — the ones scored on the full corpus (T1).

    Takes the corpus STRING rather than the checkpoint so the untrained random
    floor (which has no checkpoint but also never saw Polito) can be classified
    by the same rule. Everything that is not literally the Polito incumbent is a
    "never saw Polito" arm for eval-set purposes.
    """
    return corpus != "polito"


def polito_eval_split(corpus: str, full_sessions: list, split_map: dict,
                      split: str = "val") -> tuple[list, str]:
    """
    The T1 real-domain evaluation set for one arm, plus the NAME of that set.

    Sim-trained arms and the untrained floor never saw Polito, so they take the
    entire corpus — every split concatenated, 1,976 welds / 79 positives. The
    Polito-pretrained incumbent saw the train split during pretraining, so it
    keeps its held-out split only (11-13 positives). Returning the name is the
    point: the asymmetry is recorded in the output, never hidden, so a reader can
    see which arms were scored on 79 positives and which on 11-13.
    """
    if is_sim_trained(corpus):
        return full_sessions, "full-polito"
    return split_map[split], f"held-out-{split}"


def stamp_caveat(report: dict) -> dict:
    """
    Mark a report as simulated and attach the fixed T1 caveat, in place.

    Called on the simulated half of every pair so the caveat is carried by the
    number itself. `domain` lets any consumer tell a simulated report from a real
    one without re-deriving it from the arm's corpus.
    """
    report["t1_caveat"] = T1_CAVEAT
    report["domain"] = "simulated"
    return report


def t1_result(*, arm: str, checkpoint: str, corpus: str,
              real_report: dict, real_eval: str,
              sim_report: dict | None = None, sim_eval: str | None = None,
              is_floor: bool = False) -> dict:
    """
    One arm's T1-disciplined result: its real-domain number, and — for a
    sim-trained arm — the simulated number bound to it as an inseparable pair.

    Every arm has a real-domain (Polito) number, and that number IS reportable
    alone: a real measurement needs no caveat. A simulated number is not, so it
    only ever appears inside `res["sim"]`, which also holds the real partner and
    the caveat. There is deliberately no field carrying a bare simulated headline.
    `paired` is True exactly when a simulated number is present and therefore
    exactly when the sim/real discipline is in force for this arm.
    """
    res = {
        "arm": arm, "checkpoint": checkpoint, "corpus": corpus,
        "sim_trained": is_sim_trained(corpus), "is_floor": is_floor,
        "real": {"report": real_report, "eval": real_eval,
                 "n": int(real_report["n"]),
                 "n_pos": int(real_report.get("n_pos", 0))},
        "sim": None,
        "paired": False,
    }
    if sim_report is not None:
        res["sim"] = {"report": stamp_caveat(sim_report), "eval": sim_eval,
                      "n": int(sim_report["n"]), "caveat": T1_CAVEAT}
        res["paired"] = True
    return res


def sim_headline(result: dict) -> dict:
    """
    The simulated headline of a paired result — never returned without its real
    partner and caveat. This is the discipline in code: there is no way to pull a
    simulated number out of this module on its own. Raises if the arm has no
    simulated half (the incumbent, or a floor scored on Polito only).
    """
    if result["sim"] is None:
        raise ValueError(f"arm {result['arm']!r} has no simulated number to report")
    return {
        "sim": report_headline(result["sim"]["report"]),
        "sim_eval": result["sim"]["eval"],
        "real": report_headline(result["real"]["report"]),
        "real_eval": result["real"]["eval"],
        "caveat": T1_CAVEAT,
    }


def t1_rankings(results: list[dict]) -> dict:
    """
    Rank the sim-trained arms on BOTH evaluation sets — the input T1's detector
    needs, computed by a later ticket as ranking disagreement between the two.

    The "real" ranking is the POWERED one the spec calls for: sim-trained arms on
    full Polito (79 positives), incumbent excluded because it is not needed to
    detect Goldak-inversion and its 11-13-positive split would only add noise. The
    "sim" ranking is those same arms on their held-out simulated set. Both order
    by `report_headline` (bigger is better: AUC for the fault bit, negated MAE for
    depth), so a later ticket can compare orders without a direction flag to trip
    over. Only arms with BOTH halves are ranked — a ranking disagreement needs a
    point in each set.

    `disagreement_computable` is False with fewer than two paired arms: one arm
    has no ranking to disagree with, and the detector should say "not computable"
    rather than silently return a trivial agreement.
    """
    paired = [r for r in results if r["sim"] is not None]

    def _rank(half: str) -> list:
        scored = [(r["arm"], report_headline(r[half]["report"])) for r in paired]
        return sorted(scored, key=lambda t: t[1], reverse=True)

    return {
        "arms": [r["arm"] for r in paired],
        "sim": _rank("sim"),
        "real": _rank("real"),
        "disagreement_computable": len(paired) >= 2,
    }


def _domain_report(encoder, sessions: list, label_key: str, *,
                   window: int = WINDOW, stride: int = STRIDE,
                   device: str = "cpu", seed: int = SEED,
                   n_boot: int = N_BOOT, n_perm: int = N_PERM) -> dict:
    """
    Embed one encoder over one evaluation set and route it through the C8 metric
    layer — the one call shared by both halves of every pair. It goes through
    `rich_report` (ticket #20) unchanged, so the sim and real numbers are the
    SAME statistics (CIs, nulls, MDE) as the rest of the file, differing only in
    which sessions and which target they were computed on.
    """
    X, y, groups = embed_welds(encoder, sessions, label_key=label_key,
                               window=window, stride=stride, device=device)
    return rich_report(X, y, groups, target=label_key, seed=seed,
                       n_boot=n_boot, n_perm=n_perm)


def t1_reports_for_encoder(encoder, *, arm: str, checkpoint: str, corpus: str,
                           real_full: list, real_heldout: list,
                           sim_sessions: list | None = None,
                           real_label_key: str = LABEL_KEY,
                           sim_label_key: str = DEPTH_KEY, split: str = "val",
                           is_floor: bool = False, window: int = WINDOW,
                           stride: int = STRIDE, device: str = "cpu",
                           seed: int = SEED, n_boot: int = N_BOOT,
                           n_perm: int = N_PERM) -> dict:
    """
    Score one already-built encoder into a T1 result — the seam the checkpoint
    driver and the untrained floor both enter through.

    The real-domain half is always scored, on the eval set `polito_eval_split`
    picks from `corpus`: full Polito for a sim-trained arm or the floor, the
    held-out split for the incumbent. The simulated half is scored only when
    `sim_sessions` is supplied AND the arm is sim-trained — the incumbent has no
    simulator to be paired against, and a floor is a real-domain baseline. The two
    halves use different targets by default: the real fault bit is binary (Polito
    carries no depth), the simulated primary target is continuous fusion depth.
    """
    real_sessions, real_eval = polito_eval_split(corpus, real_full, split_map={
        split: real_heldout}, split=split)
    real_report = _domain_report(encoder, real_sessions, real_label_key,
                                 window=window, stride=stride, device=device,
                                 seed=seed, n_boot=n_boot, n_perm=n_perm)
    sim_report = sim_eval = None
    if sim_sessions is not None and is_sim_trained(corpus):
        sim_report = _domain_report(encoder, sim_sessions, sim_label_key,
                                    window=window, stride=stride, device=device,
                                    seed=seed, n_boot=n_boot, n_perm=n_perm)
        sim_eval = "held-out-sim"
    return t1_result(arm=arm, checkpoint=checkpoint, corpus=corpus,
                     real_report=real_report, real_eval=real_eval,
                     sim_report=sim_report, sim_eval=sim_eval, is_floor=is_floor)


def score_checkpoint_t1(path: Path, *, real_full: list, real_heldout: list,
                        sim_sessions: list | None = None,
                        real_label_key: str = LABEL_KEY,
                        sim_label_key: str = DEPTH_KEY, split: str = "val",
                        window: int = WINDOW, stride: int = STRIDE,
                        device: str = "cpu", seed: int = SEED,
                        n_boot: int = N_BOOT, n_perm: int = N_PERM) -> dict:
    """
    One checkpoint → one T1 result. Reads the arm's corpus off its config (which
    decides its real eval set), builds the frozen encoder, and scores it on both
    domains. The corpus field is the ONLY thing that distinguishes a sim-trained
    arm from the incumbent here, and it is exactly the field `load_corpus` writes.
    """
    from world_model.pretraining.common import build_encoder, load_transfer_checkpoint
    ckpt = load_transfer_checkpoint(Path(path))
    encoder = build_encoder(ckpt)
    corpus = arm_corpus(ckpt)
    return t1_reports_for_encoder(
        encoder, arm=ckpt["objective"], checkpoint=Path(path).name, corpus=corpus,
        real_full=real_full, real_heldout=real_heldout, sim_sessions=sim_sessions,
        real_label_key=real_label_key, sim_label_key=sim_label_key, split=split,
        window=window, stride=stride, device=device, seed=seed,
        n_boot=n_boot, n_perm=n_perm)


def score_floor_t1(*, real_full: list, real_heldout: list,
                   real_label_key: str = LABEL_KEY, split: str = "val",
                   window: int = WINDOW, stride: int = STRIDE,
                   device: str = "cpu", seed: int = SEED,
                   n_boot: int = N_BOOT, n_perm: int = N_PERM) -> dict:
    """
    The untrained random-init floor as a T1 result. It never saw Polito, so it
    takes the powered full-Polito set — which is what makes it the floor T1 wants:
    if this 79-positive floor lands inside the permutation null, the real-domain
    comparison measured noise and no arm's win is reportable. It has no simulated
    half — it is a real-domain baseline, not a corpus arm.
    """
    torch.manual_seed(seed)
    encoder = StemTrunkEncoder(PRETRAIN_CHANNELS)
    return t1_reports_for_encoder(
        encoder, arm="none", checkpoint="(random init)", corpus="(random init)",
        real_full=real_full, real_heldout=real_heldout, sim_sessions=None,
        real_label_key=real_label_key, split=split, is_floor=True,
        window=window, stride=stride, device=device, seed=seed,
        n_boot=n_boot, n_perm=n_perm)


def format_t1_rows(results: list[dict], rankings: dict) -> str:
    """
    Render the T1 block: the sim/real pairing, the recorded asymmetry, and the
    two rankings the detector consumes.

    The asymmetry table is the load-bearing part. It prints each arm's real eval
    set and its positive count side by side, so the 79-vs-11-13 gap the spec
    insists must be "recorded, not hidden" is visible on the page rather than
    inferable from the corpus column. Every simulated headline is printed with its
    real partner and the caveat marker `†`, and the caveat text is printed once at
    the foot — no simulated number appears without it.
    """
    if not results:
        return ""
    out = ["\nT1 dual evaluation — powered full-Polito scoring + sim/real pairing"]
    out.append(f"{'arm':<16} {'corpus':<16} {'real eval':<16} "
               f"{'positives':>10}  sim/real")
    for r in results:
        rr = r["real"]
        pos = f"{rr['n_pos']}/{rr['n']}"
        if r["sim"] is None:
            pairing = "real only (no simulator)" + (" [floor]" if r["is_floor"]
                                                    else " [incumbent]")
        else:
            h = sim_headline(r)
            pairing = (f"sim {h['sim']:+.4f}† / real {h['real']:+.4f}")
        out.append(f"{r['arm']:<16} {r['corpus']:<16} {rr['eval']:<16} "
                   f"{pos:>10}  {pairing}")

    # The asymmetry, stated explicitly rather than left to be read off the table.
    sim_arms = [r for r in results if is_sim_trained(r["corpus"])]
    inc = [r for r in results if not is_sim_trained(r["corpus"])]
    if sim_arms and inc:
        s_pos = sim_arms[0]["real"]["n_pos"]
        i_pos = inc[0]["real"]["n_pos"]
        out.append(f"\nasymmetry (deliberate, §4/T1): sim-trained arms scored on "
                   f"full Polito ({s_pos} positives); incumbent on its held-out "
                   f"split ({i_pos} positives). The two real-domain numbers are "
                   f"NOT symmetrically powered and must not be compared as if they "
                   f"were — TH1 is the power-limited claim this asymmetry confounds.")

    # The rankings the detector consumes — printed so a later ticket's disagreement
    # computation can be checked against what the run actually saw.
    if rankings["arms"]:
        out.append("\nsim-trained arm rankings (T1 detector input):")
        out.append("  by full-Polito (real, powered): "
                   + ", ".join(f"{a}={v:+.4f}" for a, v in rankings["real"]))
        out.append("  by held-out simulated set:       "
                   + ", ".join(f"{a}={v:+.4f}" for a, v in rankings["sim"]))
        out.append("  ranking disagreement computable: "
                   f"{rankings['disagreement_computable']} "
                   "(the Goldak-inversion signal; computed by a later ticket)")
    elif any(r["sim_trained"] for r in results):
        out.append("\nsim-trained arms present but no simulated evaluation set "
                   "supplied (--sim-eval): the sim half of each pair is PENDING, "
                   "so no simulated number is reported — the real-domain "
                   "full-Polito scores above stand alone by design, not by pairing.")

    out.append(f"\n† {T1_CAVEAT}")
    return "\n".join(out)


def _load_sim_eval_sessions(args):
    """
    The held-out split of a simulated evaluation corpus, for the sim half of each
    T1 pair. Uses the existing corpus loaders (importing them, never editing them)
    so the evaluation corpus is generated the same way the pretraining corpora
    were. Split by the same session-grouped hashing as everything else, then the
    requested split is taken — the sim number is a HELD-OUT simulated number, with
    all the T1 caveats that carries.
    """
    from world_model.data.splits import split_sessions
    if args.sim_eval == "random":
        from world_model.data.corpus_random import load_random_sessions
        sessions, _ = load_random_sessions(n_sessions=args.sim_sessions,
                                           source_seed=args.sim_seed)
    else:
        from world_model.data.corpus_goldak import load_goldak_sessions
        sessions, _ = load_goldak_sessions(variant=args.sim_variant,
                                           n_sessions=args.sim_sessions,
                                           seed=args.sim_seed)
    return split_sessions(sessions, seed=args.seed)[args.split]


def _run_dual_eval(args, p):
    """
    The C8/T1 dual-evaluation driver: the powered full-Polito real-domain score,
    the sim/real pairing, and the sim-trained rankings the detector consumes.

    Kept wholly separate from the legacy path so a C4-C7 reproduction never enters
    here. The real-domain target is the binary fault bit (Polito carries no depth);
    the simulated target, when a --sim-eval corpus is supplied, is continuous
    fusion depth — the primary target §7 scores by ΔMAE.
    """
    from world_model.data.loader_polito import load_polito_sessions
    from world_model.data.splits import split_sessions
    from world_model.eval.eval_world_model import append_run

    limit = TINY["n_sessions"] if args.tiny else args.limit
    all_sessions = load_polito_sessions(limit=limit)
    split_map = split_sessions(all_sessions, seed=args.seed)
    heldout = split_map[args.split]
    n_full = sum(int(s.meta[LABEL_KEY]) for s in all_sessions)
    n_held = sum(int(s.meta[LABEL_KEY]) for s in heldout)
    print(f"T1 dual eval: full Polito = {len(all_sessions)} welds ({n_full} "
          f"positive); held-out {args.split} = {len(heldout)} welds ({n_held} "
          f"positive)  window={args.window} stride={args.stride}")

    sim_sessions = None
    if args.sim_eval is not None:
        sim_sessions = _load_sim_eval_sessions(args)
        if any(DEPTH_KEY not in s.meta for s in sim_sessions):
            p.error(f"--sim-eval {args.sim_eval} produced sessions without "
                    f"meta[{DEPTH_KEY!r}]; the simulated half is scored on depth")
        print(f"  simulated eval ({args.sim_eval}): {len(sim_sessions)} held-out "
              f"sessions scored on {DEPTH_KEY}")

    # Gate C8-0 (ticket #26): the power precheck runs HERE, before any encoder is
    # scored, and its verdict is printed before the decisive numbers exist. The
    # fault-bit designs need only the positive counts already in hand — full Polito
    # (n_full positives) and the incumbent's symmetric held-out split (n_held) — so
    # this cannot depend on the run it gates. The depth design's MDE needs a pilot
    # error scale and is not projectable from counts alone, so it is left to the
    # per-arm reports below; the fault-bit half is the powered/underpowered call C7
    # never made in advance. Printing only — nothing here blocks execution of the
    # exploratory arms; it records which comparisons must NOT be read as decisive.
    from world_model.eval.power_gate import (fault_design, format_power_gate,
                                             power_gate, FULL_POLITO,
                                             SYMMETRIC_HELDOUT)
    gate = power_gate([
        fault_design(FULL_POLITO, n_pos=n_full, n_neg=len(all_sessions) - n_full),
        fault_design(SYMMETRIC_HELDOUT, n_pos=n_held, n_neg=len(heldout) - n_held),
    ])
    print("\n" + format_power_gate(gate) + "\n")

    common = dict(real_full=all_sessions, real_heldout=heldout,
                  sim_sessions=sim_sessions, split=args.split,
                  window=args.window, stride=args.stride, device=args.device,
                  seed=args.seed, n_boot=args.n_boot, n_perm=args.n_perm)
    results = [] if args.no_random else [score_floor_t1(
        real_full=all_sessions, real_heldout=heldout, split=args.split,
        window=args.window, stride=args.stride, device=args.device,
        seed=args.seed, n_boot=args.n_boot, n_perm=args.n_perm)]
    results += [score_checkpoint_t1(c, **common) for c in args.checkpoints]

    rankings = t1_rankings(results)
    print(format_t1_rows(results, rankings))

    config = dict(model="probe_compare_t1", split=args.split, limit=limit,
                  window=args.window, stride=args.stride, seed=args.seed)
    for r in results:
        rr = r["real"]["report"]
        note = (f"T1 dual eval; arm={r['arm']} ckpt={r['checkpoint']} "
                f"corpus={r['corpus']} real_eval={r['real']['eval']} "
                f"real_positives={r['real']['n_pos']}/{r['real']['n']} "
                f"real_auc={rr['auc']:.4f} real_inside_null={rr['inside_null_auc']}")
        if r["sim"] is not None:
            sr = r["sim"]["report"]
            # the simulated number never travels without the caveat marker
            note += (f" sim_eval={r['sim']['eval']} sim_mae={sr['mae']:.4f} "
                     f"sim_caveat=T1")
        append_run("probe_compare_t1",
                   {**config, "checkpoint": r["checkpoint"]}, args.seed,
                   split=args.split,
                   metrics=dict(n=r["real"]["n"],
                                quality_f1_macro=rr["macro_f1"],
                                fusion_mae_mm=(r["sim"]["report"]["mae"]
                                              if r["sim"] is not None else None),
                                per_class_recall=None),
                   note=note)


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
    # C8/A2. Default OFF so a C4-C7 reproduction prints byte-identical output.
    p.add_argument("--rich-metrics", action="store_true",
                   help="C8: AUC/AUPRC (or MAE/R2) with bootstrap CIs, "
                        "permutation nulls, paired differences, and the "
                        "Gate C8-0 MDE, printed after the legacy table")
    p.add_argument("--target", default=LABEL_KEY, choices=[LABEL_KEY, "depth"],
                   help=f"{LABEL_KEY} = binary secondary target (C5-C7 default); "
                        f"depth = continuous primary target (meta[{DEPTH_KEY!r}])")
    # C8/D3. Also default OFF; adds a second table, never edits the first.
    p.add_argument("--attentive-probe", action="store_true",
                   help="C8: additionally score every arm with an attentive "
                        "probe (single learnable query), report its parameter "
                        "count, and run the mandatory capacity diagnostic "
                        "against the random-init encoder")
    p.add_argument("--n-boot", type=int, default=N_BOOT,
                   help="bootstrap resamples per CI")
    p.add_argument("--n-perm", type=int, default=N_PERM,
                   help="label permutations per null")
    # C8/T1. Default OFF; a wholly separate scoring path, so nothing here can
    # touch a C4-C7 reproduction. Turns the run into the sim/real-paired, powered
    # full-Polito evaluation §4/T1 specifies.
    p.add_argument("--dual-eval", action="store_true",
                   help="C8/T1: score sim-trained arms on FULL Polito (79 "
                        "positives) and the incumbent on its held-out split, "
                        "report every simulated number paired to a real one with "
                        "the T1 caveat, and expose the sim-trained rankings the "
                        "Goldak-inversion detector consumes")
    p.add_argument("--sim-eval", choices=["goldak", "random"], default=None,
                   help="C8/T1: simulated evaluation corpus for the sim half of "
                        "each pair (held-out split of goldak or the spectrum "
                        "control); omit to run the real-domain asymmetry only")
    p.add_argument("--sim-variant", default="wide", choices=("wide", "narrow"),
                   help="goldak only: which corpus variant to score the sim half on")
    p.add_argument("--sim-sessions", type=int, default=None,
                   help="number of simulated evaluation sessions to generate")
    p.add_argument("--sim-seed", type=int, default=None,
                   help="base seed for the simulated evaluation corpus")
    args = p.parse_args()

    if args.dual_eval:
        return _run_dual_eval(args, p)

    label_key = DEPTH_KEY if args.target == "depth" else LABEL_KEY
    if args.target == "depth" and not args.rich_metrics:
        p.error("--target depth requires --rich-metrics: the depth target is "
                "continuous and has no macro-F1 to print in the legacy table")
    limit = TINY["n_sessions"] if args.tiny else args.limit

    sessions = split_sessions(load_polito_sessions(limit=limit),
                              seed=args.seed)[args.split]
    if label_key == DEPTH_KEY and any(DEPTH_KEY not in s.meta for s in sessions):
        # Polito is resistance spot welding and carries no depth ground truth;
        # the continuous target lives on the simulated corpora (C8 item 2).
        p.error(f"--target depth needs meta[{DEPTH_KEY!r}] on every session, "
                f"which the Polito loader does not provide")
    n_fault = sum(int(s.meta[LABEL_KEY]) for s in sessions)
    print(f"probing on {args.split}: {len(sessions)} welds "
          f"({n_fault} faulty)  window={args.window} stride={args.stride}")

    if args.attentive_probe and not args.rich_metrics:
        p.error("--attentive-probe requires --rich-metrics: the attentive arm "
                "reports through the C8 metric layer, and its capacity "
                "diagnostic compares against a linear arm's rich report")

    extra = dict(rich=args.rich_metrics, n_boot=args.n_boot, n_perm=args.n_perm,
                 attentive=args.attentive_probe)
    # D3: the random-init row IS the capacity diagnostic, so an attentive run
    # keeps it even when --no-random asked for it to be dropped.
    if args.no_random and args.attentive_probe:
        print("note: --no-random ignored — the D3 capacity diagnostic needs the "
              "random-init encoder")
    rows = [] if (args.no_random and not args.attentive_probe) else [
        score_random_floor(sessions, label_key=label_key, window=args.window,
                           stride=args.stride, device=args.device,
                           seed=args.seed, **extra)]
    rows += [score_checkpoint(c, sessions, label_key=label_key,
                              window=args.window, stride=args.stride,
                              device=args.device, seed=args.seed, **extra)
             for c in args.checkpoints]

    if label_key != DEPTH_KEY:
        print(f"\n{'objective':<14} {'macro-F1':>9} {'±fold':>7}  checkpoint")
        for r in rows:
            print(f"{r['objective']:<14} {r['macro_f1']:>9.4f} "
                  f"{r['fold_f1_std']:>7.4f}  {r['checkpoint']}")
    if args.rich_metrics:
        print(format_rich_rows(rows))
    diagnostic = None
    if args.attentive_probe:
        diagnostic = run_capacity_diagnostic(rows)
        print(format_attentive_rows(rows, diagnostic))

    config = dict(model="probe_compare", split=args.split, limit=limit,
                  window=args.window, stride=args.stride, seed=args.seed)
    if label_key == DEPTH_KEY:
        # only added off-default, so C5-C7 run hashes are untouched
        config["target"] = "depth"
    for r in rows:
        rep = r.get("report")
        depth = label_key == DEPTH_KEY
        # note stays comma-free (runs.csv is comma-joined)
        note = (f"linear probe; objective={r['objective']} "
                f"ckpt={r['checkpoint']} fold_std={r['fold_f1_std']:.4f} "
                f"positives={r['n_positive']}/{r['n_welds']}")
        if rep is not None:
            # C8 additions land in the note so runs.csv keeps its column set
            note += (f" mae={rep['mae']:.4f} r2={rep['r2']:.4f} "
                     f"p_mae={rep['p_mae']:.3f} mde={rep['design']['mde']:.4f}"
                     if depth else
                     f" auc={rep['auc']:.4f} auprc={rep['auprc']:.4f} "
                     f"p_auc={rep['p_auc']:.3f} "
                     f"inside_null={rep['inside_null_auc']} "
                     f"mde_auc={rep['design']['mde']:.4f}")
        att = r.get("attentive")
        if att is not None:
            # D3: the parameter count and the void flag travel with the score
            att_head = (f"attn_mae={att['mae']:.4f}" if depth
                        else f"attn_auc={att['auc']:.4f}")
            note += (f" {att_head} attn_params={att['probe_params']} "
                     f"attn_void={att['attentive_void']}")
        append_run("probe_compare", {**config, "checkpoint": r["checkpoint"]},
                   args.seed, split=args.split,
                   metrics=dict(n=r["n_welds"],
                                quality_f1_macro=None if depth else r["macro_f1"],
                                fusion_mae_mm=rep["mae"] if (depth and rep) else None,
                                per_class_recall=None),
                   note=note)


if __name__ == "__main__":
    main()
