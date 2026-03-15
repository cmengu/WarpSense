# Plan: session_feature_extractor.py (v2 — LOF/LOP focused)

**Overall Progress:** `100%` (3/3 steps complete)

---

## TLDR

Build `backend/features/session_feature_extractor.py`. It collapses 1500 raw sensor frames into 11 features specifically selected to predict Lack of Fusion and Lack of Penetration — the defect class invisible to X-ray, visual, and dye penetrant inspection (Amirafshari & Kolios, IJF 2022). LOF/LOP has a direct parameter signature: sustained low heat input, torch angle deviation from optimal, and sudden heat input drops at transition points. This file is the only input the classifier will see.

---

## Critical Decisions

- **LOF/LOP as target defect class** — features are selected for their causal relationship to fusion failure, not general weld quality. This is the defensible research position: conventional inspection misses LOF/LOP; parameter monitoring catches it.
- **`min_rolling_heat_input` over `mean_heat_input`** — a weld can have acceptable mean heat input while containing a 2-second cold window that caused LOF. The minimum of the rolling mean catches that cold window. Mean does not.
- **Torch angle expressed as deviation from optimal** — raw `angle_degrees` mean is less useful than `|angle - optimal|`. For aluminum MIG, optimal work angle is ~55°. Deviation from that is the causal signal for misdirected heat.
- **`heat_input_drop_severity`** — max single-window *decrease* in heat input (negative delta between consecutive rolling windows). Sudden drops at stitch transitions are LOF risk points.
- **One window size (1s = 100 frames)** — training set is small (~10 sessions initially). Feature count must stay proportional to sample count.
- **`heat_dissipation_rate_celsius_per_sec` nullable** — frame 0 is always None (no previous frame to diff against). All rolling features on this field use `.fillna(0)` before computation.
- **Output path: `backend/features/`** — `backend/src/` does not exist. File goes alongside existing `extractor.py` and `warp_features.py`.
- **Import strategy: `cd backend && python3` with `sys.path.insert(0, ".")`** — All executable blocks in this plan run from project root with `cd backend` and use `from data.*` / `from features.*` imports. No `backend.` prefix. No path manipulation inside `generate_feature_dataset()`.

---

## Agent Failure Protocol

1. A verification command fails → read the full error output.
2. Cause is unambiguous → make ONE targeted fix → re-run the same verification command.
3. If still failing after one fix → **STOP**. Output full contents of every file modified in this step. Report: (a) command run, (b) full error verbatim, (c) fix attempted, (d) exact state of each modified file, (e) why you cannot proceed.
4. Never attempt a second fix without human instruction.
5. Never modify files not named in the current step.

---

## Clarification Gate

All unknowns resolved from pre-flight output.

| Unknown | Required | Resolved Value |
|---------|----------|----------------|
| Frame field names | Exact keys in frame dicts | `volts`, `amps`, `angle_degrees`, `heat_dissipation_rate_celsius_per_sec` |
| Output directory | Where to write the new file | `backend/features/` (exists; `backend/src/` does not) |
| heat_diss nullable | Can it be None for arc-on frames? | Yes — frame 0 always None. Use `.fillna(0)` |
| Existing files in `backend/features/` | What already exists | `extractor.py`, `warp_features.py`, `__init__.py` |
| Frame serialisation method | How to convert frame to dict | **Filled by pre-flight item 5** — if blank → do not proceed |

---

## Pre-Flight — Run Before Any Code Changes

**Working directory for all commands:** Run from project root; each command uses `cd backend` where execution is required.

```
1. Read backend/features/extractor.py in full — confirm no SessionFeatureExtractor class already exists
2. Read backend/features/warp_features.py in full — confirm no SessionFeatures dataclass already exists
3. Run: grep -n "class SessionFeatureExtractor\|class SessionFeatures" backend/features/extractor.py backend/features/warp_features.py
   Expected: 0 matches. If any match → STOP and report.
4. Run: grep -n "def _generate_stitch_expert_frames\|def _generate_continuous_novice_frames" backend/data/mock_sessions.py
   Capture: exact function signatures (confirm they accept session_index, num_frames)
5. Run: cd backend && python3 -c "
import sys
sys.path.insert(0, '.')
from data.mock_sessions import _generate_stitch_expert_frames
f = _generate_stitch_expert_frames(0, 5)
obj = f[0]
print('TYPE:', type(obj).__name__)
print('MODULE:', type(obj).__module__)
if hasattr(obj, 'model_dump'):
    d = obj.model_dump()
    print('SERIALISATION: model_dump')
elif isinstance(obj, dict):
    d = obj
    print('SERIALISATION: dict')
elif hasattr(obj, '__dict__'):
    d = vars(obj)
    print('SERIALISATION: vars')
else:
    d = dict(obj)
    print('SERIALISATION: dict')
print('KEYS:', sorted(k for k in d.keys() if not k.startswith('_')))
"
   Capture: TYPE, MODULE, SERIALISATION, and KEYS. These fill the Baseline Snapshot.
6. Run: wc -l backend/features/extractor.py backend/features/warp_features.py
   Capture: line counts for post-plan diff
7. Run: wc -l backend/features/session_feature_extractor.py 2>/dev/null || echo "File does not exist yet"
   Capture: 0 or line count (for Step 3 append anchor)
```

**Do not change anything. Show full output and wait.**

**Baseline Snapshot (agent fills during pre-flight):**
```
SessionFeatureExtractor already exists:   no (must confirm)
SessionFeatures already exists:           no (must confirm)
Frame type at runtime:                    ____ (from TYPE line)
Frame serialisation method:               ____ (from SERIALISATION line; model_dump | vars | dict)
Frame keys at runtime:                    ____ (from KEYS line)
Line count extractor.py:                  ____
Line count warp_features.py:              ____
session_feature_extractor.py line count:  ____ (0 if not yet created)
```

**BLOCKING GATE:** If `Frame type at runtime` or `Frame serialisation method` is blank after item 5 → **do not proceed to Step 1**. Re-run pre-flight item 5 from `cd backend` and capture output. The frame serialisation assumption is the most likely runtime failure — this is a hard stop.

---

## Tasks

### Phase 1 — Feature Extractor

**Goal:** `SessionFeatures` dataclass and `SessionFeatureExtractor.extract()` exist in `backend/features/session_feature_extractor.py`, run cleanly on real mock data, and produce a flat 13-feature vector with no nulls where every feature has a direct causal link to LOF/LOP risk.

---

- [x] 🟩 **Step 1: Create `backend/features/session_feature_extractor.py`** — *Critical: all downstream classifier code depends on this interface*

  **Idempotent:** Yes — file creation. Re-running overwrites with identical content.

  **Context:** This is the data contract between raw sensor frames and the ML layer. Feature names and types must not change after the classifier trains against them. The LOF/LOP framing is the research contribution — conventional methods miss this defect class; this feature set is designed to catch it.

  **Pre-Read Gate:**
  - `grep -n "class SessionFeatureExtractor\|class SessionFeatures" backend/features/extractor.py backend/features/warp_features.py` — must return 0 matches. If any → STOP.
  - Baseline Snapshot `Frame type at runtime` and `Frame serialisation method` must be filled. If blank → **STOP. Do not proceed.** Re-run pre-flight item 5.
  - Build `to_dicts` using the captured serialisation method: if `model_dump` → `[f.model_dump() for f in frames]`; if `vars` → `[vars(f) for f in frames]`; if `dict` → frames are already dicts, pass through. Do not guess.

  **Self-Contained Rule:** Code block below is complete and immediately runnable.

  **No-Placeholder Rule:** No `<VALUE>` tokens below.

  ```python
  # backend/features/session_feature_extractor.py
  #
  # Feature set is designed around Lack of Fusion / Lack of Penetration (LOF/LOP) —
  # the defect class invisible to X-ray, visual, and dye penetrant inspection.
  # Source: Amirafshari & Kolios, International Journal of Fatigue, 2022.
  #
  # LOF/LOP causal parameters:
  #   1. Sustained low heat input (insufficient to melt base metal)
  #   2. Torch angle deviation (misdirected heat away from joint root)
  #   3. Sudden heat input drops at stitch transitions
  #
  # Required working directory for import: run from backend/ (cd backend) or
  # ensure backend/ is on PYTHONPATH. All callers must use this convention.

  import numpy as np
  import pandas as pd
  from dataclasses import dataclass, asdict
  from typing import List, Optional

  WINDOW_1S = 100          # 100 frames × 10ms = 1 second
  OPTIMAL_ANGLE_DEG = 55.0 # Optimal work angle for aluminum MIG


  @dataclass
  class SessionFeatures:
      session_id: str

      # --- Heat input features (primary LOF/LOP predictor) ---
      heat_input_mean: float
      # Mean of (volts × amps) across arc-on frames.
      # Baseline signal — low mean = chronic under-heating.

      heat_input_min_rolling: float
      # Minimum value of the 1s rolling mean of heat input.
      # Catches cold windows even when overall mean looks acceptable.
      # This is the key LOF/LOP signal: a weld can pass on mean but
      # contain a 2-second cold window that caused fusion failure.

      heat_input_drop_severity: float
      # Max single-window decrease: max(rolling_mean[t-1] - rolling_mean[t]).
      # Captures sudden heat drops at stitch start/stop transitions —
      # the highest-risk moments for LOF at the weld root.

      heat_input_cv: float
      # Coefficient of variation of heat input across arc-on frames.
      # Captures chronic instability distinct from single-window drops.

      # --- Torch angle features (secondary LOF/LOP predictor) ---
      angle_deviation_mean: float
      # Mean of |angle_degrees - OPTIMAL_ANGLE_DEG| across arc-on frames.
      # Causal: off-angle directs heat to weld surface, not joint root.

      angle_max_drift_1s: float
      # Max (window_max - window_min) of angle within any 1s window.
      # Captures unstable torch handling mid-weld.

      # --- Arc stability features ---
      voltage_cv: float
      # Coefficient of variation of volts across arc-on frames.
      # Voltage instability = changing arc length = inconsistent penetration depth.

      amps_cv: float
      # Coefficient of variation of amps.
      # Spiky current = inconsistent heat delivery.

      # --- Thermal dissipation features ---
      heat_diss_mean: float
      # Mean heat_dissipation_rate_celsius_per_sec (nullable → fillna(0)).
      # Proxy for how fast the workpiece is cooling between inputs.

      heat_diss_max_spike: float
      # Max 1s rolling std of heat dissipation rate.
      # Captures thermal instability windows.

      # --- Session structure ---
      arc_on_ratio: float
      # Arc-on frames / total frames.
      # For stitch welds: lower ratio = more inter-stitch gaps = more LOF risk points.

      # --- Label ---
      quality_label: Optional[str] = None
      # GOOD / MARGINAL / DEFECTIVE. None at inference time.

      def to_vector(self) -> dict:
          """Flat dict for XGBoost. Excludes session_id and quality_label."""
          d = asdict(self)
          d.pop("session_id")
          d.pop("quality_label")
          return d

      @property
      def feature_count(self) -> int:
          return len(self.to_vector())


  class SessionFeatureExtractor:
      """
      Converts a list of raw sensor frames into a SessionFeatures instance.
      All features have a direct causal link to LOF/LOP risk.
      """

      def extract(
          self,
          session_id: str,
          frames: List[dict],
          quality_label: Optional[str] = None,
      ) -> SessionFeatures:

          df = pd.DataFrame(frames)

          # Validate expected columns
          required = {"volts", "amps", "angle_degrees",
                      "heat_dissipation_rate_celsius_per_sec"}
          missing = required - set(df.columns)
          if missing:
              raise ValueError(
                  f"Session {session_id}: missing columns {missing}. "
                  f"Found: {list(df.columns)}"
              )

          total_frames = len(df)

          # Arc-on filter: exclude dead arc frames (startup noise, inter-stitch gaps)
          arc_on = df[(df["volts"] > 5) & (df["amps"] > 5)].copy().reset_index(drop=True)

          if len(arc_on) < WINDOW_1S:
              raise ValueError(
                  f"Session {session_id}: only {len(arc_on)} arc-on frames "
                  f"(minimum {WINDOW_1S} required for rolling features)."
              )

          # Nullable field: heat_dissipation_rate is None for frame 0
          arc_on["heat_dissipation_rate_celsius_per_sec"] = (
              arc_on["heat_dissipation_rate_celsius_per_sec"].fillna(0.0)
          )

          # Derived signal: heat input per frame
          arc_on["heat_input"] = arc_on["volts"] * arc_on["amps"]

          # Rolling 1s mean of heat input
          rolling_heat_mean = arc_on["heat_input"].rolling(WINDOW_1S).mean()

          # Heat input drop: max decrease between consecutive rolling windows
          rolling_deltas = rolling_heat_mean.diff()
          heat_input_drop_severity = float(
              (-rolling_deltas).clip(lower=0).max()
          )

          # Torch angle deviation from optimal
          arc_on["angle_deviation"] = (
              arc_on["angle_degrees"] - OPTIMAL_ANGLE_DEG
          ).abs()

          # Arc stability
          voltage_mean = arc_on["volts"].mean()
          amps_mean = arc_on["amps"].mean()
          voltage_cv = (
              arc_on["volts"].std() / voltage_mean if voltage_mean > 0 else 0.0
          )
          amps_cv = (
              arc_on["amps"].std() / amps_mean if amps_mean > 0 else 0.0
          )

          # Heat input CV
          heat_input_mean = arc_on["heat_input"].mean()
          heat_input_cv = (
              arc_on["heat_input"].std() / heat_input_mean
              if heat_input_mean > 0 else 0.0
          )

          return SessionFeatures(
              session_id=session_id,
              quality_label=quality_label,

              heat_input_mean=float(heat_input_mean),
              heat_input_min_rolling=float(rolling_heat_mean.min()),
              heat_input_drop_severity=float(heat_input_drop_severity),
              heat_input_cv=float(heat_input_cv),

              angle_deviation_mean=float(arc_on["angle_deviation"].mean()),
              angle_max_drift_1s=float(
                  arc_on["angle_degrees"]
                  .rolling(WINDOW_1S)
                  .apply(lambda x: x.max() - x.min(), raw=True)
                  .max()
              ),

              voltage_cv=float(voltage_cv),
              amps_cv=float(amps_cv),

              heat_diss_mean=float(
                  arc_on["heat_dissipation_rate_celsius_per_sec"].mean()
              ),
              heat_diss_max_spike=float(
                  arc_on["heat_dissipation_rate_celsius_per_sec"]
                  .rolling(WINDOW_1S).std().max()
              ),

              arc_on_ratio=float(len(arc_on) / total_frames),
          )
  ```

  **What it does:** Converts 1500 raw frames into 11 named floats (plus session_id and label). Every feature maps to a LOF/LOP causal mechanism documented in the inline comments.

  **Why this approach:** `heat_input_min_rolling` over mean because LOF happens in cold *windows*, not on average. `angle_deviation_mean` over raw angle because the causal variable is distance from optimal, not absolute angle. `heat_input_drop_severity` specifically targets stitch transition risk points.

  **Assumptions:**
  - Frame objects serialise to dicts with keys `volts`, `amps`, `angle_degrees`, `heat_dissipation_rate_celsius_per_sec` (confirmed pre-flight)
  - Sessions have ≥100 arc-on frames (both mock session types run 1500 frames; this is safe)
  - pandas and numpy available in backend environment

  **Risks:**
  - Frame objects don't serialise to plain dicts → `pd.DataFrame(frames)` fails or produces wrong columns → mitigation: pre-flight item 5 captures exact serialisation; blocking gate prevents proceeding if blank
  - `heat_dissipation_rate_celsius_per_sec` has nulls beyond frame 0 → rolling std returns NaN → mitigation: `.fillna(0)` is applied before all computations on this field

  **Git Checkpoint:**
  ```bash
  git add backend/features/session_feature_extractor.py
  git commit -m "step 1: add SessionFeatureExtractor with 11 LOF/LOP-focused features"
  ```

  **Subtasks:**
  - [ ] 🟥 Confirm no `SessionFeatureExtractor` or `SessionFeatures` exists in `backend/features/`
  - [ ] 🟥 Confirm Baseline Snapshot `Frame serialisation method` is filled (blocking gate)
  - [ ] 🟥 Write `session_feature_extractor.py` with exact code above
  - [ ] 🟥 Verification test passes

  **✓ Verification Test:**

  **Type:** Unit

  **Action:**
  ```bash
  cd backend && python3 - <<'EOF'
  import sys
  sys.path.insert(0, ".")
  from data.mock_sessions import _generate_stitch_expert_frames, _generate_continuous_novice_frames
  from features.session_feature_extractor import SessionFeatureExtractor

  # Use serialisation method from pre-flight. Default: model_dump for Pydantic.
  def to_dicts(frames):
      f0 = frames[0]
      if hasattr(f0, "model_dump"):
          return [f.model_dump() for f in frames]
      if isinstance(f0, dict):
          return list(frames)
      return [vars(f) for f in frames]

  extractor = SessionFeatureExtractor()

  expert_frames = to_dicts(_generate_stitch_expert_frames(0, 1500))
  novice_frames = to_dicts(_generate_continuous_novice_frames(0, 1500))

  e = extractor.extract("expert_test", expert_frames, "GOOD")
  n = extractor.extract("novice_test", novice_frames, "MARGINAL")

  vec = e.to_vector()
  assert len(vec) == 11, f"Expected 11 features, got {len(vec)}: {list(vec.keys())}"
  assert all(v is not None for v in vec.values()), f"Nulls found: {[k for k,v in vec.items() if v is None]}"
  assert all(not __import__('math').isnan(v) for v in vec.values()), f"NaNs found: {[k for k,v in vec.items() if __import__('math').isnan(v)]}"

  # LOF/LOP signal check: novice should show worse values on key features
  assert n.angle_deviation_mean > e.angle_deviation_mean, \
      f"Expected novice angle deviation > expert: {n.angle_deviation_mean:.2f} vs {e.angle_deviation_mean:.2f}"
  assert n.voltage_cv > e.voltage_cv, \
      f"Expected novice voltage_cv > expert: {n.voltage_cv:.4f} vs {e.voltage_cv:.4f}"

  print("PASS")
  print(f"\n{'Feature':<30} {'Expert':>10} {'Novice':>10}")
  print("-" * 52)
  nv = n.to_vector()
  for k, ev_val in vec.items():
      print(f"{k:<30} {ev_val:>10.3f} {nv[k]:>10.3f}")
  EOF
  ```

  **Expected:**
  - Prints `PASS`
  - 11 features, no nulls, no NaNs
  - `angle_deviation_mean` higher for novice than expert
  - `voltage_cv` higher for novice than expert

  **Observe:** Terminal output

  **Pass:** `PASS` printed, both assertions hold

  **Fail:**
  - `ModuleNotFoundError: features` → run from wrong directory → confirm `cd backend` and `ls features/__init__.py`
  - `missing columns` ValueError → frame serialisation returned unexpected keys → re-run pre-flight item 5, verify SERIALISATION and KEYS, fix to_dicts to match
  - NaN in any feature → `heat_dissipation_rate_celsius_per_sec` has nulls beyond frame 0 → add `.dropna()` audit: `arc_on["heat_dissipation_rate_celsius_per_sec"].isna().sum()` and report

---

- [x] 🟩 **Step 2: Smoke test — LOF/LOP signal separation** — *Non-critical: confirms the features discriminate before classifier is built*

  **Idempotent:** Yes — read-only

  **Action:**
  ```bash
  cd backend && python3 - <<'EOF'
  import sys, math
  sys.path.insert(0, ".")
  from data.mock_sessions import _generate_stitch_expert_frames, _generate_continuous_novice_frames
  from features.session_feature_extractor import SessionFeatureExtractor

  def to_dicts(frames):
      f0 = frames[0]
      if hasattr(f0, "model_dump"):
          return [f.model_dump() for f in frames]
      if isinstance(f0, dict):
          return list(frames)
      return [vars(f) for f in frames]

  extractor = SessionFeatureExtractor()
  e = extractor.extract("e", to_dicts(_generate_stitch_expert_frames(0, 1500)), "GOOD")
  n = extractor.extract("n", to_dicts(_generate_continuous_novice_frames(0, 1500)), "MARGINAL")

  ev, nv = e.to_vector(), n.to_vector()

  LOF_LOP_FEATURES = [
      "heat_input_min_rolling",
      "heat_input_drop_severity",
      "angle_deviation_mean",
      "angle_max_drift_1s",
      "voltage_cv",
  ]

  print(f"\n{'Feature':<30} {'Expert':>10} {'Novice':>10} {'Sep?':>8}")
  print("-" * 62)
  separated = 0
  for k in ev:
      sep = abs(ev[k] - nv[k]) > 0.05 * max(abs(ev[k]), abs(nv[k]), 1)
      tag = "YES" if sep else "-"
      marker = " ← LOF/LOP" if k in LOF_LOP_FEATURES and sep else ""
      print(f"{k:<30} {ev[k]:>10.3f} {nv[k]:>10.3f} {tag:>8}{marker}")
      if sep:
          separated += 1

  print(f"\nSeparated features: {separated}/11")
  assert separated >= 4, f"Only {separated} features separated — classifier may not learn"
  print("PASS — sufficient signal for classifier")
  EOF
  ```

  **Expected:** ≥4 features separated. `angle_deviation_mean`, `voltage_cv`, and `angle_max_drift_1s` should all show separation based on known expert vs novice differences in raw data.

  **Pass:** `PASS` printed, LOF/LOP features show separation

  **Fail:** Fewer than 4 separated → raw data differences not surviving feature computation → check arc-on filter isn't excluding too many novice frames → print `arc_on_ratio` for both sessions

---

- [x] 🟩 **Step 3: Add `generate_feature_dataset()` utility** — *Non-critical: convenience wrapper for classifier training*

  **Idempotent:** Yes

  **Context:** The classifier training script needs all sessions as a list of `SessionFeatures`. This function wraps the mock archetypes. Append to bottom of existing file — do not modify any existing code. No `sys.path.insert` or path manipulation inside the function. Imports use the same convention: caller runs from `cd backend` or has `backend/` on PYTHONPATH.

  **Pre-Read Gate:**
  - `grep -n "def generate_feature_dataset" backend/features/session_feature_extractor.py` — must return 0 matches. If already exists → STOP.
  - Run: `wc -l backend/features/session_feature_extractor.py` — capture line count N. Insert new code **after line N** (at EOF). If file has trailing newline, the new block starts on line N+1.

  **Append instruction:** Open `backend/features/session_feature_extractor.py`. The last line of the file is line N (from wc -l). Add exactly one blank line after the existing content (if not already present), then append the following block. The new function must use module-level imports — no sys.path or os.path manipulation inside the function.

  **Append this block after line N of `backend/features/session_feature_extractor.py`:**

  ```python

  def generate_feature_dataset() -> List[SessionFeatures]:
      """
      Returns SessionFeatures for all mock sessions.
      Quality labels inferred from archetype:
        stitch_expert       → GOOD
        continuous_novice   → MARGINAL
      Caller must run from backend/ or have backend/ on PYTHONPATH.
      """
      # Local import: this utility is only called during training.
      # Caller must run from cd backend or have backend/ on PYTHONPATH.
      from data.mock_sessions import (
          _generate_stitch_expert_frames,
          _generate_continuous_novice_frames,
      )

      def to_dicts(frames):
          f0 = frames[0]
          if hasattr(f0, "model_dump"):
              return [f.model_dump() for f in frames]
          if isinstance(f0, dict):
              return list(frames)
          return [vars(f) for f in frames]

      ARCHETYPES = [
          ("stitch_expert",     _generate_stitch_expert_frames,     "GOOD",     4),
          ("continuous_novice", _generate_continuous_novice_frames,  "MARGINAL", 6),
      ]

      extractor = SessionFeatureExtractor()
      dataset: List[SessionFeatures] = []

      for arc_type, generator_fn, label, n_sessions in ARCHETYPES:
          for i in range(n_sessions):
              session_id = f"sess_{arc_type}_{i+1:03d}"
              frames = generator_fn(i, 1500)
              frames_as_dicts = to_dicts(frames)
              features = extractor.extract(session_id, frames_as_dicts, label)
              dataset.append(features)

      return dataset
  ```

  **✓ Verification Test:**

  **Type:** Unit

  **Action:**
  ```bash
  cd backend && python3 - <<'EOF'
  import sys
  sys.path.insert(0, ".")
  from features.session_feature_extractor import generate_feature_dataset

  dataset = generate_feature_dataset()
  labels = [f.quality_label for f in dataset]

  assert len(dataset) == 10, f"Expected 10 sessions, got {len(dataset)}"
  assert labels.count("GOOD") == 4, f"Expected 4 GOOD, got {labels.count('GOOD')}"
  assert labels.count("MARGINAL") == 6, f"Expected 6 MARGINAL, got {labels.count('MARGINAL')}"
  assert all(len(f.to_vector()) == 11 for f in dataset), "Feature count inconsistent across sessions"

  print(f"PASS — {len(dataset)} sessions: {labels.count('GOOD')} GOOD, {labels.count('MARGINAL')} MARGINAL")
  print(f"Feature count per session: {dataset[0].feature_count}")
  EOF
  ```

  **Pass:** `PASS — 10 sessions: 4 GOOD, 6 MARGINAL`

  **Fail:**
  - Wrong session count → `n_sessions` in ARCHETYPES doesn't match `mock_welders.py` → grep welder definitions and adjust
  - Import error on `_generate_stitch_expert_frames` → function name changed → grep `mock_sessions.py` for actual function name
  - `ModuleNotFoundError` → caller did not run from `cd backend` → verify command uses `cd backend && python3`

  **Git Checkpoint:**
  ```bash
  git add backend/features/session_feature_extractor.py
  git commit -m "step 3: add generate_feature_dataset() for classifier training"
  ```

---

## Regression Guard

This plan only adds one new file to `backend/features/`. It does not modify `extractor.py`, `warp_features.py`, `mock_sessions.py`, or any route. No regression risk to existing functionality.

Post-plan check: confirm `backend/features/extractor.py` and `warp_features.py` line counts match pre-flight baseline.

---

## Success Criteria

| Feature | Target | Verification |
|---------|--------|--------------|
| `SessionFeatures` dataclass | 11 features, no nulls, no NaNs | Step 1 assertion: `len(vec) == 11` |
| LOF/LOP signal separation | `angle_deviation_mean` and `voltage_cv` higher for novice | Step 1 assertions pass |
| Dataset generation | 10 sessions, 4 GOOD + 6 MARGINAL | Step 3 verification passes |
| No regressions | `extractor.py` and `warp_features.py` unchanged | Line counts match pre-flight baseline |

---

⚠️ Do not mark a step 🟩 Done until its verification test passes.
⚠️ Do not modify `extractor.py` or `warp_features.py` — read only.
⚠️ If `Frame type at runtime` or `Frame serialisation method` is blank after pre-flight item 5 → **STOP. Do not proceed to Step 1.**
⚠️ If frame serialisation produces unexpected field names, stop at Pre-Read Gate and report exact runtime field names found.
⚠️ If any feature returns NaN, report `arc_on["heat_dissipation_rate_celsius_per_sec"].isna().sum()` before attempting any fix.
