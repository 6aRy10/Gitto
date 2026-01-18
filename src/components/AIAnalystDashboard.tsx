'use client';

import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from './ui/card';
import { Button } from './ui/button';
import { DecisionQueue } from './DecisionQueue';
import { MorningBriefing } from './MorningBriefing';
import { AskAnalyst } from './AskAnalyst';
import { api } from '@/lib/api';

interface AnalystStatus {
  status: string;
  entity_id: number;
  autonomous_mode: boolean;
  workflows: Record<string, string>;
  scheduled_tasks: Record<string, {
    enabled: boolean;
    last_run: string | null;
    cron: string;
  }>;
  decision_queue_stats: {
    total_decisions: number;
    pending: number;
    pending_by_priority: {
      critical: number;
      high: number;
      medium: number;
      low: number;
    };
  };
  recent_runs: Array<{
    workflow: string;
    started: string;
    status: string;
    triggered_by: string;
  }>;
}

interface Insight {
  type: string;
  timestamp: string;
  description: string;
  severity: string;
  details: Record<string, unknown>;
}

export function AIAnalystDashboard() {
  const [status, setStatus] = useState<AnalystStatus | null>(null);
  const [insights, setInsights] = useState<Insight[]>([]);
  const [activeTab, setActiveTab] = useState<'overview' | 'decisions' | 'briefing' | 'ask'>('overview');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadData();
    // Refresh every 30 seconds
    const interval = setInterval(loadData, 30000);
    return () => clearInterval(interval);
  }, []);

  async function loadData() {
    try {
      setError(null);
      const [statusRes, insightsRes] = await Promise.all([
        api.get('/fpa-analyst/status?entity_id=1'),
        api.get('/fpa-analyst/insights?limit=10'),
      ]);
      setStatus(statusRes.data);
      setInsights(insightsRes.data?.insights || []);
    } catch (err) {
      console.error('Failed to load analyst data:', err);
      setError('Failed to load AI Analyst data. The service may not be running.');
    } finally {
      setLoading(false);
    }
  }

  async function handleStartAnalyst() {
    try {
      await api.post('/fpa-analyst/start?entity_id=1');
      await loadData();
    } catch (err) {
      console.error('Failed to start analyst:', err);
    }
  }

  async function handleStopAnalyst() {
    try {
      await api.post('/fpa-analyst/stop?entity_id=1');
      await loadData();
    } catch (err) {
      console.error('Failed to stop analyst:', err);
    }
  }

  async function runWorkflow(workflowName: string) {
    try {
      await api.post(`/fpa-analyst/workflows/${workflowName}/run?entity_id=1`, {
        triggered_by: 'manual',
        user_id: 'dashboard',
        params: {},
      });
      await loadData();
    } catch (err) {
      console.error(`Failed to run ${workflowName}:`, err);
    }
  }

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical':
        return 'text-red-500 bg-red-500/10';
      case 'warning':
        return 'text-yellow-500 bg-yellow-500/10';
      case 'info':
        return 'text-blue-500 bg-blue-500/10';
      default:
        return 'text-gray-500 bg-gray-500/10';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'running':
        return 'text-green-500';
      case 'stopped':
        return 'text-red-500';
      case 'paused':
        return 'text-yellow-500';
      default:
        return 'text-gray-500';
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-emerald-500" />
      </div>
    );
  }

  if (error) {
    return (
      <Card className="bg-zinc-900 border-zinc-800">
        <CardContent className="p-6">
          <div className="text-center">
            <div className="text-yellow-500 mb-4">
              <svg className="w-12 h-12 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
            </div>
            <h3 className="text-lg font-medium text-zinc-200 mb-2">AI Analyst Not Available</h3>
            <p className="text-zinc-400 mb-4">{error}</p>
            <Button onClick={loadData} variant="outline">
              Retry
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold text-zinc-100">AI FP&A Analyst</h2>
          <p className="text-zinc-400 mt-1">Autonomous financial planning and analysis assistant</p>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${status?.status === 'running' ? 'bg-green-500 animate-pulse' : 'bg-zinc-500'}`} />
            <span className={`text-sm font-medium ${getStatusColor(status?.status || 'stopped')}`}>
              {status?.status?.toUpperCase() || 'UNKNOWN'}
            </span>
          </div>
          {status?.status === 'running' ? (
            <Button onClick={handleStopAnalyst} variant="outline" size="sm">
              Stop Analyst
            </Button>
          ) : (
            <Button onClick={handleStartAnalyst} size="sm" className="bg-emerald-600 hover:bg-emerald-700">
              Start Analyst
            </Button>
          )}
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex gap-2 border-b border-zinc-800 pb-2">
        {[
          { key: 'overview', label: 'Overview' },
          { key: 'decisions', label: `Decisions (${status?.decision_queue_stats?.pending || 0})` },
          { key: 'briefing', label: 'Morning Briefing' },
          { key: 'ask', label: 'Ask Analyst' },
        ].map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key as typeof activeTab)}
            className={`px-4 py-2 text-sm font-medium rounded-t-lg transition-colors ${
              activeTab === tab.key
                ? 'bg-zinc-800 text-emerald-400 border-b-2 border-emerald-400'
                : 'text-zinc-400 hover:text-zinc-200'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {activeTab === 'overview' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Quick Stats */}
          <Card className="bg-zinc-900 border-zinc-800">
            <CardHeader>
              <CardTitle className="text-zinc-200 text-lg">Decision Queue</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-zinc-400">Critical</span>
                  <span className="text-red-500 font-bold">
                    {status?.decision_queue_stats?.pending_by_priority?.critical || 0}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-zinc-400">High</span>
                  <span className="text-orange-500 font-bold">
                    {status?.decision_queue_stats?.pending_by_priority?.high || 0}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-zinc-400">Medium</span>
                  <span className="text-yellow-500 font-bold">
                    {status?.decision_queue_stats?.pending_by_priority?.medium || 0}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-zinc-400">Low</span>
                  <span className="text-zinc-300 font-bold">
                    {status?.decision_queue_stats?.pending_by_priority?.low || 0}
                  </span>
                </div>
              </div>
              <Button
                className="w-full mt-4"
                variant="outline"
                onClick={() => setActiveTab('decisions')}
              >
                View All Decisions
              </Button>
            </CardContent>
          </Card>

          {/* Scheduled Tasks */}
          <Card className="bg-zinc-900 border-zinc-800">
            <CardHeader>
              <CardTitle className="text-zinc-200 text-lg">Scheduled Tasks</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {Object.entries(status?.scheduled_tasks || {}).map(([name, task]) => (
                  <div key={name} className="flex justify-between items-center">
                    <div>
                      <span className="text-zinc-300 text-sm capitalize">
                        {name.replace(/_/g, ' ')}
                      </span>
                      {task.last_run && (
                        <p className="text-zinc-500 text-xs">
                          Last: {new Date(task.last_run).toLocaleTimeString()}
                        </p>
                      )}
                    </div>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => runWorkflow(name)}
                    >
                      Run
                    </Button>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Recent Insights */}
          <Card className="bg-zinc-900 border-zinc-800">
            <CardHeader>
              <CardTitle className="text-zinc-200 text-lg">Recent Insights</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {insights.length === 0 ? (
                  <p className="text-zinc-500 text-sm">No recent insights</p>
                ) : (
                  insights.map((insight, idx) => (
                    <div
                      key={idx}
                      className={`p-2 rounded text-sm ${getSeverityColor(insight.severity)}`}
                    >
                      <div className="font-medium">{insight.description}</div>
                      <div className="text-xs opacity-70 mt-1">
                        {new Date(insight.timestamp).toLocaleString()}
                      </div>
                    </div>
                  ))
                )}
              </div>
            </CardContent>
          </Card>

          {/* Recent Workflow Runs */}
          <Card className="bg-zinc-900 border-zinc-800 lg:col-span-3">
            <CardHeader>
              <CardTitle className="text-zinc-200 text-lg">Recent Workflow Runs</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-zinc-400 border-b border-zinc-800">
                      <th className="text-left py-2 px-4">Workflow</th>
                      <th className="text-left py-2 px-4">Started</th>
                      <th className="text-left py-2 px-4">Status</th>
                      <th className="text-left py-2 px-4">Triggered By</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(status?.recent_runs || []).map((run, idx) => (
                      <tr key={idx} className="border-b border-zinc-800/50">
                        <td className="py-2 px-4 text-zinc-200 capitalize">
                          {run.workflow.replace(/_/g, ' ')}
                        </td>
                        <td className="py-2 px-4 text-zinc-400">
                          {new Date(run.started).toLocaleString()}
                        </td>
                        <td className="py-2 px-4">
                          <span className={`px-2 py-1 rounded text-xs ${
                            run.status === 'completed' ? 'bg-green-500/20 text-green-400' :
                            run.status === 'running' ? 'bg-blue-500/20 text-blue-400' :
                            run.status === 'failed' ? 'bg-red-500/20 text-red-400' :
                            'bg-zinc-500/20 text-zinc-400'
                          }`}>
                            {run.status}
                          </span>
                        </td>
                        <td className="py-2 px-4 text-zinc-400">{run.triggered_by}</td>
                      </tr>
                    ))}
                    {(!status?.recent_runs || status.recent_runs.length === 0) && (
                      <tr>
                        <td colSpan={4} className="py-4 text-center text-zinc-500">
                          No recent workflow runs
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {activeTab === 'decisions' && <DecisionQueue onDecisionAction={loadData} />}
      {activeTab === 'briefing' && <MorningBriefing />}
      {activeTab === 'ask' && <AskAnalyst />}
    </div>
  );
}

export default AIAnalystDashboard;
