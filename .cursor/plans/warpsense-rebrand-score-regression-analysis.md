# WarpSense Rebrand Plan — Score Regression Self-Analysis

**Date:** 2026-02-16  
**Score History:** 7.4 → 8.1 → 8.0  
**Regression:** -0.1 (Iteration 3 vs Iteration 2)

---

## 1. JSON Analysis

```json
{
  "regression_summary": {
    "previous_score": 8.1,
    "current_score": 8.0,
    "delta": -0.1,
    "primary_cause": "Five minor issues identified in latest critique not yet addressed",
    "no_content_removed": true
  },
  "root_cause_analysis": {
    "what_changed": "Iteration 3 applied six critique refinements (heatmapShaderUtils 0°C, expert/novice purple-ish, clamp test, grep simplification, mockData line numbers, rgbToHex helpers)",
    "what_did_not_change": "Seagull routes, theme.ts docs, exact hex values, dependency graph, risk heatmap—all preserved from Iteration 2",
    "why_score_dropped": "Latest critique surfaced five new minor issues that lower dimension scores: clarity (Step 1.3 no code block), verification (Step 4.7 no build), risk_management (no rollback steps), edge_cases (NaN not in test block), production_ready (no build before deploy)"
  },
  "dimension_impact": {
    "completeness": "8.5 — Slightly hurt by missing rollback detail",
    "clarity": "8.5 — Step 1.3 lacks executable code block",
    "verification": "8.0 — npm run build missing; otherwise strong",
    "risk_management": "7.5 — Contingency mentioned but no step-by-step rollback",
    "edge_cases": "7.5 — NaN mentioned in Common failures but not in test block",
    "production_ready": "7.0 — Deploy pipelines typically run build; plan omits it"
  },
  "regression_contributors": [
    {
      "issue": "Step 1.3 heatmapShaderUtils import",
      "type": "Clarity",
      "impact": "Executor must infer code; no copy-paste block",
      "fix": "Add code block: import + const ANCHOR_COLORS = THERMAL_ANCHOR_COLORS_0_1"
    },
    {
      "issue": "Step 4.7 verification",
      "type": "Verification / Production",
      "impact": "Next.js build not run; deploy pipelines typically run build",
      "fix": "Add npm run build before npm test (or as separate verification)"
    },
    {
      "issue": "Risk section rollback",
      "type": "Risk Management",
      "impact": "Contingency says 'Revert thermal changes' but no instructions",
      "fix": "Add to Phase 4 or Pre-Flight: git revert <PR-commit>; npm test; redeploy"
    },
    {
      "issue": "Step 2.3 mockData line numbers",
      "type": "Clarity / Maintainability",
      "impact": "Line numbers may shift if file structure changes",
      "fix": "Add note: verify via grep if mockData structure changes"
    },
    {
      "issue": "Step 1.5 NaN handling",
      "type": "Edge Cases",
      "impact": "NaN mentioned in Common failures but not in explicit test block",
      "fix": "Add optional expect(tempToColor(NaN)).toBeDefined() or document implementation-dependent behavior"
    }
  ],
  "strengths_preserved": [
    "Pre-planning session (exploration synthesis, dependency graph, risk heatmap)",
    "Thermal pipeline sync strategy (theme.ts, rgbToHex helpers, explicit alignment)",
    "Step 1.7 exact assertions (0°C/250°C/500°C hex, clamp, expert/novice purple-ish)",
    "Step 2.3 mockData line numbers (79, 118)",
    "Step 4.5 grep with glob exclusions",
    "Step 3.5 seagull paths and Tailwind replacements",
    "Dependency graph valid DAG",
    "Known Issues (range [0,500], purple-as-error)"
  ],
  "strengths_lost": [],
  "recovery_strategy": {
    "action": "Refine plan by addressing five minor issues from critique",
    "priority_order": [
      "1. Add Step 1.3 code block (highest clarity impact)",
      "2. Add npm run build to Step 4.7",
      "3. Add rollback procedure to Phase 4 or Pre-Flight",
      "4. Add grep verification note to Step 2.3",
      "5. Add NaN edge-case test or documentation to Step 1.5"
    ],
    "expected_outcome": "Score recovers to 8.2–8.4; no structural changes required"
  }
}
```

---

## 2. Detailed Explanation

### Why the Score Decreased

The score drop is **not** caused by removing or weakening content from the previous plan. Iteration 2 and Iteration 3 share the same core structure: seagull routes, exact hex values, theme docs, dependency graph. The six refinements (0°C test, purple-ish semantics, clamp, grep, mockData lines, rgbToHex) were applied correctly and are aligned with the critique.

**The regression comes from the latest critique identifying five minor issues that were not present (or not highlighted) in the prior evaluation.** Those gaps reduce several dimension scores:

| Dimension        | Score | Driver                                            |
|------------------|-------|---------------------------------------------------|
| Risk Management  | 7.5   | No step-by-step rollback instructions             |
| Edge Cases       | 7.5   | NaN mentioned but not covered in the test block    |
| Production Ready | 7.0   | `npm run build` omitted; deploy usually runs it   |
| Clarity          | 8.5   | Step 1.3 describes the change but has no code block |
| Verification     | 8.0   | Tests are strong, but build verification is missing |

### What Changed Between Iteration 2 and 3

- **Iteration 2:** Refinements focused on seagull routes, theme docs, full code blocks in Steps 1.2 and 1.4, exact hex values, grep exclusions, Visual QA seagull, success criteria, dependency graph, and risk for missed seagull routes.
- **Iteration 3:** Applied a different set of six refinements (heatmapShaderUtils 0°C, expert/novice purple-ish, clamp, grep, mockData, rgbToHex). These are additive; they did not replace the earlier improvements.

The current plan still contains the Iteration 2 content (e.g. Step 3.5 seagull, Step 2.8 HeatMap assertions). The problem is that the new refinement cycle surfaced five additional minor issues that lower the overall score.

### What Made Things Worse

1. **Step 1.3:** The critique asks for a concrete code block. The plan only says to replace `ANCHOR_COLORS` with an import; the executor must infer the exact code. `heatmapShaderUtils.ts` currently defines `ANCHOR_COLORS` locally; the plan should show how to import `THERMAL_ANCHOR_COLORS_0_1` and alias it.
2. **Step 4.7:** Verification is limited to `npm test`. CI and deploy typically run `npm run build`; omitting it weakens verification and production readiness.
3. **Risk section:** “Contingency: Revert thermal changes” appears, but there is no procedure. A clear rollback step improves risk management.
4. **Step 2.3:** Line numbers 79 and 118 are correct now, but no note explains that they can change if the file structure changes. A short grep-based verification note would improve maintainability.
5. **Step 1.5:** Common failures mention NaN, but the test block does not. Either add an explicit NaN test or document that behavior is implementation-dependent.

### Recovering the Best Elements

- **Content that was good is still present:** Seagull routes, exact hex values, theme docs, dependency graph, risk heatmap, Known Issues, rgbToHex helpers, and Phase 1–4 structure are all intact.
- **Nothing needs to be rolled back.** The regression is from missing small polish items, not from bad changes.
- **Strategy:** Add the five fixes above without altering the rest of the plan.

---

## 3. Concrete Fixes (Recovery Plan)

Apply these edits to restore and exceed the previous score:

### Fix 1: Step 1.3 — Add Code Block

**Location:** Phase 1, Step 1.3

**Add after "What:" and before "Files:":**

```markdown
**Code:**
```typescript
import { THERMAL_ANCHOR_COLORS_0_1 } from '@/constants/theme';

const ANCHOR_COLORS = THERMAL_ANCHOR_COLORS_0_1;
// Remove the local ANCHOR_COLORS array definition (lines ~18–28)
```
```

### Fix 2: Step 4.7 — Add Build Verification

**Change:**
```markdown
**What:** `npm run build` in my-app (ensures Next.js build succeeds); then `npm test`. Deploy pipelines typically run build—verify before merge.
```

### Fix 3: Phase 4 or Pre-Flight — Add Rollback Procedure

**Add new subsection or bullet:**
```markdown
### Rollback Procedure

If thermal changes cause failures after merge:
1. `git revert <PR-commit>`
2. `npm test`
3. Redeploy if already pushed
```

### Fix 4: Step 2.3 — Add Grep Verification Note

**Add after "Verify no other green/amber hex elsewhere":**
```markdown
**Note:** Line numbers 79 and 118 are correct as of the current codebase. If mockData structure changes, verify via `rg '#10b981|#f59e0b' my-app/src/data/mockData.ts` before editing.
```

### Fix 5: Step 1.5 — Add NaN Handling

**Add to Common failures or test block:**
```markdown
- **NaN:** Both utilities should handle; optionally add `expect(tempToColor(NaN)).toBeDefined()` or document that NaN behavior is implementation-dependent and skip if not critical.
```

---

## 4. Summary

| Question                  | Answer                                                                 |
|---------------------------|------------------------------------------------------------------------|
| **Why did the score drop?** | Latest critique identified five minor issues not present before.     |
| **What changes made it worse?** | Nothing was removed; the new refinement round exposed gaps.          |
| **Strengths lost?**       | None; previous strengths are preserved.                                |
| **How to recover?**       | Add the five fixes above using the refine-plan workflow.               |
| **Expected outcome**      | Score should recover to 8.2–8.4 with no structural changes.            |
