/**
 * App layout — wraps children with AppSidebar.
 *
 * Flex row: sidebar (fixed width) + content (flex-1, full height).
 * h-dvh + overflow-hidden on the root gives both sidebar and content
 * a bounded height so the analysis page's h-full children work correctly.
 * Content div keeps overflow-y-auto so dashboard / scroll-heavy pages work.
 */
import { AppSidebar } from "@/components/AppSidebar";

export default function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex h-dvh w-full overflow-hidden bg-[var(--warp-bg)]">
      <AppSidebar />
      <div className="flex-1 min-w-0 min-h-0 flex flex-col overflow-y-auto">
        {children}
      </div>
    </div>
  );
}
