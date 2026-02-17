
Compressed exploration report:

```markdown
## Key Files
- `components/demo/DemoTour.tsx` - Custom overlay for guided tour (config-driven)
- `lib/demo-tour-config.ts` - Tour step config (2–4 steps, optional scrub)
- `lib/seagull-demo-data.ts` - Mock team data + `getDemoTeamData()`, `createMockScore()`
- `app/demo/team/page.tsx` - Team dashboard with welder cards
- `app/demo/team/[welderId]/page.tsx` - Welder report (HeatMap, FeedbackPanel, LineChart)
- `app/demo/page.tsx` - Integrate tour + CTA to team
- `components/AppNav.tsx` - Add "Team" link → `/seagull`

## Architecture
- Guided tour: custom overlay, `z-[200]` + `isolate` above WebGL (no third-party lib)
- Browser-only: `/demo/team` uses in-memory data only; no `fetchSession`/`fetchScore`
- Mock data: same pattern as `ai-feedback.test.ts` (expert 94, novice 42)
- Preset: novice spike at `timestamp_ms: 2400` (sine peak in `demo-data.ts`)
- Reuse: Seagull HeatMap, FeedbackPanel, LineChart, `generateAIFeedback` unchanged

## Dependencies / Integration
- `useFrameData` works with in-memory frames from `demo-data.ts`
- CTA on demo → `/demo/team`
- AppNav "Team" → `/seagull`

## Risks
- WebGL context limits (see `documentation/WEBGL_CONTEXT_LOSS.md`)
- Confidence 8/10; approach validated by codebase analysis
```

~30 lines, format preserved.
