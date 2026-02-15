/**
 * Browser-only demo data generation for welding sessions.
 *
 * PURPOSE: Demo mode only — NOT used in production. Enables a self-contained
 * demo at /demo with zero backend/DB/seed. Data is 100% synthesized in-browser.
 *
 * Mirrors the thermal model from the issue spec (simplified TypeScript model).
 * Python parity with backend/data/mock_sessions.py is deferred to a follow-up.
 *
 * Contract: Produces Session objects with Frame[] matching the contract
 * expected by extractHeatmapData, extractAngleData, and
 * extractCenterTemperatureWithCarryForward.
 */

import type { Session } from "@/types/session";
import type { Frame } from "@/types/frame";
import type { ThermalSnapshot } from "@/types/thermal";

// ---------------------------------------------------------------------------
// Constants (per plan: 15s duration, 10ms frames, thermal every 100ms)
// ---------------------------------------------------------------------------

const DURATION_MS = 15000;
const FRAME_INTERVAL_MS = 10;
const THERMAL_INTERVAL_MS = 100;
const DISTANCES_MM = [10, 20, 30, 40, 50];

// ---------------------------------------------------------------------------
// Thermal model (simplified TS model per plan Critical Decision 1)
// ---------------------------------------------------------------------------

/**
 * Generate a thermal snapshot at a given time and distance.
 *
 * Physics (simplified):
 *   - base_temp = 150 + (arc_power / 50)
 *   - distance_factor = exp(-distance_mm / 100)
 *   - temp_at_distance = base_temp * distance_factor
 *   - Angle drives north/south asymmetry (45° = ideal)
 *   - East (travel direction) hotter than west
 *
 * @param t_ms - Time since session start in ms.
 * @param amps - Current in amps.
 * @param volts - Voltage in volts.
 * @param angle_degrees - Torch work angle in degrees.
 * @param distance_mm - Distance along weld seam in mm.
 * @returns ThermalSnapshot with 5 readings (center, north, south, east, west).
 */
function generateThermalSnapshot(
  _t_ms: number,
  amps: number,
  volts: number,
  angle_degrees: number,
  distance_mm: number
): ThermalSnapshot {
  const arc_power = amps * volts;
  const base_temp = 150 + arc_power / 50;
  const distance_factor = Math.exp(-distance_mm / 100);
  const temp_at_distance = base_temp * distance_factor;

  const angle_offset = angle_degrees - 45;
  const north_delta = angle_offset * 3.0;
  const south_delta = -angle_offset * 3.0;
  const east_boost = 15 * distance_factor;
  const west_penalty = -10 * distance_factor;

  return {
    distance_mm,
    readings: [
      { direction: "center", temp_celsius: temp_at_distance },
      { direction: "north", temp_celsius: temp_at_distance + north_delta },
      { direction: "south", temp_celsius: temp_at_distance + south_delta },
      { direction: "east", temp_celsius: temp_at_distance + east_boost },
      { direction: "west", temp_celsius: temp_at_distance + west_penalty },
    ],
  };
}

// ---------------------------------------------------------------------------
// Signal generators — Expert: stable, minimal variation
// ---------------------------------------------------------------------------

function expertAmps(t_ms: number): number {
  const t_sec = t_ms / 1000;
  const warmup = t_sec < 0.5 ? Math.sin(t_sec * 10) * 10 : 0;
  return 150 + warmup + Math.sin(t_sec * 2) * 2; // ±2A noise
}

function expertVolts(_t_ms: number): number {
  return 22.5; // Rock solid
}

function expertAngle(t_ms: number): number {
  const t_sec = t_ms / 1000;
  return 45 + Math.sin(t_sec * 5) * 0.5; // ±0.5° tremor
}

// ---------------------------------------------------------------------------
// Signal generators — Novice: spiky amps, drifting volts/angle
// ---------------------------------------------------------------------------

function noviceAmps(t_ms: number): number {
  const t_sec = t_ms / 1000;
  const spike = Math.sin(t_sec * Math.PI) > 0.95 ? 30 : 0;
  return 150 + spike + Math.sin(t_sec * 3) * 10; // ±10A base noise
}

function noviceVolts(t_ms: number): number {
  const t_sec = t_ms / 1000;
  return 22 - (t_sec / 15) * 4; // Drift: 22V → 18V over 15 sec
}

function noviceAngle(t_ms: number): number {
  const t_sec = t_ms / 1000;
  return 45 + (t_sec / 15) * 20; // Drift: 45° → 65° over 15 sec
}

// ---------------------------------------------------------------------------
// Session builders
// ---------------------------------------------------------------------------

/**
 * Build frames for a session using the given signal generators.
 */
function buildFrames(
  ampsFn: (t: number) => number,
  voltsFn: (t: number) => number,
  angleFn: (t: number) => number
): Frame[] {
  const frames: Frame[] = [];

  for (let t = 0; t < DURATION_MS; t += FRAME_INTERVAL_MS) {
    const amps = ampsFn(t);
    const volts = voltsFn(t);
    const angle = angleFn(t);

    const thermal_snapshots =
      t % THERMAL_INTERVAL_MS === 0
        ? DISTANCES_MM.map((d) =>
            generateThermalSnapshot(t, amps, volts, angle, d)
          )
        : [];

    frames.push({
      timestamp_ms: t,
      amps,
      volts,
      angle_degrees: angle,
      thermal_snapshots,
      has_thermal_data: thermal_snapshots.length > 0,
      heat_dissipation_rate_celsius_per_sec: null,
      optional_sensors: null,
    });
  }

  return frames;
}

/**
 * Generate expert welding session.
 *
 * Expert: stable amps (~150A ±2A), rock-solid volts (22.5V),
 * steady angle (45° ±0.5°). Produces smooth thermal profile suitable
 * for heatmap visualization.
 *
 * @returns Session with 1500 frames (0–15000ms, 10ms interval).
 */
export function generateExpertSession(): Session {
  const frames = buildFrames(expertAmps, expertVolts, expertAngle);

  return {
    session_id: "demo_expert",
    operator_id: "expert_er",
    start_time: new Date().toISOString(),
    weld_type: "stainless_steel_304",
    frames,
    thermal_sample_interval_ms: THERMAL_INTERVAL_MS,
    thermal_directions: ["center", "north", "south", "east", "west"],
    thermal_distance_interval_mm: 10,
    sensor_sample_rate_hz: 100,
    status: "complete",
    frame_count: frames.length,
    expected_frame_count: frames.length,
    last_successful_frame_index: frames.length - 1,
    validation_errors: [],
    completed_at: new Date().toISOString(),
    disable_sensor_continuity_checks: false,
  };
}

/**
 * Generate novice welding session.
 *
 * Novice: spiky amps (±10A noise + occasional spikes), drifting volts
 * (22V → 18V over 15s), drifting angle (45° → 65°). Produces erratic
 * thermal profile visible in heatmap vs expert.
 *
 * @returns Session with 1500 frames (0–15000ms, 10ms interval).
 */
export function generateNoviceSession(): Session {
  const frames = buildFrames(noviceAmps, noviceVolts, noviceAngle);

  return {
    session_id: "demo_novice",
    operator_id: "novice_nr",
    start_time: new Date().toISOString(),
    weld_type: "stainless_steel_304",
    frames,
    thermal_sample_interval_ms: THERMAL_INTERVAL_MS,
    thermal_directions: ["center", "north", "south", "east", "west"],
    thermal_distance_interval_mm: 10,
    sensor_sample_rate_hz: 100,
    status: "complete",
    frame_count: frames.length,
    expected_frame_count: frames.length,
    last_successful_frame_index: frames.length - 1,
    validation_errors: [],
    completed_at: new Date().toISOString(),
    disable_sensor_continuity_checks: true,
  };
}
