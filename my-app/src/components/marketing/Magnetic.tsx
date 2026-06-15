'use client';

/**
 * Magnetic — wraps a CTA so it pulls slightly toward the cursor, springing back
 * on leave. Uses motion values + springs (never useState) so the pull runs
 * outside the React render cycle. The wrapped child (a Link/anchor) stays fully
 * functional — only the inline-block wrapper transforms.
 */

import { motion, useMotionValue, useSpring } from 'framer-motion';
import { useRef } from 'react';

const SPRING = { stiffness: 150, damping: 15, mass: 0.1 };
const PULL = 0.3; // fraction of cursor offset to follow

export function Magnetic({
  children,
  className = '',
}: {
  children: React.ReactNode;
  className?: string;
}) {
  const ref = useRef<HTMLSpanElement>(null);
  const x = useMotionValue(0);
  const y = useMotionValue(0);
  const sx = useSpring(x, SPRING);
  const sy = useSpring(y, SPRING);

  return (
    <motion.span
      ref={ref}
      style={{ x: sx, y: sy, display: 'inline-block' }}
      className={className}
      onMouseMove={(e) => {
        const r = ref.current?.getBoundingClientRect();
        if (!r) return;
        x.set((e.clientX - (r.left + r.width / 2)) * PULL);
        y.set((e.clientY - (r.top + r.height / 2)) * PULL);
      }}
      onMouseLeave={() => {
        x.set(0);
        y.set(0);
      }}
    >
      {children}
    </motion.span>
  );
}
