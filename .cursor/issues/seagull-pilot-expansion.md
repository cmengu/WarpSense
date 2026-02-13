# Seagull Pilot Expansion — WelderReport & Team Dashboard

**Type:** Feature  
**Priority:** Normal  
**Effort:** Medium  
**Labels:** `frontend` `seagull` `ai-feedback` `demo`  
**Status:** Open

---

## TL;DR

Add the Seagull pilot UI: team dashboard (`/seagull`) and individual WelderReport (`/seagull/welder/[id]`) with AI-style feedback, side-by-side heatmaps, and trend chart. Uses existing seeded sessions (`sess_expert_001`, `sess_novice_001`) via `fetchSession`—no new mock-data or seeding work.

---

## Already Done (Out of Scope)

| Item | Location |
|------|----------|
| Database setup | `QUICK_START.md`, `backend/.env` |
| Seed / wipe | `POST /api/dev/seed-mock-sessions`, `wipe-mock-sessions` |
| Mock sessions | `backend/data/mock_sessions.py` (expert, novice) |
| HeatMap + extractHeatmapData | `components/welding/HeatMap.tsx`, `utils/heatmapData.ts` |
| fetchSession, fetchScore | `lib/api.ts` |
| Side-by-side layout pattern | `compare/[sessionIdA]/[sessionIdB]/page.tsx` |
| ScorePanel (rule-based) | `components/welding/ScorePanel.tsx` |

Population flow: `STARTME.md` → `curl -X POST .../seed-mock-sessions` → DB has sess_expert_001, sess_novice_001.

---

## Remaining Work (Upcoming Expansion)

### 1. AI Feedback Engine

| Task | File | Notes |
|------|------|-------|
| Add `lib/ai-feedback.ts` | New | Rule-based `generateAIFeedback(session, historical)` → `AIFeedbackResult` |
| Define types | `types/ai-feedback.ts` or inline | `AIFeedbackResult`, `FeedbackItem`, `WelderProfile`, `skill_level`, `trend` |

Use `Session` and `Frame` shapes from existing types. Combine `fetchScore` rules with pattern detection (amps spikes, angle drift, thermal asymmetry) to produce `summary`, `feedback_items`, `skill_level`, `trend`.

### 2. Seagull Pages

| Task | File | Notes |
|------|------|-------|
| Team dashboard | `app/seagull/page.tsx` | 3 welder cards, scores, trend indicators |
| WelderReport | `app/seagull/welder/[id]/page.tsx` | Score header, AI summary, side-by-side heatmaps, feedback list, trend chart, export stubs |
| **Error handling** | WelderReport | `.catch` in useEffect; error card with message + "← Back to Team Dashboard" link (UX Safeguards §1) |
| **Back navigation** | WelderReport | "← Back to Team Dashboard" link at top when not in error state (UX Safeguards §2) |

Data: `fetchSession("sess_expert_001")` for benchmark, `fetchSession("sess_novice_001")` for "Mike Chen" (or map welder id → session id). No `lib/mock-data.ts`—use API with seeded DB.

### 3. New Components

| Task | File | Notes |
|------|------|-------|
| FeedbackPanel / FeedbackItem | `components/welding/FeedbackPanel.tsx` | Render `feedback_items` with severity styling |
| TrendChart | `components/welding/TrendChart.tsx` | LineChart of historical scores (mock array for pilot) |
| Export buttons | In WelderReport | "Email Report" / "Download PDF" — alert/toast stub for demo |

### 4. Optional: Third Welder for Team Dashboard

| Task | File | Notes |
|------|------|-------|
| Add `generate_improving_session` | `backend/data/mock_sessions.py` | Intermediate profile (e.g. sess_improving_001) |
| Extend seed route | `backend/routes/dev.py` | Include sess_improving_001 in seeded IDs |
| Wipe route | Same | Add to wipe target list |

Only if team dashboard needs 3 distinct welder profiles.

---

## Relevant Files

| File | Action |
|------|--------|
| `my-app/src/lib/ai-feedback.ts` | Create (rule-based engine) |
| `my-app/src/app/seagull/page.tsx` | Create (team dashboard) |
| `my-app/src/app/seagull/welder/[id]/page.tsx` | Create (WelderReport) |
| `my-app/src/components/welding/FeedbackPanel.tsx` | Create |
| `my-app/src/components/welding/TrendChart.tsx` | Create |
| `my-app/src/utils/heatmapData.ts` | Reuse `extractHeatmapData` |
| `my-app/src/lib/api.ts` | Reuse `fetchSession`, `fetchScore` |

---

## Welder → Session Mapping (Pilot)

For demo, hardcode `WELDER_MAP`:

- `mike-chen` → `sess_novice_001` (Mike Chen)
- `expert-benchmark` → `sess_expert_001` (Expert benchmark)

Fallback: if `params.id` not in map, use as sessionId directly (e.g. `/seagull/welder/sess_novice_001`).

Future: API endpoint or DB table mapping welder_id → session_id.

---

## Risk & Notes

- **Data contract:** `AIFeedbackResult` is frontend-only for pilot. Backend score stays rule-based; AI feedback is derived from same session data.
- **TrendChart:** Use mock `historicalScores` array (e.g. `[72, 68, 75, 78]`) until we have real welder history.
- **Export:** Stub only; no actual email/PDF logic for demo.

---

## UX Safeguards (Required)

### 1. Error Handling for Missing Sessions

**Risk:** Customer visits `/seagull/welder/mike-chen` but DB isn't seeded, session was deleted, or mapping is wrong → app crashes or shows "Loading..." forever.

**Safeguard:** Explicit `catch` in `useEffect`; set error state; render error card with actionable message and back link.

```tsx
// In WelderReport
const WELDER_MAP: Record<string, string> = {
  'mike-chen': 'sess_novice_001',
  'expert-benchmark': 'sess_expert_001'
}

useEffect(() => {
  const sessionId = WELDER_MAP[params.id] ?? params.id

  setLoading(true)
  setError(null)

  Promise.all([
    fetchSession(sessionId, { limit: 2000 }),
    fetchSession('sess_expert_001', { limit: 2000 }),
    fetchScore(sessionId)
  ])
    .then(([session, expert, score]) => {
      setSession(session)
      setExpertSession(expert)
      setScore(score)
      setReport(generateAIFeedback(session, score, historicalScores))
    })
    .catch((err) => {
      console.error('Failed to load:', err)
      setError('Session not found. Make sure mock data is seeded. See STARTME.md: curl -X POST http://localhost:8000/api/dev/seed-mock-sessions')
      setSession(null)
      setExpertSession(null)
      setScore(null)
      setReport(null)
    })
    .finally(() => setLoading(false))
}, [params.id])

// In the render (before main content)
if (error) {
  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-black p-8">
      <div className="bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800 rounded-lg p-6 max-w-md">
        <h2 className="text-lg font-bold text-red-900 dark:text-red-200">⚠️ Error</h2>
        <p className="text-red-800 dark:text-red-300 mt-2 text-sm">{error}</p>
        <Link href="/seagull" className="text-blue-600 dark:text-blue-400 underline mt-4 block">
          ← Back to Team Dashboard
        </Link>
      </div>
    </div>
  )
}
```

### 2. Back Navigation (Breadcrumbs)

**Problem:** User on `/seagull/welder/mike-chen` has no way to return to team dashboard.

**Safeguard:** Add "Back to Team Dashboard" link at top of WelderReport (above score header).

```tsx
// At top of WelderReport, before score header (when not in error state)
<div className="mb-4">
  <Link href="/seagull" className="text-blue-600 dark:text-blue-400 hover:underline text-sm">
    ← Back to Team Dashboard
  </Link>
</div>
```

---

## Reference

- Gap analysis: `docs/SEAGULL_IMPLEMENTATION_GAP_ANALYSIS.md`
- Seed/wipe: `STARTME.md`, `backend/routes/dev.py`
- Compare page (heatmap layout): `my-app/src/app/compare/[sessionIdA]/[sessionIdB]/page.tsx`

---

# Exploration: Seagull Pilot Expansion

## Integration Analysis

### Existing Codebase Patterns

| Pattern | Location | Reusable For Seagull |
|---------|----------|----------------------|
| **Compare page** | `compare/[sessionIdA]/[sessionIdB]/page.tsx` | Side-by-side heatmap layout; `Promise.all([fetchSession(A), fetchSession(B)])`; `useFrameData` → `extractHeatmapData` |
| **Replay page** | `replay/[sessionId]/page.tsx` | `ScorePanel` usage; `useFrameData`; loading/error states |
| **HeatMap** | `HeatMap.tsx` | Accepts `data`, `colorFn`, `label`, `valueLabel`; no timeline for Seagull (static aggregate) |
| **ScorePanel** | `ScorePanel.tsx` | Fetches via `fetchScore(sessionId)`; shows total + rules; **not used** — we use AI feedback instead |
| **LineChart** | `components/charts/LineChart.tsx` | Expects `{ date: string, value: number }[]`; reuse for TrendChart with `date` = "Week 1", "Week 2", etc. |
| **Home page** | `app/page.tsx` | loading/error/retry; `ErrorBoundary`; layout structure |
| **DashboardLayout** | `DashboardLayout.tsx` | MetricCard, LineChart — different use (metrics); team dashboard is distinct |

### Data Flow (Current vs Seagull)

```
CURRENT (Compare page):
  params.sessionIdA, sessionIdB
    → useEffect: Promise.all([fetchSession(A), fetchSession(B)])
    → setSessionA, setSessionB
    → useFrameData(sessionA.frames) → thermal_frames
    → extractHeatmapData(thermal_frames) → HeatmapData
    → HeatMap component

SEAGULL (WelderReport):
  params.id (welder id)
    → Map to sessionId (mike-chen → sess_novice_001)
    → useEffect: Promise.all([fetchSession(sessionId), fetchSession("sess_expert_001"), fetchScore(sessionId)])
    → setSession, setExpertSession, setScore
    → generateAIFeedback(session, score, []) → AIFeedbackResult (client-side)
    → useFrameData(session.frames) → extractHeatmapData → HeatMap (×2, side-by-side)
    → FeedbackPanel, TrendChart
```

### Dependencies & Constraints

| Dependency | Status |
|------------|--------|
| `Session`, `Frame` types | ✅ `types/session.ts`, `types/frame.ts` |
| `fetchSession`, `fetchScore` | ✅ `lib/api.ts` |
| `extractHeatmapData(frames, direction)` | ✅ `utils/heatmapData.ts` — needs `Frame[]`; `useFrameData().thermal_frames` |
| `tempToColorRange(minT, maxT)` | ✅ For shared scale across Expert vs Your Weld |
| `HeatMap` props | `sessionId`, `data`, `colorFn?`, `label`, `valueLabel?` — no `activeTimestamp` for Seagull (static view) |
| Recharts LineChart | ✅ `{ date, value }[]` — TrendChart: `[{ date: "Week 1", value: 72 }, ...]` |
| Backend feature extraction | Python only; **no frontend port** — AI feedback must re-derive or use `fetchScore` rules |

**Constraint:** Backend `extract_features` and `score_session` run server-side. AI feedback engine runs **client-side** on `Session` data. Options:

1. **Call `fetchScore`** — get `SessionScore` (total + rules), then map rules → `feedback_items` with human text.
2. **Port feature extraction to TS** — compute `amps_stddev`, `angle_max_deviation`, etc. in browser; more work, full parity.
3. **Hybrid** — use `fetchScore` for total/score; derive `summary`, `skill_level`, `trend` from rules + simple heuristics.

**Recommendation:** Option 1 or 3. `SessionScore.rules` already has `rule_id`, `passed`, `actual_value`, `threshold`. Map each to a `FeedbackItem` with template text (e.g. `amps_stability` → "Current fluctuated by {actual_value:.1f}A — aim for stability under {threshold}A").

---

## High-Level Mock Execution

### WelderReport Page (`app/seagull/welder/[id]/page.tsx`)

```
WelderReport component:
  - State: session (null), expertSession (null), score (null), report (null), loading (true), error (null)
  - Mapping: WELDER_MAP = { "mike-chen": "sess_novice_001", "expert-benchmark": "sess_expert_001" }
             sessionId = WELDER_MAP[params.id] ?? params.id (fallback for direct session ID)
  - useEffect (on [params.id]):
      * setLoading(true), setError(null)
      * Promise.all([fetchSession(sessionId), fetchSession("sess_expert_001"), fetchScore(sessionId)])
      * .then → setSession, setExpertSession, setScore, setReport(generateAIFeedback(...))
      * .catch → setError("Session not found. Make sure mock data is seeded..."), clear all data, console.error
      * .finally → setLoading(false)
  - Render logic (order matters):
      * If error: error card (red border, message, Link "← Back to Team Dashboard") — see UX Safeguards §1
      * If loading: <div>Loading AI analysis...</div>
      * If !report || !session || !expertSession: loading (guard)
      * Else:
          - Back nav: <Link href="/seagull">← Back to Team Dashboard</Link> — see UX Safeguards §2
          - Score header, AI summary, side-by-side heatmaps, FeedbackPanel, TrendChart, export buttons
```

### AI Feedback Engine (`lib/ai-feedback.ts`)

```
generateAIFeedback(session, score, historicalScores):
  - Input: Session, SessionScore (from fetchScore), number[] (mock historical)
  - Output: AIFeedbackResult { score, skill_level, trend, summary, feedback_items }
  - Logic:
      * score = score.total (from fetchScore)
      * skill_level = score >= 80 ? "Advanced" : score >= 60 ? "Intermediate" : "Beginner"
      * trend = historicalScores.length >= 2 && last > prev ? "improving" : "stable" | "declining"
      * summary = template based on skill_level + which rules failed (e.g. "Strong improvement. Focus on amp stability.")
      * feedback_items = score.rules.map(rule => ({
          severity: rule.passed ? "info" : "warning",
          message: templateForRule(rule),
          timestamp_ms: null (or derive from session if needed),
          suggestion: suggestionForRule(rule)
        }))
  - Pure function, no side effects, deterministic
```

### Team Dashboard (`app/seagull/page.tsx`)

```
SeagullDashboard:
  - State: welders (null), loading, error
  - Hardcode WELDERS = [
      { id: "mike-chen", name: "Mike Chen", sessionId: "sess_novice_001" },
      { id: "sarah-johnson", name: "Sarah Johnson", sessionId: "sess_expert_001" },  // or same for 2 welders
      ...
    ]
  - useEffect: For each welder, fetchScore(sessionId) — Promise.all
  - Cards: name, score, trend (mock), Link to /seagull/welder/[id]
  - With 2 sessions only: show 2 cards (Mike Chen, "Expert Benchmark" or similar)
  - Optional: add sess_improving_001 for 3rd card
```

### FeedbackPanel Component

```
FeedbackPanel({ items }: { items: FeedbackItem[] }):
  - Render: <div className="space-y-4"> { items.map(item => <FeedbackItem key={i} item={item} />) } </div>
  - No state; pure presentational

FeedbackItem({ item }):
  - Render: border-left by severity (green/amber/red), icon, message, suggestion
  - Severity styles: info = blue/soft, warning = amber, critical = red
```

### TrendChart Component

```
TrendChart({ data }: { data: { date: string; value: number }[] }):
  - If empty: "No historical data" placeholder
  - Else: <LineChart data={data} color="#3b82f6" height={200} />
  - Reuse existing LineChart from components/charts/LineChart.tsx
  - Pilot: pass mock data e.g. [{ date: "Week 1", value: 68 }, { date: "Week 2", value: 72 }, ...]
```

---

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│  USER                                                                   │
│  - Visits /seagull → Team dashboard (2–3 welder cards)                 │
│  - Clicks "Mike Chen" → /seagull/welder/mike-chen → WelderReport        │
└─────────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  PAGES                                                                  │
│  app/seagull/page.tsx        → fetchScore per welder                     │
│  app/seagull/welder/[id]    → fetchSession × 2, fetchScore × 1          │
└─────────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  API (lib/api.ts)                                                       │
│  fetchSession(sessionId)    → GET /api/sessions/{id}                    │
│  fetchScore(sessionId)       → GET /api/sessions/{id}/score              │
└─────────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  PROCESSING (client-side)                                                │
│  generateAIFeedback(session, score, historical) → AIFeedbackResult      │
│  useFrameData(session.frames) → thermal_frames                           │
│  extractHeatmapData(thermal_frames) → HeatmapData                        │
└─────────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  UI COMPONENTS                                                           │
│  HeatMap (×2, Expert | Your Weld), FeedbackPanel, TrendChart, Export    │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Component Structure

```
app/seagull/
  page.tsx                    NEW — Team dashboard, welder cards, fetchScore per welder
  welder/[id]/
    page.tsx                  NEW — WelderReport: score header, AI summary, heatmaps, feedback, trend

components/welding/
  FeedbackPanel.tsx          NEW — Maps feedback_items to FeedbackItem list
  (FeedbackItem inline or separate — small, keep in same file)

lib/
  ai-feedback.ts             NEW — generateAIFeedback(session, score, historical)

types/
  ai-feedback.ts             NEW — AIFeedbackResult, FeedbackItem, etc. (or inline in ai-feedback.ts)

REUSE (no new files):
  components/charts/LineChart.tsx  — TrendChart wraps or uses directly
  components/welding/HeatMap.tsx   — Two instances, Expert + Your Weld
  utils/heatmapData.ts             — extractHeatmapData, tempToColorRange
  hooks/useFrameData.ts            — thermal_frames for heatmap
```

---

## State Management Summary

| Component | State | Triggers |
|-----------|-------|----------|
| **WelderReport** | session, expertSession, score, report, loading, error | useEffect on params.id; fetchSession/fetchScore complete |
| **Team Dashboard** | welders (array of { id, name, sessionId, score }), loading, error | useEffect on mount; fetchScore per welder |
| **FeedbackPanel** | None | Props only |
| **TrendChart** | None | Props: data array |
| **AI feedback** | None (pure) | Called with session, score, historical |

---

## Side Effects (useEffect)

| Page | Effect | When |
|------|--------|------|
| WelderReport | Fetch session + expert + score | `[params.id]` (or resolved sessionId) |
| Team Dashboard | Fetch scores for all welders | `[]` (mount) |
| FeedbackPanel / TrendChart | None | — |

---

## Edge Cases

| Case | Handling |
|------|----------|
| **Loading** | Centered "Loading AI analysis..." or "Loading team..." |
| **Error (fetch fails)** | catch → setError; error card with message + "← Back to Team Dashboard" link (see UX Safeguards §1) |
| **404 session** | fetchSession throws; caught in .catch; setError with actionable message (seed curl command) |
| **Empty frames** | useFrameData returns thermal_frames=[]; extractHeatmapData yields empty HeatmapData; HeatMap shows "No thermal data" |
| **Unknown welder id** | WELDER_MAP[params.id] ?? params.id — use params.id as sessionId (allows /seagull/welder/sess_novice_001) |
| **No historical scores** | Pass [] to generateAIFeedback; trend = "stable"; TrendChart gets mock data |
| **Score loading fails** | Promise.all rejects; same catch; show error card (cannot show report without score) |
| **DB not seeded** | fetchSession 404; catch → "Session not found. Make sure mock data is seeded..." + seed curl in message |

---

## Implementation Approach

### File Tree

```
my-app/src/
  app/seagull/
    page.tsx                      NEW
    welder/[id]/
      page.tsx                    NEW
  components/welding/
    FeedbackPanel.tsx             NEW
  lib/
    ai-feedback.ts                NEW
  types/
    ai-feedback.ts                NEW (or types inline in lib)
```

### Modification vs Creation

| File | Action | Reason |
|------|--------|--------|
| `app/seagull/page.tsx` | Create | New route |
| `app/seagull/welder/[id]/page.tsx` | Create | New route |
| `components/welding/FeedbackPanel.tsx` | Create | New component; reusable |
| `lib/ai-feedback.ts` | Create | AI engine; pure logic |
| `types/ai-feedback.ts` | Create | Shared types; or inline in ai-feedback.ts |
| `components/charts/LineChart.tsx` | **No change** | Reuse as-is for TrendChart |
| `components/welding/HeatMap.tsx` | **No change** | Reuse; static view (no activeTimestamp) |
| `utils/heatmapData.ts` | **No change** | Reuse extractHeatmapData |
| `hooks/useFrameData.ts` | **No change** | Reuse |

### Why This Structure

1. **No lib/mock-data.ts** — Data comes from seeded DB via fetchSession/fetchScore. Keeps single source of truth.
2. **AI feedback in lib/** — Pure function; easy to test; no React deps.
3. **FeedbackPanel separate** — Reusable; could show on replay page later.
4. **TrendChart** — Use existing LineChart; TrendChart can be a thin wrapper or WelderReport passes data directly to LineChart.
5. **Welder-to-session map** — Hardcoded in page; future: config or API.

### Alternatives Considered

| Alternative | Rejected because |
|-------------|------------------|
| Custom hook `useWelderReport` | Adds indirection; data flow is simple; keep in page |
| Backend AI feedback endpoint | Scope creep; pilot is client-side rule-based |
| Separate TrendChart with different LineChart | Existing LineChart fits; no need for new chart |
| FeedbackItem as separate file | Small; keep with FeedbackPanel |
| Use ScorePanel on WelderReport | ScorePanel shows rules only; we need AI summary + feedback items |

---

## Open Questions / Ambiguities

1. **Team dashboard welder count** — With only sess_expert_001 and sess_novice_001, show 2 cards (Mike Chen vs Expert) or add generate_improving_session for 3 distinct profiles?
2. **Welder display names** — Hardcode "Mike Chen" for sess_novice_001, "Expert Benchmark" for sess_expert_001? Or use operator_id from Session (op_novice_01, op_expert_01)?
3. **Feedback item timestamp** — Spec mentioned "specific timestamps" (e.g. "2.3 seconds") — do we derive from frames where rule failed, or omit for pilot?
4. **TrendChart data shape** — Use `{ date: string, value: number }` to match LineChart, or `{ week: number, score: number }`? LineChart expects `date` on X-axis.
5. **Navigation** — Add "Seagull" link to main nav/header, or only via direct URL /seagull?
6. **Export stub behavior** — alert("Email report — coming soon") or toast, or both buttons do the same?
