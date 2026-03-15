# WarpSense Phase 2 — Step 2 Execution Plan
**Place agent files into repo and wire up Groq**

**Overall Progress:** `100%`

---

## CTO Review — Resolved Before Plan Execution

**Verdict: REVISE BEFORE EXECUTING** (resolved below — do not skip this section)

### Critical Flaws Found and Resolved

**Flaw 1 — `weld_classifier.py` never read (UNVERIFIABLE)**
Previous plan assumed `FEATURE_COLS` is module-level, `return WeldPrediction(...)` uses keyword args, and specific variable names exist in `predict()`. None confirmed.
**Resolution:** Step 2.1 now opens with a mandatory Pre-Read Gate that reads the actual file. Edit B is written conditionally: the agent reads the exact return block, then appends `top_drivers=top_drivers,` to it. If keyword args are NOT used, agent must STOP and report — do not guess.

**Flaw 2 — `cp` commands relied on files existing locally**
Previous plan required `warpsense_agent.py`, `build_welding_kb.py`, and `run_warpsense_agent.py` to be present as local files, with no guarantee of this.
**Resolution:** All three files are written inline in the plan. Agent creates them by running the embedded Python write scripts. No external files required.

**Flaw 3 — Step 2.3 applied replacements to a local copy then cp'd it**
With files written inline, this entire replacement flow is eliminated. The Groq-swapped content is embedded directly in the write script.
**Resolution:** Step 2.3 writes the final Groq version in one operation. No replacement steps.

### Logic Warnings (non-blocking, noted)

- `run_warpsense_agent.py` line 97 reads `train_report['top_3_drivers']` for display. This key already exists on `train()` return dict per Phase 1 — no change needed. Separate from `prediction.top_drivers` which is what Step 2.1 adds.
- `WarpSenseAgent.__init__` calls `client.get_collection()` which throws if ChromaDB not yet built. Runner's `ensure_kb_exists()` handles this on full run. If agent is instantiated directly in tests, KB must exist first.
- `weld_classifier.py` internal variable names in `predict()` are **UNVERIFIABLE** without reading the file. Step 2.1 Pre-Read Gate is mandatory, not optional.

---

## TLDR

Three new files are written into `backend/` entirely from content embedded in this plan — no external files required. One targeted edit is made to `backend/features/weld_classifier.py` to add `top_drivers` to `WeldPrediction`. After this plan executes: all imports resolve, the Groq-based agent is wired up, the KB builder is in place, and the end-to-end runner is ready to run. No database changes. No route changes.

---

## Critical Decisions

- **Decision 1:** Write all files inline from plan content — no dependency on local file state.
- **Decision 2:** Groq-swapped `warpsense_agent.py` is written in final form in one operation — no post-placement replacements.
- **Decision 3:** `top_drivers` added to `WeldPrediction` with `field(default_factory=list)` default — backward-compatible with any existing callers that don't pass it.

---

## Clarification Gate

| Unknown | Required | Source | Blocking | Resolved |
|---------|----------|--------|----------|----------|
| LLM provider | Groq free tier | Human (confirmed) | Step 2.3 | ✅ |
| Groq model | `llama-3.3-70b-versatile` | Groq docs | Step 2.3 | ✅ |
| `top_drivers` field exists | Does NOT exist yet | Session context | Step 2.1 | ✅ |
| `weld_classifier.py` internal var names | Unknown — must read file | Pre-Read Gate Step 2.1 | Step 2.1 | ⚠️ UNVERIFIABLE — agent reads file at runtime |

---

## Agent Failure Protocol

1. A verification command fails → read the full error output.
2. Cause is unambiguous → make ONE targeted fix → re-run the same verification command.
3. If still failing after one fix → **STOP**. Before stopping, output the full current contents of every file modified in this step. Report: (a) command run, (b) full error verbatim, (c) fix attempted, (d) exact state of each modified file, (e) why you cannot proceed.
4. Never attempt a second fix without human instruction.
5. Never modify files not named in the current step.

---

## Working Directory and Python

**All steps run from the repo root** unless a step explicitly states `cd backend`. Pre-flight and Steps 2.1–2.5 run from repo root. Step 2.6 explicitly `cd backend` before running its verification.

**Python:** Use `python3` exclusively throughout. Minimum supported: Python 3.11. Add to pre-flight: `python3 --version`.

---

## Pre-Flight — Run Before Any Code Changes

```bash
# 0. Confirm Python version (minimum 3.11)
python3 --version

# 1. Confirm target files do NOT already exist
ls backend/agent/warpsense_agent.py 2>&1 || echo "NOT EXISTS — correct"
ls backend/knowledge/build_welding_kb.py 2>&1 || echo "NOT EXISTS — correct"
ls backend/run_warpsense_agent.py 2>&1 || echo "NOT EXISTS — correct"

# 2. Confirm weld_classifier.py exists
ls backend/features/weld_classifier.py

# 3. Confirm top_drivers NOT yet on WeldPrediction
grep -c "top_drivers" backend/features/weld_classifier.py

# 4. Confirm deps installed
python3 -c "import chromadb; from groq import Groq; print('deps OK')"

# 5. GROQ_API_KEY: Add to repo root .env for run_warpsense_agent.py. Placeholder in .env.example.

# 6. Baseline line count
wc -l backend/features/weld_classifier.py
```

**Baseline Snapshot (agent fills during pre-flight):**
```
weld_classifier.py line count:      ____
top_drivers already in file:        YES / NO   ← must be NO
deps installed:                     YES / NO   ← must be YES
backend/agent/ already exists:      YES / NO
backend/knowledge/ already exists:  YES / NO
```

**All must pass before Step 1:**
- [ ] `grep -c "top_drivers" backend/features/weld_classifier.py` = `0`
- [ ] `python3 -c "import chromadb; from groq import Groq; print('OK')"` prints `OK`
- [ ] All three target files return `NOT EXISTS`

If deps fail → `pip install chromadb groq` then re-check.
If any target file already exists → STOP. Do not overwrite.

---

## Steps Analysis

```
Step 2.1 (Add top_drivers to WeldPrediction)   — Critical — full review — Idempotent: Yes
Step 2.2 (Create agent/ package)               — Non-critical — verification only — Idempotent: Yes
Step 2.3 (Write warpsense_agent.py)            — Critical — full review — Idempotent: Yes
Step 2.4 (Create knowledge/ + write KB file)   — Non-critical — verification only — Idempotent: Yes
Step 2.4b (Build KB, verify ChromaDB count)     — High — catches KB write failure — Idempotent: Yes
Step 2.5 (Write run_warpsense_agent.py)        — Non-critical — verification only — Idempotent: Yes
Step 2.6 (Full import smoke test)              — Non-critical — verification only — Idempotent: Yes
Step 2.6b (Verify assess path 1–3)            — High — catches agent pipeline failure — Idempotent: Yes
```

---

## Tasks

### Phase 1 — Patch Existing Classifier

**Goal:** `WeldPrediction` has a `top_drivers` field populated by `predict()`.

---

- [ ] 🟥 **Step 2.1: Add `top_drivers` to `WeldPrediction` and `predict()`** — *Critical: agent reads `prediction.top_drivers` at two callsites*

  **Idempotent:** Yes — Pre-Read Gate confirms `top_drivers` absent before any edit.

  **Context:** `WeldPrediction` in `backend/features/weld_classifier.py` currently has 4 fields. The agent's `_step1_defect_intake` and `_step4_llm_generate` both iterate `prediction.top_drivers`. Missing field = `AttributeError` at runtime, not import time.

  **Pre-Read Gate — MANDATORY, run before any edit:**
  ```bash
  # 1. Read the full WeldPrediction dataclass
  grep -n -A 20 "class WeldPrediction" backend/features/weld_classifier.py

  # 2. Read the full predict() return block
  grep -n -A 10 "return WeldPrediction" backend/features/weld_classifier.py

  # 3. Confirm FEATURE_COLS exists and note its scope (module-level or class attribute)
  grep -n "FEATURE_COLS" backend/features/weld_classifier.py

  # 4. Confirm feature_importances_ is used; note whether the model attribute is self.model or self._model — use whichever you see in Edit B
  grep -n "feature_importances_" backend/features/weld_classifier.py

  # 5. Count all WeldPrediction instantiation sites (must be exactly 1)
  grep -c "WeldPrediction(" backend/features/weld_classifier.py
  ```

  Show the full output of all 5 commands. Do not edit anything yet.

  **STOP conditions:**
  - `grep -c "WeldPrediction(" ...` returns > 1 → multiple instantiation sites; adding a field without `default_factory` breaks callers. Use `field(default_factory=list)` default (see Edit A below). Confirm default is used before proceeding.
  - `return WeldPrediction(...)` uses positional args (no `=` signs) → STOP. Report to human. Do not guess at position.
  - `FEATURE_COLS` returns 0 matches → STOP. Report to human. Cannot compute top_drivers without it.

  **Edit A — Add field to `WeldPrediction` dataclass:**

  Find the last field line inside `WeldPrediction` (from pre-read output). It will be `all_probabilities: Dict[str, float]` or similar. Insert this line **immediately after it**:
  ```python
      top_drivers: list = field(default_factory=list)  # List[Tuple[str, float]] — (feature_name, importance), top 3
  ```

  The current import is `from dataclasses import dataclass`. Replace it with `from dataclasses import dataclass, field`.

  **Edit B — Compute and populate `top_drivers` in `predict()`:**

  Using the output of Pre-Read Gate command 2, identify the line number of `return WeldPrediction(`. Insert these **three lines** immediately above it:
  ```python
      importances = zip(FEATURE_COLS, self._model.feature_importances_)
      ranked = sorted(importances, key=lambda x: x[1], reverse=True)
      top_drivers = [(name, float(imp)) for name, imp in ranked[:3]]
  ```

  Then add `top_drivers=top_drivers,` as the last argument inside the existing `return WeldPrediction(...)` call.

  > ⚠️ Use the **exact variable names** you observed in the pre-read output for `session_id=`, `quality_class=`, `confidence=`, `all_probabilities=`. Do not use the names from this plan if they differ from what the file actually contains.
  > ⚠️ If the Pre-Read Gate showed the model attribute as `self.model` (not `self._model`), use that instead. The file uses `self._model`; confirm and use whichever you see.

  **Why `field(default_factory=list):`** Backward-compatible. Any existing caller of `WeldPrediction(session_id=..., quality_class=..., confidence=..., all_probabilities=...)` without `top_drivers` will get an empty list instead of a TypeError.

  **Git Checkpoint:**
  ```bash
  git add backend/features/weld_classifier.py
  git commit -m "step 2.1: add top_drivers to WeldPrediction, populate in predict()"
  ```

  **Subtasks:**
  - [ ] 🟥 Pre-Read Gate: all 5 greps run and output shown
  - [ ] 🟥 No STOP conditions triggered
  - [ ] 🟥 `field` import confirmed or added
  - [ ] 🟥 Edit A: `top_drivers` field added to dataclass
  - [ ] 🟥 Edit B: computation + kwarg added to `predict()`
  - [ ] 🟥 Verification test passes

  **✓ Verification Test:**

  **Type:** Unit

  **Action:**
  ```bash
  cd backend
  python3 -c "
  from features.session_feature_extractor import generate_feature_dataset
  from features.weld_classifier import WeldClassifier, WeldPrediction
  sessions = generate_feature_dataset()
  clf = WeldClassifier()
  clf.train(sessions)
  pred = clf.predict(sessions[0])
  assert hasattr(pred, 'top_drivers'), 'top_drivers missing from WeldPrediction'
  assert isinstance(pred.top_drivers, list), f'expected list, got {type(pred.top_drivers)}'
  assert len(pred.top_drivers) == 3, f'expected 3, got {len(pred.top_drivers)}'
  assert isinstance(pred.top_drivers[0], tuple), f'expected tuple, got {type(pred.top_drivers[0])}'
  assert isinstance(pred.top_drivers[0][0], str), 'first element must be str'
  assert isinstance(pred.top_drivers[0][1], float), 'second element must be float'
  print(f'top_drivers OK: {pred.top_drivers}')
  "
  ```

  **Pass:** Prints `top_drivers OK: [('heat_diss_max_spike', 0.xxx), ...]`

  **Fail:**
  - `AttributeError: top_drivers` → Edit A not saved → delete `__pycache__` and retry.
  - `AssertionError: expected 3` → ranked slice missing in Edit B → check computation lines.
  - `AttributeError: feature_importances_` → `train()` not called before `predict()` in test → confirm `clf.train(sessions)` runs first.
  - `AttributeError: FEATURE_COLS` → wrong scope reference → check if it's `self.FEATURE_COLS`.

---

### Phase 2 — Write New Files

**Goal:** Three new files exist in the repo, written entirely from content in this plan.

---

- [ ] 🟥 **Step 2.2: Create `backend/agent/` package** — *Non-critical*

  **Idempotent:** Yes.

  ```bash
  mkdir -p backend/agent
  touch backend/agent/__init__.py
  ```

  **✓ Verification Test:**

  **Type:** Unit

  **Action:**
  ```bash
  python3 -c "import sys; sys.path.insert(0,'backend'); import agent; print('agent package OK')"
  ```

  **Pass:** `agent package OK` printed.

  **Git Checkpoint:**
  ```bash
  git add backend/agent/__init__.py
  git commit -m "step 2.2: create backend/agent package"
  ```

---

- [ ] 🟥 **Step 2.3: Write `backend/agent/warpsense_agent.py`** — *Critical: Groq response shape differs from Anthropic — wrong field = silent runtime crash*

  **Idempotent:** Yes — pre-flight confirmed file does not exist.

  **Context:** File is written in final Groq form directly. Key differences from the Anthropic version: `from groq import Groq`, model is `llama-3.3-70b-versatile`, client is `self.groq = Groq()`, API call is `self.groq.chat.completions.create(...)` with `temperature=0.1`, response parsed as `response.choices[0].message.content` (not `response.content[0].text`).

  Run this Python script exactly as written:

  ```python
  python3 - << 'PYEOF'
  content = r'''"""
  WarpSense — Quality Assessment Agent
  backend/agent/warpsense_agent.py

  6-step deterministic pipeline. No skipping, no reordering.
  Consumes WeldPrediction + SessionFeatures from Phase 1.
  Retrieves welding standards from ChromaDB.
  Calls Groq LLM to generate a structured quality report.
  Self-checks that every standards citation is grounded in retrieved content.
  Returns WeldQualityReport.

  Step ordering is a safety property, not a preference:
    1. Defect intake   — map top_drivers -> defect categories
    2. Threshold check — quantify which features exceed safe ranges
    3. Standards pull  — retrieve grounding from ChromaDB (AWS D1.1 / ISO 5817 / IACS)
    4. LLM generation  — structured prompt -> quality report fields
    5. Self-check      — verify every citation exists in retrieved content
    6. Return report   — WeldQualityReport dataclass

  Usage:
      from backend.agent.warpsense_agent import WarpSenseAgent
      agent = WarpSenseAgent()
      report = agent.assess(prediction, features)
  """

  import json
  import os
  import re
  from dataclasses import dataclass, field
  from datetime import datetime
  from typing import Optional

  from groq import Groq
  import chromadb
  from chromadb.utils import embedding_functions

  import sys
  from pathlib import Path

  _HERE = Path(__file__).resolve().parent
  _KB_PATH = _HERE.parent / "knowledge" / "chroma_db"

  THRESHOLDS = {
      "heat_diss_max_spike": {
          "good_max": 10.0,
          "marginal_max": 40.0,
          "unit": "C/s",
          "defect_map": ["LOF", "POROSITY"],
          "direction": "high_is_bad",
      },
      "angle_deviation_mean": {
          "good_max": 8.0,
          "marginal_max": 15.0,
          "unit": "deg",
          "defect_map": ["LOF", "UNDERCUT"],
          "direction": "high_is_bad",
      },
      "heat_input_min_rolling": {
          "good_min": 4000.0,
          "marginal_min": 3500.0,
          "unit": "J",
          "defect_map": ["LOF", "LOP"],
          "direction": "low_is_bad",
      },
      "heat_input_drop_severity": {
          "good_max": 10.0,
          "marginal_max": 15.0,
          "unit": "",
          "defect_map": ["LOF"],
          "direction": "high_is_bad",
      },
      "heat_input_cv": {
          "good_max": 0.10,
          "marginal_max": 0.20,
          "unit": "",
          "defect_map": ["LOF", "LOP"],
          "direction": "high_is_bad",
      },
      "voltage_cv": {
          "good_max": 0.08,
          "marginal_max": 0.15,
          "unit": "",
          "defect_map": ["POROSITY"],
          "direction": "high_is_bad",
      },
      "amps_cv": {
          "good_max": 0.08,
          "marginal_max": 0.12,
          "unit": "",
          "defect_map": ["LOF", "LOP"],
          "direction": "high_is_bad",
      },
      "arc_on_ratio": {
          "good_min": 0.90,
          "marginal_min": 0.75,
          "unit": "",
          "defect_map": ["LOF"],
          "direction": "low_is_bad",
      },
      "angle_max_drift_1s": {
          "good_max": 10.0,
          "marginal_max": 15.0,
          "unit": "deg",
          "defect_map": ["LOF"],
          "direction": "high_is_bad",
      },
      "heat_input_mean": {
          "good_min": 4500.0,
          "marginal_min": 3800.0,
          "unit": "J",
          "defect_map": ["LOF", "LOP"],
          "direction": "low_is_bad",
      },
  }

  DEFECT_FULL_NAME = {
      "LOF": "LACK OF FUSION (ISO 6520-1: 401)",
      "LOP": "INCOMPLETE ROOT PENETRATION (ISO 6520-1: 4021)",
      "POROSITY": "POROSITY (ISO 6520-1: 2017)",
      "UNDERCUT": "UNDERCUT (ISO 6520-1: 5011)",
      "THERMAL_INSTABILITY": "THERMAL INSTABILITY",
  }

  LOF_LOP_PRIMARY_FEATURES = {
      "heat_diss_max_spike",
      "angle_deviation_mean",
      "heat_input_min_rolling",
      "heat_input_drop_severity",
  }

  LLM_MODEL = "llama-3.3-70b-versatile"


  @dataclass
  class ThresholdViolation:
      feature: str
      value: float
      threshold: float
      threshold_type: str
      severity: str
      unit: str
      defect_categories: list

      def as_display_line(self) -> str:
          direction = ">" if self.threshold_type == "max" else "<"
          unit = f" {self.unit}" if self.unit else ""
          return (
              f"  * {self.feature:<28} {self.value:.3f}{unit}  "
              f"(threshold: {direction} {self.threshold:.3f}{unit})  "
              f"[{self.severity}] -> {', '.join(self.defect_categories)}"
          )


  @dataclass
  class StandardsChunk:
      chunk_id: str
      text: str
      source: str
      section: str
      score: float


  @dataclass
  class WeldQualityReport:
      session_id: str
      report_timestamp: str
      quality_class: str
      confidence: float
      iso_5817_level: str
      primary_defect_categories: list
      threshold_violations: list
      root_cause: str
      corrective_actions: list
      standards_references: list
      retrieved_chunks_used: list
      disposition: str
      disposition_rationale: str
      self_check_passed: bool
      self_check_notes: str
      llm_raw_response: str

      def render(self) -> str:
          return _render_report(self)


  def _render_report(r) -> str:
      disposition_icon = {"PASS": "[PASS]", "CONDITIONAL": "[CONDITIONAL]", "REWORK_REQUIRED": "[REWORK]"}.get(r.disposition, "[?]")
      quality_icon = {"GOOD": "[GOOD]", "MARGINAL": "[MARGINAL]", "DEFECTIVE": "[DEFECTIVE]"}.get(r.quality_class, "[?]")
      lines = [
          "=" * 58,
          f"WARPSENSE QUALITY REPORT -- WELD SESSION {r.session_id}",
          "=" * 58,
          f"Quality Class:      {quality_icon} {r.quality_class}",
          f"ISO 5817 Level:     {r.iso_5817_level}",
          f"Confidence:         {r.confidence:.2f}",
          f"Report Time:        {r.report_timestamp}",
          "",
      ]
      if r.threshold_violations:
          lines.append("Threshold Violations:")
          for v in r.threshold_violations:
              lines.append(v.as_display_line())
          lines.append("")
      if r.primary_defect_categories:
          lines.append("Primary Defect Risk Categories:")
          for cat in r.primary_defect_categories:
              lines.append(f"  * {DEFECT_FULL_NAME.get(cat, cat)}")
          lines.append("")
      lines.append("Root Cause:")
      for line in r.root_cause.strip().splitlines():
          lines.append(f"  {line.strip()}")
      lines.append("")
      if r.corrective_actions:
          lines.append("Corrective Parameters:")
          for action in r.corrective_actions:
              lines.append(f"  -> {action}")
          lines.append("")
      if r.standards_references:
          lines.append("Standards References:")
          for ref in r.standards_references:
              lines.append(f"  * {ref}")
          lines.append("")
      check = "PASSED" if r.self_check_passed else "FLAGGED"
      lines.append(f"Self-Check:         {check}")
      if not r.self_check_passed:
          lines.append(f"  Note: {r.self_check_notes}")
      lines.append("")
      lines.append(f"Disposition:        {disposition_icon} {r.disposition.replace('_', ' ')}")
      lines.append(f"  {r.disposition_rationale}")
      lines.append("=" * 58)
      return "\n".join(lines)


  class WarpSenseAgent:
      """6-step deterministic welding quality assessment agent."""

      def __init__(
          self,
          chroma_path=None,
          collection_name="welding_standards",
          llm_model=LLM_MODEL,
          n_standards_chunks=6,
          verbose=True,
      ):
          self.llm_model = llm_model
          self.n_chunks = n_standards_chunks
          self.verbose = verbose

          # Groq client -- reads GROQ_API_KEY from env
          self.groq = Groq()

          kb_path = chroma_path or str(_KB_PATH)
          self._log(f"[Agent] Loading ChromaDB from: {kb_path}")
          client = chromadb.PersistentClient(path=kb_path)
          ef = embedding_functions.DefaultEmbeddingFunction()
          self.collection = client.get_collection(
              name=collection_name,
              embedding_function=ef,
          )
          self._log(f"[Agent] KB loaded: {self.collection.count()} chunks")

      def assess(self, prediction, features):
          session_id = prediction.session_id
          self._log(f"\n[Agent] -- Starting assessment: {session_id} --")
          self._log("[Agent] Step 1: Defect intake")
          defect_categories = self._step1_defect_intake(prediction, features)
          self._log("[Agent] Step 2: Threshold check")
          violations = self._step2_threshold_check(features)
          self._log("[Agent] Step 3: Standards retrieval")
          chunks = self._step3_retrieve_standards(prediction, features, defect_categories, violations)
          self._log("[Agent] Step 4: LLM generation")
          llm_output = self._step4_llm_generate(prediction, features, defect_categories, violations, chunks)
          self._log("[Agent] Step 5: Self-check")
          self_check_passed, self_check_notes = self._step5_self_check(llm_output, chunks)
          self._log("[Agent] Step 6: Assembling report")
          report = self._step6_assemble_report(
              prediction, features, defect_categories, violations,
              chunks, llm_output, self_check_passed, self_check_notes
          )
          self._log(f"[Agent] -- Assessment complete: {report.disposition} --\n")
          return report

      def _step1_defect_intake(self, prediction, features):
          defects = set()
          feat_dict = features.to_vector()
          driver_feature_to_defect = {
              "heat_diss_max_spike":      ["LOF", "POROSITY"],
              "angle_deviation_mean":     ["LOF", "UNDERCUT"],
              "heat_input_min_rolling":   ["LOF", "LOP"],
              "heat_input_drop_severity": ["LOF"],
              "heat_input_cv":            ["LOF", "LOP"],
              "amps_cv":                  ["LOF", "LOP"],
              "voltage_cv":               ["POROSITY"],
              "arc_on_ratio":             ["LOF"],
              "heat_input_mean":          ["LOF", "LOP"],
              "angle_max_drift_1s":       ["LOF"],
              "heat_diss_mean":           ["LOF"],
          }
          for feat_name, _ in prediction.top_drivers:
              for cat in driver_feature_to_defect.get(feat_name, []):
                  defects.add(cat)
          for feat_name in LOF_LOP_PRIMARY_FEATURES:
              val = feat_dict.get(feat_name)
              if val is None:
                  continue
              t = THRESHOLDS.get(feat_name, {})
              if t.get("direction") == "high_is_bad":
                  if val > t.get("marginal_max", float("inf")):
                      for cat in t.get("defect_map", []):
                          defects.add(cat)
              elif t.get("direction") == "low_is_bad":
                  if val < t.get("marginal_min", 0.0):
                      for cat in t.get("defect_map", []):
                          defects.add(cat)
          hd = feat_dict.get("heat_diss_max_spike", 0)
          if hd > THRESHOLDS["heat_diss_max_spike"]["good_max"]:
              defects.add("THERMAL_INSTABILITY")
          ordered = []
          for cat in ["LOF", "LOP", "THERMAL_INSTABILITY", "UNDERCUT", "POROSITY"]:
              if cat in defects:
                  ordered.append(cat)
          self._log(f"  -> Defect categories: {ordered}")
          return ordered

      def _step2_threshold_check(self, features):
          feat_dict = features.to_vector()
          violations = []
          for feat_name, t in THRESHOLDS.items():
              val = feat_dict.get(feat_name)
              if val is None:
                  continue
              severity = None
              threshold_val = None
              threshold_type = None
              if t["direction"] == "high_is_bad":
                  if val > t["marginal_max"]:
                      severity, threshold_val, threshold_type = "RISK", t["marginal_max"], "max"
                  elif val > t["good_max"]:
                      severity, threshold_val, threshold_type = "MARGINAL", t["good_max"], "max"
              elif t["direction"] == "low_is_bad":
                  if val < t["marginal_min"]:
                      severity, threshold_val, threshold_type = "RISK", t["marginal_min"], "min"
                  elif val < t["good_min"]:
                      severity, threshold_val, threshold_type = "MARGINAL", t["good_min"], "min"
              if severity:
                  violations.append(ThresholdViolation(
                      feature=feat_name, value=val, threshold=threshold_val,
                      threshold_type=threshold_type, severity=severity,
                      unit=t.get("unit", ""), defect_categories=t.get("defect_map", []),
                  ))
          violations.sort(key=lambda v: (
              0 if v.severity == "RISK" else 1,
              0 if v.feature in LOF_LOP_PRIMARY_FEATURES else 1,
          ))
          self._log(f"  -> {len(violations)} violations: "
                    f"{sum(1 for v in violations if v.severity=='RISK')} RISK, "
                    f"{sum(1 for v in violations if v.severity=='MARGINAL')} MARGINAL")
          return violations

      def _step3_retrieve_standards(self, prediction, features, defect_categories, violations):
          queries = []
          cat_queries = {
              "LOF":                "lack of fusion incomplete fusion acceptance criteria corrective action",
              "LOP":                "incomplete root penetration corrective action acceptance criteria",
              "THERMAL_INSTABILITY":"heat dissipation spike thermal instability corrective travel speed",
              "UNDERCUT":           "undercut acceptance criteria corrective action torch angle current",
              "POROSITY":           "porosity root cause corrective action shielding gas heat dissipation",
          }
          for cat in defect_categories[:3]:
              q = cat_queries.get(cat)
              if q:
                  queries.append(q)
          for v in violations[:2]:
              queries.append(f"{v.feature.replace('_', ' ')} {v.value:.1f} corrective action threshold")
          queries.append("marine shipyard LOF LOP sensor detection invisible inspection")
          seen = set()
          unique_queries = [q for q in queries if not (q in seen or seen.add(q))]
          seen_ids = set()
          all_chunks = []
          for q in unique_queries[:5]:
              try:
                  results = self.collection.query(
                      query_texts=[q], n_results=3,
                      include=["documents", "metadatas", "distances"],
                  )
                  for i, doc in enumerate(results["documents"][0]):
                      chunk_id = results["ids"][0][i]
                      if chunk_id not in seen_ids:
                          seen_ids.add(chunk_id)
                          meta = results["metadatas"][0][i]
                          all_chunks.append(StandardsChunk(
                              chunk_id=chunk_id, text=doc,
                              source=meta.get("source", "unknown"),
                              section=meta.get("section", ""),
                              score=round(1 - results["distances"][0][i], 4),
                          ))
              except Exception as e:
                  self._log(f"  [WARN] KB query failed: {e}")
          all_chunks.sort(key=lambda c: c.score, reverse=True)
          top_chunks = all_chunks[:self.n_chunks]
          if top_chunks:
              self._log(f"  -> Retrieved {len(top_chunks)} chunks (top score: {top_chunks[0].score:.4f} from {top_chunks[0].source})")
          return top_chunks

      def _step4_llm_generate(self, prediction, features, defect_categories, violations, chunks):
          feat_dict = features.to_vector()
          violations_text = "\n".join(v.as_display_line() for v in violations) or "None"
          defects_text = ", ".join(defect_categories) or "None identified"
          top_drivers_text = "\n".join(
              f"  {name}: importance={imp:.3f}" for name, imp in prediction.top_drivers
          )
          chunks_text = "\n\n".join(
              f"[CHUNK {i+1}] Source: {c.source} | {c.section}\n{c.text}"
              for i, c in enumerate(chunks)
          )
          feature_summary = "\n".join(f"  {k}: {v:.4f}" for k, v in feat_dict.items())

          prompt = f"""You are WarpSenseAgent, an industrial welding quality assessment AI.

CLASSIFIER OUTPUT
Session ID: {prediction.session_id}
Quality Class: {prediction.quality_class}
Confidence: {prediction.confidence:.2f}
Top Feature Drivers:
{top_drivers_text}

SESSION FEATURES
{feature_summary}

THRESHOLD VIOLATIONS
{violations_text}

DEFECT RISK CATEGORIES
{defects_text}

RETRIEVED WELDING STANDARDS
{chunks_text}

INSTRUCTIONS
Produce a structured JSON report with EXACTLY these keys:
{{
  "iso_5817_level": "B" | "C" | "D" | "BELOW_D",
  "disposition": "PASS" | "CONDITIONAL" | "REWORK_REQUIRED",
  "disposition_rationale": "One sentence.",
  "root_cause": "2-4 sentences linking sensor features to defect mechanism.",
  "corrective_actions": ["Action 1", "Action 2", "Action 3"],
  "standards_references": ["Standard 1: source + section + relevance"]
}}
RULES:
1. iso_5817_level: GOOD->C or B, MARGINAL->D, DEFECTIVE->BELOW_D.
2. disposition must be REWORK_REQUIRED if quality_class is DEFECTIVE or any LOF/LOP feature is RISK.
3. corrective_actions within WPS bounds: amperage +/-15%, voltage +/-10%, travel speed +/-30%, angle +/-10% of 45deg.
4. Every standards_reference must come ONLY from retrieved chunks above.
5. 3-5 corrective_actions.
6. Respond with ONLY the JSON object. No preamble, no markdown fences."""

          response = self.groq.chat.completions.create(
              model=self.llm_model,
              max_tokens=1500,
              messages=[{"role": "user", "content": prompt}],
              temperature=0.1,
          )

          raw = response.choices[0].message.content.strip()

          clean = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.MULTILINE)
          clean = re.sub(r"\s*```$", "", clean, flags=re.MULTILINE).strip()

          try:
              parsed = json.loads(clean)
          except json.JSONDecodeError as e:
              self._log(f"  [WARN] LLM JSON parse failed: {e}. Using fallback.")
              parsed = self._fallback_report(prediction, defect_categories, violations)
              parsed["_parse_error"] = str(e)

          parsed["_raw"] = raw
          return parsed

      def _fallback_report(self, prediction, defect_categories, violations):
          has_risk = any(v.severity == "RISK" for v in violations)
          lof_risk = any(v.feature in LOF_LOP_PRIMARY_FEATURES for v in violations if v.severity == "RISK")
          return {
              "iso_5817_level": "BELOW_D" if prediction.quality_class == "DEFECTIVE" else "D",
              "disposition": "REWORK_REQUIRED" if lof_risk else ("CONDITIONAL" if has_risk else "PASS"),
              "disposition_rationale": f"Classification: {prediction.quality_class} with {len(violations)} violations.",
              "root_cause": "LLM generation failed. Review threshold violations directly.",
              "corrective_actions": ["Review threshold violations above", "Consult welding engineer"],
              "standards_references": [],
          }

      def _step5_self_check(self, llm_output, chunks):
          cited_refs = llm_output.get("standards_references", [])
          if not cited_refs:
              return True, "No citations to verify."
          known_sources = set()
          for c in chunks:
              src = c.source.lower()
              known_sources.add(src)
              if "aws" in src:
                  known_sources.update(["aws d1.1", "aws"])
              if "iso 5817" in src:
                  known_sources.add("iso 5817")
              if "iacs" in src:
                  known_sources.update(["iacs", "iacs rec"])
              if "iso 6520" in src:
                  known_sources.add("iso 6520")
          hallucinated = []
          for ref in cited_refs:
              ref_lower = ref.lower()
              grounded = any(src in ref_lower for src in known_sources)
              if not grounded:
                  section_match = any(
                      any(token in c.text.lower() for token in ref_lower.split() if len(token) > 4)
                      for c in chunks
                  )
                  if not section_match:
                      hallucinated.append(ref)
          if hallucinated:
              notes = f"Ungrounded citations: {hallucinated}"
              self._log(f"  [SELF-CHECK] WARNING: {notes}")
              return False, notes
          self._log("  [SELF-CHECK] All citations grounded.")
          return True, "All citations verified."

      def _step6_assemble_report(self, prediction, features, defect_categories, violations, chunks, llm_output, self_check_passed, self_check_notes):
          disposition = llm_output.get("disposition", "CONDITIONAL")
          lof_lop_risk = any(
              v.severity == "RISK" and any(cat in ["LOF", "LOP"] for cat in v.defect_categories)
              for v in violations
          )
          if lof_lop_risk and disposition != "REWORK_REQUIRED":
              disposition = "REWORK_REQUIRED"
              llm_output["disposition_rationale"] = (
                  "[Override] LOF/LOP RISK threshold exceeded. "
                  + llm_output.get("disposition_rationale", "")
              )
          return WeldQualityReport(
              session_id=prediction.session_id,
              report_timestamp=datetime.utcnow().isoformat() + "Z",
              quality_class=prediction.quality_class,
              confidence=prediction.confidence,
              iso_5817_level=llm_output.get("iso_5817_level", "D"),
              primary_defect_categories=defect_categories,
              threshold_violations=violations,
              root_cause=llm_output.get("root_cause", ""),
              corrective_actions=llm_output.get("corrective_actions", []),
              standards_references=llm_output.get("standards_references", []),
              retrieved_chunks_used=[c.chunk_id for c in chunks],
              disposition=disposition,
              disposition_rationale=llm_output.get("disposition_rationale", ""),
              self_check_passed=self_check_passed,
              self_check_notes=self_check_notes,
              llm_raw_response=llm_output.get("_raw", ""),
          )

      def _log(self, msg):
          if self.verbose:
              print(msg)
  '''

  import os
  os.makedirs("backend/agent", exist_ok=True)
  with open("backend/agent/warpsense_agent.py", "w") as f:
      f.write(content)
  print("Written: backend/agent/warpsense_agent.py")
  PYEOF
  ```

  **What it does:** Creates the agent file with Groq as the LLM backend. `self.groq.chat.completions.create` with `temperature=0.1` and `response.choices[0].message.content` are the two Groq-specific lines. Safety override in `_step6_assemble_report` ensures LOF/LOP RISK always maps to REWORK_REQUIRED regardless of LLM output.

  **Git Checkpoint:**
  ```bash
  git add backend/agent/warpsense_agent.py
  git commit -m "step 2.3: write warpsense_agent.py with groq backend"
  ```

  **✓ Verification Test:**

  **Type:** Unit

  **Action:**
  ```bash
  # 1. Zero Anthropic traces
  grep -c "anthropic\|claude-sonnet\|ANTHROPIC" backend/agent/warpsense_agent.py

  # 2. All Groq lines present
  grep -c "from groq import Groq" backend/agent/warpsense_agent.py
  grep -c "llama-3.3-70b-versatile" backend/agent/warpsense_agent.py
  grep -c "self.groq = Groq()" backend/agent/warpsense_agent.py
  grep -c "self.groq.chat.completions.create" backend/agent/warpsense_agent.py
  grep -Fc "response.choices[0].message.content" backend/agent/warpsense_agent.py
  grep -c "temperature=0.1" backend/agent/warpsense_agent.py

  # 3. Import smoke test (no agent instantiation; Groq client created only in WarpSenseAgent.__init__)
  cd backend
  python3 -c "
  from agent.warpsense_agent import WarpSenseAgent, WeldQualityReport, THRESHOLDS
  print(f'THRESHOLDS count: {len(THRESHOLDS)}')
  print('Import: OK')
  "
  ```

  **Pass:** grep 1 returns `0`. All grep 2 checks return `1`. Import prints `THRESHOLDS count: 10` and `Import: OK`.

  **Fail:**
  - grep 1 > 0 → Anthropic trace present → write script did not execute cleanly → delete file and re-run script.
  - Any grep 2 = 0 → that line missing → check Python write script for that specific line.
  - `ImportError: cannot import name 'Groq'` → groq not installed → `pip install groq`.

---

- [ ] 🟥 **Step 2.4: Create `backend/knowledge/` and write `build_welding_kb.py`** — *Non-critical*

  **Idempotent:** Yes.

  ```bash
  mkdir -p backend/knowledge
  touch backend/knowledge/__init__.py
  ```

  Then write the KB file. Run this Python script exactly as written:

  ```python
  python3 - << 'PYEOF'
  content = '''"""
  WarpSense -- Welding Standards Knowledge Base
  backend/knowledge/build_welding_kb.py

  Loads 63 structured chunks into ChromaDB covering:
    - AWS D1.1:2025  (Structural Welding Code)
    - ISO 5817:2023  (Quality levels B / C / D)
    - IACS Rec. 47 Rev.10 (Shipbuilding & Repair Quality Standards)
    - Heat input physics and parameter relationships
    - Root cause maps per defect type (LOF/LOP focus)
    - Corrective action protocols with specific parameter targets
    - Torch angle and travel speed effects

  Usage:
      python build_welding_kb.py           # build and persist to ./chroma_db
      python build_welding_kb.py --test    # build + run smoke tests
  """

  import argparse
  from pathlib import Path

  import chromadb
  from chromadb.utils import embedding_functions

  CHROMA_PATH = Path(__file__).parent / "chroma_db"
  COLLECTION_NAME = "welding_standards"
  DEFAULT_EF = embedding_functions.DefaultEmbeddingFunction()

  CHUNKS = [
      {"id": "aws_d11_scope", "text": "AWS D1.1/D1.1M:2025 Structural Welding Code governs welding requirements for carbon and low-alloy constructional steels. All welds shall be visually inspected unless otherwise specified. Visual inspection may begin after welds cool to ambient temperature.", "metadata": {"source": "AWS D1.1:2025", "section": "Clause 8 General", "chunk_type": "overview"}},
      {"id": "aws_d11_table81_fusion", "text": "AWS D1.1 Table 8.1 Item 2: There shall be complete fusion between weld and base metal. Incomplete penetration in CJP groove welds is not acceptable and shall be repaired. For CJP groove welds in cyclically loaded structures, zero incomplete penetration is tolerated. Incomplete penetration is a rejection criterion for all CJP welds.", "metadata": {"source": "AWS D1.1:2025", "section": "Table 8.1 Item 2", "defect_type": "incomplete_fusion", "severity": "reject", "chunk_type": "acceptance_criteria"}},
      {"id": "aws_d11_table81_undercut_static", "text": "AWS D1.1 Table 8.1 Item 7 Undercut Statically Loaded: For material less than 1 in thick, undercut shall not exceed 1/32 in. For material 1 in or greater, undercut shall not exceed 1/16 in for any weld.", "metadata": {"source": "AWS D1.1:2025", "section": "Table 8.1 Item 7", "defect_type": "undercut", "severity": "conditional", "chunk_type": "acceptance_criteria"}},
      {"id": "aws_d11_table81_undercut_cyclic", "text": "AWS D1.1 Table 8.1 Item 7 Undercut Cyclically Loaded: For primary members in tension transverse to tensile stress, undercut shall not exceed 0.01 in deep. This is the most stringent undercut limit. For all other cyclically loaded members, undercut shall not exceed 1/32 in.", "metadata": {"source": "AWS D1.1:2025", "section": "Table 8.1 Item 7", "defect_type": "undercut", "severity": "conditional", "chunk_type": "acceptance_criteria"}},
      {"id": "aws_d11_table81_porosity_static", "text": "AWS D1.1 Table 8.1 Item 8 Piping Porosity Statically Loaded: The sum of diameters of visible piping porosity 1/32 in or greater shall not exceed 3/8 in in any linear inch of weld. For welds less than 12 in, sum shall not exceed weld length times 0.06.", "metadata": {"source": "AWS D1.1:2025", "section": "Table 8.1 Item 8", "defect_type": "porosity", "severity": "conditional", "chunk_type": "acceptance_criteria"}},
      {"id": "aws_d11_table81_porosity_cyclic", "text": "AWS D1.1 Table 8.1 Item 8 Piping Porosity Cyclically Loaded: For cyclically loaded nontubular CJP groove welds transverse to tensile stress, zero porosity is permitted.", "metadata": {"source": "AWS D1.1:2025", "section": "Table 8.1 Item 8", "defect_type": "porosity", "severity": "conditional", "chunk_type": "acceptance_criteria"}},
      {"id": "aws_d11_lof_zero_tolerance", "text": "AWS D1.1 Incomplete Fusion Zero Tolerance: Incomplete fusion is defined as a condition where weld metal fails to fuse completely with base metal or adjacent weld beads. Under AWS D1.1, incomplete fusion is NOT accepted at any length. It is a direct rejection criterion requiring repair. This applies to VT, MT, PT, RT, and UT inspection. There is no acceptable length threshold for incomplete fusion.", "metadata": {"source": "AWS D1.1:2025", "section": "Clauses 8.9-8.13", "defect_type": "incomplete_fusion", "severity": "reject", "chunk_type": "acceptance_criteria"}},
      {"id": "aws_d11_heat_input_formula", "text": "AWS D1.1 Clause 6.8.5 Heat Input Formula: Heat Input kJ/in = (Voltage x Amperage x 60) / (1000 x Travel Speed in IPM). For SI: Heat Input kJ/mm = (Voltage x Amperage x 60) / (1000 x Travel Speed in mm/min). Heat input is an essential variable for WPS qualification when CVN/toughness requirements apply.", "metadata": {"source": "AWS D1.1:2025", "section": "Clause 6.8.5", "chunk_type": "formula"}},
      {"id": "aws_d11_short_circuit_ban", "text": "AWS D1.1 Short Circuit Transfer Prohibition: GMAW short-circuit transfer is NOT permitted for prequalified welding procedures under AWS D1.1 for structural welding. Short circuit transfer is susceptible to lack of fusion because the low arc energy is insufficient to melt sidewalls consistently. Spray transfer and pulsed spray are preferred.", "metadata": {"source": "AWS D1.1:2025", "section": "Prequalified WPS", "defect_type": "incomplete_fusion", "chunk_type": "procedure"}},
      {"id": "aws_d11_disposition_rework", "text": "AWS D1.1 Weld Repair and Disposition: Welds failing acceptance criteria shall be repaired or removed and replaced. Repair methods include gouging and re-welding for cracks and incomplete fusion, grinding for minor surface defects, additional passes for undersized welds. Repairs require a documented repair WPS and must be re-inspected using the same methods as the original weld.", "metadata": {"source": "AWS D1.1:2025", "section": "Clause 8.8", "chunk_type": "disposition"}},
      {"id": "aws_d11_wps_essential_variables", "text": "AWS D1.1 WPS Essential Variables: A Welding Procedure Specification must document current range, voltage range, travel speed range, preheat temperature, interpass temperature, electrode diameter, shielding gas composition and flow rate, and welding position. Changes beyond qualified ranges require re-qualification.", "metadata": {"source": "AWS D1.1:2025", "section": "Clause 5 WPS", "chunk_type": "procedure"}},
      {"id": "iso5817_overview", "text": "ISO 5817:2023 Quality Levels for Imperfections in Fusion-Welded Joints: Specifies quality levels for imperfections in fusion-welded joints in steel, nickel, titanium and their alloys. Three quality levels: B (highest strictest), C (intermediate), D (moderate lowest). Level B corresponds to highest structural integrity. ISO 5817 answers what is acceptable.", "metadata": {"source": "ISO 5817:2023", "section": "Scope", "chunk_type": "overview"}},
      {"id": "iso5817_level_selection", "text": "ISO 5817:2023 Quality Level Selection: Level B for fatigue-critical, safety-critical joints, marine primary structure. Level C for general structural welds, statically loaded with moderate consequence. Level D for non-critical brackets and fixtures. For shipyard structural hull welds, Level C or B is typical.", "metadata": {"source": "ISO 5817:2023", "section": "Section 4", "chunk_type": "guidance"}},
      {"id": "iso5817_lof_all_levels", "text": "ISO 5817:2023 Table 1 Lack of Fusion ref 401: Quality Level B: Not permitted. Quality Level C: Not permitted. Quality Level D: Not permitted. Lack of fusion is NEVER acceptable at any quality level under ISO 5817. This includes lack of side-wall fusion 4011, lack of inter-run fusion 4012, lack of root fusion 4013. LOF creates a planar discontinuity with catastrophic crack propagation risk.", "metadata": {"source": "ISO 5817:2023", "section": "Table 1 No.1.5", "defect_type": "lack_of_fusion", "severity": "reject", "chunk_type": "acceptance_criteria"}},
      {"id": "iso5817_incomplete_root_penetration", "text": "ISO 5817:2023 Table 1 Incomplete Root Penetration ref 4021: Quality Level B: Not permitted. Quality Level C: Not permitted. Quality Level D: Short imperfections only h <= 0.2t but maximum 2 mm where t is plate thickness. Levels C and B: Not permitted at any length.", "metadata": {"source": "ISO 5817:2023", "section": "Table 1 No.1.6", "defect_type": "incomplete_penetration", "severity": "conditional", "chunk_type": "acceptance_criteria"}},
      {"id": "iso5817_lof_fillet_welds", "text": "ISO 5817:2023 Table 1 No.2.12 Lack of Fusion in Fillet Welds ref 401: Quality Level B: Not permitted. Quality Level C: Not permitted. Quality Level D: Short imperfections only h <= 0.4a but max 4 mm. LOF is zero-tolerance at B and C regardless of size because LOF is a planar defect with catastrophic crack propagation risk.", "metadata": {"source": "ISO 5817:2023", "section": "Table 1 No.2.12", "defect_type": "lack_of_fusion", "severity": "reject", "chunk_type": "acceptance_criteria"}},
      {"id": "iso5817_undercut", "text": "ISO 5817:2023 Table 1 Undercut ref 5011: Level D t > 3 mm: h <= 0.2t max 1 mm. Level C t > 3 mm: h <= 0.1t max 0.5 mm. Level B t > 3 mm: h <= 0.05t max 0.5 mm. Undercut weakens section thickness at weld toe creating stress concentration for fatigue crack initiation.", "metadata": {"source": "ISO 5817:2023", "section": "Table 1 No.1.7", "defect_type": "undercut", "severity": "conditional", "chunk_type": "acceptance_criteria"}},
      {"id": "iso5817_porosity_surface", "text": "ISO 5817:2023 Table 1 Surface Pore ref 2017: Level D: d <= 0.2s but max 2 mm. Level C: d <= 0.1s but max 1 mm. Level B: Not permitted. Porosity produces rounded volumetric defects rather than planar defects and is relatively less dangerous than LOF. Cluster porosity is not permitted at any level.", "metadata": {"source": "ISO 5817:2023", "section": "Table 1 No.1.3", "defect_type": "porosity", "severity": "conditional", "chunk_type": "acceptance_criteria"}},
      {"id": "iso5817_cracks", "text": "ISO 5817:2023 Table 1 Cracks ref 100: Quality Level B Not permitted. Quality Level C Not permitted. Quality Level D Not permitted. All crack types are rejected at all quality levels. Types include longitudinal, transverse, crater, interface, and HAZ cracks.", "metadata": {"source": "ISO 5817:2023", "section": "Table 1 No.1.1", "defect_type": "crack", "severity": "reject", "chunk_type": "acceptance_criteria"}},
      {"id": "iso5817_systematic_imperfections", "text": "ISO 5817:2023 Section 5 Systematic Imperfections: Systematic imperfections are only permitted in quality level D. A systematic imperfection recurs repeatedly at regular intervals, suggesting a procedural or technique problem. A consistently high angle_deviation_mean or repeatedly low heat_input_min_rolling across sessions is a pattern of systematic imperfection requiring training correction.", "metadata": {"source": "ISO 5817:2023", "section": "Section 5", "chunk_type": "guidance"}},
      {"id": "iso5817_multiple_imperfections", "text": "ISO 5817:2023 Section 5 Multiple Imperfections: A welded joint should be assessed separately for each individual type of imperfection. When multiple imperfections are present simultaneously such as porosity plus undercut plus LOF, each must independently pass its quality level limit. The presence of porosity may mask underlying LOF.", "metadata": {"source": "ISO 5817:2023", "section": "Section 5", "chunk_type": "guidance"}},
      {"id": "iso5817_fatigue_annex_b", "text": "ISO 5817:2023 Annex B Fatigue Load Criteria: Additional requirements for welds subject to fatigue loading. At B125 highest fatigue demand: continuous undercut not permitted, weld toe radius r >= 4 mm for t >= 3 mm. Marine hull welding in cyclically loaded areas should reference Annex B criteria for primary structural members.", "metadata": {"source": "ISO 5817:2023", "section": "Annex B", "chunk_type": "fatigue"}},
      {"id": "iso6520_classification", "text": "ISO 6520-1:2007 Weld Imperfection Classification: Group 1 Cracks 100-series. Group 2 Cavities porosity piping 200-series. Group 3 Solid inclusions 300-series. Group 4 Incomplete fusion and penetration 400-series where 401 is LOF and 4021 is IRP. Group 5 Shape and dimension 500-series where 5011 is continuous undercut. Group 6 Miscellaneous 600-series.", "metadata": {"source": "ISO 6520-1:2007", "section": "All", "chunk_type": "overview"}},
      {"id": "iacs47_scope", "text": "IACS Recommendation 47 Rev.10 2021 Shipbuilding and Repair Quality Standard: Provides guidance on quality of hull structure during new construction and repair. Applies to primary and secondary structure. ANSI/AWS D1.1 is explicitly listed as a recognized international standard. Subcontractors must keep records of welder qualification certificates.", "metadata": {"source": "IACS Rec.47 Rev.10 2021", "section": "Scope", "chunk_type": "overview"}},
      {"id": "iacs47_high_heat_input_threshold", "text": "IACS UR W28 Rev.3 High Heat Input Thresholds: IACS defines high heat input welding as processes exceeding 50 kJ/cm for normal and higher strength hull structural steels. Above this threshold additional approval and testing is required. Typical target range for shipyard MIG welding on mild/HT steel is 1.0 to 3.0 kJ/mm. Heat inputs below 0.5 kJ/mm risk incomplete fusion.", "metadata": {"source": "IACS UR W28 Rev.3", "section": "High Heat Input", "chunk_type": "threshold", "defect_type": "lack_of_fusion"}},
      {"id": "iacs47_weld_ndt_coverage", "text": "IACS Rec 47 NDT Coverage: Current practice in shipyards involves spot NDT at typically 10% coverage. This means 90% of welds receive only visual inspection. LOF and LOP are subsurface planar defects invisible to visual inspection and often invisible to dye penetrant and magnetic particle unless they break the surface. Only UT reliably detects all orientations of LOF/LOP. AI-based sensor monitoring offers path to 100% first-pass LOF/LOP risk screening.", "metadata": {"source": "IACS Rec.47 / IACS UR W33", "section": "NDT", "chunk_type": "inspection", "defect_type": "lack_of_fusion"}},
      {"id": "iacs47_repair_disposition", "text": "IACS Rec 47 Repair Disposition: Defects are to be remedied by grinding and/or welding. Weld repairs require prior cleaning of groove, approved welding procedure, same or higher grade consumables, steel temperature not lower than 5 C, re-inspection by NDT after repair. For structural defects including LOF and LOP full gouge and re-weld is required.", "metadata": {"source": "IACS Rec.47 Rev.10 2021", "section": "Section 6", "chunk_type": "disposition"}},
      {"id": "iacs47_marine_environment_context", "text": "IACS Rec 47 Marine Welding Context: Shipyard welding occurs in demanding conditions including high humidity in coastal tropical locations, thick steel plates 10-50 mm, variable ambient temperatures, wind exposure affecting shielding gas. In Singapore and Southeast Asian shipyards high ambient humidity 80-90% RH increases hydrogen pickup risk. Pre-weld drying of consumables is mandatory.", "metadata": {"source": "IACS Rec.47 Rev.10 2021", "section": "Context", "chunk_type": "context"}},
      {"id": "iacs47_preheat", "text": "IACS Rec 47 Preheating: Minimum preheat of 50C is to be applied when ambient temperature is below 0C. For higher strength steels with Ceq > 0.43, preheat 100-175C depending on combined plate thickness. Moisture must be removed from weld area by heating torch before welding because moisture causes hydrogen-induced cracking.", "metadata": {"source": "IACS Rec.47 Rev.10 2021", "section": "Section 5", "chunk_type": "procedure"}},
      {"id": "heat_input_formula_physics", "text": "Heat Input Calculation Physics: Heat Input J/mm = (Voltage V x Current A x 60) / Travel Speed mm/min. Divide by 1000 for kJ/mm. Heat input governs penetration depth, HAZ width, cooling rate, microstructure, and toughness. Insufficient heat input causes incomplete fusion and cold lap. Excess heat input causes distortion, HAZ softening, and porosity from contaminant boiling.", "metadata": {"source": "AWS D1.1 / EN ISO 1011-1", "section": "Heat Input", "chunk_type": "formula"}},
      {"id": "heat_input_voltage_effect", "text": "Voltage Effect on Weld Quality: Voltage controls arc length and arc cone width. Higher voltage causes wider bead, flatter profile. Very high voltage causes undercut, inconsistent penetration, possible LOF at weld toes. For GMAW spray transfer on mild steel typical range is 22-28 V. Voltage instability with high CV indicates arc wandering and is a leading indicator of incomplete fusion and porosity risk. voltage_cv > 0.15 is a risk flag.", "metadata": {"source": "Technical reference", "section": "Voltage", "chunk_type": "parameter_effect", "defect_type": "incomplete_fusion"}},
      {"id": "heat_input_amperage_effect", "text": "Amperage Effect on Weld Quality: Amperage is the dominant driver of heat input. Higher amperage means deeper penetration and greater fusion. Too low amperage causes cold weld, lack of fusion, incomplete penetration. Amperage is directly correlated to wire feed speed in GMAW. amps_cv > 0.12 is a risk flag. Low amps_mean with high travel speed is the primary LOF/LOP sensor signature combination.", "metadata": {"source": "Technical reference", "section": "Amperage", "chunk_type": "parameter_effect", "defect_type": "incomplete_fusion"}},
      {"id": "heat_input_travel_speed_effect", "text": "Travel Speed Effect on Weld Quality: Travel speed is inversely proportional to heat input. Too fast cold travel causes insufficient heat to joint walls resulting in LOF, IRP, and poor tie-in. Too slow hot travel causes burn-through, distortion, and porosity. heat_input_drop_severity captures rapid cold transitions indicative of stitch restart events and travel speed spikes.", "metadata": {"source": "Technical reference", "section": "Travel Speed", "chunk_type": "parameter_effect", "defect_type": "lack_of_fusion"}},
      {"id": "heat_input_cv_significance", "text": "Coefficient of Variation CV in Welding: CV = standard deviation / mean. High CV on heat_input > 0.20 indicates unstable welding process where the welder is not maintaining consistent parameters. This leads to cold zones with LOF risk and hot zones with porosity risk alternating within a pass. heat_input_cv is a strong proxy for welder consistency even when mean heat input appears acceptable.", "metadata": {"source": "Technical reference", "section": "Process Stability", "chunk_type": "feature_explanation"}},
      {"id": "heat_dissipation_significance", "text": "Heat Dissipation Rate LOF Risk Signal: Spikes in heat dissipation rate indicate sudden torch movement causing rapid arc interruption, stitch starts and stops with cold restarts, excessive travel speed bursts, or loss of shielding gas coverage. Expert baseline: heat_diss_max_spike < 10 C/s. Novice risk threshold: heat_diss_max_spike > 40 C/s. Above 60 C/s high LOF/LOP risk REWORK likely required.", "metadata": {"source": "WarpSense technical basis", "section": "Feature Interpretation", "chunk_type": "feature_explanation", "defect_type": "lack_of_fusion"}},
      {"id": "root_cause_lof_primary", "text": "Root Causes Lack of Fusion: Primary causes are insufficient heat input where arc energy too low to melt sidewall metal, incorrect torch angle where arc directed away from fusion zone, excessive travel speed, short-circuit GMAW transfer, surface contamination, excessive wire extension, and cold restarts at stitch transitions. LOF is a planar defect invisible to X-ray if parallel to beam, visual inspection, and PT/MT.", "metadata": {"source": "Technical synthesis", "section": "Root Cause", "defect_type": "lack_of_fusion", "chunk_type": "root_cause"}},
      {"id": "root_cause_lop_primary", "text": "Root Causes Incomplete Root Penetration: Primary causes are insufficient amperage, excessive travel speed, root gap too small, root face too large, large electrode diameter for joint size, and incorrect torch angle in groove. LOP is most common in single-side CJP butt welds, narrow groove configurations, and positional welding. Low heat_input_mean combined with high angle_deviation = high LOP probability.", "metadata": {"source": "Technical synthesis", "section": "Root Cause", "defect_type": "incomplete_penetration", "chunk_type": "root_cause"}},
      {"id": "root_cause_porosity", "text": "Root Causes Porosity: Primary causes are moisture in flux or electrode coating, loss of shielding gas coverage from wind or excessive torch angle, base metal contamination, excessive travel speed, excessive voltage or long arc, and moisture-laden shielding gas. High heat_diss_max_spike at restart points combined with high voltage_cv increases porosity probability at stitch boundaries.", "metadata": {"source": "Technical synthesis", "section": "Root Cause", "defect_type": "porosity", "chunk_type": "root_cause"}},
      {"id": "root_cause_undercut", "text": "Root Causes Undercut: Primary causes are excessive amperage or voltage causing excess melting of base metal at weld toe, incorrect torch angle causing asymmetric heat distribution, excessive travel speed pulling molten metal from toe, and incorrect electrode manipulation. Corrective action: reduce amperage 10-15%, correct torch angle to 45 degrees, slow travel speed at weld toes.", "metadata": {"source": "Technical synthesis", "section": "Root Cause", "defect_type": "undercut", "chunk_type": "root_cause"}},
      {"id": "root_cause_cracking", "text": "Root Causes Weld Cracking: Hot cracking from high heat input and high dilution. Cold cracking from hydrogen-induced cracking in high carbon equivalent steel with high restraint and insufficient preheat. Crater cracking from abrupt arc termination. All cracks are zero tolerance at all AWS D1.1 and ISO 5817 levels. Extreme heat_input spikes followed by abrupt drops are a crater cracking risk signature.", "metadata": {"source": "Technical synthesis", "section": "Root Cause", "defect_type": "crack", "chunk_type": "root_cause"}},
      {"id": "torch_angle_work_angle", "text": "Torch Work Angle for T-joints and fillet welds: Standard optimal work angle is 45 degrees bisecting the joint to distribute heat equally to both members. Work angle too high > 55 degrees causes undercut on vertical member. Work angle too low < 35 degrees causes LOF on vertical leg. Maintaining +/- 5 degrees of target is professional standard. angle_deviation_mean > 10 degrees is elevated LOF risk. > 20 degrees is high LOF probability.", "metadata": {"source": "Technical reference", "section": "Torch Angle", "chunk_type": "technique", "defect_type": "lack_of_fusion"}},
      {"id": "torch_angle_variability_consequence", "text": "Torch Angle Variability Consequence: Welders often change torch angle to improve their view of the arc, which is a primary cause of varying penetration depth and lack of inter-run fusion. High angle_drift_1s indicates sudden technique breaks common at position changes and weld restarts. These are precisely the LOF risk points.", "metadata": {"source": "Technical synthesis", "section": "Torch Angle", "chunk_type": "feature_explanation", "defect_type": "lack_of_fusion"}},
      {"id": "corrective_lof_thermal_instability", "text": "Corrective Actions LOF from Thermal Instability: When heat_diss_max_spike > 40 C/s AND heat_input_cv > 0.20: Diagnosis is inconsistent travel speed with cold restart events. Action 1 maintain continuous arc without stops. Action 2 reduce travel speed variance by 20-30%. Action 3 verify wire feed speed is stable. Action 4 pre-heat restart points by dwelling 1-2 seconds before advancing. Expected: heat_diss_max_spike should drop below 20 C/s within 2 sessions if technique corrected.", "metadata": {"source": "WarpSense corrective protocol", "section": "Corrective", "chunk_type": "corrective_action", "defect_type": "lack_of_fusion"}},
      {"id": "corrective_lof_angle_drift", "text": "Corrective Actions LOF from Torch Angle Deviation: When angle_deviation_mean > 15 degrees from 45 degree target: Diagnosis is misdirected arc with heat not reaching fusion zone. Action 1 return torch work angle to 45 +/- 5 degrees. Action 2 check body position since angle drift often caused by reaching or stretching. Action 3 use angle guide for repetitive welds. Action 4 practice on scrap coupons until angle_deviation < 10 degrees.", "metadata": {"source": "WarpSense corrective protocol", "section": "Corrective", "chunk_type": "corrective_action", "defect_type": "lack_of_fusion"}},
      {"id": "corrective_lof_cold_window", "text": "Corrective Actions LOF from Cold Heat Windows: When heat_input_min_rolling < 3500 J AND heat_input_drop_severity > 15: Diagnosis is cold zones within pass at stitch transitions. Action 1 increase base amperage 10-15%. Action 2 at each stitch restart pause 1s before advancing. Action 3 check interpass temperature and preheat to minimum 50C if too cold. Action 4 ensure clean joint preparation. Safety constraint: do not increase heat input above 3.0 kJ/mm without re-qualifying WPS.", "metadata": {"source": "WarpSense corrective protocol", "section": "Corrective", "chunk_type": "corrective_action", "defect_type": "lack_of_fusion"}},
      {"id": "corrective_undercut_high_heat", "text": "Corrective Actions Undercut from Excessive Heat: When heat_input_mean is high AND angle_deviation_mean > 10 degrees: Action 1 reduce amperage 10-15%. Action 2 correct torch work angle to 45 +/- 5 degrees. Action 3 slow travel speed at weld toes. Action 4 reduce weave width with toe dwell instead of wide sweep. For fatigue-critical Level B members verify undercut depth <= 0.05t per ISO 5817:2023 Annex B.", "metadata": {"source": "WarpSense corrective protocol", "section": "Corrective", "chunk_type": "corrective_action", "defect_type": "undercut"}},
      {"id": "corrective_porosity_heat_diss", "text": "Corrective Actions Porosity from Arc Loss: When heat_diss_max_spike > 60 C/s: Action 1 check shielding gas flow rate set to 15-20 L/min and verify no leaks. Action 2 check for drafts and shield weld area. Action 3 reduce travel angle to maintain shielding gas coverage. Action 4 reduce voltage 1-2 V to shorten arc length. Action 5 pre-dry electrodes and wire since hydrogen from moisture is primary porosity cause in humid environments.", "metadata": {"source": "WarpSense corrective protocol", "section": "Corrective", "chunk_type": "corrective_action", "defect_type": "porosity"}},
      {"id": "corrective_parameter_bounds", "text": "WarpSense Corrective Parameter Safety Bounds: All corrective adjustments must stay within WPS-qualified ranges. Amperage adjustments within +/-15% of WPS mid-range without re-qualification. Voltage within +/-10%. Travel speed within +/-30%. Torch angle target 45 +/- 10 degrees for fillet/T-joints. Heat input must not increase beyond WPS qualified maximum. If correction would exceed WPS bounds a new WPS must be qualified before implementing.", "metadata": {"source": "WarpSense system design", "section": "Safety Bounds", "chunk_type": "constraint"}},
      {"id": "warpsense_feature_thresholds", "text": "WarpSense Feature Threshold Reference: heat_diss_max_spike GOOD < 10 MARGINAL 10-40 RISK > 40 C/s. angle_deviation_mean GOOD < 8 MARGINAL 8-15 RISK > 15 degrees. heat_input_min_rolling GOOD > 4000 MARGINAL 3500-4000 RISK < 3500 J. heat_input_drop_severity GOOD < 10 MARGINAL 10-15 RISK > 15. heat_input_cv GOOD < 0.10 MARGINAL 0.10-0.20 RISK > 0.20. arc_on_ratio GOOD > 0.90 MARGINAL 0.75-0.90 RISK < 0.75.", "metadata": {"source": "WarpSense Phase 1", "section": "Thresholds", "chunk_type": "threshold"}},
      {"id": "warpsense_defect_feature_map", "text": "WarpSense Defect-to-Feature Mapping: LOF primary sensors are angle_deviation_mean, heat_input_min_rolling, heat_diss_max_spike, arc_on_ratio. LOP primary sensors are heat_input_mean, amps_cv, heat_input_cv. Porosity primary sensors are heat_diss_max_spike and voltage_cv. Undercut primary sensors are heat_input_mean high and angle_deviation_mean for asymmetric heat.", "metadata": {"source": "WarpSense Phase 2 design", "section": "Agent Design", "chunk_type": "system_design"}},
      {"id": "warpsense_quality_class_mapping", "text": "WarpSense Quality Class to Standards Mapping: GOOD maps to ISO 5817 Level C or better and AWS D1.1 visual acceptance met. Disposition PASS. MARGINAL maps to ISO 5817 Level D and borderline AWS D1.1. Disposition CONDITIONAL PASS with monitoring. DEFECTIVE is below ISO 5817 Level D on LOF/LOP indicators. Disposition REWORK REQUIRED with UT inspection before acceptance.", "metadata": {"source": "WarpSense Phase 2 design", "section": "Quality Classes", "chunk_type": "system_design"}},
      {"id": "warpsense_lof_lop_invisible_inspection", "text": "LOF/LOP Invisible Defect Problem: Lack of fusion and incomplete root penetration are the most dangerous weld defects because they are planar defects yet NOT detectable by visual inspection VT, dye penetrant PT, magnetic particle MT if planar to field, or X-ray RT if parallel to beam. Only UT reliably detects all orientations of LOF/LOP. Current shipyard NDT coverage is approximately 10% of welds. WarpSense provides 100% first-pass LOF/LOP risk screening.", "metadata": {"source": "WarpSense system rationale", "section": "Business case", "defect_type": "lack_of_fusion", "chunk_type": "context"}},
      {"id": "warpsense_heat_input_expert_novice", "text": "WarpSense Expert vs Novice Benchmark Phase 1: heat_diss_max_spike Expert 3.6 vs Novice 65.2 C/s 18x separation. angle_deviation_mean Expert 4.0 vs Novice 20.7 degrees 5x separation. heat_input_min_rolling Expert 3982 vs Novice 3211 J 24% drop cold windows. heat_diss_max_spike ranked #1 feature by both GradientBoosting and XGBoost independently.", "metadata": {"source": "WarpSense Phase 1 results", "section": "Benchmarks", "chunk_type": "benchmark"}},
      {"id": "warpsense_arc_on_ratio", "text": "WarpSense Arc-On Ratio Feature: arc_on_ratio is fraction of session frames where arc is active V > 5 and A > 5. Low arc_on_ratio < 0.75 indicates frequent arc interruptions. Each arc restart is a LOF risk point cold restart interface. Expert arc_on_ratio is typically 0.90-0.95. Novice can drop to 0.60-0.70 with frequent stops for repositioning.", "metadata": {"source": "WarpSense Phase 1", "section": "Feature Explanation", "chunk_type": "feature_explanation"}},
      {"id": "research_amirafshari_2022", "text": "Research Anchor Amirafshari and Kolios 2022 International Journal of Fatigue: LOF and LOP are the dominant fatigue-critical defects in shipyard welds yet systematically missed by conventional inspection regimes including VT, PT, and RT. The paper quantifies the gap between true defect occurrence and detected defect rates at typical 10% NDT coverage. Travel speed instability and torch angle variability are the dominant controllable causal factors for LOF in production welding.", "metadata": {"source": "Amirafshari & Kolios 2022, Int. J. Fatigue", "section": "Research basis", "chunk_type": "research"}},
      {"id": "stitch_welding_risk", "text": "Stitch Welding Risk LOF at Restart Interfaces: Each restart creates a cold interface. The first 2-5 mm of each restart is at elevated LOF/LOP risk. Novice sensor signature is high heat_input_drop_severity and high heat_diss_max_spike. Mitigation: pre-heat restart crater before advancing, use short overlap at each restart advancing torch back 5 mm into previous bead, inspect stitch start points specifically in NDT.", "metadata": {"source": "Technical synthesis", "section": "Stitch Welding", "chunk_type": "technique", "defect_type": "lack_of_fusion"}},
      {"id": "humidity_tropical_context", "text": "Tropical Shipyard Context Humidity and Hydrogen: Singapore and Southeast Asian shipyards operate at 80-90% relative humidity. Flux-coated SMAW electrodes must be baked at 300C for 2 hours and stored at 120C. Hydrogen from moisture is the primary porosity cause and contributes to hydrogen-induced cold cracking in higher strength steels. Rapid heat dissipation in tropical humidity compresses the temperature window for hydrogen outgassing.", "metadata": {"source": "IACS Rec.47 + Technical synthesis", "section": "Environment", "chunk_type": "context"}},
      {"id": "ndt_method_selection", "text": "NDT Method Selection for LOF/LOP per ISO 17635: For LOF planar subsurface use UT PAUT preferred which detects LOF in all orientations, RT which detects LOF only if beam perpendicular to defect plane, or TOFD highly sensitive for planar defects. WarpSense recommendation: when AI risk score indicates HIGH LOF/LOP probability require UT inspection of flagged segments before acceptance. Targeted UT replaces random 10% coverage with risk-stratified coverage.", "metadata": {"source": "ISO 17635", "section": "NDT Selection", "chunk_type": "inspection", "defect_type": "lack_of_fusion"}},
      {"id": "disposition_framework", "text": "WarpSense Disposition Framework: PASS all features in GOOD range confidence > 0.80 ISO 5817 Level C met. Standard documentation next inspection at normal schedule. CONDITIONAL one or more features in MARGINAL band or confidence 0.60-0.80. Increase monitoring for next 3 sessions and flag for supervisor review. REWORK REQUIRED any LOF/LOP feature in RISK range or confidence > 0.75 for DEFECTIVE. Stop acceptance, require UT inspection, issue corrective action sheet. Third consecutive REWORK for same welder triggers mandatory retraining.", "metadata": {"source": "WarpSense Phase 2 design", "section": "Disposition", "chunk_type": "disposition"}},
      {"id": "continuous_novice_signature", "text": "Continuous Novice Weld Sensor Signature: High arc_on_ratio 0.85-0.95 continuous arc few stops. High angle_deviation_mean > 15 degrees poor torch discipline. High heat_diss_max_spike > 40 C/s technique corrections causing momentary speed bursts. Moderate heat_input_cv 0.15-0.25 inconsistent parameter control. Low heat_input_min_rolling < 3500 J despite adequate mean from travel speed bursts. This pattern is more dangerous than stitch welding because LOF is distributed throughout the weld length.", "metadata": {"source": "WarpSense Phase 1 analysis", "section": "Pattern Recognition", "chunk_type": "benchmark"}},
      {"id": "expert_weld_signature", "text": "Expert Weld Target Sensor Pattern: heat_diss_max_spike < 5 C/s controlled restarts. angle_deviation_mean < 5 degrees from 45 degree target. heat_input_min_rolling > 4000 J no cold windows. heat_input_cv < 0.08 highly consistent process. voltage_cv < 0.06 and amps_cv < 0.06 stable arc. arc_on_ratio 0.88-0.92. heat_input_drop_severity < 10 managed stitch transitions. Expert signature is the target state WarpSense corrective actions aim to achieve.", "metadata": {"source": "WarpSense Phase 1 analysis", "section": "Pattern Recognition", "chunk_type": "benchmark"}},
      {"id": "multi_pass_interpass_temp", "text": "Multi-Pass Welding Interpass Temperature: Too cold below minimum preheat causes LOF at inter-run interfaces. Too hot above maximum interpass causes HAZ softening in TMCP steels and increased distortion. Typical maximum interpass temperature for shipyard hull steel is 250C. Very low heat_diss_mean may indicate welding is occurring on a very hot base suggesting too high interpass temperature. Very high heat_diss_mean indicates cold interpass and LOF risk.", "metadata": {"source": "AWS D1.1 / IACS Rec.47", "section": "Multi-pass", "chunk_type": "procedure"}},
      {"id": "iso15614_wps_qualification", "text": "ISO 15614-1 WPS Qualification: Specifies requirements for qualification of welding procedures by testing. PQR documents actual test conditions. WPS defines production welding parameters. Parameters documented include base material, filler metal, position, heat input range, preheat, interpass temperature. WarpSense features map directly to WPS essential variables providing real-time monitoring of whether production welding stays within qualified parameter envelopes.", "metadata": {"source": "ISO 15614-1", "section": "WPS Qualification", "chunk_type": "procedure"}},
  ]


  SMOKE_TESTS = [
      {"name": "LOF acceptance criteria", "query": "Is lack of fusion acceptable in ISO 5817 quality level C welds?", "expect_id": "iso5817_lof_all_levels"},
      {"name": "Heat dissipation spike corrective", "query": "heat_diss_max_spike is 65 degrees per second corrective action", "expect_id": "corrective_lof_thermal_instability"},
      {"name": "Torch angle LOF root cause", "query": "angle deviation from 45 degrees causing incomplete fusion risk", "expect_id": "torch_angle_work_angle"},
      {"name": "Marine shipyard NDT gap", "query": "shipyard weld inspection coverage LOF invisible to X-ray visual", "expect_id": "warpsense_lof_lop_invisible_inspection"},
      {"name": "AWS LOF zero tolerance", "query": "AWS D1.1 incomplete fusion acceptance criteria rejection", "expect_id": "aws_d11_lof_zero_tolerance"},
  ]


  def build_knowledge_base(persist=True, verbose=True):
      if persist:
          client = chromadb.PersistentClient(path=str(CHROMA_PATH))
      else:
          client = chromadb.EphemeralClient()
      try:
          client.delete_collection(COLLECTION_NAME)
          if verbose:
              print(f"[KB] Deleted existing collection")
      except Exception:
          pass
      collection = client.get_or_create_collection(
          name=COLLECTION_NAME,
          embedding_function=DEFAULT_EF,
          metadata={"hnsw:space": "cosine"},
      )
      ids = [c["id"] for c in CHUNKS]
      texts = [c["text"] for c in CHUNKS]
      metadatas = [c["metadata"] for c in CHUNKS]
      batch_size = 50
      for i in range(0, len(CHUNKS), batch_size):
          collection.add(
              ids=ids[i:i + batch_size],
              documents=texts[i:i + batch_size],
              metadatas=metadatas[i:i + batch_size],
          )
          if verbose:
              print(f"[KB] Loaded {min(i + batch_size, len(CHUNKS))}/{len(CHUNKS)} chunks...")
      if verbose:
          print(f"[KB] Built: {collection.count()} chunks in {COLLECTION_NAME!r}")
          if persist:
              print(f"[KB] Persisted to: {CHROMA_PATH}")
      return collection


  def query_kb(collection, query, n_results=5, filter_defect=None):
      where = {"defect_type": filter_defect} if filter_defect else None
      results = collection.query(
          query_texts=[query], n_results=n_results, where=where,
          include=["documents", "metadatas", "distances"],
      )
      output = []
      for i, doc in enumerate(results["documents"][0]):
          output.append({
              "id": results["ids"][0][i],
              "text": doc,
              "source": results["metadatas"][0][i].get("source", "unknown"),
              "section": results["metadatas"][0][i].get("section", ""),
              "score": round(1 - results["distances"][0][i], 4),
          })
      return output


  def run_smoke_tests(collection):
      print("\\n" + "=" * 60)
      print("SMOKE TESTS")
      print("=" * 60)
      passed = 0
      for test in SMOKE_TESTS:
          results = query_kb(collection, test["query"], n_results=3)
          top_ids = [r["id"] for r in results]
          hit = test["expect_id"] in top_ids
          status = "PASS" if hit else "FAIL"
          if hit:
              passed += 1
          test_name = test["name"]
          query_preview = test["query"][:80]
          expect_id = test["expect_id"]
          print(f"\\n{status} -- {test_name}")
          print(f"  Query: {query_preview}")
          print(f"  Expected: {expect_id}")
          print(f"  Top-3: {top_ids}")
      print(f"\\nResults: {passed}/{len(SMOKE_TESTS)} passed")
      return passed == len(SMOKE_TESTS)


  if __name__ == "__main__":
      import argparse
      parser = argparse.ArgumentParser()
      parser.add_argument("--test", action="store_true")
      parser.add_argument("--ephemeral", action="store_true")
      args = parser.parse_args()
      print(f"WarpSense KB Builder -- {len(CHUNKS)} chunks")
      collection = build_knowledge_base(persist=not args.ephemeral, verbose=True)
      if args.test:
          run_smoke_tests(collection)
  '''

  import os
  os.makedirs("backend/knowledge", exist_ok=True)
  with open("backend/knowledge/build_welding_kb.py", "w") as f:
      f.write(content)
  print("Written: backend/knowledge/build_welding_kb.py")
  PYEOF
  ```

  **Git Checkpoint:**
  ```bash
  git add backend/knowledge/
  git commit -m "step 2.4: write build_welding_kb.py with 63 welding standards chunks"
  ```

  **✓ Verification Test:**

  **Type:** Unit

  **Action:**
  ```bash
  python3 -c "
  import sys
  sys.path.insert(0, 'backend')
  from knowledge.build_welding_kb import CHUNKS, SMOKE_TESTS
  print(f'Chunks: {len(CHUNKS)}')
  print(f'Smoke tests: {len(SMOKE_TESTS)}')
  assert len(CHUNKS) == 63, f'expected 63, got {len(CHUNKS)}'
  print('KB module OK')
  "
  ```

  **Pass:** `Chunks: 63` and `KB module OK` printed.

  **Fail:** Count wrong → write script truncated → re-run write script.

  **Step 2.4b — Build KB and verify ChromaDB write:**

  Run the KB builder and verify the collection is persisted with correct count. This confirms ChromaDB is functional. Run from repo root:
  ```bash
  cd backend
  python3 knowledge/build_welding_kb.py
  python3 -c "
  import chromadb
  from chromadb.utils import embedding_functions
  from pathlib import Path
  client = chromadb.PersistentClient(path=str(Path('knowledge/chroma_db')))
  coll = client.get_collection('welding_standards', embedding_function=embedding_functions.DefaultEmbeddingFunction())
  n = coll.count()
  assert n == 63, f'expected 63 chunks in ChromaDB, got {n}'
  print(f'ChromaDB OK: {n} chunks persisted')
  "
  ```

  **Pass:** `ChromaDB OK: 63 chunks persisted` printed.

  **Fail:** `AssertionError` or ChromaDB error → KB path wrong or write failed → check `backend/knowledge/chroma_db` exists and is writable.

---

- [ ] 🟥 **Step 2.5: Write `backend/run_warpsense_agent.py`** — *Non-critical*

  **Idempotent:** Yes.

  Run this Python script exactly as written:

  ```python
  python3 - << 'PYEOF'
  content = '''"""
  WarpSense -- End-to-End Demo Runner
  backend/run_warpsense_agent.py

  One command. Full pipeline output.

      python run_warpsense_agent.py                  # run all 10 sessions
      python run_warpsense_agent.py --session WS-003  # single session
      python run_warpsense_agent.py --worst           # only MARGINAL sessions
      python run_warpsense_agent.py --no-build-kb     # skip KB rebuild

  Pipeline per session:
      SessionFeatures -> WeldClassifier -> WeldPrediction -> WarpSenseAgent -> WeldQualityReport
  """

  import argparse
  import sys
  import time
  from pathlib import Path

  from dotenv import load_dotenv
  load_dotenv(Path(__file__).resolve().parent.parent / ".env")  # repo root .env

  _ROOT = Path(__file__).resolve().parent
  if str(_ROOT) not in sys.path:
      sys.path.insert(0, str(_ROOT))

  from features.session_feature_extractor import generate_feature_dataset, SessionFeatures
  from features.weld_classifier import WeldClassifier
  from agent.warpsense_agent import WarpSenseAgent


  def ensure_kb_exists(force_rebuild=False):
      kb_path = _ROOT / "knowledge" / "chroma_db"
      if not force_rebuild and kb_path.exists() and any(kb_path.iterdir()):
          print(f"[Runner] KB exists. Skipping rebuild. (--rebuild-kb to force)")
          return
      print("[Runner] Building knowledge base...")
      try:
          from knowledge.build_welding_kb import build_knowledge_base
          build_knowledge_base(persist=True, verbose=True)
      except ImportError as e:
          print(f"[Runner] ERROR: {e}")
          sys.exit(1)


  def run_pipeline(session_ids=None, only_marginal=False, verbose_agent=True):
      print("\\n" + "=" * 58)
      print("WARPSENSE -- FULL PIPELINE RUN")
      print("=" * 58)

      print("\\n[Phase 1] Generating feature dataset...")
      all_features = generate_feature_dataset()
      print(f"  -> {len(all_features)} sessions generated")

      if session_ids:
          all_features = [f for f in all_features if f.session_id in session_ids]
          if not all_features:
              print(f"ERROR: No sessions found matching: {session_ids}")
              sys.exit(1)
      elif only_marginal:
          all_features = [f for f in all_features if f.quality_label == "MARGINAL"]
          print(f"  -> Filtered to {len(all_features)} MARGINAL sessions")

      print("\\n[Phase 1] Training classifier and predicting...")
      classifier = WeldClassifier()
      all_for_training = generate_feature_dataset()
      train_report = classifier.train(all_for_training)
      acc = train_report["train_accuracy"]
      top_3 = train_report["top_3_drivers"]
      print(f"  -> Train accuracy: {acc:.2f}")
      if train_report.get("warning"):
          warn = train_report["warning"]
          print(f"  WARNING: {warn}")
      print(f"  -> Top drivers: {top_3}")

      predictions = {}
      for feat in all_features:
          pred = classifier.predict(feat)
          predictions[feat.session_id] = pred

      print("\\n[Phase 2] Initialising WarpSenseAgent...")
      agent = WarpSenseAgent(verbose=verbose_agent)

      reports = []
      total = len(all_features)

      for i, feat in enumerate(all_features, 1):
          pred = predictions[feat.session_id]
          sep = "-" * 58
          print(f"\\n{sep}")
          print(f"[{i}/{total}] Session: {feat.session_id} | Label: {feat.quality_label} | Predicted: {pred.quality_class} ({pred.confidence:.2f})")
          print(sep)
          t0 = time.time()
          report = agent.assess(pred, feat)
          elapsed = time.time() - t0
          print(f"\\n{report.render()}")
          print(f"[Timing] {elapsed:.2f}s")
          reports.append(report)

      print("\\n" + "=" * 58)
      print("PIPELINE SUMMARY")
      print("=" * 58)
      h1, h2, h3, h4, h5 = "Session", "Label", "Predicted", "Disposition", "Conf"
      print(f"{h1:<18} {h2:<12} {h3:<12} {h4:<20} {h5:<6}")
      print("-" * 68)
      for feat, report in zip(all_features, reports):
          match = "OK" if feat.quality_label == report.quality_class else "MISMATCH"
          print(f"{feat.session_id:<18} {feat.quality_label:<12} {match} {report.quality_class:<10} {report.disposition:<20} {report.confidence:.2f}")

      rework = sum(1 for r in reports if r.disposition == "REWORK_REQUIRED")
      cond = sum(1 for r in reports if r.disposition == "CONDITIONAL")
      passed = sum(1 for r in reports if r.disposition == "PASS")
      sc_fails = sum(1 for r in reports if not r.self_check_passed)
      print("-" * 68)
      print(f"PASS: {passed}  |  CONDITIONAL: {cond}  |  REWORK: {rework}")
      print(f"Self-check failures: {sc_fails}/{len(reports)}")
      print("=" * 58)
      return reports


  def main():
      parser = argparse.ArgumentParser(description="WarpSense end-to-end runner")
      parser.add_argument("--session", "-s", nargs="+")
      parser.add_argument("--worst", action="store_true")
      parser.add_argument("--quiet", action="store_true")
      parser.add_argument("--rebuild-kb", action="store_true")
      parser.add_argument("--no-build-kb", action="store_true")
      args = parser.parse_args()

      if not args.no_build_kb:
          ensure_kb_exists(force_rebuild=args.rebuild_kb)

      try:
          run_pipeline(
              session_ids=args.session,
              only_marginal=args.worst,
              verbose_agent=not args.quiet,
          )
      except Exception as e:
          print(f"\\n[ERROR] Pipeline failed: {e}")
          import traceback
          traceback.print_exc()
          sys.exit(1)


  if __name__ == "__main__":
      main()
  '''

  with open("backend/run_warpsense_agent.py", "w") as f:
      f.write(content)
  print("Written: backend/run_warpsense_agent.py")
  PYEOF
  ```

  **Git Checkpoint:**
  ```bash
  git add backend/run_warpsense_agent.py
  git commit -m "step 2.5: write run_warpsense_agent.py end-to-end runner"
  ```

  **✓ Verification Test:**

  **Type:** Unit

  **Action:**
  ```bash
  python3 -c "
  import sys
  sys.path.insert(0, 'backend')
  import ast
  with open('backend/run_warpsense_agent.py') as f:
      src = f.read()
  ast.parse(src)
  print('Syntax OK')
  print(f'Lines: {len(src.splitlines())}')
  "
  ```

  **Pass:** `Syntax OK` printed. No `SyntaxError`.

  **Fail:** `SyntaxError` → write script had escape issue → re-run write script.

---

- [ ] 🟥 **Step 2.6: Full import smoke test** — *Non-critical: read-only, confirms all modules wire together*

  **Idempotent:** Yes.

  **✓ Verification Test:**

  **Type:** Integration

  **Action:**
  ```bash
  cd backend
  python3 -c "
  from pathlib import Path
  from dotenv import load_dotenv
  load_dotenv(Path('.').resolve().parent / '.env')  # repo root .env (cwd=backend)
  import sys
  sys.path.insert(0, '.')
  from features.session_feature_extractor import generate_feature_dataset
  from features.weld_classifier import WeldClassifier, WeldPrediction
  from agent.warpsense_agent import WarpSenseAgent, WeldQualityReport, THRESHOLDS
  from knowledge.build_welding_kb import CHUNKS

  sessions = generate_feature_dataset()
  clf = WeldClassifier()
  clf.train(sessions)
  pred = clf.predict(sessions[0])

  assert hasattr(pred, 'top_drivers'), 'top_drivers missing'
  assert len(pred.top_drivers) == 3, f'expected 3 drivers got {len(pred.top_drivers)}'
  assert len(CHUNKS) == 63, f'expected 63 chunks got {len(CHUNKS)}'
  assert len(THRESHOLDS) == 10, f'expected 10 thresholds got {len(THRESHOLDS)}'

  print(f'Sessions:           {len(sessions)}')
  print(f'top_drivers[0]:     {pred.top_drivers[0]}')
  print(f'KB chunks:          {len(CHUNKS)}')
  print(f'Agent thresholds:   {len(THRESHOLDS)}')
  print('ALL IMPORTS: OK')
  "
  ```

  **Expected:**
  ```
  Sessions:           10
  top_drivers[0]:     ('heat_diss_max_spike', 0.xxx)
  KB chunks:          63
  Agent thresholds:   10
  ALL IMPORTS: OK
  ```

  **Pass:** `ALL IMPORTS: OK` printed, all counts match.

  **Fail:**
  - `ModuleNotFoundError: agent` → Step 2.2 incomplete → confirm `backend/agent/__init__.py` exists.
  - `ModuleNotFoundError: knowledge` → Step 2.4 incomplete → confirm `backend/knowledge/__init__.py` exists.
  - `AttributeError: top_drivers` → Step 2.1 incomplete → re-run Step 2.1.
  - `KB chunks: 0` → write script error → re-run Step 2.4 write script.
  - `Agent thresholds: 0` → warpsense_agent.py write failed → re-run Step 2.3 write script.

  **Step 2.6b — Verify `agent.assess()` runs (steps 1–3 without Groq):**

  Instantiate the agent and run `_step1_defect_intake`, `_step2_threshold_check`, `_step3_retrieve_standards` with real `WeldPrediction` and `SessionFeatures`. This confirms the pipeline up to the LLM call. The KB must be built (Step 2.4b) first. GROQ_API_KEY loads from repo root .env; the runner has load_dotenv built-in.
  ```bash
  cd backend
  python3 -c "
  from pathlib import Path
  from dotenv import load_dotenv
  load_dotenv(Path('.').resolve().parent / '.env')
  import sys
  sys.path.insert(0, '.')
  from features.session_feature_extractor import generate_feature_dataset
  from features.weld_classifier import WeldClassifier
  from agent.warpsense_agent import WarpSenseAgent

  sessions = generate_feature_dataset()
  clf = WeldClassifier()
  clf.train(sessions)
  pred = clf.predict(sessions[0])
  feat = sessions[0]

  agent = WarpSenseAgent(verbose=False)
  defects = agent._step1_defect_intake(pred, feat)
  violations = agent._step2_threshold_check(feat)
  chunks = agent._step3_retrieve_standards(pred, feat, defects, violations)
  assert isinstance(defects, list), 'defects must be list'
  assert isinstance(violations, list), 'violations must be list'
  assert len(chunks) > 0, 'ChromaDB must return chunks'
  print(f'assess path 1-3 OK: {len(defects)} defects, {len(violations)} violations, {len(chunks)} chunks')
  "
  ```

  **Pass:** `assess path 1-3 OK: ...` printed.

  **Fail:** Exception or 0 chunks → KB not built or path wrong → run Step 2.4b first; if KB built, check `_KB_PATH` in agent matches `backend/knowledge/chroma_db`.

  **Git Checkpoint:**
  ```bash
  # Read-only step — no commit.
  ```

---

## Regression Guard

**Systems at risk:**
- `weld_classifier.py` — the only existing file modified. Adding a field to `WeldPrediction` could break existing callers that instantiate it with positional args.

**Regression verification:**

| System | Pre-change | Post-change check |
|--------|-----------|-------------------|
| `WeldPrediction` creation | 4-field instantiation works | Step 2.1 verification test confirms `predict()` still returns valid object |
| `WeldClassifier.train()` | Returns dict with `top_3_drivers` | `grep -c "def train" backend/features/weld_classifier.py` still = 1; train dict unchanged |
| Any route importing `WeldPrediction` | Import succeeds | `grep -r "from features.weld_classifier import" backend/routes/ backend/services/ 2>/dev/null` — run each found import path in isolation |

**Test count check:**
```bash
pytest backend/tests/ -q 2>/dev/null || echo "no test suite"
# Count must not decrease from pre-flight baseline
```

---

## Rollback

```bash
# Reverse order
git revert HEAD   # Step 2.5 runner
git revert HEAD   # Step 2.4 knowledge/
git revert HEAD   # Step 2.3 agent file
git revert HEAD   # Step 2.2 agent/__init__.py
git revert HEAD   # Step 2.1 weld_classifier.py

# Confirm clean
grep -c "top_drivers" backend/features/weld_classifier.py   # must be 0
ls backend/agent/warpsense_agent.py 2>&1 || echo "gone"
```

---

## Risk Heatmap

| Step | Risk | What Could Go Wrong | Detection | Idempotent |
|------|------|---------------------|-----------|------------|
| 2.1 `top_drivers` | 🟡 Medium | UNVERIFIABLE var names in `weld_classifier.py` — Pre-Read Gate is mandatory | Verification test catches AttributeError | Yes |
| 2.2 mkdir | 🟢 Low | None | `ls` | Yes |
| 2.3 Write agent | 🔴 High | Python heredoc escape corrupts file | `ast.parse` + grep checks | Yes |
| 2.4 Write KB | 🟡 Medium | Chunk count wrong if write truncated | `len(CHUNKS) == 63` assert; Step 2.4b verifies ChromaDB | Yes |
| 2.5 Write runner | 🟢 Low | Escape issue in f-string | `ast.parse` check | Yes |
| 2.6 Smoke test | 🟢 Low | Catches all above | Run last | Yes |

---

## Success Criteria

| Feature | Target | Verification |
|---------|--------|--------------|
| `top_drivers` on `WeldPrediction` | 3 tuples `(str, float)` | Step 2.1 assertion test |
| Zero Anthropic traces in agent | `grep` = `0` | Step 2.3 check |
| Agent imports cleanly | No `ImportError` | Step 2.6 `ALL IMPORTS: OK` |
| KB chunks | 63 | Step 2.6 assert |
| All thresholds loaded | 10 | Step 2.6 assert |
| Regression: `train()` unchanged | Returns same dict | `grep -c "def train"` = 1 |

---

⚠️ **Step 2.1 Pre-Read Gate is mandatory — do not skip it. `weld_classifier.py` internal names are unverifiable without reading the file first.**
⚠️ **Step 2.3 is the highest-risk write. Run `ast.parse` before committing.**
⚠️ **Do not mark any step Done until its verification test passes.**
⚠️ **Do not batch commits — one commit per step.**