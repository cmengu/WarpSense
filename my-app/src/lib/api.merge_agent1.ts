/**
 * Agent 1 merge file — trajectory API.
 * Do not modify api.ts. Import shared utilities and add fetchTrajectory here.
 */
import { buildUrl, apiFetch } from "./api";
import type { WelderID } from "@/types/shared";
import type { WelderTrajectory } from "@/types/trajectory";

/**
 * Fetch longitudinal score history for a welder.
 */
export async function fetchTrajectory(
  welderId: WelderID
): Promise<WelderTrajectory> {
  const url = buildUrl(
    `/api/welders/${encodeURIComponent(welderId)}/trajectory`
  );
  return apiFetch<WelderTrajectory>(url);
}
