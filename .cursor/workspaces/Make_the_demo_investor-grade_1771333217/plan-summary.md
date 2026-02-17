
Summary is in `.cursor/plans/investor-grade-demo-execution-summary.md`. Here it is:

---

## Steps

1. **File:** `my-app/src/lib/demo-config.ts`  
   - **Action:** Add NOVICE_SPIKE_MS, MOCK_EXPERT_SCORE_VALUE, MOCK_NOVICE_SCORE_VALUE, DEMO_WELDERS; no magic numbers elsewhere  
   - **Key code:** `expect(NOVICE_SPIKE_MS).toBe(2400); expect(MOCK_EXPERT_SCORE_VALUE).toBe(94);`

2. **File:** `my-app/src/__tests__/lib/demo-config.test.ts`  
   - **Action:** Add validation tests for config values  
   - **Key code:** Assert NOVICE_SPIKE_MS === 2400, MOCK_EXPERT_SCORE_VALUE === 94

3. **File:** `my-app/src/utils/heatmapTempRange.ts`  
   - **Action:** `computeMinMaxTemp`: handle null/undefined points; filter NaN, null, Infinity, undefined `temp_celsius`  
   - **Key code:** Return fallback when empty or all invalid; `[{temp:NaN},{temp:200}]` → `{min:200,max:200}`

4. **File:** `my-app/src/__tests__/utils/heatmapTempRange.test.ts`  
   - **Action:** Add tests for empty, null, and invalid temp inputs  
   - **Key code:** `computeMinMaxTemp([{ temp_celsius: NaN }, { temp_celsius: 200 }])` → `{ min: 200, max: 200 }`

5. **File:** `my-app/src/lib/seagull-demo-data.ts`  
   - **Action:** Implement createMockScore and getDemoTeamData; shape must match `ai-feedback.test` mockScore  
   - **Key code:** Follow ai-feedback.test mockScore pattern; all 5 `rule_id`s in RULE_TEMPLATES

6. **File:** `my-app/src/__tests__/lib/seagull-demo-data.test.ts`  
   - **Action:** Add tests for createMockScore(94,[]), createMockScore(42,[...]); ensure generateAIFeedback accepts both; cover every rule_id  
   - **Key code:** createMockScore with each RULE_TEMPLATES key as failed → valid generateAIFeedback output

7. **File:** `my-app/src/app/demo/team/[welderId]/page.tsx`  
   - **Action:** Welder report: `session?.frames ?? []`; when empty, render PlaceholderHeatMap (neutral gradient)  
   - **Key code:** `const frames = session?.frames ?? []; frames.length === 0 ? <PlaceholderHeatMap /> : <HeatMap />`

8. **File:** `my-app/src/__tests__/app/demo/team/[welderId]/page.test.tsx`  
   - **Action:** Integration test: empty frames → PlaceholderHeatMap renders; no white screen  
   - **Key code:** Mock getDemoTeamData with `session.frames: []` → expect PlaceholderHeatMap visible

9. **File:** Phase 2 gate  
   - **Action:** Do not start Phase 2 until: (a) Phase 1 tests pass, (b) `/demo/team` loads, (c) welder report renders without white screen  
   - **Key code:** `npm test` green; manual check of /demo/team and /demo/team/mike-chen

10. **File:** Cross-browser checks  
    - **Action:** Run Safari/Chrome/Firefox and 375px viewport before finishing Phase 2  
    - **Key code:** Tour `z-[200]`; fallback `z-[300]` if Safari has issues

## Critical Details

- No magic numbers outside `demo-config`
- createMockScore shape must match what generateAIFeedback expects (mirror ai-feedback.test)
- Empty frames must always use PlaceholderHeatMap; never show a white screen
- heatmapTempRange must filter invalid temps; empty/null → use fallback
- Unit and integration tests required; Step 1.5 tests must run before Phase 2
- Phase 1: 8–10 h | Phase 2: 6–8 h | Phase 3: 3–4 h
