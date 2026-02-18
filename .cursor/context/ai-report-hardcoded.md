# Seagull Pilot — Project Context

> **Purpose:** High-level context for the Seagull pilot (8-step implementation). What exists, what patterns to follow, what constraints to respect.  
> **For AI:** Reference with `@.cursor/context/ai-report-hardcoded.md` to avoid reimplementing or violating patterns.  
> **Last Updated:** 2026-02-13

---

## Project Overview

**Name:** Seagull Pilot Expansion  
**Type:** Web App Feature (Next.js)  
**Stack:** React 19, Next.js 16, TypeScript, Tailwind  
**Stage:** MVP — Complete

**Purpose:** Team dashboard and individual welder reports with AI-style feedback, side-by-side heatmaps, trend chart. Data from seeded sessions via `fetchSession` and `fetchScore`.

**Current State:**
- ✅ Step 1: AI Feedback types
- ✅ Step 2: AI Feedback engine
- ✅ Step 3: WelderReport page
- ✅ Step 4: FeedbackPanel
- ✅ Step 5: TrendChart (LineChart)
- ✅ Step 6: Team dashboard
- ✅ Step 7: Export stubs
- ✅ Step 8: E2E smoke tests

---

## Architecture

### System Pattern

```
/seagull (Dashboard) → fetchScore per welder → Cards with score or "Score unavailable"
/seagull/welder/[id] (Report) → fetchSession×2 + fetchScore → generateAIFeedback → HeatMap×2, FeedbackPanel, LineChart
```

**Key Decisions:**
- **No lib/mock-data.ts:** Data from seeded DB via fetchSession/fetchScore. Single source of truth.
- **AI feedback client-side:** Uses fetchScore rules; maps to human-readable feedback via `generateAIFeedback`. Backend stays rule-based.
- **WELDER_MAP hardcoded:** `mike-chen` → `sess_novice_001`; `expert-benchmark` → `sess_expert_001`; fallback: params.id as sessionId.
- **Promise.allSettled (Dashboard):** One failing score must not block others. Per-card "Score unavailable".
- **Promise.all (WelderReport):** All 3 fetches needed for coherent report; fail-fast with error card.

---

## Implemented Features

> **AI Rule:** Don't reimplement what's listed here.

### AI Feedback Types
**Status:** ✅  
**What:** Data contract for `generateAIFeedback` → `AIFeedbackResult`  
**Location:** `my-app/src/types/ai-feedback.ts`  
**Exports:** `FeedbackSeverity`, `FeedbackItem`, `FeedbackTrend`, `AIFeedbackResult`

### AI Feedback Engine
**Status:** ✅  
**What:** Pure function `generateAIFeedback(session, score, historicalScores)` → `AIFeedbackResult`  
**Location:** `my-app/src/lib/ai-feedback.ts`  
**Rule templates:** amps_stability, angle_consistency, thermal_symmetry, heat_diss_consistency, volts_stability  
**Guards:** Empty score → Unknown; historicalScores.length < 2 → insufficient_data; null actual_value → "N/A"

### WelderReport Page
**Status:** ✅  
**What:** Individual welder report at `/seagull/welder/[id]`  
**Location:** `my-app/src/app/seagull/welder/[id]/page.tsx`  
**Fetches:** session, expert session (sess_expert_001), score via Promise.all  
**Renders:** Score header, AI summary, side-by-side HeatMaps (shared color scale), FeedbackPanel, LineChart, Email/PDF stub buttons  
**Error:** Error card with actionable message + "← Back to Team Dashboard" link

### FeedbackPanel
**Status:** ✅  
**What:** Renders AI feedback items with severity styling (info=blue, warning=amber)  
**Location:** `my-app/src/components/welding/FeedbackPanel.tsx`  
**Props:** `items: FeedbackItem[]`

### Team Dashboard
**Status:** ✅  
**What:** Welder cards with score or "Score unavailable" at `/seagull`  
**Location:** `my-app/src/app/seagull/page.tsx`  
**Fetches:** `Promise.allSettled(WELDERS.map(w => fetchScore(w.sessionId)))`  
**WELDERS:** Mike Chen (sess_novice_001), Expert Benchmark (sess_expert_001)

---

## Data Models

### AIFeedbackResult

```typescript
{
  score: number;           // 0–100
  skill_level: string;     // "Beginner" | "Intermediate" | "Advanced" | "Unknown"
  trend: FeedbackTrend;    // "improving" | "stable" | "declining" | "insufficient_data"
  summary: string;
  feedback_items: FeedbackItem[];
}
```

**Used by:** WelderReport, FeedbackPanel  
**Flow:** SessionScore (fetchScore) → generateAIFeedback → AIFeedbackResult

### FeedbackItem

```typescript
{
  severity: "info" | "warning";
  message: string;
  timestamp_ms: number | null;
  suggestion: string | null;
}
```

**Used by:** FeedbackPanel  
**Flow:** SessionScore.rules → generateAIFeedback → FeedbackItem[]

### Welder / WelderScoreResult

```typescript
interface Welder { id: string; name: string; sessionId: string; }
interface WelderScoreResult { welder: Welder; score: number | null; error: unknown; }
```

**Used by:** Dashboard page  
**Flow:** WELDERS → fetchScore → WelderScoreResult[]

---

## Patterns

> **AI Rule:** Follow these for consistency.

### Next.js 15/16 Async Params
**Use when:** Dynamic route params (e.g. `[id]`)  
**How:** `params` is `Promise<{ id: string }>`. Use `isPromise(params)` → wrap in `Suspense` with inner component that `use(params)`. Otherwise pass plain `params.id` (for tests).  
**Location:** `WelderReportPage`, `ReplayPage`

### Hooks Before Early Returns
**Use when:** Components with conditional early returns (error, loading)  
**How:** Call `useFrameData` (and all hooks) before any `if (error) return ...`. Hooks must run unconditionally.  
**Location:** WelderReportInner

### useEffect Cleanup for Fetch
**Use when:** `useEffect` with async fetch and setState  
**How:** `let mounted = true`; in `.then`/`.catch`/`.finally` check `if (!mounted) return`; `return () => { mounted = false; }`.  
**Location:** WelderReport, SeagullDashboardPage

### Error Logging
**Use when:** Catching errors in async handlers  
**How:** `logError("ComponentName", err)` from `@/lib/logger`. Not `console.error`.  
**Location:** WelderReport

### FeedbackPanel List Keys
**Use when:** Mapping FeedbackItem[]  
**How:** `key={\`${item.severity}-${i}-${item.message.slice(0, 40)}\`}` — stable key, not raw index.

---

## Integration Points

> **AI Rule:** Use these, don't recreate.

### fetchSession
**What:** GET session with frames  
**API:** `fetchSession(sessionId, { limit?: 2000 })`  
**Used by:** WelderReport  
**Returns:** `Session`

### fetchScore
**What:** GET session score (total + rules)  
**API:** `fetchScore(sessionId)`  
**Used by:** WelderReport, Dashboard  
**Returns:** `SessionScore` (total, rules[])

### useFrameData
**What:** Filters frames to thermal subset  
**API:** `useFrameData(frames, startMs, endMs)` — pass `null, null` for full range  
**Returns:** `{ thermal_frames, all_frames, ... }`  
**Used by:** WelderReport

### extractHeatmapData + tempToColorRange
**What:** Extract heatmap points from thermal frames; shared color scale for comparison  
**API:** `extractHeatmapData(frames)`; `tempToColorRange(minT, maxT)`  
**Used by:** WelderReport (side-by-side heatmaps)

### LineChart
**What:** Recharts line chart for "Progress Over Time"  
**API:** `LineChart({ data: { date, value }[], color?, height? })`  
**Used by:** WelderReport with MOCK_HISTORICAL

---

## Constraints

> **AI Rule:** Respect these, don't work around them.

### Welder IDs
**What:** Only `mike-chen` and `expert-benchmark` are mapped. Others fall back to id as sessionId.  
**Handle:** Add to WELDER_MAP / WELDERS when adding new pilots.

### Historical Scores
**What:** Trend requires ≥2 historical scores. Pilot uses hardcoded `[68, 72, 75]`.  
**Handle:** Future: fetch from API. For now `insufficient_data` when < 2.

### Seed Required
**What:** Sessions must be seeded for WelderReport/Dashboard to show data.  
**Handle:** Error message references `curl -X POST http://localhost:8000/api/dev/seed-mock-sessions`

### Promise.all vs allSettled
**What:** Dashboard uses allSettled (partial success). WelderReport uses all (all-or-nothing).  
**Why:** Dashboard cards independent; WelderReport needs all 3 for coherent view.

---

## File Structure

```
my-app/src/
  types/
    ai-feedback.ts          # AIFeedbackResult, FeedbackItem, FeedbackTrend
  lib/
    ai-feedback.ts          # generateAIFeedback
    logger.ts               # logError (use, not console.error)
  app/
    seagull/
      page.tsx              # Team dashboard
      welder/[id]/
        page.tsx            # Welder report
  components/
    welding/
      FeedbackPanel.tsx     # Feedback items with severity styling
  __tests__/
    types/ai-feedback.test.ts
    lib/ai-feedback.test.ts
    components/welding/FeedbackPanel.test.tsx
    components/charts/LineChart.test.tsx
    app/seagull/
      page.test.tsx
      welder/[id]/page.test.tsx
      seagull-flow-smoke.test.tsx
```

---

## API Contracts

### GET /api/sessions/:id
**Purpose:** Fetch session with frames  
**Used by:** WelderReport (×2: welder session + expert)  
**Params:** `limit=2000`

### GET /api/sessions/:id/score
**Purpose:** Fetch session score (total, rules)  
**Used by:** WelderReport, Dashboard  
**Response:** `{ total: number, rules: ScoreRule[] }`

---

## Component APIs

### FeedbackPanel
**Purpose:** Renders feedback items with severity styling  
**Props:** `items: FeedbackItem[]`  
**Location:** `components/welding/FeedbackPanel.tsx`  
**Styling:** info → blue, warning → amber; icons ℹ️/⚠️

### HeatMap (existing)
**Purpose:** Thermal heatmap visualization  
**Props:** `sessionId`, `data`, `colorFn`, `label?`, `valueLabel?`  
**Used by:** WelderReport (×2 with shared tempToColorRange)

### LineChart (existing)
**Purpose:** Line chart for progress  
**Props:** `data: { date, value }[]`, `color?`, `height?`  
**Used by:** WelderReport with MOCK_HISTORICAL

---

## Not Implemented

> **AI Rule:** Don't assume these exist.

### Email Report / Download PDF
**Status:** Stub  
**What:** Buttons show `alert('… coming soon')`  
**Why not yet:** Pilot scope

### Real Historical Scores
**Status:** Mock  
**What:** `[68, 72, 75]` hardcoded  
**Why not yet:** No backend endpoint for historical

### Trend on Dashboard Cards
**Status:** Not in scope  
**What:** Dashboard shows score only, not trend  
**Why not yet:** Would require historical per welder

---

## Related Docs

| File | Purpose |
|------|---------|
| `docs/SEAGULL_STEP1_AI_FEEDBACK_TYPES_PROCESS.md` | Step-by-step process log |
| `.cursor/plans/seagull-pilot-expansion-plan.md` | Full plan with verification |
| `.cursor/context/context-tech-stack-mvp-architecture.md` | Backend + frontend data flow |

---

**Maintenance:** Update when adding welders, changing AI feedback rules, or new Seagull features.
