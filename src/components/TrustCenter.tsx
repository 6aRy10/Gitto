"use client";

import React, { useState, useEffect, useCallback } from "react";
import { 
  Shield, TrendingUp, AlertTriangle, Clock, RefreshCw, 
  ChevronRight, Eye, Banknote, HelpCircle, ArrowLeftRight,
  Calendar, Database, Activity
} from "lucide-react";
import { getTrustReport, getTrustMetricDetails } from "@/lib/api";
import { EvidenceDrawer, EvidenceRef } from "./ui/evidence-drawer";
import { TruthBadge, TruthLevel } from "./ui/truth-badge";

// ═══════════════════════════════════════════════════════════════════════════════
// TYPES
// ═══════════════════════════════════════════════════════════════════════════════

interface TrustMetric {
  id: number;
  key: string;
  description?: string;
  value: number;
  unit: string;
  exposure_amount_base: number;
  trend_delta?: number;
  trend_direction?: "up" | "down" | "stable";
  evidence_refs?: EvidenceRef[];
  breakdown?: Record<string, unknown>;
}

interface GateFailure {
  gate: string;
  description?: string;
  threshold: number;
  actual: number;
  exposure: number;
  status: string;
}

interface TrustReport {
  id: number;
  snapshot_id: number;
  created_at: string;
  trust_score: number;
  lock_eligible: boolean;
  gate_failures: GateFailure[];
  metrics_summary?: Record<string, number>;
  config?: Record<string, unknown>;
  metrics: TrustMetric[];
}

// ═══════════════════════════════════════════════════════════════════════════════
// HELPER FUNCTIONS
// ═══════════════════════════════════════════════════════════════════════════════

const formatValue = (value: number, unit: string): string => {
  switch (unit) {
    case "percent":
      return `${value.toFixed(1)}%`;
    case "currency":
      return `€${Math.abs(value).toLocaleString("en-US", { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;
    case "hours":
      if (value === 0) return "In Sync";
      return value < 24 ? `${value.toFixed(1)}h` : `${(value / 24).toFixed(1)}d`;
    case "count":
      return value.toLocaleString();
    case "boolean":
      return value ? "Yes" : "No";
    default:
      return value.toFixed(2);
  }
};

const getMetricIcon = (key: string) => {
  switch (key) {
    case "cash_explained_pct":
      return Banknote;
    case "unknown_exposure_base":
      return HelpCircle;
    case "missing_fx_exposure_base":
      return ArrowLeftRight;
    case "freshness_mismatch_hours":
      return Clock;
    case "duplicate_exposure_base":
      return Database;
    case "suggested_matches_pending_exposure":
      return Activity;
    case "forecast_calibration_coverage":
      return TrendingUp;
    case "drift_warning":
      return AlertTriangle;
    default:
      return Shield;
  }
};

const getMetricStatus = (key: string, value: number): "good" | "warning" | "critical" => {
  switch (key) {
    case "cash_explained_pct":
      return value >= 95 ? "good" : value >= 85 ? "warning" : "critical";
    case "unknown_exposure_base":
    case "missing_fx_exposure_base":
    case "duplicate_exposure_base":
    case "suggested_matches_pending_exposure":
      return value === 0 ? "good" : value < 10000 ? "warning" : "critical";
    case "freshness_mismatch_hours":
      return value <= 24 ? "good" : value <= 72 ? "warning" : "critical";
    case "forecast_calibration_coverage":
      return value >= 90 ? "good" : value >= 70 ? "warning" : "critical";
    case "drift_warning":
      return value === 0 ? "good" : "warning";
    default:
      return "good";
  }
};

const getStatusColors = (status: "good" | "warning" | "critical") => {
  switch (status) {
    case "good":
      return { bg: "bg-emerald-500/10", border: "border-emerald-500/30", text: "text-emerald-400", icon: "text-emerald-500" };
    case "warning":
      return { bg: "bg-amber-500/10", border: "border-amber-500/30", text: "text-amber-400", icon: "text-amber-500" };
    case "critical":
      return { bg: "bg-red-500/10", border: "border-red-500/30", text: "text-red-400", icon: "text-red-500" };
  }
};

const getTruthLevelForMetric = (key: string): TruthLevel => {
  if (key.includes("bank") || key === "cash_explained_pct") return "bank-true";
  if (key.includes("reconcil") || key.includes("match")) return "reconciled";
  if (key.includes("forecast") || key.includes("model")) return "modeled";
  return "unknown";
};

// ═══════════════════════════════════════════════════════════════════════════════
// TRUST SCORE GAUGE
// ═══════════════════════════════════════════════════════════════════════════════

const TrustScoreGauge: React.FC<{ score: number; size?: "sm" | "lg" }> = ({ score, size = "lg" }) => {
  const dimensions = size === "lg" ? { width: 160, height: 160, r: 60, stroke: 10 } : { width: 80, height: 80, r: 30, stroke: 6 };
  const circumference = 2 * Math.PI * dimensions.r;
  const strokeDashoffset = circumference - (score / 100) * circumference;
  
  const getColor = () => {
    if (score >= 90) return "text-emerald-500";
    if (score >= 75) return "text-amber-500";
    return "text-red-500";
  };

  const getLabel = () => {
    if (score >= 90) return "Excellent";
    if (score >= 75) return "Good";
    if (score >= 50) return "Fair";
    return "Poor";
  };

  return (
    <div className="relative" style={{ width: dimensions.width, height: dimensions.height }}>
      <svg className="w-full h-full transform -rotate-90">
        <circle
          cx={dimensions.width / 2}
          cy={dimensions.height / 2}
          r={dimensions.r}
          fill="none"
          stroke="currentColor"
          strokeWidth={dimensions.stroke}
          className="text-zinc-800"
        />
        <circle
          cx={dimensions.width / 2}
          cy={dimensions.height / 2}
          r={dimensions.r}
          fill="none"
          stroke="currentColor"
          strokeWidth={dimensions.stroke}
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          strokeLinecap="round"
          className={`${getColor()} transition-all duration-700`}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className={`${size === "lg" ? "text-4xl" : "text-xl"} font-bold ${getColor()}`}>
          {score.toFixed(0)}
        </span>
        {size === "lg" && (
          <span className="text-xs text-zinc-500 mt-1">{getLabel()}</span>
        )}
      </div>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// METRIC CARD
// ═══════════════════════════════════════════════════════════════════════════════

const MetricCard: React.FC<{
  metric: TrustMetric;
  onViewEvidence: () => void;
}> = ({ metric, onViewEvidence }) => {
  const Icon = getMetricIcon(metric.key);
  const status = getMetricStatus(metric.key, metric.value);
  const colors = getStatusColors(status);
  const truthLevel = getTruthLevelForMetric(metric.key);
  const hasEvidence = metric.evidence_refs && metric.evidence_refs.length > 0;

  return (
    <div className={`relative p-4 rounded-xl border ${colors.bg} ${colors.border} group transition-all hover:scale-[1.02]`}>
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className={`p-2 rounded-lg bg-zinc-800/50`}>
            <Icon className={`w-5 h-5 ${colors.icon}`} />
          </div>
          <div>
            <h4 className="text-sm font-medium text-zinc-200">
              {metric.description || metric.key.replace(/_/g, " ")}
            </h4>
            <div className="flex items-center gap-2 mt-1">
              <TruthBadge level={truthLevel} compact showLabel />
            </div>
          </div>
        </div>
      </div>

      {/* Value */}
      <div className="mt-4">
        <div className="flex items-end gap-2">
          <span className={`text-3xl font-bold ${colors.text}`}>
            {formatValue(metric.value, metric.unit)}
          </span>
          {metric.trend_delta !== null && metric.trend_delta !== undefined && (
            <span className={`text-sm mb-1 ${
              metric.trend_direction === "up" 
                ? metric.key.includes("exposure") ? "text-red-400" : "text-emerald-400"
                : metric.trend_direction === "down" 
                  ? metric.key.includes("exposure") ? "text-emerald-400" : "text-red-400"
                  : "text-zinc-500"
            }`}>
              {metric.trend_direction === "up" ? "↑" : metric.trend_direction === "down" ? "↓" : "→"}
              {Math.abs(metric.trend_delta).toFixed(1)}
            </span>
          )}
        </div>

        {/* Exposure Amount */}
        {metric.exposure_amount_base > 0 && (
          <p className="text-xs text-zinc-500 mt-1">
            Exposure: €{metric.exposure_amount_base.toLocaleString()}
          </p>
        )}
      </div>

      {/* Evidence Link */}
      {hasEvidence && (
        <button
          onClick={onViewEvidence}
          className="mt-4 flex items-center gap-2 text-xs text-blue-400 hover:text-blue-300 group/btn"
        >
          <Eye className="w-3 h-3" />
          View evidence ({metric.evidence_refs!.length} items)
          <ChevronRight className="w-3 h-3 opacity-0 group-hover/btn:opacity-100 transition-opacity" />
        </button>
      )}

      {/* Breakdown Preview */}
      {metric.breakdown && Object.keys(metric.breakdown).length > 0 && (
        <details className="mt-3">
          <summary className="text-xs text-zinc-500 cursor-pointer hover:text-zinc-400">
            Show breakdown
          </summary>
          <div className="mt-2 space-y-1">
            {Object.entries(metric.breakdown).slice(0, 5).map(([key, value]) => (
              <div key={key} className="flex justify-between text-xs">
                <span className="text-zinc-400">{key.replace(/_/g, " ")}</span>
                <span className="text-zinc-300 font-mono">
                  {typeof value === "number" ? value.toLocaleString() : String(value)}
                </span>
              </div>
            ))}
          </div>
        </details>
      )}
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// MAIN COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

interface TrustCenterProps {
  snapshotId: number;
  entityName?: string;
}

export const TrustCenter: React.FC<TrustCenterProps> = ({ snapshotId, entityName }) => {
  const [report, setReport] = useState<TrustReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [evidenceDrawer, setEvidenceDrawer] = useState<{
    isOpen: boolean;
    title: string;
    evidence: EvidenceRef[];
    asOfDate?: string;
  }>({ isOpen: false, title: "", evidence: [] });

  const loadReport = useCallback(async (regenerate = false) => {
    setLoading(true);
    setError(null);
    try {
      const data = await getTrustReport(snapshotId, regenerate);
      setReport(data);
    } catch (err) {
      console.error("Failed to load trust report:", err);
      setError("Failed to load trust report");
    } finally {
      setLoading(false);
    }
  }, [snapshotId]);

  useEffect(() => {
    loadReport();
  }, [loadReport]);

  const handleViewEvidence = (metric: TrustMetric) => {
    setEvidenceDrawer({
      isOpen: true,
      title: metric.description || metric.key.replace(/_/g, " "),
      evidence: metric.evidence_refs || [],
      asOfDate: report?.created_at,
    });
  };

  if (loading) {
    return (
      <div className="p-8 text-center">
        <div className="animate-spin w-10 h-10 border-3 border-blue-500 border-t-transparent rounded-full mx-auto"></div>
        <p className="text-zinc-400 mt-4">Loading Trust Center...</p>
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="p-8 text-center">
        <AlertTriangle className="w-12 h-12 text-red-400 mx-auto mb-4" />
        <p className="text-red-400">{error || "Failed to load report"}</p>
        <button
          onClick={() => loadReport()}
          className="mt-4 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg"
        >
          Retry
        </button>
      </div>
    );
  }

  // Group metrics by category
  const primaryMetrics = report.metrics.filter(m => 
    ["cash_explained_pct", "unknown_exposure_base", "missing_fx_exposure_base"].includes(m.key)
  );
  const secondaryMetrics = report.metrics.filter(m => 
    !["cash_explained_pct", "unknown_exposure_base", "missing_fx_exposure_base"].includes(m.key)
  );

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100">
      {/* Header */}
      <div className="border-b border-zinc-800 bg-zinc-900/50">
        <div className="max-w-7xl mx-auto px-6 py-6">
          <div className="flex items-start justify-between">
            <div>
              <div className="flex items-center gap-3">
                <Shield className="w-8 h-8 text-blue-500" />
                <h1 className="text-2xl font-bold">Trust Center</h1>
              </div>
              {entityName && (
                <p className="text-zinc-500 mt-1">{entityName}</p>
              )}
            </div>

            <div className="flex items-center gap-4">
              {/* As-of Timestamp */}
              <div className="flex items-center gap-2 px-3 py-2 bg-zinc-800 rounded-lg text-sm">
                <Calendar className="w-4 h-4 text-zinc-500" />
                <span className="text-zinc-400">As of:</span>
                <span className="text-zinc-200">{new Date(report.created_at).toLocaleString()}</span>
              </div>

              {/* Refresh Button */}
              <button
                onClick={() => loadReport(true)}
                className="p-2 bg-zinc-800 hover:bg-zinc-700 rounded-lg transition-colors"
                title="Regenerate Report"
              >
                <RefreshCw className="w-5 h-5 text-zinc-400" />
              </button>
            </div>
          </div>

          {/* Trust Score Hero */}
          <div className="mt-8 flex items-center gap-8">
            <TrustScoreGauge score={report.trust_score} size="lg" />
            
            <div className="flex-1">
              <div className="flex items-center gap-3">
                <span className={`text-lg font-semibold ${
                  report.lock_eligible ? "text-emerald-400" : "text-amber-400"
                }`}>
                  {report.lock_eligible ? "✓ Lock Eligible" : "⚠ Lock Requires Override"}
                </span>
              </div>

              {/* Quick Stats */}
              <div className="mt-4 grid grid-cols-3 gap-4">
                <div className="p-3 bg-zinc-800/50 rounded-lg">
                  <p className="text-xs text-zinc-500 uppercase tracking-wider">Cash Explained</p>
                  <p className="text-xl font-bold text-zinc-200">
                    {report.metrics_summary?.cash_explained_pct?.toFixed(1) || "—"}%
                  </p>
                </div>
                <div className="p-3 bg-zinc-800/50 rounded-lg">
                  <p className="text-xs text-zinc-500 uppercase tracking-wider">Unknown Exposure</p>
                  <p className="text-xl font-bold text-zinc-200">
                    €{(report.metrics_summary?.unknown_exposure_base || 0).toLocaleString()}
                  </p>
                </div>
                <div className="p-3 bg-zinc-800/50 rounded-lg">
                  <p className="text-xs text-zinc-500 uppercase tracking-wider">Missing FX</p>
                  <p className="text-xl font-bold text-zinc-200">
                    €{(report.metrics_summary?.missing_fx_exposure_base || 0).toLocaleString()}
                  </p>
                </div>
              </div>

              {/* Gate Failures Summary */}
              {report.gate_failures.length > 0 && (
                <div className="mt-4 p-3 bg-red-500/10 border border-red-500/30 rounded-lg">
                  <p className="text-sm text-red-400 font-medium">
                    {report.gate_failures.length} Lock Gate{report.gate_failures.length > 1 ? "s" : ""} Failed
                  </p>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {report.gate_failures.map((gate, idx) => (
                      <span
                        key={idx}
                        className="px-2 py-1 text-xs bg-red-500/20 text-red-300 rounded"
                      >
                        {gate.gate.replace(/_/g, " ")}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Metrics Grid */}
      <div className="max-w-7xl mx-auto px-6 py-8">
        {/* Primary Metrics */}
        <div className="mb-8">
          <h2 className="text-lg font-semibold text-zinc-200 mb-4 flex items-center gap-2">
            <Banknote className="w-5 h-5 text-emerald-500" />
            Core Metrics
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {primaryMetrics.map(metric => (
              <MetricCard
                key={metric.key}
                metric={metric}
                onViewEvidence={() => handleViewEvidence(metric)}
              />
            ))}
          </div>
        </div>

        {/* Secondary Metrics */}
        <div>
          <h2 className="text-lg font-semibold text-zinc-200 mb-4 flex items-center gap-2">
            <Activity className="w-5 h-5 text-blue-500" />
            Data Quality Metrics
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {secondaryMetrics.map(metric => (
              <MetricCard
                key={metric.key}
                metric={metric}
                onViewEvidence={() => handleViewEvidence(metric)}
              />
            ))}
          </div>
        </div>
      </div>

      {/* Evidence Drawer */}
      <EvidenceDrawer
        isOpen={evidenceDrawer.isOpen}
        onClose={() => setEvidenceDrawer({ ...evidenceDrawer, isOpen: false })}
        title={evidenceDrawer.title}
        evidence={evidenceDrawer.evidence}
        asOfDate={evidenceDrawer.asOfDate}
      />
    </div>
  );
};

export default TrustCenter;
