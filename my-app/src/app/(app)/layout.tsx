/**
 * App layout — wraps children with AppNav.
 * Used for dashboard, replay, compare, defects, ai, and other app routes.
 */

import { AppNav } from '@/components/AppNav';

export default function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <>
      <AppNav />
      {children}
    </>
  );
}
