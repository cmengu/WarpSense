════════════════════════════════════════════════════════════════
🧠 CTO TASK PRIORITIZATION - TOP 3 TASKS
════════════════════════════════════════════════════════════════
User Focus: "plan"
Strategy Score: 8.2/10
Average Priority: 8.1/10

## 🔥 Top Priority (Execute Today)

### 1. Add Seagull to AppNav for Discoverability
**Priority:** 9.0/10 | **Impact:** 9/10 | **Effort:** 0.5hrs | **Risk:** Low

**Why:** Seagull pilot is built but only reachable via direct URL; both investors (team dashboard during demos) and operators (welder reports) need a visible entry point in the main nav.

**Opus Analysis:**
- **Leverage:** High — surfaces existing feature to both audiences; unblocks demo flow
- **Optionality:** Enables future team/operator flows from dashboard
- **Bottleneck:** Seagull undiscoverable — direct fix
- **Context fit:** "plan" context favors discoverability + docs
- **Reversibility:** Type B — trivial to revert

**Command:**
```bash
./agent "Add Seagull Team Dashboard link to AppNav in my-app/src/components/AppNav.tsx. Add a link to /seagull with label 'Team' (or 'Seagull'), styled consistently with Dashboard link (text-sm font-medium, zinc/blue). Add isSeagull pathname check for aria-current when pathname starts with /seagull. Ensure it renders in the (app) layout nav bar alongside Home, Dashboard, Demo. After implementing, verify: navigate to /seagull via the new nav link and confirm team list loads; check aria-current on /seagull and /seagull/welder/[id]."
```

**Memory:** Learnings: specific file path; dual-audience value; quick win pattern. Critique: explicit verification step improves execution quality.

---

### 2. Update CONTEXT.md with Seagull, TorchWithHeatmap3D, WarpSense
**Priority:** 8.4/10 | **Impact:** 8/10 | **Effort:** 1hr | **Risk:** Low

**Why:** Stale CONTEXT.md causes agents to suggest already-built features (e.g. "add Seagull") or outdated patterns (HeatmapPlate3D in replay). High leverage for maintainability and AI tooling. Strong plan-context fit: docs before theme polish.

**Opus Analysis:**
- **Leverage:** Single source of truth; reduces reimplementation
- **Optionality:** Keeps future sessions aligned with real project state
- **Information value:** Documents current architecture for all agents
- **Quick win:** 1hr fits learnings' task-3 preference
- **Context alignment:** Strong fit for "plan" context (9.0)

**Command:**
```bash
./agent "Update CONTEXT.md in project root: (1) Add Seagull pilot to Implemented Features — app/seagull/page.tsx (team dashboard), app/seagull/welder/[id]/page.tsx (welder report), lib/ai-feedback.ts, FeedbackPanel component. (2) In Replay/3D and Frame Data Flow sections, state that replay and demo use TorchWithHeatmap3D (unified torch+thermal metal); HeatmapPlate3D deprecated for replay. (3) Add WarpSense branding note under Visual Consistency: blue/purple gradient, no cyan/amber. (4) Fix Last Updated date: 2025-02-16 → 2026-02-17. Keep existing structure. After updating, verify: grep -i seagull CONTEXT.md returns matches for team dashboard and welder report."
```

**Risk Mitigation:** None — low risk, isolated to docs.

---

### 3. WarpSense Theme Audit for Seagull Pages (Quick Win)
**Priority:** 6.9/10 | **Impact:** 7/10 | **Effort:** 1.5hrs | **Risk:** Low

**Why:** Replay, Demo, Dashboard use WarpSense (blue/violet); Seagull may still use legacy cyan/amber. Visual consistency strengthens the "team management" story. Lower resource efficiency than Tasks 1–2; defer when time is tight.

**Opus Analysis:**
- **Systems thinking:** Completes WarpSense rebrand for Seagull
- **Compounding:** Sets pattern for future Seagull pages
- **Risk:** Reversible — can rollback color changes
- **Resource efficiency:** Lower than Tasks 1 and 2 (1.5hr for moderate impact); plan context favors docs over theme polish

**Command:**
```bash
./agent "Audit my-app/src/app/seagull/page.tsx and my-app/src/app/seagull/welder/[id]/page.tsx for WarpSense theme consistency. Replace any cyan (text-cyan, #22d3ee), amber (text-amber), or red accents with blue/violet from theme.ts (CHART_PALETTE, ERROR_HEX). Update FeedbackPanel and LineChart usage in welder report to match. Verify loading and error states use blue/violet. Ensure no legacy heatmap/thermal colors contradict WarpSense palette. After implementing, manually verify blue/violet on both /seagull and /seagull/welder/[id] pages (no cyan/amber visible)."
```

**Risk Mitigation:** Isolated to Seagull pages; no shared components mutated. **Defer under <2.5hr budget** — do Tasks 1 and 2 first.

════════════════════════════════════════════════════════════════
💡 STRATEGIC RATIONALE
════════════════════════════════════════════════════════════════

**Focus:** Discoverability → documentation → visual consistency (plan-context order)
**Bottleneck:** Seagull undiscoverable; CONTEXT.md stale; WarpSense incomplete for Seagull
**Time Budget:** ~3hrs (0.5 + 1 + 1.5)

**Execution Order:** 1 → 2 → 3 (critique-applied)
- **Plan context:** Docs before theme polish. Discoverability first, CONTEXT.md second, WarpSense last.
- **Tight time (<2.5hr):** Task 1 + Task 2 only; defer Task 3.

**Why These 3:**
1. Task 1: Highest leverage (9.0), unblocks demo flow, 0.5hr quick win
2. Task 2: Strong plan-context fit (8.4), docs > theme for planning; high AI/maintainability leverage
3. Task 3: Lowest priority (6.9), theme polish; valid but defer under tight time

**What We're NOT Doing:**
- Streaming/pagination for >10k frames
- Backend ingestion optimization
- SEAGULL_IMPLEMENTATION_GAP_ANALYSIS update (lower than CONTEXT.md)

**Critique Fixes Applied (v4):**
- **Task 2:** Added CONTEXT.md date fix (2025-02-16 → 2026-02-17)
- **Task 3 verification:** Corrected — grep belongs to Task 2; Task 3 now has its own visual verification: "manually verify blue/violet on both Seagull pages"
- **Order:** Kept 1→2→3 per critique verdict
- **Deferral:** Retained "defer Task 3 when <2.5hr budget"

**Next CTO Run:** After these complete, reassess for demo playback UX (smooth start, expert/novice labels) or full test suite.

════════════════════════════════════════════════════════════════
