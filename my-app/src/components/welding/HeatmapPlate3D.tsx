'use client';

/**
 * HeatmapPlate3D — 3D warped metal plate thermal visualization.
 *
 * Interpolates 5-point thermal data to a 100×100 grid, displaces vertices by
 * temperature (simulated thermal expansion), colors by temp (5–10°C visible steps).
 * Renders torch cone above plate. Replaces HeatMap on replay when thermal data exists.
 *
 * Uses ThermalPlate for the thermal workpiece. Kept for dev/standalone; replay/demo
 * use TorchWithHeatmap3D instead.
 *
 * @see .cursor/plans/unified-torch-heatmap-replay-plan.md
 */

import { useRef, useMemo, useEffect, useState } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';
import { getFrameAtTimestamp } from '@/utils/frameUtils';
import { ThermalPlate } from './ThermalPlate';
import type { Frame } from '@/types/frame';

// ---------------------------------------------------------------------------
// TorchIndicator subcomponent
// ---------------------------------------------------------------------------

interface TorchIndicatorProps {
  frame: Frame | null;
}

function TorchIndicator({ frame }: TorchIndicatorProps) {
  if (!frame?.angle_degrees) return null;

  const angle = ((frame.angle_degrees - 45) * Math.PI) / 180;

  return (
    <group position={[0, 2, 0]}>
      <mesh rotation={[angle, 0, 0]}>
        <coneGeometry args={[0.2, 1, 8]} />
        <meshStandardMaterial
          color="#3b82f6"
          emissive="#3b82f6"
          emissiveIntensity={0.5}
        />
      </mesh>
    </group>
  );
}

// ---------------------------------------------------------------------------
// Public component
// ---------------------------------------------------------------------------

export interface HeatmapPlate3DProps {
  frames: Frame[];
  activeTimestamp?: number | null;
  maxTemp?: number;
  minTemp?: number;
  /** Standalone plate size (larger for dev). Replay/demo use TorchWithHeatmap3D with plateSize=3. */
  plateSize?: number;
  colorSensitivity?: number;
}

export default function HeatmapPlate3D({
  frames,
  activeTimestamp,
  maxTemp = 500,
  minTemp = 0,
  plateSize = 10,
  colorSensitivity = 10,
}: HeatmapPlate3DProps) {
  const [contextLost, setContextLost] = useState(false);
  const [canvasKey, setCanvasKey] = useState(0);
  const mountedRef = useRef(true);
  const cleanupRef = useRef<(() => void) | null>(null);

  const activeFrame = useMemo(() => {
    if (frames.length === 0) return null;
    if (activeTimestamp == null) return frames[0] ?? null;
    return getFrameAtTimestamp(frames, activeTimestamp) ?? frames[0] ?? null;
  }, [frames, activeTimestamp]);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      cleanupRef.current?.();
      cleanupRef.current = null;
    };
  }, []);

  return (
    <div
      className="relative w-full h-[400px] min-h-[400px] rounded-xl overflow-hidden border-2 border-blue-400/80 bg-neutral-950"
      role="img"
      aria-label="3D heatmap plate with thermal warping"
    >
      <div className="relative h-full w-full isolate">
        {!contextLost && (
        <Canvas
          key={canvasKey}
          camera={{ position: [8, 8, 8], fov: 50 }}
          gl={{
            antialias: true,
            alpha: true,
            powerPreference: 'high-performance',
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
          }}
        >
          <color attach="background" args={['#0a0a0a']} />
          <ambientLight intensity={0.3} />
          <directionalLight position={[5, 10, 5]} intensity={0.8} />
          <pointLight position={[0, 5, 0]} intensity={0.5} color="#3b82f6" />
          <ThermalPlate
            frame={activeFrame}
            maxTemp={maxTemp}
            minTemp={minTemp}
            plateSize={plateSize}
            colorSensitivity={colorSensitivity}
          />
          <TorchIndicator frame={activeFrame} />
          <gridHelper args={[20, 20, 0x333333, 0x1a1a1a]} />
          <OrbitControls
            enablePan={false}
            minDistance={5}
            maxDistance={20}
            maxPolarAngle={Math.PI / 2 - 0.1}
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
              <p className="text-sm font-semibold text-violet-400">
                WebGL context lost
              </p>
              <p className="mt-1 text-xs text-blue-400/90">
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
    </div>
  );
}
