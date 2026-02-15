
Here is the exploration document and mock execution plan.

---

# Browser-Only Demo Mode — Exploration & Mock Execution Plan

## 1. Summary of the Feature

| Aspect | Summary |
|--------|---------|
| **Goal** | Self-contained demo at `/demo` — 100% in-browser, no backend/DB/seed. One link for prospects, any device. |
| **Current flow** | Run backend + Postgres → seed → navigate to `/replay/sess_expert_001` |
| **Target flow** | Open `/demo` → side-by-side expert vs novice replays with scores, ~30s to value |

---

## 2. Codebase Analysis

### 2.1 What Already Exists

| Item | Location | Status |
|------|----------|--------|
| **demo-data.ts** | `my-app/src/lib/demo-data.ts` | Implemented — `generateExpertSession()`, `generateNoviceSession()` |
| **demo-data tests** | `my-app/src/__tests__/lib/demo-data.test.ts` | Implemented |
| **Replay page** | `my-app/src/app/replay/[sessionId]/page.tsx` | Pattern to reuse (playback, extraction, components) |
| **demo page** | `my-app/src/app/demo/page.tsx` | Does not exist |

### 2.2 Components to Reuse (as-is)

| Component | Props | API? | Notes |
|-----------|-------|------|-------|
| **TorchViz3D** | `angle`, `temp`, `label` | No | Pure props |
| **HeatMap** | `sessionId`, `data`, `activeTimestamp`, `label` | No | Needs pre-extracted `HeatmapData` |
| **TorchAngleGraph** | `sessionId`, `data`, `activeTimestamp` | No | Needs pre-extracted `AngleData` |
| **ScorePanel** | `sessionId` | Yes | Uses `fetchScore(sessionId)` → demo cannot use as-is |

### 2.3 ScorePanel vs Demo

- `ScorePanel` calls `fetchScore(sessionId)` → requires backend.
- Demo must not call any API.
- Options:
  1. Hardcode scores (94/100 expert, 42/100 novice) in the demo layout.
  2. Add a prop to `ScorePanel` to accept a score object; when present, skip fetch.
  3. Add a `DemoScoreBlock` component that displays a score from props.

### 2.4 Data Extraction (no API)

| Utility | Input | Output | Used by |
|---------|-------|--------|---------|
| `extractHeatmapData(frames)` | `Frame[]` | `HeatmapData` | HeatMap |
| `extractAngleData(frames)` | `Frame[]` | `AngleData` | TorchAngleGraph |
| `extractCenterTemperatureWithCarryForward(frames, ts)` | `Frame[]`, number | `number` | TorchViz3D |
| `getFrameAtTimestamp(frames, ts)` | `Frame[]`, number | `Frame \| null` | TorchViz3D (`angle_degrees`) |

All of these accept `Frame[]` directly; no API or hooks needed for demo.

### 2.5 Replay Page Data Flow (for reference)

```
sessionId (route) → useEffect fetchSession → setSessionData
                    ↓
sessionData.frames → useFrameData → frameData (first_timestamp, last_timestamp, thermal_frames)
                    ↓
frameData.thermal_frames → extractHeatmapData → heatmapData
sessionData.frames → extractAngleData → angleData
                    ↓
currentTimestamp + isPlaying → setInterval(10ms) → playback
                    ↓
getFrameAtTimestamp + extractCenterTemperatureWithCarryForward → TorchViz3D, HeatMap, TorchAngleGraph
```

### 2.6 Demo vs Replay Differences

| Aspect | Replay page | Demo page |
|--------|-------------|-----------|
| **Data source** | `fetchSession(sessionId)` | `generateExpertSession()`, `generateNoviceSession()` |
| **Loading** | Yes | No (sync generation) |
| **Error** | Yes (API failure) | No (no API) |
| **Score** | `ScorePanel` fetches | Hardcoded or inline block |
| **useFrameData** | Used for first/last timestamps | Can use `frames[0]`, `frames[frames.length-1].timestamp_ms` |
| **Playback** | Same `setInterval` pattern | Same |
| **Layout** | Single column + comparison toggle | Two columns, expert | novice |

---

## 3. Data Flow (Demo Mode)

```
┌─────────────────────────────────────────────────────────────────────┐
│  Demo Page Mount                                                     │
├─────────────────────────────────────────────────────────────────────┤
│  useState(() => generateExpertSession())  ──► expertSession (once)    │
│  useState(() => generateNoviceSession())  ──► noviceSession (once)   │
│  useState(0)                               ──► currentTimestamp       │
│  useState(false)                           ──► playing                │
└─────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Derived (no useEffect)                                              │
├─────────────────────────────────────────────────────────────────────┤
│  expertHeatmap  = extractHeatmapData(expertSession.frames)           │
│  noviceHeatmap  = extractHeatmapData(noviceSession.frames)           │
│  expertAngle    = extractAngleData(expertSession.frames)             │
│  noviceAngle    = extractAngleData(noviceSession.frames)              │
└─────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Per-frame (computed from currentTimestamp)                           │
├─────────────────────────────────────────────────────────────────────┤
│  expertFrame = getFrameAtTimestamp(expertSession.frames, currentTs)   │
│  noviceFrame = getFrameAtTimestamp(noviceSession.frames, currentTs)   │
│  expertTemp  = extractCenterTemperatureWithCarryForward(...)         │
│  noviceTemp  = extractCenterTemperatureWithCarryForward(...)         │
└─────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Components (props only)                                             │
├─────────────────────────────────────────────────────────────────────┤
│  TorchViz3D(angle, temp, label)                                      │
│  HeatMap(sessionId, data, activeTimestamp, label)                    │
│  TorchAngleGraph(sessionId, data, activeTimestamp)                   │
│  Inline score block: "94/100" | "42/100"                             │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 4. Component Structure (High-Level)

### 4.1 Single Page Component

```
DemoPage (page.tsx)
  - State: expertSession, noviceSession (lazy init via useState(() => ...))
  - State: currentTimestamp (0), playing (false)
  - useEffect: playback loop (setInterval 10ms when playing)
  - Derived: expertHeatmap, noviceHeatmap, expertAngle, noviceAngle
  - Per-frame: expertFrame, noviceFrame, expertTemp, noviceTemp
  - Render: header + 2-column grid + playback controls
```

### 4.2 Layout

```
┌──────────────────────────────────────────────────────────────────┐
│  Header: "Shipyard Welding - Live Quality Analysis"              │
├────────────────────────────┬─────────────────────────────────────┤
│  EXPERT WELDER   94/100    │  NOVICE WELDER    42/100             │
├────────────────────────────┼─────────────────────────────────────┤
│  TorchViz3D (expert)       │  TorchViz3D (novice)                 │
├────────────────────────────┼─────────────────────────────────────┤
│  HeatMap (expert)          │  HeatMap (novice)                    │
├────────────────────────────┼─────────────────────────────────────┤
│  TorchAngleGraph (expert)  │  TorchAngleGraph (novice)            │
├────────────────────────────┼─────────────────────────────────────┤
│  Feedback bullets (green)  │  Feedback bullets (red)             │
└────────────────────────────┴─────────────────────────────────────┘
│  [▶ PLAY]  Timeline slider  Time display   DEMO MODE badge       │
└──────────────────────────────────────────────────────────────────┘
```

---

## 5. State Management

| State | Type | Init | Changes |
|-------|------|------|---------|
| `expertSession` | `Session` | `useState(() => generateExpertSession())` | None |
| `noviceSession` | `Session` | `useState(() => generateNoviceSession())` | None |
| `currentTimestamp` | `number` | `0` | `setInterval` every 10ms when playing; slider `onChange` |
| `playing` | `boolean` | `false` | Play/Pause; `setInterval` sets to `false` at end |

No `useContext` or external store; all state local to the page.

---

## 6. Side Effects (useEffect)

### Effect 1: Playback loop

```typescript
// Pseudocode
useEffect(() => {
  if (!playing) return;
  const id = setInterval(() => {
    setCurrentTimestamp(prev => {
      const next = prev + 10;
      if (next >= 15000) { setPlaying(false); return 0; } // loop
      return next;
    });
  }, 10);
  return () => clearInterval(id);
}, [playing]);
```

### Effect 2 (optional): Keyboard shortcuts

Replay page uses Space, ArrowLeft, ArrowRight. Can be copied or skipped for v1.

---

## 7. Edge Cases

| Case | Approach |
|------|----------|
| **Loading** | None — data generated synchronously on mount |
| **Error** | None — no API; demo-data is deterministic |
| **Empty frames** | Unlikely; generators always return 1500 frames; no extra guard |
| **Slider beyond last frame** | Slider `max=15000`; `currentTimestamp` clamped by logic |
| **Thermal frames sparse** | `extractCenterTemperatureWithCarryForward` handles carry-forward |
| **Mobile layout** | 2-column grid → stack on small screens via Tailwind `lg:grid-cols-2` |

---

## 8. Implementation Approach

### File tree

```
my-app/src/
  app/
    demo/
      page.tsx                    (NEW) - Demo page
  lib/
    demo-data.ts                  (EXISTS) - No changes (unless Python parity)
  utils/
    heatmapData.ts                (NO CHANGE)
    angleData.ts                  (NO CHANGE)
    frameUtils.ts                 (NO CHANGE)
  components/
    welding/
      HeatMap.tsx                 (NO CHANGE)
      TorchViz3D.tsx              (NO CHANGE)
      TorchAngleGraph.tsx         (NO CHANGE)
      ScorePanel.tsx              (OPTIONAL: add score prop for demo, or skip)
```

### Why this structure

1. **`page.tsx` only**  
   All logic in one page; no separate hooks or components. Keeps demo isolated and easy to remove later.

2. **No `ScorePanel` for demo**  
   Use a small inline block with hardcoded scores. Avoids modifying `ScorePanel` or adding conditional fetch logic.

3. **Reuse of TorchViz3D, HeatMap, TorchAngleGraph**  
   They expect the same `HeatmapData`, `AngleData`, and frame-based values; demo generates these locally.

4. **`useState(() => generateExpertSession())`**  
   Sessions created once on mount. No extra renders or regeneration during playback.

5. **Playback pattern**  
   Same `setInterval` + `currentTimestamp` pattern as replay page; consistent behavior and maintainability.

### Alternatives considered

| Alternative | Reason not chosen |
|-------------|--------------------|
| Custom `useDemoPlayback` hook | Overkill for a single demo page |
| Extract a `DemoColumn` component | Only two columns, minor duplication; page-level logic is fine |
| Port scoring to TS and compute real scores | Adds complexity; hardcoded scores match the spec for v1 |
| Make `ScorePanel` accept optional `score` prop | Possible, but demo layout differs (inline scores); simpler to use an inline block |

---

## 9. High-Level Pseudocode

```javascript
// Demo page skeleton
export default function DemoPage() {
  const [playing, setPlaying] = useState(false);
  const [currentTimestamp, setCurrentTimestamp] = useState(0);

  const [expertSession] = useState(() => generateExpertSession());
  const [noviceSession] = useState(() => generateNoviceSession());

  // Derived once per session (could memoize if needed)
  const expertHeatmap = extractHeatmapData(expertSession.frames);
  const noviceHeatmap = extractHeatmapData(noviceSession.frames);
  const expertAngle = extractAngleData(expertSession.frames);
  const noviceAngle = extractAngleData(noviceSession.frames);

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

  const expertFrame = getFrameAtTimestamp(expertSession.frames, currentTimestamp);
  const noviceFrame = getFrameAtTimestamp(noviceSession.frames, currentTimestamp);
  const expertTemp = extractCenterTemperatureWithCarryForward(expertSession.frames, currentTimestamp);
  const noviceTemp = extractCenterTemperatureWithCarryForward(noviceSession.frames, currentTimestamp);

  return (
    <div>
      <header>...</header>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <DemoColumn session={expertSession} heatmap={expertHeatmap} angle={expertAngle}
          frame={expertFrame} temp={expertTemp} score={94} variant="expert" />
        <DemoColumn session={noviceSession} heatmap={noviceHeatmap} angle={noviceAngle}
          frame={noviceFrame} temp={noviceTemp} score={42} variant="novice" />
      </div>
      <PlaybackControls playing={playing} onToggle={...} currentTimestamp={currentTimestamp}
        onSeek={...} max={15000} />
    </div>
  );
}
```

---

## 10. Questions & Ambiguities

### 10.1 Scoring

- **Q1**  
  Should we use hardcoded expert 94/100 and novice 42/100, or port rule-based scoring to TypeScript and compute real scores?
- **Q2**  
  If hardcoded: should the feedback bullets (e.g. “Consistent temperature”, “Torch angle drift”) also be hardcoded, or derived from session data?

### 10.2 Python Parity

- **Q3**  
  `demo-data.ts` uses a simplified thermal model vs `mock_sessions.py`. Is that acceptable for v1, or should we align with Python (BASE_CENTER_TEMPS, heat dissipation, thermal gap, etc.)?
- **Q4**  
  Do we need a unit test comparing Python and TS outputs for a fixed seed/timestamp?

### 10.3 Playback Behavior

- **Q5**  
  Should playback loop from 0 when it reaches 15s, or stop at the end?
- **Q6**  
  Do we want the same keyboard shortcuts as the replay page (Space, ArrowLeft, ArrowRight)?

### 10.4 Navigation / Discovery

- **Q7**  
  Should the home page or main nav include a link to `/demo`?

### 10.5 Layout & Design

- **Q8**  
  Use the cyan “brutalist” style from the issue (dark bg, cyan accents) or match the existing replay page styling?
- **Q9**  
  Should the layout be exactly as in the issue, or can we align more closely with the replay page to reduce divergence?

### 10.6 WebGL / Performance

- **Q10**  
  Two TorchViz3D instances = two Canvas/WebGL contexts. `.cursorrules` mention limits of ~8–16 contexts per tab. Are two contexts acceptable for the demo page?

---

## 11. Confirmation Checklist

Before implementation:

1. Confirm scoring approach (hardcoded vs computed).
2. Confirm playback behavior (loop vs stop at end).
3. Confirm Python parity expectations for demo-data.ts.
4. Confirm design/styling direction (issue mockup vs replay page).
5. Resolve any other questions above.

Once these are decided, implementation can follow this plan with minimal changes.
