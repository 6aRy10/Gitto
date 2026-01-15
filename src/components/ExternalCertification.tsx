"use client";

import React, { useState, useCallback, useEffect } from "react";
import {
  Shield, Upload, FileText, CheckCircle2, XCircle, AlertTriangle,
  Clock, ArrowLeftRight, Database, MapPin, RefreshCw, Download,
  ChevronRight, Eye, Building2, Banknote, Calendar, ExternalLink
} from "lucide-react";
import { api } from "@/lib/api";
import { EvidenceDrawer, EvidenceRef } from "./ui/evidence-drawer";
import { TruthBadge, TruthLevel } from "./ui/truth-badge";
import { AsOfStamp, DualAsOfStamp } from "./ui/as-of-stamp";

// ═══════════════════════════════════════════════════════════════════════════════
// TYPES
// ═══════════════════════════════════════════════════════════════════════════════

interface Discrepancy {
  id: number;
  category: string;
  description?: string;
  amount_base: number;
  currency?: string;
  evidence_refs?: EvidenceRef[];
  is_resolved: boolean;
}

interface AccountComparison {
  id: number;
  external_account_id?: string;
  external_account_name?: string;
  external_amount_base?: number;
  gitto_account_id?: number;
  gitto_account_name?: string;
  gitto_amount_base?: number;
  difference_base?: number;
  is_matched: boolean;
  primary_category?: string;
}

interface CertificationReport {
  id: number;
  snapshot_id: number;
  import_id: number;
  created_at: string;
  status: string;
  external_total_base: number;
  gitto_total_base: number;
  gross_difference_base: number;
  net_difference_base: number;
  explained_by_unmatched: number;
  explained_by_fx_policy: number;
  explained_by_stale_data: number;
  explained_by_mapping_gap: number;
  explained_by_timing: number;
  explained_by_rounding: number;
  unexplained_amount: number;
  certification_score: number;
  is_certified: boolean;
  certified_at?: string;
  certified_by?: string;
  discrepancies: Discrepancy[];
  account_comparisons: AccountComparison[];
}

interface ImportRecord {
  id: number;
  snapshot_id: number;
  system_name: string;
  file_name: string;
  external_as_of: string;
  gitto_as_of: string;
  row_count: number;
  external_total_base: number;
}

// ═══════════════════════════════════════════════════════════════════════════════
// HELPER FUNCTIONS
// ═══════════════════════════════════════════════════════════════════════════════

const getCategoryIcon = (category: string) => {
  switch (category) {
    case "unmatched_bank_txn":
      return Banknote;
    case "fx_policy_difference":
      return ArrowLeftRight;
    case "stale_data":
      return Clock;
    case "mapping_gap":
      return MapPin;
    case "timing_difference":
      return Clock;
    case "rounding":
      return RefreshCw;
    default:
      return AlertTriangle;
  }
};

const getCategoryColor = (category: string) => {
  switch (category) {
    case "unmatched_bank_txn":
      return { bg: "bg-amber-500/10", border: "border-amber-500/30", text: "text-amber-400" };
    case "fx_policy_difference":
      return { bg: "bg-purple-500/10", border: "border-purple-500/30", text: "text-purple-400" };
    case "stale_data":
      return { bg: "bg-orange-500/10", border: "border-orange-500/30", text: "text-orange-400" };
    case "mapping_gap":
      return { bg: "bg-blue-500/10", border: "border-blue-500/30", text: "text-blue-400" };
    case "timing_difference":
      return { bg: "bg-cyan-500/10", border: "border-cyan-500/30", text: "text-cyan-400" };
    case "rounding":
      return { bg: "bg-zinc-500/10", border: "border-zinc-500/30", text: "text-zinc-400" };
    case "unknown":
      return { bg: "bg-red-500/10", border: "border-red-500/30", text: "text-red-400" };
    default:
      return { bg: "bg-zinc-500/10", border: "border-zinc-500/30", text: "text-zinc-400" };
  }
};

const formatCurrency = (amount: number, currency: string = "EUR"): string => {
  const symbol = currency === "EUR" ? "€" : currency === "USD" ? "$" : currency;
  const sign = amount < 0 ? "-" : "";
  return `${sign}${symbol}${Math.abs(amount).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
};

const getCategoryLabel = (category: string): string => {
  const labels: Record<string, string> = {
    unmatched_bank_txn: "Unmatched Bank Transactions",
    fx_policy_difference: "FX Policy Difference",
    stale_data: "Stale Data",
    mapping_gap: "Mapping Gap",
    timing_difference: "Timing Difference",
    rounding: "Rounding",
    unknown: "Unknown",
  };
  return labels[category] || category.replace(/_/g, " ");
};

// ═══════════════════════════════════════════════════════════════════════════════
// UPLOAD STEP COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

const UploadStep: React.FC<{
  snapshotId: number;
  onImportComplete: (importRecord: ImportRecord) => void;
}> = ({ snapshotId, onImportComplete }) => {
  const [file, setFile] = useState<File | null>(null);
  const [systemName, setSystemName] = useState("");
  const [externalAsOf, setExternalAsOf] = useState("");
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleUpload = async () => {
    if (!file || !systemName || !externalAsOf) {
      setError("Please fill all required fields");
      return;
    }

    setUploading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("snapshot_id", snapshotId.toString());
      formData.append("system_name", systemName);
      formData.append("external_as_of", externalAsOf);
      formData.append("imported_by", "ui");

      const response = await api.post("/external-certification/import", formData, {
        headers: { "Content-Type": "multipart/form-data" }
      });

      onImportComplete(response.data);
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } };
      setError(error.response?.data?.detail || "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  const commonSystems = [
    "SAP TRM",
    "Kyriba",
    "GTreasury",
    "FIS",
    "ION Treasury",
    "Finastra",
    "Bloomberg TOMS",
    "Other"
  ];

  return (
    <div className="space-y-6">
      <div className="p-6 bg-zinc-800/50 rounded-xl border border-zinc-700">
        <h3 className="text-lg font-semibold text-zinc-200 mb-4 flex items-center gap-2">
          <Upload className="w-5 h-5 text-blue-400" />
          Import External TMS Data
        </h3>

        <div className="space-y-4">
          {/* File Upload */}
          <div>
            <label className="block text-sm font-medium text-zinc-400 mb-2">
              Cash Position Export (CSV) <span className="text-red-400">*</span>
            </label>
            <div className="border-2 border-dashed border-zinc-600 rounded-lg p-6 text-center hover:border-blue-500/50 transition-colors">
              <input
                type="file"
                accept=".csv"
                onChange={(e) => setFile(e.target.files?.[0] || null)}
                className="hidden"
                id="tms-file"
              />
              <label htmlFor="tms-file" className="cursor-pointer">
                {file ? (
                  <div className="flex items-center justify-center gap-2">
                    <FileText className="w-6 h-6 text-emerald-400" />
                    <span className="text-zinc-200">{file.name}</span>
                  </div>
                ) : (
                  <div>
                    <Upload className="w-8 h-8 text-zinc-500 mx-auto mb-2" />
                    <p className="text-zinc-400">Click to upload or drag and drop</p>
                    <p className="text-xs text-zinc-500 mt-1">CSV file from your TMS</p>
                  </div>
                )}
              </label>
            </div>
          </div>

          {/* System Name */}
          <div>
            <label className="block text-sm font-medium text-zinc-400 mb-2">
              Source System <span className="text-red-400">*</span>
            </label>
            <select
              value={systemName}
              onChange={(e) => setSystemName(e.target.value)}
              className="w-full p-3 bg-zinc-900 border border-zinc-700 rounded-lg text-zinc-200 focus:outline-none focus:border-blue-500"
            >
              <option value="">Select TMS...</option>
              {commonSystems.map(sys => (
                <option key={sys} value={sys}>{sys}</option>
              ))}
            </select>
          </div>

          {/* External As-Of Date */}
          <div>
            <label className="block text-sm font-medium text-zinc-400 mb-2">
              External Data As-Of <span className="text-red-400">*</span>
            </label>
            <input
              type="datetime-local"
              value={externalAsOf}
              onChange={(e) => setExternalAsOf(e.target.value)}
              className="w-full p-3 bg-zinc-900 border border-zinc-700 rounded-lg text-zinc-200 focus:outline-none focus:border-blue-500"
            />
            <p className="text-xs text-zinc-500 mt-1">
              When was this data captured in the external system?
            </p>
          </div>

          {/* Error */}
          {error && (
            <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-lg">
              <p className="text-sm text-red-400">{error}</p>
            </div>
          )}

          {/* Upload Button */}
          <button
            onClick={handleUpload}
            disabled={uploading || !file || !systemName || !externalAsOf}
            className={`w-full py-3 rounded-lg font-medium transition-colors flex items-center justify-center gap-2 ${
              uploading || !file || !systemName || !externalAsOf
                ? "bg-zinc-800 text-zinc-500 cursor-not-allowed"
                : "bg-blue-600 hover:bg-blue-500 text-white"
            }`}
          >
            {uploading ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" />
                Importing...
              </>
            ) : (
              <>
                <Upload className="w-4 h-4" />
                Import & Compare
              </>
            )}
          </button>
        </div>
      </div>

      {/* Expected CSV Format */}
      <div className="p-4 bg-zinc-800/30 rounded-lg border border-zinc-700/50">
        <h4 className="text-sm font-medium text-zinc-400 mb-2">Expected CSV Columns</h4>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
          {["account_id", "account_name", "currency", "amount", "bank_name", "fx_rate", "position_date"].map(col => (
            <div key={col} className="px-2 py-1 bg-zinc-800 rounded text-zinc-500">
              {col}
            </div>
          ))}
        </div>
        <p className="text-xs text-zinc-500 mt-2">
          Column names are flexible (e.g., "balance" = "amount", "ccy" = "currency")
        </p>
      </div>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// DISCREPANCY CARD COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

const DiscrepancyCard: React.FC<{
  discrepancy: Discrepancy;
  onViewEvidence: () => void;
}> = ({ discrepancy, onViewEvidence }) => {
  const Icon = getCategoryIcon(discrepancy.category);
  const colors = getCategoryColor(discrepancy.category);

  return (
    <div className={`p-4 rounded-lg border ${colors.bg} ${colors.border}`}>
      <div className="flex items-start justify-between">
        <div className="flex items-start gap-3">
          <div className={`p-2 rounded-lg bg-zinc-800/50`}>
            <Icon className={`w-5 h-5 ${colors.text}`} />
          </div>
          <div>
            <h4 className="text-sm font-medium text-zinc-200">
              {getCategoryLabel(discrepancy.category)}
            </h4>
            {discrepancy.description && (
              <p className="text-xs text-zinc-400 mt-1">{discrepancy.description}</p>
            )}
            {discrepancy.is_resolved && (
              <span className="inline-flex items-center gap-1 text-xs text-emerald-400 mt-1">
                <CheckCircle2 className="w-3 h-3" />
                Resolved
              </span>
            )}
          </div>
        </div>

        <div className="text-right">
          <p className={`text-lg font-bold ${colors.text}`}>
            {formatCurrency(discrepancy.amount_base)}
          </p>
          {discrepancy.evidence_refs && discrepancy.evidence_refs.length > 0 && (
            <button
              onClick={onViewEvidence}
              className="mt-1 text-xs text-blue-400 hover:text-blue-300 flex items-center gap-1"
            >
              <Eye className="w-3 h-3" />
              {discrepancy.evidence_refs.length} evidence
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// CERTIFICATION REPORT VIEW
// ═══════════════════════════════════════════════════════════════════════════════

const CertificationReportView: React.FC<{
  report: CertificationReport;
  importRecord: ImportRecord;
  onCertify: () => void;
  onExport: () => void;
}> = ({ report, importRecord, onCertify, onExport }) => {
  const [activeTab, setActiveTab] = useState<"summary" | "discrepancies" | "accounts">("summary");
  const [evidenceDrawer, setEvidenceDrawer] = useState<{
    isOpen: boolean;
    title: string;
    evidence: EvidenceRef[];
  }>({ isOpen: false, title: "", evidence: [] });

  const explainedTotal = Math.abs(report.explained_by_unmatched) +
    Math.abs(report.explained_by_fx_policy) +
    Math.abs(report.explained_by_stale_data) +
    Math.abs(report.explained_by_mapping_gap) +
    Math.abs(report.explained_by_timing) +
    Math.abs(report.explained_by_rounding);

  const explainedPct = report.gross_difference_base !== 0
    ? (explainedTotal / Math.abs(report.gross_difference_base)) * 100
    : 100;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="p-6 bg-zinc-800/50 rounded-xl border border-zinc-700">
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-3">
              <Shield className={`w-8 h-8 ${report.is_certified ? "text-emerald-400" : "text-amber-400"}`} />
              <div>
                <h2 className="text-xl font-bold text-zinc-100">
                  External System Certification
                </h2>
                <p className="text-sm text-zinc-500">
                  {importRecord.system_name} vs Gitto Bank-Truth
                </p>
              </div>
            </div>

            {/* Timestamps */}
            <div className="mt-4">
              <DualAsOfStamp
                bankTimestamp={importRecord.gitto_as_of}
                erpTimestamp={importRecord.external_as_of}
              />
            </div>
          </div>

          {/* Certification Score */}
          <div className="text-right">
            <div className={`text-5xl font-bold ${
              report.certification_score >= 90 ? "text-emerald-400" :
              report.certification_score >= 70 ? "text-amber-400" : "text-red-400"
            }`}>
              {report.certification_score.toFixed(0)}
            </div>
            <p className="text-sm text-zinc-500">Certification Score</p>
            {report.is_certified && (
              <div className="mt-2 flex items-center gap-1 text-emerald-400 justify-end">
                <CheckCircle2 className="w-4 h-4" />
                <span className="text-sm">Certified</span>
              </div>
            )}
          </div>
        </div>

        {/* Summary Metrics */}
        <div className="mt-6 grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="p-4 bg-zinc-900/50 rounded-lg">
            <p className="text-xs text-zinc-500 uppercase tracking-wider">External Total</p>
            <p className="text-xl font-bold text-zinc-200">
              {formatCurrency(report.external_total_base)}
            </p>
            <TruthBadge level="modeled" compact dark />
          </div>
          <div className="p-4 bg-zinc-900/50 rounded-lg">
            <p className="text-xs text-zinc-500 uppercase tracking-wider">Gitto Total</p>
            <p className="text-xl font-bold text-zinc-200">
              {formatCurrency(report.gitto_total_base)}
            </p>
            <TruthBadge level="bank-true" compact dark />
          </div>
          <div className="p-4 bg-zinc-900/50 rounded-lg">
            <p className="text-xs text-zinc-500 uppercase tracking-wider">Gross Difference</p>
            <p className={`text-xl font-bold ${
              Math.abs(report.gross_difference_base) < 1000 ? "text-emerald-400" : "text-amber-400"
            }`}>
              {formatCurrency(report.gross_difference_base)}
            </p>
          </div>
          <div className="p-4 bg-zinc-900/50 rounded-lg">
            <p className="text-xs text-zinc-500 uppercase tracking-wider">Explained</p>
            <p className={`text-xl font-bold ${
              explainedPct >= 95 ? "text-emerald-400" : "text-amber-400"
            }`}>
              {explainedPct.toFixed(1)}%
            </p>
          </div>
        </div>

        {/* Actions */}
        <div className="mt-6 flex items-center gap-3">
          <button
            onClick={onExport}
            className="flex items-center gap-2 px-4 py-2 bg-zinc-700 hover:bg-zinc-600 rounded-lg text-sm transition-colors"
          >
            <Download className="w-4 h-4" />
            Export Report
          </button>
          {!report.is_certified && (
            <button
              onClick={onCertify}
              disabled={report.certification_score < 80}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                report.certification_score >= 80
                  ? "bg-emerald-600 hover:bg-emerald-500 text-white"
                  : "bg-zinc-800 text-zinc-500 cursor-not-allowed"
              }`}
            >
              <CheckCircle2 className="w-4 h-4" />
              Certify Report
            </button>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-zinc-800">
        <div className="flex gap-1">
          {[
            { id: "summary", label: "Attribution Summary" },
            { id: "discrepancies", label: `Discrepancies (${report.discrepancies.length})` },
            { id: "accounts", label: `Account Comparison (${report.account_comparisons.length})` },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as typeof activeTab)}
              className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab.id
                  ? "border-blue-500 text-blue-400"
                  : "border-transparent text-zinc-500 hover:text-zinc-300"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Tab Content */}
      <div>
        {/* Summary Tab */}
        {activeTab === "summary" && (
          <div className="space-y-4">
            <h3 className="text-lg font-semibold text-zinc-200">Difference Attribution</h3>
            <p className="text-sm text-zinc-400">
              How the {formatCurrency(report.gross_difference_base)} difference is explained:
            </p>

            <div className="space-y-3">
              {[
                { category: "unmatched_bank_txn", amount: report.explained_by_unmatched },
                { category: "fx_policy_difference", amount: report.explained_by_fx_policy },
                { category: "stale_data", amount: report.explained_by_stale_data },
                { category: "mapping_gap", amount: report.explained_by_mapping_gap },
                { category: "timing_difference", amount: report.explained_by_timing },
                { category: "rounding", amount: report.explained_by_rounding },
                { category: "unknown", amount: report.unexplained_amount },
              ].filter(item => item.amount !== 0).map((item) => {
                const Icon = getCategoryIcon(item.category);
                const colors = getCategoryColor(item.category);
                const pct = report.gross_difference_base !== 0
                  ? (Math.abs(item.amount) / Math.abs(report.gross_difference_base)) * 100
                  : 0;

                return (
                  <div
                    key={item.category}
                    className={`p-4 rounded-lg border ${colors.bg} ${colors.border}`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <Icon className={`w-5 h-5 ${colors.text}`} />
                        <span className="text-sm font-medium text-zinc-200">
                          {getCategoryLabel(item.category)}
                        </span>
                      </div>
                      <div className="text-right">
                        <span className={`text-lg font-bold ${colors.text}`}>
                          {formatCurrency(item.amount)}
                        </span>
                        <span className="text-xs text-zinc-500 ml-2">
                          ({pct.toFixed(1)}%)
                        </span>
                      </div>
                    </div>
                    <div className="mt-2 h-2 bg-zinc-800 rounded-full overflow-hidden">
                      <div
                        className={`h-full ${colors.text.replace("text-", "bg-")}`}
                        style={{ width: `${Math.min(100, pct)}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Discrepancies Tab */}
        {activeTab === "discrepancies" && (
          <div className="space-y-4">
            {report.discrepancies.length === 0 ? (
              <div className="text-center py-12 text-zinc-500">
                <CheckCircle2 className="w-12 h-12 mx-auto mb-3 opacity-50" />
                <p>No discrepancies found</p>
              </div>
            ) : (
              report.discrepancies.map((disc) => (
                <DiscrepancyCard
                  key={disc.id}
                  discrepancy={disc}
                  onViewEvidence={() =>
                    setEvidenceDrawer({
                      isOpen: true,
                      title: getCategoryLabel(disc.category),
                      evidence: disc.evidence_refs || [],
                    })
                  }
                />
              ))
            )}
          </div>
        )}

        {/* Accounts Tab */}
        {activeTab === "accounts" && (
          <div className="space-y-3">
            {report.account_comparisons.map((comp) => (
              <div
                key={comp.id}
                className={`p-4 rounded-lg border ${
                  comp.is_matched && Math.abs(comp.difference_base || 0) < 100
                    ? "bg-emerald-500/5 border-emerald-500/20"
                    : comp.is_matched
                      ? "bg-amber-500/5 border-amber-500/20"
                      : "bg-red-500/5 border-red-500/20"
                }`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <Building2 className="w-4 h-4 text-zinc-500" />
                      <span className="text-sm font-medium text-zinc-200">
                        {comp.external_account_name || comp.gitto_account_name || "Unknown Account"}
                      </span>
                      {comp.is_matched ? (
                        <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                      ) : (
                        <XCircle className="w-4 h-4 text-red-400" />
                      )}
                    </div>
                    {comp.primary_category && (
                      <span className={`text-xs mt-1 inline-block ${getCategoryColor(comp.primary_category).text}`}>
                        {getCategoryLabel(comp.primary_category)}
                      </span>
                    )}
                  </div>

                  <div className="grid grid-cols-3 gap-6 text-right">
                    <div>
                      <p className="text-xs text-zinc-500">External</p>
                      <p className="text-sm font-mono text-zinc-300">
                        {comp.external_amount_base !== undefined
                          ? formatCurrency(comp.external_amount_base)
                          : "—"}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-zinc-500">Gitto</p>
                      <p className="text-sm font-mono text-zinc-300">
                        {comp.gitto_amount_base !== undefined
                          ? formatCurrency(comp.gitto_amount_base)
                          : "—"}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-zinc-500">Diff</p>
                      <p className={`text-sm font-mono font-bold ${
                        Math.abs(comp.difference_base || 0) < 100
                          ? "text-emerald-400"
                          : "text-amber-400"
                      }`}>
                        {comp.difference_base !== undefined
                          ? formatCurrency(comp.difference_base)
                          : "—"}
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

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

// ═══════════════════════════════════════════════════════════════════════════════
// MAIN COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

interface ExternalCertificationProps {
  snapshotId: number;
}

export const ExternalCertification: React.FC<ExternalCertificationProps> = ({ snapshotId }) => {
  const [step, setStep] = useState<"upload" | "report">("upload");
  const [importRecord, setImportRecord] = useState<ImportRecord | null>(null);
  const [report, setReport] = useState<CertificationReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleImportComplete = async (record: ImportRecord) => {
    setImportRecord(record);
    setLoading(true);
    setError(null);

    try {
      // Generate certification report
      const response = await api.post(`/external-certification/imports/${record.id}/generate-report`);
      setReport(response.data);
      setStep("report");
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } };
      setError(error.response?.data?.detail || "Failed to generate report");
    } finally {
      setLoading(false);
    }
  };

  const handleCertify = async () => {
    if (!report) return;

    try {
      await api.post(`/external-certification/reports/${report.id}/certify`, {
        certified_by: "current_user",
        notes: "Certified via UI"
      });

      // Refresh report
      const response = await api.get(`/external-certification/reports/${report.id}`);
      setReport(response.data);
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } };
      alert(error.response?.data?.detail || "Certification failed");
    }
  };

  const handleExport = async () => {
    if (!report) return;

    try {
      const response = await api.get(`/external-certification/reports/${report.id}/export`);
      
      // Download as JSON
      const blob = new Blob([JSON.stringify(response.data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `certification_report_${report.id}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      alert("Export failed");
    }
  };

  if (loading) {
    return (
      <div className="p-8 text-center">
        <div className="animate-spin w-10 h-10 border-3 border-blue-500 border-t-transparent rounded-full mx-auto"></div>
        <p className="text-zinc-400 mt-4">Generating certification report...</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 p-6">
      <div className="max-w-5xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-2xl font-bold flex items-center gap-3">
            <Shield className="w-8 h-8 text-purple-500" />
            External System Certification
          </h1>
          <p className="text-zinc-500 mt-1">
            Compare external TMS cash positions against Gitto bank-truth totals
          </p>
        </div>

        {/* Error */}
        {error && (
          <div className="mb-6 p-4 bg-red-500/10 border border-red-500/30 rounded-lg">
            <p className="text-red-400">{error}</p>
          </div>
        )}

        {/* Steps */}
        {step === "upload" && (
          <UploadStep
            snapshotId={snapshotId}
            onImportComplete={handleImportComplete}
          />
        )}

        {step === "report" && report && importRecord && (
          <CertificationReportView
            report={report}
            importRecord={importRecord}
            onCertify={handleCertify}
            onExport={handleExport}
          />
        )}

        {/* Back Button */}
        {step === "report" && (
          <button
            onClick={() => {
              setStep("upload");
              setReport(null);
              setImportRecord(null);
            }}
            className="mt-6 text-sm text-zinc-500 hover:text-zinc-300"
          >
            ← Import another file
          </button>
        )}
      </div>
    </div>
  );
};

export default ExternalCertification;
