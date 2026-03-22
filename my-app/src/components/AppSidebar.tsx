"use client";
/**
 * AppSidebar — collapsible left navigation for the (app) layout.
 * Replaces AppNav. Collapse state persisted in localStorage.
 *
 * Primary nav:  Analysis, Overview (was: Dashboard + Defects), AI Assist
 * Footer nav:   Thresholds
 * Design tokens: --warp-* from globals.css. No new colours.
 */
import { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

const PRIMARY_NAV = [
  { href: "/analysis",  label: "Analysis",  icon: "◈" },
  { href: "/dashboard", label: "Overview",  icon: "▦" },
  { href: "/ai",        label: "AI Assist", icon: "◇" },
] as const;

const FOOTER_NAV = [
  { href: "/admin/thresholds", label: "Thresholds", icon: "⚙" },
] as const;

const LS_KEY = "warp-sidebar-collapsed";

export function AppSidebar() {
  const pathname  = usePathname();
  const [collapsed, setCollapsed] = useState(false);

  // Hydrate from localStorage after mount — avoids SSR/hydration mismatch.
  useEffect(() => {
    try {
      if (localStorage.getItem(LS_KEY) === "true") setCollapsed(true);
    } catch { /* localStorage blocked in sandboxed contexts */ }
  }, []);

  const toggle = () => {
    setCollapsed((prev) => {
      const next = !prev;
      try { localStorage.setItem(LS_KEY, String(next)); } catch { /* ignore */ }
      return next;
    });
  };

  const itemClass = (href: string) => {
    const active = pathname === href || pathname.startsWith(href + "/");
    return [
      "flex items-center gap-3 px-2 h-9 rounded -ml-px",
      "font-mono text-[10px] uppercase tracking-widest",
      "transition-colors duration-100",
      active
        ? "bg-[var(--warp-surface-2)] text-[var(--warp-amber)] border-l-2 border-[var(--warp-amber)]"
        : "text-[var(--warp-text-muted)] border-l-2 border-transparent hover:bg-[var(--warp-surface-2)] hover:text-[var(--warp-text)]",
    ].join(" ");
  };

  return (
    <aside
      className={[
        "flex flex-col h-full shrink-0 overflow-hidden",
        "border-r border-[var(--warp-border)] bg-[var(--warp-surface)]",
        "transition-[width] duration-200",
        collapsed ? "w-14" : "w-[220px]",
      ].join(" ")}
      style={{ fontFamily: "var(--font-warp-mono), monospace" }}
      aria-label="Main navigation"
    >
      {/* Brand */}
      <Link
        href="/analysis"
        title="WarpSense"
        className="flex items-center gap-3 px-3 h-11 shrink-0 border-b border-[var(--warp-border)] hover:bg-[var(--warp-surface-2)] transition-colors duration-100"
      >
        <span className="text-[var(--warp-amber)] text-[14px] shrink-0 w-4 text-center leading-none">◈</span>
        {!collapsed && (
          <span className="font-mono text-[10px] uppercase tracking-widest text-[var(--warp-text-muted)] whitespace-nowrap">
            WarpSense
          </span>
        )}
      </Link>

      {/* Primary nav */}
      <nav className="flex-1 py-2 px-2 flex flex-col gap-0.5 overflow-hidden">
        {PRIMARY_NAV.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            title={collapsed ? item.label : undefined}
            className={itemClass(item.href)}
          >
            <span className="text-[12px] shrink-0 w-4 text-center leading-none">{item.icon}</span>
            {!collapsed && <span className="truncate">{item.label}</span>}
          </Link>
        ))}
      </nav>

      {/* Footer: admin + collapse toggle */}
      <div className="border-t border-[var(--warp-border)] py-2 px-2 flex flex-col gap-0.5">
        {FOOTER_NAV.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            title={collapsed ? item.label : undefined}
            className={[
              "flex items-center gap-3 px-2 h-8 rounded",
              "font-mono text-[10px] uppercase tracking-widest",
              "transition-colors duration-100",
              pathname.startsWith(item.href)
                ? "text-[var(--warp-amber)]"
                : "text-[var(--warp-text-dim)] hover:text-[var(--warp-text-muted)]",
            ].join(" ")}
          >
            <span className="text-[11px] shrink-0 w-4 text-center leading-none">{item.icon}</span>
            {!collapsed && <span className="truncate">{item.label}</span>}
          </Link>
        ))}

        <button
          type="button"
          onClick={toggle}
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          className="flex items-center gap-3 px-2 h-8 rounded w-full font-mono text-[10px] uppercase tracking-widest text-[var(--warp-text-dim)] hover:text-[var(--warp-text-muted)] transition-colors duration-100"
        >
          <span className="text-[12px] shrink-0 w-4 text-center leading-none select-none">
            {collapsed ? "›" : "‹"}
          </span>
          {!collapsed && <span>Collapse</span>}
        </button>
      </div>
    </aside>
  );
}
