"""
power_gate.py — Gate C8-0: the power precheck that runs BEFORE the decisive run.

For newcomers — what this gate is and why it exists at all:
  C7 did not get the wrong answer so much as ask a question its data could not
  answer, and then answer it anyway. Its real-domain ranking rested on 11-13
  positive welds; at that size the smallest AUC gap the comparison could reliably
  tell apart from chance was roughly a quarter of an AUC point, and the effects it
  was adjudicating were a tenth of that. The evidence to decide never existed, and
  nobody checked before spending the compute — the under-powered warning was
  printed, and the verdict issued over it.

  The structural fix is not a better statistic AFTER the run; it is a check BEFORE
  it. This module is that check. It takes each evaluation design C8 will use, asks
  the metric layer (ticket #20) for that design's MINIMUM DETECTABLE EFFECT — the
  smallest true effect the design has an 80% chance of calling significant at the
  95% level — and holds it up against the pre-registered §7 threshold that will be
  judged on that design. If a threshold sits BELOW its design's MDE, the design
  cannot detect the very effect the threshold demands: that comparison is declared
  UNDERPOWERED IN ADVANCE and must not be run as a decisive test. The verdict is
  recorded here, before the run, rather than reconstructed afterward — which is the
  one thing C7 could not do.

Why the MDE, not a post-hoc CI:
  A confidence interval tells you how precisely you measured AFTER you measured;
  the MDE tells you, from the design's sample sizes alone, what you could ever have
  hoped to measure. `mde_auc(n_pos, n_neg)` needs only the two class counts, and
  those are known from the session metadata before a single embedding is computed —
  so the fault-bit designs can be pre-checked with no run at all. The depth (ΔMAE)
  design's MDE needs a scale for the per-weld errors, which a pilot run supplies;
  that number is consumed here through `design_from_report`, never recomputed.

Two metric families, three geometries (spec §7 + §4/T1):
  §7 states every threshold in TWO families — ΔMAE for the continuous fusion-depth
  primary target (scored on the simulated set), and ΔAUC for the binary Polito
  fault bit (the real-domain secondary check). The fault-bit family further splits
  by evaluation GEOMETRY, because §4/T1's deliberate asymmetry gives two different
  designs with two very different powers:

    - "full-polito"        — sim-trained arms and the floor, scored on all 1,976
                             Polito welds (79 positives). The powered real-domain
                             design; TH2/TH3/TH4 are judged here.
    - "symmetric-heldout"  — the incumbent-vs-simulator comparison, where the
                             incumbent's leakage forces both arms onto the held-out
                             split (11-13 positives). The weakest design in the
                             spec; TH1 and the TH5 fault-bit tie are judged here.
                             This is C7's design, and `c7_design()` reproduces it.
    - "sim-heldout"        — the held-out simulated set, on which every depth (ΔMAE)
                             threshold is judged.

  A threshold judged on more than one family (TH1-TH3, TH5) is checked once per
  family, because a comparison can be adequately powered on depth and hopelessly
  under-powered on the fault bit at the same time — exactly the situation §7's
  two-family table was written to expose.

The one CI-excludes-0 subtlety (TH5):
  TH5 does not name a numeric margin; it asks only that the paired CI exclude zero.
  There is therefore no fixed number to compare against the MDE in advance, and —
  this is the whole point of TH5's phrasing — a CI-excludes-0 comparison can only
  ever resolve for a true effect at least as large as the design's MDE. So TH5 is
  never pre-cleared as "adequately powered"; it is recorded as CONDITIONAL, its MDE
  carried forward, and adjudicated only against the observed effect after the run
  by `adjudicate_ci_threshold`. When that observed effect falls below the MDE the
  verdict is the exact sentence C7 refused to print: "underpowered — not decided",
  NOT "tie, incumbent wins".

CLI note: this module is imported by `eval/compare_pretrains.py`, whose
`--dual-eval` path prints the gate before it scores anything. Nothing here runs on
a C4-C7 reproduction; the gate is C8 behaviour behind the C8 path only.
"""

from dataclasses import dataclass

import numpy as np

from world_model.eval.compare_pretrains import mde_auc, mde_mae

# The three evaluation geometries §4/T1 and §7 define, named once here so a
# threshold and the design it is judged on cannot drift apart by a typo.
SIM_HELDOUT = "sim-heldout"            # depth (ΔMAE), the simulated primary target
FULL_POLITO = "full-polito"           # fault bit (ΔAUC), 79 positives — powered
SYMMETRIC_HELDOUT = "symmetric-heldout"  # fault bit (ΔAUC), 11-13 positives — C7

DEPTH = "depth"
FAULT = "fault"


@dataclass(frozen=True)
class ThresholdSpec:
    """
    One row of the §7 table, split per metric family it is judged on.

    A single claim (TH1) can appear twice — once for depth on `sim-heldout`, once
    for the fault bit on `symmetric-heldout` — because §7 states it in both
    families and the two are powered independently. `value` is the pre-registered
    numeric margin, or None for TH5's "CI excludes 0", which names no margin and is
    handled as a conditional rather than a fixed comparison.
    """
    id: str
    family: str        # DEPTH or FAULT
    geometry: str       # one of the three geometry constants
    value: float | None  # numeric margin, or None for "CI excludes 0" (TH5)
    claim: str


# The pre-registered thresholds, verbatim from §7's table, one entry per
# (threshold, metric family). Depth margins are ΔMAE in symlog-mm; fault margins
# are paired ΔAUC. TH4 has no depth entry ("supervised-wins-on-depth is expected
# and not diagnostic"); TH5 carries None in both families ("CI excludes 0").
PREREGISTERED_THRESHOLDS: list[ThresholdSpec] = [
    ThresholdSpec("TH1", DEPTH, SIM_HELDOUT, 0.02,
                  "Simulator corpus beats Polito corpus"),
    ThresholdSpec("TH1", FAULT, SYMMETRIC_HELDOUT, 0.05,
                  "Simulator corpus beats Polito corpus (symmetric evaluation)"),
    ThresholdSpec("TH2", DEPTH, SIM_HELDOUT, 0.01,
                  "The win is fidelity, not volume"),
    ThresholdSpec("TH2", FAULT, FULL_POLITO, 0.03,
                  "The win is fidelity, not volume"),
    ThresholdSpec("TH3", DEPTH, SIM_HELDOUT, 0.01,
                  "Ranges were binding"),
    ThresholdSpec("TH3", FAULT, FULL_POLITO, 0.03,
                  "Ranges were binding"),
    ThresholdSpec("TH4", FAULT, FULL_POLITO, 0.05,
                  "SSL framing is obsolete (supervised beats both SSL arms)"),
    ThresholdSpec("TH5", DEPTH, SIM_HELDOUT, None,
                  "JEPA vs masked recon (paired CI excludes 0)"),
    ThresholdSpec("TH5", FAULT, SYMMETRIC_HELDOUT, None,
                  "JEPA vs masked recon (paired CI excludes 0)"),
]


@dataclass(frozen=True)
class EvaluationDesign:
    """
    One evaluation design and the power it has, computed BEFORE the decisive run.

    `mde` is the design's minimum detectable effect in the units of its family
    (ΔAUC for a fault design, ΔMAE in symlog-mm for a depth design). `n` is the
    number of welds; `n_pos`/`n_neg` are the class counts a fault design's MDE was
    built from and are None for a depth design. Construct via `fault_design` /
    `depth_design` (or `design_from_report`) rather than by hand, so the MDE always
    comes from the ticket-#20 metric layer and never from a re-derivation.
    """
    geometry: str
    family: str
    mde: float
    n: int
    n_pos: int | None = None
    n_neg: int | None = None


def fault_design(geometry: str, n_pos: int, n_neg: int,
                 r: float = 0.5) -> EvaluationDesign:
    """
    A fault-bit (ΔAUC) design from its two class counts alone — the fully a-priori
    case. `mde_auc` needs only `n_pos`, `n_neg` and the between-arm score
    correlation `r` (0.5, the conservative default two arms sharing an encoder
    family exceed), so this can be built from session metadata before any probe is
    fitted. That is what lets the fault-bit half of Gate C8-0 run with zero compute.
    """
    return EvaluationDesign(geometry, FAULT, mde_auc(n_pos, n_neg, r=r),
                            n=n_pos + n_neg, n_pos=n_pos, n_neg=n_neg)


def depth_design(geometry: str, *, abs_errors=None, mde: float | None = None,
                 n: int | None = None, r: float = 0.5) -> EvaluationDesign:
    """
    A depth (ΔMAE) design. Its MDE needs a scale for the per-weld errors, which is
    the one number that cannot be known before a run, so this takes EITHER a pilot
    run's absolute errors (and computes the MDE via `mde_mae`) OR an MDE already
    computed by the metric layer (the `design_from_report` path). Exactly one of
    `abs_errors` / `mde` must be given.
    """
    if (abs_errors is None) == (mde is None):
        raise ValueError("depth_design needs exactly one of abs_errors or mde")
    if abs_errors is not None:
        e = np.asarray(abs_errors, dtype=float)
        return EvaluationDesign(geometry, DEPTH, mde_mae(e, r=r), n=len(e))
    if n is None:
        raise ValueError("depth_design(mde=...) also needs n (the weld count)")
    return EvaluationDesign(geometry, DEPTH, float(mde), n=int(n))


def design_from_report(report: dict, geometry: str) -> EvaluationDesign:
    """
    Lift a design out of a `rich_report` (ticket #20) — the seam by which the gate
    consumes an MDE the metric layer already computed rather than recomputing one.

    A binary report carries `mde_auc` and its class counts; a continuous report
    carries `mde_mae` and its weld count. Both are read straight off the report, so
    the number the gate checks is byte-identical to the number the report printed.
    """
    if report["target"] == "binary":
        return EvaluationDesign(geometry, FAULT, float(report["mde_auc"]),
                                n=int(report["n"]),
                                n_pos=int(report.get("n_pos", 0)),
                                n_neg=int(report.get("n_neg", 0)))
    return EvaluationDesign(geometry, DEPTH, float(report["mde_mae"]),
                            n=int(report["n"]))


# Verdict strings, named once so callers compare against a constant rather than a
# spelling. "blocked" is the decisive one: it means the comparison must not run.
POWERED = "powered"          # threshold >= MDE: the design can detect it
BLOCKED = "blocked"          # threshold < MDE: underpowered in advance, do not run
CONDITIONAL = "conditional"  # CI-excludes-0 (TH5): decide only against observed effect
NO_DESIGN = "no-design"      # the design this threshold needs was not supplied


def gate_threshold(spec: ThresholdSpec,
                   designs: dict[tuple[str, str], EvaluationDesign]) -> dict:
    """
    Adjudicate ONE (threshold, family) against the design it is judged on.

    `designs` is keyed by (family, geometry). Three outcomes, per the module
    docstring: a numeric threshold below its design's MDE is BLOCKED (the C7
    failure, caught in advance); at or above it is POWERED; a None-valued
    threshold (TH5) is CONDITIONAL, carrying its MDE forward for post-run
    adjudication. A threshold whose design was not supplied is NO_DESIGN — recorded
    honestly rather than silently passed.
    """
    design = designs.get((spec.family, spec.geometry))
    metric = "ΔAUC" if spec.family == FAULT else "ΔMAE"
    row = {"id": spec.id, "family": spec.family, "geometry": spec.geometry,
           "claim": spec.claim, "metric": metric, "threshold": spec.value}
    if design is None:
        return {**row, "mde": None, "n": None, "verdict": NO_DESIGN,
                "note": f"no {spec.family}/{spec.geometry} design supplied — "
                        f"cannot pre-check power"}
    mde, n = design.mde, design.n
    row.update({"mde": mde, "n": n})
    if spec.value is None:
        return {**row, "verdict": CONDITIONAL,
                "note": f"CI-excludes-0: decisive only if observed |effect| >= "
                        f"MDE={mde:.4f}; else 'underpowered — not decided'"}
    if not np.isfinite(mde) or spec.value < mde:
        return {**row, "verdict": BLOCKED,
                "note": f"threshold {spec.value:.4f} < MDE {mde:.4f} on n={n}: "
                        f"underpowered in advance — declare exploratory, do NOT "
                        f"run as decisive"}
    return {**row, "verdict": POWERED,
            "note": f"threshold {spec.value:.4f} >= MDE {mde:.4f} on n={n}: "
                    f"adequately powered"}


def power_gate(designs: list[EvaluationDesign],
               thresholds: list[ThresholdSpec] = PREREGISTERED_THRESHOLDS) -> dict:
    """
    Gate C8-0, run over all pre-registered thresholds and all supplied designs.

    Returns the full ledger — one row per (threshold, family) — plus the four
    grouped verdict lists a driver reads before deciding what to run. `blocked` is
    the load-bearing one: any (id, family) in it names a comparison that is
    underpowered in advance and MUST be excluded from the decisive run and declared
    exploratory (§7). `recorded_before_run` is True by construction: this function
    consumes only sample sizes and pilot MDEs, never a decisive result, so calling
    it cannot depend on the run it gates.

    `any_blocked` is surfaced at the top level so the driver's guard is a single
    boolean rather than a length check a caller could forget.
    """
    lookup = {(d.family, d.geometry): d for d in designs}
    rows = [gate_threshold(spec, lookup) for spec in thresholds]
    grouped = {POWERED: [], BLOCKED: [], CONDITIONAL: [], NO_DESIGN: []}
    for r in rows:
        grouped[r["verdict"]].append((r["id"], r["family"]))
    return {
        "rows": rows,
        "blocked": grouped[BLOCKED],
        "powered": grouped[POWERED],
        "conditional": grouped[CONDITIONAL],
        "missing": grouped[NO_DESIGN],
        "any_blocked": len(grouped[BLOCKED]) > 0,
        "recorded_before_run": True,
    }


def is_blocked(gate: dict, threshold_id: str, family: str) -> bool:
    """True when this (threshold, family) comparison was blocked in advance."""
    return (threshold_id, family) in gate["blocked"]


def adjudicate_ci_threshold(mde: float, observed_effect: float) -> dict:
    """
    Resolve a CI-excludes-0 threshold (TH5) AFTER the run, against the effect it
    actually observed — the one place a decision legitimately needs the run.

    This is the sentence C7 got wrong made mechanical: a paired |effect| below the
    design's MDE cannot have produced a CI that excludes zero at this sample size,
    so the honest verdict is "underpowered — not decided", NEVER "tie, incumbent
    wins". At or above the MDE the comparison is decidable and the reported CI
    stands. `decided` is the boolean a driver branches on.
    """
    decided = np.isfinite(mde) and abs(observed_effect) >= mde
    return {
        "mde": float(mde),
        "observed_effect": float(observed_effect),
        "decided": bool(decided),
        "verdict": "decidable — read the paired CI" if decided
        else "underpowered — not decided",
    }


def c7_design() -> EvaluationDesign:
    """
    C7's real-domain evaluation design, rebuilt for the gate to judge in hindsight.

    C7 ranked encoders on the held-out Polito split — 13 positives among ~200 welds
    (§4/T1: "the Polito split carried 11-13 positives, so its ranking was noise").
    Feeding this design to `power_gate` reproduces the finding this whole spec
    exists to name: at 13 positives the ΔAUC MDE is ~0.23, so every fault-bit
    threshold judged on this geometry (TH1's 0.05, and TH5's CI-excludes-0 against
    any effect C7 plausibly saw) sits far below it and is blocked. The comparison
    could not have detected its own threshold, and Gate C8-0 says so up front.
    """
    return fault_design(SYMMETRIC_HELDOUT, n_pos=13, n_neg=187)


def format_power_gate(gate: dict) -> str:
    """
    Render Gate C8-0 as a block printed BEFORE the decisive run.

    The blocked rows are the point: each one names a comparison that will not be
    run as decisive and the number-vs-MDE that disqualified it, in the same
    "a number versus a threshold" form §7/D11 requires everywhere else. A run whose
    gate block is empty of blocks is one where every pre-registered comparison is
    powered — the state C7 was assumed to be in and never checked.
    """
    out = ["Gate C8-0 — power precheck (recorded BEFORE the decisive run)",
           f"{'id':<5} {'family':<6} {'geometry':<18} {'metric':<6} "
           f"{'threshold':>10} {'MDE':>9} {'n':>6}  verdict"]
    for r in gate["rows"]:
        thr = "CI≠0" if r["threshold"] is None else f"{r['threshold']:.4f}"
        mde = "   n/a" if r["mde"] is None else f"{r['mde']:.4f}"
        n = "   n/a" if r["n"] is None else f"{r['n']}"
        out.append(f"{r['id']:<5} {r['family']:<6} {r['geometry']:<18} "
                   f"{r['metric']:<6} {thr:>10} {mde:>9} {n:>6}  "
                   f"{r['verdict'].upper()}")
    if gate["blocked"]:
        names = ", ".join(f"{i}/{f}" for i, f in gate["blocked"])
        out.append(f"\nBLOCKED IN ADVANCE (threshold < MDE): {names}")
        out.append("  These comparisons are underpowered before any compute is "
                   "spent. Declare them exploratory; do NOT run as decisive and "
                   "reinterpret afterward (§7, and the specific C7 mistake).")
    if gate["conditional"]:
        names = ", ".join(f"{i}/{f}" for i, f in gate["conditional"])
        out.append(f"CONDITIONAL (CI-excludes-0, decide against observed effect): "
                   f"{names}")
    if gate["powered"]:
        names = ", ".join(f"{i}/{f}" for i, f in gate["powered"])
        out.append(f"adequately powered: {names}")
    if gate["missing"]:
        names = ", ".join(f"{i}/{f}" for i, f in gate["missing"])
        out.append(f"no design supplied (not pre-checked): {names}")
    return "\n".join(out)
