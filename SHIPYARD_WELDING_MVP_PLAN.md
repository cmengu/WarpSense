# Shipyard Welding MVP — Implementation Plan

**Overall Progress:** `0%`

## TLDR

Fix the last metre: verify mock data reaches the database, wire Recharts to HeatMap and TorchAngleGraph, then add Phase 2 replay controls. The data pipeline is complete; charts show placeholders and replay may 404 until seeding is confirmed. This plan tracks what exists vs what remains.

---

## Implementation Status (Audit)

Audit of current codebase vs roadmap requirements:

### ✅ Implemented

| Item | Location | Notes |
|------|----------|-------|
| POST /api/dev/seed-mock-sessions | `backend/routes/dev.py` | Guards ENV=development or DEBUG=1; calls `generate_expert_session`/`generate_novice_session`; `SessionModel.from_pydantic` cascades frames |
| Test fixture has_thermal_data | `backend/tests/test_api_integration.py` | `_minimal_frame_data()` has `has_thermal_data: False` base, `has_thermal_data: True` when `with_thermal=True` |
| filterThermalFrames fallback | `my-app/src/utils/frameUtils.ts` | `hasThermalData()` uses `f.has_thermal_data ?? (f.thermal_snapshots?.length ?? 0) > 0` |
| POST /api/sessions | `backend/routes/sessions.py` | Creates session in RECORDING status |
| GET /api/sessions/{id} | `backend/routes/sessions.py` | Returns session + frames; 404 if not found |
| Replay page fetchSession | `my-app/src/app/replay/[sessionId]/page.tsx` | `useEffect` fetches session, passes to `extractHeatmapData`, `extractAngleData` |
| extractHeatmapData, extractAngleData | `my-app/src/utils/*.ts` | Implemented and tested |
| useFrameData, useSessionMetadata | `my-app/src/hooks/*.ts` | Implemented |
| compare_sessions | `backend/services/comparison_service.py` | Aligns by timestamp, returns FrameDelta list |
| useSessionComparison | `my-app/src/hooks/useSessionComparison.ts` | Mirrors backend logic |
| Recharts | `my-app/package.json` | `recharts: ^3.7.0` installed |

### 🔴 Not Implemented / Stubbed

| Item | Location | Notes | Depends On |
|------|----------|-------|------------|
| HeatMap Recharts rendering | `my-app/src/components/welding/HeatMap.tsx` | Placeholder div with “coming soon” | Step 1 (seed verified) |
| TorchAngleGraph Recharts rendering | `my-app/src/components/welding/TorchAngleGraph.tsx` | Placeholder div with “coming soon” | Step 1 |
| GET /api/sessions/{id}/score | `backend/routes/sessions.py` | Returns 501 Not Implemented | extract_features, score_session |
| extract_features | `backend/features/extractor.py` | Returns `{}` | Domain expert thresholds |
| score_session | `backend/scoring/rule_based.py` | Returns `SessionScore(total=0, rules=[])` | extract_features |
| ScorePanel | `my-app/src/components/welding/ScorePanel.tsx` | “Coming soon” placeholder | GET /score |
| /compare page | — | Does not exist | Phase 1 |
| Phase 2: Replay controls | — | No slider, play/pause, speed | Phase 1 |
| Phase 4: WebSocket streaming | — | Not started | Phase 2 |
| Phase 5: Comparison UI | — | Not started | Phase 2 |

---

## Implementation Plans for Stubbed Items

Each item below maps to the Not Implemented table. Follow in order where dependencies exist.

| Stub | File | Depends On | Implementation Summary |
|------|------|------------|------------------------|
| **HeatMap** | `HeatMap.tsx` | Seed verified | Recharts: `ScatterChart`/`Scatter` + `Cell`; blue→yellow→red temp scale; tooltip |
| **TorchAngleGraph** | `TorchAngleGraph.tsx` | Seed verified | Recharts: `LineChart` + `Line`; ref line 45°; tooltip |
| **GET /score** | `routes/sessions.py` | Step 8, 9 | Load session → `extract_features` → `score_session` → return JSON |
| **extract_features** | `extractor.py` | Domain expert | `amps_stddev`, `angle_max_deviation`, `north_south_delta_avg`, `heat_diss_stddev`, `volts_range` |
| **score_session** | `rule_based.py` | Step 8 | 5 rules; total = passed × 20 (max 100) |
| **ScorePanel** | `ScorePanel.tsx` | GET /score | Fetch score; show total + per-rule ✓/✗ + threshold vs actual |
| **/compare page** | `app/compare/[a]/[b]/page.tsx` | Phase 1 | Fetch both; `useSessionComparison`; 3 cols: Expert \| Delta \| Novice; synced slider |
| **Phase 2** | Replay page | Phase 1 | `currentTimestamp`, slider, play/pause, speed, `activeTimestamp` prop |
| **Phase 4** | Backend + frontend | Phase 2 | WebSocket `/ws/sessions/{id}/stream`; push on POST /frames |
| **Phase 5** | Compare page | Phase 2 | Same as /compare above |

### HeatMap (`HeatMap.tsx`)

- Import `ResponsiveContainer`, `ScatterChart`, `Scatter`, `XAxis`, `YAxis`, `ZAxis`, `Tooltip`, `Cell` from `recharts`.
- Data: `data.points` → `{x: timestamp_ms, y: distance_mm, z: temp_celsius}`.
- `ZAxis range={[20, 600]}`; `Cell fill={tempToColor(temp)}` — blue (~20°C) → yellow (~310°C) → red (~600°C).
- Custom tooltip: `distance_mm`, `timestamp_ms`, `temp_celsius`.

### TorchAngleGraph (`TorchAngleGraph.tsx`)

- Import `LineChart`, `Line`, `XAxis`, `YAxis`, `ReferenceLine`, `Tooltip`.
- Data: `data.points`; `XAxis dataKey="timestamp_ms"`; `YAxis` with suitable domain.
- `ReferenceLine y={45}`; `Line dataKey="angle_degrees"`; optional: red when >50°.
- Tooltip: `timestamp_ms`, `angle_degrees`.

### extract_features + score_session (backend)

- **Blocked:** Domain expert sign-off on thresholds.
- `extract_features`: return `{amps_stddev, angle_max_deviation, north_south_delta_avg, heat_diss_stddev, volts_range}`.
- `score_session`: 5 rules (amps <15%, angle <5°, thermal <20°C, heat_diss <30, volts <2V); total = passed × 20.

### ScorePanel (`ScorePanel.tsx`)

- Add `fetchScore(sessionId)` in `api.ts`.
- `useEffect` fetch; render total + rules with ✓/✗, threshold, actual; highlight worst rule.

### /compare page

- Route: `app/compare/[sessionIdA]/[sessionIdB]/page.tsx`.
- Fetch both sessions; `useSessionComparison(sessionA, sessionB)`.
- Three columns: Expert heatmap | Delta heatmap | Novice heatmap.
- Delta colour: blue = colder, white = same, red = hotter.
- Single slider; "Compare with…" link from replay page.

---

## Critical Decisions

- **Seed route:** Use `SessionModel.from_pydantic(session)` — frames are persisted via ORM cascade. No separate frame insert loop.
- **Charts:** Recharts already in package.json; use `ResponsiveContainer` + `Cell` for heatmap, `LineChart` + `Line` for angle. No new deps.
- **Scoring:** Defer until domain expert confirms thresholds. Do not guess values.
- **filterThermalFrames:** Already uses `hasThermalData()` with fallback. No change needed.

---

## Critical Code Review (Approval Gate)

### 1. Dev Seed Route — Why it matters: Only path from mock data to DB

```python
# backend/routes/dev.py
@router.post("/seed-mock-sessions")
async def seed_mock_sessions(db: OrmSession = Depends(get_db)):
    if not _is_dev_mode():
        raise HTTPException(status_code=403, ...)
    # ...
    for session in [expert, novice]:
        model = SessionModel.from_pydantic(session)
        db.add(model)
    db.commit()
    return {"seeded": session_ids}
```

**What it does:** Seeds expert and novice sessions into PostgreSQL. `SessionModel.from_pydantic` builds ORM model with `model.frames = cls._frames_to_models(session.frames)`; SQLAlchemy cascade persists frames with the session.

**Why this approach:** Single `db.add(model)` relies on relationship `cascade="all, delete-orphan"` to persist frames. Avoids manual frame inserts.

**Assumptions:** DB schema matches ORM; `FrameModel.frame_data` stores full frame JSON; frontend expects `has_thermal_data` in frame payload.

**Risks:** If cascade does not fire (e.g. session_id mismatch), frames would be missing. Verify with: seed → GET /api/sessions/sess_expert_001 → check `frames.length === 1500`.

---

### 2. Heatmap Data Flow — Why it matters: Data integrity for charts

```typescript
// my-app/src/app/replay/[sessionId]/page.tsx
const frameData = useFrameData(sessionData?.frames ?? [], null, null);
const heatmapData = sessionData?.frames
  ? extractHeatmapData(frameData.thermal_frames)
  : null;
// ...
<HeatMap sessionId={sessionId} data={heatmapData} />
```

**What it does:** `useFrameData` applies `filterThermalFrames` (via `hasThermalData` fallback). `extractHeatmapData` builds `{points, timestamps_ms, distances_mm, point_count}` for the heatmap.

**Why this approach:** Thermal frames are filtered once; heatmap extraction is memoized. Separation of data vs rendering.

**Assumptions:** `session.frames` from API include `has_thermal_data`; backend returns frames with thermal snapshots for seeded sessions.

**Risks:** If API omits `has_thermal_data`, `hasThermalData` fallback uses `thermal_snapshots?.length` — should still work.

---

### 3. filterThermalFrames Fallback — Why it matters: Avoids silent empty charts

```typescript
// my-app/src/utils/frameUtils.ts
export function hasThermalData(frame: Frame): boolean {
  return frame.has_thermal_data ?? (frame.thermal_snapshots?.length ?? 0) > 0;
}
export function filterThermalFrames(frames: Frame[]): Frame[] {
  return frames.filter((f) => hasThermalData(f));
}
```

**What it does:** Treats frame as thermal if `has_thermal_data === true` or `thermal_snapshots` has data. Handles legacy/incomplete API responses.

**Why this approach:** Single source of truth; no duplicate logic.

**Assumptions:** Backend sets `has_thermal_data` correctly in frame_data; fallback only for edge cases.

**Risks:** None identified.

---

## Tasks

### Phase 1 — Make It Visible

- [ ] 🟥 **Step 1: Verify seed route end-to-end**
  - [ ] 🟥 Run backend with `ENV=development` or `DEBUG=1`
  - [ ] 🟥 `curl -X POST http://localhost:8000/api/dev/seed-mock-sessions` → expect `{"seeded": ["sess_expert_001", "sess_novice_001"]}`
  - [ ] 🟥 `curl http://localhost:8000/api/sessions/sess_expert_001` → expect session with ~1500 frames and thermal data
  - [ ] 🟥 Visit `/replay/sess_expert_001` → page loads without 404

- [ ] 🟥 **Step 2: Wire Recharts to HeatMap**
  - [ ] 🟥 Replace placeholder in `HeatMap.tsx` with Recharts components
  - [ ] 🟥 Use `ResponsiveContainer` + grid/cells coloured by temperature
  - [ ] 🟥 Colour scale: blue (~20°C) → yellow → red (~600°C)
  - [ ] 🟥 Tooltip: hover cell shows `distance_mm`, `timestamp_ms`, `temp_celsius`

- [ ] 🟥 **Step 3: Wire Recharts to TorchAngleGraph**
  - [ ] 🟥 Replace placeholder in `TorchAngleGraph.tsx` with `LineChart` + `Line dataKey="angle_degrees"`
  - [ ] 🟥 Reference line at 45°
  - [ ] 🟥 Highlight line red when `angle_degrees > 50°` (optional)
  - [ ] 🟥 Tooltip on hover

- [ ] 🟥 **Step 4: Phase 1 Definition of Done**
  - [ ] 🟥 Expert replay shows visible heatmap grid (time × distance × temp)
  - [ ] 🟥 Expert replay shows flat angle line ~44–46°
  - [ ] 🟥 Novice replay shows angle drifting 45° → 65°
  - [ ] 🟥 All tests pass: `pytest tests/` and `npm test`

---

### Phase 2 — Replay Controls (after Phase 1)

- [ ] 🟥 **Step 5: Time slider and currentTimestamp**
  - [ ] 🟥 Add `currentTimestamp` state to replay page
  - [ ] 🟥 `<input type="range">` from first to last `timestamp_ms`
  - [ ] 🟥 Pass `activeTimestamp` to HeatMap and TorchAngleGraph

- [ ] 🟥 **Step 6: Play/Pause and speed**
  - [ ] 🟥 Play/Pause: `requestAnimationFrame` or controlled interval, advance by `FRAME_INTERVAL_MS` (10ms)
  - [ ] 🟥 Speed control: 1×, 2×, 4×, 10×
  - [ ] 🟥 HeatMap: highlight active column; TorchAngleGraph: vertical cursor line

- [ ] 🟥 **Step 7: Keyboard shortcuts**
  - [ ] 🟥 Space = play/pause; Left/Right = step one frame

---

### Phase 3 — Scoring (after domain expert sign-off)

- [ ] 🟥 **Step 8: Feature extraction**
  - [ ] 🟥 Implement `extract_features()` in `backend/features/extractor.py` per roadmap rules
  - [ ] 🟥 Return `{amps_stddev, angle_max_deviation, north_south_delta_avg, heat_diss_stddev, volts_range}`

- [ ] 🟥 **Step 9: Rule-based scoring**
  - [ ] 🟥 Implement `score_session()` with 5 rules; total = passed × 20 (max 100)
  - [ ] 🟥 Implement `GET /api/sessions/{id}/score`

- [ ] 🟥 **Step 10: ScorePanel UI**
  - [ ] 🟥 Fetch score; show total + per-rule pass/fail + threshold vs actual
  - [ ] 🟥 Highlight worst rule

---

### Phase 4 — Live Streaming (future)

- [ ] 🟥 **Step 11: WebSocket backend**
  - [ ] 🟥 `GET /ws/sessions/{id}/stream`
  - [ ] 🟥 Push new frames on POST /frames ingestion

- [ ] 🟥 **Step 12: Frontend useWebSocket + LIVE badge**
  - [ ] 🟥 Real-time heatmap; fallback polling if disconnected

---

### Phase 5 — Multi-Session Comparison (future)

- [ ] 🟥 **Step 13: Comparison page**
  - [ ] 🟥 New page `/compare/[sessionIdA]/[sessionIdB]`
  - [ ] 🟥 Three columns: Expert | Delta | Novice heatmap
  - [ ] 🟥 Synced playback; “Compare with…” from replay page

---

## Do Not Build Yet

- Auth / operator login — no multi-user requirement yet
- ML-based scoring — validate rule-based first
- GET /api/sessions (listing) — 501; not needed for demo
- Partial upload recovery — Phase 5+
- Mobile-responsive replay — desktop-first
- Multiple thermal directions in heatmap — start with center only

---

⚠️ **Do not proceed to execution until you approve the Critical Code Review section above.**
