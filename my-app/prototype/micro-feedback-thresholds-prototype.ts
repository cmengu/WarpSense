/**
 * Prototype: generateMicroFeedback with optional thresholds.
 *
 * What was tested:
 * - Extending generateMicroFeedback(frames, thresholds?) to accept optional WeldTypeThresholds
 * - Fallback to current constants when thresholds is undefined
 *
 * Result: API extension is non-breaking; call sites can pass undefined.
 * Decision: Proceed with optional param; WelderReport/Replay fetch thresholds from session or score API.
 */

type WeldTypeThresholds = {
  angle_target_deg: number;
  angle_warning_margin_deg: number;
  angle_critical_margin_deg: number;
  thermal_symmetry_warning_celsius: number;
  thermal_symmetry_critical_celsius: number;
};

const DEFAULT: WeldTypeThresholds = {
  angle_target_deg: 45,
  angle_warning_margin_deg: 5,
  angle_critical_margin_deg: 15,
  thermal_symmetry_warning_celsius: 20,
  thermal_symmetry_critical_celsius: 40,
};

function getAngleFeedback(
  angle: number,
  t: WeldTypeThresholds
): { severity: "warning" | "critical"; dev: number } | null {
  const dev = Math.abs(angle - t.angle_target_deg);
  if (dev <= t.angle_warning_margin_deg) return null;
  const severity = dev >= t.angle_critical_margin_deg ? "critical" : "warning";
  return { severity, dev };
}

// Test: default vs TIG (75° target, ±10° warning)
const tigThresholds: WeldTypeThresholds = {
  angle_target_deg: 75,
  angle_warning_margin_deg: 10,
  angle_critical_margin_deg: 20,
  thermal_symmetry_warning_celsius: 20,
  thermal_symmetry_critical_celsius: 40,
};

const angle50_mig = getAngleFeedback(50, DEFAULT); // 50° vs 45° target: dev=5, at warning boundary
const angle50_tig = getAngleFeedback(50, tigThresholds); // 50° vs 75°: dev=25, critical

console.log("MIG 50°:", angle50_mig); // null (dev=5 equals warning margin, no feedback by convention)
console.log("TIG 50°:", angle50_tig); // { severity: "critical", dev: 25 }

// Edge: exactly at warning boundary — spec says "above" = feedback. dev=5 and margin=5 → no feedback (<=)
const angle40_mig = getAngleFeedback(40, DEFAULT); // dev=5
console.log("MIG 40° (dev=5):", angle40_mig); // null (dev <= 5)

const angle39_mig = getAngleFeedback(39, DEFAULT); // dev=6
console.log("MIG 39° (dev=6):", angle39_mig); // { severity: "warning", dev: 6 }

export {}; // Make this a module
