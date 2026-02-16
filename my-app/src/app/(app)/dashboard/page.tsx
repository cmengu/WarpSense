'use client';

import { useEffect, useState } from 'react';
import { DashboardLayout } from '@/components/dashboard/DashboardLayout';
import { ErrorBoundary } from '@/components/ErrorBoundary';
import { fetchDashboardData } from '@/lib/api';
import type { DashboardData } from '@/types/dashboard';

export default function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchDashboardData()
      .then((d) => {
        if (!cancelled) setData(d);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : String(err));
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // Loading state - show simple loading message
  if (loading) {
    return (
      <div className="min-h-screen bg-zinc-50 dark:bg-black flex items-center justify-center">
        <div className="text-center">
          <div className="text-lg text-zinc-600 dark:text-zinc-400 mb-2">
            Loading dashboard...
          </div>
          <div className="text-sm text-zinc-500 dark:text-zinc-500 mb-6">
            Fetching data from backend
          </div>
          <a
            href="/demo"
            className="text-sm text-blue-500 hover:text-blue-400 underline"
          >
            Try demo (no backend required)
          </a>
        </div>
      </div>
    );
  }

  // Error state - show error message with retry option
  if (error) {
    return (
      <div className="min-h-screen bg-zinc-50 dark:bg-black flex items-center justify-center p-6">
        <div className="max-w-md w-full bg-white dark:bg-zinc-900 rounded-lg border border-violet-200 dark:border-violet-800 p-6">
          <h2 className="text-lg font-semibold text-violet-800 dark:text-violet-400 mb-2">
            Failed to load dashboard
          </h2>
          <p className="text-sm text-violet-600 dark:text-violet-500 mb-4">
            {error}
          </p>
          <p className="text-xs text-zinc-500 dark:text-zinc-400 mb-4">
            Make sure the FastAPI backend is running on http://localhost:8000
          </p>
          <div className="flex flex-col sm:flex-row gap-3">
            <button
              onClick={() => {
                setError(null);
                setLoading(true);
                fetchDashboardData()
                  .then(setData)
                  .catch((err) =>
                    setError(err instanceof Error ? err.message : String(err))
                  )
                  .finally(() => setLoading(false));
              }}
              className="px-4 py-2 bg-violet-600 text-white rounded hover:bg-violet-700 transition-colors"
            >
              Retry
            </button>
            <a
              href="/demo"
              className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors text-center"
            >
              Try demo (no backend required)
            </a>
          </div>
        </div>
      </div>
    );
  }

  // No data state (shouldn't happen, but handle it gracefully)
  if (!data) {
    return (
      <div className="min-h-screen bg-zinc-50 dark:bg-black flex items-center justify-center">
        <div className="text-center">
          <p className="text-zinc-500 dark:text-zinc-400 mb-6">
            No data available
          </p>
          <a
            href="/demo"
            className="text-sm text-blue-500 hover:text-blue-400 underline"
          >
            Try demo (no backend required)
          </a>
        </div>
      </div>
    );
  }

  // Success state - render dashboard with data
  return (
    <ErrorBoundary>
      <div>
        <DashboardLayout data={data} />

        {/* Welding Sessions List */}
        <div className="min-h-screen bg-zinc-50 dark:bg-black p-6">
          <div className="max-w-7xl mx-auto mt-8">
            {/* Demo CTA — zero-setup, shareable link for prospects */}
            <a
              href="/demo"
              className="block mb-8 p-6 bg-blue-950/30 dark:bg-blue-950/20 border-2 border-blue-500 rounded-lg hover:border-blue-400 transition-colors"
            >
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-xl font-bold text-blue-400 mb-1">
                    Live Demo — Zero Setup
                  </h2>
                  <p className="text-sm text-zinc-500 dark:text-zinc-400">
                    Side-by-side expert vs novice replay. No backend required.
                    Works on any device. Shareable link for prospects.
                  </p>
                </div>
                <span className="text-blue-400 font-medium">View Demo →</span>
              </div>
            </a>

            <h2 className="text-2xl font-semibold mb-4 text-black dark:text-zinc-50">
              Welding Sessions
            </h2>
            <div className="space-y-2">
              <div className="text-sm text-zinc-500 dark:text-zinc-400 mb-4">
                Mock sessions for development (seed via: curl -X POST
                http://localhost:8000/api/dev/seed-mock-sessions)
              </div>
              {[
                { id: 'sess_expert_001', label: 'Expert' },
                { id: 'sess_novice_001', label: 'Novice' },
              ].map(({ id, label }) => (
                <a
                  key={id}
                  href={`/replay/${id}`}
                  className="block p-4 bg-white dark:bg-zinc-900 rounded-lg border border-zinc-200 dark:border-zinc-800 hover:border-zinc-300 dark:hover:border-zinc-700 transition-colors"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-black dark:text-zinc-50">
                      {label} ({id})
                    </span>
                    <span className="text-xs text-zinc-500 dark:text-zinc-400">
                      (mock)
                    </span>
                  </div>
                </a>
              ))}
            </div>
          </div>
        </div>
      </div>
    </ErrorBoundary>
  );
}
