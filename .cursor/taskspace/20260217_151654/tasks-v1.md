
Refined strategy output:

---

```markdown
════════════════════════════════════════════════════════════════
🧠 CTO TASK PRIORITIZATION - TOP 3 TASKS (REFINED)
════════════════════════════════════════════════════════════════
User Focus: "plan"
Context Type: general
Strategy Score: 8.5/10
Average Priority: 8.4/10
Regression: None | Critique Applied: Yes (parallel + tight-time guidance)

## 🔥 Top Priority (Execute Today)

### 1. Add Seagull to AppNav for Discoverability
**Priority:** 9.0/10 | **Impact:** 9/10 | **Effort:** 0.5hrs | **Risk:** Low

**Why:** Seagull pilot is built but only reachable via direct URL; both investors (team dashboard during demos) and operators (welder reports) need a visible entry point in the main nav.

**Opus Analysis:**
- **Leverage:** High — surfaces existing feature to both audiences; unblocks demo flow
- **Optionality:** Enables future team/operator flows from dashboard
- **Bottleneck:** Seagull undiscoverable — direct fix
- **Context fit:** "plan" context favors discoverability + docs (learnings)
- **Reversibility:** Type B — trivial to revert

**Command:**
```bash
./agent "Add Seagull Team Dashboard link to AppNav in my-app/src/components/AppNav.tsx. Add a link to /seagull with label 'Team' (or 'Seagull'), styled consistently with Dashboard link (text-sm font-medium, zinc/blue). Add isSeagull pathname check for aria-current when pathname starts with /seagull. Ensure it renders in the (app) layout nav bar alongside Home, Dashboard, Demo."
```

**Memory:** Learnings: specific file path; dual-audience value; quick win pattern for task 3 — but highest impact here justifies Task 1.

---

### 2. WarpSense Theme Audit for Seagull Pages
**Priority:** 8.3/10 | **Impact:** 7/10 | **Effort:** 1.5hrs | **Risk:** Low

**Why:** Replay, Demo, Dashboard use WarpSense (blue/violet); Seagull may still use legacy cyan/amber. Visual consistency strengthens the "team management" story for both audiences.

**Opus Analysis:**
- **Systems thinking:** Finishes WarpSense rebrand for Seagull
- **Compounding:** Sets pattern for future Seagull pages
- **Risk:** Reversible — can rollback color changes
- **Parallelizable:** Can run alongside Task 3 if desired
- **Dependencies:** None — can start after Task 1

**Command:**
```bash
./agent "Audit my-app/src/app/seagull/page.tsx and my-app/src/app/seagull/welder/[id]/page.tsx for WarpSense theme consistency. Replace any cyan (text-cyan, #22d3ee), amber (text-amber), or red accents with blue/violet from theme.ts (CHART_PALETTE, ERROR_HEX). Update FeedbackPanel and LineChart usage in welder report to match. Verify loading and error states use blue/violet. Ensure no legacy heatmap/thermal colors contradict WarpSense palette."
```

**Risk Mitigation:** Isolated to Seagull pages; no shared components mutated. Test both team list and welder report views.

---

### 3. Update CONTEXT.md with Seagull, TorchWithHeatmap3D, WarpSense
**Priority:** 8.1/10 | **Impact:** 7/10 | **Effort:** 1hr | **Risk:** Low

**Why:** Stale CONTEXT.md causes agents to suggest already-built features (e.g. "add Seagull") or outdated patterns (HeatmapPlate3D in replay). High leverage for maintainability and AI tooling.

**Opus Analysis:**
- **Leverage:** Single source of truth; reduces reimplementation
- **Optionality:** Keeps future sessions aligned with real project state
- **Information value:** Documents current architecture for all agents
- **Quick win:** 1hr fits learnings' task-3 preference
- **Tight-time path:** With <2hr budget, do Task 1 + Task 3 first (discoverability + docs)

**Command:**
```bash
./agent "Update CONTEXT.md in project root: (1) Add Seagull pilot to Implemented Features — app/seagull/page.tsx (team dashboard), app/seagull/welder/[id]/page.tsx (welder report), lib/ai-feedback.ts, FeedbackPanel component. (2) In Replay/3D and Frame Data Flow sections, state that replay and demo use TorchWithHeatmap3D (unified torch+thermal metal); HeatmapPlate3D deprecated for replay. (3) Add WarpSense branding note under Visual Consistency: blue/purple gradient, no cyan/amber. Keep existing structure."
```

**Memory:** Quick win; maintainability; specific paths; AI-tool leverage.

════════════════════════════════════════════════════════════════
💡 STRATEGIC RATIONALE
════════════════════════════════════════════════════════════════

**Focus:** Discoverability + visual consistency + documentation (plan context)  
**Bottleneck:** Seagull undiscoverable; WarpSense rebrand incomplete for Seagull; CONTEXT.md stale  
**Time Budget:** ~3hrs (0.5 + 1.5 + 1)

**Execution Order:**
1. **Default:** 1 → 2 → 3 (recommended)
2. **Parallel option:** Task 1 first, then Tasks 2 and 3 in parallel (2–3 hrs)
3. **Tight time (<2hr):** Task 1 + Task 3 only (discoverability + docs); defer Task 2

**Why These 3:**
1. Task 1: Highest leverage, unblocks demo flow, 0.5hr
2. Task 2: Finishes WarpSense for Seagull, parallelizable
3. Task 3: High AI/maintainability leverage, quick win, optional before Task 2 under tight time

**What We're NOT Doing:**
- Streaming/pagination for >10k frames
- Backend ingestion optimization
- SEAGULL_IMPLEMENTATION_GAP_ANALYSIS update (lower than CONTEXT.md)

**Critique Applied:**
- Preserved all three tasks (no critical issues)
- Added parallel execution guidance (Tasks 2 & 3)
- Added tight-time path (1 + 3 before 2)
- Slightly boosted Task 1 priority (8.9 → 9.0) from critique score
- Clarified Frame Data Flow update in Task 3 command

**Next CTO Run:** After these complete, reassess for demo playback UX (smooth start, expert/novice labels) or full test suite.

════════════════════════════════════════════════════════════════
📝 LEARNING UPDATE (Append to .cursor/memory/learnings.md)
════════════════════════════════════════════════════════════════

- [2026-02-17] general: when user context is minimal ("plan"), prioritize discoverability + documentation; Seagull existed but was hidden until AppNav task surfaced it
- [2026-02-17] general: critique suggested Task 2 and 3 parallelizable; under tight time (<2hr), Task 1 + Task 3 covers discoverability and docs before theme audit

════════════════════════════════════════════════════════════════
```

---

**Self-check:**
- [x] No regression; no high-value tasks dropped
- [x] Critique applied (parallel execution + tight-time path)
- [x] Opus-style prioritization applied
- [x] Top 3 tasks only
- [x] Tasks specific and actionable
- [x] Commands ready for `./agent`
- [x] Strategic rationale and tradeoffs clear
- [x] No blockers; Task 2 and 3 can run in parallel
