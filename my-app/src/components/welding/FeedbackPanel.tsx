/**
 * FeedbackPanel — Renders AI feedback items with severity styling.
 *
 * Used by WelderReport page to display per-rule feedback.
 * Info items (passed rules): blue. Warning items (failed rules): amber.
 */

import type { FeedbackItem } from "@/types/ai-feedback";

interface FeedbackPanelProps {
  items: FeedbackItem[];
}

export default function FeedbackPanel({ items }: FeedbackPanelProps) {
  return (
    <div className="space-y-3">
      {items.map((item, i) => (
        <div
          key={`${item.severity}-${i}-${item.message.slice(0, 40)}`}
          className={`
            p-4 rounded-lg border-l-4
            ${
              item.severity === "warning"
                ? "bg-amber-50 dark:bg-amber-950/20 border-amber-500"
                : "bg-blue-50 dark:bg-blue-950/20 border-blue-500"
            }
          `}
        >
          <div className="flex items-start gap-3">
            <span className="text-xl">
              {item.severity === "warning" ? "⚠️" : "ℹ️"}
            </span>
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
        </div>
      ))}
    </div>
  );
}
