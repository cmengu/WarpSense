# Browser-Only Demo Mode — Exploration & Mock Execution Plan

**Status:** Pre-implementation exploration  
**Issue:** `.cursor/issues/browser-only-demo-mode.md`

---

## 1. Codebase Analysis Summary

### Current Replay Page Data Flow

```
sessionId (route param)
    → useEffect: fetchSession(sessionId) → setSessionData
    → useEffect: fetchScore(sessionId) → setPrimaryScore
    → useFrameData(sessionData.frames) → thermal_frames, first_timestamp_ms, last_timestamp_ms
    → extractHeatmapData(frameData.thermal_frames)
    → extractAngleData(sessionData.frames)
    → extractCenterTemperatureWithCarryForward(frames, currentTimestamp)
```

**Replay page does NOT use:**
- `ScorePanel` for demo (ScorePanel calls `fetchScore` internally — would hit API)

**Replay page uses:**
- `useSessionMetadata` — for duration, weld_type_label (demo can skip or hardcode)
- `useFrameData` — for thermal_frames, first/last timestamp (demo can derive from frames)
- `getFrameAtTimestamp` — for current frame angle
- `extractCenterTemperatureWithCarryForward` — for weld pool color

### Component Prop Contracts (Verified)

| Component | Props | Source |
|-----------|-------|--------|
| **TorchViz3D** | `angle: number`, `temp: number`, `label?: string` | Pure props, no API |
| **HeatMap** | `sessionId`, `data?: HeatmapData \| null`, `activeTimestamp?`, `label?`, `valueLabel?` | Pure props, no API |
| **TorchAngleGraph** | `sessionId`, `data?: AngleData \| null`, `activeTimestamp?` | Pure props, no API |
| **ScorePanel** | `sessionId` only — **fetches score via fetchScore(sessionId)** | Cannot reuse in demo |

### Data Extraction Functions

| Function | Input | Output |
|----------|-------|--------|
| `extractHeatmapData(frames, direction?)` | `Frame[]` | `HeatmapData` — filters by `hasThermalData` internally |
| `extractAngleData(frames)` | `Frame[]` | `AngleData` |
| `extractCenterTemperatureWithCarryForward(frames, timestamp)` | `Frame[]`, `number` | `number` — carries forward from last thermal frame |

**Demo can pass `session.frames` directly** — no need for `useFrameData` unless we want first/last timestamp. We can compute `firstTimestamp = 0`, `lastTimestamp = 15000` from constants.

---

## 2. Python vs Issue's TypeScript Model — Critical Divergence

### Python (`mock_sessions.py`) Physics Model

- **BASE_CENTER_TEMPS**: Per-distance lookup `{10: 520, 20: 380, 30: 260, 40: 170, 50: 95}` °C
- **Power scaling**: `power_delta * POWER_THERMAL_SENSITIVITY` (0.03 °C/W)
- **Angle asymmetry**: `(angle - 45) * ANGLE_THERMAL_SENSITIVITY` (3.0 °C/deg) for N/S
- **East/West**: Fixed offsets `+40`, `-80` °C from center
- **Session cooling**: `THERMAL_DECAY_RATE` (0.8 °C/sec) over session time
- **Heat dissipation**: Pre-calculated `(prev_center_temp - curr_center_temp) / 0.1`
- **Novice thermal gap**: Mid-session skipped thermal frame (edge case)
- **Expert signal**: `expert_amps`, `expert_volts`, `expert_angle` — different formulas than issue

### Issue's Simplified TS Model

- **Base temp**: `150 + arc_power/50` → ~300°C at nominal (vs Python ~520°C at 10mm)
- **Distance**: `exp(-distance_mm/100)` decay
- **East/West**: `+15`, `-10` * distance_factor (vs Python fixed offsets)
- **Heat dissipation**: Always `null`

**Impact:** Demo heatmap colors and weld pool visuals will differ from seeded backend sessions. Thermals sit in different bands (Python 95–520°C vs simplified ~50–350°C). Heatmap `tempToColor` scales 20–600°C, so both work, but visuals won’t match backend demo 1:1.

**Decision needed:** Accept simplified model for "looks good enough" or port Python constants/formulas for parity.

---

## 3. Dependencies, Structure, Constraints

### Dependencies

| Dependency | Used By | Demo Needs? |
|------------|---------|-------------|
| `@/lib/api` | Replay (fetchSession, fetchScore) | **No** |
| `@/hooks/useFrameData` | Replay (thermal_frames, first/last ts) | Optional — can inline |
| `@/hooks/useSessionMetadata` | Replay (metadata display) | No |
| `@/utils/heatmapData` | HeatMap | Yes |
| `@/utils/angleData` | TorchAngleGraph | Yes |
| `@/utils/frameUtils` | TorchViz3D (temp carry-forward), getFrameAtTimestamp | Yes |
| `@/constants/validation` | FRAME_INTERVAL_MS (10) | Yes |
| `@/components/ErrorBoundary` | Replay, Compare | Recommended (WebGL can throw) |

### Type Requirements

- `Session` from `@/types/session` — `status: "complete"`, `completed_at` required
- `Frame` from `@/types/frame` — `volts`, `amps`, `angle_degrees` can be `number | null`; we provide numbers
- `ThermalSnapshot` from `@/types/thermal` — `distance_mm`, `readings: TemperaturePoint[]` (direction, temp_celsius)
- `HeatmapData`, `AngleData` — produced by extractors

### Constraints

1. **No API calls** — Demo must be 100% offline
2. **Single URL** — `/demo` is the entry; no query params required
3. **WebGL context** — Reuse existing pattern: dynamic import `TorchViz3D` with `ssr: false`
4. **Mobile** — Success criteria: "works on mobile"; `grid-cols-2` should collapse to `grid-cols-1` on small screens

---

## 4. High-Level Mock Execution

### Data Flow

```
User opens /demo
    ↓
DemoPage mounts
    ↓
useState(() => generateExpertSession()) → expertSession (stable, once)
useState(() => generateNoviceSession()) → noviceSession (stable, once)
    ↓
Derived (no state): expertHeatmap = extractHeatmapData(expertSession.frames)
                    noviceHeatmap = extractHeatmapData(noviceSession.frames)
                    expertAngle = extractAngleData(expertSession.frames)
                    noviceAngle = extractAngleData(noviceSession.frames)
    ↓
State: currentTimestamp (0..15000), playing (bool)
    ↓
useEffect(playing): setInterval → setCurrentTimestamp(prev + 10) every 10ms
    ↓
Per frame: expertTemp = extractCenterTemperatureWithCarryForward(expertSession.frames, currentTimestamp)
           noviceTemp = extractCenterTemperatureWithCarryForward(noviceSession.frames, currentTimestamp)
           expertFrame = frames.find(f => f.timestamp_ms === currentTimestamp)
    ↓
Render: TorchViz3D(angle, temp), HeatMap(data, activeTimestamp), TorchAngleGraph(data, activeTimestamp)
```

**No user input except:** Play/Pause button, slider (scrub)

### Component Structure (Pseudocode)

```
DemoPage
├── Header (static)
├── grid (2 columns, responsive → 1 on mobile)
│   ├── ExpertColumn
│   │   ├── Score block (hardcoded 94/100)
│   │   ├── TorchViz3D(angle, temp, "Expert Technique")
│   │   ├── HeatMap(data, activeTimestamp)
│   │   ├── TorchAngleGraph(data, activeTimestamp)
│   │   └── FeedbackPanel (hardcoded ✓ items)
│   └── NoviceColumn (same structure, 42/100, ✗ items)
├── PlaybackControls (fixed bottom)
│   ├── Play/Pause button
│   ├── Time display
│   └── Slider
└── Footer "DEMO MODE - No backend required"
```

### State Management

| State | Type | Initial | Triggers |
|-------|------|---------|----------|
| `expertSession` | `Session` | `generateExpertSession()` | None (lazy init once) |
| `noviceSession` | `Session` | `generateNoviceSession()` | None |
| `currentTimestamp` | `number` | `0` | setInterval (when playing), slider onChange |
| `playing` | `boolean` | `false` | Play button click, auto-stop at end |

**No useEffect for data loading** — data is synchronous on mount.

### Side Effects (useEffect)

```javascript
// Playback tick — only effect
useEffect(() => {
  if (!playing) return;
  const id = setInterval(() => {
    setCurrentTimestamp(prev => {
      const next = prev + 10;
      if (next >= 15000) { setPlaying(false); return 0; }
      return next;
    });
  }, 10);
  return () => clearInterval(id);
}, [playing]);
```

### Edge Cases

| Case | Handling |
|------|-----------|
| **Loading** | None — data is sync. Optional: brief "Generating demo..." if generation is slow (unlikely for 1500 frames) |
| **Error** | `generateExpertSession()` / `generateNoviceSession()` are pure — no thrown errors. WebGL: wrap in ErrorBoundary |
| **Empty thermal** | `extractHeatmapData` skips frames without `has_thermal_data`; HeatMap shows "No thermal data" if point_count=0 |
| **Frame not found** | `expertFrame = frames.find(...)` can be undefined → `angle ?? 45` fallback |
| **Slider at end** | `currentTimestamp` 0–15000; slider max=15000 |
| **Mobile layout** | `grid-cols-2` → `grid-cols-1` via responsive Tailwind |

---

## 5. Implementation Approach

### File Tree

```
my-app/src/
  lib/
    demo-data.ts          (NEW) — generateExpertSession, generateNoviceSession, thermal/signal helpers
  app/
    demo/
      page.tsx            (NEW) — DemoPage component

  components/welding/     (NO CHANGES)
    HeatMap.tsx
    TorchViz3D.tsx
    TorchAngleGraph.tsx

  utils/                  (NO CHANGES)
    heatmapData.ts
    angleData.ts
    frameUtils.ts

  types/                  (NO CHANGES)
    session.ts
    frame.ts
    thermal.ts
```

### Why This Structure

1. **demo-data.ts in lib/** — Pure data generation, no React. Same pattern as `api.ts`. Easy to unit test.
2. **demo/page.tsx only** — Single page, no nested routes. Matches `/compare`, `/replay` layout.
3. **No ScorePanel** — It fetches via API. Demo uses inline score blocks (94/100, 42/100) as in issue spec.
4. **No custom hooks** — Logic is simple: two sessions, one playback state. Extracting a hook adds indirection without benefit.
5. **ErrorBoundary** — Wrap TorchViz3D (and optionally HeatMap/TorchAngleGraph) — WebGL can fail on context loss.

### Alternatives Considered

| Alternative | Why Rejected |
|-------------|--------------|
| Static JSON in `/public/demo/*.json` | Would require backend export script + sync. Generation in TS keeps single source, easier to tweak signals. |
| Reuse `/replay/sess_expert_001` with `?demo=1` | Would need API fallback in fetchSession — adds branching, risk of hiding real failures. Separate route is clearer. |
| Extract `useDemoPlayback` hook | Only one consumer. Hook would just wrap setInterval + state. Overkill. |
| Use ScorePanel with prop override | ScorePanel has no "pass score in" prop; it always fetches. Would require modifying ScorePanel for demo-only path. Inline blocks are simpler. |

---

## 6. Skeleton Code Patterns

### demo-data.ts (structure only)

```javascript
// generateThermalSnapshot(t_ms, amps, volts, angle, distance_mm) → ThermalSnapshot
// expertAmps, expertVolts, expertAngle(t_ms) → number
// noviceAmps, noviceVolts, noviceAngle(t_ms) → number
// generateExpertSession() → Session { frames, session_id: 'demo_expert', ... }
// generateNoviceSession() → Session { frames, session_id: 'demo_novice', ... }
// Frame shape: { timestamp_ms, amps, volts, angle_degrees, thermal_snapshots, has_thermal_data, heat_dissipation: null, optional_sensors: null }
```

### demo/page.tsx (structure only)

```javascript
'use client';
const [expertSession] = useState(() => generateExpertSession());
const [noviceSession] = useState(() => generateNoviceSession());
const [playing, setPlaying] = useState(false);
const [currentTimestamp, setCurrentTimestamp] = useState(0);

const expertHeatmap = extractHeatmapData(expertSession.frames);
// ... same for novice, angleData

useEffect(() => { /* playback interval when playing */ }, [playing]);

return (
  <div>
    <ErrorBoundary>
      <div className="grid grid-cols-1 md:grid-cols-2">
        <ExpertColumn session={expertSession} heatmap={expertHeatmap} ... />
        <NoviceColumn session={noviceSession} heatmap={noviceHeatmap} ... />
      </div>
    </ErrorBoundary>
    <PlaybackControls playing={playing} currentTimestamp={currentTimestamp} onPlayToggle={...} onSeek={...} />
  </div>
);
```

---

## 7. Questions & Ambiguities

### Must Clarify

1. **Physics parity:** Use simplified thermal model (issue spec) or port Python constants for visual parity with backend-seeded sessions? Tradeoff: simplicity vs. "matches /replay/sess_expert_001".

2. **Score source:** Demo shows 94/100 and 42/100 as hardcoded. Should these be computed from a rule-based score in TS (mirroring backend scoring), or stay hardcoded for MVP? Issue says "hardcoded" in layout — assume stay hardcoded unless told otherwise.

3. **Responsive breakpoint:** `grid-cols-2` → `grid-cols-1` at `md` (768px) or `sm` (640px)? Compare page uses `lg:grid-cols-2` (1024px). Suggest `md:grid-cols-2` for demo.

### Nice to Have

4. **Keyboard shortcuts:** Replay has Space (play/pause), Arrow left/right (step). Add same to demo for consistency?
5. **Loop behavior:** Issue: "Loop back" to 0 at end. Confirm: auto-restart or stay at end until user clicks Play again?
6. **Feedback items:** Expert ✓/Novice ✗ blocks are hardcoded strings. Should they be derived from actual session data (e.g. angle drift computed from frames) for authenticity?

---

## 8. Risk Summary

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Thermal model produces empty/bad heatmap | Medium | Unit test: `extractHeatmapData(generateExpertSession().frames).point_count > 0` |
| Python port bugs (wrong formulas) | Medium | Compare sample outputs: Python vs TS at t=0, t=5000, t=15000 |
| WebGL context loss on mobile | Low | ErrorBoundary; consider adding context-loss handler if needed |
| Bundle size from demo-data | Low | ~200 LOC, acceptable per issue |

---

## 9. Confirmation

Exploration complete. Ready to implement once questions in §7 are answered. Recommend:

- **Physics:** Start with simplified model; add Python parity in follow-up if needed.
- **Score:** Hardcoded 94/42 for MVP.
- **Layout:** `md:grid-cols-2` for side-by-side on tablet+.
- **Loop:** Auto-reset to 0 and stop; user clicks Play to restart.
