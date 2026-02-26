/**
 * SiteSelector — site/team dropdown for supervisor dashboard.
 * Stores selection in URL search params (?site=X&team=Y).
 * Co-equal with date range for filtering; placed left of date controls.
 */
"use client";

import React, { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import type { Site } from "@/types/site";
import { fetchSites } from "@/lib/api";

export function SiteSelector() {
  const router = useRouter();
  const params = useSearchParams();
  const [sites, setSites] = useState<Site[]>([]);

  useEffect(() => {
    fetchSites().then(setSites).catch(() => {});
  }, []);

  const currentSite = params.get("site") ?? "";
  const currentTeam = params.get("team") ?? "";
  const selectedSite = sites.find((s) => s.id === currentSite);

  const update = (site: string, team: string) => {
    const p = new URLSearchParams(params.toString());
    if (site) p.set("site", site);
    else p.delete("site");
    if (team) p.set("team", team);
    else p.delete("team");
    router.push(`?${p.toString()}`);
  };

  if (sites.length === 0) return null;

  return (
    <div className="flex items-center gap-2" role="group" aria-label="Site and team filter">
      <select
        value={currentSite}
        onChange={(e) => update(e.target.value, "")}
        className="bg-zinc-200 dark:bg-zinc-700 border border-zinc-300 dark:border-zinc-600 rounded px-3 py-1.5 text-sm text-zinc-900 dark:text-zinc-100 hover:bg-zinc-300 dark:hover:bg-zinc-600"
      >
        <option value="">All Sites</option>
        {sites.map((s) => (
          <option key={s.id} value={s.id}>
            {s.name}
          </option>
        ))}
      </select>

      {selectedSite && selectedSite.teams.length > 0 && (
        <select
          value={currentTeam}
          onChange={(e) => update(currentSite, e.target.value)}
          className="bg-zinc-200 dark:bg-zinc-700 border border-zinc-300 dark:border-zinc-600 rounded px-3 py-1.5 text-sm text-zinc-900 dark:text-zinc-100 hover:bg-zinc-300 dark:hover:bg-zinc-600"
        >
          <option value="">All Teams</option>
          {selectedSite.teams.map((t) => (
            <option key={t.id} value={t.id}>
              {t.name}
            </option>
          ))}
        </select>
      )}
    </div>
  );
}
