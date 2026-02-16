'use client';

/**
 * TorchViz3D — Industrial demo page (Production-grade plan Step 3).
 *
 * CAD-style layout: full viewport 3D + floating panel (top-right).
 * Blue/purple WarpSense theme; Orbitron + JetBrains Mono.
 * Static display only (Option A) — no sliders, simulation, or new state.
 *
 * Access at /dev/torch-viz when dev server is running.
 */

import dynamic from 'next/dynamic';
import { Orbitron, JetBrains_Mono } from 'next/font/google';

const orbitron = Orbitron({ subsets: ['latin'], weight: ['600', '700'] });
const jetbrainsMono = JetBrains_Mono({ subsets: ['latin'] });

const TorchViz3D = dynamic(
  () => import('@/components/welding/TorchViz3D').then((m) => m.default),
  {
    ssr: false,
    loading: () => (
      <div className="flex h-64 w-full items-center justify-center rounded-xl border-2 border-blue-400/40 bg-neutral-900">
        <span className="text-blue-400/80 animate-pulse">Loading 3D…</span>
      </div>
    ),
  }
);

export default function DevTorchVizPage() {
  return (
    <div className="relative min-h-screen bg-neutral-950">
      {/* Main area: single 3D instance (avoids WebGL context limit ~8–16 per page) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 p-6 min-h-screen">
        <div className="lg:col-span-8 flex items-center justify-center">
          <div className="w-full max-w-2xl">
            <TorchViz3D angle={45} temp={450} label="LIVE PREVIEW" />
          </div>
        </div>

        {/* Floating panel — right column (CAD-style) */}
        <div
          className={`lg:col-span-4 lg:sticky lg:top-6 h-fit backdrop-blur-md bg-black/60 border-2 border-blue-400/80 rounded-lg px-4 py-4 shadow-[0_0_30px_rgba(59,130,246,0.2)] ${orbitron.className}`}
        >
          <div className="flex items-center gap-2 mb-3">
            <div className="h-2 w-2 rounded-full bg-blue-500 animate-pulse" aria-hidden />
            <h2 className="text-sm font-bold tracking-widest uppercase text-blue-400">
              TorchViz3D Demo
            </h2>
          </div>
          <div className={`space-y-2 text-xs text-blue-300/90 ${jetbrainsMono.className}`}>
            <div className="flex justify-between">
              <span className="text-blue-400/70">Instance</span>
              <span>1 (45° / 450°C)</span>
            </div>
            <div className="flex justify-between">
              <span className="text-blue-400/70">Theme</span>
              <span>Blue / Purple</span>
            </div>
          </div>
          <div className="mt-4 pt-3 border-t border-blue-400/30">
            <p className={`text-[10px] text-blue-500/80 ${jetbrainsMono.className}`}>
              Drag → rotate • Scroll → zoom
            </p>
          </div>
          <div className="mt-3 pt-3 border-t border-blue-400/20">
            <p className={`text-[10px] text-blue-400/60 uppercase tracking-wider ${orbitron.className}`}>
              Scenario reference
            </p>
            <ul className={`mt-1 text-[9px] text-blue-500/70 space-y-0.5 ${jetbrainsMono.className}`}>
              <li>Expert: 45° / 425°C</li>
              <li>Novice: 65° / 520°C</li>
              <li>Cold: 45° / 280°C</li>
              <li>Overheat: 50° / 620°C</li>
            </ul>
          </div>
        </div>
      </div>

      {/* Bottom-left path indicator */}
      <div
        className={`absolute bottom-4 left-4 z-20 px-3 py-2 backdrop-blur-md bg-black/50 border border-blue-400/40 rounded-lg ${jetbrainsMono.className}`}
      >
        <span className="text-[10px] text-blue-400/80">/dev/torch-viz</span>
      </div>
    </div>
  );
}
