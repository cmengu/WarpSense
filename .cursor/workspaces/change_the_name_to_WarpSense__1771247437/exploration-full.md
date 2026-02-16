
Here’s a concise summary of the WarpSense rebrand exploration. The full document is at `.cursor/explore-outputs/warpsense-rebrand-blue-purple-exploration.md`.

---

## Exploration summary

### Core challenge

- Replace “Shipyard Welding” with “WarpSense” everywhere.
- Limit the UI to blue and purple (dark shades only).
- Keep thermal semantics and chart readability while updating tests.

### Recommended approach: theme.ts + Tailwind

1. **Add `my-app/src/constants/theme.ts`** with:
   - `THERMAL_COLOR_ANCHORS` (blue → purple gradient)
   - `CHART_PALETTE` (6 blue/purple hex values)
   - `EXPERT_HEX`, `NOVICE_HEX`, `ERROR_HEX` for semantic colors

2. **Keep thermal sources in sync** — `heatmapData.ts`, `heatmapShaderUtils.ts`, and `heatmapFragment.glsl.ts` share the same 8 blue→purple anchors.

3. **Delta heatmap** — Blue (B hotter) → white → purple (A hotter) instead of blue → white → red.

4. **Expert vs novice** — Expert → blue (`blue-400`), Novice → purple (`purple-400`).

5. **Errors and danger** — `violet-600` / `purple-600` instead of red.

### Architectural choices

| Topic | Choice |
|-------|--------|
| Theme system | `constants/theme.ts` for hex; Tailwind for layout/borders/text |
| Thermal gradient | 8 anchors, blue→purple (0–500°C) |
| Delta heatmap | blue → white → purple |
| Expert/novice | blue vs purple |
| Error UI | violet/purple-600 |
| HeatMap active column | blue-500 outline |
| TorchAngleGraph target | purple-500 |

### Files to change (~25)

- **New:** `constants/theme.ts`
- **Thermal:** `heatmapData.ts`, `heatmapShaderUtils.ts`, `heatmapFragment.glsl.ts`, `deltaHeatmapData.ts`
- **Components:** `TorchWithHeatmap3D`, `HeatmapPlate3D`, `HeatMap`, `TorchAngleGraph`, `PieChart`, `BarChart`, `AppNav`
- **Pages:** demo, landing, replay, compare, dashboard, `DemoLayoutClient`
- **Docs:** `deploy.sh`, `.env.example`, Dockerfiles, `CONTEXT.md`, `DEPLOY.md`
- **Tests:** demo, `heatmapData`, `HeatMap`, `heatmapShaderUtils`, `deltaHeatmapData`

### Effort

~16 hours (within the original 12–20h estimate)

### Answers to your questions

1. **Palette:** Tailwind dark blues (`blue-800/900/950`) and purples (`purple-800/900/950`) for backgrounds; `blue-400`, `purple-400` for accents on dark backgrounds.
2. **Thermal gradient:** Yes — blue (cold) → purple (hot) is recommended and validated in exploration.
3. **Expert vs novice:** Blue vs purple is recommended for clear contrast.

---

Next step: **Phase 3 (Create Plan)** — a step-by-step implementation plan built on this exploration.
