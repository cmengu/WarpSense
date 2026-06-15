/**
 * Static marketing primitives for the "Instrument" (V1) system.
 * Server-safe: pure markup, no client hooks. Shared tokens live in globals.css
 * as --ws-* variables and are consumed via arbitrary Tailwind values.
 */

import { Reveal } from './Reveal';

const ACCENT = 'text-[var(--ws-amber)]';
const MONO = 'font-[family-name:var(--font-plex-mono)]';

/** Short amber rule used as a section break mark. */
export function Rule({ className = '' }: { className?: string }) {
  return (
    <span
      aria-hidden
      className={`inline-block h-0.5 w-9 bg-[var(--ws-amber)] ${className}`}
    />
  );
}

/** Mono uppercase eyebrow in the accent color. */
export function Kicker({ children }: { children: React.ReactNode }) {
  return (
    <span
      className={`${MONO} ${ACCENT} text-[12px] font-medium uppercase tracking-[0.18em]`}
    >
      {children}
    </span>
  );
}

/** Mono chrome label (muted) — section index, metadata. */
export function MonoLabel({
  children,
  className = '',
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <span
      className={`${MONO} text-[12px] uppercase tracking-[0.14em] text-[var(--ws-fg-3)] ${className}`}
    >
      {children}
    </span>
  );
}

/** Standard section header: rule + kicker, then a large display heading. */
export function SectionHead({
  kicker,
  heading,
  lead,
  id,
}: {
  kicker: string;
  heading: React.ReactNode;
  lead?: React.ReactNode;
  id?: string;
}) {
  return (
    <Reveal>
      <div className="flex items-center gap-4">
        <Rule />
        <Kicker>{kicker}</Kicker>
      </div>
      <h2
        id={id}
        className="mt-4 max-w-[20ch] text-[clamp(2.1rem,4.6vw,3.75rem)] font-extrabold leading-[0.96] tracking-[-0.03em] text-[var(--ws-fg)]"
      >
        {heading}
      </h2>
      {lead ? (
        <p className="mt-5 max-w-[62ch] text-lg leading-relaxed text-[var(--ws-fg-2)]">
          {lead}
        </p>
      ) : null}
    </Reveal>
  );
}
