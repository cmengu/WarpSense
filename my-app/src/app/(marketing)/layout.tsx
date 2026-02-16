/**
 * Marketing layout — no AppNav.
 * Used for landing page at / and future marketing routes (about, contact).
 */

import type { Metadata } from 'next';

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

export default function MarketingLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
}
