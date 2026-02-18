/**
 * Browser-only demo data for Seagull team path.
 *
 * Used by /demo/team and /demo/team/[welderId]. No fetchSession/fetchScore.
 * Thresholds from demo-config. Shape must match ai-feedback.test mockScore.
 */

import type { SessionScore } from "@/lib/api";
import {
  MOCK_EXPERT_SCORE_VALUE,
  MOCK_NOVICE_SCORE_VALUE,
  MOCK_NOVICE_FAILED_RULES,
  DEMO_WELDERS,
  type DemoWelder,
} from "@/lib/demo-config";
import { generateExpertSession, generateNoviceSession } from "@/lib/demo-data";
import { generateAIFeedback } from "@/lib/ai-feedback";
import type { Session } from "@/types/session";
import type { AIFeedbackResult } from "@/types/ai-feedback";

/** Must match RULE_TEMPLATES keys in ai-feedback.ts. Do not add unknown rule_ids. */
const RULE_IDS = [
  "amps_stability",
  "angle_consistency",
  "thermal_symmetry",
  "heat_diss_consistency",
  "volts_stability",
] as const;

const RULE_THRESHOLDS: Record<string, number> = {
  amps_stability: 3,
  angle_consistency: 5,
  thermal_symmetry: 10,
  heat_diss_consistency: 2,
  volts_stability: 1.5,
};

/**
 * Create SessionScore in shape expected by generateAIFeedback.
 * rule_ids must match RULE_TEMPLATES exactly.
 *
 * @param total - Total score 0–100.
 * @param failedRuleIds - Rule IDs that failed (passed = false).
 */
export function createMockScore(
  total: number,
  failedRuleIds: string[],
  activeThresholdSpec?: SessionScore["active_threshold_spec"]
): SessionScore {
  const rules = RULE_IDS.map((rule_id) => ({
    rule_id,
    threshold: RULE_THRESHOLDS[rule_id] ?? 5,
    passed: !failedRuleIds.includes(rule_id),
    actual_value: failedRuleIds.includes(rule_id) ? 5.5 : 2.0,
  }));
  const out: SessionScore = { total, rules };
  if (activeThresholdSpec) out.active_threshold_spec = activeThresholdSpec;
  return out;
}

export const MOCK_EXPERT_SCORE = createMockScore(MOCK_EXPERT_SCORE_VALUE, []);
export const MOCK_NOVICE_SCORE = createMockScore(MOCK_NOVICE_SCORE_VALUE, [
  ...MOCK_NOVICE_FAILED_RULES,
]);

const MOCK_HISTORICAL = [68, 72, 75];

export interface DemoTeamData {
  session: Session;
  expertSession: Session;
  score: SessionScore;
  report: AIFeedbackResult;
}

const WELDER_MAP: Record<string, "novice" | "expert"> = Object.fromEntries(
  DEMO_WELDERS.map((w) => [w.id, w.variant])
);

/**
 * Get browser-only team data for a welder.
 * Config-driven welder list; dynamic count for QA/demos.
 *
 * @param welderId - Welder ID (e.g. 'mike-chen', 'expert-benchmark').
 */
export function getDemoTeamData(welderId: string): DemoTeamData {
  const expertSession = generateExpertSession();
  const variant = WELDER_MAP[welderId] ?? "novice";
  const session =
    variant === "novice" ? generateNoviceSession() : expertSession;
  const score =
    variant === "novice" ? MOCK_NOVICE_SCORE : MOCK_EXPERT_SCORE;
  const report = generateAIFeedback(session, score, MOCK_HISTORICAL);
  return { session, expertSession, score, report };
}

/**
 * Async wrapper to mimic network delay. Use for backend integration readiness.
 * delayMs defaults to 50–150ms to reduce surprises when switching to real API.
 */
export async function getDemoTeamDataAsync(
  welderId: string,
  delayMs: number = 80
): Promise<DemoTeamData> {
  await new Promise((r) => setTimeout(r, delayMs));
  return getDemoTeamData(welderId);
}

export { DEMO_WELDERS };
export type { DemoWelder };
