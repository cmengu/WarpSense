# System 1 — Rule-Based Edge Alert

**Type:** Feature | **Priority:** High | **Effort:** Medium | **Demo:** April 9, 2026

---

## TL;DR

Build a self-contained, real-time alert module that runs on-device, reads incoming weld frames, evaluates **three rules** on every frame (Rule 1 NS thermal, Rule 2 angle, Rule 3 speed), and fires directional corrections in under 50ms. Zero database, LLM, or network calls. Data fixes first, then alert engine with three independent suppression counters, then minimal web UI with NS thermal bar, travel angle gauge, alert panel. Run `preflight_check.py` morning of April 9.

---

## Schedule (Accountability)

| Milestone | Target | Owner |
|-----------|--------|-------|
| Phase 0 complete | **March 9, 2026** (Mon) | TBD |
| Phase 1 complete | **March 23, 2026** (Mon) | TBD |
| Phase 2 (Web UI) complete | **March 30, 2026** (Mon) | TBD |
| Buffer / dry-run | **April 6–8, 2026** | — |
| April 9 demo | **April 9, 2026** | — |

---

## Target Hardware

**Document:** What laptop or device runs the April 9 demo? Record it here before March 30. Dry-run on that exact hardware during the buffer. Be prepared to answer: "Have you run this on the actual edge hardware?"

---

## Critical: Build Order

```
Phase 0 — Data fixes (MUST complete before alert engine)
├── 0a. Emit thermal every frame in aluminum generators
├── 0b. Add ctwd_mm to Frame; emit from aluminum generators
└── 0c. Calibrate thresholds (NS, angle, speed) + human review

Phase 1 — Alert engine (3 rules, 3 suppression counters)
Phase 2 — Demo (console + web UI; NS bar, angle gauge, alert panel)
```

---

## Phase 0 — Data Fixes

### Step 0a — Thermal Every Frame

**File:** `backend/data/mock_sessions.py`

- Change `is_thermal_frame = (i % 20 == 0)` to `is_thermal_frame = True` in both `_generate_stitch_expert_frames` and `_generate_continuous_novice_frames`
- Change `thermal_interval_sec` from 0.2 to 0.01

**Verification:** Run `python -m backend.scripts.verify_aluminum_mock` immediately after 0a. Emitting thermal 20× more frequently will break percentile checks and variance ratios. Fix any assertions that break. Do not assume it passes.

### Step 0b — Emit ctwd_mm on Frame

**Files:** `backend/models/frame.py`, `backend/data/mock_sessions.py`

- Add `ctwd_mm: Optional[float] = Field(None, ge=8, le=30)` to Frame
- Both generators already track ctwd_mm internally. Pass `ctwd_mm=ctwd_mm` into `Frame(...)`. No fallback. One afternoon.

**Future Rule 4 (CTWD):** Expert nominal 15mm. Warning when |ctwd − 15| > 4mm; critical when > 7mm. Correction: "Pull back torch — CTWD too long" / "Move closer — CTWD too short".

### Step 0c — Calibrate Thresholds

**File:** `backend/scripts/calibrate_alert_thresholds.py`

- Run 30 expert + 30 novice sessions
- Collect per-frame: `thermal_asymmetry_ns` (north − south), `travel_angle_deviation` (|travel_angle − 12|), `speed_change_pct` over 10-frame windows
- Set warning = expert p95, critical = expert p99
- **Reference range table** — calibration script must print PASS or WARN against these ranges. Human reviewer compares computed values against this table, not a vibe check:

| Threshold | Reference range | Script output |
|-----------|-----------------|---------------|
| thermal_ns_warning | 6–14°C | PASS if in range, WARN if outside |
| angle_deviation_warning | 3–7° | PASS if in range, WARN if outside |
| speed_drop_warning_pct | 6–12% | PASS if in range, WARN if outside |

- Output: `backend/config/alert_thresholds.json` — only after human approval

---

## Thermal Asymmetry (North/South)

North/south asymmetry tracks torch drift along the travel axis — push angle.

- `ns_asymmetry = north_temp − south_temp`
- **Positive** = north hotter = push angle drifting, torch pointing too far forward → correction: **"Reduce push angle — tilt back 3°"**
- **Negative** = south hotter = torch pointing too far back → correction: **"Increase push angle — tilt forward 3°"**

**Computation:**
- Use `thermal_snapshots[0]` (10mm distance, closest to arc)
- Find readings with `direction == "north"` and `"south"`; `ns_asymmetry = north_temp − south_temp`
- **Edge cases:** Empty snapshots → 0.0. Missing direction → 0.0 and log warning.

**Verification:** Unit tests with sign reversal: ns +20 → tilt back; ns −20 → tilt forward.

---

## Phase 1 — Alert Engine

### Rule Structure

| Rule | Metric | Correction |
|------|--------|------------|
| 1 | NS thermal | "Reduce/increase push angle — tilt back/forward 3°" |
| 2 | Travel angle | Deviation from 12°; "Travel angle drifting — correct to 12°" |
| 3 | Speed | Drop over rolling buffer; "Slowing down — maintain pace" / "Speed critical — increase to 420mm/min" |

One alert per frame — highest severity wins across all three rules. Each rule has its own suppression counter. Suppression window loaded from JSON (not hardcoded).

**Suppression is time-based, not frame-based.** Use `time.time()` and `suppression_ms`, not frame index. Otherwise changing the simulate script frame rate (e.g. 30fps vs 100fps) silently breaks suppression — the same number of frames represents different wall-clock durations. Counters store `_suppress_rule1_until` as epoch ms; compare `time.time() * 1000` against it.

### alert_thresholds.json

```json
{
  "thermal_ns_warning": null,
  "thermal_ns_critical": null,
  "angle_deviation_warning": null,
  "angle_deviation_critical": null,
  "speed_drop_warning_pct": null,
  "speed_drop_critical_pct": null,
  "nominal_travel_angle": 12.0,
  "suppression_ms": 1000
}
```

All nulls until calibration script runs and human approves. **AlertEngine raises ValueError on startup if any threshold is null or file missing** — forces calibration before use.

### FrameInput

| Field | Source | Rule |
|-------|--------|------|
| `frame_index` | Loop index | Alert payload, logging |
| `travel_angle_degrees` | `Frame.travel_angle_degrees` | 2 |
| `travel_speed_mm_per_min` | `Frame.travel_speed_mm_per_min` | 3 |
| `ns_asymmetry` | north − south | 1 |
| `amps`, `volts` | Direct | Future |
| `ctwd_mm` | `Frame.ctwd_mm` | 4 (future) |

**Do not include `angle_degrees` (work angle).** It is not used by any current rule. Carry no phantom fields.

### Alert Suppression

```
now_ms = time.time() * 1000
if now_ms < self._suppress_rule1_until:
    skip Rule 1
else:
    run Rule 1
    if alert fires: self._suppress_rule1_until = now_ms + self.suppression_ms
```

Same pattern for rules 2, 3. Three independent counters: `_suppress_rule1_until`, `_suppress_rule2_until`, `_suppress_rule3_until` (all epoch ms). `suppression_ms` from JSON (default 1000).

### push_frame Contract

- No I/O. No network. No database.
- Must complete under 50ms.
- Benchmark in unit tests: `time.time()` delta, assert p99 < 0.05.

### File Structure

```
backend/
  config/
    alert_thresholds.json
  realtime/
    __init__.py
    alert_models.py
    frame_buffer.py
    alert_engine.py
    output_handler.py
  scripts/
    simulate_realtime.py        # --loop flag
    calibrate_alert_thresholds.py
    preflight_check.py
  tests/
    test_alert_engine.py
```

---

## Phase 2 — Demo Web UI

One HTML file. One WebSocket connection. **Three visual elements that move.**

| Element | Specification |
|---------|---------------|
| **NS thermal bar** | Display range **±30°C**. Horizontal, centered at zero. Right = north hotter (red). Left = south hotter (blue). Values above +30°C clip to right edge, show red "MAX" label (saturated, not broken). Values below −30°C clip to left edge, show blue "MAX" label. Bar must animate smoothly — CSS transition 80ms. Novice sessions hit 127°C; without clipping the bar would peg and look broken. ±30°C keeps expert range (0–16°C) meaningful and shows dramatic saturation for novice. |
| **Travel angle gauge** | Rotating needle. Center = 12°. Deviates left/right as angle drifts. Color: green within warning, yellow between warning/critical, red above critical. Must move visually — static number will be ignored. |
| **Alert panel** | Flashes full-width red banner with correction text. Shows rule name, severity, message, correction. Fades after 2 seconds. Shows latest plus running count; does not stack. |

**WebSocket contract (simulate script and UI must both use this):**
- Endpoint: `/ws/realtime-alerts`
- Message schema (JSON): `{ "frame_index": int, "rule_triggered": str, "severity": str, "message": str, "correction": str, "timestamp_ms": float }`
- Without this, simulate script and UI will be built to incompatible contracts.

**WebSocket behaviour:** Reconnects automatically with exponential backoff if server restarts. Queue drains without blocking at 30fps. If alerts stack faster than UI renders: show latest plus "X pending" — do not freeze.

**simulate_realtime.py --loop:** On session complete or unhandled exception, log error, wait 2 seconds, restart from frame 0. Loop until Ctrl+C. Browser reconnects automatically. Demo never goes dead.

**Cursor directive when building the NS thermal bar:** The NS thermal bar display range is ±30°C. Values above +30°C clip to the right edge and show a red "MAX" label. Values below −30°C clip to the left edge and show a blue "MAX" label. The bar must animate smoothly between frames — do not jump instantly, use a CSS transition of 80ms so the movement is visible to a human watching in real time.

---

## Preflight Check

**File:** `backend/scripts/preflight_check.py`

**Command:** `python -m backend.scripts.preflight_check`

**Checks (in order):**
1. `alert_thresholds.json` exists, parses, no null values, AlertEngine initialises without error
2. Generate 500 novice + 500 expert frames; novice alert rate ≥ 3× expert
3. Benchmark 1000 `push_frame` calls — assert p99 < 50ms
4. OutputHandler websocket mode — queue receives alerts, drains correctly
5. Loop restart — simulate crash at frame 100, assert engine reinitialises and continues

**Exit:** 0 if all pass. Print explicit PASS/FAIL per check. Non-zero exit on any failure. Run before every demo, especially morning of April 9.

---

## Go / No-Go Gate

- [ ] `verify_aluminum_mock` passes after 0a thermal fix
- [ ] ctwd_mm on Frame, no fallback anywhere
- [ ] `alert_thresholds.json` written by calibration script, human-reviewed, no nulls
- [ ] All three rules fire with correct directional corrections
- [ ] NS asymmetry tested with sign reversal unit tests
- [ ] `push_frame` p99 < 50ms on demo hardware
- [ ] Novice ≥ 3× expert alert rate
- [ ] Alert rate ≤ 1/sec per rule (suppression working)
- [ ] Web UI: thermal bar moves, angle gauge moves, alert panel flashes
- [ ] Web UI reconnects after script restart
- [ ] `simulate_realtime --loop` restarts cleanly on crash
- [ ] `preflight_check.py` exits 0
- [ ] Zero DB, network, LLM calls in `realtime/`

---

## Demo Readiness / Production

| Rating | After This Plan |
|--------|-----------------|
| Demo (April 9) | **8/10** — NS thermal bar, angle gauge, and alert panel provide a credible real-time demo. |
| Production | **1/10** — Simulator only. Production requires real hardware, 50+ real sessions. Never claim production readiness to investors. |

---

## Vision Alignment

| Criterion | Match |
|-----------|-------|
| Investor | Live demo moment — thermal bar, angle gauge, alerts; survives restarts |
| Operator | Catches mistakes live; actionable corrections |
| Data moat | Labels deviations for future fine-tuning |
| Build order | Real-time alert is highest priority |

Labor replacement: cite median QC inspector salary in target market, one inspector per shift, two shifts — or remove specific dollar figure until sourced.

**Fix thermal first.**
