"use client";

/**
 * Demo Team Dashboard — Browser-only team view.
 *
 * Shows welder cards from DEMO_WELDERS (config-driven).
 * No fetchSession/fetchScore. Data from getDemoTeamData.
 */

import Link from "next/link";
import { DEMO_WELDERS } from "@/lib/seagull-demo-data";

export default function DemoTeamDashboardPage() {
  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-black p-8">
      <div className="max-w-4xl">
        <h1 className="text-2xl font-bold text-zinc-900 dark:text-zinc-100 mb-6">
          Team Dashboard — Demo
        </h1>
        <div className="grid gap-4 sm:grid-cols-2">
          {DEMO_WELDERS.map((welder) => (
            <Link
              key={welder.id}
              href={`/demo/team/${welder.id}`}
              className="block p-6 bg-white dark:bg-zinc-900 rounded-lg shadow border border-zinc-200 dark:border-zinc-800 hover:border-blue-500 transition-colors"
            >
              <h2 className="text-lg font-semibold text-zinc-900 dark:text-zinc-100">
                {welder.name}
              </h2>
              <p className="mt-2 text-sm">
                <span className="font-bold text-blue-600 dark:text-blue-400">
                  {welder.score}/100
                </span>
              </p>
              <p className="mt-1 text-xs text-zinc-500 dark:text-zinc-400">
                View report →
              </p>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
