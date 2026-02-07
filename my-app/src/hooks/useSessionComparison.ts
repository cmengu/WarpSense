/**
 * Hook for comparing two welding sessions.
 *
 * Mirrors the backend `compare_sessions()` logic from
 * `backend/services/comparison_service.py` — aligns frames by
 * timestamp only (no role assumption) and computes deltas.
 *
 * This runs entirely on the frontend for responsiveness.
 * The backend comparison service is the source of truth for
 * persisted comparisons.
 */

import { useMemo } from "react";

import type { Frame } from "@/types/frame";
import type { Session } from "@/types/session";
import type {
  FrameDelta,
  ThermalDelta,
  TemperatureDelta,
} from "@/types/comparison";

// ---------------------------------------------------------------------------
// Return type
// ---------------------------------------------------------------------------

export interface SessionComparisonResult {
  /** Frame-by-frame deltas for shared timestamps (session_a - session_b). */
  deltas: FrameDelta[];
  /** Number of shared timestamps. */
  shared_count: number;
  /** Timestamps only in session A. */
  only_in_a_count: number;
  /** Timestamps only in session B. */
  only_in_b_count: number;
  /** Total timestamps in session A. */
  total_a: number;
  /** Total timestamps in session B. */
  total_b: number;
}

// ---------------------------------------------------------------------------
// Pure comparison functions (deterministic, no side effects)
// ---------------------------------------------------------------------------

/**
 * Compute the delta of two optional numbers.
 * Returns null if either value is null.
 *
 * @param a - Value from session A.
 * @param b - Value from session B.
 * @returns (a - b) or null.
 */
export function deltaOptional(
  a: number | null,
  b: number | null
): number | null {
  if (a === null || b === null) return null;
  return a - b;
}

/**
 * Compute thermal deltas between two frames.
 *
 * Only compares snapshots at distances that exist in both frames.
 * Only compares readings at directions that exist in both snapshots.
 *
 * @param frameA - Frame from session A.
 * @param frameB - Frame from session B.
 * @returns Array of ThermalDelta (empty if either has no thermal data).
 */
export function computeThermalDeltas(
  frameA: Frame,
  frameB: Frame
): ThermalDelta[] {
  if (!frameA.has_thermal_data || !frameB.has_thermal_data) {
    return [];
  }
  if (!frameA.thermal_snapshots || !frameB.thermal_snapshots) {
    return [];
  }

  // Index B snapshots by distance for O(1) lookup
  const bByDistance = new Map(
    frameB.thermal_snapshots.map((s) => [s.distance_mm, s])
  );

  const deltas: ThermalDelta[] = [];

  for (const snapA of frameA.thermal_snapshots) {
    const snapB = bByDistance.get(snapA.distance_mm);
    if (!snapB) continue;
    if (!snapA.readings || !snapB.readings) continue;

    // Index B readings by direction
    const bByDir = new Map(
      snapB.readings.map((r) => [r.direction, r])
    );

    const tempDeltas: TemperatureDelta[] = [];
    for (const readingA of snapA.readings) {
      const readingB = bByDir.get(readingA.direction);
      if (!readingB) continue;
      tempDeltas.push({
        direction: readingA.direction,
        delta_temp_celsius: readingA.temp_celsius - readingB.temp_celsius,
      });
    }

    deltas.push({
      distance_mm: snapA.distance_mm,
      readings: tempDeltas,
    });
  }

  return deltas;
}

/**
 * Compare two sessions by aligning frames on timestamp.
 *
 * Pure function — mirrors `backend/services/comparison_service.py → compare_sessions`.
 * Only timestamps present in BOTH sessions produce deltas.
 *
 * @param sessionA - First session.
 * @param sessionB - Second session.
 * @returns Comparison result with deltas and counts.
 */
export function compareSessions(
  sessionA: Session,
  sessionB: Session
): SessionComparisonResult {
  // Index frames by timestamp
  const framesA = new Map<number, Frame>(
    sessionA.frames.map((f) => [f.timestamp_ms, f])
  );
  const framesB = new Map<number, Frame>(
    sessionB.frames.map((f) => [f.timestamp_ms, f])
  );

  // Find shared timestamps (sorted)
  const sharedTimestamps = [...framesA.keys()]
    .filter((t) => framesB.has(t))
    .sort((a, b) => a - b);

  const deltas: FrameDelta[] = sharedTimestamps.map((timestamp) => {
    const fA = framesA.get(timestamp)!;
    const fB = framesB.get(timestamp)!;

    return {
      timestamp_ms: timestamp,
      amps_delta: deltaOptional(fA.amps, fB.amps),
      volts_delta: deltaOptional(fA.volts, fB.volts),
      angle_degrees_delta: deltaOptional(fA.angle_degrees, fB.angle_degrees),
      heat_dissipation_rate_celsius_per_sec_delta: deltaOptional(
        fA.heat_dissipation_rate_celsius_per_sec,
        fB.heat_dissipation_rate_celsius_per_sec
      ),
      thermal_deltas: computeThermalDeltas(fA, fB),
    };
  });

  const onlyInA = [...framesA.keys()].filter((t) => !framesB.has(t)).length;
  const onlyInB = [...framesB.keys()].filter((t) => !framesA.has(t)).length;

  return {
    deltas,
    shared_count: sharedTimestamps.length,
    only_in_a_count: onlyInA,
    only_in_b_count: onlyInB,
    total_a: sessionA.frames.length,
    total_b: sessionB.frames.length,
  };
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

/**
 * React hook that compares two sessions, memoized on session references.
 *
 * Performance: Comparison is O(n) in total frames (indexing + shared timestamp scan).
 * For very large sessions (e.g. 10k+ frames each), consider server-side comparison
 * or pagination; client-side comparison may block rendering briefly.
 *
 * @param sessionA - First session (or null if not loaded).
 * @param sessionB - Second session (or null if not loaded).
 * @returns Comparison result, or null if either session is null.
 */
export function useSessionComparison(
  sessionA: Session | null,
  sessionB: Session | null
): SessionComparisonResult | null {
  return useMemo(() => {
    if (!sessionA || !sessionB) return null;
    return compareSessions(sessionA, sessionB);
  }, [sessionA, sessionB]);
}
