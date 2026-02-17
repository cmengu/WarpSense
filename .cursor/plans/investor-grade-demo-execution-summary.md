# Investor-Grade Demo — Execution Summary

## Steps

1. **File:** `my-app/src/lib/demo-config.ts`
   - **Action:** Add NOVICE_SPIKE_MS, MOCK_EXPERT_SCORE_VALUE, MOCK_NOVICE_SCORE_VALUE, DEMO_WELDERS; no magic numbers elsewhere
   - **Key code:** `expect(NOVICE_SPIKE_MS).toBe(2400); expect(MOCK_EXPERT_SCORE_VALUE).toBe(94);`

2. **File:** `my-app/src/__tests__/lib/demo-config.test.ts`
   - **Action:** Validate config values
   - **Key code:** Assert NOVICE_SPIKE_MS === 2400, MOCK_EXPERT_SCORE_VALUE === 94

3. **File:** `my-app/src/utils/heatmapTempRange.ts`
   - **Action:** computeMinMaxTemp: handle null/undefined points; filter NaN, null, Infinity, undefined temp_celsius
   - **Key code:** Return fallback when empty or all invalid; expect([{temp:NaN},{temp:200}]) → {min:200,max:200}

4. **File:** `my-app/src/__tests__/utils/heatmapTempRange.test.ts`
   - **Action:** Test empty, null, invalid temp cases
   - **Key code:** computeMinMaxTemp([{ temp_celsius: NaN }, { temp_celsius: 200 }]) → { min: 200, max: 200 }

5. **File:** `my-app/src/lib/seagull-demo-data.ts`
   - **Action:** createMockScore, getDemoTeamData; shape matches ai-feedback.test mockScore exactly
   - **Key code:** Copy ai-feedback.test mockScore pattern; all 5 rule_ids in RULE_TEMPLATES

6. **File:** `my-app/src/__tests__/lib/seagull-demo-data.test.ts`
   - **Action:** Tests for createMockScore(94,[]), createMockScore(42,[...]); generateAIFeedback accepts both; every rule_id
   - **Key code:** createMockScore with each RULE_TEMPLATES key as failed → valid generateAIFeedback output

7. **File:** `my-app/src/app/demo/team/[welderId]/page.tsx`
   - **Action:** Welder report: session?.frames ?? []; when empty → PlaceholderHeatMap (neutral gradient)
   - **Key code:** `const frames = session?.frames ?? []; frames.length === 0 ? <PlaceholderHeatMap /> : <HeatMap />`

8. **File:** `my-app/src/__tests__/app/demo/team/[welderId]/page.test.tsx`
   - **Action:** Integration test: empty frames → PlaceholderHeatMap renders; no white screen
   - **Key code:** Mock getDemoTeamData with session.frames: [] → expect PlaceholderHeatMap visible

9. **File:** Phase 2 gate
   - **Action:** Phase 2 cannot start until: (a) Phase 1 tests pass, (b) /demo/team loads, (c) welder report renders without white screen
   - **Key code:** `npm test` green; manual /demo/team + /demo/team/mike-chen check

10. **File:** Cross-browser
    - **Action:** Safari/Chrome/Firefox + 375px viewport before Phase 2 done
    - **Key code:** Tour z-[200]; contingency z-[300] if Safari fails

## Critical Details

- No magic numbers outside demo-config
- createMockScore shape = generateAIFeedback expects (copy ai-feedback.test exactly)
- Empty frames → PlaceholderHeatMap mandatory; never white screen
- heatmapTempRange filters invalid temps; empty/null → fallback
- Unit + integration tests mandatory; Step 1.5 tests before Phase 2
- Phase 1: 8–10 h | Phase 2: 6–8 h | Phase 3: 3–4 h
