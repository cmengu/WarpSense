"""
c8_headtohead.py — the C8 decisive-comparison driver (issue #27, spec §6/§7).

For newcomers — what this driver is and the one mistake it exists to not repeat:
  C7 asked whether JEPA beats masked reconstruction, got a paired difference whose
  confidence interval straddled zero, and recorded the verdict "tie, masked recon
  retains the warm-start slot." That sentence looks harmless and is the whole
  reason C8 exists. A CI that includes zero is not evidence of a tie; it is the
  absence of the power needed to call the race at all. C7's tie rule silently
  re-labelled "we could not tell" as an incumbent verdict, and every downstream
  decision inherited a verdict the data never supported.

  This driver runs the same family of comparisons C7 ran, plus the corpus
  questions C8 added, but it is built so that the C7 sentence is unsayable. When a
  paired CI includes zero the verdict is exactly "underpowered — not decided"
  (`UNDERPOWERED_NOT_DECIDED`); there is no code path, and no string anywhere in
  this file, that turns a zero-crossing CI into a default win for the incumbent.
  An incumbent CAN win — but only on a CI that excludes zero, a real result, never
  by default. `paired_ci_verdict` is the single choke point that guarantees this,
  and `test_c8_driver.py` asserts the forbidden branch does not exist.

The run inventory this driver encodes (spec §6):
  NEW checkpoints — 15 total, three seeds (1337/1338/1339) each of five arms:
    - JEPA           on goldak-wide        → primary comparison (TH5)
    - masked recon   on goldak-wide        → primary comparison (TH1/TH5)
    - masked recon   on goldak-narrow      → T3 range detector   (TH3)
    - masked recon   on spectrum-random    → T4 volume control   (TH2)
    - supervised depth on goldak-wide      → T5 SSL-obsolescence  (TH4)
  JEPA runs on goldak-wide ONLY: the corpus questions (T3 ranges, T4 volume) are
  questions about the corpus, so the incumbent objective — masked recon — answers
  them alone. Not training JEPA on narrow/random is the single biggest saving over
  the naive 5-corpus × 3-objective matrix and the reason the estimate is credible.

  REUSED from C7 — no new compute (`reused_c7_checkpoints()`):
    - JEPA-on-Polito         e7f0e92d7625, 0b1928f64c3a, a0af0e76939f
    - masked-recon-on-Polito 6a0b09b6c113, 44889df44347, 1464012e1949
  These are the Polito incumbents TH1 compares the simulator against. They are the
  arms C7 already trained at seeds 1337/1338/1339; retraining them would be both
  waste and a subtle divergence from C7's numbers. The driver references the
  checkpoint files directly and never re-enters a training subprocess for them.

Corpus/seed convention (why seeds pair):
  As in C7, `--seed` is salted into the split hash (data/splits.py), so each seed
  trains and is scored on a DIFFERENT held-out partition. A paired comparison is
  only fair between two arms that saw the SAME partition, so the simulated corpora
  are generated once at a FIXED `CORPUS_SEED` (the dataset is identical across
  arms) and `--seed` varies the split and the model init. The verdict metric is
  then the paired challenger-minus-incumbent difference across the three
  seed-matched partitions — exactly C7's design, minus C7's tie rule.

Order of operations (spec §7, non-negotiable):
  1. Train the 15 new checkpoints; reuse C7's six.
  2. Gate C8-0 FIRST — the power precheck (`run_gate_c80`). It consumes only
     sample sizes and a val-split pilot MDE, never a test result, so it is
     recorded BEFORE any decisive number exists. Any comparison it BLOCKS is
     declared exploratory and is not read as decisive (§7).
  3. Exactly ONE pre-registered touch of the test split (`TestSplitGuard`). The
     guard raises on a second touch, so the "look at test once" rule is enforced
     by construction rather than by discipline.
  4. Apply all five thresholds TH1-TH5 on both metric families where §7 names them
     (`adjudicate_all`), TH5 through the tie rule above.
  5. Fine-tuning follow-up runs ONLY if TH1 clears (`should_run_finetuning`); if
     C8 returns "underpowered — not decided," fine-tuning does not run.

Run from backend/:
  venv/bin/python world_model/experiments/notebook/c8_headtohead.py
Logs land in notebook/logs/c8_<name>.log; manifest in notebook/c8_manifest.csv.

STATUS: this driver is WRITTEN BUT UNEXECUTED. Running it end-to-end trains 15
encoders on ~20k-session simulated corpora and scores 21 checkpoints — compute far
beyond an interactive session (see the estimate in spec §6). The logic below —
matrix construction, the gate-first ordering, the single test touch, and the
threshold/tie adjudication — is what `test_c8_driver.py` exercises with stubs, so
the decision machinery is verified without spending that compute.
"""

import csv
import json
import math
import os
import re
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

from world_model.eval.power_gate import (
    DEPTH, FAULT, FULL_POLITO, SIM_HELDOUT, SYMMETRIC_HELDOUT,
    adjudicate_ci_threshold, fault_design, format_power_gate, power_gate)

# format_power_gate renders Gate C8-0's ledger for gate_status.md (§7 work-item 8);
# the compute-bearing build prints it right after run_gate_c80 returns.
_GATE_RENDERER = format_power_gate

BACKEND = Path(__file__).resolve().parents[3]   # .../backend
NOTEBOOK = Path(__file__).resolve().parent
LOGS = NOTEBOOK / "logs"
MANIFEST = NOTEBOOK / "c8_manifest.csv"
CHECKPOINTS = NOTEBOOK.parent / "checkpoints"

PYTHON = str(BACKEND / "venv" / "bin" / "python")
N_WORKERS = 2
THREADS_PER_WORKER = "4"
# Compute device for every training/scoring subprocess. An env seam rather than a
# CLI flag because TrainRun.cli_args is a frozen property with no argparse in
# reach — and because the ONLY thing that should vary between the laptop dry-run
# and the A100 execution is `C8_DEVICE=cuda`, not the command line the manifest
# records.
DEVICE = os.environ.get("C8_DEVICE", "cpu")

# C8_REHEARSAL=1 executes the WHOLE driver — training, scoring, JSON, pooling,
# adjudication — at toy scale to prove the plumbing before GPU-hours are spent.
# Three deliberate downgrades, and only these: tiny corpora/epochs, two seeds
# instead of three (enough to exercise pooling), and — the load-bearing one —
# scoring on --split val, so the single pre-registered touch of the test split
# is NOT spent on a rehearsal. Every rehearsal output is stamped REHEARSAL and
# must never be read as a C8 number.
REHEARSAL = os.environ.get("C8_REHEARSAL", "") not in ("", "0")

# The three seeds C7 used; every arm is trained once per seed and scored in
# seed-matched pairs (see the module docstring). Rehearsal keeps two so the
# cross-seed pooling is still exercised.
SEEDS: tuple[int, ...] = (1337, 1338) if REHEARSAL else (1337, 1338, 1339)

# The simulated corpora are generated once at this base seed so every arm sees the
# SAME dataset; --seed then varies only the split partition and model init. Session
# i draws seed CORPUS_SEED + i inside the loaders.
CORPUS_SEED = 20260719
# ~20k simulated sessions per corpus (spec §6 item 2 / §4).
N_SESSIONS = 60 if REHEARSAL else 20000
EPOCHS = "3" if REHEARSAL else "30"
# The split the decisive scoring touches. val in rehearsal — the ONE
# pre-registered test look (TestSplitGuard) is not spent on plumbing proof.
SCORING_SPLIT = "val" if REHEARSAL else "test"

# Arm labels — used as dict keys throughout so a comparison names an arm, never a
# raw checkpoint path.
JEPA_WIDE = "jepa_goldak_wide"
MR_WIDE = "mr_goldak_wide"
MR_NARROW = "mr_goldak_narrow"
MR_RANDOM = "mr_random"
SUP_WIDE = "sup_goldak_wide"
JEPA_POLITO = "jepa_polito"      # reused from C7
MR_POLITO = "mr_polito"          # reused from C7

_JEPA = "world_model.pretraining.jepa"
_MR = "world_model.pretraining.masked_recon"
_SUP = "world_model.pretraining.supervised_depth"


@dataclass(frozen=True)
class TrainRun:
    """
    One NEW checkpoint to train — an arm at one seed. `name` is the log/manifest
    key; `module` is the training entry point; `corpus_args` are the §6 corpus
    knobs (identical across the three seeds of an arm, so the corpus is fixed and
    only the split/init seed moves). Reused C7 checkpoints are NEVER expressed as a
    TrainRun — they carry no compute and live in `reused_c7_checkpoints()`.
    """
    name: str
    arm: str
    seed: int
    module: str
    corpus_args: tuple[str, ...]

    @property
    def cli_args(self) -> list[str]:
        """The full extra-arg list handed to the training module."""
        return ["--seed", str(self.seed), "--epochs", EPOCHS,
                "--device", DEVICE,
                "--corpus-seed", str(CORPUS_SEED),
                "--corpus-sessions", str(N_SESSIONS), *self.corpus_args]


# The five NEW arms and the corpus each trains on (spec §6 table). JEPA appears
# ONCE (goldak-wide); masked recon appears three times (wide/narrow/random);
# supervised depth once (wide). This tuple IS the "15 new checkpoints, 3 seeds
# each" claim — expanded per seed by `new_training_runs()`.
_NEW_ARMS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    (JEPA_WIDE, _JEPA, ("--corpus", "goldak", "--corpus-variant", "wide")),
    (MR_WIDE,   _MR,   ("--corpus", "goldak", "--corpus-variant", "wide")),
    (MR_NARROW, _MR,   ("--corpus", "goldak", "--corpus-variant", "narrow")),
    (MR_RANDOM, _MR,   ("--corpus", "random")),
    (SUP_WIDE,  _SUP,  ("--corpus", "goldak", "--corpus-variant", "wide")),
)


def new_training_runs() -> list[TrainRun]:
    """
    The 15 new checkpoints, three seeds per arm (spec §6). Every arm is trained on
    each of `SEEDS`, producing the seed-matched partners the paired comparison
    needs. This function is the executable form of the §6 inventory table, and
    `test_c8_driver.py` pins its shape (15 rows, JEPA on goldak-wide only, etc.).
    """
    runs: list[TrainRun] = []
    for arm, module, corpus_args in _NEW_ARMS:
        for seed in SEEDS:
            runs.append(TrainRun(name=f"{arm}_s{seed}", arm=arm, seed=seed,
                                 module=module, corpus_args=corpus_args))
    return runs


def reused_c7_checkpoints() -> dict[str, dict[int, str]]:
    """
    C7's six Polito checkpoints, reused with NO new compute (spec §6). Keyed
    arm → {seed: checkpoint_path}. These are the Polito incumbents TH1 measures the
    simulator against; they were trained in C7 at seeds 1337/1338/1339 and are
    referenced by file, never retrained. If any file is missing the driver aborts
    before touching the test split rather than silently retraining it.
    """
    jepa = ("e7f0e92d7625", "0b1928f64c3a", "a0af0e76939f")
    mr = ("6a0b09b6c113", "44889df44347", "1464012e1949")
    return {
        JEPA_POLITO: {s: str(CHECKPOINTS / f"jepa_pretrain_{h}.pt")
                      for s, h in zip(SEEDS, jepa)},
        MR_POLITO: {s: str(CHECKPOINTS / f"masked_recon_windows_{h}.pt")
                    for s, h in zip(SEEDS, mr)},
    }


# --------------------------------------------------------------------------
# Threshold plan (spec §7). One Comparison per (threshold, metric family), each
# naming the two arms it pits, the geometry it is judged on, and the pre-registered
# margin. TH5 alone carries `tie_rule=True`; its margin is None ("CI excludes 0").
# --------------------------------------------------------------------------

MET = "met"
NOT_MET = "not-met"
DECIDED = "decided"
# The exact sentence C7 refused to print. Kept as a single constant so no caller
# can spell it differently, and so the tie rule has one canonical output.
UNDERPOWERED_NOT_DECIDED = "underpowered — not decided"


@dataclass(frozen=True)
class Comparison:
    """
    One row of the §7 table for one metric family.

    `challenger` is arm A of the paired difference (positive delta ⇒ A better, the
    sign convention `paired_auc_diff`/`paired_mae_diff` share); `incumbents` is the
    arm(s) A must beat — a tuple because TH4 must beat BOTH SSL arms. `margin` is
    the pre-registered numeric threshold, or None for TH5's CI-excludes-0. `not_met`
    is §7's verbatim "if not met" clause — for a numeric threshold it is a real
    interpretation, NOT a default verdict about the challenger.
    """
    th_id: str
    family: str            # DEPTH or FAULT
    geometry: str
    challenger: str
    incumbents: tuple[str, ...]
    margin: float | None
    not_met: str
    tie_rule: bool = False


# Verbatim from §7's table. Depth margins are ΔMAE improvements (symlog-mm);
# fault margins are paired ΔAUC. TH4 has no depth row (supervised-wins-on-depth is
# expected and not diagnostic); TH5 carries None in both families.
COMPARISON_PLAN: tuple[Comparison, ...] = (
    Comparison("TH1", DEPTH, SIM_HELDOUT, MR_WIDE, (MR_POLITO,), 0.02,
               "no corpus effect detected — Polito keeps the warm-start slot"),
    Comparison("TH1", FAULT, SYMMETRIC_HELDOUT, MR_WIDE, (MR_POLITO,), 0.05,
               "no corpus effect detected — Polito keeps the warm-start slot"),
    Comparison("TH2", DEPTH, SIM_HELDOUT, MR_WIDE, (MR_RANDOM,), 0.01,
               "win attributable to volume; simulator NOT validated"),
    Comparison("TH2", FAULT, FULL_POLITO, MR_WIDE, (MR_RANDOM,), 0.03,
               "win attributable to volume; simulator NOT validated"),
    Comparison("TH3", DEPTH, SIM_HELDOUT, MR_WIDE, (MR_NARROW,), 0.01,
               "ranges not binding at this scale; do not widen further"),
    Comparison("TH3", FAULT, FULL_POLITO, MR_WIDE, (MR_NARROW,), 0.03,
               "ranges not binding at this scale; do not widen further"),
    Comparison("TH4", FAULT, FULL_POLITO, SUP_WIDE, (MR_WIDE, JEPA_WIDE), 0.05,
               "keep SSL; supervised-wins-on-sim-only is the predicted T5 "
               "pattern, not a win"),
    Comparison("TH5", DEPTH, SIM_HELDOUT, JEPA_WIDE, (MR_WIDE,), None,
               UNDERPOWERED_NOT_DECIDED, tie_rule=True),
    Comparison("TH5", FAULT, SYMMETRIC_HELDOUT, JEPA_WIDE, (MR_WIDE,), None,
               UNDERPOWERED_NOT_DECIDED, tie_rule=True),
)


def diff_delta(diff: dict, family: str) -> float:
    """The signed effect (challenger-minus-incumbent) out of a paired-diff report.

    Positive ⇒ challenger better, for BOTH families — `paired_mae_diff` already
    flips ΔMAE so lower-error-is-better reads as a positive delta, matching
    `paired_auc_diff`. Callers therefore never special-case the sign per family.
    """
    return float(diff["delta_mae"] if family == DEPTH else diff["delta_auc"])


def ci_excludes_zero(diff: dict) -> bool:
    """True when the bootstrap CI is wholly on one side of zero (the §7 gate)."""
    return bool(diff["excludes_zero"])


def paired_ci_verdict(diff: dict, family: str, *, challenger: str,
                      incumbent: str) -> dict:
    """
    THE tie rule — the single choke point for every paired verdict in C8.

    There are exactly two outcomes and the C7 sentence is neither of them:
      * CI EXCLUDES zero  → DECIDED. The winner is whichever arm the sign names;
        an incumbent win here is legitimate because it rests on a CI that clears
        zero, i.e. real evidence.
      * CI INCLUDES zero  → UNDERPOWERED_NOT_DECIDED. The comparison had no power
        to call the race, so the honest verdict says so. There is deliberately NO
        branch that returns an incumbent (or "tie") verdict on this path — the old
        C7 behaviour is not merely discouraged, it is unrepresentable here.

    A caller that wants "who won?" must go through this function, so the invariant
    holds for TH5 and for any future paired comparison that reuses it.
    """
    delta = diff_delta(diff, family)
    if not ci_excludes_zero(diff):
        return {"verdict": UNDERPOWERED_NOT_DECIDED, "winner": None,
                "delta": delta,
                "note": "paired CI includes zero — no power to decide; "
                        "NOT a tie and NOT an incumbent win (the C7 mistake)"}
    winner = challenger if delta > 0 else incumbent
    return {"verdict": DECIDED, "winner": winner, "delta": delta,
            "note": f"paired CI excludes zero — {winner} wins on real evidence"}


def adjudicate_margin(comp: Comparison, diff: dict) -> dict:
    """
    A numeric §7 threshold (TH1-TH4): MET requires BOTH the pre-registered margin
    AND a CI excluding zero, exactly as the table states ("Δ ≥ x, CI excludes 0").
    A miss is reported with §7's own "if not met" interpretation — which, unlike
    the tie rule, is a substantive reading ("no corpus effect", "win attributable
    to volume", …), never a silent hand-off to the incumbent.
    """
    delta = diff_delta(diff, comp.family)
    passes = delta >= comp.margin and ci_excludes_zero(diff)
    return {
        "id": comp.th_id, "family": comp.family, "geometry": comp.geometry,
        "metric": "ΔMAE" if comp.family == DEPTH else "ΔAUC",
        "challenger": comp.challenger, "incumbents": list(comp.incumbents),
        "margin": comp.margin, "delta": delta,
        "excludes_zero": ci_excludes_zero(diff),
        "verdict": MET if passes else NOT_MET,
        "note": (f"Δ={delta:+.4f} ≥ margin {comp.margin:.4f} and CI excludes 0"
                 if passes else
                 f"Δ={delta:+.4f} vs margin {comp.margin:.4f}, "
                 f"CI-excludes-0={ci_excludes_zero(diff)} → {comp.not_met}"),
    }


def adjudicate_tie(comp: Comparison, diff: dict, mde: float) -> dict:
    """
    TH5, the CI-excludes-0 comparison, adjudicated through the tie rule AND
    cross-checked against the design's MDE.

    Two guards must both agree the race is callable: the bootstrap CI must exclude
    zero (`paired_ci_verdict`), and the observed |effect| must reach the design's
    minimum detectable effect (`adjudicate_ci_threshold` — a CI that excludes zero
    below the MDE would be a fluke this sample size cannot support). If either says
    "cannot decide," the verdict is UNDERPOWERED_NOT_DECIDED. This is TH5's whole
    point, so it routes through the same choke point every other paired verdict does.
    """
    ci = paired_ci_verdict(diff, comp.family, challenger=comp.challenger,
                           incumbent=comp.incumbents[0])
    power = adjudicate_ci_threshold(mde, diff_delta(diff, comp.family))
    decided = ci["verdict"] == DECIDED and power["decided"]
    return {
        "id": comp.th_id, "family": comp.family, "geometry": comp.geometry,
        "metric": "ΔMAE" if comp.family == DEPTH else "ΔAUC",
        "challenger": comp.challenger, "incumbents": list(comp.incumbents),
        "margin": None, "delta": ci["delta"], "mde": float(mde),
        "excludes_zero": ci_excludes_zero(diff),
        "winner": ci["winner"] if decided else None,
        "verdict": DECIDED if decided else UNDERPOWERED_NOT_DECIDED,
        "note": (f"{ci['note']}; observed |Δ| vs MDE {mde:.4f}: {power['verdict']}"),
    }


def adjudicate_all(diffs: dict[tuple[str, str], dict],
                   mdes: dict[tuple[str, str], float]) -> list[dict]:
    """
    Apply all five thresholds on every family §7 names them (`COMPARISON_PLAN`).

    `diffs` is keyed (th_id, family) → the paired-diff report for that comparison;
    `mdes` supplies each design's MDE (only the two TH5 entries consult it). A
    comparison with no diff supplied — e.g. one Gate C8-0 blocked and the driver
    chose not to run as decisive — is recorded as such rather than silently skipped,
    so the ledger has a row for every §7 claim.
    """
    ledger: list[dict] = []
    for comp in COMPARISON_PLAN:
        key = (comp.th_id, comp.family)
        diff = diffs.get(key)
        if diff is None:
            ledger.append({
                "id": comp.th_id, "family": comp.family,
                "geometry": comp.geometry, "verdict": "not-run",
                "note": "no decisive diff supplied — blocked in advance or "
                        "deferred (see Gate C8-0)"})
        elif comp.tie_rule:
            ledger.append(adjudicate_tie(comp, diff, mdes[key]))
        else:
            ledger.append(adjudicate_margin(comp, diff))
    return ledger


def th1_clears(ledger: list[dict]) -> bool:
    """
    Did TH1 — "the simulator corpus beats Polito" — clear on its PRIMARY target?

    §7 makes fusion depth the primary target, so TH1's depth (sim-heldout) row is
    the trigger. Fine-tuning is a follow-up on a validated corpus effect; a
    fault-bit-only or underpowered TH1 does not earn the extra compute. (The spec
    says "clears §7/TH1" without naming a family; the primary-target reading is the
    most defensible and is stated here rather than left implicit.)
    """
    return any(r["id"] == "TH1" and r["family"] == DEPTH
               and r["verdict"] == MET for r in ledger)


def should_run_finetuning(ledger: list[dict]) -> bool:
    """
    The §6 rule: fine-tuning runs ONLY if the frozen-probe result clears TH1. If C8
    returns "underpowered — not decided," fine-tuning does not run — this is a hard
    gate, not a suggestion, so the follow-up cannot resurrect an undecided verdict.
    """
    return th1_clears(ledger)


class TestSplitGuard:
    """
    The single pre-registered touch of the test split, enforced (spec §7).

    `--split test` is the one look C8 is allowed at the held-out real data. Model
    selection happens on val; the test split is untouched until the arms are fixed,
    and it is read EXACTLY ONCE. This guard makes that structural: the first call to
    `touch()` is allowed and recorded, a second raises `RuntimeError`. A driver that
    reached for a second test look — to "check" a surprising number, the classic way
    a held-out set silently becomes a validation set — cannot.
    """

    def __init__(self) -> None:
        self._touched = False

    @property
    def touched(self) -> bool:
        return self._touched

    def touch(self, reason: str) -> None:
        if self._touched:
            raise RuntimeError(
                "test split already touched once — C8 pre-registers EXACTLY one "
                f"touch of --split test; refusing a second ({reason})")
        self._touched = True


def run_gate_c80(n_full_pos: int, n_full: int,
                 n_held_pos: int, n_held: int) -> dict:
    """
    Gate C8-0 — the power precheck, run FIRST, before the test split is touched.

    Builds the two fault-bit designs whose power is knowable from class counts
    alone — full Polito (79 positives, the powered real-domain design) and the
    symmetric held-out split (11-13 positives, C7's under-powered design) — and
    runs the pre-registered §7 thresholds against them. The depth-family MDEs need
    a pilot error scale from a val-split run and are folded in by the caller from
    the per-arm reports; the fault-bit half here needs no run at all, which is what
    lets the gate be `recorded_before_run` by construction. Returns the gate ledger
    for the driver to consult before deciding which comparisons to read as decisive.
    """
    gate = power_gate([
        fault_design(FULL_POLITO, n_pos=n_full_pos, n_neg=n_full - n_full_pos),
        fault_design(SYMMETRIC_HELDOUT, n_pos=n_held_pos,
                     n_neg=n_held - n_held_pos),
    ])
    assert gate["recorded_before_run"], "Gate C8-0 must not depend on the run"
    return gate


# --------------------------------------------------------------------------
# Subprocess plumbing — the executable half. Mirrors c7_headtohead.py so the two
# drivers read the same. Injected `runner`/`scorer` seams let tests drive the
# ordering and the ledger with stubs, without training anything.
# --------------------------------------------------------------------------

def run_one(run: TrainRun) -> dict:
    """Train one new checkpoint in a subprocess; parse the transfer-artifact path."""
    log_path = LOGS / f"c8_{run.name}.log"
    cmd = [PYTHON, "-m", run.module, *run.cli_args]
    env = {**os.environ, "OMP_NUM_THREADS": THREADS_PER_WORKER}
    t0 = time.monotonic()
    with open(log_path, "w") as log:
        log.write(f"$ {' '.join(cmd)}\n")
        log.flush()
        proc = subprocess.run(cmd, cwd=BACKEND, env=env,
                              stdout=log, stderr=subprocess.STDOUT)
    wall = time.monotonic() - t0
    text = log_path.read_text()
    ckpt = re.search(r"transfer artifact: (\S+)", text)
    final = text.strip().splitlines()[-1] if text.strip() else ""
    return {
        "name": run.name, "arm": run.arm, "seed": run.seed,
        "args": " ".join(run.cli_args), "returncode": proc.returncode,
        "wall_min": round(wall / 60, 1),
        "checkpoint": Path(ckpt.group(1)).name if ckpt else "",
        "final": final,
    }


def train_all(runner=run_one) -> list[dict]:
    """Train the 15 new checkpoints (2 workers, as C6/C7); reuse C7's six."""
    LOGS.mkdir(exist_ok=True)
    runs = new_training_runs()
    print(f"C8: {len(runs)} new training runs, {N_WORKERS} workers "
          f"(+ 6 reused C7 checkpoints, no compute)")
    with ThreadPoolExecutor(max_workers=N_WORKERS) as pool:
        rows = list(pool.map(runner, runs))
    with open(MANIFEST, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    return rows


def checkpoints_by_arm(trained: list[dict]) -> dict[str, dict[int, str]]:
    """
    Fuse the freshly-trained rows with C7's reused six into arm → {seed: path}.

    The single map every decisive comparison indexes: `checkpoints_by_arm[...]
    [MR_WIDE][1337]` is the goldak-wide masked-recon checkpoint at seed 1337,
    whether it was trained this run or (for the two Polito arms) reused from C7.
    """
    by_arm: dict[str, dict[int, str]] = {}
    for r in trained:
        by_arm.setdefault(r["arm"], {})[r["seed"]] = str(
            CHECKPOINTS / r["checkpoint"])
    for arm, by_seed in reused_c7_checkpoints().items():
        by_arm[arm] = dict(by_seed)
    return by_arm


def decisive_scoring_commands(by_arm: dict[str, dict[int, str]],
                              guard: TestSplitGuard) -> list[list[str]]:
    """
    Build the seed-matched `--split test` scoring commands — the SINGLE
    pre-registered touch of the test split (guard.touch is called exactly once,
    covering the whole verdict pass, as in C7 where three subprocess calls were one
    look). Each command scores a seed's challenger + incumbent through the rebuilt
    dual-eval probe so §7's ΔMAE (sim) and ΔAUC (real) come out paired. The unique
    (challenger, incumbent, sim-variant) pairs across the plan drive the matrix; the
    reused Polito arms enter here for TH1 with no retraining.
    """
    guard.touch("C8 decisive scoring — the one pre-registered test-split pass")
    # A pair gets a simulated half exactly when some §7 row judges it on the
    # sim-heldout geometry — TH1/TH2/TH3 depth (MR_WIDE vs each incumbent) and
    # TH5 depth (JEPA_WIDE vs MR_WIDE). The evaluation set is the goldak-WIDE
    # held-out split in every case: all sim-heldout challengers train on wide,
    # and narrow/random only ever appear as incumbents being scored on the
    # challenger's held-out set. (The first rehearsal caught the earlier
    # challenger-keyed variant map silently starving TH2- and TH5-depth.)
    needs_sim = {(c.challenger, inc) for c in COMPARISON_PLAN
                 if c.geometry == SIM_HELDOUT for inc in c.incumbents}
    seen: set[tuple[str, str]] = set()
    cmds: list[list[str]] = []
    for comp in COMPARISON_PLAN:
        for inc in comp.incumbents:
            pair = (comp.challenger, inc)
            if pair in seen:
                continue
            seen.add(pair)
            for seed in SEEDS:
                ca = by_arm.get(comp.challenger, {}).get(seed)
                cb = by_arm.get(inc, {}).get(seed)
                if ca is None or cb is None:
                    continue
                cmd = [PYTHON, "-m", "world_model.eval.compare_pretrains",
                       ca, cb, "--dual-eval", "--split", SCORING_SPLIT,
                       "--seed", str(seed), "--device", DEVICE,
                       "--json-out", str(scoring_json_path(
                           comp.challenger, inc, seed))]
                if REHEARSAL:
                    cmd.append("--tiny")
                if pair in needs_sim:
                    cmd += ["--sim-eval", "goldak", "--sim-variant", "wide",
                            "--sim-seed", str(CORPUS_SEED),
                            "--sim-sessions", str(N_SESSIONS)]
                cmds.append(cmd)
    return cmds


def scoring_json_path(challenger: str, incumbent: str, seed: int) -> Path:
    """Where one (pair, seed) scoring run writes its paired-diff JSON.

    A pure function of the pair — built identically when the command is
    constructed and when the ledger collects, so there is no name to drift.
    """
    return LOGS / f"c8_pairs_{challenger}__{incumbent}_s{seed}.json"


def pool_seed_diffs(diffs: list[dict], family: str) -> dict:
    """
    One decision-grade diff from the seed-matched runs — C7's convention
    ("mean Δ across the 3 seeds") made explicit and given a CI.

    Each seed trains and scores on a DIFFERENT split partition (data/splits.py
    salts the seed), so the seed-level diffs are treated as independent
    estimates of the same effect: equal-weight mean delta, combined SE
    sqrt(Σ se_i²)/k (fixed-effect, equal weights), normal CI. `excludes_zero`
    then answers pooled-CI-excludes-zero — the §7 gate — while `per_seed`
    keeps every seed-level delta on the record.
    """
    if not diffs:
        raise ValueError("pool_seed_diffs needs at least one seed-level diff")
    key = "delta_mae" if family == DEPTH else "delta_auc"
    deltas = [float(d[key]) for d in diffs]
    ses = [float(d["boot_se"]) for d in diffs]
    k = len(diffs)
    delta = sum(deltas) / k
    se = math.sqrt(sum(s ** 2 for s in ses)) / k
    lo, hi = delta - 1.96 * se, delta + 1.96 * se
    pooled = {
        key: delta, "boot_se": se, "boot_lo": lo, "boot_hi": hi,
        "excludes_zero": bool(lo > 0 or hi < 0),
        "n_seeds": k, "per_seed": deltas,
    }
    if any("t1_caveat" in d for d in diffs):
        pooled["t1_caveat"] = diffs[0].get("t1_caveat")
    return pooled


def collect_decisive_inputs(by_arm: dict[str, dict[int, str]]) -> tuple[dict, dict]:
    """
    Load every scoring run's JSON and assemble `adjudicate_all`'s two inputs:
    diffs keyed (th_id, family) and MDEs for the TH5 rows.

    Matching is by checkpoint basename (the one identity both sides share),
    and the sign is repaired when a JSON recorded the pair with the incumbent
    as arm A — `paired_*_diff` is antisymmetric, so flipping is a negation of
    the delta and a mirror of the CI. TH4 must beat BOTH SSL arms, so its diff
    is the BINDING one: whichever incumbent yields the smaller pooled delta.
    A (th, family) whose JSONs are missing is simply absent from `diffs`;
    `adjudicate_all` records it as not-run rather than inventing a verdict.
    """
    diffs: dict[tuple[str, str], dict] = {}
    mdes: dict[tuple[str, str], float] = {}
    for comp in COMPARISON_PLAN:
        per_incumbent: list[dict] = []
        for inc in comp.incumbents:
            seed_diffs: list[dict] = []
            seed_mdes: list[float] = []
            for seed in SEEDS:
                path = scoring_json_path(comp.challenger, inc, seed)
                if (not path.exists()
                        or seed not in by_arm.get(comp.challenger, {})
                        or seed not in by_arm.get(inc, {})):
                    continue
                payload = json.loads(path.read_text())
                ck_ch = Path(by_arm[comp.challenger][seed]).name
                ck_in = Path(by_arm[inc][seed]).name
                for pair in payload["pairs"]:
                    if pair["geometry"] != comp.geometry:
                        continue
                    names = (pair["a"]["checkpoint"], pair["b"]["checkpoint"])
                    if names == (ck_ch, ck_in):
                        d = dict(pair["diff"])
                    elif names == (ck_in, ck_ch):
                        d = _flip_diff(pair["diff"], comp.family)
                    else:
                        continue
                    seed_diffs.append(d)
                    geom_mde = payload.get("mdes", {}).get(comp.geometry, {})
                    if geom_mde.get("mde") is not None:
                        seed_mdes.append(float(geom_mde["mde"]))
                    break
            if seed_diffs:
                pooled = pool_seed_diffs(seed_diffs, comp.family)
                pooled["incumbent"] = inc
                if seed_mdes:
                    pooled["mde"] = sum(seed_mdes) / len(seed_mdes)
                per_incumbent.append(pooled)
        if len(per_incumbent) == len(comp.incumbents) and per_incumbent:
            binding = min(per_incumbent,
                          key=lambda d: diff_delta(d, comp.family))
            diffs[(comp.th_id, comp.family)] = binding
            if comp.tie_rule:
                mdes[(comp.th_id, comp.family)] = binding.get(
                    "mde", float("nan"))
    return diffs, mdes


def _flip_diff(diff: dict, family: str) -> dict:
    """Antisymmetric flip: the pair was recorded incumbent-first."""
    key = "delta_mae" if family == DEPTH else "delta_auc"
    out = dict(diff)
    out[key] = -float(diff[key])
    out["boot_lo"], out["boot_hi"] = -float(diff["boot_hi"]), -float(diff["boot_lo"])
    if "hm_lo" in diff and "hm_hi" in diff:
        out["hm_lo"], out["hm_hi"] = -float(diff["hm_hi"]), -float(diff["hm_lo"])
    return out


def format_ledger(ledger: list[dict]) -> str:
    """§7 work-item 8: the number-vs-threshold ledger, one row per TH claim."""
    tag = "REHEARSAL — NOT DECISIVE — " if REHEARSAL else ""
    out = [f"{tag}C8 verdict ledger (§7, tie rule in force)"]
    out.append(f"{'id':<5} {'family':<6} {'geometry':<18} {'Δ':>9} "
               f"{'margin':>7}  verdict")
    for r in ledger:
        delta = f"{r['delta']:+.4f}" if "delta" in r else "—"
        margin = ("CI≠0" if r.get("margin") is None and r["verdict"] != "not-run"
                  else f"{r['margin']:.4f}" if r.get("margin") is not None
                  else "—")
        out.append(f"{r['id']:<5} {r.get('family', '—'):<6} "
                   f"{r['geometry']:<18} {delta:>9} {margin:>7}  {r['verdict']}")
        out.append(f"      {r['note']}" if r.get("note") else "")
    return "\n".join(line for line in out if line)


def main() -> None:
    """
    Orchestrate the decisive run in the §7 order. Written but UNEXECUTED — see the
    module docstring for the compute this would spend. The pure functions it calls
    (matrix, gate, guard, adjudication) are what `test_c8_driver.py` verifies; the
    subprocess calls this wires would train 15 encoders and score 21 checkpoints.
    """
    from world_model.data.loader_polito import load_polito_sessions
    from world_model.data.splits import split_sessions
    from world_model.eval.compare_pretrains import LABEL_KEY

    if REHEARSAL:
        print("=" * 72)
        print("C8 REHEARSAL MODE — toy corpora/epochs, 2 seeds, scoring on "
              "--split val. NOTHING below is a C8 number; the pre-registered "
              "test-split touch is NOT spent.")
        print("=" * 72)
    rows = train_all()
    for r in rows:
        print(r)
    failed = [r for r in rows if r["returncode"] != 0 or not r["checkpoint"]]
    if failed:
        print(f"ABORT before Gate C8-0 — {len(failed)} run(s) failed: "
              f"{[r['name'] for r in failed]}")
        raise SystemExit(1)

    # Every reused C7 checkpoint must be on disk; a missing one would otherwise be
    # silently retrained, diverging from C7's numbers.
    for arm, by_seed in reused_c7_checkpoints().items():
        for seed, path in by_seed.items():
            if not Path(path).exists():
                print(f"ABORT — reused C7 checkpoint missing: {arm} s{seed} {path}")
                raise SystemExit(1)

    # STEP 2 — Gate C8-0 FIRST. Class counts come from the Polito loader, never from
    # a test-split scoring, so the gate is recorded before any decisive number
    # exists. Full Polito supplies the powered design; the incumbent's held-out
    # split supplies C7's under-powered one.
    all_sessions = load_polito_sessions()
    held = split_sessions(all_sessions, seed=SEEDS[0])["test"]
    gate = run_gate_c80(
        n_full_pos=sum(int(s.meta[LABEL_KEY]) for s in all_sessions),
        n_full=len(all_sessions),
        n_held_pos=sum(int(s.meta[LABEL_KEY]) for s in held),
        n_held=len(held))
    gate_text = _GATE_RENDERER(gate)
    print("\n" + gate_text + "\n")
    tag = "REHEARSAL — NOT DECISIVE\n\n" if REHEARSAL else ""
    (NOTEBOOK / "gate_status.md").write_text(
        f"{tag}# Gate C8-0 — recorded before the decisive scoring\n\n"
        f"```\n{gate_text}\n```\n")   # §7 work-item 8

    # STEP 3 — the SINGLE pre-registered touch of --split test. The guard makes a
    # second look raise; blocked comparisons are still scored for the record but
    # must be read as exploratory, not decisive (§7).
    guard = TestSplitGuard()
    by_arm = checkpoints_by_arm(rows)
    for cmd in decisive_scoring_commands(by_arm, guard):
        print("$ " + " ".join(cmd))
        subprocess.run(cmd, cwd=BACKEND, env={**os.environ})

    # STEP 4/5 — pool the seed-matched paired diffs out of the scoring JSONs,
    # apply TH1-TH5 with the tie rule, and record the ledger. This is the wiring
    # the module docstring called "the last the compute-bearing run supplies".
    diffs, mdes = collect_decisive_inputs(by_arm)
    ledger = adjudicate_all(diffs, mdes)
    print("\n" + format_ledger(ledger))
    ledger_path = NOTEBOOK / "c8_ledger.json"
    ledger_path.write_text(json.dumps(
        {"rehearsal": REHEARSAL, "split": SCORING_SPLIT, "seeds": list(SEEDS),
         "ledger": ledger,
         "diffs": {f"{th}/{fam}": d for (th, fam), d in diffs.items()}},
        indent=1))
    print(f"\nledger: {ledger_path}")
    ft = should_run_finetuning(ledger)
    print(f"fine-tuning follow-up (gated on TH1 depth): "
          f"{'RUN' if ft else 'DO NOT RUN'}"
          + (" [rehearsal — not binding]" if REHEARSAL else ""))


if __name__ == "__main__":
    main()
