'use client';

/**
 * HeatSpine — the page's connective signature. A thin vertical heat-trace runs
 * down the left gutter and draws itself (pathLength) in lockstep with scroll,
 * echoing the product sensing a weld in real time. Mostly-straight with subtle
 * thermal jitter and two sharper "arc strike" spikes.
 *
 * Sits inside the ~48px page gutter; desktop-only; decorative (aria-hidden).
 */

import { motion, useScroll, useSpring, useReducedMotion } from 'framer-motion';

// Vertical trace in a 32×1000 box (stretched to viewport height). Baseline at
// x=16 with small deviations and two amber-strike spikes.
const TRACE =
  'M16,0 L16,150 L9,182 L21,208 L12,236 L16,280 L16,300 L3,330 L29,344 L7,372 L16,408 L16,620 L11,648 L20,672 L13,700 L16,740 L16,1000';

export function HeatSpine() {
  const reduce = useReducedMotion();
  const { scrollYProgress } = useScroll();
  const smooth = useSpring(scrollYProgress, {
    stiffness: 60,
    damping: 22,
    mass: 0.4,
  });
  const pathLength = reduce ? scrollYProgress : smooth;

  return (
    <div
      aria-hidden
      className="pointer-events-none fixed inset-y-0 left-2 z-40 hidden w-8 lg:block"
    >
      <svg
        viewBox="0 0 32 1000"
        preserveAspectRatio="none"
        className="h-full w-full"
      >
        {/* instrument baseline */}
        <line
          x1="16"
          y1="0"
          x2="16"
          y2="1000"
          stroke="var(--ws-line)"
          strokeWidth="1"
          vectorEffect="non-scaling-stroke"
        />
        {/* self-drawing heat trace */}
        <motion.path
          d={TRACE}
          fill="none"
          stroke="var(--ws-amber)"
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
          vectorEffect="non-scaling-stroke"
          opacity={0.85}
          initial={{ pathLength: 0 }}
          style={{ pathLength }}
        />
      </svg>
    </div>
  );
}
