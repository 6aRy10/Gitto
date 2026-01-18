'use client';

import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from './ui/card';
import { Button } from './ui/button';
import { api } from '@/lib/api';

interface DecisionOption {
  id: string;
  label: string;
  description: string;
  risk_level: string;
  risk_explanation: string;
  impact_amount: string;
  impact_description: string;
  recommended: boolean;
  auto_executable: boolean;
}

interface Decision {
  id: string;
  title: string;
  description: string;
  category: string;
  priority: string;
  status: string;
  entity_id: number;
  snapshot_id: number | null;
  amount_at_stake: string;
  options: DecisionOption[];
  recommended_option_ids: string[];
  recommendation_reasoning: string;
  created_at: string;
  expires_at: string | null;
}

interface DecisionQueueProps {
  onDecisionAction?: () => void;
}

export function DecisionQueue({ onDecisionAction }: DecisionQueueProps) {
  const [decisions, setDecisions] = useState<Decision[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedDecision, setSelectedDecision] = useState<Decision | null>(null);
  const [selectedOptions, setSelectedOptions] = useState<string[]>([]);
  const [notes, setNotes] = useState('');
  const [processing, setProcessing] = useState(false);

  useEffect(() => {
    loadDecisions();
  }, []);

  async function loadDecisions() {
    try {
      setLoading(true);
      const response = await api.get('/fpa-analyst/decisions?entity_id=1&limit=50');
      setDecisions(response.data?.decisions || []);
    } catch (err) {
      console.error('Failed to load decisions:', err);
    } finally {
      setLoading(false);
    }
  }

  async function handleApprove() {
    if (!selectedDecision || selectedOptions.length === 0) return;
    
    try {
      setProcessing(true);
      await api.post(`/fpa-analyst/decisions/${selectedDecision.id}/approve?entity_id=1`, {
        approved_by: 'dashboard_user',
        selected_option_ids: selectedOptions,
        notes: notes || null,
      });
      setSelectedDecision(null);
      setSelectedOptions([]);
      setNotes('');
      await loadDecisions();
      onDecisionAction?.();
    } catch (err) {
      console.error('Failed to approve decision:', err);
    } finally {
      setProcessing(false);
    }
  }

  async function handleDismiss() {
    if (!selectedDecision) return;
    
    try {
      setProcessing(true);
      await api.post(`/fpa-analyst/decisions/${selectedDecision.id}/dismiss?entity_id=1`, {
        dismissed_by: 'dashboard_user',
        reason: notes || 'Dismissed from dashboard',
      });
      setSelectedDecision(null);
      setNotes('');
      await loadDecisions();
      onDecisionAction?.();
    } catch (err) {
      console.error('Failed to dismiss decision:', err);
    } finally {
      setProcessing(false);
    }
  }

  function toggleOption(optionId: string) {
    setSelectedOptions(prev =>
      prev.includes(optionId)
        ? prev.filter(id => id !== optionId)
        : [...prev, optionId]
    );
  }

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'critical':
        return 'bg-red-500/20 text-red-400 border-red-500/30';
      case 'high':
        return 'bg-orange-500/20 text-orange-400 border-orange-500/30';
      case 'medium':
        return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30';
      case 'low':
        return 'bg-zinc-500/20 text-zinc-400 border-zinc-500/30';
      default:
        return 'bg-zinc-500/20 text-zinc-400 border-zinc-500/30';
    }
  };

  const getRiskColor = (risk: string) => {
    switch (risk) {
      case 'high':
        return 'text-red-400';
      case 'medium':
        return 'text-yellow-400';
      case 'low':
        return 'text-green-400';
      default:
        return 'text-zinc-400';
    }
  };

  const formatAmount = (amount: string) => {
    const num = parseFloat(amount);
    if (isNaN(num)) return amount;
    return new Intl.NumberFormat('en-EU', {
      style: 'currency',
      currency: 'EUR',
      maximumFractionDigits: 0,
    }).format(num);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-emerald-500" />
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Decision List */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold text-zinc-200">
          Pending Decisions ({decisions.length})
        </h3>
        
        {decisions.length === 0 ? (
          <Card className="bg-zinc-900 border-zinc-800">
            <CardContent className="py-8 text-center">
              <div className="text-emerald-500 mb-4">
                <svg className="w-12 h-12 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <h4 className="text-zinc-200 font-medium mb-2">All Clear</h4>
              <p className="text-zinc-400 text-sm">No pending decisions require your attention.</p>
            </CardContent>
          </Card>
        ) : (
          decisions.map(decision => (
            <Card
              key={decision.id}
              className={`bg-zinc-900 border-zinc-800 cursor-pointer transition-colors hover:border-zinc-700 ${
                selectedDecision?.id === decision.id ? 'border-emerald-500/50 ring-1 ring-emerald-500/20' : ''
              }`}
              onClick={() => {
                setSelectedDecision(decision);
                setSelectedOptions(decision.recommended_option_ids);
                setNotes('');
              }}
            >
              <CardContent className="p-4">
                <div className="flex items-start justify-between mb-2">
                  <h4 className="text-zinc-200 font-medium">{decision.title}</h4>
                  <span className={`px-2 py-1 rounded text-xs border ${getPriorityColor(decision.priority)}`}>
                    {decision.priority.toUpperCase()}
                  </span>
                </div>
                <p className="text-zinc-400 text-sm mb-3">{decision.description}</p>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-zinc-500">
                    Amount: <span className="text-zinc-300">{formatAmount(decision.amount_at_stake)}</span>
                  </span>
                  <span className="text-zinc-500">
                    {new Date(decision.created_at).toLocaleDateString()}
                  </span>
                </div>
              </CardContent>
            </Card>
          ))
        )}
      </div>

      {/* Decision Detail */}
      <div>
        {selectedDecision ? (
          <Card className="bg-zinc-900 border-zinc-800 sticky top-4">
            <CardHeader>
              <div className="flex items-start justify-between">
                <CardTitle className="text-zinc-200">{selectedDecision.title}</CardTitle>
                <button
                  onClick={() => setSelectedDecision(null)}
                  className="text-zinc-500 hover:text-zinc-300"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            </CardHeader>
            <CardContent className="space-y-6">
              <div>
                <p className="text-zinc-400">{selectedDecision.description}</p>
                <div className="mt-2 flex items-center gap-4 text-sm">
                  <span className="text-zinc-500">
                    Amount at stake: <span className="text-amber-400 font-medium">{formatAmount(selectedDecision.amount_at_stake)}</span>
                  </span>
                </div>
              </div>

              {/* Options */}
              <div>
                <h4 className="text-zinc-300 font-medium mb-3">Options</h4>
                <div className="space-y-3">
                  {selectedDecision.options.map(option => (
                    <div
                      key={option.id}
                      onClick={() => toggleOption(option.id)}
                      className={`p-3 rounded-lg border cursor-pointer transition-colors ${
                        selectedOptions.includes(option.id)
                          ? 'bg-emerald-500/10 border-emerald-500/50'
                          : 'bg-zinc-800 border-zinc-700 hover:border-zinc-600'
                      }`}
                    >
                      <div className="flex items-start gap-3">
                        <div className={`mt-1 w-4 h-4 rounded border-2 flex-shrink-0 ${
                          selectedOptions.includes(option.id)
                            ? 'bg-emerald-500 border-emerald-500'
                            : 'border-zinc-500'
                        }`}>
                          {selectedOptions.includes(option.id) && (
                            <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                              <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                            </svg>
                          )}
                        </div>
                        <div className="flex-1">
                          <div className="flex items-center gap-2">
                            <span className="text-zinc-200 font-medium">{option.label}</span>
                            {option.recommended && (
                              <span className="px-1.5 py-0.5 bg-emerald-500/20 text-emerald-400 text-xs rounded">
                                Recommended
                              </span>
                            )}
                          </div>
                          <p className="text-zinc-400 text-sm mt-1">{option.description}</p>
                          <div className="flex items-center gap-4 mt-2 text-xs">
                            <span className={getRiskColor(option.risk_level)}>
                              Risk: {option.risk_level}
                            </span>
                            <span className="text-zinc-500">
                              Impact: {formatAmount(option.impact_amount)}
                            </span>
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* AI Recommendation */}
              {selectedDecision.recommendation_reasoning && (
                <div className="bg-zinc-800/50 rounded-lg p-4 border border-zinc-700">
                  <h4 className="text-emerald-400 font-medium text-sm mb-2 flex items-center gap-2">
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                    </svg>
                    AI Recommendation
                  </h4>
                  <p className="text-zinc-300 text-sm">{selectedDecision.recommendation_reasoning}</p>
                </div>
              )}

              {/* Notes */}
              <div>
                <label className="block text-zinc-400 text-sm mb-2">Notes (optional)</label>
                <textarea
                  value={notes}
                  onChange={e => setNotes(e.target.value)}
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-lg p-3 text-zinc-200 text-sm focus:outline-none focus:border-emerald-500"
                  rows={3}
                  placeholder="Add any notes or context..."
                />
              </div>

              {/* Actions */}
              <div className="flex gap-3">
                <Button
                  onClick={handleApprove}
                  disabled={selectedOptions.length === 0 || processing}
                  className="flex-1 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50"
                >
                  {processing ? 'Processing...' : 'Approve Selected'}
                </Button>
                <Button
                  onClick={handleDismiss}
                  variant="outline"
                  disabled={processing}
                  className="flex-1"
                >
                  Dismiss
                </Button>
              </div>
            </CardContent>
          </Card>
        ) : (
          <Card className="bg-zinc-900 border-zinc-800">
            <CardContent className="py-16 text-center">
              <div className="text-zinc-600 mb-4">
                <svg className="w-16 h-16 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
                </svg>
              </div>
              <h4 className="text-zinc-400 font-medium mb-2">Select a Decision</h4>
              <p className="text-zinc-500 text-sm">Click on a decision from the list to view details and take action.</p>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}

export default DecisionQueue;
