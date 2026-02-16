'use client';

import { useEffect, useState, useRef } from 'react';

/**
 * Hook that returns true when an element enters the viewport.
 * Uses Intersection Observer for scroll-triggered animations.
 * @param options - { once: true } means it only triggers once (stays true after first view)
 */
export function useInView(options?: { once?: boolean }) {
  const [inView, setInView] = useState(false);
  const ref = useRef<HTMLElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setInView(true);
        } else if (!options?.once) {
          setInView(false);
        }
      },
      { threshold: 0.1, rootMargin: '0px 0px -50px 0px' }
    );

    observer.observe(el);
    return () => observer.disconnect();
  }, [options?.once]);

  return { ref, inView };
}
