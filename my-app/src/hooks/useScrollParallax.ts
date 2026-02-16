'use client';

import { useEffect, useState } from 'react';

/**
 * Returns scroll progress (0–1) and derived style for parallax effects.
 * Maps scroll position to y offset and opacity for hero section.
 */
export function useScrollParallax() {
  const [scrollProgress, setScrollProgress] = useState(0);

  useEffect(() => {
    const handleScroll = () => {
      const scrollY = typeof window !== 'undefined' ? window.scrollY : 0;
      const docHeight = typeof document !== 'undefined' ? document.documentElement.scrollHeight - window.innerHeight : 1;
      setScrollProgress(docHeight > 0 ? Math.min(scrollY / (docHeight * 0.3), 1) : 0);
    };

    handleScroll();
    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const heroY = scrollProgress * 100;
  const heroOpacity = 1 - scrollProgress;

  return {
    scrollYProgress: scrollProgress,
    heroY,
    heroOpacity,
    style: {
      transform: `translateY(${heroY}px)`,
      opacity: heroOpacity,
    },
  };
}
