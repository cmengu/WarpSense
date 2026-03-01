# Alert Correction Status — Backend + Frontend Integration (Revised v3)

**Type:** Feature / Blocker resolution  
**Priority:** Normal  
**Effort:** Medium  
**Labels:** `backend` `frontend` `alerts` `demo`

---

## TL;DR

Add `corrected: bool` and `corrected_in_seconds: float | null` to `AlertPayload`; compute them only for rules 1–2 by scanning subsequent frames (ordered by `timestamp_ms`); force `corrected=False` for rules 3–11. Wire frontend `AlertCard` to show badge states. Single implementation location: `alert_service.py` only. No new modules.

---

## Critical Decisions (Fixed — No Alternatives)

| Decision | Value | Rationale |
|----------|-------|-----------|
| Correction logic location | `backend/services/alert_service.py` only | DO NOT create `alert_correction.py`. All logic lives in `alert_service.py`. |
| Rules 1–2 | Implement real in-range checks | Use thresholds from `alert_thresholds.json`. |
| Rules 3–11 | Force `corrected=False` | No computation. No "no re-trigger" heuristic. |
| Frame scan order | By `timestamp_ms > alert.timestamp_ms` ascending | Do NOT use `frame_index + 1`. |
| Threshold loading | `from realtime.alert_engine import load_thresholds` | Same function as AlertEngine. |
| `_ns_asymmetry_from_frame_data` | Use existing helper in `alert_service.py` | Accepts plain dict with key `thermal_snapshots`. Returns float. No ORM. |
| `_enrich_alerts_with_correction` | Accepts `cfg: dict` as third param | Tests pass pre-loaded cfg. `run_session_alerts` loads cfg once and passes it. No config_path in helper. |
| AlertPayload mutability | Implement both code paths | Pre-flight grep determines which: direct mutation OR model_copy. Plan shows both. |

---

## Pre-Flight (Run Before Any Code Changes)

**1. Threshold keys — confirm in config:**
```bash
grep -E "nominal_travel_angle|angle_deviation_warning|thermal_ns_warning" backend/config/alert_thresholds.json
```
Expected: all three keys present. If any missing → STOP.

**2. Circular import — confirm no dependency:**
```bash
grep -rn "from services.alert_service\|import alert_service" backend/realtime/
```
Expected: no matches. If matches → STOP.

**3. _ns_asymmetry_from_frame_data — confirm plain dict contract:**
```bash
grep -n "def _ns_asymmetry_from_frame_data" backend/services/alert_service.py
```
Read the full function body. It MUST:
- Accept a single argument of type `dict` (frame_data).
- Use only `frame_data.get("thermal_snapshots")` and nested `.get()` — no ORM, no `fm.` attributes.
- Return a `float` (north minus south at 10mm, or 0 if no thermal).

If it uses any ORM or non-dict access → STOP; tests will crash. Current implementation meets this.

**4. AlertPayload mutability:**
```bash
grep -n "frozen|model_config|ConfigDict" backend/realtime/alert_models.py
```
Record result. If `frozen=True` present → use model_copy path in Step 2. If absent → use direct mutation path.

**5. alert_service.py — variable names:**
Read `backend/services/alert_service.py` in full. Locate: `config_path` (lines 56–60), `frame_models`, `alerts`. Confirm names before editing.

---

## Backend: Verified Premises

**`run_session_alerts` structure:**
- Variable: `frame_models` (list of FrameModel).
- Variable: `config_path` (Path to alert_thresholds.json).
- Returns `list[AlertPayload]`.

**`_enrich_alerts_with_correction` signature (final):**
```python
def _enrich_alerts_with_correction(
    alerts: list[AlertPayload],
    frame_items: list[tuple[float, dict]],
    cfg: dict,
) -> None:
```
Receives pre-loaded `cfg` from `load_thresholds`. No config_path. `run_session_alerts` calls `load_thresholds(str(config_path))` once and passes `cfg` to the helper. Tests load cfg from `Path(__file__).resolve().parent.parent / "config" / "alert_thresholds.json"` and pass it.

---

## 1. Model — `backend/realtime/alert_models.py`

```python
corrected: bool = Field(False, description="Parameter returned to range before session end")
corrected_in_seconds: Optional[float] = Field(
    None,
    description="Seconds from alert to first in-range frame. Set only when corrected=True.",
)
```

---

## 2. Correction Logic — `backend/services/alert_service.py`

**Imports to add:**
```python
from realtime.alert_engine import load_thresholds
```

**Helper — inline in alert_service.py:**
```python
def _is_in_range_for_rule(
    rule_triggered: str,
    fd: dict,
    cfg: dict,
    ns_asymmetry: float,
) -> bool:
    """
    Returns True if frame data indicates parameter is back in acceptable range.
    Only rule1 and rule2 implemented. Rules 3–11 always return False.
    """
    if rule_triggered == "rule1":
        return abs(ns_asymmetry) < float(cfg["thermal_ns_warning"])
    if rule_triggered == "rule2":
        angle = fd.get("travel_angle_degrees")
        if angle is None:
            return False
        nominal = float(cfg["nominal_travel_angle"])
        dev = abs(float(angle) - nominal)
        return dev < float(cfg["angle_deviation_warning"])
    return False
```

**Post-process — `_enrich_alerts_with_correction` (accepts cfg, not config_path):**
```python
def _enrich_alerts_with_correction(
    alerts: list[AlertPayload],
    frame_items: list[tuple[float, dict]],
    cfg: dict,
) -> None:
    """Mutates alerts in place. frame_items: (timestamp_ms, frame_data) sorted by ts asc."""
    for i, a in enumerate(alerts):  # Use index, not list.index(a), to avoid identity bug with duplicate alerts
        if a.rule_triggered not in ("rule1", "rule2"):
            continue
        a_ts = a.timestamp_ms
        for ts, fd in frame_items:
            if ts <= a_ts:
                continue
            ns = _ns_asymmetry_from_frame_data(fd)
            if _is_in_range_for_rule(a.rule_triggered, fd, cfg, ns):
                sec = (ts - a_ts) / 1000.0
                # PRE-FLIGHT: if grep found frozen=True in alert_models.py → use BLOCK A. Else → use BLOCK B.
                # BLOCK A (frozen model):
                #   alerts[i] = a.model_copy(update={"corrected": True, "corrected_in_seconds": sec})
                # BLOCK B (mutable model):
                a.corrected = True
                a.corrected_in_seconds = sec
                break
```

**Implementer:** Run pre-flight step 4. If `frozen=True` found: uncomment BLOCK A, comment/remove BLOCK B. If not: keep BLOCK B, remove BLOCK A.

**In `run_session_alerts`, after the engine loop, before `return alerts`:**
```python
cfg = load_thresholds(str(config_path))
frame_items = []
for fm in frame_models:
    fd = dict(fm.frame_data)
    ts = fd.get("timestamp_ms") or fm.timestamp_ms
    frame_items.append((float(ts), fd))
_enrich_alerts_with_correction(alerts, frame_items, cfg)
return alerts
```

---

## 3. Tests — `backend/tests/test_alert_correction.py` (new)

**Import:** `from services.alert_service import _enrich_alerts_with_correction` (leading underscore does not prevent import in Python).

**Config path for tests (no filesystem mock; use real file in repo):**
```python
import pytest
from pathlib import Path

from realtime.alert_engine import load_thresholds
from realtime.alert_models import AlertPayload
from services.alert_service import _enrich_alerts_with_correction, _ns_asymmetry_from_frame_data

# Path from backend/tests/ to backend/config/
TEST_CFG = load_thresholds(str(Path(__file__).resolve().parent.parent / "config" / "alert_thresholds.json"))
```

All tests call `_enrich_alerts_with_correction(alerts, frame_items, TEST_CFG)` with plain dicts. No FrameModel. No database.

| Test | Purpose |
|------|---------|
| `test_rule1_corrected_when_subsequent_frame_in_range` | Alert at t=100, frame dict at t=200 with ns in-range → corrected=True, corrected_in_seconds=0.1 |
| `test_rule2_corrected_when_angle_returns_to_nominal` | Alert at t=100, frame dict at t=150 with angle in range → corrected=True |
| `test_rule1_not_corrected_when_no_subsequent_in_range` | Alert at t=100, all later frame dicts out of range → corrected=False |
| `test_alert_on_last_frame_no_crash` | Alert on last frame (frame_items empty or none with ts > a_ts); loop terminates, corrected=False |
| `test_rules_3_to_11_always_false` | rule_triggered in (rule3, porosity, ...) → corrected remains False |

**Derive in-range and out-of-range values from TEST_CFG. Never hardcode threshold-adjacent numbers.** In-range ns: `float(TEST_CFG["thermal_ns_warning"]) - 1` (e.g. 24). Out-of-range ns: `float(TEST_CFG["thermal_ns_warning"]) + 1` (e.g. 26). Build thermal frame dict with north/south such that north-minus-south equals the chosen ns. In-range angle: `float(TEST_CFG["nominal_travel_angle"])` (deviation 0). Out-of-range angle: `float(TEST_CFG["nominal_travel_angle"]) + float(TEST_CFG["angle_deviation_warning"]) + 1` (deviation above threshold).

---

## 4. Regression verification (mandatory)

```bash
pytest backend/tests/test_scoring.py backend/tests/test_report_summary.py backend/tests/test_alert_correction.py -v
```

```bash
curl -s "http://localhost:8000/api/sessions/sess_novice_aluminium_001_001/alerts" | python3 -m json.tool | grep -E "corrected|corrected_in"
```

---

## Frontend

### 5. API types — `my-app/src/lib/api.ts`

```ts
corrected?: boolean;
corrected_in_seconds?: number | null;
```

### 6. AlertCard — locate by function name

**Instruction:** Search for `function AlertCard` in:
- `my-app/src/app/demo/[sessionIdA]/[sessionIdB]/page.tsx`
- `my-app/src/app/compare/[sessionIdA]/[sessionIdB]/page.tsx`

**Grep to find all call sites before editing:**
```bash
grep -rn "<AlertCard" my-app/src/app/
```
Update every occurrence found. Do NOT assume a fixed count. Update every call site.

**Prop:** Add optional `currentTimestamp?: number | null` with default `null`.

**Per-file variable to pass:**

| File | Variable | Definition |
|------|----------|------------|
| `demo/.../page.tsx` | `floorTs` | `currentTimestamp ?? firstTimestamp ?? 0` (already defined) |
| `compare/.../page.tsx` | `floorTs` | `currentTimestamp ?? firstTimestamp ?? 0` (already defined) |

At each AlertCard call site, add `currentTimestamp={floorTs}`. Both pages define `floorTs`; use it so the badge sees the effective playback position (handles null currentTimestamp at session start).

**Atomic change:** Update AlertCard signature + badge logic + all call sites in the same step. Do not split.

### 7. Badge logic (TypeScript)

```ts
const sec = alert.corrected_in_seconds ?? 0;
// Intentional: corrected=True + corrected_in_seconds=null → sec=0 → treat as "corrected immediately"
const correctedNow =
  (alert.corrected ?? false) &&
  currentTimestamp != null &&
  currentTimestamp >= alert.timestamp_ms + sec * 1000;

if (correctedNow) {
  // Green: "✓ corrected in X.Xs"
} else if (alert.corrected && currentTimestamp != null && currentTimestamp < alert.timestamp_ms + sec * 1000) {
  // Amber: "correcting..."
} else {
  // Red: "✗ no correction"
}
```

Use `number | null` directly. Do NOT use `parseFloat`.

### 8. TypeScript compile verification

```bash
cd my-app && npx tsc --noEmit 2>&1 | grep -c "error TS" || true
```
If count > 0:
```bash
cd my-app && npx tsc --noEmit 2>&1 | grep "error TS"
```
Fix all errors. Re-run until count is 0. Do NOT use `head -20` — show full error set.

### 9. Demo page verification

Navigate to `/demo/sess_novice_aluminium_001_001/sess_expert_aluminium_001_001`. Confirm alerts display. Without rule1/rule2 corrections in data, most badges show "✗ no correction" — expected.

---

## Implementation order

1. Backend model — add fields; run pytest test_scoring, test_report_summary.
2. Backend correction — add `_is_in_range_for_rule`, `_enrich_alerts_with_correction` (with cfg param), wire in `run_session_alerts`; implement mutation path per pre-flight; add `test_alert_correction.py` with TEST_CFG and all 5 cases.
3. Regression + API verification — pytest, curl.
4. Frontend types — extend AlertPayload in api.ts.
5. Demo AlertCard — grep for all call sites; add prop, badge logic, pass `currentTimestamp={floorTs}` at each.
6. Compare AlertCard — same (all call sites in one step).
7. TypeScript compile — `grep -c "error TS"` then `grep "error TS"`; fix until 0.
8. Demo page visual check.
9. Frontend test for amber state (optional).

---

## Definition of Done

- [ ] `AlertPayload` has `corrected` and `corrected_in_seconds` with defaults
- [ ] `_enrich_alerts_with_correction` accepts `cfg: dict`; tests use `TEST_CFG` from real config file
- [ ] `_ns_asymmetry_from_frame_data` confirmed plain-dict; no ORM in tests
- [ ] Mutation path matches pre-flight (direct or model_copy)
- [ ] All AlertCard call sites updated (grep-verified, not assumed count)
- [ ] Demo passes `floorTs`; compare passes `floorTs`
- [ ] `npx tsc --noEmit` reports 0 errors (no truncation)
- [ ] Demo page renders and shows alerts
- [ ] No `alert_correction.py` created
