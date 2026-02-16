
Refined plan changes applied:

**Critical:**
1. **Seagull routes in Phase 3** — Step 3.5 added: seagull welder error (red→violet) and dashboard (amber→violet), with paths and code changes.
2. **theme.ts THERMAL_ANCHOR_COLORS_0_1 docs** — Documented that index `i` maps to shader `anchorPos[i]` with positions `[0, 0.1, 0.2, 0.3, 0.5, 0.7, 0.9, 1.0]`.

**Minor:**
3. **Step 1.2** — Full `tempToColor` loop (no `// ... rest same`) and explicit `tempToColorRange` remap.
4. **Step 1.4** — Full GLSL `anchorCol[8]` replacement block.
5. **Step 1.7** — Exact hex values for `heatmapData.test`: `tempToColor(0)` = #1e3a8a, `tempToColor(250)` = #7c3aed, `tempToColor(500)` = #a855f7; `tempToColorRange(400,550)` atMin #1e3a8a, atMax #a855f7.
6. **Step 2.8** — Exact hex and assertions for HeatMap.test.
7. **Range [0,500]** — Note on clamp impact for sensor data >500°C in Known Issues and synthesis.
8. **Step 4.5 grep** — Exclude `.cursor`, `node_modules`, test files; tests are updated in Phases 1–3 before grep.
9. **Step 4.6 Visual QA** — Seagull `/seagull` and `/seagull/welder/[id]` added to checklist.
10. **Success criteria** — Added #13 for seagull (no red, no amber).
11. **Dependency graph** — Seagull (item 21) added.
12. **Risk** — Failure mode for missed seagull routes added.
