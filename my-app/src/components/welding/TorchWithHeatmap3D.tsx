'use client';

/**
 * TorchWithHeatmap3D — Unified torch + thermally-colored metal workpiece.
 *
 * Single R3F Canvas: torch assembly (from TorchSceneContent) above thermal metal (from
 * ThermalPlate). Replaces separate TorchViz3D + HeatmapPlate3D on replay/demo.
 * Reduces Canvas count from 3 to 2.
 *
 * When frames has thermal data: thermally-colored workpiece (5–10°C visible steps).
 * When frames empty/undefined: flat metallic workpiece (same as TorchViz3D).
 *
 * @see .cursor/plans/unified-torch-heatmap-replay-plan.md Step 2.1
 */

import { useRef, useMemo, useState, useEffect } from 'react';
import { Orbitron, JetBrains_Mono } from 'next/font/google';
import { Canvas } from '@react-three/fiber';
import {
  OrbitControls,
  Environment,
  ContactShadows,
  PerspectiveCamera,
} from '@react-three/drei';
import * as THREE from 'three';
import {
  WORKPIECE_BASE_Y,
  ANGLE_RING_Y,
  GRID_Y,
  CONTACT_SHADOWS_Y,
} from '@/constants/welding3d';
import { getFrameAtTimestamp } from '@/utils/frameUtils';
import { ThermalPlate } from './ThermalPlate';
import { TorchSceneContent } from './TorchSceneContent';
import { WeldTrail } from './WeldTrail';
import type { Frame } from '@/types/frame';

/** Workpiece group Y — derived from welding3d for test verification. */
const WORKPIECE_GROUP_Y = WORKPIECE_BASE_Y;
export { WORKPIECE_GROUP_Y };

const orbitron = Orbitron({
  subsets: ['latin'],
  weight: ['600', '700'],
  display: 'swap',
});
const jetbrainsMono = JetBrains_Mono({ subsets: ['latin'], display: 'swap' });

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export interface TorchWithHeatmap3DProps {
  /** Torch angle in degrees (e.g. 45 = ideal). */
  angle: number;
  /** Center temperature in °C (weld pool color). */
  temp: number;
  /** Optional label shown in HUD. */
  label?: string;
  /** Where to render the HUD: 'inside' = overlay on canvas, 'outside' = above canvas in flow. Default 'inside'. */
  labelPosition?: 'inside' | 'outside';
  /** Frames with thermal data; empty = flat metal. */
  frames?: Frame[];
  /** Current replay timestamp (ms). */
  activeTimestamp?: number | null;
  /** Max temp for color scale (°C). Default 500. */
  maxTemp?: number;
  /** Min temp for color scale (°C). Default 0. */
  minTemp?: number;
  /** Physical plate size (world units). Default 3. */
  plateSize?: number;
  /** Degrees per visible color step. Default 10. */
  colorSensitivity?: number;
  /** Test-only: simulate WebGL context loss after mount. Dispatches webglcontextlost in onCreated; unit-test simulation only — real context-loss recovery may differ. */
  simulateContextLoss?: boolean;
}

// ---------------------------------------------------------------------------
// Scene content — torch + thermal or flat workpiece
// ---------------------------------------------------------------------------

type SceneContentProps = Pick<
  TorchWithHeatmap3DProps,
  'angle' | 'temp' | 'maxTemp' | 'minTemp' | 'plateSize' | 'colorSensitivity'
> & {
  frames: Frame[];
  activeTimestamp: number;
};

function SceneContent({
  angle,
  temp,
  frames,
  activeTimestamp,
  maxTemp,
  minTemp,
  plateSize,
  colorSensitivity,
}: SceneContentProps) {
  const activeFrame = useMemo(() => {
    if (frames.length === 0) return null;
    return getFrameAtTimestamp(frames, activeTimestamp) ?? frames[0] ?? null;
  }, [frames, activeTimestamp]);

  const hasThermal = frames.length > 0;

  return (
    <>
      <TorchSceneContent angle={angle} temp={temp} />

      {/* Workpiece — thermal or flat */}
      <group position={[0, WORKPIECE_GROUP_Y, 0]}>
        {frames.length >= 2 &&
          activeTimestamp > (frames[0]?.timestamp_ms ?? 0) && (
            <WeldTrail
              frames={frames}
              activeTimestamp={activeTimestamp}
              plateSize={plateSize ?? 3}
            />
          )}
        {hasThermal ? (
          <ThermalPlate
            frame={activeFrame}
            maxTemp={maxTemp ?? 500}
            minTemp={minTemp ?? 0}
            plateSize={plateSize ?? 3}
            colorSensitivity={colorSensitivity ?? 10}
          />
        ) : (
          <mesh receiveShadow rotation={[-Math.PI / 2, 0, 0]}>
            <planeGeometry args={[plateSize ?? 3, plateSize ?? 3]} />
            <meshStandardMaterial
              color="#1a1a1a"
              metalness={0.7}
              roughness={0.4}
              envMapIntensity={0.8}
            />
          </mesh>
        )}
      </group>

      {/* Angle guide ring */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, ANGLE_RING_Y, 0]}>
        <ringGeometry args={[0.8, 0.82, 32]} />
        <meshBasicMaterial
          color="#3b82f6"
          transparent
          opacity={0.3}
          side={THREE.DoubleSide}
        />
      </mesh>

      <gridHelper args={[5, 10, 0x3b82f6, 0x4b5563]} position={[0, GRID_Y, 0]} />

      <ContactShadows
        position={[0, CONTACT_SHADOWS_Y, 0]}
        opacity={0.5}
        scale={2}
        blur={2}
        far={1}
      />

      <Environment preset="city" />
    </>
  );
}

// ---------------------------------------------------------------------------
// Public component
// ---------------------------------------------------------------------------

const DEFAULT_LABEL = 'Torch & Weld Pool';

export default function TorchWithHeatmap3D({
  angle,
  temp,
  label = DEFAULT_LABEL,
  labelPosition = 'inside',
  frames = [],
  activeTimestamp,
  maxTemp = 500,
  minTemp = 0,
  plateSize = 3,
  colorSensitivity = 10,
  simulateContextLoss = false,
}: TorchWithHeatmap3DProps) {
  const [contextLost, setContextLost] = useState(false);
  const [canvasKey, setCanvasKey] = useState(0);
  const mountedRef = useRef(true);
  const cleanupRef = useRef<(() => void) | null>(null);

  const ts = activeTimestamp ?? frames?.[0]?.timestamp_ms ?? 0;

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      cleanupRef.current?.();
      cleanupRef.current = null;
    };
  }, []);

  const hudContent = label ? (
    <div className="backdrop-blur-md bg-black/50 border border-blue-400/40 rounded-lg px-4 py-3 shadow-[0_0_20px_rgba(59,130,246,0.2)]">
      <div className="flex items-center gap-2 mb-1">
        <div className="h-2 w-2 rounded-full bg-blue-500 animate-pulse" aria-hidden />
        <p
          className={`text-sm font-bold tracking-widest uppercase text-blue-400 ${orbitron.className}`}
        >
          {label}
        </p>
      </div>
      <div className="space-y-0.5">
        <div className="flex items-center gap-2">
          <span
            className={`text-[10px] uppercase tracking-wider text-blue-400/80 ${orbitron.className}`}
          >
            Torch angle
          </span>
          <span className={`text-xs text-blue-300 ${jetbrainsMono.className}`}>
            {angle.toFixed(1)}°
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span
            className={`text-[10px] uppercase tracking-wider text-blue-400/80 ${orbitron.className}`}
          >
            Weld pool temp
          </span>
          <span className={`text-xs text-blue-300 ${jetbrainsMono.className}`}>
            {temp.toFixed(0)}°C
          </span>
        </div>
      </div>
    </div>
  ) : null;

  return (
    <div className="w-full">
      {labelPosition === 'outside' && hudContent && (
        <div data-testid="hud-outside" className="mb-2">
          {hudContent}
        </div>
      )}
      <div className="relative w-full h-64 min-h-64 rounded-xl overflow-hidden border-2 border-blue-400/80 bg-neutral-950 shadow-[0_0_30px_rgba(59,130,246,0.15)]">
        {labelPosition === 'inside' && hudContent && (
          <div data-testid="hud-inside" className="absolute top-4 left-4 z-10">
            {hudContent}
          </div>
        )}
        <div className="relative h-64 w-full isolate">
        {/* When context lost: unmount Canvas to release dead WebGL context. Keyed remount
            lets user try "Reload 3D" without full page reload. See Phase 2 in
            .cursor/plans/white-screen-reload-webgl-fix-plan.md */}
        {!contextLost && (
        <Canvas
          key={canvasKey}
          shadows
          gl={{
            antialias: true,
            alpha: true,
            powerPreference: 'high-performance',
            toneMapping: THREE.ACESFilmicToneMapping,
            toneMappingExposure: 1.2,
          }}
          style={{ background: '#0a0a0a' }}
          onCreated={({ gl }) => {
            const canvas = gl.domElement;
            // Do NOT call e.preventDefault() — we don't manually recreate the renderer.
            // preventDefault tells the browser we'll restore; we never do, causing white screen
            // until hard tab reset. See .cursor/plans/white-screen-reload-webgl-fix-plan.md
            const onLost = () => {
              if (mountedRef.current) setContextLost(true);
            };
            const onRestored = () => {
              if (mountedRef.current) setContextLost(false);
            };
            canvas.addEventListener('webglcontextlost', onLost, false);
            canvas.addEventListener('webglcontextrestored', onRestored, false);
            cleanupRef.current = () => {
              canvas.removeEventListener('webglcontextlost', onLost, false);
              canvas.removeEventListener('webglcontextrestored', onRestored, false);
            };
            if (simulateContextLoss) {
              queueMicrotask(() => {
                canvas.dispatchEvent(new Event('webglcontextlost', { bubbles: false }));
              });
            }
          }}
        >
          <PerspectiveCamera makeDefault position={[1.2, 0.6, 1.5]} fov={45} />
          <OrbitControls
            enablePan={false}
            enableZoom
            minDistance={1}
            maxDistance={4}
            minPolarAngle={Math.PI / 6}
            maxPolarAngle={Math.PI / 2}
            dampingFactor={0.05}
          />
          <SceneContent
            angle={angle}
            temp={temp}
            frames={frames}
            activeTimestamp={ts}
            maxTemp={maxTemp}
            minTemp={minTemp}
            plateSize={plateSize}
            colorSensitivity={colorSensitivity}
          />
        </Canvas>
        )}
        {contextLost && (
          <div
            className="absolute inset-0 z-[100] flex items-center justify-center bg-neutral-900/95"
            role="alert"
            aria-live="assertive"
            aria-label="WebGL context lost. Reload 3D or refresh the page to restore."
          >
            <div className="rounded-lg border border-violet-500/60 bg-neutral-900 px-4 py-3 text-center shadow-lg">
              <p className={`text-sm font-semibold text-violet-400 ${orbitron.className}`}>
                WebGL context lost
              </p>
              <p className={`mt-1 text-xs text-blue-400/90 ${jetbrainsMono.className}`}>
                Try Reload 3D below; if that fails, refresh the page
              </p>
              <div className="mt-3 flex flex-col sm:flex-row gap-2 justify-center">
                <button
                  type="button"
                  onClick={() => {
                    setCanvasKey((k) => k + 1);
                    setContextLost(false);
                  }}
                  className="px-4 py-2 text-sm font-medium text-blue-400 hover:text-blue-300 underline focus:outline-none focus:ring-2 focus:ring-blue-400 focus:ring-offset-2 focus:ring-offset-neutral-900 rounded border border-blue-400/60"
                  aria-label="Reload 3D view without refreshing the page"
                >
                  Reload 3D
                </button>
                <button
                  type="button"
                  onClick={() => {
                    if (typeof window !== 'undefined') window.location.reload();
                  }}
                  className="px-4 py-2 text-sm font-medium text-violet-400/90 hover:text-violet-300/90 focus:outline-none focus:ring-2 focus:ring-violet-400 focus:ring-offset-2 focus:ring-offset-neutral-900 rounded"
                  aria-label="Refresh the page to restore 3D view"
                >
                  Refresh page
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      <div className="absolute bottom-4 right-4 z-10">
        <div className="backdrop-blur-md bg-black/50 border border-blue-400/40 rounded-lg px-3 py-2">
          <div className="flex items-center gap-2">
            <div className="w-24 h-1.5 rounded-full bg-gradient-to-r from-blue-600 via-violet-400 to-purple-400" />
            <span className={`text-[10px] text-blue-400/70 ${jetbrainsMono.className}`}>
              {minTemp}–{maxTemp}°C
            </span>
          </div>
        </div>
      </div>
      </div>
    </div>
  );
}

export { TorchWithHeatmap3D };
