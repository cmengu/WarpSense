# Shipyard MVP Stubbed Items — Exploration

**Reference:** `.cursor/issues/shipyard-mvp-stubbed-items-implementation.md`  
**Purpose:** Understand integration, data flow, backend–frontend type matching, and implementation approach before building.

---

## 0. Core Decisions (Stop Waiting — Just Pick One)

| Question | Decision | Rationale |
|----------|----------|------------|
| fetchSession limit | Use `limit: 10000` in replay page | Expert sessions ~1500 frames. 10k gives headroom. Optimize later. |
| ScoreRule.actual_value | Add to backend model now | Simple field. Better UX: "45° actual vs 50° threshold". |
| Delta colour convention | `delta = sessionA - sessionB`; red = A hotter | If A=expert, B=novice: red = expert hotter. Document in comment. |
| Heatmap rendering | **Go straight to div grid** — ScatterChart will look bad | 7500 overlapping circles; budget 1h pivot if you try ScatterChart first. |
| Playback rate | 1× = real-time (10ms per tick) | Matches user mental model. Add 2×/4× later. |
| Scoring thresholds | Use roadmap placeholders, mark `// DRAFT - awaiting validation` | Unblocks Phase 3. Update when expert weighs in. |

---

## 1. Backend ↔ Frontend Type Contract (CRITICAL — Don't Break This)

**Protected contract:** Field names and shapes must match exactly. No camelCase conversion.

### GET /api/sessions/{id} → Session

| Backend | Frontend | Serialization path |
|---------|----------|--------------------|
| `SessionModel` → `session_payload(frames)` | `Session` | `frame_to_dict` returns `frame_model.frame_data` (stored Frame JSON) |
| `FrameModel.frame_data` | `Frame` | Stored via `Frame.model_dump()` on ingest; includes `has_thermal_data` (computed_field) |
| `frame_data["has_thermal_data"]` | `Frame.has_thermal_data` | Pydantic `model_dump()` includes `@computed_field` by default |

**Frame shape (API → frontend):**
```json
{
  "timestamp_ms": 100,
  "volts": 22.5,
  "amps": 150.0,
  "angle_degrees": 45.0,
  "thermal_snapshots": [{ "distance_mm": 10.0, "readings": [{ "direction": "center", "temp_celsius": 425.3 }, ...] }],
  "has_thermal_data": true,
  "optional_sensors": null,
  "heat_dissipation_rate_celsius_per_sec": -5.2
}
```

**Guard:** `filterThermalFrames` uses `hasThermalData(f)` = `f.has_thermal_data ?? (f.thermal_snapshots?.length ?? 0) > 0`. If API omits `has_thermal_data`, fallback works. But backend MUST set it on stored frames (it does via `model_dump()`).

### GET /api/sessions/{id}/score → SessionScore (new)

| Backend | Frontend | Notes |
|---------|----------|-------|
| `SessionScore.total` (int) | `SessionScore.total` | 0–100 |
| `SessionScore.rules[]` | `SessionScore.rules[]` | Array of ScoreRule |
| `ScoreRule.rule_id` | `ScoreRule.rule_id` | e.g. "amps_variance" |
| `ScoreRule.threshold` | `ScoreRule.threshold` | e.g. 15.0 |
| `ScoreRule.passed` | `ScoreRule.passed` | boolean |
| `ScoreRule.actual_value` | `ScoreRule.actual_value` | **Add to backend** — optional float |

**Backend model change:** `backend/models/scoring.py` → add `actual_value: Optional[float] = None` to `ScoreRule`.

### extract_features — Backend Field Names (No frame_type, No torch_angle_degrees)

**Correct field names on `Frame`:**
- `f.amps` (not amps_variance — that's computed)
- `f.angle_degrees` (not torch_angle_degrees)
- `f.volts`
- `f.heat_dissipation_rate_celsius_per_sec`
- `f.thermal_snapshots` → `snapshot.readings` → find by `reading.direction in ("north","south")`

**There is no `frame_type`** — all frames have the same shape; optional fields are `null` when absent.

---

## 2. Current Architecture Summary

```
Replay Page (ReplayPageInner)
├── sessionId (from route params)
├── State: sessionData, loading, error
├── useEffect: fetchSession(sessionId) → setSessionData
├── useFrameData(sessionData?.frames, null, null) → frameData
│   └── thermal_frames, first_timestamp_ms, last_timestamp_ms
├── extractHeatmapData(frameData.thermal_frames) → heatmapData
├── extractAngleData(sessionData.frames) → angleData
└── Render:
    ├── HeatMap(sessionId, data=heatmapData)
    ├── TorchAngleGraph(sessionId, data=angleData)
    └── ScorePanel(sessionId)
```

**Data types:**
- `HeatmapData`: `{ points: HeatmapDataPoint[], timestamps_ms[], distances_mm[], point_count }`
- `AngleData`: `{ points: AngleDataPoint[], point_count, min/max/avg_angle_degrees }`
- `HeatmapDataPoint`: `{ timestamp_ms, distance_mm, temp_celsius, direction }`
- `AngleDataPoint`: `{ timestamp_ms, angle_degrees }`

---

## 3. Data Flow (High-Level)

### Phase 1 — Charts (HeatMap + TorchAngleGraph)

```
sessionId (route) 
  → fetchSession(sessionId) 
  → session.frames (API returns limit=1000 default!)
  → useFrameData filters thermal_frames
  → extractHeatmapData(thermal_frames) / extractAngleData(all_frames)
  → HeatMap(data) / TorchAngleGraph(data)
  → Recharts renders
```

**Flag:** `fetchSession` uses default `limit=1000`. Expert session has ~1500 frames. Replay will only show first 1000 unless we pass `limit: 10000` or similar. Need to fix in replay page or API default.

### Phase 2 — Replay Controls

```
currentTimestamp state (replay page)
  → slider onChange / play tick / keyboard
  → HeatMap(activeTimestamp), TorchAngleGraph(activeTimestamp)
  → Charts highlight column / cursor line
```

**New state:** `currentTimestamp` (number | null). Init to `first_timestamp_ms` when data loads.  
**New props:** `activeTimestamp?: number | null` on HeatMap and TorchAngleGraph.

### Phase 3 — Scoring

```
sessionId → fetchScore(sessionId) → GET /api/sessions/{id}/score
  → Backend: load SessionModel.to_pydantic() → extract_features → score_session
  → Response: { total, rules: [{ rule_id, threshold, passed }] }
  → ScorePanel fetches, renders
```

**Gap:** `ScoreRule` has no `actual_value`. Issue expects "threshold vs actual". Either extend API response or use a separate structure for display.

### Phase 5 — Compare Page

```
/sessionIdA /sessionIdB (route)
  → fetchSession(A), fetchSession(B) in parallel
  → useSessionComparison(sessionA, sessionB) → deltas: FrameDelta[]
  → extractDeltaHeatmapData(deltas) → delta heatmap (new util)
  → Three HeatMap components: sessionA thermal | delta | sessionB thermal
  → Single currentTimestamp drives all three
```

**Delta heatmap:** `FrameDelta.thermal_deltas` has `{ distance_mm, readings: [{ direction, delta_temp_celsius }] }`. Flatten to points with `delta_temp_celsius`; color scale: blue (negative) → white (0) → red (positive).

---

## 4. Component Structure (Proposed)

### Existing — Modify

| Component | Changes |
|-----------|---------|
| `HeatMap.tsx` | Replace placeholder with Recharts. Add optional `activeTimestamp` prop to highlight column. |
| `TorchAngleGraph.tsx` | Replace placeholder with LineChart. Add optional `activeTimestamp` prop for cursor line. |
| `ScorePanel.tsx` | Add fetch + state (score, loading, error). Render total + rules. |
| `replay/[sessionId]/page.tsx` | Add `currentTimestamp`, slider, play/pause, speed. Pass `activeTimestamp` to charts. Fix `fetchSession` limit for full session. |
| `api.ts` | Add `fetchScore(sessionId)` → GET /score. |
| `backend/routes/sessions.py` | Implement `get_session_score`: load session → extract_features → score_session → return JSON. |
| `backend/features/extractor.py` | Implement `extract_features` per roadmap. |
| `backend/scoring/rule_based.py` | Implement `score_session` + 5 rules. Replace placeholder rules. |

### New

| File | Purpose |
|------|---------|
| `app/compare/[sessionIdA]/[sessionIdB]/page.tsx` | Compare page: fetch both, useSessionComparison, 3-column layout. |
| `utils/deltaHeatmapData.ts` | `extractDeltaHeatmapData(deltas)` → grid with delta_temp, color scale. |
| `useReplayControls.ts` (optional) | Hook for currentTimestamp, play/pause, speed, keyboard. Or inline in replay page. |

---

## 5. State Management

| State | Location | Triggers |
|-------|----------|----------|
| `sessionData` | Replay page | fetchSession on mount |
| `currentTimestamp` | Replay page | Slider drag, play tick, keyboard (Space, L/R) |
| `isPlaying`, `playbackSpeed` | Replay page | Play/pause, speed selector |
| `score`, `scoreLoading`, `scoreError` | ScorePanel | fetchScore on mount |
| `sessionA`, `sessionB` | Compare page | fetchSession for both IDs |

**No global store** — all component-level state. Compare page could use `useReducer` if state gets complex.

---

## 6. Side Effects (useEffect)

| Component | Effect | Deps |
|-----------|--------|-----|
| Replay page | fetchSession → setSessionData | [sessionId] |
| Replay page | Playback interval: advance currentTimestamp by FRAME_INTERVAL_MS / speed | [isPlaying, playbackSpeed, last_timestamp_ms] |
| Replay page | Keyboard listeners (Space, L/R) | [currentTimestamp, first/last] |
| ScorePanel | fetchScore → setScore | [sessionId] |
| Compare page | fetchSession A + B → setSessionA, setSessionB | [sessionIdA, sessionIdB] |

**Playback:** Use `setInterval`, NOT `requestAnimationFrame`. RAF runs at ~60fps but you need 100 updates/sec for 10ms frames — RAF will skip frames and stutter. `setInterval(..., FRAME_INTERVAL_MS / playbackSpeed)` is correct.

---

## 7. Edge Cases

| Case | Handling |
|------|----------|
| Empty thermal frames | HeatMap already shows "No thermal data available". Keep. |
| Empty angle data | TorchAngleGraph shows "No angle data available". Keep. |
| Session 404 | Replay page shows error state. Keep. |
| Score 501 (not impl yet) | ScorePanel: catch error, show "Scoring not available" or retry. |
| Large session (1500+ frames) | fetchSession needs `limit: 10000` for full data. |
| Play at end of session | Stop when currentTimestamp >= last_timestamp_ms. |
| activeTimestamp doesn't match exact frame | Use ±5ms tolerance when highlighting column/cursor. |
| Compare: no shared timestamps | Show "No overlapping frames" or empty delta heatmap. |
| Compare: different session lengths | useSessionComparison already handles; deltas only for shared timestamps. |

---

## 8. HeatMap — Recharts Approach

Recharts has no native heatmap. Options:

**A. ScatterChart + Scatter + Cell (plan’s suggestion)**  
- Map `data.points` to `{ x: timestamp_ms, y: distance_mm, z: temp_celsius }`.  
- Use `ScatterChart`, `XAxis`, `YAxis`, `ZAxis` (range 20–600), `Scatter` with `Cell` for `fill={tempToColor(z)}`.  
- Dense grid may render as overlapping dots; cell size can be tuned.

**B. BarChart grid**  
- One bar per (timestamp, distance). Categorical axes. `Cell` for fill by temp.  
- More control over cell layout but more setup.

**C. Custom div grid**  
- `timestamps_ms.length × distances_mm.length` divs, each with background color from temp.  
- Full control, no Recharts dependency for heatmap. Simple and explicit.

**Recommendation:** **Go straight to (C) div grid.** ScatterChart with 7500 points = overlapping circles, poor grid structure, wasted time. Div grid: 1 hour to build, looks correct. Budget 1h for ScatterChart attempt only if you insist; pivot immediately if it looks bad.

**tempToColor:** Linear interpolate 20°C → `#3b82f6`, 310°C → `#eab308`, 600°C → `#ef4444`.

---

## 9. TorchAngleGraph — Recharts Approach

Straightforward `LineChart`:

```
<LineChart data={data.points}>
  <XAxis dataKey="timestamp_ms" />
  <YAxis domain={[min-5, max+5]} />
  <ReferenceLine y={45} stroke="#22c55e" />
  <Line dataKey="angle_degrees" stroke="#3b82f6" />
  <Tooltip formatter for timestamp_ms, angle_degrees />
</LineChart>
```

Optional: segment line color by threshold (red when >50°). Can use `<Line>` with `stroke` as function or multiple `<Line>` segments.

---

## 10. Backend — GET /score Implementation

```python
# Pseudocode for get_session_score
session_model = db.query(SessionModel).filter_by(session_id=session_id).first()
if not session_model:
    raise HTTPException(404, "Session not found")
session = session_model.to_pydantic()  # ORM → Pydantic Session
features = extract_features(session)
score = score_session(session, features)
return score.model_dump()  # { "total": 80, "rules": [...] }
```

**Session loading:** `SessionModel.to_pydantic()` loads frames via relationship. Ensure frame count is within reason (e.g. cap at 10k for scoring).

---

## 11. ScoreRule — actual_value

**Decision:** Extend `ScoreRule` with `actual_value: Optional[float] = None`. `score_session` sets it per rule.

---

## 12. Implementation Order & 4-Week Plan

### Phase 1 (Week 1): Make Data Visible
- **1a:** `fetchSession(sessionId, { limit: 2000 })` initially; add chunked loading if timeout (see Section 18.5)
- **1b:** HeatMap — **div grid** (ScatterChart overlaps; pivot if you try it). `tempToColor` (20°C→blue, 310°C→yellow, 600°C→red)
- **1c:** TorchAngleGraph — LineChart + ReferenceLine y={45} + tooltip

### Phase 2 (Week 2): Replay Controls
- **2a:** `currentTimestamp`, `isPlaying`, `playbackSpeed` state; slider; `setInterval` for playback
- **2b:** HeatMap/TorchAngleGraph — `activeTimestamp` prop, highlight column / cursor line
- **2c:** Keyboard shortcuts (Space=play/pause, L/R=step)

### Phase 3 (Week 3): Scoring
- **3a:** `extract_features(session)` — amps_stddev, angle_max_deviation, north_south_delta_avg, heat_diss_stddev, volts_range (use `f.amps`, `f.angle_degrees`, etc. — no frame_type)
- **3b:** `score_session` + 5 rules; `ScoreRule.actual_value`; total = passed × 20
- **3c:** GET /score; ScorePanel fetch + render

### Phase 4 (Week 4): Compare Page
- **4a:** `/compare/[sessionIdA]/[sessionIdB]` page; fetch both; `useSessionComparison`
- **4b:** `extractDeltaHeatmapData(deltas)`; delta colour: blue (-) → white (0) → red (+)
- **4c:** 3-column layout; "Compare with…" link from replay page

### Deferred: WebSocket streaming (Month 2)

---

## 13. Contract Validation Checklist (Before Ship)

Before merging any backend change that touches the API contract:

- [ ] **Frame:** `has_thermal_data` present in `frame_data` when stored (Pydantic `model_dump` includes it)
- [ ] **Frame:** `thermal_snapshots[].readings[].direction` is `"center"|"north"|"south"|"east"|"west"`
- [ ] **Session:** `frames` array order matches `timestamp_ms` ascending
- [ ] **Score response:** `rules[].rule_id`, `threshold`, `passed`; add `actual_value` when implementing
- [ ] **Frontend:** `fetchSession` passes `limit` for replay; `fetchScore` expects `{ total, rules }`

---

## 14. File Tree (What to Modify/Create)

```
my-app/src/
  app/
    replay/[sessionId]/page.tsx      MODIFY — limit, currentTimestamp, controls, activeTimestamp
    compare/[sessionIdA]/[sessionIdB]/page.tsx   NEW
  components/welding/
    HeatMap.tsx                     MODIFY — Recharts, activeTimestamp
    TorchAngleGraph.tsx             MODIFY — Recharts, activeTimestamp
    ScorePanel.tsx                  MODIFY — fetch, render score + rules
  lib/
    api.ts                          MODIFY — fetchScore
  utils/
    deltaHeatmapData.ts             NEW — extractDeltaHeatmapData
  hooks/
    useReplayControls.ts            NEW (optional) — or inline in replay page
  constants/
    validation.ts                   (FRAME_INTERVAL_MS already exists)

backend/
  features/extractor.py             MODIFY — extract_features impl
  scoring/rule_based.py             MODIFY — score_session, 5 rules
  models/scoring.py                MODIFY — ScoreRule.actual_value (optional)
  routes/sessions.py               MODIFY — get_session_score impl
```

---

## 15. extract_features — Correct Backend Field Usage

**Do NOT use:** `frame_type`, `torch_angle_degrees` — these do not exist. **Use:** `f.amps`, `f.angle_degrees`, `f.volts`, `f.heat_dissipation_rate_celsius_per_sec`, `f.thermal_snapshots`, `f.has_thermal_data`.

---

## 16. Delta Heatmap & Troubleshooting

**extractDeltaHeatmapData:** Flatten `FrameDelta.thermal_deltas` to points with `delta_temp_celsius`. `deltaTempToColor`: blue (-) → white (0) → red (+). Red = session A hotter.

**When stuck:** Recharts weird → div grid. Playback stutters → check FRAME_INTERVAL_MS. Delta empty → log deltas.length. Score 0 → log features. Charts blank → check has_thermal_data.

---

## 18. Points of Failure

### 18.1 Backend Feature Extraction Will Break (Week 3)

**Problem:** Pseudocode may use wrong fields: `torch_angle_degrees` (doesn't exist), `frame_type` (doesn't exist).

**Real backend code:**
```python
# All frames have the same shape - filter by presence of data
amps = [f.amps for f in session.frames if f.amps is not None]
angles = [f.angle_degrees for f in session.frames if f.angle_degrees is not None]

# For thermal - use has_thermal_data
thermal_frames = [f for f in session.frames if f.has_thermal_data]
for frame in thermal_frames:
    for snapshot in frame.thermal_snapshots:
        for reading in snapshot.readings:
            if reading.direction == "north":
                north_temps.append(reading.temp_celsius)
```

**Mitigation:** Before Week 3, run validation script:
```python
session = session_model.to_pydantic()
frame = session.frames[0]
print(frame.model_dump().keys())  # Verify: timestamp_ms, amps, angle_degrees, NOT torch_angle_degrees
```

---

### 18.2 Recharts ScatterChart May Not Look Like a Heatmap

**Problem:** ScatterChart renders circles. 1500 frames × 5 distances = 7,500 points → overlapping circles, no grid, poor mobile perf.

**Mitigation:** Go straight to div grid. Budget 1h for ScatterChart attempt only; pivot immediately.
```tsx
<div className="grid" style={{
  gridTemplateColumns: `repeat(${timestamps.length}, 1fr)`,
  gap: '1px'
}}>
  {points.map(p => (
    <div key={`${p.timestamp_ms}-${p.distance_mm}`}
      style={{ backgroundColor: tempToColor(p.temp_celsius), height: '20px' }}
      title={`${p.temp_celsius}°C`} />
  ))}
</div>
```

---

### 18.3 Playback Will Stutter (Week 2)

**Problem:** Roadmap says `requestAnimationFrame`, but RAF = 60fps. You need 100 updates/sec for 10ms frames. RAF skips frames → jittery playback.

**Correct approach — use setInterval:**
```ts
const interval = setInterval(() => {
  setCurrentTimestamp(prev => {
    const next = prev + (FRAME_INTERVAL_MS / playbackSpeed);
    if (next >= last_timestamp_ms) {
      setIsPlaying(false);
      return last_timestamp_ms;
    }
    return next;
  });
}, FRAME_INTERVAL_MS / playbackSpeed);
```

**Mitigation:** Ignore RAF suggestion. Use `setInterval` with precise timing.

---

### 18.4 Delta Heatmap Will Be Empty (Week 4)

**Problem:** `useSessionComparison` returns deltas only for **exactly** matching timestamps. If A has [0,10,20] and B has [0,11,21], shared_count = 0.

**Mitigation:**
- Add timestamp tolerance: `Math.abs(tsA - tsB) < 5` (5ms)
- Or: verify mock data alignment before Week 4:
```python
expert_times = {f.timestamp_ms for f in expert.frames}
novice_times = {f.timestamp_ms for f in novice.frames}
shared = expert_times & novice_times
print(f"Shared: {len(shared)} / {len(expert_times)}")  # Expect 1500/1500
```

---

### 18.5 fetchSession Will Timeout on Large Sessions (Week 1)

**Problem:** `limit: 10000` → 10k frames × ~2KB each = 20MB. Slow wifi = 10+ sec, browser timeout.

**Mitigation:**
- Week 1: Test with `limit: 2000` first.
- Add chunked loading if needed:
```ts
const loadChunks = async () => {
  const chunks = [];
  for (let offset = 0; offset < 10000; offset += 1000) {
    const data = await fetchSession(sessionId, { limit: 1000, offset });
    chunks.push(...data.frames);
    if (data.frames.length < 1000) break;
  }
  setAllFrames(chunks);
};
```

---

## 19. High-Level Overview (Failure Points Marked)

| Week | Task | Risk | Mitigation |
|------|------|------|------------|
| **1** | HeatMap | ⚠️ ScatterChart bad → div grid | Pivot after 1h |
| **1** | fetchSession limit | ⚠️ 10k timeout | Start limit: 2000; chunk if needed |
| **1** | TorchAngleGraph | ✅ LineChart works | — |
| **2** | Playback loop | ⚠️ RAF stutters | Use setInterval |
| **2** | activeTimestamp | ⚠️ No exact match | Add ±5ms tolerance |
| **3** | extract_features | 🚨 Wrong fields | Run validation script first |
| **3** | score_session | ⚠️ Arbitrary thresholds | Mark // DRAFT |
| **4** | Delta heatmap | 🚨 Empty deltas | Verify mock alignment; add tolerance |

---

## 20. Revised Implementation Order (With Checkpoints)

**Week 1 — CHECKPOINT AFTER DAY 2**
- Day 1 AM: Try ScatterChart (1h). PM: If bad → div grid (1h)
- CHECKPOINT: Blue-to-red gradient visible?
- Day 2–3: TorchAngleGraph
- CHECKPOINT: Expert flat, novice drift?
- Day 4: Chunked loading if >2s load
- CHECKPOINT: 1500 frames load in <5s?

**Week 3 — VALIDATE FIRST**
- Day 0 (Fri Week 2): `validate_frame_fields.py` — print `frame.model_dump().keys()`
- CHECKPOINT: Fields match docs before coding extract_features.

**Week 4 — MOCK DATA ALIGNMENT**
- Day 0 (Fri Week 3): Verify expert/novice shared timestamps ≈ 100%
- CHECKPOINT: If <90% overlap, fix mock generation before delta logic.

---

## 21. Pre-Flight Checklist

**Week 1:** Recharts installed? Fetch 1000 frames <2s? tempToColor tested?

**Week 2:** FRAME_INTERVAL_MS = 10? Keyboard events work in Next.js?

**Week 3:** Field names validated? extract_features <2s? ScoreRule.actual_value added?

**Week 4:** Mock sessions aligned? useSessionComparison returns >0 deltas? Delta color scale (-50 to +50) tested?

---

## 22. Failure Probability Estimate

| Phase | Risk | Why |
|-------|------|-----|
| Week 1 Charts | 40% | ScatterChart may look bad; large payloads may timeout |
| Week 2 Controls | 20% | RAF vs setInterval; activeTimestamp tolerance |
| Week 3 Scoring | **70%** | Wrong field names; 10k frame perf; arbitrary thresholds |
| Week 4 Compare | 60% | Timestamp alignment; delta rendering |

**Overall: Week 3 is highest risk. Budget extra time.**

---

## 17. (Legacy) Questions

All answered in Section 0. Proceed with those choices.