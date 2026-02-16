import type { Metadata } from 'next';

/**
 * Landing page layout — shareable metadata for investor links.
 * AppNav is omitted for /landing; (marketing) routes use MarketingLayout at /.
 * This layout serves the legacy /landing path that re-exports (marketing)/page.
 */

export const metadata: Metadata = {
  title: 'WeldVision — The Future of Industrial Training',
  description:
    'Real-time thermal analytics and AI-powered feedback transforming skilled labor training in heavy industry. 87% training reduction, $2.4M savings per facility.',
  openGraph: {
    title: 'WeldVision — The Future of Industrial Training',
    description:
      'Real-time thermal analytics and AI-powered feedback transforming skilled labor training in heavy industry.',
    type: 'website',
  },
};

export default function LandingLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
}
