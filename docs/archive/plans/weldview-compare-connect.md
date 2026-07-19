# Plan: Connect Analysis Page to Compare Sessions

**Overall Progress:** `0%` (0 / 2 steps done)

---

## TLDR

The analysis page (`/analysis`) is the primary "weld view" surface — users select a session from the left panel and see the AI report in `QualityReportCard`. There is currently no path from this view to the compare feature. This plan adds a **"Compare" button** to `QualityReportCard`'s action footer. Clicking it navigates to `/compare?sessionA={session_id}`, which pre-fills the compare landing form with the current session so the user only needs to pick the second session. Two files are touched; no new files are created.

---

## Architecture Overview

**The problem this plan solves:**
`QualityReportCard` (`src/components/analysis/QualityReportCard.tsx`) has an action footer with "Export PDF", "Copy Session ID", and "Re-analyse" buttons. There is no "Compare" entry point. The only compare links in the app are on the dashboard and the replay page. A user working in the analysis view has no way to reach `/compare` without navigating away first.

**The pattern applied:**
*Callback prop delegation (same as `onReanalyse`).* `QualityReportCard` receives `onCompare?: () => void`; it does not own navigation logic. `AnalysisTimeline` owns the handler because it has `sessionId` in scope and is the natural place to build the `/compare?sessionA=…` URL. This mirrors the existing `onReanalyse` pattern exactly — the card fires a signal, the parent acts on it.

**What stays unchanged:**
- `src/app/(app)/analysis/page.tsx` — no changes; `AnalysisTimeline` handles the compare URL internally using `sessionId` it already holds.
- `src/app/compare/page.tsx` — already reads `?sessionA` from query params (confirmed at line 14). No changes needed.
- `src/components/analysis/SessionList.tsx` — no changes; compare is initiated from the report, not the list.
- All test files — no new tests required for a button that delegates to `router.push`.

**What this plan adds:**
- One new prop (`onCompare`) on `QualityReportCard` — owns nothing beyond rendering the button and calling the callback.
- One new handler + `useRouter` import in `AnalysisTimeline` — owns the URL construction and navigation.

**Critical decisions:**

| Decision | Alternative considered | Why alternative rejected |
|----------|----------------------|--------------------------|
| Handler lives in `AnalysisTimeline`, not `AnalysisPage` | Bubble callback to `AnalysisPage` (like `onReanalyse` for `handleReanalyse`) | `AnalysisTimeline` already has `sessionId`; adding one more prop passthrough to `AnalysisPage` adds noise with no benefit |
| Navigate to `/compare?sessionA={id}` (compare landing) | Navigate directly to `/compare/{id}/{DEFAULT_SESSION}` | Landing page lets user pick sessionB; direct URL would hard-code a second session the user may not want |
| `onCompare` is optional (`?`) | Required | Existing render contexts where `QualityReportCard` is used without a router (e.g. tests) must not break |

**Known limitations:**

| Limitation | Why acceptable now | Upgrade path |
|-----------|-------------------|--------------|
| User must still pick sessionB on the compare landing | Out of scope; the landing page `SessionBrowserPanel` already provides a good picker UI | Future: open `SessionBrowserPanel` inline on the analysis page if requested |

---

## Clarification Gate

All unknowns resolved from codebase reads. No human input required.

| Unknown | Required | Source | Resolved |
|---------|----------|--------|----------|
| Does compare landing pre-fill `?sessionA`? | Yes — confirmed line 14 of `compare/page.tsx` | Codebase | ✅ |
| Where is `QualityReportCard` rendered? | Inside `AnalysisTimeline` at line 279 | Codebase | ✅ |
| Does `AnalysisTimeline` already use `useRouter`? | No — must add import | Codebase | ✅ |
| Is `sessionId` accessible in `AnalysisTimeline` scope? | Yes — prop at line 28, used throughout | Codebase | ✅ |

---

## Agent Failure Protocol

1. A verification command fails → read the full error output.
2. Cause is unambiguous → make ONE targeted fix → re-run the same verification command.
3. If still failing after one fix → **STOP**. Output full contents of every modified file. Report: (a) command run, (b) full error verbatim, (c) fix attempted, (d) current state of each modified file, (e) why you cannot proceed.
4. Never attempt a second fix without human instruction.
5. Never modify files not named in the current step.

---

## Pre-Flight — Run Before Any Code Changes

```bash
# 1. Confirm QualityReportCard footer button section (anchor)
grep -n "onReanalyse\|Re-analyse\|Export PDF\|Copy Session" \
  src/components/analysis/QualityReportCard.tsx

# 2. Confirm AnalysisTimeline QualityReportCard call site
grep -n "QualityReportCard\|onReanalyse\|sessionId" \
  src/components/analysis/AnalysisTimeline.tsx

# 3. Confirm compare landing reads ?sessionA (no change needed but sanity check)
grep -n "sessionAFromQuery\|searchParams.get" \
  src/app/compare/page.tsx

# 4. Baseline test count
npx jest --no-coverage 2>&1 | tail -3
```

**Baseline Snapshot (agent fills during pre-flight):**
```
Test count before plan:         ____
Line count QualityReportCard:   396
Line count AnalysisTimeline:    ____
```

**Automated checks (all must pass before Step 1):**
- [ ] `onReanalyse` appears in `QualityReportCard.tsx` — confirms footer pattern to mirror
- [ ] `QualityReportCard` appears in `AnalysisTimeline.tsx` — confirms the call site
- [ ] `sessionId` appears as a prop in `AnalysisTimeline.tsx` — confirms URL can be built there
- [ ] `searchParams.get('sessionA')` exists in `compare/page.tsx` — confirms pre-fill works

---

## Tasks

### Phase 1 — Add "Compare" button to QualityReportCard

**Goal:** `QualityReportCard` has a "Compare" button in its footer that calls `onCompare?.()` when clicked.

---

- [ ] 🟥 **Step 1: Add `onCompare` prop and button to `QualityReportCard`** — *Non-critical: prop is optional; no existing consumers break*

  **Step Architecture Thinking:**

  **Pattern applied:** Open/Closed + Optional Callback Prop. The component is open for extension (new prop) without modifying any existing behavior. The button is disabled/invisible when `onCompare` is not provided (same as `Re-analyse`).

  **Why this step exists first in the sequence:**
  `AnalysisTimeline` (Step 2) passes `onCompare` to `QualityReportCard`. That prop must exist in the type before Step 2 can compile. Step 1 must complete first.

  **Why this file is the right location:**
  `QualityReportCard` owns the action footer UI. Adding the button here keeps all footer actions co-located and consistent in style.

  **Alternative approach considered and rejected:**
  Add a "Compare" link directly inside `AnalysisTimeline` outside of `QualityReportCard` — rejected because it would duplicate the footer affordance pattern and place a navigation trigger outside the card that owns it.

  **What breaks if this step deviates:**
  If `onCompare` is made required instead of optional, every existing test that renders `QualityReportCard` without the prop will throw a TypeScript error.

  ---

  **Idempotent:** Yes — adding an optional prop to an interface and a conditional button is safe to re-apply.

  **Context:** `QualityReportCard`'s footer currently has three buttons (lines ~368–393). This step adds a fourth button after "Re-analyse", matching the existing button style exactly.

  **Pre-Read Gate:**
  Before any edit:
  - Run `grep -n "onReanalyse\|Re-analyse" src/components/analysis/QualityReportCard.tsx`
    Must return matches inside the `QualityReportCardProps` interface AND the footer JSX. If 0 matches → STOP.
  - Run `grep -n "onCompare" src/components/analysis/QualityReportCard.tsx`
    Must return 0 matches (prop doesn't exist yet). If already present → STOP, it's already done.

  **Self-Contained Rule:** All code below is complete and runnable. No references to other steps.

  **No-Placeholder Rule:** No `<VALUE>` tokens anywhere below.

  ---

  **Edit 1 — Add `onCompare` to the props interface**

  In `src/components/analysis/QualityReportCard.tsx`, find:
  ```ts
  export interface QualityReportCardProps {
    report: WarpReport;
    /** Wired in Phase UI-7 from selectedSession.welder_name. */
    welderDisplayName?: string | null;
    /** Wired in Phase UI-7 to start analysis again for the same session. */
    onReanalyse?: () => void;
  }
  ```
  Replace with:
  ```ts
  export interface QualityReportCardProps {
    report: WarpReport;
    /** Wired in Phase UI-7 from selectedSession.welder_name. */
    welderDisplayName?: string | null;
    /** Wired in Phase UI-7 to start analysis again for the same session. */
    onReanalyse?: () => void;
    /** Navigate to /compare pre-filled with this session as sessionA. */
    onCompare?: () => void;
  }
  ```

  **Edit 2 — Destructure `onCompare` in the component signature**

  Find:
  ```ts
  export function QualityReportCard({
    report,
    welderDisplayName,
    onReanalyse,
  }: QualityReportCardProps) {
  ```
  Replace with:
  ```ts
  export function QualityReportCard({
    report,
    welderDisplayName,
    onReanalyse,
    onCompare,
  }: QualityReportCardProps) {
  ```

  **Edit 3 — Add "Compare" button in the footer**

  Find the exact Re-analyse button block:
  ```tsx
        <button
          type="button"
          onClick={() => onReanalyse?.()}
          disabled={!onReanalyse}
          className="font-mono text-[9px] uppercase tracking-widest px-2 py-0.5 border border-zinc-800 text-[var(--warp-text-muted)] hover:border-amber-400 hover:text-[var(--warp-amber)] transition-colors duration-100 disabled:opacity-30 disabled:cursor-not-allowed"
        >
          Re-analyse
        </button>
  ```
  Replace with:
  ```tsx
        <button
          type="button"
          onClick={() => onReanalyse?.()}
          disabled={!onReanalyse}
          className="font-mono text-[9px] uppercase tracking-widest px-2 py-0.5 border border-zinc-800 text-[var(--warp-text-muted)] hover:border-amber-400 hover:text-[var(--warp-amber)] transition-colors duration-100 disabled:opacity-30 disabled:cursor-not-allowed"
        >
          Re-analyse
        </button>

        <button
          type="button"
          onClick={() => onCompare?.()}
          disabled={!onCompare}
          className="font-mono text-[9px] uppercase tracking-widest px-2 py-0.5 border border-zinc-800 text-[var(--warp-text-muted)] hover:border-amber-400 hover:text-[var(--warp-amber)] transition-colors duration-100 disabled:opacity-30 disabled:cursor-not-allowed"
        >
          Compare
        </button>
  ```

  **What it does:** Adds `onCompare?: () => void` to the props contract and renders a "Compare" button in the footer that is greyed-out/disabled when no handler is provided (identical disabled behaviour to "Re-analyse").

  **Why this approach:** Mirrors the `onReanalyse` pattern exactly — consistent style, consistent disabled state, zero risk to existing consumers.

  **Assumptions:**
  - The Re-analyse button block appears exactly once in `QualityReportCard.tsx` (confirmed by grep before edit)
  - Footer uses a flex-wrap row that accommodates a fourth button without layout changes

  **Risks:**
  - If `onReanalyse` block appears more than once → grep in Pre-Read Gate catches it before edit.

  **Git Checkpoint:**
  ```bash
  git add src/components/analysis/QualityReportCard.tsx
  git commit -m "feat: add onCompare prop and Compare button to QualityReportCard"
  ```

  **Subtasks:**
  - [ ] 🟥 Add `onCompare?: () => void` to `QualityReportCardProps` interface
  - [ ] 🟥 Destructure `onCompare` in component function signature
  - [ ] 🟥 Add "Compare" button after "Re-analyse" in footer

  **✓ Verification Test:**

  **Type:** Unit (visual grep)

  **Action:**
  ```bash
  grep -n "onCompare\|Compare" src/components/analysis/QualityReportCard.tsx
  ```

  **Expected:**
  - `onCompare?: () => void;` appears in the interface
  - `onCompare,` appears in destructuring
  - `onClick={() => onCompare?.()}` appears in the JSX footer
  - `Re-analyse` still present — confirm with:
    ```bash
    grep -c "Re-analyse" src/components/analysis/QualityReportCard.tsx
    # Must return ≥ 1
    ```

  **Pass:** All four items above confirmed.

  **Fail:**
  - If `onCompare` missing from interface → Edit 1 was not applied → re-read file and reapply
  - If `Re-analyse` button missing → wrong block was replaced → check git diff and restore

---

### Phase 2 — Wire handler in AnalysisTimeline

**Goal:** When the user clicks "Compare" in the report, the browser navigates to `/compare?sessionA={sessionId}`.

---

- [ ] 🟥 **Step 2: Add `useRouter` + `handleCompare` to `AnalysisTimeline` and pass to `QualityReportCard`** — *Non-critical: additive change to a single file*

  **Step Architecture Thinking:**

  **Pattern applied:** Handler ownership at the scope that has the data. `AnalysisTimeline` has `sessionId` (the data needed to build the URL). It is the correct and minimal place to own the navigate callback rather than drilling through `AnalysisPage`.

  **Why this step exists after Step 1:**
  Step 1 defined `onCompare` as a valid prop on `QualityReportCard`. Without Step 1 complete, TypeScript will reject the prop passed in this step.

  **Why this file is the right location:**
  `AnalysisTimeline` already holds `sessionId` as a prop and renders `QualityReportCard`. It is the lowest common ancestor that has both the data (`sessionId`) and the render target (`QualityReportCard`). No additional prop drilling required.

  **Alternative approach considered and rejected:**
  Bubble `onCompare` up to `AnalysisPage` and pass `handleCompare` down through `AnalysisTimeline`. Rejected because it adds a prop to `AnalysisTimeline`'s public interface unnecessarily — `AnalysisPage` does not need to know about compare navigation; that is a concern of the timeline + report view.

  **What breaks if this step deviates:**
  If `sessionId` is not URL-encoded in the `router.push` call, session IDs containing special characters (e.g., slashes, spaces) will produce a malformed URL.

  ---

  **Idempotent:** Yes — adding an import and a callback to a component is safe to re-apply.

  **Context:** `AnalysisTimeline` renders `QualityReportCard` at line ~279 with `onReanalyse` but not `onCompare`. This step adds the missing wiring.

  **Pre-Read Gate:**
  Before any edit:
  - Run `grep -n "useRouter\|from 'next/navigation'" src/components/analysis/AnalysisTimeline.tsx`
    Must return 0 matches (not yet imported). If already present → skip the import edit only.
  - Run `grep -n "QualityReportCard" src/components/analysis/AnalysisTimeline.tsx`
    Must return exactly 1 match (the JSX call site). If 0 or 2+ → STOP.
  - Run `grep -n "onCompare" src/components/analysis/AnalysisTimeline.tsx`
    Must return 0 matches. If already present → STOP, already done.
  - Run `grep -n "const \[phase, setPhase\]" src/components/analysis/AnalysisTimeline.tsx`
    Must return exactly 1 match. Copy the verbatim line (including any alignment spaces) — this is the anchor for Edit 2. If 0 matches → STOP.

  **Self-Contained Rule:** All code below is complete and runnable.

  **No-Placeholder Rule:** No `<VALUE>` tokens below.

  ---

  **Edit 1 — Add `useRouter` import**

  Find (exact line in AnalysisTimeline.tsx):
  ```ts
  import { useState, useEffect, useRef } from "react";
  ```
  Replace with:
  ```ts
  import { useState, useEffect, useRef, useCallback } from "react";
  import { useRouter } from "next/navigation";
  ```

  **Edit 2 — Add `handleCompare` callback in the component body**

  Find this exact two-line block (verbatim — 2-space function-body indentation, plus the column-alignment spaces; confirmed by Pre-Read Gate grep):
  ```ts
  const [phase, setPhase]           = useState<Phase>("streaming");
  const [progress, setProgress]     = useState(0);
  ```
  Replace with:
  ```ts
  const router = useRouter();
  const handleCompare = useCallback(() => {
    router.push(`/compare?sessionA=${encodeURIComponent(sessionId)}`);
  }, [router, sessionId]);

  const [phase, setPhase]           = useState<Phase>("streaming");
  const [progress, setProgress]     = useState(0);
  ```

  > ⚠️ The code above shows the literal file content without markdown list indentation. Each line begins with 2 spaces (the function body indent), then the column-aligned variable names. If the Edit tool fails to find the anchor, re-run the Pre-Read Gate grep, copy the exact output verbatim, and use that as the old_string.

  **Edit 3 — Pass `onCompare` to `QualityReportCard`**

  Find the exact `QualityReportCard` JSX block:
  ```tsx
            <QualityReportCard
              report={report}
              welderDisplayName={welderDisplayName}
              onReanalyse={onReanalyse}
            />
  ```
  Replace with:
  ```tsx
            <QualityReportCard
              report={report}
              welderDisplayName={welderDisplayName}
              onReanalyse={onReanalyse}
              onCompare={handleCompare}
            />
  ```

  **What it does:** Imports `useRouter`, creates a stable `handleCompare` callback that pushes `/compare?sessionA={sessionId}`, and passes it to `QualityReportCard`. When the user clicks "Compare", the browser navigates to the compare landing form pre-filled with the current session.

  **Why this approach:** `useCallback` with `[router, sessionId]` deps matches the existing `onReanalyse` memo pattern in the file and avoids unnecessary re-renders.

  **Assumptions:**
  - `sessionId` prop is stable (it is — it's a plain string from the parent)
  - `phase` state variable exists at module scope of `AnalysisTimeline` (confirmed by pre-read grep)

  **Risks:**
  - `useCallback` is confirmed absent from `AnalysisTimeline.tsx` line 16 (`import { useState, useEffect, useRef } from "react"`). Edit 1 replacement is unconditional — no conditional branch needed.

  **Git Checkpoint:**
  ```bash
  git add src/components/analysis/AnalysisTimeline.tsx
  git commit -m "feat: wire Compare button in AnalysisTimeline to /compare?sessionA"
  ```

  **Subtasks:**
  - [ ] 🟥 Add `useRouter` import from `next/navigation`
  - [ ] 🟥 Add `handleCompare` callback using `router.push`
  - [ ] 🟥 Pass `onCompare={handleCompare}` to `QualityReportCard`

  **✓ Verification Test:**

  **Type:** Integration (dev server)

  **Action:**
  1. `npm run dev`
  2. Navigate to `http://localhost:3000/analysis`
  3. Click any session in the left panel
  4. Wait for the AI report to complete (or use a cached report)
  5. Click "Compare" in the report footer

  **Expected:**
  - Browser navigates to `/compare?sessionA={the_session_id}`
  - The compare landing form has Session A pre-filled with that session ID
  - Session B input is empty (user picks it)

  **Pass:** Compare landing form loads with Session A pre-filled.

  **Fail:**
  - "Compare" button stays grey / disabled → `onCompare` prop not passed → check Edit 3 was applied
  - Button is not visible → Step 1 Edit 3 not applied → grep `QualityReportCard.tsx` for "Compare"
  - Navigation goes to wrong URL → check `handleCompare` URL string in Edit 2

---

## Regression Guard

**Systems at risk:**
- `QualityReportCard` — existing consumers (tests, storybook if any) render without `onCompare`; button must stay disabled/greyed, not throw

**Regression verification:**

| System | Pre-change behaviour | Post-change verification |
|--------|---------------------|--------------------------|
| QualityReportCard render without `onCompare` | Renders with 3 footer buttons | Still renders with 3 buttons + 1 greyed "Compare" |
| Re-analyse button | Works unchanged | Still calls `onReanalyse` — confirm by grep that old block untouched |
| Existing test suite | 695 total, 27 pre-existing failures | Run `npx jest --no-coverage` — count must not decrease below 668 passing |

**Test count regression check:**
```bash
npx jest --no-coverage 2>&1 | tail -3
# Must show ≥ 668 passing tests
```

---

## Rollback Procedure

```bash
git revert HEAD     # reverts Step 2 (AnalysisTimeline)
git revert HEAD~1   # reverts Step 1 (QualityReportCard)

# Confirm:
npx jest --no-coverage 2>&1 | tail -3
# Must show same passing count as pre-flight baseline
```

---

## Success Criteria

| Feature | Target | Verification |
|---------|--------|--------------|
| "Compare" button visible in report | Appears in footer after analysis completes | **Do:** open analysis page, select session, wait for report → **Expect:** "Compare" button in footer alongside "Export PDF", "Copy Session ID", "Re-analyse" |
| Compare navigation pre-fills sessionA | `/compare?sessionA={id}` in address bar | **Do:** click "Compare" → **Expect:** compare landing loads with Session A input pre-filled |
| Disabled when no handler | Button greyed out | **Do:** render `<QualityReportCard report={…} />` without `onCompare` → **Expect:** button has `disabled` attribute and `opacity-30` |
| No regression | Existing buttons unchanged | **Do:** `grep -n "Re-analyse\|Export PDF\|Copy Session ID" QualityReportCard.tsx` → **Expect:** all three still present |
| Test count | ≥ 668 passing | `npx jest --no-coverage` |

---

⚠️ **Do not mark a step 🟩 Done until its verification test passes.**
⚠️ **Do not proceed past a Human Gate without explicit human input.**
⚠️ **Step 2 Edit 2 anchor must include alignment spaces exactly as they appear in the file — use the verbatim output from the Pre-Read Gate grep, not a normalised version.**
⚠️ **URL-encode `sessionId` in the `router.push` call — session IDs may contain special characters.**
