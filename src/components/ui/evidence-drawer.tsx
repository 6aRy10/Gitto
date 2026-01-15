"use client";

import React, { useState } from "react";
import { X, ChevronRight, ExternalLink, FileText, Building2, CreditCard, Receipt, ArrowLeftRight, TrendingUp, Database } from "lucide-react";
import { TruthBadge, getTruthLevelFromSource, TruthLevel } from "./truth-badge";

// ═══════════════════════════════════════════════════════════════════════════════
// TYPES
// ═══════════════════════════════════════════════════════════════════════════════

export interface EvidenceRef {
  type: string;
  id: number | string;
  amount?: number;
  currency?: string;
  date?: string;
  reference?: string;
  counterparty?: string;
  document_number?: string;
  customer?: string;
  description?: string;
  details?: Record<string, unknown>;
  truth_level?: TruthLevel;
}

interface EvidenceDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  subtitle?: string;
  evidence: EvidenceRef[];
  asOfDate?: string;
  onDrilldown?: (ref: EvidenceRef) => void;
}

// ═══════════════════════════════════════════════════════════════════════════════
// HELPER FUNCTIONS
// ═══════════════════════════════════════════════════════════════════════════════

const getEvidenceIcon = (type: string) => {
  switch (type.toLowerCase()) {
    case "invoice":
      return FileText;
    case "bank_txn":
    case "bank_transaction":
      return CreditCard;
    case "vendor_bill":
    case "bill":
      return Receipt;
    case "reconciliation":
      return ArrowLeftRight;
    case "forecast":
    case "forecast_row":
      return TrendingUp;
    case "dataset":
      return Database;
    case "customer":
    case "counterparty":
      return Building2;
    default:
      return FileText;
  }
};

const getEvidenceTypeBadge = (type: string): { bg: string; text: string } => {
  switch (type.toLowerCase()) {
    case "invoice":
      return { bg: "bg-blue-500/20", text: "text-blue-400" };
    case "bank_txn":
    case "bank_transaction":
      return { bg: "bg-emerald-500/20", text: "text-emerald-400" };
    case "vendor_bill":
    case "bill":
      return { bg: "bg-orange-500/20", text: "text-orange-400" };
    case "reconciliation":
      return { bg: "bg-purple-500/20", text: "text-purple-400" };
    case "forecast":
    case "forecast_row":
      return { bg: "bg-amber-500/20", text: "text-amber-400" };
    case "dataset":
      return { bg: "bg-cyan-500/20", text: "text-cyan-400" };
    default:
      return { bg: "bg-zinc-500/20", text: "text-zinc-400" };
  }
};

const formatCurrency = (amount: number, currency: string = "EUR"): string => {
  const symbol = currency === "EUR" ? "€" : currency === "USD" ? "$" : currency === "GBP" ? "£" : currency;
  return `${symbol}${amount.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
};

// ═══════════════════════════════════════════════════════════════════════════════
// EVIDENCE ITEM COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

const EvidenceItem: React.FC<{
  evidence: EvidenceRef;
  onDrilldown?: (ref: EvidenceRef) => void;
}> = ({ evidence, onDrilldown }) => {
  const Icon = getEvidenceIcon(evidence.type);
  const badge = getEvidenceTypeBadge(evidence.type);
  const truthLevel = evidence.truth_level || getTruthLevelFromSource(evidence.type === "bank_txn" ? "bank" : evidence.type === "invoice" ? "reconciled" : "modeled");

  return (
    <div className="group p-4 bg-zinc-800/50 hover:bg-zinc-800 rounded-lg border border-zinc-700/50 hover:border-zinc-600 transition-all">
      <div className="flex items-start gap-3">
        {/* Icon */}
        <div className={`p-2 rounded-lg ${badge.bg}`}>
          <Icon className={`w-4 h-4 ${badge.text}`} />
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          {/* Header Row */}
          <div className="flex items-center gap-2 flex-wrap">
            <span className={`text-xs px-2 py-0.5 rounded font-medium ${badge.bg} ${badge.text} uppercase`}>
              {evidence.type.replace(/_/g, " ")}
            </span>
            <span className="text-sm font-mono text-zinc-300">
              {evidence.document_number || evidence.reference || `#${evidence.id}`}
            </span>
            <TruthBadge level={truthLevel} compact showLabel={false} />
          </div>

          {/* Details Row */}
          <div className="mt-2 flex items-center gap-4 text-xs text-zinc-400">
            {evidence.customer && (
              <span className="flex items-center gap-1">
                <Building2 className="w-3 h-3" />
                {evidence.customer}
              </span>
            )}
            {evidence.counterparty && (
              <span className="flex items-center gap-1">
                <Building2 className="w-3 h-3" />
                {evidence.counterparty}
              </span>
            )}
            {evidence.date && (
              <span>{new Date(evidence.date).toLocaleDateString()}</span>
            )}
          </div>

          {/* Description */}
          {evidence.description && (
            <p className="mt-1 text-xs text-zinc-500 truncate">{evidence.description}</p>
          )}
        </div>

        {/* Amount & Actions */}
        <div className="flex flex-col items-end gap-2">
          {evidence.amount !== undefined && (
            <span className="text-sm font-mono font-medium text-zinc-200">
              {formatCurrency(evidence.amount, evidence.currency)}
            </span>
          )}
          {onDrilldown && (
            <button
              onClick={() => onDrilldown(evidence)}
              className="opacity-0 group-hover:opacity-100 text-xs text-blue-400 hover:text-blue-300 flex items-center gap-1 transition-opacity"
            >
              View <ExternalLink className="w-3 h-3" />
            </button>
          )}
        </div>
      </div>

      {/* Extra Details (collapsed by default) */}
      {evidence.details && Object.keys(evidence.details).length > 0 && (
        <details className="mt-3">
          <summary className="text-xs text-zinc-500 cursor-pointer hover:text-zinc-400">
            Show details
          </summary>
          <div className="mt-2 p-2 bg-zinc-900 rounded text-xs font-mono text-zinc-400">
            <pre className="whitespace-pre-wrap">
              {JSON.stringify(evidence.details, null, 2)}
            </pre>
          </div>
        </details>
      )}
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// MAIN DRAWER COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

export const EvidenceDrawer: React.FC<EvidenceDrawerProps> = ({
  isOpen,
  onClose,
  title,
  subtitle,
  evidence,
  asOfDate,
  onDrilldown,
}) => {
  const [filterType, setFilterType] = useState<string>("all");

  // Get unique types for filter
  const evidenceTypes = ["all", ...new Set(evidence.map(e => e.type))];

  // Filter evidence
  const filteredEvidence = filterType === "all" 
    ? evidence 
    : evidence.filter(e => e.type === filterType);

  // Calculate totals
  const totalAmount = evidence.reduce((sum, e) => sum + (e.amount || 0), 0);

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div 
        className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40"
        onClick={onClose}
      />

      {/* Drawer */}
      <div className="fixed right-0 top-0 h-full w-full max-w-xl bg-zinc-900 border-l border-zinc-800 shadow-2xl z-50 flex flex-col">
        {/* Header */}
        <div className="flex-shrink-0 p-6 border-b border-zinc-800">
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <h2 className="text-lg font-semibold text-zinc-100">{title}</h2>
              {subtitle && (
                <p className="text-sm text-zinc-500 mt-1">{subtitle}</p>
              )}
            </div>
            <button
              onClick={onClose}
              className="p-2 text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 rounded-lg transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* As-of stamp */}
          {asOfDate && (
            <div className="mt-3 flex items-center gap-2 text-xs text-zinc-500">
              <span className="px-2 py-1 bg-zinc-800 rounded">
                As of: {new Date(asOfDate).toLocaleString()}
              </span>
            </div>
          )}

          {/* Summary */}
          <div className="mt-4 grid grid-cols-2 gap-4">
            <div className="p-3 bg-zinc-800/50 rounded-lg">
              <p className="text-xs text-zinc-500">Evidence Items</p>
              <p className="text-xl font-bold text-zinc-200">{evidence.length}</p>
            </div>
            <div className="p-3 bg-zinc-800/50 rounded-lg">
              <p className="text-xs text-zinc-500">Total Exposure</p>
              <p className="text-xl font-bold text-zinc-200">{formatCurrency(totalAmount)}</p>
            </div>
          </div>

          {/* Filter */}
          {evidenceTypes.length > 2 && (
            <div className="mt-4 flex gap-2 flex-wrap">
              {evidenceTypes.map(type => (
                <button
                  key={type}
                  onClick={() => setFilterType(type)}
                  className={`px-3 py-1.5 text-xs rounded-full transition-colors ${
                    filterType === type
                      ? "bg-blue-500/20 text-blue-400 border border-blue-500/50"
                      : "bg-zinc-800 text-zinc-400 border border-zinc-700 hover:border-zinc-600"
                  }`}
                >
                  {type === "all" ? "All" : type.replace(/_/g, " ")}
                  {type !== "all" && (
                    <span className="ml-1 text-zinc-500">
                      ({evidence.filter(e => e.type === type).length})
                    </span>
                  )}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4">
          {filteredEvidence.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-zinc-500">
              <FileText className="w-12 h-12 mb-3 opacity-50" />
              <p>No evidence items</p>
            </div>
          ) : (
            <div className="space-y-3">
              {filteredEvidence.map((ref, idx) => (
                <EvidenceItem 
                  key={`${ref.type}-${ref.id}-${idx}`} 
                  evidence={ref}
                  onDrilldown={onDrilldown}
                />
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex-shrink-0 p-4 border-t border-zinc-800 bg-zinc-900/50">
          <div className="flex items-center justify-between text-xs text-zinc-500">
            <span>
              Showing {filteredEvidence.length} of {evidence.length} items
            </span>
            <button
              onClick={onClose}
              className="px-4 py-2 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 rounded-lg transition-colors"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </>
  );
};

export default EvidenceDrawer;
