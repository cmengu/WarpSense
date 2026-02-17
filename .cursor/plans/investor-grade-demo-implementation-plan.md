# Investor-Grade Demo — Implementation Blueprint (Refined)

**Issue:** `.cursor/issues/investor-grade-demo-guided-tour-seagull.md`  
**Exploration:** `.cursor/explore/investor-grade-demo-exploration.md`  
**Time Budget:** 90–120 minutes minimum for plan creation  
**Total Implementation Estimate:** 20–34 hours (Phase 1 ~8–10h, Phase 2 ~6–8h, Phase 3 ~3–4h; +2–4h buffer for debugging, E2E, cross-browser)  
**Created:** 2026-02-17

---

## MANDATORY PRE-PLANNING THINKING SESSION

### A. Exploration Review and Synthesis

**1. Core approach (one sentence):**  
Build a custom lightweight tour overlay with config-driven steps plus a dedicated browser-only team path at `/demo/team`, reusing all Seagull components (HeatMap, FeedbackPanel, LineChart, generateAIFeedback) and feeding them data from `getDemoTeamData` + `createMockScore`, with a "See Team Management" CTA connecting demo to team story.

**Key decisions:**
- Custom tour (no react-joyride/driver.js) — full control, no deps, explicit logic. **Contingency:** If timeline allows and prototype proves brittle, consider Driver.js or Shepherd.js; custom is high-risk for complex overlays.
- `/demo/team` as dedicated route — clean separation from API-dependent `/seagull`
- `lib/seagull-demo-data.ts` for mock SessionScore and `getDemoTeamData` — keeps demo-data.ts focused on sessions
- Tour z-index 200 with `isolate` — beats TorchWithHeatmap3D (z-100). **Contingency:** If Safari issues, increase to z-[300].
- AppNav "Team" → `/seagull`; Demo CTA → `/demo/team`
- Preset timestamp 2400ms for novice spike (sine peak in demo-data)
- **Config-driven thresholds:** Single `src/lib/demo-config.ts` for score thresholds, novice spike timestamp, welder list — mock and real AI logic share same source of truth. **CEO rule: No magic numbers anywhere else.**
- **Mock data integrity:** Mock data must never lie visually; investors notice discrepancies. getDemoTeamData must exactly match the shape generateAIFeedback expects.

**2. Major components:**
- **DemoTour** (components/demo/DemoTour.tsx): Overlay with step config, Next/Skip, optional scrub callback. z-[200], isolate. **Focus trap, aria-modal, role="dialog", aria-labels.** Highlight fallback when highlightSelector fails. Animated transitions.
- **demo-tour-config.ts**: Tour step definitions (title, body, highlightSelector?, timestamp_ms?, nextLabel, isLast). Pulls `NOVICE_SPIKE_MS` from demo-config. 2–4 steps.
- **demo-config.ts** (new): `NOVICE_SPIKE_MS`, `MOCK_EXPERT_SCORE_VALUE`, `MOCK_NOVICE_SCORE_VALUE`, `DEMO_WELDERS` array (dynamic, not just two).
- **seagull-demo-data.ts**: `createMockScore(total, failedRuleIds)`, `getDemoTeamData(welderId)` returning `{ session, expertSession, score, report }`. Uses thresholds from demo-config. **Shape must exactly match ai-feedback.test mockScore pattern; every rule_id must exist in RULE_TEMPLATES.**
- **utils/heatmapTempRange.ts** (new): `computeMinMaxTemp(points, fallbackMin?, fallbackMax?)` — shared min/max logic with fallback. **Handle empty arrays, null/undefined points, invalid temp_celsius (NaN, null, Infinity).**
- **app/demo/team/page.tsx**: Team dashboard with dynamic welder cards from config.
- **app/demo/team/[welderId]/page.tsx**: Welder report (HeatMap, FeedbackPanel, LineChart) driven by getDemoTeamData. **Critical: Empty frames MUST render PlaceholderHeatMap with neutral gradient — no white screen.**
- **AppNav**: Add Team link → /seagull.
- **Demo page**: Integrate DemoTour, add CTA "See Team Management" → /demo/team. **Debounced scrub callback.** Handle empty/malformed frames.

**3. Data flow:**
```
Input: User visits /demo
  ↓
Transform: generateExpertSession(), generateNoviceSession() → sessions
  ↓
Process: DemoTour steps config → overlay, onStepEnter(step) → debounced setCurrentTimestamp(step.timestamp_ms), setPlaying(false)
  ↓
Output: Narrative overlays, scrub to 2400ms, CTA → /demo/team

Input: User visits /demo/team
  ↓
Transform: getDemoTeamData() or getDemoTeamDataAsync() → { session, expertSession, score, report }
  ↓
Process: createMockScore from config, generateAIFeedback(session, score, historical)
  ↓
Output: Team dashboard with cards; /demo/team/[welderId] → full welder report
```

**4. Biggest risks:**
- **Risk #1:** Tour overlay hidden behind 3D Canvas — z-index/stacking in Safari. Mitigation: z-[200], isolate; if Safari fails, z-[300].
- **Risk #2:** Browser-only Seagull diverges from API Seagull — two code paths. Mitigation: Reuse same components; only data layer differs.
- **Risk #3:** Mock SessionScore shape mismatch — generateAIFeedback expects rule_ids from RULE_TEMPLATES. Mitigation: **Copy ai-feedback.test.ts mockScore pattern exactly; unit test every rule_id.**
- **Risk #4:** Preset timestamp wrong — narrative says "2.3s" but spike at 2.5s. Mitigation: Use 2400ms from demo-config (exploration verified sine peaks ~2.4–2.6s).
- **Risk #5:** Mobile tour UX poor — overlay too small. Mitigation: Responsive overlay, test at 375px.
- **Risk #6:** Navigation during tour — CTA or external nav might redirect mid-tour. Mitigation: Dismiss overlay before redirect; ensure onComplete/onSkip clear state.
- **Risk #7:** Empty frames → white screen. Mitigation: **Always render PlaceholderHeatMap (neutral gradient) when point_count === 0 or frames empty/null. Non-negotiable.**

**5. Phase dependency — HARD GATE:**
**Phase 2 cannot begin until:**
- (a) All Phase 1 unit and integration tests pass
- (b) /demo/team loads without errors
- (c) /demo/team/mike-chen renders (HeatMap or PlaceholderHeatMap) without white screen
- (d) No fetchSession/fetchScore calls when visiting /demo/team

---

### B. Dependency Brainstorm

**Major work items (before ordering):**
1. demo-config.ts (thresholds, welders, constants)
2. utils/heatmapTempRange.ts (computeMinMaxTemp)
3. createMockScore + getDemoTeamData in seagull-demo-data.ts
4. lib/seagull-demo-data.ts (new file)
5. app/demo/team/page.tsx (team dashboard)
6. app/demo/team/[welderId]/page.tsx (welder report)
7. lib/demo-tour-config.ts (step definitions)
8. components/demo/DemoTour.tsx (tour overlay: focus trap, a11y, highlight fallback, step logging)
9. Integrate DemoTour into app/demo/page.tsx (debounced onStepEnter)
10. Add "See Team Management" CTA to demo
11. Add Team link to AppNav
12. Add data-tour attributes (if using highlightSelector)
13. Responsive tour overlay styling, max/min width, z-index per breakpoint
14. Keyboard and touch gesture testing
15. Verification tests (unit, integration, E2E with Playwright/Cypress)
16. Contingency demo path documentation
17. Optional: feature flags for CTA/tour (toggle off if fails)

**Dependency graph:**
```
demo-config.ts
  ↓
createMockScore + getDemoTeamData (seagull-demo-data.ts)
  ↓
heatmapTempRange.ts (welder report min/max)
  ↓
app/demo/team/page.tsx
  ↓
app/demo/team/[welderId]/page.tsx

lib/demo-tour-config.ts (imports from demo-config)
  ↓
DemoTour.tsx
  ↓
Integrate into demo/page.tsx (debounce)
  ↓
Add CTA

AppNav modification (independent)
```

**Critical path:** demo-config → seagull-demo-data → team pages → tour config → DemoTour → demo integration → CTA. AppNav is parallel.

---

### C. Risk-Based Planning

**Top risks from exploration + critique:**
1. Tour z-index wrong (P 25%, I Medium) — Use z-[200] isolate; Safari test early; Contingency: z-[300].
2. Mock score shape wrong (P 20%, I Medium) — Copy ai-feedback.test mockScore exactly; unit test createMockScore with generateAIFeedback; Contingency: Add assertion for every rule_id.
3. Browser-only drift (P 60%, I Medium) — Reuse components; only data source differs; Contingency: Extract shared WelderReportView.
4. Preset timestamp wrong (P 30%, I Low) — Use demo-config.NOVICE_SPIKE_MS; Contingency: Adjust config.
5. Mobile overlay poor (P 40%, I Medium) — Responsive overlay; max-width, min-width; test 375px early in Phase 2.
6. Focus trap / a11y (P 35%, I Medium) — Trap focus inside overlay; Tab/Escape tests; Contingency: Document keyboard shortcut clearly.
7. Empty frames / white screen (P 50%, I High) — Always show PlaceholderHeatMap with neutral gradient; no exceptions.
8. Phase 2 started before Phase 1 done (P 30%, I High) — Hard gate: Phase 1 tests must pass first.

**Failure modes:**
1. If tour doesn't render: Check z-index, ensure DemoTour is inside demo page DOM
2. If highlightSelector fails: **Fallback:** Use default element (e.g. overlay center) or no spotlight; animate transitions to avoid abrupt jumps
3. If getDemoTeamData returns wrong shape: useFrameData expects frames[]; verify session.frames; handle null/undefined
4. If createMockScore breaks generateAIFeedback: rule_ids must match RULE_TEMPLATES exactly
5. If /demo/team 404: Verify route exists at src/app/demo/team/page.tsx
6. If CTA links wrong: Should be /demo/team not /seagull
7. If playback overrides scrub: setPlaying(false) when onScrubToTimestamp called; debounce scrub to prevent UI lag
8. If Skip doesn't dismiss: Ensure state clears, overlay unmounts
9. If AppNav Team goes to wrong URL: Should be /seagull
10. If novice spike not visible at 2400ms: Adjust NOVICE_SPIKE_MS in demo-config
11. If empty/malformed frames: Show PlaceholderHeatMap with neutral gradient; never white screen
12. If navigation interrupts tour: Dismiss overlay before redirect; test CTA click flow

---

## 1. Phase Breakdown Strategy

### A. Natural Breaking Points

**Phase boundaries:**
1. After seagull-demo-data + team pages — User can view team dashboard and welder report without backend
2. After DemoTour + config — User can see guided tour on /demo
3. After integration + CTA + AppNav — User has full investor flow: demo → tour → CTA → team

**Valid phase boundaries (all Yes):**
- Phase 1: Browser-only team path — Ship alone? Yes. User value? Yes. Testable? Yes. **Must pass tests before Phase 2.**
- Phase 2: Guided tour — **Time-box steps first, then polish.** Don't commit extended window until prototype works. **Integrate only after Phase 1 tests pass.**
- Phase 3: CTA + AppNav + polish — Completes investor flow. Depends on Phase 1 and 2.

### B. Phase Design

**Phase 1: Browser-Only Team Path (~8–10 hours)**  
**Goal:** User can view team dashboard and welder report without backend.  
**Includes:** demo-config.ts, heatmapTempRange.ts, seagull-demo-data.ts, /demo/team, /demo/team/[welderId], frame validation, placeholder HeatMap, computeMinMaxTemp, **all unit and integration tests.**  
**After:** User can open /demo/team, see dynamic welder cards (Mike Chen 42, Expert Benchmark 94), click into welder report, see HeatMap (or PlaceholderHeatMap with neutral gradient when no frames), FeedbackPanel, LineChart. **All Phase 1 tests pass.**

**Phase 2: Guided Tour (~6–8 hours)**  
**Goal:** User sees 2–4 step narrative overlay on /demo explaining expert vs novice.  
**Includes:** demo-tour-config.ts, DemoTour component (focus trap, a11y, highlight fallback, step logging, transitions), integrate into demo page, **debounced** scrub callback, preset 2400ms. **Cross-browser testing (Safari, Firefox, Chrome) and device testing (375px, iPad, iPhone) early — do not wait until Phase 3.**  
**After:** User opens /demo, sees tour overlay, can Next/Skip, Tab/Escape work, at one step scrubs to 2.4s novice spike. **Verified on Safari.** **Contingency demo path** documented.

**Phase 3: CTA, AppNav, Polish (~3–4 hours)**  
**Goal:** Full investor flow with discoverable team path.  
**Includes:** "See Team Management" CTA (dismiss overlay before navigate), AppNav Team link, responsive tour (max/min width, z-index per breakpoint), keyboard/touch testing. Optional feature flags.  
**After:** User completes tour or skips, sees CTA, navigates to /demo/team; app users see Team in nav. Navigation never interrupts tour.

**Time rationale:** Phase headers include buffer. Pad for debugging real behavior, not happy-path scenarios. Unit tests and placeholder handling add 1–2h to Phase 1.

### C. Phase Dependency Graph

```
Phase 1 (Browser-Only Team) ──┬──→ Phase 2 (Guided Tour) ──→ Phase 3 (CTA + AppNav)
   │                              │
   └──────────────────────────────┘
   HARD GATE: Phase 1 tests pass
```

Phase 2 depends on Phase 1 (tests pass, /demo/team works). Phase 3 depends on both.

### D. Phase Success Criteria

**Phase 1 Done When:**
- [ ] demo-config.ts has NOVICE_SPIKE_MS, score thresholds, DEMO_WELDERS; **validation test asserts all expected values**
- [ ] computeMinMaxTemp utility exists with fallback; **test empty array, invalid temps, null points**
- [ ] createMockScore(94, []) and createMockScore(42, [...]) produce valid SessionScore; **generateAIFeedback accepts them; every rule_id tested**
- [ ] getDemoTeamData('mike-chen') returns session, expertSession, score, report; **report.score === 42**
- [ ] getDemoTeamData('expert-benchmark') returns report.score === 94
- [ ] /demo/team loads and shows welder cards (from config)
- [ ] /demo/team/mike-chen loads and shows HeatMap or PlaceholderHeatMap (neutral gradient) when no frames; **no white screen**
- [ ] No fetchSession/fetchScore when visiting /demo/team
- [ ] All Phase 1 verification tests pass (automated)

**Phase 2 Done When:**
- [ ] DemoTour renders overlay with 2–4 steps
- [ ] Next advances steps; Skip dismisses tour
- [ ] Focus trapped inside overlay; Tab/Escape work; aria-modal, role="dialog", aria-labels
- [ ] Highlight fallback when highlightSelector fails; animated transitions
- [ ] Step with timestamp_ms scrubs playback (debounced) to 2.4s
- [ ] Step logging for debug during investor demo
- [ ] Visual checklist for overlay steps
- [ ] **Tested on Safari, Firefox, Chrome** — overlay visible, z-index correct, no scroll-off
- [ ] **375px viewport** — overlay no overflow, buttons accessible
- [ ] All Phase 2 verification tests pass (automated)

**Phase 3 Done When:**
- [ ] "See Team Management" CTA visible; dismisses overlay before navigate
- [ ] CTA links to /demo/team
- [ ] AppNav has Team link → /seagull
- [ ] Tour responsive at 375px; max/min width, z-index per breakpoint
- [ ] Keyboard and touch gestures verified on mobile
- [ ] All Phase 3 verification tests pass (automated)

---

## 2. Step Definition

### Critical vs Non-Critical Classification

| Step | Type | Critical? | Reason |
|------|------|-----------|--------|
| 1.1 demo-config + heatmapTempRange | Config/Util | Yes | Single source of truth; min/max fallback; edge cases |
| 1.2 createMockScore + seagull-demo-data | Backend/Data | Yes | Mock shape must exactly match generateAIFeedback |
| 1.3 Team dashboard page | Page | Yes | New route; data flow |
| 1.4 Welder report page | Page | Yes | Reuse components; frame validation; PlaceholderHeatMap mandatory |
| 1.5 Unit tests | Test | Yes | **Phase 2 gate: cannot proceed without passing** |
| 2.1 demo-tour-config | Config | No | Simple config object |
| 2.2 DemoTour component | Component | Yes | Overlay, focus trap, a11y, highlight fallback |
| 2.3 Integrate tour into demo | Integration | Yes | Debounced callback, empty/malformed frame handling |
| 2.4 Cross-browser testing | Test | Yes | Safari, Chrome, Firefox; 375px early |
| 3.1 CTA component | UI | No | Dismiss before navigate |
| 3.2 AppNav Team link | UI | No | Add one Link |
| 3.3 Responsive + a11y | Polish | No | Styling, aria, breakpoint testing |

---

## Phase 1 — Browser-Only Team Path

**Goal:** User can view team dashboard and welder report without backend.  
**Time Estimate:** ~8–10 hours (includes 1–2h test buffer)  
**Risk Level:** 🟡 Medium (browser-only data path)

---

#### Step 1.1: Create demo-config.ts and heatmapTempRange utility — *Critical: Single source of truth*

**Why critical:** Magic numbers scattered across mock and tour cause drift. Mock data must never lie visually; investors notice discrepancies. **CEO rule: No magic numbers outside config.** A single config ensures mock and real AI logic share the same thresholds.

**Files:** Create `src/lib/demo-config.ts`, Create `src/utils/heatmapTempRange.ts`

**demo-config.ts:**
```typescript
// src/lib/demo-config.ts
/**
 * Demo mode configuration — single source of truth for thresholds and mock data.
 * Mock and real AI logic share these values. Do not duplicate anywhere.
 */

/** Timestamp (ms) for novice temperature spike narrative. Sine peak ~2.4–2.6s. */
export const NOVICE_SPIKE_MS = 2400;

/** Mock expert score (all rules pass). */
export const MOCK_EXPERT_SCORE_VALUE = 94;

/** Mock novice score (3 rules fail). */
export const MOCK_NOVICE_SCORE_VALUE = 42;

/** Failed rule IDs for novice mock. Must match RULE_TEMPLATES keys in ai-feedback.ts. */
export const MOCK_NOVICE_FAILED_RULES = [
  'amps_stability',
  'angle_consistency',
  'thermal_symmetry',
] as const;

export interface DemoWelder {
  id: string;
  name: string;
  score: number;
  variant: 'novice' | 'expert';
}

/** Welders for team dashboard. Extend for QA/demos with more welders. */
export const DEMO_WELDERS: DemoWelder[] = [
  { id: 'mike-chen', name: 'Mike Chen', score: 42, variant: 'novice' },
  { id: 'expert-benchmark', name: 'Expert Benchmark', score: 94, variant: 'expert' },
];
```

**heatmapTempRange.ts:**
```typescript
// src/utils/heatmapTempRange.ts
/**
 * Compute min/max temperature from heatmap points with fallback.
 * Extracted for reuse across team report, compare, replay.
 * Handles: empty array, null/undefined points, invalid temp_celsius.
 */

import { THERMAL_MIN_TEMP, THERMAL_ABSOLUTE_MAX } from '@/constants/thermal';

export interface HeatmapPoint {
  temp_celsius: number;
}

/**
 * Returns { min, max } from points, or fallback when empty/invalid.
 * Fallbacks from thermal constants (0°C, 600°C).
 * Filters out null, undefined, NaN, Infinity.
 */
export function computeMinMaxTemp(
  points: Array<{ temp_celsius?: number | null }> | null | undefined,
  fallbackMin: number = THERMAL_MIN_TEMP,
  fallbackMax: number = THERMAL_ABSOLUTE_MAX
): { min: number; max: number } {
  if (!points || !Array.isArray(points) || points.length === 0) {
    return { min: fallbackMin, max: fallbackMax };
  }
  const temps = points
    .map((p) => p?.temp_celsius)
    .filter((t): t is number => t != null && Number.isFinite(t));
  if (temps.length === 0) {
    return { min: fallbackMin, max: fallbackMax };
  }
  const min = Math.min(...temps);
  const max = Math.max(...temps);
  if (min > max || !Number.isFinite(min) || !Number.isFinite(max)) {
    return { min: fallbackMin, max: fallbackMax };
  }
  return { min, max };
}
```

**Verification (specific assertions):**
- **Test file:** `src/__tests__/lib/demo-config.test.ts`, `src/__tests__/utils/heatmapTempRange.test.ts`
- **demo-config:** `expect(NOVICE_SPIKE_MS).toBe(2400); expect(MOCK_EXPERT_SCORE_VALUE).toBe(94); expect(MOCK_NOVICE_SCORE_VALUE).toBe(42); expect(DEMO_WELDERS.length).toBeGreaterThanOrEqual(2); expect(DEMO_WELDERS[0].score).toBe(42); expect(DEMO_WELDERS[1].score).toBe(94);`
- **heatmapTempRange:** 
  - `computeMinMaxTemp([])` → `{ min: 0, max: 600 }`
  - `computeMinMaxTemp(null)` → fallback
  - `computeMinMaxTemp(undefined)` → fallback
  - `computeMinMaxTemp([{ temp_celsius: 100 }, { temp_celsius: 400 }])` → `{ min: 100, max: 400 }`
  - `computeMinMaxTemp([{ temp_celsius: NaN }, { temp_celsius: 200 }])` → `{ min: 200, max: 200 }` or fallback per impl
  - `computeMinMaxTemp([{ temp_celsius: undefined }])` → fallback

**Time estimate:** 1–1.5 hours

---

#### Step 1.2: Create lib/seagull-demo-data.ts with createMockScore and getDemoTeamData — *Critical: Data integrity, generateAIFeedback contract*

**Why critical:** Mock SessionScore must **exactly** match the shape expected by generateAIFeedback. Wrong rule_ids or structure yields "No scoring rules" or broken feedback. **Copy ai-feedback.test.ts mockScore pattern.** Every rule_id must exist in RULE_TEMPLATES.

**Context:**
- generateAIFeedback expects SessionScore with `total` and `rules[]` where each rule has `rule_id`, `threshold`, `passed`, `actual_value`.
- RULE_TEMPLATES keys: amps_stability, angle_consistency, thermal_symmetry, heat_diss_consistency, volts_stability.
- ai-feedback.test.ts mockScore provides the pattern — use same rule_ids and structure.
- Use MOCK_EXPERT_SCORE_VALUE, MOCK_NOVICE_SCORE_VALUE, MOCK_NOVICE_FAILED_RULES from demo-config.
- getDemoTeamData must return session, expertSession, score, report for a given welderId.
- **Optional async:** For backend integration readiness, add `getDemoTeamDataAsync(welderId, delayMs?)` returning Promise.

**Full code:**

```typescript
// src/lib/seagull-demo-data.ts
/**
 * Browser-only demo data for Seagull team path.
 * Used by /demo/team and /demo/team/[welderId]. No fetchSession/fetchScore.
 * Thresholds from demo-config. Shape must match ai-feedback.test mockScore.
 */

import type { SessionScore } from '@/lib/api';
import {
  MOCK_EXPERT_SCORE_VALUE,
  MOCK_NOVICE_SCORE_VALUE,
  MOCK_NOVICE_FAILED_RULES,
  DEMO_WELDERS,
  type DemoWelder,
} from '@/lib/demo-config';
import { generateExpertSession, generateNoviceSession } from '@/lib/demo-data';
import { generateAIFeedback } from '@/lib/ai-feedback';
import type { Session } from '@/types/session';
import type { AIFeedbackResult } from '@/types/ai-feedback';

/** Must match RULE_TEMPLATES keys in ai-feedback.ts. Do not add unknown rule_ids. */
const RULE_IDS = [
  'amps_stability',
  'angle_consistency',
  'thermal_symmetry',
  'heat_diss_consistency',
  'volts_stability',
] as const;

const RULE_THRESHOLDS: Record<string, number> = {
  amps_stability: 3,
  angle_consistency: 5,
  thermal_symmetry: 10,
  heat_diss_consistency: 2,
  volts_stability: 1.5,
};

/**
 * Create SessionScore in shape expected by generateAIFeedback.
 * rule_ids must match RULE_TEMPLATES exactly.
 */
export function createMockScore(
  total: number,
  failedRuleIds: string[]
): SessionScore {
  const rules = RULE_IDS.map((rule_id) => ({
    rule_id,
    threshold: RULE_THRESHOLDS[rule_id] ?? 5,
    passed: !failedRuleIds.includes(rule_id),
    actual_value: failedRuleIds.includes(rule_id) ? 5.5 : 2.0,
  }));
  return { total, rules };
}

export const MOCK_EXPERT_SCORE = createMockScore(MOCK_EXPERT_SCORE_VALUE, []);
export const MOCK_NOVICE_SCORE = createMockScore(
  MOCK_NOVICE_SCORE_VALUE,
  [...MOCK_NOVICE_FAILED_RULES]
);

const MOCK_HISTORICAL = [68, 72, 75];

export interface DemoTeamData {
  session: Session;
  expertSession: Session;
  score: SessionScore;
  report: AIFeedbackResult;
}

const WELDER_MAP: Record<string, 'novice' | 'expert'> = Object.fromEntries(
  DEMO_WELDERS.map((w) => [w.id, w.variant])
);

/**
 * Get browser-only team data for a welder.
 * Config-driven welder list; dynamic count for QA/demos.
 */
export function getDemoTeamData(welderId: string): DemoTeamData {
  const expertSession = generateExpertSession();
  const variant = WELDER_MAP[welderId] ?? 'novice';
  const session =
    variant === 'novice' ? generateNoviceSession() : expertSession;
  const score =
    variant === 'novice' ? MOCK_NOVICE_SCORE : MOCK_EXPERT_SCORE;
  const report = generateAIFeedback(session, score, MOCK_HISTORICAL);
  return { session, expertSession, score, report };
}

/**
 * Optional: Async wrapper to mimic network delay. Use for backend integration readiness.
 * delayMs defaults to 50–150ms to reduce surprises when switching to real API.
 */
export async function getDemoTeamDataAsync(
  welderId: string,
  delayMs: number = 80
): Promise<DemoTeamData> {
  await new Promise((r) => setTimeout(r, delayMs));
  return getDemoTeamData(welderId);
}

export { DEMO_WELDERS };
export type { DemoWelder };
```

**Files:** Create `src/lib/seagull-demo-data.ts`

**Verification (specific):**
- Unit test: `createMockScore(94, [])` yields total 94, 5 rules all passed, generateAIFeedback(session, score, [72,75]) returns valid result with feedback_items.length === 5
- Unit test: `createMockScore(42, ['amps_stability'])` yields at least one failed rule; generateAIFeedback does not return "No scoring rules"
- Unit test: `getDemoTeamData('mike-chen').report.score === 42`
- Unit test: `getDemoTeamData('expert-benchmark').report.score === 94`
- Unit test: getDemoTeamData uses MOCK_NOVICE_FAILED_RULES from demo-config; failed rules match
- **Every rule_id test:** Assert createMockScore with each of amps_stability, angle_consistency, thermal_symmetry, heat_diss_consistency, volts_stability as failed produces feedback_items with that rule

**Time estimate:** 1.5–2 hours

---

#### Step 1.3: Create app/demo/team/page.tsx — Team dashboard (browser-only)

**What:** Team dashboard page at /demo/team showing welder cards from DEMO_WELDERS. No fetch.  
**Why:** Investors need zero-setup team view. Scalable to N welders. **Build this before Phase 2.**

**Files:** Create `src/app/demo/team/page.tsx`

**Code skeleton:**
```typescript
// src/app/demo/team/page.tsx
'use client';

import Link from 'next/link';
import { DEMO_WELDERS } from '@/lib/seagull-demo-data';

export default function DemoTeamDashboardPage() {
  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-black p-8">
      <div className="max-w-4xl">
        <h1 className="text-2xl font-bold text-zinc-900 dark:text-zinc-100 mb-6">
          Team Dashboard — Demo
        </h1>
        <div className="grid gap-4 sm:grid-cols-2">
          {DEMO_WELDERS.map((welder) => (
            <Link
              key={welder.id}
              href={`/demo/team/${welder.id}`}
              className="block p-6 bg-white dark:bg-zinc-900 rounded-lg shadow border border-zinc-200 dark:border-zinc-800 hover:border-blue-500 transition-colors"
            >
              <h2 className="text-lg font-semibold text-zinc-900 dark:text-zinc-100">
                {welder.name}
              </h2>
              <p className="mt-2 text-sm">
                <span className="font-bold text-blue-600 dark:text-blue-400">
                  {welder.score}/100
                </span>
              </p>
              <p className="mt-1 text-xs text-zinc-500 dark:text-zinc-400">
                View report →
              </p>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
```

**Verification:** Render page; assert N cards from DEMO_WELDERS; Mike Chen shows 42, Expert Benchmark shows 94; links point to /demo/team/[welderId]; no fetch calls.

**Time estimate:** 1 hour

---

#### Step 1.4: Create app/demo/team/[welderId]/page.tsx — Welder report (browser-only) — *Critical: Frame validation, PlaceholderHeatMap mandatory*

**Why critical:** Must replicate Seagull welder report UI without API calls. **Validate frame data:** if no frames, null frames, or empty thermal data, show PlaceholderHeatMap with neutral gradient. **No white screen. Non-negotiable.** Extract min/max temp via computeMinMaxTemp.

**Context:** useFrameData(session?.frames ?? [], null, null). extractHeatmapData(frameData.thermal_frames). **Edge cases:**
- session.frames undefined → use []
- session.frames empty [] → PlaceholderHeatMap
- thermal_frames empty → PlaceholderHeatMap
- point_count === 0 → PlaceholderHeatMap

**Full code (skeleton):**
```typescript
// src/app/demo/team/[welderId]/page.tsx
'use client';

import { use } from 'react';
import Link from 'next/link';
import { getDemoTeamData, DEMO_WELDERS } from '@/lib/seagull-demo-data';
import { useFrameData } from '@/hooks/useFrameData';
import { extractHeatmapData, tempToColorRange } from '@/utils/heatmapData';
import { computeMinMaxTemp } from '@/utils/heatmapTempRange';
import HeatMap from '@/components/welding/HeatMap';
import FeedbackPanel from '@/components/welding/FeedbackPanel';
import { LineChart } from '@/components/charts/LineChart';

const MOCK_HISTORICAL_CHART = [
  { date: 'Week 1', value: 68 },
  { date: 'Week 2', value: 72 },
  { date: 'Week 3', value: 75 },
];

/** Placeholder when no thermal data — neutral gradient, no white screen. */
function PlaceholderHeatMap({ label }: { label: string }) {
  return (
    <div className="heat-map-container bg-white dark:bg-zinc-900 rounded-lg border border-zinc-200 dark:border-zinc-800 p-6">
      <h3 className="text-lg font-semibold mb-4 text-black dark:text-zinc-50">{label}</h3>
      <div
        className="min-h-[300px] flex items-center justify-center rounded border border-dashed border-zinc-300 dark:border-zinc-700"
        style={{
          background: 'linear-gradient(135deg, #e2e8f0 0%, #94a3b8 50%, #64748b 100%)',
        }}
      >
        <p className="text-sm text-zinc-600 dark:text-zinc-400">No thermal data — demo placeholder</p>
      </div>
    </div>
  );
}

function WelderReportContent({ welderId }: { welderId: string }) {
  const data = getDemoTeamData(welderId);
  const { session, expertSession, report } = data;

  // Guard: null/undefined frames
  const sessionFrames = session?.frames ?? [];
  const expertFrames = expertSession?.frames ?? [];

  const frameData = useFrameData(sessionFrames, null, null);
  const expertFrameData = useFrameData(expertFrames, null, null);

  const heatmapData = extractHeatmapData(frameData.thermal_frames);
  const expertHeatmapData = extractHeatmapData(expertFrameData.thermal_frames);

  const hasSessionThermal = heatmapData.point_count > 0;
  const hasExpertThermal = expertHeatmapData.point_count > 0;

  const allPoints = [...heatmapData.points, ...expertHeatmapData.points];
  const { min: minT, max: maxT } = computeMinMaxTemp(allPoints);
  const colorFn = tempToColorRange(minT, maxT);

  const displayName =
    DEMO_WELDERS.find((w) => w.id === welderId)?.name ?? welderId;

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-black p-8">
      <div className="mb-4">
        <Link href="/demo/team" className="text-blue-600 dark:text-blue-400 hover:underline text-sm">
          ← Back to Team Dashboard
        </Link>
      </div>
      {/* ... header, AI summary from report ... */}
      <div className="bg-white dark:bg-zinc-900 rounded-lg shadow p-6 mb-8">
        <h2 className="text-xl font-bold mb-4">Thermal Comparison</h2>
        <div className="grid grid-cols-2 gap-8">
          <div>
            <h3 className="text-sm font-semibold text-zinc-600 dark:text-zinc-400 mb-2">Expert Benchmark</h3>
            {hasExpertThermal ? (
              <HeatMap sessionId="expert" data={expertHeatmapData} colorFn={colorFn} label="Expert" />
            ) : (
              <PlaceholderHeatMap label="Expert" />
            )}
          </div>
          <div>
            <h3 className="text-sm font-semibold text-zinc-600 dark:text-zinc-400 mb-2">Your Weld</h3>
            {hasSessionThermal ? (
              <HeatMap sessionId={session.session_id} data={heatmapData} colorFn={colorFn} label={displayName} />
            ) : (
              <PlaceholderHeatMap label={displayName} />
            )}
          </div>
        </div>
      </div>
      {/* FeedbackPanel, LineChart ... */}
    </div>
  );
}

export default function DemoTeamWelderPage({ params }: { params: Promise<{ welderId: string }> }) {
  const { welderId } = use(params);
  if (!DEMO_WELDERS.some((w) => w.id === welderId)) {
    return (
      <div className="min-h-screen bg-zinc-50 dark:bg-black p-8">
        <p>Welder not found</p>
        <Link href="/demo/team">← Back to Team Dashboard</Link>
      </div>
    );
  }
  return <WelderReportContent welderId={welderId} />;
}
```

**Note:** Next.js 15 async params: use `use(params)`. Lock Next.js 15 in package.json; if downgrade possible, isolate `use(params)` in a wrapper component.

**Verification:**
- Render with welderId="mike-chen"; assert score 42, AI summary, Thermal Comparison; HeatMap or PlaceholderHeatMap visible
- **Integration test with mock empty frames:** Override getDemoTeamData or pass session with frames: [] → PlaceholderHeatMap (neutral gradient) must render; no white screen
- **Integration test:** welderId="expert-benchmark" → score 94

**Time estimate:** 2–2.5 hours

---

#### Step 1.5: Add unit and integration tests — *Critical: Phase 2 gate*

**Files:** `src/__tests__/lib/seagull-demo-data.test.ts`, `src/__tests__/lib/demo-config.test.ts`, `src/__tests__/utils/heatmapTempRange.test.ts`, `src/__tests__/app/demo/team/page.test.tsx`, `src/__tests__/app/demo/team/[welderId]/page.test.tsx`

**Test cases:**

**demo-config.test.ts:**
- NOVICE_SPIKE_MS === 2400
- MOCK_EXPERT_SCORE_VALUE === 94
- MOCK_NOVICE_SCORE_VALUE === 42
- DEMO_WELDERS.length >= 2
- DEMO_WELDERS[0].id === 'mike-chen', score === 42
- DEMO_WELDERS[1].id === 'expert-benchmark', score === 94

**heatmapTempRange.test.ts:**
- computeMinMaxTemp([]) returns fallback { min: 0, max: 600 }
- computeMinMaxTemp(null) returns fallback
- computeMinMaxTemp([{ temp_celsius: 100 }, { temp_celsius: 400 }]) returns { min: 100, max: 400 }
- computeMinMaxTemp with invalid temps (NaN, undefined) returns fallback or filters correctly

**seagull-demo-data.test.ts:**
- createMockScore(94, []) yields total 94, 5 rules all passed
- createMockScore(42, ['amps_stability']) yields at least one failed rule
- generateAIFeedback(session, createMockScore(94, []), [72, 75]) returns valid AIFeedbackResult; feedback_items.length === 5
- generateAIFeedback(session, createMockScore(42, MOCK_NOVICE_FAILED_RULES), [72, 75]) returns summary containing failed rule names
- getDemoTeamData('mike-chen') returns report.score === 42
- getDemoTeamData('expert-benchmark') returns report.score === 94
- **Every rule_id:** createMockScore with each RULE_TEMPLATES key as failed produces valid generateAIFeedback output

**demo/team/page.test.tsx:**
- Renders N cards from DEMO_WELDERS
- Links point to /demo/team/[welderId]
- No fetch mocks required (browser-only)

**demo/team/[welderId]/page.test.tsx:**
- mike-chen renders with score 42
- expert-benchmark renders with score 94
- **PlaceholderHeatMap:** Mock session with frames: [] → PlaceholderHeatMap (or equivalent neutral gradient UI) visible; no white screen

**Phase 2 cannot proceed until all above tests pass.**

**Time estimate:** 1.5–2 hours

---

**Phase 1 Total Time:** ~8–10 hours

---

## Phase 2 — Guided Tour

**Goal:** User sees 2–4 step narrative overlay on /demo.  
**Time Estimate:** ~6–8 hours  
**Risk Level:** 🟡 Medium (z-index, scrub callback, a11y)

**Strategy:** Time-box steps first, then polish. Don't commit extended window for complex overlay until prototype works. **Start Phase 2 only after Phase 1 tests pass.** Test on Safari, Firefox, Chrome, iPad, iPhone landscape early in Phase 2.

---

#### Step 2.1: Create lib/demo-tour-config.ts

**What:** Tour step definitions. 2–4 steps. Pull NOVICE_SPIKE_MS from demo-config.

**Files:** Create `src/lib/demo-tour-config.ts`

```typescript
// src/lib/demo-tour-config.ts
import { NOVICE_SPIKE_MS } from '@/lib/demo-config';

export interface TourStep {
  id: string;
  title: string;
  body: string;
  highlightSelector?: string;
  timestamp_ms?: number;
  nextLabel: string;
  isLast?: boolean;
}

export const DEMO_TOUR_STEPS: TourStep[] = [
  { id: 'intro', title: 'Expert vs Novice', body: '...', nextLabel: 'Next' },
  { id: 'expert', title: 'Expert Technique', body: '...', nextLabel: 'Next' },
  {
    id: 'novice_spike',
    title: 'Novice Moment',
    body: '...',
    timestamp_ms: NOVICE_SPIKE_MS,
    nextLabel: 'Next',
  },
  {
    id: 'score',
    title: 'What the Scores Mean',
    body: '...',
    nextLabel: 'See Team Management',
    isLast: true,
  },
];
```

**Verification:** Import DEMO_TOUR_STEPS; assert length 4; step with id 'novice_spike' has timestamp_ms === NOVICE_SPIKE_MS (2400).

**Time estimate:** 0.5 hours

---

#### Step 2.2: Create components/demo/DemoTour.tsx — *Critical: Focus trap, a11y, highlight fallback, step logging*

**Why critical:** Overlay must appear above 3D Canvas. Must trap focus, support Tab/Escape, have aria-modal, role="dialog", aria-labels. **Highlight fallback:** if highlightSelector fails, use default element or center overlay; animate transitions. **Step logging:** console.log or debug callback per step for investor demo debugging. **Visual checklist:** Create per-step checklist (title visible, body visible, buttons accessible) for consistency.

**Files:** Create `src/components/demo/DemoTour.tsx`

**Implementation requirements:**
1. **Focus trap:** Use `useEffect` + `ref` to trap focus inside overlay; Tab cycles Skip → Next (or vice versa).
2. **aria-modal="true"**, role="dialog", aria-labelledby, aria-describedby
3. **aria-label** on Skip and Next: `aria-label="Skip tour"`, `aria-label={step.nextLabel}` (or "Next step")
4. **Escape** key: document-level listener
5. **Highlight fallback:** If `step.highlightSelector` and `document.querySelector(step.highlightSelector)` is null, do not highlight; show overlay centered. Optionally scroll overlay into view. **Animate:** Add `transition-all duration-200` to overlay position/size to avoid abrupt jumps.
6. **Step logging:** On step change, `if (typeof window !== 'undefined' && process.env.NODE_ENV === 'development') { console.log('[DemoTour] step:', step.id, step.title); }` or accept optional `onStepLog?(step)` prop.
7. **Visual checklist (document in plan):** For each step, verify: overlay visible, title in DOM, body in DOM, Skip and Next in DOM, both focusable, Escape dismisses.
8. **z-index:** 200; if Safari fails, document contingency: increase to z-[300].

**Full code (key additions):**
```typescript
// src/components/demo/DemoTour.tsx
'use client';

import { useState, useCallback, useEffect, useRef } from 'react';
import type { TourStep } from '@/lib/demo-tour-config';

interface DemoTourProps {
  steps: TourStep[];
  onStepEnter?: (step: TourStep) => void;
  onComplete?: () => void;
  onSkip?: () => void;
  onStepLog?: (step: TourStep, index: number) => void;
}

const FOCUSABLE_SELECTOR = 'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])';

export function DemoTour({ steps, onStepEnter, onComplete, onSkip, onStepLog }: DemoTourProps) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isDismissed, setIsDismissed] = useState(false);
  const overlayRef = useRef<HTMLDivElement>(null);

  const step = steps[currentIndex];

  // Focus trap: keep focus inside overlay
  useEffect(() => {
    if (!overlayRef.current || !step) return;
    const el = overlayRef.current;
    const focusables = el.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR);
    if (focusables.length > 0 && !el.contains(document.activeElement)) {
      focusables[0].focus();
    }
  }, [currentIndex, step]);

  useEffect(() => {
    if (step) {
      onStepEnter?.(step);
      onStepLog?.(step, currentIndex);
    }
  }, [step, onStepEnter, onStepLog, currentIndex]);

  const handleNext = useCallback(() => {
    const s = steps[currentIndex];
    if (s?.isLast) {
      onComplete?.();
      setIsDismissed(true);
      return;
    }
    setCurrentIndex((i) => Math.min(i + 1, steps.length - 1));
  }, [currentIndex, steps, onComplete]);

  const handleSkip = useCallback(() => {
    onSkip?.();
    setIsDismissed(true);
  }, [onSkip]);

  useEffect(() => {
    const h = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        handleSkip();
      }
    };
    document.addEventListener('keydown', h);
    return () => document.removeEventListener('keydown', h);
  }, [handleSkip]);

  if (isDismissed || steps.length === 0) return null;
  if (!step) return null;

  return (
    <div
      ref={overlayRef}
      className="fixed inset-0 z-[200] isolate flex items-center justify-center p-4 transition-all duration-200"
      role="dialog"
      aria-modal="true"
      aria-labelledby="tour-title"
      aria-describedby="tour-body"
    >
      <div
        className="absolute inset-0 bg-black/60"
        onClick={handleSkip}
        role="button"
        tabIndex={0}
        aria-label="Click to skip tour"
        onKeyDown={(e) => e.key === 'Enter' && handleSkip()}
      />
      <div className="relative z-10 bg-neutral-900 border-2 border-blue-400 rounded-lg p-6 max-w-md w-full shadow-xl min-w-[280px] max-w-[calc(100vw-2rem)]">
        <h2 id="tour-title" className="text-xl font-bold text-blue-400 mb-2">
          {step.title}
        </h2>
        <p id="tour-body" className="text-gray-300 mb-6">
          {step.body}
        </p>
        <div className="flex justify-between gap-4">
          <button
            type="button"
            onClick={handleSkip}
            className="px-4 py-2 text-gray-400 hover:text-white transition"
            aria-label="Skip tour"
          >
            Skip tour
          </button>
          <button
            type="button"
            onClick={handleNext}
            className="px-6 py-2 bg-blue-400 text-black font-bold rounded hover:bg-blue-300 transition"
            aria-label={step.nextLabel}
          >
            {step.nextLabel}
          </button>
        </div>
        <p className="text-xs text-gray-500 mt-4">
          Step {currentIndex + 1} of {steps.length}
        </p>
      </div>
    </div>
  );
}
```

**Verification:** Render DemoTour; assert focus trap (Tab stays inside); Escape skips; aria attributes present; at 375px overlay visible, no overflow. **Manual checklist:** For each step: title, body, Skip, Next visible and focusable. **Safari:** Overlay visible, not hidden behind 3D.

**Time estimate:** 2–2.5 hours

---

#### Step 2.3: Integrate DemoTour into app/demo/page.tsx — *Critical: Debounced scrub, empty/malformed frames*

**What:** Add DemoTour to DemoPageContent. **Debounce onStepEnter** scrub callbacks (150ms) to prevent UI lag when stepping rapidly. **Handle empty/malformed frames:** if getFrameAtTimestamp returns null or frames are empty, do not crash; demo page already uses useMemo for heatmap; ensure TorchWithHeatmap3D and HeatMap receive safe fallbacks.

**Files:** Modify `src/app/demo/page.tsx`

**Subtasks:**
- [ ] Import DemoTour, DEMO_TOUR_STEPS
- [ ] Add `const [showTour, setShowTour] = useState(true)`
- [ ] Render DemoTour only when `showTour && sessions`
- [ ] **Debounced onStepEnter (150ms):**
  ```typescript
  const scrubTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const onStepEnter = useCallback((step: TourStep) => {
    if (scrubTimeoutRef.current) clearTimeout(scrubTimeoutRef.current);
    if (step.timestamp_ms != null) {
      scrubTimeoutRef.current = setTimeout(() => {
        setCurrentTimestamp(step.timestamp_ms!);
        setPlaying(false);
        scrubTimeoutRef.current = null;
      }, 150);
    }
  }, []);
  useEffect(() => () => { scrubTimeoutRef.current && clearTimeout(scrubTimeoutRef.current); }, []);
  ```
- [ ] onComplete/onSkip: setShowTour(false)
- [ ] **Empty/malformed frames:** Demo page uses sessions from generateExpertSession/generateNoviceSession; these produce frames. If a step would scrub to a timestamp with no frame, getFrameAtTimestamp returns nearest; TorchWithHeatmap3D handles null thermal data. Document: "If frame data is delayed or missing, tour still progresses; 3D may show previous frame."
- [ ] Pass onStepLog (optional) for debug: `onStepLog={(s, i) => console.log('[DemoTour]', i, s.id)}`

**Verification:** Render DemoPage; onStepEnter with timestamp_ms 2400 triggers debounced scrub; rapid step changes don't cause lag. Mock missing frame: assert no crash. Scrub moves playback to 2400ms at novice_spike step.

**Time estimate:** 1.5 hours

---

#### Step 2.4: Multi-device and cross-browser testing — *Mandatory before Phase 2 done*

**What:** Test tour on Safari, Firefox, Chrome; 375px viewport; iPad, iPhone landscape. Document edge cases: overlapping modals, scroll, animation delays. **Do not wait until Phase 3.**

**Subtasks:**
- [ ] Manual: Safari — overlay visible, z-index correct, no scroll-off, Tab/Escape work
- [ ] Manual: Firefox — overlay visible, Tab/Escape work
- [ ] Manual: Chrome — overlay visible, Tab/Escape work
- [ ] Manual: 375px — overlay no overflow, buttons accessible
- [ ] Manual: iPad/iPhone landscape — touch gestures, Tap to advance
- [ ] Document: If modal overlaps (e.g. browser autofill), ensure tour z-index wins or document known limitation
- [ ] Document: Scroll during tour — overlay fixed; document if body scroll causes issues
- [ ] Contingency: If Safari z-index fails, try z-[300]

**Verification:** All browsers pass; 375px usable; no console errors. Document results.

**Time estimate:** 1–1.5 hours

---

**Phase 2 Total Time:** ~6–8 hours

---

## Phase 3 — CTA, AppNav, Polish

**Goal:** Full investor flow.  
**Time Estimate:** ~3–4 hours

---

#### Step 3.1: Add "See Team Management" CTA to demo page

**What:** Button/link after tour completion or in header. **Dismiss overlay before navigate:** CTA click should not interrupt tour mid-step; either CTA is shown after tour completion, or clicking CTA programmatically dismisses tour first then navigates.

**Files:** Modify `src/app/demo/page.tsx`

**CTA placement:** In header div after title. Use Next.js Link with `href="/demo/team"`. CTA always visible; clicking it dismisses tour (if shown) then navigates.

**Implementation:**
```tsx
const router = useRouter();
const handleCtaClick = () => {
  setShowTour(false);
  router.push('/demo/team');
};
// Or use Link with onClick that clears tour state before navigation
<Link href="/demo/team" onClick={() => setShowTour(false)} className="...">
  See Team Management →
</Link>
```

**Verification:** CTA visible; click navigates to /demo/team; if tour was open, it dismisses first; no redirect mid-tour.

**Time estimate:** 0.5 hours

---

#### Step 3.2: Add Team link to AppNav

**What:** Add "Team" link to AppNav, href /seagull.

**Files:** Modify `src/components/AppNav.tsx`

**Insertion:** After Demo link. aria-current when pathname starts with /seagull.

**Verification:** Team link present, href="/seagull", no 404.

**Time estimate:** 0.5 hours

---

#### Step 3.3: Tour responsive and keyboard/touch

**What:** Overlay responsive at 375px. Tab/Enter/Escape. **Responsive constraints:** max-width, min-width, z-index per breakpoint. Test keyboard and touch on mobile.

**Files:** Modify `src/components/demo/DemoTour.tsx`

**Subtasks:**
- [ ] Overlay: `min-w-[280px] max-w-[calc(100vw-2rem)]`, padding p-4
- [ ] Buttons focusable; tab order correct
- [ ] Escape skips (document-level)
- [ ] At 375px: overlay visible, no horizontal overflow, buttons accessible
- [ ] Z-index: 200; test with multiple modals (e.g. browser dialog)
- [ ] Touch: Tap Skip/Next works; no double-tap required

**Verification:** Render at 375px; assert overlay and controls visible. Keyboard and touch assertions in test.

**Time estimate:** 1 hour

---

#### Step 3.4: Contingency demo path and optional feature flags

**What:** Document contingency path: if tour or CTA breaks, investor can still run a coherent narrative (go directly to /demo/team, show team cards, click welder, show report). Optional: feature flags for tour overlay and CTA.

**Files:** Add to README or docs/ if they exist; otherwise plan-level note.

**Contingency path:**
1. Skip tour: go to /demo, dismiss immediately, show CTA
2. Direct URL: /demo/team → team dashboard → welder report
3. If HeatMap fails: PlaceholderHeatMap with neutral gradient shown
4. If 3D fails: 2D HeatMap fallback (per demo page)

**Optional feature flags (if time):**
- `NEXT_PUBLIC_DEMO_TOUR_ENABLED=true|false`
- `NEXT_PUBLIC_DEMO_CTA_ENABLED=true|false`
- Wrap DemoTour and CTA in conditionals

**Time estimate:** 0.5 hours

---

#### Step 3.5: (Optional) Update documentation

**What:** If investor-facing docs exist, add "Investor Demo" section: /demo, tour, CTA, /demo/team, browser-only. Document fallback behavior for overlay, chart, and components.

**Time estimate:** 0.5 hours (optional)

---

**Phase 3 Total Time:** ~3–4 hours

---

## 3. Pre-Flight Checklist

**Path convention:** All file paths use `src/` prefix. Run `npm install`, `npm test`, `npm run dev` from `my-app/`.

**Next.js:** Lock Next.js 15. If downgrade planned, isolate `use(params)` in wrapper component.

### Phase 1 Prerequisites

| Requirement | How to Verify | If Missing |
|-------------|---------------|------------|
| Node 18+ | `node --version` | Install from nodejs.org |
| npm | `npm --version` | Comes with Node |
| Dependencies | `npm install` in my-app | Run npm install |
| Dev server | `npm run dev` in my-app | Start server |
| Next.js 15 | package.json | Lock version |

### Phase 2 Prerequisites (HARD GATE)

| Requirement | How to Verify | If Missing |
|-------------|---------------|------------|
| Phase 1 complete | All Phase 1 tests pass | Complete Phase 1 |
| /demo/team loads | Navigate to /demo/team | Fix Phase 1 |
| /demo/team/mike-chen renders | No white screen | Fix Step 1.4 |
| demo-data.ts | generateExpertSession exists | Already exists |

### Phase 3 Prerequisites

| Requirement | How to Verify | If Missing |
|-------------|---------------|------------|
| Phase 1 and 2 complete | Tour + team work | Complete prior phases |

---

## 4. Testing & Verification Improvements

**Strategy:** Unit + integration + E2E. Mock async failure. Visual regression (screenshots) if tooling available. **Tests are not optional; add them now, not later.**

### Unit & Integration (Jest + React Testing Library)

- **demo-config:** Constants, DEMO_WELDERS, validation assertions
- **heatmapTempRange:** computeMinMaxTemp fallback, empty, invalid temps
- **seagull-demo-data:** createMockScore, getDemoTeamData shapes, generateAIFeedback contract, every rule_id
- **DemoTour:** Overlay renders, Next/Skip, focus trap, Escape
- **Demo page:** DemoTour integration, debounced scrub, CTA
- **Team pages:** Cards, welder report, PlaceholderHeatMap when empty frames

### E2E (Playwright or Cypress)

- **Tour overlay + scrub + CTA flow:** Visit /demo → see tour → Next through steps → scrub to 2.4s → Skip or complete → CTA visible → click → /demo/team
- **Team path:** Visit /demo/team → cards → click welder → report

### Mock Async Failure

- **Test overlay when frame data delayed/missing:** Mock getDemoTeamData or sessions to resolve after delay; assert tour still renders, no white screen. Mock empty frames; assert PlaceholderHeatMap.

### Visual Regression (Optional)

- Screenshots of key demo steps; compare to baseline if Playwright/Cypress screenshots configured.

**Test file locations:** `src/__tests__/lib/`, `src/__tests__/utils/`, `src/__tests__/app/demo/`, `src/__tests__/components/demo/`, `e2e/` (if added).

---

## 5. Risk Heatmap

| Phase | Step | Risk | P | I | Detection | Mitigation |
|-------|------|------|---|---|-----------|------------|
| 1 | 1.1 | Config drift | 10% | M | Values duplicated | Single demo-config |
| 1 | 1.2 | Mock score shape wrong | 20% | M | generateAIFeedback throws | Copy ai-feedback.test exactly |
| 1 | 1.4 | Blank HeatMap / no placeholder | 15% | H | White screen | PlaceholderHeatMap mandatory |
| 2 | 2.2 | Tour hidden behind 3D | 25% | M | Overlay not visible in Safari | z-[200], isolate; contingency z-[300] |
| 2 | 2.2 | Focus trap fails | 20% | M | Tab escapes | Focus trap useEffect |
| 2 | 2.3 | Scrub lag / no debounce | 15% | L | UI jank | 150ms debounce |
| 2 | 2.3 | Empty frames crash | 10% | M | White screen | Graceful fallback |
| 3 | 3.1 | Nav interrupts tour | 25% | M | Redirect mid-tour | Dismiss before navigate |
| 3 | 3.3 | Mobile cramped | 40% | M | Overflow | min/max width, 375px test |
| All | - | Phase 2 started early | 30% | H | Tour broken, team broken | Hard gate: Phase 1 tests pass |

---

## 6. Success Criteria

| # | Requirement | Target | Verification | Priority |
|---|-------------|--------|--------------|----------|
| 1 | Guided tour on /demo | 2–4 steps, Next/Skip | DemoTour.test.tsx | P0 |
| 2 | Preset scenario | Scrub to 2.4s (debounced) | onStepEnter mock | P0 |
| 3 | Focus trap, a11y | Tab, Escape, aria | DemoTour a11y tests | P0 |
| 4 | Highlight fallback | No crash when selector fails | Document | P1 |
| 5 | CTA to team | Visible, dismiss before navigate | demo page test | P0 |
| 6 | Team dashboard | N cards from config | demo/team/page test | P0 |
| 7 | Welder report | HeatMap or PlaceholderHeatMap | welder page test | P0 |
| 8 | PlaceholderHeatMap | Neutral gradient when no frames; no white screen | welder page test | P0 |
| 9 | Config-driven | No magic numbers; validate all values | demo-config tests | P0 |
| 10 | Responsive tour | 375px usable | viewport test | P1 |
| 11 | Contingency path | Documented | README/docs | P2 |
| 12 | Data integrity | createMockScore shape = generateAIFeedback expects | seagull-demo-data tests | P0 |
| 13 | Cross-browser | Safari, Chrome, Firefox verified | Manual/checklist | P1 |

**Definition of Done:** All P0 pass. P1 pass or deferred. All verification via automated tests. Phase 2 starts only after Phase 1 tests pass.

---

## 7. Rollback

To undo: revert `src/lib/demo-config.ts`, `src/utils/heatmapTempRange.ts`, `src/lib/seagull-demo-data.ts`, `src/app/demo/team/*`, `src/lib/demo-tour-config.ts`, `src/components/demo/DemoTour.tsx`; revert changes to `src/app/demo/page.tsx`, `src/components/AppNav.tsx`. Remove added test files. Run `cd my-app && npm test`.

---

## 8. Known Issues & Limitations

- **Driver.js/Shepherd.js:** Custom tour chosen for control. If prototype proves brittle, consider battle-tested library; custom is higher risk for complex overlays.
- **Next.js 15:** Async params require `use()`. If downgrading, isolate in wrapper.
- **Mock data integrity:** Mock must match expected visuals (scores, spike at 2.4s). Validate manually before investor demo.
- **WebGL context limit:** Demo uses 2 instances; no new 3D. See LEARNING_LOG, WEBGL_CONTEXT_LOSS.md.
- **Safari z-index:** If overlay hidden behind 3D, try z-[300]. Document if persists.

---

**Plan complete. Ready for implementation.**
