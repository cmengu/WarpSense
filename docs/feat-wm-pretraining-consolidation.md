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

## What's next

- **C4** — the JEPA training loop (mask_contiguous → predict → latent MSE →
  ema_update), CLI, and probe comparison vs masked_recon; saves through the
  same contract with `objective="jepa"`.
