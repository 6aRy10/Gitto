'use client';

import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from './ui/card';
import { Button } from './ui/button';
import { api } from '@/lib/api';

interface CashMovement {
  movement_type: string;
  amount: string;
  currency: string;
  description: string;
  counterparty: string | null;
  transaction_id: number | null;
  timestamp: string;
}

interface CashPosition {
  as_of: string;
  opening_balance: string;
  total_inflows: string;
  total_outflows: string;
  current_balance: string;
  expected_balance: string;
  variance_from_expected: string;
  currency: string;
}

interface AttentionItem {
  severity: string;
  title: string;
  description: string;
  amount: string | null;
  recommended_action: string;
  decision_id: string | null;
}

interface BriefingData {
  id: string;
  entity_id: number;
  briefing_date: string;
  generated_at: string;
  cash_position: CashPosition;
  overnight_inflows: CashMovement[];
  overnight_outflows: CashMovement[];
  surprises: AttentionItem[];
  expected_inflows: Array<{
    amount: string;
    counterparty: string | null;
    description: string;
  }>;
  expected_outflows: Array<{
    amount: string;
    counterparty: string | null;
    description: string;
  }>;
  total_expected_inflows: string;
  total_expected_outflows: string;
  attention_items: AttentionItem[];
  position_vs_forecast_pct: number;
  executive_summary: string;
}

export function MorningBriefing() {
  const [briefing, setBriefing] = useState<BriefingData | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadBriefing();
  }, []);

  async function loadBriefing() {
    try {
      setLoading(true);
      setError(null);
      const response = await api.get('/fpa-analyst/morning-briefing?entity_id=1');
      setBriefing(response.data);
    } catch (err) {
      console.error('Failed to load briefing:', err);
      setError('Failed to load morning briefing');
    } finally {
      setLoading(false);
    }
  }

  async function generateBriefing() {
    try {
      setGenerating(true);
      setError(null);
      const response = await api.post('/fpa-analyst/workflows/morning_briefing/run?entity_id=1', {
        triggered_by: 'manual',
        user_id: 'dashboard',
        params: {},
      });
      if (response.data?.result) {
        setBriefing(response.data.result);
      } else {
        await loadBriefing();
      }
    } catch (err) {
      console.error('Failed to generate briefing:', err);
      setError('Failed to generate morning briefing');
    } finally {
      setGenerating(false);
    }
  }

  const formatAmount = (amount: string | number) => {
    const num = typeof amount === 'string' ? parseFloat(amount) : amount;
    if (isNaN(num)) return amount;
    return new Intl.NumberFormat('en-EU', {
      style: 'currency',
      currency: 'EUR',
      maximumFractionDigits: 0,
    }).format(num);
  };

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'critical':
        return '🔴';
      case 'warning':
        return '⚠️';
      case 'info':
        return 'ℹ️';
      default:
        return '•';
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-emerald-500" />
      </div>
    );
  }

  if (error && !briefing) {
    return (
      <Card className="bg-zinc-900 border-zinc-800">
        <CardContent className="p-6 text-center">
          <div className="text-yellow-500 mb-4">
            <svg className="w-12 h-12 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          </div>
          <h3 className="text-lg font-medium text-zinc-200 mb-2">No Briefing Available</h3>
          <p className="text-zinc-400 mb-4">{error}</p>
          <Button onClick={generateBriefing} disabled={generating}>
            {generating ? 'Generating...' : 'Generate Morning Briefing'}
          </Button>
        </CardContent>
      </Card>
    );
  }

  if (!briefing) {
    return (
      <Card className="bg-zinc-900 border-zinc-800">
        <CardContent className="p-6 text-center">
          <h3 className="text-lg font-medium text-zinc-200 mb-2">No Briefing Yet</h3>
          <p className="text-zinc-400 mb-4">Generate today&apos;s morning briefing to see cash position and key insights.</p>
          <Button onClick={generateBriefing} disabled={generating}>
            {generating ? 'Generating...' : 'Generate Morning Briefing'}
          </Button>
        </CardContent>
      </Card>
    );
  }

  const variance = parseFloat(briefing.cash_position.variance_from_expected);
  const varianceIsNegative = variance < 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-xl font-semibold text-zinc-200">
            Morning Briefing - {new Date(briefing.briefing_date).toLocaleDateString('en-US', {
              weekday: 'long',
              year: 'numeric',
              month: 'long',
              day: 'numeric',
            })}
          </h3>
          <p className="text-zinc-500 text-sm mt-1">
            Generated at {new Date(briefing.generated_at).toLocaleTimeString()}
          </p>
        </div>
        <Button onClick={generateBriefing} variant="outline" disabled={generating}>
          {generating ? 'Refreshing...' : 'Refresh'}
        </Button>
      </div>

      {/* Executive Summary */}
      {briefing.executive_summary && (
        <Card className="bg-zinc-900 border-zinc-800">
          <CardContent className="p-4">
            <pre className="text-zinc-300 text-sm whitespace-pre-wrap font-sans">
              {briefing.executive_summary}
            </pre>
          </CardContent>
        </Card>
      )}

      {/* Cash Position */}
      <Card className="bg-zinc-900 border-zinc-800">
        <CardHeader>
          <CardTitle className="text-zinc-200 text-lg">Cash Position</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-zinc-800 rounded-lg p-4">
              <div className="text-zinc-400 text-sm mb-1">Opening Balance</div>
              <div className="text-zinc-200 text-xl font-semibold">
                {formatAmount(briefing.cash_position.opening_balance)}
              </div>
            </div>
            <div className="bg-zinc-800 rounded-lg p-4">
              <div className="text-zinc-400 text-sm mb-1">Current Balance</div>
              <div className="text-emerald-400 text-xl font-semibold">
                {formatAmount(briefing.cash_position.current_balance)}
              </div>
            </div>
            <div className="bg-zinc-800 rounded-lg p-4">
              <div className="text-zinc-400 text-sm mb-1">Expected</div>
              <div className="text-zinc-200 text-xl font-semibold">
                {formatAmount(briefing.cash_position.expected_balance)}
              </div>
            </div>
            <div className="bg-zinc-800 rounded-lg p-4">
              <div className="text-zinc-400 text-sm mb-1">Variance</div>
              <div className={`text-xl font-semibold ${varianceIsNegative ? 'text-red-400' : 'text-green-400'}`}>
                {varianceIsNegative ? '' : '+'}{formatAmount(variance)}
                <span className="text-sm ml-1">
                  ({varianceIsNegative ? '' : '+'}{briefing.position_vs_forecast_pct.toFixed(1)}%)
                </span>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Overnight Activity & Expected */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Overnight Activity */}
        <Card className="bg-zinc-900 border-zinc-800">
          <CardHeader>
            <CardTitle className="text-zinc-200 text-lg">Overnight Activity</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Inflows */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-green-400 font-medium">Inflows</span>
                <span className="text-green-400 font-medium">
                  +{formatAmount(briefing.cash_position.total_inflows)}
                </span>
              </div>
              <div className="space-y-2 max-h-32 overflow-y-auto">
                {briefing.overnight_inflows.length === 0 ? (
                  <p className="text-zinc-500 text-sm">No overnight inflows</p>
                ) : (
                  briefing.overnight_inflows.slice(0, 5).map((item, idx) => (
                    <div key={idx} className="flex justify-between text-sm">
                      <span className="text-zinc-400 truncate max-w-[200px]">
                        {item.counterparty || item.description}
                      </span>
                      <span className="text-green-400">+{formatAmount(item.amount)}</span>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Outflows */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-red-400 font-medium">Outflows</span>
                <span className="text-red-400 font-medium">
                  -{formatAmount(briefing.cash_position.total_outflows)}
                </span>
              </div>
              <div className="space-y-2 max-h-32 overflow-y-auto">
                {briefing.overnight_outflows.length === 0 ? (
                  <p className="text-zinc-500 text-sm">No overnight outflows</p>
                ) : (
                  briefing.overnight_outflows.slice(0, 5).map((item, idx) => (
                    <div key={idx} className="flex justify-between text-sm">
                      <span className="text-zinc-400 truncate max-w-[200px]">
                        {item.counterparty || item.description}
                      </span>
                      <span className="text-red-400">-{formatAmount(item.amount)}</span>
                    </div>
                  ))
                )}
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Expected Today */}
        <Card className="bg-zinc-900 border-zinc-800">
          <CardHeader>
            <CardTitle className="text-zinc-200 text-lg">Expected Today</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Expected Inflows */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-emerald-400 font-medium">Expected Inflows</span>
                <span className="text-emerald-400 font-medium">
                  {formatAmount(briefing.total_expected_inflows)}
                </span>
              </div>
              <div className="space-y-2 max-h-32 overflow-y-auto">
                {briefing.expected_inflows.length === 0 ? (
                  <p className="text-zinc-500 text-sm">No expected inflows today</p>
                ) : (
                  briefing.expected_inflows.slice(0, 5).map((item, idx) => (
                    <div key={idx} className="flex justify-between text-sm">
                      <span className="text-zinc-400 truncate max-w-[200px]">
                        {item.counterparty || item.description}
                      </span>
                      <span className="text-emerald-400">{formatAmount(item.amount)}</span>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Expected Outflows */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-amber-400 font-medium">Expected Outflows</span>
                <span className="text-amber-400 font-medium">
                  {formatAmount(briefing.total_expected_outflows)}
                </span>
              </div>
              <div className="space-y-2 max-h-32 overflow-y-auto">
                {briefing.expected_outflows.length === 0 ? (
                  <p className="text-zinc-500 text-sm">No expected outflows today</p>
                ) : (
                  briefing.expected_outflows.slice(0, 5).map((item, idx) => (
                    <div key={idx} className="flex justify-between text-sm">
                      <span className="text-zinc-400 truncate max-w-[200px]">
                        {item.counterparty || item.description}
                      </span>
                      <span className="text-amber-400">{formatAmount(item.amount)}</span>
                    </div>
                  ))
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Attention Items */}
      {(briefing.attention_items.length > 0 || briefing.surprises.length > 0) && (
        <Card className="bg-zinc-900 border-zinc-800">
          <CardHeader>
            <CardTitle className="text-zinc-200 text-lg">Attention Needed</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {[...briefing.surprises, ...briefing.attention_items].map((item, idx) => (
                <div
                  key={idx}
                  className={`p-3 rounded-lg border ${
                    item.severity === 'critical' ? 'bg-red-500/10 border-red-500/30' :
                    item.severity === 'warning' ? 'bg-yellow-500/10 border-yellow-500/30' :
                    'bg-zinc-800 border-zinc-700'
                  }`}
                >
                  <div className="flex items-start gap-2">
                    <span className="flex-shrink-0">{getSeverityIcon(item.severity)}</span>
                    <div className="flex-1">
                      <div className="text-zinc-200 font-medium">{item.title}</div>
                      <p className="text-zinc-400 text-sm mt-1">{item.description}</p>
                      {item.recommended_action && (
                        <p className="text-emerald-400 text-sm mt-2">
                          → {item.recommended_action}
                        </p>
                      )}
                    </div>
                    {item.amount && (
                      <span className="text-zinc-300 font-medium">
                        {formatAmount(item.amount)}
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

export default MorningBriefing;
