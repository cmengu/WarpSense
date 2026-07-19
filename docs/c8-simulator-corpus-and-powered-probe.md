# Issue: C8 — Simulator-corpus pretraining + a probe that can detect an effect

**Type:** Experiment (world model)
**Priority:** High — blocks every further pretraining comparison
**Effort:** 7–10 engineer-days + compute (see §6 run inventory)
**Labels:** `world-model` `pretraining` `evaluation` `sim2real` `pre-gate-0`
**Version:** v3 — ticket-ready. Adds the run inventory (§6), pre-registered
thresholds (§7), a power precheck that gates the decisive run (Gate C8-0), and
resolves the four open design decisions (§5). Sequencing corrected.

---

## TL;DR

C7 concluded "tie, masked recon retains the warm-start slot." That verdict is
uninformative: the probe it was measured with had no statistical power, and the
corpus it transferred from is the wrong welding process. C8 changes **both** —
pretrain on simulated arc welds instead of Polito spot welds, and replace the
probe with one that can distinguish a real effect from noise — then re-runs the
JEPA vs masked-recon comparison once.

**v2 added the sim-to-real trap register (§4).** Training on synthetic data drawn
from known parameter ranges is standard practice (*domain randomization*) and has
well-documented ways of failing silently. Each trap carries a mitigation **and a
detector** — the observation that reveals we fell in anyway. A trap with no
detector is not mitigated, just noted.

**v3 makes it executable.** The v2 matrix implied ~30 pretraining runs and ~180
scorings against a 5–9 day estimate; §6 trims it to **15 new checkpoints** by
reusing C7's six and demoting fine-tuning to a conditional follow-up. §7
pre-registers the thresholds the repo's D11 rule requires, and **Gate C8-0**
computes the minimum detectable effect *before* the decisive run — so an
underpowered comparison is declared in advance rather than discovered afterward.
That inversion is the structural fix for the C7 failure.

Scope: `world_model/pretraining/`, `world_model/simulator/weld_sim.py`,
`world_model/eval/compare_pretrains.py`, and a new experiment driver. No
architecture changes, no new sensing, no real-data dependency, no UI-facing
claims.

Source analysis: [`docs/world-model-beyond-jepa-options.md`](../world-model-beyond-jepa-options.md)

---

## 1. Current State vs Expected Outcome

### Current State

- **Pretraining corpus is Polito** — 1,976 real *resistance spot* welds
  (`data/loader_polito.py`), 79 faulty / 1,897 good. The target domain is
  aluminium *MIG arc* welding: different process, different material, and only 2
  of 6 production channels — `PRETRAIN_CHANNELS = ["volts", "amps"]`.
- **The probe is macro-F1 on a 4% fault bit** — `eval/compare_pretrains.py` uses
  `f1_score(average="macro")` on hard labels (lines 108, 116, 119). No ROC, no
  AUPRC, no confidence interval anywhere in the file.
- **C7 results sit inside the null.** JEPA 0.5064 / 0.5284 / 0.5189, masked recon
  0.4903 / 0.4473 / 0.5167, random-init floor 0.4967 / 0.4449 / 0.5020;
  `fold_std` 0.03–0.08; **11–13 positives** out of 277–308. Permutation null
  ≈0.49–0.50, 95% band ≈0.46–0.56 — every number including the floor falls
  inside. `probe_macro_f1` already prints an under-powered warning; C7 issued a
  verdict anyway.
- **The protocol is linear probing.** V-JEPA's authors measured +16–17 points
  from replacing linear probes with attentive probing.
- **The simulator is already capable and already wired** — all six channels plus
  per-frame fusion depth; `TrainWindows` consumes `SessionTensor`; the
  `pretraining/common.py` checkpoint contract is objective-agnostic.
- **But the simulator is narrower than it looks** (§4/T3): `sample_params()`
  randomises six physical quantities and leaves `drift` and `noise` at their
  dataclass defaults, and models no defect mechanism except the stitch-restart
  fusion dip.

### Expected Outcome

- `sample_params()` randomises noise and drift; ranges widened per §5/D1.
- A corpus flag selects simulator, spectrum-matched-random, or Polito.
- Polito **demoted from training set to real-domain evaluation set** — which
  unlocks scoring sim-trained arms on **all 1,976 welds / 79 positives** rather
  than a held-out sliver (§4/T1).
- `compare_pretrains.py` reports AUC + AUPRC with bootstrap CIs, the paired
  between-arm difference with a CI, the permutation null, **and the minimum
  detectable effect**.
- An attentive-probe arm exists, with a probe-capacity diagnostic (§5/D3).
- A supervised-on-simulated-depth arm exists (§4/T5).
- **Gate C8-0 passes before the decisive run**, or C8 stops and reports why.
- Verdict recorded in `gate_status.md` in number-vs-threshold form, including an
  explicit "underpowered — not decided" branch.

---

## 2. Why both variables change at once

The repo's instinct — one variable per experiment — is correct in general and
wrong here. Both current settings are *independently known-broken*: the corpus is
the wrong process, and the probe cannot detect an effect of any size. Fixing one
at a time costs two full experiments to reach the same knowledge, and the
intermediate result is uninterpretable either way.

The cost is that a positive result won't attribute between the two changes. That
is acceptable because **neither old setting is a candidate to return to**.
Attribution is only worth paying for when a variable might be reverted.

---

## 3. Where this sits in the wider practice

Generating synthetic training data by sampling parameters from known ranges is
called **domain randomization**, and it is mainstream. Tobin et al. (2017)
transferred object detectors trained purely on randomised renderings to real
robot cameras; Hwangbo et al. (2019, *Science Robotics*) trained ANYmal's
locomotion entirely in simulation and deployed to hardware. The
engineering-surrogate version — sweep an expensive solver, train a cheap network
to approximate it — is routine in aerospace and is the closest analogue here.

Two findings shape the design below.

**Realism is not the objective; coverage is.** Optical-flow networks trained on
FlyingChairs — 3D chairs on random Flickr backgrounds — generalise well to real
video and *outperform* networks trained on the more photorealistic
FlyingThings3D. Fidelity is not the axis that pays. This is why §5/D1 spends its
effort on ranges rather than on simulator accuracy.

**Real data is often better spent calibrating the simulator than fine-tuning the
model.** Chebotar et al. (2019) adapt the *simulation parameter distribution*
from a few real roll-outs. Directly relevant to budgeting Gate 0's first coupons
(§4/T6).

---

## 4. The sim-to-real trap register

Each trap: what it is, why we're exposed, the mitigation, and **the detector**.
T1 and T2 are the dangerous ones — their failure mode is invisible to a simulated
test set.

### T1 — Learning the simulator's inverse (the silent one)

**The trap.** A model trained on Goldak-generated welds learns to invert
*Goldak*, not physics. Held-out simulated data cannot detect this: it was
produced by the same equations, so it inherits the same errors and rewards the
same skill. The test shares the assumption it is meant to test.

**Exposure.** Total. Every simulated number C8 produces has this property, as
does Gate 1.5's 0.109 mm oracle ceiling.

**Mitigation.** Structural, not statistical: **no simulated metric is ever
reported alone.** Every headline number is a sim/real pair, with the simulated
half carrying a fixed caveat string in `gate_status.md`.

**Detector — repaired in v3.** v2 specified "arm ranking on sim disagrees with
arm ranking on Polito," which did not work: the Polito split carried 11–13
positives, so its ranking was noise and disagreement carried no information.

The repair follows from the demotion itself. **Arms pretrained on Goldak or
random never see Polito at all**, so they can be scored on the *entire* corpus —
1,976 welds, **79 positives**, roughly a 7× increase over the split. The 11–13
figure was an artefact of a train/test split that only existed because Polito was
training data.

This introduces a deliberate asymmetry, which §7 handles explicitly:

| Arm family | Real-domain evaluation | Positives |
|---|---|---|
| Goldak / random / supervised | **full Polito** | 79 |
| Polito-pretrained (incumbent) | held-out split only | 11–13 |

T1's detector uses the **powered** full-Polito ranking among sim-trained arms
only — the incumbent is not needed to detect Goldak-inversion. The symmetric
incumbent-vs-simulator comparison is reported separately and remains
power-limited; §7/TH1 states the threshold it must clear.

### T2 — The corpus contains almost no failure modes

**The trap.** `SimParams` exposes no defect parameters. The only failure
mechanism simulated is the stitch-restart fusion dip. The production alert engine
ships **seven** signatures — porosity, arc instability, crater crack, oxide
inclusion, undercut, lack of fusion, burn-through. Six do not exist in the corpus.

**Mitigation.** Scope honesty, not more simulation. C8 does not claim sim
pretraining teaches defect structure and **must not be evaluated on defect
targets it never saw**: fusion depth is primary, the Polito fault bit is a
secondary real-domain check. Extending simulator defect coverage is **out of
scope** (§8) — it is physics modelling with its own validation burden.

**Detector.** Sim-pretrained encoders beating Polito-pretrained ones on depth
while *losing* on defect-flavoured targets. Expected, not anomalous — recording
the prediction prevents it being read later as a regression.

### T3 — Under-randomization (verified in code)

**The trap.** Domain randomization fails when ranges are too narrow, because the
real world then sits outside the training distribution rather than inside it.

**Exposure.** Confirmed by reading `weld_sim.py`. `sample_params()` randomises
volts (18–26), amps (90–200), travel speed (150–450), plate thickness (3–10 mm),
ambient (10–35 °C) and a stitch schedule — then **leaves `drift` and `noise` at
their dataclass defaults**. Every session shares one identical sensor-noise
signature. On the noise axis the training distribution is a single point, so
reality is *guaranteed* to fall outside it.

**Mitigation.** Randomise `drift` and `noise` per session (§5/D1) — the highest
value-per-line change in C8 — and widen the six physical ranges.

**Detector.** A narrow-range and a wide-range corpus, compared on full Polito.
Run for masked reconstruction only (§6) — the range question is about the corpus,
so one objective suffices.

### T4 — Volume masquerading as fidelity

**The trap.** 1,976 Polito welds → ~20k simulated sessions is a 10× data
increase. Synthetic-pretraining gains are frequently attributable to volume
alone, and FlyingChairs shows fidelity is not the axis that pays.

**Mitigation.** A **spectrum-matched random** control corpus (§5/D2).

**Detector.** §7/TH2. If Goldak does not clear the random control by the
pre-registered margin, the win is volume — report it as such and do not describe
the simulator as validated.

### T5 — Free labels going unused

**The trap.** The simulator supplies per-frame fusion depth. Carrying the SSL
framing over from the Polito era — where self-supervision was *forced* by absent
labels — discards a stronger signal for no stated reason. Gate 1.5 already showed
supervised learning works in sim (0.109 mm MAE).

**Mitigation.** A **supervised-on-simulated-depth arm** as a fourth contender
(§5/D4). The argument for keeping SSL is real — an encoder fitted directly to
Goldak's depth mapping is maximally exposed to T1 — but it should be *tested*.

**Detector.** The sim/real gap per T1, compared between the supervised and SSL
arms. **Prediction: supervised wins on sim, loses on full Polito.** If it wins on
both by §7/TH4's margin, the SSL framing is obsolete for this project.

### T6 — Spending Gate 0's first coupons wrongly

**The trap.** The instinctive use of first real data is fine-tuning. Chebotar et
al. instead adapt the *simulation parameter distribution*, improving every future
synthetic sample rather than one model.

**Mitigation.** Not a C8 work item (C8 is pre-Gate-0), recorded so the decision
isn't made by default when coupons arrive. §5/D1's ranges are what they should
calibrate.

**Detector.** N/A until Gate 0.

---

## 5. Resolved design decisions

v2 left four decisions implicit. Defaults below; override in review, but do not
leave open — each blocked a ticket.

### D1 — How much wider do the ranges get?

Midpoints unchanged; **half-widths ×1.5** on the six physical quantities. `drift`
and `noise` drawn **log-uniform over [0.5×, 2.0×] their current defaults**,
per session, per key.

*Rationale:* ×1.5 broadens coverage without generating physically absurd welds,
and the log-uniform noise scale spans the plausible gap between simulator and a
real ESP32 in both directions. Whether to widen further is answered by T3's
detector, not guessed now.

### D2 — What exactly is the random corpus?

**Spectrum-matched noise**, not white noise: per channel, match the power
spectral density of the Goldak corpus and randomise the phases. Same marginal
statistics, same frequency content, **no causal or physical structure**.

*Rationale:* white noise is a trivially weak control — beating it proves almost
nothing, since any temporally structured corpus would. Spectrum matching makes
T4's test meaningful: if Goldak beats this, the win is structural rather than
spectral.

### D3 — Attentive-probe protocol (and its overfitting risk)

Single learnable query, single head, no MLP, dropout on attention weights, early
stopping on an inner validation fold nested inside the existing GroupKFold.
Report the probe's **parameter count** beside its score.

**Mandatory diagnostic:** run the attentive probe on the **random-init encoder**
too. If attentive-on-random beats linear-on-pretrained, the probe is fitting
itself rather than reading the encoder, and every attentive number that run is
void.

*Rationale:* a learnable query has parameters, and on 79 positives — let alone
11–13 — it can score well by memorising. The diagnostic is what separates "the
encoder knows more than a linear probe can read" from "the probe is strong."

### D4 — Supervised arm head and loss

Linear head on the same `StemTrunkEncoder` hidden states → per-frame depth,
symlog-transformed target (matching `training/symlog.py`), MSE loss. Stems and
trunk keep the `TRANSFER_PREFIXES` contract so the checkpoint stays interchangeable
with the SSL ones.

*Rationale:* the arm must differ from the SSL arms in *objective only*. Any
architectural difference would confound T5's comparison.

---

## 6. Run inventory (what "5–9 days" was hiding)

v2's matrix implied ~30 pretraining runs and ~180 scorings. Trimmed:

**Reused from C7 — no new compute.** JEPA-on-Polito
(`e7f0e92d7625`, `0b1928f64c3a`, `a0af0e76939f`) and masked-recon-on-Polito
(`6a0b09b6c113`, `44889df44347`, `1464012e1949`) at seeds 1337/1338/1339.

**New checkpoints — 15 total, 3 seeds each:**

| Objective | Corpus | Runs | Answers |
|---|---|---|---|
| JEPA | goldak-wide | 3 | primary comparison |
| Masked recon | goldak-wide | 3 | primary comparison |
| Masked recon | goldak-narrow | 3 | T3 detector |
| Masked recon | spectrum-random | 3 | T4 control |
| Supervised depth | goldak-wide | 3 | T5 |

JEPA runs only on goldak-wide: the corpus questions (T3, T4) are about the
corpus, so the incumbent objective alone answers them. This is the single
biggest saving and the main reason the estimate is now credible.

**Scoring:** 21 checkpoints × 2 probe types (linear, attentive) × 2 evaluation
sets (held-out sim, Polito) ≈ **84 scorings**, plus random-init floors. Linear
probes are cheap; attentive probes are small.

**Fine-tuning is demoted to a conditional follow-up.** v2 made it a C8 arm, which
meant ~30 encoder retrains. It now runs only on the winning arm plus the
incumbent (2 × 3 = 6 runs) and **only if** the frozen-probe result clears
§7/TH1. If C8 returns "underpowered — not decided," fine-tuning does not run.

---

## 7. Pre-registered thresholds (D11)

The repo's rule is *a number versus a threshold, or it didn't happen*. v2 had
acceptance criteria (was it built) but no thresholds (what result means what).
Fixed here, before any run.

**Gate C8-0 — power precheck. Runs BEFORE the decisive comparison.**
The probe harness reports the **minimum detectable effect** for each evaluation
design. If a threshold below sits under its MDE, that comparison is declared
**underpowered in advance** and is not run as a decisive test. This is the
structural fix for C7: the power check moves upstream of the experiment instead
of being reconstructed afterward.

**Two targets, two metric families.** T2 makes fusion depth the primary target and
the Polito fault bit the secondary real-domain check. Depth is *continuous*, so it
is scored by **ΔMAE** (symlog-space, lower is better); the fault bit is *binary*,
so it is scored by **ΔAUC**. Every threshold below therefore names both. v3.0
stated all five thresholds in ΔAUC alone, which left the declared primary target
with no threshold at all — corrected here.

| ID | Claim | Threshold — depth (primary, sim) | Threshold — fault bit (secondary, real) | If not met |
|---|---|---|---|---|
| **TH1** | Simulator corpus beats Polito corpus | ΔMAE ≥ **0.02 mm** improvement, CI excludes 0 | paired ΔAUC ≥ **+0.05**, CI excludes 0, symmetric evaluation | "no corpus effect detected" — Polito keeps the warm-start slot |
| **TH2** | The win is fidelity, not volume | goldak-wide beats spectrum-random, ΔMAE ≥ **0.01 mm** | ΔAUC ≥ **+0.03**, CI excludes 0 | "win attributable to volume; simulator NOT validated" |
| **TH3** | Ranges were binding | goldak-wide beats goldak-narrow, ΔMAE ≥ **0.01 mm** | ΔAUC ≥ **+0.03**, CI excludes 0 | ranges not binding at this scale; do not widen further |
| **TH4** | SSL framing is obsolete | — (supervised is expected to win here; not diagnostic) | supervised beats both SSL arms by ΔAUC ≥ **+0.05** on **full Polito** | keep SSL; supervised-wins-on-sim-only is the predicted T5 pattern, not a win |
| **TH5** | JEPA vs masked recon | paired ΔMAE CI excludes 0 | paired ΔAUC CI excludes 0 | **"underpowered — not decided"** — *not* "tie, incumbent wins" |

TH4 is deliberately one-sided: the supervised arm trains directly on depth, so
beating the SSL arms on depth is expected and proves nothing. Only its
**real-domain** performance is diagnostic — which is exactly the T5 prediction.

TH5's phrasing is the specific C7 failure this spec exists to avoid: C7's tie rule
silently converted an absence of power into a verdict about JEPA.

**These thresholds are provisional until Gate C8-0 runs.** If the MDE comes back
above a threshold, raise the threshold or declare that comparison exploratory —
do not run it as decisive and reinterpret afterward.

---

## 8. Work Items

Ordered. Item 1 must precede item 2 — v2 had these reversed, so item 2 would have
regenerated a corpus item 1 had just built.

1. **Fix and widen the generator (T3, D1) — 0.5 d.** `sample_params()` draws
   `drift` and `noise` per session; six physical half-widths ×1.5; ranges become
   an explicit recorded parameter.
2. **Generate corpora — 0.5 d + compute.** ~20k sessions each for goldak-wide,
   goldak-narrow, spectrum-random. Persist seed **and ranges**; bit-for-bit
   regenerable. Session-grouped splits via existing `data/splits.py` salting.
3. **Corpus flag — 0.5 d.** `--corpus {polito,goldak,random}` on
   `masked_recon.py` and `jepa.py`, plus a path to the generated corpus. Default
   stays `polito`; no existing reproduction changes behaviour.
4. **Rebuild the probe (A2) — 2–3 d.** AUC + AUPRC + bootstrap CIs alongside
   macro-F1 (keep it, for C5–C7 continuity); paired difference CI (Hanley &
   McNeil 1983); permutation null printed beside every number; **MDE reported**
   (Gate C8-0); every result on both sim and Polito evaluation sets.
5. **Attentive probe (D3) — 1 d.** Including the random-init diagnostic.
6. **Supervised-on-sim-depth arm (D4) — 1 d.**
7. **Driver + decisive run — 1–2 d + compute.**
   `experiments/notebook/c8_headtohead.py`: seed-matched, one pre-registered
   test-split touch, Gate C8-0 first, §7 thresholds applied as written.
8. **Record in `gate_status.md` — 0.5 d.** Number-vs-threshold form for every
   TH, including the "underpowered — not decided" branch.

---

## 9. Acceptance Criteria

- [ ] `sample_params()` randomises `drift` and `noise` per session (T3).
- [ ] Six physical half-widths widened ×1.5; ranges recorded with the corpus (D1).
- [ ] Three corpora generated, regenerable from seed + ranges.
- [ ] Spectrum-matched random corpus — verified PSD match per channel (D2).
- [ ] `--corpus {polito,goldak,random}` on both objectives; default unchanged.
- [ ] Probe emits AUC + AUPRC + bootstrap CIs + paired CI + permutation null + MDE.
- [ ] Attentive probe implemented, parameter count reported, random-init
      diagnostic run and passing (D3).
- [ ] Supervised arm shares `TRANSFER_PREFIXES`; differs in objective only (D4).
- [ ] **Gate C8-0 run and recorded before the decisive comparison.**
- [ ] Sim-trained arms scored on **full Polito (79 positives)**; incumbent scored
      on its held-out split; asymmetry stated in the report (T1).
- [ ] Every headline number reported as a sim/real pair, sim carrying the T1
      caveat (T1).
- [ ] All five TH thresholds evaluated and recorded in `gate_status.md`.
- [ ] Fine-tuning follow-up run *only* if TH1 clears.

---

## 10. Explicitly Out of Scope

- **Gate 0 real arc-weld data collection.** The dominant term for any millimetre
  claim, but weeks of procurement, not competing for the same resource. Run C8
  *during* procurement. See T6 for budgeting its first coupons.
- **Extending simulator defect coverage (T2).** Six of seven production defect
  signatures are unmodelled; fixing that is physics modelling with its own
  validation burden. Separate ticket.
- **Fine-tuning as a C8 arm.** Demoted to conditional follow-up (§6).
- **Adding thermal sensing (B2).** Separate decision with its own cheap test.
- **New SSL objectives (TF-C, SimMTM).** Only after C8 reports.
- **Any architecture change.** Failures so far are all upstream of the model.
- **Any UI-facing millimetre figure.** The D10 rule holds.

---

## 11. Risks

- **The simulator's parameter distribution is uncalibrated** (Step 9 not done).
  Same-process pretraining on a miscalibrated simulator can still transfer badly.
  Accepted pre-Gate-0 limitation — C8 reports relative comparisons between arms,
  never an absolute millimetre claim.
- **T1 is mitigated, not solved.** Full-Polito scoring raises real-domain
  positives ~7× and makes T1's detector viable, but Polito is still the wrong
  process and can only ever be a weak proxy. The real detector arrives with Gate 0.
- **The asymmetric evaluation (T1) is a genuine confound for TH1.** Sim-trained
  arms get 79 positives; the incumbent gets 11–13. TH1 is therefore evaluated on
  the *symmetric* split and is the most power-limited claim in the spec — the
  most likely to return "underpowered" from Gate C8-0. That is an acceptable
  outcome and must be reported as such, not worked around.
- **Negative transfer from Polito cannot be measured until Gate 0** — detecting
  it requires held-out target-domain data. C8 sidesteps rather than resolves it.
