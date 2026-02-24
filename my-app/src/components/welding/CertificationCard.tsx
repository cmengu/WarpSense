"use client";

import React, { useEffect, useState } from "react";
import {
  WelderCertificationSummary,
  CertificationStatusItem,
} from "@/types/certification";
import type { CertificationStatus, WelderID } from "@/types/shared";
import { fetchCertificationStatus } from "@/lib/api";
import { logError } from "@/lib/logger";

interface CertificationCardProps {
  welderId: WelderID;
}

const STATUS_STYLES: Record<
  CertificationStatus,
  { badge: string; bar: string; icon: string }
> = {
  certified: {
    badge: "bg-green-500/10 text-green-400 border-green-500/30",
    bar: "bg-green-500",
    icon: "✓",
  },
  on_track: {
    badge: "bg-cyan-500/10 text-cyan-400 border-cyan-500/30",
    bar: "bg-cyan-500",
    icon: "→",
  },
  at_risk: {
    badge: "bg-red-500/10 text-red-400 border-red-500/30",
    bar: "bg-red-500",
    icon: "⚠",
  },
  not_started: {
    badge: "bg-neutral-800 text-neutral-500 border-neutral-700",
    bar: "bg-neutral-700",
    icon: "○",
  },
};

function CertRow({ item }: { item: CertificationStatusItem }) {
  const styles = STATUS_STYLES[item.status];
  const progress = Math.min(
    100,
    (item.qualifying_sessions / item.cert_standard.sessions_required) * 100
  );

  return (
    <div className="py-3 border-b border-neutral-800 last:border-0">
      <div className="flex items-center justify-between mb-2">
        <div>
          <p className="text-sm font-medium text-white">
            {item.cert_standard.name}
          </p>
          <p className="text-xs text-neutral-500 mt-0.5">
            Score ≥ {item.cert_standard.required_score} ·{" "}
            {item.cert_standard.sessions_required} sessions
          </p>
        </div>
        <span
          className={`text-xs font-semibold uppercase px-2 py-0.5
                         rounded border ${styles.badge}`}
        >
          {styles.icon} {item.status.replace("_", " ")}
        </span>
      </div>
      <div className="h-1.5 bg-neutral-800 rounded-full overflow-hidden mb-1.5">
        <div
          className={`h-full rounded-full transition-all ${styles.bar}`}
          style={{ width: `${progress}%` }}
        />
      </div>
      <div className="flex justify-between text-xs text-neutral-600">
        <span>
          {item.qualifying_sessions}/
          {item.cert_standard.sessions_required} qualifying sessions
        </span>
        {item.status === "certified" ? (
          <span className="text-green-400">Certified</span>
        ) : item.sessions_to_target ? (
          <span>~{item.sessions_to_target} sessions to cert</span>
        ) : item.current_avg_score ? (
          <span>Avg: {item.current_avg_score}/100</span>
        ) : null}
      </div>
    </div>
  );
}

export function CertificationCard({ welderId }: CertificationCardProps) {
  const [summary, setSummary] =
    useState<WelderCertificationSummary | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    fetchCertificationStatus(welderId)
      .then((s) => {
        if (mounted) {
          setSummary(s);
          setLoading(false);
        }
      })
      .catch((err) => {
        logError("CertificationCard", err);
        if (mounted) setLoading(false);
      });
    return () => {
      mounted = false;
    };
  }, [welderId]);

  return (
    <div className="rounded-lg border border-neutral-800 bg-neutral-900 p-6">
      <h2
        className="text-sm font-semibold uppercase tracking-widest
                     text-neutral-400 mb-4"
      >
        Certification Readiness
      </h2>
      {loading && (
        <div className="h-32 bg-neutral-800 rounded animate-pulse" />
      )}
      {!loading && !summary && (
        <p className="text-sm text-neutral-500">
          Unable to load certification data.
        </p>
      )}
      {!loading && summary && (
        <div>
          {summary.certifications.map((item) => (
            <CertRow key={item.cert_standard.id} item={item} />
          ))}
        </div>
      )}
    </div>
  );
}

export default CertificationCard;
