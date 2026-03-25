# Plan: MVP Believability — Pareto 80/20

**Overall Progress:** `0%` (0 / 3 steps done)

---

## TLDR

Three surgical changes that together make the product look production-ready: (1) wire the already-built PDF export so the "Export PDF" button actually works — infrastructure was 100% complete, only the `handleExportPdf` stub needed replacing; (2) add a live KPI strip (Sessions Analysed / Pass Rate / Rework Caught) above the analysis view, computed from sessions already in state — zero new API calls; (3) add per-action checkboxes with an "All actions reviewed" banner to the corrective actions list — turns the read-only report into an operational tool. No new packages. No auth. No backend changes.

---

## Architecture Overview

**The problem this plan solves:**
- `QualityReportCard.tsx` line 193: `handleExportPdf` is a no-op placeholder that logs a warning. The complete PDF pipeline (template, API route, chart capture util) is implemented but not wired.
- `analysis/page.tsx`: sessions are fetched but their aggregate metrics (pass rate, rework count) are never surfaced — the page shows no business numbers.
- `QualityReportCard.tsx` lines 242–246: corrective actions are a static read-only list with no way to acknowledge them.

**The pattern(s) applied:**
- *Facade*: `handleExportPdf` becomes a thin orchestrator — capture chart → build payload → POST → download blob. Each substep is already implemented; the handler just calls them in sequence.
- *Derived state*: KPI numbers (`passRate`, `reworkCount`) are computed inline from `allSessions` array — no extra API, no context, no memoization needed at MVP scale.
- *Local UI state*: `acknowledged: Set<number>` is transient React state. Resets on session change (component remounts via `key={viewState.sessionId}` in parent). No persistence needed for MVP.

**What stays unchanged:**
- `src/components/pdf/WelderReportPDF.tsx` — PDF template, untouched.
- `src/app/api/welder-report-pdf/route.ts` — API route, untouched.
- `src/lib/pdf-chart-capture.ts` — chart capture util, untouched (read-only dependency).
- `src/components/analysis/WelderTrendChart.tsx` — chart component, untouched. ID wrapper added in parent.
- `src/components/analysis/SessionList.tsx` — session list, untouched.
- `src/components/analysis/AnalysisTimeline.tsx` — streaming timeline, untouched.

**What this plan adds:**
- `analysis/page.tsx`: `allSessions` state + `useEffect` fetch + 3 KPI computed vars + KPI strip JSX + `id="welder-trend-chart"` wrapper around `WelderTrendChart`.
- `QualityReportCard.tsx`: `isPdfLoading` state + `acknowledged` state + real `handleExportPdf` async impl + updated Export PDF button + updated corrective actions list with checkboxes + "All actions reviewed" banner.

**Critical decisions:**

| Decision | Alternative considered | Why alternative rejected |
|----------|----------------------|--------------------------|
| Add `id` wrapper div in `analysis/page.tsx` | Add `id` prop to `WelderTrendChart` component | Avoids touching `WelderTrendChart`; wrapper div is zero-logic |
| KPI computed inline in render | Memoize with `useMemo` | Unnecessary for MVP scale; 3 simple filters on ≤100 sessions |
| `acknowledged` as `Set<number>` in `useState` | localStorage persistence | MVP only; state resets correctly on session change via parent `key` |
| Derive score from `report.disposition` | Expect a numeric `quality_score` on `WarpReport` | `WarpReport` has no direct `quality_score` field; disposition is the authoritative signal |
| Separate `allSessions` fetch in page | Lift state up from `SessionList` | `SessionList` fetches internally and doesn't expose its data; adding a parallel fetch is simpler than refactoring `SessionList` |

**Known limitations:**

| Limitation | Why acceptable now | Upgrade path |
|-----------|-------------------|--------------|
| Chart capture may snapshot "Loading trend…" text if chart hasn't rendered | PDF still generates; user can re-click once chart loads | Pass `chartDataUrl` as optional — API already handles null gracefully |
| `acknowledged` state lost on page refresh | MVP demo doesn't need persistence | Store in `localStorage` keyed by `session_id` |
| KPI strip uses all sessions ever loaded, not a time-filtered window | Sufficient for demo — numbers grow meaningfully | Add date filter UI when needed |

---

## Clarification Gate

All unknowns resolved from codebase reads. No human input required.

| Unknown | Required | Source | Resolved |
|---------|----------|--------|----------|
| WelderTrendChart DOM id | None exists — must add wrapper | Codebase read | ✅ |
| WarpReport score field | No `quality_score`; derive from `disposition` (PASS=1.0, CONDITIONAL=0.5, REWORK_REQUIRED=0.0) | Codebase read | ✅ |
| `fetchMockSessions` already imported in `analysis/page.tsx` | Yes — line 24 | Codebase read | ✅ |
| `logWarn` still used after placeholder removal | Yes — kept for error logging in new impl | Codebase read | ✅ |
| `handleExportPdf` dependency array | `[isPdfLoading, report, welderDisplayName]` | Codebase read | ✅ |
| `<ol>` classes compatible with flex `<li>` children | `list-decimal list-inside` breaks with flex children — must drop in replacement | CSS analysis | ✅ |

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
# 1. Confirm handleExportPdf placeholder exists (anchor for Step 1)
grep -n "Export PDF not implemented" src/components/analysis/QualityReportCard.tsx

# 2. Confirm corrective actions list anchor (anchor for Step 3)
grep -n "list-decimal list-inside" src/components/analysis/QualityReportCard.tsx

# 3. Confirm WelderTrendChart render site (anchor for Step 1 chart wrapper)
grep -n "WelderTrendChart" src/app/\(app\)/analysis/page.tsx

# 4. Confirm isAnalysing state line (anchor for Step 2 state addition)
grep -n "isAnalysing" src/app/\(app\)/analysis/page.tsx

# 5. Confirm healthOk computed var (anchor for Step 2 KPI vars)
grep -n "healthOk" src/app/\(app\)/analysis/page.tsx

# 6. Baseline test count
npx jest --no-coverage 2>&1 | tail -3

# 7. Line counts
wc -l src/components/analysis/QualityReportCard.tsx src/app/\(app\)/analysis/page.tsx
```

**Baseline Snapshot (agent fills during pre-flight):**
```
Test count before plan:           ____
Line count QualityReportCard.tsx: 409
Line count analysis/page.tsx:     264
```

**Automated checks (all must pass before Step 1):**
- [ ] `grep "Export PDF not implemented" src/components/analysis/QualityReportCard.tsx` returns exactly 1 match
- [ ] `grep "list-decimal list-inside" src/components/analysis/QualityReportCard.tsx` returns exactly 1 match
- [ ] `grep "WelderTrendChart" src/app/(app)/analysis/page.tsx` returns at least 1 match
- [ ] `grep "isAnalysing" src/app/(app)/analysis/page.tsx` returns at least 1 match at the `useState` line
- [ ] `captureChartToBase64` does NOT yet exist in `QualityReportCard.tsx` (would indicate Step 1 already run)

---

## Environment Matrix

| Step | Dev | Notes |
|------|-----|-------|
| Step 1 | ✅ | Dev server must be running to test PDF download |
| Step 2 | ✅ | Sessions must be present in mock data for KPI strip to appear |
| Step 3 | ✅ | Requires a completed analysis to render corrective actions |

---

## Tasks

### Phase 1 — Wire PDF Export

**Goal:** Clicking "Export PDF" in `QualityReportCard` produces a downloadable `.pdf` file containing the welder's trend chart, root cause, corrective actions, and report metadata.

---

- [ ] 🟥 **Step 1: Wire PDF export** — *Critical: replaces placeholder stub with live async fetch + download; touches two files*

  **Step Architecture Thinking:**

  **Pattern applied:** Facade — `handleExportPdf` orchestrates three already-implemented subsystems (chart capture, API route, blob download) without owning any of their logic.

  **Why this step exists first in the sequence:**
  Steps 2 and 3 are independent. Step 1 is done first because it has the highest ROI (visible, tangible output) and the most edits.

  **Why these files are the right locations:**
  - `analysis/page.tsx`: owns the `WelderTrendChart` render site — the only place to add the `id` wrapper without touching the chart component.
  - `QualityReportCard.tsx`: owns the Export PDF button and `handleExportPdf` callback — the only place that has access to `report` and `welderDisplayName`.

  **Alternative approach considered and rejected:**
  Pass a `onExportPdf` callback prop from `AnalysisTimeline` down to `QualityReportCard`, allowing `AnalysisTimeline` to own the fetch — rejected because `QualityReportCard` already has direct access to all required fields (`report`, `welderDisplayName`) and adding an indirection layer adds prop drilling with no benefit.

  **What breaks if this step deviates:**
  If `isPdfLoading` is not in the `useCallback` dependency array, rapid double-clicks could fire two concurrent PDF requests. If the `id` wrapper is not added to `analysis/page.tsx`, `captureChartToBase64` returns `null` (element not found) — the PDF generates without a chart image, which is silent but suboptimal.

  ---

  **Idempotent:** Yes — re-running the edit produces the same result.

  **Context:** `handleExportPdf` at line 193 is a one-liner placeholder. The PDF API route, template, and chart capture util are all complete and tested. This step closes the wiring gap.

  ---

  ### Edit 1 — `analysis/page.tsx`: add `id` wrapper around `WelderTrendChart`

  **Pre-Read Gate:**
  - Run `grep -n "WelderTrendChart welderId" src/app/\(app\)/analysis/page.tsx`. Must return exactly 1 match. If 0 or 2+ → STOP.
  - Run `grep -n "welder-trend-chart" src/app/\(app\)/analysis/page.tsx`. Must return 0 matches. If 1+ → STOP (already done).

  **Anchor Uniqueness Check:**
  - Target: `            <WelderTrendChart welderId={selectedSession.welder_id} />`
  - Must appear exactly 1 time in the file.

  Find (verbatim — 12 leading spaces):
  ```tsx
          {selectedSession && (
            <WelderTrendChart welderId={selectedSession.welder_id} />
          )}
  ```
  Replace with:
  ```tsx
          {selectedSession && (
            <div id="welder-trend-chart">
              <WelderTrendChart welderId={selectedSession.welder_id} />
            </div>
          )}
  ```

  ---

  ### Edit 2 — `QualityReportCard.tsx`: add `captureChartToBase64` import

  **Pre-Read Gate:**
  - Run `grep -n "pdf-chart-capture" src/components/analysis/QualityReportCard.tsx`. Must return 0 matches. If 1+ → STOP (already done).
  - Run `grep -n 'from "@/lib/logger"' src/components/analysis/QualityReportCard.tsx`. Must return exactly 1 match.

  **Anchor Uniqueness Check:**
  - Target: `import { logWarn } from "@/lib/logger";`
  - Must appear exactly 1 time in the file.

  Find (verbatim):
  ```ts
  import { logWarn } from "@/lib/logger";
  ```
  Replace with:
  ```ts
  import { logWarn } from "@/lib/logger";
  import { captureChartToBase64 } from "@/lib/pdf-chart-capture";
  ```

  ---

  ### Edit 3 — `QualityReportCard.tsx`: add `isPdfLoading` state

  **Pre-Read Gate:**
  - Run `grep -n "isPdfLoading" src/components/analysis/QualityReportCard.tsx`. Must return 0 matches. If 1+ → STOP (already done).
  - Run `grep -n "copyFeedback, setCopyFeedback" src/components/analysis/QualityReportCard.tsx`. Must return exactly 1 match.

  Find (verbatim — 2 leading spaces):
  ```ts
  const [copyFeedback, setCopyFeedback] = useState(false);
  ```
  Replace with:
  ```ts
  const [copyFeedback, setCopyFeedback] = useState(false);
  const [isPdfLoading, setIsPdfLoading] = useState(false);
  ```

  ---

  ### Edit 4 — `QualityReportCard.tsx`: replace `handleExportPdf` stub with real implementation

  **Pre-Read Gate:**
  - Run `grep -n "Export PDF not implemented" src/components/analysis/QualityReportCard.tsx`. Must return exactly 1 match. If 0 → STOP (already replaced).

  **Anchor Uniqueness Check:**
  - Target block starts with `  const handleExportPdf = useCallback(() => {`
  - Must appear exactly 1 time in the file.

  Find (verbatim — 2 leading spaces throughout):
  ```ts
  const handleExportPdf = useCallback(() => {
    // Phase UI-7 replaces this placeholder with a real export flow.
    logWarn("[QualityReportCard]", "Export PDF not implemented", { sessionId: report.session_id });
  }, [report.session_id]);
  ```
  Replace with:
  ```ts
  const handleExportPdf = useCallback(async () => {
    if (isPdfLoading) return;
    setIsPdfLoading(true);
    try {
      const chartDataUrl = await captureChartToBase64("welder-trend-chart");
      const scoreTotal =
        report.disposition === "PASS"         ? 1.0
        : report.disposition === "CONDITIONAL" ? 0.5
        : 0.0;
      const payload = {
        welder: { name: welderDisplayName ?? "Unknown" },
        score:  { total: scoreTotal },
        feedback: {
          summary: report.root_cause,
          feedback_items: report.corrective_actions.map((action, i) => ({
            message:  action,
            severity: i === 0 ? "high" : "medium",
          })),
        },
        narrative:   report.disposition_rationale.slice(0, 2000),
        chartDataUrl,
        sessionDate: new Date(report.report_timestamp).toLocaleDateString("en-GB"),
      };
      const res = await fetch("/api/welder-report-pdf", {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify(payload),
      });
      if (!res.ok) {
        logWarn("[QualityReportCard]", "PDF export failed", { status: res.status, sessionId: report.session_id });
        return;
      }
      const blob = await res.blob();
      const url  = URL.createObjectURL(blob);
      const a    = document.createElement("a");
      a.href     = url;
      a.download = `${report.session_id}-report.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      logWarn("[QualityReportCard]", "PDF export error", { error: String(err), sessionId: report.session_id });
    } finally {
      setIsPdfLoading(false);
    }
  }, [isPdfLoading, report, welderDisplayName]);
  ```

  ---

  ### Edit 5 — `QualityReportCard.tsx`: update Export PDF button

  **Pre-Read Gate:**
  - Run `grep -n "onClick={handleExportPdf}" src/components/analysis/QualityReportCard.tsx`. Must return exactly 1 match.

  Find (verbatim — 8 leading spaces):
  ```tsx
          <button
            type="button"
            onClick={handleExportPdf}
            className="font-mono text-[9px] uppercase tracking-widest px-2 py-0.5 border border-zinc-800 text-[var(--warp-text-muted)] hover:border-amber-400 hover:text-[var(--warp-amber)] transition-colors duration-100"
          >
            Export PDF
          </button>
  ```
  Replace with:
  ```tsx
          <button
            type="button"
            onClick={() => { void handleExportPdf(); }}
            disabled={isPdfLoading}
            className="font-mono text-[9px] uppercase tracking-widest px-2 py-0.5 border border-zinc-800 text-[var(--warp-text-muted)] hover:border-amber-400 hover:text-[var(--warp-amber)] transition-colors duration-100 disabled:opacity-30 disabled:cursor-not-allowed"
          >
            {isPdfLoading ? "Generating…" : "Export PDF"}
          </button>
  ```

  ---

  **What it does:** Clicking "Export PDF" captures the quality trend chart as a PNG, builds a typed POST body from the report fields, calls `/api/welder-report-pdf`, and triggers a browser file download of the returned PDF. The button shows "Generating…" and is disabled during the request to prevent double-clicks.

  **Why this approach:** All infrastructure was already built. The only gap was the orchestration in `handleExportPdf`. Five surgical edits close it with no new dependencies.

  **Assumptions:**
  - The `WelderTrendChart` has rendered (or is in loading state) before the user clicks "Export PDF" — if in loading state, `captureChartToBase64` returns a PNG of the loading skeleton, which the API accepts gracefully as `chartDataUrl`.
  - `fetch` is available (Next.js App Router, browser context — guaranteed).
  - The dev server is running when the button is clicked in testing.

  **Risks:**
  - API returns 413 (body too large) if chart PNG exceeds 2MB → mitigation: `pixelRatio: 2` in chart capture produces ~200–400KB for a 320px chart — well within 2MB limit.
  - `welderDisplayName` is `null` → API receives `{ name: "Unknown" }` → PDF renders "Unknown" as welder name. Acceptable for MVP.

  **Git Checkpoint:**
  ```bash
  git add src/app/\(app\)/analysis/page.tsx src/components/analysis/QualityReportCard.tsx
  git commit -m "feat: wire PDF export in QualityReportCard — chart capture + API call + blob download"
  ```

  **Subtasks:**
  - [ ] 🟥 Edit 1: add `id="welder-trend-chart"` wrapper in `analysis/page.tsx`
  - [ ] 🟥 Edit 2: add `captureChartToBase64` import in `QualityReportCard.tsx`
  - [ ] 🟥 Edit 3: add `isPdfLoading` state in `QualityReportCard.tsx`
  - [ ] 🟥 Edit 4: replace `handleExportPdf` stub with async impl in `QualityReportCard.tsx`
  - [ ] 🟥 Edit 5: update Export PDF button onClick + disabled + label in `QualityReportCard.tsx`

  **✓ Verification Test:**

  **Type:** E2E (dev server)

  **Action:**
  1. `npm run dev` (if not already running)
  2. Navigate to `http://localhost:3000/analysis`
  3. Select any session that has a completed analysis report
  4. Click "Export PDF" in the footer of the report card

  **Expected:**
  - Button changes to "Generating…" and is disabled during generation
  - Browser triggers a file download named `<sessionId>-report.pdf`
  - File opens as a valid PDF

  **Code assertions:**
  ```bash
  # Confirm placeholder is gone
  grep "Export PDF not implemented" src/components/analysis/QualityReportCard.tsx
  # Must return 0 matches

  # Confirm chart wrapper added
  grep "welder-trend-chart" src/app/\(app\)/analysis/page.tsx
  # Must return 1 match
  ```

  **Pass:** PDF file downloads and opens without error.

  **Fail:**
  - "Generating…" appears but no download → check browser DevTools Network tab for `/api/welder-report-pdf` response status; 400 = payload shape mismatch → re-read Edit 4 payload object
  - `captureChartToBase64` returns null → `id="welder-trend-chart"` wrapper not applied → re-check Edit 1

---

### Phase 2 — KPI Metrics Strip

**Goal:** A horizontal strip showing "Sessions Analysed / Pass Rate / Rework Caught" appears above the split view, computed from the loaded sessions list.

---

- [ ] 🟥 **Step 2: Add KPI strip to analysis page** — *Non-critical: additive UI computed from existing data*

  **Step Architecture Thinking:**

  **Pattern applied:** Derived state — three KPI numbers computed inline from `allSessions` array. No memoization, no new API calls, no new components.

  **Why this step exists after Step 1:**
  Fully independent. Placed here to keep Step 1 focused on the most impactful change.

  **Why this file is the right location:**
  `analysis/page.tsx` already calls `fetchMockSessions` inside `handleAnalyseAll`. A second `useEffect` on mount reuses the same call to populate a dedicated `allSessions` state for KPI computation.

  **Alternative approach considered and rejected:**
  Lift session state out of `SessionList` so the page can access it — rejected because `SessionList` fetches internally; refactoring it to accept/return data is a larger change than a parallel `fetchMockSessions` call.

  **What breaks if this step deviates:**
  If KPI vars are computed inside JSX (IIFE or inline expression) rather than before the return, TypeScript type narrowing inside JSX is limited and the code becomes unreadable. Computing before `return` is the correct pattern.

  ---

  **Idempotent:** Yes — re-running the edit produces the same result.

  ---

  ### Edit 1 — `analysis/page.tsx`: add `allSessions` state

  **Pre-Read Gate:**
  - Run `grep -n "allSessions" src/app/\(app\)/analysis/page.tsx`. Must return 0 matches. If 1+ → STOP (already done).
  - Run `grep -n "isAnalysing.*useState" src/app/\(app\)/analysis/page.tsx`. Must return exactly 1 match.

  Find (verbatim — 2 leading spaces, column-aligned):
  ```ts
  const [isAnalysing, setIsAnalysing]         = useState(false);
  ```
  Replace with:
  ```ts
  const [isAnalysing, setIsAnalysing]         = useState(false);
  const [allSessions, setAllSessions]         = useState<MockSession[]>([]);
  ```

  ---

  ### Edit 2 — `analysis/page.tsx`: add `useEffect` to fetch sessions on mount

  **Pre-Read Gate:**
  - Run `grep -n "HEALTH_POLL_MS" src/app/\(app\)/analysis/page.tsx`. Must return exactly 1 match (confirms the health effect anchor is unique).

  Find (verbatim — last 3 lines of the health poll `useEffect`, 6 leading spaces for `const id`, 6 for `return`, 4 for `}, [])`):
  ```ts
      const id = setInterval(() => void poll(), HEALTH_POLL_MS);
      return () => { cancelled = true; clearInterval(id); };
    }, []);
  ```
  Replace with:
  ```ts
      const id = setInterval(() => void poll(), HEALTH_POLL_MS);
      return () => { cancelled = true; clearInterval(id); };
    }, []);

  useEffect(() => {
    fetchMockSessions()
      .then(setAllSessions)
      .catch(() => {});
  }, []);
  ```

  ---

  ### Edit 3 — `analysis/page.tsx`: add KPI computed variables

  **Pre-Read Gate:**
  - Run `grep -n "healthOk" src/app/\(app\)/analysis/page.tsx`. Must return at least 1 match at the `const healthOk =` line.
  - Run `grep -n "kpiPassRate\|kpiReworkCount" src/app/\(app\)/analysis/page.tsx`. Must return 0 matches.

  Find (verbatim — 2 leading spaces):
  ```ts
  const healthOk =
    health !== null &&
    health.graph_initialised &&
    health.classifier_initialised;
  ```
  Replace with:
  ```ts
  const healthOk =
    health !== null &&
    health.graph_initialised &&
    health.classifier_initialised;

  const analysedSessions = allSessions.filter((s) => s.disposition !== null);
  const kpiPassRate       = analysedSessions.length > 0
    ? Math.round(
        (analysedSessions.filter((s) => s.disposition === "PASS").length / analysedSessions.length) * 100,
      )
    : 0;
  const kpiReworkCount = analysedSessions.filter((s) => s.disposition === "REWORK_REQUIRED").length;
  ```

  ---

  ### Edit 4 — `analysis/page.tsx`: add KPI strip JSX

  **Pre-Read Gate:**
  - Run `grep -n "AI pipeline unavailable" src/app/\(app\)/analysis/page.tsx`. Must return exactly 1 match.
  - Run `grep -n "analysedSessions.length > 0" src/app/\(app\)/analysis/page.tsx`. Must return 0 matches.

  Find (verbatim — 6 leading spaces for outer, 8 for inner div):
  ```tsx
      {health !== null && !healthOk && (
        <div className="shrink-0 border-b border-amber-900 bg-amber-950/40 px-4 py-2 font-mono text-[10px] text-amber-400">
          AI pipeline unavailable — analysis may not complete
        </div>
      )}
  ```
  Replace with:
  ```tsx
      {health !== null && !healthOk && (
        <div className="shrink-0 border-b border-amber-900 bg-amber-950/40 px-4 py-2 font-mono text-[10px] text-amber-400">
          AI pipeline unavailable — analysis may not complete
        </div>
      )}

      {analysedSessions.length > 0 && (
        <div className="flex shrink-0 gap-6 border-b border-[var(--warp-border)] bg-[var(--warp-surface)] px-4 py-2">
          <div>
            <p className="font-mono text-[8px] uppercase tracking-widest text-[var(--warp-text-muted)]">Sessions Analysed</p>
            <p className="font-mono text-[16px] text-[var(--warp-text)]">{analysedSessions.length}</p>
          </div>
          <div>
            <p className="font-mono text-[8px] uppercase tracking-widest text-[var(--warp-text-muted)]">Pass Rate</p>
            <p className="font-mono text-[16px] text-green-400">{kpiPassRate}%</p>
          </div>
          <div>
            <p className="font-mono text-[8px] uppercase tracking-widest text-[var(--warp-text-muted)]">Rework Caught</p>
            <p className="font-mono text-[16px] text-red-400">{kpiReworkCount}</p>
          </div>
        </div>
      )}
  ```

  **What it does:** Fetches the sessions list once on mount. Computes pass rate and rework count from sessions with non-null dispositions. Renders a compact 3-stat horizontal strip — hidden until data loads (no flicker).

  **Why this approach:** Zero new API calls, zero new components. The strip only renders when there are analysed sessions, so it never shows misleading zeros on a fresh install.

  **Assumptions:**
  - `fetchMockSessions()` returns sessions including their `disposition` field (confirmed: `MockSession.disposition: WarpDisposition | null`).
  - Sessions with `disposition === null` are pending/not-yet-analysed and are correctly excluded from KPIs.

  **Risks:**
  - Double fetch: `fetchMockSessions` is called here AND inside `SessionList` — two identical requests fire on mount → mitigation: acceptable for MVP; both are GET requests with no side effects. Deduplicate later with a shared context if needed.

  **Git Checkpoint:**
  ```bash
  git add src/app/\(app\)/analysis/page.tsx
  git commit -m "feat: add KPI metrics strip — sessions analysed, pass rate, rework caught"
  ```

  **Subtasks:**
  - [ ] 🟥 Edit 1: add `allSessions` state
  - [ ] 🟥 Edit 2: add mount-time `fetchMockSessions` useEffect
  - [ ] 🟥 Edit 3: add `analysedSessions`, `kpiPassRate`, `kpiReworkCount` computed vars
  - [ ] 🟥 Edit 4: add KPI strip JSX after health warning

  **✓ Verification Test:**

  **Type:** E2E (dev server)

  **Action:**
  1. Navigate to `http://localhost:3000/analysis`
  2. Wait for sessions to load in the left sidebar (≤2 seconds)
  3. Inspect the area between the header bar and the split view

  **Expected:**
  - KPI strip visible with three labelled stat cards
  - "Sessions Analysed" shows a number > 0
  - "Pass Rate" shows a percentage (green text)
  - "Rework Caught" shows a count (red text)
  - Strip is absent when no sessions have been analysed (edge case — acceptable)

  **Pass:** KPI strip renders with non-zero "Sessions Analysed".

  **Fail:**
  - Strip not visible → `allSessions` not populating → check `fetchMockSessions` effect was added and confirm `grep "fetchMockSessions" src/app/(app)/analysis/page.tsx` returns 2 matches (one in handleAnalyseAll, one in new useEffect)
  - All zeros → sessions have no dispositions yet → trigger an analysis for one session to populate data, then revisit

---

### Phase 3 — Corrective Action Acknowledgment

**Goal:** Each corrective action in the report has a checkbox. Checking all actions shows a green "All actions reviewed" banner.

---

- [ ] 🟥 **Step 3: Add corrective action acknowledgment** — *Non-critical: additive state + JSX to existing list*

  **Step Architecture Thinking:**

  **Pattern applied:** Local UI state — `Set<number>` tracks acknowledged indices. Toggling inserts/removes from the set immutably. Banner derives from `acknowledged.size === actions.length`.

  **Why this step exists last:**
  Independent of Steps 1 and 2. Placed last as it touches `QualityReportCard.tsx` which Step 1 already edits — sequencing avoids simultaneous edits to the same file.

  **Why this file is the right location:**
  `QualityReportCard.tsx` owns the corrective actions section. The `acknowledged` state is scoped to this component — it resets correctly when a new session is selected because `AnalysisTimeline` is remounted via `key={viewState.sessionId}` in the parent.

  **Alternative approach considered and rejected:**
  Use `localStorage` keyed by `session_id` to persist acknowledgments across refreshes — rejected as unnecessary for MVP demo; the pattern is identical, just the initial state changes.

  **What breaks if this step deviates:**
  If `list-decimal list-inside` is kept on `<ol>` while `<li>` uses `flex`, the CSS list marker overlaps with the flex row. The replacement drops these two classes — this is intentional and must not be reverted.

  ---

  **Idempotent:** Yes — re-running the edit produces the same result.

  ---

  ### Edit 1 — `QualityReportCard.tsx`: add `acknowledged` state

  **Pre-Read Gate:**
  - Run `grep -n "acknowledged" src/components/analysis/QualityReportCard.tsx`. Must return 0 matches. If 1+ → STOP (already done).
  - Run `grep -n "isPdfLoading" src/components/analysis/QualityReportCard.tsx`. Must return exactly 1 match at the `useState` line (confirms Step 1 Edit 3 ran).

  Find (verbatim — 2 leading spaces):
  ```ts
  const [isPdfLoading, setIsPdfLoading] = useState(false);
  ```
  Replace with:
  ```ts
  const [isPdfLoading, setIsPdfLoading]   = useState(false);
  const [acknowledged, setAcknowledged]   = useState<Set<number>>(new Set());
  ```

  ---

  ### Edit 2 — `QualityReportCard.tsx`: replace corrective actions list with checkboxes

  **Pre-Read Gate:**
  - Run `grep -n "list-decimal list-inside" src/components/analysis/QualityReportCard.tsx`. Must return exactly 1 match. If 0 → STOP (already replaced or anchor wrong).

  **Anchor Uniqueness Check:**
  - Target: `        <ol className="space-y-1 list-decimal list-inside font-mono text-[11px] text-[var(--warp-text)]">`
  - Must appear exactly 1 time in the file.

  Find (verbatim — 10 leading spaces for `<ol>`, 12 for `{report...`, 14 for `<li>`):
  ```tsx
          <ol className="space-y-1 list-decimal list-inside font-mono text-[11px] text-[var(--warp-text)]">
            {report.corrective_actions.map((action, index) => (
              <li key={index}>{action}</li>
            ))}
          </ol>
  ```
  Replace with:
  ```tsx
          {report.corrective_actions.length > 0 &&
            acknowledged.size === report.corrective_actions.length && (
              <div className="mb-2 flex items-center gap-1.5 font-mono text-[9px] text-green-400">
                <span>●</span>
                <span>All actions reviewed</span>
              </div>
            )}
          <ol className="space-y-1.5 font-mono text-[11px] text-[var(--warp-text)]">
            {report.corrective_actions.map((action, index) => (
              <li key={index} className="flex items-start gap-2">
                <input
                  type="checkbox"
                  checked={acknowledged.has(index)}
                  onChange={() =>
                    setAcknowledged((prev) => {
                      const next = new Set(prev);
                      if (next.has(index)) next.delete(index);
                      else next.add(index);
                      return next;
                    })
                  }
                  className="mt-0.5 shrink-0 accent-amber-400"
                />
                <span className={acknowledged.has(index) ? "line-through text-zinc-600" : ""}>
                  {action}
                </span>
              </li>
            ))}
          </ol>
  ```

  **What it does:** Each corrective action gains an amber checkbox. Checked items get strikethrough + grey text. When all actions are checked, a green "All actions reviewed" banner appears above the list. State resets when the user selects a different session (parent remounts via `key`).

  **Why this approach:** `Set<number>` is the minimal immutable toggle pattern for indexed lists. No library needed. The banner condition is a single comparison: `acknowledged.size === actions.length`.

  **Assumptions:**
  - `report.corrective_actions` is always an array (never `undefined`) — confirmed by `WarpReport` type definition.
  - `accent-amber-400` Tailwind class styles the checkbox accent color — supported in modern browsers.

  **Risks:**
  - CSS `accent-amber-400` not available in older Tailwind v2 — mitigation: project uses Tailwind v3 (confirmed by `tailwind.config.ts` patterns in codebase).

  **Git Checkpoint:**
  ```bash
  git add src/components/analysis/QualityReportCard.tsx
  git commit -m "feat: add corrective action acknowledgment checkboxes with all-reviewed banner"
  ```

  **Subtasks:**
  - [ ] 🟥 Edit 1: add `acknowledged` state after `isPdfLoading`
  - [ ] 🟥 Edit 2: replace static `<ol>` with checkbox list + banner

  **✓ Verification Test:**

  **Type:** E2E (dev server)

  **Action:**
  1. Navigate to `http://localhost:3000/analysis`
  2. Select a session with a completed report that has corrective actions
  3. Check all checkboxes one by one

  **Expected:**
  - Each action item shows an amber checkbox
  - Checked items show strikethrough text and grey color
  - After checking all items: green "● All actions reviewed" banner appears above the list
  - `list-decimal list-inside` classes no longer present in DOM:
    ```bash
    grep "list-decimal list-inside" src/components/analysis/QualityReportCard.tsx
    # Must return 0 matches
    ```

  **Pass:** "All actions reviewed" banner appears after all checkboxes are checked.

  **Fail:**
  - Checkboxes appear but no banner → condition `acknowledged.size === report.corrective_actions.length` not met → confirm `acknowledged` state is being set correctly; check for off-by-one in the `Set` toggle logic
  - Layout broken (numbers + checkboxes overlapping) → `list-decimal list-inside` still present → re-check Edit 2 replacement removed those classes

---

## Regression Guard

**Systems at risk:**
- `QualityReportCard.tsx` — any test asserting the "Export PDF" button text or `handleExportPdf` behaviour; corrective actions list structure
- `analysis/page.tsx` — any test asserting layout or element count

**Regression verification:**

| System | Pre-change behaviour | Post-change verification |
|--------|---------------------|--------------------------|
| Export PDF button | Renders "Export PDF", onClick logs warning | Button renders "Export PDF" (not generating), onClick triggers real fetch |
| Corrective actions | Static `<li>` list with numbers | `<li>` with checkbox + span; `list-decimal list-inside` gone |
| KPI strip | Not present | Present when sessions with dispositions exist |
| Existing `/seagull` redirect | Unrelated — unchanged | `grep "seagull" next.config.ts` returns 1 match |

**Test count regression check:**
```bash
npx jest --no-coverage 2>&1 | tail -3
# Must show ≥ same passing count as pre-flight baseline
```

---

## Rollback Procedure

```bash
git revert HEAD      # reverts Step 3 (QualityReportCard checkboxes)
git revert HEAD~1    # reverts Step 2 (KPI strip)
git revert HEAD~2    # reverts Step 1 (PDF export wiring)

# Confirm:
grep "Export PDF not implemented" src/components/analysis/QualityReportCard.tsx  # must return 1 match
grep "list-decimal list-inside" src/components/analysis/QualityReportCard.tsx    # must return 1 match
grep "allSessions" src/app/\(app\)/analysis/page.tsx                             # must return 0 matches
```

---

## Success Criteria

| Feature | Target | Verification |
|---------|--------|--------------|
| PDF export works | "Export PDF" button downloads a `.pdf` file | Click button on a completed report → file downloads |
| PDF button state | Shows "Generating…" during request, disabled | Observe button label during generation |
| KPI strip visible | Three stat cards above split view | Navigate to `/analysis` → strip appears when sessions exist |
| Pass Rate accurate | Computed from actual dispositions | Manually count PASS sessions and compare to displayed % |
| Checkboxes work | Amber checkbox per corrective action | Check each → strikethrough appears |
| Banner triggers | "All actions reviewed" after all checked | Check all → banner appears |
| Tests unchanged | ≥ pre-plan baseline | `npx jest --no-coverage` |

---

⚠️ **Do not mark a step 🟩 Done until its verification test passes.**
⚠️ **Do not batch all 3 steps into one commit — one commit per step.**
⚠️ **Step 3 edits `QualityReportCard.tsx` — confirm Step 1 has already been applied before running Step 3 (both touch the same file; sequential not concurrent).**
⚠️ **`list-decimal list-inside` MUST be removed from `<ol>` in Step 3 Edit 2 — do not keep it.**
⚠️ **If `isPdfLoading` state is missing when Step 3 Edit 1 runs, Step 1 Edit 3 was not applied — run it first.**
