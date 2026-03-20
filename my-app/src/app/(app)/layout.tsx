/**
 * App layout — wraps children with AppNav.
 *
 * Grid: row 1 = nav (auto height), row 2 = remaining viewport (`1fr`).
 * The content row uses `min-h-0` so nested flex children can scroll correctly.
 * Route pages that need full below-nav height should use `h-full min-h-0 flex flex-col`
 * instead of `calc(100vh - <nav px>)`.
 */

import { AppNav } from '@/components/AppNav';

export default function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-dvh grid grid-rows-[auto_1fr]">
      <AppNav />
      <div className="min-h-0 flex h-full min-w-0 flex-col overflow-y-auto">
        {children}
      </div>
    </div>
  );
}
