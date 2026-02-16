# Code Review Report - Round 1

## Demo Page (browser-only-demo-mode-plan.md)

**Scope:** All files created or modified for the browser-only demo mode implementation.

---

## Summary

- **Files Reviewed:** 7
- **Total Issues Found:** 18
- **CRITICAL:** 0 issues
- **HIGH:** 4 issues
- **MEDIUM:** 6 issues
- **LOW:** 8 issues

---

## Files Under Review

### Created Files

1. `my-app/src/lib/demo-data.ts` (227 lines)
2. `my-app/src/app/demo/page.tsx` (320 lines)
3. `my-app/src/app/demo/layout.tsx` (32 lines)
4. `my-app/src/__tests__/app/demo/page.test.tsx` (109 lines)
5. `my-app/src/__tests__/lib/demo-data.test.ts` (119 lines)

### Modified Files

1. `my-app/src/components/AppNav.tsx` (42 lines) — Demo link added
2. `my-app/src/app/page.tsx` (176 lines) — "Try demo" links in loading/error/no-data states

**Total:** 7 files, ~1025 lines of code

---

## Issues by Severity

### 🚨 CRITICAL Issues (Must Fix Before Deploy)

*None found.* No hardcoded secrets, SQL injection, XSS, or data integrity violations.

---

### ⚠️ HIGH Priority Issues (Fix Soon)

#### 1. **[HIGH]** `my-app/src/app/demo/page.tsx:49-50` — Duplicated constants

- **Issue:** `DURATION_MS` and `FRAME_INTERVAL_MS` are defined locally and also exist in `demo-data.ts`. If one is updated without the other, playback and data will desync.
- **Code:**
  ```typescript
  const DURATION_MS = 15000;
  const FRAME_INTERVAL_MS = 10;
  ```
- **Risk:** Maintenance drift; playback could run past data or stop early
- **Fix:** Import from a shared source (e.g. `demo-data.ts` or `src/constants/demo.ts`):
  ```typescript
  import { DURATION_MS, FRAME_INTERVAL_MS } from '@/lib/demo-data';
  // Or export from demo-data and import here
  ```
  If `demo-data.ts` doesn't export these, add:
  ```typescript
  export const DURATION_MS = 15000;
  export const FRAME_INTERVAL_MS = 10;
  ```

#### 2. **[HIGH]** `my-app/src/app/demo/layout.tsx` — ErrorBoundary "Try again" won't recover from session-generation failure

- **Issue:** If `generateExpertSession()` or `generateNoviceSession()` throws during `useState` init, the ErrorBoundary catches it. Clicking "Try again" re-mounts the page, which re-runs the same `useState` initializer and throws again.
- **Risk:** User gets stuck in an error loop; only a full page refresh can recover
- **Fix:** Add a demo-specific fallback that directs the user to refresh:
  ```tsx
  <ErrorBoundary
    fallback={
      <div className="p-8 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
        <h2 className="text-lg font-semibold text-red-800 dark:text-red-400 mb-2">
          Demo failed to load
        </h2>
        <p className="text-sm text-red-600 dark:text-red-500 mb-4">
          Session data could not be generated. Please refresh the page.
        </p>
        <button
          onClick={() => typeof window !== 'undefined' && window.location.reload()}
          className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
        >
          Refresh page
        </button>
      </div>
    }
  >
    {children}
  </ErrorBoundary>
  ```

#### 3. **[HIGH]** `my-app/src/app/demo/page.tsx:56-71` — Synchronous session generation blocks main thread

- **Issue:** `generateExpertSession()` and `generateNoviceSession()` run synchronously in `useState` initializers. Each creates 1500 frames with thermal snapshots. Total ~3000 frames built on mount.
- **Risk:** On low-end devices, 50–200ms+ main-thread blocking before first paint; potential jank
- **Fix:** Consider lazy initialization via `useMemo` with a loading state, or defer to `useEffect`:
  ```typescript
  const [sessions, setSessions] = useState<{ expert: Session; novice: Session } | null>(null);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    try {
      setSessions({
        expert: generateExpertSession(),
        novice: generateNoviceSession(),
      });
    } catch (err) {
      logError('DemoPage', err, { context: 'session-generation' });
      setError(err instanceof Error ? err : new Error(String(err)));
    }
  }, []);

  if (error) return <ErrorFallback error={error} />;
  if (!sessions) return <div role="status" aria-live="polite">Loading demo…</div>;
  ```

#### 4. **[HIGH]** `my-app/src/app/demo/layout.tsx:28-29` — `React.ReactNode` used without explicit React import

- **Issue:** `children: React.ReactNode` relies on React being in scope (global or transitive). No `import React` or `import type { ReactNode } from 'react'`.
- **Risk:** Fragile; can break if TS/ESLint config changes; some builds require explicit import
- **Fix:** Use explicit import:
  ```typescript
  import type { ReactNode } from 'react';

  export default function DemoLayout({ children }: { children: ReactNode }) {
    return <ErrorBoundary>{children}</ErrorBoundary>;
  }
  ```

---

### 📋 MEDIUM Priority Issues (Should Fix)

#### 5. **[MEDIUM]** `my-app/src/app/demo/page.tsx:255,261,265` — Hardcoded feedback bullets don't match actual data

- **Issue:** Novice feedback says "Temperature spike at 2.3s (+65°C)" and "Erratic heat dissipation (10-120°C/s)". Demo data has `heat_dissipation_rate_celsius_per_sec: null` for all frames. Spike timing is driven by `Math.sin(t_sec * Math.PI) > 0.95`, which peaks near 0.5s, 1.5s, 2.5s — not exactly 2.3s.
- **Impact:** Misleading for users who correlate feedback with visuals
- **Fix:** Either derive feedback from actual data (e.g. detect spike timestamps, compute dissipation) or label as illustrative: e.g. "Example: Temperature spike (similar pattern visible in novice data)".

#### 6. **[MEDIUM]** `my-app/src/app/page.tsx:69-78` — Retry button lacks error logging

- **Issue:** On retry, `fetchDashboardData()` is called. `.catch(setError)` updates state but does not call `logError`. Failures are invisible to monitoring.
- **Code:**
  ```typescript
  .catch((err) => setError(err instanceof Error ? err.message : String(err)))
  ```
- **Fix:**
  ```typescript
  import { logError } from '@/lib/logger';

  .catch((err) => {
    logError('HomePage', err, { context: 'dashboard-retry' });
    setError(err instanceof Error ? err.message : String(err));
  })
  ```

#### 7. **[MEDIUM]** `my-app/src/app/demo/page.tsx:283-286` — Time display not announced to screen readers during playback

- **Issue:** Playback updates time every 10ms. The time span has no `aria-live`, so screen reader users don't hear updates.
- **Fix:** Add `aria-live="polite"` and `role="status"` to the time display container:
  ```tsx
  <div
    className="flex flex-col"
    role="status"
    aria-live="polite"
    aria-label={`Playback time: ${(currentTimestamp / 1000).toFixed(1)} seconds`}
  >
    <span className="text-cyan-400 text-sm">Time</span>
    <span className="text-white font-mono">
      {(currentTimestamp / 1000).toFixed(1)}s / 15.0s
    </span>
  </div>
  ```

#### 8. **[MEDIUM]** `my-app/src/app/demo/page.tsx:206-207` — Magic numbers in expert feedback

- **Issue:** "Consistent temperature (±5°C)" and "Smooth heat dissipation (30°C/s)" use hardcoded values. Expert frames have `heat_dissipation_rate_celsius_per_sec: null`.
- **Impact:** Feedback is illustrative, not data-driven; could confuse users comparing to actual charts
- **Fix:** Document as illustrative, or compute from `extractCenterTemperatureWithCarryForward` variance if desired.

#### 9. **[MEDIUM]** `my-app/src/lib/demo-data.ts` — No explicit DURATION_MS/FRAME_INTERVAL_MS export

- **Issue:** Constants are internal. Page duplicates them. Centralizing would reduce drift risk.
- **Fix:** Export from `demo-data.ts`:
  ```typescript
  export const DURATION_MS = 15000;
  export const FRAME_INTERVAL_MS = 10;
  ```

#### 10. **[MEDIUM]** `my-app/src/__tests__/app/demo/page.test.tsx` — Test does not verify playback advancement

- **Issue:** Tests check play/pause toggle but do not assert that `currentTimestamp` advances when playing.
- **Fix:** Use `jest.useFakeTimers()` and advance time to verify timestamp increments:
  ```typescript
  it('advances timestamp when playing', () => {
    jest.useFakeTimers();
    render(<DemoPage />);
    fireEvent.click(screen.getByRole('button', { name: /play demo/i }));
    act(() => { jest.advanceTimersByTime(100); });
    expect(screen.getByText(/0\.1s \/ 15\.0s/)).toBeInTheDocument();
    jest.useRealTimers();
  });
  ```

---

### 💡 LOW Priority Issues (Nice to Have)

#### 11. **[LOW]** `my-app/src/app/page.tsx:43-48, 84-88, 104-108` — Use Next.js `Link` instead of `<a href="/demo">`

- **Issue:** Three "Try demo" links use `<a href="/demo">`. Next.js `Link` provides client-side navigation and prefetching.
- **Fix:** Replace with `<Link href="/demo">` for faster navigation.

#### 12. **[LOW]** `my-app/src/app/demo/page.tsx` — JSDoc could document props/behavior

- **Issue:** DemoPage has no props but could document playback behavior (0→15s, stop at end, no loop).
- **Fix:** Optional JSDoc for future maintainers.

#### 13. **[LOW]** `my-app/src/app/demo/page.tsx:154-210` — Column structure could use semantic elements

- **Issue:** Expert/novice columns use `<div className="space-y-6">`. Could use `<section>` or `<article>` for better semantics.
- **Fix:** `<section aria-label="Expert welder comparison">` for each column.

#### 14. **[LOW]** `my-app/src/__tests__/app/demo/page.test.tsx:20-25` — Unused mock parameters

- **Issue:** `_importFn` and `_options` are prefixed with underscore (unused). Convention is fine, but could add `// eslint-disable-next-line @typescript-eslint/no-unused-vars` if lint rules flag them.

#### 15. **[LOW]** `my-app/src/components/AppNav.tsx:17` — Redundant path check

- **Issue:** `pathname.startsWith('/demo')` is redundant if `/demo` has no sub-routes. `pathname === '/demo'` suffices.
- **Fix:** Simplify to `const isDemo = pathname === '/demo';` unless sub-routes are planned.

#### 16. **[LOW]** `my-app/src/lib/demo-data.ts:178,211` — `new Date().toISOString()` called twice per session

- **Issue:** `start_time` and `completed_at` may differ by 1ms. Cosmetically inconsistent.
- **Fix:** Single `const now = new Date().toISOString();` used for both.

#### 17. **[LOW]** `my-app/src/app/demo/page.tsx:271` — Playback button lacks focus ring

- **Issue:** Button has `transition` but no explicit `focus:outline-none focus:ring-2 focus:ring-cyan-400` for keyboard users.
- **Fix:** Add focus styles: `focus:outline-none focus:ring-2 focus:ring-cyan-400 focus:ring-offset-2 focus:ring-offset-neutral-950`

#### 18. **[LOW]** `my-app/src/__tests__/lib/demo-data.test.ts` — No test for thermal value ranges

- **Issue:** Tests check `point_count > 0` and `t0 > 100 && t0 < 800`, but not that temps stay within physically plausible range across all frames.
- **Fix:** Optional assertion that all temps are 0–1000°C for sanity.

---

## Issues by File

### `my-app/src/lib/demo-data.ts`
- Lines 178, 211: [LOW] Duplicate `new Date().toISOString()` calls
- No DURATION_MS/FRAME_INTERVAL_MS export: [MEDIUM]

### `my-app/src/app/demo/page.tsx`
- Lines 49-50: [HIGH] Duplicated constants
- Lines 56-71: [HIGH] Blocking session generation
- Lines 206-207, 255, 261, 265: [MEDIUM] Hardcoded feedback vs actual data
- Lines 283-286: [MEDIUM] Time display missing aria-live
- Line 271: [LOW] Playback button focus ring

### `my-app/src/app/demo/layout.tsx`
- Lines 26-31: [HIGH] ErrorBoundary retry won't recover; [HIGH] React.ReactNode without import

### `my-app/src/app/page.tsx`
- Lines 69-78: [MEDIUM] Retry lacks logError
- Lines 43-48, 84-88, 104-108: [LOW] Use Link instead of `<a>`

### `my-app/src/components/AppNav.tsx`
- Line 17: [LOW] Redundant pathname check

### `my-app/src/__tests__/app/demo/page.test.tsx`
- [MEDIUM] No playback advancement test
- Lines 20-25: [LOW] Unused mock params

### `my-app/src/__tests__/lib/demo-data.test.ts`
- [LOW] No thermal range assertion

---

## Positive Findings ✅

- **Logging:** Demo page uses `logError` correctly; no raw `console.log` in app code
- **TypeScript:** No `any`, `@ts-ignore`, or `@ts-expect-error` in demo files
- **Error boundaries:** Viz components wrapped in ErrorBoundary; WebGL loss handled in TorchViz3D
- **WebGL:** Exactly 2 TorchViz3D instances; ESLint rule enforces limit; context-loss overlay present
- **Accessibility:** Playback button has `aria-label`; slider has `aria-label` and `aria-valuetext`; decorative elements use `aria-hidden`
- **Hooks:** useEffect has cleanup (`clearInterval`); playback wrap-around handled via ref + effect
- **Memoization:** `useMemo` for heatmap/angle extraction; stable session state
- **Tests:** Good coverage for smoke, scores, controls, mocks; demo-data unit tests verify frame structure and integration
- **Architecture:** Clear separation (demo-data, page, layout); reuses existing components and utils

---

## Recommendations for Round 2

1. Fix all HIGH issues, especially constant duplication and ErrorBoundary recovery.
2. Add `logError` to home page retry path.
3. Improve accessibility of time display for screen readers.
4. Consider async session generation for performance.
5. Add playback advancement test.

---

## Testing Checklist for Developer

- [ ] DURATION_MS/FRAME_INTERVAL_MS single source of truth
- [ ] ErrorBoundary fallback includes "Refresh" for session-generation failure
- [ ] ReactNode import explicit in demo layout
- [ ] TypeScript compiles with no errors
- [ ] ESLint passes
- [ ] No raw console.log in demo code
- [ ] Time display has aria-live for playback
- [ ] Playback button has focus ring
- [ ] `npm test -- demo` passes
- [ ] Manual test: /demo loads, play/pause works, slider scrubs, no API calls

---

# Review Status: ✅ No CRITICAL Issues

**HIGH issues should be fixed before deployment.** Demo is functionally sound; improvements focus on maintainability, recovery, and accessibility.

**Total Issues:** 18 (CRITICAL: 0, HIGH: 4, MEDIUM: 6, LOW: 8)

**Next Step:** Address HIGH and selected MEDIUM issues, then request Round 2 review.
