/**
 * Tests for AI feedback types (Seagull pilot Step 1).
 *
 * Validates:
 *   - Types compile and import successfully
 *   - AIFeedbackResult has score, skill_level, trend, summary, feedback_items
 *   - FeedbackItem has severity, message, timestamp_ms, suggestion
 *   - FeedbackTrend accepts all four literal values
 */

import type {
  AIFeedbackResult,
  FeedbackItem,
  FeedbackSeverity,
  FeedbackTrend,
} from "@/types/ai-feedback";

// ---------------------------------------------------------------------------
// Import verification (TypeScript compiles)
// ---------------------------------------------------------------------------

describe("AI feedback types — import and structure", () => {
  it("AIFeedbackResult has all required keys", () => {
    const result: AIFeedbackResult = {
      score: 75,
      skill_level: "Intermediate",
      trend: "improving",
      summary: "Strong performance across all metrics.",
      feedback_items: [],
    };
    expect(result).toHaveProperty("score", 75);
    expect(result).toHaveProperty("skill_level", "Intermediate");
    expect(result).toHaveProperty("trend", "improving");
    expect(result).toHaveProperty("summary");
    expect(result).toHaveProperty("feedback_items");
    expect(Array.isArray(result.feedback_items)).toBe(true);
  });

  it("FeedbackItem has severity, message, timestamp_ms, suggestion", () => {
    const item: FeedbackItem = {
      severity: "warning",
      message: "Current fluctuated by 5.2A — aim for stability under 3A",
      timestamp_ms: null,
      suggestion: "Improve amps stability.",
    };
    expect(item).toHaveProperty("severity", "warning");
    expect(item).toHaveProperty("message");
    expect(item).toHaveProperty("timestamp_ms");
    expect(item).toHaveProperty("suggestion");
  });

  it("FeedbackSeverity accepts info, warning, and critical", () => {
    const info: FeedbackSeverity = "info";
    const warning: FeedbackSeverity = "warning";
    const critical: FeedbackSeverity = "critical";
    expect(info).toBe("info");
    expect(warning).toBe("warning");
    expect(critical).toBe("critical");
  });

  it("FeedbackItem with optional frameIndex and type (micro-feedback)", () => {
    const item: FeedbackItem = {
      severity: "warning",
      message: "Torch angle drifted 12° at frame 420 — keep within ±5°",
      timestamp_ms: null,
      suggestion: "Maintain consistent work angle.",
      frameIndex: 420,
      type: "angle",
    };
    expect(item.frameIndex).toBe(420);
    expect(item.type).toBe("angle");
  });

  it("FeedbackTrend accepts all four values", () => {
    const improving: FeedbackTrend = "improving";
    const stable: FeedbackTrend = "stable";
    const declining: FeedbackTrend = "declining";
    const insufficient: FeedbackTrend = "insufficient_data";
    expect([improving, stable, declining, insufficient]).toHaveLength(4);
  });

  it("AIFeedbackResult with full feedback_items compiles", () => {
    const items: FeedbackItem[] = [
      {
        severity: "info",
        message: "Angle within target.",
        timestamp_ms: null,
        suggestion: null,
      },
      {
        severity: "warning",
        message: "Current fluctuated by 5.2A.",
        timestamp_ms: 1000,
        suggestion: "Improve amps stability.",
      },
    ];
    const result: AIFeedbackResult = {
      score: 60,
      skill_level: "Intermediate",
      trend: "declining",
      summary: "Focus on: amps stability.",
      feedback_items: items,
    };
    expect(result.feedback_items).toHaveLength(2);
  });
});
