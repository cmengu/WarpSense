
Summary of updates for the WarpSense rebrand and blue/purple color scheme:

## Summary of Changes

### 1. Welding Components
- **TorchViz3D.tsx**: Replaced cyan (`#22d3ee`) with blue (`#3b82f6`) for the angle guide ring and grid helper; `text-cyan-500/50` → `text-blue-500/50`; shadows `rgba(6,182,212,...)` → `rgba(59,130,246,...)`.
- **TorchWithHeatmap3D.tsx**: Angle guide ring and grid helper color → blue.
- **HeatmapPlate3D.tsx**: Context-loss UI `text-amber-400` → `text-violet-400`; button `hover:text-cyan-300` → `hover:text-blue-300`.

### 2. Navigation & Dashboard
- **AppNav.tsx**: Demo link `text-cyan-*` → `text-blue-*`.
- **Dashboard page.tsx**: Loading/error/no-data states switched from cyan/red to blue/violet. Error state uses violet instead of red; demo CTA uses blue.

### 3. Error & Feedback UI
- **DemoLayoutClient.tsx**: Error fallback from red to violet.
- **FeedbackPanel.tsx**: Warning styling from amber to violet.
- **seagull/welder/[id]/page.tsx**: Error state from red to violet.
- **seagull/page.tsx**: “Score unavailable” text from amber to violet.

### 4. Dev Page
- **dev/torch-viz/page.tsx**: Cyan → blue; green pulse dot → blue; “Cyan” theme label → “Blue / Purple”; shadows use blue rgba.

### 5. Documentation & Tests
- **CONTEXT.md**: Temperature gradient updated from “Blue→yellow→red” to “Blue→purple” with 8 anchors.
- **Marketing page comment**: Removed “cyan” from gradient description.
- **deltaHeatmapData.test.ts**: Comment updated (“red at +50” → “purple at +50”).
- **FeedbackPanel.test.tsx**: Amber expectations → violet.
- **dev/torch-viz/page.test.tsx**: Cyan theme → WarpSense theme.
- **LineChart.test.tsx**: Custom color `#ef4444` → `#a855f7` for theme alignment.

Branding and palette usage:
- **theme.ts**: `THERMAL_COLOR_ANCHORS`, `CHART_PALETTE`, `EXPERT_HEX`, `NOVICE_HEX`, `ERROR_HEX` already use blue/purple/violet.
- **Marketing page**: Gradients already use blue–violet–purple.
- **Demo page**: Uses “WarpSense — Live Quality Analysis”.

Run tests to confirm everything passes:

```bash
cd my-app && npm test -- --run
```
