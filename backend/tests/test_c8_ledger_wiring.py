"""
Tests for the C8 decisive-run LEDGER WIRING — the seam between the scoring
subprocesses and the adjudication (`c8_headtohead.py`, the part the module
docstring used to call "the last wiring the compute-bearing run supplies").

Three surfaces, all pure logic (no training, no corpus):

  * `pool_seed_diffs` — C7's mean-across-seeds convention with a combined CI.
    The pooled delta must be the equal-weight mean, the SE the fixed-effect
    combination, and `excludes_zero` must be answered by the POOLED interval —
    three seeds that individually straddle zero can pool to a decisive one, and
    the reverse must be impossible.
  * `collect_decisive_inputs` — JSON → (diffs, mdes) assembly: checkpoint-name
    matching, the antisymmetric flip when a pair was recorded incumbent-first,
    TH4's binding-incumbent rule, and absence → not-run (never a verdict).
  * `t1_paired_matrix` (eval side) — every §7-pairable geometry appears with
    the right metric family, identical-weld enforcement, and the T1 caveat
    riding on every simulated (depth) diff.

The rehearsal switch is also pinned: rehearsal must scale the run DOWN and
move scoring to val, and the default must remain the pre-registered decisive
configuration — a rehearsal that silently became the real thing (or vice
versa) is exactly the kind of quiet drift C8 exists to make loud.
"""

import importlib
import json
import math

import numpy as np
import pytest

import world_model.experiments.notebook.c8_headtohead as d
from world_model.eval.compare_pretrains import (T1_CAVEAT, t1_paired_matrix,
                                                t1_result)


# ---------------------------------------------------------------------------
# pool_seed_diffs
# ---------------------------------------------------------------------------

def _diff(delta, se, family=d.FAULT, caveat=False):
    key = "delta_mae" if family == d.DEPTH else "delta_auc"
    out = {key: delta, "boot_se": se,
           "boot_lo": delta - 1.96 * se, "boot_hi": delta + 1.96 * se,
           "excludes_zero": bool(delta - 1.96 * se > 0 or delta + 1.96 * se < 0)}
    if caveat:
        out["t1_caveat"] = T1_CAVEAT
    return out


def test_pooling_is_the_equal_weight_mean_of_seed_deltas():
    pooled = d.pool_seed_diffs(
        [_diff(0.10, 0.01), _diff(0.20, 0.01), _diff(0.30, 0.01)], d.FAULT)
    assert pooled["delta_auc"] == pytest.approx(0.20)
    assert pooled["per_seed"] == [0.10, 0.20, 0.30]
    assert pooled["n_seeds"] == 3


def test_pooled_se_is_the_fixed_effect_combination():
    pooled = d.pool_seed_diffs([_diff(0.1, 0.03), _diff(0.1, 0.04)], d.FAULT)
    assert pooled["boot_se"] == pytest.approx(math.sqrt(0.03**2 + 0.04**2) / 2)


def test_seeds_that_individually_straddle_zero_can_pool_decisive():
    # each seed: 0.05 ± 1.96*0.04 straddles zero; pooled over 3: SE shrinks
    # to 0.0231 → CI [0.0047, 0.0953] excludes zero.
    seeds = [_diff(0.05, 0.04)] * 3
    assert not seeds[0]["excludes_zero"]
    pooled = d.pool_seed_diffs(seeds, d.FAULT)
    assert pooled["excludes_zero"]


def test_disagreeing_seeds_pool_to_underpowered_not_decisive():
    pooled = d.pool_seed_diffs([_diff(0.30, 0.01), _diff(-0.30, 0.01)], d.FAULT)
    assert pooled["delta_auc"] == pytest.approx(0.0)
    assert not pooled["excludes_zero"]


def test_depth_pooling_reads_delta_mae_and_keeps_the_caveat():
    pooled = d.pool_seed_diffs(
        [_diff(0.03, 0.001, d.DEPTH, caveat=True)] * 2, d.DEPTH)
    assert "delta_mae" in pooled and "delta_auc" not in pooled
    assert pooled["t1_caveat"] == T1_CAVEAT


def test_pooling_refuses_an_empty_seed_list():
    with pytest.raises(ValueError):
        d.pool_seed_diffs([], d.FAULT)


# ---------------------------------------------------------------------------
# _flip_diff — the antisymmetric repair
# ---------------------------------------------------------------------------

def test_flip_negates_delta_and_mirrors_the_ci():
    diff = {"delta_auc": 0.2, "boot_se": 0.01, "boot_lo": 0.18, "boot_hi": 0.22,
            "hm_lo": 0.17, "hm_hi": 0.23, "excludes_zero": True}
    flipped = d._flip_diff(diff, d.FAULT)
    assert flipped["delta_auc"] == -0.2
    assert (flipped["boot_lo"], flipped["boot_hi"]) == (-0.22, -0.18)
    assert (flipped["hm_lo"], flipped["hm_hi"]) == (-0.23, -0.17)
    # excludes_zero is invariant under mirroring
    assert flipped["excludes_zero"] == diff["excludes_zero"]


# ---------------------------------------------------------------------------
# collect_decisive_inputs — JSON assembly
# ---------------------------------------------------------------------------

def _write_pair_json(monkeypatch, tmp_path, entries):
    """Point LOGS at tmp and write one JSON per (challenger, incumbent, seed)."""
    monkeypatch.setattr(d, "LOGS", tmp_path)
    for (ch, inc, seed), payload in entries.items():
        (tmp_path / d.scoring_json_path(ch, inc, seed).name).write_text(
            json.dumps(payload))


def _payload(pairs, mde=0.02):
    return {"pairs": pairs,
            "mdes": {p["geometry"]: {"metric": "delta_auc", "mde": mde, "n": 32}
                     for p in pairs}}


def _pair(ck_a, ck_b, geometry, delta, se=0.001, family=d.FAULT):
    return {"a": {"arm": "x", "checkpoint": ck_a, "corpus": "goldak-wide"},
            "b": {"arm": "y", "checkpoint": ck_b, "corpus": "polito"},
            "geometry": geometry, "diff": _diff(delta, se, family)}


def _by_arm_for(comp):
    arms = {comp.challenger, *comp.incumbents}
    return {arm: {seed: f"/ckpt/{arm}_s{seed}.pt" for seed in d.SEEDS}
            for arm in arms}


def _comp(th_id, family):
    return next(c for c in d.COMPARISON_PLAN
                if c.th_id == th_id and c.family == family)


def test_collect_pools_across_seeds_and_keys_by_th_and_family(
        monkeypatch, tmp_path):
    comp = _comp("TH1", d.FAULT)
    inc = comp.incumbents[0]
    entries = {}
    for i, seed in enumerate(d.SEEDS):
        ck_ch = f"{comp.challenger}_s{seed}.pt"
        ck_in = f"{inc}_s{seed}.pt"
        entries[(comp.challenger, inc, seed)] = _payload(
            [_pair(ck_ch, ck_in, comp.geometry, 0.10 + 0.10 * i)])
    _write_pair_json(monkeypatch, tmp_path, entries)
    diffs, _ = d.collect_decisive_inputs(_by_arm_for(comp))
    key = (comp.th_id, comp.family)
    assert key in diffs
    expected = sum(0.10 + 0.10 * i for i in range(len(d.SEEDS))) / len(d.SEEDS)
    assert diffs[key]["delta_auc"] == pytest.approx(expected)


def test_collect_flips_a_pair_recorded_incumbent_first(monkeypatch, tmp_path):
    comp = _comp("TH1", d.FAULT)
    inc = comp.incumbents[0]
    entries = {}
    for seed in d.SEEDS:
        # incumbent recorded as arm A ⇒ the raw delta is incumbent-minus-
        # challenger and must come back negated.
        entries[(comp.challenger, inc, seed)] = _payload(
            [_pair(f"{inc}_s{seed}.pt", f"{comp.challenger}_s{seed}.pt",
                   comp.geometry, -0.15)])
    _write_pair_json(monkeypatch, tmp_path, entries)
    diffs, _ = d.collect_decisive_inputs(_by_arm_for(comp))
    assert diffs[(comp.th_id, comp.family)]["delta_auc"] == pytest.approx(0.15)


def test_th4_takes_the_binding_incumbent_the_smaller_delta(
        monkeypatch, tmp_path):
    comp = _comp("TH4", d.FAULT)
    assert len(comp.incumbents) == 2, "TH4 must name both SSL arms"
    entries = {}
    deltas = {comp.incumbents[0]: 0.30, comp.incumbents[1]: 0.04}
    for inc, delta in deltas.items():
        for seed in d.SEEDS:
            entries[(comp.challenger, inc, seed)] = _payload(
                [_pair(f"{comp.challenger}_s{seed}.pt", f"{inc}_s{seed}.pt",
                       comp.geometry, delta)])
    _write_pair_json(monkeypatch, tmp_path, entries)
    diffs, _ = d.collect_decisive_inputs(_by_arm_for(comp))
    binding = diffs[(comp.th_id, comp.family)]
    assert binding["delta_auc"] == pytest.approx(0.04)
    assert binding["incumbent"] == comp.incumbents[1]


def test_th4_with_one_incumbent_missing_reports_not_run(monkeypatch, tmp_path):
    comp = _comp("TH4", d.FAULT)
    inc = comp.incumbents[0]          # only ONE of the two required incumbents
    entries = {}
    for seed in d.SEEDS:
        entries[(comp.challenger, inc, seed)] = _payload(
            [_pair(f"{comp.challenger}_s{seed}.pt", f"{inc}_s{seed}.pt",
                   comp.geometry, 0.30)])
    _write_pair_json(monkeypatch, tmp_path, entries)
    diffs, mdes = d.collect_decisive_inputs(_by_arm_for(comp))
    assert (comp.th_id, comp.family) not in diffs
    ledger = d.adjudicate_all(diffs, mdes)
    row = next(r for r in ledger
               if r["id"] == "TH4" and r.get("family", d.FAULT) == d.FAULT)
    assert row["verdict"] == "not-run"


def test_missing_jsons_flow_through_to_a_not_run_ledger(monkeypatch, tmp_path):
    monkeypatch.setattr(d, "LOGS", tmp_path)     # empty dir: no scoring ran
    diffs, mdes = d.collect_decisive_inputs({})
    assert diffs == {} and mdes == {}
    ledger = d.adjudicate_all(diffs, mdes)
    assert all(r["verdict"] == "not-run" for r in ledger)


def test_th5_rows_carry_their_design_mde(monkeypatch, tmp_path):
    comp = _comp("TH5", d.FAULT)
    inc = comp.incumbents[0]
    entries = {}
    for seed in d.SEEDS:
        entries[(comp.challenger, inc, seed)] = _payload(
            [_pair(f"{comp.challenger}_s{seed}.pt", f"{inc}_s{seed}.pt",
                   comp.geometry, 0.20)], mde=0.07)
    _write_pair_json(monkeypatch, tmp_path, entries)
    _, mdes = d.collect_decisive_inputs(_by_arm_for(comp))
    assert mdes[(comp.th_id, comp.family)] == pytest.approx(0.07)


# ---------------------------------------------------------------------------
# t1_paired_matrix — the eval-side half of the seam
# ---------------------------------------------------------------------------

def _clf_report(scores, labels, mde=0.05):
    scores, labels = np.asarray(scores, float), np.asarray(labels)
    return {"scores": scores, "labels": labels, "preds": (scores > 0.5),
            "n": len(labels), "design": {"metric": "delta_auc", "mde": mde}}


def _reg_report(preds, y, mde=0.01):
    return {"preds": np.asarray(preds, float), "y": np.asarray(y, float),
            "n": len(y), "design": {"metric": "delta_mae", "mde": mde}}


def _arm(name, *, full=None, heldout=None, sim=None, sim_probe=None):
    real_report = full if full is not None else heldout
    real_eval = "full-polito" if full is not None else "held-out-val"
    return t1_result(arm=name, checkpoint=f"{name}.pt", corpus="goldak-wide"
                     if full is not None else "(polito)",
                     real_report=real_report, real_eval=real_eval,
                     sim_report=sim, sim_eval="held-out-sim" if sim else None,
                     heldout_report=heldout if full is not None else None,
                     sim_probe_report=sim_probe)


def test_matrix_pairs_every_shared_geometry_with_the_right_family():
    rng = np.random.default_rng(0)
    y = np.array([0, 1] * 16)
    sa, sb = rng.random(32), rng.random(32)
    yh = np.array([0, 1] * 8)
    ha, hb = rng.random(16), rng.random(16)
    depth_y = rng.random(24)
    a = _arm("a", full=_clf_report(sa, y), heldout=_clf_report(ha, yh),
             sim=_reg_report(rng.random(24), depth_y))
    b = _arm("b", full=_clf_report(sb, y), heldout=_clf_report(hb, yh),
             sim=_reg_report(rng.random(24), depth_y))
    matrix = t1_paired_matrix([a, b], n_boot=50)
    geoms = {p["geometry"] for p in matrix["pairs"]}
    assert geoms == {"full-polito", "symmetric-heldout", "sim-heldout"}
    for p in matrix["pairs"]:
        if p["geometry"] == "sim-heldout":
            assert "delta_mae" in p["diff"]
            assert p["diff"]["t1_caveat"] == T1_CAVEAT     # sim number → caveat
        else:
            assert "delta_auc" in p["diff"]
            assert "t1_caveat" not in p["diff"]


def test_matrix_pairs_incumbent_depth_through_the_sim_probe_retention():
    rng = np.random.default_rng(1)
    yh = np.array([0, 1] * 8)
    depth_y = rng.random(24)
    challenger = _arm("ch", full=_clf_report(rng.random(32), np.array([0, 1] * 16)),
                      heldout=_clf_report(rng.random(16), yh),
                      sim=_reg_report(rng.random(24), depth_y))
    incumbent = _arm("inc", heldout=_clf_report(rng.random(16), yh),
                     sim_probe=_reg_report(rng.random(24), depth_y))
    matrix = t1_paired_matrix([challenger, incumbent], n_boot=50)
    assert any(p["geometry"] == "sim-heldout" for p in matrix["pairs"])


def test_matrix_refuses_paired_auc_on_different_welds():
    rng = np.random.default_rng(2)
    a = _arm("a", full=_clf_report(rng.random(32), np.array([0, 1] * 16)))
    b = _arm("b", full=_clf_report(rng.random(32), np.array([1, 0] * 16)))
    with pytest.raises(ValueError, match="identical welds"):
        t1_paired_matrix([a, b], n_boot=50)


def test_matrix_reports_each_geometry_design_mde_once():
    rng = np.random.default_rng(3)
    y = np.array([0, 1] * 16)
    a = _arm("a", full=_clf_report(rng.random(32), y, mde=0.123))
    b = _arm("b", full=_clf_report(rng.random(32), y, mde=0.123))
    matrix = t1_paired_matrix([a, b], n_boot=50)
    assert matrix["mdes"]["full-polito"]["mde"] == pytest.approx(0.123)


# ---------------------------------------------------------------------------
# the rehearsal switch
# ---------------------------------------------------------------------------

def _reload_with(monkeypatch, value):
    if value is None:
        monkeypatch.delenv("C8_REHEARSAL", raising=False)
    else:
        monkeypatch.setenv("C8_REHEARSAL", value)
    mod = importlib.reload(d)
    return mod


def test_default_is_the_pre_registered_decisive_configuration(monkeypatch):
    mod = _reload_with(monkeypatch, None)
    try:
        assert not mod.REHEARSAL
        assert mod.SEEDS == (1337, 1338, 1339)
        assert mod.N_SESSIONS == 20000
        assert mod.EPOCHS == "30"
        assert mod.SCORING_SPLIT == "test"
    finally:
        _reload_with(monkeypatch, None)


def test_rehearsal_scales_down_and_moves_scoring_off_the_test_split(
        monkeypatch):
    mod = _reload_with(monkeypatch, "1")
    try:
        assert mod.REHEARSAL
        assert len(mod.SEEDS) == 2          # pooling still exercised
        assert mod.N_SESSIONS < 1000 and mod.EPOCHS != "30"
        assert mod.SCORING_SPLIT == "val"   # the one test look is NOT spent
        cmds = mod.decisive_scoring_commands(
            {c.challenger: {s: f"/x/{c.challenger}_{s}.pt" for s in mod.SEEDS}
             for c in mod.COMPARISON_PLAN}
            | {i: {s: f"/x/{i}_{s}.pt" for s in mod.SEEDS}
               for c in mod.COMPARISON_PLAN for i in c.incumbents},
            mod.TestSplitGuard())
        assert all("test" not in cmd[cmd.index("--split") + 1] for cmd in cmds)
        assert all("--tiny" in cmd for cmd in cmds)
    finally:
        _reload_with(monkeypatch, None)


def test_every_sim_heldout_comparison_gets_a_simulated_half(monkeypatch):
    # The first rehearsal caught TH2- and TH5-depth starving: their scoring
    # commands carried no --sim-eval, so the primary TH5 depth comparison
    # could never be computed. Pin the repair: every pair some §7 row judges
    # on sim-heldout must be scored with a simulated half, on goldak-wide.
    mod = _reload_with(monkeypatch, None)
    try:
        by_arm = ({c.challenger: {s: f"/x/{c.challenger}_{s}.pt"
                                  for s in mod.SEEDS}
                   for c in mod.COMPARISON_PLAN}
                  | {i: {s: f"/x/{i}_{s}.pt" for s in mod.SEEDS}
                     for c in mod.COMPARISON_PLAN for i in c.incumbents})
        cmds = mod.decisive_scoring_commands(by_arm, mod.TestSplitGuard())
        by_json = {cmd[cmd.index("--json-out") + 1]: cmd for cmd in cmds}
        for comp in mod.COMPARISON_PLAN:
            if comp.geometry != mod.SIM_HELDOUT:
                continue
            for inc in comp.incumbents:
                for seed in mod.SEEDS:
                    cmd = by_json[str(mod.scoring_json_path(
                        comp.challenger, inc, seed))]
                    assert "--sim-eval" in cmd, (comp.th_id, inc)
                    assert cmd[cmd.index("--sim-variant") + 1] == "wide"
    finally:
        _reload_with(monkeypatch, None)


def test_scoring_commands_carry_a_json_out_per_pair_and_seed(monkeypatch):
    mod = _reload_with(monkeypatch, None)
    try:
        by_arm = ({c.challenger: {s: f"/x/{c.challenger}_{s}.pt"
                                  for s in mod.SEEDS}
                   for c in mod.COMPARISON_PLAN}
                  | {i: {s: f"/x/{i}_{s}.pt" for s in mod.SEEDS}
                     for c in mod.COMPARISON_PLAN for i in c.incumbents})
        cmds = mod.decisive_scoring_commands(by_arm, mod.TestSplitGuard())
        paths = [cmd[cmd.index("--json-out") + 1] for cmd in cmds]
        assert len(paths) == len(set(paths)), "one JSON per (pair, seed)"
    finally:
        _reload_with(monkeypatch, None)
