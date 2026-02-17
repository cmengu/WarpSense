/**
 * WarpSense Micro-Feedback — frame-level actionable guidance types.
 *
 * frameIndex and type are REQUIRED for micro-feedback items. Omit only for
 * session-level FeedbackItem. Never use optional here — it breaks click-to-scrub.
 *
 * @see .cursor/issues/warpsense-micro-feedback-feature.md
 * @see .cursor/explore/warpsense-micro-feedback-exploration.md
 */

/** Feedback type for frame-level micro-feedback (Phase 1 scope). */
export type MicroFeedbackType = "angle" | "thermal";

/**
 * Severity levels for micro-feedback.
 * - info: Minor note (e.g. rule passed)
 * - warning: Moderate deviation (e.g. 5–15° angle drift, thermal asymmetry)
 * - critical: Severe deviation (e.g. >15° angle drift)
 */
export type MicroFeedbackSeverity = "info" | "warning" | "critical";

/**
 * Single micro-feedback item anchored to a specific frame.
 *
 * frameIndex and type are REQUIRED — they enable click-to-scrub in replay.
 * Never optional for micro items.
 */
export interface MicroFeedbackItem {
  /** Frame index in Session.frames — required for jump-to-frame. */
  frameIndex: number;
  /** Feedback category — required for key uniqueness and validation. */
  type: MicroFeedbackType;
  severity: MicroFeedbackSeverity;
  message: string;
  /** Optional suggestion for the welder. */
  suggestion?: string;
}
