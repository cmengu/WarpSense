
Here’s the implementation blueprint and how it’s structured:

---

## Implementation blueprint

**Location:** `.cursor/plans/investor-grade-demo-implementation-plan.md`

### Summary

**Pre-planning synthesis**
- Core approach: Custom tour overlay plus dedicated `/demo/team` route using `getDemoTeamData` and `createMockScore`.
- Main risks: Tour z-index, mock score shape, browser-only vs API path divergence. Each has mitigations.
- Dependencies: `seagull-demo-data` → team pages → tour config → DemoTour → demo integration. AppNav can be done in parallel.

**Phase breakdown**

| Phase | Goal | Est. Time |
|-------|------|-----------|
| **Phase 1: Browser-only team path** | Team dashboard + welder report without backend | ~7.5h |
| **Phase 2: Guided tour** | 2–4 step narrative overlay with optional scrub | ~5h |
| **Phase 3: CTA, AppNav, polish** | Full investor flow with discoverable team path | ~2.5h |

**Steps (11 total)**

- **Phase 1:** createMockScore + getDemoTeamData, team dashboard, welder report, unit tests, invalid welderId handling
- **Phase 2:** Tour config, DemoTour component (with code), integration into demo page
- **Phase 3:** CTA, AppNav Team link, responsive/a11y polish

**Artifacts in the plan**

1. Full code for:
   - `lib/seagull-demo-data.ts` (createMockScore, getDemoTeamData)
   - `app/demo/team/[welderId]/page.tsx` (welder report structure)
   - `components/demo/DemoTour.tsx` (overlay, `z-[200]`, `useEffect`)

2. Verification tests for every step, with pass criteria and common failure modes

3. Risk heatmap (~16 risks) with mitigations and detection signals

4. Thinking checkpoints for phase sanity, step quality, and final review

**Implementation order**

1. Create `lib/seagull-demo-data.ts` (Step 1.1) — base for team path  
2. Create `app/demo/team/page.tsx` (Step 1.2)  
3. Create `app/demo/team/[welderId]/page.tsx` (Step 1.3)  
4. Add unit tests and invalid-ID handling (Steps 1.4–1.5)  
5. Create `lib/demo-tour-config.ts` and `components/demo/DemoTour.tsx` (Phase 2)  
6. Integrate tour and CTA into the demo page (Phase 3)  
7. Add AppNav Team link  

Another developer or agent can implement this plan without needing clarification.
