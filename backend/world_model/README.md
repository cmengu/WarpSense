# world_model/ — the weld world model, from first principles

Working plan and step statuses: `STEPS.md` at repo root (single source of truth).
Gates and rationale: `FUTURE_PLANS_WORLD_MODELS.md`. This README explains the
*fundamentals* behind Steps 1–7 — what each piece is, and why it exists — for
someone who has never touched the subject.

## The problem, before any code

A weld is a physical process you can't see inside. The metal melts, fuses to a
certain **depth**, and solidifies — and that depth decides whether the joint
holds. But our sensors never measure it. They measure *side effects* at 100
frames per second: voltage, current, torch angle, travel angle, travel speed,
and heat-dissipation rate. Six numbers per frame, ~1500 frames per weld.

The whole project is one question: **can you recover the hidden state of a
physical process from its observable side effects?** Steps 1–6 don't answer it
— they build the equipment to answer it *honestly*. Every step pairs a
capability with an anti-self-deception mechanism, because the default outcome
of an ML project is fooling yourself with a leaked metric or a circular
validation.

```
Step 1  canonical tensors      ↔  session-level splits (no frame leakage)
Step 2  visualization          ↔  data bugs visible before any model exists
Step 3  a model                ↔  a boring baseline the fancy model must beat
Step 4  a simulator            ↔  a calibration gate before its data counts
Step 5  a feasibility number   ↔  GroupKFold + a kill criterion fixed in advance
Step 6  pretraining            ↔  a mean-predictor floor it had to beat
Step 7  the world model itself ↔  its load-bearing wiring pinned by tests
```

---

## Step 1 — Canonical schema, loaders, splits (`data/`)

A neural network doesn't eat "welds," it eats tensors — rectangular arrays of
numbers. So the first decision is: what is *the* shape of one weld?

**`schema.py` — `SessionTensor`.** One session is a matrix `x[T, 6]`: one
**row per moment** (100 rows/second), one **column per sensor**. A *channel*
is one column — the full time history of one measurement:

```
            volts   amps   angle  travel_ang  speed  heat_diss
t=0.00s   [ 22.1,  198.3,  45.2,     12.1,    398.0,    0.4 ]
t=0.01s   [ 22.3,  199.1,  45.0,     12.3,    401.2,    0.5 ]
  ...        ...     ...    ...       ...       ...      ...
t=14.99s  [  0.1,    0.2,  46.1,     14.8,    352.1,  118.9 ]
          — shape [T=1500, C=6]: 1500 moments × 6 sensors —
```

("6 channels = 6 dimensions" only in the bookkeeping sense: each row is a
point in a 6-dimensional space the way a spreadsheet row with six cells is.
Nothing spatial. A tensor's "dimensions" means its shape — `[T, 6]` is a 2-D
array whose second axis has size 6.)

Alongside `x` rides `mask[T, 6]`, a boolean matrix answering "is this cell
real?" per entry. Missingness is a first-class citizen of the format because
real sensors go missing: the Polito dataset carries 2 of our 6 channels, and a
field ESP32 may drop one. One mechanism handles it everywhere — batch padding
(`batch.py`) reuses the same mask, so padded frames and absent sensors are the
same case by construction.

**`loader_mock.py` / `loader_polito.py` / `loader_esp32.py`** are converters
*into* that format. Nothing downstream ever sees a raw format.

**`splits.py` — where the first self-deception lives.** You must score on data
the model never saw, but *how* you split matters: consecutive frames of one
weld are nearly identical (autocorrelation). If frames of weld #7 land in both
train and test, the model can "recognize weld #7" instead of learning welding,
and the score inflates. So we split by **session**, never by frame, using a
salted hash of the session ID — deterministic, so a session never migrates
between splits as the corpus grows (D9).

## Step 2 — Visualization, built early (`viz/timeline.py`)

Most data bugs are invisible in aggregate statistics and obvious to the eye —
a channel that's all zeros, a normalization applied twice, a reversed time
axis. So the eyes come before any model: `timeline.py` renders any
SessionTensor as **six stacked line plots sharing one time axis** — one
subplot per column of the matrix (that is all "plotting 6 channels" means).
Masked spans are greyed out so absent data is *visibly* absent, and overlay
rows can carry model outputs later (predicted depth, `z_phys` traces, risk
bands — dev only; no mm figures in any UI until Gate 5, D10).

On a good plot you can read the physics across subplots: in a stitch weld,
volts and amps drop to zero together at every stitch boundary, and the
heat-dissipation row spikes at exactly those moments — the weld pool dumping
heat the instant the arc stops feeding it. That cross-channel structure is
what the models must learn.

![Mock stitch-expert weld: six stacked channel subplots sharing one time axis](experiments/plots/mock_stitch_expert_0000.png)

*Mock stitch-expert weld, all 6 channels present. Each subplot is one column
of `x[1500, 6]` against time. Volts and amps drop to zero together six times
(arc off between stitches), and every time they do, heat_dissipation spikes.*

The mask made visible — a real Polito weld, which carries only 2 of our 6
sensors:

![Polito spot weld: volts and amps present, four channels greyed out as absent](experiments/plots/polito_0003_0_3_2023-06-13.png)

*Real Polito spot weld #3. Same 6-row format, but 4 rows say "channel absent"
— mask=False, drawn grey so missing data is visibly missing rather than
silently zero. Note the volts/amps y-axis: 0–1, because the dataset authors
pre-normalized. Every data source flows through this one format; that is the
whole point of SessionTensor.*

## Step 3 — The GRU baseline (`baselines/`, `architecture/stems.py`)

Two fundamentals here — one about the model, one about method.

**What a stem is.** Raw channels have wildly different scales and meanings —
22 volts, 400 mm/min, 45 degrees. A **stem** is a small learned translator for
*one* channel: a `Conv1d` window sliding over 5 consecutive frames of that
single sensor, emitting 16 learned numbers per frame describing the local
motion (rising? spiking? flat?). One column `[T]` becomes `[T, 16]`.

```
volts [T] ──▶ stems["volts"] (Conv1d, k=5) ──▶ [T, 16]
amps  [T] ──▶ stems["amps"]  (Conv1d, k=5) ──▶ [T, 16]
angle — absent ──▶ stems["angle"] skipped (mask) ──▶ contributes nothing
                          │
        MEAN over channels present at each frame
                          ▼
                       [T, 16] ──▶ trunk
```

Two choices in that picture do all the work. **One stem per channel *name***:
the stems live in a `ModuleDict` keyed by string — six separate little
experts. That keying is the transfer mechanism (D5): Polito data only ever
exercises `stems["volts"]` and `stems["amps"]`, so exactly those two entries
carry real-data knowledge into the world model. **Mean, not sum**, over
available channels: a sum would make a 6-sensor frame's embedding three times
larger in magnitude than a 2-sensor frame's; a mean keeps them in the same
space regardless of sensor count.

**What a GRU is.** A weld is a *sequence* — order carries the information. A
recurrent network processes it by carrying a **hidden state** `h` (here 64
numbers) updated once per frame: `h_new = f(h_old, frame)`. Think of `h` as
working memory — a running summary of everything seen so far. A **GRU** (Gated
Recurrent Unit) is an update rule with *learned gates*: at each frame the
network decides how much old memory to keep and how much to overwrite. Without
gates, frame 10's memory washes out by frame 1500; gates let it hold "there
was a heat drop at second 3" for the rest of the weld. After the last frame,
`h_T` summarizes the whole weld and a linear head reads the quality class off
it.

**Why build the boring model first.** Never build the fancy thing without a
cheap opponent. The world model (controlled Latent ODE, physics losses,
counterfactuals) is months of work; a plain GRU classifier is days. If the
fancy thing can't beat the boring thing on the same data — same stems, same
tensors, so the fight is model-vs-model, not pipeline-vs-pipeline — you ship
the boring thing. Pre-registered as Gate 3. The baseline is the bar the world
model must clear to *earn its complexity*.

## Step 4 — The Goldak simulator (`simulator/`)

**The data problem:** zero real arc-welding sessions with known fusion depth
exist here. Ground truth means physically cutting welds open (sectioning
coupons) — slow, expensive, capped at dozens. Networks want thousands. The
classic escape: simulate.

**The physics:** welding is at its core a heat problem. Goldak's 1984 model
describes the arc as a **double-ellipsoid heat source** — a 3-D blob of power
injection, steeper in front, trailing behind, moving along the plate. Feed it
into the heat-conduction equation and you get the temperature field over time;
fusion depth falls out by definition (how deep does the melting-point region
reach?). The simulator emits full sessions: the 6 sensor channels *plus* the
hidden per-frame depth label no real sensor can provide. In a stitch weld the
depth trace saw-tooths — builds while the arc is on, decays while it's off:

![Goldak simulated session: six channels plus a ground-truth fusion depth row](experiments/plots/goldak_00003.png)

*Simulated Goldak session #3. Same six channels on top — but the bottom row is
**depth true**: the fusion depth at every frame, known exactly because the
physics model computed it. This label is what Step 5's oracle predicts and is
scored against.*

**The trap it creates:** a simulator gives infinite labeled data *of the
simulator*, not of reality. Train on it, validate on it, and you've proven the
model can invert its own training data — circular. Hence Gate 1 (calibrate
against real sectioned coupons before the corpus counts) and the D10 rule (no
millimetre figure reaches any UI until Gate 5).

## Step 5 — Gate 1.5, the observability ceiling (`eval/probes.py`)

The most fundamental question, asked *before* committing months: **is fusion
depth even recoverable from these six channels?** Information-theoretically:
if two welds with different depths produce indistinguishable sensor streams,
no architecture can tell them apart — model capacity cannot create information
absent from the input.

**The oracle trick:** to measure the *ceiling* rather than any one model's
skill, make the problem as easy as possible and see if it's solvable at all.
Simulated data (truth known), 100-frame windows, hand-computed features, a
gradient-boosted tree — a strong, cheap, zero-tuning learner given every
advantage. Its predictions are scored against the simulator's own depth row.
If even the pampered oracle fails, the signal isn't there, and the project
stops before the expensive part. That's what a **gate** is: a kill criterion
fixed before seeing results, so a bad number can't be rationalized afterward.

**The subtle trap, leakage again:** overlapping windows from one session are
near-duplicates; ordinary cross-validation scatters them across folds and the
oracle "recognizes the session" — a false green light on the plan's most
important number. Hence **GroupKFold by session**: whole sessions stay in one
fold.

**Result (see `experiments/gate_status.md`):** oracle MAE **0.109 mm** vs a
1.0 mm threshold (mean-predictor baseline 0.66 mm) → PASS. Deliberately a
"mini-gate": cheap and knowingly circular (model of the simulator, judged by
the simulator), which is legitimate for the one question it asks — *do the
channels carry the signal at all?* A mini-gate buys an early, cheap **no**;
only real coupons (Gates 1/5) can buy the expensive **yes**. The 0.109 mm
ceiling is provisional until Gate 1 calibration.

## Step 6 — Gate 0.5, Polito pre-training (`training/pretrain_polito.py`)

**The problem it solves:** mock data is *too clean* — a model can ace it and
fall over on real arc noise. The repo's only real sensor data is Polito:
1,976 industrial spot welds (voltage, current, force; 79 faulty). It's the
wrong process (spot, not arc) with 2 of our 6 channels, so it cannot train the
final model. Its job is a **warm start**: teach the stems and trunk what real
electrical dynamics look like, then reuse those weights when the world model
trains (Step 8). This is the standard pretrain→fine-tune recipe (BERT, wav2vec,
ImageNet transfer): gradient descent from a random start on scarce data
overfits; pretraining on plentiful *related* data moves the weights to a
region where fine-tuning only has to adjust.

**How it trains,** jointly:
- **Masked reconstruction** — hide 15% of timesteps, reconstruct the sensor
  values at the hidden frames from the trunk's hidden state. The time-series
  version of BERT's masked-word objective; no labels needed; forces the trunk
  to model temporal structure.
- **Fault bit** — one logit per weld, BCE with `pos_weight = n_good/n_faulty`
  (≈24), else the model wins by always answering "good" (79 vs 1,897).

**What transfers:** exactly `{stems["volts"], stems["amps"], trunk}` — the
dictionary keying from Step 3 doing its job. The trunk is a single-layer GRU
whose weights are shape-identical to the `GRUCell` inside Step 7's ODE-RNN
encoder (pinned by a test). The recon and fault heads are pretrain-only
scaffolding and are excluded. No input normalization: Polito arrives
pre-normalized [0,1]; standardizing with statistics the ESP32 path can't
reproduce would poison the transfer.

**Result (see `experiments/gate_status.md`):** held-out masked-recon MSE
**0.00083** vs **0.0743** for the mean predictor (~90×) → the kill criterion
("pipeline can't learn real electrical dynamics at all") cleared. The fault
head is honest-but-weak (macro-F1 0.14 under the imbalance) — recorded, and
irrelevant to the warm start since it doesn't transfer. Artifact:
`experiments/checkpoints/polito_pretrain_8a68998bf644.pt`.

## Step 7 — The world model itself (`architecture/`)

### In plain English

Step 7 is the actual world model — the machine the whole project is named
after. Everything in Steps 1–6 was preparation. The old GRU baseline just
watches sensors and blurts out a verdict; it never forms an idea of *what
state the weld is in*, so it can't answer "what was the depth at second 7?"
or "what if the welder had done something different?". Step 7 builds a model
that keeps an internal picture of the weld at every moment, and rules for how
that picture changes as the welder acts. Three parts:

1. **The inspector** (`encoder.py`) — figures out the *starting* condition of
   the weld (plate fit-up, starting temperature — things no sensor measures
   directly). It reads the recording backwards so it sees the whole weld
   before describing the start, and it outputs a guess *with uncertainty*,
   not a single confident number.

2. **The physics engine** (`odefunc.py`) — instead of learning "new frame in,
   update the summary," it learns *how fast the weld's condition is changing*
   given the current condition and what the welder is doing right now (volts,
   amps, angles, travel speed). A standard maths solver adds that rate up
   over time — like turning speed into position — giving the weld's state at
   every instant. The crucial design choice is that the welder's actions are
   a live input: to ask "what if the amps were higher?", you just edit the
   actions and replay. A test locks this in so it can't silently break.

3. **The gauges** (`decoder.py`) — five deliberately simple readers that turn
   the state into outputs: heat dissipation, the control signals, the
   per-frame depth curve (the headline new output), the pass/fail quality
   verdict, and the 11 engineered features. They're kept dumb on purpose so
   all the intelligence is forced into the state itself. Four state numbers
   are pinned to actually mean "thermal state" via a crude heat-balance
   penalty plus wiring that makes the heat gauge read *only* those four.

"Done" for Step 7 is honest and modest: data flows through it forwards and
backwards on CPU, gradients reach all parts, and the key wiring is pinned by
tests. Nothing is trained yet — every weight is random until Step 8 (the
training loop) trains it.

### In full

Everything before this was equipment. Step 7 is the machine the project is
named after, and the motive comes straight from the GRU baseline's blind spot.
The baseline is one pipe: sensor table → running summary → the summary is
handed **directly to the answer heads** → verdict. It never commits to any
notion of *what state the weld is in* — so it cannot say what the depth was at
second 7, and it cannot answer "what if the welder had corrected the angle?",
because there is nothing to replay. Step 7 builds the machine that *does*
commit: an internal **state of the weld** at every instant, plus rules for how
that state evolves under the welder's actions. Three parts — an inspector, a
physics engine, and a panel of gauges.

**The inspector (`encoder.py`) — produce the starting condition.** Something
must first answer "what was the situation when this weld began?" — plate
fit-up, starting temperature, none of it directly sensed. The encoder reads
the stem embeddings **backwards** — last frame first — so that by the time it
reaches frame 0 it has seen the whole story, and its description of the start
is written with hindsight, like an inspector who watches the entire tape
before writing the report's opening line. Internally it is nearly the Step 3
trunk (same stems, same 64-number working memory — deliberately, so the Step 6
Polito weights snap straight in via `load_pretrained_trunk()`), with one
addition: between frames, the memory is nudged by `h += dt · f(h)` — a **Euler
step**, the "position += speed × time" of numerical integration — bridging the
10 ms gaps as continuous drift rather than nothing. Its output is not an
answer but a **distribution** over a 32-number starting state `z0`: a best
guess plus a spread per number, sampled during training (the VAE
reparameterisation trick) so the model cannot pretend to certainty it doesn't
have.

**The physics engine (`odefunc.py`) — evolve the condition.** The core idea in
one sentence: instead of learning "given this frame, update the summary" (the
GRU's move), learn **how fast the weld's condition is changing** — a rate:

```
dz/dt = f_θ( z,  u(t) )          f_θ: a small MLP, (32 + 5) → 64 → 64 → 32
         │     │
   current     what the welder is DOING right now: volts, amps,
   condition   both angles, travel speed — interpolated between frames
```

Knowing the rate at every instant, a standard ODE solver (`torchdiffeq`) adds
it up over the weld — exactly like integrating speed to get position — and
out comes `z_t` at every frame: the trajectory.

The load-bearing word is **controlled**. The plan docs originally wrote
`dz/dt = f_θ(z, t)` — no welder input. That version can still fit data, but
only by smuggling the entire future action sequence into `z0`, and then
"what if the amps were higher at second 7?" is *unaskable* — there is no input
to edit. With `u(t)` as a live input, the counterfactual is trivial: keep the
same `z0`, edit the action buffer, re-integrate, compare depth curves. That is
Gate 2's monotonicity battery, and it is architecturally possible *only*
because of this wiring — so a test pins it (same `z0`, edited `u(t)`, the
trajectories must differ). Solver choice is pragmatic, not clever: adaptive
`dopri5` through the **adjoint** method in training (backprop through ~1500
solver steps would store everything and blow up memory; the adjoint
re-integrates backwards instead — compute for memory), fixed-step `rk4` at
inference (predictable latency, the 500 ms p95 budget).

**The grounding vise (`z_phys`) — keep four numbers honest.** Left alone, the
32 latent numbers become an inscrutable soup and "physics-informed" becomes
decoration. So dims 0–3 are declared *thermal state* and squeezed from two
sides. Side one, a physics residual: their learned rate is penalised when it
disagrees with a crude heat balance — energy in ∝ volts × amps, energy out ∝
how hot things already are (Newtonian cooling). Side two, wiring: the
heat-dissipation gauge below may read **only** those four dims. Heat
information must flow through `z_phys` or reconstruction fails; it has nowhere
to go but "actually track heat." The two constants in the heat law are
simulator placeholders until Gate 1 fits them against sectioned coupons —
worse, `u(t)` is built from *normalised* controls, so they are placeholders
squared. Pre-registered; nobody mistakes the pre-Gate-1 physics loss for
physics.

**The gauges (`decoder.py`) — deliberately dumb readers.** Five heads read the
trajectory, and every one is a two-layer MLP (`Linear → tanh → Linear`, hidden
64) — a **multi-layer perceptron**, the plainest network there is: weighted
sums, squash, weighted sums. No attention, nothing clever, and that is the
design: if a reader were powerful it could solve the task on its own from a
mediocre latent, the "state" would become decorative, and replaying it under
edited actions would produce nonsense. Weak readers force the intelligence
into the trajectory. The five: `heat_diss_hat[t]` from `z[:, :4]` **only**
(the vise's second jaw — input width literally 4, pinned by a test that also
checks perturbing `z_free` leaves it bit-identical); `other5_hat[t]`, the five
control channels reconstructed (what nails the trajectory to the actual
session); `depth_hat[t]`, the per-frame fusion-depth curve — *the* new output;
`quality_probs` from the final state concatenated with the existing 11
engineered features (PHOENIX-style fusion — reuse, don't reimplement); and
`feats_hat`, predicting those same 11 features (free supervision for Step 8).

**`world_model.py`** assembles the three parts into `WeldWorldModel` — same
normalizer-buffers-in-the-checkpoint discipline as the GRU baseline, an
`infer(SessionTensor)` surface mirroring `GRUBaseline.predict`, and the
counterfactual hook exposed as `forward(..., controls=edited_buffer)`.

**What "done" means here — and doesn't.** Step 7's done-when was deliberately
modest: one tiny mock batch flows forward and backward on CPU through the
adjoint path, gradients reach all four components, and the wiring that must
never silently regress is pinned by tests (heat-head input == 4;
controlledness; the Polito-trunk → GRUCell name mapping; quality head width
== 32 + 11). No claim of learning anything is made or possible — every weight
is random until Step 8 trains it, and every believable number still waits on
Gates 0/1. The anti-self-deception mechanism this time is the humblest one:
the architecture's promises are encoded as tests, so the machine we eventually
evaluate is provably the machine described here.

---

## Where this leaves the plan

Steps 1–7 done; both cheap gates passed with pre-registered criteria; the
world-model machine is built, wired, and pinned — but untrained. Next in code:
Step 8 (training loop — symlog targets, free-nats KL, sigmoid fade-in of the
loss terms, warm-started from the Step 6 artifact). Steps 9+ are blocked on
Gate 0 — real data collection (30 sessions + 8 sectioned coupons), the longest
lead time in the plan and the only thing no amount of code substitutes for.

Evidence discipline (D11): every run appends to `experiments/runs.csv`; every
gate outcome is recorded in `experiments/gate_status.md` as number vs
threshold, or it didn't happen.
