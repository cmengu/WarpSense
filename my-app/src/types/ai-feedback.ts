/**
 * AI feedback types for the Seagull pilot welder report.
 *
 * Data contract for generateAIFeedback(session, score, historical) → AIFeedbackResult.
 * These types underpin the FeedbackPanel and WelderReport UI.
 *
 * Severity and trend values are explicit unions — no magic strings.
 */

// ---------------------------------------------------------------------------
// FeedbackItem
// ---------------------------------------------------------------------------

/**
 * Severity of a feedback item.
 * 'info' = rule passed; 'warning' = rule failed.
 */
export type FeedbackSeverity = "info" | "warning";

/**
 * Single feedback item derived from a scoring rule.
 *
 * Each rule in SessionScore maps to one FeedbackItem with a human-readable
 * message and optional suggestion when the rule failed.
 */
export interface FeedbackItem {
  /** info = passed; warning = failed. */
  severity: FeedbackSeverity;
  /** Human-readable message (e.g. "Current fluctuated by 5.2A — aim for stability under 3A"). */
  message: string;
  /** Optional timestamp in ms when the issue occurred. null = not applicable. */
  timestamp_ms: number | null;
  /** Suggestion when rule failed (e.g. "Improve amps stability."). null when passed. */
  suggestion: string | null;
}

// ---------------------------------------------------------------------------
// Trend
// ---------------------------------------------------------------------------

/**
 * Skill trend derived from historical scores.
 *
 * Requires at least 2 historical scores to compute.
 * 'insufficient_data' when < 2 scores.
 */
export type FeedbackTrend =
  | "improving" // latest > previous
  | "stable" // latest === previous
  | "declining" // latest < previous
  | "insufficient_data"; // < 2 historical scores

// ---------------------------------------------------------------------------
// AIFeedbackResult
// ---------------------------------------------------------------------------

/**
 * Result of generateAIFeedback.
 *
 * Contains score, skill level label, trend, summary string, and per-rule
 * feedback items. Used by WelderReport page and FeedbackPanel.
 */
export interface AIFeedbackResult {
  /** Total score 0–100 (from SessionScore.total). */
  score: number;
  /** Skill level label: "Beginner" | "Intermediate" | "Advanced" | "Unknown". */
  skill_level: string;
  /** Trend derived from historical scores. */
  trend: FeedbackTrend;
  /** Human-readable summary (e.g. "Focus on: amps stability, angle consistency."). */
  summary: string;
  /** Per-rule feedback items (one per rule in SessionScore.rules). */
  feedback_items: FeedbackItem[];
}
