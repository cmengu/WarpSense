# STEPS.md — World Model Build Plan (Single Source of Truth)

> Consolidated, ordered implementation plan with pseudocode for the WarpSense
> weld world model. This file is the working plan; update step status here.
>
> Companions: `FUTURE_PLANS_WORLD_MODELS.md` (gates + rationale),
> `WORLD_MODEL_IMPLEMENTATION_REFERENCE.md` (per-paper detail),
> `WORLD_MODEL_README.md` (public summary).
>
> Created: 2026-07-04 · Status legend: ⬜ not started · 🟨 in progress · ✅ done · ⛔ blocked

---

## 0. Decisions Locked In (from planning sessions)

| # | Decision | Value |
|---|---|---|
| D1 | Input channels | **6 scalars**: `volts`, `amps`, `angle_degrees`, `travel_angle_degrees`, `travel_speed_mm_per_min`, `heat_dissipation_rate_celsius_per_sec` (upgraded from the plan doc's "4 channels" — travel speed is a Goldak input, it belongs in the encoder) |
| D2 | Canonical session schema | `SessionTensor`: `x[T,6] float32` + `mask[T,6] bool` + `meta dict`. Every data source maps into this; nothing downstream sees raw formats |
| D3 | Missing-data policy | Availability mask carried end-to-end; encoder trained with **random channel dropout** so masked channels are native, not a special case |
| D4 | Mock data usage | Plumbing/dev ONLY. Any number computed on mock data is a pipeline check, never a result. No fabricated "realistic" data — real gaps stay visibly empty (Gate 0 principle) |
| D5 | Polito transfer strategy | **Per-channel stems + shared trunk + masked-channel training.** Polito (V/I/force, spot welding) activates 2–3 stems, pre-trains the shared trunk on real arc electrical dynamics. Warm start only — modest expectations |
| D6 | Latent structure | `z ∈ R^32 = [z_phys(4) ‖ z_free(28)]`. `z_phys` predefined by **wiring** (heat-diss decoder reads ONLY `z[0:4]`) + physics residual on `z[0:4]` only. `z_free` unnamed, unconstrained. Latent size is a config param; sweep {16,32,64} at Gate 2, pick smallest that stops improving |
| D7 | Physics escalation path (pre-registered) | If physics-ablation shows no OOD effect while heat-diss recon is good → switch `z_phys` dynamics to hard-coded heat equation + small learned correction (gray-box mechanism #3) |
| D8 | Compute | No local GPU. Everything through Gate 1.5 runs CPU/MPS. Every config has a `--tiny` preset (200 sessions, latent 16, 20 epochs) for local dev. Full training: Kaggle free GPU (~30h/wk) or Colab |
| D9 | Splits | Split by **session / generation parameters**, never by frame. Hold out entire domain-randomisation regions for OOD eval |
| D10 | Visualization | Cheap matplotlib timeline + `z_phys` trace built EARLY (dev tool + demo). Frontend (`FusionDepthChart.tsx`) later. Hard rule: risk bands only, **no mm figures in any UI until Gate 5** |
| D11 | Evidence discipline | Every training run appends one row to `experiments/runs.csv` (config hash, seed, metrics). Gate outcomes recorded in `experiments/gate_status.md` with number vs threshold |

Data on disk today: `data/public/polito_rsw/` (downloaded ✅ — 1,976 welds, V/I/force,
79 faulty / 1,897 good). Mock generator: `backend/data/mock_sessions.py` (emits all 6
channels). **No real weld data exists yet** (Gate 0 pending). No Goldak corpus exists yet
(correctly blocked on Gate 1).

---

## Existing Codebase Analysis (what the world model plugs into)

Verified against the code on 2026-07-04. The world model reuses four existing
assets and mirrors two existing patterns — it is an add-on, not a rewrite.

### `backend/models/frame.py` — the input contract
`Frame` (pydantic). Carries all 6 chosen channels (D1) **plus** `thermal_snapshots:
List[ThermalSnapshot]` (the 5×5 grid — our Gate 1.5 fallback sensor) and
`optional_sensors: Dict[str, bool]` availability flags. **Every sensor field is
`Optional`** — this is why D3 (mask policy) is mandatory, not nice-to-have.
`loader_esp32.py` and `loader_mock.py` both consume this model → one code path.

### `backend/data/mock_sessions.py` — the dev data source (D4: plumbing only)
Three generators: `_generate_stitch_expert_frames` (~1500 frames, 220-on/30-off
stitch pattern), `_generate_continuous_novice_frames`, and
`_generate_aluminium_parametric_frames` (parametric quality profiles — useful for
smoke-testing class balance). 100 Hz, all 6 channels emitted. It already runs a
physics-lite thermal grid (`_step_thermal_state`: power-scaled heating + conduction
+ angle bias) — heat_diss is *computed* from it, which is exactly why the real
sensor path must be bench-verified (Gate 0). Note: it is too clean (structured
profiles, mild noise) — a model can ace mock and fail on real arc noise; Polito
pre-training (Step 6) exists to counter this.

### `backend/features/session_feature_extractor.py` — free supervision (reuse as-is)
`SessionFeatures`: the 11 features, each causally documented in comments
(heat_input_mean / min_rolling / drop_severity / cv, angle_deviation_mean /
max_drift_1s, voltage_cv, …). `SessionFeatureExtractor.extract(frames)` +
`.to_vector()`. The world model consumes this THREE ways with zero changes:
`L_aux` targets (Step 8), the `concat(z_T, feats_11)` quality-head input (Step 7,
PHOENIX fusion), and the Gate 2 probe targets (Step 12). Do not reimplement.

### `backend/features/weld_classifier.py` — the incumbent + Gate 2 opponent
`WeldClassifier` (GBDT, persisted at `ml_models/weld_classifier.joblib`) →
`WeldPrediction {quality_class, confidence, all_probabilities}`. This is the
"probe latent→quality ≥ GBDT" bar in Gate 2. Its output schema is also the shape
our quality head should match, so downstream consumers need no adaptation.

### `backend/services/warp_service.py` — the pattern to mirror
`init_warp_components()` initialises singletons at app lifespan → 
`world_model_service.py` copies this (load checkpoint once, `get_world_model()`).
`analyse_session_stream()` is an SSE `AsyncGenerator` with `_sse(event)` framing and
a progress callback → the `world_model` event (Step 14) is one more `yield` in this
generator, after the existing report event. It already builds an
`al_feature_cache: dict[str, SessionFeatures]` — reuse it instead of re-extracting.

### `backend/routes/warp_analysis.py` — the surface
`run_analysis` returns `StreamingResponse` (SSE) — extend, don't add a new route.
`get_report`, `get_mock_sessions`, `get_quality_trend` exist; world-model fields get
appended to the report payload post-Gate 6 only.

### `backend/scoring/` — the safety floor (NEVER touched)
`rule_based.py` + `thresholds` produce `threshold_violations` — the deterministic
FNR = 0.000 layer. The plan's non-negotiable: this stays below every learned
component; the world model adds fields and never gates dispositions before Gate 6.

### `backend/eval/` — existing harness to extend, not replace
`eval_pipeline.py` / `eval_scenarios.py` hold the 24-scenario suite referenced by
Gate 6. `eval/eval_world_model.py` (Step 3) should import these scenarios rather
than duplicating them, adding the synthetic FN_RISK suite alongside.

### `backend/database/models.py` — where results persist
SQLAlchemy Base lives here; `WeldWorldModelResultModel` (Step 14) is added via an
Alembic migration (`backend/alembic/` already configured).

### Gaps the new code must fill (nothing existing covers these)
- No tensorised session representation anywhere → `SessionTensor` (Step 1).
- No train/val/test split logic anywhere (classifier trains on a parametric corpus
  from `generate_feature_dataset()` in-process) → `splits.py` (Step 1).
- No time-resolved output of any kind (all verdicts are per-session scalars) → the
  per-frame depth trajectory is genuinely new surface.
- Two session JSON formats exist: `data/mock/session_00{1,2}.json`
  (`meta/heatMap/torchAngleDeg/score` — frontend fixture, ignore for training) vs
  the `Frame` contract (canonical).

---

## Directory Layout (target)

```
backend/world_model/
├── config.py                # all knobs; --tiny preset; seeds
├── data/
│   ├── schema.py            # SessionTensor
│   ├── loader_mock.py       # dev only (D4)
│   ├── loader_polito.py     # data/public/polito_rsw → SessionTensor
│   ├── loader_esp32.py      # real captures (stub until Gate 0)
│   └── splits.py            # D9
├── simulator/               # goldak.py, weld_sim.py, defect_injector.py, calibration.py
├── architecture/            # stems.py, encoder.py, odefunc.py, decoder.py, world_model.py
├── baselines/gru_baseline.py
├── training/                # symlog.py, losses.py, train.py, pretrain_polito.py
├── inference/               # uncertainty.py, ood.py
├── eval/                    # eval_world_model.py, eval_counterfactual.py, probes.py
├── viz/timeline.py          # matplotlib dev visualization (D10)
└── experiments/             # runs.csv, gate_status.md
```

---

## The Steps

Two tracks run in parallel. **Track P (physical)** has lead times measured in weeks —
start it first even though it's not code. **Track C (code)** is fully unblocked
through Step 8.

```
Track P:  P1 ──────────────────────────────► Gate 0 ──► Step 9 (Gate 1) ─► ... 
Track C:  1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 ──────────────┘
```

---

### STEP P1 — Physical track: start the clocks ⬜ (no code; longest lead time)

- [ ] Submit **Intel Robotic Welding** dataset access request on HuggingFace (gated,
      days of latency; must be done from your account — cannot be automated).
- [ ] Arrange real-weld access: university lab / makerspace / welding school / hire a
      welder for a day. Define the 30-weld matrix: ~10 nominal, ~5 cold (low current),
      ~5 off-angle, ~5 fast-travel, ~5 stitch-restart abuse.
- [ ] Arrange sectioning + ~10% NaOH etch for ≥8 coupons (~$200 materials).
- [ ] Bench-test ESP32 → `POST /sessions` capture path with `esp32_firmware/` —
      one powered-on capture, even a dry run. Verify the heat-diss channel produces a
      usable signal on real hardware (in mock it is *computed*, not sensed).

**Done when (= Gate 0):** ≥30 real sessions captured; ≥8 coupons sectioned with
measured penetration; heat-diss verified on hardware.
**Kill criterion:** real sensor stats look nothing like mock → existing classifier
results are also invalid → re-baseline the whole project before world-model work.

---

### STEP 1 — Config, canonical schema, loaders, splits ✅ (2026-07-04)

> Implemented in `backend/world_model/{config.py, data/}`; tests in
> `backend/tests/test_world_model_step1.py` (8 passing; full 1,976-weld Polito
> load verified — 79 faulty / 1,897 good matches the published counts).
> Two facts learned from the data, now encoded in the loaders:
> (a) the Polito metadata triple (Car Body, Spot, Date) is NOT unique — 52 rows
> are same-day re-welds; all four CSVs share row order, so the loader aligns
> positionally and disambiguates session_ids with the row index. All welds are
> exactly T=1000. (b) the novice generator's docstring claims thermal frames
> every 20 frames, but the code emits every frame — heat_diss is dense in all
> mock kinds; only frame 0 is masked.

Everything downstream consumes `SessionTensor` and reads `config.py`. Build this first.

```python
# config.py
CHANNELS = ["volts", "amps", "angle_degrees", "travel_angle_degrees",
            "travel_speed_mm_per_min", "heat_dissipation_rate_celsius_per_sec"]
LATENT_DIM = 32          # sweep {16,32,64} at Step 12
PHYS_DIMS  = 4           # z[0:4] = z_phys (D6)
SEED = 1337
TINY = dict(n_sessions=200, latent=16, epochs=20)   # local dev preset (D8)

# data/schema.py
@dataclass
class SessionTensor:
    x:    np.ndarray   # [T, 6] float32, symlog applied later not here
    mask: np.ndarray   # [T, 6] bool — True where sensor value present (D3)
    meta: dict         # session_id, source ∈ {mock, polito, esp32, goldak},
                       # labels if any (quality class, fault bit, fusion depth[T])

# data/loader_mock.py    — call generate_* in backend/data/mock_sessions.py,
#                          Frame objects → SessionTensor. source="mock". DEV ONLY (D4).
# data/loader_polito.py  — read current/voltage/force CSVs (one weld per row;
#                          first 3 cols are metadata: Car Body, Welding Spot, Date;
#                          remaining ~2600 cols are the series — values arrive
#                          pre-normalised [0,1], so do NOT symlog/renormalise them
#                          with ESP32 stats). Map V→ch0, I→ch1; force → pretrain-only
#                          extra stem (carried in meta). mask=False for the 4 absent
#                          channels. label = fault bit from labels.csv, joined on the
#                          3 metadata cols.
# data/loader_esp32.py   — stub raising NotImplementedError until Gate 0 data lands.

# data/splits.py (D9)
def split_sessions(sessions, by="session_id", holdout_ood_regions=None):
    # hash(session_id) → train/val/test 70/15/15. NEVER split by frame.
    # for goldak corpus: also reserve param-space regions (e.g. plate_thickness
    # extremes) entirely for OOD eval.
```

**Done when:** `pytest` proves mock and Polito sessions round-trip through
`SessionTensor` with correct shapes/masks; splits are deterministic under `SEED`.

---

### STEP 2 — Dev visualization (build the eyes early) ✅ (2026-07-04)

> Implemented in `backend/world_model/viz/timeline.py` with a CLI
> (`python -m world_model.viz.timeline --source {mock,polito} ...`).
> Verified by eyeball: mock novice shows arc breaks + angle-drift sawtooth;
> Polito shows the two-pulse RSW profile with 4 channels greyed "absent".
> Supports overlay rows (depth_hat±std, depth_true, z_phys, risk bands) for
> Steps 3+. Deps live in `backend/world_model/requirements.txt` (matplotlib,
> torch 2.12 w/ MPS, torchdiffeq, scikit-learn — kept out of the production
> freeze until post-Gate 6).

```python
# viz/timeline.py
def plot_session(st: SessionTensor, extra: dict | None = None):
    # 6 stacked channel subplots vs time (masked spans greyed out)
    # if extra: overlay depth_hat[T] curve + confidence band,
    #           z_phys[T,4] traces, red/yellow/green risk bands
    # savefig(experiments/plots/{session_id}.png)
```

Used from Step 3 onward to eyeball every artifact (mock vs Polito vs Goldak vs real).
**Done when:** one command renders any `SessionTensor` from any loader.

---

### STEP 3 — GRU baseline + eval harness (build the bar first) ✅ (2026-07-04)

> Implemented: `architecture/stems.py` (per-channel Conv1d stems keyed by name,
> mask-aware MEAN, whole-channel dropout), `data/batch.py` (padding collation —
> padding IS mask=False), `baselines/gru_baseline.py` (stems→GRU(16→64)→h_T→
> quality+depth heads; normalizer stored as buffers, fit on train only),
> `eval/eval_world_model.py` (macro-F1 harness + runs.csv logging, D11),
> `training/train_gru.py` (CLI w/ --tiny). Tests: 6 in
> `tests/test_world_model_step3.py`. Plumbing run (`--tiny`, 200 mock sessions,
> 20 epochs, CPU ~2 min): test macro-F1 0.864, DEFECTIVE recall 1.0 — a
> pipeline check per D4, NOT a result; rows in `experiments/runs.csv`.

The boring baseline is the Gate 3 opponent — it must exist BEFORE the thing it measures.

```python
# baselines/gru_baseline.py
class GRUBaseline(nn.Module):
    # per-channel stems (shared with world model later — write in architecture/stems.py):
    #   stem_c = Conv1d(1→16, k=5, padding=2)  per channel; output [B,16,T] → transpose to [B,T,16]
    #   h_t = Σ_available stem_c(x[:,c]) / max(n_available, 1)  # MEAN not sum — else
    #         # embedding magnitude varies with sensor count; guard n=0 frames
    # trunk: GRU(16→64), take h_T
    # heads: quality logits (3), depth_mm (scalar; trained only when labels exist)

# eval/eval_world_model.py — model-agnostic harness:
def evaluate(model, test_sessions) -> dict:
    return {"quality_f1": ...,   # MACRO F1 — DEFECTIVE is the rare class that matters;
                                 # micro/accuracy would hide it
            "fusion_mae_mm": ...,                      # mae only if labels present
            "per_class_recall": ..., "n": ...}
# every call appends a row to experiments/runs.csv (D11)
```

Train on mock (plumbing check only, D4). Runs on CPU in minutes with `--tiny`.
**Done when:** harness produces a `runs.csv` row; GRU trains end-to-end on mock;
random-channel-dropout training works (drop each channel p=0.15).

---

### STEP 4 — Goldak simulator (aluminium) ✅ (2026-07-05)

> Implemented in `backend/world_model/simulator/{goldak.py, weld_sim.py}`;
> tests in `backend/tests/test_world_model_step4.py` (9 passing).
> `goldak.py`: double-ellipsoid `power_density` (verified: integrates to
> η·V·I over the workpiece half-space) + `fusion_zone_depth` via bisection on
> the Rosenthal thick-plate solution (Al 6061 constants; nominal 22 V/130 A/
> 250 mm·min⁻¹ → ~3.2 mm, plausible). `weld_sim.py`: `simulate_session` emits
> x[T,6] + clean `meta["fusion_depth_mm"][T]`; quasi-steady depth chased
> through a first-order lag (τ=0.5 s) so restarts dip (the Rosenthal
> transient limitation, papered over pending Gate 1); lumped pool temperature
> supplies heat_diss; cos-angle power penalty; sensor noise on readout only.
> `sample_params(seed)` gives deterministic domain randomisation for
> Steps 5/10. Viz: `--source goldak` renders with depth_true overlay —
> eyeballed: depth ↑ with I, ↓ with speed, dips at stitch restarts.
> C_THERMAL/K_COOLING remain placeholders until Gate 1 calibration.

```python
# simulator/goldak.py
class GoldakHeatSource:
    # params: ellipsoid semi-axes (a,b,c_f,c_r), eta=0.8, Al 6061 constants
    def power_density(x, y, z, t, V, I, v): ...        # W/m³ double-ellipsoid
    def fusion_zone_depth(V, I, v) -> float: ...       # Rosenthal-type root solve, m
    def cooling_rate(frames) -> np.ndarray: ...        # → heat_diss channel

# simulator/weld_sim.py
def simulate_session(params) -> SessionTensor:
    # params: I, V, travel_speed profile, angles profile, stitch schedule,
    #         plate_thickness, ambient_T, CTWD, material props, sensor noise σ
    # emits x[T,6] AND meta["fusion_depth_mm"][T]  ← the hidden-state label
    # KNOWN LIMITATION: Rosenthal is quasi-steady → worst at stitch transitions
    # (exactly the LOF moments). Gate 1 tests this; fallback = transient FEM (FEniCS).
```

**Done when:** simulated sessions plot sanely in viz (depth ↑ with I, ↓ with speed,
dips at stitch restarts); unit tests assert those three directions of change.

---

### STEP 5 — Gate 1.5: observability-ceiling test ✅ PASS (2026-07-05)

> Implemented in `eval/probes.py` (make_windows + oracle_ceiling + CLI w/
> --tiny); tests in `tests/test_world_model_step5.py` (3 passing: window
> alignment contract, session grouping, oracle-beats-mean sanity).
> **Full run: 1000 sessions → 29,000 windows, 5-fold GroupKFold-by-session
> HistGBR → ceiling MAE 0.109 ± 0.014 mm vs 1.0 mm threshold → PASS**
> (mean-predictor baseline 0.660 mm, so the sensors carry ~6× signal over
> chance). Recorded in `experiments/gate_status.md` + runs.csv row.
> Caveats: (a) pre-Gate-1 simulator — provisional until coupon calibration;
> (b) likely optimistic — sim depth is a deterministic lagged function of the
> sensed controls with no hidden material variation; real welds have
> unsensed state (fit-up, contamination, wire quality). The 9× margin under
> threshold is the buffer against that optimism. Green light for Steps 6–8.

Inside the simulator, where depth is KNOWN: how well can the 6 channels possibly
recover it? This bounds the entire project before architecture commitment.

```python
# eval/probes.py :: oracle_ceiling()
corpus = [simulate_session(random_params()) for _ in range(1000)]   # CPU, no defects needed
X = windows(corpus.x, w=100, stride=50)   # [N, 6*100]; stride, else 1.4M rows
y = depth_at_window_end(corpus)           # define alignment ONCE: depth at last frame
groups = session_id_per_window(corpus)
oracle = HistGradientBoostingRegressor()  # plain GBDT chokes on N×600 at this scale
ceiling_mae = cross_val(oracle, X, y, cv=GroupKFold(groups))
# ⚠ GroupKFold by SESSION is load-bearing: windows from one session in both train
# and test would leak and report a fake (too-low) ceiling → false green light
```

**PASS:** ceiling ≤ ~1.0 mm → proceed. **KILL:** > 1 mm → 6 scalars are physically
insufficient; add sensing (5×5 thermal snapshots already in the Frame model) and
re-run BEFORE building any world model. Record number in `gate_status.md`.

---

### STEP 6 — Gate 0.5: Polito pre-training (parallel, optional accelerator) ✅ PASS (2026-07-06)

> Done: `training/pretrain_polito.py` + `tests/test_world_model_step6.py` (6 tests).
> Held-out masked-recon MSE 0.00083 vs 0.074 mean-baseline (~90×) → kill criterion
> cleared. Transfer artifact `experiments/checkpoints/polito_pretrain_8a68998bf644.pt`
> = {stems[volts], stems[amps], trunk}; trunk weights are GRUCell-shaped for the
> Step 7 encoder (pinned by test). Fault head weak (macro-F1 0.14 under 79/1,897
> imbalance) — pretrain-only scaffolding, does not transfer. Force stem omitted:
> would not transfer, and the two channels that do are the point.

```python
# training/pretrain_polito.py
# model: stems (V, I only — force optional as pretrain-extra stem) + GRU/ODE-RNN trunk
# objectives: masked-reconstruction (mask 15% of timesteps, reconstruct) 
#             + fault-bit head (careful: 79/1897 imbalance → class weights or focal loss)
# transfer artifact: state_dict of {stems[volts], stems[amps], trunk}
```

**Done when:** trunk pre-trained on real electrical dynamics; recon works on held-out
Polito welds; weights saved for Step 8 init. **Kill criterion:** pipeline can't learn
real electrical dynamics at all → architecture problem exposed early — fix now.

---

### STEP 7 — World-model architecture ⬜

```python
# architecture/stems.py     — per-channel Conv1d stems, mask-aware sum (shared w/ GRU)
# architecture/encoder.py   — ODE-RNN, BACKWARD over frames:
#     h_i = GRUCell(stem(x_i, mask_i), h_{i+1})
#     h_i = h_i + dt * odefunc_enc(h_i)              # Euler fine here
#     mu0, log_sigma0 = Linear(h_0);  z0 = mu0 + eps * exp(log_sigma0)
# architecture/odefunc.py   — CONTROLLED ODE: dz/dt = f_θ(z, u(t), t)
#     # ⚠ CORRECTION over the plan docs (they write f_θ(z,t) — autonomous):
#     # weld dynamics are DRIVEN by the control channels. An autonomous ODE would
#     # force z0 to memorise the whole future input sequence, and counterfactuals
#     # ("correct the angle at second 7") would be IMPOSSIBLE — you cannot
#     # intervene on an input the dynamics never receives. u(t) is what the
#     # counterfactual explorer edits.
#     u(t) = interp(controls[T,5], t)     # volts, amps, both angles, travel_speed
#                                         # (piecewise-linear; frozen buffer per session)
#     f_θ = MLP(32 + 5 → 64 → 64 → 32, tanh)
#     odeint_adjoint(f, z0, t, method="dopri5")  # training — adjoint, else backprop
#                                                # through 1500 steps blows up memory
#     odeint(f, z0, t, method="rk4")             # inference (500ms p95 budget)
#     physics_residual(z_traj, u):        # D6 — z_phys ONLY
#         dz_learned = f_θ(z_t, u_t, t)[:, :4]        # evaluate f at trajectory pts
#         dz_target  = (u.V*u.I*0.8)/C_THERMAL - K_COOLING * z_t[:, :4]
#         return mse(dz_learned, dz_target)
#     # C_THERMAL, K_COOLING: placeholders until Gate 1 calibration fits them —
#     # L_physics is well-defined but physically meaningless before Gate 1
# architecture/decoder.py   — four heads over trajectory z_t [T,32]:
#     heat_diss_hat[t] = MLP_heat(z_t[:, 0:4])        # ← THE GROUNDING (D6). 
#                                                     #   input tensor is literally z[:, :4]
#     other5_hat[t]    = MLP_sens(z_t)                # volts/amps/angles/speed from full z
#     depth_hat[t]     = MLP_depth(z_t)               # per-frame → the timeline curve
#     quality_probs    = MLP_qual(concat(z_T, feats_11))   # PHOENIX feature fusion
#     feats_hat        = MLP_feat(z_T)                # free supervision (existing extractor)
# architecture/world_model.py — WeldWorldModel.infer(SessionTensor) → result dict
```

**Done when:** forward + backward pass on one `--tiny` mock batch on CPU; a shape test
asserts `MLP_heat` input dim == 4 (grounding cannot silently regress).

---

### STEP 8 — Training loop ⬜

```python
# training/symlog.py — symlog/symexp on ALL recon targets; free-nats KL (nats=1.0);
#                      PercentileNorm for the quality loss. NO KL balancing (fixed prior).
# training/losses.py
def total_loss(L, epoch):
    return ( L.recon                                   # always on
           + fade(epoch,  50, 150) * 0.10 * L.physics  # sigmoid fade-in
           + fade(epoch, 150, 250) * 1.00 * L.quality
           + fade(epoch,   0, 100) * 0.05 * L.aux      # 11 engineered features
           + 0.001 * L.kl )
# training/train.py — init stems/trunk from Step 6 weights; channel dropout p=0.15;
#                     seed everything; append runs.csv row per epoch-block (D11)
```

**Done when:** loss curves on `--tiny` mock corpus show recon ↓ and z_phys traces in
viz rise with arc-on / decay at arc-off. (Plumbing check — mock, so not a result. D4)

---

—— everything below needs real data (Gate 0) or a validated simulator (Gate 1) ——

### STEP 9 — Gate 1: simulator calibration vs reality ⛔ blocked on Gate 0

```python
# simulator/calibration.py
# (a) sensor moments: sim {V, I, heat_diss} stats vs REAL sessions within ±15%
# (b) fusion physics: Goldak depth vs sectioned coupons within ±25%
# (c) direction-of-change at TRANSIENTS: ↑I→↑depth, ↑speed→↓depth, restart→↓depth
# fit C_THERMAL, K_COOLING here (feeds back into physics_residual)
```
**KILL:** (c) fails → Rosenthal insufficient → transient FEM (FEniCS) or stop.

### STEP 10 — Generate the 5,000-session corpus ⛔ blocked on Gate 1

```python
# simulator/defect_injector.py — LOF = cold window; LOP = angle + power deficit
# weld_sim.py corpus loop: domain randomisation over material props, ambient T,
# CTWD, travel speed, plate thickness, sensor noise (else silent sim-overfit).
# splits.py reserves whole param regions as OOD holdout (D9).
```

### STEP 11 — Full training run (cloud GPU) ⛔ after Step 10

Same `train.py`, full config, 300 epochs, on Kaggle/Colab GPU (D8). GRU baseline
retrained on the same corpus — same splits, same harness.

### STEP 12 — Gates 2 + 3: earn the complexity ⛔ after Step 11

```python
# eval/probes.py    — linear probe z→11 features (beats mean baseline?);
#                     probe z→quality vs GBDT on features; latent sweep {16,32,64}
# eval/eval_counterfactual.py — monotonicity battery: edit u(t) (the control buffer),
#                     re-integrate the SAME z0 through the ODE, compare depth curves.
#                     Pairs: ↑V·I→↑depth, ↑speed→↓depth, ↑angle dev→↓depth.
#                     PASS ≥95% of pairs. (Only possible because the ODE is
#                     controlled — see Step 7 correction.)
# physics ablation  — train w/ and w/o L_physics; compare on OOD holdout.
#                     Null effect → invoke D7 escalation (hard-coded z_phys dynamics)
```
**KILL (Gate 3):** GRU matches world model on quality F1 AND fusion MAE → **ship the
GRU**, defer the world model, write it in the README.

### STEP 13 — Gate 4: transfer to real ⛔ blocked on Gate 0 + Step 12

Fine-tune on the ~30 real sessions with `L_recon + L_aux + L_physics` only (no quality
head — too few labels). Synthetic replay buffer mixed in (forgetting guard).
**PASS:** feature-decoder R² ≥ 0.5 on real; latent KL syn↔real < 0.5 nats;
recon ≤ 2× synthetic error.

### STEP 14 — Gate 5: coupon truth → then UI ⛔ blocked on Step 13

Fresh ≥10 coupons, never used in calibration. Predicted vs measured depth,
photographed, in the README — the project's credibility artifact.
**PASS:** MAE ≤ 1.0 mm, direction ≥90% → mm figures allowed in UI.
Until then: `FusionDepthChart.tsx` + `WorldModelCard.tsx` ship with **risk bands only**.
Backend integration: `services/world_model_service.py`, SSE `world_model` event,
`WeldWorldModelResultModel` table (per plan §7).

### STEP 15 — Gate 6: shadow deployment ⛔ blocked on Step 14

2–4 weeks silent alongside the existing pipeline; every disagreement manually
reviewed; FNR = 0.000 on expanded eval; OOD detector wired (`inference/ood.py` —
recon error / latent Mahalanobis); p95 ≤ 500 ms with rk4.
**KILL:** any missed defect in shadow mode → not deployable, full stop.
(Streaming/edge student = Workstream S, post-Gate 3, separate effort.)

---

## Immediate next actions (this week)

1. **You:** submit Intel HF access request; start arranging weld-shop access (P1).
2. **Code:** Step 1 (schema + loaders + splits) → Step 2 (viz) → Step 3 (GRU + harness).
3. Then Step 4–5: Goldak + the observability ceiling — the number that tells us
   whether this whole architecture is worth building.
