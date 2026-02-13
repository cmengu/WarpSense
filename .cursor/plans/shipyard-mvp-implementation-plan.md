# Shipyard MVP — Implementation Plan

**Overall Progress:** `100%` (13/13 steps)

**Reference:** `.cursor/explore/shipyard-mvp-stubbed-items-exploration.md`

---

## TLDR

Implement 10 stubbed items across 4 weeks: div-grid HeatMap, LineChart TorchAngleGraph, replay controls (slider, play/pause, setInterval), scoring (extract_features, score_session, GET /score, ScorePanel), and compare page with delta heatmap. Data pipeline exists; charts and scoring show placeholders. Avoid wrong backend field names, RAF for playback, ScatterChart for heatmap, timestamp mismatch in comparison.

---

## Critical Decisions

- **Heatmap:** Div grid, not Recharts ScatterChart — 7500 overlapping circles look bad; div grid gives pixel-perfect control.
- **Playback:** setInterval, not requestAnimationFrame — 100 updates/sec needed for 10ms frames; RAF gives only 60fps.
- **extract_features:** Use `f.angle_degrees`, `f.amps`, `f.has_thermal_data` — NOT `torch_angle_degrees` or `frame_type`.
- **fetchSession:** Start with `limit: 2000`; add chunked loading if timeout.
- **Delta comparison:** Verify mock data alignment first; add ±5ms tolerance if needed for real sensor data.
- **ScoreRule:** Add `actual_value: Optional[float]` to backend model for "actual vs threshold" display.

---

## Tasks

### Phase 1 — Week 1: Make Data Visible

**Goal:** Replace "Visualization coming soon" with actual charts.

---

- [ ] 🟩 **Step 1: fetchSession limit + chunked fallback** — *Why it matters: API integration, large payloads* ✓ Verified

  **Context:** Expert session has ~1500 frames. Default limit=1000 truncates data. Over slow wifi, 3MB may timeout.

  **Code snippet:**
  ```typescript
  // my-app/src/app/replay/[sessionId]/page.tsx — fetch effect
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    const load = async () => {
      const data = await fetchSession(sessionId, { limit: 2000 });
      if (!cancelled) setSessionData(data);
    };
    load().catch((err) => {
      if (!cancelled) setError(err?.message ?? String(err));
    }).finally(() => {
      if (!cancelled) setLoading(false);
    });

    return () => { cancelled = true; };
  }, [sessionId]);
  ```

  **What it does:** Fetches session with explicit limit 2000 (covers 1500-frame expert). If timeout, implement chunked loading (1000-frame batches with offset).

  **Why this approach:** Backend supports limit/offset. Default 1000 is insufficient for full replay.

  **Assumptions:** Backend returns frames in ascending timestamp_ms order; Session has `frames: Frame[]`.

  **Risks:** Chunked loading must preserve order; multiple requests increase latency.

  **Subtasks:**
  - [x] 🟩 Change replay page to `fetchSession(sessionId, { limit: 2000 })`
  - [x] 🟩 Test with 1500-frame expert session — backend + frontend tests pass
  - [ ] 🟥 If timeout or >5s, implement chunked loading (1000-frame batches with offset)

  **✓ Verification Test:**

  **Action:** Start backend and frontend; seed mock sessions; navigate to replay page for expert session ID.

  **Expected Result:** Session loads fully; heatmap and angle data display; `frameData.thermal_frames.length === 1500` (or session frame count).

  **How to Observe:** Network tab shows GET with `limit=2000`; heatmap renders many columns; no "No thermal data" placeholder when session has thermal frames.

  **Pass Criteria:** 1500-frame session loads; heatmap has columns; no truncation to 1000 frames.

  **Common Failures & Fixes:**
  - **If only 1000 frames load:** fetchSession not passing limit param — check useEffect calls `fetchSession(sessionId, { limit: 2000 })`.
  - **If timeout:** Implement chunked loading with offset loop.
  - **If heatmap empty:** Session may not have thermal data — verify mock session has thermal_snapshots.

---

- [ ] 🟩 **Step 2: HeatMap — div grid** ✓

  **Subtasks:**
  - [x] 🟩 Create `tempToColor(temp: number): string` — 20°C→#3b82f6, 310°C→#eab308, 600°C→#ef4444 (linear interpolate)
  - [x] 🟩 Replace placeholder with CSS grid of divs (columns=timestamps, rows=distances; overflow-x-auto)
  - [x] 🟩 Add `activeTimestamp?: number | null` prop; highlight column with ±50ms tolerance

  **✓ Verification Test:**

  **Action:** Load replay page with expert session; observe heatmap.

  **Expected Result:** Blue-to-red gradient visible; expert shows ~490°C (yellow) at center distances; novice shows spikes to ~520°C.

  **How to Observe:** Visual heatmap grid; tooltip on hover shows temp and distance; colors transition blue → yellow → red.

  **Pass Criteria:** Heatmap renders; gradient matches temp range; no overlapping circles or Recharts ScatterChart artifacts.

  **Common Failures & Fixes:**
  - **If "No thermal data":** Check extractHeatmapData receives thermal_frames; verify session has thermal_snapshots.
  - **If flat/gray:** tempToColor may return same color — check interpolation logic.
  - **If overflow broken:** Wrap grid in overflow-x-auto for 1500 columns.

---

- [ ] 🟩 **Step 3: TorchAngleGraph — LineChart** ✓

  **Subtasks:**
  - [x] 🟩 Install Recharts if not present (already in package.json)
  - [x] 🟩 Replace placeholder with LineChart; XAxis (timestamp_ms), YAxis (angle_degrees), ReferenceLine y={45}, Line dot={false}
  - [x] 🟩 Add `activeTimestamp` prop; vertical ReferenceLine as cursor

  **✓ Verification Test:**

  **Action:** Load replay page with expert and novice sessions; observe angle graph.

  **Expected Result:** Expert flat ~44–46°; novice drifts 45°→65° over time; green dashed line at 45° target.

  **How to Observe:** LineChart shows angle over time; expert line nearly horizontal; novice line climbs.

  **Pass Criteria:** LineChart renders; expert flat, novice drift visible; ReferenceLine at 45°.

  **Common Failures & Fixes:**
  - **If "No angle data":** Check extractAngleData and session frames have angle_degrees.
  - **If Y-axis squashed:** Set YAxis domain to [min-5, max+5].

---

### Phase 2 — Week 2: Replay Controls

**Goal:** Scrub timeline, play/pause with spacebar, charts update in real-time.

---

- [x] 🟩 **Step 4: State + slider** ✓

  **Subtasks:**
  - [x] 🟩 Add state: `currentTimestamp`, `isPlaying`, `playbackSpeed` (1, 2, or 4)
  - [x] 🟩 Init currentTimestamp when frameData loads
  - [x] 🟩 Add slider from first_timestamp_ms to last_timestamp_ms; onChange → setCurrentTimestamp; pause if dragging

  **✓ Verification Test:** `my-app/src/__tests__/app/replay/[sessionId]/page.test.tsx` — `Step 4 verification: slider renders, moves, updates currentTimestamp`

  **What the test returns (PASS):**
  | Check | Result | Meaning |
  |-------|--------|---------|
  | `slider_rendered` | ✓ | Timeline slider in DOM when session has 2+ frames |
  | `slider_range` | min=0, max=10 | min/max from `first_timestamp_ms` / `last_timestamp_ms` |
  | `slider_init` | value=0 | Value initializes to firstTimestamp |
  | `slider_onchange` | ✓ | fireEvent.change updates state; time label shows `0.01 s` (10 ms) |

  **What FAIL looks like:** Assertion error indicates which check failed (slider missing, wrong min/max/value, or time label not updating after drag).

  **Common Failures & Fixes:**
  - **If slider doesn't move:** Check value/onChange bound to state; ensure first_timestamp_ms/last_timestamp_ms valid.
  - **If range wrong:** useFrameData may return null for empty frames — guard with frameData check.

---

- [x] 🟩 **Step 5: Playback loop** ✓ — *Why it matters: State management, correct timing*

  **Context:** Frames arrive every 10ms (100Hz). RAF = 60fps → skips frames. Must use setInterval for 100 updates/sec.

  **Subtasks:**
  - [x] 🟩 Add useEffect with setInterval; interval = FRAME_INTERVAL_MS / playbackSpeed
  - [x] 🟩 Stop when currentTimestamp >= last_timestamp_ms; clear on unmount
  - [x] 🟩 Pass `activeTimestamp={currentTimestamp}` to HeatMap and TorchAngleGraph
  - [x] 🟩 Add Play/Pause button

  **✓ Verification Test:** `my-app/src/__tests__/app/replay/[sessionId]/page.test.tsx` — `Step 5 verification: Play advances playback; stops at end; interval cleared on unmount`

  **What the test returns (PASS):**
  | Check | Result | Meaning |
  |-------|--------|---------|
  | `play_button_rendered` | ✓ | Play button in DOM when session has valid range |
  | `play_toggles_pause` | ✓ | Click Play toggles button label to Pause |
  | `playback_advances` | ✓ | setInterval advances currentTimestamp; after 20ms wall-clock, display 0.02 s (2 ticks at 10ms) |
  | `playback_stops_at_end` | ✓ | At lastTimestamp (40ms), isPlaying → false; button shows Play |
  | `interval_cleared_on_unmount` | ✓ | Unmount clears interval; advance 100ms post-unmount causes no errors |

  **Test setup:** Mock session 0–40 ms (5 frames). Uses jest.useFakeTimers() + act() for deterministic advancement.

  **What FAIL looks like:** Assertion error indicates which check failed (button missing, time not advancing, or Play not restoring at end).

  **Common Failures & Fixes:**
  - **If stuttery:** Likely using RAF — switch to setInterval.
  - **If too fast:** Check playbackSpeed divisor in interval.
  - **If doesn't stop:** Guard `next >= last_timestamp_ms` and setIsPlaying(false).

---

- [x] 🟩 **Step 6: Keyboard shortcuts** ✓

  **Subtasks:**
  - [x] 🟩 `window.addEventListener('keydown', ...)` — Space = toggle play, L/R = step ±10ms
  - [x] 🟩 Clean up on unmount
  - [x] 🟩 preventDefault on Space and L/R (no scroll, no page jump)
  - [x] 🟩 Ignore when focus in INPUT/TEXTAREA/SELECT

  **✓ Verification Test:** `my-app/src/__tests__/app/replay/[sessionId]/page.test.tsx` — `Step 6 verification: Space toggles play; L/R step ±10ms; cleanup on unmount`

  **What the test returns (PASS):**
  | Check | Result | Meaning |
  |-------|--------|---------|
  | `space_toggles_play` | ✓ | Space toggles Play↔Pause (twice verified) |
  | `arrow_right_steps` | ✓ | ArrowRight at 0ms → 10ms (0.01 s) |
  | `arrow_left_steps` | ✓ | ArrowLeft at 10ms → 0ms (0 s); steps pause playback |
  | `arrow_clamped` | ✓ | ArrowLeft at 0 stays 0; ArrowRight at 10 stays 10 |
  | `cleanup_on_unmount` | ✓ | Unmount removes listener; fire keydown does not throw |

  **Test setup:** Mock 0–10 ms (2 frames). fireEvent.keyDown(window, { code }) simulates keys. Uses getByText(..., { selector: 'p' }) to avoid matching metadata "0s".

  **What FAIL looks like:** Assertion error indicates which check failed.

  **Common Failures & Fixes:**
  - **If Space does nothing:** Event may be captured elsewhere; check addEventListener target.
  - **If L/R scroll page:** Call preventDefault on keydown.

---

### Phase 3 — Week 3: Scoring (Highest-Risk Week)

**Goal:** Backend computes score; ScorePanel shows "80/100" with per-rule breakdown.

---

- [x] 🟩 **Step 7: Validate frame fields (Day 0)** ✓

  **Subtasks:**
  - [x] 🟩 Create `backend/scripts/validate_frame_fields.py`
  - [x] 🟩 Load session via db; print frame.model_dump().keys(); assert angle_degrees, amps, has_thermal_data; assert NOT torch_angle_degrees, frame_type

  **✓ Verification Test:** `backend/tests/test_validate_frame_fields.py` + run script

  **What the test returns (PASS):**
  | Check | Result | Meaning |
  |-------|--------|---------|
  | `required_keys_present` | ✓ | angle_degrees, amps, has_thermal_data in Frame.model_dump() |
  | `prohibited_keys_absent` | ✓ | torch_angle_degrees, frame_type NOT in keys |
  | `validate_accepts_valid` | ✓ | validate_frame_keys(Frame) does not raise |
  | `validate_rejects_missing` | ✓ | Fake frame missing angle_degrees → AssertionError |
  | `validate_rejects_prohibited` | ✓ | Fake frame with torch_angle_degrees → AssertionError |

  **Script run (manual, with DB seeded):** `cd backend && python scripts/validate_frame_fields.py`
  - Prerequisite: DATABASE_URL set; DB seeded (POST /seed-mock-sessions with ENV=development)
  - Exit 0: prints keys; all assertions pass
  - Exit 1: no session, assertion failed, or connection error

  **If FAIL:** Wrong field names in models/frame.py — fix to match scoring contract.

  **Common Failures & Fixes:**
  - **If KeyError/AttributeError:** Wrong field name — fix assertions to match backend/models/frame.py.
  - **If no session:** Seed mock sessions first.

---

- [x] 🟩 **Step 8: extract_features** ✓ — *Why it matters: Wrong field names fail silently*

  **Context:** Frame has `angle_degrees`, `amps`, `has_thermal_data` — NOT `torch_angle_degrees` or `frame_type`. Wrong names → zeros → scoring broken.

  **Code snippet:**
  ```python
  # backend/features/extractor.py
  import statistics
  from models.session import Session

  def extract_features(session: Session) -> dict:
      amps = [f.amps for f in session.frames if f.amps is not None]
      angles = [f.angle_degrees for f in session.frames if f.angle_degrees is not None]
      thermal_frames = [f for f in session.frames if f.has_thermal_data]

      north_temps, south_temps = [], []
      for f in thermal_frames:
          for snap in f.thermal_snapshots:
              for r in snap.readings:
                  if r.direction == "north":
                      north_temps.append(r.temp_celsius)
                  elif r.direction == "south":
                      south_temps.append(r.temp_celsius)

      heat_diss = [f.heat_dissipation_rate_celsius_per_sec for f in session.frames
                   if f.heat_dissipation_rate_celsius_per_sec is not None]
      volts = [f.volts for f in session.frames if f.volts is not None]

      return {
          "amps_stddev": statistics.stdev(amps) if len(amps) > 1 else 0,
          "angle_max_deviation": max(abs(a - 45) for a in angles) if angles else 0,
          "north_south_delta_avg": abs(statistics.mean(north_temps) - statistics.mean(south_temps))
                                    if north_temps and south_temps else 0,
          "heat_diss_stddev": statistics.stdev(heat_diss) if len(heat_diss) > 1 else 0,
          "volts_range": max(volts) - min(volts) if volts else 0,
      }
  ```

  **What it does:** Extracts 5 features: amps_stddev, angle_max_deviation, north_south_delta_avg, heat_diss_stddev, volts_range.

  **Why this approach:** Filter by presence; use correct field names from Frame model.

  **Assumptions:** Session has frames; thermal snapshots have north/south readings.

  **Risks:** Wrong field names → all zeros; run Step 7 first.

  **Subtasks:**
  - [x] 🟩 Implement extract_features in backend/features/extractor.py
  - [x] 🟩 5 features as above; use f.amps, f.angle_degrees, f.has_thermal_data

  **✓ Verification Test:** `backend/tests/test_extract_features.py`

  **Action:** Run `cd backend && source venv/bin/activate && pytest tests/test_extract_features.py -v`

  **What the test returns (PASS):**
  | Check | Result | Meaning |
  |-------|--------|---------|
  | `all_keys_present` | ✓ | Returns dict with amps_stddev, angle_max_deviation, north_south_delta_avg, heat_diss_stddev, volts_range |
  | `expert_non_zero` | ✓ | Expert yields non-zero features |
  | `novice_non_zero` | ✓ | Novice yields non-zero features; amps_stddev > 0, angle_max_deviation > 0 |
  | `expert_less_than_novice_on_amps` | ✓ | Expert amps_stddev < novice amps_stddev |
  | `expert_less_than_novice_on_angle` | ✓ | Expert angle_max_deviation < novice angle_max_deviation |
  | `empty_session_returns_zeros` | ✓ | Empty session yields all zeros |
  | `single_frame_returns_zero_stddev` | ✓ | Single-frame session yields 0 for *_stddev features |

  **Pass Criteria:** All 9 tests pass; expert < novice on amps_stddev and angle_max_deviation.

  **Common Failures & Fixes:**
  - **If all zeros:** Wrong field names — run Step 7; check Frame model.
  - **If KeyError:** Missing direction in readings — verify thermal model has north/south.
  - **If statistics.stdev empty:** Guard with len > 1.

---

- [x] 🟩 **Step 9: score_session + ScoreRule.actual_value** ✓

  **Subtasks:**
  - [x] 🟩 Add `actual_value: Optional[float] = None` to ScoreRule in backend/models/scoring.py
  - [x] 🟩 Implement 5 rules in rule_based.py: amps_stability, angle_consistency, thermal_symmetry, heat_diss_consistency, volts_stability; mark DRAFT thresholds
  - [x] 🟩 total = sum(r.passed for r in rules) * 20

  **✓ Verification Test:** `backend/tests/test_score_session.py`

  **Action:** Run `cd backend && source venv/bin/activate && pytest tests/test_score_session.py -v`

  **What the test returns (PASS):**
  | Check | Result | Meaning |
  |-------|--------|---------|
  | `expert_total_100` | ✓ | Expert session → total 100 |
  | `expert_all_rules_passed` | ✓ | Expert passes all 5 rules |
  | `novice_total_approx_40` | ✓ | Novice total ~40 (2 rules pass, 3 fail) |
  | `novice_fails_three_rules` | ✓ | Novice fails amps_stability, angle_consistency, volts_stability |
  | `all_rules_have_actual_value` | ✓ | Every rule has actual_value set |
  | `total_is_passed_times_20` | ✓ | total = sum(r.passed for r in rules) * 20 |
  | `five_rules_present` | ✓ | Exactly 5 rules: amps_stability, angle_consistency, thermal_symmetry, heat_diss_consistency, volts_stability |

  **Pass Criteria:** Expert 100/100; novice <50; each rule has actual_value set.

  **Common Failures & Fixes:**
  - **If expert not 100:** Thresholds may be too strict — mark DRAFT and tune.
  - **If actual_value missing:** Add to ScoreRule model and set in score_session.

---

- [x] 🟩 **Step 10: GET /score + ScorePanel** ✓ — *Why it matters: New API endpoint, frontend integration*

  **Context:** ScorePanel fetches score; backend loads session, extracts features, scores, returns JSON.

  **Subtasks:**
  - [x] 🟩 Implement get_session_score in backend/routes/sessions.py (with joinedload for frames)
  - [x] 🟩 Add fetchScore(sessionId) in api.ts; add SessionScore, ScoreRule interfaces
  - [x] 🟩 ScorePanel: fetch on mount; loading/error/success; render total + rules with ✓/✗, threshold, actual_value

  **✓ Verification Test (Backend):** `backend/tests/test_get_session_score.py`

  **Action:** Run `cd backend && source venv/bin/activate && pytest tests/test_get_session_score.py -v`

  **What the test returns (PASS):**
  | Check | Result | Meaning |
  |-------|--------|---------|
  | `expert_returns_200` | ✓ | GET /api/sessions/sess_expert_001/score → 200 |
  | `expert_total_100` | ✓ | Response total=100 |
  | `expert_has_five_rules` | ✓ | rules array has 5 items |
  | `expert_all_rules_have_actual_value` | ✓ | Every rule has actual_value set (not null) |
  | `novice_returns_approx_40` | ✓ | Novice session total 30–60 |
  | `session_not_found_404` | ✓ | Unknown session_id → 404 |

  **✓ Verification Test (Frontend):** `my-app/src/__tests__/components/welding/ScorePanel.test.tsx`

  **Action:** Run `cd my-app && npm test -- --testPathPattern=ScorePanel --no-watch`

  **What the test returns (PASS):**
  | Check | Result | Meaning |
  |-------|--------|---------|
  | `displays_score_panel_title` | ✓ | "Scoring Feedback" in DOM |
  | `shows_loading_initially` | ✓ | "Loading score..." on mount |
  | `calls_fetchScore_with_sessionId` | ✓ | fetchScore(sessionId) invoked |
  | `shows_score_on_success` | ✓ | 100/100, 5 rules, no "Coming soon" |
  | `shows_error_on_fetch_failure` | ✓ | Error state when fetchScore rejects |

  **Pass Criteria:** Backend 6 tests pass; frontend 5 tests pass; expert 100/100; novice ~40/100.

  **Points of Failure (mitigated):**
  - Session not found → 404 (explicit check)
  - Frames not loaded → joinedload(SessionModel.frames) for single-query load
  - extract_features/score_session exception → FastAPI returns 500 with detail
  - ScorePanel race on unmount → cancelled flag prevents setState after unmount
  - API_BASE_URL wrong → Error state shows message; verify NEXT_PUBLIC_API_URL

  **Common Failures & Fixes:**
  - **If 404:** Session not found — seed mock sessions.
  - **If 500:** Check extract_features, score_session; verify imports (get_db, SessionModel).
  - **If ScorePanel empty:** fetchScore may fail — check error state; verify API_BASE_URL.

---

### Phase 4 — Week 4: Compare Page

**Goal:** Expert vs novice side-by-side with delta heatmap.

---

- [x] 🟩 **Step 11: Mock alignment check (Day 0)** ✓

  **Subtasks:**
  - [x] 🟩 Run: `len(expert_times & novice_times) / len(expert_times) * 100` — 100%
  - [x] 🟩 Verified: mock_sessions.py uses same duration_ms (15_000) and frame_interval_ms (10)

  **✓ Verification Test:** `backend/tests/test_mock_alignment.py`

  **Action:** Run `cd backend && source venv/bin/activate && pytest tests/test_mock_alignment.py -v`

  **What the test returns (PASS):**
  | Check | Result | Meaning |
  |-------|--------|---------|
  | `overlap_at_least_90_percent` | ✓ | shared / expert_timestamps >= 90% |
  | `overlap_100_percent` | ✓ | Both use range(0, 15000, 10) → 100% |
  | `shared_count_equals_expert_count` | ✓ | Every expert timestamp has novice match |
  | `same_frame_count` | ✓ | Expert and novice have 1500 frames each |

  **Pass Criteria:** ≥90% overlap before Step 12 (verified 100%).

  **Common Failures & Fixes:**
  - **If <90%:** Mock generator changed — ensure both use same duration_ms and frame_interval_ms.

---

- [x] 🟩 **Step 12: Compare page** ✓

  **Subtasks:**
  - [x] 🟩 Create `app/compare/[sessionIdA]/[sessionIdB]/page.tsx`
  - [x] 🟩 Promise.all([fetchSession(idA, {limit: 2000}), fetchSession(idB, {limit: 2000})])
  - [x] 🟩 useSessionComparison(sessionA, sessionB); single currentTimestamp + slider; 3-column grid
  - [x] 🟩 Add "Compare with…" link from replay page (→ `/compare?sessionA={sessionId}`); add `app/compare/page.tsx` form to pick Session B and navigate to `/compare/[sessionIdA]/[sessionIdB]`

  **Implementation notes:** Compare page fetches both sessions in parallel, derives heatmap data via useFrameData + extractHeatmapData for A/B and extractDeltaHeatmapData for the middle column. Single timeline slider and Play/Pause; keyboard Space/L/R. Breadcrumbs link to Dashboard and each session’s replay.

  **✓ Verification Test:**

  **Action:** Navigate to compare page with expert and novice session IDs (e.g. `/compare/sess_expert_001/sess_novice_001` or use Compare form at `/compare?sessionA=sess_expert_001`).

  **Expected Result:** Both sessions load; 3 columns render (sessionA heatmap, delta, sessionB heatmap); slider works.

  **How to Observe:** Compare page renders; no "No overlapping frames" if mock aligned.

  **Pass Criteria:** 3 columns; both sessions visible; deltas array length > 1000.

  **Common Failures & Fixes:**
  - **If "No overlapping frames":** Run Step 11; add ±5ms tolerance to useSessionComparison if needed.
  - **If one column empty:** Check fetchSession limit; verify session IDs valid.

---

- [x] 🟩 **Step 13: Delta heatmap** ✓

  **Subtasks:**
  - [x] 🟩 Create `utils/deltaHeatmapData.ts` — flatten thermal_deltas to points; temp_celsius = delta_temp_celsius
  - [x] 🟩 `deltaTempToColor(delta)`: blue (-50) → white (0) → red (+50)
  - [x] 🟩 3 HeatMaps: sessionA (tempToColor), delta (deltaTempToColor), sessionB (tempToColor)

  **Implementation notes:** `extractDeltaHeatmapData(deltas, direction)` returns same HeatmapData shape as extractHeatmapData. HeatMap component extended with optional `colorFn`, `label`, and `valueLabel` so the delta column uses `deltaTempToColor` and shows "Δ +12.5°C" in tooltips.

  **✓ Verification Test:**

  **Action:** Load compare page; observe delta heatmap.

  **Expected Result:** Delta shows red where expert (A) hotter; blue where novice (B) hotter; white near 0.

  **How to Observe:** Middle column color scale; red = A hotter; blue = B hotter.

  **Pass Criteria:** Delta heatmap renders; color convention correct; red at 10–30mm where expert applied more heat.

  **Common Failures & Fixes:**
  - **If delta empty:** Check extractDeltaHeatmapData; verify thermal_deltas in FrameDelta.
  - **If wrong colors:** deltaTempToColor sign — red = positive delta = A hotter.
  - **If Heatmap expects different shape:** extractDeltaHeatmapData must return HeatmapData shape (points, timestamps_ms, distances_mm).

---

## Pre-Flight Checklist (Print & Check Each Phase)

| Phase | Dependency Check | How to Verify | Status |
|-------|------------------|---------------|--------|
| **Phase 1** | Recharts installed | `npm ls recharts` or import works | ⬜ |
| | Backend running | GET /api/sessions returns or health check | ⬜ |
| | Mock sessions seeded | Expert/novice sessions exist in DB | ⬜ |
| | Can fetch 1000 frames <2s | Browser network tab | ⬜ |
| **Phase 2** | FRAME_INTERVAL_MS === 10 | Check constants/validation.ts | ⬜ |
| | Keyboard events work | Space/L/R in Next.js | ⬜ |
| **Phase 3** | validate_frame_fields.py passed | Run script; asserts pass | ⬜ |
| | ScoreRule.actual_value added | backend/models/scoring.py | ⬜ |
| **Phase 4** | Mock alignment ≥90% | Python: shared/total | ✅ |
| | useSessionComparison returns >1000 deltas | Compare page loads; 3 columns | ✅ |

---

## Risk Heatmap (Where You'll Get Stuck)

| Phase | Risk Level | What Could Go Wrong | How to Detect Early |
|-------|-----------|---------------------|---------------------|
| Phase 1 | 🟡 40% | ScatterChart overlapping; large payload timeout | Heatmap looks like overlapping circles; load >5s → chunk |
| Phase 2 | 🟢 20% | RAF stutters; activeTimestamp no exact match | Playback jittery → use setInterval; ±50ms for scrub |
| Phase 3 | 🔴 70% | Wrong field names → silent zeros; 30k frames OOM | Run validate_frame_fields.py first; score 0 → check features |
| Phase 4 | 🟠 60% | Timestamp mismatch → empty deltas | shared_count === 0 → verify mock alignment; add tolerance |

---

## Success Criteria (End-to-End Validation)

| Feature | Target Behavior | Verification Method |
|---------|-----------------|---------------------|
| Full session load | 1500-frame expert loads completely | **Test:** Load replay for expert → **Expect:** Heatmap 1500 cols, no truncation → **Location:** Network tab, heatmap |
| Heatmap gradient | Blue→red by temperature | **Test:** View expert/novice → **Expect:** Expert ~490°C yellow; novice spikes → **Location:** Heatmap + tooltip |
| Angle graph | Expert flat, novice drift | **Test:** View both sessions → **Expect:** Expert 44–46°; novice 45°→65° → **Location:** TorchAngleGraph |
| Scrub + play | Slider and spacebar work | **Test:** Drag slider, press Space → **Expect:** Charts update; 1× = 15s for 15s session → **Location:** UI |
| Expert score 100% | All 5 rules pass | **Test:** Load expert replay → **Expect:** ScorePanel "100/100" with 5 ✓ → **Location:** ScorePanel |
| Novice score <50% | 3 rules fail | **Test:** Load novice replay → **Expect:** "40/100" with 3 ✗ → **Location:** ScorePanel |
| Delta heatmap | Red = expert hotter | **Test:** Load compare page → **Expect:** Red at 10–30mm where expert applied heat → **Location:** Delta column |

---

## Assumptions Verification (Reference)

| Assumption | Verified Against | Status |
|------------|------------------|--------|
| Frame: angle_degrees, amps, has_thermal_data (no torch_angle_degrees, frame_type) | backend/models/frame.py | ✅ |
| fetchSession accepts { limit, offset }; default 1000 | my-app/src/lib/api.ts | ✅ |
| FRAME_INTERVAL_MS === 10 | my-app/src/constants/validation.ts | ✅ |
| Mock expert/novice same timestamp sequence | backend/data/mock_sessions.py | ✅ |
| ScoreRule needs actual_value | backend/models/scoring.py | ✅ |
| HeatMap/TorchAngleGraph need activeTimestamp | HeatMap.tsx, TorchAngleGraph.tsx | ✅ |

---

⚠️ **Do not mark a step as 🟩 Done until its verification test passes. If blocked, mark 🟨 In Progress and document what failed.**
