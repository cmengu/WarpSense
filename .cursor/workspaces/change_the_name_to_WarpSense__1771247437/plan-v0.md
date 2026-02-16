
Summary of what was created:

## WarpSense Rebrand Implementation Plan

An implementation plan for the WarpSense rebrand is saved at:

**`.cursor/plans/warpsense-rebrand-blue-purple-plan.md`**

### Summary

**4 Phases | 31 Steps | ~16–20 hours**

| Phase | Focus | Steps | Time |
|-------|--------|-------|------|
| **1. Foundation** | theme.ts, thermal pipeline (heatmapData, heatmapShaderUtils, GLSL), delta heatmap | 7 | 6–8 h |
| **2. Components** | PieChart, BarChart, mockData, HeatMap, TorchAngleGraph, TorchWithHeatmap3D, HeatmapPlate3D | 8 | 4–5 h |
| **3. Pages** | Demo, landing, replay, compare, dashboard – branding and colors | 9 | 4–5 h |
| **4. Docs & QA** | deploy.sh, .env, Dockerfiles, CONTEXT, DEPLOY, grep, visual QA | 7 | 2–3 h |

### Decisions

1. **theme.ts** as source of truth for hex (thermal, charts, semantic).
2. **8 thermal anchors** for blue→purple gradient in heatmapData, heatmapShaderUtils, and GLSL.
3. **Delta heatmap** scale: blue (B hotter) → white → purple (A hotter).
4. **Expert** = blue-400; **Novice** = purple-400.
5. **Error** = violet-600.
6. **Docker container names** left as-is (out of scope).

### Critical Path

`theme.ts` → thermal triad (heatmapData, heatmapShaderUtils, GLSL) → delta heatmap → charts → components → pages → docs → tests.

### Notable Plan Content

- Full `theme.ts` implementation with 8 anchors and hex values.
- Verification steps for each step.
- Common failures and fixes.
- Thermal sync test to keep heatmapData, heatmapShaderUtils, and GLSL aligned.
- Mapping of test changes (heatmapData, heatmapShaderUtils, deltaHeatmapData, HeatMap, demo).
- Pre-flight checklist and risk table.
- 15 success criteria.
- Progress tracking section.

Implementation can follow the plan in order, with Phase 1 as the required starting point.
