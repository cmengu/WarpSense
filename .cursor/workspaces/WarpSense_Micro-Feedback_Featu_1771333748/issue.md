
I've created the WarpSense Micro-Feedback issue at `.cursor/issues/warpsense-micro-feedback-feature.md`.

## Summary

The issue follows the Create Issue (Deep Capture Mode) template and covers:

### Structure

1. **Pre-issue thinking** – Brain dump, 20+ questions, Five Whys
2. **Information gathering** – Codebase search, docs, related features
3. **Thinking checkpoints** – Assumptions, edge cases, red-teaming
4. **11 core sections** – Title, TL;DR, current state, desired outcome, scope, constraints, related context, open questions, risks, classification, strategic context

### Findings from the codebase

- **FeedbackPanel** – Uses `FeedbackItem` (severity, message, suggestion) but no `frameIndex` or `type`
- **generateAIFeedback** – Session-level only; can extend with a parallel `generateMicroFeedback(frames)`
- **Frame** – Has `angle_degrees`, `volts`, `amps`, `thermal_snapshots`, `heat_dissipation_rate_celsius_per_sec`
- **extractFivePointFromFrame** – Can be used for thermal symmetry (N/S/E/W)
- **Replay** – Timeline slider + `currentTimestamp`; suitable for click-to-scrub from feedback
- **WebGL** – Max 1–2 Canvas per page; no new Canvas for overlay without cutting elsewhere

### Phased scope

- **Phase 1 (in scope):** Angle drift + thermal symmetry, `MicroFeedbackItem` type, FeedbackPanel changes, timeline markers
- **Phase 2+ (out):** Voltage/amps, travel speed, cooling rate, 3D overlay, configurable thresholds

### Metrics

- Word count: ~3,500
- Acceptance criteria: 12+
- Open questions: 10
- Risks: 8 with mitigations
- Effort: 24–40h (Phase 1 ~24h)

### Suggested next steps

1. Validate with a stakeholder (5–10 min)
2. Answer blocker questions (#2, #3, #6, #7 in Open Questions)
3. Run **Phase 2: Explore Feature** to decide client vs server, threshold details, and implementation approach

The issue is written so that someone can run the exploration phase without extra context.
