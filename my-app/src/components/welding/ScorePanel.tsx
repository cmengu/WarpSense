'use client';

import { useEffect, useState } from 'react';
import { fetchScore, type SessionScore } from '@/lib/api';

/**
 * ScorePanel Component
 * Fetches and displays rule-based scoring feedback for a welding session.
 *
 * States: loading, error, success.
 * Renders total (e.g. 100/100), per-rule ✓/✗ with threshold and actual_value.
 *
 * @param sessionId - Session ID to display score for
 */
interface ScorePanelProps {
  sessionId: string;
}

export default function ScorePanel({ sessionId }: ScorePanelProps) {
  const [score, setScore] = useState<SessionScore | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!sessionId) {
      setLoading(false);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError(null);
    setScore(null);

    fetchScore(sessionId)
      .then((data) => {
        if (!cancelled) {
          setScore(data);
          setError(null);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : String(err));
          setScore(null);
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [sessionId]);

  return (
    <div className="score-panel-container bg-white dark:bg-zinc-900 rounded-lg border border-zinc-200 dark:border-zinc-800 p-6">
      <h3 className="text-lg font-semibold mb-4 text-black dark:text-zinc-50">
        Scoring Feedback
      </h3>

      {loading && (
        <div className="text-zinc-500 dark:text-zinc-400 min-h-[120px] flex items-center justify-center border border-dashed border-zinc-300 dark:border-zinc-700 rounded">
          <p className="text-sm">Loading score...</p>
        </div>
      )}

      {error && !loading && (
        <div className="min-h-[120px] flex items-center justify-center border border-red-200 dark:border-red-800 rounded bg-red-50 dark:bg-red-950/30 p-4">
          <p className="text-sm text-red-700 dark:text-red-400">
            Failed to load score: {error}
          </p>
        </div>
      )}

      {score && !loading && !error && (
        <div className="space-y-4">
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold text-black dark:text-zinc-50">
              {score.total}/100
            </span>
          </div>
          {score.active_threshold_spec && (
            <p className="text-sm text-zinc-500 dark:text-zinc-400 mt-2">
              Evaluated against{' '}
              {score.active_threshold_spec.weld_type.toUpperCase()} spec —
              Target {score.active_threshold_spec.angle_target}° ±
              {score.active_threshold_spec.angle_warning}°
            </p>
          )}

          <ul className="space-y-2" role="list" aria-label="Scoring rules">
            {score.rules.map((rule) => (
              <li
                key={rule.rule_id}
                className="flex items-center justify-between gap-3 py-2 px-3 rounded bg-zinc-50 dark:bg-zinc-800/50 text-sm"
              >
                <div className="flex items-center gap-2">
                  <span
                    className={
                      rule.passed
                        ? 'text-green-600 dark:text-green-400'
                        : 'text-red-600 dark:text-red-400'
                    }
                    aria-label={rule.passed ? 'Passed' : 'Failed'}
                  >
                    {rule.passed ? '✓' : '✗'}
                  </span>
                  <span className="font-medium text-zinc-700 dark:text-zinc-300 capitalize">
                    {rule.rule_id.replace(/_/g, ' ')}
                  </span>
                </div>
                <div className="text-zinc-500 dark:text-zinc-400">
                  {rule.actual_value != null ? (
                    <>
                      <span className="tabular-nums">
                        {rule.actual_value.toFixed(2)}
                      </span>
                      {' / '}
                      <span className="tabular-nums">{rule.threshold}</span>
                    </>
                  ) : (
                    <span className="tabular-nums">{rule.threshold}</span>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
