/**
 * Marketing layout — no AppNav.
 * Serves the WarpSense investor/customer landing at / and other marketing routes.
 */

import type { Metadata } from 'next';

const DESCRIPTION =
  'WarpSense is a clip-on sensor system that monitors five structural parameters in real time during the weld — delivering a pass-or-flag verdict the moment the joint is finished, before any inspector walks over.';

export const metadata: Metadata = {
  title: 'WarpSense — AI-Powered Weld Intelligence',
  description: DESCRIPTION,
  openGraph: {
    title: 'WarpSense — AI-Powered Weld Intelligence',
    description: DESCRIPTION,
    type: 'website',
    siteName: 'WarpSense',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'WarpSense — AI-Powered Weld Intelligence',
    description: DESCRIPTION,
  },
};

export default function MarketingLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
}
