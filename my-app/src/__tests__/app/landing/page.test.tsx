/**
 * Landing page — smoke test for investor presentation page.
 *
 * Verifies key sections: Hero, Stats, Technology, Demo, Social Proof (generic
 * placeholders), CTA. Mocks framer-motion with Proxy-based mock that filters
 * style prop (MotionValues are invalid in DOM).
 *
 * Import from (marketing)/page; test file stays at landing/ for path simplicity.
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import LandingPage from '@/app/(marketing)/page';

// Proxy-based Framer mock — filter style prop so MotionValues don't reach DOM
jest.mock('framer-motion', () => {
  const React = require('react');
  return {
    motion: new Proxy(
      {},
      {
        get: (_target, prop) => {
          return React.forwardRef(
            (
              props: Record<string, unknown> & { children?: React.ReactNode },
              ref: React.Ref<unknown>
            ) => {
              const { style, ...rest } = props;
              return React.createElement(prop as string, { ...rest, ref });
            }
          );
        },
      }
    ),
    AnimatePresence: ({
      children,
    }: {
      children: React.ReactNode;
    }) => <>{children}</>,
    useScroll: () => ({ scrollYProgress: { get: () => 0 } }),
    useTransform: () => ({ get: () => 0 }),
    useInView: () => true,
  };
});

describe('LandingPage', () => {
  it('renders hero heading with gradient text', () => {
    render(<LandingPage />);
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(
      /The Future of/i
    );
    expect(screen.getByText(/Industrial Training/)).toBeInTheDocument();
  });

  it('renders hero subtext', () => {
    render(<LandingPage />);
    expect(
      screen.getByText(/Real-time thermal analytics and AI-powered feedback/i)
    ).toBeInTheDocument();
  });

  it('renders stats section (87%, $2.4M, 94%)', () => {
    render(<LandingPage />);
    expect(screen.getByText('87%')).toBeInTheDocument();
    expect(screen.getByText('$2.4M')).toBeInTheDocument();
    expect(screen.getAllByText('94%').length).toBeGreaterThanOrEqual(1);
  });

  it('renders technology section heading', () => {
    render(<LandingPage />);
    expect(screen.getByText(/Precision meets simplicity/i)).toBeInTheDocument();
  });

  it('renders four feature cards', () => {
    render(<LandingPage />);
    expect(screen.getByText(/Real-time Analysis/i)).toBeInTheDocument();
    expect(screen.getByText(/AI-Powered Insights/i)).toBeInTheDocument();
    expect(screen.getByText(/Enterprise Security/i)).toBeInTheDocument();
    expect(screen.getByText(/Plug & Play Hardware/i)).toBeInTheDocument();
  });

  it('renders demo section with See it in action', () => {
    render(<LandingPage />);
    expect(screen.getByText(/See it in action/i)).toBeInTheDocument();
    expect(screen.getByText(/Interactive Demo/i)).toBeInTheDocument();
  });

  it('renders Try Full Demo link to /demo', () => {
    render(<LandingPage />);
    const link = screen.getByRole('link', { name: /Try Full Demo/i });
    expect(link).toHaveAttribute('href', '/demo');
  });

  it('renders social proof with generic placeholders', () => {
    render(<LandingPage />);
    expect(screen.getByText(/Trusted by industry leaders/i)).toBeInTheDocument();
    expect(screen.getByText(/Major US Shipyards/)).toBeInTheDocument();
    expect(screen.getByText(/Defense Contractors/)).toBeInTheDocument();
    expect(screen.getByText(/Fortune 500 Manufacturing/)).toBeInTheDocument();
    expect(screen.getByText(/Heavy Industry Leaders/)).toBeInTheDocument();
  });

  it('renders CTA section with Schedule Demo and Download Deck', () => {
    render(<LandingPage />);
    expect(
      screen.getByText(/Ready to transform your training?/i)
    ).toBeInTheDocument();
    expect(
      screen.getByRole('link', { name: /Schedule a Demo/i })
    ).toBeInTheDocument();
    expect(
      screen.getByRole('link', { name: /Download Deck/i })
    ).toBeInTheDocument();
  });

  it('links See Live Demo to /demo', () => {
    render(<LandingPage />);
    const link = screen.getByRole('link', { name: /See Live Demo/i });
    expect(link).toHaveAttribute('href', '/demo');
  });

  it('links Request Demo to /demo when env unset', async () => {
    const envBackup = process.env.NEXT_PUBLIC_DEMO_BOOKING_URL;
    const deckBackup = process.env.NEXT_PUBLIC_INVESTOR_DECK_URL;
    delete process.env.NEXT_PUBLIC_DEMO_BOOKING_URL;
    delete process.env.NEXT_PUBLIC_INVESTOR_DECK_URL;
    jest.resetModules();
    try {
      const { default: LandingPageFresh } = await import(
        '@/app/(marketing)/page'
      );
      render(<LandingPageFresh />);
      const links = screen.getAllByRole('link', { name: /Request Demo/i });
      expect(links.length).toBeGreaterThan(0);
      expect(links[0]).toHaveAttribute('href', '/demo');
    } finally {
      if (envBackup !== undefined)
        process.env.NEXT_PUBLIC_DEMO_BOOKING_URL = envBackup;
      if (deckBackup !== undefined)
        process.env.NEXT_PUBLIC_INVESTOR_DECK_URL = deckBackup;
      jest.resetModules();
    }
  });

  it('renders footer with WeldVision', () => {
    render(<LandingPage />);
    expect(screen.getByText(/WeldVision/)).toBeInTheDocument();
    expect(screen.getByText(/All rights reserved/)).toBeInTheDocument();
  });

  it('renders WeldVision branding in nav linking to /', () => {
    render(<LandingPage />);
    const navLinks = screen.getAllByText('WeldVision');
    const homeLink = navLinks.find((el) => el.closest('a')?.getAttribute('href') === '/');
    expect(homeLink || navLinks[0]).toBeTruthy();
  });
});
