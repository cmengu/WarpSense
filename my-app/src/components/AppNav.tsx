/**
 * AppNav — Minimal global navigation for app routes.
 *
 * Renders only in (app) layout (dashboard, demo, replay, compare).
 * Landing at / has its own nav; AppNav is omitted via route groups.
 *
 * Home → / (landing), Dashboard → /dashboard, Demo → /demo
 */

'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

export function AppNav() {
  const pathname = usePathname();
  const isDashboard =
    pathname === '/dashboard' || pathname.startsWith('/dashboard');
  const isDemo = pathname === '/demo' || pathname.startsWith('/demo');
  const isTeam = pathname.startsWith('/seagull');
  const isSupervisor =
    pathname === '/supervisor' || pathname.startsWith('/supervisor');
  const isDefects =
    pathname === '/defects' || pathname.startsWith('/defects');
  const isAI = pathname === '/ai' || pathname.startsWith('/ai');
  const isRealtime = pathname === '/realtime' || pathname.startsWith('/realtime');

  return (
    <nav
      className="border-b border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 px-6 py-3"
      aria-label="Main navigation"
    >
      <div className="max-w-7xl mx-auto flex items-center gap-6">
        <Link
          href="/"
          className="text-sm font-medium text-zinc-700 dark:text-zinc-300 hover:text-zinc-900 dark:hover:text-zinc-100"
          aria-current={pathname === '/' ? 'page' : undefined}
        >
          Home
        </Link>
        <Link
          href="/dashboard"
          className="text-sm font-medium text-zinc-700 dark:text-zinc-300 hover:text-zinc-900 dark:hover:text-zinc-100"
          aria-current={isDashboard ? 'page' : undefined}
        >
          Dashboard
        </Link>
        <Link
          href="/demo"
          className="text-sm font-medium text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300"
          aria-current={isDemo ? 'page' : undefined}
        >
          Demo
        </Link>
        <Link
          href="/seagull"
          className="text-sm font-medium text-zinc-700 dark:text-zinc-300 hover:text-zinc-900 dark:hover:text-zinc-100"
          aria-current={isTeam ? 'page' : undefined}
        >
          Team
        </Link>
        <Link
          href="/supervisor"
          className="text-sm font-medium text-zinc-700 dark:text-zinc-300 hover:text-zinc-900 dark:hover:text-zinc-100"
          aria-current={isSupervisor ? 'page' : undefined}
        >
          Supervisor
        </Link>
        <Link
          href="/defects"
          className="text-sm font-medium text-zinc-700 dark:text-zinc-300 hover:text-zinc-900 dark:hover:text-zinc-100"
          aria-current={isDefects ? 'page' : undefined}
        >
          Defects
        </Link>
        <Link
          href="/realtime"
          className="text-sm font-medium text-zinc-700 dark:text-zinc-300 hover:text-zinc-900 dark:hover:text-zinc-100"
          aria-current={isRealtime ? 'page' : undefined}
        >
          Realtime
        </Link>
        <Link
          href="/ai"
          className="text-sm font-medium text-zinc-700 dark:text-zinc-300 hover:text-zinc-900 dark:hover:text-zinc-100"
          aria-current={isAI ? 'page' : undefined}
        >
          AI
        </Link>
      </div>
    </nav>
  );
}
