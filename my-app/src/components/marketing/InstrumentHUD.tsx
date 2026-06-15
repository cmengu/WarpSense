'use client';

/**
 * InstrumentHUD — a fixed section readout on the right edge (`02 / 10 · PROBLEM`)
 * driven by an IntersectionObserver, reframing the scroll as reading an
 * instrument. The scroll-progress indicator itself lives on the left edge
 * (HeatSpine), so this side carries only the section label.
 *
 * Lives inside the ~48px page gutter (content uses px-12), so it never overlaps
 * content. Desktop-only; pointer-events-none; decorative.
 */

import { useEffect, useState } from 'react';
import { HUD_SECTIONS } from '@/lib/warpsense-content';

const MONO = 'font-[family-name:var(--font-plex-mono)]';
const TOTAL = HUD_SECTIONS.length;
const pad = (n: number) => String(n).padStart(2, '0');

export function InstrumentHUD() {
  const [activeId, setActiveId] = useState<string>(HUD_SECTIONS[0].id);

  useEffect(() => {
    const els = HUD_SECTIONS.map((s) => document.getElementById(s.id)).filter(
      (el): el is HTMLElement => el !== null
    );
    if (els.length === 0) return;
    const obs = new IntersectionObserver(
      (entries) => {
        for (const e of entries) {
          if (e.isIntersecting) setActiveId(e.target.id);
        }
      },
      // Collapse the root to the viewport's vertical centre line, so exactly
      // one (contiguous) section crosses it at a time — no ambiguous band.
      { rootMargin: '-50% 0px -50% 0px', threshold: 0 }
    );
    els.forEach((el) => obs.observe(el));
    return () => obs.disconnect();
  }, []);

  const idx = Math.max(
    0,
    HUD_SECTIONS.findIndex((s) => s.id === activeId)
  );
  const label = HUD_SECTIONS[idx].label;

  return (
    <div
      aria-hidden
      className={`${MONO} pointer-events-none fixed right-4 top-1/2 z-40 hidden -translate-y-1/2 text-[11px] uppercase tracking-[0.16em] text-[var(--ws-fg-3)] lg:block`}
      style={{ writingMode: 'vertical-rl' }}
    >
      <span className="text-[var(--ws-amber)]">{pad(idx + 1)}</span>
      <span> / {pad(TOTAL)} · {label}</span>
    </div>
  );
}
