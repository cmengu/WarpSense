/**
 * Demo tour step definitions — config-driven narrative overlay.
 *
 * 2–4 steps. Pulls NOVICE_SPIKE_MS from demo-config.
 */

import { NOVICE_SPIKE_MS } from "@/lib/demo-config";

export interface TourStep {
  id: string;
  title: string;
  body: string;
  highlightSelector?: string;
  timestamp_ms?: number;
  nextLabel: string;
  isLast?: boolean;
}

export const DEMO_TOUR_STEPS: TourStep[] = [
  {
    id: "intro",
    title: "Expert vs Novice",
    body: "See the difference between an expert welder's smooth technique and a novice's learning curve. Both recordings use the same equipment — only skill level varies.",
    nextLabel: "Next",
  },
  {
    id: "expert",
    title: "Expert Technique",
    body: "Notice the expert's consistent temperature, steady angle, and smooth heat dissipation. This is the benchmark we help welders work toward.",
    nextLabel: "Next",
  },
  {
    id: "novice_spike",
    title: "Novice Moment",
    body: "Around 2.4 seconds, the novice's current spikes — a common arc instability. Our AI catches these moments and guides improvement.",
    timestamp_ms: NOVICE_SPIKE_MS,
    nextLabel: "Next",
  },
  {
    id: "score",
    title: "What the Scores Mean",
    body: "Scores come from 5 quality rules: amps stability, angle consistency, thermal symmetry, heat dissipation, and volts stability. See how your team compares.",
    nextLabel: "See Team Management",
    isLast: true,
  },
];
