/**
 * Landing page — smoke test for the WarpSense "Instrument" (V1) landing.
 *
 * Verifies the key sections render with their real, verbatim content and that
 * the live-demo / contact CTAs point to the right targets. Content lives in
 * lib/warpsense-content; sections use framer-motion <Reveal> (whileInView).
 * IntersectionObserver is mocked in jest.setup.js, so revealed content is
 * present in the DOM at initial opacity.
 *
 * Import from (marketing)/page; test file stays at landing/ for path simplicity.
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import LandingPage from '@/app/(marketing)/page';

describe('LandingPage', () => {
  it('renders the hero headline', () => {
    render(<LandingPage />);
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(
      /Weld defects caught before the\s*inspector\s*arrives/i
    );
  });

  it('renders the hero subtext', () => {
    render(<LandingPage />);
    expect(
      screen.getByText(/clip-on sensor system that monitors five structural parameters/i)
    ).toBeInTheDocument();
  });

  it('renders the problem section', () => {
    render(<LandingPage />);
    expect(
      screen.getByText(/Quality control runs on eyes, after the metal has cooled/i)
    ).toBeInTheDocument();
    expect(
      screen.getByText(/The expert workforce is disappearing/i)
    ).toBeInTheDocument();
  });

  it('renders the four how-it-works steps', () => {
    render(<LandingPage />);
    expect(screen.getByText(/^Clip on$/i)).toBeInTheDocument();
    expect(screen.getByText(/Measure in real time/i)).toBeInTheDocument();
    expect(screen.getByText(/Instant verdict/i)).toBeInTheDocument();
    expect(screen.getByText(/See what X-ray misses/i)).toBeInTheDocument();
  });

  it('renders the market tiers (TAM / SAM / SOM)', () => {
    render(<LandingPage />);
    expect(screen.getByText('TAM')).toBeInTheDocument();
    expect(screen.getByText('SAM')).toBeInTheDocument();
    expect(screen.getByText('SOM')).toBeInTheDocument();
    expect(screen.getByText(/\$4\.7/)).toBeInTheDocument();
  });

  it('renders the competitive-advantage (moat) section', () => {
    render(<LandingPage />);
    expect(screen.getByText(/Why No One Has Built This/i)).toBeInTheDocument();
    expect(screen.getByText(/Hardware-agnostic by design/i)).toBeInTheDocument();
    expect(screen.getByText(/Camera systems are blind/i)).toBeInTheDocument();
  });

  it('renders real validation quotes with named attribution', () => {
    render(<LandingPage />);
    expect(
      screen.getByText(/ten years for a welder to develop the judgment/i)
    ).toBeInTheDocument();
    expect(screen.getByText(/Mr Tuck Wai/)).toBeInTheDocument();
  });

  it('renders the founding team', () => {
    render(<LandingPage />);
    expect(screen.getByText(/Ng Chen Meng/)).toBeInTheDocument();
    expect(screen.getByText(/Yuan Yi Ning/)).toBeInTheDocument();
  });

  it('links the hero live-demo CTA to /dashboard', () => {
    render(<LandingPage />);
    const link = screen.getByRole('link', { name: /See the live demo/i });
    expect(link).toHaveAttribute('href', '/dashboard');
  });

  it('links the demo section CTA(s) to /dashboard', () => {
    render(<LandingPage />);
    const links = screen.getAllByRole('link', { name: /Open the live dashboard/i });
    expect(links.length).toBeGreaterThanOrEqual(1);
    links.forEach((l) => expect(l).toHaveAttribute('href', '/dashboard'));
  });

  it('renders the honest proof strip', () => {
    render(<LandingPage />);
    expect(
      screen.getByText('Active production shipyards')
    ).toBeInTheDocument();
    expect(
      screen.getByText('Structural parameters measured')
    ).toBeInTheDocument();
  });

  it('renders the contact section with a Schedule a demo CTA', () => {
    render(<LandingPage />);
    expect(screen.getByText(/Talk to us/i)).toBeInTheDocument();
    expect(
      screen.getByRole('link', { name: /Schedule a demo/i })
    ).toBeInTheDocument();
  });

  it('renders a footer with WarpSense and legal links', () => {
    render(<LandingPage />);
    expect(screen.getAllByText(/WarpSense/).length).toBeGreaterThanOrEqual(1);
    expect(screen.getByRole('link', { name: /^Privacy$/i })).toHaveAttribute(
      'href',
      '/privacy'
    );
    expect(screen.getByRole('link', { name: /^Terms$/i })).toHaveAttribute(
      'href',
      '/terms'
    );
  });
});
