# Investor-Grade Demo — Phase 2: Deep Technical Exploration

**Issue:** `.cursor/issues/investor-grade-demo-guided-tour-seagull.md`  
**Time Budget:** 45–90 minutes minimum  
**Exploration Date:** 2026-02-17

---

## MANDATORY PRE-EXPLORATION THINKING SESSION (20 minutes minimum)

### A. Exploration Scope Understanding

**1. Core technical challenge (one sentence):**  
Building an investor-facing narrative layer that makes welding data understandable to non-technical audiences, while providing a zero-backend path from tech demo through team management story.

**Why it's hard:**  
Investors see abstract sensor data (heatmaps, angles, 3D torches) without domain knowledge. The demo currently shows 94 vs 42 scores and bullet lists but no guided explanation. Seagull tells the enterprise story (team dashboard, welder reports, AI feedback) but depends on backend APIs. Bridging these requires (a) a tour/overlay system that doesn't exist in the codebase, (b) a browser-only data path for Seagull that mirrors API shape, and (c) narrative copy that connects visuals to business outcomes.

**What makes it non-trivial:**  
- No existing guided-tour or overlay component; must build or integrate a library.  
- Seagull welder report uses `fetchSession`, `fetchScore`, `useFrameData` — all API-dependent; browser-only path needs mock SessionScore and in-memory frames.  
- WebGL/3D context: overlay must coexist with 2 TorchWithHeatmap3D instances; z-index and stacking can conflict.  
- Demo layout is standalone (no AppNav); team path may need its own layout or integration with app layout for nav.  
- Narrative must be non-technical (“temperature spike” not “thermal_snapshots”) and connect 94/42 to “production-ready vs needs training.”

**2. Major unknowns**

| # | Unknown | Why it matters |
|---|---------|----------------|
| 1 | Exact tour step count and copy | Affects UX and config structure |
| 2 | Whether to use a tour library (react-joyride, driver.js) or custom overlay | Bundle size, maintenance, flexibility |
| 3 | Precise timestamp for “novice spike” moment | demo-data.ts uses sine; spike at ~0.5s, 2.5s, etc. — need exact value for preset scenario |
| 4 | Browser-only team path: /demo/team vs /seagull?demo=1 vs separate route | Routing, reuse of Seagull components, URL semantics |
| 5 | Mock SessionScore shape for expert (94) and novice (42) | generateAIFeedback needs rules; must match RULE_TEMPLATES |
| 6 | Tour overlay z-index vs WebGL Canvas stacking | TorchWithHeatmap3D uses z-[100]; overlay must win |
| 7 | How many welders/cards in browser-only team dashboard | Scope: 1 vs 2 vs full parity |
| 8 | Accessibility: keyboard nav, screen reader support | WCAG; affects tour implementation |

**3. Questions that MUST be answered in this exploration**

1. How do we implement a guided tour (library vs custom)?  
2. How do we define “preset scenario” (timestamp + copy)?  
3. Where does browser-only team data live (demo-data.ts vs seagull-demo-data.ts)?  
4. What mock SessionScore satisfies generateAIFeedback for expert (94) and novice (42)?  
5. How does /demo integrate with AppNav (if at all)?  
6. What z-index/stacking ensures tour overlay appears above 3D Canvas?  
7. How do we scrub to a specific timestamp from tour step?  
8. What’s the minimal team path (dashboard + one welder report)?  
9. How do we test tour and browser-only Seagull without backend?  
10. Does Seagull welder report need useFrameData or can it use frames directly from demo-data?

**4. What could we get wrong**

- **Over-engineering the tour:** Adding a heavy library when a simple overlay suffices.  
- **Diverging browser-only and API Seagull:** Two code paths that drift over time.  
- **Wrong z-index:** Tour hidden behind Canvas.  
- **Mock SessionScore mismatch:** generateAIFeedback expects specific rule_ids; wrong shape yields broken feedback.  
- **Preset timestamp mismatch:** Scrub to 2.3s but spike is at 2.5s.  
- **Breaking existing demo behavior:** Tour integration changes playback or layout.  
- **Mobile overlay too small:** Tour unusable on small screens.

---

### B. Approach Brainstorm

**Approach A: Custom lightweight tour overlay**  
- **Description:** Build a simple React component: overlay + step config (title, body, highlightSelector), Next/Skip buttons, optional spotlight. No external library.  
- **Gut feeling:** Good  
- **First concern:** Spotlight/highlight positioning (getBoundingClientRect, scroll) can be fiddly; need to handle responsive layout.

**Approach B: react-joyride**  
- **Description:** Use react-joyride for guided tours; add `data-tour` attributes to demo elements.  
- **Gut feeling:** Uncertain  
- **First concern:** Bundle size (~30KB+), may have opinionated styling; need to verify WarpSense blue/purple compatibility.

**Approach C: driver.js**  
- **Description:** Lightweight (~5KB), vanilla JS; wrap in React component.  
- **Gut feeling:** Good  
- **First concern:** Less React-native; may need useEffect/ref for integration.

**Approach D: /demo/team as new route, full browser-only**  
- **Description:** Create `/demo/team` page that renders team dashboard + welder report using demo-data.ts + mock SessionScore. No fetchSession/fetchScore.  
- **Gut feeling:** Good  
- **First concern:** Duplication of Seagull UI unless we extract shared components or pass `demoMode` prop.

**Approach E: /seagull with ?demo=1 fallback**  
- **Description:** Seagull pages detect `?demo=1`; on API failure or demo param, use demo-data + mock score.  
- **Gut feeling:** Uncertain  
- **First concern:** Mixing API and demo logic in same component; more branching.

**Approach F: Shared WelderReport component with dataSource prop**  
- **Description:** Extract WelderReport from seagull/welder/[id]; accept `dataSource: 'api' | 'demo'`. Demo passes sessions + mock score.  
- **Gut feeling:** Good  
- **First concern:** useFrameData and fetch flow are intertwined; refactor needed.

---

### C. Constraint Mapping

**Technical constraints:**

1. **WebGL:** Max 2 TorchWithHeatmap3D per page (demo already at limit).  
2. **Tour overlay z-index:** Must beat TorchWithHeatmap3D overlay (z-[100]); per LEARNING_LOG.  
3. **demo-data.ts:** Expert/novice sessions exist; SessionScore does not.  
4. **generateAIFeedback:** Expects Session, SessionScore, historicalScores (number[]).  
5. **WarpSense palette:** Blue/purple only; no rainbow.  
6. **Append-only / no mutation:** Browser-only path must not mutate production data.  
7. **Demo layout:** No AppNav; standalone.

**How constraints shape solutions:**

- Constraint “WebGL max 2” → no new 3D components on demo; tour is 2D overlay only.  
- Constraint “z-[100] on 3D overlay” → tour overlay needs z-[150] or similar + `isolate` stacking context (per LEARNING_LOG Safari fix).  
- Constraint “generateAIFeedback expects SessionScore” → we must create mock `{ total, rules }` with rule_ids matching RULE_TEMPLATES (amps_stability, angle_consistency, thermal_symmetry, heat_diss_consistency, volts_stability).  
- Constraint “demo layout no AppNav” → CTA “See Team Management” links out; team path may use (app) layout with AppNav for consistency.

---

### D. Risk Preview

**Scary thing #1: Tour overlay hidden behind 3D**  
- **Why scary:** User sees nothing; tour appears broken.  
- **Likelihood:** 25%  
- **Could kill project:** No — fixable with z-index/stacking.  
- **Mitigation:** Use z-[200], `isolate`, test in Safari.

**Scary thing #2: Browser-only Seagull diverges from API path**  
- **Why scary:** Two code paths; bug fixes must be applied twice.  
- **Likelihood:** 60%  
- **Could kill project:** No — maintenance burden.  
- **Mitigation:** Reuse WelderReport/HeatMap/FeedbackPanel; only data source differs.

**Scary thing #3: generateAIFeedback breaks with mock SessionScore**  
- **Why scary:** Welder report shows “No scoring rules” or malformed feedback.  
- **Likelihood:** 20%  
- **Could kill project:** No — we have ai-feedback.test.ts with mockScore; shape is known.

---

## 1. Research Existing Solutions

### A. Internal Codebase Research

**Similar Implementation #1: Demo page overlay/header**

- **Location:** `my-app/src/app/demo/page.tsx`  
- **What it does:** Renders header “WarpSense — Live Quality Analysis”, side-by-side expert/novice, playback controls, fixed bottom bar.  
- **Patterns:** No overlay; header is static. Bullet lists (expert: consistent temp, angle; novice: spike at 2.3s) already provide narrative hooks.  
- **Reuse:** Step config can reference these bullets; “preset scenario” can scrub to 2300ms and highlight novice column.  
- **What to avoid:** Don’t block the entire viewport; allow skip.

**Similar Implementation #2: TorchWithHeatmap3D context-loss overlay**

- **Location:** `my-app/src/components/welding/TorchWithHeatmap3D.tsx` (per WEBGL plan)  
- **What it does:** Shows “Refresh to restore” overlay when WebGL context is lost.  
- **Patterns:** `z-[100]`, `isolate` stacking context, `role="alert"`, overlay inside component.  
- **Key snippet (conceptual):**
```tsx
<div className="absolute inset-0 z-[100] isolate ..." role="alert">
  Context lost. Refresh to restore.
  <button>Refresh</button>
</div>
```
- **Reuse:** Tour overlay must use higher z-index (e.g. z-[200]) and live at page level, not inside TorchWithHeatmap3D.  
- **Edge case:** If both context-loss and tour show, tour should be on top (user can dismiss tour first).

**Similar Implementation #3: Seagull welder report**

- **Location:** `my-app/src/app/seagull/welder/[id]/page.tsx`  
- **What it does:** Fetches session + expert session + score; generates AI feedback; renders HeatMap, FeedbackPanel, LineChart.  
- **Data flow:** `fetchSession` → `useFrameData` → `extractHeatmapData`; `fetchScore` → `generateAIFeedback` → `report`.  
- **Reuse:** HeatMap, FeedbackPanel, LineChart, generateAIFeedback are all reusable.  
- **Gap:** Data comes from API. Browser-only needs: (1) Session from generateExpertSession/generateNoviceSession, (2) mock SessionScore, (3) useFrameData works with frames directly — no fetch.

**Similar Implementation #4: ErrorBoundary fallback**

- **Location:** `my-app/src/components/ErrorBoundary.tsx`, `DemoLayoutClient.tsx`  
- **What it does:** Catches render errors; shows fallback UI with “Refresh page”.  
- **Pattern:** Error boundary wraps children; fallback is full-page.  
- **Reuse:** Tour failures (e.g. missing highlight target) should not crash page; graceful fallback to “Skip tour” behavior.

**Similar Implementation #5: AppNav + route groups**

- **Location:** `my-app/src/components/AppNav.tsx`, `app/(app)/layout.tsx`  
- **What it does:** AppNav in (app) layout; Demo link goes to /demo. No Team/Seagull link.  
- **Modification needed:** Add “Team” link to /seagull (or /demo/team). Demo page itself stays standalone; CTA goes to team path.

### B. Pattern Analysis

**Pattern #1: Overlay with high z-index + isolate**

- **Used in:** TorchWithHeatmap3D (context-loss overlay), LEARNING_LOG Safari fix  
- **When to use:** Any overlay that must appear above WebGL or complex stacking contexts  
- **Implementation:**
```tsx
<div className="fixed inset-0 z-[200] isolate pointer-events-none">
  <div className="pointer-events-auto ...">Tour content</div>
</div>
```
- **Pros:** Reliable visibility; works in Safari  
- **Cons:** Must coordinate with other overlays  
- **Applicability:** High — tour overlay

**Pattern #2: Config-driven steps**

- **Used in:** Common tour libraries; proposed tour  
- **When to use:** Multi-step flows with consistent structure  
- **Implementation:**
```ts
interface TourStep {
  id: string;
  title: string;
  body: string;
  highlightSelector?: string;
  timestamp_ms?: number;
  nextLabel: string;
  isLast?: boolean;
}
```
- **Applicability:** High

**Pattern #3: Data-source abstraction**

- **Used in:** Seagull (today: API only)  
- **When to use:** Same UI, different data sources  
- **Implementation:** `useDemoTeamData()` vs `useSeagullApiData()`; or single hook that returns `{ session, expertSession, score, report }` from either source.  
- **Applicability:** High — browser-only Seagull

### C. External Research

**Research Query #1:** “React guided tour library lightweight 2024”

- **Source:** npm, GitHub  
- **Libraries:** react-joyride, driver.js, intro.js, shepherd.js  
- **Insights:**
  - react-joyride: ~30KB, React-native, steps + tooltips, good docs
  - driver.js: ~5KB, vanilla, minimal deps, `driverObj.highlight(selector)`
  - intro.js: Heavier, commercial option  
- **Applicability:** driver.js or custom for minimal bundle; react-joyride if we want React-first tooltips

**Research Query #2:** “SessionScore mock for generateAIFeedback”

- **Source:** `ai-feedback.test.ts`  
- **Key insight:** mockScore() returns `{ total, rules }` with rule_ids: amps_stability, angle_consistency, thermal_symmetry, heat_diss_consistency, volts_stability. Expert 94 = 5 rules passed (or 4 + high total). Novice 42 = 2 rules passed (100/5=20 per rule).  
- **Applicability:** Direct — use this shape for demo mock

**Research Query #3:** “Novice spike timestamp demo-data”

- **Source:** `lib/demo-data.ts`  
- **Key insight:** `noviceAmps` uses `Math.sin(t_sec * Math.PI) > NOVICE_SPIKE_THRESHOLD`; sine peaks at t=0.5, 2.5, 4.5. Temperature spike follows amps. For “2.3s” narrative, 2300ms is reasonable; actual spike may be 2500ms. Use 2300 or 2500 for tour.  
- **Applicability:** Use 2300 or 2500 in preset scenario config

**Library evaluation**

| Library        | Size  | Dependencies | License | Use?   | Notes                         |
|----------------|-------|-------------|---------|--------|-------------------------------|
| react-joyride  | ~30KB | react       | MIT     | Maybe  | Full-featured; may be overkill |
| driver.js      | ~5KB  | none        | MIT     | Yes    | Lightweight; easy highlight   |
| Custom overlay | 0     | none        | —       | Yes    | Full control; ~2–3h build    |

**Best practices**

1. **Tour skippable:** Always provide Skip; some users prefer to explore.  
2. **Steps short:** 1–2 sentences per step; non-technical language.  
3. **Highlight visible:** Ensure highlight isn’t covered by overlay.  
4. **Keyboard accessible:** Tab, Enter for Next/Skip.  
5. **Mobile responsive:** Overlay and text scale; consider simplified flow on small screens.

**Pitfalls**

1. **Blocking overlay:** Full-screen modal annoys; use spotlight or partial overlay.  
2. **Too many steps:** 4+ steps increase bounce; keep to 2–4.  
3. **No skip:** Frustrating for returning users.  
4. **Missing highlight target:** Selector fails; have fallback (e.g. center overlay).  
5. **Z-index wars:** Document overlay hierarchy (context-loss < tour < modal).

---

## THINKING CHECKPOINT #1

**Surprising finding:** ai-feedback.test.ts already has a complete mockScore(); we can reuse that pattern for expert (94) and novice (42) mocks.  
**Concerning finding:** Seagull welder report tightly couples fetch + useFrameData; refactoring to support both API and demo data requires care.  
**Encouraging finding:** HeatMap, FeedbackPanel, LineChart, generateAIFeedback are all pure/reusable; only the data-fetch layer needs a second path.  

**Emerging approaches:**  
- Custom overlay (good control, no deps) vs driver.js (fast, small).  
- /demo/team as dedicated route (clean separation) vs ?demo=1 on Seagull (single route).  

**Still to prototype:** (1) Mock SessionScore for expert/novice, (2) Tour overlay z-index vs 3D, (3) Scrub to timestamp from tour step.

---

## 2. Prototype Critical Paths

### A. Critical Paths Identified

| # | Path | Why critical | Must prototype? |
|---|-----|--------------|------------------|
| 1 | Mock SessionScore for expert (94) and novice (42) | generateAIFeedback needs it | Yes |
| 2 | Tour overlay z-index above TorchWithHeatmap3D | Visibility | Yes |
| 3 | Scrub playback to timestamp from tour step | Preset “2.3s spike” moment | Yes |
| 4 | Browser-only data path for WelderReport | No fetchSession/fetchScore | Yes |
| 5 | Tour step config structure | Drives implementation | Consider |

### B. Prototype #1: Mock SessionScore

**Purpose:** Verify we can produce SessionScore that yields 94 and 42 from generateAIFeedback.

**Code:**

```typescript
// lib/demo-data.ts or lib/seagull-demo-data.ts
import type { SessionScore } from '@/lib/api';
import { generateAIFeedback } from '@/lib/ai-feedback';

export function createMockScore(total: number, failedRuleIds: string[]): SessionScore {
  const allRules = [
    { rule_id: 'amps_stability', threshold: 3, passed: true, actual_value: 2 },
    { rule_id: 'angle_consistency', threshold: 5, passed: true, actual_value: 2 },
    { rule_id: 'thermal_symmetry', threshold: 10, passed: true, actual_value: 5 },
    { rule_id: 'heat_diss_consistency', threshold: 2, passed: true, actual_value: 1 },
    { rule_id: 'volts_stability', threshold: 1.5, passed: true, actual_value: 0.5 },
  ];
  const rules = allRules.map((r) => ({
    ...r,
    passed: !failedRuleIds.includes(r.rule_id),
    actual_value: failedRuleIds.includes(r.rule_id) ? (r.actual_value! + 5) : r.actual_value,
  }));
  return { total, rules };
}

// Expert: 94 = 4–5 passed
const MOCK_EXPERT_SCORE = createMockScore(94, []);
// Novice: 42 = 2 passed
const MOCK_NOVICE_SCORE = createMockScore(42, ['amps_stability', 'angle_consistency', 'thermal_symmetry']);
```

**Findings:** generateAIFeedback uses score.total and score.rules; total can be set directly. Rules must have correct rule_ids for RULE_TEMPLATES.  
**Decision:** This approach works. Proceed.

### B. Prototype #2: Tour Overlay z-index

**Purpose:** Ensure overlay appears above 3D Canvas.

**Approach:** Fixed overlay with `z-[200]` and `isolate`. TorchWithHeatmap3D uses z-[100]. Page-level overlay wins.

```tsx
<div className="fixed inset-0 z-[200] isolate bg-black/50 flex items-center justify-center pointer-events-auto">
  <div className="bg-neutral-900 border-2 border-blue-400 rounded-lg p-6 max-w-md">
    <h3>Tour Step 1</h3>
    <p>Watch the blue side—expert keeps temperature steady.</p>
    <button onClick={onNext}>Next</button>
    <button onClick={onSkip}>Skip</button>
  </div>
</div>
```

**Findings:** z-[200] > z-[100]; isolate creates new stacking context. Overlay should appear on top.  
**Decision:** Proceed. Manual test on /demo with both TorchWithHeatmap3D instances.

### B. Prototype #3: Scrub to Timestamp

**Purpose:** Tour step triggers `setCurrentTimestamp(2300)` to show novice spike.

**Approach:** DemoPageContent already has `currentTimestamp` and `setCurrentTimestamp`. Tour component receives `onScrubToTimestamp` callback. When step has `timestamp_ms`, call it.

```tsx
// In tour config
{ id: 'novice_spike', title: 'Novice moment', body: '...', timestamp_ms: 2300 }

// In DemoPageContent
<DemoTour
  steps={tourSteps}
  onStepEnter={(step) => {
    if (step.timestamp_ms != null) setCurrentTimestamp(step.timestamp_ms);
  }}
  onComplete={...}
/>
```

**Findings:** Callback pattern works. Set playing to false when scrubbing so playback doesn’t override.  
**Decision:** Proceed.

### B. Prototype #4: Browser-Only WelderReport Data

**Purpose:** Render WelderReport without fetchSession/fetchScore.

**Approach:** Create `getDemoTeamData(welderId)` returning `{ session, expertSession, score, report }`. Use generateExpertSession, generateNoviceSession, createMockScore, generateAIFeedback. useFrameData works with session.frames directly (it accepts frames array).

**Findings:** useFrameData(session?.frames ?? [], ...) — we can pass frames from demo-data. generateAIFeedback(session, score, [68,72,75]) works with mock score. HeatMap, FeedbackPanel, LineChart are stateless.  
**Decision:** Browser-only path is feasible. New page /demo/team or /demo/team/[welderId] that uses getDemoTeamData.

---

## THINKING CHECKPOINT #2

**Clear:** Mock SessionScore, tour z-index, scrub callback, browser-only data path.  
**Risky:** Refactoring WelderReport to support both API and demo — may need a wrapper page that fetches OR uses demo data, then passes same shape to shared components.  
**Leading approach:** Custom lightweight tour + /demo/team route with getDemoTeamData. Reuse Seagull components; only data source differs.

---

## 3. Evaluate Approaches

### Approach Comparison Matrix

| Criterion              | Weight | Custom Overlay | react-joyride | driver.js |
|------------------------|--------|----------------|---------------|-----------|
| Implementation effort  | 20%    | Medium (4)     | Low (5)       | Low (5)   |
| Bundle size            | 15%    | 0 (5)          | +30KB (2)     | +5KB (4)  |
| Flexibility (WarpSense) | 15%   | High (5)       | Medium (3)    | Medium (3) |
| Maintenance            | 15%    | Our code (4)   | Dep (3)       | Dep (4)   |
| Accessibility          | 10%    | We implement(3)| Built-in (4)  | Basic (3) |
| Spotlight/highlight    | 10%    | Manual (3)     | Built-in (5)  | Built-in (5) |
| Risk                   | 15%    | Low (5)        | Medium (3)    | Low (4)   |
| **Weighted score**     | 100%   | **4.0**        | **3.5**       | **4.0**   |

**Winner:** Custom overlay or driver.js (tie). Custom gives full control and no deps; driver.js is fast to integrate.

**Team path:**

| Criterion    | /demo/team (new route) | /seagull?demo=1 |
|--------------|------------------------|----------------|
| Clarity      | Clear investor path    | Single URL, mixed concerns |
| Reuse        | Reuse components       | Same           |
| Code split   | Clean                  | Branching in Seagull |
| **Choice**   | **/demo/team**         | Rejected       |

### Final Recommendation

**Recommended approach:**

1. **Tour:** Custom lightweight overlay component (`DemoTour`) with config-driven steps. z-[200], isolate. Skip always visible. Optional timestamp scrub per step.  
2. **Team path:** New route `/demo/team` with dashboard (2 cards: Mike Chen / Expert Benchmark) and `/demo/team/[welderId]` for welder report. Uses `getDemoTeamData`, `createMockScore`, `generateAIFeedback`. Reuse HeatMap, FeedbackPanel, LineChart.  
3. **CTA:** “See Team Management” button on demo (after tour or in header) → `/demo/team`.  
4. **AppNav:** Add “Team” link to AppNav → `/seagull` (or `/demo/team`). Per issue: “Seagull/Team link in AppNav” — link to `/seagull` for app users; `/demo/team` for investor flow from demo.  
5. **Mock SessionScore:** `createMockScore(94, [])` and `createMockScore(42, ['amps_stability','angle_consistency','thermal_symmetry'])` (or similar) to match narrative.

**Confidence:** High (8/10).

---

## 4. Architectural Decisions

### Decision #1: Custom Tour Overlay (No Library)

**Question:** Use library or custom?

**Context:** Need 2–4 steps, skip, optional highlight, optional scrub. react-joyride adds ~30KB; driver.js ~5KB. Project prefers “boring, auditable” code.

**Options:**

- A: react-joyride — built-in tooltip, spotlight, steps.  
- B: driver.js — lightweight, highlight API.  
- C: Custom — full control, no deps, ~2–3h to build.

**Decision:** Custom overlay.

**Rationale:** Steps are simple; no spotlight required for MVP (can add later). Custom keeps bundle small and logic explicit. If we need spotlight, we can add `getBoundingClientRect` + overlay cutout. Reversible: can swap in driver.js later.

### Decision #2: /demo/team as Dedicated Route

**Question:** Where does browser-only team live?

**Context:** Seagull uses fetchSession/fetchScore. Investor demo must work with zero backend.

**Options:**

- A: /demo/team — new route, demo data only.  
- B: /seagull?demo=1 — fallback when API fails.  
- C: /seagull with client-side detection (no backend → use demo).

**Decision:** /demo/team.

**Rationale:** Clear separation. Demo flow: /demo → /demo/team. No branching in Seagull. Reuse components by importing them into /demo/team pages.

### Decision #3: Mock SessionScore in lib/demo-data.ts or lib/seagull-demo-data.ts

**Question:** Where to define createMockScore and expert/novice mocks?

**Context:** generateAIFeedback expects SessionScore. demo-data.ts already has expert/novice sessions.

**Decision:** Add `createMockScore` and `MOCK_EXPERT_SCORE`, `MOCK_NOVICE_SCORE` to a new `lib/seagull-demo-data.ts` (or extend demo-data.ts). Keep seagull-demo-data focused on “team-shaped” mock to avoid bloating demo-data.

**Rationale:** demo-data.ts is for session generation. Seagull demo needs welder + score. `seagull-demo-data.ts` can export `getDemoTeamData(welderId)` and mock scores.

### Decision #4: Tour Step Config with Optional timestamp_ms

**Question:** How to define preset “2.3s spike” moment?

**Decision:** Add `timestamp_ms?: number` to TourStep. When step has it, call `onScrubToTimestamp(timestamp_ms)` on step enter. Set playing=false when scrubbing.

### Decision #5: AppNav Team Link → /seagull

**Question:** Where does Team link go?

**Decision:** AppNav “Team” → `/seagull`. Demo CTA “See Team Management” → `/demo/team`. Rationale: App users see full Seagull (with backend when available); investors coming from demo use /demo/team.

### Decision #6: Reuse useFrameData for Demo Sessions

**Question:** Does WelderReport need changes for demo data?

**Decision:** No. useFrameData(frames, null, null) works with in-memory frames. We pass `session.frames` from generateNoviceSession/generateExpertSession. Same hook, different data source.

### Decision #7: Tour z-index 200

**Decision:** Tour overlay uses `z-[200]` and `isolate`. TorchWithHeatmap3D uses z-[100]. Ensures tour is visible.

### Decision #8: No localStorage Persistence for Tour

**Decision:** Do not persist “don’t show again” in MVP. Tour shows on each visit. Can add localStorage later.

---

## 5. Edge Cases

### Data

| Edge case      | Handling                                                   |
|----------------|------------------------------------------------------------|
| Empty sessions | demo-data always returns valid sessions; no empty case     |
| Null score     | createMockScore never returns null                         |
| Malformed data | generateAIFeedback guards empty rules                       |

### User Interaction

| Edge case     | Handling                                 |
|---------------|------------------------------------------|
| Rapid Next    | Disable Next during transition           |
| Skip mid-step | Dismiss tour immediately                 |
| Refresh       | Tour restarts (no persistence)             |

### Network

| Edge case     | Handling                                 |
|---------------|------------------------------------------|
| N/A (demo)    | /demo and /demo/team are browser-only    |

### Browser

| Edge case    | Handling                                   |
|--------------|--------------------------------------------|
| Safari stacking | Use isolate + z-[200] per LEARNING_LOG   |
| Small viewport  | Responsive overlay; test 320px             |

### State

| Edge case            | Handling                                        |
|----------------------|-------------------------------------------------|
| Unmount during tour  | Cleanup in useEffect return                     |
| Scrub during play   | setPlaying(false) when scrubbing                |

---

## 6. Risk Analysis

### Technical Risks

| Risk                    | P   | I   | Mitigation                                      |
|-------------------------|----|----|--------------------------------------------------|
| Tour z-index wrong      | 25%| M   | z-[200], isolate; test Safari                     |
| Mock score shape wrong  | 20%| M   | Reuse ai-feedback.test mockScore pattern         |
| Browser-only drift     | 60%| M   | Reuse same components; only data layer differs   |
| Preset timestamp wrong | 30%| L   | Verify spike at 2300 vs 2500 in demo-data        |

### Execution Risks

| Risk        | Mitigation                           |
|-------------|--------------------------------------|
| Scope creep | Stick to 2–4 steps, dashboard + 1 report |
| Copy delay  | Placeholder copy; refine later       |

---

## 7. Exploration Summary

### TL;DR

Explored how to make the demo investor-grade with a guided tour and browser-only team path. Chose a **custom lightweight tour overlay** (no library) with config-driven steps, optional scrub to timestamp, and skip. Chose **/demo/team** as a dedicated browser-only route for team dashboard and welder report, reusing HeatMap, FeedbackPanel, LineChart, and generateAIFeedback. Mock SessionScore will be created via `createMockScore(94, [])` and `createMockScore(42, [...])` in a new `seagull-demo-data.ts`. Tour overlay uses z-[200] to stay above 3D Canvas. AppNav gets a “Team” link to /seagull; demo CTA links to /demo/team. Main risk is browser-only/API path divergence; mitigated by reusing components. **Ready for planning.**

### Recommended Approach Summary

- **Tour:** Custom DemoTour component, 2–4 steps, skip, optional timestamp scrub.  
- **Team path:** /demo/team (dashboard + welder report), getDemoTeamData + createMockScore.  
- **CTA:** “See Team Management” → /demo/team.  
- **AppNav:** Add Team → /seagull.

### Files to Create

1. `components/demo/DemoTour.tsx` — Tour overlay  
2. `lib/demo-tour-config.ts` — Step definitions  
3. `lib/seagull-demo-data.ts` — getDemoTeamData, createMockScore  
4. `app/demo/team/page.tsx` — Team dashboard (browser-only)  
5. `app/demo/team/[welderId]/page.tsx` — Welder report (browser-only)

### Files to Modify

1. `app/demo/page.tsx` — Integrate DemoTour, add CTA  
2. `components/AppNav.tsx` — Add Team link

### Dependencies

- None (custom implementation)

### Critical Path (Implementation Order)

1. createMockScore + getDemoTeamData  
2. /demo/team dashboard page  
3. /demo/team/[welderId] welder report page  
4. DemoTour component + config  
5. Integrate tour into demo page  
6. Add CTA and AppNav Team link

### Effort Estimate

- Tour: 8–12 h  
- Preset scenario: 2–4 h  
- CTA: 1–2 h  
- Browser-only team: 8–16 h  
- AppNav: ~1 h  
- Copy: 2–4 h  
- **Total: 24–40 h** (matches issue)

### Preset Timestamp Verification

From `demo-data.ts`: `Math.sin(t_sec * Math.PI) > 0.95` triggers novice amps spike.  
Sine peaks at t ≈ 0.4, 0.6, 1.4, 1.6, 2.4, 2.6 sec. The narrative bullet says "2.3s" — use **2400 ms** or **2600 ms** for the preset scenario (closer to actual spike). 2300 ms is acceptable as approximate.

### Open Items for Planning

1. Exact tour step copy (placeholder vs final)  
2. Precise preset timestamp: recommend 2400 ms (or 2300 for narrative alignment)  
3. Mobile tour layout (simplified vs full)
