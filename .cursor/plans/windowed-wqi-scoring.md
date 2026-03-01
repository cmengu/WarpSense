# Windowed WQI Scoring Plan (Refined)

**Overall Progress:** `0%`

## TLDR

Add windowed WQI scoring to the pipeline without changing core logic. Introduce `extract_features_for_frames(frames, angle_target_deg)` and `score_frames_windowed(frames, thresholds, session_metadata, ...)` as wrappers. Add optional fields to Session (`wqi_timeline`, `mean_wqi`, `median_wqi`, `min_wqi`, `max_wqi`, `wqi_trend`). In `scoring_service`, after `score_session`, compute windowed WQI, derive mean/median/min/max/trend, and persist onto the session model alongside `score_total`. No changes to `extract_features` body, `score_session` body, or `total = int(round(100 * passed_count / len(rules)))` formula.

**Out of scope (follow-up):** routes/dev.py, scripts/backfill_score_total.py. This plan only wires the score endpoint in routes/sessions.py.

---

## Critical Decisions

- **Decision 1:** `extract_features` delegates to `extract_features_for_frames(session.frames, angle_target_deg)` — core logic lives in one place.
- **Decision 2:** `score_frames_windowed` receives `session_metadata` dict with `weld_type`, `thermal_sample_interval_ms`, `thermal_directions`, `thermal_distance_interval_mm`, `sensor_sample_rate_hz` so dummy Session passes Session validators (thermal_distance_consistency etc.).
- **Decision 3:** `score_session` rule selection is driven by **thresholds** only (checks `t.travel_speed_consistency is not None` etc.), not session.weld_type. weld_type in dummy Session is for Session construction consistency and future-proofing.
- **Decision 4:** Trend = avg(second_half) - avg(first_half). First half = wqis[:n//2], second half = wqis[n//2:]. Unequal lengths expected — do not balance. diff > 5 → "improving", < -5 → "degrading", else "stable". **Trend only when ≥4 windows**; else `wqi_trend=None`.
- **Decision 5:** SessionScore uses `model_copy(update={...})` — no direct mutation.
- **Decision 6:** Route passes `session` to `get_session_score` to avoid double `to_pydantic()` on large frame lists.
- **Decision 7:** `get_session_score` uses `*` (keyword-only) for new params so existing `(session_id, db)` call sites remain valid.

---

## Agent Failure Protocol

1. A verification command fails → read the full error output.
2. Cause is unambiguous → make ONE targeted fix → re-run the same verification command.
3. If still failing after one fix → **STOP**. Output full contents of modified files, report (a) command, (b) error verbatim, (c) fix attempted, (d) file state, (e) why you cannot proceed.
4. Never attempt a second fix without human instruction.
5. Never modify files not named in the current step.

---

## Pre-Flight — Run Before Any Code Changes

```
# 1. extract_features: confirm pure, no side effects
grep -n "log\|metric\|print\|logging" backend/features/extractor.py

# 2. disable_sensor_continuity_checks MUST exist
grep -n "disable_sensor_continuity_checks" backend/models/session.py
# If 0 matches: STOP. Report: "Session does not have disable_sensor_continuity_checks. Dummy Session will fail.
# Options: (a) add field to Session first, (b) restructure score_frames_windowed to avoid constructing Session."
# Do not proceed to Step 2.

# 3. Session validators: which fields cross-check against frames?
grep -n "validate_\|thermal_distance\|thermal_directions\|thermal_sample" backend/models/session.py

# 4. from_pydantic insertion anchor
grep -n "version=" backend/database/models.py
# If "version=1," exists in the cls() call inside from_pydantic → anchor holds. Use "after score_total=..., before version=1,".
# If version=1 does NOT exist → use fallback: "Insert the 6 new kwargs as the last kwargs before the closing ) of the single cls(...) call in from_pydantic."

# 5. Frame type parity: FrameModel.to_pydantic() must return models.frame.Frame (same as session.frames[0])
grep -n "class Frame\|def to_pydantic" backend/models/frame.py backend/database/models.py
# Confirm FrameModel.to_pydantic returns Frame from models.frame. If FrameModel returns a different type, windowed features compute against wrong shape — report before Step 5.

# 6. get_session_score call sites: any third positional arg?
grep -rn "get_session_score(" backend/
# Every call passes only (session_id, db). If any passes a third positional arg → use keyword-only params (add * before include_windowed in signature).

# 7. score_session( block uniqueness (Step 5C)
grep -c "score_session(session, features" backend/routes/sessions.py
# Must be exactly 1. If 2+ → anchor ambiguous. Report to human before replacing.

# 8. Step 1 fixture: identify session source for test
grep -rn "generate_expert_session\|generate_novice_session" backend/tests/test_extract_features.py
# Use generate_expert_session() or generate_novice_session() from data.mock_sessions (not a conftest fixture).

# 9. Alembic head
cd backend && alembic current

# 10. Test count
cd backend && python -m pytest -q --tb=no 2>/dev/null | tail -1
```

**Baseline Snapshot:** Alembic head ____, Test count ____, version=1 in from_pydantic: yes/no ____

---

## Tasks

### Phase 1 — Feature Extraction Refactor

- [ ] 🟥 **Step 1: Add extract_features_for_frames to extractor.py**

  **Idempotent:** Yes.

  **Pre-Read Gate:** Read full `extract_features`; confirm it calls `_compute_cyclogram_area`, uses `POROSITY_SIGMA_THRESHOLD`, etc.

  **Implementation:**

  1. Add `from models.frame import Frame` (or `List["Frame"]` with `from __future__ import annotations`).
  2. Add `extract_features_for_frames(frames: List[Frame], angle_target_deg: float = 45) -> Dict[str, Any]`:
     - Copy the **exact body** of `extract_features`, including calls to `_compute_cyclogram_area`, `POROSITY_SIGMA_THRESHOLD`, and any other helpers.
     - Replace every `session.frames` with `frames`.
     - **Do not inline** helper logic; keep references to `_compute_cyclogram_area` and module constants.
  3. Replace `extract_features` body with: `return extract_features_for_frames(session.frames, angle_target_deg)`.

  **Git Checkpoint:** `git add backend/features/extractor.py && git commit -m "step 1: add extract_features_for_frames, delegate extract_features"`

  **✓ Verification Test:** Add to `backend/tests/test_extract_features.py`:
  ```python
  def test_extract_features_for_frames_equals_extract_features(self) -> None:
      session = generate_expert_session()
      assert extract_features_for_frames(session.frames, 45) == extract_features(session, 45)
  ```
  Use `generate_expert_session` from `data.mock_sessions` (same import as existing tests). Existing tests must pass.

---

### Phase 2 — Windowed Scoring

- [ ] 🟥 **Step 2: Add score_frames_windowed to rule_based.py**

  **Idempotent:** Yes.

  **Pre-Read Gate:** Session validators (from Pre-Flight #2) reference `thermal_distance_interval_mm`, `thermal_directions`. Dummy Session must receive actual session values to pass validation.

  **Implementation:**

  1. Add imports: `from datetime import datetime`, `from typing import List`, `from features.extractor import extract_features_for_frames`, `from models.frame import Frame`
  2. Add after `score_session`:

  ```python
  def score_frames_windowed(
      frames: List[Frame],
      thresholds: Optional[WeldTypeThresholds],
      session_metadata: Dict[str, Any],
      angle_target_deg: float = 45,
      window_size: int = 50,
  ) -> List[Dict[str, Any]]:
      """
      Score frames in tumbling windows. Returns [{frame_start, frame_end, wqi}, ...].
      session_metadata: dict with weld_type, thermal_sample_interval_ms, thermal_directions,
        thermal_distance_interval_mm, sensor_sample_rate_hz from parent session.
        Required so dummy Session passes validators (e.g. validate_thermal_distance_consistency).
      """
      if not frames or window_size < 1:
          return []
      m = session_metadata
      weld_type = m.get("weld_type", "mig")
      thermal_sample_interval_ms = m.get("thermal_sample_interval_ms", 100)
      thermal_directions = m.get("thermal_directions", ["center"])
      thermal_distance_interval_mm = m.get("thermal_distance_interval_mm", 1.0)
      sensor_sample_rate_hz = m.get("sensor_sample_rate_hz", 100)
      result = []
      for start in range(0, len(frames), window_size):
          window = frames[start : start + window_size]
          if len(window) < 10:
              continue
          features = extract_features_for_frames(window, angle_target_deg)
          dummy = Session(
              session_id="__window__",
              operator_id="",
              start_time=datetime.now(),
              weld_type=weld_type,
              thermal_sample_interval_ms=thermal_sample_interval_ms,
              thermal_directions=thermal_directions,
              thermal_distance_interval_mm=thermal_distance_interval_mm,
              sensor_sample_rate_hz=sensor_sample_rate_hz,
              frames=window,
              frame_count=len(window),
              disable_sensor_continuity_checks=True,
          )
          score = score_session(dummy, features, thresholds)
          result.append({"frame_start": start, "frame_end": start + len(window) - 1, "wqi": score.total})
      return result
  ```

  **Git Checkpoint:** `git add backend/scoring/rule_based.py && git commit -m "step 2: add score_frames_windowed"`

  **✓ Verification Test**

  1. Import chain: `cd backend && python -c "from services.scoring_service import get_session_score; from scoring.rule_based import score_frames_windowed; print('import ok')"`
  2. Unit test: result non-empty, has frame_start/frame_end/wqi; variation or single window.
  3. **Rule-set parity:** `score_session` selects rules via **thresholds** only. With aluminum thresholds (travel_speed_consistency set): `full = score_session(session, features, thresholds)`; `result = score_frames_windowed(frames, thresholds, session_metadata, ...)`. First window: `w = frames[:50]`, `f = extract_features_for_frames(w, ...)`, `sw = score_session(dummy, f, thresholds)`. Assert `len(sw.rules) == len(full.rules)` — both use same thresholds. session_metadata can use session.weld_type etc. for consistency.

---

### Phase 3 — Session Model Fields

- [ ] 🟥 **Step 3: Add WQI fields to Session model**

  **Idempotent:** Yes.

  **Implementation:** In `backend/models/session.py`, after `score_total`:
  ```python
  wqi_timeline: Optional[List[dict]] = Field(default=None, description="[{frame_start, frame_end, wqi}]")
  mean_wqi: Optional[float] = Field(default=None)
  median_wqi: Optional[float] = Field(default=None)
  min_wqi: Optional[int] = Field(default=None)
  max_wqi: Optional[int] = Field(default=None)
  wqi_trend: Optional[str] = Field(default=None, description="improving|degrading|stable")
  ```

  **Git Checkpoint:** `git add backend/models/session.py && git commit -m "step 3: add wqi fields to Session"`

  **✓ Verification Test:** `s.model_copy(update={'mean_wqi': 60.0})`; assert `s2.mean_wqi == 60.0`

---

- [ ] 🟥 **Step 4: Add WQI columns to SessionModel + migration**

  **Idempotent:** Yes.

  **Pre-Read Gate:** `cd backend && alembic current` — use printed head as `down_revision`.

  **Implementation:**

  1. Create `backend/alembic/versions/014_add_wqi_windowed_columns.py` with `down_revision` from `alembic current`. Add columns: wqi_timeline (JSON), mean_wqi (Float), median_wqi (Float), min_wqi (Integer), max_wqi (Integer), wqi_trend (String(32)).

  2. SessionModel: add the 6 columns after `score_total`.

  3. **to_pydantic():** Add 6 kwargs to `Session(...)` after `score_total=self.score_total,` and before `process_type=`:
     ```python
     wqi_timeline=getattr(self, "wqi_timeline", None),
     mean_wqi=getattr(self, "mean_wqi", None),
     median_wqi=getattr(self, "median_wqi", None),
     min_wqi=getattr(self, "min_wqi", None),
     max_wqi=getattr(self, "max_wqi", None),
     wqi_trend=getattr(self, "wqi_trend", None),
     ```

  4. **from_pydantic():** Use anchor from Pre-Flight #4. If `version=1,` exists in cls() call: insert the 6 new kwargs on the line immediately after `score_total=getattr(session, "score_total", None),` and before `version=1,`. If version=1 does not exist: insert the 6 new kwargs as the last kwargs before the closing `)` of the single `cls(...)` call. Exact lines to insert:
     ```python
     wqi_timeline=getattr(session, "wqi_timeline", None),
     mean_wqi=getattr(session, "mean_wqi", None),
     median_wqi=getattr(session, "median_wqi", None),
     min_wqi=getattr(session, "min_wqi", None),
     max_wqi=getattr(session, "max_wqi", None),
     wqi_trend=getattr(session, "wqi_trend", None),
     ```
     No **kwargs unpacking; one kwarg per line.

  **Git Checkpoint:** `git add backend/database/models.py backend/alembic/versions/014_*.py && git commit -m "step 4: add wqi columns to SessionModel"`

  **✓ Verification Test:**

  1. `alembic upgrade head && alembic downgrade -1 && alembic upgrade head`
  2. **to_pydantic:** Load SessionModel with wqi_timeline set; `s = m.to_pydantic()`; `assert s.wqi_timeline is not None`
  3. **from_pydantic:** `session = Session(..., wqi_timeline=[{"frame_start":0,"frame_end":49,"wqi":60}], ...)`; `m = SessionModel.from_pydantic(session)`; `assert m.wqi_timeline is not None`

  **Human Gate:** `[PHASE A COMPLETE — WAITING FOR HUMAN TO CONFIRM MIGRATION 014 SAFE TO RUN]`

---

### Phase 4 — Scoring Service + Persistence

- [ ] 🟥 **Step 5: Extend scoring_service and wire route persistence**

  **Idempotent:** Yes.

  **Pre-Read Gate:**
  - `grep -n "extract_features\|score_session" backend/routes/sessions.py` — only the score endpoint block should reference them; if others do, do NOT remove imports.
  - `grep -n "if session_model.status == SessionStatus.COMPLETE" backend/routes/sessions.py` — identify persistence block start for end-anchor.

  **Implementation:**

  **5A. models/scoring.py**

  Add optional fields **after** `rules: List[ScoreRule]`, **before** any `model_config`, `@validator`, or end of class. SessionScore currently has no validators; add after the last field:
  ```python
  wqi_timeline: Optional[List[dict]] = None
  mean_wqi: Optional[float] = None
  median_wqi: Optional[float] = None
  min_wqi: Optional[int] = None
  max_wqi: Optional[int] = None
  wqi_trend: Optional[str] = None
  ```

  **5B. scoring_service.py**

  Add `from typing import Optional`, `import statistics`, `from scoring.rule_based import score_frames_windowed`.

  **Updated full signature (keyword-only for new params — safe for existing call sites):**
  ```python
  def get_session_score(
      session_id: str,
      db: "DBSession",
      *,
      include_windowed: bool = False,
      session_model: Optional["SessionModel"] = None,
      session: Optional["Session"] = None,
  ) -> SessionScore:
  ```
  The `*` forces all new params to be keyword-only; existing `get_session_score(session_id, db)` calls remain valid.

  **Explicit flow (frames and session binding):**

  1. If `session_model is None`: fetch from db as now; raise if not found.
  2. `frames = getattr(session_model, "frames", None) or []`
  3. If `len(frames) < 10`: raise ValueError (as now).
  4. If `session is None`: `session = session_model.to_pydantic()` (only when not passed — avoids double conversion when route passes session).
  5. `process_type = getattr(session_model, "process_type", None) or "mig"`
  6. `thresholds = get_thresholds(db, process_type)`
  7. `features = extract_features(session, angle_target_deg=thresholds.angle_target_degrees if thresholds else 45)`
  8. `score = score_session(session, features, thresholds)`
  9. If `include_windowed` and `len(frames) >= 10`:
     - `angle_target_deg = thresholds.angle_target_degrees if thresholds else 45`
     - `session_metadata = {"weld_type": session.weld_type, "thermal_sample_interval_ms": session.thermal_sample_interval_ms, "thermal_directions": session.thermal_directions, "thermal_distance_interval_mm": session.thermal_distance_interval_mm, "sensor_sample_rate_hz": session.sensor_sample_rate_hz}`
     - `frame_list = [f.to_pydantic() for f in frames]`
     - `timeline = score_frames_windowed(frame_list, thresholds, session_metadata, angle_target_deg=angle_target_deg, window_size=50)`
     - If timeline: mean, median, min, max; trend if `len(timeline) >= 4`: first_half = wqis[:n//2], second_half = wqis[n//2:]; diff = mean(second_half) - mean(first_half). Unequal lengths are expected and correct — do not balance them. Then `score = score.model_copy(update={...})`
  10. Return `score`.

  **5C. routes/sessions.py**

  **Before replacement:** Run `grep -c "score_session(session, features" backend/routes/sessions.py`. Must return 1. If 2+ → report to human; do not replace.

  **Block boundaries (content anchors, no line numbers):**

  - **Start:** First line that is `session = session_model.to_pydantic()`
  - **End:** Last line that is `score = score_session(session, features, thresholds)`
  - The block does NOT include the blank line or the comment `# Lazy persistence:` or the `if session_model.status == ...` block.

  Replace the block (start through end inclusive) with:
  ```python
  session = session_model.to_pydantic()
  score = get_session_score(
      session_id, db,
      include_windowed=True,
      session_model=session_model,
      session=session,
  )
  ```
  (Keyword args required; signature uses `*` for keyword-only.)

  **Import removal:** Only if `grep` shows extract_features and score_session are unused elsewhere: remove `from features.extractor import extract_features` and `from scoring.rule_based import score_session`.

  **Verification after refactor:** `session` must remain in scope for `_build_alerts_from_frames(list(session.frames))` and `score_session_decomposed(..., list(session.frames), ...)`. The refactored block keeps `session = session_model.to_pydantic()` as the first line, so `session` is in scope.

  **Persistence block:** Find the block containing `session_model.score_total = score.total` (inside the `if session_model.status == SessionStatus.COMPLETE.value and session_model.score_total is None ...`). Add immediately after `session_model.score_total = score.total`:
  ```python
  session_model.wqi_timeline = score.wqi_timeline
  session_model.mean_wqi = score.mean_wqi
  session_model.median_wqi = score.median_wqi
  session_model.min_wqi = score.min_wqi
  session_model.max_wqi = score.max_wqi
  session_model.wqi_trend = score.wqi_trend
  ```

  **5D. routes/dev.py and backfill** — Out of scope. Do not modify.

  **Git Checkpoint:** `git add backend/models/scoring.py backend/services/scoring_service.py backend/routes/sessions.py && git commit -m "step 5: windowed WQI in scoring_service, persist in score endpoint"`

  **✓ Verification Test**

  1. `pytest tests/test_score_session.py tests/test_scoring_thresholds.py tests/test_trajectory_service.py -v`
  2. **Frame type parity:** `frame_list = [f.to_pydantic() for f in session_model.frames]`; `assert type(frame_list[0]) == type(session.frames[0]), "FrameModel.to_pydantic() type mismatch"`
  3. `GET /sessions/{id}/score` for COMPLETE session with 100+ frames → response includes wqi_timeline, mean_wqi, etc.
  4. DB: `SELECT wqi_timeline, mean_wqi FROM sessions WHERE session_id = '...'` non-null after first score.
  5. No NameError for `session` in _build_alerts_from_frames or score_session_decomposed.

---

## Regression Guard

| System | Check |
|--------|-------|
| Trajectory | `pytest tests/test_trajectory_service.py` |
| Narrative | `pytest tests/test_narrative*` |
| GET /score | Returns total, rules, optionally wqi_* |
| Test count | ≥ Pre-Flight baseline |

---

## Rollback Procedure

```bash
git revert <step5_commit>
cd backend && alembic downgrade -1
git revert <step4_commit> <step3_commit> <step2_commit> <step1_commit>
python -m pytest -q --tb=no | tail -1
```

---

## Success Criteria

| Feature | Verification |
|---------|--------------|
| extract_features_for_frames == extract_features | Unit test Step 1 |
| score_frames_windowed returns varying WQIs | Unit test Step 2 |
| Dummy Session passes validators (session_metadata) | Step 2 |
| Windowed and full use same rule set | Rule-set parity test Step 2 |
| Session.wqi_* optional fields | model_copy test |
| to_pydantic and from_pydantic map new columns | Step 4 verification |
| frame_list type matches session.frames type | Step 5 assertion |
| GET /score persists wqi_* | API + DB check |
| session in scope, no double to_pydantic | Route passes session |
| Trajectory/narrative unchanged | Regression tests |

---

⚠️ **Do not mark a step Done until its verification test passes.**
⚠️ **Do not proceed past a Human Gate without explicit human input.**
