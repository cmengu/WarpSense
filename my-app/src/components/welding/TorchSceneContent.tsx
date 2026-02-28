'use client';

/**
 * TorchSceneContent — Shared torch geometry + lights for TorchViz3D and TorchWithHeatmap3D.
 *
 * Renders the MIG gun (gooseneck, handle, grip, nozzle, contact tip, arc) and lighting.
 * Does NOT render workpiece, grid, Environment — those stay in each parent's SceneContent.
 * RectAreaLightUniformsLib.init() lives here so it runs when TorchWithHeatmap3D loads
 * on replay page (without loading TorchViz3D).
 *
 * @see docs/ISSUE_TORCH_VIZ3D_VISUAL_LEGITIMACY.md
 */

import { useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import { RectAreaLightUniformsLib } from 'three/addons/lights/RectAreaLightUniformsLib.js';
import { getArcColor } from '@/utils/torchColors';
import {
  TORCH_GROUP_Y,
  WELD_POOL_OFFSET_Y,
  WELD_POOL_CENTER_Y,
} from '@/constants/welding3d';

if (typeof window !== 'undefined') {
  RectAreaLightUniformsLib.init();
}

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export interface TorchSceneContentProps {
  angle: number;
  temp: number;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function TorchSceneContent({ angle, temp }: TorchSceneContentProps) {
  const torchGroupRef = useRef<THREE.Group>(null);
  const arcColor = useMemo(() => getArcColor(temp), [temp]);
  const glowIntensity = useMemo(() => Math.min(4, 0.5 + (temp / 700) * 2.5), [temp]);

  useFrame(() => {
    if (torchGroupRef.current) {
      torchGroupRef.current.rotation.x = ((angle - 45) * Math.PI) / 180;
    }
  });

  return (
    <>
      <ambientLight intensity={0.3} />
      <rectAreaLight
        position={[0, 3, -1]}
        width={4}
        height={0.4}
        intensity={1}
        color="#ffffff"
      />
      <directionalLight
        position={[4, 8, 3]}
        intensity={2.2}
        castShadow
        shadow-mapSize-width={1024}
        shadow-mapSize-height={1024}
        shadow-camera-far={50}
        shadow-camera-left={-10}
        shadow-camera-right={10}
        shadow-camera-top={10}
        shadow-camera-bottom={-10}
      />
      <directionalLight position={[-4, 2, -4]} intensity={0.15} color="#ffffff" />
      <pointLight position={[0, 5, 0]} intensity={0.5} color="#ffffff" />
      <pointLight
        position={[0, -0.4, 0]}
        intensity={glowIntensity}
        color={arcColor}
        distance={2}
        decay={2}
      />
      <pointLight
        position={[0, WELD_POOL_CENTER_Y - 0.05, 0.1]}
        intensity={0.3}
        color={arcColor}
        distance={2}
        decay={2}
      />

      {/* Torch assembly — gooseneck: 3 nested groups for MIG bend. WeldTrail stays in TorchWithHeatmap3D. */}
      <group ref={torchGroupRef} position={[0, TORCH_GROUP_Y, 0]}>
        <group rotation={[-0.45, 0, 0]}>
          <group rotation={[-0.35, 0, 0]}>
            <group rotation={[-0.15, 0, 0]}>
              {/* Handle barrel — gunmetal */}
              <mesh castShadow receiveShadow position={[0, 0, 0]}>
                <cylinderGeometry args={[0.05, 0.045, 0.9, 32]} />
                <meshStandardMaterial
                  color="#2a2a2a"
                  metalness={0.9}
                  roughness={0.18}
                  envMapIntensity={1.5}
                />
              </mesh>
              {/* Grip bands (4) — rubber */}
              {[0.06, 0.16, 0.25, 0.34].map((y) => (
                <mesh key={y} castShadow receiveShadow position={[0, y, 0]}>
                  <cylinderGeometry args={[0.052, 0.052, 0.04, 32]} />
                  <meshStandardMaterial
                    color="#1a1a1a"
                    metalness={0}
                    roughness={0.98}
                  />
                </mesh>
              ))}
              {/* Trigger housing — rubber */}
              <mesh castShadow receiveShadow position={[0.055, 0.08, 0]}>
                <boxGeometry args={[0.08, 0.06, 0.04]} />
                <meshStandardMaterial color="#1a1a1a" metalness={0} roughness={0.98} />
              </mesh>
              <mesh castShadow receiveShadow position={[0.06, 0.04, 0]}>
                <boxGeometry args={[0.02, 0.04, 0.03]} />
                <meshStandardMaterial color="#1a1a1a" metalness={0} roughness={0.98} />
              </mesh>
              {/* Cable collar — entry + rubber shroud at handle top */}
              <mesh castShadow receiveShadow position={[0, 0.38, 0]}>
                <cylinderGeometry args={[0.04, 0.045, 0.06, 32]} />
                <meshStandardMaterial color="#2a2a2a" metalness={0.9} roughness={0.18} />
              </mesh>
              <mesh castShadow receiveShadow position={[0, 0.42, 0]}>
                <cylinderGeometry args={[0.048, 0.048, 0.04, 32]} />
                <meshStandardMaterial color="#1a1a1a" metalness={0} roughness={0.98} />
              </mesh>
              {/* Nozzle — brass, two-part */}
              <mesh castShadow receiveShadow position={[0, -0.5, 0]}>
                <coneGeometry args={[0.08, 0.12, 32]} />
                <meshStandardMaterial
                  color="#b8860b"
                  metalness={0.95}
                  roughness={0.35}
                  envMapIntensity={2}
                />
              </mesh>
              <mesh castShadow receiveShadow position={[0, -0.56, 0]}>
                <cylinderGeometry args={[0.04, 0.04, 0.04, 32]} />
                <meshStandardMaterial
                  color="#b8860b"
                  metalness={0.95}
                  roughness={0.35}
                  envMapIntensity={2}
                />
              </mesh>
              {/* Contact tip — copper */}
              <mesh castShadow receiveShadow position={[0, -0.58, 0]}>
                <cylinderGeometry args={[0.0065, 0.0065, 0.035, 16]} />
                <meshStandardMaterial color="#b87333" metalness={0.9} roughness={0.18} />
              </mesh>
              {/* Arc point — pinpoint */}
              <mesh castShadow position={[0, WELD_POOL_OFFSET_Y, 0]}>
                <sphereGeometry args={[0.018, 16, 16]} />
                <meshStandardMaterial
                  color={arcColor}
                  emissive={arcColor}
                  emissiveIntensity={glowIntensity}
                  metalness={0.8}
                  roughness={0.1}
                  envMapIntensity={3}
                />
              </mesh>
              {/* Glow halo */}
              <mesh position={[0, WELD_POOL_OFFSET_Y, 0]}>
                <sphereGeometry args={[0.055, 16, 16]} />
                <meshBasicMaterial
                  color={arcColor}
                  transparent
                  opacity={0.08}
                  side={THREE.BackSide}
                />
              </mesh>
            </group>
          </group>
        </group>
      </group>
    </>
  );
}
