'use client';

/**
 * ThermalPlate — Reusable 3D thermal workpiece mesh.
 *
 * Interpolates 5-point thermal data to a 100×100 grid, displaces vertices by
 * temperature (thermal expansion), colors by temp (stepped gradient 5–10°C visible).
 * Used by HeatmapPlate3D and TorchWithHeatmap3D.
 *
 * WebGL resources (DataTexture, ShaderMaterial) are created in useEffect and
 * disposed in cleanup — never in useMemo, per React rules and Strict Mode safety.
 *
 * @see .cursor/plans/unified-torch-heatmap-replay-plan.md Step 2.2a
 */

import { useRef, useMemo, useEffect, useState } from 'react';
import * as THREE from 'three';
import { interpolateThermalGrid } from '@/utils/thermalInterpolation';
import { extractFivePointFromFrame, DEFAULT_AMBIENT_CELSIUS } from '@/utils/frameUtils';
import { heatmapVertexShader } from './shaders/heatmapVertex.glsl';
import { heatmapFragmentShader } from './shaders/heatmapFragment.glsl';
import type { Frame } from '@/types/frame';

const GRID_SIZE = 100;

export interface ThermalPlateProps {
  /** Frame with thermal data; null = ambient fill. */
  frame: Frame | null;
  /** Max temp for color scale (°C). */
  maxTemp: number;
  /** Min temp for color scale (°C). Default 0. */
  minTemp?: number;
  /** Physical size of plate in world units (meters, same scale as torch). Default 3. */
  plateSize: number;
  /** Degrees per visible color step. Default 10. */
  colorSensitivity?: number;
}

/**
 * Thermal workpiece mesh — plane with vertex displacement and heat-sensitive color.
 * Position/rotation must be set by parent. In TorchWithHeatmap3D, use WORKPIECE_BASE_Y
 * from @/constants/welding3d so metal surface (with max displacement) stays below
 * weld pool. See .cursor/issues/metal-heatmap-y-position-clipping-torch.md.
 */
export function ThermalPlate({
  frame,
  maxTemp,
  minTemp = 0,
  plateSize,
  colorSensitivity = 10,
}: ThermalPlateProps) {
  const meshRef = useRef<THREE.Mesh>(null);
  const textureRef = useRef<THREE.DataTexture | null>(null);
  const materialRef = useRef<THREE.ShaderMaterial | null>(null);
  const [materialReady, setMaterialReady] = useState(false);

  const thermalData = useMemo(() => extractFivePointFromFrame(frame), [frame]);

  // Create WebGL resources in useEffect — never in useMemo (side effects violate React rules).
  useEffect(() => {
    const data = new Float32Array(GRID_SIZE * GRID_SIZE);
    data.fill(DEFAULT_AMBIENT_CELSIUS);

    const tex = new THREE.DataTexture(
      data,
      GRID_SIZE,
      GRID_SIZE,
      THREE.RedFormat,
      THREE.FloatType
    );
    textureRef.current = tex;

    const mat = new THREE.ShaderMaterial({
      vertexShader: heatmapVertexShader,
      fragmentShader: heatmapFragmentShader,
      uniforms: {
        uTemperatureMap: { value: tex },
        uMinTemp: { value: minTemp },
        uMaxTemp: { value: Math.max(0.001, maxTemp) },
        uStepCelsius: { value: colorSensitivity },
        // uMaxDisplacement must match MAX_THERMAL_DISPLACEMENT in welding3d.ts; do not change without updating constants and welding3d.test.
        uMaxDisplacement: { value: 0.5 },
      },
      side: THREE.DoubleSide,
    });
    materialRef.current = mat;
    setMaterialReady(true);

    return () => {
      tex.dispose();
      mat.dispose();
      textureRef.current = null;
      materialRef.current = null;
      setMaterialReady(false);
    };
  }, [maxTemp, minTemp, colorSensitivity]);

  // Update texture data and uniforms when thermal data or scale params change.
  useEffect(() => {
    const tex = textureRef.current;
    const mat = materialRef.current;
    if (!tex || !mat) return;

    const data = new Float32Array(GRID_SIZE * GRID_SIZE);
    if (thermalData) {
      const grid = interpolateThermalGrid(
        thermalData.center,
        thermalData.north,
        thermalData.south,
        thermalData.east,
        thermalData.west,
        GRID_SIZE
      );
      for (let y = 0; y < GRID_SIZE; y++) {
        for (let x = 0; x < GRID_SIZE; x++) {
          data[y * GRID_SIZE + x] = grid[y][x];
        }
      }
    } else {
      data.fill(DEFAULT_AMBIENT_CELSIUS);
    }

    // Robust update: DataTexture.image.data must match length/type of source array.
    if (tex.image?.data && tex.image.data.length === data.length) {
      tex.image.data.set(data);
      tex.needsUpdate = true;
    }

    mat.uniforms.uMinTemp.value = minTemp;
    mat.uniforms.uMaxTemp.value = Math.max(0.001, maxTemp);
    mat.uniforms.uStepCelsius.value = colorSensitivity;
  }, [thermalData, maxTemp, minTemp, colorSensitivity]);

  if (!materialReady || !materialRef.current) {
    return null;
  }

  return (
    <mesh ref={meshRef} rotation={[-Math.PI / 2, 0, 0]} material={materialRef.current}>
      <planeGeometry args={[plateSize, plateSize, GRID_SIZE, GRID_SIZE]} />
    </mesh>
  );
}
