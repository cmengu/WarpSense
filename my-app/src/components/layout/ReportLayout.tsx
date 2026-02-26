/**
 * ReportLayout — slot-based layout for welder report page.
 *
 * RULES:
 * - Never add feature logic here
 * - Never remove a slot — only add new ones
 * - All slots are optional — absent slots render nothing
 * - Page owns theme (zinc/blue); ReportLayout is structural only
 * - thresholdSpec renders in header right column for layout parity
 */
import React from "react";
import type { SessionID } from "@/types/shared";

/**
 * Slot-based layout for welder report pages. Renders header (name, score, threshold)
 * and optional slots: narrative, heatmaps, feedback, progress, trajectory,
 * benchmarks, coaching, certification, actions.
 */
export interface ReportLayoutProps {
  welderName: string;
  sessionId: SessionID;
  scoreTotal: number;
  weldType?: string;
  sessionDate?: string;
  skillLevel?: string;
  trend?: string;
  thresholdSpec?: React.ReactNode;

  backLink?: React.ReactNode;
  narrative?: React.ReactNode;
  compliance?: React.ReactNode;
  heatmaps?: React.ReactNode;
  feedback?: React.ReactNode;
  progress?: React.ReactNode;
  trajectory?: React.ReactNode;
  benchmarks?: React.ReactNode;
  coaching?: React.ReactNode;
  certification?: React.ReactNode;
  actions?: React.ReactNode;
}

export function ReportLayout({
  welderName,
  sessionId,
  scoreTotal,
  weldType,
  sessionDate,
  skillLevel,
  trend,
  thresholdSpec,
  backLink,
  narrative,
  compliance,
  heatmaps,
  feedback,
  progress,
  trajectory,
  benchmarks,
  coaching,
  certification,
  actions,
}: ReportLayoutProps) {
  const showSkillTrend = [skillLevel, trend].filter(Boolean).join(" • ");

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-black p-8">
      {backLink && <div className="mb-4">{backLink}</div>}

      <div className="bg-white dark:bg-zinc-900 rounded-lg shadow p-6 mb-8">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-bold">
              {welderName} — Weekly Report
            </h1>
            {weldType && (
              <span className="text-sm text-zinc-600 dark:text-zinc-400 ml-2">
                {weldType.toUpperCase()}
              </span>
            )}
            {sessionDate && (
              <span className="text-sm text-zinc-600 dark:text-zinc-400 ml-2">
                {sessionDate}
              </span>
            )}
          </div>
          <div className="text-right">
            <div className="text-5xl font-bold text-blue-600">
              {scoreTotal}/100
            </div>
            {showSkillTrend && (
              <div
                className="text-sm text-zinc-600 dark:text-zinc-400"
                data-testid="report-header-trend"
              >
                {showSkillTrend}
              </div>
            )}
            {thresholdSpec && (
              <div
                className="text-sm text-zinc-600 dark:text-zinc-400 mt-1"
                data-testid="header-threshold"
              >
                {thresholdSpec}
              </div>
            )}
          </div>
        </div>
        {narrative && (
          <div className="mt-4" data-testid="report-narrative">
            {narrative}
          </div>
        )}
      </div>

      <div className="space-y-8">
        {compliance && (
          <section aria-label="Compliance">{compliance}</section>
        )}
        {heatmaps && (
          <section aria-label="Thermal Heatmaps">{heatmaps}</section>
        )}
        {feedback && (
          <section aria-label="Detailed Feedback">{feedback}</section>
        )}
        {progress && (
          <section
            aria-label="Progress Over Time"
            data-testid="progress-slot"
          >
            {progress}
          </section>
        )}
        {trajectory && (
          <section aria-label="Skill Trajectory">{trajectory}</section>
        )}
        {benchmarks && (
          <section aria-label="Benchmark Comparison">{benchmarks}</section>
        )}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {coaching && (
            <section aria-label="Coaching Plan">{coaching}</section>
          )}
          {certification && (
            <section aria-label="Certification Status">{certification}</section>
          )}
        </div>
        {actions && (
          <section aria-label="Actions" className="flex flex-col gap-4">
            {actions}
          </section>
        )}
      </div>
    </div>
  );
}

export default ReportLayout;
