'use client';

/**
 * WeldTrail — Colored point cloud on workpiece showing torch path up to activeTimestamp.
 *
 * Renders only arc-active frames (volts > 1 && amps > 1). Uses cumulative distance
 * for X-axis; falls back to timestamp-linear when all frames have null travel_speed.
 * Pre-allocates 10000 points; second useEffect updates via .array.set().
 *
 * @see docs/ISSUE_WELD_TRAIL.md
 */

import { useRef, useCallback, useMemo, useEffect, useState } from 'react';
import * as THREE from 'three';
import { extractCenterTemperature, isArcActive } from '@/utils/frameUtils';
import { AL_TRAVEL_SPEED_BASE_MEAN } from '@/constants/aluminum';
import { FRAME_INTERVAL_MS } from '@/constants/validation';
import type { Frame } from '@/types/frame';

const FRAME_DURATION_MIN = FRAME_INTERVAL_MS / 60000;
const MAX_POINTS = 10000;

// ---------------------------------------------------------------------------
// Color mapping (green <200, orange <400, red >=400)
// ---------------------------------------------------------------------------

function tempToTrailColor(temp: number): [number, number, number] {
  const green = [0x22 / 255, 0xc5 / 255, 0x5e / 255] as const;
  const orange = [0xf9 / 255, 0x73 / 255, 0x16 / 255] as const;
  const red = [0xef / 255, 0x44 / 255, 0x44 / 255] as const;
  if (temp < 200) return [...green];
  if (temp < 400) return [...orange];
  return [...red];
}

// ---------------------------------------------------------------------------
// computeTrailData (exported for tests)
// ---------------------------------------------------------------------------

export function computeTrailData(
  frames: Frame[],
  activeTimestamp: number,
  plateSize: number,
  onFallbackWarning?: () => void
): { positions: Float32Array; colors: Float32Array; count: number } {
  const arcActive = frames.filter(
    (f) => isArcActive(f) && f.timestamp_ms <= activeTimestamp
  );

  if (arcActive.length < 2) {
    return {
      positions: new Float32Array(0),
      colors: new Float32Array(0),
      count: 0,
    };
  }

  const allNullSpeed = arcActive.every((f) => f.travel_speed_mm_per_min == null);
  if (allNullSpeed) {
    onFallbackWarning?.();
  }

  type WithDist = { frame: Frame; rawCumDist: number; xNorm: number };
  const withDist: WithDist[] = [];

  if (allNullSpeed) {
    const totalMs =
      arcActive[arcActive.length - 1].timestamp_ms - arcActive[0].timestamp_ms ||
      1;
    for (const f of arcActive) {
      const xNorm =
        (f.timestamp_ms - arcActive[0].timestamp_ms) / totalMs;
      withDist.push({ frame: f, rawCumDist: 0, xNorm });
    }
  } else {
    // Two-pass normalization: Pass 1 accumulate, Pass 2 xNorm
    let cumDist = 0;
    const rawDistances: number[] = [];
    for (const f of arcActive) {
      const speed = f.travel_speed_mm_per_min ?? AL_TRAVEL_SPEED_BASE_MEAN;
      cumDist += speed * FRAME_DURATION_MIN;
      rawDistances.push(cumDist);
    }
    const totalDist = cumDist || 1;
    let idx = 0;
    for (const f of arcActive) {
      const xNorm = rawDistances[idx] / totalDist;
      withDist.push({ frame: f, rawCumDist: rawDistances[idx], xNorm });
      idx++;
    }
  }

  const sampled = withDist.filter((_, i) => i % 5 === 0);

  const half = plateSize / 2;
  const positions: number[] = [];
  const colors: number[] = [];

  for (const { frame, xNorm } of sampled) {
    const x = Math.max(-half, Math.min(half, xNorm * plateSize - half));
    const zDrift = Math.max(
      -0.3,
      Math.min(0.3, (frame.angle_degrees ?? 45) * 0.005)
    );
    positions.push(x, 0, zDrift);

    const temp = extractCenterTemperature(frame) ?? 450;
    const [r, g, b] = tempToTrailColor(temp);
    colors.push(r, g, b);
  }

  const count = positions.length / 3;
  const posArr = new Float32Array(positions);
  const colArr = new Float32Array(colors);

  return { positions: posArr, colors: colArr, count };
}

// ---------------------------------------------------------------------------
// WeldTrail component
// ---------------------------------------------------------------------------

export interface WeldTrailProps {
  frames: Frame[];
  activeTimestamp: number;
  plateSize: number;
}

export function WeldTrail({
  frames,
  activeTimestamp,
  plateSize,
}: WeldTrailProps) {
  const geometryRef = useRef<THREE.BufferGeometry | null>(null);
  const materialRef = useRef<THREE.PointsMaterial | null>(null);
  const pointsRef = useRef<THREE.Points>(null);
  const [ready, setReady] = useState(false);

  const warnRef = useRef(false);
  const cb = useCallback(() => {
    if (!warnRef.current) {
      console.warn(
        '[WeldTrail] All frames have null travel_speed_mm_per_min; using timestamp-linear fallback'
      );
      warnRef.current = true;
    }
  }, []);

  useEffect(() => {
    warnRef.current = false;
  }, [frames]);

  // CPU-side Float32Array allocation per activeTimestamp is intentional and acceptable at demo scale (~200 points).
  const { positions, colors, count } = useMemo(
    () => computeTrailData(frames, activeTimestamp, plateSize, cb),
    [frames, activeTimestamp, plateSize, cb]
  );

  // First useEffect: create BufferGeometry and PointsMaterial; dispose on cleanup
  useEffect(() => {
    const geo = new THREE.BufferGeometry();
    geo.setAttribute(
      'position',
      new THREE.Float32BufferAttribute(new Float32Array(MAX_POINTS * 3), 3)
    );
    geo.setAttribute(
      'color',
      new THREE.Float32BufferAttribute(new Float32Array(MAX_POINTS * 3), 3)
    );

    const mat = new THREE.PointsMaterial({
      size: 0.03,
      vertexColors: true,
      sizeAttenuation: true,
    });

    geometryRef.current = geo;
    materialRef.current = mat;
    setReady(true);

    return () => {
      geo.dispose();
      mat.dispose();
      geometryRef.current = null;
      materialRef.current = null;
      setReady(false);
    };
  }, []);

  // Second useEffect: update attributes when positions/colors/count change
  useEffect(() => {
    const geo = geometryRef.current;
    const mat = materialRef.current;
    if (!geo || !mat) return;

    if (count === 0) {
      geo.setDrawRange(0, 0);
      return;
    }

    const posAttr = geo.attributes.position;
    const colAttr = geo.attributes.color;
    if (
      positions.length > (posAttr.array as Float32Array).length ||
      colors.length > (colAttr.array as Float32Array).length
    ) {
      console.error('[WeldTrail] positions overflow pre-allocated buffer');
      return;
    }

    (posAttr.array as Float32Array).set(positions);
    posAttr.needsUpdate = true;
    (colAttr.array as Float32Array).set(colors);
    colAttr.needsUpdate = true;
    geo.setDrawRange(0, count);
  }, [positions, colors, count]);

  const geo = geometryRef.current;
  const mat = materialRef.current;
  if (!ready || count === 0 || !geo || !mat) return null;

  return (
    <points ref={pointsRef} geometry={geo} material={mat} />
  );
}
