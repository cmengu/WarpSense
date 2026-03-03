"use client";

import { useEffect, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { SessionBrowserPanel } from "@/components/SessionBrowserPanel";

const DEFAULT_SESSION_A = "sess_novice_aluminium_001_001";
const DEFAULT_SESSION_B = "sess_expert_aluminium_001_001";

function DemoLandingInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const autostart = searchParams.get("autostart") === "true";

  useEffect(() => {
    if (autostart) {
      router.replace(`/demo/${DEFAULT_SESSION_A}/${DEFAULT_SESSION_B}`);
    }
  }, [autostart, router]);

  if (autostart) {
    return (
      <div className="min-h-screen bg-zinc-950 flex items-center justify-center">
        <p className="text-zinc-500 text-xs font-mono tracking-widest animate-pulse">
          Redirecting to demo…
        </p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-zinc-950 flex flex-col items-center justify-center px-4 py-12">
      <div className="w-full max-w-3xl mb-6">
        <p className="text-[9px] uppercase tracking-[0.35em] text-zinc-600 font-mono mb-1">
          WELDVIEW SYS v1.0
        </p>
        <h1 className="text-xl font-bold text-zinc-100 font-mono tracking-tight">
          Compare Welding Sessions
        </h1>
        <p className="text-zinc-500 text-xs font-mono mt-1">
          Select any two sessions below to analyse side-by-side.
        </p>
      </div>
      <div className="w-full max-w-3xl">
        <SessionBrowserPanel navigateTo="demo" />
      </div>
      <p className="mt-6 text-[10px] font-mono text-zinc-700">
        or{" "}
        <a
          href={`/demo/${DEFAULT_SESSION_A}/${DEFAULT_SESSION_B}`}
          className="underline underline-offset-2 hover:text-zinc-400 transition-colors"
        >
          jump straight to the aluminium demo →
        </a>
      </p>
    </div>
  );
}

export default function DemoLandingPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-zinc-950 flex items-center justify-center">
          <p className="text-zinc-500 text-xs font-mono tracking-widest animate-pulse">
            Loading…
          </p>
        </div>
      }
    >
      <DemoLandingInner />
    </Suspense>
  );
}
