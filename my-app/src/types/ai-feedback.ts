/**
 * AI feedback types for the Seagull pilot welder report.
 *
 * Data contract for generateAIFeedback(session, score, historical) → AIFeedbackResult.
 * These types underpin the FeedbackPanel and WelderReport UI.
 *
 * Severity and trend values are explicit unions — no magic strings.
 *
 * WarpSense Micro-Feedback: FeedbackItem extends with optional frameIndex and type
 * for frame-level items. Session-level items omit both.
 */

import type { MicroFeedbackType } from "./micro-feedback";

// ---------------------------------------------------------------------------
// FeedbackItem
// ---------------------------------------------------------------------------

/**
 * Severity of a feedback item.
 * 'info' = rule passed; 'warning' = rule failed; 'critical' = severe deviation (micro-feedback).
 */
export type FeedbackSeverity = "info" | "warning" | "critical";

/**
 * Single feedback item derived from a scoring rule or micro-feedback.
 *
 * Session-level (WelderReport): severity, message, timestamp_ms, suggestion.
 * Micro-level (Replay): add frameIndex + type — required for click-to-scrub.
 */
export interface FeedbackItem {
  /** info = passed; warning = failed; critical = severe deviation. */
  severity: FeedbackSeverity;
  /** Human-readable message (e.g. "Current fluctuated by 5.2A — aim for stability under 3A"). */
  message: string;
  /** Optional timestamp in ms when the issue occurred. null = not applicable. */
  timestamp_ms: number | null;
  /** Suggestion when rule failed (e.g. "Improve amps stability."). null when passed. */
  suggestion: string | null;
  /** Frame index for micro-feedback — present only on frame-level items. */
  frameIndex?: number;
  /** Feedback type for micro-feedback — present only on frame-level items. */
  type?: MicroFeedbackType;
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
