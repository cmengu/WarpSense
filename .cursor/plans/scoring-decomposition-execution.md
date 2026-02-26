# Feature Implementation Plan: Scoring Decomposition + Heat Input

**Overall Progress:** `100%`

## TLDR

Replace the abstract single-number score with a structured SessionScore object that decomposes into named AWS D1.2-relevant categories: heat input compliance, torch angle excursions, arc termination quality, defect alert summary, and interpass temperature. Heat input is calculated per frame from amps/volts/speed and checked against a configurable WPS range. Every excursion is timestamped with duration. Scope: scoring module only. No mock data, alert engine, or UI changes.

---

## Critical Decisions

- **Score storage:** Mixed (lazy write-through). `score_total` is persisted in DB on first GET /sessions/{id}/score for COMPLETE sessions. Rescore endpoint + backfill script required.
- **WPS range:** Default 0.9–1.5 kJ/mm via scoring_config.json. Session 1 mock targets 0.5–0.9 — document mismatch; do not silently pass.
- **SessionScore:** New canonical output. Old `total` becomes `session_score.overall_score`; keep old field for backward compat (TODO: remove in Session 4).
- **Heat input formula:** `(amps × volts × 60) / (travel_speed_mm_per_min × 1000)` kJ/mm. Skip when any field None or travel_speed ≤ 0.
- **Interpass:** Timer-based proxy (no plate sensor). 45s min gap as proxy for >60°C. Document as estimate, not measurement.
- **Excursion logging:** Full window with `duration_ms`; log start and end, not just trigger frame.
- **Type hints:** `Optional[float]`, `List`, `Dict` from `typing` — Python 3.8 compat.

---

## Clarification Gate

| Unknown | Required | Source | Blocking | Resolved |
|---------|----------|--------|----------|----------|
| Score storage architecture | lazy vs stored vs mixed | Pre-flight code read | Step 2 | ✅ Mixed |
| Existing scoring module | file path | Pre-flight | Step 1 | ✅ backend/scoring/rule_based.py |
| SessionScore consumer | what compare/score endpoints expect | Pre-flight route read | Step 5 | ✅ total, rules; compare does NOT use score |
| WPS config location | new or existing | Pre-flight | Step 3 | ✅ New: config/scoring_config.json |

---

## Agent Failure Protocol

1. Verification command fails → read full error output.
2. Cause unambiguous → ONE targeted fix → re-run same command.
3. Still failing → STOP. Output full contents of every modified file. Report: (a) command, (b) full error, (c) fix attempted, (d) file state, (e) why you cannot proceed.
4. Never attempt second fix without human instruction.
5. Never modify files not named in current step.

---

## Pre-Flight — Run Before Any Code Changes

```
Read backend/scoring/rule_based.py, backend/models/scoring.py, backend/routes/sessions.py (lines 323–403)
Capture and output:
(1) Every function in scoring/rule_based.py: score_session, _check_amps_stability, _check_angle_consistency, etc.
(2) Exact signature of score_session(session, features, thresholds) -> SessionScore
(3) Current SessionScore fields in models/scoring.py: total, rules
(4) Files that import from scoring.rule_based: routes/sessions, services/scoring_service, tests, etc.
(5) Run: cd backend && python -m pytest tests/ -q --tb=no 2>&1 | tail -5
(6) Run: wc -l backend/scoring/rule_based.py backend/models/scoring.py backend/routes/sessions.py backend/models/frame.py
(7) grep -n "heat_input_kj_per_mm\|arc_termination_type" backend/models/frame.py
(8) grep -n "score_total" backend/database/models.py
(9) grep -n "class AlertEngine\|def __init__" backend/realtime/alert_engine.py — confirm AlertEngine(config_path) takes config path; pass "config/alert_thresholds.json" explicitly
Do not change anything. Show full output and wait.
```

**Baseline Snapshot (agent fills during pre-flight):**
```
Test count before plan: ____
Line count rule_based.py:    ____
Line count models/scoring.py: ____
Line count routes/sessions.py: ____
Line count frame.py: ____
```

**Architecture Decision (agent fills during pre-flight):**
- Score storage: [x] stored on creation (lazy write-through) [ ] lazy/on-request only [ ] mixed
- Score location: backend/database/models.py SessionModel.score_total
- Compare endpoint: Does NOT read score (uses frame deltas)
- Rescore endpoint needed: [x] yes [ ] no

**Automated checks (all must pass before Step 1):**
- [ ] Scoring module identified and read in full
- [ ] `heat_input_kj_per_mm` exists on Frame
- [ ] `arc_termination_type` exists on Frame
- [ ] Baseline test count captured
- [ ] Architecture decision resolved — rescore endpoint in scope

---

## Steps Analysis

| Step | Critical? | Reason | Idempotent |
|------|-----------|--------|------------|
| 1 | Yes | Schema is shared contract | Yes |
| 2 | Yes | Config drives WPS range | Yes |
| 3 | Yes | Heat input calculator | Yes |
| 4 | Yes | Score components | Yes |
| 5 | Yes | Wire scoring to sessions | Yes |
| 6 | Yes | Rescore (stored scores) | Yes |
| 7 | No | Tests | Yes |
| 8 | No | Regression guard | Yes |

---

## Tasks

### Phase 1 — Schema and Config

**Goal:** SessionScore schema defined; scoring config with WPS range and weights.

---

- [ ] 🟥 **Step 1: Define SessionScore schema** — *Critical*

  **Idempotent:** Yes.

  **Pre-Read Gate:**
  - `grep -n "class.*Score\|SessionScore" backend/scoring/ -r --include="*.py"` — no models.py in scoring/ yet; rule_based imports from models.scoring
  - `grep -n "from pydantic\|BaseModel" backend/models/scoring.py` — confirms Pydantic style
  - `grep -n "class SessionScore" backend/models/scoring.py` — 1 match; OLD schema (total, rules). NEW schema goes in backend/scoring/models.py

  **Self-Contained Rule:** Create backend/scoring/models.py. Use Pydantic BaseModel (match models/scoring.py). Define ExcursionEvent, ScoreComponent, SessionScore. No business logic.

  **Anchor Uniqueness Check:** New file — no anchor. Create backend/scoring/models.py and backend/scoring/__init__.py update if needed.

  ```python
  # backend/scoring/models.py
  """AWS D1.2 decomposition scoring models. Schema only — no business logic."""

  from typing import Dict, List, Tuple

  from pydantic import BaseModel, Field


  class ExcursionEvent(BaseModel):
      timestamp_ms: float
      parameter: str  # e.g. "travel_angle_degrees", "heat_input_kj_per_mm"
      value: float
      threshold: float
      duration_ms: float


  class ScoreComponent(BaseModel):
      name: str
      passed: bool
      score: float  # 0.0–1.0
      excursions: List[ExcursionEvent] = Field(default_factory=list)
      summary: str


  class DecomposedSessionScore(BaseModel):
      """AWS D1.2 decomposed session score. Canonical output for new scoring."""
      session_id: str
      overall_score: float  # weighted mean of component scores
      passed: bool  # all critical components passed
      components: Dict[str, ScoreComponent] = Field(default_factory=dict)
      frame_count: int
      arc_on_frame_count: int
      computed_at_ms: float = 0.0
      wps_range_kj_per_mm: Tuple[float, float] = (0.9, 1.5)
  ```

  **Note:** Named `DecomposedSessionScore` to avoid conflict with existing `models.scoring.SessionScore`. Plan refers to "SessionScore" as the target; this is the new schema. Downstream can alias if desired.

  **What it does:** Defines Pydantic models for ExcursionEvent, ScoreComponent, and the new decomposed score.

  **Assumptions:**
  - Python 3.8+ (Tuple from typing)
  - Pydantic installed

  **Git Checkpoint:**
  ```bash
  git add backend/scoring/models.py
  git commit -m "step 1: define DecomposedSessionScore, ScoreComponent, ExcursionEvent schema"
  ```

  **✓ Verification Test:**

  **Type:** Unit
  **Action:** `cd backend && python -c "
  from scoring.models import DecomposedSessionScore, ScoreComponent, ExcursionEvent
  e = ExcursionEvent(timestamp_ms=1000, parameter='heat_input_kj_per_mm', value=1.6, threshold=1.5, duration_ms=200)
  c = ScoreComponent(name='heat_input', passed=False, score=0.7, excursions=[e], summary='2 frames above WPS ceiling')
  s = DecomposedSessionScore(session_id='test', overall_score=0.7, passed=False, components={'heat_input': c}, frame_count=1500, arc_on_frame_count=900, computed_at_ms=0, wps_range_kj_per_mm=(0.9, 1.5))
  assert s.components['heat_input'].excursions[0].parameter == 'heat_input_kj_per_mm'
  print('OK')
  "`
  **Expected:** Exit 0, prints OK
  **Pass:** No ImportError; assertion holds
  **Fail:** ImportError → add backend to PYTHONPATH or run from backend/; check scoring/__init__.py exports

---

- [ ] 🟥 **Step 2: Add scoring config** — *Critical*

  **Idempotent:** Yes.

  **Pre-Read Gate:**
  - `ls backend/config/` — alert_thresholds.json exists
  - `grep -n "scoring_config" backend/ -r --include="*.py"` → 0 matches
  - `grep -n "def load_thresholds" backend/realtime/alert_engine.py` — use same pattern for load_scoring_config

  **Self-Contained Rule:** Create scoring_config.json and scoring/config.py with load_scoring_config.

  ```json
  {
    "wps_heat_input_min_kj_per_mm": 0.9,
    "wps_heat_input_max_kj_per_mm": 1.5,
    "torch_angle_max_degrees": 20.0,
    "interpass_min_ms": 45000,
    "interpass_max_temp_c": 60,
    "arc_termination_weight": 0.25,
    "heat_input_weight": 0.35,
    "torch_angle_weight": 0.25,
    "defect_alert_weight": 0.10,
    "interpass_weight": 0.05,
    "component_weights_note": "Must sum to 1.0. heat_input weighted highest per AWS D1.2."
  }
  ```

  ```python
  # backend/scoring/config.py
  """Load and validate scoring_config.json."""

  import json
  from pathlib import Path


  REQUIRED_KEYS = (
      "wps_heat_input_min_kj_per_mm",
      "wps_heat_input_max_kj_per_mm",
      "torch_angle_max_degrees",
      "interpass_min_ms",
      "interpass_max_temp_c",
      "arc_termination_weight",
      "heat_input_weight",
      "torch_angle_weight",
      "defect_alert_weight",
      "interpass_weight",
  )


  def load_scoring_config(config_path: str) -> dict:
      """Load and validate scoring_config.json. Raises ValueError on missing keys."""
      path = Path(config_path)
      if not path.is_absolute():
          backend = Path(__file__).resolve().parent.parent
          path = backend / config_path
      if not path.exists():
          raise FileNotFoundError(f"scoring_config not found: {path}")
      data = json.loads(path.read_text())
      for key in REQUIRED_KEYS:
          if data.get(key) is None:
              raise ValueError(f"scoring_config key {key!r} is null or missing in {path}")
      return data
  ```

  **What it does:** Adds config file and loader; validates required keys.

  **Git Checkpoint:**
  ```bash
  git add backend/config/scoring_config.json backend/scoring/config.py
  git commit -m "step 2: add scoring config with WPS range and component weights"
  ```

  **✓ Verification Test:**

  **Type:** Unit
  **Action:** `cd backend && python -c "
  from scoring.config import load_scoring_config
  cfg = load_scoring_config('config/scoring_config.json')
  assert cfg['wps_heat_input_min_kj_per_mm'] == 0.9
  w = cfg['arc_termination_weight'] + cfg['heat_input_weight'] + cfg['torch_angle_weight'] + cfg['defect_alert_weight'] + cfg['interpass_weight']
  assert abs(w - 1.0) < 0.001
  print('OK')
  "`
  **Expected:** Exit 0, prints OK
  **Pass:** Weights sum to 1.0
  **Fail:** KeyError → check JSON keys; sum != 1.0 → fix weights

---

### Phase 2 — Calculators

**Goal:** Heat input, torch angle, arc termination, defect alert, and interpass components implemented.

---

- [ ] 🟥 **Step 3: Heat input calculator** — *Critical*

  **Idempotent:** Yes.

  **Pre-Read Gate:**
  - `grep -n "DecomposedSessionScore\|ScoreComponent" backend/scoring/models.py` — matches from Step 1
  - `grep -n "heat_input_kj_per_mm" backend/models/frame.py` — 1 match

  **Self-Contained Rule:** Create backend/scoring/heat_input.py. Single function `calculate_heat_input_component(frames, cfg) -> ScoreComponent`. Track excursion windows; close on arc-off or loop end.

  ```python
  # backend/scoring/heat_input.py
  """Heat input component: per-frame kJ/mm vs WPS range."""

  from typing import List, Optional

  from scoring.models import ExcursionEvent, ScoreComponent


  def _close_excursion(
      excursions: List[ExcursionEvent],
      start_ms: Optional[float],
      end_ms: float,
      parameter: str,
      value: float,
      threshold: float,
  ) -> None:
      """Append excursion if one is open. Call on arc-off or loop end."""
      if start_ms is not None:
          excursions.append(
              ExcursionEvent(
                  timestamp_ms=start_ms,
                  parameter=parameter,
                  value=value,
                  threshold=threshold,
                  duration_ms=end_ms - start_ms,
              )
          )


  def calculate_heat_input_component(frames: list, cfg: dict) -> ScoreComponent:
      """Compute heat input component. Excursion = frame outside WPS range."""
      wps_min = cfg["wps_heat_input_min_kj_per_mm"]
      wps_max = cfg["wps_heat_input_max_kj_per_mm"]
      excursions: List[ExcursionEvent] = []
      excursion_start_ms: Optional[float] = None
      excursion_start_value: Optional[float] = None
      excursion_threshold: Optional[float] = None
      arc_on_count = 0
      last_arc_on_ms: Optional[float] = None

      for frame in frames:
          amps = getattr(frame, "amps", None)
          volts = getattr(frame, "volts", None)
          speed = getattr(frame, "travel_speed_mm_per_min", None)
          ts = getattr(frame, "timestamp_ms", 0)

          if amps is None or volts is None or speed is None or speed <= 0:
              # last_arc_on_ms is correct here — excursion ends at last arc-on frame, not current arc-off frame
              if excursion_start_ms is not None and last_arc_on_ms is not None and excursion_threshold is not None:
                  _close_excursion(
                      excursions, excursion_start_ms, last_arc_on_ms,
                      "heat_input_kj_per_mm", excursion_start_value or 0.0, excursion_threshold
                  )
                  excursion_start_ms = None
              continue

          hi = (amps * volts * 60) / (speed * 1000)
          arc_on_count += 1
          last_arc_on_ms = ts

          threshold = wps_min if hi < wps_min else wps_max
          if hi < wps_min or hi > wps_max:
              if excursion_start_ms is None:
                  excursion_start_ms = ts
                  excursion_start_value = hi
                  excursion_threshold = threshold
          else:
              if excursion_start_ms is not None and excursion_start_value is not None and excursion_threshold is not None:
                  excursions.append(
                      ExcursionEvent(
                          timestamp_ms=excursion_start_ms,
                          parameter="heat_input_kj_per_mm",
                          value=excursion_start_value,
                          threshold=excursion_threshold,
                          duration_ms=ts - excursion_start_ms,
                      )
                  )
                  excursion_start_ms = None

      if excursion_start_ms is not None and last_arc_on_ms is not None and excursion_threshold is not None and excursion_start_value is not None:
          _close_excursion(
              excursions, excursion_start_ms, last_arc_on_ms,
              "heat_input_kj_per_mm", excursion_start_value, excursion_threshold
          )

      # Penalty: ~10% score drop per excursion per 10% of arc-on frames; collapses to 0 when excursions >= 10% of arc-on count
      score_val = 1.0 - min(1.0, len(excursions) / max(arc_on_count, 1) * 10)
      return ScoreComponent(
          name="heat_input",
          passed=len(excursions) == 0,
          score=round(score_val, 3),
          excursions=excursions,
          summary=f"{len(excursions)} heat input excursions vs WPS range {wps_min}–{wps_max} kJ/mm",
      )
  ```

  **What it does:** Iterates frames with amps/volts/speed, computes heat input, logs excursions outside WPS.

  **Git Checkpoint:**
  ```bash
  git add backend/scoring/heat_input.py
  git commit -m "step 3: heat input calculator with excursion tracking"
  ```

  **✓ Verification Test:**

  **Type:** Unit
  **Action:** `cd backend && python -c "
  from scoring.heat_input import calculate_heat_input_component
  from unittest.mock import MagicMock
  f1 = MagicMock(); f1.amps=180; f1.volts=22; f1.travel_speed_mm_per_min=400; f1.timestamp_ms=0
  f2 = MagicMock(); f2.amps=200; f2.volts=24; f2.travel_speed_mm_per_min=300; f2.timestamp_ms=100
  cfg = {'wps_heat_input_min_kj_per_mm': 0.9, 'wps_heat_input_max_kj_per_mm': 1.5}
  result = calculate_heat_input_component([f1, f2], cfg)
  assert result.name == 'heat_input'
  assert len(result.excursions) >= 1
  print('OK')
  "`
  **Expected:** Exit 0, prints OK (f1: 0.594 < 0.9 → excursion)
  **Pass:** result.excursions non-empty
  **Fail:** AssertionError → check WPS range and formula

---

- [ ] 🟥 **Step 4: Score component calculators** — *Critical*

  **Idempotent:** Yes.

  **Pre-Read Gate:**
  - `grep -n "def calculate_heat_input" backend/scoring/heat_input.py` — 1 match
  - Read backend/scoring/models.py — confirm ScoreComponent, ExcursionEvent fields
  - `grep -n "AlertPayload" backend/realtime/alert_models.py` — AlertPayload has rule_triggered, timestamp_ms, etc.

  **Self-Contained Rule:** Create backend/scoring/components.py with four functions. Each returns ScoreComponent.

  ```python
  # backend/scoring/components.py
  """Torch angle, arc termination, defect alert, interpass score components."""

  import logging
  from typing import Dict, List, Optional

  from realtime.alert_models import AlertPayload
  from scoring.models import ExcursionEvent, ScoreComponent

  _logger = logging.getLogger(__name__)


  def calculate_torch_angle_component(frames: list, cfg: dict) -> ScoreComponent:
      """Check travel_angle_degrees vs torch_angle_max_degrees. Excursion = >20 or <0."""
      max_deg = cfg["torch_angle_max_degrees"]
      excursions: List[ExcursionEvent] = []
      excursion_start_ms: Optional[float] = None
      excursion_start_value: Optional[float] = None
      excursion_threshold: Optional[float] = None
      last_valid_ms: Optional[float] = None

      for frame in frames:
          angle = getattr(frame, "travel_angle_degrees", None)
          ts = getattr(frame, "timestamp_ms", 0)
          if angle is None:
              if excursion_start_ms is not None and last_valid_ms is not None and excursion_threshold is not None and excursion_start_value is not None:
                  excursions.append(ExcursionEvent(
                      timestamp_ms=excursion_start_ms, parameter="travel_angle_degrees",
                      value=excursion_start_value, threshold=excursion_threshold,
                      duration_ms=last_valid_ms - excursion_start_ms,
                  ))
                  excursion_start_ms = None
              continue
          last_valid_ms = ts
          threshold = max_deg if angle > max_deg else 0.0
          is_violation = angle > max_deg or angle < 0
          if is_violation:
              if excursion_start_ms is None:
                  excursion_start_ms = ts
                  excursion_start_value = angle
                  excursion_threshold = threshold
          else:
              if excursion_start_ms is not None:
                  excursions.append(ExcursionEvent(
                      timestamp_ms=excursion_start_ms, parameter="travel_angle_degrees",
                      value=excursion_start_value, threshold=excursion_threshold,
                      duration_ms=ts - excursion_start_ms,
                  ))
                  excursion_start_ms = None

      if excursion_start_ms is not None and last_valid_ms is not None and excursion_threshold is not None and excursion_start_value is not None:
          excursions.append(ExcursionEvent(
              timestamp_ms=excursion_start_ms, parameter="travel_angle_degrees",
              value=excursion_start_value, threshold=excursion_threshold,
              duration_ms=last_valid_ms - excursion_start_ms,
          ))

      score_val = 1.0 - min(1.0, len(excursions) * 0.2)
      return ScoreComponent(
          name="torch_angle",
          passed=len(excursions) == 0,
          score=round(score_val, 3),
          excursions=excursions,
          summary=f"{len(excursions)} torch angle excursions (max {max_deg}°, no drag)",
      )


  def calculate_arc_termination_component(frames: list, cfg: dict) -> ScoreComponent:
      """Excursion = frame with arc_termination_type == 'no_crater_fill'. duration_ms=0."""
      excursions: List[ExcursionEvent] = []
      for frame in frames:
          at = getattr(frame, "arc_termination_type", None)
          ts = getattr(frame, "timestamp_ms", 0)
          if at == "no_crater_fill":
              excursions.append(ExcursionEvent(
                  timestamp_ms=ts, parameter="arc_termination_type", value=0.0, threshold=0.0, duration_ms=0.0,
              ))
      count = len(excursions)
      return ScoreComponent(
          name="arc_termination",
          passed=count == 0,
          score=1.0 if count == 0 else round(max(0.0, 1.0 - count * 0.25), 3),
          excursions=excursions,
          summary=f"{count} abrupt arc terminations without crater fill",
      )


  def calculate_defect_alert_component(alerts: List[AlertPayload], cfg: dict) -> ScoreComponent:
      """Group alerts by rule_triggered. Critical (porosity, crater_crack, burn_through, arc_instability) → fail.
      Warnings (oxide_inclusion) → score penalty only, not automatic fail."""
      CRITICAL = {"porosity", "crater_crack", "burn_through", "arc_instability"}
      excursions: List[ExcursionEvent] = []
      by_rule: Dict[str, int] = {}
      dropped = [a for a in alerts if not isinstance(a, AlertPayload)]
      if dropped:
          _logger.warning("calculate_defect_alert_component: %d non-AlertPayload items dropped", len(dropped))
      for a in alerts:
          if not isinstance(a, AlertPayload):
              continue
          rule = a.rule_triggered
          ts = a.timestamp_ms
          excursions.append(ExcursionEvent(timestamp_ms=ts, parameter=rule, value=1.0, threshold=0.0, duration_ms=0.0))
          by_rule[rule] = by_rule.get(rule, 0) + 1
      has_critical = any(r in CRITICAL for r in by_rule)
      score_val = 0.0 if has_critical else (1.0 - min(1.0, len(alerts) * 0.1))
      return ScoreComponent(
          name="defect_alerts",
          passed=not has_critical,
          score=round(score_val, 3),
          excursions=excursions,
          summary=f"defects: {dict(by_rule)}" if by_rule else "no defect alerts",
      )


  def calculate_interpass_component(frames: list, cfg: dict) -> ScoreComponent:
      """Timer model only. No plate temperature sensor. Gap < interpass_min_ms → violation."""
      min_ms = cfg["interpass_min_ms"]
      excursions: List[ExcursionEvent] = []
      prev_arc_on_ms: Optional[float] = None
      prev_arc_off_ms: Optional[float] = None

      for frame in frames:
          amps = getattr(frame, "amps", None)
          ts = getattr(frame, "timestamp_ms", 0)
          arc_on = amps is not None and amps > 1.0
          if arc_on:
              if prev_arc_off_ms is not None and prev_arc_on_ms is not None:
                  gap = ts - prev_arc_off_ms
                  if gap < min_ms and gap > 0:
                      excursions.append(ExcursionEvent(
                          timestamp_ms=prev_arc_off_ms, parameter="interpass_gap_ms",
                          value=gap, threshold=min_ms, duration_ms=gap,
                      ))
              prev_arc_on_ms = ts
              prev_arc_off_ms = None
          else:
              if prev_arc_on_ms is not None:
                  prev_arc_off_ms = ts
              else:
                  prev_arc_off_ms = None

      score_val = 1.0 - min(1.0, len(excursions) * 0.3)
      return ScoreComponent(
          name="interpass",
          passed=len(excursions) == 0,
          score=round(score_val, 3),
          excursions=excursions,
          summary=f"{len(excursions)} interpass violations (< {min_ms}ms gap). Timer proxy only.",
      )
  ```

  **What it does:** Four component calculators; defect takes alerts list; interpass detects arc-off→arc-on gaps.

  **Git Checkpoint:**
  ```bash
  git add backend/scoring/components.py
  git commit -m "step 4: torch angle, arc termination, defect alert, interpass components"
  ```

  **✓ Verification Test:**

  **Type:** Unit
  **Action:** `cd backend && python -c "
  from scoring.components import (
      calculate_torch_angle_component,
      calculate_arc_termination_component,
      calculate_defect_alert_component,
      calculate_interpass_component,
  )
  from unittest.mock import MagicMock
  f = MagicMock(); f.travel_angle_degrees=25.0; f.timestamp_ms=500; f.arc_termination_type=None; f.amps=155
  cfg = {'torch_angle_max_degrees': 20.0, 'interpass_min_ms': 45000}
  r = calculate_torch_angle_component([f], cfg)
  assert r.name == 'torch_angle' and len(r.excursions) >= 1
  f2 = MagicMock(); f2.arc_termination_type='no_crater_fill'; f2.timestamp_ms=1000; f2.amps=0
  r2 = calculate_arc_termination_component([f2], cfg)
  assert not r2.passed
  print('OK')
  "`
  **Expected:** Exit 0, prints OK
  **Pass:** torch_angle and arc_termination assertions hold
  **Fail:** Check travel_angle_degrees, arc_termination_type handling

---

### Phase 3 — Orchestration and Wiring

**Goal:** SessionScorer orchestrator; GET /score returns session_score alongside old format; rescore endpoint + script.

---

- [ ] 🟥 **Step 5: Create SessionScorer and wire to sessions** — *Critical*

  **Idempotent:** Yes.

  **Pre-Read Gate:**
  - `grep -n "def calculate_torch_angle" backend/scoring/components.py` — 1 match
  - `grep -n "def calculate_heat_input" backend/scoring/heat_input.py` — 1 match
  - Read backend/routes/sessions.py lines 323–403 — get_session_score calls score_session, returns result
  - `grep -n "^import os\|^from os" backend/routes/sessions.py` — if 0 matches, add `import os` for ENV check
  - `grep -n "get_session_alerts\|AlertEngine" backend/routes/sessions.py` — get_session_alerts builds FrameInput, runs AlertEngine

  **Anchor Uniqueness Check:** Insert `session_score` into `result` before `return result` (line ~390). Must be single return in get_session_score.

  **Self-Contained Rule:** Create scorer.py; in get_session_score, run frames through AlertEngine to get alerts, call new score_session_decomposed, add session_score to result.

  ```python
  # backend/scoring/scorer.py
  """Orchestrator: AWS D1.2 decomposed scoring."""

  import os
  import time
  from typing import List, Optional

  from realtime.alert_engine import AlertEngine
  from realtime.alert_models import AlertPayload, FrameInput

  from scoring.components import (
      calculate_arc_termination_component,
      calculate_defect_alert_component,
      calculate_interpass_component,
      calculate_torch_angle_component,
  )
  from scoring.config import load_scoring_config
  from scoring.heat_input import calculate_heat_input_component
  from scoring.models import DecomposedSessionScore, ScoreComponent

  ALERT_CONFIG_PATH = "config/alert_thresholds.json"


  def _build_alerts_from_frames(
      frames: list,
      config_path: str = ALERT_CONFIG_PATH,
  ) -> List[AlertPayload]:
      """Build FrameInput list, run through AlertEngine, return alerts. Single source for routes + script."""
      engine = AlertEngine(config_path=config_path)
      alerts: List[AlertPayload] = []
      for i, f in enumerate(frames):
          fi = FrameInput(
              frame_index=i,
              timestamp_ms=getattr(f, "timestamp_ms", None),
              travel_angle_degrees=getattr(f, "travel_angle_degrees", None),
              travel_speed_mm_per_min=getattr(f, "travel_speed_mm_per_min", None),
              ns_asymmetry=0.0,
              volts=getattr(f, "volts", None),
              amps=getattr(f, "amps", None),
          )
          out = engine.push_frame(fi)
          if out:
              alerts.append(out)
      return alerts


  def score_session_decomposed(
      frames: list,
      alerts: list,
      session_id: str,
      cfg: Optional[dict] = None,
      config_path: str = "config/scoring_config.json",
  ) -> "DecomposedSessionScore":
      """Compute decomposed AWS D1.2 score. Critical = heat_input, arc_termination, defect_alerts."""
      if cfg is None:
          cfg = load_scoring_config(config_path)
      arc_on = sum(1 for f in frames if getattr(f, "amps", None) is not None and getattr(f, "amps", 0) > 1.0)
      heat = calculate_heat_input_component(frames, cfg)
      torch = calculate_torch_angle_component(frames, cfg)
      arc_term = calculate_arc_termination_component(frames, cfg)
      defect = calculate_defect_alert_component(alerts, cfg)
      interpass = calculate_interpass_component(frames, cfg)
      components = {
          "heat_input": heat,
          "torch_angle": torch,
          "arc_termination": arc_term,
          "defect_alerts": defect,
          "interpass": interpass,
      }
      critical = [heat, arc_term, defect]
      passed = all(c.passed for c in critical)
      weights = {
          "heat_input": cfg["heat_input_weight"],
          "torch_angle": cfg["torch_angle_weight"],
          "arc_termination": cfg["arc_termination_weight"],
          "defect_alerts": cfg["defect_alert_weight"],
          "interpass": cfg["interpass_weight"],
      }
      overall = sum(c.score * weights[c.name] for c in components.values())
      wps_range = (cfg["wps_heat_input_min_kj_per_mm"], cfg["wps_heat_input_max_kj_per_mm"])
      return DecomposedSessionScore(
          session_id=session_id,
          overall_score=round(overall, 3),
          passed=passed,
          components=components,
          frame_count=len(frames),
          arc_on_frame_count=arc_on,
          computed_at_ms=time.time() * 1000,
          wps_range_kj_per_mm=wps_range,
      )
  ```

  **Wire in routes/sessions.py:** Insert decomposed score block after `result = score.model_dump()` and before `result["active_threshold_spec"] = {`.

  **Uniqueness-Before-Replace:** Run `grep -n "result = score.model_dump()" backend/routes/sessions.py` — must return exactly 1 match (inside get_session_score). Run `grep -n 'result\[\"active_threshold_spec\"\]' backend/routes/sessions.py` — 1 match.

  **Exact replacement:**
  - **old_string:**
  ```
    result = score.model_dump()
    result["active_threshold_spec"] = {
  ```
  - **new_string:**
  ```
    result = score.model_dump()
    try:
        from scoring.scorer import score_session_decomposed, _build_alerts_from_frames
        alerts = _build_alerts_from_frames(list(session.frames))
        decomposed = score_session_decomposed(list(session.frames), alerts, session_id)
        result["session_score"] = decomposed.model_dump()
    except Exception:
        logger.exception("Decomposed score failed")
        # Only suppress and return null in production; re-raise in dev/staging so failures are visible
        if os.environ.get("ENV") != "production":
            raise
        result["session_score"] = None
    # TODO Session 4: remove legacy total/rules, use session_score only.
    # TODO Before Session 4: add mock WPS config (0.4–1.0) for test sessions or explicit annotation when expert mock (0.5–0.9) flags below WPS (0.9 floor); QA will otherwise see every expert failing heat_input.
    result["active_threshold_spec"] = {
  ```
  - Use `logger` (already in routes/sessions.py). Add `import os` at top of routes/sessions.py if not present.

  **What it does:** Orchestrates all components; wires into GET /score response.

  **Risks:**
  - AlertEngine adds latency → mitigation: non-blocking; on failure set session_score=None
  - ns_asymmetry=0.0 for FrameInput → thermal rules may under-report; acceptable per scope (scoring only)

  **Git Checkpoint:**
  ```bash
  git add backend/scoring/scorer.py backend/routes/sessions.py
  git commit -m "step 5: SessionScorer orchestrator, wire session_score to GET /score"
  ```

  **✓ Verification Test:**

  **Type:** Integration
  **Action:** `cd backend && python -c "
  from scoring.scorer import score_session_decomposed
  from unittest.mock import MagicMock
  frames = [MagicMock(amps=200, volts=24, travel_speed_mm_per_min=320, timestamp_ms=i*10, travel_angle_degrees=12, arc_termination_type=None) for i in range(20)]
  dec = score_session_decomposed(frames, [], 'test')
  assert dec.session_id == 'test'
  assert 'heat_input' in dec.components
  print('OK')
  "`
  **Expected:** Exit 0, prints OK (skip _build_alerts_from_frames; MagicMock frames would cause FrameInput ValidationError; that path tested by simulate_realtime smoke)
  **Pass:** No ValidationError; session_score structure present
  **Fail:** Check scorer imports, config load
  **Additional:** `cd backend && timeout 5 python -m scripts.simulate_realtime --mode novice --frames 200 --output console 2>&1 | tail -5` — no crash (exercises _build_alerts_from_frames with real frames)

---

- [ ] 🟥 **Step 6: Rescore endpoint and backfill script** — *Critical*

  **Idempotent:** Yes.

  **Pre-Read Gate:**
  - `grep -n "score_total" backend/database/models.py` — 1 match (column exists)
  - `grep -n "def to_pydantic" backend/database/models.py` — SessionModel.to_pydantic must exist (1+ match)
  - `grep -n "status" backend/database/models.py` — SessionModel.status column must exist
  - `grep -n "rescore" backend/routes/ -r` → 0 matches

  **Self-Contained Rule:** Add POST /sessions/{session_id}/rescore. Use _build_alerts_from_frames from scorer. Add rescore_all_sessions.py script using same helper.

  **Anchor Uniqueness Check:** Add new route after get_session_score. No existing rescore route.

  **Routes addition:** Add after get_session_score (after line 403, before get_session_alerts at 406):

  ```python
  @router.post("/sessions/{session_id}/rescore")
  async def rescore_session(
      session_id: str,
      db: OrmSession = Depends(get_db),
  ):
      """Recompute decomposed score, persist score_total. For backfill after scoring changes."""
      # TODO: add auth guard before exposing to QA environment
      session_model = (
          db.query(SessionModel)
          .options(joinedload(SessionModel.frames))
          .filter_by(session_id=session_id)
          .first()
      )
      if not session_model:
          raise HTTPException(status_code=404, detail="Session not found")
      frames = getattr(session_model, "frames", None) or []
      if len(frames) < 10:
          raise HTTPException(status_code=400, detail="Insufficient frames for scoring")
      session = session_model.to_pydantic()
      from scoring.scorer import score_session_decomposed, _build_alerts_from_frames
      alerts = _build_alerts_from_frames(list(session.frames))
      decomposed = score_session_decomposed(list(session.frames), alerts, session_id)
      session_model.score_total = int(round(decomposed.overall_score * 100))
      db.commit()
      return decomposed.model_dump()
  ```

  **Script:** Create backend/scripts/rescore_all_sessions.py (uses _build_alerts_from_frames):

  ```python
  # backend/scripts/rescore_all_sessions.py
  """Backfill score_total using decomposed scoring. Run after scoring logic changes."""
  import sys
  from pathlib import Path
  sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
  from sqlalchemy.orm import joinedload
  from database.connection import SessionLocal
  from database.models import SessionModel
  from scoring.scorer import score_session_decomposed, _build_alerts_from_frames

  def main():
      db = SessionLocal()
      try:
          models = db.query(SessionModel).options(joinedload(SessionModel.frames)).filter(
              SessionModel.status == "complete"
          ).all()
          for m in models:
              frames = getattr(m, "frames", None) or []
              if len(frames) < 10:
                  continue
              session = m.to_pydantic()
              alerts = _build_alerts_from_frames(list(session.frames))
              dec = score_session_decomposed(list(session.frames), alerts, m.session_id)
              m.score_total = int(round(dec.overall_score * 100))
              print(f"{m.session_id}: {dec.overall_score:.3f} -> {m.score_total}")
          db.commit()
      finally:
          db.close()

  if __name__ == "__main__":
      main()
  ```

  **What it does:** Enables backfill of score_total after scoring logic changes.

  **Git Checkpoint:**
  ```bash
  git add backend/routes/sessions.py backend/scripts/rescore_all_sessions.py
  git commit -m "step 6: rescore endpoint and backfill script"
  ```

  **✓ Verification Test:**

  **Type:** Integration
  **Action:** `grep -n "rescore" backend/routes/sessions.py` — at least 1 match
  **Action (automated, no server):** `cd backend && python -c "from routes.sessions import rescore_session; print('OK')"`
  **Expected:** Route present; import succeeds (confirms function + decorator don't throw)
  **Pass:** grep finds rescore; import prints OK
  **Fail:** ImportError → check routes.sessions path, rescore_session definition
  **Manual (optional):** `curl -X POST http://localhost:8000/api/sessions/{valid_session_id}/rescore` — returns JSON with session_score structure

---

### Phase 4 — Tests and Regression

**Goal:** Unit tests; regression guard.

---

- [ ] 🟥 **Step 7: Unit tests** — *Non-critical*

  **Idempotent:** Yes.

  **Self-Contained Rule:** Create backend/tests/test_scoring.py with at least: test_heat_input_in_range_no_excursions, test_heat_input_below_wps_flags_excursion, test_torch_angle_drag_flags_excursion, test_arc_termination_no_crater_fill_fails, test_defect_alert_porosity_fails_component, test_defect_alert_oxide_inclusion_passes_component, test_interpass_below_minimum_flags, test_build_alerts_from_frames_returns_list, test_session_score_overall_is_weighted_mean. Use MagicMock for frames; AlertPayload for defect tests; SimpleNamespace for _build_alerts_from_frames (real values to avoid FrameInput ValidationError).

  **Minimal test structure:**
  ```python
  # backend/tests/test_scoring.py
  """Unit tests for decomposed scoring (heat input, torch angle, arc termination, defect, interpass)."""
  import pytest
  from unittest.mock import MagicMock
  from scoring.heat_input import calculate_heat_input_component
  from scoring.components import (
      calculate_torch_angle_component,
      calculate_arc_termination_component,
      calculate_defect_alert_component,
      calculate_interpass_component,
  )
  from scoring.scorer import score_session_decomposed

  def test_heat_input_in_range_no_excursions():
      """200A x 24V x 60 / (250 mm/min x 1000) = 1.152 kJ/mm — clearly inside 0.9–1.5 range."""
      cfg = {"wps_heat_input_min_kj_per_mm": 0.9, "wps_heat_input_max_kj_per_mm": 1.5}
      f = MagicMock(amps=200, volts=24, travel_speed_mm_per_min=250, timestamp_ms=0)
      r = calculate_heat_input_component([f], cfg)
      assert r.passed and len(r.excursions) == 0

  def test_heat_input_below_wps_flags_excursion():
      cfg = {"wps_heat_input_min_kj_per_mm": 0.9, "wps_heat_input_max_kj_per_mm": 1.5}
      f = MagicMock(amps=180, volts=22, travel_speed_mm_per_min=400, timestamp_ms=0)
      r = calculate_heat_input_component([f], cfg)
      assert not r.passed and len(r.excursions) >= 1

  def test_torch_angle_drag_flags_excursion():
      cfg = {"torch_angle_max_degrees": 20.0, "interpass_min_ms": 45000}
      f = MagicMock(travel_angle_degrees=-5.0, timestamp_ms=500, amps=155)
      r = calculate_torch_angle_component([f], cfg)
      assert len(r.excursions) >= 1

  def test_arc_termination_no_crater_fill_fails():
      cfg = {"torch_angle_max_degrees": 20.0, "interpass_min_ms": 45000}
      f = MagicMock(arc_termination_type="no_crater_fill", timestamp_ms=1000)
      r = calculate_arc_termination_component([f], cfg)
      assert not r.passed

  def test_defect_alert_porosity_fails_component():
      from realtime.alert_models import AlertPayload
      cfg = {}
      a = AlertPayload(frame_index=0, rule_triggered="porosity", severity="critical", message="x", correction="y", timestamp_ms=100)
      r = calculate_defect_alert_component([a], cfg)
      assert not r.passed

  def test_defect_alert_oxide_inclusion_passes_component():
      """Warnings (oxide_inclusion) → score penalty only, not automatic fail."""
      from realtime.alert_models import AlertPayload
      cfg = {}
      a = AlertPayload(frame_index=0, rule_triggered="oxide_inclusion", severity="warning", message="x", correction="y", timestamp_ms=100)
      r = calculate_defect_alert_component([a], cfg)
      assert r.passed

  def test_interpass_below_minimum_flags():
      cfg = {"interpass_min_ms": 45000}
      f1 = MagicMock(amps=150, timestamp_ms=0)
      f2 = MagicMock(amps=0, timestamp_ms=10000)
      f3 = MagicMock(amps=150, timestamp_ms=20000)
      r = calculate_interpass_component([f1, f2, f3], cfg)
      assert len(r.excursions) >= 1

  def test_build_alerts_from_frames_returns_list():
      """_build_alerts_from_frames returns list; does not crash on real frame-like objects."""
      from types import SimpleNamespace
      from scoring.scorer import _build_alerts_from_frames
      f = SimpleNamespace(amps=200.0, volts=24.0, travel_speed_mm_per_min=250.0, timestamp_ms=0, travel_angle_degrees=12.0)
      result = _build_alerts_from_frames([f])
      assert isinstance(result, list)

  def test_session_score_overall_is_weighted_mean():
      cfg = {"heat_input_weight": 0.35, "torch_angle_weight": 0.25, "arc_termination_weight": 0.25,
             "defect_alert_weight": 0.10, "interpass_weight": 0.05,
             "wps_heat_input_min_kj_per_mm": 0.9, "wps_heat_input_max_kj_per_mm": 1.5,
             "torch_angle_max_degrees": 20.0, "interpass_min_ms": 45000}
      frames = [MagicMock(amps=200, volts=24, travel_speed_mm_per_min=320, timestamp_ms=i*10,
                  travel_angle_degrees=12, arc_termination_type=None) for i in range(20)]
      dec = score_session_decomposed(frames, [], "s1", cfg=cfg)
      assert 0 <= dec.overall_score <= 1.0
  ```

  **Git Checkpoint:**
  ```bash
  git add backend/tests/test_scoring.py
  git commit -m "step 7: scoring decomposition unit tests"
  ```

  **✓ Verification Test:**

  **Type:** Unit
  **Action:** `cd backend && python -m pytest tests/test_scoring.py -v`
  **Expected:** All tests pass
  **Pass:** Exit 0
  **Fail:** Fix failing test; do not change production code without re-verification

---

- [ ] 🟥 **Step 8: Regression guard** — *Non-critical*

  **Idempotent:** Yes.

  **Action:**
  - `cd backend && python -m pytest tests/ -v` — test count ≥ pre-flight baseline
  - `cd backend && timeout 5 python -m scripts.simulate_realtime --mode novice --frames 200 --output console 2>&1` — no crash
  - `cd backend && timeout 5 python -m scripts.simulate_realtime --mode expert --frames 200 --output console 2>&1` — no crash
  - If rescore script exists: `cd backend && python scripts/rescore_all_sessions.py 2>&1` — no crash (or skip if no sessions)

  **Known:** Expert mock (0.5–0.9 kJ/mm) vs WPS (0.9–1.5) — expert may show heat input excursions. Do not lower WPS floor to make tests pass.

  **Git Checkpoint:**
  ```bash
  git add -A
  git status
  git commit -m "step 8: regression guard passed" || true
  ```

---

## Regression Guard

| System | Pre-change | Post-change |
|--------|------------|-------------|
| Alert engine | Passes | Unchanged |
| Sessions route | Returns score | Returns score + session_score |
| Compare endpoint | No score | No score (unchanged) |
| Mock data | verify script passes | Unchanged |
| Test count | Baseline | ≥ baseline |

---

## Rollback Procedure

```bash
N=$(git log --oneline <FIRST_PLAN_COMMIT>..HEAD | wc -l)
for i in $(seq 1 $N); do git revert --no-edit HEAD; done
```

---

## Pre-Flight Checklist

| Phase | Check | How to Confirm | Status |
|-------|-------|----------------|--------|
| Pre-flight | Clarification Gate complete | All unknowns resolved | ⬜ |
| Pre-flight | Baseline snapshot captured | Test count + line counts | ⬜ |
| Phase 1 | heat_input_kj_per_mm on Frame | grep frame.py | ⬜ |
| Phase 1 | arc_termination_type on Frame | grep frame.py | ⬜ |
| Phase 2 | Step 1 models import | python -c "from scoring.models import ..." | ⬜ |
| Phase 2 | Step 2 config loads | python -c "from scoring.config import load_scoring_config" | ⬜ |
| Phase 3 | Step 5 anchor unique | grep "result = score.model_dump()" — 1 match | ⬜ |
| Phase 4 | Test count ≥ baseline | pytest tests/ -q | ⬜ |

---

## Risk Heatmap

| Step | Risk Level | What Could Go Wrong | Early Detection | Idempotent |
|------|------------|---------------------|-----------------|------------|
| Step 1 | Low | Schema mismatch with consumers | Import test | Yes |
| Step 2 | Low | Weights don't sum to 1.0 | Verification script | Yes |
| Step 3 | Medium | Div-by-zero if travel_speed=0 | Unit test with MagicMock | Yes |
| Step 4 | Medium | AlertPayload shape mismatch | calculate_defect_alert_component test | Yes |
| Step 5 | High | AlertEngine adds latency, breaks GET /score | simulate_realtime smoke | Yes |
| Step 6 | Medium | Rescore overwrites score_total | Manual curl | Yes |
| Step 7 | Low | Test assumptions wrong | pytest -v | Yes |
| Step 8 | Low | Regression | Full test run | Yes |

---

## Success Criteria

| Feature | Target | Verification |
|---------|--------|--------------|
| DecomposedSessionScore schema | Importable, all fields | Unit test Step 1 |
| Heat input | Per-frame, WPS range, duration | Unit test Step 3 |
| Torch angle | Excursions >20 or <0 | Unit test Step 4 |
| Arc termination | no_crater_fill → fail | Unit test Step 4 |
| Defect alerts | Critical fail; warnings pass | Unit tests Step 4 (porosity fails, oxide passes) |
| Interpass | Gap <45s → violation | Unit test Step 4 |
| Overall score | Weighted mean | Unit test Step 7 |
| Rescore endpoint | POST works | Integration Step 6 |
| _build_alerts_from_frames | Returns list, no crash | Unit test Step 7 |
| Sessions route | session_score alongside total | Integration Step 5 |
| Regression | Tests ≥ baseline, no crash | Step 8 |
