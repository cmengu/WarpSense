# System 1 — Rule-Based Edge Alert — Implementation Plan

**Overall Progress:** 85% (Phase 0–3 implemented; UI at /realtime)

---

## TLDR

Build a self-contained, real-time alert module that runs on-device, reads incoming weld frames, evaluates three rules on every frame (Rule 1 NS thermal, Rule 2 angle, Rule 3 speed), and fires directional corrections in under 50ms. Zero database, LLM, or network calls. Data fixes first, then alert engine with three independent suppression counters, then minimal web UI with NS thermal bar, travel angle gauge, alert panel. Run `preflight_check.py` morning of April 9.

---

## Critical Decisions

- **Time-based suppression:** Use `time.time()` and `suppression_ms`, not frame index. Changing simulate script frame rate would otherwise silently break suppression.
- **±30°C NS bar range:** Values above ±30°C clip to edge with red/blue "MAX" label. Prevents novice 127°C from pegging the bar; keeps expert 0–16°C meaningful.
- **AlertEngine fails on null thresholds:** Raise `ValueError` on startup if any threshold is null or file missing — forces calibration before use.
- **No angle_degrees in FrameInput:** Work angle is unused by current rules. Carry no phantom fields.
- **One alert per frame:** Highest severity wins across all three rules. If two rules fire at the same severity, return the one with the lower rule number — Rule 1 over Rule 2 over Rule 3. Each rule has its own suppression counter.
- **HTTP POST IPC:** Simulate script and FastAPI run in separate processes. No shared in-memory queue. Simulate POSTs alerts to `/internal/alert`; FastAPI broadcasts to WebSocket clients.

---

## Agent Failure Protocol

1. A verification command fails → read the full error output.
2. Cause is unambiguous → make ONE targeted fix → re-run the same verification command.
3. If still failing after one fix → **STOP**. Report: (a) command run, (b) full error verbatim, (c) fix attempted, (d) why you cannot proceed.
4. Never attempt a second fix without human instruction.
5. Never modify files not named in the current step.

---

## Pre-Flight — Run Before Any Code Changes

Read [backend/models/frame.py](backend/models/frame.py), [backend/data/mock_sessions.py](backend/data/mock_sessions.py) (aluminum generators) in full. List:

1. Every field currently defined on `Frame`, in order
2. Exact current `Frame(...)` call sites in `_generate_stitch_expert_frames` and `_generate_continuous_novice_frames` (line numbers)
3. Whether `backend/config/` or `backend/realtime/` exists
4. Every file that imports from `models.frame` or `data.mock_sessions`

**Automated checks (all must pass before Step 1):**

- [ ] `cd backend && source venv/bin/activate && python -m scripts.verify_aluminum_mock` exits 0 (Phase 0a done)
- [ ] `Frame` model does NOT have `ctwd_mm` field yet
- [ ] `backend/config/` does not exist
- [ ] `backend/realtime/` does not exist

---

## Tasks

### Phase 0 — Data Fixes (MUST complete before alert engine)

**Goal:** Thermal every frame (done), ctwd_mm on Frame and emitted, thresholds calibrated and human-approved.

---

- [x] **Step 0a: Thermal Every Frame** — Done

  Already implemented: `is_thermal_frame = True`, `thermal_interval_sec = 0.01` in both aluminum generators. `verify_aluminum_mock` passes.

---

- [ ] **Step 0b: Emit ctwd_mm on Frame** — Critical

  **Context:** Both aluminum generators track `ctwd_mm` internally for thermal/porosity physics. Frame model lacks it; alert Rule 4 (future) needs it. No fallback — explicit `Optional`, None when absent.

  **Pre-Read Gate:**
  - `grep -n 'class Frame' backend/models/frame.py` → exactly 1 match
  - `grep -n 'travel_angle_degrees' backend/models/frame.py` → exists; anchor for insertion
  - `grep -n 'Frame(' backend/data/mock_sessions.py` → two call sites (expert ~354, novice ~481)

  **Anchor Uniqueness Check:**
  - Insert `ctwd_mm` after `travel_angle_degrees` in Frame model
  - Add `ctwd_mm=ctwd_mm` to both Frame(...) calls in mock_sessions

  **Self-Contained Rule:** All code below is complete. No placeholders.

  **File 1: backend/models/frame.py**

  After `travel_angle_degrees` field (before `@computed_field`), add:

  ```python
  ctwd_mm: Optional[float] = Field(
      None,
      ge=8.0,
      le=30.0,
      description="Contact tip-to-work distance in mm. Expert nominal 15mm. Future Rule 4.",
  )
  ```

  **File 2: backend/data/mock_sessions.py**

  In `_generate_stitch_expert_frames`, add to Frame(...) call:
  `ctwd_mm=ctwd_mm,`

  In `_generate_continuous_novice_frames`, add to Frame(...) call:
  `ctwd_mm=ctwd_mm,`

  **What it does:** Frame gains optional ctwd_mm; aluminum generators emit it. No fallback.

  **Assumptions:** Frame validators do not reject unknown kwargs. Pydantic v2 accepts new optional fields.

  **Risks:**
  - Existing code constructing Frame without ctwd_mm → mitigation: Optional with None default
  - Serialization/API may need updating → mitigation: optional field, existing responses unchanged

  **Verification Test:**

  **Action:** `cd backend && source venv/bin/activate && python -c "
  from models.frame import Frame
  from data.mock_sessions import _generate_stitch_expert_frames
  frames = _generate_stitch_expert_frames(0, 10)
  assert all(hasattr(f, 'ctwd_mm') for f in frames)
  assert frames[0].ctwd_mm is not None and 12 <= frames[0].ctwd_mm <= 17
  print('OK')
  "`

  **Expected:** `OK`

  **Fail:** AttributeError → ctwd_mm not added to Frame; None/range → generators not passing ctwd_mm

---

- [ ] **Step 0c: Calibrate Thresholds** — Critical (Split Operation)

  **Context:** Thresholds must come from real expert/novice data, not hand-tuning. Script runs 30+30 sessions, computes p95/p99, outputs JSON. Human reviews against reference table before approval. No stub config file until Phase B — avoids AlertEngine loading null schema during Phase 1 development.

  **Phase A — Create calibration script only (no config file)**

  **Pre-Read Gate:**
  - `grep -n 'extract_features\|north_south_delta\|travel_angle' backend/features/extractor.py` — confirm feature extraction exists
  - `grep -n 'north.*south\|direction' backend/models/thermal.py` — confirm TemperaturePoint.direction

  **Create:**

  1. `backend/scripts/calibrate_alert_thresholds.py`:
     - At top of file, docstring or inline comment with the exact JSON schema (for Phase B). Example:
       ```python
       # Output schema (written only in Phase B with --write):
       # { "thermal_ns_warning": float, "thermal_ns_critical": float, "angle_deviation_warning": float,
       #   "angle_deviation_critical": float, "speed_drop_warning_pct": float, "speed_drop_critical_pct": float,
       #   "nominal_travel_angle": 12.0, "suppression_ms": 1000 }
       ```
     - Import: `from data.mock_sessions import _generate_stitch_expert_frames, _generate_continuous_novice_frames`
     - Build 30 expert: for i in range(30): `frames = _generate_stitch_expert_frames(session_index=i, num_frames=1500)`. Build 30 novice: for i in range(30): `frames = _generate_continuous_novice_frames(session_index=i, num_frames=1500)`. Iterate frames directly: `for frame in frames:` — no Session construction needed.
     - Per-frame: `ns_asymmetry` from thermal_snapshots[0] north−south; `travel_angle_deviation` = |travel_angle_degrees − 12|; `speed_change_pct` = (current_speed - speed_10_frames_ago) / speed_10_frames_ago * 100 when speed_10_frames_ago > 0, else 0. Negative = deceleration. Use the same formula in `frame_buffer` (Step 3).
     - Compute expert p95 (warning), p99 (critical) for each metric
     - Print PASS/WARN against reference: thermal_ns 6–14°C, angle_dev 3–7°, speed_drop 6–12%
     - Do NOT create `backend/config/` or any JSON file. Do NOT write JSON until human approves.

  **Phase A Verification:** Script runs, prints three metric values and PASS/WARN. `backend/config/` and `backend/config/alert_thresholds.json` do NOT exist.

  **Human Gate — Phase A complete:**
  Output `"[PHASE A COMPLETE — WAITING FOR HUMAN TO REVIEW CALIBRATION OUTPUT AND APPROVE WRITE TO alert_thresholds.json]"` as the final line.
  Do not write any file until human confirms.

  **Phase B — Populate alert_thresholds.json after human approval**

  Only execute after human provides: "Approved — write thresholds" and confirms values are within reference ranges.

  Script adds `--write` flag. When `--write` passed and output PASS: create `backend/config/` if missing, write `backend/config/alert_thresholds.json` with computed values. Set `suppression_ms: 1000`, `nominal_travel_angle: 12.0`.

  **Phase B Verification:** `test -f backend/config/alert_thresholds.json && cat backend/config/alert_thresholds.json` shows no nulls. `cd backend && source venv/bin/activate && python -c "from realtime.alert_engine import AlertEngine; AlertEngine.load_thresholds('config/alert_thresholds.json')"` runs without ValueError (AlertEngine may not exist yet; if so, defer this check until Step 1).

---

### Phase 1 — Alert Engine

**Goal:** Three rules, three suppression counters, time-based suppression, push_frame &lt; 50ms p99, zero I/O.

---

- [ ] **Step 1: Create realtime module structure** — Non-critical

  **Create files:**
  - `backend/realtime/__init__.py` (empty or exports)
  - `backend/realtime/alert_models.py` — `FrameInput`, `AlertPayload` Pydantic models
  - `backend/realtime/frame_buffer.py` — 10-frame rolling buffer for speed_change_pct
  - `backend/realtime/alert_engine.py` — `AlertEngine` class, `push_frame`, `load_thresholds`
  - `backend/realtime/output_handler.py` — interface for console/WebSocket (HTTP POST)

  **FrameInput fields:** `frame_index`, `travel_angle_degrees`, `travel_speed_mm_per_min`, `ns_asymmetry`. No angle_degrees.

  **AlertPayload schema:** `{ "frame_index": int, "rule_triggered": str, "severity": str, "message": str, "correction": str, "timestamp_ms": float }`

  **Verification:** With config missing (before 0c Phase B): `AlertEngine.load_thresholds('config/alert_thresholds.json')` raises an error. With valid config (after 0c Phase B): loads and `AlertEngine` instantiates.

---

- [ ] **Step 2: Implement AlertEngine rules** — Critical

  **Context:** Core logic. Three rules, highest severity wins. Time-based suppression per rule.

  **Pre-Read Gate:**
  - `grep -n 'suppression_ms\|thermal_ns' backend/config/alert_thresholds.json` — schema (file must exist from 0c Phase B)
  - Confirm `FrameInput` has exact fields specified in issue

  **Implement in alert_engine.py:**
  - `_suppress_rule1_until`, `_suppress_rule2_until`, `_suppress_rule3_until` (epoch ms)
  - `now_ms = time.time() * 1000`
  - Rule 1: ns_asymmetry vs thermal_ns_warning/critical. Correction: "Reduce push angle — tilt back 3°" (positive) / "Increase push angle — tilt forward 3°" (negative)
  - Rule 2: |travel_angle − 12| vs angle_deviation_warning/critical. Correction: if travel_angle > 12° → "Travel angle too steep — reduce to 12°"; if travel_angle < 12° → "Travel angle too shallow — increase to 12°"
  - Rule 3: speed_change_pct over 10-frame buffer vs speed_drop_warning_pct/critical. Correction: "Slowing down — maintain pace" / "Speed critical — increase to 420mm/min"
  - One alert per frame; if multiple fire, highest severity wins. Tiebreak: same severity → lower rule number wins (Rule 1 over Rule 2 over Rule 3).
  - On fire: `_suppress_ruleN_until = now_ms + suppression_ms`

  **Edge cases:** Empty thermal snapshots → ns_asymmetry 0.0. Missing direction → 0.0, log warning.

  **Verification:** Unit test with ns +20 → tilt back; ns −20 → tilt forward.

---

- [ ] **Step 3: Implement frame_buffer for speed change** — Non-critical

  **Context:** Rule 3 needs rolling 10-frame window for speed_change_pct. Same formula as calibration script (Step 0c).

  **Formula:** `speed_change_pct = (current_speed - speed_10_frames_ago) / speed_10_frames_ago * 100` when speed_10_frames_ago > 0; else 0. Negative = deceleration.

  **Implement:** Append frame speed to rolling buffer (max 11 values). When buffer has 11+ entries, compute pct from current (index -1) vs entry at index -11. Handle &lt; 10 frames: return 0 or None.

  **Verification:** Unit test with known speed sequence; assert correct pct.

---

- [ ] **Step 4: Benchmark push_frame** — Critical

  **Context:** Must complete under 50ms p99.

  **Implement:** In `tests/test_alert_engine.py`, benchmark 1000 `push_frame` calls. Loop i from 0 to 999; for each call use FrameInput `frame_index=i, travel_angle_degrees=18.0, travel_speed_mm_per_min=300.0, ns_asymmetry=20.0`. Use a fresh AlertEngine instance per call so suppression from a previous alert does not block rule evaluation — otherwise after the first alert fires, suppression would short-circuit the next 999 calls and the benchmark would only measure the fast early-exit path, not the full rule logic. Assert p99 &lt; 0.05 s.

  **Verification:** `cd backend && source venv/bin/activate && pytest tests/test_alert_engine.py -v -k benchmark` (or equivalent). Pass.

---

- [ ] **Step 5: simulate_realtime.py script** — Non-critical

  **Context:** Feeds frames to AlertEngine. Supports `--mode expert|novice` so preflight_check can compare alert rates. Supports `--output console|websocket`.

  **Implement:**
  - `--mode expert` — load aluminum stitch expert frames
  - `--mode novice` — load aluminum continuous novice frames
  - `--frames N` — stop after N frames and exit cleanly. Default: run full session (1500 frames). When used with `--loop`, limits frames per loop iteration, not total across restarts.
  - `--output console` — print alerts to stdout
  - `--output websocket` — POST frame data to `http://localhost:8000/internal/frame` every 3rd frame only (10fps; 30fps synchronous POSTs would block and make loop choppy). POST alerts to `http://localhost:8000/internal/alert` when alert fires (requires backend running)
  - `--crash-at N` — at frame index N, raise an unhandled exception (for preflight loop-restart test). Log crash, then `--loop` catches and restarts
  - For each frame: extract ns_asymmetry from thermal_snapshots[0], build FrameInput, push_frame
  - `--loop`: on session complete or exception, log "Restarting session", wait 2s, restart from frame 0
  - Console output format for each alert (when `--output console`): `ALERT frame={frame_index} rule={rule_triggered} severity={severity} correction={correction}`. One line per alert. Preflight counts lines containing "ALERT" in stdout.

  **Verification:**
  - `cd backend && source venv/bin/activate && python -m scripts.simulate_realtime --mode expert --output console --frames 100` runs 100 frames without error
  - `python -m scripts.simulate_realtime --mode novice --output console --frames 100` runs 100 frames without error
  - Both modes produce different frame sequences (expert stitch, novice continuous)
  - `python -m scripts.simulate_realtime --mode novice --loop --crash-at 50 --output console` — run for 8 seconds, stdout contains "Restarting session" (crash at frame 50, loop restarts)

---

### Phase 2 — Demo Web UI

**Goal:** One HTML, one WebSocket. NS thermal bar (±30°C, MAX labels, 80ms transition), travel angle gauge, alert panel. Simulate and FastAPI run in separate processes; HTTP POST as IPC.

---

- [ ] **Step 6: WebSocket + HTTP POST IPC** — Critical

  **Context:** The simulate script and FastAPI run in separate processes. Do not use a shared in-memory queue. Use HTTP POST as IPC.

  **Implement:**

  1. **POST /internal/alert** (development only):
     - Accepts `AlertPayload` JSON body
     - Broadcasts to all active WebSocket connections
     - Add to a router mounted only when `ENV=development` or `DEBUG=1` — never expose in production
     - Response: 200 OK

  2. **POST /internal/frame** (development only):
     - Accepts `{ "frame_index": int, "ns_asymmetry": float, "travel_angle_degrees": float }`
     - Broadcasts to all active WebSocket connections
     - Same development-only router as /internal/alert
     - Response: 200 OK
     - Simulate script calls this every 3rd frame when `--output websocket` (10fps; avoids blocking loop). UI uses for bar/gauge

  3. **GET /config/thresholds** (development only):
     - Returns `alert_thresholds.json` as JSON. Same development-only router. UI fetches on load for gauge color bands (angle_deviation_warning, angle_deviation_critical).

  4. **GET /ws/realtime-alerts**:
     - WebSocket endpoint browsers connect to. Maintain `active_connections: List[WebSocket] = []` at module level.
     - Message schema: `{ "frame_index", "rule_triggered", "severity", "message", "correction", "timestamp_ms" }` for alerts; `{ "frame_index", "ns_asymmetry", "travel_angle_degrees" }` for frames

  5. **Connection management:** On WebSocket connect, append to `active_connections`. On disconnect (exception or close), remove. Use try/finally or disconnect handler.

  6. **Broadcast logic:** When POST /internal/alert or POST /internal/frame receives payload, iterate `active_connections`, call `await ws.send_text(json.dumps(payload))` for each. Catch and log per-connection errors; do not fail the POST if one client disconnects mid-send.

  7. **OutputHandler websocket mode (in simulate script):** When alert fires, call `requests.post('http://localhost:8000/internal/alert', json=payload_dict)` synchronously. Alerts fire at most ~3/sec; synchronous POST is acceptable.

  **Verification:**
  - Start backend with ENV=development
  - `curl -s http://localhost:8000/config/thresholds` returns JSON with `angle_deviation_warning` and `angle_deviation_critical`
  - `curl -X POST http://localhost:8000/internal/alert -H "Content-Type: application/json" -d '{"frame_index":0,"rule_triggered":"rule1","severity":"warning","message":"NS asymmetry","correction":"tilt back 3°","timestamp_ms":1234.5}'` returns 200
  - `curl -X POST http://localhost:8000/internal/frame -H "Content-Type: application/json" -d '{"frame_index":0,"ns_asymmetry":15.2,"travel_angle_degrees":14.0}'` returns 200
  - Connect `wscat -c ws://localhost:8000/ws/realtime-alerts`, then run both POST curls — wscat receives both JSON messages

---

- [ ] **Step 7: NS thermal bar component** — Critical

  **Cursor directive:** Display range ±30°C. Values &gt; +30°C clip to right edge, red "MAX". Values &lt; −30°C clip to left edge, blue "MAX". CSS transition 80ms.

  **Implement:** Horizontal bar, centered at 0. Right = north hotter (red), left = south hotter (blue). Clip display value to ±30. MAX labels when saturated.

  **Verification:** Novice session → bar hits edge, MAX visible. Expert → bar moves in 0–16°C range.

---

- [ ] **Step 8: Travel angle gauge** — Non-critical

  **Implement:** Rotating needle, center 12°. Green within warning, yellow warning–critical, red above critical. Fetch GET /config/thresholds on load; use `angle_deviation_warning` and `angle_deviation_critical` for color bands. Must move visually.

  **Verification:** Angle drift → needle moves, color changes.

---

- [ ] **Step 9: Alert panel** — Non-critical

  **Implement:** Full-width red banner, correction text. Flash on alert. Fade after 2s. Latest + count; no stacking. "X pending" if queue backs up.

  **Verification:** Alert fires → banner shows, fades.

---

- [ ] **Step 10: Demo page and integration** — Non-critical

  **Implement:** Single page with thermal bar, angle gauge, alert panel. On load: fetch GET /config/thresholds for gauge color bands. WebSocket client with reconnect + exponential backoff. Subscribes to /ws/realtime-alerts. Receives frame messages (ns_asymmetry, travel_angle_degrees) and alert messages from Step 6 broadcasts. Bar and gauge drive from frame messages; panel from alert messages.

  **Verification:** Run `simulate_realtime --mode novice --output websocket --loop`, open page → all three elements update.

---

### Phase 3 — Preflight

- [ ] **Step 11: preflight_check.py** — Critical

  **Implement:** Script runs these checks (in order):

  1. `alert_thresholds.json` exists, parses, no nulls, AlertEngine init OK
  2. Run `simulate_realtime --mode expert --output console --frames 500`, count lines in stdout containing "ALERT". Run `simulate_realtime --mode novice --output console --frames 500`, count similarly. Assert novice_alert_count ≥ 3 × expert_alert_count
  3. Benchmark 1000 push_frame → p99 &lt; 50ms
  4. Assert backend is already running at localhost:8000. Use `curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/docs` — FastAPI serves GET /docs by default. If connection refused or non-200, print `FAIL: Backend not running — start with ENV=development uvicorn main:app before running preflight` and exit non-zero. Then run `simulate_realtime --mode novice --output websocket --frames 500`. Verify each POST returns 200, no exceptions
  5. Loop restart — run `simulate_realtime --mode novice --loop --crash-at 100 --output console` as subprocess, capture stdout for 10 seconds, assert the string "Restarting session" appears in output (after the crash)

  **Exit:** 0 if all pass. Print PASS/FAIL per check. Non-zero on any failure.

  **Verification:** `cd backend && source venv/bin/activate && python -m scripts.preflight_check` exits 0.

---

## Regression Guard

| System | Pre-change behavior | Post-change verification |
|--------|---------------------|--------------------------|
| Aluminum mock | verify_aluminum_mock passes | Same command, exit 0 |
| Frame serialization | Existing consumers get frames | No breaking changes to Frame; ctwd_mm optional |
| Session API | Returns frames for replay | Frames include ctwd_mm when present |
| Extract features | north_south_delta_avg computed | Same; no dependency on ctwd_mm |

---

## Rollback Procedure

```bash
# Per step (reverse order):
# Step 11: Remove preflight_check.py
# Step 10–7: Remove UI components, WebSocket route, /internal/alert route
# Step 6: Remove WebSocket and internal alert routes
# Step 5: Remove simulate_realtime.py
# Step 4–1: Remove backend/realtime/
# Step 0c Phase B: Delete backend/config/alert_thresholds.json, backend/config/
# Step 0c Phase A: Remove calibrate_alert_thresholds.py
# Step 0b: Remove ctwd_mm from Frame and Frame(...) calls
# Confirm: verify_aluminum_mock passes, Frame has no ctwd_mm
```

---

## Pre-Flight Checklist

| Phase | Check | How to Confirm | Status |
|-------|-------|----------------|--------|
| Phase 0 | verify_aluminum_mock passes | Exit 0 | Done |
| Phase 0 | Frame has no ctwd_mm | grep Frame model | Pending |
| Phase 0 | config/ does not exist | ls backend/config 2>/dev/null; test $? -ne 0 | Pending |
| Phase 1 | alert_thresholds.json exists (after 0c Phase B) | test -f backend/config/alert_thresholds.json | Pending |
| Phase 2 | HTTP POST IPC contract | simulate --output websocket POSTs to /internal/alert | Pending |
| Phase 3 | preflight_check exits 0 | Run script | Pending |

---

## Risk Heatmap

| Step | Risk | Early Detection |
|------|------|-----------------|
| 0b | Frame consumers break on new field | Optional, None default; test imports |
| 0c Phase B | Wrong thresholds written | Human gate; reference range check |
| 2 | Rule logic wrong | Unit tests sign reversal |
| 4 | push_frame &gt; 50ms | Benchmark in CI |
| 6 | Backend not running when simulate websocket mode | Clear error: ConnectionRefused |
| 7 | Bar pegged, looks broken | ±30°C + MAX labels per directive |

---

## Success Criteria

| Feature | Target | Verification |
|---------|--------|--------------|
| Thermal every frame | All frames have thermal | verify_aluminum_mock, has_thermal true |
| ctwd_mm on Frame | Emitted by aluminum | Frame.ctwd_mm in 12–17 (expert) / 10–25 (novice) |
| Thresholds | No nulls, human-approved | AlertEngine init, PASS in reference range |
| Rule 1 | Directional correction | ns +20 → tilt back; ns −20 → tilt forward |
| Rule 2, 3 | Fire with correct message | Unit tests |
| push_frame | p99 &lt; 50ms | Benchmark test |
| --mode expert/novice | Preflight can compare rates | simulate --mode expert and --mode novice both work |
| Novice vs expert | Novice ≥ 3× expert alerts | preflight check 2 |
| Suppression | ≤ 1 alert/sec per rule | Time-based, 1000ms window |
| HTTP POST IPC | Simulate → backend → WebSocket | POST /internal/alert broadcast to clients |
| NS bar | ±30°C, MAX when saturated | Visual, 80ms transition |
| preflight_check | Exit 0 | All 5 checks pass |

---

Do not mark a step Done until its verification test passes. Do not proceed past a Human Gate without explicit human input. If blocked, document: (a) what failed, (b) what was tried, (c) why you cannot continue.
