/**
 * Tests for AI feedback engine (Seagull pilot Step 2).
 *
 * Validates:
 *   - generateAIFeedback returns valid AIFeedbackResult
 *   - Trend derived from historical scores (improving, stable, declining)
 *   - Empty/invalid score guards
 *   - feedback_items from rules with correct templates
 */

import { generateAIFeedback } from "@/lib/ai-feedback";
import type { SessionScore } from "@/lib/api";
import type { Session } from "@/types/session";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Minimal valid session (unused by engine but required by signature). */
function mockSession(): Session {
  return {
    session_id: "sess_001",
    operator_id: "op_42",
    start_time: "2026-02-07T10:00:00Z",
    weld_type: "butt_joint",
    thermal_sample_interval_ms: 100,
    thermal_directions: ["center", "north", "south", "east", "west"],
    thermal_distance_interval_mm: 10.0,
    sensor_sample_rate_hz: 100,
    frames: [],
    status: "recording",
    frame_count: 0,
    expected_frame_count: null,
    last_successful_frame_index: null,
    validation_errors: [],
    completed_at: null,
  };
}

/** Mock score with 5 rules (some pass, some fail). */
function mockScore(overrides: Partial<SessionScore> = {}): SessionScore {
  return {
    total: 75,
    rules: [
      {
        rule_id: "amps_stability",
        threshold: 3,
        passed: false,
        actual_value: 5.2,
      },
      {
        rule_id: "angle_consistency",
        threshold: 5,
        passed: true,
        actual_value: 3.1,
      },
      {
        rule_id: "thermal_symmetry",
        threshold: 10,
        passed: true,
        actual_value: 7.0,
      },
      {
        rule_id: "heat_diss_consistency",
        threshold: 2,
        passed: false,
        actual_value: null,
      },
      {
        rule_id: "volts_stability",
        threshold: 1.5,
        passed: true,
        actual_value: 0.8,
      },
    ],
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// generateAIFeedback — result shape and trend
// ---------------------------------------------------------------------------

describe("generateAIFeedback", () => {
  it("returns valid AIFeedbackResult with score, skill_level, trend, summary, feedback_items", () => {
    const result = generateAIFeedback(mockSession(), mockScore(), [72, 75]);

    expect(result).toHaveProperty("score", 75);
    expect(result).toHaveProperty("skill_level", "Intermediate");
    expect(result).toHaveProperty("trend", "improving");
    expect(result).toHaveProperty("summary");
    expect(result).toHaveProperty("feedback_items");
    expect(Array.isArray(result.feedback_items)).toBe(true);
    expect(result.feedback_items).toHaveLength(5);
  });

  it("trend is improving when latest > previous", () => {
    const result = generateAIFeedback(mockSession(), mockScore(), [72, 75]);
    expect(result.trend).toBe("improving");
  });

  it("trend is declining when latest < previous", () => {
    const result = generateAIFeedback(mockSession(), mockScore(), [78, 75]);
    expect(result.trend).toBe("declining");
  });

  it("trend is stable when latest === previous", () => {
    const result = generateAIFeedback(mockSession(), mockScore(), [75, 75]);
    expect(result.trend).toBe("stable");
  });

  it("trend is insufficient_data when < 2 historical scores", () => {
    expect(
      generateAIFeedback(mockSession(), mockScore(), []).trend
    ).toBe("insufficient_data");
    expect(
      generateAIFeedback(mockSession(), mockScore(), [75]).trend
    ).toBe("insufficient_data");
  });
});

// ---------------------------------------------------------------------------
// generateAIFeedback — last-slot historicalScores contract (Step 5.3)
// Caller must pass sc.total for last slot when available; never 0.
// Engine does not special-case 0; [..., 0] when prev is higher → "declining".
// ---------------------------------------------------------------------------

describe("generateAIFeedback — last-slot historicalScores", () => {
  it("trend is improving when last slot has real score and prev is lower", () => {
    const result = generateAIFeedback(
      mockSession(),
      mockScore({ total: 74 }),
      [58, 62, 66, 70, 74]
    );
    expect(result.trend).toBe("improving");
  });

  it("trend is declining when last slot is 0 and prev is higher (caller pitfall)", () => {
    const result = generateAIFeedback(
      mockSession(),
      mockScore({ total: 50 }),
      [72, 75, 78, 80, 0]
    );
    expect(result.trend).toBe("declining");
  });

  it("trend is declining when last slot has real lower score", () => {
    const result = generateAIFeedback(
      mockSession(),
      mockScore({ total: 60 }),
      [76, 72, 68, 64, 60]
    );
    expect(result.trend).toBe("declining");
  });

  it("trend is stable when last two scores equal", () => {
    const result = generateAIFeedback(
      mockSession(),
      mockScore({ total: 71 }),
      [68, 70, 71, 71]
    );
    expect(result.trend).toBe("stable");
  });
});

// ---------------------------------------------------------------------------
// generateAIFeedback — empty score guard
// ---------------------------------------------------------------------------

describe("generateAIFeedback — empty score guard", () => {
  it("returns early with Unknown, insufficient_data when score.rules is empty", () => {
    const result = generateAIFeedback(mockSession(), { total: 0, rules: [] }, [
      72,
      75,
    ]);

    expect(result.score).toBe(0);
    expect(result.skill_level).toBe("Unknown");
    expect(result.trend).toBe("insufficient_data");
    expect(result.summary).toBe("No scoring rules available.");
    expect(result.feedback_items).toEqual([]);
  });

  it("handles nullish score gracefully", () => {
    const result = generateAIFeedback(
      mockSession(),
      { total: 0, rules: [] } as SessionScore,
      []
    );
    expect(result.feedback_items).toEqual([]);
  });
});

// ---------------------------------------------------------------------------
// generateAIFeedback — feedback_items from rules
// ---------------------------------------------------------------------------

describe("generateAIFeedback — feedback_items", () => {
  it("maps each rule to a FeedbackItem with correct severity", () => {
    const result = generateAIFeedback(mockSession(), mockScore(), [72, 75]);

    // amps_stability: failed -> warning
    expect(result.feedback_items[0].severity).toBe("warning");
    expect(result.feedback_items[0].message).toContain("5.2");
    expect(result.feedback_items[0].message).toContain("3A");
    expect(result.feedback_items[0].suggestion).toBe("Improve amps stability.");

    // angle_consistency: passed -> info
    expect(result.feedback_items[1].severity).toBe("info");
    expect(result.feedback_items[1].suggestion).toBeNull();
  });

  it("uses N/A for null actual_value in template", () => {
    const result = generateAIFeedback(mockSession(), mockScore(), [72, 75]);
    // heat_diss_consistency has actual_value: null
    const heatDissItem = result.feedback_items.find(
      (f) => f.message.includes("Heat dissipation")
    );
    expect(heatDissItem?.message).toContain("N/A");
  });

  it("falls back to generic format for unknown rule_id", () => {
    const score = mockScore({
      rules: [
        {
          rule_id: "unknown_rule",
          threshold: 100,
          passed: false,
          actual_value: 50,
        },
      ],
    });
    const result = generateAIFeedback(mockSession(), score, [72, 75]);
    expect(result.feedback_items[0].message).toContain("unknown_rule");
    expect(result.feedback_items[0].message).toContain("50");
    expect(result.feedback_items[0].message).toContain("100");
  });
});

// ---------------------------------------------------------------------------
// generateAIFeedback — skill_level
// ---------------------------------------------------------------------------

describe("generateAIFeedback — skill_level", () => {
  it("Advanced when total >= 80", () => {
    const result = generateAIFeedback(
      mockSession(),
      mockScore({ total: 80 }),
      [72, 75]
    );
    expect(result.skill_level).toBe("Advanced");
  });

  it("Intermediate when 60 <= total < 80", () => {
    const result = generateAIFeedback(
      mockSession(),
      mockScore({ total: 60 }),
      [72, 75]
    );
    expect(result.skill_level).toBe("Intermediate");
  });

  it("Beginner when total < 60", () => {
    const result = generateAIFeedback(
      mockSession(),
      mockScore({ total: 40 }),
      [72, 75]
    );
    expect(result.skill_level).toBe("Beginner");
  });
});
