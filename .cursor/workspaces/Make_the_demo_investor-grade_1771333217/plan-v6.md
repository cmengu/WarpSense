
The refined plan is saved at `.cursor/plans/investor-grade-demo-implementation-plan.md`. It includes:

**Tour overlay**
- Focus trap, aria-modal, role="dialog", aria-labels for Next/Skip
- Highlight fallback when `highlightSelector` fails
- 150ms debounced scrub callbacks
- Step logging for debugging
- Visual checklist per step
- Transitions on overlay

**Data layer**
- `demo-config.ts` for thresholds, spike timestamp, and `DEMO_WELDERS`
- `computeMinMaxTemp()` in `heatmapTempRange.ts`
- Configurable welder count
- Optional `getDemoTeamDataAsync()` with delay

**Phase 1**
- Placeholder HeatMap with neutral gradient when frames are empty
- Frame validation and graceful handling

**Phase 2**
- Time-boxing of steps
- Multi-device/browser testing
- Edge-case handling (modals, scroll, animation)

**Phase 3**
- Dismiss tour overlay before navigation
- Responsive layout (min/max width, z-index)
- Contingency demo path
- Optional feature flags

**Testing**
- Unit, integration, and E2E
- Mock async failure
- Optional visual regression / screenshots
