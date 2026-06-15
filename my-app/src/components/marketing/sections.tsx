/**
 * WarpSense marketing sections — "Instrument" (V1) system.
 * Server components (static markup) wrapped in <Reveal> for scroll motion.
 * Flat planes, hairline dividers, mono chrome, single amber accent.
 */

import Link from 'next/link';
import Image from 'next/image';
import { Reveal } from './Reveal';
import { HeatSignature } from './HeatSignature';
import { CountUp } from './CountUp';
import { Magnetic } from './Magnetic';
import { Kicker, Rule, MonoLabel, SectionHead } from './ui';
import {
  BRAND,
  EXPLORE_LINKS,
  HERO,
  PROOF,
  PROBLEMS,
  STEPS,
  MARKET,
  MOAT,
  VALIDATION,
  TEAM,
  RAISE,
  CONTACT,
  CONTACT_EMAIL,
} from '@/lib/warpsense-content';

const MONO = 'font-[family-name:var(--font-plex-mono)]';

/** Where the working quality-scoring dashboard lives in this app. */
const DASHBOARD_HREF = '/dashboard';

/** Optional external CTAs — env-driven with graceful fallbacks (build-time inlined). */
const BOOKING_URL =
  (process.env.NEXT_PUBLIC_DEMO_BOOKING_URL ?? '').trim() || `mailto:${CONTACT_EMAIL}`;
const DECK_URL = (process.env.NEXT_PUBLIC_INVESTOR_DECK_URL ?? '').trim();
const isExternal = (u: string) => u.startsWith('http');

const SECTION = 'border-t border-[var(--ws-line)] py-24 md:py-28';
const WRAP = 'mx-auto max-w-[1320px] px-6 md:px-12';

/* ----------------------------------------------------------------- Hero */

export function Hero() {
  return (
    <header
      id="top"
      className="relative overflow-hidden px-6 pb-24 pt-28 md:px-12 md:pb-28 md:pt-36"
    >
      {/* receding floor grid — perspective-tilted hairlines fading up into the canvas */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-x-0 bottom-0 h-[70%] overflow-hidden"
        style={{ perspective: '600px' }}
      >
        <div
          className="absolute inset-0 origin-bottom opacity-[0.55]"
          style={{
            transform: 'rotateX(72deg) scale(1.6)',
            backgroundImage:
              'linear-gradient(var(--ws-line-2) 1px,transparent 1px),linear-gradient(90deg,var(--ws-line-2) 1px,transparent 1px)',
            backgroundSize: '56px 56px',
            maskImage: 'linear-gradient(to top, #000 5%, transparent 70%)',
            WebkitMaskImage: 'linear-gradient(to top, #000 5%, transparent 70%)',
          }}
        />
      </div>
      <div className="relative mx-auto max-w-[1320px]">
        <Reveal immediate>
          <Kicker>{HERO.kicker}</Kicker>
        </Reveal>

        <Reveal immediate delay={0.06}>
          <h1 className="mt-6 max-w-[16ch] text-[clamp(3rem,8vw,7.5rem)] font-black leading-[0.9] tracking-[-0.035em] text-[var(--ws-fg)]">
            {HERO.headline.map((word, i) => (
              <span key={i}>
                {i === HERO.emphasisIndex ? (
                  <span className="text-[var(--ws-amber)]">{word}</span>
                ) : (
                  word
                )}{' '}
              </span>
            ))}
          </h1>
        </Reveal>

        <Reveal immediate delay={0.12}>
          <p className="mt-7 max-w-[58ch] text-lg leading-relaxed text-[var(--ws-fg-2)] md:text-xl">
            {HERO.sub}
          </p>
        </Reveal>

        <Reveal immediate delay={0.18}>
          <div className="mt-10 flex flex-wrap items-center gap-3.5">
            <Magnetic>
              <Link
                href={DASHBOARD_HREF}
                className={`${MONO} inline-block bg-[var(--ws-amber)] px-6 py-3.5 text-[13px] uppercase tracking-[0.08em] text-[var(--ws-ink)] transition-colors hover:bg-[var(--ws-amber-hi)]`}
              >
                See the live demo →
              </Link>
            </Magnetic>
            <a
              href={HERO.primaryCta.href}
              className={`${MONO} border border-[var(--ws-line-2)] px-6 py-3.5 text-[13px] uppercase tracking-[0.08em] text-[var(--ws-fg)] transition-colors hover:border-[var(--ws-fg-3)]`}
            >
              {HERO.primaryCta.label}
            </a>
          </div>
        </Reveal>

        {/* scroll cue */}
        <Reveal immediate delay={0.3} className="mt-20 hidden md:block">
          <a
            href="#problem"
            className={`${MONO} inline-flex items-center gap-3 text-[11px] uppercase tracking-[0.2em] text-[var(--ws-fg-3)] transition-colors hover:text-[var(--ws-fg-2)]`}
          >
            Scroll
            <span className="animate-bounce-scroll text-[var(--ws-amber)]" aria-hidden>
              ↓
            </span>
          </a>
        </Reveal>
      </div>
    </header>
  );
}

/* ------------------------------------------------------------ ProofStrip */

export function ProofStrip() {
  return (
    <section
      aria-label="Research footing"
      className="border-y border-[var(--ws-line)] bg-[var(--ws-panel)]/40"
    >
      <div className={`${WRAP} grid grid-cols-2 lg:grid-cols-4`}>
        {PROOF.map((p, i) => (
          <Reveal
            key={p.label}
            delay={i * 0.06}
            className={`py-8 md:py-10 ${
              i < PROOF.length - 1 ? 'lg:border-r lg:border-[var(--ws-line)]' : ''
            } ${i % 2 === 0 ? 'border-r border-[var(--ws-line)] lg:border-r' : ''} ${
              i < 2 ? 'border-b border-[var(--ws-line)] lg:border-b-0' : ''
            } pr-4 lg:pl-8 lg:first:pl-0`}
          >
            <CountUp
              value={p.value}
              className="block text-[2rem] font-black leading-none tracking-[-0.02em] text-[var(--ws-amber)] md:text-[2.5rem]"
            />
            <div className="mt-2.5 max-w-[22ch] text-[13px] leading-snug text-[var(--ws-fg-2)]">
              {p.label}
            </div>
          </Reveal>
        ))}
      </div>
    </section>
  );
}

/* -------------------------------------------------------------- Problem */

export function Problem() {
  return (
    <section id="problem" className={SECTION}>
      <div className={WRAP}>
        <SectionHead
          kicker="The Problem"
          heading="Quality control runs on eyes, after the metal has cooled"
        />
        <div className="mt-14 grid grid-cols-1 border border-[var(--ws-line)] md:grid-cols-2">
          {PROBLEMS.map((p, i) => (
            <Reveal
              key={p.index}
              delay={i * 0.08}
              className={`p-8 transition-[background,box-shadow] duration-300 hover:bg-[var(--ws-panel)]/40 hover:shadow-[inset_2px_0_0_var(--ws-amber)] md:p-10 ${
                i === 0
                  ? 'border-b border-[var(--ws-line)] md:border-b-0 md:border-r'
                  : ''
              }`}
            >
              <MonoLabel className="text-[var(--ws-amber)]">
                / {p.index} — {p.label}
              </MonoLabel>
              <h3 className="mt-5 text-2xl font-bold tracking-[-0.01em] text-[var(--ws-fg)]">
                {p.title}
              </h3>
              <p className="mt-4 text-[16px] leading-relaxed text-[var(--ws-fg-2)]">
                {p.body}
              </p>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ------------------------------------------------------------- Statement */

export function Statement() {
  return (
    <section
      aria-label="The core problem, stated plainly"
      className="relative flex min-h-[78vh] items-center overflow-hidden border-t border-[var(--ws-line)] py-24"
    >
      <div className={`${WRAP} w-full`}>
        <Reveal>
          <MonoLabel className="text-[var(--ws-amber)]">The core problem</MonoLabel>
          <p className="mt-6 max-w-[16ch] text-[clamp(2.75rem,7vw,6.5rem)] font-black leading-[0.94] tracking-[-0.035em] text-[var(--ws-fg)]">
            <span className="text-[var(--ws-amber)]">Zero data</span> is captured
            between arc strike and inspection.
          </p>
        </Reveal>

        {/* self-drawing heat trace — the page's kinetic signature */}
        <div className="mt-16">
          <HeatSignature />
          <div className="mt-3 flex justify-between">
            <MonoLabel>Arc strike</MonoLabel>
            <MonoLabel>Inspection</MonoLabel>
          </div>
        </div>
      </div>
    </section>
  );
}

/* ----------------------------------------------------------- How / System */

export function HowItWorks() {
  return (
    <section id="system" className={SECTION}>
      <div className={WRAP}>
        <SectionHead
          kicker="How It Works"
          heading="Four steps. No change to the welder's process."
        />
        <div className="mt-14 grid grid-cols-1 border-t border-[var(--ws-line)] sm:grid-cols-2 lg:grid-cols-4">
          {STEPS.map((s, i) => (
            <Reveal
              key={s.index}
              delay={i * 0.06}
              className="border-b border-[var(--ws-line)] p-7 transition-[background,box-shadow] duration-300 hover:bg-[var(--ws-panel)]/40 hover:shadow-[inset_0_2px_0_var(--ws-amber)] sm:[&:nth-child(odd)]:border-r lg:border-b-0 lg:border-r lg:last:border-r-0"
            >
              <MonoLabel className="text-[var(--ws-amber)]">/ {s.index}</MonoLabel>
              <h3 className="mt-5 text-xl font-bold tracking-[-0.01em] text-[var(--ws-fg)]">
                {s.title}
              </h3>
              <p className="mt-3 text-[15px] leading-relaxed text-[var(--ws-fg-2)]">
                {s.body}
              </p>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ----------------------------------------------------------------- Demo */

export function Demo() {
  return (
    <section id="demo" className={SECTION}>
      <div className={WRAP}>
        <SectionHead
          kicker="See It In Action"
          heading="The dashboard that turns sensor data into a verdict"
          lead="Our quality-scoring dashboard takes raw weld measurements and resolves them into a single pass-or-flag read — the same surface an inspector would use. Open it and explore a worked session."
        />
        <Reveal delay={0.1} className="mt-12">
          <div className="border border-[var(--ws-line)] bg-[var(--ws-panel)]">
            <div className="flex items-center justify-between border-b border-[var(--ws-line)] bg-[var(--ws-panel-2)] px-5 py-3">
              <MonoLabel>WarpSense · Quality Dashboard</MonoLabel>
              <span
                className={`${MONO} bg-[var(--ws-amber)] px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.1em] text-[var(--ws-ink)]`}
              >
                Demo
              </span>
            </div>

            {/* working dashboard preview */}
            <Link
              href={DASHBOARD_HREF}
              className="group relative block aspect-[16/9] overflow-hidden border-b border-[var(--ws-line)]"
              aria-label="Open the live dashboard"
            >
              <Image
                src="/dashboard-preview.png"
                alt="WarpSense quality dashboard: a roster of weld panels scored 0–100, colour-coded pass / needs-inspection, with fleet KPIs across the top."
                fill
                sizes="(max-width: 768px) 100vw, 1200px"
                className="object-cover object-top transition-transform duration-700 ease-out group-hover:scale-[1.015]"
                priority={false}
              />
              <div
                aria-hidden
                className="absolute inset-0 bg-gradient-to-t from-[var(--ws-ink)]/55 via-transparent to-transparent"
              />
            </Link>

            <div className="flex flex-col items-start gap-6 p-8 md:flex-row md:items-center md:justify-between md:p-10">
              <div className="max-w-[48ch]">
                <p className="text-xl font-semibold text-[var(--ws-fg)]">
                  A live, working interface — not a static screenshot.
                </p>
                <p className="mt-3 text-[15px] leading-relaxed text-[var(--ws-fg-2)]">
                  Built full-stack from data pipeline to inspector alerts. Walk a
                  scored weld session end to end.
                </p>
              </div>
              <Link
                href={DASHBOARD_HREF}
                className={`${MONO} shrink-0 bg-[var(--ws-amber)] px-6 py-3.5 text-[13px] uppercase tracking-[0.08em] text-[var(--ws-ink)] transition-colors hover:bg-[var(--ws-amber-hi)]`}
              >
                Open the live dashboard →
              </Link>
            </div>
          </div>
        </Reveal>
      </div>
    </section>
  );
}

/* ---------------------------------------------------------------- Market */

export function Market() {
  return (
    <section id="market" className={SECTION}>
      <div className={WRAP}>
        <SectionHead
          kicker="Market Opportunity"
          heading="A measurable wedge in a US$156B industry"
        />
        {/* descending funnel — rows narrow as the market does (TAM → SAM → SOM) */}
        <div className="mt-14">
          {MARKET.tiers.map((t, i) => (
            <Reveal
              key={t.tier}
              delay={i * 0.08}
              className={`w-full border-t border-l-2 border-[var(--ws-line)] border-l-[var(--ws-amber)] py-7 pl-6 transition-colors duration-300 hover:bg-[var(--ws-panel)]/40 md:pl-8 ${
                ['', 'md:max-w-[74%]', 'md:max-w-[49%]'][i]
              }`}
            >
              <div className="flex flex-wrap items-baseline gap-x-5 gap-y-1">
                <MonoLabel>{t.tier}</MonoLabel>
                <span className="text-[clamp(2.25rem,4.6vw,3.5rem)] font-black leading-none tracking-[-0.03em] text-[var(--ws-amber)]">
                  {t.value}
                </span>
              </div>
              <p className="mt-3 max-w-[58ch] text-[14.5px] leading-relaxed text-[var(--ws-fg-2)]">
                {t.desc}
              </p>
            </Reveal>
          ))}
          <MonoLabel className="mt-4 block">
            Addressable market narrowing to the SE-Asia beachhead
          </MonoLabel>
        </div>

        {/* go-to-market roadmap — amber-ruled steps, not feature cards */}
        <div className="mt-16 grid grid-cols-1 gap-x-8 gap-y-8 md:grid-cols-3">
          {MARKET.stages.map((s, i) => (
            <Reveal
              key={s.index}
              delay={i * 0.06}
              className="border-t-2 border-[var(--ws-amber)] pt-5"
            >
              <MonoLabel className="text-[var(--ws-amber)]">{s.index}</MonoLabel>
              <h3 className="mt-3 text-lg font-bold text-[var(--ws-fg)]">{s.title}</h3>
              <p className="mt-2 text-[14.5px] leading-relaxed text-[var(--ws-fg-2)]">
                {s.body}
              </p>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ------------------------------------------------------------ Moat (band) */

export function Moat() {
  return (
    <section id="moat" className="bg-[var(--ws-amber)] py-24 md:py-28">
      <div className={WRAP}>
        <Reveal>
          <span
            className={`${MONO} text-[12px] font-medium uppercase tracking-[0.18em] text-[rgba(10,10,11,0.6)]`}
          >
            Why No One Has Built This
          </span>
          <h2 className="mt-4 max-w-[22ch] text-[clamp(2.1rem,4.6vw,3.75rem)] font-extrabold leading-[0.96] tracking-[-0.03em] text-[var(--ws-ink)]">
            A dataset moat that can only be built on the floor
          </h2>
        </Reveal>
        <div className="mt-14 grid grid-cols-1 border-t border-[rgba(10,10,11,0.2)] md:grid-cols-3">
          {MOAT.map((m, i) => (
            <Reveal
              key={m.index}
              delay={i * 0.08}
              className={`py-9 md:pr-8 ${
                i < 2 ? 'border-b border-[rgba(10,10,11,0.2)] md:border-b-0' : ''
              }`}
            >
              <span
                className={`${MONO} text-[12px] uppercase tracking-[0.14em] text-[rgba(10,10,11,0.55)]`}
              >
                / {m.index}
              </span>
              <h3 className="mt-4 text-xl font-bold tracking-[-0.01em] text-[var(--ws-ink)]">
                {m.title}
              </h3>
              <p className="mt-3 text-[15px] leading-relaxed text-[rgba(10,10,11,0.72)]">
                {m.body}
              </p>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ------------------------------------------------------------ Validation */

export function Validation() {
  return (
    <section id="validation" className={SECTION}>
      <div className={WRAP}>
        <SectionHead
          kicker="We Went to the Yards"
          heading="Field notes, not marketing copy"
          lead={VALIDATION.intro}
        />
        <div className="mt-12 flex flex-col gap-10">
          {VALIDATION.quotes.map((q, i) => (
            <Reveal
              key={q.name}
              delay={i * 0.06}
              className="max-w-[82ch] border-l-2 border-[var(--ws-amber)] pl-7"
            >
              <p className="text-2xl font-semibold leading-[1.28] tracking-[-0.01em] text-[var(--ws-fg)] md:text-[27px]">
                &ldquo;{q.quote}&rdquo;
              </p>
              <div className={`${MONO} mt-4 text-[12.5px] uppercase tracking-[0.06em] text-[var(--ws-fg-3)]`}>
                {q.name} · {q.role}
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ------------------------------------------------------------------ Team */

export function Team() {
  return (
    <section id="team" className={SECTION}>
      <div className={WRAP}>
        <SectionHead kicker="The Team" heading="Four founders, building on the floor" />
        <div className="mt-14 grid grid-cols-1 border-t border-[var(--ws-line)] md:grid-cols-2">
          {TEAM.map((m, i) => (
            <Reveal
              key={m.name}
              delay={(i % 2) * 0.08}
              className={`border-b border-[var(--ws-line)] p-8 transition-colors duration-300 hover:bg-[var(--ws-panel)]/40 md:p-10 ${
                i % 2 === 0 ? 'md:border-r' : ''
              }`}
            >
              <h3 className="text-xl font-bold tracking-[-0.01em] text-[var(--ws-fg)]">
                {m.name}
              </h3>
              <div className={`${MONO} mt-1.5 text-[12px] uppercase tracking-[0.1em] text-[var(--ws-amber)]`}>
                {m.affiliation}
              </div>
              <p className="mt-4 text-[15px] leading-relaxed text-[var(--ws-fg-2)]">
                {m.bio}
              </p>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ----------------------------------------------------------------- Raise */

export function Raise() {
  return (
    <section id="raise" className={SECTION}>
      <div className={WRAP}>
        <SectionHead
          kicker="The Plan"
          heading={
            <>
              Raising <span className="text-[var(--ws-amber)]">{RAISE.amount}</span> to
              put sensors on live yards
            </>
          }
          lead="A 12-month plan to move from concept to first paying contract. Forward-looking — every milestone below is a target, not a result."
        />

        {/* allocation as a single horizontal stacked bar + legend (no pie slop) */}
        <Reveal delay={0.08} className="mt-12">
          <div className="flex h-3 w-full overflow-hidden border border-[var(--ws-line)]">
            {RAISE.allocation.map((a, i) => (
              <div
                key={a.label}
                style={{ width: `${a.pct}%` }}
                className={i % 2 === 0 ? 'bg-[var(--ws-amber)]' : 'bg-[var(--ws-line-2)]'}
                aria-hidden
              />
            ))}
          </div>
          <ul className="mt-5 grid grid-cols-2 gap-x-6 gap-y-2 sm:grid-cols-3 lg:grid-cols-5">
            {RAISE.allocation.map((a) => (
              <li key={a.label} className="flex items-baseline justify-between gap-2">
                <span className="text-[14px] text-[var(--ws-fg-2)]">{a.label}</span>
                <span className={`${MONO} text-[13px] text-[var(--ws-fg)]`}>{a.pct}%</span>
              </li>
            ))}
          </ul>
        </Reveal>

        <div className="mt-14 grid grid-cols-1 gap-px md:grid-cols-2">
          {RAISE.milestones.map((m, i) => (
            <Reveal
              key={m.window}
              delay={i * 0.08}
              className="border-t-2 border-[var(--ws-amber)] pt-6 md:pr-10"
            >
              <MonoLabel className="text-[var(--ws-fg)]">{m.window}</MonoLabel>
              <ul className="mt-4 space-y-3">
                {m.points.map((pt) => (
                  <li key={pt} className="flex gap-3 text-[15px] leading-snug text-[var(--ws-fg-2)]">
                    <span className={`${MONO} text-[var(--ws-amber)]`} aria-hidden>
                      /
                    </span>
                    <span>{pt}</span>
                  </li>
                ))}
              </ul>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}

/* --------------------------------------------------------------- Contact */

export function Contact() {
  return (
    <section id="contact" className="border-t border-[var(--ws-line)] py-28 md:py-32">
      <div className={WRAP}>
        <Reveal>
          <div className="flex items-center gap-4">
            <Rule />
            <Kicker>Contact</Kicker>
          </div>
          <h2 className="mt-5 max-w-[20ch] text-[clamp(2.5rem,6vw,4.5rem)] font-black leading-[0.94] tracking-[-0.03em] text-[var(--ws-fg)]">
            {CONTACT.headline}
          </h2>
          <p className="mt-6 max-w-[56ch] text-lg leading-relaxed text-[var(--ws-fg-2)]">
            {CONTACT.sub}
          </p>
        </Reveal>

        <Reveal delay={0.1}>
          <div className="mt-10 flex flex-wrap items-center gap-4">
            <Magnetic>
              <a
                href={BOOKING_URL}
                {...(isExternal(BOOKING_URL)
                  ? { target: '_blank', rel: 'noopener noreferrer' }
                  : {})}
                className={`${MONO} inline-block bg-[var(--ws-amber)] px-7 py-4 text-[13px] uppercase tracking-[0.08em] text-[var(--ws-ink)] transition-colors hover:bg-[var(--ws-amber-hi)]`}
              >
                Schedule a demo
              </a>
            </Magnetic>
            {DECK_URL ? (
              <a
                href={DECK_URL}
                {...(DECK_URL.endsWith('.pdf') ? { download: true } : {})}
                {...(isExternal(DECK_URL)
                  ? { target: '_blank', rel: 'noopener noreferrer' }
                  : {})}
                className={`${MONO} border border-[var(--ws-line-2)] px-7 py-4 text-[13px] uppercase tracking-[0.08em] text-[var(--ws-fg)] transition-colors hover:border-[var(--ws-fg-3)]`}
              >
                Download deck
              </a>
            ) : null}
            <a
              href={`mailto:${CONTACT_EMAIL}`}
              className={`${MONO} text-[13px] uppercase tracking-[0.06em] text-[var(--ws-amber)] underline-offset-4 hover:underline`}
            >
              {CONTACT_EMAIL}
            </a>
          </div>
        </Reveal>
      </div>
    </section>
  );
}

/* ---------------------------------------------------------------- Footer */

export function Footer() {
  const linkClass =
    'text-[14px] text-[var(--ws-fg-2)] transition-colors hover:text-[var(--ws-fg)]';
  return (
    <footer className="border-t border-[var(--ws-line)] py-14 md:py-16">
      <div className={WRAP}>
        <div className="grid grid-cols-1 gap-10 md:grid-cols-[1.5fr_1fr_1fr] md:gap-12">
          {/* brand */}
          <div>
            <a
              href="#top"
              className="text-xl font-extrabold tracking-[-0.02em] text-[var(--ws-fg)]"
            >
              Warp<span className="text-[var(--ws-amber)]">Sense</span>
            </a>
            <p className="mt-3 max-w-[34ch] text-[14px] leading-relaxed text-[var(--ws-fg-2)]">
              {BRAND.oneLiner}
            </p>
          </div>

          {/* explore — live product surfaces */}
          <nav aria-label="Explore">
            <MonoLabel>Explore</MonoLabel>
            <ul className="mt-4 space-y-2.5">
              {EXPLORE_LINKS.map((l) => (
                <li key={l.href}>
                  <Link href={l.href} className={linkClass}>
                    {l.label}
                  </Link>
                </li>
              ))}
            </ul>
          </nav>

          {/* company / legal */}
          <nav aria-label="Company">
            <MonoLabel>Company</MonoLabel>
            <ul className="mt-4 space-y-2.5">
              <li>
                <a href="#contact" className={linkClass}>
                  Contact
                </a>
              </li>
              <li>
                <Link href="/privacy" className={linkClass}>
                  Privacy
                </Link>
              </li>
              <li>
                <Link href="/terms" className={linkClass}>
                  Terms
                </Link>
              </li>
            </ul>
          </nav>
        </div>

        <div className="mt-12 flex flex-col items-start justify-between gap-3 border-t border-[var(--ws-line)] pt-6 sm:flex-row sm:items-center">
          <MonoLabel>© {new Date().getFullYear()} WarpSense</MonoLabel>
          <MonoLabel>Singapore</MonoLabel>
        </div>
      </div>
    </footer>
  );
}
