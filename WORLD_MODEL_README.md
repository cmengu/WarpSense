# WarpSense — World Model of the Weld

A physics-informed latent state estimator for aluminium MIG welds. It estimates the
internal weld state — primarily **fusion-zone depth** — at every instant of a pass,
from four scalar sensor channels, with calibrated uncertainty.

> **Status: planning / pre-Gate-0.** No real weld data has been collected. Nothing
> here is validated against physical welds. See [§10](#10-status).

---

## 1. Overview

Fusion-zone depth — the depth of metal that melts and re-solidifies — determines
whether a weld carries load. No surface sensor can measure it. The world model infers
it as a hidden state from the ESP32 stream (volts, amps, torch angle, heat
dissipation), constrains the estimate with weld heat-transfer physics, and reports
where and when fusion fell short, with uncertainty.

It is a second opinion layered on the existing quality pipeline. It adds fields; it
does not change dispositions until it has earned that trust through the gates in §7.
The deterministic safety override remains below every learned component.

## 2. Problem

The existing pipeline classifies a weld after completion from 11 summary statistics
and returns a verdict without a cause. Two gaps:

- Fusion depth, the load-bearing variable, is never estimated — only inferred
  indirectly from surface features.
- A post-hoc verdict ("REWORK_REQUIRED") locates no failure in time and gives no
  physical explanation.

The world model closes both: a continuous internal-state estimate that pinpoints the
failure moment and quantifies confidence.

## 3. Architecture

Pipeline: **encode → evolve → decode.**

```
ESP32 stream   [4 channels × 1500 frames]
      │
ODE-RNN encoder (backward pass)        → z0 ~ N(μ, σ) ∈ R^32
      │                                  structured: z = [ z_phys(4) ‖ z_free(28) ]
Neural ODE   dz/dt = f(z, t)           → z_t for all t
  + heat-balance residual on z_phys
      │
  ┌───┴──────────┬───────────────┬────────────────┐
sensor         quality          fusion           feature
decoder        decoder          decoder          decoder
heat-diss      concat(z_T,      z_T → depth_mm   z_T → 11 feats
from z_phys    11 features)     (synthetic GT)   (self-supervised)
only           → 3 classes
```

- **Encoder** — compresses a full session into a distribution over its initial latent
  state. Backward ODE-RNN; fixed 100 Hz input (no irregular-sampling machinery).
- **Structured latent** — four dimensions (`z_phys`) are reserved for thermal state
  and are the *only* input to the heat-dissipation decoder. Thermal information must
  flow through them or reconstruction fails. This is what makes the physics constraint
  binding rather than decorative.
- **Dynamics** — a Neural ODE evolves the latent continuously; a heat-balance residual
  (heat in − heat out) constrains `z_phys`.
- **Decoders** — four heads: sensor reconstruction, quality (3-class, fused with the
  11 engineered features), fusion depth in mm (synthetic ground truth only, gated for
  UI), and engineered-feature regression (free self-supervision).
- **Solvers** — adaptive `dopri5` in training; fixed-step `rk4` at inference to hold
  the latency budget.

Training uses progressive loss-fading (reconstruction → features → physics →
quality), symlog targets, and free-nats KL.

## 4. Research stack

Each paper supplies one component; none is implemented in full.

| Component | Source | Contribution |
|---|---|---|
| Synthetic data + fusion-depth labels | Goldak et al. (1984) | Double-ellipsoid heat source → simulated welds with known fusion depth. Re-parameterised for aluminium; calibrated against real coupons |
| Continuous dynamics | Chen et al. (2018), Neural ODEs | `dz/dt = f(z,t)` via `torchdiffeq` |
| Encoder | Rubanova et al. (2019), Latent ODEs | Backward ODE-RNN → `z0` distribution |
| Physics constraint | Raissi et al. (2019), PINNs | Heat-balance residual as a loss term on `z_phys` |
| Loss scheduling | Andreoli et al. (2025) | Progressive sigmoid fade-in of loss terms |
| Training stability | Hafner et al. (2023), DreamerV3 | symlog, free nats, percentile norm (KL balancing dropped — no learned prior) |
| Quality readout | PHOENIX (2025) | Feature-level fusion of latent + engineered features; confidence output |
| Streaming tokenizer (deferred) | Micheli et al. (2022), IRIS | VQ-VAE windows → tokens; Phase 2, distilled from the trained model |
| Label selection | Settles (2012), Active Learning | Entropy-based uncertainty sampling for which real welds to label |

## 5. Key design decisions

- **Physics grounding is architectural, not a loss alone.** A physics penalty on an
  arbitrary latent dimension is decorative — gradient descent routes thermal
  information around it. Grounding the heat-dissipation decoder to `z_phys` alone
  forces the constraint to bind.
- **MVP is post-session only.** The ODE-RNN encoder needs the full session. Streaming
  (VQ-VAE) is deferred and will be **distilled** from the trained model, not
  co-trained — the two latent spaces are not interchangeable.
- **Complexity must beat a baseline.** A plain supervised GRU on raw frames is trained
  first. The world model ships only if it beats the GRU on held-out synthetic data
  (quality F1 *and* fusion MAE) and shows valid counterfactuals. Otherwise the GRU
  ships.
- **No millimetres before coupon validation.** Until fusion depth is validated against
  physically sectioned coupons, the UI shows qualitative risk bands only. A precise
  wrong number is the most dangerous possible output.
- **No images.** The system uses four scalar channels. Image-based weld-pool sensing
  is a different, easier problem and is out of scope; image datasets serve only as a
  defect-taxonomy reference.
- **Aluminium, not steel.** The Goldak model is re-parameterised for Al 6061 (η ≈ 0.8,
  aluminium thermal constants). The steel-oriented standards in the knowledge base
  must be reconciled before any production claim.

## 6. Data strategy — three layers, not interchangeable

| Layer | Purpose | Source | Note |
|---|---|---|---|
| Synthetic (Goldak) | Train the model; the only source of fusion-depth labels | Generated | The MVP training set |
| Public real | Optional encoder pre-training on real arc noise | Polito RSW (open); Intel (gated) | Has neither the channels nor depth labels — pre-training only |
| Own real | The reality anchor: calibration, transfer, validation | ESP32 captures + sectioned coupons | Required; nothing substitutes |

Synthetic is the amplifier; real is the anchor. Validating synthetic against synthetic
is circular and prohibited — the central correction of this plan.

## 7. Validation gates

No component advances on expectation; each advances on a number. Kill criteria are
fixed before the experiment and not moved after seeing data.

| Gate | Proves | Kill criterion |
|---|---|---|
| **0 — Reality** | ≥30 real sessions + ≥8 sectioned coupons; heat-diss verified on hardware | Real stats unlike mock → existing results also invalid; re-baseline |
| **1 — Simulator validity** | Penetration within ±25% of coupons; direction-of-change correct | Wrong on transients → synthetic labels are noise; transient FEM or stop |
| **1.5 — Observability ceiling** | Oracle regressor (4 channels → depth) ≤ ~1.0 mm error in sim | Ceiling > 1 mm → 4 channels insufficient; add sensing |
| **2 — Representation** | Latent probe beats hand features; ≥ GBDT on held-out | Latent adds nothing |
| **3 — Earn the complexity** | Beats GRU (F1 and fusion MAE); counterfactual monotonicity ≥95%; physics ablation measurable | GRU wins → ship GRU. Ablation null → physics decorative |
| **4 — Transfer** | Feature-decoder R² ≥ 0.5 on real; latent KL syn↔real < 0.5 nats | No transfer happened |
| **5 — Fusion truth** | MAE ≤ 1.0 mm vs fresh ≥10 coupons; direction ≥90% | Until passed: risk bands only |
| **6 — Deployment** | 2–4 wk shadow; FNR = 0.000 on expanded eval; OOD wired; p95 ≤ 500 ms | Any missed defect → not deployable |

*0.5 — optional public-data pre-training, runs parallel to Gate 0. 7 — edge viability,
deferred with the streaming student.*

## 8. Scope

- **MVP:** post-session fusion-depth + quality estimation on synthetic data —
  encoder, Neural ODE, four heads, GRU baseline, eval harness.
- **Deferred:** streaming / edge inference (distilled student, Gate 7); additional
  defect heads (HAZ softening, hot-cracking risk) on the shared thermal latent;
  counterfactual explorer; 3D visualisation (post coupon validation only).
- **Out of scope:** image/vision sensing; changes to the existing agent/disposition
  layer.

## 9. Principles

- Pre-registered kill criteria, never moved after seeing data.
- Every complex component must beat its boring baseline on held-out data.
- One physical validation artifact (a sectioned coupon vs predicted depth) outweighs
  any number of synthetic metrics.
- Negative results are documented, not hidden.
- The deterministic safety floor (FNR = 0.000) sits below every learned component and
  is never replaced.

## 10. Status

Planning, pre-Gate-0. The repository contains no real weld data — all sessions are
synthetic/mock, and no world-model code is implemented yet. Immediate path: build
`goldak.py` (aluminium) and the observability-ceiling test, train the GRU baseline,
and begin real-data collection (Gate 0) in parallel. No fusion-depth figure is
surfaced in any UI until Gate 5 passes.
