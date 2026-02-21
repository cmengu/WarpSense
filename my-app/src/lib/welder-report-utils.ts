/**
 * Pure helpers for welder report fetch result processing.
 * Used by page and tests — changing this file changes both.
 *
 * HIST_FIRST_IDX: Must match page allPromises layout:
 *   indices 0,1,2 = primary, expert, score
 *   indices HIST_FIRST_IDX..trajectoryIdx-1 = hist (SessionScore)
 *   trajectoryIdx = trajectory (WelderTrajectory, MUST be last)
 * When adding a fetch before histPromises, update HIST_FIRST_IDX.
 * See Step 4.1 contract test that binds to page layout.
 */
import type { SessionScore } from "@/lib/api";

export const PRIMARY_RESULT_IDX = 0;
export const EXPERT_RESULT_IDX = 1;
export const SCORE_RESULT_IDX = 2;
export const HIST_FIRST_IDX = 3; // Must match allPromises: [primary, expert, score, ...hist, trajectory]

/**
 * Extract historical scores (number[]) from results, excluding trajectory.
 * trajectoryIdx MUST be the index of the trajectory result (last element).
 *
 * @throws Error if any element of historicalScores is not a finite number (production-safe).
 * Rejects NaN and Infinity.
 */
export function computeHistoricalScores(
  results: PromiseSettledResult<unknown>[],
  trajectoryIdx: number
): number[] {
  const histResults = results.slice(HIST_FIRST_IDX, trajectoryIdx);
  const lastIdx = histResults.length - 1;
  const scoreResult = results[SCORE_RESULT_IDX];
  const sc =
    scoreResult?.status === "fulfilled" ? (scoreResult.value as SessionScore) : null;

  const historicalScores = histResults.map((r, i) => {
    if (r.status === "fulfilled") return (r.value as SessionScore).total;
    if (i === lastIdx && sc != null) return sc.total;
    return 0;
  });

  const isValid = (x: unknown): x is number =>
    typeof x === "number" && !Number.isNaN(x) && Number.isFinite(x);

  if (!historicalScores.every(isValid)) {
    throw new Error(
      `WelderReport: historicalScores must be finite number[]; got: ${JSON.stringify(historicalScores)}`
    );
  }
  return historicalScores;
}

/**
 * Extract trajectory from results. trajectoryIdx MUST be the trajectory result index.
 */
export function getTrajectoryFromResults<T>(
  results: PromiseSettledResult<unknown>[],
  trajectoryIdx: number
): T | null {
  const r = results[trajectoryIdx];
  if (r?.status === "fulfilled") return r.value as T;
  return null;
}

/**
 * Asserts the result at trajectoryIdx is a WelderTrajectory (has welder_id).
 * Call before setTrajectory to enforce "trajectory last" invariant.
 * @throws Error if invariant violated.
 */
export function assertTrajectoryAtIdx(
  results: PromiseSettledResult<unknown>[],
  trajectoryIdx: number
): void {
  const r = results[trajectoryIdx];
  if (!r || r.status !== "fulfilled") return;
  const v = r.value as Record<string, unknown>;
  if (!v || typeof v.welder_id !== "string") {
    throw new Error(
      `WelderReport: trajectory invariant violated — result at index ${trajectoryIdx} is not WelderTrajectory (missing welder_id). Did you add a fetch after trajectoryPromise?`
    );
  }
}
