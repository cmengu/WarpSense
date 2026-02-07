/**
 * Hook for parsing and filtering frame data safely.
 *
 * Wraps the utility functions from `frameUtils.ts` in a React hook
 * with memoization, so components can efficiently access thermal data,
 * filter frames, and extract sensor readings.
 */

import { useMemo } from "react";

import type { Frame } from "@/types/frame";
import {
  filterThermalFrames,
  filterFramesByTimeRange,
} from "@/utils/frameUtils";

// ---------------------------------------------------------------------------
// Return type
// ---------------------------------------------------------------------------

export interface FrameDataResult {
  /** All frames (pass-through). */
  all_frames: Frame[];
  /** Only frames with thermal data. */
  thermal_frames: Frame[];
  /** Total frame count. */
  total_count: number;
  /** Count of frames with thermal data. */
  thermal_count: number;
  /** Whether any frames have thermal data. */
  has_any_thermal: boolean;
  /** First frame timestamp in ms (or null if empty). */
  first_timestamp_ms: number | null;
  /** Last frame timestamp in ms (or null if empty). */
  last_timestamp_ms: number | null;
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

/**
 * React hook that derives filtered/parsed frame data.
 *
 * Memoized on the frames array, startMs, and endMs.
 *
 * @param frames - Array of frames to process.
 * @param startMs - Optional time range start in ms (inclusive). Null = no lower bound.
 * @param endMs - Optional time range end in ms (inclusive). Null = no upper bound.
 * @returns Processed frame data with thermal filtering and counts.
 */
export function useFrameData(
  frames: Frame[],
  startMs: number | null = null,
  endMs: number | null = null
): FrameDataResult {
  return useMemo(() => {
    // Apply time range filter first
    const rangeFiltered = filterFramesByTimeRange(frames, startMs, endMs);

    // Then extract thermal-only subset
    const thermalOnly = filterThermalFrames(rangeFiltered);

    return {
      all_frames: rangeFiltered,
      thermal_frames: thermalOnly,
      total_count: rangeFiltered.length,
      thermal_count: thermalOnly.length,
      has_any_thermal: thermalOnly.length > 0,
      first_timestamp_ms:
        rangeFiltered.length > 0 ? rangeFiltered[0].timestamp_ms : null,
      last_timestamp_ms:
        rangeFiltered.length > 0
          ? rangeFiltered[rangeFiltered.length - 1].timestamp_ms
          : null,
    };
  }, [frames, startMs, endMs]);
}
