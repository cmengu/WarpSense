/**
 * FeedbackPanel — Renders AI feedback items with severity styling.
 *
 * Used by WelderReport page (session-level) and Replay page (micro-feedback).
 * Session-level: severity, message; no frameIndex/type.
 * Micro-level: frameIndex + type — clickable to jump to frame when onFrameSelect provided.
 */

import type { FeedbackItem, FeedbackSeverity } from "@/types/ai-feedback";
import type { MicroFeedbackItem } from "@/types/micro-feedback";
import type { Frame } from "@/types/frame";
import { logWarn } from "@/lib/logger";

const VALID_MICRO_TYPES = ["angle", "thermal"] as const;

const SEVERITY_STYLES: Record<
  FeedbackSeverity,
  { bg: string; border: string; icon: string }
> = {
  info: {
    bg: "bg-blue-50 dark:bg-blue-950/20",
    border: "border-blue-500",
    icon: "ℹ️",
  },
  warning: {
    bg: "bg-violet-50 dark:bg-violet-950/20",
    border: "border-violet-500",
    icon: "⚠️",
  },
  critical: {
    bg: "bg-amber-50 dark:bg-amber-950/20",
    border: "border-amber-500",
    icon: "⛔",
  },
};

function getSeverityStyle(severity: FeedbackSeverity) {
  if (severity in SEVERITY_STYLES) {
    return SEVERITY_STYLES[severity as keyof typeof SEVERITY_STYLES];
  }
  logWarn("FeedbackPanel", `Unknown FeedbackSeverity: ${severity}, falling back to info`);
  return SEVERITY_STYLES.info;
}

interface FeedbackPanelProps {
  /** Session-level (FeedbackItem) or frame-level (MicroFeedbackItem) feedback. */
  items: (FeedbackItem | MicroFeedbackItem)[];
  /** Frames for resolving timestamp from frameIndex (Replay only). */
  frames?: Frame[];
  /** Called when user clicks a micro-feedback item to jump to frame (Replay only). */
  onFrameSelect?: (timestamp_ms: number) => void;
}

export default function FeedbackPanel({
  items,
  frames,
  onFrameSelect,
}: FeedbackPanelProps) {
  return (
    <div className="space-y-3" role="list" aria-live="polite">
      {items.map((item, i) => {
        const hasFrameIndex =
          "frameIndex" in item &&
          typeof item.frameIndex === "number" &&
          Number.isInteger(item.frameIndex) &&
          item.frameIndex >= 0;
        const hasValidType =
          "type" in item &&
          item.type != null &&
          (VALID_MICRO_TYPES as readonly string[]).includes(item.type as string);
        const isMicroItem = hasFrameIndex && hasValidType;
        const framesArray = frames && Array.isArray(frames) ? frames : [];
        const frameIdx =
          isMicroItem && typeof item.frameIndex === "number" ? item.frameIndex : null;
        const isValidFrameIndex =
          frameIdx != null && frameIdx < framesArray.length;
        const timestamp_ms = isValidFrameIndex && frameIdx != null
          ? framesArray[frameIdx]?.timestamp_ms ?? null
          : null;
        const isClickable =
          isMicroItem &&
          isValidFrameIndex &&
          timestamp_ms != null &&
          typeof onFrameSelect === "function";

        const key =
          hasFrameIndex && hasValidType
            ? `fb-${item.frameIndex}-${item.type}`
            : `session-${item.severity}-${i}`;
        const style = getSeverityStyle(item.severity);

        const content = (
          <div className="flex items-start gap-3">
            <span className="text-xl">{style.icon}</span>
            <div className="flex-1">
              <p className="text-sm font-medium text-zinc-900 dark:text-zinc-100">
                {item.message}
              </p>
              {item.suggestion && (
                <p className="text-xs text-zinc-600 dark:text-zinc-400 mt-1">
                  💡 {item.suggestion}
                </p>
              )}
            </div>
          </div>
        );

        if (isClickable) {
          return (
            <button
              key={key}
              type="button"
              onClick={() => {
                if (
                  typeof onFrameSelect === "function" &&
                  timestamp_ms != null
                ) {
                  onFrameSelect(timestamp_ms);
                }
              }}
              className={`
                w-full text-left p-4 rounded-lg border-l-4 transition-colors
                hover:opacity-90 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-400
                ${style.bg} ${style.border}
              `}
              aria-label={`Jump to frame ${frameIdx}: ${item.message}`}
              data-testid="micro-feedback-item"
            >
              {content}
            </button>
          );
        }

        return (
          <div
            key={key}
            className={`p-4 rounded-lg border-l-4 ${style.bg} ${style.border}`}
            data-testid={isMicroItem ? "micro-feedback-item" : "feedback-item"}
          >
            {content}
          </div>
        );
      })}
    </div>
  );
}
