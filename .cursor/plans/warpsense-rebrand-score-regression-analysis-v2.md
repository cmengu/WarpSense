# WarpSense Rebrand Plan — Score Regression Self-Analysis (Iteration 4 → 5)

**Date:** 2026-02-16  
**Score History:** 7.4 → 8.1 → 8.0 → 8.5 → 8.4  
**Regression:** -0.1 (Iteration 5 vs Iteration 4)

---

## 1. JSON Analysis

```json
{
  "regression_summary": {
    "previous_score": 8.5,
    "current_score": 8.4,
    "delta": -0.1,
    "primary_cause": "Five new minor issues surfaced by 8.4 critique; no content from Iteration 4 was removed",
    "no_content_removed": true
  },
  "root_cause_analysis": {
    "what_changed": "Iteration 5 applied three refinements: Step 1.5 test location (heatmapData.test.ts vs heatmapSync.test.ts), Steps 3.1 & 3.3 optional rg for demo/landing Tailwind, Step 4.5 grep exclusion rationale",
    "what_did_not_change": "All Iteration 4 refinements are present: Step 1.3 code block, Step 4.7 npm run build, Rollback procedure, Step 2.3 mockData rg note, Step 1.5 NaN handling",
    "why_score_dropped": "The 8.4 critique surfaced five additional minor issues that lower dimension scores: (1) Step 1.2 lacks explicit line reference for tempToColorRange, (2) Step 2.3 rg in Note but not copy-pasteable code block, (3) Step 2.6 lacks optional rg for TorchWithHeatmap3D, (4) Step 1.6 deltaTempToColor has no NaN note, (5) Step 1.1 has no constants barrel export note"
  },
  "dimension_impact": {
    "completeness": "8.5 — Slightly hurt by missing line refs and optional rg",
    "clarity": "8.5 — tempToColorRange line 118 missing; mockData rg not in code block",
    "verification": "8.5 — Solid",
    "dependencies": "9.0 — Strong",
    "risk_management": "8.0 — Rollback present; no additional gap",
    "edge_cases": "7.5 — deltaTempToColor NaN not documented; tempToColor NaN is in 1.5 but delta heatmap separate",
    "production_ready": "8.5 — Build + rollback present"
  },
  "regression_contributors": [
    {
      "issue": "Step 1.2 tempToColorRange line reference",
      "type": "Clarity",
      "impact": "Executor must search heatmapData.ts for remap; heatmapData.ts line 118 has `const t = 20 + p * (600 - 20)`",
      "fix": "Add explicit line reference: 'In tempToColorRange (heatmapData.ts ~line 118): change `const t = 20 + p * (600 - 20)` to `const t = p * 500`'"
    },
    {
      "issue": "Step 2.3 mockData rg command not copy-pasteable",
      "type": "Clarity",
      "impact": "rg appears in Note text but not in a code block; executor must retype",
      "fix": "Add code block: ```bash\nrg '#10b981|#f59e0b' my-app/src/data/mockData.ts\n```"
    },
    {
      "issue": "Step 2.6 TorchWithHeatmap3D no optional rg",
      "type": "Consistency / Clarity",
      "impact": "Steps 3.1 and 3.3 have optional rg for demo/landing; 2.6 lists Tailwind changes but no rg to locate them",
      "fix": "Add optional helper: `rg 'cyan|green|amber' my-app/src/components/welding/TorchWithHeatmap3D.tsx`"
    },
    {
      "issue": "Step 1.6 deltaTempToColor NaN",
      "type": "Edge Cases",
      "impact": "Current impl uses Math.max(-50, Math.min(50, d)); NaN propagates. Low risk for compare page, but no note",
      "fix": "Add one-line note: 'deltaTempToColor: NaN propagates; behavior undefined. Optional: add clamp or skip if not critical.' Or optional test: expect(deltaTempToColor(NaN)).toBeDefined()"
    },
    {
      "issue": "Step 1.1 constants barrel",
      "type": "Future-proofing",
      "impact": "No constants/index.ts barrel exists; if one is added later, theme.ts would need exporting",
      "fix": "Add one sentence: 'If constants/index.ts exists (or is added), add theme export.'"
    }
  ],
  "strengths_preserved": [
    "Pre-planning session (exploration synthesis, dependency graph, risk heatmap)",
    "Phase 1 thermal pipeline: theme.ts, sync test, rgbToHex helpers, explicit alignment",
    "Step 1.3 full code block (import + ANCHOR_COLORS alias)",
    "Step 4.7 npm run build before npm test",
    "Rollback procedure (git revert, npm test, redeploy)",
    "Step 2.3 mockData line numbers and rg note",
    "Step 1.5 NaN handling for tempToColor (Common failures + optional test)",
    "Steps 3.1 and 3.3 optional rg for demo/landing Tailwind",
    "Step 4.5 grep exclusion rationale for tests",
    "Seagull routes in Phase 3 and Visual QA"
  ],
  "strengths_lost": [],
  "recovery_strategy": {
    "action": "Apply the five minor fixes from the 8.4 critique improvement_priority",
    "priority_order": [
      "1. Step 1.2: Add line 118 reference for tempToColorRange remap",
      "2. Step 2.3: Add copy-pasteable rg code block for mockData",
      "3. Step 2.6: Add optional rg for TorchWithHeatmap3D Tailwind classes",
      "4. Step 1.6: Add NaN note or optional test for deltaTempToColor",
      "5. Step 1.1: Add constants barrel export note"
    ],
    "expected_outcome": "Score recovers to 8.5+; approach 9.0 with all five refinements",
    "no_structural_changes": true
  }
}
```

---

## 2. Detailed Explanation

### Why the Score Decreased

The regression is **not** caused by removing or weakening content. The current plan retains all five refinements from Iteration 4:

- Step 1.3 code block ✓  
- Step 4.7 build verification ✓  
- Rollback procedure ✓  
- Step 2.3 mockData rg note ✓  
- Step 1.5 NaN handling ✓  

Iteration 5 added three refinements (1.5 test location, 3.1/3.3 rg, 4.5 rationale). Nothing was dropped.

The score dropped because the **8.4 critique identified five new minor issues** that were not flagged in the 8.5 evaluation. These gaps affect clarity, edge-case coverage, and consistency:

| Issue | Dimension | Impact |
|-------|-----------|--------|
| Step 1.2 no line ref | Clarity | Executor searches heatmapData.ts; line 118 holds the remap |
| Step 2.3 rg in Note only | Clarity | Not copy-pasteable; executor retypes |
| Step 2.6 no optional rg | Consistency | 3.1/3.3 have rg; 2.6 does not |
| Step 1.6 no NaN note | Edge Cases | deltaTempToColor uses Math.max/min; NaN propagates |
| Step 1.1 no barrel note | Completeness | Future constants/index.ts would need theme export |

### What Changed Between Iteration 4 and 5

- **Iteration 4:** Scored 8.5 after applying five refinements from prior critique + regression: 1.3 code block, 4.7 build, rollback, 2.3 rg, 1.5 NaN.
- **Iteration 5:** Applied three refinements from a new critique: 1.5 test location, 3.1/3.3 optional rg, 4.5 exclusion rationale.

These changes are additive. The regression comes from the 8.4 critique applying a stricter or broader rubric and flagging five more minor gaps.

### What Made Things Worse (Net Effect)

1. **Step 1.2 tempToColorRange:** The plan shows the remap change (`20 + p * (600 - 20)` → `p * 500`) but does not reference line 118 in `heatmapData.ts`. The codebase shows the remap at line 118; adding this reference speeds up localization.

2. **Step 2.3 mockData:** The `rg '#10b981|#f59e0b' my-app/src/data/mockData.ts` command appears in the Note. It is not in a separate code block, so it is not easily copy-pasteable.

3. **Step 2.6 TorchWithHeatmap3D:** Steps 3.1 and 3.3 include optional `rg` commands for demo and landing Tailwind. Step 2.6 lists Tailwind changes (border-cyan-400 → border-blue-500, etc.) but has no similar `rg` helper, breaking the pattern.

4. **Step 1.6 deltaTempToColor:** Step 1.5 covers `tempToColor(NaN)` for the main thermal pipeline. The critique asks about `deltaTempToColor` in Step 1.6: `Math.max(-50, Math.min(50, d))` lets NaN propagate. Low risk on the compare page, but the plan should note this or add an optional test.

5. **Step 1.1 constants barrel:** There is no `constants/index.ts` barrel. If one is added later, `theme.ts` would need to be exported. A one-line note future-proofs the plan.

### Recovering the Best Elements

- **Nothing was lost.** All Iteration 4 strengths are still present.
- **Strategy:** Add the five fixes above without changing plan structure.
- **Expected outcome:** Score returns to 8.5; with all five refinements, the plan moves toward 9.0.

---

## 3. Concrete Fixes (Recovery Plan)

### Fix 1: Step 1.2 — Add Line Reference for tempToColorRange

**Location:** Phase 1, Step 1.2, tempToColorRange code block (around line 375)

**Change:** Add explicit line reference before or in the tempToColorRange snippet:

```markdown
**tempToColorRange:** In heatmapData.ts (line 118), change remap from `20 + p * (600 - 20)` to `p * 500` so normalized [0,1] maps to [0, 500]°C:
```

### Fix 2: Step 2.3 — Add Copy-Pasteable rg Code Block

**Location:** Phase 2, Step 2.3, after "Note:" paragraph

**Add:**
```markdown
**Verify line numbers before edit:**
```bash
rg '#10b981|#f59e0b' my-app/src/data/mockData.ts
```
```

### Fix 3: Step 2.6 — Add Optional rg for TorchWithHeatmap3D

**Location:** Phase 2, Step 2.6, at start of "What:" section (before the bullet list)

**Add:**
```markdown
**Locate Tailwind classes (optional helper):**
```bash
rg 'cyan|green|amber' my-app/src/components/welding/TorchWithHeatmap3D.tsx
```
```

### Fix 4: Step 1.6 — Add deltaTempToColor NaN Note

**Location:** Phase 1, Step 1.6, in "Common failures" or as new bullet

**Add:**
```markdown
**NaN:** deltaTempToColor uses `Math.max(-50, Math.min(50, d))`; NaN propagates and may produce invalid output. Low risk for compare page; optionally add `expect(deltaTempToColor(NaN)).toBeDefined()` or document that behavior is implementation-dependent.
```

### Fix 5: Step 1.1 — Add Constants Barrel Note

**Location:** Phase 1, Step 1.1, in "Subtasks" or "Verification" section

**Add:**
```markdown
**Barrel export:** If `constants/index.ts` exists (or is added later), add `theme` export so theme.ts is discoverable.
```

---

## 4. Summary

| Question | Answer |
|----------|--------|
| **Why did the score drop?** | The 8.4 critique surfaced five minor issues not flagged in the 8.5 evaluation. |
| **What changes made it worse?** | None; no content was removed. Iteration 5 added three refinements; the regression comes from five new minor gaps. |
| **Strengths lost?** | None; all Iteration 4 refinements remain. |
| **How to recover?** | Apply the five minor fixes using refine-plan or direct edits. |
| **Expected outcome** | Score recovers to 8.5; with full polish, approaches 9.0. |

---

## 5. Recommendation

**Proceed or refine?** The 8.4 critique recommends **proceed** — the plan has zero critical issues and no execution blockers. The five minor issues are polish, not preconditions.

**If refining first:** Apply the five fixes above. Total effort: ~15 minutes.

**If proceeding:** Incorporate fixes during implementation (e.g., use `rg` when touching mockData or TorchWithHeatmap3D).
