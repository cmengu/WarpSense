"""
test_c8_power_gate.py — Gate C8-0, the power precheck in eval/power_gate.py.

What these tests defend. C7's failure was not a wrong number; it was running a
comparison whose data could not have produced a right one, and adjudicating it
anyway. Ticket #26 moves the power check UPSTREAM of the experiment: before any
decisive comparison, the MDE of each evaluation design is held up against the
pre-registered §7 threshold judged on it, and any threshold below its MDE is
declared underpowered in advance. The tests are organised around the four
properties that inversion must have:

  1. It is CORRECT on designs whose power is known. A tiny-n symmetric split must
     block its thresholds; a large-n design must not block by size alone. The MDEs
     come from the ticket-#20 metric layer, so a test that fixes n fixes the answer.
  2. It maps every §7 threshold to the RIGHT design. Depth thresholds are judged on
     the simulated set, fault-bit thresholds on Polito, and TH1's fault claim on
     the symmetric split while TH2-TH4 sit on full Polito — the two-family, two-
     geometry structure §7 wrote the table in.
  3. It is RECORDED BEFORE the run. The gate consumes only sample sizes and pilot
     MDEs, never a decisive result, so it cannot depend on the run it gates.
  4. It REPRODUCES the C7 finding. Fed C7's own design (13 positives on the held-out
     split), the gate blocks the fault-bit comparison and — via the CI-excludes-0
     adjudication — returns "underpowered — not decided" for the JEPA-vs-recon tie
     C7 called for the incumbent.

Designs are built from explicit sample sizes wherever the MDE's value is the thing
under test — a test of the gate's logic should not depend on a bootstrap. The MDE
functions themselves are tested in test_c8_probe_metrics.py; here they are trusted.
"""

import numpy as np
import pytest

from world_model.eval.compare_pretrains import mde_auc, mde_mae
from world_model.eval.power_gate import (
    BLOCKED, CONDITIONAL, DEPTH, FAULT, FULL_POLITO, NO_DESIGN, POWERED,
    PREREGISTERED_THRESHOLDS, SIM_HELDOUT, SYMMETRIC_HELDOUT,
    adjudicate_ci_threshold, c7_design, depth_design, design_from_report,
    fault_design, format_power_gate, gate_threshold, is_blocked, power_gate)


# --------------------------------------------------------------------------
# The threshold registry matches §7 exactly.
# --------------------------------------------------------------------------

def test_registry_covers_th1_through_th5_in_both_families():
    ids = {t.id for t in PREREGISTERED_THRESHOLDS}
    assert ids == {"TH1", "TH2", "TH3", "TH4", "TH5"}
    # every threshold has a fault-bit entry; TH4 alone has no depth entry
    fault = {t.id for t in PREREGISTERED_THRESHOLDS if t.family == FAULT}
    depth = {t.id for t in PREREGISTERED_THRESHOLDS if t.family == DEPTH}
    assert fault == {"TH1", "TH2", "TH3", "TH4", "TH5"}
    assert depth == {"TH1", "TH2", "TH3", "TH5"}      # TH4 depth is not diagnostic


def test_th5_carries_no_numeric_margin():
    th5 = [t for t in PREREGISTERED_THRESHOLDS if t.id == "TH5"]
    assert all(t.value is None for t in th5)          # "CI excludes 0", not a margin


def test_geometry_assignment_follows_section_4_asymmetry():
    by = {(t.id, t.family): t for t in PREREGISTERED_THRESHOLDS}
    # TH1's fault claim is the symmetric incumbent-vs-sim comparison (11-13 pos)
    assert by[("TH1", FAULT)].geometry == SYMMETRIC_HELDOUT
    # TH2-TH4 fault claims are the powered full-Polito design (79 pos)
    assert by[("TH2", FAULT)].geometry == FULL_POLITO
    assert by[("TH3", FAULT)].geometry == FULL_POLITO
    assert by[("TH4", FAULT)].geometry == FULL_POLITO
    # every depth threshold is judged on the simulated set
    assert all(t.geometry == SIM_HELDOUT
               for t in PREREGISTERED_THRESHOLDS if t.family == DEPTH)


# --------------------------------------------------------------------------
# gate_threshold: the three verdicts, on designs whose power is known.
# --------------------------------------------------------------------------

def test_threshold_below_mde_is_blocked():
    # 13 positives → MDE ~0.23; TH1's 0.05 fault margin sits far below it
    d = fault_design(SYMMETRIC_HELDOUT, n_pos=13, n_neg=187)
    spec = next(t for t in PREREGISTERED_THRESHOLDS
                if t.id == "TH1" and t.family == FAULT)
    row = gate_threshold(spec, {(FAULT, SYMMETRIC_HELDOUT): d})
    assert row["verdict"] == BLOCKED
    assert row["threshold"] < row["mde"]


def test_threshold_at_or_above_mde_is_powered():
    # a design whose MDE we drive below the threshold by hand
    d = fault_design("big", n_pos=800, n_neg=8000)
    assert d.mde < 0.05           # sanity: this large design can detect 0.05
    from world_model.eval.power_gate import ThresholdSpec
    spec = ThresholdSpec("THX", FAULT, "big", 0.05, "synthetic")
    row = gate_threshold(spec, {(FAULT, "big"): d})
    assert row["verdict"] == POWERED
    assert row["threshold"] >= row["mde"]


def test_ci_excludes_zero_threshold_is_conditional_not_blocked():
    d = fault_design(SYMMETRIC_HELDOUT, n_pos=13, n_neg=187)
    spec = next(t for t in PREREGISTERED_THRESHOLDS
                if t.id == "TH5" and t.family == FAULT)
    row = gate_threshold(spec, {(FAULT, SYMMETRIC_HELDOUT): d})
    assert row["verdict"] == CONDITIONAL
    assert row["mde"] == pytest.approx(d.mde)         # MDE carried forward


def test_missing_design_is_recorded_not_silently_passed():
    spec = next(t for t in PREREGISTERED_THRESHOLDS
                if t.id == "TH4" and t.family == FAULT)
    row = gate_threshold(spec, {})                    # no design supplied
    assert row["verdict"] == NO_DESIGN
    assert row["mde"] is None


def test_non_finite_mde_blocks():
    # a degenerate design (no positives) yields a nan MDE and must block, not pass
    d = fault_design("degenerate", n_pos=0, n_neg=200)
    assert not np.isfinite(d.mde)
    from world_model.eval.power_gate import ThresholdSpec
    spec = ThresholdSpec("THX", FAULT, "degenerate", 0.05, "synthetic")
    row = gate_threshold(spec, {(FAULT, "degenerate"): d})
    assert row["verdict"] == BLOCKED


# --------------------------------------------------------------------------
# power_gate: the full ledger over the real registry.
# --------------------------------------------------------------------------

def _c8_designs(depth_n=400, depth_sd=0.3, seed=0):
    """The three C8 designs at their planned sizes, for a full-gate test."""
    rng = np.random.default_rng(seed)
    abs_err = np.abs(rng.normal(0, depth_sd, size=depth_n))
    return [
        fault_design(FULL_POLITO, n_pos=79, n_neg=1976 - 79),
        fault_design(SYMMETRIC_HELDOUT, n_pos=13, n_neg=187),
        depth_design(SIM_HELDOUT, abs_errors=abs_err),
    ]


def test_full_gate_partitions_every_threshold():
    gate = power_gate(_c8_designs())
    # every registry row lands in exactly one verdict bucket
    total = (len(gate["blocked"]) + len(gate["powered"])
             + len(gate["conditional"]) + len(gate["missing"]))
    assert total == len(PREREGISTERED_THRESHOLDS)
    assert len(gate["rows"]) == len(PREREGISTERED_THRESHOLDS)


def test_full_gate_blocks_the_symmetric_fault_comparison():
    gate = power_gate(_c8_designs())
    assert gate["any_blocked"]
    # TH1's fault claim on the symmetric split is the canonical underpowered one
    assert is_blocked(gate, "TH1", FAULT)


def test_full_polito_is_more_powered_than_symmetric_split():
    # the whole point of §4/T1's asymmetry: 79 positives beats 13
    mde_full = mde_auc(79, 1976 - 79)
    mde_sym = mde_auc(13, 187)
    assert mde_full < mde_sym


def test_gate_is_recorded_before_the_run_flag():
    gate = power_gate(_c8_designs())
    assert gate["recorded_before_run"] is True


def test_gate_consumes_only_designs_not_results():
    # power_gate's signature takes designs (sizes/MDEs), never a scored report —
    # the structural guarantee that it runs before the decisive comparison.
    import inspect
    params = list(inspect.signature(power_gate).parameters)
    assert params == ["designs", "thresholds"]


# --------------------------------------------------------------------------
# design_from_report: consuming a ticket-#20 report's MDE unchanged.
# --------------------------------------------------------------------------

def test_design_from_binary_report_reads_mde_auc():
    report = {"target": "binary", "mde_auc": 0.0945, "n": 1976,
              "n_pos": 79, "n_neg": 1897}
    d = design_from_report(report, FULL_POLITO)
    assert d.family == FAULT
    assert d.mde == pytest.approx(0.0945)
    assert d.n_pos == 79


def test_design_from_continuous_report_reads_mde_mae():
    report = {"target": "continuous", "mde_mae": 0.025, "n": 400}
    d = design_from_report(report, SIM_HELDOUT)
    assert d.family == DEPTH
    assert d.mde == pytest.approx(0.025)
    assert d.n == 400


def test_depth_design_requires_exactly_one_of_abs_errors_or_mde():
    with pytest.raises(ValueError):
        depth_design(SIM_HELDOUT)                       # neither
    with pytest.raises(ValueError):
        depth_design(SIM_HELDOUT, abs_errors=[0.1, 0.2], mde=0.03)  # both
    with pytest.raises(ValueError):
        depth_design(SIM_HELDOUT, mde=0.03)             # mde without n


# --------------------------------------------------------------------------
# The C7 reproduction — the acceptance criterion of the ticket.
# --------------------------------------------------------------------------

def test_c7_design_reproduces_underpowered_finding():
    # C7 ranked encoders on the held-out Polito split (13 positives). Fed to the
    # gate, that design blocks the fault-bit comparison it was judged on.
    gate = power_gate([c7_design()])
    assert gate["any_blocked"]
    # TH1's fault margin (0.05) is blocked; the design's MDE dwarfs it
    assert is_blocked(gate, "TH1", FAULT)
    blocked_row = next(r for r in gate["rows"]
                       if r["id"] == "TH1" and r["family"] == FAULT)
    assert blocked_row["mde"] > 0.2          # ~0.23 at 13 positives
    assert blocked_row["threshold"] == 0.05


def test_c7_jepa_vs_recon_tie_is_not_decided():
    # C7's specific mistake: a JEPA-vs-recon margin of ~+0.033 called a tie for the
    # incumbent. Against the design's MDE (~0.23) that effect is undetectable, so
    # the honest verdict is "underpowered — not decided", never "incumbent wins".
    design = c7_design()
    c7_observed_margin = 0.033               # the margin C7 actually adjudicated
    verdict = adjudicate_ci_threshold(design.mde, c7_observed_margin)
    assert verdict["decided"] is False
    assert verdict["verdict"] == "underpowered — not decided"


def test_ci_adjudication_decides_when_effect_clears_mde():
    # the other branch: a real effect at least as large as the MDE is decidable
    design = c7_design()
    verdict = adjudicate_ci_threshold(design.mde, design.mde + 0.01)
    assert verdict["decided"] is True
    assert "read the paired CI" in verdict["verdict"]


# --------------------------------------------------------------------------
# The rendered block carries the finding onto the page.
# --------------------------------------------------------------------------

def test_format_names_blocked_comparisons():
    text = format_power_gate(power_gate(_c8_designs()))
    assert "Gate C8-0" in text
    assert "BEFORE the decisive run" in text
    assert "BLOCKED IN ADVANCE" in text
    assert "TH1/fault" in text                         # the symmetric-split block


def test_format_handles_all_powered_without_a_block_section():
    # a design large enough to power every numeric threshold prints no block
    huge = [fault_design(FULL_POLITO, n_pos=5000, n_neg=50000),
            fault_design(SYMMETRIC_HELDOUT, n_pos=5000, n_neg=50000),
            depth_design(SIM_HELDOUT, mde=0.001, n=100000)]
    gate = power_gate(huge)
    assert not gate["any_blocked"]
    assert "BLOCKED IN ADVANCE" not in format_power_gate(gate)
