/**
 * App layout — wraps children with AppNav.
 * Used for dashboard, demo, replay, compare, and other app routes.
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
