
Here is the CTO Task Prioritization output:

```markdown
════════════════════════════════════════════════════════════════
🧠 CTO TASK PRIORITIZATION - TOP 3 TASKS
════════════════════════════════════════════════════════════════
User Focus: "plan"
Context Type: general
Strategy Score: 8.2/10
Average Priority: 8.3/10
Memory Applied: yes — learnings.md loaded (specific paths, dual-audience, quick wins for task 3)

## 🔥 Top Priority (Execute Today)

### 1. Add Seagull to AppNav for Discoverability
**Priority:** 8.7/10 | **Impact:** 8/10 | **Effort:** 0.5hrs | **Risk:** Low

**Why (dual-audience):**
- Investor value: Team dashboard becomes discoverable during demos; reinforces "team management" story
- Operator value: Direct path to welder reports from main nav instead of needing URL

**Principle applied:** Principle 1 — Value Delivery > Technical Elegance (stakeholders notice discoverability)

**Opus Analysis:**
- Leverage: Makes Seagull pilot reachable; surfaces existing feature
- Optionality: Enables future team/operator flows from dashboard
- Bottleneck: Seagull currently only reachable via direct URL; hidden to both audiences

**Acceptance criteria:**
- [ ] AppNav shows "Team" or "Seagull" link next to Dashboard and Demo
- [ ] Link routes to `/seagull`; active state when pathname starts with `/seagull`

**Command:**
```bash
./agent "Add Seagull Team Dashboard link to AppNav in my-app/src/components/AppNav.tsx. Add a link to /seagull with label 'Team' (or 'Seagull'), styled consistently with Dashboard link. Add isSeagull pathname check for aria-current. Ensure it renders in the (app) layout nav bar."
```

**Memory note:** Learnings: specific file path in command; dual-audience (investors see team view, operators get entry point). Quick win aligns with task-3 preference.

---

### 2. WarpSense Theme Audit for Seagull Pages
**Priority:** 8.2/10 | **Impact:** 7/10 | **Effort:** 1.5hrs | **Risk:** Low

**Why (dual-audience):**
- Investor value: Consistent blue/violet branding; no legacy cyan/amber after rebrand
- Operator value: Coherent visual system across Team, Replay, Compare, Demo

**Principle applied:** Principle 1 — Value Delivery > Technical Elegance (visual consistency strengthens perception)

**Opus Analysis:**
- Leverage: Completes WarpSense rebrand for Seagull (rebrand done for TorchViz, HeatmapPlate, Dashboard)
- Optionality: Sets pattern for future pages
- Bottleneck: Seagull may still use pre-rebrand colors; context shows cyan→blue, amber→violet changes elsewhere

**Acceptance criteria:**
- [ ] No cyan, amber, or red accents in seagull/page.tsx or seagull/welder/[id]/page.tsx
- [ ] Loading/error/CTA states use blue/violet per WarpSense theme
- [ ] FeedbackPanel and LineChart in welder report align with theme.ts palette

**Command:**
```bash
./agent "Audit my-app/src/app/seagull/page.tsx and my-app/src/app/seagull/welder/[id]/page.tsx for WarpSense theme consistency. Replace any cyan (text-cyan, #22d3ee), amber (text-amber), or red accents with blue/violet from theme.ts (CHART_PALETTE, ERROR_HEX). Update FeedbackPanel and LineChart usage in welder report to match. Verify loading and error states use blue/violet."
```

**Memory note:** Learnings: demo context prefers UI polish; dual-audience theme consistency; specific file paths.

---

### 3. Update CONTEXT.md with Seagull, TorchWithHeatmap3D, WarpSense
**Priority:** 7.8/10 | **Impact:** 6/10 | **Effort:** 1hr | **Risk:** Low

**Why (dual-audience):**
- Investor value: Indirect (better AI suggestions reduce wasted work)
- Operator value: Indirect (agents stop suggesting already-built features)

**Principle applied:** Principle 6 — Documented Decisions > Undocumented Flexibility; Principle 7 — Optimize for Maintainability

**Opus Analysis:**
- Leverage: CONTEXT.md is used by AI tools; stale docs cause reimplementation
- Optionality: Keeps single source of truth for project state
- Bottleneck: CONTEXT still describes HeatmapPlate3D for replay; omits Seagull pilot; missing WarpSense branding note

**Acceptance criteria:**
- [ ] Implemented Features includes Seagull Team Dashboard and Welder Report
- [ ] Replay section notes TorchWithHeatmap3D (not HeatmapPlate3D) for thermal replay
- [ ] Visual Consistency references WarpSense blue/purple palette

**Command:**
```bash
./agent "Update CONTEXT.md in project root: (1) Add Seagull pilot to Implemented Features — app/seagull/page.tsx (team dashboard), app/seagull/welder/[id]/page.tsx (welder report), lib/ai-feedback.ts, FeedbackPanel component. (2) In Replay/3D section, state that replay and demo use TorchWithHeatmap3D (unified torch+thermal metal), not HeatmapPlate3D. (3) Add WarpSense branding note under Visual Consistency: blue/purple gradient, no cyan/amber. Keep existing structure."
```

**Memory note:** Quick win (<2hr); maintainability-focused; learnings favor specific file paths in command.

════════════════════════════════════════════════════════════════
💡 STRATEGIC RATIONALE
════════════════════════════════════════════════════════════════

**Current bottleneck:** Seagull pilot exists but is undiscoverable (no nav link); visual consistency with WarpSense rebrand may be partial; CONTEXT.md is out of date and can mislead agents.

**What we're NOT doing:** Streaming/pagination for >10k frames (deferred until operator scale blocks); backend ingestion optimization (low investor visibility for "plan"); docs/SEAGULL_IMPLEMENTATION_GAP_ANALYSIS.md update (lower priority than CONTEXT.md).

**Next session focus:** After Seagull discoverability and theme audit: consider demo page playback UX polish (smooth start, clearer expert/novice labels) or run full test suite to verify WarpSense + metal clipping changes.

════════════════════════════════════════════════════════════════
📝 LEARNING UPDATE (Append to .cursor/memory/learnings.md)
════════════════════════════════════════════════════════════════

- [2026-02-17] general: when user context is minimal ("plan"), prioritize discoverability + documentation tasks; Seagull exists but was hidden until AppNav task surfaced it
```
