'use client';

import React, { useState, useEffect } from 'react';
import { 
  ChevronRight, 
  ChevronLeft, 
  Lock, 
  AlertTriangle, 
  CheckCircle2, 
  TrendingDown,
  TrendingUp,
  Clock,
  Users,
  FileCheck,
  Play,
  Pause,
  SkipForward
} from 'lucide-react';

// ═══════════════════════════════════════════════════════════════════════════════
// MEETING MODE - "GitHub for Cash" Weekly Meeting Flow
// ═══════════════════════════════════════════════════════════════════════════════

interface MeetingModeProps {
  snapshotId: number;
  onComplete?: () => void;
}

interface MeetingStep {
  id: number;
  key: string;
  label: string;
  description: string;
  icon: React.ReactNode;
  status: 'pending' | 'active' | 'completed';
}

interface MeetingData {
  snapshot_id: number;
  status: string;
  is_locked: boolean;
  steps: {
    '1_cash_today': {
      label: string;
      bank_balance: number;
      cash_explained_pct: number;
      unknown_bucket: number;
    };
    '2_forecast': {
      label: string;
      min_cash_threshold: number;
      endpoint: string;
    };
    '3_red_weeks': {
      label: string;
      description: string;
      count: number;
    };
    '4_variance': {
      label: string;
      vs_snapshot_id: number | null;
      bank_delta: number | null;
    };
    '5_actions': {
      label: string;
      pending_count: number;
      actions: Array<{
  id: number;
  type: string;
  description: string;
  owner: string;
      }>;
    };
    '6_lock': {
      label: string;
      can_lock: boolean;
      blockers: {
        critical_exceptions: number;
        pending_approvals: number;
      };
    };
  };
  exceptions_summary: Array<{
    id: number;
    type: string;
    severity: string;
  }>;
}

const MeetingMode: React.FC<MeetingModeProps> = ({ snapshotId, onComplete }) => {
  const [currentStep, setCurrentStep] = useState(0);
  const [meetingData, setMeetingData] = useState<MeetingData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isPresenting, setIsPresenting] = useState(false);
  const [approvedActions, setApprovedActions] = useState<Set<number>>(new Set());

  // Define meeting steps
  const steps: MeetingStep[] = [
    {
      id: 1,
      key: '1_cash_today',
      label: 'Cash Today',
      description: 'Current bank truth and explained %',
      icon: <TrendingUp className="w-5 h-5" />,
      status: currentStep === 0 ? 'active' : currentStep > 0 ? 'completed' : 'pending'
    },
    {
      id: 2,
      key: '2_forecast',
      label: '13-Week Forecast',
      description: 'P50/P75 probabilistic view',
      icon: <TrendingDown className="w-5 h-5" />,
      status: currentStep === 1 ? 'active' : currentStep > 1 ? 'completed' : 'pending'
    },
    {
      id: 3,
      key: '3_red_weeks',
      label: 'Red Weeks',
      description: 'Weeks below minimum cash',
      icon: <AlertTriangle className="w-5 h-5" />,
      status: currentStep === 2 ? 'active' : currentStep > 2 ? 'completed' : 'pending'
    },
    {
      id: 4,
      key: '4_variance',
      label: 'Variance Diff',
      description: 'Changes vs last locked snapshot',
      icon: <FileCheck className="w-5 h-5" />,
      status: currentStep === 3 ? 'active' : currentStep > 3 ? 'completed' : 'pending'
    },
    {
      id: 5,
      key: '5_actions',
      label: 'Approve Actions',
      description: 'Pending decisions',
      icon: <Users className="w-5 h-5" />,
      status: currentStep === 4 ? 'active' : currentStep > 4 ? 'completed' : 'pending'
    },
    {
      id: 6,
      key: '6_lock',
      label: 'Lock Snapshot',
      description: 'Finalize weekly position',
      icon: <Lock className="w-5 h-5" />,
      status: currentStep === 5 ? 'active' : currentStep > 5 ? 'completed' : 'pending'
    }
  ];

  useEffect(() => {
    fetchMeetingData();
  }, [snapshotId]);

  const fetchMeetingData = async () => {
    setIsLoading(true);
    try {
      // In production, this would call the API
      // const response = await fetch(`/api/v1/meeting-mode/${snapshotId}`);
      // const data = await response.json();
      
      // Mock data for UI development
      const mockData: MeetingData = {
        snapshot_id: snapshotId,
        status: 'ready_for_review',
        is_locked: false,
        steps: {
          '1_cash_today': {
            label: 'Cash Today',
            bank_balance: 2650000,
            cash_explained_pct: 97,
            unknown_bucket: 45000
          },
          '2_forecast': {
            label: '13-Week Forecast',
            min_cash_threshold: 500000,
            endpoint: `/api/v1/workspace/13w?snapshot_id=${snapshotId}`
          },
          '3_red_weeks': {
            label: 'Red Weeks',
            description: 'Weeks with net outflow below minimum',
            count: 2
          },
          '4_variance': {
            label: 'Variance vs Last',
            vs_snapshot_id: snapshotId - 1,
            bank_delta: 125000
          },
          '5_actions': {
            label: 'Pending Decisions',
            pending_count: 3,
            actions: [
              { id: 1, type: 'delay_vendor', description: 'Delay Acme Corp payment by 7 days', owner: 'treasury@gitto.io' },
              { id: 2, type: 'push_collections', description: 'Priority call to BigCo ($45K overdue)', owner: 'ar@gitto.io' },
              { id: 3, type: 'draw_revolver', description: 'Draw €100K from revolver for W7 buffer', owner: 'cfo@gitto.io' }
            ]
          },
          '6_lock': {
            label: 'Lock Snapshot',
            can_lock: true,
            blockers: {
              critical_exceptions: 0,
              pending_approvals: 3
            }
          }
        },
        exceptions_summary: [
          { id: 1, type: 'missing_fx_rate', severity: 'warning' },
          { id: 2, type: 'suggested_match_pending', severity: 'info' }
        ]
      };
      
      setMeetingData(mockData);
    } catch (error) {
      console.error('Failed to load meeting data:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleNext = () => {
    if (currentStep < steps.length - 1) {
      setCurrentStep(prev => prev + 1);
    }
  };

  const handlePrev = () => {
    if (currentStep > 0) {
      setCurrentStep(prev => prev - 1);
    }
  };

  const handleApproveAction = (actionId: number) => {
    setApprovedActions(prev => new Set([...prev, actionId]));
  };

  const handleLockSnapshot = async () => {
    // In production, this would call the API
    alert(`Snapshot ${snapshotId} locked successfully!`);
    onComplete?.();
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-EU', {
      style: 'currency',
      currency: 'EUR',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(amount);
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#0A0A0F] flex items-center justify-center">
        <div className="text-white/60 flex items-center gap-3">
          <div className="w-5 h-5 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin" />
          Loading meeting data...
        </div>
      </div>
    );
  }

  if (!meetingData) {
    return (
      <div className="min-h-screen bg-[#0A0A0F] flex items-center justify-center">
        <div className="text-red-400">Failed to load meeting data</div>
      </div>
    );
  }

        return (
    <div className="min-h-screen bg-[#0A0A0F] text-white">
      {/* Header */}
      <div className="border-b border-white/10 bg-[#0D0D12]">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <div className="h-10 w-10 rounded-xl bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center">
                <Play className="w-5 h-5 text-white" />
              </div>
              <div>
                <h1 className="text-lg font-bold">Meeting Mode</h1>
                <p className="text-xs text-white/50">Snapshot #{snapshotId} • Weekly Cash Review</p>
              </div>
            </div>
          </div>
          
          <div className="flex items-center gap-4">
            <button
              onClick={() => setIsPresenting(!isPresenting)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
                isPresenting 
                  ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                  : 'bg-white/5 text-white/60 hover:text-white border border-white/10'
              }`}
            >
              {isPresenting ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
              {isPresenting ? 'Presenting' : 'Present'}
            </button>
            
            <div className="text-sm text-white/40">
              Step {currentStep + 1} of {steps.length}
            </div>
          </div>
        </div>
      </div>

      {/* Progress Steps */}
      <div className="border-b border-white/5 bg-[#0D0D12]/50">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            {steps.map((step, index) => (
              <React.Fragment key={step.id}>
                <button
                  onClick={() => setCurrentStep(index)}
                  className={`flex items-center gap-3 px-4 py-2 rounded-lg transition-all ${
                    step.status === 'active'
                      ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                      : step.status === 'completed'
                      ? 'bg-white/5 text-white/70'
                      : 'text-white/40 hover:text-white/60'
                  }`}
                >
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
                    step.status === 'active'
                      ? 'bg-emerald-500/30'
                      : step.status === 'completed'
                      ? 'bg-emerald-500/10'
                      : 'bg-white/5'
                  }`}>
                    {step.status === 'completed' ? (
                      <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                    ) : (
                      step.icon
                    )}
                  </div>
                  <div className="hidden lg:block text-left">
                    <div className="text-sm font-medium">{step.label}</div>
                    <div className="text-[10px] text-white/40">{step.description}</div>
                </div>
                </button>
                
                {index < steps.length - 1 && (
                  <div className={`flex-1 h-px mx-2 ${
                    index < currentStep ? 'bg-emerald-500/50' : 'bg-white/10'
                  }`} />
                )}
              </React.Fragment>
            ))}
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-6 py-8">
        {/* Step 1: Cash Today */}
        {currentStep === 0 && (
          <div className="space-y-8 animate-fadeIn">
            <div className="text-center mb-12">
              <h2 className="text-3xl font-bold mb-2">Cash Today</h2>
              <p className="text-white/50">Bank truth as of latest sync</p>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="bg-[#0D0D12] rounded-2xl p-8 border border-white/10">
                <div className="text-sm text-white/50 mb-2">Total Bank Balance</div>
                  <div className="text-4xl font-bold text-white">
                  {formatCurrency(meetingData.steps['1_cash_today'].bank_balance)}
                </div>
                <div className="mt-4 flex items-center gap-2 text-emerald-400 text-sm">
                  <TrendingUp className="w-4 h-4" />
                  <span>+5.2% vs last week</span>
                </div>
                  </div>
              
              <div className="bg-[#0D0D12] rounded-2xl p-8 border border-white/10">
                <div className="text-sm text-white/50 mb-2">Cash Explained</div>
                <div className="text-4xl font-bold text-emerald-400">
                  {meetingData.steps['1_cash_today'].cash_explained_pct}%
                </div>
                <div className="mt-4">
                  <div className="w-full bg-white/10 rounded-full h-2">
                    <div 
                      className="bg-emerald-500 h-2 rounded-full transition-all duration-1000"
                      style={{ width: `${meetingData.steps['1_cash_today'].cash_explained_pct}%` }}
                    />
                  </div>
                </div>
              </div>
              
              <div className="bg-[#0D0D12] rounded-2xl p-8 border border-white/10">
                <div className="text-sm text-white/50 mb-2">Unknown Bucket</div>
                <div className="text-4xl font-bold text-amber-400">
                  {formatCurrency(meetingData.steps['1_cash_today'].unknown_bucket)}
                </div>
                <div className="mt-4 flex items-center gap-2 text-amber-400 text-sm">
                  <AlertTriangle className="w-4 h-4" />
                  <span>Requires investigation</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Step 2: Forecast */}
        {currentStep === 1 && (
          <div className="space-y-8 animate-fadeIn">
            <div className="text-center mb-12">
              <h2 className="text-3xl font-bold mb-2">13-Week Forecast</h2>
              <p className="text-white/50">Probabilistic cash projection (P50 view)</p>
            </div>
            
            <div className="bg-[#0D0D12] rounded-2xl p-8 border border-white/10">
              <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-4">
                  <button className="px-4 py-2 bg-emerald-500/20 text-emerald-400 rounded-lg text-sm font-medium">P50</button>
                  <button className="px-4 py-2 text-white/40 hover:text-white rounded-lg text-sm">P25</button>
                  <button className="px-4 py-2 text-white/40 hover:text-white rounded-lg text-sm">P75</button>
                </div>
                <div className="text-sm text-white/40">
                  Min Cash Threshold: {formatCurrency(meetingData.steps['2_forecast'].min_cash_threshold)}
                </div>
              </div>
              
              {/* Simplified forecast visualization */}
              <div className="h-64 flex items-end gap-2">
                {Array.from({ length: 13 }).map((_, i) => {
                  const height = 30 + Math.random() * 50;
                  const isRed = i === 6 || i === 9;
                  return (
                    <div key={i} className="flex-1 flex flex-col items-center gap-2">
                      <div 
                        className={`w-full rounded-t-lg transition-all ${
                          isRed ? 'bg-red-500/80' : 'bg-emerald-500/60'
                        }`}
                        style={{ height: `${height}%` }}
                      />
                      <span className="text-[10px] text-white/40">W{i + 1}</span>
                    </div>
                  );
                })}
              </div>
              
              <div className="mt-6 flex items-center gap-6 text-sm">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded bg-emerald-500/60" />
                  <span className="text-white/60">Above minimum</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded bg-red-500/80" />
                  <span className="text-white/60">Below minimum (Red Week)</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Step 3: Red Weeks */}
        {currentStep === 2 && (
          <div className="space-y-8 animate-fadeIn">
            <div className="text-center mb-12">
              <h2 className="text-3xl font-bold mb-2">Red Weeks Analysis</h2>
              <p className="text-white/50">{meetingData.steps['3_red_weeks'].count} weeks require attention</p>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="bg-red-500/10 rounded-2xl p-8 border border-red-500/20">
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-12 h-12 rounded-xl bg-red-500/20 flex items-center justify-center">
                    <AlertTriangle className="w-6 h-6 text-red-400" />
                  </div>
                  <div>
                    <div className="font-bold text-red-400">Week 7</div>
                    <div className="text-sm text-white/50">Mar 10 - Mar 16</div>
                  </div>
                </div>
                <div className="space-y-3">
                  <div className="flex justify-between text-sm">
                    <span className="text-white/60">Projected Balance</span>
                    <span className="text-red-400 font-medium">€320,000</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-white/60">Gap to Minimum</span>
                    <span className="text-red-400 font-medium">-€180,000</span>
                  </div>
                  <div className="text-xs text-white/40 mt-4">
                    <strong>Top causes:</strong> Quarterly rent (€85K), Payroll (€120K)
                  </div>
                </div>
              </div>
              
              <div className="bg-amber-500/10 rounded-2xl p-8 border border-amber-500/20">
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-12 h-12 rounded-xl bg-amber-500/20 flex items-center justify-center">
                    <Clock className="w-6 h-6 text-amber-400" />
                  </div>
                    <div>
                    <div className="font-bold text-amber-400">Week 10</div>
                    <div className="text-sm text-white/50">Mar 31 - Apr 6</div>
                      </div>
                      </div>
                <div className="space-y-3">
                  <div className="flex justify-between text-sm">
                    <span className="text-white/60">Projected Balance</span>
                    <span className="text-amber-400 font-medium">€480,000</span>
                      </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-white/60">Gap to Minimum</span>
                    <span className="text-amber-400 font-medium">-€20,000</span>
                    </div>
                  <div className="text-xs text-white/40 mt-4">
                    <strong>Top causes:</strong> Vendor payment batch (€95K)
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Step 4: Variance */}
        {currentStep === 3 && (
          <div className="space-y-8 animate-fadeIn">
            <div className="text-center mb-12">
              <h2 className="text-3xl font-bold mb-2">Variance Analysis</h2>
              <p className="text-white/50">
                Changes vs Snapshot #{meetingData.steps['4_variance'].vs_snapshot_id || 'N/A'}
              </p>
            </div>
            
            <div className="bg-[#0D0D12] rounded-2xl p-8 border border-white/10">
              <div className="flex items-center justify-center gap-8 mb-8">
                <div className="text-center">
                  <div className="text-sm text-white/50 mb-1">Last Week</div>
                  <div className="text-2xl font-bold">€2,525,000</div>
                </div>
                <ChevronRight className="w-8 h-8 text-white/20" />
                <div className="text-center">
                  <div className="text-sm text-white/50 mb-1">This Week</div>
                  <div className="text-2xl font-bold">€2,650,000</div>
                </div>
                <div className="text-center px-6 py-3 bg-emerald-500/20 rounded-xl border border-emerald-500/30">
                  <div className="text-sm text-emerald-400 mb-1">Delta</div>
                  <div className="text-2xl font-bold text-emerald-400">
                    +{formatCurrency(meetingData.steps['4_variance'].bank_delta || 0)}
                  </div>
                </div>
              </div>
              
              <div className="border-t border-white/10 pt-6">
                <h3 className="text-sm font-semibold text-white/70 mb-4">Variance Drivers</h3>
                <div className="space-y-3">
                  {[
                    { label: 'AR Collections above plan', amount: 85000, type: 'positive' },
                    { label: 'Delayed vendor payments', amount: 45000, type: 'positive' },
                    { label: 'New invoice issued', amount: -5000, type: 'negative' }
                  ].map((driver, i) => (
                    <div key={i} className="flex items-center justify-between py-2 border-b border-white/5">
                      <span className="text-white/60">{driver.label}</span>
                      <span className={driver.type === 'positive' ? 'text-emerald-400' : 'text-red-400'}>
                        {driver.type === 'positive' ? '+' : ''}{formatCurrency(driver.amount)}
                      </span>
              </div>
            ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Step 5: Actions */}
        {currentStep === 4 && (
          <div className="space-y-8 animate-fadeIn">
            <div className="text-center mb-12">
              <h2 className="text-3xl font-bold mb-2">Pending Decisions</h2>
              <p className="text-white/50">
                {meetingData.steps['5_actions'].pending_count - approvedActions.size} actions awaiting approval
              </p>
                  </div>
            
            <div className="space-y-4">
              {meetingData.steps['5_actions'].actions.map((action) => (
                <div 
                  key={action.id}
                  className={`bg-[#0D0D12] rounded-2xl p-6 border transition-all ${
                    approvedActions.has(action.id)
                      ? 'border-emerald-500/30 bg-emerald-500/5'
                      : 'border-white/10'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${
                        action.type === 'delay_vendor' 
                          ? 'bg-amber-500/20' 
                          : action.type === 'push_collections'
                          ? 'bg-blue-500/20'
                          : 'bg-purple-500/20'
                      }`}>
                        {approvedActions.has(action.id) ? (
                          <CheckCircle2 className="w-6 h-6 text-emerald-400" />
                        ) : (
                          <Clock className="w-6 h-6 text-white/60" />
                        )}
                      </div>
                      <div>
                        <div className="font-medium text-white">{action.description}</div>
                        <div className="text-sm text-white/40">
                          Owner: {action.owner} • Type: {action.type.replace('_', ' ')}
                        </div>
                      </div>
                    </div>
                    
                    {!approvedActions.has(action.id) && (
                      <button
                        onClick={() => handleApproveAction(action.id)}
                        className="px-6 py-2 bg-emerald-500 hover:bg-emerald-600 text-white rounded-lg font-medium transition-colors"
                      >
                        Approve
                      </button>
                    )}
                    
                    {approvedActions.has(action.id) && (
                      <span className="text-emerald-400 font-medium flex items-center gap-2">
                        <CheckCircle2 className="w-5 h-5" />
                        Approved
                    </span>
                    )}
                </div>
              </div>
            ))}
            </div>
          </div>
        )}

        {/* Step 6: Lock */}
        {currentStep === 5 && (
          <div className="space-y-8 animate-fadeIn">
            <div className="text-center mb-12">
              <h2 className="text-3xl font-bold mb-2">Lock Snapshot</h2>
              <p className="text-white/50">Finalize the weekly cash position</p>
            </div>
            
            <div className="max-w-xl mx-auto">
              <div className="bg-[#0D0D12] rounded-2xl p-8 border border-white/10">
                <div className="text-center mb-8">
                  <div className="w-20 h-20 mx-auto rounded-full bg-emerald-500/20 flex items-center justify-center mb-4">
                    <Lock className="w-10 h-10 text-emerald-400" />
                  </div>
                  <h3 className="text-xl font-bold mb-2">Ready to Lock?</h3>
                  <p className="text-white/50 text-sm">
                    Locked snapshots are immutable and cannot be modified.
                  </p>
                </div>
                
                <div className="space-y-4 mb-8">
                  <div className="flex items-center justify-between py-3 border-b border-white/10">
                    <span className="text-white/60">Critical Exceptions</span>
                    <span className={meetingData.steps['6_lock'].blockers.critical_exceptions === 0 
                      ? 'text-emerald-400' : 'text-red-400'
                    }>
                      {meetingData.steps['6_lock'].blockers.critical_exceptions === 0 
                        ? '✓ None' 
                        : `${meetingData.steps['6_lock'].blockers.critical_exceptions} blocking`
                      }
                    </span>
                  </div>
                  <div className="flex items-center justify-between py-3 border-b border-white/10">
                    <span className="text-white/60">Actions Approved</span>
                    <span className={approvedActions.size === meetingData.steps['5_actions'].pending_count
                      ? 'text-emerald-400' : 'text-amber-400'
                    }>
                      {approvedActions.size} / {meetingData.steps['5_actions'].pending_count}
                  </span>
                </div>
                  <div className="flex items-center justify-between py-3">
                    <span className="text-white/60">Your Role</span>
                    <span className={meetingData.steps['6_lock'].can_lock 
                      ? 'text-emerald-400' : 'text-red-400'
                    }>
                      {meetingData.steps['6_lock'].can_lock ? 'CFO (Can Lock)' : 'Cannot Lock'}
                    </span>
                  </div>
                </div>
                
                <button
                  onClick={handleLockSnapshot}
                  disabled={!meetingData.steps['6_lock'].can_lock || meetingData.steps['6_lock'].blockers.critical_exceptions > 0}
                  className={`w-full py-4 rounded-xl font-bold text-lg transition-all ${
                    meetingData.steps['6_lock'].can_lock && meetingData.steps['6_lock'].blockers.critical_exceptions === 0
                      ? 'bg-emerald-500 hover:bg-emerald-600 text-white'
                      : 'bg-white/5 text-white/30 cursor-not-allowed'
                  }`}
                >
                  <Lock className="w-5 h-5 inline-block mr-2" />
                  Lock Snapshot #{snapshotId}
                </button>
              </div>
            </div>
          </div>
          )}
        </div>

      {/* Navigation Footer */}
      <div className="fixed bottom-0 left-0 right-0 border-t border-white/10 bg-[#0D0D12]/95 backdrop-blur">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <button
            onClick={handlePrev}
            disabled={currentStep === 0}
            className={`flex items-center gap-2 px-6 py-3 rounded-xl transition-all ${
              currentStep === 0
                ? 'text-white/30 cursor-not-allowed'
                : 'bg-white/5 text-white hover:bg-white/10 border border-white/10'
            }`}
          >
            <ChevronLeft className="w-5 h-5" />
            Previous
        </button>
        
        <div className="flex items-center gap-2">
            {steps.map((_, i) => (
              <div
              key={i}
                className={`w-2 h-2 rounded-full transition-all ${
                  i === currentStep ? 'bg-emerald-500 w-6' : 
                  i < currentStep ? 'bg-emerald-500/50' : 'bg-white/20'
              }`}
            />
          ))}
        </div>

        <button
            onClick={handleNext}
            disabled={currentStep === steps.length - 1}
            className={`flex items-center gap-2 px-6 py-3 rounded-xl transition-all ${
              currentStep === steps.length - 1
                ? 'text-white/30 cursor-not-allowed'
                : 'bg-emerald-500 text-white hover:bg-emerald-600'
            }`}
          >
            Next
            <ChevronRight className="w-5 h-5" />
        </button>
        </div>
      </div>

      <style jsx>{`
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(10px); }
          to { opacity: 1; transform: translateY(0); }
        }
        .animate-fadeIn {
          animation: fadeIn 0.5s ease-out;
        }
      `}</style>
    </div>
  );
};

export default MeetingMode;
