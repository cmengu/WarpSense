'use client';

/**
 * HeatSignature — a thin thermal-trace line that draws itself on scroll-into-view.
 * Mostly-flat baseline with one sharp "arc strike" spike, echoing the product's
 * real-time heat sensing. The single restrained kinetic signature of the page.
 *
 * Procedural (SVG/CSS) — no raster image. The soft amber field at the spike is
 * the page's one nod to "arc light", kept low-opacity to avoid neon-glow slop.
 */

import { motion } from 'framer-motion';

export function HeatSignature({ className = '' }: { className?: string }) {
  // Flat baseline → sharp "arc strike" spike near x≈490 → settle. viewBox 1200×140.
  const d =
    'M0,96 L250,96 L292,92 L330,98 L372,93 L430,94 L470,28 L500,120 L534,58 L576,84 L640,96 L900,96 L944,90 L986,98 L1200,95';

  return (
    <div className={`relative w-full ${className}`} aria-hidden>
      {/* faint heat bloom at the spike — single-hue, kept very low to avoid glow-slop */}
      <div
        className="pointer-events-none absolute left-[40%] top-1/2 h-28 w-28 -translate-y-1/2 rounded-full"
        style={{
          background:
            'radial-gradient(circle, rgba(232,93,38,0.12) 0%, rgba(232,93,38,0) 72%)',
        }}
      />
      <svg
        viewBox="0 0 1200 140"
        preserveAspectRatio="none"
        className="block h-[120px] w-full"
      >
        {/* instrument baseline */}
        <line x1="0" y1="96" x2="1200" y2="96" stroke="var(--ws-line)" strokeWidth="1" />
        {/* self-drawing heat trace */}
        <motion.path
          d={d}
          fill="none"
          stroke="var(--ws-amber)"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          vectorEffect="non-scaling-stroke"
          initial={{ pathLength: 0, opacity: 0.4 }}
          whileInView={{ pathLength: 1, opacity: 1 }}
          viewport={{ once: true, margin: '-60px' }}
          transition={{ duration: 1.8, ease: [0.16, 1, 0.3, 1] }}
        />
      </svg>
    </div>
  );
}
