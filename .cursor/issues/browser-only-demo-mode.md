# Browser-Only Demo Mode

**Type:** Feature  
**Priority:** High  
**Effort:** Medium  
**Labels:** `frontend` `demo` `replay` `zero-setup`  
**Status:** Open

---

## Issue Card (quick scan)

| | |
|---|---|
| **TL;DR** | Self-contained demo at `/demo` — 100% in-browser, no backend/DB/seed. One link for prospects, any device, LinkedIn-ready. |
| **Current** | Run uvicorn + Postgres → seed script → navigate to `/replay/sess_expert_001` → explain stack. Minutes, laptop-only. |
| **Expected** | Open `/demo` → side-by-side expert vs novice replays with scores. ~30s to value, zero setup, shareable link. |
| **Relevant files** | `my-app/src/lib/demo-data.ts` (new), `my-app/src/app/demo/page.tsx` (new), port from `backend/data/mock_sessions.py` |
| **Risks** | TS thermal model may diverge from Python; unit test parity. Bundle ~200KB acceptable. |
| **Vision** | Replay + scoring with zero setup → prospects see value in ~30s. One URL to 100 prospects; works on any device. |

---

## TL;DR

Self-contained demo that runs 100% in the browser. One URL (`/demo`)—no backend, no PostgreSQL, no seed script. Enables sending a link to prospects, demoing on any device, and posting on LinkedIn with no setup or explanation.

---

## Rationale

**Problem:** Right now, showing your product requires:

- Backend running (`uvicorn main:app`)
- PostgreSQL container
- Seed script (`POST /api/dev/seed-mock-sessions`)
- Navigate to `/replay/sess_expert_001`
- Explain what everything means

This kills demos. You can't send a link. You can't demo on a customer's laptop. You can't post on LinkedIn.

**Solution:** Self-contained demo that runs 100% in browser.

**Business value:**

- Send one URL to 100 prospects
- Works on any device (phone, tablet, laptop)
- No setup, no backend, no explanation needed
- Customer sees value in 30 seconds

---

## Current State vs Expected

| | Current | Expected |
|---|--------|----------|
| **Demo flow** | Run uvicorn → start Postgres → `POST /api/dev/seed-mock-sessions` → open `/replay/sess_expert_001` → explain stack | Open one URL (`/demo`); replay and score render from in-browser generated data |
| **Portability** | Laptop with backend + DB only | Any device (phone, tablet, laptop); shareable link |
| **Time to value** | Minutes (setup + navigation) | ~30 seconds (click link, see replay) |

---

## High-Level Architecture

```
Demo page → lib/demo-data.ts (in-browser) → Session object
  ↓
Same components (HeatMap, TorchViz3D, TorchAngleGraph)
  ↓
Auto-plays side-by-side expert vs novice
```

### Architecture Diagram

```
┌──────────────────────────────────────────────────────────────┐
│ Demo Page (/demo)                                             │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  [State]                                                      │
│    - expertSession (generated once)                           │
│    - noviceSession (generated once)                           │
│    - currentTimestamp (playback position)                    │
│    - extractHeatmapData(frames)                               │
│    - extractAngleData(frames)                                 │
│    - extractCenterTemperatureWithCarryForward(...)            │
│                                                               │
│  [Components] (REUSED from replay page)                       │
│    - TorchViz3D (angle, temp, label)                          │
│    - HeatMap (data, activeTimestamp)                          │
│    - TorchAngleGraph (data, activeTimestamp)                  │
│                                                               │
│  [Playback] (same setInterval pattern)                        │
│    - setInterval(() => setCurrentTimestamp(prev + 10), 10)    │
│                                                               │
└──────────────────────────────────────────────────────────────┘
         ↓ uses (browser-only, no API)
┌──────────────────────────────────────────────────────────────┐
│ lib/demo-data.ts                                              │
│   - generateExpertSession() → Session                         │
│   - generateNoviceSession() → Session                         │
│   - (mirrors Python mock_sessions.py)                         │
└──────────────────────────────────────────────────────────────┘
```

---

## Key Technical Decision

**Reuse existing components, duplicate data generation logic**

| Component | Status |
|-----------|--------|
| HeatMap | ✅ No changes |
| TorchViz3D | ✅ No changes |
| TorchAngleGraph | ✅ No changes |
| Backend | ❌ Not called |
| Mock data | 🔄 Port from Python → TypeScript |

---

## What Gets Reused vs. Built

| Item | Source | Status |
|------|--------|--------|
| TorchViz3D | Existing | No changes |
| HeatMap | Existing | No changes |
| TorchAngleGraph | Existing | No changes |
| extractHeatmapData | Existing | No changes |
| extractAngleData | Existing | No changes |
| extractCenterTemp... | Existing | No changes |
| Playback loop | Existing (replay page pattern) | Copy pattern |
| demo-data.ts | 🆕 NEW | Port from Python |
| demo page | 🆕 NEW | Layout + integration |

**Code reuse: ~80%** | **New code: ~20%**

---

## Implementation Plan

### Step 1: Port Mock Data to TypeScript (Day 1 morning)

**File:** `my-app/src/lib/demo-data.ts`

```typescript
/**
 * Browser-only mock data generation
 * Mirrors backend/data/mock_sessions.py
 *
 * PURPOSE: Demo mode only - NOT used in production
 * THROWAWAY: Delete when all customers are on real sensors
 */

import { Session, Frame, ThermalSnapshot } from '@/types/session';

function generateThermalSnapshot(
  t_ms: number,
  amps: number,
  volts: number,
  angle_degrees: number,
  distance_mm: number
): ThermalSnapshot {
  const arc_power = amps * volts;
  const base_temp = 150 + (arc_power / 50); // ~300°C at 150A × 22V

  // Angle affects north/south asymmetry
  const angle_offset = angle_degrees - 45; // deviation from ideal
  const north_delta = angle_offset * 3.0; // °C per degree
  const south_delta = -angle_offset * 3.0;

  // Distance affects temperature (decay along weld)
  const distance_factor = Math.exp(-distance_mm / 100);
  const temp_at_distance = base_temp * distance_factor;

  // Travel direction: east hotter than west
  const east_boost = 15 * distance_factor;
  const west_penalty = -10 * distance_factor;

  return {
    distance_mm,
    readings: [
      { direction: 'center', temp_celsius: temp_at_distance },
      { direction: 'north', temp_celsius: temp_at_distance + north_delta },
      { direction: 'south', temp_celsius: temp_at_distance + south_delta },
      { direction: 'east', temp_celsius: temp_at_distance + east_boost },
      { direction: 'west', temp_celsius: temp_at_distance + west_penalty }
    ]
  };
}

// Signal generators (same as Python)
function expertAmps(t_ms: number): number {
  const t_sec = t_ms / 1000;
  const warmup = t_sec < 0.5 ? Math.sin(t_sec * 10) * 10 : 0;
  return 150 + warmup + Math.sin(t_sec * 2) * 2; // ±2A noise
}

function expertVolts(t_ms: number): number {
  return 22.5; // Rock solid
}

function expertAngle(t_ms: number): number {
  const t_sec = t_ms / 1000;
  return 45 + Math.sin(t_sec * 5) * 0.5; // ±0.5° tremor
}

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

// Session generators
export function generateExpertSession(): Session {
  const frames: Frame[] = [];
  const DURATION_MS = 15000; // 15 seconds
  const DISTANCES = [10, 20, 30, 40, 50]; // mm along weld

  for (let t = 0; t < DURATION_MS; t += 10) {
    const amps = expertAmps(t);
    const volts = expertVolts(t);
    const angle = expertAngle(t);

    const thermal_snapshots = t % 100 === 0
      ? DISTANCES.map(d => generateThermalSnapshot(t, amps, volts, angle, d))
      : [];

    frames.push({
      timestamp_ms: t,
      amps,
      volts,
      angle_degrees: angle,
      thermal_snapshots,
      has_thermal_data: thermal_snapshots.length > 0,
      heat_dissipation_rate_celsius_per_sec: null,
      optional_sensors: null
    });
  }

  return {
    session_id: 'demo_expert',
    operator_id: 'expert_er',
    start_time: new Date().toISOString(),
    weld_type: 'stainless_steel_304',
    frames,
    thermal_sample_interval_ms: 100,
    thermal_directions: ['center', 'north', 'south', 'east', 'west'],
    thermal_distance_interval_mm: 10,
    sensor_sample_rate_hz: 100,
    status: 'complete',
    frame_count: frames.length,
    expected_frame_count: frames.length,
    last_successful_frame_index: frames.length - 1,
    validation_errors: [],
    completed_at: new Date().toISOString(),
    disable_sensor_continuity_checks: false
  };
}

export function generateNoviceSession(): Session {
  // Same structure, different signal generators (noviceAmps, noviceVolts, noviceAngle)
}
```

**Constraint:** This duplicates Python logic. Keep it. When sensors arrive, this file becomes irrelevant but it's only ~200 LOC.

---

### Step 2: Build Demo Page (Day 1 afternoon + Day 2)

**File:** `my-app/src/app/demo/page.tsx`

```typescript
'use client';

import { useState, useEffect } from 'react';
import dynamic from 'next/dynamic';
import { generateExpertSession, generateNoviceSession } from '@/lib/demo-data';
import { extractHeatmapData } from '@/utils/heatmapData';
import { extractAngleData } from '@/utils/angleData';
import { extractCenterTemperatureWithCarryForward } from '@/utils/frameUtils';

const TorchViz3D = dynamic(
  () => import('@/components/welding/TorchViz3D'),
  { ssr: false }
);
const HeatMap = dynamic(
  () => import('@/components/welding/HeatMap'),
  { ssr: false }
);
const TorchAngleGraph = dynamic(
  () => import('@/components/welding/TorchAngleGraph'),
  { ssr: false }
);

export default function DemoPage() {
  const [playing, setPlaying] = useState(false);
  const [currentTimestamp, setCurrentTimestamp] = useState(0);

  const [expertSession] = useState(() => generateExpertSession());
  const [noviceSession] = useState(() => generateNoviceSession());

  const expertHeatmap = extractHeatmapData(expertSession.frames);
  const noviceHeatmap = extractHeatmapData(noviceSession.frames);
  const expertAngle = extractAngleData(expertSession.frames);
  const noviceAngle = extractAngleData(noviceSession.frames);

  useEffect(() => {
    if (!playing) return;

    const interval = setInterval(() => {
      setCurrentTimestamp(prev => {
        const next = prev + 10;
        if (next >= 15000) {
          setPlaying(false);
          return 0; // Loop back
        }
        return next;
      });
    }, 10); // 100 Hz playback

    return () => clearInterval(interval);
  }, [playing]);

  const expertFrame = expertSession.frames.find(f => f.timestamp_ms === currentTimestamp);
  const noviceFrame = noviceSession.frames.find(f => f.timestamp_ms === currentTimestamp);

  const expertTemp = extractCenterTemperatureWithCarryForward(
    expertSession.frames,
    currentTimestamp
  );
  const noviceTemp = extractCenterTemperatureWithCarryForward(
    noviceSession.frames,
    currentTimestamp
  );

  return (
    <div className="min-h-screen bg-neutral-950 text-white">
      <div className="border-b-2 border-cyan-400 bg-neutral-900 p-6">
        <h1 className="text-4xl font-bold text-cyan-400 uppercase tracking-wider">
          Shipyard Welding - Live Quality Analysis
        </h1>
        <p className="text-gray-400 mt-2">
          Real-time weld quality feedback system for industrial training
        </p>
      </div>

      <div className="grid grid-cols-2 gap-8 p-8">
        {/* Expert column */}
        <div className="space-y-6">
          <div className="flex items-center gap-3">
            <div className="w-4 h-4 bg-green-400 rounded-full animate-pulse" />
            <h2 className="text-2xl font-bold text-green-400">EXPERT WELDER</h2>
            <span className="ml-auto text-3xl font-bold text-green-400">94/100</span>
          </div>

          <div className="h-64">
            <TorchViz3D
              angle={expertFrame?.angle_degrees ?? 45}
              temp={expertTemp}
              label="Expert Technique"
            />
          </div>

          <HeatMap
            sessionId="demo_expert"
            data={expertHeatmap}
            activeTimestamp={currentTimestamp}
            label="Temperature Profile"
          />

          <TorchAngleGraph
            sessionId="demo_expert"
            data={expertAngle}
            activeTimestamp={currentTimestamp}
          />

          <div className="bg-green-900/20 border border-green-400/50 rounded-lg p-4 space-y-2">
            <p className="text-green-400 flex items-center gap-2">
              <span>✓</span><span>Consistent temperature (±5°C)</span>
            </p>
            <p className="text-green-400 flex items-center gap-2">
              <span>✓</span><span>Steady torch angle (45° ±0.5°)</span>
            </p>
            <p className="text-green-400 flex items-center gap-2">
              <span>✓</span><span>Smooth heat dissipation (30°C/s)</span>
            </p>
          </div>
        </div>

        {/* Novice column */}
        <div className="space-y-6">
          <div className="flex items-center gap-3">
            <div className="w-4 h-4 bg-red-400 rounded-full animate-pulse" />
            <h2 className="text-2xl font-bold text-red-400">NOVICE WELDER</h2>
            <span className="ml-auto text-3xl font-bold text-red-400">42/100</span>
          </div>

          <div className="h-64">
            <TorchViz3D
              angle={noviceFrame?.angle_degrees ?? 45}
              temp={noviceTemp}
              label="Novice Technique"
            />
          </div>

          <HeatMap
            sessionId="demo_novice"
            data={noviceHeatmap}
            activeTimestamp={currentTimestamp}
            label="Temperature Profile"
          />

          <TorchAngleGraph
            sessionId="demo_novice"
            data={noviceAngle}
            activeTimestamp={currentTimestamp}
          />

          <div className="bg-red-900/20 border border-red-400/50 rounded-lg p-4 space-y-2">
            <p className="text-red-400 flex items-center gap-2">
              <span>✗</span><span>Temperature spike at 2.3s (+65°C)</span>
            </p>
            <p className="text-red-400 flex items-center gap-2">
              <span>✗</span><span>Torch angle drift (45° → 62°)</span>
            </p>
            <p className="text-red-400 flex items-center gap-2">
              <span>✗</span><span>Erratic heat dissipation (10-120°C/s)</span>
            </p>
          </div>
        </div>
      </div>

      {/* Playback controls */}
      <div className="fixed bottom-8 left-1/2 -translate-x-1/2 bg-cyan-950/90 backdrop-blur border-2 border-cyan-400 rounded-lg p-4 flex items-center gap-4">
        <button
          onClick={() => setPlaying(!playing)}
          className="px-8 py-3 bg-cyan-400 text-black font-bold rounded hover:bg-cyan-300 transition"
        >
          {playing ? '⏸ PAUSE' : '▶ PLAY'} DEMO
        </button>

        <div className="flex flex-col">
          <span className="text-cyan-400 text-sm">Time</span>
          <span className="text-white font-mono">{(currentTimestamp / 1000).toFixed(1)}s / 15.0s</span>
        </div>

        <input
          type="range"
          min="0"
          max="15000"
          step="10"
          value={currentTimestamp}
          onChange={(e) => {
            setCurrentTimestamp(Number(e.target.value));
            setPlaying(false);
          }}
          className="w-64"
        />
      </div>

      <div className="fixed bottom-2 right-4 text-cyan-400/60 text-sm font-mono">
        DEMO MODE - No backend required
      </div>
    </div>
  );
}
```

---

## Success Criteria (End of Day 2)

```bash
# 1. Demo page loads without backend
npm run dev
open http://localhost:3000/demo
# Should see side-by-side expert vs novice

# 2. Auto-play works
# Click "PLAY DEMO"
# Should see playback advance

# 3. Zero API calls
# Open DevTools → Network tab
# Should see ZERO API calls (all data in-browser)

# 4. Works on mobile
# Open on phone
# Should be responsive, playback works
```

---

## Risks & Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| TypeScript port has bugs | Demo shows wrong data | Unit test physics model; compare Python vs TS output |
| Bundle size (dup data) | Slow page load | Acceptable for demo (~200KB extra); can optimize later |
| Components don't work without API | Can't reuse | Test components with static data first (Day 1 morning) |

---

## Relevant Files (Summary)

| Area | File |
|------|------|
| Demo data (NEW) | `my-app/src/lib/demo-data.ts` |
| Demo page (NEW) | `my-app/src/app/demo/page.tsx` |
| Source to mirror | `backend/data/mock_sessions.py` |
| Reuse as-is | HeatMap, TorchViz3D, TorchAngleGraph, extractHeatmapData, extractAngleData, frameUtils |

---

## How This Furthers Our Vision

- **Product vision (recording, replaying, scoring):** Demo showcases replay and scoring with zero setup, so prospects see the value proposition immediately.
- **Business:** One URL to 100 prospects; works on any device; no setup or backend explanation; customer sees value in ~30 seconds. Enables LinkedIn/social demos and ad-hoc customer demos on their machines.

---

*Days 3–10 plan (if applicable) to be added when ready.*
