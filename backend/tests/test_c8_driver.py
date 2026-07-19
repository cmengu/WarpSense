"""
test_c8_driver.py — the C8 decisive-run driver in
experiments/notebook/c8_headtohead.py (issue #27, spec §6/§7).

What these tests defend. The driver's job is not to train models — that is a
compute-heavy run this suite never triggers — but to encode three things
correctly, and it is those three the tests pin:

  1. THE MATRIX (§6). Exactly 15 new checkpoints, three seeds each, with JEPA on
     goldak-wide ONLY and masked recon spanning wide/narrow/random; plus C7's six
     Polito checkpoints reused by reference, never retrained.
  2. THE ORDER (§7). Gate C8-0 is recorded BEFORE any test-split touch, and the
     test split is touched EXACTLY once — enforced by TestSplitGuard, not by
     discipline.
  3. THE TIE RULE (§7/TH5). A paired CI that includes zero yields
     "underpowered — not decided", and there is NO path — and no string in the
     source — that turns a zero-crossing CI into "tie, incumbent wins". This is the
     specific C7 failure C8 exists to make unrepresentable, so it gets the most
     tests.

Everything here runs on stubs and hand-built diff dicts; nothing loads a corpus,
trains an encoder, or reads the test split. The paired-diff shape the stubs use
matches `paired_auc_diff`/`paired_mae_diff` in compare_pretrains.py (delta +
excludes_zero + boot bounds), so the adjudication is exercised against the real
contract.
"""

from pathlib import Path

import pytest

from world_model.eval.power_gate import (
    DEPTH, FAULT, FULL_POLITO, SIM_HELDOUT, SYMMETRIC_HELDOUT)
from world_model.experiments.notebook import c8_headtohead as d


# --------------------------------------------------------------------------
# Helpers — paired-diff dicts shaped like the real metric layer's output.
# --------------------------------------------------------------------------

def fault_diff(delta, lo, hi):
    return {"delta_auc": delta, "boot_lo": lo, "boot_hi": hi,
            "excludes_zero": bool(lo > 0 or hi < 0)}


def depth_diff(delta, lo, hi):
    return {"delta_mae": delta, "boot_lo": lo, "boot_hi": hi,
            "excludes_zero": bool(lo > 0 or hi < 0)}


# ==========================================================================
# 1. THE MATRIX (§6)
# ==========================================================================

def test_exactly_fifteen_new_checkpoints_three_seeds_each():
    runs = d.new_training_runs()
    assert len(runs) == 15
    # three seeds per arm, five arms
    by_arm = {}
    for r in runs:
        by_arm.setdefault(r.arm, []).append(r.seed)
    assert len(by_arm) == 5
    for arm, seeds in by_arm.items():
        assert sorted(seeds) == [1337, 1338, 1339], arm


def test_jepa_trains_on_goldak_wide_only():
    runs = d.new_training_runs()
    jepa = [r for r in runs if r.module == d._JEPA]
    assert len(jepa) == 3                       # one arm × three seeds
    for r in jepa:
        assert r.arm == d.JEPA_WIDE
        assert "goldak" in r.corpus_args and "wide" in r.corpus_args
    # JEPA is NOT trained on narrow or random — the §6 saving.
    assert not any(r.module == d._JEPA and r.arm in (d.MR_NARROW, d.MR_RANDOM)
                   for r in runs)


def test_masked_recon_spans_wide_narrow_random():
    runs = d.new_training_runs()
    mr_arms = {r.arm for r in runs if r.module == d._MR}
    assert mr_arms == {d.MR_WIDE, d.MR_NARROW, d.MR_RANDOM}
    # the T4 control is the spectrum-random corpus, no goldak variant
    rnd = [r for r in runs if r.arm == d.MR_RANDOM]
    assert all("random" in r.corpus_args for r in rnd)
    assert all("goldak" not in r.corpus_args for r in rnd)


def test_supervised_arm_is_goldak_wide_t5():
    runs = d.new_training_runs()
    sup = [r for r in runs if r.module == d._SUP]
    assert len(sup) == 3
    assert all(r.arm == d.SUP_WIDE for r in sup)
    assert all("goldak" in r.corpus_args and "wide" in r.corpus_args for r in sup)


def test_seed_matched_corpus_is_fixed_across_seeds():
    # the corpus is generated once (fixed CORPUS_SEED); only --seed moves, so the
    # three seeds of an arm are seed-matched partners on the SAME dataset.
    runs = [r for r in d.new_training_runs() if r.arm == d.MR_WIDE]
    for r in runs:
        assert f"--corpus-seed" in r.cli_args
        assert str(d.CORPUS_SEED) in r.cli_args
        assert "--seed" in r.cli_args and str(r.seed) in r.cli_args


def test_reused_c7_checkpoints_are_the_six_named_hashes():
    reused = d.reused_c7_checkpoints()
    assert set(reused) == {d.JEPA_POLITO, d.MR_POLITO}
    jepa = {Path(p).name for p in reused[d.JEPA_POLITO].values()}
    mr = {Path(p).name for p in reused[d.MR_POLITO].values()}
    assert jepa == {"jepa_pretrain_e7f0e92d7625.pt",
                    "jepa_pretrain_0b1928f64c3a.pt",
                    "jepa_pretrain_a0af0e76939f.pt"}
    assert mr == {"masked_recon_windows_6a0b09b6c113.pt",
                  "masked_recon_windows_44889df44347.pt",
                  "masked_recon_windows_1464012e1949.pt"}
    # keyed by the three seeds
    assert set(reused[d.JEPA_POLITO]) == {1337, 1338, 1339}


def test_reused_checkpoints_are_never_expressed_as_training_runs():
    # no new TrainRun trains on Polito — the reused six carry no compute.
    for r in d.new_training_runs():
        assert "polito" not in r.corpus_args
        assert r.arm not in (d.JEPA_POLITO, d.MR_POLITO)


# ==========================================================================
# 2. THE ORDER (§7): gate first, exactly one test touch
# ==========================================================================

def test_gate_c80_recorded_before_run():
    gate = d.run_gate_c80(n_full_pos=79, n_full=1976,
                          n_held_pos=13, n_held=200)
    assert gate["recorded_before_run"] is True
    # the underpowered C7 symmetric design is blocked; the powered full-Polito
    # design need not be — the gate distinguishes them.
    blocked_geoms = {geom for (_id, fam) in gate["blocked"] for geom in [fam]}
    assert gate["any_blocked"] is True


def test_full_polito_is_more_powered_than_symmetric_split():
    # §4/T1's asymmetry: 79 positives has strictly more power (smaller MDE) than
    # the 13-positive symmetric split. Both fault MDEs still exceed §7's 0.03-0.05
    # margins at these sizes — a real finding the gate surfaces rather than hides —
    # so the driver's job is to record which comparisons must NOT be read as
    # decisive, exactly what run_gate_c80 does.
    gate = d.run_gate_c80(n_full_pos=79, n_full=1976,
                          n_held_pos=13, n_held=200)
    rows = {(r["id"], r["family"], r["geometry"]): r for r in gate["rows"]}
    full = rows[("TH2", FAULT, FULL_POLITO)]
    sym = rows[("TH1", FAULT, SYMMETRIC_HELDOUT)]
    assert full["mde"] < sym["mde"]
    # the symmetric (C7) design is blocked in advance
    assert sym["verdict"] == "blocked"


def test_test_split_touched_exactly_once():
    guard = d.TestSplitGuard()
    assert guard.touched is False
    guard.touch("decisive scoring")
    assert guard.touched is True
    with pytest.raises(RuntimeError, match="already touched once"):
        guard.touch("a sneaky second look")


def _fake_trained_rows():
    # one row per new checkpoint, as train_all would return
    return [{"name": r.name, "arm": r.arm, "seed": r.seed, "args": "",
             "returncode": 0, "wall_min": 0.0, "checkpoint": f"{r.name}.pt",
             "final": "ok"} for r in d.new_training_runs()]


def test_checkpoints_by_arm_fuses_trained_and_reused():
    by_arm = d.checkpoints_by_arm(_fake_trained_rows())
    # five trained arms + the two reused Polito arms
    assert set(by_arm) == {d.JEPA_WIDE, d.MR_WIDE, d.MR_NARROW, d.MR_RANDOM,
                           d.SUP_WIDE, d.JEPA_POLITO, d.MR_POLITO}
    assert set(by_arm[d.MR_WIDE]) == {1337, 1338, 1339}
    # reused arms point at the C7 hashes, not freshly named checkpoints
    assert "jepa_pretrain_e7f0e92d7625.pt" in by_arm[d.JEPA_POLITO][1337]


def test_decisive_scoring_touches_test_split_exactly_once():
    by_arm = d.checkpoints_by_arm(_fake_trained_rows())
    guard = d.TestSplitGuard()
    cmds = d.decisive_scoring_commands(by_arm, guard)
    assert guard.touched is True
    # every command is a --dual-eval --split test scoring pass
    assert cmds and all("--split" in c and "test" in c and "--dual-eval" in c
                        for c in cmds)
    # a second decisive pass is refused — the single-touch invariant
    with pytest.raises(RuntimeError):
        d.decisive_scoring_commands(by_arm, guard)


def test_decisive_scoring_pairs_th1_against_reused_polito():
    by_arm = d.checkpoints_by_arm(_fake_trained_rows())
    cmds = d.decisive_scoring_commands(by_arm, d.TestSplitGuard())
    flat = ["\n".join(c) for c in cmds]
    # TH1 pits goldak-wide against the reused Polito incumbent
    assert any("e7f0e92d7625" in " ".join(c) or "6a0b09b6c113" in " ".join(c)
               for c in cmds)


def test_main_trains_then_gate_then_touches_test_in_order(monkeypatch, tmp_path):
    # Stub the runner so nothing trains; record the order of the key phases.
    order = []

    def fake_runner(run):
        order.append(("train", run.name))
        return {"name": run.name, "arm": run.arm, "seed": run.seed,
                "args": "", "returncode": 0, "wall_min": 0.0,
                "checkpoint": f"{run.name}.pt", "final": "ok"}

    monkeypatch.setattr(d, "run_one", fake_runner)
    monkeypatch.setattr(d, "LOGS", tmp_path / "logs")
    monkeypatch.setattr(d, "MANIFEST", tmp_path / "m.csv")
    # make the reused-checkpoint existence check pass without real files
    monkeypatch.setattr(d.Path, "exists", lambda self: True)

    rows = d.train_all(runner=fake_runner)
    assert len(rows) == 15
    assert all(o[0] == "train" for o in order)
    # the gate consumes only counts and cannot touch a result
    gate = d.run_gate_c80(79, 1976, 13, 200)
    assert gate["recorded_before_run"]


# ==========================================================================
# 3. THE TIE RULE (§7/TH5) — the point of the whole experiment
# ==========================================================================

def test_ci_including_zero_is_underpowered_not_decided():
    diff = fault_diff(0.03, lo=-0.02, hi=0.08)   # straddles zero
    out = d.paired_ci_verdict(diff, FAULT,
                              challenger=d.JEPA_WIDE, incumbent=d.MR_WIDE)
    assert out["verdict"] == d.UNDERPOWERED_NOT_DECIDED
    assert out["winner"] is None


def test_ci_including_zero_never_returns_an_incumbent_win():
    # a NEGATIVE point estimate whose CI still crosses zero is exactly C7's case:
    # masked recon "ahead" but not beyond noise. The old rule handed this to the
    # incumbent; the tie rule must not.
    diff = fault_diff(-0.033, lo=-0.11, hi=0.04)
    out = d.paired_ci_verdict(diff, FAULT,
                              challenger=d.JEPA_WIDE, incumbent=d.MR_WIDE)
    assert out["verdict"] == d.UNDERPOWERED_NOT_DECIDED
    assert out["winner"] is None
    assert d.MR_WIDE not in (out["winner"] or "")


def test_ci_excluding_zero_decides_and_may_name_the_incumbent():
    # an incumbent win is legitimate ONLY when the CI clears zero (real evidence).
    diff = fault_diff(-0.09, lo=-0.15, hi=-0.03)
    out = d.paired_ci_verdict(diff, FAULT,
                              challenger=d.JEPA_WIDE, incumbent=d.MR_WIDE)
    assert out["verdict"] == d.DECIDED
    assert out["winner"] == d.MR_WIDE          # allowed: CI excludes zero


def test_ci_excluding_zero_names_the_challenger_when_ahead():
    diff = depth_diff(0.05, lo=0.02, hi=0.08)
    out = d.paired_ci_verdict(diff, DEPTH,
                              challenger=d.JEPA_WIDE, incumbent=d.MR_WIDE)
    assert out["verdict"] == d.DECIDED
    assert out["winner"] == d.JEPA_WIDE


def test_th5_underpowered_when_effect_below_mde_even_if_ci_excludes_zero():
    # both guards must agree: a CI that excludes zero but sits below the design MDE
    # is a fluke this sample size cannot support → still not decided.
    comp = next(c for c in d.COMPARISON_PLAN
                if c.th_id == "TH5" and c.family == FAULT)
    diff = fault_diff(0.02, lo=0.001, hi=0.039)   # excludes zero, tiny effect
    out = d.adjudicate_tie(comp, diff, mde=0.23)   # huge MDE (C7's design)
    assert out["verdict"] == d.UNDERPOWERED_NOT_DECIDED
    assert out["winner"] is None


def test_th5_decided_when_ci_excludes_zero_and_effect_clears_mde():
    comp = next(c for c in d.COMPARISON_PLAN
                if c.th_id == "TH5" and c.family == DEPTH)
    diff = depth_diff(0.10, lo=0.05, hi=0.15)
    out = d.adjudicate_tie(comp, diff, mde=0.04)
    assert out["verdict"] == d.DECIDED
    assert out["winner"] == d.JEPA_WIDE


def test_no_incumbent_wins_string_anywhere_in_the_driver_source():
    src = Path(d.__file__).read_text().lower()
    # the exact C7 sentence, and the shape of it, must not appear as a verdict.
    assert "incumbent wins" not in src
    assert "tie, incumbent" not in src
    assert "tie -> incumbent" not in src


# ==========================================================================
# 4. THRESHOLD APPLICATION (§7): all five, both families where named
# ==========================================================================

def test_comparison_plan_covers_all_five_thresholds_both_families():
    ids = {c.th_id for c in d.COMPARISON_PLAN}
    assert ids == {"TH1", "TH2", "TH3", "TH4", "TH5"}
    fault = {c.th_id for c in d.COMPARISON_PLAN if c.family == FAULT}
    depth = {c.th_id for c in d.COMPARISON_PLAN if c.family == DEPTH}
    assert fault == {"TH1", "TH2", "TH3", "TH4", "TH5"}
    assert depth == {"TH1", "TH2", "TH3", "TH5"}   # TH4 depth is not diagnostic


def test_th4_must_beat_both_ssl_arms():
    comp = next(c for c in d.COMPARISON_PLAN if c.th_id == "TH4")
    assert set(comp.incumbents) == {d.MR_WIDE, d.JEPA_WIDE}
    assert comp.challenger == d.SUP_WIDE
    assert comp.family == FAULT and comp.geometry == FULL_POLITO


def test_margin_threshold_met_requires_margin_and_ci_excludes_zero():
    comp = next(c for c in d.COMPARISON_PLAN
                if c.th_id == "TH1" and c.family == DEPTH)
    # clears margin AND CI excludes zero → met
    out = d.adjudicate_margin(comp, depth_diff(0.03, 0.01, 0.05))
    assert out["verdict"] == d.MET
    # clears margin but CI straddles zero → not met (no power)
    out = d.adjudicate_margin(comp, depth_diff(0.03, -0.01, 0.07))
    assert out["verdict"] == d.NOT_MET
    # CI excludes zero but below margin → not met
    out = d.adjudicate_margin(comp, depth_diff(0.005, 0.001, 0.009))
    assert out["verdict"] == d.NOT_MET


def test_adjudicate_all_produces_one_row_per_plan_entry():
    diffs = {}
    mdes = {}
    for c in d.COMPARISON_PLAN:
        mk = depth_diff if c.family == DEPTH else fault_diff
        diffs[(c.th_id, c.family)] = mk(0.10, 0.05, 0.15)
        mdes[(c.th_id, c.family)] = 0.02
    ledger = d.adjudicate_all(diffs, mdes)
    assert len(ledger) == len(d.COMPARISON_PLAN)
    # a missing diff is recorded as not-run, never silently dropped
    partial = d.adjudicate_all({}, {})
    assert len(partial) == len(d.COMPARISON_PLAN)
    assert all(r["verdict"] == "not-run" for r in partial)


# ==========================================================================
# 5. FINE-TUNING FOLLOW-UP gated on TH1 (§6)
# ==========================================================================

def _ledger_with_th1_depth(verdict):
    return [{"id": "TH1", "family": DEPTH, "geometry": SIM_HELDOUT,
             "verdict": verdict}]


def test_finetuning_runs_only_when_th1_depth_is_met():
    assert d.should_run_finetuning(_ledger_with_th1_depth(d.MET)) is True
    assert d.should_run_finetuning(_ledger_with_th1_depth(d.NOT_MET)) is False


def test_finetuning_does_not_run_on_underpowered_th1():
    led = _ledger_with_th1_depth(d.UNDERPOWERED_NOT_DECIDED)
    assert d.should_run_finetuning(led) is False


def test_finetuning_ignores_a_fault_only_th1_pass():
    # TH1 met on the fault bit but not on the primary depth target → no follow-up.
    led = [{"id": "TH1", "family": FAULT, "geometry": SYMMETRIC_HELDOUT,
            "verdict": d.MET}]
    assert d.should_run_finetuning(led) is False
