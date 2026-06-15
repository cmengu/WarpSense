'use client';

/**
 * Marketing nav — sticky, gunmetal, mono links. Mobile menu with escape +
 * click-outside close and focus return. Single accent CTA.
 */

import { useEffect, useRef, useState } from 'react';
import { NAV_LINKS, BRAND } from '@/lib/warpsense-content';

const MONO = 'font-[family-name:var(--font-plex-mono)]';

export function Nav() {
  const [open, setOpen] = useState(false);
  const navRef = useRef<HTMLElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const firstLinkRef = useRef<HTMLAnchorElement>(null);
  const prevOpen = useRef(false);

  useEffect(() => {
    const onEsc = (e: KeyboardEvent) => e.key === 'Escape' && setOpen(false);
    window.addEventListener('keydown', onEsc);
    return () => window.removeEventListener('keydown', onEsc);
  }, []);

  useEffect(() => {
    if (!open) return;
    const onClick = (e: MouseEvent) => {
      if (navRef.current && !navRef.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('click', onClick);
    return () => document.removeEventListener('click', onClick);
  }, [open]);

  useEffect(() => {
    if (open) firstLinkRef.current?.focus();
    else if (prevOpen.current) triggerRef.current?.focus();
    prevOpen.current = open;
  }, [open]);

  return (
    <nav
      ref={navRef}
      aria-label="Main navigation"
      className="sticky top-0 z-50 border-b border-[var(--ws-line)] bg-[var(--ws-ink)]/85 backdrop-blur-xl"
    >
      <div className="mx-auto flex h-16 max-w-[1320px] items-center justify-between px-6 md:px-12">
        <a
          href="#top"
          className="text-xl font-extrabold tracking-[-0.02em] text-[var(--ws-fg)]"
        >
          Warp<span className="text-[var(--ws-amber)]">Sense</span>
        </a>

        <div className="hidden items-center gap-9 md:flex">
          {NAV_LINKS.map((l) => (
            <a
              key={l.href}
              href={l.href}
              className={`${MONO} text-[12.5px] uppercase tracking-[0.08em] text-[var(--ws-fg-2)] transition-colors hover:text-[var(--ws-fg)]`}
            >
              {l.label}
            </a>
          ))}
          <a
            href="#contact"
            className={`${MONO} border border-[var(--ws-amber)] px-5 py-2.5 text-[12.5px] uppercase tracking-[0.08em] text-[var(--ws-amber)] transition-colors hover:bg-[var(--ws-amber)] hover:text-[var(--ws-ink)]`}
          >
            Contact
          </a>
        </div>

        <button
          ref={triggerRef}
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            setOpen((v) => !v);
          }}
          aria-expanded={open}
          aria-controls="mobile-nav"
          aria-label={open ? 'Close menu' : 'Open menu'}
          className="rounded p-2 text-[var(--ws-fg)] transition-colors hover:bg-white/10 md:hidden"
        >
          <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.8}
              d={open ? 'M6 18L18 6M6 6l12 12' : 'M4 7h16M4 12h16M4 17h16'}
            />
          </svg>
        </button>
      </div>

      <div
        id="mobile-nav"
        role="dialog"
        aria-modal="true"
        aria-label="Mobile navigation"
        className={`overflow-hidden border-t border-[var(--ws-line)] bg-[var(--ws-ink)]/97 backdrop-blur-xl transition-[max-height,opacity] duration-200 md:hidden ${
          open ? 'max-h-[460px] opacity-100' : 'max-h-0 opacity-0'
        }`}
      >
        {open && (
          <div className="flex flex-col gap-1 px-6 py-4">
            {NAV_LINKS.map((l, i) => (
              <a
                key={l.href}
                ref={i === 0 ? firstLinkRef : undefined}
                href={l.href}
                onClick={() => setOpen(false)}
                className={`${MONO} py-2 text-sm uppercase tracking-[0.08em] text-[var(--ws-fg-2)] hover:text-[var(--ws-fg)]`}
              >
                {l.label}
              </a>
            ))}
            <a
              href="#contact"
              onClick={() => setOpen(false)}
              className={`${MONO} mt-2 border border-[var(--ws-amber)] px-5 py-3 text-center text-[12.5px] uppercase tracking-[0.08em] text-[var(--ws-amber)]`}
            >
              Contact {BRAND.name}
            </a>
          </div>
        )}
      </div>
    </nav>
  );
}
