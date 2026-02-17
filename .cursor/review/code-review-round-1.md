# Code Review Report - Round 1

## Summary

- **Files Reviewed:** 15
- **Total Issues Found:** 21
- **CRITICAL:** 0 issues
- **HIGH:** 6 issues
- **MEDIUM:** 8 issues
- **LOW:** 7 issues

---

## Files Under Review

### Created Files

1. `my-app/src/lib/demo-config.ts` (41 lines)
2. `my-app/src/__tests__/lib/demo-config.test.ts` (47 lines)
3. `my-app/src/utils/heatmapTempRange.ts` (39 lines)
4. `my-app/src/__tests__/utils/heatmapTempRange.test.ts` (72 lines)
5. `my-app/src/lib/seagull-demo-data.ts` (107 lines)
6. `my-app/src/__tests__/lib/seagull-demo-data.test.ts` (106 lines)
7. `my-app/src/app/demo/team/page.tsx` (45 lines)
8. `my-app/src/app/demo/team/[welderId]/page.tsx` (196 lines)
9. `my-app/src/__tests__/app/demo/team/[welderId]/page.test.tsx` (132 lines)
10. `my-app/src/lib/demo-tour-config.ts` (47 lines)
11. `my-app/src/components/demo/DemoTour.tsx` (131 lines)
12. `my-app/src/__tests__/lib/demo-tour-config.test.ts` (26 lines)
13. `my-app/src/__tests__/app/demo/team/page.test.tsx` (33 lines)

### Modified Files

1. `my-app/src/app/demo/page.tsx` (343 lines; modified for DemoTour, CTA, config-driven scores)
2. `my-app/src/components/AppNav.tsx` (61 lines; Team link to `/seagull`)

**Total:** 15 files, ~1,426 lines of code (excluding tests: ~1,122 LOC)

---

## Issues by Severity

### 🚨 CRITICAL Issues (Must Fix Before Deploy)

*No critical issues identified in the reviewed implementation.*

The codebase does not contain hardcoded secrets, SQL injection, or other critical security flaws in the new code. Error boundaries and logging are appropriately used.

---

### ⚠️ HIGH Priority Issues (Fix Soon)

1. **[HIGH]** `my-app/src/components/demo/DemoTour.tsx:94-98`
   - **Issue:** Backdrop div with `role="button"` does not handle Space key — only Enter.
   - **Code:** `onKeyDown={(e) => e.key === 'Enter' && handleSkip()}`
   - **Risk:** WCAG 2.1 requires both Enter and Space to activate buttons. Keyboard users pressing Space will not skip the tour.
   - **Fix:**
   ```typescript
   onKeyDown={(e) => {
     if (e.key === 'Enter' || e.key === ' ') {
       e.preventDefault();
       handleSkip();
     }
   }}
   ```

2. **[HIGH]** `my-app/src/components/demo/DemoTour.tsx:37-44`
   - **Issue:** Focus trap is incomplete — aria-modal="true" implies focus should be trapped, but there is no logic to prevent Tab from leaving the dialog.
   - **Code:** Effect focuses first focusable element but does not trap tab order.
   - **Risk:** Screen reader and keyboard users can tab out of the modal into the page beneath, violating modal semantics.
   - **Fix:** Implement proper focus trap (e.g. `focus-trap-react` or manual Tab/Shift+Tab handling to cycle within overlay focusables).

3. **[HIGH]** `my-app/src/app/demo/page.tsx:144`
   - **Issue:** Non-null assertion (`!`) used on `step.timestamp_ms`.
   - **Code:** `setCurrentTimestamp(step.timestamp_ms!);`
   - **Risk:** If the step shape changes and `timestamp_ms` is unexpectedly undefined, this could set `undefined` and cause downstream issues.
   - **Fix:**
   ```typescript
   const ts = step.timestamp_ms;
   if (ts != null) {
     scrubTimeoutRef.current = setTimeout(() => {
       setCurrentTimestamp(ts);
       setPlaying(false);
       scrubTimeoutRef.current = null;
     }, 150);
   }
   ```

4. **[HIGH]** `my-app/src/components/AppNav.tsx:50-56`
   - **Issue:** Team link points to `/seagull` while demo team dashboard is at `/demo/team`. Users in demo flow use CTA → `/demo/team`; users clicking "Team" in nav go to `/seagull` (backend-dependent).
   - **Code:** `<Link href="/seagull" ...>Team</Link>`
   - **Risk:** Investor demo flow: if user is on a page with AppNav (e.g. dashboard) and clicks Team, they get `/seagull` which fetches from API. Demo team is at `/demo/team`. Two different flows may confuse users and break offline/shareable demo expectations.
   - **Fix:** Document intent explicitly, or align: e.g. add Team nav item that routes to `/demo/team` when in demo context, or ensure `/seagull` gracefully degrades when API is unavailable.

5. **[HIGH]** `my-app/src/__tests__/lib/demo-tour-config.test.ts:16-17`
   - **Issue:** Non-null assertion on `step` in test.
   - **Code:** `expect(step!.timestamp_ms).toBe(NOVICE_SPIKE_MS);`
   - **Risk:** If `find` returns undefined, test would throw before assertion. Masks potential regression.
   - **Fix:**
   ```typescript
   const step = DEMO_TOUR_STEPS.find((s) => s.id === "novice_spike");
   expect(step).toBeDefined();
   if (!step) return;
   expect(step.timestamp_ms).toBe(NOVICE_SPIKE_MS);
   expect(step.timestamp_ms).toBe(2400);
   ```

6. **[HIGH]** `my-app/src/app/demo/team/[welderId]/page.tsx:99-101`
   - **Issue:** AI analysis summary rendered without sanitization. `report.summary` comes from `generateAIFeedback` (controlled) but the pattern could encourage future unsanitized user content.
   - **Code:** `<p className="text-sm font-medium">🤖 AI Analysis: {report.summary}</p>`
   - **Risk:** Low today — data is from `generateAIFeedback`. If `report.summary` is later sourced from user input or API, it could introduce XSS.
   - **Fix:** Add a comment that `report.summary` must remain server/controlled. If ever sourced from user input, sanitize or use a safe rendering approach.

---

### 📋 MEDIUM Priority Issues (Should Fix)

1. **[MEDIUM]** `my-app/src/app/demo/team/[welderId]/page.tsx:31-50`
   - **Issue:** PlaceholderHeatMap uses hardcoded light gradient (`#e2e8f0`, `#94a3b8`, `#64748b`) that does not adapt to dark mode.
   - **Code:** `background: "linear-gradient(135deg, #e2e8f0 0%, #94a3b8 50%, #64748b 100%)"`
   - **Impact:** In dark mode, the placeholder may look inconsistent with surrounding dark UI.
   - **Fix:** Use Tailwind gradient classes or CSS variables that respect dark mode, e.g. `bg-gradient-to-br from-zinc-200 to-zinc-500 dark:from-zinc-600 dark:to-zinc-800` or equivalent.

2. **[MEDIUM]** `my-app/src/lib/seagull-demo-data.ts:30-36`
   - **Issue:** `RULE_THRESHOLDS` typed as `Record<string, number>` — not enforced against `RULE_IDS`. Adding a new rule_id to RULE_IDS without updating RULE_THRESHOLDS is not type-checked.
   - **Code:** `const RULE_THRESHOLDS: Record<string, number> = { ... };`
   - **Impact:** Silent fallback to `5` for missing rules; easy to forget to add thresholds.
   - **Fix:**
   ```typescript
   const RULE_THRESHOLDS: Record<(typeof RULE_IDS)[number], number> = {
     amps_stability: 3,
     angle_consistency: 5,
     thermal_symmetry: 10,
     heat_diss_consistency: 2,
     volts_stability: 1.5,
   };
   ```

3. **[MEDIUM]** `my-app/src/lib/seagull-demo-data.ts:45-55`
   - **Issue:** `createMockScore` accepts `failedRuleIds: string[]` — any string is allowed. Unknown rule_ids appear as passed.
   - **Code:** `failedRuleIds: string[]`
   - **Impact:** Typos (e.g. `"amp_stability"`) would not fail; incorrect mock data could slip through.
   - **Fix:** Validate against RULE_IDS or use `(typeof RULE_IDS)[number][]` for type safety.

4. **[MEDIUM]** `my-app/src/lib/demo-tour-config.ts:34`
   - **Issue:** Step body text hardcodes "Around 2.4 seconds" — does not derive from `NOVICE_SPIKE_MS`.
   - **Code:** `body: "Around 2.4 seconds, the novice's current spikes..."`
   - **Impact:** If `NOVICE_SPIKE_MS` changes, the narrative and scrub behavior would be inconsistent.
   - **Fix:** Use template literal: `` `Around ${NOVICE_SPIKE_MS / 1000} seconds...` `` or a shared constant for the display string.

5. **[MEDIUM]** `my-app/src/app/demo/page.tsx:99-106` and `my-app/src/app/demo/DemoLayoutClient.tsx:21-25`
   - **Issue:** Redundant `typeof window !== 'undefined'` check before `window.location.reload()` in client components.
   - **Code:** `onClick={() => typeof window !== 'undefined' && window.location.reload()}`
   - **Impact:** Unnecessary; in 'use client' components, `window` is defined when handlers run.
   - **Fix:** Simplify to `onClick={() => window.location.reload()}`.

6. **[MEDIUM]** `my-app/src/app/demo/team/[welderId]/page.tsx:24-29`
   - **Issue:** `MOCK_HISTORICAL_CHART` duplicated pattern from `MOCK_HISTORICAL` in seagull-demo-data. Values differ slightly (68,72,75 vs seagull's [68,72,75]).
   - **Code:** `const MOCK_HISTORICAL_CHART = [{ date: "Week 1", value: 68 }, ...];`
   - **Impact:** Two sources of truth for mock historical scores; risk of drift.
   - **Fix:** Import `MOCK_HISTORICAL` from seagull-demo-data and map to chart shape, or export a shared constant from demo-config.

7. **[MEDIUM]** `my-app/src/app/demo/team/page.tsx:11`
   - **Issue:** `DEMO_WELDERS` imported from seagull-demo-data instead of demo-config.
   - **Code:** `import { DEMO_WELDERS } from "@/lib/seagull-demo-data";`
   - **Impact:** Indirection; demo-config is the documented single source of truth.
   - **Fix:** Import from `@/lib/demo-config` for consistency with plan ("CEO rule: No magic numbers outside this file" — welder list is config).

8. **[MEDIUM]** `my-app/src/components/demo/DemoTour.tsx:86`
   - **Issue:** Magic number `z-[200]` for overlay stacking.
   - **Code:** `className="fixed inset-0 z-[200] isolate..."`
   - **Impact:** Harder to maintain if multiple overlays need coordinated z-index.
   - **Fix:** Extract `const OVERLAY_Z = 200` (or from constants) and reference in JSDoc contingency note for Safari.

---

### 💡 LOW Priority Issues (Nice to Have)

1. **[LOW]** `my-app/src/app/demo/team/[welderId]/page.tsx:31`
   - **Issue:** PlaceholderHeatMap missing JSDoc.
   - **Code:** `function PlaceholderHeatMap({ label }: { label: string }) {`
   - **Impact:** Less discoverable for maintainers.
   - **Fix:** Add JSDoc describing purpose (neutral gradient when no thermal data).

2. **[LOW]** `my-app/src/app/demo/team/[welderId]/page.tsx:53`
   - **Issue:** WelderReportContent missing JSDoc.
   - **Fix:** Add JSDoc for params and role in page structure.

3. **[LOW]** `my-app/src/app/demo/team/[welderId]/page.tsx:34`
   - **Issue:** PlaceholderHeatMap container uses `heat-map-container` class — may not be defined in globals.
   - **Code:** `className="heat-map-container bg-white dark:bg-zinc-900..."`
   - **Impact:** Unused class or hidden styling dependency.
   - **Fix:** Remove if unused, or document in shared styles.

4. **[LOW]** `my-app/src/components/demo/DemoTour.tsx:19`
   - **Issue:** `onStepLog` prop is optional and unused in demo page — may be dead API.
   - **Impact:** Unused optional callback; could be removed or documented as for analytics.
   - **Fix:** Add JSDoc: "Optional callback for analytics/logging step views."

5. **[LOW]** `my-app/src/app/demo/team/[welderId]/page.test.tsx:37-59`
   - **Issue:** Mock implementation returns `report` with minimal fields; real `AIFeedbackResult` may have more.
   - **Impact:** Tests may pass while runtime type differs slightly.
   - **Fix:** Use `satisfies AIFeedbackResult` or import a factory from test utils.

6. **[LOW]** `my-app/src/utils/heatmapTempRange.ts:34`
   - **Issue:** Redundant check `min > max` — after filtering valid numbers, `Math.min`/`Math.max` guarantee min ≤ max.
   - **Code:** `if (min > max || !Number.isFinite(min) || !Number.isFinite(max))`
   - **Impact:** Defensive but slightly redundant; `min > max` is impossible with non-empty valid array.
   - **Fix:** Keep for robustness or simplify to `if (!Number.isFinite(min) || !Number.isFinite(max))` (single-point edge case is fine).

7. **[LOW]** `my-app/src/lib/demo-config.ts:31`
   - **Issue:** `DEMO_WELDERS` uses numeric literals (42, 94) instead of `MOCK_NOVICE_SCORE_VALUE` and `MOCK_EXPERT_SCORE_VALUE`.
   - **Code:** `{ id: "mike-chen", name: "Mike Chen", score: 42, variant: "novice" }`
   - **Impact:** If config values change, DEMO_WELDERS could drift.
   - **Fix:** Use `score: MOCK_NOVICE_SCORE_VALUE` and `score: MOCK_EXPERT_SCORE_VALUE` in DEMO_WELDERS.

---

## Issues by File

### `my-app/src/lib/demo-config.ts`
- Line 31-38: [LOW] DEMO_WELDERS uses magic numbers instead of MOCK_* constants

### `my-app/src/utils/heatmapTempRange.ts`
- Line 34: [LOW] Redundant min > max check

### `my-app/src/lib/seagull-demo-data.ts`
- Lines 30-36: [MEDIUM] RULE_THRESHOLDS not type-safe against RULE_IDS
- Lines 45-55: [MEDIUM] createMockScore accepts arbitrary failedRuleIds

### `my-app/src/lib/demo-tour-config.ts`
- Line 34: [MEDIUM] Hardcoded "2.4 seconds" in step body

### `my-app/src/components/demo/DemoTour.tsx`
- Lines 37-44: [HIGH] Incomplete focus trap for aria-modal
- Lines 94-98: [HIGH] Backdrop button missing Space key handler
- Line 86: [MEDIUM] Magic number z-[200]
- Line 19: [LOW] onStepLog undocumented

### `my-app/src/app/demo/page.tsx`
- Line 144: [HIGH] Non-null assertion on step.timestamp_ms
- Lines 99-106: [MEDIUM] Redundant window check

### `my-app/src/app/demo/DemoLayoutClient.tsx`
- Lines 21-25: [MEDIUM] Redundant window check (referenced in demo page context)

### `my-app/src/app/demo/team/page.tsx`
- Line 11: [MEDIUM] DEMO_WELDERS from seagull-demo-data instead of demo-config

### `my-app/src/app/demo/team/[welderId]/page.tsx`
- Lines 31-50: [MEDIUM] PlaceholderHeatMap light-only gradient
- Lines 24-29: [MEDIUM] Duplicated MOCK_HISTORICAL_CHART
- Lines 99-101: [HIGH] Document sanitization expectation for report.summary
- Lines 31, 53: [LOW] Missing JSDoc on PlaceholderHeatMap, WelderReportContent
- Line 34: [LOW] heat-map-container class usage

### `my-app/src/components/AppNav.tsx`
- Lines 50-56: [HIGH] Team link vs demo team route mismatch

### `my-app/src/__tests__/lib/demo-tour-config.test.ts`
- Lines 16-17: [HIGH] Non-null assertion in test

### `my-app/src/__tests__/app/demo/team/[welderId]/page.test.tsx`
- Lines 37-59: [LOW] Mock could use satisfies AIFeedbackResult

---

## Positive Findings ✅

- **demo-config.ts:** Clear single source of truth; constants well-documented; no magic numbers in score values within the config array (aside from LOW issue above).
- **heatmapTempRange.ts:** Robust handling of null/undefined/NaN/Infinity; pure function; good test coverage.
- **seagull-demo-data.ts:** `createMockScore` shape aligns with `generateAIFeedback`; good integration with RULE_TEMPLATES.
- **DemoTour.tsx:** aria-modal, aria-labelledby, aria-describedby, Escape handler, and cleanup on unmount are correct.
- **demo/page.tsx:** Error handling with logError; ErrorBoundary usage; proper cleanup of scrubTimeout; memoization of heatmap/angle data; no effect dependency suppressions.
- **Welder report page:** PlaceholderHeatMap prevents white screen; Suspense for async params; unknown welderId handled.
- **Tests:** Solid coverage for config, heatmap range, seagull data, tour config, and team pages.
- **No console.log/debugger/alert** in new production code.
- **No TODO/FIXME/XXX** in new code.
- **No @ts-ignore or `any`** in new code.
- **TypeScript strict mode** respected; explicit types throughout.

---

## Recommendations for Round 2

After fixes are applied:
1. **Re-check all HIGH issues** — Especially focus trap and Space key for DemoTour.
2. **Verify Team vs demo team routing** — Ensure investor demo flow is unambiguous.
3. **Run a11y audit** — axe-core or Lighthouse accessibility check on DemoTour and demo team pages.
4. **Confirm demos work offline** — `/demo` and `/demo/team` paths should not require API.
5. **Check 375px viewport** — Per implementation notes, verify layout at narrow width.

---

## Testing Checklist for Developer

Before requesting Round 2 review:
- [ ] All HIGH issues fixed and tested
- [ ] DemoTour: Space key skips tour; focus trapped within modal
- [ ] TypeScript compiles with no errors
- [ ] ESLint passes with no errors
- [ ] No non-null assertions (`!`) without explicit guards
- [ ] DEMO_WELDERS uses MOCK_NOVICE_SCORE_VALUE / MOCK_EXPERT_SCORE_VALUE
- [ ] Tour step body derives "2.4 seconds" from NOVICE_SPIKE_MS
- [ ] Manual test: /demo → tour → See Team Management → /demo/team
- [ ] Manual test: /demo/team/mike-chen and /demo/team/expert-benchmark
- [ ] Run: `npm test -- demo-config heatmapTempRange seagull-demo-data demo-tour-config demo/team`

---

# Review Status: ⚠️ HIGH ISSUES FOUND

**Recommend fixing HIGH issues before deployment.** No CRITICAL issues.

Total Issues: 21 (CRITICAL: 0, HIGH: 6, MEDIUM: 8, LOW: 7)

Next Step: Address HIGH and MEDIUM issues, then request Round 2 review.
