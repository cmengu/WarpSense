# Compare Page — Plain English Summary

**Overall Progress:** `100%`

## TLDR

Add a computed plain-English summary under the Compare page `<h1>` that synthesizes alert counts and end-of-session weld pool temperatures. After alerts and sessions load, the page shows a single sentence such as "Session A generated 2.3× more alerts and ran 45°C hotter than Session B." This improves investor/user comprehension without changing existing behavior.

---

## Critical Decisions

- **Decision 1:** Use `useMemo` with `[alertsA, alertsB, sessionA, sessionB, lastTimestamp]` — summary recomputes when alerts or session data changes; `lastTimestamp` ensures we use end-of-session temps.
- **Decision 2:** Use `extractCenterTemperatureWithCarryForward` (already imported) at `lastTimestamp ?? 0` — matches existing 3D viz logic.
- **Decision 3:** Handle both ratio directions — "Session A generated X× more alerts" when A ≥ B; "Session B generated Y× more alerts" when B > A. Same for temp: "Session A ran X°C hotter" vs "Session B ran X°C hotter."

---

## Clarification Gate

| Unknown | Required | Source | Blocking | Resolved |
|---------|----------|--------|----------|----------|
| H1 text change | Keep existing "Compare: {sessionIdA} vs {sessionIdB}" or use "Novice Welder vs Expert Welder"? | human | Step 1 | ⬜ Use existing — plan only adds summary under current h1 |

---

## Agent Failure Protocol

1. A verification command fails → read the full error output.
2. Cause is unambiguous → make ONE targeted fix → re-run the same verification command.
3. If still failing after one fix → **STOP**. Before stopping, output the full current contents of every file modified in this step. Report: (a) command run, (b) full error verbatim, (c) fix attempted, (d) current state of each modified file, (e) why you cannot proceed.
4. Never attempt a second fix without human instruction.
5. Never modify files not named in the current step.

---

## Pre-Flight — Run Before Any Code Changes

```
Read my-app/src/app/compare/[sessionIdA]/[sessionIdB]/page.tsx in full. Capture:
(1) Exact line where <h1 className="text-3xl font-semibold mb-2..."> appears
(2) Exact line where the following <p> (comparison.shared_count...) appears
(3) Dependencies: alertsA, alertsB, sessionA, sessionB, lastTimestamp — confirm all exist in ComparePageInner scope
(4) grep -n "extractCenterTemperatureWithCarryForward" my-app/src/app/compare --r
(5) cd my-app && npm test -- --testPathPattern="compare.*page" --passWithNoTests 2>&1 | tail -20
(6) wc -l my-app/src/app/compare/[sessionIdA]/[sessionIdB]/page.tsx

Do not change anything. Show full output and wait.
```

**Baseline Snapshot (agent fills during pre-flight):**
```
Test count (compare page tests): ____
Line count page.tsx: ____
h1 line: ____
```

**Automated checks (all must pass before Step 1):**
- [ ] Compare page tests pass
- [ ] `extractCenterTemperatureWithCarryForward` imported from `@/utils/frameUtils`
- [ ] `alertsA`, `alertsB`, `sessionA`, `sessionB`, `lastTimestamp` exist in `ComparePageInner`
- [ ] Single `<h1>` with "Compare:" in correct scope

---

## Environment Matrix

| Step | Dev | Staging | Prod | Notes |
|------|-----|---------|------|-------|
| Step 1 | ✅ | ✅ | ✅ | No environment-specific changes |

---

## Tasks

### Phase 1 — Add Plain English Summary

**Goal:** Summary text appears under the h1 when alerts or temp data is available.

---

- [x] 🟩 **Step 1: Add summaryText useMemo and render under h1** — *Non-critical: UI-only additive change*

  **Idempotent:** Yes — re-running produces same JSX; no side effects.

  **Context:** ComparePageInner shows session IDs and frame counts but no high-level insight. Adding a memoized summary gives users a quick "A vs B" readout (alert ratio and end-of-session temperature difference).

  **Pre-Read Gate:**
  - Run `grep -n '<h1 className="text-3xl font-semibold mb-2' my-app/src/app/compare/\[sessionIdA\]/\[sessionIdB\]/page.tsx` — must return exactly 1 match.
  - Run `grep -n 'lastTimestamp' my-app/src/app/compare/\[sessionIdA\]/\[sessionIdB\]/page.tsx` — confirm it exists (comparison.deltas).
  - Run `grep -n 'extractCenterTemperatureWithCarryForward' my-app/src/utils/frameUtils.ts` — confirm export exists.

  **Self-Contained Rule:** All code below is complete. No placeholders.

  **No-Placeholder Rule:** No `<VALUE>` tokens.

  **Code to add:**

  1. **Insert useMemo** — after `lastTimestamp` (around line 137), before `floorTs`:

  ```typescript
  const summaryText = useMemo(() => {
    if (!alertsA.length && !alertsB.length) return null;
    let ratioPart: string | null = null;
    if (alertsA.length > 0 && alertsB.length === 0) {
      ratioPart = 'Session A had all the alerts';
    } else if (alertsA.length === 0 && alertsB.length > 0) {
      ratioPart = 'Session B had all the alerts';
    } else if (alertsA.length > 0 && alertsB.length > 0) {
      const ratio = (alertsA.length / alertsB.length).toFixed(1);
      ratioPart =
        Number(ratio) >= 1
          ? `Session A generated ${ratio}× more alerts`
          : `Session B generated ${(alertsB.length / alertsA.length).toFixed(1)}× more alerts`;
    }
    const tempA = sessionA?.frames
      ? extractCenterTemperatureWithCarryForward(sessionA.frames, lastTimestamp ?? 0)
      : null;
    const tempB = sessionB?.frames
      ? extractCenterTemperatureWithCarryForward(sessionB.frames, lastTimestamp ?? 0)
      : null;
    const tempDiff =
      tempA != null && tempB != null ? Math.abs(tempA - tempB) : null;
    const tempPart =
      tempDiff != null && tempDiff > 0
        ? (tempA as number) > (tempB as number)
          ? `Session A ran ${tempDiff.toFixed(0)}°C hotter than Session B`
          : `Session B ran ${tempDiff.toFixed(0)}°C hotter than Session A`
        : null;
    const parts = [ratioPart, tempPart].filter(Boolean);
    return parts.length > 0 ? parts.join(' and ') + '.' : null;
  }, [alertsA, alertsB, sessionA, sessionB, lastTimestamp]);
  ```

  **Note:** The user's snippet said "ran X hotter than Session B" for the temp part. The above logic correctly handles both directions: when A > B we say "ran X hotter than Session B" (A is subject); when B > A we say "Session B ran X hotter than Session A."

  2. **Insert JSX** — directly under the h1 (after `</h1>`, before the existing comparison `<p>`):

  ```tsx
        <h1 className="text-3xl font-semibold mb-2 text-black dark:text-zinc-50">
          Compare: {sessionIdA} vs {sessionIdB}
        </h1>
        {summaryText && (
          <p className="text-base text-zinc-400 mb-2 font-medium">
            {summaryText}
          </p>
        )}
        {comparison && (
  ```

  **What it does:** Derives alert ratio and end-of-session center temp diff; builds a sentence and renders it only when non-empty.

  **Why this approach:** UseMemo avoids recalculation on every render; deps ensure freshness when alerts/sessions load.

  **Assumptions:**
  - `lastTimestamp` is the end of overlap (from comparison.deltas)
  - `extractCenterTemperatureWithCarryForward` accepts `frames` and `timestamp_ms`
  - `sessionA?.frames` and `sessionB?.frames` are sorted by `timestamp_ms`

  **Risks:**
  - `text-zinc-400` may be low-contrast in light mode → mitigation: user requested this class; can tune later.
  - When both ratio and temp are null → returns null; no empty string shown.

  **Git Checkpoint:**
  ```bash
  git add my-app/src/app/compare/[sessionIdA]/[sessionIdB]/page.tsx
  git commit -m "compare: add plain English summary under h1"
  ```

  **Subtasks:**
  - [x] 🟩 Add summaryText useMemo after lastTimestamp
  - [x] 🟩 Add conditional <p> block under h1

  **✓ Verification Test:**

  **Type:** Unit (Jest)

  **Action:**
  ```bash
  cd my-app && npm test -- --testPathPattern="compare.*page" --passWithNoTests
  ```

  **Expected:** All compare page tests pass.

  **Observe:** Jest output.

  **Pass:** Exit code 0, no failing tests.

  **Fail:**
  - If `summaryText` causes "Cannot read property of undefined" → check `lastTimestamp` null handling in useMemo
  - If test "renders two torch instances" fails → ensure new JSX did not break layout (no extra wrapper that alters structure)

---

## Regression Guard

**Systems at risk:**
- Compare page layout — new `<p>` could affect spacing.

**Regression verification:**

| System | Pre-change behavior | Post-change verification |
|--------|---------------------|---------------------------|
| Compare page | Renders h1, comparison p, heatmaps, alert feed | Same elements render; summary appears when alerts/temp exist |
| Compare tests | All pass | `npm test -- --testPathPattern="compare.*page"` passes |

**Test count regression check:**
- Tests before plan (from Pre-Flight): `____`
- Tests after plan: must be `≥` baseline.

---

## Rollback Procedure

```bash
git revert HEAD
# or
git checkout HEAD~1 -- my-app/src/app/compare/[sessionIdA]/[sessionIdB]/page.tsx
```

---

## Pre-Flight Checklist

| Phase | Check | How to Confirm | Status |
|-------|-------|----------------|--------|
| Pre-flight | Baseline snapshot captured | Test count + line count recorded | ⬜ |
| | h1 anchor exists once | grep returns 1 match | ⬜ |
| | extractCenterTemperatureWithCarryForward imported | grep in page.tsx | ⬜ |
| Step 1 | Existing tests pass | npm test compare page | ⬜ |

---

## Risk Heatmap

| Step | Risk Level | What Could Go Wrong | Early Detection | Idempotent |
|------|-----------|---------------------|-----------------|------------|
| Step 1 | 🟢 Low | Typo in useMemo deps causes stale summary | Tests pass; manual check summary updates | Yes |

---

## Success Criteria

| Feature | Target | Verification |
|---------|--------|--------------|
| Summary text | Renders when alerts or temp differ | Do: load compare with 2 sessions with alerts — Expect: sentence under h1 — Look: DOM |
| No alerts/temp | Summary hidden | Do: load compare with 0 alerts both sides — Expect: no summary p — Look: no extra paragraph |
| Alert ratio | Correct A:B or B:A | Do: A=10 alerts, B=5 — Expect: "Session A generated 2.0× more alerts" |
| Temp diff | Correct °C and direction | Do: A hotter at end — Expect: "ran X°C hotter than Session B" |
| Tests | ≥ pre-plan | Run `npm test -- --testPathPattern="compare.*page"` → pass |

---

⚠️ **Do not mark Step 1 🟩 Done until verification test passes.**
⚠️ **Do not batch steps into one git commit.**
