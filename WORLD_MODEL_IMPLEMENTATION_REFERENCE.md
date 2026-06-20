# WarpSense World Model — Complete Implementation Reference & Critical Analysis

> The full technical reference for the world-model pivot: every research paper and the
> exact component taken from it, the corrected architecture, file-by-file implementation
> map, training pipeline, integration plan, the complete critical analysis that reshaped
> the plan, the go/no-go gates, data strategy, MVP product shape, and anti-fluff charter.
>
> **Companion document:** `FUTURE_PLANS_WORLD_MODELS.md` is the living plan — gate
> status updates happen there. This file is the deep reference.
>
> All corrections from the 2026-06-11 critical review are applied inline in Part A and
> marked **[CORRECTED]**. The original flaws are preserved verbatim in Part B so the
> reasoning is auditable.

---

# PART A — IMPLEMENTATION REFERENCE

## A1. The Research Paper Stack

Nine papers. Each contributes exactly one component. Nothing is implemented in full.

---

### Paper 1 — Goldak, Chakravarti & Bibby (1984)
**"A New Finite Element Model for Welding Heat Sources"**
*Metallurgical Transactions B, Vol. 15, pp. 299–305*

**What it gives you:** the equations to synthesise training data, and the only source
of ground truth for a signal the ESP32 physically cannot measure — fusion zone depth.

The double-ellipsoid heat source is the industry-standard welding thermal model
(basis of Simufact, Sysweld). Power density deposited by the arc:

```
q(x,y,z,t) = (6√3 · Q · f_f) / (π√π · a · b · c_f) · exp(−3x²/c_f² − 3y²/a² − 3z²/b²)
```

where `Q = V × I × η` (η ≈ 0.8 for GMAW aluminium) and `a, b, c_f, c_r` are the
ellipsoid semi-axes, calibrated per material/process.

**What you implement:**

```python
# backend/world_model/simulator/goldak.py
class GoldakHeatSource:
    # .power_density(x, y, z, t, V, I, v)  → W/m³
    # .fusion_zone_depth(V, I, v)          → metres (Rosenthal-type root solve)
    # .cooling_rate(frames)                → °C/s per frame
    #                                        maps to heat_dissipation_rate_celsius_per_sec
```

**[CORRECTED] Calibration step (mandatory, two parts):**
1. **Sensor-channel calibration** — moment-match the simulator's `{volts, amps,
   heat_dissipation}` statistics against **real ESP32 sessions** (NOT the mock
   generator — see Part B fatal flaw). Tolerance: ±15%.
2. **Fusion-physics calibration** — Goldak-predicted penetration must match
   **physically sectioned coupons** within ±25%, with direction-of-change correct
   (↑current → ↑depth, ↑travel speed → ↓depth, stitch restart → ↓depth).
   Moment-matching sensor statistics alone calibrates the observable channels, not
   the fusion geometry — you can match sensor moments perfectly and still have depth
   wrong by 2×. Only cut-and-etch coupons calibrate the part that matters.

**Known limitation to budget for:** Rosenthal-type solutions assume quasi-steady
state and ignore latent heat of fusion. Both assumptions break at **stitch
transitions** — which are precisely the LOF-risk moments (our own
`heat_input_drop_severity` feature targets them). Gate 1 explicitly tests transient
direction-of-change; if Rosenthal fails it, upgrade to transient FEM (FEniCS/sfepy)
before generating any training data.

---

### Paper 2 — Raissi, Perdikaris & Karniadakis (2019)
**"Physics-Informed Neural Networks"**
*Journal of Computational Physics, Vol. 378, pp. 686–707*

**What it gives you:** one extra loss term that penalises physically impossible
dynamics. In thermophysical domains, encoding the governing PDE as a loss reduces
required labelled data by 10–100× — the single result that makes this project
feasible at WarpSense's data scale.

**What you implement:**

```python
# backend/world_model/training/losses.py
def physics_loss(z_phys, dz_phys_dt_learned, V, I):
    # Simplified Goldak heat balance on the weld centreline:
    #   dT/dt = Q/(rho * cp * V_melt) − k_cooling * (T − T_ambient)
    Q_arc = V * I * 0.8                      # eta = 0.8, GMAW aluminium
    dz_physics = Q_arc / C_THERMAL - K_COOLING * z_phys
    return F.mse_loss(dz_phys_dt_learned, dz_physics)

# C_THERMAL = rho*cp*V_melt for Al 6061 (normalised units)
# K_COOLING fit to real-session cooling signatures during Gate 1 calibration
```

**[CORRECTED] Grounding requirement — without this the loss is decorative:**
Penalising one latent dimension for violating heat balance does *not* force the
network to use that dimension for thermal state. Gradient descent will satisfy the
constraint on the designated dim while routing real thermal information through the
unconstrained dims — the loss goes to zero without constraining anything
("physics-washing").

The fix is architectural: structure the latent as `z = [z_phys(4) ‖ z_free(28)]`
and wire the sensor decoder so that `heat_dissipation_rate` is reconstructed
**exclusively from `z_phys`** (a separate head whose input is only the z_phys
block). Now thermal information *must* flow through the constrained dims or
reconstruction fails. The physics residual applies to `z_phys` only.

**What to skip:** the full PINN framework (collocation points, boundary-condition
losses, PDE-solving mode). One residual term on a grounded latent block is the
entire take.

---

### Paper 3 — Chen, Rubanova, Bettencourt & Duvenaud (2018)
**"Neural Ordinary Differential Equations"** — *NeurIPS 2018*

**What it gives you:** the `torchdiffeq` library. The weld is a continuous physical
process — there is no discrete "next frame"; the metal evolves between 10ms samples
according to the heat equation. Neural ODEs model `dz/dt = f_θ(z, t)` directly.

**What you implement:**

```python
# backend/world_model/architecture/odefunc.py
from torchdiffeq import odeint            # the entire dependency from this paper

class WeldODEFunc(nn.Module):
    # f_θ(z, t) — learned dynamics
    # Architecture: MLP 32 → 64 → 64 → 32, tanh activations
    # Training:  odeint(odefunc, z0, t_span, method='dopri5')   # adaptive RK, stiff-safe
    # Inference: odeint(odefunc, z0, t_span, method='rk4')      # [CORRECTED] fixed-step
```

**[CORRECTED]:** `dopri5` adaptive stepping through stiff thermal-spike dynamics can
blow up function-evaluation counts and threatens the 500ms p95 latency gate. Use
`dopri5` for training accuracy, fixed-step `rk4` at inference.

Install: `pip install torchdiffeq`.

---

### Paper 4 — Rubanova, Chen & Duvenaud (2019)
**"Latent ODEs for Irregularly-Sampled Time Series"** — *NeurIPS 2019*

**What it gives you:** the encoder — how to compress a 1,500-frame session into a
latent initial state. This architecture (not Dreamer's RSSM) is the right fit
because RSSM assumes a discrete-step MDP while the weld is continuous-time physics.

The ODE-RNN encoder processes the session **backwards** (frame 1500 → frame 0). At
each step a GRU cell ingests the observation; an ODE step evolves the hidden state
between observations. Output: `z_0 ~ N(μ₀, σ₀)` — a distribution over the weld's
initial latent state. The Neural ODE then rolls `z_t` forward through the session.

**What you implement:**

```python
# backend/world_model/architecture/encoder.py
class ODERNNEncoder(nn.Module):
    # Backward pass over x_1500, x_1499, ..., x_0:
    #   h_i = GRUCell(x_i, h_{i+1})        # observe sensor frame
    #   h_i = h_i + dt * odefunc(h_i)      # ODE step between frames (Euler fine here)
    # Output:
    #   mu_0, log_sigma_0 = Linear(h_0)
    #   z_0 ~ N(mu_0, exp(log_sigma_0))    # reparameterisation trick
```

**What to skip:** irregular-sampling interpolation (ESP32 is fixed 100Hz); Poisson
process likelihoods; full ELBO derivation — use the standard VAE ELBO with
`L_KL = KL(N(μ₀, σ₀) ‖ N(0, I))`.

---

### Paper 5 — Micheli, Alonso & Fleuret (2022)
**"Transformers are Sample-Efficient World Models" (IRIS)**
*ICLR 2023 — top 5% notable paper · github.com/eloialonso/iris*

**What it gives you:** the VQ-VAE tokenizer, adapted from image patches to sensor
windows — the streaming/real-time inference path.

Each 100-frame sensor window (4 channels × 100 frames) maps to one discrete token
from a 512-entry codebook. A 1,500-frame session becomes 15 tokens.

**What you implement:**

```python
# backend/world_model/architecture/tokenizer.py
class SensorVQVAE(nn.Module):
    # Encoder:  1D-Conv([4, 100]) → z_e ∈ R^64
    # VQ layer: z_q = codebook[argmin_k ||z_e − e_k||²]   # K=512, dim 64, EMA updates
    # Decoder:  MLP(z_q) → x̂ ∈ R^[4×100]
    #
    # L_vqvae = L_recon + 0.25 * ||sg(z_e) − z_q||²       # commitment weight from IRIS
```

**[CORRECTED] Sequencing:** the original reference fed both the ODE-RNN encoder
(offline) and the VQ tokenizer (streaming) into the same dynamics model — incoherent,
since a `z_0` Gaussian and a discrete token sequence are not interchangeable latent
spaces. Resolution: **the MVP is post-session only (ODE-RNN encoder alone)**, which
matches the current product surface (`POST /sessions/:id/analyse`). The streaming
tokenizer is Phase 2, **distilled from the trained world model** (teacher–student),
not co-trained.

**What to skip:** the GPT-style transformer dynamics (replaced by Neural ODE); the
image encoder/decoder; the Atari training loop.

---

### Paper 6 — Hafner et al. (2023)
**"Mastering Diverse Domains through World Models" (DreamerV3)**
*arXiv 2301.04104 · github.com/danijar/dreamerv3*

**What it gives you:** training-stability tricks from Appendix A that are critical on
small datasets. Sensor channels span orders of magnitude (volts 20–30, amps 160–220,
heat_diss 0–120, heat_input 3,000–5,000); unconstrained, high-magnitude targets
dominate the gradient.

**What you implement:**

```python
# backend/world_model/training/symlog.py

# 1. symlog — apply to ALL reconstruction targets
def symlog(x):  return torch.sign(x) * torch.log(torch.abs(x) + 1)
def symexp(x):  return torch.sign(x) * (torch.exp(torch.abs(x)) - 1)

# 2. Free nats — prevents posterior collapse on small data
def kl_loss(mu, log_sigma, free_nats=1.0):
    kl = -0.5 * (1 + 2*log_sigma - mu**2 - torch.exp(2*log_sigma))
    return torch.clamp(kl, min=free_nats).mean()

# 3. Percentile normalisation — for the quality supervision signal
class PercentileNorm:
    # Running 5th/95th percentile of prediction errors; normalise the quality loss
    # by this range so rare quality labels don't destabilise training.
```

**[CORRECTED] KL balancing is dropped.** DreamerV3's KL balancing (α = 0.8) requires
a *learned* prior network to balance the posterior against. The Latent ODE uses a
fixed N(0, I) prior — there is nothing to balance. Keep symlog, free nats, and
percentile normalisation; drop balancing (or revisit if a learned sequence prior is
added later).

**What to skip:** RSSM, discrete categorical latents, actor-critic, all benchmark
code.

---

### Paper 7 — PHOENIX (2025)
**"A Physics-Informed and Data-Driven Framework for Robotic Welding in Manufacturing"**
*Nature Communications, Vol. 16, May 2025 · github.com/iVPPA/PHOENIX*

**What it gives you:** the only published system that does what we are building —
physics-informed welding state prediction. 98% accuracy at 50ms horizon on VPPA
welding. Study Figure 2 of the paper as the architecture pattern.

**What you take:**
- Sliding-window accumulation of temporal sensor data (→ our 100-frame windows)
- **Feature-level fusion**: concatenate `[z_T, engineered_features(11)]` before the
  quality head — learned representation *plus* the existing hand features, not
  either/or
- Confidence-bound output: quality-distribution entropy as the uncertainty signal

**[CORRECTED] Expectation management:** PHOENIX's input included melt-pool
*imaging* — thousands of pixels of direct visual observation. We have 4 scalar
channels; the information content is orders of magnitude lower. Their 98% is **not**
our ceiling estimate. Gate 1.5 (observability-ceiling test) measures our actual
ceiling empirically before architecture commitment.

**What to skip:** the X-ray pipeline, VPPA-specific process parameters, robot
control loop.

---

### Paper 8 — Andreoli, Meissner et al. (2025)
**"Improved Training Strategies for PINNs using Real Experimental Data in Aluminum
Spot Welding"** — *arXiv 2508.04595*

**What it gives you:** the progressive loss-fading schedule — the training-loop
modification that makes multi-objective training converge on small data. Adding all
loss terms at epoch 0 lets the physics constraint overwhelm reconstruction before
the encoder has learned anything.

**What you implement:**

```python
# backend/world_model/training/losses.py
import math

def fade(epoch, start, end):
    if epoch < start: return 0.0
    if epoch > end:   return 1.0
    p = (epoch - start) / (end - start)
    return 1 / (1 + math.exp(-8 * (p - 0.5)))          # smooth sigmoid fade-in

def total_loss(L_recon, L_physics, L_quality, L_aux, L_KL, epoch):
    return (
        L_recon                                         # always on — the foundation
      + fade(epoch,  50, 150) * 0.10 * L_physics        # heat balance, ep 50→150
      + fade(epoch, 150, 250) * 1.00 * L_quality        # quality labels, ep 150→250
      + fade(epoch,   0, 100) * 0.05 * L_aux            # engineered features, ep 0→100
      + 0.001 * L_KL                                    # free-nats KL, always on
    )
```

---

### Paper 9 — Settles (2012)
**"Active Learning"** — *Morgan & Claypool Synthesis Lectures*

**What it gives you:** the labelling-loop design — uncertainty sampling. You don't
need labels on all real sessions, only the most *informative* ones.

**What you implement:**

```python
# backend/world_model/inference/uncertainty.py
def session_uncertainty(quality_probs) -> float:
    return float(-sum(p * math.log(p + 1e-8) for p in quality_probs))
    # max entropy for 3 classes = log(3) ≈ 1.099 nats
    # REVIEW_THRESHOLD = 0.65 nats (tuned to catch borderline cases like TC_019)
```

**[CORRECTED] Two operational requirements the original reference omitted:**
1. **Label source must be defined**: LOF is subsurface — visual inspection cannot
   confirm it. Labels come from UT or destructive sectioning; budget the cost per
   label and name who performs it.
2. **Catastrophic-forgetting guard**: fine-tuning the quality decoder on tiny real
   batches (every ~10 labels) requires a **synthetic replay buffer** mixed into each
   fine-tune (or freeze the encoder and adapt only the head).

Also note: softmax entropy is miscalibrated under distribution shift — low entropy
does *not* mean in-distribution. A separate OOD detector is required (see A3,
`inference/ood.py`).

---

## A2. The Complete Architecture (Corrected MVP)

Post-session analysis only. Streaming is Phase 2 (distilled tokenizer).

```
                  ESP32 SENSOR STREAM
            [volts · amps · angle · heat_diss]
                4 channels × 1500 frames
                         │
              ┌──────────▼──────────┐
              │   ODE-RNN Encoder   │   (Rubanova 2019)
              │  backward GRU pass  │
              │  frame 1500 → 0     │
              │  + ODE between obs  │
              └──────────┬──────────┘
                         │
            z_0 ~ N(μ₀, σ₀) ∈ R³²
            structured: z = [z_phys(4) ‖ z_free(28)]      [CORRECTED]
                         │
              ┌──────────▼──────────┐
              │  Neural ODE         │   (Chen 2018)
              │  dz/dt = f_θ(z,t)   │
              │  MLP 32→64→64→32    │
              │  dopri5 train /     │
              │  rk4 inference      │   [CORRECTED]
              │                     │
              │  + physics residual │   (Raissi 2019)
              │    on z_phys only   │   [CORRECTED]
              └──────────┬──────────┘
                         │
              z_t for all t ∈ [0, T]
                         │
     ┌───────────┬───────┴────────┬────────────────┐
     │           │                │                │
┌────▼─────┐ ┌───▼────────┐ ┌─────▼───────┐ ┌──────▼───────┐
│ Sensor   │ │ Quality    │ │ Fusion-     │ │ Feature      │
│ Decoder  │ │ Decoder    │ │ Depth       │ │ Decoder      │
│          │ │            │ │ Decoder     │ │              │
│ heat_diss│ │ concat(z_T,│ │             │ │ MLP(z_T →    │
│ from     │ │ 11 feats)  │ │ MLP(z_T →   │ │  11 features)│
│ z_phys   │ │ → P(GOOD/  │ │  depth_mm)  │ │              │
│ ONLY;    │ │   MARG/    │ │             │ │ L_aux: MSE vs│
│ V/A/angle│ │   DEF)     │ │ L_fusion:   │ │ existing     │
│ from full│ │ (PHOENIX   │ │ MSE vs      │ │ extractor —  │
│ z        │ │  fusion)   │ │ Goldak GT   │ │ free signal, │
│          │ │            │ │ (synthetic  │ │ no labels    │
│ L_recon  │ │ L_quality  │ │  only)      │ │ needed       │
│ all data │ │ labelled   │ │             │ │ all data     │
└──────────┘ └────────────┘ └─────────────┘ └──────────────┘

TRAINING SIGNAL SOURCES
──────────────────────────────────────────────────────────────
L_recon    ← all synthetic + all real   (self-supervised, no labels)
L_physics  ← all synthetic + all real   (physics is always true)
L_aux      ← all synthetic + all real   (features computed, no labels)
L_fusion   ← synthetic only             (ground truth from Goldak)
L_quality  ← synthetic labels + labelled real sessions only
L_KL       ← always on                  (free nats = 1.0)
```

All reconstruction targets in symlog space (DreamerV3). Loss schedule per Paper 8.

---

## A3. File-by-File Implementation Map

```
backend/world_model/                     ← new top-level module
│
├── simulator/
│   ├── goldak.py                        ← Paper 1
│   │     GoldakHeatSource
│   │     .power_density(x,y,z,t,V,I,v)  → W/m³
│   │     .fusion_zone_depth(V,I,v)      → metres
│   │     .cooling_rate(frames)          → °C/s per frame
│   ├── weld_sim.py                      ← Paper 1
│   │     WeldSimulator.generate(n=5000) → List[(frames_dict, ground_truth)]
│   │     ground_truth: fusion_depth_t, quality_label, defect_type, defect_window
│   │     Domain randomisation: material props, ambient temp, CTWD, travel
│   │     speed, plate thickness, sensor noise  [CORRECTED — mandatory]
│   ├── defect_injector.py               ← Paper 1
│   │     LOFInjector — reduce Q_arc in [t_start, t_end] window
│   │     LOPInjector — inject angle deviation + penetration deficit
│   └── calibration.py                   ← Paper 1  [CORRECTED]
│         moment_match(REAL_sessions, simulator)        — sensor channels ±15%
│         coupon_validate(sectioned_coupons, simulator) — penetration ±25%
│
├── architecture/
│   ├── encoder.py                       ← Paper 4
│   │     ODERNNEncoder: x[B,T,4], t[T] → mu_0[B,32], log_sigma_0[B,32]
│   ├── odefunc.py                       ← Papers 3 + 2
│   │     WeldODEFunc.forward(t, z)                → dz_dt[B,32]
│   │     WeldODEFunc.physics_residual(z_phys, dz, V, I) → scalar loss
│   ├── decoder.py                       ← Papers 6 + 7  [CORRECTED]
│   │     SensorDecoder   — heat_diss head wired to z_phys ONLY (grounding)
│   │     QualityDecoder  — MLP(concat(z_T[32], feats[11])) → 3 classes
│   │     FusionDecoder   — MLP(z_T) → depth_mm
│   │     FeatureDecoder  — MLP(z_T) → 11 SessionFeatures
│   ├── tokenizer.py                     ← Paper 5  [Phase 2 only — distilled]
│   │     SensorVQVAE: [B,4,100] → token_ids[B] + z_q[B,64] + x̂[B,4,100]
│   └── world_model.py
│         WeldWorldModel.forward(frames) → WeldWorldModelOutput
│         WeldWorldModel.infer(frames)   → WeldWorldModelResult (API surface)
│
├── baselines/                           [CORRECTED — new, Gate 3 requirement]
│   └── gru_baseline.py
│         Plain supervised GRU / 1D-CNN on raw frames → quality + fusion depth.
│         The boring baseline the world model must beat to justify existing.
│
├── training/
│   ├── symlog.py                        ← Paper 6 (KL balancing dropped)
│   ├── losses.py                        ← Papers 2 + 6 + 8
│   │     physics_loss, kl_loss(free_nats), fade(), total_loss()
│   └── train.py                         ← Papers 4 + 8
│         --phase tokenizer | synthetic | real-finetune | quality-finetune
│         quality-finetune mixes a synthetic replay buffer  [CORRECTED]
│
├── inference/
│   ├── uncertainty.py                   ← Paper 9
│   │     session_uncertainty() → nats; REVIEW_THRESHOLD = 0.65
│   ├── ood.py                           [CORRECTED — new]
│   │     OOD detector: reconstruction-error threshold / latent Mahalanobis.
│   │     Non-aluminium / non-MIG inputs get FLAGGED, never silently predicted.
│   └── streaming.py                     ← Paper 5  [Phase 2]
│         StreamingInference.update(window) → StreamingResult
│
└── eval/
    ├── eval_world_model.py
    │     24 existing scenarios + expanded synthetic FN_RISK suite
    │     fusion-depth error vs Goldak GT (synthetic) AND vs coupons (real)
    │     uncertainty calibration (ECE)
    │     observability-ceiling oracle test (Gate 1.5)
    └── eval_counterfactual.py           [CORRECTED — new]
          Monotonicity battery: ↑V·I→↑depth, ↑speed→↓depth, ↑angle dev→↓depth
          ≥95% of sampled counterfactual pairs must satisfy (Gate 3)
```

---

## A4. Integration With the Existing WarpSense Stack

### Backend — one new service, one extended route

**New: `backend/services/world_model_service.py`** (mirrors `warp_service.py`):

```python
_world_model: WeldWorldModel | None = None    # initialised in main.py lifespan()

def get_world_model() -> WeldWorldModel:
    return _world_model

def analyse_with_world_model(frames: list[dict]) -> WeldWorldModelResult:
    return get_world_model().infer(frames)
```

**Extend `routes/warp_analysis.py`** — append world-model output to the existing
SSE stream in `POST /api/sessions/{session_id}/analyse`:

```python
wm_result = analyse_with_world_model(frames)
yield f"data: {json.dumps({'type': 'world_model', 'result': wm_result.to_dict()})}\n\n"
```

**New PostgreSQL model** in `database/models.py`:

```python
class WeldWorldModelResultModel(Base):
    __tablename__ = "weld_world_model_results"
    id                = Column(UUID, primary_key=True)
    session_id        = Column(String, ForeignKey("sessions.id"))
    fusion_depth_mm   = Column(JSON)      # per-frame estimates
    quality_class     = Column(String)    # GOOD / MARGINAL / DEFECTIVE
    confidence        = Column(Float)
    uncertainty       = Column(Float)     # entropy, nats
    review_required   = Column(Boolean)   # entropy > 0.65 nats
    ood_flag          = Column(Boolean)   # [CORRECTED] OOD detector result
    latent_trajectory = Column(JSON)      # z_t for UI visualisation
    created_at        = Column(DateTime)
```

### Frontend — two new components

**`FusionDepthChart.tsx`** — the weld timeline (Recharts, matches
`WelderQualityTrend` style): time on X (0–15s), estimated fusion depth on Y, AWS
D1.1 minimum as a reference line, confidence band as shaded area, colour-coded
risk regions (green/yellow/red) per second.

**`WorldModelCard.tsx`** — alongside `QualityReportCard`: depth estimate,
plain-English uncertainty label ("High confidence" / "Review recommended"),
"failed at second X.X" derived from the first red region.

**[CORRECTED] Hard UI restriction:** until Gate 5 passes (coupon validation), the
chart shows **qualitative risk bands only — no millimetre figures**. A
wrong-but-precise number in front of a quality engineer is the most dangerous
output this system can produce.

### The safety floor — unchanged, forever

`report.disposition` continues to come from the existing pipeline. The
deterministic threshold override stays below every learned component, exactly as it
sits below the LLM layer today. The world model adds fields; it does not gate
dispositions until Gate 6 passes.

---

## A5. Training Pipeline Step by Step

```
STEP 0 — REALITY (Gate 0 — blocks everything)                    [CORRECTED]
  Collect ≥30 real ESP32 sessions (incl. deliberate defects).
  Section + etch ≥8 coupons; measure penetration.
  Bench-verify the heat-dissipation channel on real hardware.
  Parallel (Gate 0.5): pre-train encoder on public real datasets
  (SmartData@Polito RSW — open; Intel Robotic Welding — request access).

STEP 1 — Goldak simulator (Gate 1, 1.5)
  Implement goldak.py; calibrate sensor moments vs REAL sessions (±15%)
  AND penetration vs coupons (±25%, direction-of-change correct).
  Run the observability-ceiling oracle test (Gate 1.5):
  best-possible regressor from 4 sim channels → sim fusion depth.
  Ceiling > ~1.0mm → add sensing before proceeding.
  Output: 5,000 domain-randomised synthetic sessions.
  Time: ~1–2 weeks code + the physical calibration lead time.

STEP 2 — Boring baseline FIRST (Gate 3 prep)                     [CORRECTED]
  Train baselines/gru_baseline.py on the synthetic corpus.
  It is the bar — build the bar before the thing it measures.
  Time: ~3 days.

STEP 3 — World model on synthetic (Gates 2, 3)
  Loss schedule: L_recon always; L_aux ep 0–100; L_physics ep 50–150;
  L_quality ep 150–250; free-nats KL always. 300 epochs.
  Pass: probes beat hand features; beats GRU on held-out F1 + fusion MAE;
  counterfactual monotonicity ≥95%; physics-ablation shows measurable effect.
  Time: ~4h GPU / ~24h CPU per run.

STEP 4 — Sim-to-real fine-tune (Gate 4)
  ONLY after Gate 0 — on the ≥30 REAL sessions.
  L_recon + L_aux + L_physics only (no L_quality — real labels don't exist yet).
  Pass: feature-decoder R² ≥ 0.5 on real; latent KL synthetic↔real < 0.5 nats.
  Time: ~30 min.

STEP 5 — Fusion validation (Gate 5)
  Fresh ≥10 coupons. Predicted vs measured depth, photographed, in the README.
  Pass: MAE ≤ 1.0mm; direction-of-change ≥90% correct.
  Until passed: no mm in UI.

STEP 6 — Active-learning loop (ongoing)
  entropy > 0.65 nats → review_required = True → surfaced in WeldAnalysisPanel.
  Inspector label (UT or sectioning, NOT visual — LOF is subsurface) →
  labelled_real_sessions table. Every ~10 labels: quality-finetune WITH
  synthetic replay buffer.                                        [CORRECTED]
  Target: ~50 labelled real sessions → real performance parity.

STEP 7 — Shadow deployment (Gate 6)
  2–4 weeks silent operation alongside the existing pipeline; every
  disagreement manually reviewed. Then — and only then — UI surfacing.
```

---

## A6. Deployment Evaluation Gate

The world model only touches the production response when ALL pass:

| Metric | Requirement | Notes |
|---|---|---|
| FNR on expanded eval set | = 0.000 | 24 scenarios + synthetic FN_RISK suite. **[CORRECTED]** 0/24 alone is weak evidence — binomial 95% CI upper bound ≈ 12% |
| F1 on synthetic held-out | ≥ 0.900 | And must ≥ GRU baseline |
| Fusion depth MAE | ≤ 1.0mm **vs real coupons** | **[CORRECTED]** — synthetic-only validation is circular and does not count |
| Uncertainty calibration | ECE ≤ 0.10 | Computed on real sessions where labels exist |
| OOD detection | Wired and tested | **[CORRECTED]** non-aluminium/non-MIG flagged, never silently predicted |
| Latency p95 | ≤ 500ms | With rk4 fixed-step inference |
| Shadow mode | 2–4 weeks, all disagreements reviewed | **[CORRECTED]** any missed defect → not deployable |

Until all pass: world-model output is written to `weld_world_model_results` but not
surfaced in UI or included in the quality report.

---

# PART B — THE CRITICAL ANALYSIS (2026-06-11)

The review that reshaped Part A. Preserved in full so the reasoning is auditable.

## B1. Verdict

**Conditionally viable.** The architecture and paper stack are sound. The plan as
originally written contained one fatal blind spot, three serious technical flaws,
and several inflated claims. Executed as originally documented, it would most
likely have produced a model that works beautifully and means nothing.

## B2. The Fatal Flaw — There Is No Real Data Anywhere in This Project

Verified directly in the repo (2026-06-11):

- The only session data in the entire project is `data/mock/session_001.json` and
  `session_002.json`, plus sessions generated at runtime by
  `backend/data/mock_sessions.py` — a hand-built simulator with tuned constants
  (`AL_AMPS_NOISE_EXPERT = 6.0`, etc.).
- `data/features/` is empty. `generate_feature_dataset()` builds entirely from mock
  generators (`_generate_stitch_expert_frames`, `_generate_continuous_novice_frames`,
  `_generate_aluminium_parametric_frames`).
- ESP32 firmware exists (`esp32_firmware/main.ino`) but no captured weld has ever
  flowed through it into this repo.
- The README's own Known Limitations admits it: *"Production deployment requires…
  real shipyard session data."*

Earlier planning analysis repeatedly referred to "your 10 real sessions." **That was
wrong.** Consequences for the original plan:

1. **Phase 0 calibration** ("moment-match Goldak against your 10 real sessions")
   would calibrate one simulator against another simulator. Two models agreeing
   proves nothing about welds.
2. **Phase 3 "sim-to-real fine-tune"** was actually sim-to-sim. The domain gap it
   claimed to close was the gap between two pieces of our own Python.
3. **The end product** would have been a world model of `mock_sessions.py` — a
   learned imitation of our own mock generator with a physics loss bolted on. It
   would have passed every original gate and told us nothing about a single
   physical weld.

This does not kill the project. It reorders it: **the first milestone is not
`goldak.py` — it is striking real arcs with the ESP32 rig and cutting coupons
open.** Everything else is downstream.

## B3. Serious Technical Flaws

### Flaw 1 — The physics loss as written was decorative, not constraining

The plan designated one latent dimension as `z_heat` and penalised it for violating
heat balance. Nothing forces the network to *use* that dimension for thermal
information. Gradient descent will make `z_heat` follow the ODE perfectly while
routing the real thermal signal through the other unconstrained dimensions — the
physics loss reaches zero; the model hallucinates freely. A known failure mode of
soft physics constraints ("physics-themed" vs physics-informed).

**Fix (applied in A1/A2):** structured latent `z = [z_phys ‖ z_free]`; the
heat-dissipation channel decoded *exclusively* from `z_phys` — architecturally, not
by hope. Then the constraint has teeth: if `z_phys` doesn't carry thermal state,
reconstruction fails.

### Flaw 2 — The fusion-depth validation gate was circular

The original deployment gate: "fusion depth MAE ≤ 0.5mm vs Goldak ground truth
(synthetic)." The model is trained to predict the simulator's output, then
validated against the simulator's output. Passing proves the model can invert its
own training data — nothing more. The earlier conversation had correctly identified
destructive coupon testing as "the non-negotiable," and the final implementation
reference quietly dropped it from the gates — exactly the drift that produces a
confident system with no anchor to reality.

**Fix (applied in A6 / Gate 5):** no millimetre figure reaches a quality engineer
until validated against ≥10 physically sectioned coupons (MAE ≤ 1.0mm,
direction-of-change ≥90%). Until then: qualitative risk bands.

### Flaw 3 — The boring baseline was missing, and it might win

The plan never trained the null hypothesis: a plain supervised GRU / 1D-CNN on raw
frames, same 5,000 synthetic sessions, predicting quality and fusion depth
directly — three days of work, no ODE, no VQ-VAE. If it matches the world model on
held-out data, the entire apparatus is unjustified complexity, and any reviewer
will say so in the first meeting.

**Fix (applied as Gate 3):** the world model must beat the GRU on held-out synthetic
(quality F1 AND fusion MAE) and demonstrate capabilities the baseline cannot have
(counterfactual monotonicity, physics-ablation effect). If the GRU wins, ship the
GRU as MVP and defer the world model — viability of the *project* does not require
this exact architecture.

### Flaw 4 — Smaller incoherences

- **KL balancing inapplicable**: requires a learned prior; Latent ODE prior is fixed
  N(0, I). Dropped.
- **Two incompatible encoders**: ODE-RNN (offline) and VQ tokenizer (streaming) were
  drawn feeding the same dynamics model; their latent spaces are not
  interchangeable. Resolved: MVP is post-session only; tokenizer is Phase 2,
  distilled teacher→student.

## B4. Moderate Risks Priced Into the Plan

1. **Rosenthal fails exactly where the defects live.** Quasi-steady assumptions and
   ignored latent heat break at stitch transitions — the precise LOF-risk moments
   our `heat_input_drop_severity` feature targets. The simulator will be least
   accurate where accuracy matters most. Gate 1 tests transient
   direction-of-change; transient FEM (FEniCS) is the budgeted fallback.
2. **The PHOENIX 98% ceiling does not transfer.** PHOENIX had melt-pool imaging;
   we have 4 scalar channels. There may be a hard observability ceiling — multiple
   internal weld states producing identical 4-channel signatures. The earlier
   90–95% expectation was optimistic extrapolation, not evidence. Gate 1.5
   (oracle ceiling test inside the simulator) measures it for two days of work.
3. **Active-learning label source undefined.** LOF is subsurface; visual inspection
   cannot confirm it. Labels = UT or sectioning, with named cost and owner.
   Otherwise label noise lands on exactly the rarest, most safety-critical class.
4. **Catastrophic forgetting** on tiny fine-tune batches → synthetic replay buffer
   required on every quality-finetune.
5. **Latency**: `dopri5` through a 1,500-frame encode threatens the 500ms p95 gate →
   rk4 fixed-step at inference.
6. **FNR = 0/24 is weak statistical evidence** — the 95% binomial upper bound on
   0/24 is ≈ 12%. The world-model gate uses an expanded scenario set.

## B5. The Go/No-Go Gates

**Meta-rules:** (1) kill criteria are written before the experiment runs and never
moved after seeing data; (2) failing a gate is a documented result, not a setback;
(3) nothing advances on "it should work" — it advances on a number.

| Gate | Blocks | Pass criteria | Kill condition |
|---|---|---|---|
| **0 — Reality** | all world-model code | ≥30 real ESP32 sessions (incl. deliberate defects); ≥8 sectioned coupons with measured penetration; heat-diss channel verified on hardware | Real sensor stats look nothing like mock → the *existing* classifier results are also invalid; re-baseline the whole project first |
| **0.5 — Public-data pre-training** (parallel accelerator) | nothing | Encoder pre-trained on Polito + Intel; reconstruction works on real signals; codebook ≥60% utilisation | Pipeline can't learn real electrical dynamics → architecture problem exposed early, fix before our own data arrives |
| **1 — Simulator validity** | generating the 5,000-session corpus | Penetration within ±25% of coupons; direction-of-change correct incl. stitch transients; sensor moments vs REAL sessions within ~15% | Wrong on transient direction-of-change → synthetic fusion labels are noise; transient FEM or stop |
| **1.5 — Observability ceiling** | architecture commitment | Oracle regressor (4 sim channels → sim fusion depth) ≤ ~1.0mm irreducible error | Ceiling > 1mm → 4 channels physically insufficient; add sensing (5×5 thermal snapshot array already in the data model) before any modelling |
| **2 — Representation** | full world-model training | VQ codebook ≥60% utilisation; linear probe latent→11 features beats mean baseline; probe latent→quality ≥ GBDT on synthetic held-out | Latent loses to hand features → representation adds nothing |
| **3 — Earn the complexity** | backend integration | ≥ GRU baseline on held-out synthetic (F1 AND fusion MAE); counterfactual monotonicity ≥95%; physics-ablation shows measurable OOD effect | GRU matches → ship GRU, defer world model. Ablation null → physics term decorative; fix grounding first |
| **4 — Transfer** | trusting real-weld outputs | Feature-decoder R² ≥ 0.5 on real; latent KL syn↔real < 0.5 nats; reconstruction ≤ 2× synthetic error | Can't beat mean-prediction on real features → no transfer happened |
| **5 — Fusion truth** | any mm figure in UI | MAE ≤ 1.0mm vs fresh ≥10 coupons; direction-of-change ≥90% | Until passed: risk bands only |
| **6 — Deployment** | influencing any disposition | 2–4 weeks shadow mode, all disagreements reviewed; FNR = 0.000 on expanded eval; OOD detector wired; p95 ≤ 500ms | Any missed defect in shadow mode → not deployable, full stop |

## B6. What Survives the Critique

The architecture choices are defensible: Latent ODE over RSSM for continuous physics
is right; physics-informed over pure-learned at this data scale is right (the
literature is unambiguous — every paper that dropped the physics prior needed orders
of magnitude more data); progressive loss fading is right; keeping the deterministic
safety override untouched is exactly right. The paper-to-component mapping is real,
not citation decoration.

What changed is the spine: **the critical path runs through a welding shop, not
through `goldak.py`.** Real arcs, real coupons — roughly $200 of materials and a few
shop days — come before the first line of world-model code, because Gates 0/1/1.5
are the cheapest points in the programme to discover the vision needs adjusting. The
most expensive failure mode available is not building the model wrong; it is
building it right, on top of nothing.

---

# PART C — DATA STRATEGY: THREE LAYERS, NOT INTERCHANGEABLE

### Layer 1 — Public real datasets (breadth + sensor realism). Use now.

Prove the pipeline learns from *real* electrical signals; teach the encoder real arc
noise. They do **not** pass Gate 0: none has our channels
(`heat_dissipation_rate`, `angle_degrees`), our process (aluminium MIG stitch), or
any paired penetration-depth ground truth.

| Dataset | Size | Contents | Access | Use |
|---|---|---|---|---|
| [SmartData@Polito RSW](https://github.com/smartdatapolito/resistance_spot_welding_dataset) | 1,976 labelled | V/I/force/displacement time series, fault labels | Open | Encoder pre-training; real-noise statistics |
| [Intel Robotic Welding Multimodal](https://huggingface.co/datasets/IntelLabs/Intel_Robotic_Welding_Multimodal_Dataset) | 4,000+ | GMAW arc V/I time series + audio/video/images, 12 defect classes | Gated — request | Closest process match; pre-training + taxonomy |
| [Bacioiu TIG SS304](https://www.kaggle.com/datasets/danielbacioiu/tig-stainless-steel-304) | 45,058 imgs / 56 runs | Weld-pool HDR images, 6 classes incl. LOF/LOP | Open | Label taxonomy only |
| [Kaggle V/I time series](https://www.kaggle.com/datasets/thunder7/welding-current-and-voltage-time-series-data) | Small | Arc V/I, no labels | Open | Minor pre-training |
| [Void formation FSW](https://www.kaggle.com/datasets/arindambaruah/void-formation-process-data-in-welding) | 108 | Params → void labels | Open | Minor reference |

### Layer 2 — Our own real data (the anchor). This IS Gate 0. Nothing substitutes.

≥30 real ESP32 sessions (weld matrix: ~10 nominal, ~5 cold/low-current, ~5
off-angle, ~5 fast-travel, ~5 stitch-restart abuse) + ≥8 sectioned and etched
coupons with measured penetration (aluminium: bandsaw, polish, ~10% NaOH etch,
calipers/macro photo; ≈$200 materials; via university lab, makerspace, welding
school, or a certified inspection shop).

**Why synthetic data can never pass Gate 0:** Gate 0 exists to provide the reality
anchor that synthetic data is validated *against*. Synthesising data to validate
synthetic data is the exact circularity of the fatal flaw (B2). Synthetic is the
**amplifier** (Layer 3); real is the **anchor** (Layer 2). Both required, never
interchangeable.

### Layer 3 — Goldak synthetic corpus (volume + hidden-state labels). Only after Gate 1.

5,000 sessions, per-frame `fusion_zone_depth` ground truth, LOF/LOP injection,
domain randomisation (material properties, ambient temp, CTWD, travel speed, plate
thickness, sensor noise). Without randomisation the model overfits the simulator
manifold and transfer fails silently.

---

# PART D — THE MVP PRODUCT SHAPE

**Not a 3D simulation** (that is Phase 4, after coupon validation — an unvalidated
volumetric render creates false confidence, which in safety-critical welding is
worse than nothing). **Not just a verdict.** The MVP is a **temporal weld-health
dashboard**:

**Screen 1 — Weld Timeline** (the new thing): time on X; estimated fusion depth
line; confidence band (wide = uncertain); colour-coded risk regions per second.
Current system: "REWORK_REQUIRED." World model: "fusion failed at second 8.3, 2mm
window below AWS D1.1 minimum, never recovered."

**Screen 2 — Verdict Card** (existing, enriched): minimum fusion depth vs standard
("3.2mm est., minimum 4.0mm" — post-Gate 5 only) + inspection priority from
uncertainty ("recommend physical verification of root pass, seconds 7.8–9.1").

**Screen 3 — Welder Feedback View**: sensor replay with fusion estimate overlaid;
marker at the failure moment; "angle drifted to 72° at 8.1s — heat redirected away
from root, est. 1.4mm fusion shortfall." Actionable in a way "REWORK_REQUIRED"
never is.

**Phased product progression:**
1. Enhanced verdict (same interface + depth estimate + uncertainty + failure second)
2. Temporal dashboard (the first visible proof of the world model — the
   stakeholder demo)
3. Counterfactual explorer ("what if voltage was 2V higher at second 8?" — latent
   rollout; the feature that makes the world-model difference legible)
4. 3D visualisation (only after destructive-test validation; then it's a window,
   not decoration)

**The two-minute demo:** pull a REWORK_REQUIRED session → timeline shows red at
second 8 → "angle drifted 17°, est. depth dropped 5.8→2.9mm, joint fails under load
here" → adjust angle in the counterfactual, re-simulate → red turns green → "the
current system tells you the weld failed; this tells you why, where, when, and what
would have prevented it — and estimates the variable no sensor in this factory can
measure."

---

# PART E — ANTI-FLUFF CHARTER

1. **Pre-registered kill criteria** — written before the experiment, never edited
   after. Fluff happens when success is defined after seeing the results.
2. **The boring-baseline rule** — every complex component must beat its boring
   alternative on held-out data, with the threshold declared in advance (the README
   already lives this: "P@6 < 0.70 → build hybrid"). If the GRU wins, the GRU
   ships and the README says so.
3. **One physical artifact beats ten dashboards** — flagship evidence is a photo of
   a sectioned weld next to the model's predicted depth, measured vs predicted.
4. **Negative results go in the README** — "X failed Gate Y at Z, we did W instead"
   is what reads as real engineering.
5. **No millimetres before Gate 5; no dispositions before Gate 6.**
6. **Don't call it a world model until it earns the name** — the justifying
   capability is validated counterfactual reasoning. Until then: "physics-informed
   latent state estimator," an honest claim that is already strong.
7. **The safety floor is non-negotiable** — the deterministic threshold override
   stays below every learned component. FNR = 0.000 gates everything.

---

# PART F — IMMEDIATE NEXT ACTIONS

1. **Today:** request Intel Robotic Welding dataset access on HuggingFace (gated;
   days of latency — start the clock).
2. **Today:** download SmartData@Polito RSW; write a loader normalising to the
   WarpSense frame contract.
3. **This week:** arrange real-weld access (university lab / makerspace / welding
   school / hire a welder); define the 30-weld matrix; arrange sectioning + etch
   for 8 coupons.
4. **This week:** bench-test the full ESP32 → `POST /sessions` capture path with
   `esp32_firmware/main.ino` — one real powered-on capture, even a dry run.
5. **Next:** build `baselines/gru_baseline.py` and the eval harness so the
   measuring stick exists before the thing it measures.

---

# PART G — JEPA / SIGReg / EBM / CONTRASTIVE: WHAT APPLIES (added 2026-06-12)

Verdict on the LeCun self-supervised stack for this project:

| Idea | Verdict | Where / why |
|---|---|---|
| **JEPA objective** (predict in latent space, not input space) | **YES — as encoder pre-training contender** | Gate 0.5 / Gate 2. Reconstruction objectives force the encoder to model stochastic arc noise (real V/I signals are noisy by physics); latent prediction lets it ignore the unpredictable and keep the process state. Time-series JEPA work (ECG-JEPA, TS-JEPA, multimodal sensor JEPA 2025–26) shows latent prediction rivals supervised representations and is more robust to noise + label scarcity — exactly our regime. |
| **SIGReg / LeJEPA** (Balestriero & LeCun, arXiv 2511.08544) | **YES — if JEPA route is taken, use LeJEPA specifically** | SIGReg constrains embeddings to an isotropic Gaussian via sketched 1D projections — provably collapse-free by construction, single hyperparameter, no EMA teacher / stop-gradient heuristics (fragile at small scale). Directly answers the representation-collapse risk we flagged for 4-channel low-dim inputs. ~50 lines; code at github.com/rbalestr-lab/lejepa. |
| **Energy-based models** (explicit EBM training, MCMC) | **NO — conceptual lens only** | The EBM insight — many internal states compatible with one observation — is our observability-ceiling problem (Gate 1.5) and is handled by the probabilistic decoder + uncertainty head. No energy-landscape training needed. |
| **Contrastive methods** (SimCLR-style, TS2Vec-style) | **NO** | LeCun's own critique (sample-inefficient in high-dim embedding space) plus a domain-specific killer: contrastive needs label-preserving augmentations, and standard time-series augmentations destroy weld physics — amplitude-scaling amps *changes heat input* (H = V·I/v), time-warping changes travel speed. An invariance objective would teach the encoder to ignore exactly the signals that matter. JEPA's masked latent prediction needs no semantic augmentations. |

**The architectural tension and its resolution:** pure JEPA has no decoder — embeddings
are abstract, so it cannot ground `z_phys` physically (our anti-physics-washing fix
requires heat_diss decoded exclusively from `z_phys`). Resolution: **hybrid objective
mapped onto the structured latent** —

```
z_phys (4)  ← reconstruction grounding (heat_diss head) + physics residual   [unchanged]
z_free (28) ← JEPA latent-prediction loss + SIGReg anti-collapse             [new option]
```

JEPA trains the abstract part; physics grounds the physical part. SIGReg and our
free-nats KL are cousins (both push toward N(0,I)); keep the KL on the probabilistic
μ/σ head, apply SIGReg to the deterministic JEPA embeddings during pre-training.

**Pre-registered Gate 2 amendment:** compare three encoder pre-trainings — (a) none,
(b) reconstruction/VQ-VAE, (c) LeJEPA — by frozen-encoder linear probe on the 11
engineered features + quality classification on synthetic held-out. Winner must lead
by a pre-declared margin; otherwise take the simpler option (b).

**What JEPA does NOT change:** the gates, the Goldak anchor, the coupons, the GRU
baseline, the Neural ODE dynamics, or the safety floor. It is a candidate for one
slot — how the encoder learns its representation — not a replacement for the
physics-grounded world model. (V-JEPA2-style video prediction becomes relevant only
if a melt-pool camera or the 5×5 thermal-snapshot array is added as a modality.)

---

# PART H — DEFECT CRITICALITY: IS LOF/LOP THE RIGHT TARGET? (added 2026-06-12)

Literature check on whether LOF/LOP are the critical defects, and what else is
critical-but-hard-to-monitor with current industrial practice.

## H1. LOF/LOP focus is validated

- The codebase's cited source is real: Amirafshari & Kolios (Int. J. Fatigue 2021,
  defect frequency/size statistics for ship structures; 2022, Bayesian POD
  estimation in fabrication yards).
- Fracture mechanics ranking: planar defects (cracks, LOF, LOP) ≫ volumetric
  (porosity, inclusions) > geometric (undercut). LOF/LOP are crack-like stress
  concentrators.
- POD studies confirm the monitoring gap: some LOF is invisible on radiographs
  entirely; PAUT a90 ≈ 6.9mm vs RT a90 ≈ 12.7mm for discontinuities — RT (the most
  common industrial NDT) is weakest exactly on the planar class. "Kissing bonds"
  (tight, closed LOF interfaces) evade even conventional UT — only nonlinear
  ultrasonic research techniques detect them. Post-hoc NDT cannot be fully relied
  on for this class → in-process monitoring is the only reliable strategy.
  This *strengthens* the project thesis.

## H2. Three other critical defects that are harder to monitor than LOF/LOP

| Defect | Why critical | Why current practice can't monitor it | World-model relevance |
|---|---|---|---|
| **HAZ softening (6061-T6)** | 30–50% strength loss next to the weld (≈40% tensile, ≈50% yield). Weld looks perfect, passes visual/bend, fails under load | It is a *property change*, not a flaw — **invisible to every NDT method that exists**. Only hardness/tensile testing reveals it | **Highest.** Softening is a direct function of thermal history (Mg₂Si precipitate dissolution). The Myhr–Grong kinetic model maps temperature history → strength knockdown. `z_phys` already estimates thermal state → a softening decoder head is nearly free. No competitor monitoring product can see this |
| **Hydrogen cold cracking (steels)** | Delayed cracking up to 48–72h after welding; codes mandate ≥48h wait before final NDT (major cost offshore) | **Physically impossible to inspect at weld time — the crack does not exist yet.** A weld inspected and passed can be cracked by morning | Medium — cannot detect, but CAN predict *susceptibility* from cooling rate (t8/5), heat input, preheat compliance → risk score + "delayed inspection required" flag. Only applies if/when WarpSense targets steel (note: the KB is AWS D1.1/IACS steel-oriented; the data is aluminium — resolve this scope tension) |
| **Hot / solidification cracking (Al 6061)** | AA6061 is **highly susceptible** in the fusion zone; cracks form during solidification in the mushy zone | In-process detection is poorly developed in the literature; post-weld detection is surface/UT dependent | Medium — literature ties susceptibility to high heat input + power density, both already measured. Mushy-zone strain is unobservable, but a thermal-precursor risk index is feasible. Mitigation is procedural (ER4043 filler) |
| Porosity (Al) | Most *frequent* aluminium defect (hydrogen solubility drop at solidification) | Detectable — volumetric, RT-visible | Correctly deprioritised: less critical per fracture mechanics AND already monitorable. Already present in the RAG corpus categories |

## H3. Scope recommendation

1. **Keep LOF/LOP as the primary target** — validated as the critical+undermonitored
   class; kissing-bond literature shows even post-hoc UT fails on the worst variants.
2. **Add HAZ-softening estimation as a second world-model output** — a
   Myhr–Grong-style kinetic decoder on the thermal latent. Near-zero added sensing
   cost, detects something NO NDT can, and uniquely differentiates the product.
   Validation path: hardness traverse measurements on the same Gate-0/Gate-5 coupons
   (cheap to add to the destructive-test protocol).
3. **Optional: hot-cracking risk index** from heat input + power density (flag, not
   verdict).
4. **Defer cold-cracking risk scoring** until a steel variant exists; note it as the
   strongest expansion argument for shipyard customers (48h-wait cost reduction).
5. **Resolve the aluminium-data vs steel-standards (AWS D1.1) inconsistency** in the
   KB before production claims.

---

# PART I — THE THREE-DEFECT WORLD MODEL: VALIDITY & DESIGN (added 2026-06-12)

Targets: (1) LOF/LOP, (2) HAZ softening, (3) hot/solidification cracking.

## I1. The unifying validity argument

All three defects share **one causal bottleneck: the thermal history T(x,t)**.

- **LOF/LOP** — fusion occurs where T exceeds liquidus (~650°C for 6061); fusion
  depth is the depth of that isotherm. Deficit = defect.
- **HAZ softening** — Mg₂Si strengthening precipitates dissolve as a deterministic
  function of time-at-temperature. The Myhr–Grong isokinetic model (Acta Metall.
  1991, developed for 6xxx weldments) maps T(x,t) → dissolved fraction → hardness
  loss via an integral of the form X_d ∝ ∫ dt / t*(T).
- **Hot cracking** — susceptibility scales with mushy-zone size and solidification
  conditions (RDG criterion, Rappaz–Drezet–Gremaud 1999), both set by heat input
  and power density — thermal-field quantities. (The strain/restraint term is NOT
  thermally observable — hence Tier 2.)

The sensors observe exactly this bottleneck: V·I is instantaneous power in;
heat_dissipation is power out; angle directs the field. **One estimated hidden
state (thermal history) feeds three read-outs.** The marginal cost per defect is a
decoder head plus a validation protocol — not a new model.

**The mutual-information bonus:** a hardness traverse is effectively a spatial
record of the temperature history the HAZ experienced. Hardness ground truth
doesn't just validate the softening head — it back-constrains the shared thermal
state, improving fusion-depth estimation too. The defects are mutually informative
through the shared latent.

## I2. Per-defect validity verdict

| Defect | Causal observability | Ground truth | Physics model | Tier |
|---|---|---|---|---|
| LOF/LOP | Good (heat input, angle, cooling) — subject to Gate 1.5 ceiling | Macro-etch coupon sections (~1 point/coupon) | Goldak → liquidus isotherm | **Tier 1 — quantitative estimate** |
| HAZ softening | **Best of the three** — deterministic function of thermal history, no stochastic nucleation step | Vickers hardness traverse (~20–50 points/coupon — the densest real signal in the project) | Myhr–Grong isokinetic dissolution | **Tier 1 — quantitative estimate** |
| Hot cracking | Partial — thermal precursors observable; mushy-zone strain and restraint are NOT | Provoked-crack coupons (autogenous beads on 6061 crack reliably; ER4043 beads don't) + dye penetrant/micro-sections | RDG-criterion scaling for the index | **Tier 2 — risk flag only, never a verdict** |

## I3. Design: learn the state, keep the read-outs as physics

```
            shared encoder + Neural ODE  →  thermal latent trajectory z_phys(t)
                                              (expanded to ~8 dims: peak-temp scale,
                                               effective efficiency η, cooling coeff,
                                               angular asymmetry, residuals)
                     │
   ┌─────────────────┼──────────────────────────┐
   │                 │                          │
FUSION HEAD      SOFTENING HEAD             HOT-CRACK RISK HEAD
learned MLP      **differentiable physics   **rule-based formula**
(z→depth_mm)     layer, not learned**:      RDG-scaled index from
trained on       Myhr–Grong integral        (heat input, power density,
synthetic GT +   computed from estimated    est. solidification rate)
coupon anchor    T(x,t); alloy constants    × filler/joint susceptibility
                 from literature; small     factor from session metadata
                 learned correction only    (WPS: ER4043 vs 5356 vs
                 after hardness data        autogenous). No learned
                 exists                     component until crack data exists
```

Principle: **learning is concentrated where data is dense (sensor → thermal
state); physics is used where data is scarce (state → defect)**. The softening
"decoder" is auditable physics — the only learned part is the thermal state it
reads, which is shared with (and validated through) the fusion head.

## I4. Training data per head

- Shared encoder/dynamics: 5K synthetic + public real (JEPA pre-train) + ≥30 own
  real sessions (self-supervised) — unchanged.
- Fusion head: synthetic Goldak GT + coupon depths (Gates 1/5).
- Softening head: synthetic GT is **free** (run Myhr–Grong on simulated thermal
  fields) + hardness traverses on the same coupons → hundreds of real GT points.
- Hot-crack head: no training; validation only — index must separate provoked-crack
  coupons from ER4043 controls (target AUC ≥ 0.8).

## I5. Gate amendments

- **Gate 0 coupon protocol upgraded** — each coupon serves three masters: macro
  etch (depth), hardness traverse (softening), dye penetrant + micro-sections
  (cracks). Marginal cost per coupon: small.
- **Gate 1.5 per defect** — run the observability-ceiling oracle separately for
  depth and for min-HV/softened-width (softening expected to be better-posed).
- **Gate 5 splits**: 5a depth MAE ≤ 1.0mm; 5b min-HV error ≤ ~10 HV and softened
  width ±25%; 5c risk index separates crack/no-crack coupon groups (AUC ≥ 0.8).
- **Hardness measurement timing must be standardised** — 6061 HAZ naturally ages
  for days–weeks post-weld, partially recovering hardness. Fix the protocol (e.g.,
  measure at ≥7 days) and state which condition the model predicts.

## I6. Honest scope limits

1. Hot cracking ships as a **flag with stated inputs**, never a detection claim —
   strain/restraint is unobservable from these sensors.
2. Single-pass welds only for the MVP — multi-pass reheating invalidates the
   simple thermal-history → softening mapping.
3. Known initial temper (T6) assumed; the softening model is alloy- and
   temper-specific.
4. The aluminium-data / steel-standards (AWS D1.1) inconsistency must be resolved
   before production claims.

---

# PART J — EDGE INFERENCE & SYSTEMS CO-DESIGN (added 2026-06-16)

A systems workstream layered on the model plan: quantization, a real custom kernel,
explicit distillation, a production serving stack, inference co-design, an upstream
contribution, and a scaling study. Two framing rules keep it consistent with the rest
of this document instead of contradicting it.

## J0. Two rules that keep this honest

**Rule 1 — Two distinct inference targets. Do not conflate them.**

| Target | What it is | Where it runs | Budget | Optimisation surface |
|---|---|---|---|---|
| **Teacher** (MVP) | Full ODE-RNN encoder + Neural ODE + 4 heads | **Server-side**, post-session (`POST /sessions/:id/analyse`) | p95 ≤ 500ms (Gate 6) | Serving stack (J4); GPU kernel fusion (J2) |
| **Student** (Phase 2) | Distilled streaming tokenizer + tiny dynamics (Paper 5) | On-device target: **ESP32-S3** | per-window, **energy-bound** | Quantization (J1), MCU kernel (J2), co-design (J5) |

The MVP world model is **not** an on-MCU model — a backward ODE-RNN over 1,500 frames
plus a Neural ODE is server-class compute. The ESP32 target is the **distilled
streaming student** already in the plan (Paper 5: "distilled from the trained world
model, not co-trained"). Most of this workstream is the engineering build-out of that
student, plus a server-side serving stack for the teacher. *Hardware note:* on-device
NN inference realistically requires the **ESP32-S3** (128-bit vector/PIE extensions,
ESP-DSP/ESP-NN); a plain ESP32 (LX6, no SIMD) makes the student impractical and pushes
everything server-side — confirm which silicon the rig uses before committing to J1/J2.

**Rule 2 — Nothing here optimises a model that has not earned its existence.**
Quantizing, kernel-fusing, or distilling a world model that has not passed **Gate 3**
(beats the GRU baseline) is polishing something that may be deleted. Most of PART J is
**post-Gate-3 / Phase 2** by construction. The two items that run early — because they
*inform* architecture rather than optimise a frozen model — are the **scaling study
(J7)** and the **serving-harness scaffold (J4)**, both of which work against whatever
model sits behind them, including the GRU baseline.

## J1–J7. The deliverables

| # | Deliverable | Maps to | Artifact (the number) | Earliest |
|---|---|---|---|---|
| **J1** | int8→int4 quantization of the student | Paper 5 student | quality Δ vs latency vs **energy (mJ/inference)** at fp32/int8/int4, measured on ESP32-S3 | post-Gate 3 |
| **J2** | Fused ODE-step + encoder-read kernel | Papers 3, 4 | measured p50/p95 speedup: **Triton** (GPU teacher) + **hand-C/ESP-DSP** (MCU student) | post-Gate 3 |
| **J3** | Teacher→student distillation | Paper 5 (made explicit) | teacher-size × student-size → student-quality **Pareto** (F1, fusion MAE) | post-Gate 3 |
| **J4** | Streaming serving stack | Paper 5 + A4 + Phase G | p50/p99 latency + throughput-under-load **harness**; hidden-state-carry (KV-cache analog) | scaffold early; carry post-student |
| **J5** | Inference co-design sweep | A2 architecture | quality × latency × memory **frontier** over (latent dim, rk4 steps, head width); justified operating point | informs arch; finalise post-Gate 3 |
| **J6** | One merged upstream PR | torchdiffeq / ExecuTorch / TFLite-Micro / LeJEPA | merged **PR link** | standing policy |
| **J7** | Mini scaling study | Step 1 corpus | model-size × data-quantity → held-out-error **grid**; data- vs capacity-bound verdict | early (after Gate 1 + GRU) |

**J1 — Quantization (energy is the real objective).** On an MCU the binding constraint
is not latency but **energy per inference** — "99% of cost is power" is literally true
on a peripheral-/battery-powered ESP32-S3. Report the *curve*, not a point: fp32 → int8
→ int4 accuracy knockdown against measured mJ/inference (INA-style current probe) and
per-window latency. Pre-register the kill line: if int4 costs > Δ accuracy on the **LOF
class** (the safety-critical one), int4 is off the table for disposition-relevant heads
— keep int8, or keep that head server-side. This is a quantization study you have to do
anyway to know whether on-device is even viable (Gate 7).

**J2 — The kernel that matters.** The Neural-ODE "clock" is the latency tail: rk4 over
the session is many tiny *sequential* matmuls (32→64→64→32) with poor hardware
utilisation — the classic ragged/small-sequential-op bottleneck. Fuse the ODE-step +
encoder-read into one kernel: **Triton** on the GPU teacher, hand-optimised C using
**ESP-DSP / ESP32-S3 vector (PIE) extensions** on the MCU student. Deliverable is the
measured before/after p50/p95 — the project's "Pallas kernel beating `ragged_dot`"
equivalent. Honesty note: the S3's SIMD is narrow; report the *real* speedup, and if
it is marginal, that is itself the finding (the step is **memory-bound**, not
compute-bound — which then redirects the optimisation).

**J3 — Distillation, made an explicit curve.** The plan already specifies a distilled
streaming student (Paper 5); PART J turns "distill it" into a measured **teacher-size →
student-quality** frontier so the on-device size is a justified choice, not a guess.
Distil against teacher *soft* targets — quality logits, fusion-depth, **and the latent
trajectory** `z_t`. Matching the latent trajectory (not just the verdict) is what
preserves world-model behaviour through the shrink.

**J4 — Serving stack, not a toy endpoint.** Upgrade the Phase-G shadow service (A4)
from a single `infer()` call into a streaming service: micro-batch concurrent sensor
windows; **carry the world-model hidden state forward across the stream** — the direct
recurrent analog of an LLM KV-cache (recompute-free continuation); backpressure /
request-queue under load; a benchmark harness reporting **p50/p99 latency and
throughput**. The harness is built early (it benchmarks whatever is behind it,
including the GRU); the hidden-state-carry lands with the streaming student. Feinberg's
named primitives — KV cache, load balancing, request queuing — map onto this one-to-one.

**J5 — Co-design, stated as joint optimisation.** The architecture constants (32-dim
latent, rk4 step count, head widths) are not arbitrary — present them as the chosen
point on a **quality × latency × memory** frontier for the target hardware. This
extends the existing rk4-at-inference latency decision into an explicit sweep and ties
to Gate 1.5: if the observability ceiling permits a smaller latent, take the cheaper
model. The deliverable framing is *joint optimisation over quality + latency + memory*,
not three separate plots.

**J6 — One merged upstream PR (standing policy, not a scheduled task).** You will hit a
real limitation building this — likely candidates: `torchdiffeq` fixed-step adjoint /
event handling; **ExecuTorch or TFLite-Micro operator coverage for the ODE-solver loop**
on MCU (the rk4 integration is not a standard NN op — you wrap quantized matmuls in a
custom loop, which is exactly where coverage gaps appear); a `LeJEPA` reference-impl
edge (PART G). When you hit it, fix it upstream and land the PR. That merged PR is the
literal "contribute to a serving stack" signal; naming the candidates here is why it is
plannable at all.

**J7 — Mini scaling study (the earliest-runnable item).** You are building the synthetic
generator anyway (Step 1). Sweep **model-size × data-quantity → held-out error**. Even
small, it answers two planning questions with numbers: (1) is the world model
**data-bound or capacity-bound** vs the GRU, and (2) what is the marginal value of
synthetic sessions beyond 5,000 — generate more, or is the ceiling elsewhere (Gate 1.5
observability)? This is the "recipe → predicted loss" frame, and it is cheap enough to
run the week the corpus exists.

## J-gates (pre-registered, following the PART I precedent)

| Gate | Blocks | Pass criteria | Kill criterion |
|---|---|---|---|
| **7 — Edge viability** | any claim of on-device inference | Distilled int8/int4 student within Δ accuracy of the teacher (quality F1 **and** fusion MAE) at ≤ target ms/window **and** ≤ target mJ/inference on ESP32-S3 | Student loses > Δ on the **LOF class** at every size that fits the MCU → on-device LOF detection is not viable; ship streaming **server-side**, document the finding |

Gate 6's `p95 ≤ 500ms` (server teacher) is unchanged; Gate 7 adds the *edge* budget for
the student. **The FNR = 0.000 safety floor applies to whichever artifact touches
disposition** — a quantized student does not get a weaker safety bar than the server
model. No accuracy is traded for the MCU on the safety-critical class.

## J-map — the systems-credibility surface

This workstream doubles as the project's systems-engineering narrative for an
inference-systems reviewer/investor (the KV-cache / request-queuing / kernel-win /
recipe→loss profile). Kept honest — every row resolves to a **number measured on
hardware or a held-out set**, per the anti-fluff charter (§E), which is exactly what a
systems reviewer rewards (measured speedups, energy curves, a merged PR) over
architecture diagrams:

| Reviewer vertical | Deliverable | Proof artifact |
|---|---|---|
| Quantization | J1 | fp32/int8/int4 quality × latency × energy curve, on-device |
| Custom kernels | J2 | measured Triton + MCU kernel speedup (the `ragged_dot` analog) |
| Distillation | J3 | teacher→student quality Pareto |
| Serving (KV-cache, queuing, load) | J4 | p50/p99 + throughput harness; hidden-state-carry |
| Inference co-design | J5 | quality × latency × memory frontier + justified operating point |
| Upstream contribution | J6 | merged PR |
| Scaling (recipe→loss) | J7 | model × data → error grid; data/capacity verdict |

---

# APPENDIX — SOURCES

**Core implementation papers**
- Goldak, Chakravarti & Bibby (1984), Metallurgical Transactions B — https://doi.org/10.1007/BF02656090
- Raissi, Perdikaris & Karniadakis (2019), J. Computational Physics — https://doi.org/10.1016/j.jcp.2018.10.045
- Chen et al. (2018), Neural ODEs, NeurIPS — https://arxiv.org/abs/1806.07366 · https://github.com/rtqichen/torchdiffeq
- Rubanova, Chen & Duvenaud (2019), Latent ODEs, NeurIPS — https://arxiv.org/abs/1907.03907
- Micheli, Alonso & Fleuret (2022), IRIS, ICLR 2023 — https://arxiv.org/abs/2209.00588 · https://github.com/eloialonso/iris
- Hafner et al. (2023), DreamerV3 — https://arxiv.org/abs/2301.04104 · https://github.com/danijar/dreamerv3
- PHOENIX (2025), Nature Communications — https://www.nature.com/articles/s41467-025-60164-y · https://github.com/iVPPA/PHOENIX
- Andreoli et al. (2025), PINN spot welding — https://arxiv.org/abs/2508.04595
- Settles (2012), Active Learning, Morgan & Claypool

**Context / landscape**
- Ha & Schmidhuber (2018), World Models — https://worldmodels.github.io/
- DayDreamer (2022), CoRL — https://arxiv.org/abs/2206.14176
- TD-MPC2 (2023) — https://arxiv.org/abs/2310.16828
- Ding et al. (2024), world-models survey, ACM Computing Surveys — https://arxiv.org/abs/2411.14499
- PINN 78% data-reduction result, J. Intelligent Manufacturing — https://link.springer.com/article/10.1007/s10845-024-02460-w
