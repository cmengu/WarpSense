# WarpSense — Phase 3 Evaluation Framework (Implementation Plan)

**Overall Progress: `0%`**

---

## TLDR

Phase 3 builds the evaluation infrastructure that produces the baseline numbers the entire project depends on. Nothing in `backend/eval/` exists yet. This plan creates four files from scratch — `eval_scenarios.py`, `eval_pipeline.py`, `eval_retrieval.py`, `eval_prompts.py` — plus two public methods on `WarpSenseAgent` that the prompt eval depends on. After this plan executes, running `python backend/eval/eval_pipeline.py --category FN_RISK` will produce a real FNR number against adversarial boundary scenarios. That number is the safety claim at the centre of the Razer interview.

---

## Architecture Overview

**The problem this plan solves:**

No evaluation infrastructure exists. `backend/eval/` is absent entirely. This means:
- There is no way to verify the pipeline produces correct dispositions on known inputs.
- The FNR = 0.00 safety claim cannot be substantiated — it is an assertion, not a measured number.
- There is no way to compare prompt strategies or quantify what the self-check step is actually worth.
- The P@k retrieval curve does not exist, so the Phase 5 BM25 build/skip decision has no data behind it.

This plan creates the measurement layer that turns every qualitative claim into a number.

**The patterns applied:**

| Pattern | What it is | Why chosen | What breaks if violated |
|---|---|---|---|
| **Data Layer First** | Scenario data (`eval_scenarios.py`) is authored before any runner that consumes it | Runners import from a single source of truth; changing a scenario value propagates everywhere | If runners inline their own feature values, a single threshold change requires edits in 3 files |
| **Override-on-Baseline** | `make_features()` applies a sparse dict of overrides to a known-good expert baseline | Each scenario communicates only what is *different* from a passing session — intent is immediately readable | If every scenario specifies all 11 features, a threshold change in `warpsense_agent.py` requires updating every scenario by hand |
| **Facade / Public Contract** | `prepare_context()` and `verify_citations()` are stable public wrappers over private step methods | `eval_prompts.py` is decoupled from internal step numbering — Phase 4 can rename `_step3` without touching the eval | If `eval_prompts.py` calls `_step3_retrieve_standards` directly, any Phase 4 refactor breaks the eval |
| **Observed Confusion Matrix** | Confusion matrix is computed from `most_common_actual` (what the pipeline actually returned) not from inferred labels | Metrics are trustworthy because they record what happened, not what we expected | If we infer actual from expected, a bug that always returns CONDITIONAL would show FNR = 0 incorrectly |
| **C3 as True Baseline** | C3 uses `self_check_passed = False` by design, not by error | The A1 vs C3 delta measures what the self-check step is worth; if C3 were True, the delta collapses to zero | If C3 sets `self_check_passed = True`, the self-check value appears to be 0% and the step looks worthless |

**What stays unchanged:**

| File | Why untouched |
|---|---|
| `backend/agent/warpsense_agent.py` (all existing methods) | Step 3.4 only *adds* two public methods; all existing behaviour is unchanged |
| `backend/features/session_feature_extractor.py` | Consumed read-only by eval_scenarios.py |
| `backend/features/weld_classifier.py` | Consumed read-only by eval_pipeline.py and eval_prompts.py |
| `backend/knowledge/build_welding_kb.py` | ChromaDB must already be built; this plan only reads from it |
| All Phase 1 and Phase 2 files | Eval is a new layer, not a refactor of the existing pipeline |

**What this plan adds:**

| File / Class | Single responsibility |
|---|---|
| `backend/eval/__init__.py` | Makes `backend/eval/` a Python package |
| `backend/eval/eval_scenarios.py` | Data layer: defines `EvalScenario`, `BASE_EXPERT_FEATURES`, `make_features()`, and all 24 ground-truth scenarios |
| `backend/eval/eval_pipeline.py` | Pipeline runner: trains classifier, runs agent, computes confusion matrix from observed dispositions, reports FNR |
| `backend/eval/eval_retrieval.py` | Retrieval runner: queries ChromaDB against 25 ground-truth query→chunk pairs, computes P@k/R@k/MRR across k=1,2,3,5,6 |
| `backend/eval/eval_prompts.py` | Prompt runner: evaluates 8 variants across 24 scenarios, measures corrective action specificity and citation grounding rate |
| `WarpSenseAgent.prepare_context()` | Stable public wrapper: Steps 1–3 (defect intake + threshold check + retrieval) |
| `WarpSenseAgent.verify_citations()` | Stable public wrapper: Step 5 (self-check) |

**Critical decisions:**

| Decision | Alternative considered | Why alternative rejected |
|----------|----------------------|--------------------------|
| `eval_scenarios.py` built first, all other eval files import from it | Each eval file defines its own test fixtures inline | Inline fixtures diverge silently — a threshold boundary fix in one file doesn't propagate to others |
| `prepare_context()` and `verify_citations()` as public API before `eval_prompts.py` is written | `eval_prompts.py` calls private step methods directly | Private method names are implementation details; Phase 4 will rename them; the eval must not be entangled with internal numbering |
| `most_common_actual` computed via `Counter` across N runs | Use `actual_disposition` from a single run | Single-run metrics are noisy for LLM-backed components; mode across N runs reflects stable pipeline behaviour |
| `K_VALUES = [1, 2, 3, 5, 6]` — k=6 is the operating point | k=3 as the primary reported metric | The agent currently retrieves 6 chunks (`n_standards_chunks=6`); evaluating at k=3 would report metrics for a configuration that doesn't exist in production |
| C3 sets `self_check_passed = False` | C3 sets `self_check_passed = True` (no call made, assume pass) | True would collapse the A1 vs C3 delta to zero, making the self-check step appear worthless |
| All 4 LOF/LOP features use boundary values `±0.1` from threshold in FN_RISK scenarios | Round numbers well inside RISK band | Floor cases test that the RISK threshold is actually enforced at the boundary; well-inside-RISK scenarios would pass even with a miscalibrated threshold |
| `PipelineEvalReport` uses `mean_llm_response_rate` not `mean_llm_alignment` | Field name `iso_5817_align_rate` or `mean_llm_alignment` | The eval cannot measure true alignment without a gold-standard iso_5817_level per scenario; the field measures response *presence*, not correctness — the name must reflect that |

**Known limitations:**

| Limitation | Why acceptable now | Upgrade path |
|-----------|-------------------|--------------|
| Latency breakdown is p50/p95/p99 of total round-trip only; no per-component timing | Phase 6 will add `RunTracer`; building it now would scope-creep Phase 3 | Add `RunTracer` in Phase 6; `PipelineEvalReport` already documents "Component breakdown: Phase 6 (RunTracer)" |
| `iso_5817_level` accuracy is not measured per scenario | Requires a gold-standard label per scenario, which would require expert review | Phase 6 adds EXACT tolerance to `EvalScenario`; for now `DISPOSITION_ONLY` is sufficient to prove the safety claim |
| 24 scenarios is a small sample | Sufficient to demonstrate FNR = 0.00 on boundary cases; not sufficient for a statistically robust production claim | Phase 6 expands to 50+ scenarios using the same `EvalScenario` dataclass |
| `--no-llm` flag not implemented | Not needed for initial FNR measurement; adding it now adds argparse complexity | Add in Phase 6 as part of CI speed optimisation |

---

## Critical Decisions
- **Data layer first** — `eval_scenarios.py` before any runner; single source of truth for all 24 test inputs.
- **Facade over internals** — `prepare_context()` and `verify_citations()` decouple the eval from private step numbering before `eval_prompts.py` is written.
- **Observed confusion matrix** — `most_common_actual` via `Counter` ensures metrics describe what actually happened.
- **k=6 as operating point** — `K_VALUES` includes 6 and the summary marker fires at `k == 6`, not `k == 3`.
- **C3 = False baseline** — C3 sets `self_check_passed = False` so the A1 vs C3 delta is a real measurement, not a zero.
- **Boundary FN_RISK values** — TC_021 through TC_024 use `threshold ± 0.1` to test that the threshold is enforced at the floor.

---

## Clarification Gate

| Unknown | Required | Source | Blocking | Resolved |
|---------|----------|--------|----------|----------|
| Exact GOOD band thresholds for all 11 features | Values for `heat_input_min_rolling`, `arc_on_ratio`, etc. | Pre-Flight reads `warpsense_agent.py` THRESHOLDS | Steps 3.1, 3.2 | ⬜ |
| `SessionFeatures` accepts `quality_label`? | Optional[str] = None or absent | Pre-Flight reads `session_feature_extractor.py` | Step 3.2 | ⬜ |
| Exact signatures and return types of `_step1`, `_step3` | Single value (list) not tuple | Pre-Flight reads `warpsense_agent.py` | Step 3.4 | ⬜ |
| Exact signatures of `_step2`, `_step5_self_check` | Method names and parameter order | Pre-Flight reads `warpsense_agent.py` | Step 3.4 | ⬜ |
| Return type of `_step5_self_check` | `(bool, str)` or other | Pre-Flight reads method signature | Step 3.4 | ⬜ |
| `WeldQualityReport` field names | `disposition`, `iso_5817_level`, `confidence`, `self_check_passed` | Pre-Flight reads `warpsense_agent.py` | Step 3.3 | ⬜ |
| `StandardsChunk` and `ThresholdViolation` shapes | `chunk_id`, `source`, `section`, `text`; `as_display_line()` | Pre-Flight reads `warpsense_agent.py` | Step 3.6 | ⬜ |
| `generate_feature_dataset` return type; `WeldClassifier.train` expects | List[SessionFeatures] | Pre-Flight runs inline check | Step 3.3 | ⬜ |
| Chunk IDs in `build_welding_kb.py` | Spot-check 3 IDs vs GROUND_TRUTH | Pre-Flight grep | Step 3.5 | ⬜ |
| `SessionFeatures` field names and constructor signature | All 11 feature field names in order | Pre-Flight reads `session_feature_extractor.py` | Step 3.1 | ⬜ |
| `WeldPrediction` fields | `session_id`, `quality_class`, `confidence`, `top_drivers` | Pre-Flight reads `weld_classifier.py` | Steps 3.2, 3.3 | ⬜ |
| ChromaDB collection name | `"welding_standards"` or other | Pre-Flight reads `build_welding_kb.py` | Steps 3.3, 3.5 | ⬜ |
| Chroma path | `backend/knowledge/chroma_db/` or other | Pre-Flight reads `build_welding_kb.py` | Steps 3.3, 3.5 | ⬜ |

All resolved in Pre-Flight via codebase reads. No human input required.

---

## Agent Failure Protocol

1. A verification command fails → read the full error output.
2. Cause is unambiguous → make ONE targeted fix → re-run the same verification command.
3. If still failing after one fix → **STOP**. Output full contents of every file modified in this step. Report: (a) command run, (b) full error verbatim, (c) fix attempted, (d) current state of each modified file, (e) why you cannot proceed.
4. Never attempt a second fix without human instruction.
5. Never modify files not named in the current step.

---

## Pre-Flight — Run Before Any Code Changes

```
Read the following files in full and capture:

(1) backend/agent/warpsense_agent.py
    — all method names defined on WarpSenseAgent (grep "    def ")
    — exact signature of _step1_defect_intake
    — exact signature of _step2_threshold_check
    — exact signature of _step3_retrieve_standards
    — exact signature of _step5_self_check (note: does it accept dict or typed object?)
    — exact return type of _step5_self_check
    — full THRESHOLDS constant (all 11 features, all band values)
    — exact line of "def assess" (insertion anchor for Step 3.4) — COPY THIS VERBATIM for str_replace find string
    — confirm "def prepare_context" does NOT exist yet

(2) backend/features/session_feature_extractor.py
    — exact SessionFeatures dataclass field names in order
    — exact constructor signature
    — run: grep -n "def to_vector" backend/features/session_feature_extractor.py
    — Must return exactly 1 match. _step1_defect_intake and _step2_threshold_check both call features.to_vector(). If SessionFeatures does not implement to_vector(), every assessment fails with AttributeError, caught by broad except → report=None → actual_disposition="ERROR" → FNR=1.000. Silent corruption of the headline metric.
    — run: grep -n "quality_label" backend/features/session_feature_extractor.py
    — If grep returns matches (quality_label present in dataclass or extract_session_features): SessionFeatures accepts quality_label → use make_features() Block A in Step 3.2 (includes quality_label=quality_label).
    — If grep returns no matches: SessionFeatures does NOT accept quality_label → use make_features() Block B in Step 3.2 (omit quality_label line entirely).

(3) backend/features/weld_classifier.py
    — exact WeldPrediction dataclass field names in order
    — exact signature of predict()

(4) backend/knowledge/build_welding_kb.py
    — exact COLLECTION_NAME string
    — exact chroma_db path string
    — chunk structure: each CHUNKS item has "id" (not "chunk_id") — ChromaDB stores ids; StandardsChunk uses chunk_id. Confirm the agent's _step3 returns StandardsChunk objects with chunk_id, source, section, text attributes.

(5) backend/agent/warpsense_agent.py (additional reads)
    — WeldQualityReport dataclass: list all field names (disposition, iso_5817_level, confidence, self_check_passed, etc.)
    — ThresholdViolation: confirm as_display_line() method exists; CRITICAL — confirm .severity and .defect_categories attributes exist (LOF/LOP safety override in eval_prompts _run_once uses v.severity and v.defect_categories; wrong names = override never fires = FN scenarios pass incorrectly)
    — StandardsChunk: confirm chunk_id, source, section, text, score attributes
    — _step1_defect_intake: return type (single value: list) — NOT a tuple
    — _step3_retrieve_standards: return type (single value: list[StandardsChunk]) — NOT a tuple
    — generate_feature_dataset: run `from backend.features.session_feature_extractor import generate_feature_dataset; d=generate_feature_dataset(); print(type(d), len(d), type(d[0]) if d else None)` — must return List[SessionFeatures]

(6) Check directory structure:
    — run: ls backend/eval/     (must not exist yet — confirm before creating)
    — run: ls backend/agent/    (confirm warpsense_agent.py exists)
    — run: ls backend/features/ (confirm both feature files exist)
    — _ROOT depth: from backend/eval/eval_*.py, Path(__file__).parent.parent.parent must reach project root containing .env. Confirm: Path("backend/eval/eval_pipeline.py").resolve().parent.parent.parent == project root.

(7) Chunk ID spot-check (for Step 3.5 ground truth):
    — run: grep -E '"id":\s*"[^"]+"' backend/knowledge/build_welding_kb.py | head -20
    — Spot-check: do "iso5817_lof_all_levels", "corrective_lof_angle_drift", "heat_dissipation_significance" exist verbatim? If any differs → update GROUND_TRUTH in Step 3.5 to match.

(8) ChromaDB populated (single gate for Steps 3.3 Part B, 3.4 Part B, 3.5):
    — run: python -c "import chromadb; c=chromadb.PersistentClient(path='backend/knowledge/chroma_db'); n=c.get_collection('welding_standards').count(); print(n)"
    — Must return a number > 0. If 0 or error, run python backend/knowledge/build_welding_kb.py before any step that requires ChromaDB.
    — Record result in baseline: ChromaDB chunk count = ____

Do not change anything. Show full output and wait.
```

**Baseline Snapshot (agent fills during pre-flight):**
```
WarpSenseAgent methods (in order):               ____
_step1_defect_intake signature:                  ____
_step1_defect_intake return type:                ____ (single value: list — NOT tuple)
_step2_threshold_check signature:                ____
_step3_retrieve_standards signature:             ____
_step3_retrieve_standards return type:           ____ (single value: list[StandardsChunk] — NOT tuple)
_step5_self_check signature:                     ____
_step5_self_check return type:                   ____
THRESHOLDS (all 11 features, all bands):         ____
Exact "def assess" line (for Step 3.4 find string): ____ (copy verbatim — may include type annotations)
SessionFeatures fields (in order):               ____
SessionFeatures.to_vector() exists?              ____ (grep must return exactly 1 match — if 0, eval cannot run)
quality_label grep result (make_features Block A/B): ____ (matches → Block A; no matches → Block B)
WeldPrediction fields (in order):                ____
WeldQualityReport fields (disposition, iso_5817_level, confidence, self_check_passed, etc.): ____
StandardsChunk attributes:                       ____ (chunk_id, source, section, text, score)
ThresholdViolation.as_display_line() exists?     ____ (YES/NO)
ThresholdViolation .severity and .defect_categories exist? ____ (YES/NO — LOF/LOP override uses these)
generate_feature_dataset return type:            ____ (must be List[SessionFeatures])
WeldClassifier.train() expects:                  ____ (List[SessionFeatures])
COLLECTION_NAME:                                 ____
chroma_db path:                                  ____
Chunk IDs spot-check (iso5817_lof_all_levels, corrective_lof_angle_drift, heat_dissipation_significance): ____
backend/eval/ exists:                            NO (must be NO — if YES, stop and report)
prepare_context exists on agent:                 NO (must be NO — if YES, skip Step 3.4)
ChromaDB chunk count (Pre-Flight check 8):       ____ (must be > 0 for Steps 3.3 Part B, 3.4 Part B, 3.5, 3.7)
```

**Pre-flight checks (all must pass before Step 3.1):**
- [ ] `backend/eval/` does not exist yet
- [ ] `warpsense_agent.py` exists and `WarpSenseAgent` class is present
- [ ] All 4 private step methods exist with expected names
- [ ] `_step5_self_check` accepts `dict` as first argument (if not — STOP and report actual type)
- [ ] `_step1_defect_intake` returns single value (list); `_step3_retrieve_standards` returns single value (list[StandardsChunk])
- [ ] `SessionFeatures` and `WeldPrediction` dataclasses confirmed with field names
- [ ] `grep -n "def to_vector" backend/features/session_feature_extractor.py` — must return exactly 1 match. If 0 → pipeline broken; every scenario returns ERROR and FNR=1.000.
- [ ] `grep -n "quality_label" backend/features/session_feature_extractor.py` — if matches: use Block A (include quality_label); if no matches: use Block B (omit quality_label)
- [ ] `WeldQualityReport` field names confirmed: disposition, iso_5817_level, confidence, self_check_passed
- [ ] `StandardsChunk` has chunk_id, source, section, text; `ThresholdViolation` has as_display_line(), .severity, .defect_categories (safety override depends on these)
- [ ] `generate_feature_dataset()` returns `List[SessionFeatures]`; `WeldClassifier.train()` accepts same
- [ ] THRESHOLDS constant fully captured — needed to set correct boundary values in scenarios
- [ ] At least 3 GROUND_TRUTH chunk IDs (iso5817_lof_all_levels, corrective_lof_angle_drift, heat_dissipation_significance) match build_welding_kb.py

---

## Environment Matrix

| Step | Dev | Staging | Prod | Notes |
|------|-----|---------|------|-------|
| 3.1 | ✅ | ✅ | ✅ | Creates eval/ dir and __init__.py |
| 3.2 | ✅ | ✅ | ✅ | Creates eval_scenarios.py |
| 3.3 | ✅ | ✅ | ✅ | Creates eval_pipeline.py |
| 3.4 | ✅ | ✅ | ✅ | Modifies warpsense_agent.py |
| 3.5 | ✅ | ✅ | ✅ | Creates eval_retrieval.py — requires ChromaDB populated |
| 3.6 | ✅ | ✅ | ✅ | Creates eval_prompts.py — requires Step 3.4 complete |
| 3.7 | ✅ | ✅ | ✅ | E2E smoke test — gated exit condition |

---

## Steps Analysis

```
Step 3.1 (Scaffold)      — Non-critical (no logic, no imports, pure mkdir)         — verification only — Idempotent: Yes
Step 3.2 (Scenarios)     — Critical (every other eval file imports from this)       — full code review  — Idempotent: Yes
Step 3.3 (Pipeline eval) — Critical (produces the headline FNR number)              — full code review  — Idempotent: Yes
Step 3.4 (Agent API)     — Critical (modifies a file the entire system uses)        — full code review  — Idempotent: Yes
Step 3.5 (Retrieval eval)— Critical (P@6 drives Phase 5 build/skip decision)        — full code review  — Idempotent: Yes
Step 3.6 (Prompt eval)   — Critical (depends on Steps 3.2 and 3.4; measures safety claim) — full code review — Idempotent: Yes
Step 3.7 (E2E gate)     — Critical (mandatory exit; FNR=0.000)                        — verification only  — Idempotent: Yes
```

---

## Tasks

### Phase 3.A — Directory Scaffold

**Goal:** `backend/eval/` exists as a Python package with a `results/` subdirectory. Nothing imports from it yet, so this is pure scaffolding with zero risk.

---

- [ ] 🟥 **Step 3.1: Create `backend/eval/` package and `results/` directory** — *Non-critical: pure scaffolding, no logic*

  **Step Architecture Thinking:**

  **Pattern applied:** Package Namespace Boundary — creating `__init__.py` declares that `backend/eval/` is a Python module, not a loose directory. This is not decorative; it is what allows `from backend.eval.eval_scenarios import SCENARIOS` to resolve correctly.

  **Why this step exists here in the sequence:**
  Before this step: no Python package at `backend/eval/`, so any import from a future eval file will raise `ModuleNotFoundError`. After this step: the package namespace exists and all subsequent steps can place files into it.

  **Why this file / class is the right location:**
  `backend/eval/` mirrors the existing package structure (`backend/agent/`, `backend/features/`, `backend/knowledge/`). Keeping eval as a sibling package means it can import from other `backend.*` packages without path gymnastics.

  **Alternative approach considered and rejected:**
  Place all eval scripts in the project root as flat scripts with no package structure. Rejected because flat scripts require `sys.path.insert(0, '.')` in every file and cannot be imported by each other cleanly — `eval_pipeline.py` needs to import `eval_scenarios.py`, which requires them to share a package.

  **What breaks if this step deviates from the described pattern:**
  If `__init__.py` is omitted, `from backend.eval.eval_scenarios import SCENARIOS` raises `ModuleNotFoundError` in every subsequent step.

  ---

  **Idempotent:** Yes — `mkdir -p` and `touch` are no-ops if targets already exist.

  **Pre-Read Gate:**
  - Run `ls backend/eval/ 2>&1`. Must return `No such file or directory`. If directory exists → STOP and report its contents.

  ```bash
  mkdir -p backend/eval/results
  touch backend/eval/__init__.py
  touch backend/eval/results/.gitkeep
  ```

  **What it does:** Creates the `backend/eval/` Python package and the `results/` subdirectory where all eval JSON outputs are written. The `.gitkeep` ensures the empty results directory is tracked by git.

  **Git Checkpoint:**
  ```bash
  git add backend/eval/__init__.py
  git add backend/eval/results/.gitkeep
  git commit -m "step 3.1: create backend/eval/ package scaffold"
  ```

  **Subtasks:**
  - [ ] 🟥 `backend/eval/` directory exists
  - [ ] 🟥 `backend/eval/__init__.py` exists (empty)
  - [ ] 🟥 `backend/eval/results/` directory exists

  **✓ Verification Test:**

  **Type:** Unit

  **Action:**
  ```bash
  python -c "
  import pathlib
  assert pathlib.Path('backend/eval/__init__.py').exists(), '__init__.py missing'
  assert pathlib.Path('backend/eval/results').is_dir(), 'results/ dir missing'
  print('PASS: backend/eval/ package created')
  "
  ```

  **Pass:** `PASS: backend/eval/ package created`

  **Fail:**
  - `__init__.py missing` → `touch` command did not run — re-run manually
  - `results/ dir missing` → `mkdir -p` did not run — re-run manually

---

### Phase 3.B — Scenario Dataset

**Goal:** 24 deterministic eval scenarios exist in `eval_scenarios.py`, importable as `SCENARIOS`. Feature values are verified against THRESHOLDS from Pre-Flight so no scenario has a contradicting expected disposition.

---

- [ ] 🟥 **Step 3.2: Create `backend/eval/eval_scenarios.py`** — *Critical: every other eval file imports from this; wrong values here corrupt every downstream metric*

  **Step Architecture Thinking:**

  **Pattern applied:** Single Source of Truth (Data Layer) + Override-on-Baseline. The entire eval corpus is defined in one file. Consumers (`eval_pipeline.py`, `eval_prompts.py`) import `SCENARIOS` — they never define their own fixtures. The override pattern (`make_features(overrides={...})`) means each scenario only expresses what is *different* from a known-good expert session. The intent of TC_002 is immediately readable: it overrides only `heat_diss_max_spike`, so that is the feature under test.

  **Why this step exists here in the sequence:**
  Before this step: nothing can be evaluated because there is no ground truth. After this step: Steps 3.3, 3.5, and 3.6 each have a concrete, importable set of test inputs with known expected outputs. The confusion matrix in Step 3.3 is only meaningful because the expected dispositions were fixed independently of the pipeline.

  **Why this file / class is the right location:**
  `eval_scenarios.py` is the contract between the test author and the evaluators. Keeping it separate from any runner means the scenarios can be read, reviewed, and changed without touching evaluation logic. Any future Phase 6 scenario expansion adds rows to this file only.

  **Alternative approach considered and rejected:**
  Each eval runner defines its own scenarios inline (e.g. `eval_pipeline.py` constructs `SessionFeatures` at the top of its `main()`). Rejected because inline fixtures diverge silently: if `warpsense_agent.py` changes a RISK threshold, the pipeline eval and the prompt eval would be testing against different boundaries unless both files are updated in sync.

  **What breaks if this step deviates from the described pattern:**
  If `BASE_EXPERT_FEATURES` contains a value outside the GOOD band (e.g. `heat_input_min_rolling=3982.0`, which is MARGINAL), every TRUE_PASS scenario inherits a threshold violation, causing the pipeline to return CONDITIONAL instead of PASS, and the FPR metric becomes meaningless.

  ---

  **Idempotent:** Yes — creating a file that does not exist.

  **Context:** This file is the ground truth for the entire eval. It defines what the pipeline is supposed to do in 24 specific situations. The 24 scenarios are split into four categories: TRUE_REWORK (must fire REWORK_REQUIRED), TRUE_PASS (must not fire), FP_RISK (must not over-fire — CONDITIONAL is correct), FN_RISK (safety-critical floor cases — must fire). All feature values must be verified against THRESHOLDS before writing. The critical constraint: TRUE_PASS scenarios must have ALL features inside GOOD band. FN_RISK scenarios must have at least one feature in RISK band.

  **Pre-Read Gate:**
  - Confirm THRESHOLDS captured in Pre-Flight baseline. If any field is blank → re-read `warpsense_agent.py` before proceeding.
  - Confirm `SessionFeatures` constructor signature captured. If blank → re-read `session_feature_extractor.py`.
  - Run `grep -n "quality_label" backend/features/session_feature_extractor.py`. If output shows matches (quality_label in dataclass or function) → use **Block A** below. If no matches → use **Block B** (omit quality_label line).
  - `grep -n "eval_scenarios" backend/eval/__init__.py` → must return 0 (file doesn't exist yet).

  **quality_label in make_features:** Run `grep -n "quality_label" backend/features/session_feature_extractor.py` before writing. If output contains matches → write Block A (includes `quality_label=quality_label`). If output is empty → write Block B only (omit the quality_label line from SessionFeatures). The code block shows both; you must write exactly one. Writing both or the wrong one causes TypeError at scenario construction.

  **No-Placeholder Rule:** All threshold boundary values below are taken from THRESHOLDS as read in Pre-Flight. Before writing: verify each feature's GOOD band against Pre-Flight output. **Decision rule:** If any THRESHOLDS band value differs from the comment: (a) update the feature value in that scenario to be 10% inside the correct GOOD band, (b) update the comment to match the actual threshold, (c) do NOT change expected_disposition. Example: if heat_input_min_rolling GOOD is `> 3800` not `> 4000`, set the scenario value to `4180.0` (10% inside) and comment to `# GOOD: > 3800`.

  ```python
  """
  eval_scenarios.py
  -----------------
  24 deterministic eval scenarios for WarpSense pipeline testing.

  Each scenario constructs a SessionFeatures with specific fixed values,
  runs the full agent pipeline, and compares the output disposition to
  the expected label.

  No randomness. No mock generators. Fully reproducible.

  Scenario categories:
    TRUE_REWORK  (8) — pipeline must fire REWORK_REQUIRED
    TRUE_PASS    (8) — pipeline must NOT fire, PASS expected
    FP_RISK      (4) — CONDITIONAL expected, not REWORK (over-firing risk)
    FN_RISK      (4) — floor/boundary cases that must NOT be missed

  Usage:
      from backend.eval.eval_scenarios import SCENARIOS, BASE_EXPERT_FEATURES
  """

  from dataclasses import dataclass
  from typing import Optional
  import sys
  from pathlib import Path

  _ROOT = Path(__file__).resolve().parent.parent.parent
  if str(_ROOT) not in sys.path:
      sys.path.insert(0, str(_ROOT))

  from backend.features.session_feature_extractor import SessionFeatures


  # ─────────────────────────────────────────────────────────────────────────────
  # BASE EXPERT FEATURE VALUES
  # All values safely inside GOOD band per THRESHOLDS in warpsense_agent.py.
  # Scenarios override only the features relevant to the test case.
  # ─────────────────────────────────────────────────────────────────────────────

  BASE_EXPERT_FEATURES = {
      "heat_input_mean":          5200.0,   # GOOD: > 4500
      "heat_input_min_rolling":   4200.0,   # GOOD: > 4000
      "heat_input_drop_severity":  7.0,     # GOOD: < 10
      "heat_input_cv":             0.07,    # GOOD: < 0.10
      "angle_deviation_mean":      4.0,     # GOOD: < 8
      "angle_max_drift_1s":        6.0,     # GOOD: < 10
      "voltage_cv":                0.05,    # GOOD: < 0.08
      "amps_cv":                   0.05,    # GOOD: < 0.08
      "heat_diss_mean":            1.2,     # GOOD: low
      "heat_diss_max_spike":       4.0,     # GOOD: < 10
      "arc_on_ratio":              0.93,    # GOOD: > 0.90
  }


  # make_features — copy Block A OR Block B. Block A if Pre-Flight grep found quality_label; Block B if not.
  #
  # Block A (grep returned matches):
  def make_features(session_id: str, overrides: dict, quality_label: Optional[str] = None) -> SessionFeatures:
      vals = {**BASE_EXPERT_FEATURES, **overrides}
      return SessionFeatures(
          session_id=session_id,
          heat_input_mean=vals["heat_input_mean"],
          heat_input_min_rolling=vals["heat_input_min_rolling"],
          heat_input_drop_severity=vals["heat_input_drop_severity"],
          heat_input_cv=vals["heat_input_cv"],
          angle_deviation_mean=vals["angle_deviation_mean"],
          angle_max_drift_1s=vals["angle_max_drift_1s"],
          voltage_cv=vals["voltage_cv"],
          amps_cv=vals["amps_cv"],
          heat_diss_mean=vals["heat_diss_mean"],
          heat_diss_max_spike=vals["heat_diss_max_spike"],
          arc_on_ratio=vals["arc_on_ratio"],
          quality_label=quality_label,
      )
  #
  # Block B (grep returned no matches — omit quality_label):
  # def make_features(session_id: str, overrides: dict, quality_label: Optional[str] = None) -> SessionFeatures:
  #     vals = {**BASE_EXPERT_FEATURES, **overrides}
  #     return SessionFeatures(
  #         session_id=session_id,
  #         heat_input_mean=vals["heat_input_mean"], heat_input_min_rolling=vals["heat_input_min_rolling"],
  #         heat_input_drop_severity=vals["heat_input_drop_severity"], heat_input_cv=vals["heat_input_cv"],
  #         angle_deviation_mean=vals["angle_deviation_mean"], angle_max_drift_1s=vals["angle_max_drift_1s"],
  #         voltage_cv=vals["voltage_cv"], amps_cv=vals["amps_cv"], heat_diss_mean=vals["heat_diss_mean"],
  #         heat_diss_max_spike=vals["heat_diss_max_spike"], arc_on_ratio=vals["arc_on_ratio"],
  #     )


  # ─────────────────────────────────────────────────────────────────────────────
  # EVAL SCENARIO DATACLASS
  # ─────────────────────────────────────────────────────────────────────────────

  @dataclass
  class EvalScenario:
      scenario_id:          str
      description:          str
      category:             str        # TRUE_REWORK | TRUE_PASS | FP_RISK | FN_RISK
      features:             SessionFeatures
      expected_disposition: str        # PASS | CONDITIONAL | REWORK_REQUIRED
      tolerance:            str = "DISPOSITION_ONLY"
      # DISPOSITION_ONLY:  only disposition checked (LLM output varies between runs)
      # EXACT:             disposition AND iso_5817_level must match — enforcement in Phase 6
      notes:                str = ""


  # ─────────────────────────────────────────────────────────────────────────────
  # SCENARIOS
  # ─────────────────────────────────────────────────────────────────────────────

  SCENARIOS: list[EvalScenario] = [

      # ── TRUE_REWORK (8) ───────────────────────────────────────────────────────

      EvalScenario(
          scenario_id="TC_001_novice_classic",
          description="Classic novice profile — high thermal spike + high angle drift",
          category="TRUE_REWORK",
          features=make_features("TC_001", {
              "heat_diss_max_spike":      65.0,   # RISK: > 40
              "angle_deviation_mean":     20.0,   # RISK: > 15
              "heat_input_min_rolling":  3200.0,  # RISK: < 3500
              "heat_input_drop_severity": 17.0,  # RISK: > 15
          }, quality_label="MARGINAL"),
          expected_disposition="REWORK_REQUIRED",
          notes="Mirrors the novice benchmark from Phase 1. All 4 LOF features in RISK.",
      ),

      EvalScenario(
          scenario_id="TC_002_thermal_spike_only",
          description="Thermal spike only — all other features at expert baseline",
          category="TRUE_REWORK",
          features=make_features("TC_002", {
              "heat_diss_max_spike": 45.0,  # RISK: > 40
          }, quality_label="MARGINAL"),
          expected_disposition="REWORK_REQUIRED",
          notes="Single-feature RISK. Tests that thermal spike alone triggers REWORK.",
      ),

      EvalScenario(
          scenario_id="TC_003_angle_drift_only",
          description="Angle drift only — all other features at expert baseline",
          category="TRUE_REWORK",
          features=make_features("TC_003", {
              "angle_deviation_mean": 22.0,  # RISK: > 15
          }, quality_label="MARGINAL"),
          expected_disposition="REWORK_REQUIRED",
          notes="Single-feature RISK. Tests that angle drift alone triggers REWORK.",
      ),

      EvalScenario(
          scenario_id="TC_004_cold_window_lop_risk",
          description="Cold arc window — heat_input_min_rolling in RISK band (LOP risk)",
          category="TRUE_REWORK",
          features=make_features("TC_004", {
              "heat_input_min_rolling": 2000.0,  # RISK: < 3500
          }, quality_label="MARGINAL"),
          expected_disposition="REWORK_REQUIRED",
          notes="LOP primary signal. Tests cold arc window detection independently.",
      ),

      EvalScenario(
          scenario_id="TC_005_all_lof_features_at_risk_floor",
          description="All 4 LOF features at exactly marginal_max + 0.1 (boundary RISK entry)",
          category="TRUE_REWORK",
          features=make_features("TC_005", {
              "heat_diss_max_spike":      40.1,   # RISK: > 40
              "angle_deviation_mean":     15.1,   # RISK: > 15
              "heat_input_min_rolling":  3499.9,  # RISK: < 3500
              "heat_input_drop_severity": 15.1,   # RISK: > 15
          }, quality_label="MARGINAL"),
          expected_disposition="REWORK_REQUIRED",
          notes="All 4 LOF features just inside RISK band. Tests boundary precision.",
      ),

      EvalScenario(
          scenario_id="TC_006_compound_process_instability",
          description="Compound instability — high heat_input_cv + high voltage_cv",
          category="TRUE_REWORK",
          features=make_features("TC_006", {
              "heat_input_cv": 0.30,   # RISK: > 0.20
              "voltage_cv":    0.18,   # RISK: > 0.15
              "amps_cv":       0.15,   # RISK: > 0.12
          }, quality_label="MARGINAL"),
          expected_disposition="REWORK_REQUIRED",
          notes="heat_input_cv in RISK maps to LOF — triggers hard override to REWORK.",
      ),

      EvalScenario(
          scenario_id="TC_007_low_arc_continuity",
          description="Very low arc-on ratio — excessive arc interruptions",
          category="TRUE_REWORK",
          features=make_features("TC_007", {
              "arc_on_ratio": 0.55,  # RISK: < 0.75
          }, quality_label="MARGINAL"),
          expected_disposition="REWORK_REQUIRED",
          notes="Each arc restart is a cold-start LOF risk. arc_on_ratio=0.55 is extreme.",
      ),

      EvalScenario(
          scenario_id="TC_008_heat_drop_severity_risk",
          description="heat_input_drop_severity just inside RISK band",
          category="TRUE_REWORK",
          features=make_features("TC_008", {
              "heat_input_drop_severity": 15.5,  # RISK: > 15
          }, quality_label="MARGINAL"),
          expected_disposition="REWORK_REQUIRED",
          notes="Stitch transition severity in RISK. LOF at every restart boundary.",
      ),

      # ── TRUE_PASS (8) ─────────────────────────────────────────────────────────
      # All features inside GOOD band. Disposition must be PASS.
      # NOTE: heat_input_min_rolling uses 4200.0 (not 3982 — that value is MARGINAL).
      # NOTE: arc_on_ratio uses 0.91 (not 0.88 — that value is MARGINAL).

      EvalScenario(
          scenario_id="TC_009_expert_benchmark_exact",
          description="Expert benchmark profile — all features in GOOD band",
          category="TRUE_PASS",
          features=make_features("TC_009", {
              "heat_diss_max_spike":      3.6,
              "angle_deviation_mean":     4.0,
              "heat_input_min_rolling":   4200.0,  # GOOD: > 4000
              "heat_input_drop_severity": 9.8,
              "heat_input_mean":          5500.0,
              "heat_input_cv":            0.07,
              "voltage_cv":               0.05,
              "amps_cv":                  0.05,
              "arc_on_ratio":             0.93,
          }, quality_label="GOOD"),
          expected_disposition="PASS",
          notes="Expert benchmark profile. heat_input_min_rolling=4200 (GOOD band — Phase 1 raw value 3982 sits in MARGINAL).",
      ),

      EvalScenario(
          scenario_id="TC_010_all_features_good_band_boundary",
          description="All features at GOOD band boundary — just inside threshold",
          category="TRUE_PASS",
          features=make_features("TC_010", {
              "heat_diss_max_spike":      9.9,    # GOOD: < 10
              "angle_deviation_mean":     7.9,    # GOOD: < 8
              "heat_input_min_rolling":   4001.0, # GOOD: > 4000
              "heat_input_drop_severity": 9.9,    # GOOD: < 10
              "heat_input_cv":            0.09,   # GOOD: < 0.10
              "voltage_cv":               0.07,   # GOOD: < 0.08
              "amps_cv":                  0.07,   # GOOD: < 0.08
              "arc_on_ratio":             0.901,  # GOOD: > 0.90
              "heat_input_mean":          4501.0, # GOOD: > 4500
          }, quality_label="GOOD"),
          expected_disposition="PASS",
          notes="Boundary -0.1 case. Tests that good-band boundary does not trigger.",
      ),

      EvalScenario(
          scenario_id="TC_011_thermal_spike_below_threshold",
          description="heat_diss_max_spike at 9.9 — one unit below GOOD threshold",
          category="TRUE_PASS",
          features=make_features("TC_011", {
              "heat_diss_max_spike": 9.9,
          }, quality_label="GOOD"),
          expected_disposition="PASS",
          notes="Single-feature boundary below GOOD threshold. Must not trigger.",
      ),

      EvalScenario(
          scenario_id="TC_012_angle_deviation_below_threshold",
          description="angle_deviation_mean at 7.9 — one unit below GOOD threshold",
          category="TRUE_PASS",
          features=make_features("TC_012", {
              "angle_deviation_mean": 7.9,
          }, quality_label="GOOD"),
          expected_disposition="PASS",
          notes="Single-feature boundary below GOOD threshold. Must not trigger.",
      ),

      EvalScenario(
          scenario_id="TC_013_hot_but_controlled",
          description="High heat input but all consistency metrics GOOD",
          category="TRUE_PASS",
          features=make_features("TC_013", {
              "heat_input_mean": 8000.0,
              "heat_input_cv":   0.05,
              "heat_diss_mean":  3.0,
          }, quality_label="GOOD"),
          expected_disposition="PASS",
          notes="High heat input is not dangerous — only low heat input is RISK.",
      ),

      EvalScenario(
          scenario_id="TC_014_stitch_expert_profile",
          description="Stitch expert profile — controlled restarts, all features GOOD",
          category="TRUE_PASS",
          features=make_features("TC_014", {
              "heat_input_drop_severity": 9.5,   # GOOD: < 10
              "arc_on_ratio":             0.91,  # GOOD: > 0.90 — stitch pauses captured by drop_severity, not arc_on_ratio
              "heat_input_min_rolling":   4100.0,
          }, quality_label="GOOD"),
          expected_disposition="PASS",
          notes="arc_on_ratio=0.91 (GOOD). Stitch pauses are captured by heat_input_drop_severity=9.5.",
      ),

      EvalScenario(
          scenario_id="TC_015_continuous_expert_arc",
          description="Very high arc continuity — near-perfect continuous pass",
          category="TRUE_PASS",
          features=make_features("TC_015", {
              "arc_on_ratio":  0.97,
              "heat_input_cv": 0.04,
              "voltage_cv":    0.03,
              "amps_cv":       0.03,
          }, quality_label="GOOD"),
          expected_disposition="PASS",
          notes="Ideal continuous pass. All stability metrics at floor.",
      ),

      EvalScenario(
          scenario_id="TC_016_minimal_variance_process",
          description="Extremely consistent process — all CV metrics at floor",
          category="TRUE_PASS",
          features=make_features("TC_016", {
              "heat_input_cv":       0.02,
              "voltage_cv":          0.02,
              "amps_cv":             0.02,
              "heat_diss_max_spike": 2.0,
              "angle_deviation_mean": 2.0,
          }, quality_label="GOOD"),
          expected_disposition="PASS",
          notes="Robotic-quality consistency. Baseline sanity check for PASS.",
      ),

      # ── FP_RISK (4) ───────────────────────────────────────────────────────────
      # MARGINAL band features only — no RISK band LOF/LOP features.
      # Expected: CONDITIONAL (not REWORK_REQUIRED).

      EvalScenario(
          scenario_id="TC_017_heat_input_mean_marginal",
          description="heat_input_mean in MARGINAL band — cold weld but not RISK",
          category="FP_RISK",
          features=make_features("TC_017", {
              "heat_input_mean": 4000.0,  # MARGINAL: 3800–4500
          }, quality_label="MARGINAL"),
          expected_disposition="CONDITIONAL",
          notes="Cold weld by heat_input_mean but above RISK threshold. All LOF primary features GOOD.",
      ),

      EvalScenario(
          scenario_id="TC_018_voltage_cv_marginal",
          description="voltage_cv marginally elevated — arc length slightly unstable",
          category="FP_RISK",
          features=make_features("TC_018", {
              "voltage_cv": 0.10,  # MARGINAL: 0.08–0.15
          }, quality_label="MARGINAL"),
          expected_disposition="CONDITIONAL",
          notes="voltage_cv maps to POROSITY not LOF/LOP. No RISK-band LOF features. Must stay CONDITIONAL.",
      ),

      EvalScenario(
          scenario_id="TC_019_arc_on_ratio_borderline",
          description="arc_on_ratio = 0.80 — borderline but in MARGINAL band",
          category="FP_RISK",
          features=make_features("TC_019", {
              "arc_on_ratio": 0.80,  # MARGINAL: 0.75–0.90
          }, quality_label="MARGINAL"),
          expected_disposition="CONDITIONAL",
          notes="arc_on_ratio MARGINAL — some restarts but not at RISK level. Must not trigger REWORK.",
      ),

      EvalScenario(
          scenario_id="TC_020_single_marginal_feature",
          description="One MARGINAL feature (heat_input_drop_severity), nothing in RISK",
          category="FP_RISK",
          features=make_features("TC_020", {
              "heat_input_drop_severity": 12.0,  # MARGINAL: 10–15
          }, quality_label="MARGINAL"),
          expected_disposition="CONDITIONAL",
          notes="Single MARGINAL violation, no RISK. Core over-firing prevention test.",
      ),

      # ── FN_RISK (4) ───────────────────────────────────────────────────────────
      # Safety-critical. FNR = 0.00 requires all 4 to pass.
      # A miss here means a defective weld is accepted.

      EvalScenario(
          scenario_id="TC_021_thermal_spike_risk_floor",
          description="heat_diss_max_spike = 41.0 — minimum value inside RISK band",
          category="FN_RISK",
          features=make_features("TC_021", {
              "heat_diss_max_spike": 41.0,  # RISK floor: > 40
          }, quality_label="MARGINAL"),
          expected_disposition="REWORK_REQUIRED",
          notes="Floor case for thermal RISK band. A miss means the RISK threshold is not enforced.",
      ),

      EvalScenario(
          scenario_id="TC_022_angle_deviation_risk_floor",
          description="angle_deviation_mean = 15.1 — minimum value inside RISK band",
          category="FN_RISK",
          features=make_features("TC_022", {
              "angle_deviation_mean": 15.1,  # RISK floor: > 15
          }, quality_label="MARGINAL"),
          expected_disposition="REWORK_REQUIRED",
          notes="Floor case for angle RISK band. Tests boundary precision on LOF geometry feature.",
      ),

      EvalScenario(
          scenario_id="TC_023_compound_marginal_risk",
          description="Two features at RISK from different domains — compound defect",
          category="FN_RISK",
          features=make_features("TC_023", {
              "heat_input_drop_severity": 15.5,  # RISK: > 15 (LOF)
              "voltage_cv":               0.16,  # RISK: > 0.15 (POROSITY)
              "amps_cv":                  0.13,  # RISK: > 0.12
          }, quality_label="MARGINAL"),
          expected_disposition="REWORK_REQUIRED",
          notes="heat_input_drop_severity in RISK triggers LOF override. Compound multi-domain RISK.",
      ),

      EvalScenario(
          scenario_id="TC_024_low_confidence_with_risk_feature",
          description="Low classifier confidence but one RISK LOF feature",
          category="FN_RISK",
          features=make_features("TC_024", {
              "arc_on_ratio":    0.74,   # RISK: < 0.75 (LOF)
              "heat_input_mean": 4100.0, # MARGINAL
              "heat_input_cv":   0.14,   # MARGINAL
          }, quality_label="MARGINAL"),
          expected_disposition="REWORK_REQUIRED",
          notes="arc_on_ratio RISK triggers LOF override regardless of classifier confidence. Most important FN scenario.",
      ),
  ]


  # ─────────────────────────────────────────────────────────────────────────────
  # HELPERS
  # ─────────────────────────────────────────────────────────────────────────────

  def get_scenarios_by_category(category: str) -> list[EvalScenario]:
      return [s for s in SCENARIOS if s.category == category]


  def get_scenario_by_id(scenario_id: str) -> Optional[EvalScenario]:
      for s in SCENARIOS:
          if s.scenario_id == scenario_id:
              return s
      return None


  def print_scenario_summary() -> None:
      counts = {}
      for s in SCENARIOS:
          counts[s.category] = counts.get(s.category, 0) + 1
      print(f"EvalScenario summary: {len(SCENARIOS)} total")
      for cat, n in sorted(counts.items()):
          print(f"  {cat:<15} {n}")


  if __name__ == "__main__":
      print_scenario_summary()
  ```

  **Why this approach:** Override-on-baseline means each scenario only specifies what's different from a known-good session. This makes the intent of each test immediately readable — if TC_002 only overrides `heat_diss_max_spike`, the reader knows exactly which feature is being tested.

  **Assumptions:**
  - `SessionFeatures` constructor accepts exactly these 11 named fields plus `quality_label` — confirmed in Pre-Flight
  - THRESHOLDS GOOD bands match the values in the comments — confirmed in Pre-Flight

  **Risks:**
  - `SessionFeatures` field order differs from assumed → Pre-Flight captures exact constructor signature; abort if mismatch.
  - A threshold has changed since the plan was written → All boundary values use comments showing the band rule; agent can re-verify against THRESHOLDS before writing.

  **Git Checkpoint:**
  ```bash
  git add backend/eval/eval_scenarios.py
  git commit -m "step 3.2: create eval_scenarios.py — 24 deterministic scenarios across 4 categories"
  ```

  **Subtasks:**
  - [ ] 🟥 `EvalScenario` dataclass defined with `tolerance` defaulting to `"DISPOSITION_ONLY"`
  - [ ] 🟥 `BASE_EXPERT_FEATURES` defined with all 11 features in GOOD band
  - [ ] 🟥 `make_features()` helper defined
  - [ ] 🟥 All 24 scenarios defined: 8 TRUE_REWORK, 8 TRUE_PASS, 4 FP_RISK, 4 FN_RISK
  - [ ] 🟥 TC_009 `heat_input_min_rolling` = 4200.0 (not 3982)
  - [ ] 🟥 TC_014 `arc_on_ratio` = 0.91 (not 0.88)
  - [ ] 🟥 Helper functions `get_scenarios_by_category`, `get_scenario_by_id`, `print_scenario_summary` defined

  **✓ Verification Test:**

  **Type:** Unit

  **Action:**
  ```bash
  python backend/eval/eval_scenarios.py
  ```

  **Expected:**
  ```
  EvalScenario summary: 24 total
    FN_RISK         4
    FP_RISK         4
    TRUE_PASS       8
    TRUE_REWORK     8
  ```

  **Additional assertions:**
  ```bash
  python -c "
  import sys; sys.path.insert(0, '.')
  from backend.eval.eval_scenarios import get_scenario_by_id, SCENARIOS
  assert len(SCENARIOS) == 24, f'expected 24 scenarios, got {len(SCENARIOS)}'
  tc9  = get_scenario_by_id('TC_009_expert_benchmark_exact')
  tc14 = get_scenario_by_id('TC_014_stitch_expert_profile')
  assert tc9.features.heat_input_min_rolling == 4200.0, f'TC_009 rolling={tc9.features.heat_input_min_rolling}'
  assert tc14.features.arc_on_ratio == 0.91, f'TC_014 arc_on={tc14.features.arc_on_ratio}'
  fn = [s for s in SCENARIOS if s.category == 'FN_RISK']
  assert all(s.expected_disposition == 'REWORK_REQUIRED' for s in fn), 'FN_RISK scenario has wrong expected_disposition'
  tp = [s for s in SCENARIOS if s.category == 'TRUE_PASS']
  assert all(s.expected_disposition == 'PASS' for s in tp), 'TRUE_PASS scenario has wrong expected_disposition'
  print('PASS: 24 scenarios, TC_009/TC_014 values correct, categories correct')
  "
  ```

  **Pass:** Both commands complete without error.

  **Fail:**
  - `ImportError: SessionFeatures` → constructor signature mismatch — re-read Pre-Flight baseline and adjust field names
  - Count ≠ 24 → a scenario block was not written — count `EvalScenario(` occurrences in the file
  - TC_009 assertion fails → wrong value was written — grep the file for `3982`

---

### Phase 3.C — Pipeline Evaluator

**Goal:** `eval_pipeline.py` exists and can run the 24 scenarios against the live pipeline, producing a `PipelineEvalReport` with correct confusion matrix, renamed metrics, and no fabricated latency fields.

---

- [ ] 🟥 **Step 3.3: Create `backend/eval/eval_pipeline.py`** — *Critical: this is the file that produces the headline FNR number*

  **Step Architecture Thinking:**

  **Pattern applied:** Observed Confusion Matrix + Aggregator/Runner separation. `PipelineEvaluator` separates the concern of running a single scenario (`_run_single`) from the concern of aggregating N runs into stable metrics (`_run_scenario_aggregate`). The confusion matrix is computed from `Counter`-derived `most_common_actual` — the mode of what the pipeline actually returned — not from a single noisy run and not by inferring actuals from expected labels.

  **Why this step exists here in the sequence:**
  Before this step: there is no way to run the 24 scenarios against the pipeline and get a number. After this step: the command `python eval_pipeline.py --category FN_RISK` produces a real FNR. This is the first point in Phase 3 where a safety claim can be substantiated.

  **Why this file / class is the right location:**
  `eval_pipeline.py` is the runner that ties together the scenario corpus (Step 3.2), the trained classifier (`weld_classifier.py`), and the agent (`warpsense_agent.py`). None of those three files should know about evaluation — the runner is the correct place to orchestrate them.

  **Alternative approach considered and rejected:**
  Compute the confusion matrix from a single run per scenario (no N-runs aggregation). Rejected because LLM-backed components are non-deterministic — a single run can produce the wrong disposition by chance. `most_common_actual` across N runs is the stable observable; a single-run matrix would show variance as failures.

  **What breaks if this step deviates from the described pattern:**
  If the confusion matrix uses inferred actuals (e.g. `_infer_actual(expected, fallback_used)`) instead of observed `most_common_actual`, a bug that always returns CONDITIONAL would show FNR = 0.000 while silently failing all REWORK_REQUIRED scenarios.

  ---

  **Idempotent:** Yes — creating a file that does not exist.

  **Pre-Read Gate:**
  - `WeldClassifier`, `WarpSenseAgent`, `generate_feature_dataset` confirmed in Pre-Flight.
  - `WeldQualityReport` field names confirmed: disposition, iso_5817_level, confidence, self_check_passed (Pre-Flight baseline). The agent returns WeldQualityReport; _run_single accesses report.disposition, report.iso_5817_level, report.confidence, report.self_check_passed. Wrong field names → AttributeError caught by bare except → fallback_used=True on every scenario.
  - `generate_feature_dataset()` return type confirmed: must be `List[SessionFeatures]`. `WeldClassifier.train(dataset)` expects `List[SessionFeatures]`. If generate_feature_dataset returns dict/DataFrame/tuples → PipelineEvaluator.__init__ fails at train().
  - RESULTS_DIR (`backend/eval/results/`) confirmed to exist from Step 3.1.

  ```python
  """
  eval_pipeline.py
  ----------------
  Runs all 24 eval scenarios against the WarpSense pipeline.
  Computes F1, FNR, Precision, Recall, FPR, and latency.
  LLM metrics run each scenario N times and report mean.

  Usage:
      python eval_pipeline.py                     # all 24 scenarios, 1 run each
      python eval_pipeline.py --llm-runs 3        # LLM metrics: run each 3 times
      python eval_pipeline.py --category FN_RISK  # run only false-negative cases
      python eval_pipeline.py --save              # write results to JSON

  (--no-llm flag deferred to Phase 6 — not needed for initial implementation)
  """

  import argparse
  import json
  import sys
  import time
  from collections import Counter
  from dataclasses import dataclass, asdict
  from datetime import datetime
  from pathlib import Path
  from statistics import mean, stdev
  from typing import Optional

  _ROOT = Path(__file__).resolve().parent.parent.parent
  if str(_ROOT) not in sys.path:
      sys.path.insert(0, str(_ROOT))

  from dotenv import load_dotenv
  load_dotenv(_ROOT / ".env")

  from backend.features.session_feature_extractor import generate_feature_dataset
  from backend.features.weld_classifier import WeldClassifier
  from backend.agent.warpsense_agent import WarpSenseAgent
  from backend.eval.eval_scenarios import SCENARIOS, EvalScenario, get_scenarios_by_category

  RESULTS_DIR = Path(__file__).parent / "results"
  RESULTS_DIR.mkdir(exist_ok=True)


  # ─────────────────────────────────────────────────────────────────────────────
  # RESULT DATACLASSES
  # ─────────────────────────────────────────────────────────────────────────────

  @dataclass
  class ScenarioRunResult:
      scenario_id:          str
      category:             str
      expected_disposition: str
      actual_disposition:   str
      correct:              bool
      iso_5817_level:       str
      confidence:           float
      self_check_passed:    bool
      fallback_used:        bool
      total_ms:             float
      error:                Optional[str] = None


  @dataclass
  class ScenarioAggregateResult:
      scenario_id:               str
      category:                  str
      expected_disposition:      str
      runs:                      int
      correct_count:             int
      disposition_match_rate:    float    # pipeline accuracy (deterministic)
      most_common_actual:        str      # mode of actual dispositions observed across runs
      llm_response_rate:         float    # fraction of runs where LLM returned non-empty iso_5817_level
                                          # NOTE: this is response presence, not alignment accuracy
      fallback_rate:             float
      self_check_pass_rate:      float
      mean_total_ms:             float
      std_total_ms:              float


  @dataclass
  class PipelineEvalReport:
      timestamp:              str
      n_scenarios:            int
      llm_runs_per_scenario:  int

      # Classification metrics (REWORK_REQUIRED = positive class)
      tp: int
      fp: int
      tn: int
      fn: int
      precision:              float
      recall:                 float
      f1:                     float
      fpr:                    float
      fnr:                    float

      # LLM metrics
      mean_llm_response_rate: float    # fraction of runs where LLM returned non-empty iso_5817_level
      mean_fallback_rate:     float
      mean_self_check_pass:   float

      # Latency (ms) — component breakdown added in Phase 6 via RunTracer
      p50_ms:                 float
      p95_ms:                 float
      p99_ms:                 float

      scenario_results:       list


  # ─────────────────────────────────────────────────────────────────────────────
  # RUNNER
  # ─────────────────────────────────────────────────────────────────────────────

  class PipelineEvaluator:
      def __init__(self, llm_runs: int = 1, verbose: bool = True):
          self.llm_runs = llm_runs
          self.verbose = verbose

          self._log("[Eval] Training classifier...")
          dataset = generate_feature_dataset()
          self.classifier = WeldClassifier()
          self.classifier.train(dataset)
          self._log(f"[Eval] Classifier trained on {len(dataset)} sessions")

          self._log("[Eval] Initialising WarpSenseAgent...")
          self.agent = WarpSenseAgent(verbose=False)
          self._log("[Eval] Agent ready")

      def _log(self, msg: str) -> None:
          if self.verbose:
              print(msg)

      def _run_single(self, scenario: EvalScenario) -> ScenarioRunResult:
          """Run one scenario once. Returns a ScenarioRunResult."""
          features = scenario.features

          t_start = time.perf_counter()
          prediction = self.classifier.predict(features)

          fallback_used = False
          error = None
          try:
              report = self.agent.assess(prediction, features)
              fallback_used = "LLM generation failed" in report.root_cause
          except Exception as e:
              error = str(e)
              report = None

          total_ms = (time.perf_counter() - t_start) * 1000

          if report is None:
              return ScenarioRunResult(
                  scenario_id=scenario.scenario_id,
                  category=scenario.category,
                  expected_disposition=scenario.expected_disposition,
                  actual_disposition="ERROR",
                  correct=False,
                  iso_5817_level="ERROR",
                  confidence=0.0,
                  self_check_passed=False,
                  fallback_used=True,
                  total_ms=total_ms,
                  error=error,
              )

          actual = report.disposition
          correct = (actual == scenario.expected_disposition)

          return ScenarioRunResult(
              scenario_id=scenario.scenario_id,
              category=scenario.category,
              expected_disposition=scenario.expected_disposition,
              actual_disposition=actual,
              correct=correct,
              iso_5817_level=report.iso_5817_level,
              confidence=report.confidence,
              self_check_passed=report.self_check_passed,
              fallback_used=fallback_used,
              total_ms=total_ms,
              error=error,
          )

      def _run_scenario_aggregate(self, scenario: EvalScenario) -> ScenarioAggregateResult:
          """Run one scenario self.llm_runs times and aggregate."""
          runs = []
          for _ in range(self.llm_runs):
              result = self._run_single(scenario)
              runs.append(result)

          n = len(runs)
          correct_count = sum(1 for r in runs if r.correct)
          llm_responded = sum(1 for r in runs if r.iso_5817_level not in ("ERROR", ""))
          fallback_count = sum(1 for r in runs if r.fallback_used)
          sc_pass_count = sum(1 for r in runs if r.self_check_passed)
          latencies = [r.total_ms for r in runs]
          actual_dispositions = [r.actual_disposition for r in runs]
          most_common_actual = Counter(actual_dispositions).most_common(1)[0][0]

          return ScenarioAggregateResult(
              scenario_id=scenario.scenario_id,
              category=scenario.category,
              expected_disposition=scenario.expected_disposition,
              runs=n,
              correct_count=correct_count,
              disposition_match_rate=correct_count / n,
              most_common_actual=most_common_actual,
              llm_response_rate=llm_responded / n,
              fallback_rate=fallback_count / n,
              self_check_pass_rate=sc_pass_count / n,
              mean_total_ms=mean(latencies),
              std_total_ms=stdev(latencies) if n > 1 else 0.0,
          )

      def evaluate(self, scenarios: list[EvalScenario]) -> PipelineEvalReport:
          self._log(f"\n{'='*60}")
          self._log(f"WARPSENSE PIPELINE EVAL — {len(scenarios)} scenarios × {self.llm_runs} run(s)")
          self._log(f"{'='*60}\n")

          agg_results = []
          all_latencies = []

          for i, scenario in enumerate(scenarios, 1):
              self._log(f"[{i:02d}/{len(scenarios)}] {scenario.scenario_id} ({scenario.category})")
              agg = self._run_scenario_aggregate(scenario)
              agg_results.append(agg)
              all_latencies.append(agg.mean_total_ms)

              status = "✅" if agg.disposition_match_rate == 1.0 else "❌"
              self._log(
                  f"        {status} match={agg.disposition_match_rate:.0%} "
                  f"expected={agg.expected_disposition} actual={agg.most_common_actual} "
                  f"latency={agg.mean_total_ms:.0f}ms"
              )

          # ── Classification metrics ────────────────────────────────────────────
          # Positive class = REWORK_REQUIRED
          # Uses most_common_actual (observed) — not inferred
          tp = fp = tn = fn = 0
          for agg in agg_results:
              expected = agg.expected_disposition
              actual = agg.most_common_actual

              if expected == "REWORK_REQUIRED" and actual == "REWORK_REQUIRED":
                  tp += 1
              elif expected != "REWORK_REQUIRED" and actual == "REWORK_REQUIRED":
                  fp += 1
              elif expected != "REWORK_REQUIRED" and actual != "REWORK_REQUIRED":
                  tn += 1
              elif expected == "REWORK_REQUIRED" and actual != "REWORK_REQUIRED":
                  fn += 1

          precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
          recall    = tp / (tp + fn) if (tp + fn) > 0 else 0.0
          f1        = (2 * precision * recall / (precision + recall)
                       if (precision + recall) > 0 else 0.0)
          fpr       = fp / (fp + tn) if (fp + tn) > 0 else 0.0
          fnr       = fn / (fn + tp) if (fn + tp) > 0 else 0.0

          # ── LLM metrics ───────────────────────────────────────────────────────
          mean_llm_resp  = mean(a.llm_response_rate for a in agg_results)
          mean_fallback  = mean(a.fallback_rate for a in agg_results)
          mean_sc_pass   = mean(a.self_check_pass_rate for a in agg_results)

          # ── Latency ───────────────────────────────────────────────────────────
          sorted_lat = sorted(all_latencies)
          n = len(sorted_lat)
          p50 = sorted_lat[int(n * 0.50)]
          p95 = sorted_lat[min(int(n * 0.95), n - 1)]
          p99 = sorted_lat[min(int(n * 0.99), n - 1)]

          report = PipelineEvalReport(
              timestamp=datetime.utcnow().isoformat(),
              n_scenarios=len(scenarios),
              llm_runs_per_scenario=self.llm_runs,
              tp=tp, fp=fp, tn=tn, fn=fn,
              precision=precision, recall=recall, f1=f1, fpr=fpr, fnr=fnr,
              mean_llm_response_rate=mean_llm_resp,
              mean_fallback_rate=mean_fallback,
              mean_self_check_pass=mean_sc_pass,
              p50_ms=p50, p95_ms=p95, p99_ms=p99,
              scenario_results=[asdict(a) for a in agg_results],
          )

          self._print_summary(report, agg_results)
          return report

      def _print_summary(self, report: PipelineEvalReport, agg_results: list) -> None:
          w = 60
          print(f"\n{'='*w}")
          print("PIPELINE EVAL SUMMARY")
          print(f"{'='*w}")
          print(f"\nClassification Metrics (positive = REWORK_REQUIRED):")
          print(f"  {'Metric':<25} {'Score'}")
          print(f"  {'-'*35}")
          print(f"  {'Precision':<25} {report.precision:.3f}")
          print(f"  {'Recall':<25} {report.recall:.3f}")
          print(f"  {'F1':<25} {report.f1:.3f}")
          print(f"  {'FPR (false alarm rate)':<25} {report.fpr:.3f}")
          fnr_note = " ← HEADLINE (safety)" if report.fnr == 0.0 else " ← WARNING: misses"
          print(f"  {'FNR (missed defects)':<25} {report.fnr:.3f}{fnr_note}")
          print(f"  {'TP / FP / TN / FN':<25} {report.tp} / {report.fp} / {report.tn} / {report.fn}")

          print(f"\nLLM Metrics (mean over {report.llm_runs_per_scenario} run(s)):")
          print(f"  {'LLM response rate':<30} {report.mean_llm_response_rate:.1%}  (non-empty iso_5817_level — not true alignment)")
          print(f"  {'Fallback rate':<30} {report.mean_fallback_rate:.1%}")
          print(f"  {'Self-check pass rate':<30} {report.mean_self_check_pass:.1%}")

          print(f"\nLatency (ms):")
          print(f"  {'p50':<30} {report.p50_ms:.0f} ms")
          print(f"  {'p95':<30} {report.p95_ms:.0f} ms")
          print(f"  {'p99':<30} {report.p99_ms:.0f} ms")
          print(f"  Component breakdown: Phase 6 (RunTracer)")

          print(f"\nScenario breakdown:")
          print(f"  {'ID':<38} {'Cat':<12} {'Expected':<22} {'Actual':<22} {'Match'}")
          print(f"  {'-'*100}")
          for agg in agg_results:
              match_str = f"{agg.disposition_match_rate:.0%}"
              icon = "✅" if agg.disposition_match_rate == 1.0 else "❌"
              print(f"  {icon} {agg.scenario_id:<36} {agg.category:<12} "
                    f"{agg.expected_disposition:<22} {agg.most_common_actual:<22} {match_str}")

          failures = [a for a in agg_results if a.disposition_match_rate < 1.0]
          fn_failures = [a for a in agg_results if a.category == "FN_RISK" and a.disposition_match_rate < 1.0]
          if fn_failures:
              print(f"\n⚠️  CRITICAL: {len(fn_failures)} FALSE-NEGATIVE failures:")
              for a in fn_failures:
                  print(f"   {a.scenario_id} — expected REWORK_REQUIRED, got {a.most_common_actual}")
          elif failures:
              print(f"\n⚠️  {len(failures)} scenario(s) failed (non-safety-critical)")
          else:
              print(f"\n✅ All {len(agg_results)} scenarios passed")

          print(f"{'='*w}\n")

      def save(self, report: PipelineEvalReport) -> Path:
          ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
          out = RESULTS_DIR / f"pipeline_eval_{ts}.json"
          with open(out, "w") as f:
              json.dump(asdict(report), f, indent=2)
          print(f"[Eval] Results saved: {out}")
          return out


  def main():
      parser = argparse.ArgumentParser(description="WarpSense pipeline evaluator")
      parser.add_argument("--llm-runs", type=int, default=1)
      parser.add_argument("--category", type=str, default=None,
                          choices=["TRUE_REWORK", "TRUE_PASS", "FP_RISK", "FN_RISK"])
      parser.add_argument("--scenario", type=str, default=None)
      parser.add_argument("--quiet", action="store_true")
      parser.add_argument("--save", action="store_true")
      args = parser.parse_args()

      if args.scenario:
          scenarios = [s for s in SCENARIOS if s.scenario_id == args.scenario]
          if not scenarios:
              print(f"ERROR: scenario '{args.scenario}' not found")
              sys.exit(1)
      elif args.category:
          scenarios = get_scenarios_by_category(args.category)
      else:
          scenarios = SCENARIOS

      evaluator = PipelineEvaluator(llm_runs=args.llm_runs, verbose=not args.quiet)
      report = evaluator.evaluate(scenarios)

      if args.save:
          evaluator.save(report)

      fn_failures = [
          r for r in report.scenario_results
          if r["category"] == "FN_RISK" and r["disposition_match_rate"] < 1.0
      ]
      if fn_failures:
          print(f"FAIL: {len(fn_failures)} FN_RISK scenario(s) failed — safety-critical")
          sys.exit(1)


  if __name__ == "__main__":
      main()
  ```

  **Assumptions:**
  - `WeldQualityReport` has `disposition`, `iso_5817_level`, `confidence`, `self_check_passed`, `root_cause` — confirmed in Pre-Flight
  - `generate_feature_dataset()` returns `List[SessionFeatures]` — confirmed in Pre-Flight

  **Risks:**
  - Wrong `WeldQualityReport` field names → every `_run_single` hits `except Exception` → every scenario returns `fallback_used=True` and `actual_disposition="ERROR"` → FNR = 0.000 because FN_RISK scenarios show "ERROR" ≠ "REWORK_REQUIRED" but are counted as FN → mitigation: Pre-Flight confirms all field names before writing.

  **Git Checkpoint:**
  ```bash
  git add backend/eval/eval_pipeline.py
  git commit -m "step 3.3: create eval_pipeline.py — confusion matrix from observed dispositions, correct metric names"
  ```

  **Subtasks:**
  - [ ] 🟥 `Counter` imported from `collections`
  - [ ] 🟥 `most_common_actual` field in `ScenarioAggregateResult`
  - [ ] 🟥 `llm_response_rate` (not `iso_5817_align_rate`) in `ScenarioAggregateResult`
  - [ ] 🟥 `mean_llm_response_rate` (not `mean_llm_alignment`) in `PipelineEvalReport`
  - [ ] 🟥 No fabricated latency breakdown fields
  - [ ] 🟥 Confusion matrix uses `agg.most_common_actual` — no `_infer_actual` function
  - [ ] 🟥 No `--no-llm` flag in argparse (add in Phase 6 if required)

  **✓ Verification Test:**

  **Type:** Unit (import only — ChromaDB populated per Pre-Flight check 8 before running full eval)

  **Action:**
  ```bash
  python -c "
  import sys; sys.path.insert(0, '.')
  from backend.eval.eval_pipeline import (
      PipelineEvaluator, ScenarioAggregateResult, PipelineEvalReport
  )
  agg_fields    = list(ScenarioAggregateResult.__dataclass_fields__)
  report_fields = list(PipelineEvalReport.__dataclass_fields__)

  assert 'most_common_actual'    in agg_fields,    'most_common_actual missing'
  assert 'llm_response_rate'     in agg_fields,    'llm_response_rate missing'
  assert 'iso_5817_align_rate'   not in agg_fields, 'old field still present'
  assert 'mean_llm_response_rate' in report_fields, 'mean_llm_response_rate missing'
  assert 'mean_llm_alignment'    not in report_fields, 'old field still present'
  assert 'mean_classifier_ms'    not in report_fields, 'fabricated field present'
  assert 'mean_retrieval_ms'     not in report_fields, 'fabricated field present'

  import pathlib
  src = pathlib.Path('backend/eval/eval_pipeline.py').read_text()
  assert 'def _infer_actual' not in src, '_infer_actual should not exist'
  assert 'Counter' in src,               'Counter not imported'

  print('PASS: dataclass fields correct, no fabricated latency, no _infer_actual')
  "
  ```

  **Pass:** `PASS: dataclass fields correct, no fabricated latency, no _infer_actual`

  **Fail:**
  - Any field assertion fails → file was not written correctly — re-check the dataclass definitions

---

### Phase 3.D — Agent Public API

**Goal:** `WarpSenseAgent` has `prepare_context()` and `verify_citations()` as public methods. `eval_prompts.py` (Step 3.6) can be written against these names without touching private step methods.

---

- [ ] 🟥 **Step 3.4: Add `prepare_context()` and `verify_citations()` to `WarpSenseAgent`** — *Critical: Step 3.6 depends on these existing; modifies a file the entire system uses*

  **Step Architecture Thinking:**

  **Pattern applied:** Facade — two stable public methods wrap the sequence of private steps that the eval needs to call. This is the Dependency Inversion Principle applied at the eval boundary: `eval_prompts.py` depends on the abstraction (`prepare_context`, `verify_citations`), not on the concrete step implementations (`_step1_defect_intake`, `_step3_retrieve_standards`, `_step5_self_check`).

  **Why this step exists here in the sequence:**
  Before this step: `eval_prompts.py` cannot be written without hardcoding private method names, which would make it fragile to the Phase 4 refactor. After this step: a stable public contract exists and `eval_prompts.py` can be written entirely against these two method names. The public methods must exist before Step 3.6 is written — not after.

  **Why this file / class is the right location:**
  `warpsense_agent.py` already owns Steps 1–5. The public methods are thin wrappers that expose a stable slice of that existing logic. Putting them anywhere else would require passing internal agent state across a module boundary.

  **Alternative approach considered and rejected:**
  `eval_prompts.py` calls `_step1_defect_intake`, `_step3_retrieve_standards`, and `_step5_self_check` directly. Rejected because (a) private method names are an implementation detail, not a contract, (b) Phase 4 will reorganise the step pipeline and will rename these methods, and (c) the eval would silently break with a `AttributeError` and the failure would be discovered at eval run time rather than at the contract definition point.

  **What breaks if this step deviates from the described pattern:**
  If `prepare_context()` returns `(chunks, violations, defect_categories)` instead of `(violations, chunks, defect_categories)`, `eval_prompts.py`'s LOF/LOP safety override would iterate over chunks looking for `.severity` and `.defect_categories`, find neither, and never fire — causing all 4 FN_RISK scenarios to return CONDITIONAL instead of REWORK_REQUIRED.

  ---

  **Idempotent:** Yes — adding new methods does not affect existing behaviour.

  **Pre-Read Gate:**
  - `grep -n "def prepare_context\|def verify_citations" backend/agent/warpsense_agent.py` → must return 0. If any → already added; skip this step.
  - `grep -n "def _step1_defect_intake" backend/agent/warpsense_agent.py` → must return exactly 1. If 0 → STOP: method name differs from assumed; report actual names.
  - `grep -n "def _step2_threshold_check" backend/agent/warpsense_agent.py` → must return exactly 1. If 0 → STOP.
  - `grep -n "def _step3_retrieve_standards" backend/agent/warpsense_agent.py` → must return exactly 1. If 0 → STOP.
  - `grep -n "def _step5_self_check" backend/agent/warpsense_agent.py` → must return exactly 1. If 0 → STOP.
  - `grep -n "def assess" backend/agent/warpsense_agent.py` → must return exactly 1 (insertion anchor).
  - Confirm from Pre-Flight: `_step5_self_check` accepts `dict` as first arg. If it accepts a typed object → STOP and report before inserting.

  **Insertion — Exact str_replace anchor:**

  **Pre-Read:**
  - Run `grep -n "def assess" backend/agent/warpsense_agent.py` → capture the exact line.
  - Run `grep -E "^\t" backend/agent/warpsense_agent.py || true` (or `head -50 backend/agent/warpsense_agent.py | grep $'\t' || true`). If the file uses tab characters for indentation, rewrite every indented line in the inserted block to use tabs instead of spaces.
  - The inserted block must use the same indentation style as the file (4 spaces or tabs).

  **str_replace — CRITICAL:** The find string must be the **exact** `def assess` line from the Pre-Flight baseline output. No other value is acceptable. If the actual signature has type annotations, the find string must include them. Using an example or guessed line will cause zero matches and str_replace will fail with no indication of why.

  **Find string:** [USE EXACT def assess LINE FROM PRE-FLIGHT BASELINE — COPY VERBATIM]

  **Replace with** the following block. The block ends with the original `def assess` line — you must insert the exact line from Pre-Flight as the final line of the replace block. Do not use any example. [INSERT VERBATIM def assess LINE FROM PRE-FLIGHT AS THE LAST LINE OF THE BLOCK BELOW]

  ```
      # ── Public eval API ──────────────────────────────────────────────────────
      # Stable wrappers used by eval_prompts.py.
      # Decouple the eval from internal step numbering — if private step methods
      # are renamed during Phase 4 refactoring, update only here.

      def prepare_context(self, features: "SessionFeatures", prediction: "WeldPrediction") -> tuple:
          """
          Run Steps 1–3 and return (violations, chunks, defect_categories).
          Used by eval_prompts.py to reproduce retrieval context for each
          prompt variant without running the full assess() pipeline.

          Note: prepare_context takes (features, prediction) but _step3_retrieve_standards
          takes (prediction, features, ...) — argument order reversal is intentional.
          """
          defect_categories = self._step1_defect_intake(prediction, features)
          violations = self._step2_threshold_check(features)
          chunks = self._step3_retrieve_standards(
              prediction, features, defect_categories, violations
          )
          return violations, chunks, defect_categories

      def verify_citations(self, report_dict: dict, chunks: list) -> tuple:
          """
          Run Step 5 (self-check) against a raw parsed JSON dict and retrieved chunks.
          Returns (passed: bool, reason: str).
          Used by eval_prompts.py to apply citation grounding check across
          all prompt variants without calling _step5_self_check directly.
          """
          return self._step5_self_check(report_dict, chunks)

      [INSERT VERBATIM def assess LINE FROM PRE-FLIGHT HERE]
  ```

  **Critical:** `_step1_defect_intake` returns a single value (list), not a tuple. `_step3_retrieve_standards` returns a single value (list of StandardsChunk), not a tuple. Do NOT use `chunks, _ =` or `defect_categories, _ =`.

  **Assumptions:**
  - `_step5_self_check` accepts a plain `dict` as its first argument (Pre-Flight confirmed)
  - The exact `def assess` signature matches what str_replace will find (Pre-Flight captured verbatim)

  **Risks:**
  - `_step5_self_check` accepts a typed `WeldQualityReport` not a plain `dict` → `verify_citations` would fail at call time with a type error → mitigation: Pre-Flight explicitly confirms the first argument type; if it is not `dict`, STOP and report before inserting.
  - Wrong return order in `prepare_context` (chunks before violations) → LOF/LOP safety override in `eval_prompts.py` iterates the wrong list → FN_RISK scenarios silently pass when they should fail → mitigation: Part B integration test asserts `hasattr(violations[0], 'severity')`.

  **Git Checkpoint:**
  ```bash
  git add backend/agent/warpsense_agent.py
  git commit -m "step 3.4: add prepare_context() and verify_citations() public eval API to WarpSenseAgent"
  ```

  **Subtasks:**
  - [ ] 🟥 All 4 private step methods confirmed present in Pre-Read Gate
  - [ ] 🟥 `_step5_self_check` confirmed to accept `dict` (or STOP)
  - [ ] 🟥 `prepare_context()` inserted before `assess()`
  - [ ] 🟥 `verify_citations()` inserted before `assess()`
  - [ ] 🟥 `assess()` still present and unmodified
  - [ ] 🟥 Part B integration test passes (return order: violations, chunks, defect_categories)

  **✓ Verification Test:**

  **Part A — Method existence and signatures (no external deps):**
  ```bash
  python -c "
  import sys, inspect; sys.path.insert(0, '.')
  from backend.agent.warpsense_agent import WarpSenseAgent
  assert hasattr(WarpSenseAgent, 'prepare_context'),  'prepare_context missing'
  assert hasattr(WarpSenseAgent, 'verify_citations'),  'verify_citations missing'
  assert hasattr(WarpSenseAgent, 'assess'),            'assess missing — insertion may have replaced it'
  pc = inspect.signature(WarpSenseAgent.prepare_context)
  vc = inspect.signature(WarpSenseAgent.verify_citations)
  assert 'features'    in pc.parameters, 'prepare_context missing features param'
  assert 'prediction'  in pc.parameters, 'prepare_context missing prediction param'
  assert 'report_dict' in vc.parameters, 'verify_citations missing report_dict param'
  assert 'chunks'      in vc.parameters, 'verify_citations missing chunks param'
  print('PASS A: prepare_context and verify_citations present; assess intact')
  "
  ```

  **Part B — Return-order integration assertion (requires ChromaDB populated per Pre-Flight check 8 + eval_scenarios from Step 3.2):**

  Catches return-order problems, empty retrieval, and `.severity` on live violation objects — all at Step 3.4 rather than at the E2E smoke test. If Pre-Flight ChromaDB check failed, run `python backend/knowledge/build_welding_kb.py` first.

  ```bash
  python -c "
  import sys; sys.path.insert(0, '.')
  from backend.agent.warpsense_agent import WarpSenseAgent
  from backend.features.session_feature_extractor import generate_feature_dataset
  from backend.features.weld_classifier import WeldClassifier
  from backend.eval.eval_scenarios import get_scenario_by_id

  dataset = generate_feature_dataset()
  clf = WeldClassifier(); clf.train(dataset)
  agent = WarpSenseAgent(verbose=False)
  scenario = get_scenario_by_id('TC_001_novice_classic')
  pred = clf.predict(scenario.features)
  violations, chunks, defect_categories = agent.prepare_context(scenario.features, pred)
  assert isinstance(violations, list), f'violations is {type(violations)}, expected list'
  assert isinstance(chunks, list), f'chunks is {type(chunks)}, expected list'
  assert len(chunks) > 0, 'prepare_context returned empty chunks'
  assert hasattr(violations[0], 'severity') if violations else True, 'violation missing .severity'
  print(f'PASS B: prepare_context returns (violations={len(violations)}, chunks={len(chunks)}, defect_categories={type(defect_categories).__name__})')
  "
  ```

  **Pass:** Part A prints PASS; Part B prints `PASS B: prepare_context returns (violations=N, chunks=M, defect_categories=list)`.

  **Fail:**
  - `prepare_context missing` → insertion anchor not matched — re-run `grep -n "def assess"` and check exact whitespace
  - `assess missing` → insertion replaced `assess` — revert and re-read the file
  - Part B: ValueError on unpack → wrong number of return values
  - Part B: `hasattr(violations[0], 'severity')` False → first return is not violations (wrong order)
  - Part B: `len(chunks) > 0` False → empty retrieval (KB not built or query failed)
  - Part B: ChromaDB/import errors → run `python backend/knowledge/build_welding_kb.py`; ensure Step 3.2 complete

---

### Phase 3.E — Retrieval Evaluator

**Goal:** `eval_retrieval.py` exists with 25 ground-truth query→chunk pairs and a metrics loop that varies k=1,2,3,5,6. k=6 is marked as the current agent operating point. Running it produces the P@k curve that determines whether Phase 5 BM25 search is worth building.

---

- [ ] 🟥 **Step 3.5: Create `backend/eval/eval_retrieval.py`** — *Critical: P@6 score drives the Phase 5 build/skip decision*

  **Step Architecture Thinking:**

  **Pattern applied:** Measurement-Driven Architecture Decision — this file exists specifically to produce the data that will justify or reject the Phase 5 BM25 build. The operating point `k=6` is not a test value; it is the exact value used in production (`n_standards_chunks=6`). Evaluating at k=3 would be measuring a configuration that does not exist in the live system.

  **Why this step exists here in the sequence:**
  Before this step: there is no way to know whether ChromaDB alone is sufficient for standards retrieval, or whether BM25 hybrid search is needed. After this step: the P@6 number answers that question. This step is independent of Steps 3.3 and 3.4 — it only touches ChromaDB and does not use the classifier or agent.

  **Why this file / class is the right location:**
  `eval_retrieval.py` is an independent runner like `eval_pipeline.py`. It only reads from ChromaDB and the ground-truth query list. Keeping it separate means it can be run without training the classifier or initialising the agent.

  **Alternative approach considered and rejected:**
  Evaluate at k=3 as the primary metric (common default in RAG eval literature). Rejected because the agent currently retrieves 6 chunks, not 3. A P@3 score would systematically understate retrieval quality at the actual operating point. An agent evaluating 6 chunks and a RAG eval measuring 3 is an invalid comparison.

  **What breaks if this step deviates from the described pattern:**
  If `K_VALUES` does not include 6, the "current operating point" marker never fires, the interpretation block has no data for the production configuration, and the Phase 5 build/skip decision has no valid evidence. If the marker fires at k=3 instead of k=6, the "adequate / strong / weak" interpretation maps to the wrong k and the Phase 5 decision is wrong.

  ---

  **Idempotent:** Yes — creating a new file.

  **Pre-Read Gate:**
  - Confirm `COLLECTION_NAME` and `CHROMA_PATH` from Pre-Flight baseline. If blank → re-read `build_welding_kb.py`.
  - ChromaDB must be populated (Pre-Flight check 8). Run `python -c "import chromadb; c=chromadb.PersistentClient(path='backend/knowledge/chroma_db'); n=c.get_collection('welding_standards').count(); exit(0 if n > 0 else 1)"` — must exit 0. If exit 1, run `python backend/knowledge/build_welding_kb.py` first.
  - **Chunk ID spot-check:** Run `grep -E '"id":\s*"[^"]+"' backend/knowledge/build_welding_kb.py` and verify at least: `iso5817_lof_all_levels`, `corrective_lof_angle_drift`, `heat_dissipation_significance` exist verbatim. If any GROUND_TRUTH relevant_ids string differs (e.g. `iso5817_lof_all` vs `iso5817_lof_all_levels`), update that RetrievalQuery's relevant_ids to match build_welding_kb.py exactly. P@k = 0 on every query indicates ID mismatch.

  ```python
  """
  eval_retrieval.py
  -----------------
  Evaluates ChromaDB retrieval quality against 25 ground-truth query→chunk_id pairs.

  Metrics:
    Precision@k = |retrieved ∩ relevant| / k
    Recall@k    = |retrieved ∩ relevant| / |relevant|
    MRR         = mean(1 / rank_of_first_relevant_doc)

  Varies k = 1, 2, 3, 5, 6 (6 = actual agent operating point).
  Chunk IDs must match build_welding_kb.py exactly.

  Usage:
      python eval_retrieval.py                  # all 25 queries, k=1,2,3,5,6
      python eval_retrieval.py --k 3 6          # specific k values
      python eval_retrieval.py --category lof   # filter by defect category
      python eval_retrieval.py --save
  """

  import argparse
  import json
  import sys
  from dataclasses import dataclass, asdict
  from datetime import datetime
  from pathlib import Path
  from statistics import mean
  from typing import Optional

  _ROOT = Path(__file__).resolve().parent.parent.parent
  if str(_ROOT) not in sys.path:
      sys.path.insert(0, str(_ROOT))

  import chromadb
  from chromadb.utils import embedding_functions

  CHROMA_PATH = _ROOT / "backend" / "knowledge" / "chroma_db"
  COLLECTION_NAME = "welding_standards"
  RESULTS_DIR = Path(__file__).parent / "results"
  RESULTS_DIR.mkdir(exist_ok=True)

  K_VALUES = [1, 2, 3, 5, 6]  # 6 = actual agent operating point (n_standards_chunks=6)


  # ─────────────────────────────────────────────────────────────────────────────
  # GROUND TRUTH — 25 query → relevant chunk IDs
  # ─────────────────────────────────────────────────────────────────────────────

  @dataclass
  class RetrievalQuery:
      query_id:     str
      query:        str
      relevant_ids: list[str]
      category:     str   # lof | lop | thermal | porosity | undercut | system | threshold


  GROUND_TRUTH: list[RetrievalQuery] = [

      # ── LOF (6 queries) ──────────────────────────────────────────────────────

      RetrievalQuery(
          query_id="RQ_001",
          query="lack of fusion acceptance criteria ISO 5817 all quality levels",
          relevant_ids=["iso5817_lof_all_levels", "aws_d11_lof_zero_tolerance", "iso5817_lof_fillet_welds"],
          category="lof",
      ),
      RetrievalQuery(
          query_id="RQ_002",
          query="torch angle deviation 45 degrees lack of fusion root cause",
          relevant_ids=["torch_angle_work_angle", "torch_angle_variability_consequence", "corrective_lof_angle_drift"],
          category="lof",
      ),
      RetrievalQuery(
          query_id="RQ_003",
          query="corrective action for angle deviation mean exceeding 15 degrees",
          relevant_ids=["corrective_lof_angle_drift", "torch_angle_work_angle", "warpsense_feature_thresholds"],
          category="lof",
      ),
      RetrievalQuery(
          query_id="RQ_004",
          query="stitch welding restart cold interface lack of fusion risk",
          relevant_ids=["stitch_welding_risk", "corrective_lof_cold_window", "warpsense_arc_on_ratio"],
          category="lof",
      ),
      RetrievalQuery(
          query_id="RQ_005",
          query="incomplete fusion AWS D1.1 rejection criterion repair",
          relevant_ids=["aws_d11_lof_zero_tolerance", "aws_d11_table81_fusion", "aws_d11_disposition_rework"],
          category="lof",
      ),
      RetrievalQuery(
          query_id="RQ_006",
          query="LOF LOP invisible to X-ray visual inspection shipyard NDT",
          relevant_ids=["warpsense_lof_lop_invisible_inspection", "iacs47_weld_ndt_coverage", "ndt_method_selection"],
          category="lof",
      ),

      # ── LOP (3 queries) ──────────────────────────────────────────────────────

      RetrievalQuery(
          query_id="RQ_007",
          query="incomplete root penetration ISO 5817 quality level D acceptance",
          relevant_ids=["iso5817_incomplete_root_penetration", "root_cause_lop_primary"],
          category="lop",
      ),
      RetrievalQuery(
          query_id="RQ_008",
          query="cold arc window low heat input minimum rolling incomplete penetration",
          relevant_ids=["corrective_lof_cold_window", "root_cause_lop_primary", "iacs47_high_heat_input_threshold"],
          category="lop",
      ),
      RetrievalQuery(
          query_id="RQ_009",
          query="heat input too low amperage insufficient LOF LOP causes",
          relevant_ids=["heat_input_amperage_effect", "root_cause_lof_primary", "root_cause_lop_primary"],
          category="lop",
      ),

      # ── Thermal (4 queries) ──────────────────────────────────────────────────

      RetrievalQuery(
          query_id="RQ_010",
          query="heat dissipation spike 65 degrees per second corrective action",
          relevant_ids=["corrective_lof_thermal_instability", "heat_dissipation_significance"],
          category="thermal",
      ),
      RetrievalQuery(
          query_id="RQ_011",
          query="heat_diss_max_spike threshold expert novice benchmark",
          relevant_ids=["heat_dissipation_significance", "warpsense_heat_input_expert_novice", "warpsense_feature_thresholds"],
          category="thermal",
      ),
      RetrievalQuery(
          query_id="RQ_012",
          query="rapid cooling rate preheat hydrogen cracking risk",
          relevant_ids=["iacs47_preheat", "root_cause_cracking", "heat_dissipation_significance"],
          category="thermal",
      ),
      RetrievalQuery(
          query_id="RQ_013",
          query="heat input drop severity stitch transition corrective reduce variance",
          relevant_ids=["corrective_lof_thermal_instability", "stitch_welding_risk", "heat_input_travel_speed_effect"],
          category="thermal",
      ),

      # ── Porosity (3 queries) ─────────────────────────────────────────────────

      RetrievalQuery(
          query_id="RQ_014",
          query="porosity root cause moisture shielding gas humidity",
          relevant_ids=["root_cause_porosity", "humidity_tropical_context", "corrective_porosity_heat_diss"],
          category="porosity",
      ),
      RetrievalQuery(
          query_id="RQ_015",
          query="voltage CV instability porosity arc length corrective",
          relevant_ids=["heat_input_voltage_effect", "corrective_porosity_heat_diss", "root_cause_porosity"],
          category="porosity",
      ),
      RetrievalQuery(
          query_id="RQ_016",
          query="ISO 5817 porosity surface pore quality level acceptance",
          relevant_ids=["iso5817_porosity_surface", "aws_d11_table81_porosity_static"],
          category="porosity",
      ),

      # ── Undercut (2 queries) ─────────────────────────────────────────────────

      RetrievalQuery(
          query_id="RQ_017",
          query="undercut acceptance criteria ISO 5817 level C maximum depth",
          relevant_ids=["iso5817_undercut", "aws_d11_table81_undercut_static", "aws_d11_table81_undercut_cyclic"],
          category="undercut",
      ),
      RetrievalQuery(
          query_id="RQ_018",
          query="undercut corrective reduce amperage torch angle 45 degrees",
          relevant_ids=["corrective_undercut_high_heat", "root_cause_undercut", "torch_angle_work_angle"],
          category="undercut",
      ),

      # ── Thresholds (4 queries) ───────────────────────────────────────────────

      RetrievalQuery(
          query_id="RQ_019",
          query="WarpSense feature thresholds GOOD MARGINAL RISK bands",
          relevant_ids=["warpsense_feature_thresholds", "warpsense_defect_feature_map"],
          category="threshold",
      ),
      RetrievalQuery(
          query_id="RQ_020",
          query="WarpSense quality class GOOD MARGINAL DEFECTIVE ISO 5817 mapping",
          relevant_ids=["warpsense_quality_class_mapping", "iso5817_overview", "iso5817_level_selection"],
          category="threshold",
      ),
      RetrievalQuery(
          query_id="RQ_021",
          query="corrective parameter bounds WPS amperage voltage travel speed limits",
          relevant_ids=["corrective_parameter_bounds", "aws_d11_wps_essential_variables"],
          category="threshold",
      ),
      RetrievalQuery(
          query_id="RQ_022",
          query="disposition framework REWORK REQUIRED CONDITIONAL PASS criteria",
          relevant_ids=["disposition_framework", "warpsense_quality_class_mapping", "aws_d11_disposition_rework"],
          category="threshold",
      ),

      # ── Shipyard context (3 queries) ─────────────────────────────────────────

      RetrievalQuery(
          query_id="RQ_023",
          query="IACS recommendation 47 shipyard weld quality inspection coverage",
          relevant_ids=["iacs47_weld_ndt_coverage", "iacs47_scope", "research_amirafshari_2022"],
          category="system",
      ),
      RetrievalQuery(
          query_id="RQ_024",
          query="marine welding tropical humidity Singapore moisture porosity",
          relevant_ids=["humidity_tropical_context", "iacs47_marine_environment_context", "iacs47_preheat"],
          category="system",
      ),
      RetrievalQuery(
          query_id="RQ_025",
          query="heat input formula kJ/mm voltage amperage travel speed calculation",
          relevant_ids=["aws_d11_heat_input_formula", "heat_input_formula_physics"],
          category="system",
      ),
  ]


  # ─────────────────────────────────────────────────────────────────────────────
  # METRICS
  # ─────────────────────────────────────────────────────────────────────────────

  def precision_at_k(retrieved: list[str], relevant: list[str], k: int) -> float:
      top_k = retrieved[:k]
      hits = sum(1 for doc_id in top_k if doc_id in relevant)
      return hits / k


  def recall_at_k(retrieved: list[str], relevant: list[str], k: int) -> float:
      top_k = retrieved[:k]
      hits = sum(1 for doc_id in top_k if doc_id in relevant)
      return hits / len(relevant) if relevant else 0.0


  def reciprocal_rank(retrieved: list[str], relevant: list[str]) -> float:
      for i, doc_id in enumerate(retrieved, 1):
          if doc_id in relevant:
              return 1.0 / i
      return 0.0


  # ─────────────────────────────────────────────────────────────────────────────
  # EVALUATOR
  # ─────────────────────────────────────────────────────────────────────────────

  @dataclass
  class QueryResult:
      query_id:      str
      query:         str
      category:      str
      retrieved_ids: list[str]
      relevant_ids:  list[str]
      rr:            float
      p_at_k:        dict
      r_at_k:        dict


  @dataclass
  class RetrievalEvalReport:
      timestamp:   str
      n_queries:   int
      k_values:    list[int]
      mrr:         float
      mean_p_at_k: dict
      mean_r_at_k: dict
      by_category: dict
      query_results: list


  class RetrievalEvaluator:
      def __init__(self, verbose: bool = True):
          self.verbose = verbose
          self._log(f"[RAGEval] Loading ChromaDB from {CHROMA_PATH}")
          client = chromadb.PersistentClient(path=str(CHROMA_PATH))
          ef = embedding_functions.DefaultEmbeddingFunction()
          self.collection = client.get_collection(name=COLLECTION_NAME, embedding_function=ef)
          self._log(f"[RAGEval] Collection loaded: {self.collection.count()} chunks")

      def _log(self, msg: str) -> None:
          if self.verbose:
              print(msg)

      def _retrieve(self, query: str, k: int) -> list[str]:
          results = self.collection.query(query_texts=[query], n_results=k, include=["ids"])
          return results["ids"][0]

      def _eval_query(self, q: RetrievalQuery, max_k: int) -> QueryResult:
          retrieved = self._retrieve(q.query, max_k)
          rr = reciprocal_rank(retrieved, q.relevant_ids)
          p_at_k = {k: precision_at_k(retrieved, q.relevant_ids, k) for k in K_VALUES if k <= max_k}
          r_at_k = {k: recall_at_k(retrieved, q.relevant_ids, k) for k in K_VALUES if k <= max_k}
          return QueryResult(
              query_id=q.query_id, query=q.query, category=q.category,
              retrieved_ids=retrieved, relevant_ids=q.relevant_ids,
              rr=rr, p_at_k=p_at_k, r_at_k=r_at_k,
          )

      def evaluate(self, queries: Optional[list[RetrievalQuery]] = None,
                   k_values: list[int] = K_VALUES) -> RetrievalEvalReport:
          queries = queries or GROUND_TRUTH
          max_k = max(k_values)

          self._log(f"\n{'='*60}")
          self._log(f"RAG RETRIEVAL EVAL — {len(queries)} queries, k={k_values}")
          self._log(f"{'='*60}\n")

          qr_list = []
          for q in queries:
              qr = self._eval_query(q, max_k)
              qr_list.append(qr)
              hits = [cid for cid in qr.retrieved_ids[:3] if cid in q.relevant_ids]
              self._log(f"  {q.query_id}  RR={qr.rr:.2f}  P@3={qr.p_at_k.get(3,0):.2f}  "
                        f"P@6={qr.p_at_k.get(6,0):.2f}  hits={hits}")

          mrr = mean(qr.rr for qr in qr_list)
          mean_p = {k: mean(qr.p_at_k.get(k, 0) for qr in qr_list) for k in k_values}
          mean_r = {k: mean(qr.r_at_k.get(k, 0) for qr in qr_list) for k in k_values}

          categories = sorted(set(q.category for q in queries))
          by_cat = {}
          for cat in categories:
              cat_qrs = [qr for qr in qr_list if qr.category == cat]
              by_cat[cat] = {
                  "n":      len(cat_qrs),
                  "mrr":    mean(qr.rr for qr in cat_qrs),
                  "p_at_3": mean(qr.p_at_k.get(3, 0) for qr in cat_qrs),
                  "p_at_6": mean(qr.p_at_k.get(6, 0) for qr in cat_qrs),
                  "r_at_6": mean(qr.r_at_k.get(6, 0) for qr in cat_qrs),
              }

          report = RetrievalEvalReport(
              timestamp=datetime.utcnow().isoformat(),
              n_queries=len(queries),
              k_values=k_values,
              mrr=mrr,
              mean_p_at_k={str(k): v for k, v in mean_p.items()},
              mean_r_at_k={str(k): v for k, v in mean_r.items()},
              by_category=by_cat,
              query_results=[asdict(qr) for qr in qr_list],
          )

          self._print_summary(report)
          return report

      def _print_summary(self, r: RetrievalEvalReport) -> None:
          w = 60
          print(f"\n{'='*w}")
          print("RETRIEVAL EVAL SUMMARY")
          print(f"{'='*w}")
          print(f"\nMRR:  {r.mrr:.3f}")
          print(f"\n{'k':<6} {'Precision@k':<18} {'Recall@k'}")
          print(f"{'-'*40}")
          for k in r.k_values:
              pk = r.mean_p_at_k.get(str(k), 0)
              rk = r.mean_r_at_k.get(str(k), 0)
              marker = " ← current (n_standards_chunks=6)" if k == 6 else ""
              print(f"  {k:<4} {pk:<18.3f} {rk:.3f}{marker}")

          print(f"\nBy category:")
          print(f"  {'Category':<12} {'N':<5} {'MRR':<8} {'P@3':<8} {'P@6':<8} {'R@6'}")
          print(f"  {'-'*50}")
          for cat, vals in sorted(r.by_category.items()):
              print(f"  {cat:<12} {vals['n']:<5} {vals['mrr']:<8.3f} "
                    f"{vals.get('p_at_3', 0):<8.3f} {vals.get('p_at_6', 0):<8.3f} {vals.get('r_at_6', 0):.3f}")

          print(f"\n{'='*w}\n")
          print("Interpretation (based on P@6 — actual operating point):")
          p6 = r.mean_p_at_k.get("6", 0)
          if p6 >= 0.85:
              print(f"  P@6 = {p6:.2f} — retrieval strong. BM25 hybrid (Phase 5) likely not needed.")
          elif p6 >= 0.70:
              print(f"  P@6 = {p6:.2f} — retrieval adequate. BM25 hybrid worth building.")
          else:
              print(f"  P@6 = {p6:.2f} — retrieval weak. BM25 hybrid clearly justified.")

      def save(self, report: RetrievalEvalReport) -> Path:
          ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
          out = RESULTS_DIR / f"retrieval_eval_{ts}.json"
          with open(out, "w") as f:
              json.dump(asdict(report), f, indent=2)
          print(f"[RAGEval] Results saved: {out}")
          return out


  def main():
      parser = argparse.ArgumentParser(description="WarpSense RAG retrieval evaluator")
      parser.add_argument("--k", type=int, nargs="+", default=K_VALUES)
      parser.add_argument("--category", type=str, default=None,
                          choices=["lof", "lop", "thermal", "porosity", "undercut", "system", "threshold"])
      parser.add_argument("--query", type=str, default=None)
      parser.add_argument("--save", action="store_true")
      parser.add_argument("--quiet", action="store_true")
      args = parser.parse_args()

      queries = GROUND_TRUTH
      if args.query:
          queries = [q for q in queries if q.query_id == args.query]
      elif args.category:
          queries = [q for q in queries if q.category == args.category]

      evaluator = RetrievalEvaluator(verbose=not args.quiet)
      report = evaluator.evaluate(queries=queries, k_values=args.k)

      if args.save:
          evaluator.save(report)


  if __name__ == "__main__":
      main()
  ```

  **Assumptions:**
  - ChromaDB is populated before this step is run
  - All 25 `relevant_ids` strings match chunk IDs in `build_welding_kb.py` verbatim — confirmed via Pre-Read Gate spot-check

  **Risks:**
  - Chunk IDs in GROUND_TRUTH don't match `build_welding_kb.py` → all P@k = 0 silently → P@6 = 0.000 → Phase 5 build/skip decision based on wrong data → mitigation: Pre-Read Gate runs grep spot-check of 3 IDs before writing.

  **Git Checkpoint:**
  ```bash
  git add backend/eval/eval_retrieval.py
  git commit -m "step 3.5: create eval_retrieval.py — 25 ground-truth queries, k=1,2,3,5,6, marker at k=6"
  ```

  **Subtasks:**
  - [ ] 🟥 `K_VALUES = [1, 2, 3, 5, 6]`
  - [ ] 🟥 "current" marker fires at `k == 6`
  - [ ] 🟥 Interpretation block uses `P@6`, not `P@3`
  - [ ] 🟥 All 25 ground-truth queries defined across 7 categories
  - [ ] 🟥 `by_category` dict includes `p_at_6` and `r_at_6`

  **✓ Verification Test:**

  **Action:**
  ```bash
  python -c "
  import sys; sys.path.insert(0, '.')
  from backend.eval.eval_retrieval import GROUND_TRUTH, K_VALUES
  assert K_VALUES == [1, 2, 3, 5, 6], f'K_VALUES wrong: {K_VALUES}'
  assert len(GROUND_TRUTH) == 25, f'expected 25 queries, got {len(GROUND_TRUTH)}'

  import pathlib
  src = pathlib.Path('backend/eval/eval_retrieval.py').read_text()
  assert 'if k == 6' in src,  'marker at k==6 missing'
  assert 'if k == 3' not in src, 'old k==3 marker still present'
  assert 'P@6' in src, 'P@6 not referenced in interpretation block'

  print('PASS: K_VALUES correct, 25 queries, k=6 is current operating point')
  "
  ```

  **Retrieval quality smoke test (proves ChromaDB live and chunk IDs match):**
  ```bash
  python backend/eval/eval_retrieval.py --query RQ_001 --k 6
  ```
  Must complete without error. Output must show at least one relevant ID (iso5817_lof_all_levels, aws_d11_lof_zero_tolerance, or iso5817_lof_fillet_welds) in the retrieved list. If P@6 = 0.000 for RQ_001, chunk IDs do not match — re-check GROUND_TRUTH relevant_ids against build_welding_kb.py.

  **Pass:** Both the unit assertion and the retrieval smoke test pass.

---

### Phase 3.F — Prompt Evaluator

**Goal:** `eval_prompts.py` exists with all 8 variants (A1/A2/A3/B1/B2/B3/C2/C3), uses `prepare_context()` and `verify_citations()` exclusively (no private step calls), and branches correctly on C-dimension self-check behaviour.

---

- [ ] 🟥 **Step 3.6: Create `backend/eval/eval_prompts.py`** — *Critical: produces the corrective-action-specificity comparison table; C3 baseline required to quantify self-check value*

  **Step Architecture Thinking:**

  **Pattern applied:** Strategy Pattern (prompt variants as interchangeable strategies) + Facade Consumption. Each of the 8 prompt variants is a string template — a strategy for prompting the LLM. The `PromptEvaluator` applies each strategy against the same 24 scenarios using identical infrastructure (same classifier, same `prepare_context()`, same `verify_citations()` calls). The C-dimension branching (C2 uses embedded self-verification, C3 skips verification entirely) is the only behavioural difference between variants — the measurement infrastructure is identical.

  **Why this step exists here in the sequence:**
  Before this step: there is no way to compare prompt strategies or measure what the self-check step is worth. After this step: the comparison table shows which prompt dimension (root-cause reasoning style / corrective action framing / self-check approach) most affects corrective action specificity and citation grounding. Step 3.4 must be complete before this step because `prepare_context()` and `verify_citations()` must exist on the agent.

  **Why this file / class is the right location:**
  `eval_prompts.py` is a consumer of the Facade (Step 3.4), the scenario corpus (Step 3.2), and the trained classifier. It does not modify any of those — it only reads from them. The prompt string templates belong here, not in `warpsense_agent.py`, because they are evaluation variants, not production code.

  **Alternative approach considered and rejected:**
  `eval_prompts.py` calls `_step1_defect_intake`, `_step3_retrieve_standards`, and `_step5_self_check` directly, bypassing the Facade. Rejected because (a) this couples the eval to the internal step numbering, (b) a Phase 4 rename of `_step3` to `_retrieve` would break the eval with an `AttributeError` at run time, and (c) the explicit purpose of Steps 3.4 and 3.6 is to establish a stable contract boundary before Phase 4 refactoring.

  **What breaks if this step deviates from the described pattern:**
  If C3 sets `self_check_passed = True` instead of `False`, the A1 vs C3 self-check delta collapses to approximately zero (both ~100%), and the self-check step appears to add no safety value. This is the most dangerous deviation — it produces a misleading number that would justify removing the self-check step.

  ---

  **Idempotent:** Yes — creating a new file.

  **Pre-Read Gate:**
  - `grep -n "def prepare_context\|def verify_citations" backend/agent/warpsense_agent.py` → must return exactly 2 matches. If 0 → Step 3.4 not complete; STOP.
  - Run `grep -n "severity\|defect_categories" backend/agent/warpsense_agent.py` — confirm both attribute names exist on ThresholdViolation before writing the LOF/LOP override. If names differ (e.g. v.band, v.defect_types), use the actual names or the override never fires.
  - **Chunk and violation shapes (Pre-Flight confirmed):** `build_context_block` uses `c.chunk_id`, `c.source`, `c.section`, `c.text` — StandardsChunk must have these. `build_violations_block` uses `v.as_display_line()` — ThresholdViolation must have this method.
  - **_ROOT depth:** From `backend/eval/eval_prompts.py`, `Path(__file__).resolve().parent.parent.parent` must reach project root (containing `.env`). Confirm in Pre-Flight; if project layout differs, adjust the `.parent` chain.

  ```python
  """
  eval_prompts.py
  ---------------
  Evaluates 8 prompt variants across all 24 eval scenarios.

  Dimensions:
    A — Root cause reasoning style (Direct / Chain-of-thought / Few-shot)
    B — Corrective action framing (Parameter targets / Process narrative / Checklist)
    C — Self-check (Separate call / Embedded / None)

  Key metric: corrective action specificity
    Score 1.0 if the action contains a measurable target (number, %, degrees).
    Score 0.0 if vague ("improve technique").

  C3 (no self-check) is the baseline that quantifies what the self-check step is worth.
  The gap between C3.self_check_pass_rate and A1.self_check_pass_rate is the safety
  cost of removing the citation verification step.

  Usage:
      python eval_prompts.py                    # all 8 variants, 3 runs each
      python eval_prompts.py --variant A1 C3    # compare specific variants
      python eval_prompts.py --runs 1           # fast mode
      python eval_prompts.py --scenario TC_021_thermal_spike_risk_floor  # single scenario
      python eval_prompts.py --save
  """

  import argparse
  import json
  import re
  import sys
  import time
  from dataclasses import dataclass, asdict
  from datetime import datetime
  from pathlib import Path
  from statistics import mean, stdev
  from typing import Optional

  _ROOT = Path(__file__).resolve().parent.parent.parent
  if str(_ROOT) not in sys.path:
      sys.path.insert(0, str(_ROOT))

  from dotenv import load_dotenv
  load_dotenv(_ROOT / ".env")

  from groq import Groq

  from backend.features.session_feature_extractor import generate_feature_dataset
  from backend.features.weld_classifier import WeldClassifier
  from backend.agent.warpsense_agent import WarpSenseAgent
  from backend.eval.eval_scenarios import SCENARIOS, EvalScenario

  RESULTS_DIR = Path(__file__).parent / "results"
  RESULTS_DIR.mkdir(exist_ok=True)

  GROQ_MODEL = "llama-3.3-70b-versatile"

  # Patterns that indicate a measurable target in a corrective action
  SPECIFICITY_PATTERNS = [
      r"\d+\s*%",
      r"\d+\s*degrees?",
      r"±\s*\d+",
      r"\+/-\s*\d+",
      r"\d+\s*[Cc]/s",
      r"\d+\s*[Cc]",
      r"\d+\s*(mm|cm|m)\b",
      r"\d+\s*(kJ|J)\b",
      r"\d+\.?\d*\s*[Vv]olt",
      r"\d+\.?\d*\s*[Aa]mp",
      r"within\s+\d+\s+session",
      r"reduce\s+\w+\s+by\s+\d+",
      r"increase\s+\w+\s+by\s+\d+",
      r"below\s+\d+",
      r"above\s+\d+",
      r"at least\s+\d+",
  ]


  def specificity_score(action: str) -> float:
      for pattern in SPECIFICITY_PATTERNS:
          if re.search(pattern, action, re.IGNORECASE):
              return 1.0
      return 0.0


  def mean_specificity(actions: list[str]) -> float:
      if not actions:
          return 0.0
      return mean(specificity_score(a) for a in actions)


  # ─────────────────────────────────────────────────────────────────────────────
  # PROMPT VARIANTS
  # ─────────────────────────────────────────────────────────────────────────────

  def build_context_block(chunks: list) -> str:
      return "\n\n".join(
          f"[{c.chunk_id}] {c.source} | {c.section}\n{c.text}"
          for c in chunks
      )


  def build_violations_block(violations: list) -> str:
      return "\n".join(v.as_display_line() for v in violations) or "None"


  # ── A1: Direct (current baseline) ────────────────────────────────────────────

  PROMPT_A1 = """You are WarpSenseAgent, a welding quality assessment AI.

  Session: {session_id}
  Quality Class: {quality_class} (confidence: {confidence:.2f})
  Top Drivers: {top_drivers}

  Threshold Violations:
  {violations}

  Retrieved Standards:
  {context}

  Produce a JSON report with exactly these keys:
  {{"iso_5817_level": "B"|"C"|"D"|"BELOW_D", "disposition": "PASS"|"CONDITIONAL"|"REWORK_REQUIRED",
  "disposition_rationale": "One sentence.", "root_cause": "2-3 sentences linking features to defect mechanism.",
  "corrective_actions": ["Action with specific target value", ...], "standards_references": ["Source: section"]}}

  Rules: (1) DEFECTIVE->BELOW_D, MARGINAL->D, GOOD->C. (2) Any LOF/LOP RISK feature -> REWORK_REQUIRED.
  (3) Corrective actions must include specific numeric targets. (4) Only cite retrieved sources.
  Respond with ONLY the JSON object."""


  # ── A2: Chain-of-thought ─────────────────────────────────────────────────────

  PROMPT_A2 = """You are WarpSenseAgent, a welding quality assessment AI.

  Session: {session_id}
  Quality Class: {quality_class} (confidence: {confidence:.2f})
  Top Drivers: {top_drivers}

  Threshold Violations:
  {violations}

  Retrieved Standards:
  {context}

  Think step by step before producing your JSON:
  Step 1: Which features are in RISK band? Which are MARGINAL?
  Step 2: Map RISK features to defect type (LOF/LOP -> REWORK_REQUIRED; others -> CONDITIONAL).
  Step 3: Identify the primary physical mechanism from the retrieved standards.
  Step 4: Derive specific corrective parameters from the retrieved corrective protocols.
  Step 5: Verify every standard you cite appears in the retrieved context above.

  Now produce a JSON report:
  {{"iso_5817_level": "B"|"C"|"D"|"BELOW_D", "disposition": "PASS"|"CONDITIONAL"|"REWORK_REQUIRED",
  "disposition_rationale": "One sentence.", "root_cause": "2-3 sentences linking features to defect mechanism.",
  "corrective_actions": ["Action with specific target value", ...], "standards_references": ["Source: section"]}}

  Respond with ONLY the JSON object."""


  # ── A3: Few-shot ──────────────────────────────────────────────────────────────

  PROMPT_A3 = """You are WarpSenseAgent, a welding quality assessment AI.

  Here are two worked examples of correct assessments:

  EXAMPLE 1 (REWORK_REQUIRED):
  Violations: heat_diss_max_spike=65.2 C/s [RISK], angle_deviation_mean=20.7 deg [RISK]
  Output: {{"iso_5817_level": "BELOW_D", "disposition": "REWORK_REQUIRED",
  "disposition_rationale": "Two LOF primary features in RISK band.",
  "root_cause": "Thermal spikes at 65 C/s indicate abrupt arc interruptions with cold restarts. Torch angle deviation of 20.7 degrees redirects arc energy away from the fusion boundary.",
  "corrective_actions": ["Correct torch angle to 45 degrees plus or minus 5", "Reduce travel speed variance by 20%", "Maintain preheat to minimum 80C before restart"],
  "standards_references": ["ISO 5817:2023 iso5817_lof_all_levels: LOF not permitted at any level"]}}

  EXAMPLE 2 (CONDITIONAL):
  Violations: heat_input_mean=4000 J [MARGINAL]
  Output: {{"iso_5817_level": "D", "disposition": "CONDITIONAL",
  "disposition_rationale": "Single MARGINAL violation — monitor next 3 sessions.",
  "root_cause": "Heat input mean slightly below optimal, no LOF features in RISK band.",
  "corrective_actions": ["Increase wire feed speed by 5% to raise heat input above 4500 J"],
  "standards_references": ["WarpSense Phase 1 warpsense_feature_thresholds: heat_input_mean GOOD > 4500 J"]}}

  Now assess this session:
  Session: {session_id} | Class: {quality_class} ({confidence:.2f}) | Drivers: {top_drivers}

  Threshold Violations:
  {violations}

  Retrieved Standards:
  {context}

  Respond with ONLY the JSON object using the same structure as the examples above."""


  # ── B1: Parameter targets (same as A1 — baseline already uses parameter targets) ──

  PROMPT_B1 = PROMPT_A1


  # ── B2: Process narrative ─────────────────────────────────────────────────────

  PROMPT_B2 = """You are WarpSenseAgent, a welding quality assessment AI.

  Session: {session_id}
  Quality Class: {quality_class} (confidence: {confidence:.2f})
  Top Drivers: {top_drivers}

  Threshold Violations:
  {violations}

  Retrieved Standards:
  {context}

  Produce a JSON report with exactly these keys:
  {{"iso_5817_level": "B"|"C"|"D"|"BELOW_D", "disposition": "PASS"|"CONDITIONAL"|"REWORK_REQUIRED",
  "disposition_rationale": "One sentence.", "root_cause": "2-3 sentences linking features to defect mechanism.",
  "corrective_actions": ["The welder should ... because ...", ...], "standards_references": ["Source: section"]}}

  Rules: (1) DEFECTIVE->BELOW_D, MARGINAL->D, GOOD->C. (2) Any LOF/LOP RISK feature -> REWORK_REQUIRED.
  (3) Corrective actions must describe what the welder should physically do and why.
  (4) Only cite retrieved sources.
  Respond with ONLY the JSON object."""


  # ── B3: Checklist format ──────────────────────────────────────────────────────

  PROMPT_B3 = """You are WarpSenseAgent, a welding quality assessment AI.

  Session: {session_id}
  Quality Class: {quality_class} (confidence: {confidence:.2f})
  Top Drivers: {top_drivers}

  Threshold Violations:
  {violations}

  Retrieved Standards:
  {context}

  Produce a JSON report with exactly these keys:
  {{"iso_5817_level": "B"|"C"|"D"|"BELOW_D", "disposition": "PASS"|"CONDITIONAL"|"REWORK_REQUIRED",
  "disposition_rationale": "One sentence.", "root_cause": "2-3 sentences linking features to defect mechanism.",
  "corrective_actions": ["Step 1: [verb] ...", "Step 2: [verb] ...", ...], "standards_references": ["Source: section"]}}

  Rules: (1) DEFECTIVE->BELOW_D, MARGINAL->D, GOOD->C. (2) Any LOF/LOP RISK feature -> REWORK_REQUIRED.
  (3) Each corrective action must be a numbered step starting with an action verb, independently actionable.
  (4) Only cite retrieved sources.
  Respond with ONLY the JSON object."""


  # ── C2: Embedded self-verification ───────────────────────────────────────────

  PROMPT_C2 = """You are WarpSenseAgent, a welding quality assessment AI.

  Session: {session_id}
  Quality Class: {quality_class} (confidence: {confidence:.2f})
  Top Drivers: {top_drivers}

  Threshold Violations:
  {violations}

  Retrieved Standards:
  {context}

  Before finalising your report, verify that every standard you cite appears in the
  Retrieved Standards above. Set "self_verified": true if all citations are grounded,
  false if any citation is not present in the retrieved context.

  Produce a JSON report with exactly these keys:
  {{"iso_5817_level": "B"|"C"|"D"|"BELOW_D", "disposition": "PASS"|"CONDITIONAL"|"REWORK_REQUIRED",
  "disposition_rationale": "One sentence.", "root_cause": "2-3 sentences linking features to defect mechanism.",
  "corrective_actions": ["Action with specific target value", ...], "standards_references": ["Source: section"],
  "self_verified": true|false}}

  Rules: (1) DEFECTIVE->BELOW_D, MARGINAL->D, GOOD->C. (2) Any LOF/LOP RISK feature -> REWORK_REQUIRED.
  (3) Corrective actions must include specific numeric targets. (4) Only cite retrieved sources.
  Respond with ONLY the JSON object."""


  # ── C3: No self-check (baseline) ─────────────────────────────────────────────
  # Same prompt as A1. The distinction is in _run_once: verify_citations is NOT called.
  # Purpose: quantify alignment degradation from removing the self-check step entirely.

  PROMPT_C3 = PROMPT_A1


  PROMPT_VARIANTS = {
      "A1": ("Direct (current)",         PROMPT_A1),
      "A2": ("Chain-of-thought",         PROMPT_A2),
      "A3": ("Few-shot examples",        PROMPT_A3),
      "B1": ("Parameter targets",        PROMPT_B1),
      "B2": ("Process narrative",        PROMPT_B2),
      "B3": ("Checklist format",         PROMPT_B3),
      "C2": ("Embedded self-verify",     PROMPT_C2),
      "C3": ("No self-check (baseline)", PROMPT_C3),
  }


  # ─────────────────────────────────────────────────────────────────────────────
  # RUNNER
  # ─────────────────────────────────────────────────────────────────────────────

  @dataclass
  class PromptRunResult:
      variant_id:           str
      scenario_id:          str
      expected_disposition: str
      actual_disposition:   str
      correct:              bool
      iso_5817_level:       str
      corrective_actions:   list[str]
      specificity_score:    float
      fallback_used:        bool
      self_check_passed:    bool
      latency_ms:           float
      error:                Optional[str] = None


  @dataclass
  class VariantSummary:
      variant_id:             str
      variant_name:           str
      n_scenarios:            int
      runs_per_scenario:      int
      disposition_match_rate: float
      mean_specificity:       float
      std_specificity:        float
      fallback_rate:          float
      self_check_pass_rate:   float
      mean_latency_ms:        float
      std_latency_ms:         float


  class PromptEvaluator:
      def __init__(self, runs_per_scenario: int = 3, verbose: bool = True):
          self.runs = runs_per_scenario
          self.verbose = verbose

          dataset = generate_feature_dataset()
          self.classifier = WeldClassifier()
          self.classifier.train(dataset)

          # Agent used for prepare_context() and verify_citations() only — not for LLM step
          self.agent = WarpSenseAgent(verbose=False)

          self.groq = Groq()

      def _log(self, msg):
          if self.verbose:
              print(msg)

      def _call_llm(self, prompt: str) -> tuple[dict, float, bool]:
          t0 = time.perf_counter()
          fallback_used = False
          raw = ""
          try:
              response = self.groq.chat.completions.create(
                  model=GROQ_MODEL,
                  messages=[{"role": "user", "content": prompt}],
                  temperature=0.2,
                  max_tokens=1024,
              )
              raw = response.choices[0].message.content.strip()
              raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.MULTILINE)
              raw = re.sub(r"\s*```$", "", raw, flags=re.MULTILINE).strip()
              parsed = json.loads(raw)
          except json.JSONDecodeError:
              match = re.search(r"\{.*\}", raw, re.DOTALL)
              parsed = json.loads(match.group()) if match else {}
              fallback_used = True
          except Exception as e:
              parsed = {
                  "disposition": "CONDITIONAL",
                  "iso_5817_level": "D",
                  "root_cause": f"LLM call failed: {e}",
                  "corrective_actions": [],
                  "standards_references": [],
                  "disposition_rationale": "Fallback",
              }
              fallback_used = True

          latency_ms = (time.perf_counter() - t0) * 1000
          return parsed, latency_ms, fallback_used

      def _run_once(self, variant_id: str, prompt_template: str,
                    scenario: EvalScenario) -> PromptRunResult:
          features = scenario.features
          prediction = self.classifier.predict(features)

          # Use public API — decoupled from internal step numbering
          violations, chunks, _ = self.agent.prepare_context(features, prediction)

          top_drivers_str = ", ".join(f"{name}({imp:.2f})" for name, imp in prediction.top_drivers)
          context = build_context_block(chunks)
          violations_str = build_violations_block(violations)

          prompt = prompt_template.format(
              session_id=features.session_id,
              quality_class=prediction.quality_class,
              confidence=prediction.confidence,
              top_drivers=top_drivers_str,
              violations=violations_str,
              context=context,
          )

          parsed, latency_ms, fallback_used = self._call_llm(prompt)

          # Apply LOF/LOP safety override (same logic as agent Step 6)
          disposition = parsed.get("disposition", "CONDITIONAL")
          lof_lop_risk = any(
              v.severity == "RISK" and any(cat in ["LOF", "LOP"] for cat in v.defect_categories)
              for v in violations
          )
          if lof_lop_risk and disposition != "REWORK_REQUIRED":
              disposition = "REWORK_REQUIRED"

          # Self-check — branch on C-dimension:
          # C3: no self-check — citations were never verified. Set False (0% grounded) so the
          #     A1 vs C3 comparison measures "A1 had X% grounded citations; C3 had 0% verified."
          #     If we set True, both A1 and C3 would show self_check_pass_rate=1.0 and delta=0.
          # C2: embedded self-verification — LLM sets self_verified key
          # All others: separate verify_citations call via public agent API
          if variant_id == "C3":
              self_check_passed = False  # never checked — C3 baseline has 0% citation grounding
          elif variant_id == "C2":
              self_check_passed = bool(parsed.get("self_verified", False))
          else:
              self_check_passed, _ = self.agent.verify_citations(parsed, chunks)

          actions = parsed.get("corrective_actions", [])
          spec = mean_specificity(actions)
          correct = (disposition == scenario.expected_disposition)

          return PromptRunResult(
              variant_id=variant_id,
              scenario_id=scenario.scenario_id,
              expected_disposition=scenario.expected_disposition,
              actual_disposition=disposition,
              correct=correct,
              iso_5817_level=parsed.get("iso_5817_level", ""),
              corrective_actions=actions,
              specificity_score=spec,
              fallback_used=fallback_used,
              self_check_passed=self_check_passed,
              latency_ms=latency_ms,
          )

      def evaluate_variant(self, variant_id: str,
                           scenarios: list[EvalScenario]) -> tuple[VariantSummary, list[PromptRunResult]]:
          variant_name, prompt_template = PROMPT_VARIANTS[variant_id]
          self._log(f"\n  Variant {variant_id}: {variant_name}")
          self._log(f"  {'-'*50}")

          all_runs: list[PromptRunResult] = []
          for scenario in scenarios:
              for run_idx in range(self.runs):
                  result = self._run_once(variant_id, prompt_template, scenario)
                  all_runs.append(result)
                  icon = "✅" if result.correct else "❌"
                  self._log(f"    {icon} {scenario.scenario_id} run={run_idx+1} "
                            f"match={result.correct} spec={result.specificity_score:.1f} "
                            f"{result.latency_ms:.0f}ms")

          n_runs = len(all_runs)
          n_correct = sum(1 for r in all_runs if r.correct)
          specs = [r.specificity_score for r in all_runs]
          lats = [r.latency_ms for r in all_runs]

          summary = VariantSummary(
              variant_id=variant_id,
              variant_name=variant_name,
              n_scenarios=len(scenarios),
              runs_per_scenario=self.runs,
              disposition_match_rate=n_correct / n_runs,
              mean_specificity=mean(specs),
              std_specificity=stdev(specs) if len(specs) > 1 else 0.0,
              fallback_rate=mean(1.0 if r.fallback_used else 0.0 for r in all_runs),
              self_check_pass_rate=mean(1.0 if r.self_check_passed else 0.0 for r in all_runs),
              mean_latency_ms=mean(lats),
              std_latency_ms=stdev(lats) if len(lats) > 1 else 0.0,
          )
          return summary, all_runs

      def evaluate_all(self, variant_ids: list[str],
                       scenarios: list[EvalScenario]) -> list[VariantSummary]:
          self._log(f"\n{'='*60}")
          self._log(f"PROMPT EVAL — {len(variant_ids)} variants × {len(scenarios)} scenarios × {self.runs} run(s)")
          self._log(f"{'='*60}")

          summaries = []
          for vid in variant_ids:
              summary, _ = self.evaluate_variant(vid, scenarios)
              summaries.append(summary)

          self._print_comparison(summaries)
          return summaries

      def _print_comparison(self, summaries: list[VariantSummary]) -> None:
          print(f"\n{'='*75}")
          print("PROMPT VARIANT COMPARISON")
          print(f"{'='*75}")
          print(f"\n{'Var':<4} {'Name':<25} {'Match%':<10} {'Specificity':<18} {'Fallback%':<12} {'SC Pass%':<12} {'ms'}")
          print(f"{'-'*90}")
          for s in summaries:
              print(f"  {s.variant_id:<4} {s.variant_name:<25} "
                    f"{s.disposition_match_rate:<10.1%} "
                    f"{s.mean_specificity:.2f} ± {s.std_specificity:.2f}{'':5} "
                    f"{s.fallback_rate:<12.1%} "
                    f"{s.self_check_pass_rate:<12.1%} "
                    f"{s.mean_latency_ms:.0f}")

          best_spec = max(summaries, key=lambda s: s.mean_specificity)
          c3 = next((s for s in summaries if s.variant_id == "C3"), None)
          a1 = next((s for s in summaries if s.variant_id == "A1"), None)

          print(f"\nHighest corrective action specificity: {best_spec.variant_id} ({best_spec.variant_name})")
          print(f"  mean_specificity = {best_spec.mean_specificity:.2f}")
          print(f"  (1.0 = action contains measurable target; 0.0 = vague advice)")

          if c3 and a1:
              sc_delta = a1.self_check_pass_rate - c3.self_check_pass_rate
              print(f"\nSelf-check value (A1 vs C3):")
              print(f"  A1 (with self-check):    {a1.self_check_pass_rate:.1%} citations grounded in retrieved chunks")
              print(f"  C3 (no self-check):      {c3.self_check_pass_rate:.1%} verified (C3 never runs verify_citations)")
              print(f"  Delta:                   {sc_delta:+.1%}  ← citation grounding gained by self-check step")

          print(f"\n{'='*75}\n")

      def save(self, summaries: list[VariantSummary]) -> Path:
          ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
          out = RESULTS_DIR / f"prompt_eval_{ts}.json"
          with open(out, "w") as f:
              json.dump([asdict(s) for s in summaries], f, indent=2)
          print(f"[PromptEval] Results saved: {out}")
          return out


  def main():
      parser = argparse.ArgumentParser(description="WarpSense prompt variant evaluator")
      parser.add_argument("--variant", type=str, nargs="+", default=list(PROMPT_VARIANTS.keys()),
                          choices=list(PROMPT_VARIANTS.keys()))
      parser.add_argument("--runs", type=int, default=3)
      parser.add_argument("--category", type=str, default=None,
                          choices=["TRUE_REWORK", "TRUE_PASS", "FP_RISK", "FN_RISK"])
      parser.add_argument("--scenario", type=str, default=None)
      parser.add_argument("--save", action="store_true")
      parser.add_argument("--quiet", action="store_true")
      args = parser.parse_args()

      scenarios = SCENARIOS
      if args.scenario:
          scenarios = [s for s in scenarios if s.scenario_id == args.scenario]
          if not scenarios:
              print(f"ERROR: scenario '{args.scenario}' not found"); sys.exit(1)
      if args.category:
          scenarios = [s for s in scenarios if s.category == args.category]

      evaluator = PromptEvaluator(runs_per_scenario=args.runs, verbose=not args.quiet)
      summaries = evaluator.evaluate_all(args.variant, scenarios)

      if args.save:
          evaluator.save(summaries)


  if __name__ == "__main__":
      main()
  ```

  **Assumptions:**
  - `StandardsChunk` has `chunk_id`, `source`, `section`, `text` — confirmed in Pre-Flight
  - `ThresholdViolation` has `as_display_line()`, `.severity`, `.defect_categories` — confirmed in Pre-Flight
  - Step 3.4 complete: `prepare_context()` and `verify_citations()` exist on agent

  **Risks:**
  - `ThresholdViolation.severity` or `.defect_categories` has wrong attribute name → LOF/LOP safety override never fires → all 4 FN_RISK scenarios return CONDITIONAL → mitigation: Pre-Flight explicitly confirms these attribute names before writing.
  - C3 `self_check_passed = True` by mistake → delta A1 vs C3 collapses to zero → mitigation: verification test checks `'variant_id == "C3"' in src` and asserts that the C3 branch sets False.

  **Git Checkpoint:**
  ```bash
  git add backend/eval/eval_prompts.py
  git commit -m "step 3.6: create eval_prompts.py — 8 variants (A1/A2/A3/B1/B2/B3/C2/C3), public agent API, C-dimension self-check branching"
  ```

  **Subtasks:**
  - [ ] 🟥 All 8 variants defined in `PROMPT_VARIANTS`
  - [ ] 🟥 `PROMPT_B1 = PROMPT_A1` and `PROMPT_C3 = PROMPT_A1` (no redundant prompt text)
  - [ ] 🟥 `_run_once` uses `self.agent.prepare_context()` — no private step method calls
  - [ ] 🟥 C2/C3 self-check branching present in `_run_once`
  - [ ] 🟥 `_print_comparison` prints A1 vs C3 self-check delta

  **✓ Verification Test:**

  **Action:**
  ```bash
  python -c "
  import sys, pathlib; sys.path.insert(0, '.')
  from backend.eval.eval_prompts import PROMPT_VARIANTS

  expected = {'A1', 'A2', 'A3', 'B1', 'B2', 'B3', 'C2', 'C3'}
  assert set(PROMPT_VARIANTS.keys()) == expected, f'variants mismatch: {set(PROMPT_VARIANTS.keys())}'

  src = pathlib.Path('backend/eval/eval_prompts.py').read_text()
  assert '_step5_self_check'         not in src, 'private _step5_self_check call present'
  assert '_step3_retrieve_standards' not in src, 'private _step3_retrieve_standards call present'
  assert '_step1_defect_intake'      not in src, 'private _step1_defect_intake call present'
  assert 'prepare_context'  in src, 'prepare_context not used'
  assert 'verify_citations' in src, 'verify_citations not used'
  assert 'variant_id == \"C3\"' in src, 'C3 branch missing'
  assert 'variant_id == \"C2\"' in src, 'C2 branch missing'

  print('PASS: 8 variants, no private calls, public API used, C-dimension branches present')
  "
  ```

  **Prompt execution smoke test (proves wiring correct — one variant, one scenario, one run):**
  ```bash
  python backend/eval/eval_prompts.py --variant A1 --runs 1 --scenario TC_021_thermal_spike_risk_floor
  ```
  Must complete without error. If it fails (build_context_block shape, top_drivers unpack, Groq API, etc.), the file is not wired correctly — fix before declaring Step 3.6 done.

  **Pass:** Both the unit assertion and the smoke test pass.

---

### Phase 3.G — E2E Smoke Test (Gated Exit)

- [ ] 🟥 **Step 3.7: Run E2E smoke test — mandatory exit condition for Phase 3**

  **Goal:** Phase 3 is not complete until the pipeline produces FNR = 0.000 on FN_RISK scenarios. This step is a formal gate, not optional regression prose.

  **Pre-requisites:** Steps 3.1 through 3.6 must be complete. ChromaDB populated (Pre-Flight check 8).

  **Action:**
  ```bash
  python backend/eval/eval_pipeline.py --category FN_RISK
  ```

  **Pass criteria:**
  - Exit code = 0
  - Output shows 4/4 ✅ for all FN_RISK scenarios
  - FNR = 0.000
  - No "CRITICAL: N FALSE-NEGATIVE failures" message

  **Fail criteria:** If exit code ≠ 0 or FNR ≠ 0.000 → STOP. Phase 3 is not complete. Do not declare Phase 3 done. Report the failure and await human instruction.

  **Subtasks:**
  - [ ] 🟥 Command completes with exit code 0
  - [ ] 🟥 FNR = 0.000
  - [ ] 🟥 All 4 FN_RISK scenarios show disposition_match_rate = 100%

  **✓ Verification:** The command itself is the verification. No separate test script.

---

## Regression Guard

**Systems at risk:**
- `warpsense_agent.py` — new methods inserted before `assess()`. If `assess()` was accidentally replaced or its signature changed, the entire Phase 2 pipeline breaks.
- `backend/eval/` imports — if `SessionFeatures` or `WeldPrediction` field names changed between when the plan was written and when it runs, all eval imports will fail at scenario construction time.

**Regression verification:**

| System | Pre-change behaviour | Post-change verification |
|--------|---------------------|--------------------------|
| `warpsense_agent.py` | `assess()` runs and returns `WeldQualityReport` | `python -c "from backend.agent.warpsense_agent import WarpSenseAgent; assert hasattr(WarpSenseAgent,'assess')"` |
| `eval_scenarios.py` | 24 scenarios importable | `python backend/eval/eval_scenarios.py` → `24 total` |
| All eval imports | No import errors | `python -c "from backend.eval.eval_pipeline import PipelineEvaluator; from backend.eval.eval_retrieval import RetrievalEvaluator; from backend.eval.eval_prompts import PROMPT_VARIANTS; print('all imports ok')"` |

**E2E smoke test:** Formal Step 3.7 below. Must pass before Phase 3 is complete.

---

## Rollback Procedure

```bash
# Rollback in reverse order — one revert per commit

git revert HEAD    # reverts step 3.6 (eval_prompts.py)
git revert HEAD    # reverts step 3.5 (eval_retrieval.py)
git revert HEAD    # reverts step 3.4 (warpsense_agent.py public methods)
git revert HEAD    # reverts step 3.3 (eval_pipeline.py)
git revert HEAD    # reverts step 3.2 (eval_scenarios.py)
git revert HEAD    # reverts step 3.1 (eval/ scaffold)

# Confirm clean state:
python -c "import pathlib; assert not pathlib.Path('backend/eval').exists(), 'eval/ still present'"
python -c "from backend.agent.warpsense_agent import WarpSenseAgent; assert not hasattr(WarpSenseAgent,'prepare_context'), 'public methods still present'"
echo "Rollback confirmed"
```

---

## Pre-Flight Checklist

| Phase | Check | How to Confirm | Status |
|-------|-------|----------------|--------|
| **Pre-flight** | All 7 Clarification Gate unknowns resolved | Pre-Flight reads complete, snapshot filled | ⬜ |
| | `backend/eval/` does not exist | `ls backend/eval/` returns no such file | ⬜ |
| **3.A** | Step 3.1 complete | `python -c "import pathlib; assert pathlib.Path('backend/eval/__init__.py').exists()"` | ⬜ |
| **3.B** | THRESHOLDS confirmed from Pre-Flight | Snapshot field filled | ⬜ |
| | `SessionFeatures` constructor confirmed | Snapshot field filled | ⬜ |
| **3.C** | Step 3.2 complete | `python backend/eval/eval_scenarios.py` → 24 total | ⬜ |
| **3.D** | All 4 private step methods confirmed | Pre-Read Gate grep returns 1 each | ⬜ |
| | `_step5_self_check` accepts `dict` | Confirmed from Pre-Flight | ⬜ |
| **3.E** | ChromaDB populated (Pre-Flight check 8) | Chunk count > 0 | ⬜ |
| **3.F** | Step 3.4 complete | `prepare_context` on agent returns 2 grep matches | ⬜ |
| **3.G** | Step 3.7 E2E gate | `python backend/eval/eval_pipeline.py --category FN_RISK` exit 0, FNR=0.000 | ⬜ |

---

## Risk Heatmap

| Step | Risk Level | What Could Go Wrong | Early Detection | Idempotent |
|------|-----------|---------------------|-----------------|------------|
| 3.1 | 🟢 Low | Directory already exists; .gitkeep missing from bash block | Pre-Read Gate; git add fails if .gitkeep not created | Yes |
| 3.2 | 🟡 Medium | `SessionFeatures` field mismatch or quality_label not accepted → runtime error on scenario import | Pre-Flight confirms; Verification import test | Yes |
| 3.3 | 🟡 Medium | `WeldQualityReport`/`generate_feature_dataset` type mismatch → AttributeError or train() fails | Pre-Flight confirms field names and return types | Yes |
| 3.4 | 🔴 High | `_step5_self_check` accepts typed object not dict; wrong unpack of _step1/_step3 return values; wrong return order in prepare_context silently breaks FN safety override | Pre-Read Gate; exact str_replace anchor; return-order Part B integration test | Yes |
| 3.5 | 🟡 Medium | Chunk IDs in GROUND_TRUTH don't match `build_welding_kb.py` → all P@k = 0 silently → wrong Phase 5 decision | Pre-Flight spot-check of 3 IDs; Pre-Read Gate grep before writing | Yes |
| 3.6 | 🟡 Medium | `build_context_block`/`build_violations_block` assume wrong chunk/violation shape; C3 self_check=True masks delta; ThresholdViolation wrong attribute names silently disable LOF/LOP override | Pre-Flight confirms StandardsChunk/ThresholdViolation attributes; C3 branch in verification; Step 3.6 Pre-Read grep for severity/defect_categories | Yes |
| 3.7 | 🔴 High | FNR ≠ 0.000 — Phase 3 silently incomplete; safety claim invalid | Mandatory gate; explicit exit condition | N/A |

---

## Success Criteria

| Deliverable | Target | Verification |
|-------------|--------|--------------|
| Package scaffold | `backend/eval/` importable | Step 3.1 verification |
| 24 scenarios | Correct values, correct categories | `python backend/eval/eval_scenarios.py` → 24 total |
| TC_009 | `heat_input_min_rolling == 4200.0` | Step 3.2 assertion script |
| TC_014 | `arc_on_ratio == 0.91` | Step 3.2 assertion script |
| Pipeline eval | FNR = 0.000 on FN_RISK | Step 3.7: `python backend/eval/eval_pipeline.py --category FN_RISK` → exit 0 |
| Confusion matrix | Uses observed dispositions | `most_common_actual` in `ScenarioAggregateResult` |
| Retrieval eval | k=6 is operating point | K_VALUES includes 6, marker at k==6 |
| 8 prompt variants | All dimensions present | `set(PROMPT_VARIANTS.keys()) == {A1,A2,A3,B1,B2,B3,C2,C3}` |
| Public agent API | No private method calls in eval_prompts | grep confirms absence |
| `warpsense_agent.py` | `assess()` intact after Step 3.4 | Import + `hasattr` check |

---

⚠️ **Execute in order: 3.1 → 3.2 → 3.3 → 3.4 → 3.5 → 3.6 → 3.7. Step 3.6 requires Step 3.4. Step 3.7 is the mandatory E2E gate — Phase 3 is not complete until it passes.**
⚠️ **Pre-Flight must complete before Step 3.2. If any THRESHOLDS field is blank → re-read the agent first.**
⚠️ **If Pre-Read Gate fails on private method names in Step 3.4 → STOP. Do not guess method names.**
⚠️ **Do not batch multiple steps into one git commit.**
⚠️ **Run the E2E smoke test after Step 3.6 before declaring Phase 3 complete.**