/**
 * Tests for WeldTrail computeTrailData and isArcActive.
 *
 * WeldTrail component renders inside R3F Canvas; we test the pure
 * computeTrailData logic and isArcActive boundary conditions.
 */

import { computeTrailData } from '@/components/welding/WeldTrail';
import { isArcActive } from '@/utils/frameUtils';
import type { Frame } from '@/types/frame';

function makeFrame(
  overrides: Partial<{
    timestamp_ms: number;
    volts: number | null;
    amps: number | null;
    angle_degrees: number;
    travel_speed_mm_per_min: number | null;
    has_thermal_data: boolean;
    thermal_snapshots: unknown[];
  }> = {}
): Frame {
  return {
    timestamp_ms: 0,
    volts: 22,
    amps: 150,
    angle_degrees: 45,
    travel_speed_mm_per_min: 400,
    has_thermal_data: false,
    thermal_snapshots: [],
    heat_dissipation_rate_celsius_per_sec: 0,
    ...overrides,
  } as unknown as Frame;
}

const singleArcOnFrame = makeFrame({ timestamp_ms: 0, volts: 22, amps: 150 });

describe('isArcActive', () => {
  it('returns false when volts === 1 exactly (boundary)', () => {
    expect(isArcActive(makeFrame({ volts: 1, amps: 150 }))).toBe(false);
  });
  it('returns false when amps === 1 exactly (boundary)', () => {
    expect(isArcActive(makeFrame({ volts: 22, amps: 1 }))).toBe(false);
  });
  it('returns true when volts > 1 and amps > 1', () => {
    expect(isArcActive(makeFrame({ volts: 22, amps: 150 }))).toBe(true);
  });
  it('returns false when volts is 0', () => {
    expect(isArcActive(makeFrame({ volts: 0, amps: 150 }))).toBe(false);
  });
  it('returns false when amps is 0', () => {
    expect(isArcActive(makeFrame({ volts: 22, amps: 0 }))).toBe(false);
  });
});

describe('computeTrailData', () => {
  it('arc-off frames (volts=0 or amps=0) produce zero points', () => {
    const framesOff = Array.from({ length: 20 }, (_, i) =>
      makeFrame({ timestamp_ms: i * 10, volts: 0, amps: 0 })
    );
    const { count: c0 } = computeTrailData(framesOff, 200, 3);
    expect(c0).toBe(0);

    const framesAmpOff = Array.from({ length: 20 }, (_, i) =>
      makeFrame({ timestamp_ms: i * 10, volts: 22, amps: 0 })
    );
    const { count: c1 } = computeTrailData(framesAmpOff, 200, 3);
    expect(c1).toBe(0);
  });

  it('arc-on frames (volts>1, amps>1) produce points', () => {
    const frames = Array.from({ length: 20 }, (_, i) =>
      makeFrame({ timestamp_ms: i * 10, volts: 22, amps: 150, travel_speed_mm_per_min: 400 })
    );
    const { count } = computeTrailData(frames, 200, 3);
    expect(count).toBeGreaterThan(0);
  });

  it('cumulative distance: high-speed segment has larger step than low-speed', () => {
    const frames = [
      ...Array.from({ length: 6 }, (_, i) =>
        makeFrame({
          timestamp_ms: i * 10,
          volts: 22,
          amps: 150,
          travel_speed_mm_per_min: 200,
        })
      ),
      ...Array.from({ length: 6 }, (_, i) =>
        makeFrame({
          timestamp_ms: (i + 6) * 10,
          volts: 22,
          amps: 150,
          travel_speed_mm_per_min: 600,
        })
      ),
    ];
    const { positions, count } = computeTrailData(frames, 120, 3);
    expect(count).toBeGreaterThanOrEqual(3);
    if (count >= 3) {
      const x0 = positions[0];
      const x1 = positions[3];
      const x2 = positions[6];
      const lowSpeedStep = x1 - x0;
      const highSpeedStep = x2 - x1;
      expect(highSpeedStep / lowSpeedStep).toBeGreaterThan(2.5);
      expect(highSpeedStep / lowSpeedStep).toBeLessThan(3.5);
    }
  });

  it('positions and colors have length exactly count * 3', () => {
    const frames = Array.from({ length: 20 }, (_, i) =>
      makeFrame({ timestamp_ms: i * 10, volts: 22, amps: 150, travel_speed_mm_per_min: 400 })
    );
    const { positions, colors, count } = computeTrailData(frames, 200, 3);
    expect(positions.length).toBe(count * 3);
    expect(colors.length).toBe(count * 3);
  });

  it('cold frames produce green color (R low, G high)', () => {
    const frames = Array.from({ length: 20 }, (_, i) =>
      makeFrame({
        timestamp_ms: i * 10,
        volts: 22,
        amps: 150,
        travel_speed_mm_per_min: 400,
        has_thermal_data: true,
        thermal_snapshots: [
          {
            distance_mm: 10,
            readings: [{ direction: 'center' as const, temp_celsius: 100 }],
          },
        ],
      })
    );
    const { colors, count } = computeTrailData(frames, 200, 3);
    expect(count).toBeGreaterThan(0);
    const r = colors[0];
    const g = colors[1];
    expect(g).toBeGreaterThan(r);
  });

  it('hot frames (fallback 450°C) produce red color (R high, G low)', () => {
    const frames = Array.from({ length: 20 }, (_, i) =>
      makeFrame({ timestamp_ms: i * 10, volts: 22, amps: 150 })
    );
    const { colors, count } = computeTrailData(frames, 200, 3);
    expect(count).toBeGreaterThan(0);
    const r = colors[0];
    const g = colors[1];
    expect(r).toBeGreaterThan(g);
  });

  it('all x values in [-plateSize/2, plateSize/2]', () => {
    const frames = Array.from({ length: 20 }, (_, i) =>
      makeFrame({ timestamp_ms: i * 10, volts: 22, amps: 150, travel_speed_mm_per_min: 400 })
    );
    const { positions, count } = computeTrailData(frames, 200, 3);
    const half = 3 / 2;
    for (let i = 0; i < count; i++) {
      const x = positions[i * 3];
      expect(x).toBeGreaterThanOrEqual(-half);
      expect(x).toBeLessThanOrEqual(half);
    }
  });

  it('extreme angle does not push Z outside [-0.3, 0.3]', () => {
    const frames = Array.from({ length: 20 }, (_, i) =>
      makeFrame({
        timestamp_ms: i * 10,
        volts: 22,
        amps: 150,
        angle_degrees: 89.6,
        travel_speed_mm_per_min: 400,
      })
    );
    const { positions, count } = computeTrailData(frames, 300, 3);
    // Float32 precision: 0.3 may become ~0.30000001
    const eps = 1e-5;
    for (let i = 0; i < count; i++) {
      expect(positions[i * 3 + 2]).toBeLessThanOrEqual(0.3 + eps);
      expect(positions[i * 3 + 2]).toBeGreaterThanOrEqual(-0.3 - eps);
    }
  });

  it('all null travel_speed calls onFallbackWarning once', () => {
    const frames = Array.from({ length: 20 }, (_, i) =>
      makeFrame({
        timestamp_ms: i * 10,
        volts: 22,
        amps: 150,
        travel_speed_mm_per_min: null,
      })
    );
    const warnSpy = jest.fn();
    computeTrailData(frames, 300, 3, warnSpy);
    expect(warnSpy).toHaveBeenCalledTimes(1);
  });

  it('empty frames returns count 0', () => {
    const { count } = computeTrailData([], 0, 3);
    expect(count).toBe(0);
  });

  it('single arc-on frame returns count 0 (arcActive.length < 2)', () => {
    const { count } = computeTrailData([singleArcOnFrame], 10, 3);
    expect(count).toBe(0);
  });
});
