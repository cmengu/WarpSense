# Dashboard Welder Roster — Visual Redesign Plan

**Overall Progress:** `100%`

## TLDR

Replace the current dashboard page UI with the WelderDashboard visual design while preserving all existing API integration, data fetching, and routing. Backend and API contracts unchanged. Welders and scores come from the existing data layer. Presentation only.

---

## Critical Decisions

- **Decision 1:** Keep `WELDERS` exactly as defined in `my-app/src/app/(app)/dashboard/page.tsx` (10 welders including expert-benchmark). IDs and names must match `backend/data/mock_welders.py` WELDER_ARCHETYPES entries (welder_id→id, name, sessions→sessionCount).
- **Decision 2:** Preserve API links — View report → `/replay/[sessionId]`, Compare to expert → `/compare/[sessionId]/[EXPERT_SESSION_ID]`, Full report → `/seagull/welder/[id]`. Use `<Link href={...}>` components. Do NOT use `<button>` or `onClick={() => router.push(...)}` for navigation.
- **Decision 3:** Roster — 9 welders in main grid (exclude expert-benchmark) + Expert Benchmark as separate card below. Expert card has no "Compare to expert" link.
- **Decision 4:** Stats bar — Computed from welderScores. Edge cases: Avg Score "—" when all null; Quality Index "—" when totalNonNull === 0; Active Welders = rosterWelders.length (9); Total Sessions = sum of sessionCount.
- **Decision 5:** Trend — Placeholder: `score !== null ? Math.min(15, Math.max(-15, Math.round((score - 75) / 2))) : 0`.
- **Decision 6:** No inline nav — AppNav in layout provides Home, Dashboard, Defects, AI. Page content starts with ambient background + "Welder Roster" + stats bar + cards. No WELDVIEW header/nav.

---

## Clarification Gate

| Unknown | Required | Source | Blocking | Resolved |
|---------|----------|--------|----------|----------|
| lucide-react | Add via npm install | package.json | Step 1 | ⬜ |

---

## Agent Failure Protocol

1. Verification fails → read full error.
2. Cause clear → one targeted fix → re-run same verification.
3. Still failing → **STOP**. Output: (a) command, (b) full error, (c) fix attempted, (d) full contents of each modified file, (e) why you cannot proceed.
4. Never second fix without human instruction.
5. Never modify files not named in the current step.

---

## Pre-Flight — Run Before Any Code Changes

Execute in order. Record results.

**1. Check dashboard test file exists:**
```bash
test -f my-app/src/__tests__/app/\(app\)/dashboard/page.test.tsx && echo "EXISTS" || echo "MISSING"
```
- If EXISTS: set `DASHBOARD_TESTS_EXIST=true`. Proceed with Step 3 and test verification.
- If MISSING: set `DASHBOARD_TESTS_EXIST=false`. Omit Step 3. Use manual verification only. Omit `data-score-tier` (optional; can still add for consistency).

**2. Run tests (if DASHBOARD_TESTS_EXIST=true):**
```bash
cd my-app && npm test -- --testPathPattern="dashboard|seagull-flow" 2>&1
```
Record: Pass count ____, Fail count ____.

**3. Baseline line count:**
```bash
wc -l my-app/src/app/\(app\)/dashboard/page.tsx
```
Record: ____ lines.

**4. Verify WELDERS alignment:**
```bash
grep -A2 "welder_id" backend/data/mock_welders.py | head -30
```
Confirm dashboard WELDERS ids match: mike-chen, sara-okafor, james-park, lucia-reyes, tom-bradley, ana-silva, derek-kwon, priya-nair, marcus-bell, expert-benchmark.

**Baseline Snapshot (agent fills during pre-flight):**
```
DASHBOARD_TESTS_EXIST: true | false
Test count (if tests exist): ____
Line count dashboard page: ____
```

---

## Environment Matrix

| Step | Dev | Staging | Prod |
|------|-----|---------|------|
| 1, 2a–2d | ✅ | ✅ | ✅ |
| 3 | ✅ if tests exist | ✅ if tests exist | ✅ if tests exist |

---

## Tasks

### Phase 1 — Dependency

- [ ] 🟥 **Step 1: Add lucide-react** — *Critical (required for Step 2a icons)*

  **Idempotent:** Yes.

  **Action and verification (run together):**
  ```bash
  cd my-app && npm install lucide-react && grep -q lucide-react package.json || echo "FAILED"
  ```
  Expected: No output (success). If FAILED is printed, install did not succeed — fix before proceeding.

  **Git Checkpoint:**
  ```bash
  git add my-app/package.json my-app/package-lock.json
  git commit -m "step 1: add lucide-react for dashboard icons"
  ```

---

### Phase 2 — Dashboard UI Replacement (Split)

- [ ] 🟥 **Step 2a: Replace UI structure — layout, cards, styling** — *Critical*

  **Idempotent:** Yes.

  **Pre-Read Gate:**
  - `grep -c "WELDERS\|getLatestSessionId\|fetchScore" my-app/src/app/\(app\)/dashboard/page.tsx` — must be ≥ 3.

  **Context:** Replace page layout with dark theme, welder cards grid. Keep all data layer logic. Do NOT change stats bar yet; do NOT add Expert card yet.

  **Data flow (preserve exactly — do NOT change fetch loop):**
  1. Fetch scores for ALL 10 WELDERS (including expert-benchmark) — same useEffect, same fetches map over WELDERS.
  2. Store all 10 results in welderScores state.
  3. For grid rendering: `rosterResults = welderScores.filter(r => r.welder.id !== "expert-benchmark")`.
  4. Sort rosterResults by score ascending (worst first): `(a,b) => (a.score ?? Infinity) - (b.score ?? Infinity)`.
  5. Render the sorted 9 in the grid.
  Do NOT filter WELDERS before fetch. Fetch for all 10. Filter only for display.

  **File structure (preserve/add exactly — single canonical order):**
  ```typescript
  // 1. Client directive (required for hooks)
  "use client";

  // 2. Imports
  import { useEffect, useState } from "react";
  import Link from "next/link";
  import { fetchScore } from "@/lib/api";
  import type { SessionScore } from "@/lib/api";
  import { ArrowRight, TrendingUp, AlertTriangle, CheckCircle } from "lucide-react";

  // 3. Constants
  const EXPERT_SESSION_ID = "sess_expert-benchmark_005";
  const FETCH_TIMEOUT_MS = 5000;

  // 4. Interfaces
  interface Welder { id: string; name: string; sessionCount: number; }
  interface WelderScoreResult { welder: Welder; score: number | null; }

  // 5. Arrays (preserve exactly — copy from current file)
  const WELDERS: Welder[] = [
    { id: "mike-chen", name: "Mike Chen", sessionCount: 5 },
    { id: "sara-okafor", name: "Sara Okafor", sessionCount: 5 },
    { id: "james-park", name: "James Park", sessionCount: 5 },
    { id: "lucia-reyes", name: "Lucia Reyes", sessionCount: 5 },
    { id: "tom-bradley", name: "Tom Bradley", sessionCount: 3 },
    { id: "ana-silva", name: "Ana Silva", sessionCount: 5 },
    { id: "derek-kwon", name: "Derek Kwon", sessionCount: 5 },
    { id: "priya-nair", name: "Priya Nair", sessionCount: 5 },
    { id: "marcus-bell", name: "Marcus Bell", sessionCount: 5 },
    { id: "expert-benchmark", name: "Expert Benchmark", sessionCount: 5 },
  ];

  // 6. Helper functions (in this order) — preserve getLatestSessionId and fetchScoreWithTimeout from current file
  // Remove getScoreBadgeClass (replaced by getScoreColor and getScoreTier)
  function getLatestSessionId(w: Welder): string { return `sess_${w.id}_${String(w.sessionCount).padStart(3,"0")}`; }
  function getScoreColor(score: number | null): string { /* see below */ }
  function getScoreTier(score: number | null): string { /* see below */ }
  async function fetchScoreWithTimeout(sessionId: string, signal?: AbortSignal): Promise<SessionScore | null> {
    const timeout = new Promise<null>((_, reject) => setTimeout(() => reject(new Error("fetchScore timeout")), FETCH_TIMEOUT_MS));
    try { return await Promise.race([fetchScore(sessionId, signal), timeout]); } catch { return null; }
  }

  // 7. Component — see "Component structure" below for full JSX
  export default function DashboardPage() { ... }
  ```
  Icons used: TrendingUp (trend display), ArrowRight (link buttons), CheckCircle (score≥90), AlertTriangle (score<60) — rendered inline via ternary next to welder name.

  **Component structure (render return — implement exactly):**
  ```tsx
  export default function DashboardPage() {
    const [welderScores, setWelderScores] = useState<WelderScoreResult[] | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
      let mounted = true;
      const controller = new AbortController();
      setLoading(true);
      const fetches = WELDERS.map((w) => ({ welder: w, sessionId: getLatestSessionId(w) }));
      Promise.allSettled(
        fetches.map((f) => fetchScoreWithTimeout(f.sessionId, controller.signal).catch(() => null))
      ).then((results) => {
        if (!mounted) return;
        setWelderScores(
          fetches.map((f, i) => {
            const r = results[i];
            return {
              welder: f.welder,
              score: r.status === "fulfilled" && r.value != null ? (r.value as SessionScore).total : null,
            };
          })
        );
        setLoading(false);
      });
      return () => { mounted = false; controller.abort(); };
    }, []);

    if (loading || welderScores === null) {
      return (
        <div className="min-h-screen bg-black text-gray-100 relative overflow-hidden">
          <div className="fixed inset-0 bg-gradient-to-br from-cyan-900/5 via-transparent to-emerald-900/5 pointer-events-none" />
          <div className="max-w-7xl mx-auto px-6 py-12">
            <h2 className="text-4xl font-bold mb-6">Welder Roster</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {WELDERS.filter(w => w.id !== "expert-benchmark").map((w) => (
                <div key={w.id} className="rounded-xl p-6 bg-gray-900/80 animate-pulse">
                  <div className="h-5 w-32 bg-gray-700 rounded mb-2" />
                  <div className="h-4 w-24 bg-gray-700 rounded" />
                </div>
              ))}
            </div>
          </div>
        </div>
      );
    }

    const rosterResults = welderScores?.filter(r => r.welder.id !== "expert-benchmark") ?? [];
    const sorted = [...rosterResults].sort((a, b) => (a.score ?? Infinity) - (b.score ?? Infinity));

    return (
      <div className="min-h-screen bg-black text-gray-100 relative overflow-hidden">
        <div className="fixed inset-0 bg-gradient-to-br from-cyan-900/5 via-transparent to-emerald-900/5 pointer-events-none" />
        <div className="fixed inset-0 pointer-events-none">
          <div className="absolute top-0 left-1/4 w-96 h-96 bg-cyan-500/5 rounded-full blur-[120px]" />
          <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-emerald-500/5 rounded-full blur-[120px]" />
        </div>
        <main className="relative max-w-7xl mx-auto px-6 py-12">
          <h2 className="text-4xl font-bold tracking-tight mb-2">Welder Roster</h2>
          {/* Stats bar inserted by Step 2b — placeholder for now */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-8">
            {sorted.map(({ welder, score }) => {
              const sessionId = getLatestSessionId(welder);
              const isExpert = welder.id === "expert-benchmark";
              const trend = score !== null ? Math.min(15, Math.max(-15, Math.round((score - 75) / 2))) : 0;
              return (
                <div
                  key={welder.id}
                  className="relative rounded-xl overflow-hidden p-6 transition-colors duration-200"
                  style={{
                    background: "linear-gradient(135deg, rgba(255,255,255,0.05), rgba(255,255,255,0.02))",
                    boxShadow: "0 8px 32px -8px rgba(0,0,0,0.6), inset 0 1px 0 rgba(255,255,255,0.05)",
                  }}
                >
                  <div className="flex items-start justify-between mb-4">
                    <h3 className="text-xl font-bold text-gray-100">{welder.name}</h3>
                    <div className="flex items-center gap-2" style={{ color: score !== null ? getScoreColor(score) : undefined }}>
                      {score !== null && (score >= 90 ? <CheckCircle className="w-4 h-4" /> : score >= 60 ? <TrendingUp className="w-4 h-4" /> : <AlertTriangle className="w-4 h-4" />)}
                    </div>
                  </div>
                  <div className="flex items-center gap-2 text-xs text-gray-500 mb-4">
                    <span>{welder.sessionCount} sessions</span>
                    <span>•</span>
                    <span className={trend > 0 ? "text-emerald-400" : trend < 0 ? "text-red-400" : "text-gray-500"}>
                      {trend > 0 ? "+" : ""}{trend}%
                      <TrendingUp className={`inline w-3 h-3 ml-0.5 ${trend < 0 ? "rotate-180" : ""}`} />
                    </span>
                  </div>
                  <div className="mb-6">
                    {score !== null ? (
                      <span
                        data-score-tier={getScoreTier(score)}
                        className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium"
                        style={{ color: getScoreColor(score), backgroundColor: `${getScoreColor(score)}20` }}
                      >
                        {score}/100
                      </span>
                    ) : (
                      <span className="text-violet-400">Score unavailable</span>
                    )}
                  </div>
                  <div className="space-y-2">
                    <Link href={`/replay/${sessionId}`} className="flex items-center justify-between text-sm text-gray-400 hover:text-cyan-400 py-2">
                      <span>View report</span>
                      <ArrowRight className="w-4 h-4" />
                    </Link>
                    {!isExpert && (
                      <Link href={`/compare/${sessionId}/${EXPERT_SESSION_ID}`} className="flex items-center justify-between text-sm text-gray-400 hover:text-cyan-400 py-2">
                        <span>Compare to expert</span>
                        <ArrowRight className="w-4 h-4" />
                      </Link>
                    )}
                    <Link href={`/seagull/welder/${welder.id}`} className="flex items-center justify-between text-sm text-gray-400 hover:text-cyan-400 py-2">
                      <span>Full report</span>
                      <ArrowRight className="w-4 h-4" />
                    </Link>
                  </div>
                </div>
              );
            })}
          </div>
          {/* Expert card inserted by Step 2c */}
        </main>
      </div>
    );
  }
  ```
  **Ambient background:** Implement the two blur divs as shown (cyan top-left, emerald bottom-right). Improves visual appeal; do not omit.

  **Functions to preserve:** getLatestSessionId (returns sess_{id}_{paddedCount}) and fetchScoreWithTimeout (Promise.race with 5s timeout) — copy exactly from current file.
  **Remove:** getScoreBadgeClass function (replaced by getScoreColor and getScoreTier).

  **Exact color/tier functions — copy verbatim:**
  ```typescript
  function getScoreColor(score: number | null): string {
    if (score === null) return "#6b7280";
    if (score >= 90) return "#00ff9f";
    if (score >= 75) return "#7fff00";
    if (score >= 60) return "#ffb800";
    if (score >= 40) return "#ff6b00";
    return "#ff3838";
  }
  function getScoreTier(score: number | null): string {
    if (score === null) return "unknown";
    if (score >= 90) return "excellent";
    if (score >= 75) return "good";
    if (score >= 60) return "fair";
    if (score >= 40) return "poor";
    return "critical";
  }
  ```

  **CRITICAL:** Use `<Link href={...}>` for View report, Compare to expert, Full report. NOT button, NOT onClick router.push.
  ```tsx
  {/* CRITICAL: Use Link for navigation — required for SEO and test compatibility */}
  <Link href={`/replay/${sessionId}`}>View report</Link>
  ```

  **Pre-Step verification (required):** Before editing dashboard page, confirm lucide-react is installed:
  ```bash
  grep -q lucide-react my-app/package.json || echo "ERROR: Run Step 1 first"
  ```
  If ERROR is printed, run Step 1 before proceeding.

  **Verification (required before commit):**
  ```bash
  cd my-app && npm run build
  ```
  Expected: Build succeeds with no TypeScript errors. If it fails, STOP and output the full error before committing.

  **Sanity check:** Run `wc -l my-app/src/app/\(app\)/dashboard/page.tsx`. Expected: ~200–280 lines. If under 100 or over 400, review structure.

  **Git Checkpoint:**
  ```bash
  git add my-app/src/app/\(app\)/dashboard/page.tsx
  git commit -m "step 2a: replace dashboard layout and card styling"
  ```

---

- [ ] 🟥 **Step 2b: Add stats bar with edge-case handling** — *Critical*

  **Idempotent:** Yes.

  **Context:** Add 4-stat bar above welder grid. Compute from welderScores. Replace the Step 2a placeholder comment with the full stats bar block.

  **Code placement:** Add these computations inside DashboardPage, after the `sorted` constant and before the `return` statement:
  ```typescript
  // ... existing from Step 2a ...
  const rosterResults = welderScores?.filter(r => r.welder.id !== "expert-benchmark") ?? [];
  const sorted = [...rosterResults].sort((a, b) => (a.score ?? Infinity) - (b.score ?? Infinity));

  // ADD FOR STATS BAR:
  const rosterWelders = WELDERS.filter(w => w.id !== "expert-benchmark");
  const scores = rosterResults.map(r => r.score).filter((s): s is number => s !== null);
  const totalNonNull = scores.length;
  const avgScore = totalNonNull === 0 ? "—" : String(Math.round(scores.reduce((a,b)=>a+b,0) / totalNonNull));
  const totalSessions = rosterWelders.reduce((s, w) => s + w.sessionCount, 0);
  const countAbove80 = scores.filter(s => s >= 80).length;
  const qualityIndex = totalNonNull === 0 ? "—" : `${Math.round((countAbove80 / totalNonNull) * 100)}%`;

  return ( ... );
  ```

  **Stats bar structure:** Replace the `{/* Stats bar inserted by Step 2b — placeholder for now */}` comment with the block below. The h2 "Welder Roster" remains from Step 2a; add the p and stats grid after it:
  ```tsx
  <p className="text-gray-500 text-sm mb-6">Last updated: {new Date().toLocaleTimeString()}</p>
  <div className="grid grid-cols-4 gap-4 mb-6">
    <div className="rounded-lg p-4" style={{ background: "linear-gradient(135deg, rgba(255,255,255,0.05), rgba(255,255,255,0.02))" }}>
      <div className="text-2xl font-bold text-gray-100">{rosterWelders.length}</div>
      <div className="text-xs text-gray-500 uppercase tracking-wider">Active Welders</div>
    </div>
    <div className="rounded-lg p-4" style={{ background: "linear-gradient(135deg, rgba(255,255,255,0.05), rgba(255,255,255,0.02))" }}>
      <div className="text-2xl font-bold text-gray-100">{avgScore}</div>
      <div className="text-xs text-gray-500 uppercase tracking-wider">Avg Score</div>
    </div>
    <div className="rounded-lg p-4" style={{ background: "linear-gradient(135deg, rgba(255,255,255,0.05), rgba(255,255,255,0.02))" }}>
      <div className="text-2xl font-bold text-gray-100">{totalSessions}</div>
      <div className="text-xs text-gray-500 uppercase tracking-wider">Total Sessions</div>
    </div>
    <div className="rounded-lg p-4" style={{ background: "linear-gradient(135deg, rgba(255,255,255,0.05), rgba(255,255,255,0.02))" }}>
      <div className="text-2xl font-bold text-gray-100">{qualityIndex}</div>
      <div className="text-xs text-gray-500 uppercase tracking-wider">Quality Index</div>
    </div>
  </div>
  ```
  The welder cards grid follows immediately (unchanged from Step 2a).
  Order: Active Welders, Avg Score, Total Sessions, Quality Index.

  **Insertion method:** Replace the `{/* Stats bar inserted by Step 2b — placeholder for now */}` comment with the stats bar JSX block (p + grid of 4 stats). Do not leave the comment.

  Stats display: Active Welders = `rosterWelders.length`, Avg Score = `avgScore`, Total Sessions = `totalSessions`, Quality Index = `qualityIndex`.

  **Verification (manual):** With 9 welders and scores [85,75,65,55,85,75,65,55,85], expect Avg Score 72, Quality Index 33%.

  **Git Checkpoint:**
  ```bash
  git add my-app/src/app/\(app\)/dashboard/page.tsx
  git commit -m "step 2b: add stats bar with edge-case handling"
  ```

---

- [ ] 🟥 **Step 2c: Add Expert Benchmark card** — *Critical*

  **Idempotent:** Yes.

  **Context:** Replace the `{/* Expert card inserted by Step 2c */}` comment with the Expert Benchmark card block. Do not leave the comment.

  **Code placement:** Add expert score extraction inside DashboardPage, after the stats bar computations from Step 2b and before the `return` statement:
  ```typescript
  // ... stats bar formulas from 2b ...
  const qualityIndex = ...;

  // ADD FOR EXPERT CARD:
  const expertResult = welderScores?.find(r => r.welder.id === "expert-benchmark");
  const expertScore = expertResult?.score ?? null;

  return ( ... );
  ```

  **Expert score extraction (same as above):**
  ```typescript
  const expertResult = welderScores?.find(r => r.welder.id === "expert-benchmark");
  const expertScore = expertResult?.score ?? null;
  ```

  **Exact structure:** Expert card displays its score when available, using same badge styling as welder cards (inline-flex, padding, rounded):
  ```tsx
  {/* Expert Benchmark — separate card, no Compare to expert link */}
  <div className="mt-8 relative rounded-xl p-6 overflow-hidden" style={{ background: "linear-gradient(135deg, rgba(255,255,255,0.05), rgba(255,255,255,0.02))", boxShadow: "0 8px 32px rgba(0,0,0,0.6)" }}>
    <div className="flex items-center gap-3 mb-2">
      <CheckCircle className="w-5 h-5 text-cyan-400" />
      <h3 className="text-lg font-bold text-gray-100">Expert Benchmark</h3>
    </div>
    {expertScore !== null && (
      <span
        data-score-tier={getScoreTier(expertScore)}
        className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium"
        style={{ color: getScoreColor(expertScore), backgroundColor: `${getScoreColor(expertScore)}20` }}
      >
        {expertScore}/100
      </span>
    )}
    <p className="text-sm text-gray-400 mb-4 mt-2">Reference standard for optimal weld quality parameters and technique</p>
    <Link href={`/replay/${EXPERT_SESSION_ID}`} className="text-sm text-cyan-400 hover:text-cyan-300">View benchmark details</Link>
    <span className="mx-2 text-gray-600">|</span>
    <Link href={`/seagull/welder/expert-benchmark`} className="text-sm text-cyan-400 hover:text-cyan-300">Full report</Link>
  </div>
  ```
  Do NOT add "Compare to expert" on this card. Replace the Step 2a comment with this block; do not leave the comment.

  **Verification (manual):** Count links with text "Compare to expert" on page. Must be exactly 9.

  **Git Checkpoint:**
  ```bash
  git add my-app/src/app/\(app\)/dashboard/page.tsx
  git commit -m "step 2c: add Expert Benchmark card"
  ```

---

- [ ] 🟥 **Step 2d: Verify links and data-score-tier** — *Critical*

  **Idempotent:** Yes.

  **Context:** Confirm all links and attributes are correct.

  **Checks:**
  1. Every welder card has `data-score-tier={getScoreTier(score)}` on the score display element (the span or div showing the number).
  2. View report → `href={/replay/${sessionId}}`
  3. Compare to expert → `href={/compare/${sessionId}/${EXPERT_SESSION_ID}}` only when `welder.id !== "expert-benchmark"`
  4. Full report → `href={/seagull/welder/${welder.id}}`

  **Verification:**
  ```bash
  grep -n "Link\|href=\|data-score-tier" my-app/src/app/\(app\)/dashboard/page.tsx
  ```
  Confirm structure. Then:
  ```bash
  cd my-app && npm run build
  ```
  Expected: build succeeds.

  **Manual verification (always perform, regardless of test status):**
  1. `npm run dev`, open http://localhost:3000/dashboard
  2. 9 cards in grid + 1 Expert card below
  3. Scores visible, colors match tier
  4. Click "View report" → navigates to /replay/sess_[id]_[nnn]
  5. "Compare to expert" appears on 9 cards only
  6. Stats bar shows 4 metrics (non-blank when data loaded)

  **Git Checkpoint:**
  ```bash
  git add my-app/src/app/\(app\)/dashboard/page.tsx
  git commit -m "step 2d: verify links and data-score-tier"
  ```

---

### Phase 3 — Test Updates (Only if DASHBOARD_TESTS_EXIST=true)

- [ ] 🟥 **Step 3: Update dashboard tests** — *Critical, conditional*

  **Skip if:** Pre-Flight reported `DASHBOARD_TESTS_EXIST=false`.

  **File:** `my-app/src/__tests__/app/(app)/dashboard/page.test.tsx`

  **Before making changes:** Read the entire test file. Identify ALL assertions that reference:
  - Tailwind classes (bg-green-100, bg-amber-100, bg-red-100, etc.)
  - onClick handlers or router.push calls
  - Hard-coded welder counts (10 cards, etc.)
  - Card structure expectations (role="button", etc.)
  Then update each as specified below.

  **Changes:**

  1. **Score badge colour test:** Replace `toHaveClass("bg-green-100")` with:
     ```typescript
     const badge = document.querySelector('[data-score-tier="good"]');
     expect(badge).toBeInTheDocument();
     ```
     (For mock score 85, tier is "good".)

  2. **"10 welder cards"** → Assert 9 names in grid + "Expert Benchmark" in document. E.g.:
     ```typescript
     expect(screen.getByText(/Mike Chen/)).toBeInTheDocument();
     expect(screen.getByText(/Expert Benchmark/)).toBeInTheDocument();
     expect(screen.getAllByRole("link", { name: /Compare to expert/ })).toHaveLength(9);
     ```

  3. **"sorts cards by score ascending"** — Unchanged if first card is still worst score.

  4. **"Expert Benchmark card has no Compare to expert link"** — Assert count of Compare links === 9.

  5. **"links Full report to /seagull/welder/[id]"** — Link text must match /Full report/. Still valid with Link.

  6. **"calls fetchScore for latest session only"** — Unchanged. One call per welder.

  **Verification:**
  ```bash
  cd my-app && npm test -- --testPathPattern="dashboard|seagull-flow"
  ```
  Expected: All tests pass.

  **Git Checkpoint:**
  ```bash
  git add my-app/src/__tests__/app/\(app\)/dashboard/page.test.tsx
  git commit -m "step 3: update dashboard tests for new design"
  ```

---

## Regression Guard

**Systems at risk:** Dashboard page, seagull flow.

**Regression verification:**

| System | Pre-change | Post-change |
|--------|------------|-------------|
| Dashboard | 10 cards, fetchScore, correct links | Same; new styling |
| Seagull flow | Dashboard loads | Same behavior |
| API | fetchScore unchanged | No edits to api.ts or backend |

**Test count (when tests exist):** Post-plan test count must be ≥ pre-flight baseline. If baseline was 0, no regression check on count.

---

## Rollback Procedure

```bash
git log --oneline -5
git revert <commit-range>
# Or restore specific files:
git checkout HEAD~3 -- my-app/src/app/\(app\)/dashboard/page.tsx
git checkout HEAD~3 -- my-app/src/__tests__/app/\(app\)/dashboard/page.test.tsx
```

---

## Pre-Flight Checklist

| Check | How to Confirm | Status |
|-------|-----------------|--------|
| Dashboard test file exists | `test -f ...` → EXISTS/MISSING | ⬜ |
| DASHBOARD_TESTS_EXIST set | true or false | ⬜ |
| Baseline line count | wc -l dashboard page | ⬜ |
| WELDERS matches backend | grep mock_welders | ⬜ |

---

## Verification Summary

| Step | Action | Expected |
|------|--------|----------|
| 1 | `npm install lucide-react` | package.json contains lucide-react |
| 2a | Replace layout | Dark theme, 9 cards, getScoreColor/getScoreTier |
| 2b | Add stats bar | 4 metrics, edge cases handled |
| 2c | Add Expert card | Below grid, no Compare link |
| 2d | Verify links + build | grep confirms structure; build succeeds |
| 3 | Update tests (if exist) | `npm test -- dashboard\|seagull-flow` passes |

---

## Success Criteria

| Feature | Target | Verification |
|---------|--------|--------------|
| Visual design | Dark theme, stats bar, cards | Manual or screenshot |
| Data | WELDERS + fetchScore | Code review |
| Links | /replay/, /compare/, /seagull/ correct | grep + manual click |
| Expert card | Separate, no Compare link | Count Compare links = 9 |
| Stats bar | No division-by-zero | Formula includes totalNonNull check |
| Tests | Pass (if exist) | npm test |
| Backend | Unchanged | No edits to backend/ or api.ts |
