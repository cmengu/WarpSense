/**
 * Tests for seagull-demo-data.ts — createMockScore, getDemoTeamData.
 *
 * Validates: createMockScore shape matches generateAIFeedback contract,
 * every rule_id produces valid output, getDemoTeamData returns correct scores.
 */

import { createMockScore, getDemoTeamData } from "@/lib/seagull-demo-data";
import { MOCK_NOVICE_FAILED_RULES } from "@/lib/demo-config";
import { generateAIFeedback } from "@/lib/ai-feedback";
import { generateExpertSession } from "@/lib/demo-data";
import {
  MOCK_EXPERT_SCORE_VALUE,
  MOCK_NOVICE_SCORE_VALUE,
} from "@/lib/demo-config";

const RULE_IDS = [
  "amps_stability",
  "angle_consistency",
  "thermal_symmetry",
  "heat_diss_consistency",
  "volts_stability",
];

describe("seagull-demo-data", () => {
  describe("createMockScore", () => {
    it("createMockScore(94, []) yields total 94, 5 rules all passed", () => {
      const score = createMockScore(94, []);
      expect(score.total).toBe(94);
      expect(score.rules).toHaveLength(5);
      expect(score.rules.every((r) => r.passed)).toBe(true);
    });

    it("createMockScore(42, ['amps_stability']) yields at least one failed rule", () => {
      const score = createMockScore(42, ["amps_stability"]);
      expect(score.total).toBe(42);
      const failed = score.rules.filter((r) => !r.passed);
      expect(failed.length).toBeGreaterThanOrEqual(1);
      expect(failed.some((r) => r.rule_id === "amps_stability")).toBe(true);
    });

    it("generateAIFeedback accepts createMockScore(94, [])", () => {
      const session = generateExpertSession();
      const score = createMockScore(94, []);
      const result = generateAIFeedback(session, score, [72, 75]);
      expect(result.feedback_items).toHaveLength(5);
      expect(result.score).toBe(94);
    });

    it("generateAIFeedback accepts createMockScore(42, MOCK_NOVICE_FAILED_RULES)", () => {
      const session = generateExpertSession();
      const score = createMockScore(42, [...MOCK_NOVICE_FAILED_RULES]);
      const result = generateAIFeedback(session, score, [72, 75]);
      expect(result.feedback_items.length).toBeGreaterThan(0);
      expect(result.score).toBe(42);
      expect(result.summary).toContain("Focus on");
    });

    it.each(RULE_IDS)(
      "createMockScore with %s as failed produces valid generateAIFeedback output",
      (ruleId) => {
        const session = generateExpertSession();
        const score = createMockScore(50, [ruleId]);
        const result = generateAIFeedback(session, score, [72, 75]);
        expect(result.feedback_items).toHaveLength(5);
        const failedItem = result.feedback_items.find(
          (f) => f.severity === "warning"
        );
        expect(failedItem).toBeDefined();
      }
    );
  });

  describe("getDemoTeamData", () => {
    it("getDemoTeamData('mike-chen') returns report.score === 42", () => {
      const data = getDemoTeamData("mike-chen");
      expect(data.report.score).toBe(MOCK_NOVICE_SCORE_VALUE);
      expect(data.report.score).toBe(42);
    });

    it("getDemoTeamData('expert-benchmark') returns report.score === 94", () => {
      const data = getDemoTeamData("expert-benchmark");
      expect(data.report.score).toBe(MOCK_EXPERT_SCORE_VALUE);
      expect(data.report.score).toBe(94);
    });

    it("getDemoTeamData returns session, expertSession, score, report", () => {
      const data = getDemoTeamData("mike-chen");
      expect(data.session).toBeDefined();
      expect(data.expertSession).toBeDefined();
      expect(data.score).toBeDefined();
      expect(data.report).toBeDefined();
      expect(data.session.frames).toBeDefined();
      expect(data.expertSession.frames).toBeDefined();
    });

    it("unknown welderId defaults to novice", () => {
      const data = getDemoTeamData("unknown-welder");
      expect(data.report.score).toBe(42);
    });
  });
});
