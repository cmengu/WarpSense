'use client';

/**
 * TorchViz3D — Industrial-grade 3D torch + weld pool visualization.
 *
 * Renders a multi-part welding torch (handle, grip, nozzle, weld pool, glow halo)
 * with PBR materials, OrbitControls, HDRI reflections. Torch angle driven by
 * `angle` (degrees); weld pool color by `temp` (°C). Industrial HUD with
 * Orbitron + JetBrains Mono typography, blue/purple WarpSense theme.
 *
 * @see .cursor/plans/torchviz3d-production-grade-plan.md — Step 2
 */

import { useRef, useMemo, useState, useEffect } from 'react';
import { Orbitron, JetBrains_Mono } from 'next/font/google';
import { Canvas, useFrame } from '@react-three/fiber';
import {
  OrbitControls,
  Environment,
  ContactShadows,
  PerspectiveCamera,
} from '@react-three/drei';
import * as THREE from 'three';
import { getArcColor, getTempReadoutColor } from '@/utils/torchColors';

const orbitron = Orbitron({ subsets: ['latin'], weight: ['600', '700'] });
const jetbrainsMono = JetBrains_Mono({ subsets: ['latin'] });

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export interface TorchViz3DProps {
  /** Torch angle in degrees (e.g. 45 = ideal). Drives rotation around X. */
  angle: number;
  /** Center temperature in °C. Drives weld pool sphere color (green → orange → red). */
  temp: number;
  /** Optional label shown in HUD (e.g. "Current Session", "Comparison"). */
  label?: string;
}

// ---------------------------------------------------------------------------
// Scene content — runs inside Canvas
// ---------------------------------------------------------------------------

interface SceneContentProps {
  angle: number;
  temp: number;
}

function SceneContent({ angle, temp }: SceneContentProps) {
  const torchGroupRef = useRef<THREE.Group>(null);
  const arcColor = useMemo(() => getArcColor(temp), [temp]);
  const glowIntensity = useMemo(() => 0.5 + (temp / 700) * 2.5, [temp]);

  useFrame(() => {
    if (torchGroupRef.current) {
      torchGroupRef.current.rotation.x = ((angle - 45) * Math.PI) / 180;
    }
  });

  return (
    <>
      <ambientLight intensity={0.3} />
      <directionalLight
        position={[10, 10, 5]}
        intensity={1.5}
        castShadow
        shadow-mapSize-width={1024}
        shadow-mapSize-height={1024}
        shadow-camera-far={50}
        shadow-camera-left={-10}
        shadow-camera-right={10}
        shadow-camera-top={10}
        shadow-camera-bottom={-10}
      />
      <directionalLight position={[-5, 3, -5]} intensity={0.8} color="#6366f1" />
      <pointLight position={[0, 5, 0]} intensity={0.5} color="#ffffff" />
      <pointLight
        position={[0, -0.4, 0]}
        intensity={glowIntensity}
        color={arcColor}
        distance={2}
        decay={2}
      />

      {/* Torch assembly */}
      <group ref={torchGroupRef} position={[0, 0.4, 0]}>
        {/* Handle — PBR metal */}
        <mesh castShadow receiveShadow position={[0, 0, 0]}>
          <cylinderGeometry args={[0.05, 0.045, 0.9, 32]} />
          <meshStandardMaterial
            color="#2a2a2a"
            metalness={0.9}
            roughness={0.2}
            envMapIntensity={1.5}
          />
        </mesh>
        {/* Grip */}
        <mesh castShadow receiveShadow position={[0, 0.1, 0]}>
          <cylinderGeometry args={[0.052, 0.052, 0.3, 32]} />
          <meshStandardMaterial
            color="#1a1a1a"
            metalness={0.3}
            roughness={0.8}
          />
        </mesh>
        {/* Nozzle cone */}
        <mesh castShadow receiveShadow position={[0, -0.5, 0]}>
          <coneGeometry args={[0.08, 0.15, 32]} />
          <meshStandardMaterial
            color="#3a3a3a"
            metalness={0.95}
            roughness={0.15}
            envMapIntensity={2}
          />
        </mesh>
        {/* Weld pool sphere */}
        <mesh castShadow position={[0, -0.6, 0]}>
          <sphereGeometry args={[0.12, 32, 32]} />
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
        <mesh position={[0, -0.6, 0]}>
          <sphereGeometry args={[0.18, 32, 32]} />
          <meshBasicMaterial
            color={arcColor}
            transparent
            opacity={0.15}
            side={THREE.BackSide}
          />
        </mesh>
      </group>

      {/* Workpiece */}
      <mesh
        receiveShadow
        rotation={[-Math.PI / 2, 0, 0]}
        position={[0, -0.6, 0]}
      >
        <planeGeometry args={[3, 3]} />
        <meshStandardMaterial
          color="#1a1a1a"
          metalness={0.7}
          roughness={0.4}
          envMapIntensity={0.8}
        />
      </mesh>

      {/* Angle guide ring */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.59, 0]}>
        <ringGeometry args={[0.8, 0.82, 32]} />
        <meshBasicMaterial color="#3b82f6" transparent opacity={0.3} side={THREE.DoubleSide} />
      </mesh>

      {/* Grid helper — industrial coordinate system */}
      <gridHelper args={[5, 10, 0x3b82f6, 0x4b5563]} position={[0, -0.6, 0]} />

      <ContactShadows
        position={[0, -0.59, 0]}
        opacity={0.5}
        scale={2}
        blur={2}
        far={1}
      />

      <Environment preset="warehouse" />
    </>
  );
}

// ---------------------------------------------------------------------------
// Public component
// ---------------------------------------------------------------------------

const DEFAULT_LABEL = 'Torch & Weld Pool';

export default function TorchViz3D({ angle, temp, label = DEFAULT_LABEL }: TorchViz3DProps) {
  const [contextLost, setContextLost] = useState(false);
  const [canvasKey, setCanvasKey] = useState(0);
  const mountedRef = useRef(true);
  const cleanupRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      cleanupRef.current?.();
      cleanupRef.current = null;
    };
  }, []);

  return (
    <div className="relative w-full h-64 min-h-64 rounded-xl overflow-hidden border-2 border-blue-400/80 bg-neutral-950 shadow-[0_0_30px_rgba(59,130,246,0.15)]">
      {/* HUD overlay — industrial style */}
      {label && (
        <div className="absolute top-4 left-4 z-10">
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
                <span className={`text-[10px] uppercase tracking-wider text-blue-400/80 ${orbitron.className}`}>
                  Torch angle
                </span>
                <span className={`text-xs text-blue-300 ${jetbrainsMono.className}`}>
                  {angle.toFixed(1)}°
                </span>
              </div>
              <div className="flex items-center gap-2">
                <span className={`text-[10px] uppercase tracking-wider text-blue-400/80 ${orbitron.className}`}>
                  Weld pool temp
                </span>
                <span className={`text-xs ${getTempReadoutColor(temp)} ${jetbrainsMono.className}`}>
                  {temp.toFixed(0)}°C
                </span>
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="relative h-64 w-full isolate">
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
          <SceneContent angle={angle} temp={temp} />
        </Canvas>
        )}
        {/* WebGL context lost overlay — unmount Canvas to release dead context.
            "Reload 3D" tries remount without full refresh. See Phase 2 in
            .cursor/plans/white-screen-reload-webgl-fix-plan.md */}
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

      {/* Temp scale indicator */}
      <div className="absolute bottom-4 right-4 z-10">
        <div className="backdrop-blur-md bg-black/50 border border-blue-400/40 rounded-lg px-3 py-2">
          <div className="flex items-center gap-2">
            <div className="w-24 h-1.5 rounded-full bg-gradient-to-r from-blue-600 via-blue-400 to-violet-400" />
            <span className={`text-[10px] text-blue-400/70 ${jetbrainsMono.className}`}>
              0–700°C
            </span>
          </div>
        </div>
      </div>

      {/* Technical footer */}
      <div
        className={`absolute bottom-4 left-4 z-10 text-[9px] text-blue-500/50 ${jetbrainsMono.className}`}
      >
        SENSOR_ID: TH_001 | SAMPLE_RATE: 10Hz
      </div>
    </div>
  );
}
