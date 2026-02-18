
I've written the issue spec and saved it to `.cursor/issues/10-mock-welders-with-skill-arcs.md`. Here's what it contains:

**Summary**

- **Type:** Feature – add 10 welder archetypes with distinct skill arcs for sales demos  
- **Root cause:** No mock data layer for archetypes and no arc-driven frame generation  
- **Current state:** Tables for mock sessions, seed/wipe, dashboard, welder report, scoring, and APIs  
- **Gaps:** 2 welders only, no coaching badges, no arc-aligned frame data, hardcoded score history  

**Desired outcome**

1. 10 welder cards (Mike Chen, Sara Okafor, James Park, Lucia Reyes, Tom Bradley, Ana Silva, Derek Kwon, Priya Nair, Marcus Bell, Expert Benchmark)  
2. Coaching badges: green "On track", amber "Needs attention", neutral  
3. Arc-driven frame generation so heatmaps and micro-feedback align with each arc  
4. Real score history for the welder report trend chart  

**Technical notes**

- Reuse `operator_id` as welder identifier (no DB change)  
- Fix typo: `bae` → `base` in the score formula  
- Session IDs: `sess_{welder_id}_{001..00n}`  
- Wipe extended to remove all ~45 mock sessions  

**Effort:** M (8–16h total: ~10h backend, ~3h frontend, ~2h tests, ~1h review)
