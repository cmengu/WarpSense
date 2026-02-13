'use client';

import { useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { Suspense, useState } from 'react';

/**
 * Compare landing page: choose two session IDs and go to the comparison view.
 * Query param sessionA pre-fills the first input (e.g. from replay "Compare with…" link).
 */
function CompareForm() {
  const searchParams = useSearchParams();
  const sessionAFromQuery = searchParams.get('sessionA') ?? '';
  const [sessionIdA, setSessionIdA] = useState(sessionAFromQuery);
  const [sessionIdB, setSessionIdB] = useState('');

  const canCompare =
    sessionIdA.trim().length > 0 && sessionIdB.trim().length > 0;
  const compareHref = canCompare
    ? `/compare/${encodeURIComponent(sessionIdA.trim())}/${encodeURIComponent(sessionIdB.trim())}`
    : '#';

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-black p-6">
      <div className="max-w-md mx-auto">
        <Link
          href="/"
          className="text-sm text-zinc-500 dark:text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-300 mb-4 inline-block"
        >
          Dashboard
        </Link>
        <h1 className="text-2xl font-semibold mb-2 text-black dark:text-zinc-50">
          Compare two sessions
        </h1>
        <p className="text-sm text-zinc-600 dark:text-zinc-400 mb-6">
          Enter two session IDs to view side-by-side heatmaps and the temperature delta (A − B).
        </p>
        <form
          className="space-y-4"
          onSubmit={(e) => {
            e.preventDefault();
            if (canCompare) {
              window.location.href = compareHref;
            }
          }}
        >
          <div>
            <label
              htmlFor="session-a"
              className="block text-sm font-medium text-zinc-700 dark:text-zinc-300 mb-1"
            >
              Session A
            </label>
            <input
              id="session-a"
              type="text"
              value={sessionIdA}
              onChange={(e) => setSessionIdA(e.target.value)}
              placeholder="e.g. sess_expert_001"
              className="w-full px-3 py-2 rounded-md border border-zinc-300 dark:border-zinc-600 bg-white dark:bg-zinc-900 text-black dark:text-zinc-100 placeholder:text-zinc-400"
            />
          </div>
          <div>
            <label
              htmlFor="session-b"
              className="block text-sm font-medium text-zinc-700 dark:text-zinc-300 mb-1"
            >
              Session B
            </label>
            <input
              id="session-b"
              type="text"
              value={sessionIdB}
              onChange={(e) => setSessionIdB(e.target.value)}
              placeholder="e.g. sess_novice_001"
              className="w-full px-3 py-2 rounded-md border border-zinc-300 dark:border-zinc-600 bg-white dark:bg-zinc-900 text-black dark:text-zinc-100 placeholder:text-zinc-400"
            />
          </div>
          <Link
            href={compareHref}
            className={`inline-block px-4 py-2 rounded-md text-sm font-medium ${
              canCompare
                ? 'bg-blue-500 text-white hover:bg-blue-600'
                : 'bg-zinc-300 dark:bg-zinc-600 text-zinc-500 dark:text-zinc-400 cursor-not-allowed pointer-events-none'
            }`}
            aria-disabled={!canCompare}
          >
            Compare
          </Link>
        </form>
      </div>
    </div>
  );
}

export default function CompareIndexPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-zinc-50 dark:bg-black flex items-center justify-center">
          <div className="text-sm text-zinc-500">Loading...</div>
        </div>
      }
    >
      <CompareForm />
    </Suspense>
  );
}
