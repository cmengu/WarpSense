# World-Model Pretraining Consolidation (`feat/wm-pretraining-consolidation`)

Source-of-truth explainer for the C0–C2 refactor: what each file does, why the
seams are where they are, and how this fits into the world-model step plan.

## Where this sits in the step plan

- **Step 6 (done)** — Polito pretraining, Gate 0.5 PASS. Produced the real
  checkpoint `polito_pretrain_8a68998bf644.pt`. The code lived as one
  monolithic script, `training/pretrain_polito.py`.
- **This branch (C0–C2)** — a *refactor, not a new step*. It reorganizes Step 6's
  code so a second pretraining objective (JEPA, C3–C4) can be added as a
  sibling instead of a copy-paste fork. Verified bit-for-bit identical to the
  old code (same seeds → same weights to 10 decimal places; the real Step-6
  checkpoint still loads).
- **Step 7/8 (done, this branch's ancestor)** — warm-start the ODE-RNN encoder
  from a pretraining checkpoint. They consume checkpoints **only** through the
  contract in `pretraining/common.py`.
- **Steps 9+** — blocked on Gate 0 real-data collection.

## The pipeline, end to end

```
raw sessions ──(windows.py)──► fixed-size windows ──(windows.py)──► masked puzzle
                                                                        │
                              ┌─────────────────────────────────────────┘
                              ▼
                     (trunk.py) encoder ──► hidden states ──► objective head → loss
                              │
                              ▼ (when training finishes)
                     (common.py) save_transfer_checkpoint ──► .pt file on disk
                              │
                              ▼
                     Step 7/8 load_transfer_checkpoint → warm-start ODE-RNN
```

## File by file

### `architecture/trunk.py` — the shared encoder (the "body")

`StemTrunkEncoder` is the neural network whose weights we actually care about:
per-channel stems followed by a single-layer GRU. It maps a window of sensor
readings `[B, T, C]` to one 64-number summary vector per timestep
`[B, T, HIDDEN_DIM=64]`.

It is **not** the whole model, and it does **no masking**. It is the shared
*body*; each pretraining objective bolts a disposable *head* onto it:

| Objective | Head bolted on | Trained artifact kept |
|---|---|---|
| masked reconstruction | reconstruction head (predict hidden values) | encoder only |
| JEPA (C3–C4) | predictor MLP + EMA target encoder | encoder only |

Same engine, different test rigs. The heads are scaffolding: they exist only to
force the encoder to learn, and are discarded at save time
(`transfer_state_dict()` keeps `stems.*` + `trunk.*` only).

**What the network literally is.** Nothing is downloaded from the internet —
no pretrained weights, no hub model. It is assembled from two standard PyTorch
layer types with freshly random-initialized weights:

- `ChannelStems` (`architecture/stems.py`): one tiny `nn.Conv1d(1, 16,
  kernel_size=5)` per sensor channel — a learned filter sliding over 5
  consecutive frames of that one sensor, emitting 16 features per frame. The
  per-channel outputs are averaged (mean over channels present) into one
  16-vector per frame.
- `nn.GRU(16, 64)`: a recurrent layer that reads those 16-vectors frame by
  frame, carrying a 64-number memory forward through time.

Instantiation is one line — `StemTrunkEncoder(["volts", "amps"])` — and the
whole thing is ~16k parameters for the 2-channel Polito case (192 in the
stems, 15,744 in the GRU). Deliberately tiny: sized for ~2k real welds, not
internet-scale data. `[4, 300, 2]` in → `[4, 300, 64]` out.

The **transfer contract** is defined here once: state-dict key names
(`stems.*`, `trunk.*`), `HIDDEN_DIM = 64`, and GRU↔GRUCell shape compatibility
that lets Step 7's ODE-RNN cell load trunk weights by name-mapping. Renaming
these attributes silently orphans every existing checkpoint — a test pins them.

### `data/windows.py` — data prep: slicing AND masking

Two jobs:

1. **Slicing.** Sessions are minutes long and variable-length; SSL wants many
   fixed-size samples. `TrainWindows` builds a lightweight index — a Python
   list of `(session_number, start_frame)` pairs — and slices the real array
   lazily in `__getitem__`. No data is copied up front.
2. **Masking.** `mask_timesteps` (scattered frames, the BERT recipe, fraction
   0.15 in masked recon) and `mask_contiguous` (one solid block, the I-JEPA
   recipe, block covering 25–50 % of the window). Both hide *whole timesteps
   across all channels* — moments in time, not channels.

Two dataset classes, deliberately:

- `TrainWindows` returns `(x, mask)` only — it physically has no labels field,
  so "pretraining never sees labels" is a property of the type, not of
  reviewer discipline.
- `ProbeWindows` adds `(labels, group)` for linear-probe *evaluation* only;
  `group` = session index for GroupKFold (overlapping windows of one session
  must stay in one fold or the split leaks).

### Why mask at all if there are no labels? (self-supervision)

"No labels" means no *human* labels (fault codes, weld quality). Masking
manufactures labels out of the data itself: hide part of the signal, and the
hidden values become the answer key. The model can only fill in the blanks by
learning how the physical signals actually behave — and that understanding
(stored in the encoder weights) is the entire product. The prediction heads
and the reconstructions themselves are thrown away.

Scattered vs. block masking are two difficulty settings for the same idea:
scattered single frames can be solved by local interpolation (signals are
smooth); one missing 25–50 % block forces the model to understand the
*dynamics* of the process to predict a whole missing region.

### What does research say about ratios? (sensor time series specifically)

The governing principle: the ratio must scale with the signal's redundancy.
Text tokens are information-dense, so BERT gets away with 15 %; smooth
continuous signals are highly redundant, so small scattered holes are solvable
by local interpolation and teach the model little. Closest-domain numbers
(from the literature, as of Jan 2026 — re-verify before citing formally):

- **TST** (Zerveas et al. 2021, multivariate sensor time series): 15 % total,
  but in *contiguous geometric spans* (mean length ~3), per channel — their key
  finding was that span masking matters more than the raw ratio.
- **wav2vec 2.0** (raw audio waveforms — the closest analogue to 100 Hz weld
  signals): ~49 % of frames end up masked, via overlapping spans of 10.
- **SimMTM / PatchTST self-supervised** (time-series, 2023): 40–50 %.
- **Ti-MAE / TimeMAE**: 60–75 %.
- Images/video for context: MAE 75 %, VideoMAE up to 90 %.

Takeaway for this repo: the literature sweet spot for continuous sensor data
is roughly **40–60 %, hidden in contiguous spans**. Our `mask_contiguous`
`ratio_range = (0.25, 0.5)` sits at the low edge of that; our scattered
`MASK_FRACTION = 0.15` (Step 6 legacy, BERT convention) is likely too easy and
is the first knob to ablate — either raise it toward 30–50 % or switch masked
recon to span masking.

### `pretraining/common.py` — the checkpoint file-format spec (not a database)

Three functions that define the one envelope every objective's checkpoint uses:

- `save_transfer_checkpoint` — encoder weights + metadata (`objective`,
  `channels`, dims, training config) in one standard payload.
- `load_transfer_checkpoint` — reads any such file; pre-contract Step 6 files
  get `objective: "masked_recon"` inferred instead of failing.
- `build_encoder` — reconstructs a ready-to-use `StemTrunkEncoder` from a
  loaded checkpoint.

It stores nothing and remembers nothing — the *run log* is `runs.csv`, and the
*weights memory* is each `.pt` file. common.py is the librarian/format spec:
because every objective writes the same envelope, downstream consumers can't
tell a masked-recon checkpoint from a JEPA one except by the `objective`
field. If JEPA wins the probe comparison, swapping a file path is the entire
migration.

### `pretraining/masked_recon.py` — Step 6 training loop, relocated

The former `training/pretrain_polito.py`, moved via `git mv` (history
preserved); its ad-hoc `torch.save` replaced with the contract call. Behavior
otherwise untouched.

### `training/pretrain_polito.py` — deprecation shim

20 lines that re-export everything from `pretraining/masked_recon.py` so the
documented CLI `python -m world_model.training.pretrain_polito` keeps working.
Mail forwarding after moving house. New code imports the new path.

## Testing philosophy

Every test is "do something, assert the result" — the craft is choosing *what*
to assert. Three flavors used here:

1. **Behavior** — e.g. run `mask_contiguous`, assert the hidden frames form
   exactly one unbroken block.
2. **Contract pinning** — load the real Step-6 checkpoint into the extracted
   encoder, assert every key matches. A tripwire: rename `stems` and a test
   screams "you orphaned every checkpoint" instead of failing silently later.
3. **Absence guards** — assert `TrainWindows` items carry no labels. Testing
   that something *can't* happen.

### `pretraining/jepa.py` — the JEPA components (C3, done)

The ~70 genuinely new lines. `JEPAPretrainModel` subclasses `StemTrunkEncoder`
(self = the online/student encoder, so `stems.*`/`trunk.*` keep the contract
names) and adds:

- **predictor** — `Linear(64→128) → GELU → Linear(128→64)`, guesses the
  embeddings of the hidden block from the context encoding. Disposable head.
- **target** — a second `StemTrunkEncoder`, initialized as an exact copy of
  the online one, `requires_grad_(False)`. Produces the answer key from the
  full unmasked window (`target_encode`). Never trained by gradients;
  `ema_update()` drags it behind the student:
  `target = decay·target + (1−decay)·online` (decay 0.996, BYOL/I-JEPA
  convention). This is the anti-collapse mechanism: if one network made both
  guess and answer, "output a constant" would zero the loss.

No decoder anywhere — the loss (C4) compares embeddings to embeddings.
`transfer_state_dict()` excludes `predictor.*`/`target.*` for free (wrong
prefixes), so a JEPA checkpoint is contract-identical to a masked-recon one.

Tests pin: target never receives gradients; EMA moves the target at exactly
`1−decay`; the saved artifact contains only the online encoder and round-trips
through `common.py`; predictor output shape matches the embedding shape.

### The C4 training loop (done 2026-07-14)

`pretraining/jepa.py` now carries the run path: `TrainWindows` (300/50) →
`mask_contiguous` with the new generic `n_blocks` param (default 4 blocks
totalling 40–50% hidden; `--n-blocks 1` is the smoke configuration) → target
encodes the full window without gradients → online encoder + predictor guess
the hidden-frame embeddings → latent MSE → optimizer step → `ema_update()`.
CLI mirrors masked_recon (`python -m world_model.pretraining.jepa --tiny`);
checkpoints save through the contract with `objective="jepa"`.

Two **collapse dials** in `evaluate()`, because JEPA's failure mode is a loss
that looks great while the encoder says the same thing about every weld:

- `embed_std` — how spread out the target embeddings are. Collapse drags it
  to zero.
- `latent_mse_mean_baseline` — the score of predicting the average embedding
  everywhere. Healthy: latent MSE well under it. Collapse: both race to zero
  together.

`masked_recon.py --window 300` is the matching **control diet**: masked recon
re-trained on the same windows (recon-only — `TrainWindows` physically has no
labels), so the C7 head-to-head changes exactly one variable. Note the JEPA
raw training loss *rises* across epochs by design: the EMA target keeps
getting richer, so the answer key gets harder — read health off the val
latent MSE vs its mean-baseline, not the loss curve.

Tiny-preset smoke results (200 welds, 20 epochs, committed to `runs.csv`):
JEPA test latent MSE 0.00223 vs 0.02047 baseline, embed_std rising 0.028 →
0.113 (no collapse); masked-recon windows 0.00140 vs 0.07293.

### The C5 ruler (done 2026-07-14)

`eval/compare_pretrains.py` measures any transfer checkpoint the same way:
load through the contract → freeze the encoder → embed `ProbeWindows` →
mean-pool per weld (window vector = the GRU hidden state at the last frame;
weld vector = mean of its window vectors) → logistic-regression probe under
GroupKFold by session → macro-F1, pooled across held-out folds (pooling keeps
the number stable when a fold holds none of the 79 rare faults). A
randomly-initialised encoder is scored alongside as the floor every contender
must clear — "probe ≈ floor" is also the pre-registered too-short-window
symptom.

The probe is deliberately LINEAR: if the fault signal isn't already laid out
in the embedding, a linear model can't dig it out — a stronger probe would
measure the classifier, not the encoder. `--split val` is for model
selection (C6, picking JEPA's entrant); `--split test` is touched exactly
once, for the C7 verdict.

Real-data edge case baked in: with rare positives a training fold can hold a
single class; the probe degrades to a constant prediction for that fold and
warns when positives < folds ("under-powered"), instead of crashing — found
by the tiny smoke (val = 33 welds, 1 faulty), not by the synthetic tests.

### The C6 study (done 2026-07-16)

One knob at a time from the C4 default (window=300, stride=50, 4 blocks
totalling 40–50% hidden, EMA 0.996), seed 1337, 30 epochs, full Polito data;
every checkpoint scored by the C5 ruler on `--split val` (287 welds, 13
faulty). Driver: `experiments/notebook/c6_collapse_ablations.py` (the
`c6_essential.py` variant ran the final three configs after two restarts).

| config | knob | val macro-F1 (± fold) | train-time dials |
|---|---|---|---|
| (random init) | — the floor | 0.4734 ± 0.0387 | — |
| default | — | **0.4888 ± 0.0394** | MSE 0.012 vs baseline 0.156, std 0.36 |
| oneblock | 1 mask block | 0.4852 ± 0.0585 | MSE 0.048 vs 0.204, std 0.40 |
| sharedweights | EMA → 0.0 | 0.4813 ± 0.0335 | MSE 0.017 vs 0.170, std 0.34 |
| w600 | window 600 | 0.4784 ± 0.0372 | MSE 0.019 vs 0.137, std 0.32 |
| w1000 | window 1000 | 0.4646 ± 0.0573 | MSE 0.012 vs 0.080, std 0.24 |

Three configs (scattered 0.15, ratio 0.15–0.25, ratio 0.55–0.65) were **cut
by decision mid-study**: with the default already at the probe floor,
fine-tuning the masking ratio cannot answer the question the study is for,
and machine time was the binding constraint. Re-run them only if C7 makes
JEPA look worth tuning.

What the numbers say:

1. **No config separates from the random floor.** Every JEPA encoder predicts
   hidden-block embeddings far better than the mean baseline (7–17× lower
   latent MSE) — it genuinely learns weld dynamics — yet none of that is
   linearly readable as fault information. The failure is not collapse
   (embed_std healthy everywhere); the representation is just
   fault-irrelevant.
2. **Window length is exonerated.** The pre-registered too-short symptom
   (probe ≈ floor at 300) was present, but 600 didn't help and 1000 scored
   *below* the floor. There is no knee to pick — the knob doesn't matter.
   Caveat: Polito welds are uniformly T=1000, so window=1000 degenerates to
   one window per weld (1,381 training samples, 9-minute run) and its probe
   is the noisiest of the sweep.
3. **The EMA target is not load-bearing at this scale.** With shared weights
   (decay 0.0) the encoder did not collapse in 30 epochs (embed_std 0.34,
   MSE 10× under baseline). At 16k parameters on 2k welds, the classic JEPA
   failure mode simply didn't bite — and preventing it was never the
   bottleneck.

**Verdict for C7:** the entrant is the **default config** (best val probe,
0.4888), but the expectation set by this study is that masked recon retains
the crown — JEPA at this scale shows no probe-visible advantage over an
untrained encoder. C7's job is to make that official on `--split test`
(3 seeds, tie → incumbent), and the interesting comparison is masked recon
vs the floor, not JEPA vs masked recon.

### The C7 head-to-head (done 2026-07-16)

The decisive comparison (issue #15): JEPA default config vs masked recon on
the window diet (300/50, 30 epochs, full Polito), 3 seeds each, scored by
the C5 ruler on `--split test` — touched once. Driver:
`experiments/notebook/c7_headtohead.py`; per-seed scoring logs in
`notebook/logs/c7_test_scoring_s*.log`.

**A protocol discovery, made before any test-split look:** `--seed` is
salted into the split hash (`data/splits.py`), so seeds 1338/1339 train on a
*different train/test partition* than 1337. Scoring all six checkpoints on
the seed-1337 test split (the original plan) would have been asymmetric —
the 1338/1339 encoders pretrained on most of those welds (no labels leak,
pretraining is label-free, but the 1337 models never saw *their* test
welds). Fix, using existing code only: **seed-matched pairs** — for each
seed, one `compare_pretrains --seed <s> --split test` call scoring that
seed's JEPA + masked recon + random floor on the test split neither encoder
trained on. The verdict metric is the paired JEPA−masked-recon difference
across seeds.

| seed | test welds (faulty) | floor | JEPA | masked recon | JEPA − MR |
|---|---|---|---|---|---|
| 1337 | 308 (11) | 0.4967 ± 0.0456 | 0.5064 ± 0.0484 | 0.4903 ± 0.0526 | +0.016 |
| 1338 | 277 (12) | 0.4449 ± 0.0705 | 0.5284 ± 0.0798 | 0.4473 ± 0.0563 | +0.081 |
| 1339 | 294 (13) | 0.5020 ± 0.0623 | 0.5189 ± 0.0666 | 0.5167 ± 0.0690 | +0.002 |

(macro-F1 ± fold std; all encoders trained healthily — JEPA latent MSE
9–11× under mean-baseline with no collapse, masked recon ~90× under.)

**Verdict: tie → the incumbent masked recon keeps the Step 9+ warm-start
slot.** JEPA finished ahead on all three seeds directionally (mean +0.033),
but not beyond seed noise: the three paired differences spread 0.002–0.081
(std ≈ 0.042), two of the three sit far inside fold noise (±0.05–0.08), and
the 95% interval on the mean difference crosses zero comfortably. The
pre-registered rule ("masked recon keeps the slot unless JEPA clearly beats
it") therefore reads tie.

The deeper C7 finding matches C6: **neither objective separates from the
random-init floor with confidence** (masked recon mean −floor +0.004; JEPA
+0.037, all within noise). Both encoders demonstrably learn weld dynamics —
the pretraining metrics are far under their baselines — but on ~2k welds
with 79 faults, none of it is linearly readable as fault information. The
warm-start value of pretraining (Gate 0.5's actual claim) is untouched by
this; what C7 rules out is the *pretraining objective* being a lever worth
tuning at Polito scale. The old fault-head 0.14 stays a footnote — a
different ruler.

## What's next

- C0–C7 complete. The pretraining objective for the Step 9+ world-model
  warm-start is settled: **masked recon** (incumbent retained). Step 11+
  full-scale details sharpen after Gate 0 lands real arc-weld data.

## Decisions from the 2026-07-14 grilling (C4–C7 spec)

- **Both objectives train on the same diet**: `TrainWindows`, window=300,
  stride=50. Masked recon is re-trained on windows so the C7 head-to-head
  changes exactly one variable (the objective). The Step-6 whole-session
  checkpoint is kept as a historical reference column only. Polito welds are
  uniformly T=1000 frames (verified), so 300/50 gives 15 windows per weld
  (~29.6k samples from 1,976 welds).
- **Why keep masked recon at all**: it's the control group. JEPA's wins are
  from internet-scale data + big Transformers; this is 2k welds + a 16k-param
  GRU, masked recon already passed Gate 0.5 here, and JEPA has a failure mode
  (collapse) that yields a low loss and a useless encoder — undetectable
  without a comparison point.
- **window=300 is inherited (Gate 1.5), not chosen** — declared revisitable.
  Pre-registered diagnostics: too short ⇒ JEPA loss plateaus high, probe ≈
  baseline, 300→600 helps; too long ⇒ overfitting + noisy probes, 600→1000
  hurts. Readout: C5 probe score vs window length, pick the knee.
- **C5 = the ruler**: any transfer checkpoint → freeze encoder → embed
  ProbeWindows → mean-pool per weld → linear probe (GroupKFold by session) →
  macro-F1. Identical treatment for every contender; C6/C7 are C5 applied
  repeatedly.
- **C6 protocol**: one knob at a time from the default config — masking
  ratio/style, EMA vs shared-weights, window length {300, 600, 1000} (~8
  configs); 1 seed for the sweep, 3 seeds for finalists. Runs once as a study.
- **Testing seams (confirmed)**: zero new seams. Everything C4–C7 needs is
  testable at two existing boundaries: (1) the transfer-checkpoint contract in
  `pretraining/common.py` — a JEPA run must produce a checkpoint that
  round-trips through the contract and is indistinguishable from a masked-recon
  one except `objective="jepa"`; new tests join
  `backend/tests/test_world_model_pretraining.py`. Same seam covers C5: two
  contract checkpoints in, one comparable score per checkpoint out. (2) the
  `--tiny` CLI smoke — run the whole loop on the tiny preset, assert it
  completes and saves a valid checkpoint. Below those, only genuinely new
  functions get direct behavior tests (multi-block masking: exactly n blocks,
  ratio bounds hold; mean-pooling: one vector per weld; GroupKFold: no session
  straddles folds). C6/C7 are experiments, not code — no tests beyond what
  C5's harness carries; their outputs are `runs.csv` rows and doc updates.
