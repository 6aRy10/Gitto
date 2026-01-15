"use client";

import React from "react";
import { Clock, Calendar, AlertCircle, CheckCircle2 } from "lucide-react";

// ═══════════════════════════════════════════════════════════════════════════════
// TYPES
// ═══════════════════════════════════════════════════════════════════════════════

interface AsOfStampProps {
  timestamp: string | Date;
  label?: string;
  source?: "bank" | "erp" | "forecast" | "manual";
  isStale?: boolean;
  staleThresholdHours?: number;
  className?: string;
  variant?: "default" | "compact" | "prominent";
}

// ═══════════════════════════════════════════════════════════════════════════════
// HELPER FUNCTIONS
// ═══════════════════════════════════════════════════════════════════════════════

const formatTimestamp = (timestamp: string | Date): string => {
  const date = typeof timestamp === "string" ? new Date(timestamp) : timestamp;
  return date.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
};

const getRelativeTime = (timestamp: string | Date): string => {
  const date = typeof timestamp === "string" ? new Date(timestamp) : timestamp;
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffHours = diffMs / (1000 * 60 * 60);
  const diffDays = diffHours / 24;

  if (diffHours < 1) {
    return "just now";
  } else if (diffHours < 24) {
    return `${Math.floor(diffHours)}h ago`;
  } else if (diffDays < 7) {
    return `${Math.floor(diffDays)}d ago`;
  } else {
    return formatTimestamp(timestamp);
  }
};

const isTimestampStale = (timestamp: string | Date, thresholdHours: number): boolean => {
  const date = typeof timestamp === "string" ? new Date(timestamp) : timestamp;
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffHours = diffMs / (1000 * 60 * 60);
  return diffHours > thresholdHours;
};

const getSourceConfig = (source: string) => {
  switch (source) {
    case "bank":
      return { label: "Bank Feed", color: "text-emerald-400", bg: "bg-emerald-500/20" };
    case "erp":
      return { label: "ERP Sync", color: "text-blue-400", bg: "bg-blue-500/20" };
    case "forecast":
      return { label: "Forecast", color: "text-amber-400", bg: "bg-amber-500/20" };
    case "manual":
      return { label: "Manual", color: "text-purple-400", bg: "bg-purple-500/20" };
    default:
      return { label: "Data", color: "text-zinc-400", bg: "bg-zinc-500/20" };
  }
};

// ═══════════════════════════════════════════════════════════════════════════════
// MAIN COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

export const AsOfStamp: React.FC<AsOfStampProps> = ({
  timestamp,
  label = "As of",
  source,
  isStale: forcedStale,
  staleThresholdHours = 24,
  className = "",
  variant = "default",
}) => {
  const stale = forcedStale ?? isTimestampStale(timestamp, staleThresholdHours);
  const sourceConfig = source ? getSourceConfig(source) : null;

  if (variant === "compact") {
    return (
      <span className={`inline-flex items-center gap-1.5 text-xs ${stale ? "text-amber-400" : "text-zinc-500"} ${className}`}>
        <Clock className="w-3 h-3" />
        {getRelativeTime(timestamp)}
        {stale && <AlertCircle className="w-3 h-3" />}
      </span>
    );
  }

  if (variant === "prominent") {
    return (
      <div className={`p-4 rounded-xl border ${stale ? "bg-amber-500/10 border-amber-500/30" : "bg-zinc-800/50 border-zinc-700"} ${className}`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className={`p-2 rounded-lg ${stale ? "bg-amber-500/20" : "bg-zinc-700"}`}>
              <Calendar className={`w-5 h-5 ${stale ? "text-amber-400" : "text-zinc-400"}`} />
            </div>
            <div>
              <p className="text-xs text-zinc-500 uppercase tracking-wider">{label}</p>
              <p className="text-lg font-semibold text-zinc-200">{formatTimestamp(timestamp)}</p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {sourceConfig && (
              <span className={`px-2 py-1 rounded text-xs font-medium ${sourceConfig.bg} ${sourceConfig.color}`}>
                {sourceConfig.label}
              </span>
            )}
            {stale ? (
              <span className="px-2 py-1 rounded text-xs font-medium bg-amber-500/20 text-amber-400 flex items-center gap-1">
                <AlertCircle className="w-3 h-3" />
                Stale
              </span>
            ) : (
              <span className="px-2 py-1 rounded text-xs font-medium bg-emerald-500/20 text-emerald-400 flex items-center gap-1">
                <CheckCircle2 className="w-3 h-3" />
                Fresh
              </span>
            )}
          </div>
        </div>

        {stale && (
          <p className="mt-3 text-xs text-amber-400">
            Data is more than {staleThresholdHours} hours old. Consider refreshing.
          </p>
        )}
      </div>
    );
  }

  // Default variant
  return (
    <div className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border ${
      stale ? "bg-amber-500/10 border-amber-500/30" : "bg-zinc-800/50 border-zinc-700"
    } ${className}`}>
      <Clock className={`w-4 h-4 ${stale ? "text-amber-400" : "text-zinc-500"}`} />
      <span className={`text-sm ${stale ? "text-amber-400" : "text-zinc-400"}`}>
        {label}:
      </span>
      <span className="text-sm text-zinc-200 font-medium">
        {formatTimestamp(timestamp)}
      </span>
      {sourceConfig && (
        <span className={`px-1.5 py-0.5 rounded text-xs ${sourceConfig.bg} ${sourceConfig.color}`}>
          {sourceConfig.label}
        </span>
      )}
      {stale && (
        <AlertCircle className="w-4 h-4 text-amber-400" />
      )}
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// DUAL TIMESTAMP COMPONENT (Bank vs ERP)
// ═══════════════════════════════════════════════════════════════════════════════

interface DualAsOfStampProps {
  bankTimestamp?: string | Date;
  erpTimestamp?: string | Date;
  className?: string;
}

export const DualAsOfStamp: React.FC<DualAsOfStampProps> = ({
  bankTimestamp,
  erpTimestamp,
  className = "",
}) => {
  const mismatchHours = bankTimestamp && erpTimestamp
    ? Math.abs(
        (new Date(bankTimestamp).getTime() - new Date(erpTimestamp).getTime()) /
          (1000 * 60 * 60)
      )
    : 0;

  const hasMismatch = mismatchHours > 24;

  return (
    <div className={`p-4 rounded-xl border ${hasMismatch ? "bg-amber-500/10 border-amber-500/30" : "bg-zinc-800/50 border-zinc-700"} ${className}`}>
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-sm font-medium text-zinc-300">Data Freshness</h4>
        {hasMismatch && (
          <span className="px-2 py-1 rounded text-xs font-medium bg-amber-500/20 text-amber-400 flex items-center gap-1">
            <AlertCircle className="w-3 h-3" />
            {mismatchHours.toFixed(0)}h mismatch
          </span>
        )}
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="p-3 bg-zinc-900/50 rounded-lg">
          <p className="text-xs text-zinc-500 uppercase tracking-wider mb-1">Bank Feed</p>
          {bankTimestamp ? (
            <>
              <p className="text-sm font-medium text-emerald-400">{formatTimestamp(bankTimestamp)}</p>
              <p className="text-xs text-zinc-500">{getRelativeTime(bankTimestamp)}</p>
            </>
          ) : (
            <p className="text-sm text-zinc-500">Not available</p>
          )}
        </div>

        <div className="p-3 bg-zinc-900/50 rounded-lg">
          <p className="text-xs text-zinc-500 uppercase tracking-wider mb-1">ERP Sync</p>
          {erpTimestamp ? (
            <>
              <p className="text-sm font-medium text-blue-400">{formatTimestamp(erpTimestamp)}</p>
              <p className="text-xs text-zinc-500">{getRelativeTime(erpTimestamp)}</p>
            </>
          ) : (
            <p className="text-sm text-zinc-500">Not available</p>
          )}
        </div>
      </div>
    </div>
  );
};

export default AsOfStamp;
