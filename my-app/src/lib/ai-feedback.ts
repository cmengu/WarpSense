/**
 * AI feedback engine for the Seagull pilot welder report.
 *
 * Pure function: maps SessionScore (from fetchScore) to AIFeedbackResult.
 * No React, no fetch — deterministic and testable.
 *
 * Uses rule templates for human-readable messages. New backend rules
 * need a template in RULE_TEMPLATES or fall back to generic format.
 */

import type { Session } from "@/types/session";
import type { SessionScore } from "@/lib/api";
import type { AIFeedbackResult, FeedbackItem } from "@/types/ai-feedback";

export const RULE_TEMPLATES: Record<
  string,
  (r: { actual_value: number | null; threshold: number }) => string
> = {
  amps_stability: (r) =>
    `Current fluctuated by ${r.actual_value?.toFixed(1) ?? "N/A"}A — aim for stability under ${r.threshold}A`,
  angle_consistency: (r) =>
    `Angle deviation ${r.actual_value?.toFixed(1) ?? "N/A"}° — keep within ±${r.threshold}° of 45°`,
  thermal_symmetry: (r) =>
    `North/south temp delta ${r.actual_value?.toFixed(1) ?? "N/A"}°C — aim for <${r.threshold}°C`,
  heat_diss_consistency: (r) =>
    `Heat dissipation variability ${r.actual_value?.toFixed(1) ?? "N/A"} — target <${r.threshold}`,
  volts_stability: (r) =>
    `Voltage range ${r.actual_value?.toFixed(1) ?? "N/A"}V — keep under ${r.threshold}V`,
};

/**
 * Generate AI-style feedback from session score and historical scores.
 *
 * Maps SessionScore rules to human-readable FeedbackItems.
 * Determines skill_level from total; trend from last 2 historical scores.
 *
 * @param _session - Session (unused for pilot; reserved for future use).
 * @param score - SessionScore from fetchScore.
 * @param historicalScores - Array of past scores (chronological order).
 * @returns AIFeedbackResult with score, skill_level, trend, summary, feedback_items.
 */
export function generateAIFeedback(
  _session: Session,
  score: SessionScore,
  historicalScores: number[]
): AIFeedbackResult {
  // Guard: empty score
  if (!score || !score.rules || score.rules.length === 0) {
    return {
      score: 0,
      skill_level: "Unknown",
      trend: "insufficient_data",
      summary: "No scoring rules available.",
      feedback_items: [],
    };
  }

  const total = score.total;
  const skill_level =
    total >= 80 ? "Advanced" : total >= 60 ? "Intermediate" : "Beginner";

  // Guard: insufficient historical data for trend
  const trend =
    historicalScores.length < 2
      ? "insufficient_data"
      : historicalScores[historicalScores.length - 1] >
        historicalScores[historicalScores.length - 2]
        ? "improving"
        : historicalScores[historicalScores.length - 1] <
            historicalScores[historicalScores.length - 2]
          ? "declining"
          : "stable";

  const failedRules = score.rules.filter((r) => !r.passed);
  const summary =
    failedRules.length === 0
      ? "Strong performance across all metrics."
      : `Focus on: ${failedRules.map((r) => r.rule_id.replace(/_/g, " ")).join(", ")}.`;

  // Guard: null actual_value in template
  const feedback_items: FeedbackItem[] = score.rules.map((rule) => {
    const template =
      RULE_TEMPLATES[rule.rule_id] ??
      ((r) => `${rule.rule_id}: ${r.actual_value ?? "N/A"} / ${r.threshold}`);
    const actualVal = rule.actual_value ?? null;
    return {
      severity: rule.passed ? "info" : "warning",
      message: template({ actual_value: actualVal, threshold: rule.threshold }),
      timestamp_ms: null,
      suggestion: rule.passed
        ? null
        : `Improve ${rule.rule_id.replace(/_/g, " ")}.`,
    };
  });

  return { score: total, skill_level, trend, summary, feedback_items };
}
