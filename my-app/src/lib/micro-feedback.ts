/**
 * WarpSense Micro-Feedback — frame-level actionable guidance.
 *
 * Generates MicroFeedbackItem[] from frames for angle drift and thermal symmetry.
 * Client-side only; called after fetchSession. Precompute once per session.
 *
 * API: v1 — exported types and generateMicroFeedback. Changes are documented in CHANGELOG.
 *
 * @see .cursor/issues/warpsense-micro-feedback-feature.md
 * @see .cursor/explore/warpsense-micro-feedback-exploration.md
 */

import type { Frame } from "@/types/frame";
import type { WeldTypeThresholds } from "@/types/thresholds";
import { logWarn } from "@/lib/logger";
import { extractFivePointFromFrame } from "@/utils/frameUtils";
import type {
  MicroFeedbackItem,
  MicroFeedbackSeverity,
} from "@/types/micro-feedback";

/** Default when thresholds not provided (legacy callers). */
const ANGLE_TARGET_DEG = 45;
const ANGLE_WARNING_THRESHOLD_DEG = 5;
const ANGLE_CRITICAL_THRESHOLD_DEG = 15;
const THERMAL_VARIANCE_THRESHOLD_CELSIUS = 20;
/** Max micro-feedback items per type (angle, thermal) to avoid UI overwhelm. */
const CAP_PER_TYPE = 50;

const CARDINAL_DIRECTIONS = ["north", "south", "east", "west"] as const;

/** Returns true only if all 4 cardinal directions have a numeric reading. */
function hasAllCardinalReadings(frame: Frame): boolean {
  const readings = frame.thermal_snapshots?.[0]?.readings ?? [];
  return CARDINAL_DIRECTIONS.every((dir) =>
    readings.some(
      (r) =>
        r.direction === dir &&
        typeof r.temp_celsius === "number" &&
        !Number.isNaN(r.temp_celsius)
    )
  );
}

function generateAngleDriftFeedback(
  frames: Frame[],
  target: number,
  warning: number,
  critical: number
): MicroFeedbackItem[] {
  const items: MicroFeedbackItem[] = [];
  for (let i = 0; i < frames.length && items.length < CAP_PER_TYPE; i++) {
    const frame = frames[i];
    if (!frame) continue;
    const a = frame.angle_degrees;
    if (a == null || typeof a !== "number" || Number.isNaN(a)) continue;
    const dev = Math.abs(a - target);
    if (dev <= warning) continue;
    const severity: MicroFeedbackSeverity =
      dev >= critical ? "critical" : "warning";
    items.push({
      frameIndex: i,
      severity,
      message: `Torch angle drifted ${dev.toFixed(1)}° at frame ${i} — keep within ±${warning}°`,
      suggestion: "Maintain consistent work angle for uniform penetration.",
      type: "angle",
    });
  }
  return items;
}

function generateThermalSymmetryFeedback(
  frames: Frame[],
  thresh: number
): MicroFeedbackItem[] {
  const items: MicroFeedbackItem[] = [];
  for (let i = 0; i < frames.length && items.length < CAP_PER_TYPE; i++) {
    const frame = frames[i];
    if (!frame || !frame.has_thermal_data) continue;
    if (!hasAllCardinalReadings(frame)) continue;
    const five = extractFivePointFromFrame(frame);
    if (!five) continue;
    const { north, south, east, west } = five;
    if (
      north == null ||
      south == null ||
      east == null ||
      west == null ||
      Number.isNaN(north) ||
      Number.isNaN(south) ||
      Number.isNaN(east) ||
      Number.isNaN(west)
    )
      continue;
    const maxDelta = Math.max(
      Math.abs(north - south),
      Math.abs(east - west)
    );
    if (maxDelta <= thresh) continue;
    items.push({
      frameIndex: i,
      severity: "warning",
      message: `Thermal asymmetry detected at frame ${i} (Δ${maxDelta.toFixed(0)}°C) — aim for uniform heating`,
      suggestion: "Check torch position and travel direction.",
      type: "thermal",
    });
  }
  return items;
}

/**
 * Generate micro-feedback from session frames.
 *
 * Runs angle drift and thermal symmetry generators. Returns combined,
 * sorted-by-frameIndex items. Caps at CAP_PER_TYPE per type.
 *
 * When thresholds provided, uses configured values (angle target/warning/critical,
 * thermal). Otherwise falls back to defaults for legacy callers.
 *
 * Defensive: per-generator try-catch; partial results on sub-generator failure.
 *
 * @param frames - Session frames (from Session.frames).
 * @param thresholds - Optional WeldTypeThresholds from score's active_threshold_spec.
 * @returns MicroFeedbackItem[] sorted by frameIndex.
 */
export function generateMicroFeedback(
  frames: Frame[],
  thresholds?: WeldTypeThresholds | null
): MicroFeedbackItem[] {
  const angleTarget =
    thresholds?.angle_target_degrees ?? ANGLE_TARGET_DEG;
  const angleWarning =
    thresholds?.angle_warning_margin ?? ANGLE_WARNING_THRESHOLD_DEG;
  const angleCritical =
    thresholds?.angle_critical_margin ?? ANGLE_CRITICAL_THRESHOLD_DEG;
  const thermalThresh =
    thresholds?.thermal_symmetry_warning_celsius ??
    THERMAL_VARIANCE_THRESHOLD_CELSIUS;

  if (!Array.isArray(frames) || frames.length === 0) return [];

  let angle: MicroFeedbackItem[] = [];
  let thermal: MicroFeedbackItem[] = [];

  try {
    angle = generateAngleDriftFeedback(
      frames,
      angleTarget,
      angleWarning,
      angleCritical
    );
  } catch (err) {
    logWarn("micro-feedback", "Angle feedback generation failed", {
      error: err,
    });
  }

  try {
    thermal = generateThermalSymmetryFeedback(frames, thermalThresh);
  } catch (err) {
    logWarn("micro-feedback", "Thermal feedback generation failed", {
      error: err,
    });
  }

  try {
    return [...angle, ...thermal].sort((a, b) => a.frameIndex - b.frameIndex);
  } catch (err) {
    logWarn("micro-feedback", "Micro-feedback sort/merge failed", {
      error: err,
    });
    return [...angle, ...thermal];
  }
}
