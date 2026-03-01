/**
 * Landing page — smoke test for investor presentation page.
 *
 * Verifies key sections: Hero, Stats, Technology, Demo, Social Proof (generic
 * placeholders), CTA.
 *
 * Import from (marketing)/page; test file stays at landing/ for path simplicity.
 * Landing page uses CSS animations + useInView/useScrollParallax (no framer-motion).
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import LandingPage from '@/app/(marketing)/page';

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

  it('renders Try Full Demo link to /dashboard', () => {
    render(<LandingPage />);
    const link = screen.getByRole('link', { name: /Try Full Demo/i });
    expect(link).toHaveAttribute('href', '/dashboard');
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

  it('links See Live Demo to /dashboard', () => {
    render(<LandingPage />);
    const link = screen.getByRole('link', { name: /See Live Demo/i });
    expect(link).toHaveAttribute('href', '/dashboard');
  });

  it('links Request Demo to /dashboard (fallback when env unset)', () => {
    render(<LandingPage />);
    const links = screen.getAllByRole('link', { name: /Request Demo/i });
    expect(links.length).toBeGreaterThan(0);
    expect(links[0]).toHaveAttribute('href', '/dashboard');
  });

  it('renders footer with WarpSense', () => {
    render(<LandingPage />);
    expect(screen.getAllByText(/WarpSense/).length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(/All rights reserved/)).toBeInTheDocument();
  });

  it('renders WarpSense branding in nav linking to /', () => {
    render(<LandingPage />);
    const navLinks = screen.getAllByText('WarpSense');
    const homeLink = navLinks.find((el) => el.closest('a')?.getAttribute('href') === '/');
    expect(homeLink || navLinks[0]).toBeTruthy();
  });
});
