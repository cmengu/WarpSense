# Seagull Pilot Expansion — Implementation Plan

**Overall Progress:** `100%` (8/8 steps)

---

## TLDR

Add the Seagull pilot UI: team dashboard (`/seagull`) and individual WelderReport (`/seagull/welder/[id]`) with AI-style feedback, side-by-side heatmaps, and trend chart. Data comes from existing seeded sessions via `fetchSession` and `fetchScore`; no new mock-data or seeding work. UX safeguards: explicit error handling for missing sessions and back navigation.

---

## Critical vs Non-Critical Steps

| Step | Critical? | Reason |
|------|-----------|--------|
| Step 1: AI Feedback types | **Yes** | Data contract; underpins report structure |
| Step 2: AI Feedback engine | **Yes** | Transforms SessionScore → AIFeedbackResult; core logic |
| Step 3: WelderReport page | **Yes** | API integration, state management, error handling, data flow |
| Step 4: FeedbackPanel | No | Presentational only |
| Step 5: TrendChart | No | Reuses LineChart; presentational |
| Step 6: Team dashboard | **Yes** | API integration; fetchScore per welder |
| Step 7: Export stubs | No | UI polish |
| Step 8: Verification | No | Smoke tests only |

---

## Critical Decisions

- **No lib/mock-data.ts:** Data from seeded DB via fetchSession/fetchScore. Single source of truth.
- **AI feedback client-side:** Uses fetchScore rules; maps to human-readable feedback. Backend stays rule-based.
- **WELDER_MAP hardcoded:** `mike-chen` → `sess_novice_001`; `expert-benchmark` → `sess_expert_001`; fallback: params.id as sessionId.
- **Error handling required:** .catch in useEffect; error card with seed command; "← Back to Team Dashboard" link.
- **Back nav required:** Link at top of WelderReport when not in error state.
- **TrendChart:** Reuse existing LineChart; mock `{ date, value }[]` for pilot.

---

## Prerequisites (Already Done)

- `fetchSession`, `fetchScore` in lib/api.ts
- HeatMap, extractHeatmapData, tempToColorRange, useFrameData
- Session, Frame types; SessionScore from fetchScore
- Seed/wipe routes; sess_expert_001, sess_novice_001 in DB

---

## Phase 2 Prerequisites (Verify Before Step 3)

### useFrameData Signature

| Param | Type | Purpose |
|-------|------|---------|
| `frames` | `Frame[]` | Raw session frames |
| `startMs` | `number \| null` | Time range start (inclusive). `null` = no lower bound. |
| `endMs` | `number \| null` | Time range end (inclusive). `null` = no upper bound. |

**Return:** `{ thermal_frames: Frame[], all_frames: Frame[], total_count, thermal_count, has_any_thermal, first_timestamp_ms, last_timestamp_ms }`

**Filtering:** Filters by `has_thermal_data` internally via `filterThermalFrames`. Pass `null, null` for full range.

### HeatMap Component Interface

| Prop | Type | Required? | Notes |
|------|------|-----------|-------|
| `sessionId` | string | Yes | For labelling |
| `data` | HeatmapData \| null | No | From extractHeatmapData; undefined shows "No thermal data" |
| `colorFn` | (value_celsius: number) => string | No | Default: tempToColor. Use tempToColorRange for shared scale. |
| `activeTimestamp` | number \| null | No | Static view: omit or pass undefined |
| `label` | string | No | Column heading |
| `valueLabel` | 'temperature' \| 'delta' | No | Tooltip format |

**Before Step 3 — Verification checklist:**
- [ ] 🟥 Verify HeatMap prop interface: colorFn accepted; activeTimestamp optional (pass undefined for static view)
- [ ] 🟥 Confirm sessionId vs label: sessionId for labelling; label for column heading
- [ ] 🟥 Test: render HeatMap in isolation with mock data (e.g. `components/welding/__tests__/HeatMap.test.tsx` or Storybook)

### LineChart Component Interface

| Prop | Type | Notes |
|------|------|-------|
| `data` | `{ date: string; value: number; label?: string }[]` | X-axis uses `date`; line uses `value` |
| `color` | string | Default `#3b82f6` |
| `height` | number | Default 300; ResponsiveContainer height |

---

## Tasks

### Phase 1 — AI Feedback Foundation

**Goal:** Pure `generateAIFeedback(session, score, historical)` → AIFeedbackResult. No UI yet.

- [x] 🟩 **Step 1: AI Feedback types** — *Critical: data contract* ✓ (2026-02-13)

  **Subtasks:**
  - [x] 🟩 Create `my-app/src/types/ai-feedback.ts`
  - [x] 🟩 Define `AIFeedbackResult` (score, skill_level, trend, summary, feedback_items)
  - [x] 🟩 Define `FeedbackItem` (severity, message, timestamp_ms?, suggestion)
  - [x] 🟩 trend type: `'improving' | 'stable' | 'declining' | 'insufficient_data'`

  **✓ Verification Test:**

  **Action:** Import types in a test file; ensure no TypeScript errors.

  **Expected:** Types compile; `AIFeedbackResult` has score, skill_level, trend, summary, feedback_items; `FeedbackItem` has severity, message, suggestion.

  **How to Observe:** `npx tsc --noEmit` in my-app; no type errors.

  **Pass Criteria:** Types defined; imports succeed.

  **Common Failures & Fixes:**
  - **Import fails:** Check file path; ensure `types/` is in tsconfig paths.

---

- [x] 🟩 **Step 2: AI Feedback engine** — *Critical: core logic* ✓ (2026-02-13)

  **Context:** Maps SessionScore (from fetchScore) to AIFeedbackResult. Pure function; no React, no fetch. Determines skill_level, trend, summary, feedback_items from rules.

  **Code (implementation reference):**

  ```typescript
  // lib/ai-feedback.ts
  import type { Session } from '@/types/session';
  import type { SessionScore } from '@/lib/api';
  import type { AIFeedbackResult, FeedbackItem } from '@/types/ai-feedback';

  const RULE_TEMPLATES: Record<string, (r: { actual_value: number | null; threshold: number }) => string> = {
    amps_stability: (r) => `Current fluctuated by ${r.actual_value?.toFixed(1) ?? 'N/A'}A — aim for stability under ${r.threshold}A`,
    angle_consistency: (r) => `Angle deviation ${r.actual_value?.toFixed(1) ?? 'N/A'}° — keep within ±${r.threshold}° of 45°`,
    thermal_symmetry: (r) => `North/south temp delta ${r.actual_value?.toFixed(1) ?? 'N/A'}°C — aim for <${r.threshold}°C`,
    heat_diss_consistency: (r) => `Heat dissipation variability ${r.actual_value?.toFixed(1) ?? 'N/A'} — target <${r.threshold}`,
    volts_stability: (r) => `Voltage range ${r.actual_value?.toFixed(1) ?? 'N/A'}V — keep under ${r.threshold}V`,
  };

  export function generateAIFeedback(
    _session: Session,
    score: SessionScore,
    historicalScores: number[]
  ): AIFeedbackResult {
    // Guard: empty score
    if (!score || !score.rules || score.rules.length === 0) {
      return {
        score: 0,
        skill_level: 'Unknown',
        trend: 'insufficient_data',
        summary: 'No scoring rules available.',
        feedback_items: [],
      };
    }

    const total = score.total;
    const skill_level = total >= 80 ? 'Advanced' : total >= 60 ? 'Intermediate' : 'Beginner';

    // Guard: insufficient historical data for trend
    const trend =
      historicalScores.length < 2
        ? 'insufficient_data'
        : historicalScores[historicalScores.length - 1] > historicalScores[historicalScores.length - 2]
          ? 'improving'
          : historicalScores[historicalScores.length - 1] < historicalScores[historicalScores.length - 2]
            ? 'declining'
            : 'stable';

    const failedRules = score.rules.filter((r) => !r.passed);
    const summary =
      failedRules.length === 0
        ? 'Strong performance across all metrics.'
        : `Focus on: ${failedRules.map((r) => r.rule_id.replace(/_/g, ' ')).join(', ')}.`;

    // Guard: null actual_value in template
    const feedback_items: FeedbackItem[] = score.rules.map((rule) => {
      const template =
        RULE_TEMPLATES[rule.rule_id] ??
        ((r) => `${rule.rule_id}: ${r.actual_value ?? 'N/A'} / ${r.threshold}`);
      const actualVal = rule.actual_value ?? null;
      return {
        severity: rule.passed ? 'info' : 'warning',
        message: template({ actual_value: actualVal, threshold: rule.threshold }),
        timestamp_ms: null,
        suggestion: rule.passed ? null : `Improve ${rule.rule_id.replace(/_/g, ' ')}.`,
      };
    });

    return { score: total, skill_level, trend, summary, feedback_items };
  }
  ```

  **What it does:** Takes Session (unused for pilot), SessionScore, historical array; returns AIFeedbackResult with skill_level, trend, summary, feedback_items from rules.

  **Why this approach:** Reuses fetchScore rules; no port of backend feature extraction; deterministic, testable.

  **Assumptions:**
  - SessionScore.rules has rule_id, passed, actual_value, threshold.
  - Rule IDs match RULE_TEMPLATES keys.

  **Risks:**
  - New rule in backend → add template or fallback.
  - historicalScores empty → trend = "insufficient_data" (guarded).
  - score.rules empty → return early with feedback_items = [] (guarded).
  - rule.actual_value null → template uses "N/A" (guarded).

  **✓ Verification Test:**

  **Action:** Call `generateAIFeedback(session, mockScore, [72, 75])` in a test; assert result shape and trend.

  **Expected:** Returns object with score, skill_level, trend ("improving"), summary string, feedback_items array.

  **How to Observe:** Jest test or console.log in component.

  **Pass Criteria:** Function returns valid AIFeedbackResult; trend derived from historical.

  **Common Failures & Fixes:**
  - **feedback_items empty:** Check score.rules is non-empty.
  - **template undefined:** Add fallback for unknown rule_id.

---

### Phase 2 — WelderReport Page

**Goal:** User can visit `/seagull/welder/mike-chen` and see report with score, AI summary, heatmaps, feedback, trend chart. Error state and back nav work.

- [x] 🟩 **Step 3: WelderReport page** — *Critical: API integration, state management, error handling* ✓ (2026-02-13)

  **Context:** Main Seagull report. Fetches session + expert + score; calls generateAIFeedback; renders heatmaps, FeedbackPanel, TrendChart. Must handle 404/unseeded DB without hanging.

  **Subtasks:**
  - [ ] 🟥 **Handle Next.js 15 async params:** `params` is `Promise<{ id: string }>` — use Option A (server) or Option B (client with `use`)
  - [ ] 🟥 Test with both `/seagull/welder/mike-chen` and `/seagull/welder/expert-benchmark` routes

  **⚠️ Next.js 15 async params (CRITICAL):** Your code assumes `params: { id: string }`. Reality: `params: Promise<{ id: string }>`. Step 3 will fail without handling.

  **Option A — Server Component (recommended):**
  ```tsx
  export default async function WelderReportPage({ params }: { params: Promise<{ id: string }> }) {
    const { id } = await params;
    const sessionId = WELDER_MAP[id] ?? id;
    return <WelderReportClient sessionId={sessionId} />;
  }
  ```

  **Option B — Client Component with use():** Wrap in Suspense (layout or parent) because `use(params)` suspends until Promise resolves.
  ```tsx
  'use client';
  import { use } from 'react';
  export default function WelderReportPage({ params }: { params: Promise<{ id: string }> }) {
    const { id } = use(params);
    const sessionId = WELDER_MAP[id] ?? id;
    // ... rest of client logic
  }
  ```

  **Code (implementation reference):**

  ```tsx
  // app/seagull/welder/[id]/page.tsx
  'use client';

  import { use, useEffect, useState } from 'react';
  import Link from 'next/link';
  import { fetchSession, fetchScore } from '@/lib/api';
  import { generateAIFeedback } from '@/lib/ai-feedback';
  import { useFrameData } from '@/hooks/useFrameData';
  import { extractHeatmapData, tempToColorRange } from '@/utils/heatmapData';
  import HeatMap from '@/components/welding/HeatMap';
  import FeedbackPanel from '@/components/welding/FeedbackPanel';
  import { LineChart } from '@/components/charts/LineChart';
  import type { Session } from '@/types/session';

  const WELDER_MAP: Record<string, string> = {
    'mike-chen': 'sess_novice_001',
    'expert-benchmark': 'sess_expert_001',
  };

  const MOCK_HISTORICAL = [{ date: 'Week 1', value: 68 }, { date: 'Week 2', value: 72 }, { date: 'Week 3', value: 75 }];

  export default function WelderReportPage({ params }: { params: Promise<{ id: string }> }) {
    const { id } = use(params);  // Next.js 15: params is a Promise
    const sessionId = WELDER_MAP[id] ?? id;

    const [session, setSession] = useState<Session | null>(null);
    const [expertSession, setExpertSession] = useState<Session | null>(null);
    const [score, setScore] = useState<{ total: number; rules: unknown[] } | null>(null);
    const [report, setReport] = useState<ReturnType<typeof generateAIFeedback> | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
      setLoading(true);
      setError(null);
      Promise.all([
        fetchSession(sessionId, { limit: 2000 }),
        fetchSession('sess_expert_001', { limit: 2000 }),
        fetchScore(sessionId),
      ])
        .then(([s, e, sc]) => {
          setSession(s);
          setExpertSession(e);
          setScore(sc);
          setReport(generateAIFeedback(s, sc, [68, 72, 75]));
        })
        .catch((err) => {
          console.error('Failed to load:', err);
          setError('Session not found. Make sure mock data is seeded. See STARTME.md: curl -X POST http://localhost:8000/api/dev/seed-mock-sessions');
          setSession(null);
          setExpertSession(null);
          setScore(null);
          setReport(null);
        })
        .finally(() => setLoading(false));
    }, [sessionId]);

    if (error) {
      return (
        <div className="min-h-screen bg-zinc-50 dark:bg-black p-8">
          <div className="bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800 rounded-lg p-6 max-w-md">
            <h2 className="text-lg font-bold text-red-900 dark:text-red-200">⚠️ Error</h2>
            <p className="text-red-800 dark:text-red-300 mt-2 text-sm">{error}</p>
            <Link href="/seagull" className="text-blue-600 dark:text-blue-400 underline mt-4 block">← Back to Team Dashboard</Link>
          </div>
        </div>
      );
    }

    // Hooks must run unconditionally — call before early returns
    const frameData = useFrameData(session?.frames ?? [], null, null);
    const expertFrameData = useFrameData(expertSession?.frames ?? [], null, null);

    if (loading || !report || !session || !expertSession) {
      return <div className="min-h-screen flex items-center justify-center">Loading AI analysis...</div>;
    }
    const heatmapData = extractHeatmapData(frameData.thermal_frames);
    const expertHeatmapData = extractHeatmapData(expertFrameData.thermal_frames);

    const minT = Math.min(...heatmapData.points.map(p => p.temp_celsius), ...expertHeatmapData.points.map(p => p.temp_celsius));
    const maxT = Math.max(...heatmapData.points.map(p => p.temp_celsius), ...expertHeatmapData.points.map(p => p.temp_celsius));
    const colorFn = tempToColorRange(minT, maxT);

    return (
      <div className="min-h-screen bg-zinc-50 dark:bg-black p-8">
        <div className="mb-4">
          <Link href="/seagull" className="text-blue-600 dark:text-blue-400 hover:underline text-sm">← Back to Team Dashboard</Link>
        </div>

        <div className="bg-white dark:bg-zinc-900 rounded-lg shadow p-6 mb-8">
          <div className="flex justify-between items-center">
            <h1 className="text-3xl font-bold">Mike Chen — Weekly Report</h1>
            <div className="text-right">
              <div className="text-5xl font-bold text-blue-600">{report.score}/100</div>
              <div className="text-sm text-zinc-600">{report.skill_level} • {report.trend}</div>
            </div>
          </div>
          <div className="mt-4 p-4 bg-blue-50 dark:bg-blue-950/30 border-l-4 border-blue-500 rounded">
            <p className="text-sm font-medium">🤖 AI Analysis: {report.summary}</p>
          </div>
        </div>

        <div className="bg-white dark:bg-zinc-900 rounded-lg shadow p-6 mb-8">
          <h2 className="text-xl font-bold mb-4">Thermal Comparison</h2>
          <div className="grid grid-cols-2 gap-8">
            <div><h3 className="text-sm font-semibold text-zinc-600 mb-2">Expert Benchmark</h3><HeatMap sessionId="expert" data={expertHeatmapData} colorFn={colorFn} label="Expert" /></div>
            <div><h3 className="text-sm font-semibold text-zinc-600 mb-2">Your Weld</h3><HeatMap sessionId={sessionId} data={heatmapData} colorFn={colorFn} label="Mike Chen" /></div>
          </div>
        </div>

        <div className="bg-white dark:bg-zinc-900 rounded-lg shadow p-6 mb-8">
          <h2 className="text-xl font-bold mb-4">Detailed Feedback</h2>
          <FeedbackPanel items={report.feedback_items} />
        </div>

        <div className="bg-white dark:bg-zinc-900 rounded-lg shadow p-6 mb-8">
          <h2 className="text-xl font-bold mb-4">Progress Over Time</h2>
          <LineChart data={MOCK_HISTORICAL} color="#3b82f6" height={200} />
        </div>

        <div className="flex gap-4">
          <button className="bg-blue-600 text-white px-6 py-3 rounded-lg font-semibold hover:bg-blue-700" onClick={() => alert('Email report — coming soon')}>📧 Email Report</button>
          <button className="bg-zinc-200 text-zinc-800 px-6 py-3 rounded-lg font-semibold hover:bg-zinc-300" onClick={() => alert('Download PDF — coming soon')}>📄 Download PDF</button>
        </div>
      </div>
    );
  }
  ```

  **What it does:** Fetches session, expert, score; generates AI report; renders score header, AI summary, side-by-side heatmaps, FeedbackPanel, LineChart, export stubs. Error state shows actionable message + back link. Back nav at top when success.

  **Why this approach:** Single useEffect; Promise.all for parallel fetch; catch clears state and sets error; render order: error → loading → content.

  **Assumptions:**
  - Next.js 15: params is Promise; use `use(params)` to unwrap.
  - HeatMap accepts colorFn, label, sessionId, data (verified in Phase 2 prerequisites).

  **Risks:**
  - useFrameData hooks run unconditionally with session?.frames ?? []; when loading, thermal_frames empty.
  - HeatMap optional activeTimestamp — omit for static view.

  **✓ Verification Test:**

  **Action:**
  - Seed DB: `curl -X POST http://localhost:8000/api/dev/seed-mock-sessions`
  - Start frontend; visit `/seagull/welder/mike-chen`
  - Verify: score header, AI summary, two heatmaps, feedback list, trend chart, export buttons
  - Click "← Back to Team Dashboard" → navigates to /seagull
  - Stop backend or use invalid sessionId → verify error card appears with message and back link

  **Expected Result:**
  - Page loads with report when DB seeded
  - Back link works
  - Error state when session 404
  - No console errors

  **How to Observe:**
  - Visual: score, heatmaps, feedback, chart
  - Network: 3 requests (fetchSession × 2, fetchScore)
  - Console: no errors

  **Pass Criteria:**
  - Report renders with all sections
  - Error handling prevents infinite loading
  - Back nav works

  **Common Failures & Fixes:**
  - **Loading forever:** Ensure .catch runs; check fetchSession/fetchScore throw on 404.
  - **HeatMap empty:** extractHeatmapData needs thermal_frames; useFrameData filters by has_thermal_data.
  - **params.id undefined / page crash:** Next.js 15 passes `Promise<params>`; use `const { id } = use(params)`.
  - **use() not found:** Import from React: `import { use } from 'react'`.

---

### Phase 3 — Supporting Components

**Goal:** FeedbackPanel renders feedback items; TrendChart shows mock progress.

- [x] 🟩 **Step 4: FeedbackPanel component** (non-critical) ✓ (2026-02-13)

  **Full spec — layout, severity, typography:**

  | Aspect | Spec |
  |--------|------|
  | Layout | Vertical list (`space-y-3`); each item in rounded card |
  | Severity info | `bg-blue-50 dark:bg-blue-950/20`, `border-l-4 border-blue-500` |
  | Severity warning | `bg-amber-50 dark:bg-amber-950/20`, `border-l-4 border-amber-500` |
  | Typography | Message: `text-sm font-medium`; suggestion: `text-xs mt-1` |
  | Icons | info → ℹ️; warning → ⚠️ |
  | Spacing | `p-4`, `flex items-start gap-3` between icon and content |

  **Code (implementation reference):**

  ```tsx
  // components/welding/FeedbackPanel.tsx
  import type { FeedbackItem } from '@/types/ai-feedback';

  interface FeedbackPanelProps {
    items: FeedbackItem[];
  }

  export default function FeedbackPanel({ items }: FeedbackPanelProps) {
    return (
      <div className="space-y-3">
        {items.map((item, i) => (
          <div
            key={i}
            className={`
              p-4 rounded-lg border-l-4
              ${item.severity === 'warning'
                ? 'bg-amber-50 dark:bg-amber-950/20 border-amber-500'
                : 'bg-blue-50 dark:bg-blue-950/20 border-blue-500'
              }
            `}
          >
            <div className="flex items-start gap-3">
              <span className="text-xl">
                {item.severity === 'warning' ? '⚠️' : 'ℹ️'}
              </span>
              <div className="flex-1">
                <p className="text-sm font-medium text-zinc-900 dark:text-zinc-100">
                  {item.message}
                </p>
                {item.suggestion && (
                  <p className="text-xs text-zinc-600 dark:text-zinc-400 mt-1">
                    💡 {item.suggestion}
                  </p>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    );
  }
  ```

  **✓ Verification Test:**

  **Action:** Render FeedbackPanel with mock items (info + warning); check severity colors and layout.

  **Expected:** Items render with correct border/background; icons; suggestion appears when present.

  **Pass Criteria:** Presentational; no state; matches full spec.

---

- [x] 🟩 **Step 5: TrendChart** (non-critical) ✓ (2026-02-13)

  **Subtasks:**
  - [x] 🟩 Use existing `LineChart` from `components/charts/LineChart.tsx`
  - [x] 🟩 **Verify LineChart prop interface:**
    - Data format: `{ date: string, value: number }[]` (X-axis: `date`; line: `value`)
    - Color prop: `color="#3b82f6"` or default
    - Height prop: `height={200}` or wrap in container with fixed height
  - [x] 🟩 Render in isolation: `<LineChart data={[{ date: 'W1', value: 70 }]} />` to confirm interface
  - [x] 🟩 No new TrendChart component; WelderReport imports LineChart directly

  **✓ Verification Test:**

  **Action:** LineChart receives `MOCK_HISTORICAL`; renders in WelderReport.

  **Expected:** Line chart with 3 points; X-axis shows "Week 1", "Week 2", "Week 3"; no "No data available".

  **Pass Criteria:** Chart renders; data format matches LineChart interface.

---

### Phase 4 — Team Dashboard

**Goal:** User can visit `/seagull` and see welder cards with scores; click through to report.

- [x] 🟩 **Step 6: Team dashboard page** — *Critical: API integration* ✓ (2026-02-13)

  **Context:** Fetches fetchScore for each welder; displays cards with name, score, trend; Link to /seagull/welder/[id].

  **Subtasks:**
  - [x] 🟩 Create `app/seagull/page.tsx`
  - [x] 🟩 Hardcode WELDERS = [{ id: 'mike-chen', name: 'Mike Chen', sessionId: 'sess_novice_001' }, { id: 'expert-benchmark', name: 'Expert Benchmark', sessionId: 'sess_expert_001' }]
  - [x] 🟩 **Use Promise.allSettled (not Promise.all)** — one failing score must not block others
  - [x] 🟩 Display error state per welder card (e.g. "Score unavailable") when that welder's fetch fails
  - [x] 🟩 Still show working cards even if one fails
  - [x] 🟩 Cards: name, score (or "Score unavailable"), Link to /seagull/welder/[id]
  - [x] 🟩 Loading state while any fetch pending

  **Code pattern (Promise.allSettled):**

  ```typescript
  Promise.allSettled(welders.map((w) => fetchScore(w.sessionId))).then((results) => {
    const scores = results.map((r, i) => ({
      welder: welders[i],
      score: r.status === 'fulfilled' ? r.value.total : null,
      error: r.status === 'rejected' ? r.reason : null,
    }));
    setWelderScores(scores);
  });
  ```

  **✓ Verification Test:**

  **Action:**
  - Visit `/seagull`
  - Verify 2 cards (Mike Chen, Expert Benchmark) with scores
  - Click Mike Chen → /seagull/welder/mike-chen
  - Simulate one fetch failing (e.g. wrong sessionId for one welder) → other card still shows score; failed card shows "Score unavailable"

  **Expected:** Dashboard shows 2 cards; partial failures don't block working cards.

  **Pass Criteria:** Dashboard loads; Promise.allSettled used; per-card error display.

  **Common Failures & Fixes:**
  - **All cards fail if one fails:** Use Promise.allSettled, not Promise.all.
  - **Wrong score:** Check sessionId mapping.

---

### Phase 5 — Polish

**Goal:** Export buttons show stub behavior.

- [x] 🟩 **Step 7: Export stubs** (non-critical) ✓ (2026-02-13)

  **Subtasks:**
  - [x] 🟩 Email Report button: `onClick={() => alert('Email report — coming soon')}`
  - [x] 🟩 Download PDF button: `onClick={() => alert('Download PDF — coming soon')}`

  **✓ Verification Test:**

  **Action:** Click each button.

  **Expected:** Alert shown.

  **Pass Criteria:** Buttons don't throw.

---

### Phase 6 — Verification

- [x] 🟩 **Step 8: End-to-end verification** ✓ (2026-02-13)

  **Action:**
  - Ensure backend running; seed mock sessions
  - Visit /seagull → see 2 cards
  - Click Mike Chen → see WelderReport with score, AI summary, heatmaps, feedback, chart
  - Click Back → return to dashboard
  - Simulate 404 (wrong sessionId or stop backend) → see error card with back link

  **Expected:** Full flow works; error recovery works.

  **Pass Criteria:** All user paths pass; no crashes.

---

## Pre-Flight Checklist (Print & Check Each Phase)

| Phase | Dependency Check | How to Verify | Status |
|-------|------------------|---------------|--------|
| **Phase 1** | Session, SessionScore types exist | Import from types/session, lib/api | ⬜ |
| | fetchSession, fetchScore work | curl or browser: GET /api/sessions/sess_expert_001, /score | ⬜ |
| **Phase 2** | DB seeded | sess_expert_001, sess_novice_001 exist | ⬜ |
| | HeatMap accepts colorFn, optional activeTimestamp | Render HeatMap with mock data; check props | ⬜ |
| | useFrameData(frames, null, null) returns thermal_frames | Call with mock frames; verify filterThermalFrames applied | ⬜ |
| | Next.js 15: params is Promise | Check Next.js version; use `use(params)` or await | ⬜ |
| **Phase 3** | LineChart data: { date, value }[], color, height | components/charts/LineChart.tsx interface | ⬜ |
| **Phase 4** | Same as Phase 2 | — | ⬜ |

---

## Risk Heatmap (Where You'll Get Stuck)

| Phase | Risk Level | What Could Go Wrong | How to Detect Early |
|-------|-----------|---------------------|---------------------|
| Phase 1 | 🟡 30% | AIFeedbackResult shape doesn't match FeedbackPanel | Type error when passing items |
| Phase 2 | 🔴 60% | fetchSession 404 hangs (no catch) | Loading forever; add catch + setError |
| Phase 2 | 🟡 40% | useFrameData before session set | Guard ensures session non-null; hooks run after guard |
| Phase 4 | 🟡 40% | fetchScore fails for one welder | Use Promise.allSettled; per-card "Score unavailable" |

---

## Success Criteria (End-to-End Validation)

| Feature | Target Behavior | Verification Method |
|---------|-----------------|---------------------|
| **Team dashboard** | 2 welder cards, scores from API | Visit /seagull → cards show; network: fetchScore × 2 |
| **WelderReport** | Score, AI summary, heatmaps, feedback, trend chart | Visit /seagull/welder/mike-chen → all sections visible |
| **Error handling** | 404 shows error card + back link | Unseeded DB or invalid id → error state; no infinite loading |
| **Back navigation** | Link returns to dashboard | Click "← Back to Team Dashboard" → /seagull |
| **Export stubs** | Buttons show alert | Click Email/PDF → alert |

---

⚠️ **Do not mark a step as 🟩 Done until its verification test passes. If blocked, mark 🟨 In Progress and document what failed.**
