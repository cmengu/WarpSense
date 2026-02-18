export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950 p-6">
      <nav className="mb-6 flex gap-4">
        <a
          href="/admin/thresholds"
          className="text-blue-600 dark:text-blue-400 hover:underline"
        >
          Thresholds
        </a>
        <a
          href="/"
          className="text-zinc-600 dark:text-zinc-400 hover:underline"
        >
          ← App
        </a>
      </nav>
      {children}
    </div>
  );
}
