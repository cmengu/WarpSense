# WarpSense Frontend Integration Plan

**Overall Progress:** `0% — 0 / 9 steps complete`

---

## TLDR

The current WarpSense UI has three structural problems: (1) a horizontal top-nav that wastes vertical space and carries zero verdict information, (2) the session list buries the disposition as a tiny badge at the end of each row, and (3) technical internal labels (`quality_class`, `confidence: 0.87`, agent code-names, raw feature variable names) appear in supervisor-facing views. This plan fixes all three in order: first restructure navigation to a collapsible left sidebar that merges Dashboard + Defects into a single "Overview" entry, then enforce verdict-first visual hierarchy across the session list, AnalysisTimeline header, and Dashboard panel cards, then translate every internal label into operational language a QA supervisor reads without training.

After this plan executes: the app has a sidebar (220 px expanded / 56 px collapsed, persisted in `localStorage`), every session row shows a 2 px left border in its disposition colour before any analysis starts, the AnalysisTimeline header turns the verdict colour the moment streaming completes, Dashboard panel cards carry a 3 px left verdict border, and the report card shows `87% confidence · ISO 5817 Grade C` instead of `MARGINAL · confidence 87.3% · ISO C`. No routes, API contracts, or backend data shapes change.

---

## Architecture Overview

**Problems solved (file → limitation):**
1. `src/app/(app)/layout.tsx` — `grid grid-rows-[auto_1fr]` with horizontal `AppNav`; vertical space wasted; nav carries no verdict signal
2. `src/components/analysis/SessionList.tsx` — `border-l-transparent` on unselected rows; disposition badge is the last, smallest element
3. `src/components/analysis/AnalysisTimeline.tsx` — header text stays neutral `text-[var(--warp-text-muted)]` when `phase === "done"`; disposition colour only visible below the agent cards
4. `src/app/(app)/dashboard/page.tsx` — inspection decision is a `w-2 h-2` (8 px) dot buried mid-card; `border: 1px solid rgba(255,255,255,0.09)` gives no verdict signal
5. `src/components/analysis/QualityReportCard.tsx` — `{report.quality_class} · confidence {n}% · ISO {x}` exposes internal ML vocabulary; `buildDriverBars` uses raw feature variable names; Assessment Details shows code-level agent names
6. `src/components/analysis/WelderTrendChart.tsx` — `yTickFormatter` returns `"COND"` (not operational); tooltip appends a numeric score alongside the disposition label
7. `src/components/analysis/SpecialistCard.tsx` — `STAGE_LABEL` shows "Thermal" / "Geometry" / "Process" — one-word technical stubs
8. `backend/agent/specialists.py` — `_threshold_fallback()` corrective actions use Python variable names (`heat_diss_max_spike`)

**Patterns applied:**
- **Display-name mapping (DRY):** a single `const FEATURE_DISPLAY` dict in `QualityReportCard.tsx` and `_FEATURE_LABELS` dict in `specialists.py` are the sole source of truth for translating internal identifiers; downstream JSX/Python reads from these maps rather than duplicating translations in-place
- **Token-only colouring:** all verdict colours use the existing `--warp-green` / `--warp-amber` / `--warp-danger` CSS variables or their Tailwind equivalents (`green-500`, `amber-400`, `red-500`); no new colour values are introduced
- **localStorage for UI state:** sidebar collapse state is a pure UI preference; no server state, no React context, no URL param — one `localStorage.getItem/setItem` call in a `useEffect`, isolated to `AppSidebar`

**What stays unchanged:**
- All route paths (`/analysis`, `/dashboard`, `/ai`, `/admin/thresholds`) — no URL changes
- `AppNav.tsx` — left in place, simply no longer imported by the layout
- All API contracts, SSE event shapes, DB schemas
- `AnalysisTimeline` streaming logic (only the header's CSS classes change)
- `QualityReportCard` data contract (only display formatting changes)
- `WarpReport` TypeScript type

**What this plan adds:**
- `src/components/AppSidebar.tsx` — new client component; owns collapse toggle + `localStorage` persistence; renders primary nav + footer nav; imports nothing outside Next.js + React

**Critical decisions:**

| Decision | Alternative considered | Why rejected |
|---|---|---|
| Sidebar replaces top nav (not augments) | Keep top nav, add sidebar as secondary | Two nav surfaces create ambiguity about which is authoritative; top nav wastes 44 px of vertical space the analysis surface needs |
| Dashboard + Defects → single "Overview" sidebar entry | Keep as separate entries | Both are aggregate views for the same supervisor persona; two entries for the same mental model adds nav cognitive load |
| Sidebar collapse state in `localStorage` | React context | Context would require a provider wrapping the layout; `localStorage` is 3 lines and scoped entirely to `AppSidebar` |
| 2 px disposition border on session rows, amber overrides when selected | Full row background tint | Border is scannable at any row height; tint would conflict with the existing selected-row highlight (`bg-[var(--warp-surface-2)]`) |
| Update `STAGE_LABEL` values in-place | Add a second dict `STAGE_DOMAIN` | Single dict is simpler; the old single-word labels ("Thermal") serve no purpose that the new labels ("Heat Profile") don't also serve |

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
# 1. Confirm layout currently imports AppNav (not AppSidebar)
grep -n "AppNav\|AppSidebar" my-app/src/app/\(app\)/layout.tsx

# 2. Confirm AppSidebar does NOT yet exist
ls my-app/src/components/AppSidebar.tsx 2>&1

# 3. Confirm SessionList border classes
grep -n "border-l-transparent\|border-l-amber" my-app/src/components/analysis/SessionList.tsx

# 4. Confirm AnalysisTimeline header text
grep -n "Analysis in Progress\|Analysis Complete" my-app/src/components/analysis/AnalysisTimeline.tsx

# 5. Confirm QualityReportCard quality_class line
grep -n "quality_class" my-app/src/components/analysis/QualityReportCard.tsx

# 6. Confirm STAGE_LABEL values
grep -n "STAGE_LABEL\|thermal_agent\|geometry_agent\|process_agent" my-app/src/components/analysis/SpecialistCard.tsx

# 7. Record test count
cd my-app && npx tsc --noEmit 2>&1 | tail -5
```

**Baseline Snapshot (agent fills during pre-flight):**
```
AppNav imported in layout: ____
AppSidebar.tsx exists: ____
SessionList border-l-transparent exists: ____
AnalysisTimeline header text exists: ____
QualityReportCard quality_class line exists: ____
SpecialistCard STAGE_LABEL values: ____
TSC errors before plan: ____
```

---

## Phase 1 — Sidebar Navigation

**Goal:** Top `AppNav` bar is replaced by a collapsible left sidebar. Dashboard + Defects are merged under the "Overview" entry. The content area gains the full viewport height.

---

- [ ] 🟥 **Step 1: Create `AppSidebar.tsx`** — *Critical: new file that Step 2 imports*

  **Step Architecture Thinking:**

  **Pattern applied:** Single Responsibility — this component owns exactly one thing: rendering the sidebar nav and persisting its collapse state. It reads `usePathname()` for active highlighting and `localStorage` for collapse state. Nothing else.

  **Why this step exists first:** Step 2 changes the layout import from `AppNav` to `AppSidebar`. The file must exist before the layout is modified or the app breaks immediately on any page render.

  **Why `src/components/AppSidebar.tsx`:** Convention — all shared layout components live in `src/components/`. `AppNav.tsx` lives here; its replacement belongs in the same location.

  **Alternative rejected:** Adding sidebar markup directly into `(app)/layout.tsx`. Rejected because layout files should be thin; mixing nav state logic into the layout violates SRP and makes the collapse toggle untestable in isolation.

  **What breaks if deviated:** If this file is not created before Step 2 runs, the layout import fails and every app route 500s.

  ---

  **Idempotent:** Yes — creating a new file is idempotent; running twice produces no error.

  **Pre-Read Gate:**
  - `ls my-app/src/components/AppSidebar.tsx` must return "No such file". If it exists → read it first to confirm it matches the code below before overwriting.

  ```tsx
  "use client";
  /**
   * AppSidebar — collapsible left navigation for the (app) layout.
   * Replaces AppNav. Collapse state persisted in localStorage.
   *
   * Primary nav:  Analysis, Overview (was: Dashboard + Defects), AI Assist
   * Footer nav:   Thresholds
   * Design tokens: --warp-* from globals.css. No new colours.
   */
  import { useState, useEffect } from "react";
  import Link from "next/link";
  import { usePathname } from "next/navigation";

  const PRIMARY_NAV = [
    { href: "/analysis",  label: "Analysis",  icon: "◈" },
    { href: "/dashboard", label: "Overview",  icon: "▦" },
    { href: "/ai",        label: "AI Assist", icon: "◇" },
  ] as const;

  const FOOTER_NAV = [
    { href: "/admin/thresholds", label: "Thresholds", icon: "⚙" },
  ] as const;

  const LS_KEY = "warp-sidebar-collapsed";

  export function AppSidebar() {
    const pathname  = usePathname();
    const [collapsed, setCollapsed] = useState(false);

    // Hydrate from localStorage after mount — avoids SSR/hydration mismatch.
    useEffect(() => {
      try {
        if (localStorage.getItem(LS_KEY) === "true") setCollapsed(true);
      } catch { /* localStorage blocked in sandboxed contexts */ }
    }, []);

    const toggle = () => {
      setCollapsed((prev) => {
        const next = !prev;
        try { localStorage.setItem(LS_KEY, String(next)); } catch { /* ignore */ }
        return next;
      });
    };

    const itemClass = (href: string) => {
      const active = pathname === href || pathname.startsWith(href + "/");
      return [
        "flex items-center gap-3 px-2 h-9 rounded -ml-px",
        "font-mono text-[10px] uppercase tracking-widest",
        "transition-colors duration-100",
        active
          ? "bg-[var(--warp-surface-2)] text-[var(--warp-amber)] border-l-2 border-[var(--warp-amber)]"
          : "text-[var(--warp-text-muted)] border-l-2 border-transparent hover:bg-[var(--warp-surface-2)] hover:text-[var(--warp-text)]",
      ].join(" ");
    };

    return (
      <aside
        className={[
          "flex flex-col h-full shrink-0 overflow-hidden",
          "border-r border-[var(--warp-border)] bg-[var(--warp-surface)]",
          "transition-[width] duration-200",
          collapsed ? "w-14" : "w-[220px]",
        ].join(" ")}
        style={{ fontFamily: "var(--font-warp-mono), monospace" }}
        aria-label="Main navigation"
      >
        {/* Brand */}
        <Link
          href="/analysis"
          title="WarpSense"
          className="flex items-center gap-3 px-3 h-11 shrink-0 border-b border-[var(--warp-border)] hover:bg-[var(--warp-surface-2)] transition-colors duration-100"
        >
          <span className="text-[var(--warp-amber)] text-[14px] shrink-0 w-4 text-center leading-none">◈</span>
          {!collapsed && (
            <span className="font-mono text-[10px] uppercase tracking-widest text-[var(--warp-text-muted)] whitespace-nowrap">
              WarpSense
            </span>
          )}
        </Link>

        {/* Primary nav */}
        <nav className="flex-1 py-2 px-2 flex flex-col gap-0.5 overflow-hidden">
          {PRIMARY_NAV.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              title={collapsed ? item.label : undefined}
              className={itemClass(item.href)}
            >
              <span className="text-[12px] shrink-0 w-4 text-center leading-none">{item.icon}</span>
              {!collapsed && <span className="truncate">{item.label}</span>}
            </Link>
          ))}
        </nav>

        {/* Footer: admin + collapse toggle */}
        <div className="border-t border-[var(--warp-border)] py-2 px-2 flex flex-col gap-0.5">
          {FOOTER_NAV.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              title={collapsed ? item.label : undefined}
              className={[
                "flex items-center gap-3 px-2 h-8 rounded",
                "font-mono text-[10px] uppercase tracking-widest",
                "transition-colors duration-100",
                pathname.startsWith(item.href)
                  ? "text-[var(--warp-amber)]"
                  : "text-[var(--warp-text-dim)] hover:text-[var(--warp-text-muted)]",
              ].join(" ")}
            >
              <span className="text-[11px] shrink-0 w-4 text-center leading-none">{item.icon}</span>
              {!collapsed && <span className="truncate">{item.label}</span>}
            </Link>
          ))}

          <button
            type="button"
            onClick={toggle}
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            className="flex items-center gap-3 px-2 h-8 rounded w-full font-mono text-[10px] uppercase tracking-widest text-[var(--warp-text-dim)] hover:text-[var(--warp-text-muted)] transition-colors duration-100"
          >
            <span className="text-[12px] shrink-0 w-4 text-center leading-none select-none">
              {collapsed ? "›" : "‹"}
            </span>
            {!collapsed && <span>Collapse</span>}
          </button>
        </div>
      </aside>
    );
  }
  ```

  **What it does:** Renders a `220 px / 56 px` left sidebar with 3 primary nav items, 1 admin footer item, and a collapse toggle. Persists collapse state in `localStorage["warp-sidebar-collapsed"]`. Active route highlighted with amber left border.

  **Assumptions:**
  - `var(--warp-surface)`, `var(--warp-border)`, `var(--warp-amber)`, `var(--warp-surface-2)`, `var(--warp-text-muted)`, `var(--warp-text-dim)`, `var(--warp-text)` are defined in `globals.css`
  - `var(--font-warp-mono)` is defined in `globals.css`
  - `transition-[width]` is supported by the Tailwind config (it's a core utility in Tailwind v3+)

  **Risks:**
  - `transition-[width]` not in safelist → add `transition-[width]` to `tailwind.config.js` safelist if class is purged. Mitigation: verify with a dev build that the class appears in the compiled CSS.

  **Git Checkpoint:**
  ```bash
  git add my-app/src/components/AppSidebar.tsx
  git commit -m "step 1: add AppSidebar — collapsible left nav replacing AppNav"
  ```

  **✓ Verification Test:**

  **Type:** Integration

  **Action:** `grep -n "AppSidebar\|PRIMARY_NAV\|LS_KEY" my-app/src/components/AppSidebar.tsx`

  **Expected:** 3+ matches — `AppSidebar`, `PRIMARY_NAV`, `LS_KEY` all present

  **Pass:** All 3 identifiers found in the new file

  **Fail:**
  - If file not found → Step 1 write failed → re-run the Write tool with the exact code above

---

- [ ] 🟥 **Step 2: Update `(app)/layout.tsx` — swap AppNav for AppSidebar** — *Critical: affects every app route*

  **Step Architecture Thinking:**

  **Pattern applied:** Composition — the layout is a thin shell that composes `AppSidebar` + `children`. No logic, no state.

  **Why this step follows Step 1:** The new file must exist before the import is added.

  **Why `(app)/layout.tsx`:** This is the only file that imports `AppNav`; it is the exact boundary where the nav component is injected into the route tree.

  **Alternative rejected:** Wrapping `AppNav` inside `AppSidebar` (adapter pattern). Rejected because `AppNav` is a horizontal bar; wrapping it would produce a sidebar containing a horizontal bar, which is visually broken.

  **What breaks if deviated:** If `AppSidebar` import path is wrong, every app route fails to compile.

  ---

  **Idempotent:** Yes — the file is replaced to exactly the content below; running twice produces the same result.

  **Pre-Read Gate:**
  - `grep -n "AppNav\|AppSidebar" my-app/src/app/\(app\)/layout.tsx` — must show `AppNav` imported, `AppSidebar` absent. If `AppSidebar` already present → this step already ran; verify content matches and skip.

  ```tsx
  /**
   * App layout — wraps children with AppSidebar.
   *
   * Flex row: sidebar (fixed width) + content (flex-1, full height).
   * h-dvh + overflow-hidden on the root gives both sidebar and content
   * a bounded height so the analysis page's h-full children work correctly.
   * Content div keeps overflow-y-auto so dashboard / scroll-heavy pages work.
   */
  import { AppSidebar } from "@/components/AppSidebar";

  export default function AppLayout({
    children,
  }: {
    children: React.ReactNode;
  }) {
    return (
      <div className="flex h-dvh w-full overflow-hidden bg-[var(--warp-bg)]">
        <AppSidebar />
        <div className="flex-1 min-w-0 min-h-0 flex flex-col overflow-y-auto">
          {children}
        </div>
      </div>
    );
  }
  ```

  **What it does:** Replaces `grid grid-rows-[auto_1fr]` + `AppNav` with a flex row: `AppSidebar` on the left + `children` in a scrollable `flex-1` div. `h-dvh overflow-hidden` on the root gives the analysis page's `h-full` children a bounded height without `calc()`.

  **Assumptions:**
  - `var(--warp-bg)` defined in `globals.css` (it is: `#080a0e`)
  - Analysis page uses `h-full min-h-0 flex flex-col` — this still works because the content div is `flex flex-col` and `h-full` children fill it
  - Dashboard page uses `min-h-screen` — this still works because `overflow-y-auto` on the content div scrolls when content overflows

  **Risks:**
  - Dashboard `min-h-screen` inside `overflow-y-auto` with `h-dvh` parent: `min-h-screen = 100dvh`; since the parent is already `h-dvh`, this is satisfied without overflow and the page renders correctly. If the dashboard needs to scroll, `overflow-y-auto` handles it. → No risk.
  - Analysis page `min-w-[1200px]` inner div: with 220 px sidebar, viewport needs ≥ 1420 px. User can collapse sidebar to 56 px (1256 px). → Document this constraint; no code change.

  **Git Checkpoint:**
  ```bash
  git add my-app/src/app/\(app\)/layout.tsx
  git commit -m "step 2: layout uses AppSidebar flex row, replaces AppNav grid"
  ```

  **✓ Verification Test:**

  **Type:** Integration

  **Action:** `grep -c "AppNav" my-app/src/app/\(app\)/layout.tsx`

  **Expected:** `0` — `AppNav` no longer referenced in the layout

  **Pass:** grep returns `0`

  **Fail:**
  - If `AppNav` still present → edit was not saved → re-apply the full file content above

---

## Phase 2 — Verdict-First Visual Hierarchy

**Goal:** Three surfaces enforce Rule 1 (verdict in ≤ 3 seconds): session list rows carry disposition colour before any click; the AnalysisTimeline header turns the verdict colour on completion; dashboard panel cards carry a 3 px left border.

---

- [ ] 🟥 **Step 3: `SessionList.tsx` — disposition-coloured left border on session rows** — *Non-critical: isolated to one component*

  **Step Architecture Thinking:**

  **Pattern applied:** Token-based colouring with a deterministic mapping function. One helper `dispositionBorderClass` maps `WarpDisposition | null` → Tailwind class. The session row className reads from it. Zero state changes.

  **Why here in the sequence:** Phase 1 must be complete so the sidebar doesn't interfere with session list layout during visual verification.

  **Why `SessionList.tsx`:** The session row button is the only place where `session.disposition` is available alongside the row's className.

  **Alternative rejected:** Adding a coloured `<div>` inside the row as a vertical stripe. Rejected because it adds a DOM node for purely cosmetic purposes; `border-l-2` achieves the same result as a CSS property.

  **What breaks if deviated:** If `dispositionBorderClass` returns an invalid Tailwind class (e.g. a dynamic string not in the safelist), the border will not render in production builds.

  ---

  **Idempotent:** Yes — the helper function and className change are deterministic.

  **Pre-Read Gate:**
  - `grep -n "border-l-transparent\|border-l-2" my-app/src/components/analysis/SessionList.tsx` — must show both strings exist. The `border-l-transparent` is the exact string to replace.

  **Anchor Uniqueness Check:**
  - `"border-l-transparent hover:bg-[var(--warp-surface-2)] hover:border-l-zinc-600"` must appear exactly once in `SessionList.tsx`. Confirm before editing.

  Add the helper function immediately before the `SkeletonRows` function (after `formatDate`, before `function SkeletonRows`):

  ```tsx
  /** Maps disposition to a Tailwind left-border colour class for unselected rows. */
  function dispositionBorderClass(disposition: MockSession["disposition"]): string {
    if (disposition === "PASS")             return "border-l-green-500";
    if (disposition === "CONDITIONAL")      return "border-l-amber-400";
    if (disposition === "REWORK_REQUIRED")  return "border-l-red-500";
    return "border-l-zinc-700";
  }
  ```

  Replace the existing not-selected className branch (the exact string to replace is inside the `className` array on the session row `<button>`):

  ```tsx
  // OLD — replace this exact string:
  : "border-l-transparent hover:bg-[var(--warp-surface-2)] hover:border-l-zinc-600",

  // NEW — replace with:
  : `${dispositionBorderClass(session.disposition)} hover:bg-[var(--warp-surface-2)]`,
  ```

  **Git Checkpoint:**
  ```bash
  git add my-app/src/components/analysis/SessionList.tsx
  git commit -m "step 3: session rows show disposition colour as left border"
  ```

  **✓ Verification Test:**

  **Type:** Unit

  **Action:** `grep -n "dispositionBorderClass\|border-l-transparent" my-app/src/components/analysis/SessionList.tsx`

  **Expected:**
  - `dispositionBorderClass` appears (function definition + call site = 2 matches)
  - `border-l-transparent` does NOT appear (0 matches)

  **Pass:** `dispositionBorderClass` found; `border-l-transparent` absent

  **Fail:**
  - If `border-l-transparent` still present → replace step was not applied → re-apply the exact string substitution above

---

- [ ] 🟥 **Step 4: `AnalysisTimeline.tsx` — verdict-coloured header on `phase === "done"`** — *Non-critical: isolated to one component*

  **Step Architecture Thinking:**

  **Pattern applied:** Conditional CSS class derivation from existing state. The `report` state variable (already present) drives three derived class strings that are applied inline. No new state, no new effects.

  **Why here in the sequence:** Phase 1 complete. Step 3 complete (session list). The timeline header is the next verdict-first surface going from entry point → analysis view.

  **Why `AnalysisTimeline.tsx`:** The header JSX and the `report` / `phase` state are both in this file. The derivation is 3 lines of logic.

  **Alternative rejected:** Emitting a `disposition` prop from `AnalysisTimeline` up to `analysis/page.tsx` and colouring the header there. Rejected because the header is inside `AnalysisTimeline`; crossing the component boundary for a CSS class change adds complexity with zero benefit.

  **What breaks if deviated:** If the derived class uses a dynamic string that Tailwind can't statically analyse (e.g. `` `text-${color}-400` ``), the class will be purged in production. Use the full class name strings as shown below.

  ---

  **Idempotent:** Yes.

  **Pre-Read Gate:**
  - `grep -n "Analysis in Progress\|Analysis Complete\|border-zinc-900 shrink-0" my-app/src/components/analysis/AnalysisTimeline.tsx`
  - `"Analysis Complete"` must be present (confirms step has not yet run). If absent → step already ran; verify content and skip.
  - `"border-zinc-900 shrink-0"` must appear exactly once — that is the header div anchor.
  - `grep -c 'return (' my-app/src/components/analysis/AnalysisTimeline.tsx` — must return `1`. If 2+ → STOP; identify the correct JSX `return (` by line number before inserting.

  **Change A — Insert three derived constants** in the component body immediately before the `return (` statement (after the `useEffect` hooks, before the JSX):

  ```tsx
  // Derived once per render — drives header colour on completion.
  const headerBorderClass =
    phase === "done" && report
      ? report.disposition === "PASS"          ? "border-green-900"
        : report.disposition === "CONDITIONAL" ? "border-amber-900"
        : "border-red-900"
      : "border-zinc-900";

  const headerTextClass =
    phase === "done" && report
      ? report.disposition === "PASS"          ? "text-green-400"
        : report.disposition === "CONDITIONAL" ? "text-amber-400"
        : "text-red-400"
      : "text-[var(--warp-text-muted)]";

  const headerLabel =
    phase === "done" && report
      ? report.disposition === "REWORK_REQUIRED" ? "Rework Required"
        : report.disposition === "CONDITIONAL"   ? "Conditional"
        : "Pass"
      : "Analysis in Progress";
  ```

  **Anchor Uniqueness Check for Change B:**
  - `grep -c 'flex items-center justify-between px-4 py-3 border-b border-zinc-900 shrink-0' my-app/src/components/analysis/AnalysisTimeline.tsx`
  - Must return `1`. If 0 → step already ran or file differs; STOP.

  **Change B — Replace OLD header div.** The exact OLD string to replace:

  ```tsx
      <div className="flex items-center justify-between px-4 py-3 border-b border-zinc-900 shrink-0">
        <span className="font-mono text-[10px] uppercase tracking-widest text-[var(--warp-text-muted)]">
          {phase === "streaming" ? "Analysis in Progress" : "Analysis Complete"}
        </span>
        <span className="font-mono text-[9px] text-[var(--warp-text-dim)]">{sessionId}</span>
      </div>
  ```

  Replace with:

  ```tsx
      {/* Header + verdict colour on done */}
      <div className={`flex items-center justify-between px-4 py-3 border-b shrink-0 ${headerBorderClass}`}>
        <span className={`font-mono text-[11px] font-semibold uppercase tracking-widest ${headerTextClass}`}>
          {headerLabel}
        </span>
        <span className="font-mono text-[9px] text-[var(--warp-text-dim)]">{sessionId}</span>
      </div>
  ```

  **What it does:** Three `const` declarations above `return` derive the header's border colour, text colour, and label from `phase` + `report.disposition`. During streaming: neutral zinc. On completion: border and text turn green/amber/red with the verdict word. No IIFE — standard idiomatic React.

  **Note on font-size:** bumped from `text-[10px]` to `text-[11px] font-semibold` for the verdict label to increase visual weight when displaying the result.

  **Git Checkpoint:**
  ```bash
  git add my-app/src/components/analysis/AnalysisTimeline.tsx
  git commit -m "step 4: AnalysisTimeline header turns verdict colour on completion"
  ```

  **✓ Verification Test:**

  **Type:** Unit

  **Action:**
  ```bash
  grep -n "Analysis Complete\|headerBorderClass\|headerTextClass\|border-green-900\|Rework Required" \
    my-app/src/components/analysis/AnalysisTimeline.tsx
  ```

  **Expected:**
  - `"Analysis Complete"` → 0 matches (confirms OLD removed)
  - `headerBorderClass` → ≥ 2 matches (definition + JSX usage)
  - `headerTextClass` → ≥ 2 matches
  - `border-green-900` → 1 match
  - `Rework Required` → 1 match

  **Pass:** All five conditions met

  **Fail:**
  - If `Analysis Complete` still present → Change B not applied → re-apply the exact OLD→NEW string substitution above
  - If `headerBorderClass` absent → Change A not applied → insert the three const declarations before `return (`

---

- [ ] 🟥 **Step 5: Dashboard panel cards — 3 px verdict left border** — *Non-critical: isolated to dashboard page*

  **Step Architecture Thinking:**

  **Pattern applied:** Inline style override. The dashboard uses inline `style` objects (not Tailwind) for border — the existing `border: "1px solid rgba(255,255,255,0.09)"` shorthand must be split into individual border sides so `borderLeft` can carry the verdict colour at 3 px.

  **Why here in the sequence:** Follows Steps 3 and 4 to complete the verdict-first pass across all three data surfaces before moving to language cleanup.

  **Why `dashboard/page.tsx`:** The panel card `<div>` and the `riskLevel` variable derived from `score` are in this file. `riskLevel` is already computed; we just wire it to a border colour.

  **Alternative rejected:** Adding a `<div className="absolute left-0 inset-y-0 w-[3px]">` stripe inside the card. Rejected because it requires `relative` positioning and introduces a DOM node for cosmetic purposes; `borderLeft` achieves the same result.

  **What breaks if deviated:** If `border` shorthand is used alongside `borderLeft`, the shorthand wins (CSS specificity). The `border` key must be removed from the style object and replaced with the four individual border sides.

  ---

  **Idempotent:** Yes.

  **Pre-Read Gate:**
  - Read lines 312–340 of `my-app/src/app/(app)/dashboard/page.tsx` to confirm the exact current `style` object on the panel card `<div>`.
  - `grep -n "border: .1px solid rgba" my-app/src/app/\(app\)/dashboard/page.tsx` — must return exactly 1 match inside the `.map(({ panel, score, riskLevel })` callback.

  Replace the panel card `<div>`'s `style` object. The **exact string to replace** is the current style object inside the panel card `<div key={panel.id}>`:

  ```tsx
  // OLD style object — replace this:
  style={{
    background:
      "linear-gradient(160deg, #181c21 0%, #111316 60%)",
    border: "1px solid rgba(255,255,255,0.09)",
    borderTopColor: "rgba(255,255,255,0.14)",
    boxShadow:
      "0 1px 0 0 rgba(255,255,255,0.06) inset, 0 -1px 0 0 rgba(0,0,0,0.4) inset, 0 4px 8px rgba(0,0,0,0.35), 0 12px 28px rgba(0,0,0,0.3)",
  }}

  // NEW style object — replace with:
  style={{
    background:
      "linear-gradient(160deg, #181c21 0%, #111316 60%)",
    borderTop:    "1px solid rgba(255,255,255,0.14)",
    borderRight:  "1px solid rgba(255,255,255,0.09)",
    borderBottom: "1px solid rgba(255,255,255,0.09)",
    borderLeft: riskLevel === "green"
      ? "3px solid #22c55e"
      : riskLevel === "amber"
        ? "3px solid #f59e0b"
        : "3px solid #ef4444",
    boxShadow:
      "0 1px 0 0 rgba(255,255,255,0.06) inset, 0 -1px 0 0 rgba(0,0,0,0.4) inset, 0 4px 8px rgba(0,0,0,0.35), 0 12px 28px rgba(0,0,0,0.3)",
  }}
  ```

  **Git Checkpoint:**
  ```bash
  git add my-app/src/app/\(app\)/dashboard/page.tsx
  git commit -m "step 5: dashboard panel cards carry 3px verdict left border"
  ```

  **✓ Verification Test:**

  **Type:** Unit

  **Action:** `grep -n "borderLeft.*riskLevel\|3px solid" my-app/src/app/\(app\)/dashboard/page.tsx`

  **Expected:** 2+ matches — `borderLeft` with `riskLevel` condition and `3px solid` appear

  **Pass:** Both strings found

  **Fail:**
  - If `border: "1px solid rgba(255,255,255,0.09)"` still present → the shorthand was not replaced → re-apply the full style object substitution above

---

## Phase 3 — Operational Language

**Goal:** Every number, label, and identifier that a QA supervisor cannot interpret without training is either removed or translated. Four components are touched; no API contracts change.

---

- [ ] 🟥 **Step 6: `QualityReportCard.tsx` — remove `quality_class`, translate confidence and ISO, add feature display names** — *Non-critical: display-only changes*

  **Step Architecture Thinking:**

  **Pattern applied:** Display-name mapping (DRY). A single `FEATURE_DISPLAY` constant at the top of the file is the sole translation layer for feature variable names. `buildDriverBars` reads from it. `AGENT_DISPLAY` does the same for agent names in Assessment Details.

  **Why here:** Phases 1 and 2 complete. Operational language is polish that builds on the correct visual hierarchy already in place.

  **Why this file:** Both the `quality_class` line and the `buildDriverBars` label are in `QualityReportCard.tsx`. Centralising the display map here avoids cross-file coupling.

  **Alternative rejected:** Translating feature names in the backend before they reach the frontend. Rejected because feature names are already being used as identifiers in threshold violation data structures; translating them server-side would break the data contract. Display-name mapping at the render layer is the correct separation.

  **What breaks if deviated:** If `FEATURE_DISPLAY` is defined inside `buildDriverBars` instead of at module level, `AGENT_DISPLAY` cannot share the same scope without duplication.

  ---

  **Idempotent:** Yes.

  **Pre-Read Gate:**
  - `grep -n "quality_class\|FEATURE_DISPLAY\|AGENT_DISPLAY" my-app/src/components/analysis/QualityReportCard.tsx` — `quality_class` must be present, `FEATURE_DISPLAY` and `AGENT_DISPLAY` must be absent. If display maps already exist → compare and skip if identical.

  **Change A — Add two display-name constants** at the top of the file, immediately after the `import` block (after line 5, before the interface definitions):

  ```tsx
  /** Maps internal feature variable names → short operational labels for supervisor-facing display. */
  const FEATURE_DISPLAY: Record<string, string> = {
    heat_diss_max_spike:       "Peak heat dissipation",
    heat_input_min_rolling:    "Min rolling heat input",
    heat_input_drop_severity:  "Heat input drop",
    angle_deviation_mean:      "Torch angle deviation",
    angle_max_drift_1s:        "Torch angle drift (1 s)",
    voltage_cv:                "Voltage stability",
    amps_cv:                   "Current stability",
    heat_input_cv:             "Heat input consistency",
    arc_on_ratio:              "Arc continuity",
    heat_input_mean:           "Average heat input",
  };

  /** Maps agent code-names → operational display labels. */
  const AGENT_DISPLAY: Record<string, string> = {
    ThermalAgent:           "Heat Profile",
    GeometryAgent:          "Torch Angle",
    ProcessStabilityAgent:  "Arc Stability",
  };
  ```

  **Change B — Fix the metadata line** (currently line 210 in the file). Replace the exact string:

  ```tsx
  // OLD — replace this exact JSX expression:
  <p className="font-mono text-[10px] text-white/60 mt-2">
    {report.quality_class} · confidence {(report.confidence * 100).toFixed(1)}% · ISO{" "}
    {report.iso_5817_level}
  </p>

  // NEW:
  <p className="font-mono text-[10px] text-white/60 mt-2">
    {(report.confidence * 100).toFixed(0)}% confidence · ISO 5817 Grade {report.iso_5817_level}
  </p>
  ```

  **Change C — Use `FEATURE_DISPLAY` in `buildDriverBars`**. Replace the exact string inside the `scored` `.map()` call:

  ```tsx
  // OLD — replace this exact object key:
  label: item.feature,

  // NEW:
  label: FEATURE_DISPLAY[item.feature] ?? item.feature.replace(/_/g, " "),
  ```

  **Change D — Use `AGENT_DISPLAY` in Assessment Details specialist rows**. Replace the exact string inside the `{specialistRows.map(…)}` block:

  ```tsx
  // OLD — replace this exact JSX expression (in the <summary> element):
  {row.agent_name}
  {row.disposition ? ` · ${row.disposition}` : ""}

  // NEW:
  {AGENT_DISPLAY[row.agent_name] ?? row.agent_name}
  {row.disposition ? ` · ${row.disposition.replace("_", " ")}` : ""}
  ```

  **Git Checkpoint:**
  ```bash
  git add my-app/src/components/analysis/QualityReportCard.tsx
  git commit -m "step 6: report card removes quality_class, translates labels and feature names"
  ```

  **✓ Verification Test:**

  **Type:** Unit

  **Action:**
  ```bash
  grep -n "quality_class\|FEATURE_DISPLAY\|AGENT_DISPLAY\|ISO 5817 Grade" my-app/src/components/analysis/QualityReportCard.tsx
  grep -n "AGENT_DISPLAY\[row\.agent_name\]" my-app/src/components/analysis/QualityReportCard.tsx
  ```

  **Expected:**
  - `quality_class` appears 0 times in JSX (may still appear in the `WarpReport` type import — check it is not in a JSX expression)
  - `FEATURE_DISPLAY` appears ≥ 2 times (definition + usage in `buildDriverBars`)
  - `AGENT_DISPLAY` appears ≥ 2 times (definition + call site)
  - `ISO 5817 Grade` appears 1 time
  - `AGENT_DISPLAY[row.agent_name]` appears ≥ 1 time (confirms Change D was applied to the `<summary>` JSX, not just the constants block)

  **Pass:** All five conditions met

  **Fail:**
  - If `quality_class` still in JSX → Change B not applied → re-apply the exact string substitution
  - If `FEATURE_DISPLAY` absent → Change A not applied → add the constants block
  - If `AGENT_DISPLAY[row.agent_name]` absent → Change D not applied → re-apply the `<summary>` JSX substitution

---

- [ ] 🟥 **Step 7: `WelderTrendChart.tsx` — fix `"COND"` to `"Review"` and remove score from tooltip** — *Non-critical: isolated*

  **Idempotent:** Yes.

  **Pre-Read Gate:**
  - `grep -n "COND\|yTickFormatter\|formatter.*disposition" my-app/src/components/analysis/WelderTrendChart.tsx`
  - Confirm `"COND"` is in `yTickFormatter` at line ~52 and the tooltip `formatter` returns `${disposition} (${n})`.

  **Change A — Fix `yTickFormatter`** (replace the function body, lines 49–54):

  ```tsx
  // OLD:
  function yTickFormatter(value: number): string {
    if (value === 1.0) return "PASS";
    if (value === 0.5) return "COND";
    if (value === 0.0) return "REWORK";
    return String(value);
  }

  // NEW:
  function yTickFormatter(value: number): string {
    if (value === 1.0) return "Pass";
    if (value === 0.5) return "Review";
    if (value === 0.0) return "Rework";
    return String(value);
  }
  ```

  **Change B — Fix tooltip formatter** to show disposition label only, no numeric score. Replace the entire `formatter` prop on `<Tooltip>`:

  ```tsx
  // OLD:
  formatter={(value, _name, item) => {
    const row =
      item &&
      typeof item === "object" &&
      "payload" in item
        ? (item.payload as ChartRow | undefined)
        : undefined;
    const disposition = row?.disposition ?? "";
    const n =
      typeof value === "number" && Number.isFinite(value)
        ? value
        : "—";
    return [`${disposition} (${n})`, "Quality"];
  }}

  // NEW:
  formatter={(_value, _name, item) => {
    const row =
      item && typeof item === "object" && "payload" in item
        ? (item.payload as ChartRow | undefined)
        : undefined;
    const d = row?.disposition ?? "";
    const label =
      d === "REWORK_REQUIRED" ? "Rework Required"
      : d === "CONDITIONAL"   ? "Conditional"
      : d === "PASS"          ? "Pass"
      : d;
    return [label, "Result"];
  }}
  ```

  **Git Checkpoint:**
  ```bash
  git add my-app/src/components/analysis/WelderTrendChart.tsx
  git commit -m "step 7: trend chart Y-axis uses Pass/Review/Rework; tooltip drops score"
  ```

  **✓ Verification Test:**

  **Type:** Unit

  **Action:** `grep -n '"COND"\|"PASS"\|"Review"\|Rework Required' my-app/src/components/analysis/WelderTrendChart.tsx`

  **Expected:**
  - `"COND"` appears 0 times
  - `"Review"` appears 1 time
  - `"Rework Required"` appears 1 time

  **Pass:** `"COND"` absent; `"Review"` and `"Rework Required"` present

---

- [ ] 🟥 **Step 8: `SpecialistCard.tsx` — operational domain labels** — *Non-critical: 3-value dict change*

  **Idempotent:** Yes.

  **Pre-Read Gate:**
  - `grep -n "STAGE_LABEL\|thermal_agent\|Thermal\|Geometry\|Process" my-app/src/components/analysis/SpecialistCard.tsx`
  - Confirm `STAGE_LABEL` dict exists with values `"Thermal"`, `"Geometry"`, `"Process"`.

  Replace the `STAGE_LABEL` dict values (lines 7–11). The exact string to replace:

  ```tsx
  // OLD:
  const STAGE_LABEL: Record<AgentStage, string> = {
    thermal_agent:  "Thermal",
    geometry_agent: "Geometry",
    process_agent:  "Process",
  };

  // NEW:
  const STAGE_LABEL: Record<AgentStage, string> = {
    thermal_agent:  "Heat Profile",
    geometry_agent: "Torch Angle",
    process_agent:  "Arc Stability",
  };
  ```

  **Git Checkpoint:**
  ```bash
  git add my-app/src/components/analysis/SpecialistCard.tsx
  git commit -m "step 8: specialist cards use operational domain labels"
  ```

  **✓ Verification Test:**

  **Type:** Unit

  **Action:** `grep -n "Heat Profile\|Torch Angle\|Arc Stability\|\"Thermal\"\|\"Geometry\"\|\"Process\"" my-app/src/components/analysis/SpecialistCard.tsx`

  **Expected:**
  - `"Thermal"`, `"Geometry"`, `"Process"` appear 0 times as dict values
  - `"Heat Profile"`, `"Torch Angle"`, `"Arc Stability"` each appear 1 time

  **Pass:** Old labels absent; new labels present

---

- [ ] 🟥 **Step 9: `specialists.py` — human-readable feature names in `_threshold_fallback`** — *Non-critical: backend display text only*

  **Idempotent:** Yes.

  **Pre-Read Gate:**
  - `grep -n "_FEATURE_LABELS\|heat_diss_max_spike.*replace\|_threshold_fallback" backend/agent/specialists.py`
  - Confirm `_threshold_fallback` exists, `_FEATURE_LABELS` does NOT exist, and the corrective action line uses `v.feature.replace("_", " ")`.

  **Change A — Add `_FEATURE_LABELS` dict** at module level in `specialists.py`, immediately after the `logger = logging.getLogger(__name__)` line:

  ```python
  # Human-readable display names for threshold features — used in _threshold_fallback()
  # corrective actions so the user-facing report never shows raw Python variable names.
  _FEATURE_LABELS: dict[str, str] = {
      "heat_diss_max_spike":       "peak heat dissipation rate",
      "heat_input_min_rolling":    "minimum rolling heat input",
      "heat_input_drop_severity":  "heat input drop severity",
      "angle_deviation_mean":      "average torch angle deviation",
      "angle_max_drift_1s":        "max torch angle drift (1 s)",
      "voltage_cv":                "voltage consistency (CV)",
      "amps_cv":                   "current consistency (CV)",
      "heat_input_cv":             "heat input consistency (CV)",
      "arc_on_ratio":              "arc continuity ratio",
      "heat_input_mean":           "average heat input",
  }
  ```

  **Change B — Use `_FEATURE_LABELS` in `_threshold_fallback`**. Three substitutions inside the method body. Replace these exact strings:

  ```python
  # OLD root_cause for risk — replace:
  feat_list  = ", ".join(v.feature.replace("_", " ") for v in risk_viols)

  # NEW:
  feat_list  = ", ".join(_FEATURE_LABELS.get(v.feature, v.feature.replace("_", " ")) for v in risk_viols)
  ```

  ```python
  # OLD root_cause for marginal — replace:
  feat_list  = ", ".join(v.feature.replace("_", " ") for v in marginal_viols)

  # NEW:
  feat_list  = ", ".join(_FEATURE_LABELS.get(v.feature, v.feature.replace("_", " ")) for v in marginal_viols)
  ```

  ```python
  # OLD corrective action — replace:
  corrective_actions.append(
      f"Adjust {v.feature.replace('_', ' ')} {direction} "
      f"{v.threshold}{unit_str} (current: {v.value:.3g}{unit_str})"
  )

  # NEW:
  label = _FEATURE_LABELS.get(v.feature, v.feature.replace("_", " "))
  corrective_actions.append(
      f"Adjust {label} {direction} "
      f"{v.threshold}{unit_str} (current: {v.value:.3g}{unit_str})"
  )
  ```

  **Git Checkpoint:**
  ```bash
  git add backend/agent/specialists.py
  git commit -m "step 9: threshold fallback uses human-readable feature labels in corrective actions"
  ```

  **✓ Verification Test:**

  **Type:** Unit

  **Action:** `grep -n "_FEATURE_LABELS\|peak heat dissipation" backend/agent/specialists.py`

  **Expected:** `_FEATURE_LABELS` defined (1 match for the dict name) + `"peak heat dissipation rate"` present as a value

  **Pass:** Both strings found

  **Fail:**
  - If `_FEATURE_LABELS` absent → Change A not applied → add the dict block after `logger = logging.getLogger(__name__)`

---

## Regression Guard

| System | Pre-change behaviour | Post-change verification |
|---|---|---|
| Analysis page routing | `AppNav` routes to `/analysis` | Navigate to `/analysis` — sidebar "Analysis" item is active (amber border) |
| Dashboard routing | `AppNav` routes to `/dashboard` | Navigate to `/dashboard` — sidebar "Overview" item is active |
| Analysis page height | `h-full` fills below-nav space | `AnalysisTimeline` fills full content height with no scrollbar on outer container |
| Session row selection | Amber border appears on click | Click a session — amber border overrides disposition colour ✓; click another — first row reverts to disposition colour |
| WelderTrendChart | Y-axis shows "PASS"/"COND"/"REWORK" | Y-axis shows "Pass"/"Review"/"Rework" — no "COND" |
| SpecialistCard done | Shows "Thermal" / "Geometry" / "Process" | Shows "Heat Profile" / "Torch Angle" / "Arc Stability" |

---

## Rollback

```bash
# Revert all steps (newest first)
git revert HEAD~8..HEAD --no-commit && git commit -m "revert: roll back frontend integration plan"

# Or revert individual steps by their commit hash (recorded at each git checkpoint above)
```

---

## Success Criteria

| Rule | Target | Verification |
|---|---|---|
| Rule 1 — Verdict first | Session list: disposition visible at glance without clicking | Open `/analysis` — every analysed session row has a coloured left border before any row is clicked |
| Rule 1 — Verdict first | Timeline: verdict visible in header on completion | Run analysis on any session — header turns green/amber/red with the disposition word when streaming ends |
| Rule 1 — Verdict first | Dashboard: verdict visible at card level | Open `/dashboard` — each panel card has a 3 px left border in its risk colour |
| Rule 3 — Operational language | Report shows no `quality_class` | Run analysis → open report → `MARGINAL` / `GOOD` / `DEFECTIVE` not visible anywhere in the card |
| Rule 3 — Operational language | Confidence as `%` not decimal | Report shows e.g. `87% confidence` not `0.87` |
| Rule 3 — Operational language | ISO label full | Report shows `ISO 5817 Grade C` not `ISO C` |
| Rule 3 — Operational language | Specialist cards say `Heat Profile` | SpecialistCard done state shows `Heat Profile`, `Torch Angle`, `Arc Stability` |
| Navigation | Sidebar renders on all app routes | Visit `/analysis`, `/dashboard`, `/ai`, `/admin/thresholds` — sidebar present on all four |
| Navigation | Collapse toggle persists | Collapse sidebar, refresh browser — sidebar stays collapsed |

---

⚠️ **Do not mark a step 🟩 Done until its verification test passes.**
⚠️ **Do not proceed past Phase 1 without confirming the app compiles (`npx tsc --noEmit`).**
⚠️ **Never modify files not named in the current step.**
⚠️ **Each step gets its own git commit — do not batch.**
