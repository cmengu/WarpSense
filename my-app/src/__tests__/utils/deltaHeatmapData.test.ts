/**
 * Step 13 verification: delta heatmap data extraction and color scale.
 *
 * Verification result (when PASS):
 *   - deltaTempToColor: blue at -50, white at 0, purple at +50
 *   - extractDeltaHeatmapData: returns HeatmapData shape; points have temp_celsius = delta_temp_celsius
 *   - empty deltas return zero point_count
 */

import {
  deltaTempToColor,
  extractDeltaHeatmapData,
} from '@/utils/deltaHeatmapData';
import type { FrameDelta } from '@/types/comparison';

describe('deltaTempToColor', () => {
  it('maps -50 to blue, 0 to white, +50 to purple', () => {
    const blueHex = deltaTempToColor(-50);
    const whiteHex = deltaTempToColor(0);
    const purpleHex = deltaTempToColor(50);

    expect(blueHex).toMatch(/^#[0-9a-f]{6}$/i);
    expect(whiteHex).toMatch(/^#[0-9a-f]{6}$/i);
    expect(purpleHex).toMatch(/^#[0-9a-f]{6}$/i);

    const parse = (hex: string) => ({
      r: parseInt(hex.slice(1, 3), 16),
      g: parseInt(hex.slice(3, 5), 16),
      b: parseInt(hex.slice(5, 7), 16),
    });
    const b = parse(blueHex);
    const w = parse(whiteHex);
    const p = parse(purpleHex);

    expect(b.b).toBeGreaterThan(b.r);
    expect(w.r).toBe(255);
    expect(w.g).toBe(255);
    expect(w.b).toBe(255);
    expect(p.r).toBeCloseTo(168, -1);
    expect(p.g).toBeCloseTo(85, -1);
    expect(p.b).toBeCloseTo(247, -1);
  });

  it('clamps values outside -50 to +50', () => {
    expect(deltaTempToColor(-100)).toBe(deltaTempToColor(-50));
    expect(deltaTempToColor(100)).toBe(deltaTempToColor(50));
  });

  it('returns white for NaN input', () => {
    expect(deltaTempToColor(NaN)).toBe('#ffffff');
  });
});

describe('extractDeltaHeatmapData', () => {
  it('Step 13: returns HeatmapData shape with points, timestamps_ms, distances_mm, point_count', () => {
    const deltas: FrameDelta[] = [
      {
        timestamp_ms: 0,
        amps_delta: null,
        volts_delta: null,
        angle_degrees_delta: null,
        heat_dissipation_rate_celsius_per_sec_delta: null,
        thermal_deltas: [
          {
            distance_mm: 10,
            readings: [
              { direction: 'center', delta_temp_celsius: 5.0 },
            ],
          },
        ],
      },
      {
        timestamp_ms: 10,
        amps_delta: null,
        volts_delta: null,
        angle_degrees_delta: null,
        heat_dissipation_rate_celsius_per_sec_delta: null,
        thermal_deltas: [
          {
            distance_mm: 10,
            readings: [
              { direction: 'center', delta_temp_celsius: -3.0 },
            ],
          },
        ],
      },
    ];

    const result = extractDeltaHeatmapData(deltas, 'center');

    expect(result).toHaveProperty('points');
    expect(result).toHaveProperty('timestamps_ms');
    expect(result).toHaveProperty('distances_mm');
    expect(result).toHaveProperty('point_count');
    expect(result.point_count).toBe(2);
    expect(result.points).toHaveLength(2);
    expect(result.timestamps_ms).toEqual([0, 10]);
    expect(result.distances_mm).toEqual([10]);
    expect(result.points[0].temp_celsius).toBe(5.0);
    expect(result.points[1].temp_celsius).toBe(-3.0);
  });

  it('returns zeros/empty when deltas empty', () => {
    const result = extractDeltaHeatmapData([], 'center');
    expect(result.point_count).toBe(0);
    expect(result.points).toHaveLength(0);
    expect(result.timestamps_ms).toEqual([]);
    expect(result.distances_mm).toEqual([]);
  });

  it('filters by direction (center only by default)', () => {
    const deltas: FrameDelta[] = [
      {
        timestamp_ms: 0,
        amps_delta: null,
        volts_delta: null,
        angle_degrees_delta: null,
        heat_dissipation_rate_celsius_per_sec_delta: null,
        thermal_deltas: [
          {
            distance_mm: 10,
            readings: [
              { direction: 'center', delta_temp_celsius: 1.0 },
              { direction: 'north', delta_temp_celsius: 2.0 },
            ],
          },
        ],
      },
    ];
    const result = extractDeltaHeatmapData(deltas, 'center');
    expect(result.point_count).toBe(1);
    expect(result.points[0].temp_celsius).toBe(1.0);
  });
});
