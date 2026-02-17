/**
 * Validation tests for demo-config.ts.
 *
 * Ensures NOVICE_SPIKE_MS, score thresholds, and DEMO_WELDERS match plan values.
 */

import {
  NOVICE_SPIKE_MS,
  MOCK_EXPERT_SCORE_VALUE,
  MOCK_NOVICE_SCORE_VALUE,
  MOCK_NOVICE_FAILED_RULES,
  DEMO_WELDERS,
} from "@/lib/demo-config";

describe("demo-config", () => {
  it("NOVICE_SPIKE_MS equals 2400", () => {
    expect(NOVICE_SPIKE_MS).toBe(2400);
  });

  it("MOCK_EXPERT_SCORE_VALUE equals 94", () => {
    expect(MOCK_EXPERT_SCORE_VALUE).toBe(94);
  });

  it("MOCK_NOVICE_SCORE_VALUE equals 42", () => {
    expect(MOCK_NOVICE_SCORE_VALUE).toBe(42);
  });

  it("DEMO_WELDERS has at least 2 entries", () => {
    expect(DEMO_WELDERS.length).toBeGreaterThanOrEqual(2);
  });

  it("DEMO_WELDERS[0] is mike-chen with score 42", () => {
    expect(DEMO_WELDERS[0].id).toBe("mike-chen");
    expect(DEMO_WELDERS[0].score).toBe(42);
  });

  it("DEMO_WELDERS[1] is expert-benchmark with score 94", () => {
    expect(DEMO_WELDERS[1].id).toBe("expert-benchmark");
    expect(DEMO_WELDERS[1].score).toBe(94);
  });

  it("MOCK_NOVICE_FAILED_RULES contains amps_stability, angle_consistency, thermal_symmetry", () => {
    expect(MOCK_NOVICE_FAILED_RULES).toContain("amps_stability");
    expect(MOCK_NOVICE_FAILED_RULES).toContain("angle_consistency");
    expect(MOCK_NOVICE_FAILED_RULES).toContain("thermal_symmetry");
  });
});
