'use client';

import type { ReactNode } from 'react';
import { ErrorBoundary } from '@/components/ErrorBoundary';

/**
 * Client wrapper for demo layout — ErrorBoundary with refresh fallback.
 * "Try again" cannot recover session-generation failure (useState init throws);
 * only a full page refresh works.
 */
const DEMO_ERROR_FALLBACK = (
  <div className="min-h-screen flex items-center justify-center bg-neutral-950 p-8">
    <div className="p-8 bg-violet-50 dark:bg-violet-900/20 border border-violet-200 dark:border-violet-800 rounded-lg max-w-md">
      <h2 className="text-lg font-semibold text-violet-800 dark:text-violet-400 mb-2">
        Demo failed to load
      </h2>
      <p className="text-sm text-violet-600 dark:text-violet-500 mb-4">
        Session data could not be generated. Please refresh the page.
      </p>
      <button
        type="button"
        onClick={() => typeof window !== 'undefined' && window.location.reload()}
        className="px-4 py-2 bg-violet-600 text-white rounded hover:bg-violet-700 transition-colors"
      >
        Refresh page
      </button>
    </div>
  </div>
);

export function DemoLayoutClient({ children }: { children: ReactNode }) {
  return <ErrorBoundary fallback={DEMO_ERROR_FALLBACK}>{children}</ErrorBoundary>;
}
