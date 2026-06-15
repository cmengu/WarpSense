'use client';

/**
 * CountUp — animates the leading integer of a value from 0 → target when the
 * element scrolls into view, preserving any suffix (e.g. "41 yrs"). One-shot,
 * once per mount. Values without a leading digit render as-is.
 */

import { animate, useInView } from 'framer-motion';
import { useEffect, useRef, useState } from 'react';

export function CountUp({
  value,
  className,
}: {
  value: string;
  className?: string;
}) {
  const match = value.match(/^(\d+)(.*)$/);
  const target = match ? parseInt(match[1], 10) : 0;
  const suffix = match ? match[2] : '';

  const ref = useRef<HTMLSpanElement>(null);
  const inView = useInView(ref, { once: true, margin: '-60px' });
  // Initialise to the true value so SSR/no-JS renders the real number (never a
  // misleading "0 shipyards"); the count-up runs only once, in view, with JS.
  const [n, setN] = useState(target);

  useEffect(() => {
    if (!inView || !match) return;
    const controls = animate(0, target, {
      duration: 1.1,
      ease: [0.16, 1, 0.3, 1],
      onUpdate: (v) => setN(Math.round(v)),
    });
    return () => controls.stop();
  }, [inView, target, match]);

  return (
    <span ref={ref} className={className}>
      {match ? `${n}${suffix}` : value}
    </span>
  );
}
