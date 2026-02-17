/**
 * TimelineMarkers — Renders micro-feedback markers on the replay timeline.
 *
 * Positions markers by frame timestamp; hides when duration <= 0 (single-frame).
 * Clickable to jump to frame (pause + setCurrentTimestamp).
 *
 * @see .cursor/issues/warpsense-micro-feedback-feature.md
 */

import type { MicroFeedbackItem } from "@/types/micro-feedback";
import type { Frame } from "@/types/frame";

const VALID_MICRO_TYPES = ["angle", "thermal"] as const;

/** Severity → marker color (WarpSense blue/purple palette). */
const SEVERITY_COLORS: Record<
  MicroFeedbackItem["severity"],
  { bg: string; border: string }
> = {
  info: { bg: "bg-blue-400", border: "border-blue-500" },
  warning: { bg: "bg-violet-500", border: "border-violet-600" },
  critical: { bg: "bg-amber-500", border: "border-amber-600" },
};

interface TimelineMarkersProps {
  /** Micro-feedback items to render as markers. */
  items: MicroFeedbackItem[];
  /** Frames for resolving timestamp from frameIndex. */
  frames: Frame[];
  /** First timestamp in session (ms). */
  firstTimestamp: number;
  /** Last timestamp in session (ms). */
  lastTimestamp: number;
  /** Called when user clicks a marker to jump to frame. */
  onFrameSelect: (timestamp_ms: number) => void;
}

/**
 * Renders clickable markers on the timeline for micro-feedback items.
 * Hides when duration <= 0 to avoid division by zero.
 */
export default function TimelineMarkers({
  items,
  frames,
  firstTimestamp,
  lastTimestamp,
  onFrameSelect,
}: TimelineMarkersProps) {
  const duration = lastTimestamp - firstTimestamp;
  if (duration <= 0 || !Array.isArray(frames) || frames.length === 0) {
    return null;
  }

  const validItems = items.filter((item) => {
    const hasValidType =
      item.type != null &&
      (VALID_MICRO_TYPES as readonly string[]).includes(item.type);
    const isValidIndex = item.frameIndex >= 0 && item.frameIndex < frames.length;
    const ts = frames[item.frameIndex]?.timestamp_ms;
    return hasValidType && isValidIndex && ts != null;
  });

  if (validItems.length === 0) return null;

  return (
    <div
      className="absolute top-0 left-0 right-0 h-2 pointer-events-none flex"
      aria-label="Timeline markers for frame-level feedback"
    >
      <div className="relative w-full h-full flex pointer-events-auto">
        {validItems.map((item) => {
          const ts = frames[item.frameIndex].timestamp_ms;
          const pct = ((ts - firstTimestamp) / duration) * 100;
          const style = SEVERITY_COLORS[item.severity];

          return (
            <button
              key={`marker-${item.frameIndex}-${item.type}`}
              type="button"
              onClick={() => onFrameSelect(ts)}
              className={`
                absolute w-3 h-3 -mt-0.5 -ml-1.5 rounded-full
                border-2 ${style.bg} ${style.border}
                hover:scale-125 focus:outline-none focus:ring-2 focus:ring-blue-400 focus:ring-offset-1
                transition-transform cursor-pointer
              `}
              style={{ left: `${pct}%` }}
              aria-label={`Jump to frame ${item.frameIndex}: ${item.message}`}
              data-testid="timeline-marker"
            />
          );
        })}
      </div>
    </div>
  );
}
