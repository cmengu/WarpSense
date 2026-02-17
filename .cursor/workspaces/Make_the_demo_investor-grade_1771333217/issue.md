
Here’s what was created:

## Issue Created

**File:** `.cursor/issues/investor-grade-demo-guided-tour-seagull.md`  
**Title:** `[Feature] Investor-grade demo: guided tour, narrative overlays, and browser-only Seagull enterprise path`

---

## Summary of the Issue

### Findings from the codebase

1. **`/demo` (browser-only)**  
   - Side‑by‑side expert vs novice, 94 vs 42 scores  
   - No guided tour or narrative overlays  
   - No link to team/Seagull  
   - No AppNav on the demo layout

2. **`/seagull` (backend-dependent)**  
   - Team dashboard and welder report with AI feedback  
   - Uses `fetchSession` and `fetchScore` → fails without backend + seeded data  
   - Not linked in AppNav and not usable for zero-setup investor demos

3. **Gap:**  
   - Demo lacks narrative for non-technical investors  
   - Seagull tells the enterprise story but needs backend  
   - There is no single investor flow from demo to team management

### Proposed scope

| In scope | Effort |
|----------|--------|
| Guided tour on /demo (2–4 steps, skip, narrative) | 8–12 h |
| Preset scenarios (e.g. highlight 2.3s novice spike) | 2–4 h |
| “See Team Management” CTA from demo | 1–2 h |
| Browser-only team path (dashboard + welder report) | 8–16 h |
| Seagull/Team link in AppNav | ~1 h |
| Narrative copy (placeholder or final) | 2–4 h |

**Total estimate:** 24–40 hours

### Decisions captured

- Tour: skippable, 2–4 steps, non-technical language  
- Team path: `/demo/team` or similar browser-only route using `demo-data.ts`  
- Seagull: add Team link to AppNav; browser-only path for investor demos  

---

## Next steps

1. Share with stakeholder (5 min)  
2. Resolve open questions (Q1–Q10) before exploration  
3. Phase 2: Explore feature (technical approaches, data flow)  
4. Phase 3: Create plan (step-by-step implementation)

The issue includes pre-issue thinking (brain dump, question storm, five whys), current state, desired outcome, scope boundaries, constraints, risks, and open questions. It’s ready to use for exploration and planning.
