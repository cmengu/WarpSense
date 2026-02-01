'use client';

import { useEffect, useState } from 'react';
import { DashboardLayout } from '@/components/dashboard/DashboardLayout';
import { ErrorBoundary } from '@/components/ErrorBoundary';
import { fetchDashboardData } from '@/lib/api';
import type { DashboardData } from '@/types/dashboard';

export default function Home() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Fetch dashboard data from FastAPI backend on component mount
    // Backend is the single source of truth - no fallback mock data
    fetchDashboardData()
      .then(setData)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  // Loading state - show simple loading message
  if (loading) {
    return (
      <div className="min-h-screen bg-zinc-50 dark:bg-black flex items-center justify-center">
        <div className="text-center">
          <div className="text-lg text-zinc-600 dark:text-zinc-400 mb-2">
            Loading dashboard...
          </div>
          <div className="text-sm text-zinc-500 dark:text-zinc-500">
            Fetching data from backend
          </div>
        </div>
      </div>
    );
  }

  // Error state - show error message with retry option
  if (error) {
    return (
      <div className="min-h-screen bg-zinc-50 dark:bg-black flex items-center justify-center p-6">
        <div className="max-w-md w-full bg-white dark:bg-zinc-900 rounded-lg border border-red-200 dark:border-red-800 p-6">
          <h2 className="text-lg font-semibold text-red-800 dark:text-red-400 mb-2">
            Failed to load dashboard
          </h2>
          <p className="text-sm text-red-600 dark:text-red-500 mb-4">
            {error}
          </p>
          <p className="text-xs text-zinc-500 dark:text-zinc-400 mb-4">
            Make sure the FastAPI backend is running on http://localhost:8000
          </p>
          <button
            onClick={() => {
              setError(null);
              setLoading(true);
              fetchDashboardData()
                .then(setData)
                .catch((err) => setError(err.message))
                .finally(() => setLoading(false));
            }}
            className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  // No data state (shouldn't happen, but handle it gracefully)
  if (!data) {
    return (
      <div className="min-h-screen bg-zinc-50 dark:bg-black flex items-center justify-center">
        <div className="text-center text-zinc-500 dark:text-zinc-400">
          No data available
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
            <h2 className="text-2xl font-semibold mb-4 text-black dark:text-zinc-50">
              Welding Sessions
            </h2>
            <div className="space-y-2">
              <div className="text-sm text-zinc-500 dark:text-zinc-400 mb-4">
                Mock sessions for development
              </div>
              {['a1b2c3', 'd4e5f6'].map((sessionId) => (
                <a
                  key={sessionId}
                  href={`/replay/${sessionId}`}
                  className="block p-4 bg-white dark:bg-zinc-900 rounded-lg border border-zinc-200 dark:border-zinc-800 hover:border-zinc-300 dark:hover:border-zinc-700 transition-colors"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-black dark:text-zinc-50">
                      Session {sessionId}
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
