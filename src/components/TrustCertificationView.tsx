"use client";

import React, { useState, useEffect } from "react";
import { api } from "@/lib/api";

// ═══════════════════════════════════════════════════════════════════════════════
// TYPES
// ═══════════════════════════════════════════════════════════════════════════════

interface EvidenceRef {
  ref_type: string;
  ref_id: number;
  ref_key?: string;
  amount?: number;
  currency?: string;
  description?: string;
}

interface TrustMetric {
  name: string;
  value: number;
  unit: string;
  status: "pass" | "warn" | "fail" | "skip";
  threshold?: number;
  threshold_type?: string;
  amount_weighted: boolean;
  evidence_count: number;
  evidence: EvidenceRef[];
  details: Record<string, unknown>;
}

interface InvariantCheck {
  name: string;
  passed: boolean;
  severity: "critical" | "error" | "warning";
  message: string;
  evidence_count: number;
  evidence: EvidenceRef[];
  details: Record<string, unknown>;
}

interface LockGate {
  name: string;
  passed: boolean;
  can_override: boolean;
  requires_acknowledgment: boolean;
  metric?: TrustMetric;
  invariant?: InvariantCheck;
  acknowledgment_text_required?: string;
}

interface TrustReport {
  snapshot_id: number;
  snapshot_name: string;
  dataset_id?: string;
  generated_at: string;
  metrics: TrustMetric[];
  invariants: InvariantCheck[];
  lock_gates: LockGate[];
  overall_trust_score: number;
  lock_eligible: boolean;
  lock_blocked_reasons: string[];
}

// ═══════════════════════════════════════════════════════════════════════════════
// UTILITY FUNCTIONS
// ═══════════════════════════════════════════════════════════════════════════════

const formatValue = (value: number, unit: string): string => {
  switch (unit) {
    case "percent":
      return `${value.toFixed(1)}%`;
    case "currency":
      return `€${value.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    case "hours":
      return value < 24 ? `${value.toFixed(1)}h` : `${(value / 24).toFixed(1)}d`;
    case "count":
      return value.toLocaleString();
    default:
      return value.toString();
  }
};

const getStatusColor = (status: string): string => {
  switch (status) {
    case "pass":
      return "text-emerald-400";
    case "warn":
      return "text-amber-400";
    case "fail":
      return "text-red-400";
    case "skip":
      return "text-zinc-500";
    default:
      return "text-zinc-400";
  }
};

const getStatusBg = (status: string): string => {
  switch (status) {
    case "pass":
      return "bg-emerald-500/10 border-emerald-500/30";
    case "warn":
      return "bg-amber-500/10 border-amber-500/30";
    case "fail":
      return "bg-red-500/10 border-red-500/30";
    case "skip":
      return "bg-zinc-500/10 border-zinc-500/30";
    default:
      return "bg-zinc-800 border-zinc-700";
  }
};

const getSeverityColor = (severity: string): string => {
  switch (severity) {
    case "critical":
      return "text-red-500";
    case "error":
      return "text-orange-400";
    case "warning":
      return "text-amber-400";
    default:
      return "text-zinc-400";
  }
};

const getTrustScoreColor = (score: number): string => {
  if (score >= 90) return "text-emerald-400";
  if (score >= 75) return "text-amber-400";
  return "text-red-400";
};

const getTrustScoreLabel = (score: number): string => {
  if (score >= 90) return "High Confidence";
  if (score >= 75) return "Medium Confidence";
  return "Low Confidence";
};

// ═══════════════════════════════════════════════════════════════════════════════
// SUB-COMPONENTS
// ═══════════════════════════════════════════════════════════════════════════════

const TrustScoreGauge: React.FC<{ score: number }> = ({ score }) => {
  const circumference = 2 * Math.PI * 45;
  const strokeDashoffset = circumference - (score / 100) * circumference;
  
  return (
    <div className="relative w-32 h-32">
      <svg className="w-full h-full transform -rotate-90">
        <circle
          cx="64"
          cy="64"
          r="45"
          fill="none"
          stroke="currentColor"
          strokeWidth="8"
          className="text-zinc-800"
        />
        <circle
          cx="64"
          cy="64"
          r="45"
          fill="none"
          stroke="currentColor"
          strokeWidth="8"
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          strokeLinecap="round"
          className={getTrustScoreColor(score)}
          style={{ transition: "stroke-dashoffset 0.5s ease" }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className={`text-2xl font-bold ${getTrustScoreColor(score)}`}>
          {score.toFixed(0)}
        </span>
        <span className="text-xs text-zinc-500">/ 100</span>
      </div>
    </div>
  );
};

const MetricCard: React.FC<{
  metric: TrustMetric;
  onViewEvidence: (metric: TrustMetric) => void;
}> = ({ metric, onViewEvidence }) => {
  return (
    <div className={`p-4 rounded-lg border ${getStatusBg(metric.status)}`}>
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <h4 className="text-sm font-medium text-zinc-300">{metric.name}</h4>
          <div className="mt-1 flex items-baseline gap-2">
            <span className={`text-2xl font-bold ${getStatusColor(metric.status)}`}>
              {formatValue(metric.value, metric.unit)}
            </span>
            {metric.threshold && (
              <span className="text-xs text-zinc-500">
                ({metric.threshold_type === "min" ? "≥" : "≤"} {formatValue(metric.threshold, metric.unit === "currency" ? "percent" : metric.unit)})
              </span>
            )}
          </div>
          {metric.amount_weighted && (
            <span className="text-xs text-zinc-500 mt-1 block">Amount-weighted</span>
          )}
        </div>
        <div className="flex flex-col items-end gap-2">
          <span className={`text-xs px-2 py-0.5 rounded uppercase font-medium ${getStatusColor(metric.status)}`}>
            {metric.status}
          </span>
          {metric.evidence_count > 0 && (
            <button
              onClick={() => onViewEvidence(metric)}
              className="text-xs text-blue-400 hover:text-blue-300 underline"
            >
              {metric.evidence_count} items
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

const InvariantCard: React.FC<{
  invariant: InvariantCheck;
  onViewEvidence: (invariant: InvariantCheck) => void;
}> = ({ invariant, onViewEvidence }) => {
  return (
    <div className={`p-3 rounded-lg border ${invariant.passed ? "bg-emerald-500/5 border-emerald-500/20" : "bg-red-500/5 border-red-500/20"}`}>
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <span className={invariant.passed ? "text-emerald-400" : "text-red-400"}>
              {invariant.passed ? "✓" : "✗"}
            </span>
            <h4 className="text-sm font-medium text-zinc-300">{invariant.name}</h4>
            <span className={`text-xs px-1.5 py-0.5 rounded ${getSeverityColor(invariant.severity)} bg-zinc-800`}>
              {invariant.severity}
            </span>
          </div>
          <p className="text-xs text-zinc-500 mt-1">{invariant.message}</p>
        </div>
        {invariant.evidence_count > 0 && (
          <button
            onClick={() => onViewEvidence(invariant)}
            className="text-xs text-blue-400 hover:text-blue-300 underline"
          >
            {invariant.evidence_count} items
          </button>
        )}
      </div>
    </div>
  );
};

const LockGateCard: React.FC<{
  gate: LockGate;
  acknowledgmentText: string;
  onAcknowledgmentChange: (text: string) => void;
}> = ({ gate, acknowledgmentText, onAcknowledgmentChange }) => {
  const isAcknowledged = acknowledgmentText === gate.acknowledgment_text_required;
  
  return (
    <div className={`p-4 rounded-lg border ${gate.passed ? "bg-emerald-500/5 border-emerald-500/20" : gate.can_override ? "bg-amber-500/5 border-amber-500/20" : "bg-red-500/5 border-red-500/20"}`}>
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <span className={gate.passed ? "text-emerald-400 text-lg" : gate.can_override ? "text-amber-400 text-lg" : "text-red-400 text-lg"}>
              {gate.passed ? "🔓" : gate.can_override ? "⚠️" : "🔒"}
            </span>
            <h4 className="text-sm font-medium text-zinc-300">{gate.name}</h4>
          </div>
          
          {!gate.passed && (
            <div className="mt-2">
              {gate.can_override ? (
                <div className="space-y-2">
                  <p className="text-xs text-amber-400">Override available with acknowledgment:</p>
                  {gate.acknowledgment_text_required && (
                    <div className="bg-zinc-900 p-2 rounded text-xs">
                      <p className="text-zinc-400 mb-2">Required acknowledgment:</p>
                      <p className="text-zinc-300 italic">"{gate.acknowledgment_text_required}"</p>
                      <textarea
                        className="w-full mt-2 p-2 bg-zinc-800 border border-zinc-700 rounded text-xs text-zinc-300 resize-none"
                        placeholder="Type the acknowledgment text exactly as shown above..."
                        rows={2}
                        value={acknowledgmentText}
                        onChange={(e) => onAcknowledgmentChange(e.target.value)}
                      />
                      {isAcknowledged && (
                        <p className="text-emerald-400 text-xs mt-1">✓ Acknowledgment accepted</p>
                      )}
                    </div>
                  )}
                </div>
              ) : (
                <p className="text-xs text-red-400">Cannot be overridden - must be resolved</p>
              )}
            </div>
          )}
        </div>
        
        <div className="flex flex-col items-end">
          <span className={`text-xs px-2 py-0.5 rounded ${gate.passed ? "bg-emerald-500/20 text-emerald-400" : gate.can_override ? "bg-amber-500/20 text-amber-400" : "bg-red-500/20 text-red-400"}`}>
            {gate.passed ? "PASS" : gate.can_override ? "OVERRIDE" : "BLOCKED"}
          </span>
        </div>
      </div>
    </div>
  );
};

const EvidenceModal: React.FC<{
  title: string;
  evidence: EvidenceRef[];
  onClose: () => void;
}> = ({ title, evidence, onClose }) => {
  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50" onClick={onClose}>
      <div className="bg-zinc-900 rounded-lg border border-zinc-700 w-full max-w-2xl max-h-[80vh] overflow-hidden" onClick={(e) => e.stopPropagation()}>
        <div className="p-4 border-b border-zinc-700 flex items-center justify-between">
          <h3 className="text-lg font-semibold text-zinc-200">{title}</h3>
          <button onClick={onClose} className="text-zinc-500 hover:text-zinc-300">✕</button>
        </div>
        <div className="p-4 overflow-y-auto max-h-[60vh]">
          {evidence.length === 0 ? (
            <p className="text-zinc-500 text-center py-4">No evidence items</p>
          ) : (
            <div className="space-y-2">
              {evidence.map((e, idx) => (
                <div key={idx} className="p-3 bg-zinc-800 rounded border border-zinc-700">
                  <div className="flex items-start justify-between">
                    <div>
                      <span className="text-xs text-zinc-500 uppercase">{e.ref_type}</span>
                      <p className="text-sm text-zinc-300">{e.ref_key || `#${e.ref_id}`}</p>
                      {e.description && (
                        <p className="text-xs text-zinc-400 mt-1">{e.description}</p>
                      )}
                    </div>
                    {e.amount && (
                      <span className="text-sm font-mono text-zinc-300">
                        {e.currency || "€"}{e.amount.toLocaleString()}
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// MAIN COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

interface TrustCertificationViewProps {
  snapshotId: number;
  onLockSuccess?: () => void;
}

export const TrustCertificationView: React.FC<TrustCertificationViewProps> = ({
  snapshotId,
  onLockSuccess,
}) => {
  const [report, setReport] = useState<TrustReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [acknowledgments, setAcknowledgments] = useState<Record<string, string>>({});
  const [evidenceModal, setEvidenceModal] = useState<{ title: string; evidence: EvidenceRef[] } | null>(null);
  const [lockLoading, setLockLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<"metrics" | "invariants" | "gates">("metrics");

  useEffect(() => {
    loadTrustReport();
  }, [snapshotId]);

  const loadTrustReport = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.get(`/snapshots/${snapshotId}/trust-report`);
      setReport(res.data);
    } catch (err: unknown) {
      console.error("Failed to load trust report:", err);
      setError("Failed to load trust report");
    } finally {
      setLoading(false);
    }
  };

  const handleAcknowledgmentChange = (gateName: string, text: string) => {
    setAcknowledgments((prev) => ({ ...prev, [gateName]: text }));
  };

  const handleLock = async () => {
    if (!report) return;
    
    setLockLoading(true);
    try {
      const res = await api.post(`/snapshots/${snapshotId}/trust-certification/lock`, {
        user: "current_user", // Replace with actual user
        override_acknowledgments: acknowledgments,
      });
      
      if (res.data.success) {
        alert("Snapshot locked successfully!");
        onLockSuccess?.();
        loadTrustReport();
      }
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: { message?: string; missing_acknowledgments?: Array<{ gate_name: string }> } } } };
      const detail = error.response?.data?.detail;
      if (detail?.missing_acknowledgments) {
        alert(`Missing acknowledgments for: ${detail.missing_acknowledgments.map((a: { gate_name: string }) => a.gate_name).join(", ")}`);
      } else {
        alert(detail?.message || "Lock failed");
      }
    } finally {
      setLockLoading(false);
    }
  };

  const canLock = () => {
    if (!report) return false;
    
    // Check all gates
    for (const gate of report.lock_gates) {
      if (!gate.passed) {
        if (!gate.can_override) return false;
        if (gate.requires_acknowledgment && acknowledgments[gate.name] !== gate.acknowledgment_text_required) {
          return false;
        }
      }
    }
    return true;
  };

  if (loading) {
    return (
      <div className="p-6 text-center">
        <div className="animate-spin w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full mx-auto"></div>
        <p className="text-zinc-400 mt-2">Loading trust certification...</p>
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="p-6 text-center">
        <p className="text-red-400">{error || "Failed to load report"}</p>
        <button onClick={loadTrustReport} className="mt-2 text-blue-400 hover:text-blue-300 underline">
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="bg-zinc-900 rounded-lg border border-zinc-800 overflow-hidden">
      {/* Header */}
      <div className="p-6 border-b border-zinc-800">
        <div className="flex items-start justify-between">
          <div>
            <h2 className="text-xl font-bold text-zinc-100">Trust Certification</h2>
            <p className="text-sm text-zinc-500 mt-1">
              Snapshot: {report.snapshot_name} • Generated: {new Date(report.generated_at).toLocaleString()}
            </p>
            {report.dataset_id && (
              <p className="text-xs text-zinc-600 mt-0.5">Dataset: {report.dataset_id}</p>
            )}
          </div>
          <div className="flex items-center gap-4">
            <TrustScoreGauge score={report.overall_trust_score} />
            <div className="text-right">
              <p className={`text-sm font-medium ${getTrustScoreColor(report.overall_trust_score)}`}>
                {getTrustScoreLabel(report.overall_trust_score)}
              </p>
              <p className={`text-xs mt-1 ${report.lock_eligible ? "text-emerald-400" : "text-amber-400"}`}>
                {report.lock_eligible ? "✓ Lock Eligible" : "⚠ Lock Requires Override"}
              </p>
            </div>
          </div>
        </div>
        
        {report.lock_blocked_reasons.length > 0 && (
          <div className="mt-4 p-3 bg-red-500/10 border border-red-500/30 rounded-lg">
            <p className="text-sm text-red-400 font-medium">Lock Blocked:</p>
            <ul className="mt-1 text-xs text-red-300">
              {report.lock_blocked_reasons.map((reason, idx) => (
                <li key={idx}>• {reason}</li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* Tabs */}
      <div className="border-b border-zinc-800">
        <div className="flex">
          {(["metrics", "invariants", "gates"] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab
                  ? "border-blue-500 text-blue-400"
                  : "border-transparent text-zinc-500 hover:text-zinc-300"
              }`}
            >
              {tab === "metrics" && `Metrics (${report.metrics.length})`}
              {tab === "invariants" && `Invariants (${report.invariants.length})`}
              {tab === "gates" && `Lock Gates (${report.lock_gates.length})`}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div className="p-6">
        {activeTab === "metrics" && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {report.metrics.map((metric, idx) => (
              <MetricCard
                key={idx}
                metric={metric}
                onViewEvidence={(m) => setEvidenceModal({ title: m.name, evidence: m.evidence })}
              />
            ))}
          </div>
        )}

        {activeTab === "invariants" && (
          <div className="space-y-3">
            {report.invariants.map((inv, idx) => (
              <InvariantCard
                key={idx}
                invariant={inv}
                onViewEvidence={(i) => setEvidenceModal({ title: i.name, evidence: i.evidence })}
              />
            ))}
          </div>
        )}

        {activeTab === "gates" && (
          <div className="space-y-4">
            {report.lock_gates.map((gate, idx) => (
              <LockGateCard
                key={idx}
                gate={gate}
                acknowledgmentText={acknowledgments[gate.name] || ""}
                onAcknowledgmentChange={(text) => handleAcknowledgmentChange(gate.name, text)}
              />
            ))}
            
            <div className="pt-4 border-t border-zinc-800">
              <button
                onClick={handleLock}
                disabled={!canLock() || lockLoading}
                className={`w-full py-3 rounded-lg font-medium transition-colors ${
                  canLock()
                    ? "bg-blue-600 hover:bg-blue-500 text-white"
                    : "bg-zinc-800 text-zinc-500 cursor-not-allowed"
                }`}
              >
                {lockLoading ? "Locking..." : canLock() ? "🔒 Lock Snapshot" : "Complete all gates to lock"}
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Evidence Modal */}
      {evidenceModal && (
        <EvidenceModal
          title={evidenceModal.title}
          evidence={evidenceModal.evidence}
          onClose={() => setEvidenceModal(null)}
        />
      )}
    </div>
  );
};

export default TrustCertificationView;
