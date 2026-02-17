# WarpSense Micro-Feedback — Execution Summary

## Steps

1. File: `my-app/src/types/micro-feedback.ts`
   - Action: Create MicroFeedbackType, MicroFeedbackSeverity, MicroFeedbackItem (frameIndex + type required)
   - Key code: `MicroFeedbackItem { frameIndex: number; type: MicroFeedbackType; severity; message; suggestion? }`

2. File: `my-app/src/types/ai-feedback.ts`
   - Action: Add "critical" to FeedbackSeverity; add optional frameIndex?, type? to FeedbackItem
   - Key code: `FeedbackSeverity = "info" | "warning" | "critical"`

3. File: `my-app/src/lib/micro-feedback.ts`
   - Action: Create generateMicroFeedback, angle + thermal generators, hasAllCardinalReadings
   - Key code: `generateMicroFeedback(frames)` → try-catch; skip thermal if any N/S/E/W missing

4. File: `my-app/src/__tests__/lib/micro-feedback-prototype.test.ts`
   - Action: Migrate to import from @/lib/micro-feedback; add edge-case tests
   - Key code: `import { generateMicroFeedback } from "@/lib/micro-feedback"`

5. File: `my-app/src/components/welding/FeedbackPanel.tsx`
   - Action: Add SEVERITY_STYLES (info, warning, critical); add frames?, onFrameSelect?
   - Key code: `SEVERITY_STYLES: Record<FeedbackSeverity, { bg; border; icon }>`

6. File: `my-app/src/components/welding/FeedbackPanel.tsx`
   - Action: Clickable only when BOTH frameIndex AND type ("angle"|"thermal") valid; guard onFrameSelect
   - Key code: `const isClickable = hasFrameIndex && hasValidType && typeof onFrameSelect === "function"`

7. File: `my-app/src/components/welding/FeedbackPanel.tsx`
   - Action: Key format: `fb-${frameIndex}-${type}` for micro; `session-${severity}-${i}` for session
   - Key code: `key = hasFrameIndex && hasValidType ? \`fb-${item.frameIndex}-${item.type}\` : \`session-${i}\``

8. File: `my-app/src/app/replay/[sessionId]/page.tsx`
   - Action: useMemo generateMicroFeedback; FeedbackPanel; handleFrameSelect
   - Key code: `useMemo(() => generateMicroFeedback(sessionData?.frames ?? []), [sessionData?.frames])`

9. File: `my-app/src/app/replay/[sessionId]/page.tsx` (or TimelineMarkers)
   - Action: Timeline markers; position = duration>0 ? (ts-first)/duration*100 : 0; hide if duration<=0
   - Key code: `const pct = duration > 0 ? ((ts - firstTimestamp) / duration) * 100 : 0`

10. File: `my-app/src/components/welding/TimelineMarkers.tsx`
    - Action: Extract marker rendering; props: items, frames, firstTimestamp, lastTimestamp, onFrameSelect
    - Key code: New component; replay page imports and uses it

11. File: `my-app/src/app/replay/[sessionId]/page.tsx`
    - Action: "No feedback" when microFeedback.length === 0
    - Key code: `microFeedback.length === 0 && <p>No frame-level feedback</p>`

12. Files: FeedbackPanel, TimelineMarkers
    - Action: Add data-testid="micro-feedback-item", data-testid="timeline-marker"
    - Key code: `data-testid="micro-feedback-item"`

## Critical Details

- MicroFeedbackItem: frameIndex and type NEVER optional — required for click-to-scrub
- FeedbackPanel: clickable ONLY when BOTH frameIndex AND type present; guard onFrameSelect with typeof
- Thermal generator: skip frame if any N/S/E/W reading missing — never use DEFAULT_AMBIENT for variance
- Severity: grep all usages; every branch handles info|warning|critical
- Position formula: guard division by zero — duration <= 0 → hide markers
- Replay: 'use client'; generateMicroFeedback only in useMemo
- 10k frames perf target: <200ms
