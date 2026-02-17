/**
 * Demo mode configuration — single source of truth for thresholds and mock data.
 *
 * Mock and real AI logic share these values. Do not duplicate anywhere.
 * CEO rule: No magic numbers outside this file.
 */

/** Timestamp (ms) for novice temperature spike narrative. Sine peak ~2.4–2.6s. */
export const NOVICE_SPIKE_MS = 2400;

/** Mock expert score (all rules pass). */
export const MOCK_EXPERT_SCORE_VALUE = 94;

/** Mock novice score (3 rules fail). */
export const MOCK_NOVICE_SCORE_VALUE = 42;

/** Failed rule IDs for novice mock. Must match RULE_TEMPLATES keys in ai-feedback.ts. */
export const MOCK_NOVICE_FAILED_RULES = [
  "amps_stability",
  "angle_consistency",
  "thermal_symmetry",
] as const;

export interface DemoWelder {
  id: string;
  name: string;
  score: number;
  variant: "novice" | "expert";
}

/** Welders for team dashboard. Extend for QA/demos with more welders. */
export const DEMO_WELDERS: DemoWelder[] = [
  { id: "mike-chen", name: "Mike Chen", score: 42, variant: "novice" },
  {
    id: "expert-benchmark",
    name: "Expert Benchmark",
    score: 94,
    variant: "expert",
  },
];
