"use client";

import React, { useState, useEffect, useCallback } from "react";
import {
  Shield, AlertCircle, CheckCircle2, XCircle, Clock, FileText,
  ChevronRight, RefreshCw, Lock, Unlock, AlertTriangle, Activity,
  Download, Eye, Play, ArrowRight, BadgeCheck, Calendar
} from "lucide-react";
import { 
  getTrustReport, getLatestInvariants, runInvariants, 
  getDatasetHealth, lockSnapshot 
} from "@/lib/api";
import { EvidenceDrawer, EvidenceRef } from "./ui/evidence-drawer";
import { TruthBadge, TruthLevel } from "./ui/truth-badge";

// ═══════════════════════════════════════════════════════════════════════════════
// TYPES
// ═══════════════════════════════════════════════════════════════════════════════

interface HealthFinding {
  id: number;
  category: string;
  severity: "info" | "warn" | "critical";
  metric_key: string;
  metric_value: number;
  exposure_amount_base: number;
  count_rows: number;
  sample_evidence_json?: EvidenceRef[];
}

interface InvariantResult {
  id: number;
  name: string;
  description?: string;
  status: "pass" | "fail" | "warn" | "skip";
  severity: string;
  details_json?: Record<string, unknown>;
  proof_string?: string;
  evidence_refs_json?: EvidenceRef[];
  exposure_amount: number;
}

interface InvariantRun {
  id: number;
  snapshot_id: number;
  created_at: string;
  completed_at?: string;
  status: string;
  summary_json?: {
    total_invariants: number;
    passed: number;
    failed: number;
    warnings: number;
    skipped: number;
    critical_failures: number;
    execution_time_ms: number;
  };
  results: InvariantResult[];
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
}

// ═══════════════════════════════════════════════════════════════════════════════
// HELPER FUNCTIONS
// ═══════════════════════════════════════════════════════════════════════════════

const getSeverityColors = (severity: string) => {
  switch (severity) {
    case "critical":
      return { bg: "bg-red-500/10", border: "border-red-500/30", text: "text-red-400", icon: XCircle };
    case "error":
    case "warn":
      return { bg: "bg-amber-500/10", border: "border-amber-500/30", text: "text-amber-400", icon: AlertTriangle };
    case "warning":
    case "info":
      return { bg: "bg-blue-500/10", border: "border-blue-500/30", text: "text-blue-400", icon: AlertCircle };
    default:
      return { bg: "bg-zinc-500/10", border: "border-zinc-500/30", text: "text-zinc-400", icon: AlertCircle };
  }
};

const getStatusColors = (status: string) => {
  switch (status) {
    case "pass":
      return { bg: "bg-emerald-500/10", border: "border-emerald-500/30", text: "text-emerald-400", icon: CheckCircle2 };
    case "fail":
      return { bg: "bg-red-500/10", border: "border-red-500/30", text: "text-red-400", icon: XCircle };
    case "warn":
      return { bg: "bg-amber-500/10", border: "border-amber-500/30", text: "text-amber-400", icon: AlertTriangle };
    case "skip":
      return { bg: "bg-zinc-500/10", border: "border-zinc-500/30", text: "text-zinc-400", icon: Clock };
    default:
      return { bg: "bg-zinc-500/10", border: "border-zinc-500/30", text: "text-zinc-400", icon: AlertCircle };
  }
};

// ═══════════════════════════════════════════════════════════════════════════════
// HEALTH FINDING CARD
// ═══════════════════════════════════════════════════════════════════════════════

const HealthFindingCard: React.FC<{
  finding: HealthFinding;
  onViewEvidence: () => void;
}> = ({ finding, onViewEvidence }) => {
  const colors = getSeverityColors(finding.severity);
  const Icon = colors.icon;

  return (
    <div className={`p-4 rounded-lg border ${colors.bg} ${colors.border}`}>
      <div className="flex items-start justify-between">
        <div className="flex items-start gap-3">
          <Icon className={`w-5 h-5 ${colors.text} flex-shrink-0 mt-0.5`} />
          <div>
            <div className="flex items-center gap-2">
              <span className={`text-xs px-2 py-0.5 rounded font-medium uppercase ${colors.bg} ${colors.text}`}>
                {finding.severity}
              </span>
              <h4 className="text-sm font-medium text-zinc-200">
                {finding.category.replace(/_/g, " ")}
              </h4>
            </div>
            <p className="text-xs text-zinc-400 mt-1">
              {finding.metric_key}: {finding.metric_value}
            </p>
          </div>
        </div>

        <div className="text-right">
          <p className="text-lg font-bold text-zinc-200">
            €{finding.exposure_amount_base.toLocaleString()}
          </p>
          <p className="text-xs text-zinc-500">
            {finding.count_rows} rows
          </p>
        </div>
      </div>

      {finding.sample_evidence_json && finding.sample_evidence_json.length > 0 && (
        <button
          onClick={onViewEvidence}
          className="mt-3 flex items-center gap-2 text-xs text-blue-400 hover:text-blue-300"
        >
          <Eye className="w-3 h-3" />
          View evidence
          <ChevronRight className="w-3 h-3" />
        </button>
      )}
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// INVARIANT RESULT CARD
// ═══════════════════════════════════════════════════════════════════════════════

const InvariantResultCard: React.FC<{
  result: InvariantResult;
  onViewEvidence: () => void;
}> = ({ result, onViewEvidence }) => {
  const colors = getStatusColors(result.status);
  const Icon = colors.icon;

  return (
    <div className={`p-4 rounded-lg border ${colors.bg} ${colors.border}`}>
      <div className="flex items-start justify-between">
        <div className="flex items-start gap-3">
          <Icon className={`w-5 h-5 ${colors.text} flex-shrink-0 mt-0.5`} />
          <div>
            <div className="flex items-center gap-2">
              <span className={`text-xs px-2 py-0.5 rounded font-medium uppercase ${colors.text}`}>
                {result.status}
              </span>
              <span className="text-xs px-2 py-0.5 rounded bg-zinc-800 text-zinc-400">
                {result.severity}
              </span>
            </div>
            <h4 className="text-sm font-medium text-zinc-200 mt-1">
              {result.name.replace(/_/g, " ")}
            </h4>
            {result.description && (
              <p className="text-xs text-zinc-500 mt-0.5">{result.description}</p>
            )}
          </div>
        </div>

        {result.exposure_amount > 0 && (
          <div className="text-right">
            <p className="text-sm font-bold text-zinc-200">
              €{result.exposure_amount.toLocaleString()}
            </p>
            <p className="text-xs text-zinc-500">exposure</p>
          </div>
        )}
      </div>

      {/* Proof String */}
      {result.proof_string && (
        <div className="mt-3 p-2 bg-zinc-900/50 rounded text-xs text-zinc-400 font-mono">
          {result.proof_string}
        </div>
      )}

      {/* Evidence Link */}
      {result.evidence_refs_json && result.evidence_refs_json.length > 0 && (
        <button
          onClick={onViewEvidence}
          className="mt-3 flex items-center gap-2 text-xs text-blue-400 hover:text-blue-300"
        >
          <Eye className="w-3 h-3" />
          View {result.evidence_refs_json.length} evidence items
          <ChevronRight className="w-3 h-3" />
        </button>
      )}
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// LOCK GATE CARD
// ═══════════════════════════════════════════════════════════════════════════════

const LockGateCard: React.FC<{
  gate: GateFailure;
}> = ({ gate }) => {
  const passed = gate.status === "passed";

  return (
    <div className={`p-4 rounded-lg border ${
      passed 
        ? "bg-emerald-500/10 border-emerald-500/30" 
        : "bg-red-500/10 border-red-500/30"
    }`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          {passed ? (
            <CheckCircle2 className="w-5 h-5 text-emerald-400" />
          ) : (
            <XCircle className="w-5 h-5 text-red-400" />
          )}
          <div>
            <h4 className="text-sm font-medium text-zinc-200">
              {gate.gate.replace(/_/g, " ")}
            </h4>
            {gate.description && (
              <p className="text-xs text-zinc-500">{gate.description}</p>
            )}
          </div>
        </div>

        <div className="text-right">
          <p className={`text-sm font-mono ${passed ? "text-emerald-400" : "text-red-400"}`}>
            {(gate.actual * 100).toFixed(2)}%
          </p>
          <p className="text-xs text-zinc-500">
            threshold: {(gate.threshold * 100).toFixed(2)}%
          </p>
        </div>
      </div>

      {!passed && gate.exposure > 0 && (
        <div className="mt-2 pt-2 border-t border-zinc-800">
          <p className="text-xs text-zinc-400">
            Exposure: <span className="text-red-400 font-medium">€{gate.exposure.toLocaleString()}</span>
          </p>
        </div>
      )}
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// LOCK MODAL
// ═══════════════════════════════════════════════════════════════════════════════

const LockModal: React.FC<{
  isOpen: boolean;
  onClose: () => void;
  snapshotId: number;
  trustReport: TrustReport;
  onSuccess: () => void;
}> = ({ isOpen, onClose, snapshotId, trustReport, onSuccess }) => {
  const [acknowledgment, setAcknowledgment] = useState("");
  const [reason, setReason] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const needsOverride = !trustReport.lock_eligible;
  const minAckLength = 20;
  const canSubmit = trustReport.lock_eligible || acknowledgment.length >= minAckLength;

  const handleLock = async () => {
    setLoading(true);
    setError(null);

    try {
      const payload: {
        user_id: string;
        user_email: string;
        user_role: string;
        override_acknowledgment?: string;
        override_reason?: string;
      } = {
        user_id: "current-user", // Replace with actual user
        user_email: "user@company.com",
        user_role: "CFO",
      };

      if (needsOverride) {
        payload.override_acknowledgment = acknowledgment;
        payload.override_reason = reason;
      }

      await lockSnapshot(snapshotId, payload);
      onSuccess();
      onClose();
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } };
      setError(error.response?.data?.detail || "Failed to lock snapshot");
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50" onClick={onClose}>
      <div 
        className="bg-zinc-900 rounded-xl border border-zinc-800 w-full max-w-lg overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="p-6 border-b border-zinc-800">
          <div className="flex items-center gap-3">
            <div className={`p-2 rounded-lg ${trustReport.lock_eligible ? "bg-emerald-500/20" : "bg-amber-500/20"}`}>
              {trustReport.lock_eligible ? (
                <Lock className="w-6 h-6 text-emerald-400" />
              ) : (
                <AlertTriangle className="w-6 h-6 text-amber-400" />
              )}
            </div>
            <div>
              <h2 className="text-lg font-semibold text-zinc-100">
                {trustReport.lock_eligible ? "Lock Snapshot" : "Lock with Override"}
              </h2>
              <p className="text-sm text-zinc-500">
                {trustReport.lock_eligible 
                  ? "All gates passed. Ready to lock."
                  : `${trustReport.gate_failures.length} gate(s) failed. Override required.`
                }
              </p>
            </div>
          </div>
        </div>

        {/* Failed Gates */}
        {needsOverride && (
          <div className="p-6 border-b border-zinc-800">
            <h3 className="text-sm font-medium text-zinc-300 mb-3">Failed Gates</h3>
            <div className="space-y-2">
              {trustReport.gate_failures.map((gate, idx) => (
                <div key={idx} className="flex items-center justify-between p-3 bg-red-500/10 rounded-lg">
                  <span className="text-sm text-zinc-300">{gate.gate.replace(/_/g, " ")}</span>
                  <span className="text-sm text-red-400">
                    €{gate.exposure.toLocaleString()} exposure
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Override Form */}
        {needsOverride && (
          <div className="p-6 border-b border-zinc-800">
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-zinc-300 mb-2">
                  Acknowledgment <span className="text-red-400">*</span>
                </label>
                <textarea
                  className="w-full p-3 bg-zinc-800 border border-zinc-700 rounded-lg text-sm text-zinc-200 resize-none focus:outline-none focus:border-blue-500"
                  placeholder={`I acknowledge the risks and accept responsibility for locking this snapshot... (min ${minAckLength} characters)`}
                  rows={3}
                  value={acknowledgment}
                  onChange={(e) => setAcknowledgment(e.target.value)}
                />
                <p className="text-xs text-zinc-500 mt-1">
                  {acknowledgment.length} / {minAckLength} characters minimum
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-zinc-300 mb-2">
                  Reason (optional)
                </label>
                <input
                  type="text"
                  className="w-full p-3 bg-zinc-800 border border-zinc-700 rounded-lg text-sm text-zinc-200 focus:outline-none focus:border-blue-500"
                  placeholder="e.g., Q4 deadline, client commitment..."
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                />
              </div>
            </div>
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="p-4 mx-6 mt-4 bg-red-500/10 border border-red-500/30 rounded-lg">
            <p className="text-sm text-red-400">{error}</p>
          </div>
        )}

        {/* Actions */}
        <div className="p-6 flex items-center justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm text-zinc-400 hover:text-zinc-200 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleLock}
            disabled={!canSubmit || loading}
            className={`px-6 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-2 ${
              canSubmit && !loading
                ? "bg-blue-600 hover:bg-blue-500 text-white"
                : "bg-zinc-800 text-zinc-500 cursor-not-allowed"
            }`}
          >
            {loading ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" />
                Locking...
              </>
            ) : (
              <>
                <Lock className="w-4 h-4" />
                {needsOverride ? "Lock with Override" : "Lock Snapshot"}
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// MAIN COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

interface SnapshotReviewProps {
  snapshotId: number;
  snapshotName?: string;
  datasetId?: string;
  isCFO?: boolean;
  onLockSuccess?: () => void;
}

export const SnapshotReview: React.FC<SnapshotReviewProps> = ({
  snapshotId,
  snapshotName,
  datasetId,
  isCFO = false,
  onLockSuccess,
}) => {
  const [activeTab, setActiveTab] = useState<"health" | "invariants" | "gates">("health");
  const [trustReport, setTrustReport] = useState<TrustReport | null>(null);
  const [invariantRun, setInvariantRun] = useState<InvariantRun | null>(null);
  const [healthFindings, setHealthFindings] = useState<HealthFinding[]>([]);
  const [loading, setLoading] = useState(true);
  const [runningInvariants, setRunningInvariants] = useState(false);
  const [showLockModal, setShowLockModal] = useState(false);
  const [evidenceDrawer, setEvidenceDrawer] = useState<{
    isOpen: boolean;
    title: string;
    evidence: EvidenceRef[];
  }>({ isOpen: false, title: "", evidence: [] });

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [trust, invariants] = await Promise.all([
        getTrustReport(snapshotId),
        getLatestInvariants(snapshotId).catch(() => null),
      ]);

      setTrustReport(trust);
      setInvariantRun(invariants);

      // Load health findings if dataset ID available
      if (datasetId) {
        try {
          const health = await getDatasetHealth(datasetId);
          setHealthFindings(health.findings || []);
        } catch {
          // Health report may not exist
        }
      }
    } catch (err) {
      console.error("Failed to load review data:", err);
    } finally {
      setLoading(false);
    }
  }, [snapshotId, datasetId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleRunInvariants = async () => {
    setRunningInvariants(true);
    try {
      const result = await runInvariants(snapshotId, "pre-meeting-review");
      setInvariantRun(result);
    } catch (err) {
      console.error("Failed to run invariants:", err);
    } finally {
      setRunningInvariants(false);
    }
  };

  const handleGenerateWeeklyPack = () => {
    // Generate view-only summary
    window.open(`/weekly-pack/${snapshotId}`, "_blank");
  };

  if (loading) {
    return (
      <div className="p-8 text-center">
        <div className="animate-spin w-10 h-10 border-3 border-blue-500 border-t-transparent rounded-full mx-auto"></div>
        <p className="text-zinc-400 mt-4">Loading Snapshot Review...</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100">
      {/* Header */}
      <div className="border-b border-zinc-800 bg-zinc-900/50">
        <div className="max-w-7xl mx-auto px-6 py-6">
          <div className="flex items-start justify-between">
            <div>
              <div className="flex items-center gap-3">
                <BadgeCheck className="w-8 h-8 text-purple-500" />
                <div>
                  <h1 className="text-2xl font-bold">Pre-Meeting Review</h1>
                  {snapshotName && (
                    <p className="text-zinc-500">{snapshotName}</p>
                  )}
                </div>
              </div>

              {/* Status Summary */}
              <div className="mt-4 flex items-center gap-4">
                {trustReport && (
                  <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full ${
                    trustReport.lock_eligible 
                      ? "bg-emerald-500/20 text-emerald-400" 
                      : "bg-amber-500/20 text-amber-400"
                  }`}>
                    {trustReport.lock_eligible ? (
                      <Unlock className="w-4 h-4" />
                    ) : (
                      <Lock className="w-4 h-4" />
                    )}
                    <span className="text-sm font-medium">
                      {trustReport.lock_eligible ? "Lock Eligible" : "Override Required"}
                    </span>
                  </div>
                )}

                {invariantRun && (
                  <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full ${
                    invariantRun.status === "passed"
                      ? "bg-emerald-500/20 text-emerald-400"
                      : invariantRun.status === "failed"
                        ? "bg-red-500/20 text-red-400"
                        : "bg-amber-500/20 text-amber-400"
                  }`}>
                    <Activity className="w-4 h-4" />
                    <span className="text-sm font-medium">
                      {invariantRun.summary_json?.passed || 0}/{invariantRun.summary_json?.total_invariants || 0} Invariants
                    </span>
                  </div>
                )}

                {trustReport && (
                  <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-zinc-800 text-zinc-400">
                    <Shield className="w-4 h-4" />
                    <span className="text-sm font-medium">
                      Trust Score: {trustReport.trust_score.toFixed(0)}
                    </span>
                  </div>
                )}
              </div>
            </div>

            {/* Actions */}
            <div className="flex items-center gap-3">
              <button
                onClick={handleGenerateWeeklyPack}
                className="flex items-center gap-2 px-4 py-2 bg-zinc-800 hover:bg-zinc-700 rounded-lg text-sm transition-colors"
              >
                <Download className="w-4 h-4" />
                Generate Weekly Pack
              </button>

              {isCFO ? (
                <button
                  onClick={() => setShowLockModal(true)}
                  disabled={!trustReport}
                  className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded-lg text-sm font-medium transition-colors"
                >
                  <Lock className="w-4 h-4" />
                  Lock Snapshot
                </button>
              ) : (
                <button
                  onClick={() => alert("Request sent to CFO for approval")}
                  className="flex items-center gap-2 px-4 py-2 bg-purple-600 hover:bg-purple-500 rounded-lg text-sm font-medium transition-colors"
                >
                  <ArrowRight className="w-4 h-4" />
                  Request CFO Lock
                </button>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-zinc-800">
        <div className="max-w-7xl mx-auto px-6">
          <div className="flex gap-1">
            {[
              { id: "health", label: "Health Findings", count: healthFindings.length },
              { id: "invariants", label: "Invariants", count: invariantRun?.results.length || 0 },
              { id: "gates", label: "Lock Gates", count: trustReport?.gate_failures.length || 0 },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as typeof activeTab)}
                className={`px-6 py-4 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === tab.id
                    ? "border-blue-500 text-blue-400"
                    : "border-transparent text-zinc-500 hover:text-zinc-300"
                }`}
              >
                {tab.label}
                {tab.count > 0 && (
                  <span className={`ml-2 px-2 py-0.5 rounded-full text-xs ${
                    activeTab === tab.id ? "bg-blue-500/20" : "bg-zinc-800"
                  }`}>
                    {tab.count}
                  </span>
                )}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-7xl mx-auto px-6 py-8">
        {/* Health Findings Tab */}
        {activeTab === "health" && (
          <div className="space-y-4">
            {healthFindings.length === 0 ? (
              <div className="text-center py-12 text-zinc-500">
                <FileText className="w-12 h-12 mx-auto mb-3 opacity-50" />
                <p>No health findings for this dataset</p>
              </div>
            ) : (
              <>
                {/* Summary by Severity */}
                <div className="grid grid-cols-3 gap-4 mb-6">
                  {["critical", "warn", "info"].map((severity) => {
                    const count = healthFindings.filter(f => f.severity === severity).length;
                    const exposure = healthFindings
                      .filter(f => f.severity === severity)
                      .reduce((sum, f) => sum + f.exposure_amount_base, 0);
                    const colors = getSeverityColors(severity);

                    return (
                      <div key={severity} className={`p-4 rounded-lg border ${colors.bg} ${colors.border}`}>
                        <p className="text-xs text-zinc-500 uppercase">{severity}</p>
                        <p className={`text-2xl font-bold ${colors.text}`}>{count}</p>
                        <p className="text-sm text-zinc-400">€{exposure.toLocaleString()}</p>
                      </div>
                    );
                  })}
                </div>

                {healthFindings.map((finding) => (
                  <HealthFindingCard
                    key={finding.id}
                    finding={finding}
                    onViewEvidence={() =>
                      setEvidenceDrawer({
                        isOpen: true,
                        title: finding.category,
                        evidence: finding.sample_evidence_json || [],
                      })
                    }
                  />
                ))}
              </>
            )}
          </div>
        )}

        {/* Invariants Tab */}
        {activeTab === "invariants" && (
          <div className="space-y-4">
            {/* Run Invariants Button */}
            <div className="flex items-center justify-between mb-6">
              <div>
                {invariantRun && (
                  <p className="text-sm text-zinc-500">
                    Last run: {new Date(invariantRun.created_at).toLocaleString()}
                    {invariantRun.summary_json && (
                      <span className="ml-2">
                        ({invariantRun.summary_json.execution_time_ms.toFixed(0)}ms)
                      </span>
                    )}
                  </p>
                )}
              </div>
              <button
                onClick={handleRunInvariants}
                disabled={runningInvariants}
                className="flex items-center gap-2 px-4 py-2 bg-purple-600 hover:bg-purple-500 rounded-lg text-sm font-medium transition-colors"
              >
                {runningInvariants ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    Running...
                  </>
                ) : (
                  <>
                    <Play className="w-4 h-4" />
                    Run Invariants
                  </>
                )}
              </button>
            </div>

            {/* Results */}
            {invariantRun ? (
              <div className="space-y-3">
                {invariantRun.results.map((result) => (
                  <InvariantResultCard
                    key={result.id}
                    result={result}
                    onViewEvidence={() =>
                      setEvidenceDrawer({
                        isOpen: true,
                        title: result.name,
                        evidence: result.evidence_refs_json || [],
                      })
                    }
                  />
                ))}
              </div>
            ) : (
              <div className="text-center py-12 text-zinc-500">
                <Activity className="w-12 h-12 mx-auto mb-3 opacity-50" />
                <p>No invariant results. Click "Run Invariants" to check.</p>
              </div>
            )}
          </div>
        )}

        {/* Lock Gates Tab */}
        {activeTab === "gates" && trustReport && (
          <div className="space-y-4">
            {/* Lock Status */}
            <div className={`p-6 rounded-xl border ${
              trustReport.lock_eligible
                ? "bg-emerald-500/10 border-emerald-500/30"
                : "bg-amber-500/10 border-amber-500/30"
            }`}>
              <div className="flex items-center gap-4">
                {trustReport.lock_eligible ? (
                  <Unlock className="w-8 h-8 text-emerald-400" />
                ) : (
                  <Lock className="w-8 h-8 text-amber-400" />
                )}
                <div>
                  <h3 className="text-lg font-semibold text-zinc-200">
                    {trustReport.lock_eligible
                      ? "Ready to Lock"
                      : "Override Required"}
                  </h3>
                  <p className="text-sm text-zinc-400">
                    {trustReport.lock_eligible
                      ? "All lock gates passed. This snapshot can be locked."
                      : `${trustReport.gate_failures.length} gate(s) failed. CFO override required.`}
                  </p>
                </div>
              </div>
            </div>

            {/* All Gates */}
            <div className="space-y-3">
              {/* Passed gates (if any in gate_failures means failed) */}
              {trustReport.gate_failures.map((gate, idx) => (
                <LockGateCard key={idx} gate={gate} />
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Lock Modal */}
      {trustReport && (
        <LockModal
          isOpen={showLockModal}
          onClose={() => setShowLockModal(false)}
          snapshotId={snapshotId}
          trustReport={trustReport}
          onSuccess={() => {
            loadData();
            onLockSuccess?.();
          }}
        />
      )}

      {/* Evidence Drawer */}
      <EvidenceDrawer
        isOpen={evidenceDrawer.isOpen}
        onClose={() => setEvidenceDrawer({ ...evidenceDrawer, isOpen: false })}
        title={evidenceDrawer.title}
        evidence={evidenceDrawer.evidence}
      />
    </div>
  );
};

export default SnapshotReview;
