'use client';

import React, { useState, useEffect } from 'react';

interface MatchCandidate {
  invoice_id: number;
  invoice_number: string;
  customer_name: string;
  amount: number;
  tier: number;
  confidence: number;
  suggested_allocation: number | null;
  reasons: string[];
}

interface MatchResult {
  bank_txn_id: number;
  amount: number;
  status: string;
  best_tier: number;
  candidates_count: number;
  top_candidates: MatchCandidate[];
}

interface CashExplained {
  total_bank_inflows: number;
  matched_amount: number;
  unmatched_amount: number;
  cash_explained_pct: number;
  target_pct: number;
  status: string;
}

interface Exception {
  id: number;
  bank_transaction_id: number;
  status: string;
  assignee_id: string | null;
  days_unmatched: number;
  sla_due_at: string | null;
  resolution_type: string | null;
  created_at: string;
}

interface ReconciliationCockpitProps {
  snapshotId: number;
}

export default function ReconciliationCockpit({ snapshotId }: ReconciliationCockpitProps) {
  const [matchResults, setMatchResults] = useState<MatchResult[]>([]);
  const [cashExplained, setCashExplained] = useState<CashExplained | null>(null);
  const [exceptions, setExceptions] = useState<Exception[]>([]);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<'matches' | 'exceptions'>('matches');
  const [summary, setSummary] = useState({
    auto_matched: 0,
    suggested: 0,
    manual_required: 0,
    no_match: 0
  });

  const runMatching = async () => {
    setLoading(true);
    try {
      const res = await fetch(`/api/snapshots/${snapshotId}/matching/find-matches`, {
        method: 'POST'
      });
      const data = await res.json();
      setMatchResults(data.results || []);
      setCashExplained(data.cash_explained);
      setSummary(data.summary || {});
    } catch (err) {
      console.error('Matching failed:', err);
    }
    setLoading(false);
  };

  const loadExceptions = async () => {
    try {
      const res = await fetch(`/api/snapshots/${snapshotId}/exceptions`);
      const data = await res.json();
      setExceptions(data);
    } catch (err) {
      console.error('Failed to load exceptions:', err);
    }
  };

  const approveAllocation = async (bankTxnId: number, candidate: MatchCandidate) => {
    try {
      await fetch('/api/matching/allocations', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          bank_txn_id: bankTxnId,
          invoice_id: candidate.invoice_id,
          allocated_amount: candidate.suggested_allocation || candidate.amount,
          tier: candidate.tier,
          confidence: candidate.confidence,
          approved_by: 'current_user' // TODO: Real user
        })
      });
      // Refresh
      runMatching();
    } catch (err) {
      console.error('Approval failed:', err);
    }
  };

  useEffect(() => {
    if (snapshotId) {
      loadExceptions();
    }
  }, [snapshotId]);

  const getTierBadge = (tier: number) => {
    const styles = {
      1: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
      2: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
      3: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
      4: 'bg-red-500/20 text-red-400 border-red-500/30'
    };
    const labels = {
      1: 'Tier 1 - Exact',
      2: 'Tier 2 - Rules',
      3: 'Tier 3 - Suggested',
      4: 'Tier 4 - Manual'
    };
    return (
      <span className={`text-xs px-2 py-0.5 rounded-full border ${styles[tier as keyof typeof styles] || styles[4]}`}>
        {labels[tier as keyof typeof labels] || 'Manual'}
      </span>
    );
  };

  const getStatusBadge = (status: string) => {
    const styles: Record<string, string> = {
      new: 'bg-blue-500/20 text-blue-400',
      assigned: 'bg-amber-500/20 text-amber-400',
      in_review: 'bg-purple-500/20 text-purple-400',
      resolved: 'bg-emerald-500/20 text-emerald-400',
      escalated: 'bg-red-500/20 text-red-400'
    };
    return (
      <span className={`text-xs px-2 py-0.5 rounded-full ${styles[status] || 'bg-gray-500/20 text-gray-400'}`}>
        {status}
      </span>
    );
  };

  return (
    <div className="bg-[#0D0D12] rounded-2xl border border-white/10 p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-bold text-white">Reconciliation Cockpit</h2>
          <p className="text-sm text-white/40">Bank truth + invoice matching</p>
        </div>
        <button
          onClick={runMatching}
          disabled={loading}
          className="px-4 py-2 bg-white text-[#0A0A0F] rounded-lg font-medium text-sm hover:bg-white/90 transition-colors disabled:opacity-50"
        >
          {loading ? 'Running...' : 'Run Matching Engine'}
        </button>
      </div>

      {/* Cash Explained KPI */}
      {cashExplained && (
        <div className="grid grid-cols-4 gap-4 mb-6">
          <div className="bg-[#141419] rounded-xl p-4 border border-white/5">
            <div className="text-sm text-white/40 mb-1">Cash Explained</div>
            <div className={`text-2xl font-bold ${
              cashExplained.status === 'healthy' ? 'text-emerald-400' :
              cashExplained.status === 'warning' ? 'text-amber-400' : 'text-red-400'
            }`}>
              {cashExplained.cash_explained_pct}%
            </div>
            <div className="text-xs text-white/30 mt-1">Target: {cashExplained.target_pct}%</div>
          </div>
          <div className="bg-[#141419] rounded-xl p-4 border border-white/5">
            <div className="text-sm text-white/40 mb-1">Total Inflows</div>
            <div className="text-2xl font-bold text-white">
              €{(cashExplained.total_bank_inflows / 1000).toFixed(0)}K
            </div>
          </div>
          <div className="bg-[#141419] rounded-xl p-4 border border-white/5">
            <div className="text-sm text-white/40 mb-1">Matched</div>
            <div className="text-2xl font-bold text-emerald-400">
              €{(cashExplained.matched_amount / 1000).toFixed(0)}K
            </div>
          </div>
          <div className="bg-[#141419] rounded-xl p-4 border border-white/5">
            <div className="text-sm text-white/40 mb-1">Unmatched</div>
            <div className="text-2xl font-bold text-amber-400">
              €{(cashExplained.unmatched_amount / 1000).toFixed(0)}K
            </div>
          </div>
        </div>
      )}

      {/* Summary Stats */}
      {matchResults.length > 0 && (
        <div className="flex gap-4 mb-6">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-emerald-400" />
            <span className="text-sm text-white/60">Auto-matched: {summary.auto_matched}</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-amber-400" />
            <span className="text-sm text-white/60">Suggested: {summary.suggested}</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-red-400" />
            <span className="text-sm text-white/60">Manual: {summary.manual_required}</span>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-2 mb-6">
        <button
          onClick={() => setActiveTab('matches')}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            activeTab === 'matches'
              ? 'bg-white text-[#0A0A0F]'
              : 'bg-white/5 text-white/60 hover:bg-white/10'
          }`}
        >
          Match Candidates
        </button>
        <button
          onClick={() => { setActiveTab('exceptions'); loadExceptions(); }}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            activeTab === 'exceptions'
              ? 'bg-white text-[#0A0A0F]'
              : 'bg-white/5 text-white/60 hover:bg-white/10'
          }`}
        >
          Exceptions ({exceptions.filter(e => e.status !== 'resolved').length})
        </button>
      </div>

      {/* Match Results */}
      {activeTab === 'matches' && (
        <div className="space-y-4 max-h-[500px] overflow-y-auto">
          {matchResults.length === 0 ? (
            <div className="text-center py-12 text-white/40">
              Click "Run Matching Engine" to find matches
            </div>
          ) : (
            matchResults.map((result) => (
              <div key={result.bank_txn_id} className="bg-[#141419] rounded-xl p-4 border border-white/5">
                <div className="flex items-center justify-between mb-3">
                  <div>
                    <span className="text-white font-medium">Bank Txn #{result.bank_txn_id}</span>
                    <span className="text-white/40 ml-2">€{result.amount.toLocaleString()}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    {getTierBadge(result.best_tier)}
                    <span className={`text-xs px-2 py-0.5 rounded-full ${
                      result.status === 'auto_matched' ? 'bg-emerald-500/20 text-emerald-400' :
                      result.status === 'suggested' ? 'bg-amber-500/20 text-amber-400' :
                      'bg-red-500/20 text-red-400'
                    }`}>
                      {result.status.replace('_', ' ')}
                    </span>
                  </div>
                </div>

                {result.top_candidates.length > 0 ? (
                  <div className="space-y-2">
                    {result.top_candidates.map((candidate, idx) => (
                      <div key={idx} className="flex items-center justify-between bg-[#0D0D12] rounded-lg p-3">
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="text-white text-sm">{candidate.invoice_number}</span>
                            <span className="text-white/40 text-xs">{candidate.customer_name}</span>
                          </div>
                          <div className="flex items-center gap-2 mt-1">
                            <span className="text-white/60 text-xs">€{candidate.amount.toLocaleString()}</span>
                            <span className="text-white/40 text-xs">
                              Confidence: {(candidate.confidence * 100).toFixed(0)}%
                            </span>
                          </div>
                          {candidate.reasons.length > 0 && (
                            <div className="flex flex-wrap gap-1 mt-1">
                              {candidate.reasons.map((reason, i) => (
                                <span key={i} className="text-[10px] px-1.5 py-0.5 bg-white/5 rounded text-white/40">
                                  {reason}
                                </span>
                              ))}
                            </div>
                          )}
                        </div>
                        <button
                          onClick={() => approveAllocation(result.bank_txn_id, candidate)}
                          className="px-3 py-1.5 bg-emerald-500/20 text-emerald-400 rounded-lg text-xs font-medium hover:bg-emerald-500/30 transition-colors"
                        >
                          Approve
                        </button>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-white/40 text-sm">No matching candidates found</div>
                )}
              </div>
            ))
          )}
        </div>
      )}

      {/* Exceptions */}
      {activeTab === 'exceptions' && (
        <div className="space-y-3 max-h-[500px] overflow-y-auto">
          {exceptions.length === 0 ? (
            <div className="text-center py-12 text-white/40">
              No unmatched exceptions
            </div>
          ) : (
            exceptions.map((exc) => (
              <div key={exc.id} className="flex items-center justify-between bg-[#141419] rounded-xl p-4 border border-white/5">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-white font-medium">Exception #{exc.id}</span>
                    {getStatusBadge(exc.status)}
                  </div>
                  <div className="text-xs text-white/40 mt-1">
                    Bank Txn #{exc.bank_transaction_id} • {exc.days_unmatched} days unmatched
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {exc.assignee_id ? (
                    <span className="text-xs text-white/40">Assigned to: {exc.assignee_id}</span>
                  ) : (
                    <button className="px-3 py-1.5 bg-blue-500/20 text-blue-400 rounded-lg text-xs font-medium hover:bg-blue-500/30 transition-colors">
                      Assign
                    </button>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}




