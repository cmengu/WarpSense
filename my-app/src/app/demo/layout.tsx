import type { Metadata } from 'next';
import type { ReactNode } from 'react';
import { DemoLayoutClient } from './DemoLayoutClient';

/**
 * Demo route layout — shareable metadata for prospects and LinkedIn.
 *
 * og:title and description enable rich link previews when sharing
 * https://yoursite.com/demo on social or in emails.
 *
 * Wraps children in ErrorBoundary (via DemoLayoutClient) to catch session
 * generation or render failures. Fallback uses "Refresh page" because
 * session-generation failure in useState cannot be recovered by remounting.
 */

export const metadata: Metadata = {
  title: 'Live Demo — WarpSense',
  description:
    'Side-by-side expert vs novice welding replay. Zero setup, no backend. Real-time quality analysis for industrial training. Shareable link.',
  openGraph: {
    title: 'Live Demo — WarpSense',
    description:
      'Side-by-side expert vs novice welding replay. Zero setup. Real-time quality analysis.',
    type: 'website',
  },
};

export default function DemoLayout({ children }: { children: ReactNode }) {
  return <DemoLayoutClient>{children}</DemoLayoutClient>;
}
