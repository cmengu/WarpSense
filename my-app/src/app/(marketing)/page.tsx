'use client';

/**
 * Landing Page — Premium Apple-inspired investor presentation page.
 *
 * PURPOSE: Marketing page at / for investor demos, prospect sharing, pitch support.
 * No backend required. ROI stats, technology highlights, social proof, CTAs.
 *
 * Design: Black bg, blue/purple gradients only, glass morphism, CSS animations
 * (parallax, staggered fade-in, scroll indicator).
 *
 * CTA destinations: env vars with empty-string fallback per plan.
 */

import { useRef, useState, useEffect } from 'react';
import Link from 'next/link';
import { useInView } from '@/hooks/useInView';
import { useScrollParallax } from '@/hooks/useScrollParallax';

/**
 * Schedule Demo: Calendly/Cal.com URL or fallback to /demo.
 * Evaluated at build time (Next.js inlines NEXT_PUBLIC_*). Fallback when undefined or empty.
 */
const DEMO_BOOKING_URL =
  (typeof process !== 'undefined' &&
    (process.env?.NEXT_PUBLIC_DEMO_BOOKING_URL ?? '').trim()) ||
  '/demo';

/**
 * Download Deck: PDF URL or fallback to #download-deck anchor in CTA section.
 * Evaluated at build time. Fallback scrolls to section when env unset.
 */
const INVESTOR_DECK_URL =
  (typeof process !== 'undefined' &&
    (process.env?.NEXT_PUBLIC_INVESTOR_DECK_URL ?? '').trim()) ||
  '#download-deck';

const SOCIAL_PROOF_ITEMS = [
  'Major US Shipyards',
  'Defense Contractors',
  'Fortune 500 Manufacturing',
  'Heavy Industry Leaders',
];

/** Inline style for fade-in-up animation when inView */
function fadeInUpStyle(inView: boolean, delay = 0) {
  return {
    opacity: inView ? 1 : 0,
    transform: inView ? 'translateY(0)' : 'translateY(20px)',
    transition: `opacity 0.8s ease-out ${delay}s, transform 0.8s ease-out ${delay}s`,
  };
}

/** Inline style for fade-in animation when inView */
function fadeInStyle(inView: boolean) {
  return {
    opacity: inView ? 1 : 0,
    transition: 'opacity 1s ease-out',
  };
}

/** Inline style for slide-in-left when inView */
function slideInLeftStyle(inView: boolean, delay = 0) {
  return {
    opacity: inView ? 1 : 0,
    transform: inView ? 'translateX(0)' : 'translateX(-30px)',
    transition: `opacity 0.8s ease-out ${delay}s, transform 0.8s ease-out ${delay}s`,
  };
}

/** Inline style for slide-in-right when inView */
function slideInRightStyle(inView: boolean, delay = 0) {
  return {
    opacity: inView ? 1 : 0,
    transform: inView ? 'translateX(0)' : 'translateX(30px)',
    transition: `opacity 0.8s ease-out ${delay}s, transform 0.8s ease-out ${delay}s`,
  };
}

/** Inline style for scale-in when inView */
function scaleInStyle(inView: boolean, delay = 0) {
  return {
    opacity: inView ? 1 : 0,
    transform: inView ? 'scale(1)' : 'scale(0.95)',
    transition: `opacity 1s ease-out ${delay}s, transform 1s ease-out ${delay}s`,
  };
}

export default function LandingPage() {
  const heroInView = useInView({ once: true });
  const statsInView = useInView({ once: true });
  const techInView = useInView({ once: true });
  const demoInView = useInView({ once: true });
  const socialInView = useInView({ once: true });
  const impactInView = useInView({ once: true });

  const { style: parallaxStyle } = useScrollParallax();

  const navRef = useRef<HTMLElement>(null);
  const mobileFirstLinkRef = useRef<HTMLAnchorElement>(null);
  const mobileNavTriggerRef = useRef<HTMLButtonElement>(null);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  const navLinks = [
    { href: '#technology', label: 'Technology' },
    { href: '#analytics', label: 'Analytics' },
    { href: '#impact', label: 'Impact' },
  ];

  // Escape key closes mobile nav
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setMobileNavOpen(false);
    };
    window.addEventListener('keydown', handleEscape);
    return () => window.removeEventListener('keydown', handleEscape);
  }, []);

  // Click outside closes mobile nav (stopPropagation on hamburger prevents race)
  useEffect(() => {
    if (!mobileNavOpen) return;
    const handleClickOutside = (e: MouseEvent) => {
      if (
        navRef.current &&
        !navRef.current.contains(e.target as Node)
      ) {
        setMobileNavOpen(false);
      }
    };
    document.addEventListener('click', handleClickOutside);
    return () => document.removeEventListener('click', handleClickOutside);
  }, [mobileNavOpen]);

  // Focus trap: move focus into mobile nav when opened, return to trigger on close
  const prevMobileNavOpen = useRef(false);
  useEffect(() => {
    if (mobileNavOpen) {
      mobileFirstLinkRef.current?.focus();
    } else if (prevMobileNavOpen.current) {
      mobileNavTriggerRef.current?.focus();
    }
    prevMobileNavOpen.current = mobileNavOpen;
  }, [mobileNavOpen]);

  /** Returns true if url is external (http/https). */
  const isExternal = (url: string) => url.startsWith('http');

  return (
    <div className="bg-black text-white overflow-hidden">
      <nav
        ref={navRef}
        className="fixed top-0 w-full z-50 bg-black/80 backdrop-blur-xl border-b border-white/10"
        aria-label="Main navigation"
      >
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <Link
            href="/"
            className="text-2xl font-semibold tracking-tight text-white hover:text-white"
          >
            WarpSense
          </Link>

          <div className="hidden md:flex items-center gap-8 text-sm">
            {navLinks.map((link) => (
              <a
                key={link.href}
                href={link.href}
                className="hover:text-gray-400 transition-colors"
              >
                {link.label}
              </a>
            ))}
            <a
              href={DEMO_BOOKING_URL}
              {...(isExternal(DEMO_BOOKING_URL)
                ? {
                    target: '_blank',
                    rel: 'noopener noreferrer',
                  }
                : {})}
              className="bg-white text-black px-6 py-2 rounded-full font-medium hover:bg-gray-200 transition-colors"
            >
              Request Demo
            </a>
          </div>

          <div className="md:hidden flex items-center gap-4">
            <a
              href="/demo"
              className="text-sm font-medium text-white hover:text-gray-300"
            >
              Demo
            </a>
            <button
              ref={mobileNavTriggerRef}
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                setMobileNavOpen((prev) => !prev);
              }}
              className="p-2 rounded-lg hover:bg-white/10 transition-colors"
              aria-expanded={mobileNavOpen}
              aria-controls="mobile-nav"
              aria-label={mobileNavOpen ? 'Close menu' : 'Open menu'}
            >
              <svg
                className="w-6 h-6"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                {mobileNavOpen ? (
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M6 18L18 6M6 6l12 12"
                  />
                ) : (
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M4 6h16M4 12h16M4 18h16"
                  />
                )}
              </svg>
            </button>
          </div>
        </div>

        <div
          id="mobile-nav"
          role="dialog"
          aria-modal="true"
          aria-label="Mobile navigation"
          className={`md:hidden border-t border-white/10 bg-black/95 backdrop-blur-xl overflow-hidden mobile-nav-panel ${
            mobileNavOpen ? 'opacity-100 max-h-[500px]' : 'opacity-0 max-h-0'
          }`}
        >
          {mobileNavOpen && (
            <div className="px-6 py-4 flex flex-col gap-4">
              {navLinks.map((link, idx) => (
                <a
                  key={link.href}
                  ref={idx === 0 ? mobileFirstLinkRef : undefined}
                  href={link.href}
                  onClick={() => setMobileNavOpen(false)}
                  className="text-base hover:text-gray-400 transition-colors"
                >
                  {link.label}
                </a>
              ))}
              <a
                href={DEMO_BOOKING_URL}
                onClick={() => setMobileNavOpen(false)}
                {...(isExternal(DEMO_BOOKING_URL)
                  ? {
                      target: '_blank',
                      rel: 'noopener noreferrer',
                    }
                  : {})}
                className="bg-white text-black px-6 py-3 rounded-full font-medium hover:bg-gray-200 transition-colors text-center"
              >
                Request Demo
              </a>
            </div>
          )}
        </div>
      </nav>

      <section
        ref={heroInView.ref}
        className="relative h-screen flex items-center justify-center overflow-hidden"
        aria-labelledby="hero-heading"
      >
        <div className="absolute inset-0 bg-gradient-to-b from-blue-950/20 via-black to-black" />
        <div
          className="absolute inset-0 opacity-20"
          aria-hidden
          style={{ perspective: '500px' }}
        >
          <div
            className="absolute inset-0"
            style={{
              backgroundImage: `linear-gradient(rgba(59, 130, 246, 0.1) 1px, transparent 1px),
                                linear-gradient(90deg, rgba(59, 130, 246, 0.1) 1px, transparent 1px)`,
              backgroundSize: '50px 50px',
              transform: 'rotateX(60deg)',
              transformOrigin: 'center bottom',
            }}
          />
        </div>

        <div
          className="relative z-10 text-center px-6 max-w-5xl"
          style={parallaxStyle}
        >
          <div style={fadeInUpStyle(heroInView.inView, 0)}>
            <h1
              id="hero-heading"
              className="text-7xl md:text-8xl font-bold tracking-tight mb-6 bg-gradient-to-r from-white via-blue-100 to-white bg-clip-text text-transparent"
            >
              The Future of
              <br />
              Industrial Training
            </h1>
          </div>

          <p
            className="text-xl md:text-2xl text-gray-400 mb-12 max-w-3xl mx-auto"
            style={fadeInUpStyle(heroInView.inView, 0.2)}
          >
            Real-time thermal analytics and AI-powered feedback transforming
            skilled labor training in heavy industry
          </p>

          <div
            style={fadeInUpStyle(heroInView.inView, 0.4)}
            className="flex flex-col sm:flex-row gap-4 justify-center"
          >
            <Link
              href="/demo"
              className="bg-white text-black px-8 py-4 rounded-full text-lg font-semibold hover:bg-gray-200 transition-colors text-center"
            >
              See Live Demo
            </Link>
            <a
              href="#analytics"
              className="border border-white/30 px-8 py-4 rounded-full text-lg font-semibold hover:bg-white/10 transition-colors text-center"
            >
              See Demo Section
            </a>
          </div>
        </div>

        <div
          className="absolute bottom-8 left-1/2 -translate-x-1/2 animate-bounce-scroll"
          aria-hidden
        >
          <div className="w-6 h-10 border-2 border-white/30 rounded-full flex items-start justify-center p-2">
            <div className="w-1 h-2 bg-white/50 rounded-full" />
          </div>
        </div>
      </section>

      <section ref={statsInView.ref} className="py-32 relative">
        <div className="absolute inset-0 bg-gradient-to-b from-black via-blue-950/10 to-black" />
        <div className="max-w-7xl mx-auto px-6 relative z-10">
          <div
            className="grid grid-cols-1 md:grid-cols-3 gap-16"
            style={fadeInStyle(statsInView.inView)}
          >
            <div
              className="text-center"
              style={fadeInUpStyle(statsInView.inView, 0.1)}
            >
              <div className="text-7xl font-bold bg-gradient-to-r from-blue-400 to-violet-400 bg-clip-text text-transparent mb-4">
                87%
              </div>
              <div className="text-xl text-gray-400">
                Reduction in training time
              </div>
              <div className="text-sm text-gray-600 mt-2">
                Industry average: 6 months → 3 weeks
              </div>
            </div>
            <div
              className="text-center"
              style={fadeInUpStyle(statsInView.inView, 0.2)}
            >
              <div className="text-7xl font-bold bg-gradient-to-r from-violet-400 to-purple-400 bg-clip-text text-transparent mb-4">
                $2.4M
              </div>
              <div className="text-xl text-gray-400">
                Average cost savings per facility
              </div>
              <div className="text-sm text-gray-600 mt-2">
                Reduced material waste + faster certification
              </div>
            </div>
            <div
              className="text-center"
              style={fadeInUpStyle(statsInView.inView, 0.3)}
            >
              <div className="text-7xl font-bold bg-gradient-to-r from-blue-500 to-purple-500 bg-clip-text text-transparent mb-4">
                94%
              </div>
              <div className="text-xl text-gray-400">
                First-time weld quality
              </div>
              <div className="text-sm text-gray-600 mt-2">
                vs. 42% industry standard for novices
              </div>
            </div>
          </div>
        </div>
      </section>

      <section id="technology" ref={techInView.ref} className="py-32 relative">
        <div className="max-w-7xl mx-auto px-6">
          <div
            className="text-center mb-20"
            style={fadeInUpStyle(techInView.inView)}
          >
            <h2 className="text-5xl md:text-6xl font-bold mb-6">
              Precision meets simplicity
            </h2>
            <p className="text-xl text-gray-400 max-w-3xl mx-auto">
              Military-grade thermal sensors combined with intuitive real-time
              feedback
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-12 items-center">
            <div
              style={slideInLeftStyle(techInView.inView)}
              className="bg-gradient-to-br from-blue-950/40 to-purple-950/40 rounded-3xl p-12 backdrop-blur-sm border border-white/10"
            >
              <div className="w-16 h-16 bg-blue-500/20 rounded-2xl flex items-center justify-center mb-6">
                <svg
                  className="w-8 h-8 text-blue-400"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M13 10V3L4 14h7v7l9-11h-7z"
                  />
                </svg>
              </div>
              <h3 className="text-3xl font-bold mb-4">Real-time Analysis</h3>
              <p className="text-gray-400 text-lg leading-relaxed">
                100Hz thermal monitoring with instant feedback. Catch mistakes
                in milliseconds, not hours.
              </p>
            </div>

            <div
              style={slideInRightStyle(techInView.inView)}
              className="bg-gradient-to-br from-violet-950/40 to-purple-950/40 rounded-3xl p-12 backdrop-blur-sm border border-white/10"
            >
              <div className="w-16 h-16 bg-purple-500/20 rounded-2xl flex items-center justify-center mb-6">
                <svg
                  className="w-8 h-8 text-purple-400"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
                  />
                </svg>
              </div>
              <h3 className="text-3xl font-bold mb-4">AI-Powered Insights</h3>
              <p className="text-gray-400 text-lg leading-relaxed">
                Pattern recognition learns from expert welders. Personalized
                coaching for every trainee.
              </p>
            </div>

            <div
              style={slideInLeftStyle(techInView.inView, 0.1)}
              className="bg-gradient-to-br from-blue-950/40 to-violet-950/40 rounded-3xl p-12 backdrop-blur-sm border border-white/10"
            >
              <div className="w-16 h-16 bg-blue-500/20 rounded-2xl flex items-center justify-center mb-6">
                <svg
                  className="w-8 h-8 text-blue-400"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"
                  />
                </svg>
              </div>
              <h3 className="text-3xl font-bold mb-4">Enterprise Security</h3>
              <p className="text-gray-400 text-lg leading-relaxed">
                On-premise deployment. Your data never leaves your facility. SOC
                2 compliant.
              </p>
            </div>

            <div
              style={slideInRightStyle(techInView.inView, 0.1)}
              className="bg-gradient-to-br from-violet-950/40 to-purple-950/40 rounded-3xl p-12 backdrop-blur-sm border border-white/10"
            >
              <div className="w-16 h-16 bg-violet-500/20 rounded-2xl flex items-center justify-center mb-6">
                <svg
                  className="w-8 h-8 text-violet-400"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
                  />
                </svg>
              </div>
              <h3 className="text-3xl font-bold mb-4">Plug & Play Hardware</h3>
              <p className="text-gray-400 text-lg leading-relaxed">
                Retrofit existing equipment in under 30 minutes. No production
                downtime.
              </p>
            </div>
          </div>
        </div>
      </section>

      <section
        id="analytics"
        ref={demoInView.ref}
        className="py-32 relative overflow-hidden"
      >
        <div className="absolute inset-0 bg-gradient-to-b from-black via-blue-950/20 to-black" />
        <div className="max-w-7xl mx-auto px-6 relative z-10">
          <div
            className="text-center mb-20"
            style={fadeInUpStyle(demoInView.inView)}
          >
            <h2 className="text-5xl md:text-6xl font-bold mb-6">
              See it in action
            </h2>
            <p className="text-xl text-gray-400 max-w-3xl mx-auto">
              Live thermal visualization and real-time quality metrics
            </p>
          </div>

          <div
            style={scaleInStyle(demoInView.inView, 0.3)}
            className="bg-gradient-to-br from-gray-900 to-black rounded-3xl p-8 md:p-16 border border-white/10 shadow-2xl"
          >
            <div className="aspect-video bg-gradient-to-br from-blue-950/40 to-purple-950/40 rounded-2xl flex items-center justify-center">
              <div className="text-center">
                <div className="w-24 h-24 bg-white/10 rounded-full flex items-center justify-center mx-auto mb-6 backdrop-blur-sm">
                  <svg
                    className="w-12 h-12 text-white"
                    fill="currentColor"
                    viewBox="0 0 20 20"
                  >
                    <path d="M6.3 2.841A1.5 1.5 0 004 4.11V15.89a1.5 1.5 0 002.3 1.269l9.344-5.89a1.5 1.5 0 000-2.538L6.3 2.84z" />
                  </svg>
                </div>
                <p className="text-2xl font-semibold mb-2">Interactive Demo</p>
                <p className="text-gray-400">
                  Use the button below to launch the full demo with live thermal analysis
                </p>
              </div>
            </div>

            <div className="mt-8 flex justify-center">
              <Link
                href="/demo"
                className="inline-flex items-center gap-2 bg-white text-black px-6 py-3 rounded-full font-semibold hover:bg-gray-200 transition-colors"
              >
                Try Full Demo <span aria-hidden>→</span>
              </Link>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-8 mt-12">
              <div className="text-center">
                <div className="text-4xl font-bold text-blue-400 mb-2">
                  300°C
                </div>
                <div className="text-sm text-gray-400">Optimal Temperature</div>
              </div>
              <div className="text-center">
                <div className="text-4xl font-bold text-blue-400 mb-2">45°</div>
                <div className="text-sm text-gray-400">Perfect Torch Angle</div>
              </div>
              <div className="text-center">
                <div className="text-4xl font-bold text-purple-400 mb-2">
                  30°C/s
                </div>
                <div className="text-sm text-gray-400">Heat Dissipation</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section ref={socialInView.ref} className="py-32 relative">
        <div className="max-w-7xl mx-auto px-6">
          <div
            className="text-center mb-20"
            style={fadeInUpStyle(socialInView.inView)}
          >
            <h2 className="text-5xl md:text-6xl font-bold mb-6">
              Trusted by industry leaders
            </h2>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-12">
            {SOCIAL_PROOF_ITEMS.map((item, i) => (
              <div
                key={item}
                style={fadeInUpStyle(socialInView.inView, i * 0.1)}
                className="flex items-center justify-center text-2xl font-semibold text-gray-600 hover:text-white transition-colors text-center"
              >
                {item}
              </div>
            ))}
          </div>
        </div>
      </section>

      <section id="impact" ref={impactInView.ref} className="py-32 relative scroll-mt-20">
        <span
          id="download-deck"
          className="absolute -top-8 block scroll-mt-24"
          aria-hidden
        />
        <div className="absolute inset-0 bg-gradient-to-b from-black via-blue-950/30 to-black" />
        <div
          style={fadeInUpStyle(impactInView.inView)}
          className="max-w-4xl mx-auto px-6 text-center relative z-10"
        >
          <h2 className="text-5xl md:text-7xl font-bold mb-8 bg-gradient-to-r from-white via-blue-100 to-white bg-clip-text text-transparent">
            Ready to transform your training?
          </h2>
          <p className="text-xl md:text-2xl text-gray-400 mb-12">
            Join the future of skilled labor development
          </p>
          <div className="flex flex-col sm:flex-row gap-6 justify-center">
            <a
              href={DEMO_BOOKING_URL}
              {...(isExternal(DEMO_BOOKING_URL)
                ? {
                    target: '_blank',
                    rel: 'noopener noreferrer',
                  }
                : {})}
              className="bg-white text-black px-10 py-5 rounded-full text-lg font-semibold hover:bg-gray-200 transition-colors shadow-2xl text-center"
            >
              Schedule a Demo
            </a>
            <a
              href={INVESTOR_DECK_URL}
              {...(INVESTOR_DECK_URL.endsWith('.pdf')
                ? { download: true }
                : {})}
              {...(isExternal(INVESTOR_DECK_URL)
                ? {
                    target: '_blank',
                    rel: 'noopener noreferrer',
                  }
                : {})}
              className="border border-white/30 px-10 py-5 rounded-full text-lg font-semibold hover:bg-white/10 transition-colors text-center"
            >
              Download Deck
            </a>
          </div>
        </div>
      </section>

      <footer className="border-t border-white/10 py-12">
        <div className="max-w-7xl mx-auto px-6 flex flex-col sm:flex-row items-center justify-between gap-4 text-sm text-gray-600">
          <div>© {new Date().getFullYear()} WarpSense. All rights reserved.</div>
          <div className="flex gap-8">
            <Link
              href="/privacy"
              className="hover:text-white transition-colors"
            >
              Privacy
            </Link>
            <Link
              href="/terms"
              className="hover:text-white transition-colors"
            >
              Terms
            </Link>
            <Link href="#impact" className="hover:text-white transition-colors">
              Contact
            </Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
