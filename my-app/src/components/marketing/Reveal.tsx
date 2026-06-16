'use client';

/**
 * Reveal — subtle scroll-triggered fade-up used across the marketing page.
 * Restrained on purpose (deep-tech, not consumer). Respects reduced-motion
 * via framer-motion's built-in handling of the `transition` + viewport once.
 */

import { motion, type HTMLMotionProps } from 'framer-motion';

type RevealProps = HTMLMotionProps<'div'> & {
  /** Stagger delay in seconds. */
  delay?: number;
  as?: 'div' | 'section' | 'li' | 'span';
  /**
   * Animate on mount instead of on scroll-into-view. Use for above-the-fold
   * content (hero) so visibility never depends on the IntersectionObserver.
   */
  immediate?: boolean;
};

const EASE = [0.16, 1, 0.3, 1] as const;

export function Reveal({
  delay = 0,
  as = 'div',
  immediate = false,
  children,
  ...rest
}: RevealProps) {
  // All supported tags are HTML elements accepting the same motion props;
  // cast to a single concrete type to avoid the polymorphic-union mismatch.
  const MotionTag = motion[as] as typeof motion.div;
  const reveal = immediate
    ? { animate: { opacity: 1, y: 0 } }
    : {
        whileInView: { opacity: 1, y: 0 },
        viewport: { once: true, margin: '-80px' },
      };
  return (
    <MotionTag
      initial={{ opacity: 0, y: 18 }}
      {...reveal}
      transition={{ duration: 0.6, ease: EASE, delay }}
      {...rest}
    >
      {children}
    </MotionTag>
  );
}
