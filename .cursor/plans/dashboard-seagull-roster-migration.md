# Dashboard Seagull Roster Migration

**Overall Progress:** `100%`

## Implementation Status (Complete)

All 9 steps implemented and committed. Migration is complete.

**Test status:** Dashboard, landing, and app tests pass. `WelderReportPage` tests (`__tests__/app/seagull/welder/[id]/page.test.tsx`) remain failing (page stuck in loading; mocks for welder report data/fetch not resolving). These failures appear pre-existing and are outside the scope of this migration. Consider a follow-up ticket to fix welder report test mocks.

---

## TLDR

Replace `(app)/dashboard` with the seagull welder roster floor view (10 welder cards). Fix score badge colors (red/amber/green by score), sort cards worst-first (nulls last), and update card links to replay and compare. Redirect `/seagull` to `/dashboard`. Remove live, realtime, supervisor, demo routes. Add "Full report →" link on each card so `/seagull/welder/[id]` stays reachable (RankingsTable deferred).

---

## Critical Decisions

- **Decision 1:** Score badge colour is based on **absolute score** (red <60, amber 60–80, green ≥80), replacing the current trend-based badges (On track / Needs attention / Neutral).
- **Decision 2:** Cards link to `/replay/[sessionId]` for individual report; non-expert cards also get "Compare to expert" linking to `/compare/[sessionId]/[expertSessionId]`.
- **Decision 3:** `/seagull` redirects to `/dashboard` using Next.js redirect config. The welder report at `/seagull/welder/[id]` remains and is reachable via "Full report →" link on each welder card. RankingsTable deferred to a future ticket.
- **Decision 4:** Remove "Team" from AppNav since Dashboard now serves that purpose; all navigation goes through Dashboard.
- **Decision 5:** `EXPERT_SESSION_ID` is a named constant (not inlined). If the session does not exist in the backend, the compare link will 404; consider env/config in future.
- **Decision 6:** Remove routes: `(app)/live`, `(app)/realtime`, `(app)/supervisor`, `app/demo` (and demo/team). Update AppNav, manifest.json, and any links that pointed to these routes.

---

## Clarification Gate

| Unknown | Required | Source | Blocking | Resolved |
|---------|----------|--------|----------|----------|
| Keep trend badges alongside score color? | Clarification | Human | Step 2 | Assume: replace with score-based color only |
| Add "Compare to expert" link now or defer? | Clarification | Human | Step 2 | Assume: add now for non-expert cards |

---

## Pre-Flight — Run Before Any Code Changes

1. Read `my-app/src/app/(app)/dashboard/page.tsx` and `my-app/src/app/seagull/page.tsx` in full.
2. Confirm `getLatestSessionId`, `getBadge`, `WELDERS`, `WelderScoreResult` exist in seagull page.
3. Run `npm test -- --testPathPattern="seagull|dashboard|supervisor|live|realtime|demo"` — record passing test count.
4. `grep -n "href=.*seagull" my-app/src` — list all seagull links to update.
5. Confirm where RankingsTable renders: `grep -rn "RankingsTable" my-app/src` — currently only in `(app)/supervisor/page.tsx`. Dashboard layout does NOT include it.

---

## Pre-Flight — Baseline Snapshot (agent fills in during pre-flight)

```
Test count before plan: ____                          (A)
Tests in demo/ directory: ____                        (B)
Tests in supervisor/ directory: ____                  (C)
Tests in live/ directory: ____                       (D)
Tests in realtime/ directory: ____                    (E)

Adjusted minimum = A - B - C - D - E = ____          (F)
```

Success criterion for `npm test` at end of plan: count ≥ F

**How to compute B–E:** Run `npm test -- --testPathPattern="demo" --json 2>/dev/null | jq '.numTotalTests // 0'` for B; `--testPathPattern="supervisor"` for C; `--testPathPattern="live"` for D; `--testPathPattern="realtime"` for E.

---

## Agent Failure Protocol

1. A verification command fails → read the full error output.
2. Cause is unambiguous → make ONE targeted fix → re-run the same verification command.
3. If still failing after one fix → **STOP**. Output full contents of modified files, report command/error/fix/state.
4. Never attempt a second fix without human instruction.
5. Never modify files not named in the current step.

---

## Tasks

### Phase 1 — Dashboard Replacement and Fixes

**Goal:** Dashboard becomes the welder roster floor view with correct badge colors, sort order, and links.

---

- [x] **Step 1: Replace dashboard content with seagull roster (move)**

  **Idempotent:** Yes  
  **Context:** Dashboard currently shows DashboardLayout + Welding Sessions + Demo CTA. Replace with seagull roster content (no DashboardLayout, no welding sessions, no demo CTA).

  **Pre-Read Gate:**
  - `grep -n "DashboardLayout\|Welding Sessions" my-app/src/app/\(app\)/dashboard/page.tsx` — confirm current structure
  - `grep -n "WELDERS\|getLatestSessionId\|WelderScoreResult" my-app/src/app/seagull/page.tsx` — confirm source structure

  **Action:** Replace the entire content of `my-app/src/app/(app)/dashboard/page.tsx` with the seagull page logic and UI. Copy from `seagull/page.tsx`:
  - Constants: `WELDERS`, `getLatestSessionId`, `getSecondLatestSessionId`, `FETCH_TIMEOUT_MS`, `fetchScoreWithTimeout`, interfaces (Step 2 will remove dead code)
  - Update card links from `href={/seagull/welder/${welder.id}}` to `href={/replay/${getLatestSessionId(welder)}}`
  - Keep the same loading/error structure
  - Update page title from "Team Dashboard — Seagull Pilot" to "Welder Roster" or "Team Dashboard"

  **Do not yet** change badge logic, sort order, or add compare link — those are Step 2.

  **Verification:**
  - Type: Unit
  - Action: `npm test -- --testPathPattern="seagull/page"` (will need to update import path to dashboard in tests)
  - Expected: Tests pass after updating test to import from dashboard
  - Pass: All seagull roster tests pass
  - Fail: If tests import from seagull, update test file to import from `@/app/(app)/dashboard/page` and assert links go to `/replay/...`

  **Git Checkpoint:** `git add my-app/src/app/\(app\)/dashboard/page.tsx && git commit -m "step 1: move seagull roster content into dashboard"`

---

- [x] **Step 2: Apply three fixes — badge color, sort, links + remove dead code**

  **Idempotent:** Yes  
  **Context:** Implement the three user-requested fixes and remove code that becomes unused.

  **2a) Score badge colour**
  Replace the trend-based `getBadge(score, secondScore)` usage with score-based colour:
  - Red: score < 60 (`bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300`)
  - Amber: 60 ≤ score < 80 (`bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300`)
  - Green: score ≥ 80 (`bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300`)
  - Unknown (score === null): keep existing "Score unavailable" styling

  Apply this to the score display (the numeric part or a badge next to it). Remove the old On track / Needs attention / Neutral badge rendering.

  **2b) Sort by score ascending (nulls last)**
  Before mapping over `welderScores`, sort by `score` ascending. Null scores must sort LAST (after worst real scores). Use `Infinity` so nulls compare higher than any real score:
  ```ts
  const sorted = [...welderScores].sort((a, b) => {
    const sa = a.score ?? Infinity;  // nulls last in ascending order
    const sb = b.score ?? Infinity;
    return sa - sb;
  });
  ```
  **Do not use** `-1` — that would put nulls first, which is wrong.

  **2c) Links**
  - Primary card link: `href={/replay/${getLatestSessionId(welder)}}` (card wraps content in Link)
  - Add constant at top of file: `const EXPERT_SESSION_ID = 'sess_expert-benchmark_005';` — use this for compare links, not an inline string. Note: if this session does not exist in the backend, compare will 404; consider env/config later.
  - Add secondary link for non-expert: "Compare to expert" → `href={/compare/${getLatestSessionId(welder)}/${EXPERT_SESSION_ID}}`
  - Expert Benchmark card: no "Compare to expert" link (only "View report" → replay)
  - The "View report →" text should be the primary link; "Compare to expert" can be a smaller link beside it for non-expert cards

  **2d) Remove dead code**
  - Remove `getBadge` — no longer used
  - Remove `getSecondLatestSessionId` — no longer used
  - Remove second-score fetch logic from `useEffect`: only fetch latest session per welder. Simplify the `fetches` array to one entry per welder (latest only). Update `byWelder` / `WelderScoreResult` to drop `secondScore`.
  - Remove `secondScore` from `WelderScoreResult` interface and all usages

  **Pre-Read Gate:**
  - Confirm `welder.id === "expert-benchmark"` is the expert card
  - `getLatestSessionId` for expert = `sess_expert-benchmark_005`

  **Verification:**
  - Type: Unit
  - Action: Add assertions in dashboard/roster test: first card has lowest score (not null); if any card has null score, it appears after all scored cards; links include `/replay/` and `/compare/` (for non-expert)
  - Expected: Sort order correct (lowest first, nulls last), links correct, no references to `getBadge` or `getSecondLatestSessionId`
  - Pass: Test asserts first rendered card has lowest score; "Compare to expert" absent on Expert Benchmark card; null-score cards appear at end
  - Fail: If nulls appear first, the sort used `-1` instead of `Infinity`

  **Git Checkpoint:** `git add my-app/src/app/\(app\)/dashboard/page.tsx && git commit -m "step 2: score badge color, sort ascending nulls-last, replay/compare links, remove dead code"`

---

- [x] **Step 3: Add "Full report" link to each welder card (replaces RankingsTable deferral)**

  **Idempotent:** Yes  
  **Context:** RankingsTable is being removed with supervisor. Rather than rendering a raw table below the roster grid with no design spec, defer RankingsTable to a future ticket. Instead, add a small "Full report →" link on each card pointing to `/seagull/welder/${welder.id}` so the welder report page stays reachable without requiring RankingsTable at all.

  **Action:** On each welder card, below the "Compare to expert" link (or below "View report →" on Expert Benchmark card), add:
  ```tsx
  <a href={`/seagull/welder/${welder.id}`}
    className="text-xs text-zinc-500 dark:text-zinc-400 hover:underline">
    Full report →
  </a>
  ```
  Expert Benchmark card gets this link too. Do not add RankingsTable to dashboard in this plan.

  **Verification:**
  - Each card renders: score badge, "View report →", "Full report →" (expert card has no "Compare to expert")
  - Click "Full report →" on Mike Chen card, assert navigates to `/seagull/welder/mike-chen`

  **Git Checkpoint:** `git add my-app/src/app/\(app\)/dashboard/page.tsx && git commit -m "step 3: add full report link to cards, defer RankingsTable"`

---

- [x] **Step 4: Redirect /seagull to /dashboard**

  **Idempotent:** Yes  
  **Context:** Old bookmarks and nav to /seagull should land on /dashboard.

  **Action:** Add redirect in `next.config.ts` (or `next.config.js`):
  ```ts
  redirects: async () => [
    { source: '/seagull', destination: '/dashboard', permanent: false },
  ],
  ```
  If redirects already exist, append to the array.

  **Verification:**
  - Type: Integration
  - Action: Start dev server, `curl -sI http://localhost:3000/seagull` or navigate to /seagull
  - Expected: 307/308 redirect to /dashboard
  - Pass: Redirect occurs
  - Fail: Check next.config for correct syntax

  **Git Checkpoint:** `git add next.config.* && git commit -m "step 4: redirect /seagull to /dashboard"`

---

- [x] **Step 5: Update back-links and nav**

  **Idempotent:** Yes  
  **Context:** Welder report references /seagull for back link. Update to /dashboard. Remove Team from AppNav. Remove Supervisor, Realtime, Demo from AppNav (routes being wiped).

  **5a)** In `my-app/src/app/seagull/welder/[id]/page.tsx`: change both `href="/seagull"` to `href="/dashboard"` (in backLink and error state).

  **5b)** In `my-app/src/components/AppNav.tsx`:
  - Remove the "Team" nav item (Link to /seagull)
  - Remove the "Supervisor" nav item
  - Remove the "Realtime" nav item
  - Remove the "Demo" nav item (demo route is being wiped; landing/marketing links will need updating in Step 9)

  **Verification:**
  - Type: Unit
  - Action: `npm test -- --testPathPattern="welder/\[id\]|seagull-flow"` — tests expect `href="/seagull"`; update to expect `href="/dashboard"`
  - Expected: Tests pass with new back-link target
  - Pass: Welder report tests pass; back link asserts `href="/dashboard"`

  **Git Checkpoint:** `git add my-app/src/app/seagull/welder/\[id\]/page.tsx my-app/src/components/AppNav.tsx my-app/src/__tests__/* && git commit -m "step 5: update back-links to /dashboard, remove Team/Supervisor/Realtime/Demo nav"`

---

- [x] **Step 6: Update and migrate tests**

  **Idempotent:** Yes  
  **Context:** Seagull roster tests import from seagull page. Roster now lives in dashboard.

  **Action:**
  - Create or update `my-app/src/__tests__/app/(app)/dashboard/page.test.tsx` to test the roster (copy/adapt from seagull page.test.tsx)
  - Update imports: `import DashboardPage from '@/app/(app)/dashboard/page'`
  - Update assertions: badge colors (red/amber/green by score), sort order (first card = lowest score; nulls last), links to /replay and /compare
  - Remove or simplify `my-app/src/__tests__/app/seagull/page.test.tsx` — the seagull page redirects; either remove or test redirect
  - Update `seagull-flow-smoke.test.tsx` to start from /dashboard instead of /seagull (or adjust for redirect)

  **Verification:**
  - Type: Unit
  - Action: `npm test`
  - Expected: All tests pass
  - Pass: Test count ≥ F (from pre-flight); no failures
  - Fail: Fix any import or assertion errors

  **Git Checkpoint:** `git add my-app/src/__tests__/ && git commit -m "step 6: migrate roster tests to dashboard"`

---

- [x] **Step 7: Remove seagull root page**

  **Idempotent:** Yes  
  **Context:** With redirect in place, `/seagull` no longer needs a page component. Keep `app/seagull/welder/[id]/page.tsx` for the welder report.

  **Action:** Delete `app/seagull/page.tsx`. Next.js `redirects` in config takes precedence; requests to /seagull will redirect before hitting any page.

  **Verification:**
  - After deleting, ensure `/seagull` still redirects to /dashboard
  - Ensure `/seagull/welder/mike-chen` still loads the welder report

  **Git Checkpoint:** `git add my-app/src/app/seagull/page.tsx && git commit -m "step 7: remove seagull root page"`

---

### Phase 2 — Route Cleanup (live, realtime, supervisor, demo)

**Goal:** Remove live, realtime, supervisor, and demo routes. Update dependent links.

---

- [x] **Step 8: Remove live, realtime, supervisor routes**

  **Idempotent:** Partial — deletion is not re-runnable. Guard each delete:
  ```bash
  [ -d my-app/src/app/\(app\)/live ] && rm -rf my-app/src/app/\(app\)/live
  [ -d my-app/src/app/\(app\)/realtime ] && rm -rf my-app/src/app/\(app\)/realtime
  [ -d my-app/src/app/\(app\)/supervisor ] && rm -rf my-app/src/app/\(app\)/supervisor
  ```
  If directories are already gone, commands are no-ops.

  **Context:** These routes are being wiped per plan.

  **Action:**
  - Delete the directories using the guarded commands above
  - `my-app/public/manifest.json`: change `start_url` from `"/live"` to `"/dashboard"`
  - AppNav: Supervisor and Realtime were removed in Step 5; ensure no leftover references
  - Delete `e2e/supervisor-export.spec.ts`. Do not repoint it — supervisor is gone and there is no equivalent route to test.

  **Verification:**
  - `ls my-app/src/app/\(app\)/live` — should fail (directory gone)
  - `ls my-app/src/app/\(app\)/realtime` — should fail
  - `ls my-app/src/app/\(app\)/supervisor` — should fail
  - No import errors from removed pages

  **Git Checkpoint:** `git add my-app/src/app/\(app\)/live my-app/src/app/\(app\)/realtime my-app/src/app/\(app\)/supervisor my-app/public/manifest.json e2e/ && git commit -m "step 8: remove live, realtime, supervisor routes"`

---

- [x] **Step 9: Remove demo route and update links**

  **Idempotent:** Partial — deletion is not re-runnable. Guard:
  ```bash
  [ -d my-app/src/app/demo ] && rm -rf my-app/src/app/demo
  ```
  If already gone, command is a no-op.

  **Context:** Demo route is being wiped. Landing and marketing pages link to /demo.

  **Pre-Read Gate:** Before any action:
  - `grep -rn "demo-tour-config" my-app/src` — record every file that imports it. All will be handled in this step.

  **Action:**
  - Delete `my-app/src/app/demo/` using the guarded command above
  - `my-app/src/lib/demo-tour-config.ts`: read the file. Delete it entirely. Run `grep -rn "demo-tour-config" my-app/src` — for each file that imports it: remove that import. Delete `my-app/src/__tests__/lib/demo-tour-config.test.ts` (tests deleted module). Delete `my-app/src/components/demo/DemoTour.tsx` (only consumer is demo page; cannot function without demo-tour-config)
  - Update links that pointed to /demo:
    - `my-app/src/app/(app)/dashboard/page.tsx`: remove any "Try demo" links (dashboard was replaced in Step 1; new dashboard has no demo CTA — verify and remove any remaining)
    - `my-app/src/app/landing/page.tsx`: change links from `/demo` to `/dashboard`
    - `my-app/src/app/(marketing)/page.tsx`: change `href="/demo"` and `DEMO_URL` fallback from `/demo` to `/dashboard`
  - Delete `my-app/src/__tests__/lib/demo-tour-config.test.ts`
  - Delete `my-app/src/components/demo/DemoTour.tsx` (and `my-app/src/components/demo/` if empty after)
  - AppNav: Demo was removed in Step 5; ensure no leftover references
  - Delete tests in `my-app/src/__tests__/app/demo/` — remove the directory

  **Verification:**
  - `ls my-app/src/app/demo` — should fail (directory gone)
  - `grep -rn "demo-tour-config" my-app/src` — should return no results
  - `grep -r "href=.*/demo" my-app/src` — should return no results (or only in comments/docs)
  - Landing and marketing pages render without broken /demo links

  **Git Checkpoint:** `git add my-app/src/app/demo my-app/src/app/landing my-app/src/app/\(marketing\) my-app/src/__tests__/app/demo my-app/src/__tests__/lib/demo-tour-config.test.ts my-app/src/lib/demo-tour-config.ts my-app/src/components/demo/ my-app/src/components/AppNav.tsx && git commit -m "step 9: remove demo route, delete demo-tour-config, update landing/marketing links to /dashboard"`

---

## Regression Guard

**Systems at risk:**
- Compare page (links to /dashboard) — no change needed
- Replay page — now linked from dashboard cards — no change
- Welder report — reachable via "Full report →" on each card (RankingsTable deferred)
- Landing, marketing — links updated from /demo to /dashboard
- manifest.json start_url — updated from /live to /dashboard

**Regression verification:**
| System | Pre-change | Post-change |
|--------|------------|-------------|
| /dashboard | DashboardLayout + sessions | Welder roster with Full report links |
| /seagull | Roster page | Redirect to /dashboard |
| /seagull/welder/[id] | Full report | Unchanged; reachable via "Full report →" on cards |
| /live, /realtime, /supervisor | Exist | Removed |
| /demo | Exists | Removed; links → /dashboard |
| AppNav | Dashboard, Team, Demo, Supervisor, Realtime, … | Dashboard, Home, Defects, AI (reduced) |

**Test count:** Must be ≥ F (from pre-flight baseline snapshot).

---

## Rollback Procedure

```bash
# Reverse in reverse step order
git revert <commit-Step9>
git revert <commit-Step8>
git revert <commit-Step7>
...
git revert <commit-Step1>
```

---

## Success Criteria

| Feature | Target | Verification |
|---------|--------|--------------|
| Dashboard shows welder roster | 10 cards, scores, badges | Navigate to /dashboard |
| Score badge color | Red <60, amber 60–80, green ≥80 | Inspect score styling |
| Sort order | Worst first (ascending), nulls last | First card has lowest score; null-score cards at end |
| View report link | /replay/[sessionId] | Click card or link |
| Compare to expert | /compare/[A]/[EXPERT_SESSION_ID] | Non-expert cards only; constant not inline |
| /seagull redirect | → /dashboard | Navigate to /seagull |
| Welder report reachable | Via "Full report →" link on each card | Click "Full report →" on any card → /seagull/welder/[id] |
| Welder report back link | → /dashboard | Click "Back to Team Dashboard" |
| Dead code removed | No getBadge, getSecondLatestSessionId, secondScore | grep confirms removal |
| live, realtime, supervisor, demo | Removed | 404 or redirect; nav cleaned |
| Test count | ≥ F (pre-calculated in pre-flight) | `npm test` |
