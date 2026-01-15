'use client';

import { useState, useEffect } from 'react';
import { api } from '../lib/api';
import { 
  DollarSign, 
  TrendingDown, 
  AlertCircle, 
  ChevronRight, 
  ArrowUpRight, 
  ArrowDownRight,
  ShieldCheck,
  Zap,
  Clock,
  Filter,
  Layers,
  Calendar,
  Plus,
  X,
  HelpCircle,
  Target
} from 'lucide-react';
import { Button } from './ui/button';
import { Card, CardContent } from './ui/card';
import { AsOfStamp } from './ui/as-of-stamp';
import { TruthBadgeLegend } from './ui/truth-badge';

interface UnknownBucket {
  total_unknown_amount: number;
  total_unknown_count: number;
  unknown_pct: number;
  kpi_target_met: boolean;
  categories: {
    missing_due_dates: { count: number; amount: number };
    held_ap_bills: { count: number; amount: number };
    unmatched_bank_cash: { count: number; amount: number };
    missing_fx_rates: { count: number; amount: number; currencies: string[] };
  };
}

interface WorkspaceData {
  summary: {
    opening_cash: number;
    min_threshold: number;
    min_projected: number;
  };
  grid: {
    week_label: string;
    start_date: string;
    opening_cash: number;
    inflow_p50: number;
    inflow_p25: number;
    inflow_p75: number;
    outflow_total: number;
    outflow_committed: number;
    closing_cash: number;
    is_critical: boolean;
  }[];
}

export default function ThirteenWeekWorkspace({ snapshotId }: { snapshotId: number }) {
  const [data, setData] = useState<WorkspaceData | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedWeek, setSelectedWeek] = useState<number | null>(null);
  const [drilldownType, setDrilldownType] = useState<'inflow' | 'outflow' | null>(null);
  const [drilldownData, setDrilldownData] = useState<any[]>([]);
  const [priorities, setPriorities] = useState<any[]>([]);
  const [lateRisks, setLateRisks] = useState<any[]>([]);
  const [activeLevers, setActiveLevers] = useState<string[]>([]);
  const [unknownBucket, setUnknownBucket] = useState<UnknownBucket | null>(null);
  const [snapshotMeta, setSnapshotMeta] = useState<any>(null);
  const [leverPolicy, setLeverPolicy] = useState<{
    max_vendor_delay_days: number;
    min_cash_threshold: number;
    approval_threshold: number;
    protected_vendors: string[];
  } | null>(null);
  const [leverImpacts, setLeverImpacts] = useState<{ [key: string]: number }>({
    delay_vendor: 0,
    push_collections: 0,
    financing: 0
  });
  const [showUnknownDrilldown, setShowUnknownDrilldown] = useState(false);
  const [redWeekAnalysis, setRedWeekAnalysis] = useState<any>(null);

  const processedGrid = data?.grid.map((week, idx) => {
    let inflows = week.inflow_p50;
    let outflows = week.outflow_total;
    
    // Apply Levers
    if (activeLevers.includes('delay_vendor')) {
      // Logic: Delay 20% of outflows to the next week
      const delayAmount = week.outflow_total * 0.2;
      outflows -= delayAmount;
      // In a real implementation, we'd add this to the NEXT week's outflows
      // For this interactive simulation, we'll assume it slides out of the 13w window for immediate visibility
    }
    
    if (activeLevers.includes('push_collections')) {
      // Logic: Pull forward 10% of next week's inflows into current week
      const nextWeek = data.grid[idx + 1];
      if (nextWeek) {
        inflows += nextWeek.inflow_p50 * 0.1;
      }
    }
    
    if (activeLevers.includes('financing') && week.closing_cash < data.summary.min_threshold) {
      // Logic: Draw exactly enough to meet threshold (Simulated Facility)
      const shortfall = data.summary.min_threshold - week.closing_cash;
      inflows += Math.max(0, shortfall);
    }

    return { ...week, adjusted_inflow: inflows, adjusted_outflow: outflows };
  }) || [];

  // Recalculate balances based on adjusted flows
  let runningCash = data?.summary.opening_cash || 0;
  const finalGrid = processedGrid.map(week => {
    const opening = runningCash;
    const net = week.adjusted_inflow - week.adjusted_outflow;
    const closing = opening + net;
    runningCash = closing;
    return { 
      ...week, 
      opening_cash: opening, 
      closing_cash: closing, 
      is_critical: closing < (data?.summary.min_threshold || 0) 
    };
  });

  const [isClient, setIsClient] = useState(false);

  useEffect(() => {
    setIsClient(true);
  }, []);

  useEffect(() => {
    if (snapshotId && isClient) {
      loadWorkspace();
      loadPriorities();
      loadLateRisks();
      loadUnknownBucket();
      loadSnapshotMeta();
    }
  }, [snapshotId, isClient]);

  const loadWorkspace = async () => {
    setLoading(true);
    try {
      const res = await api.get(`/snapshots/${snapshotId}/workspace-13w`);
      setData(res.data);
    } catch (e) {
      console.error("Failed to load 13w workspace:", e);
    }
    setLoading(false);
  };

  const loadUnknownBucket = async () => {
    try {
      const res = await api.get(`/snapshots/${snapshotId}/unknown-bucket`);
      setUnknownBucket(res.data);
    } catch (e) {
      console.error("Failed to load unknown bucket:", e);
    }
  };

  const loadSnapshotMeta = async () => {
    try {
      const res = await api.get(`/snapshots/${snapshotId}`);
      setSnapshotMeta(res.data);
      // Load lever policy using entity_id from snapshot
      if (res.data.entity_id) {
        loadLeverPolicy(res.data.entity_id);
      }
    } catch (e) {
      console.error("Failed to load snapshot metadata:", e);
    }
  };

  const loadLeverPolicy = async (entityId: number) => {
    try {
      const res = await api.get(`/entities/${entityId}/lever-policy`);
      setLeverPolicy(res.data);
    } catch (e) {
      console.error("Failed to load lever policy:", e);
    }
  };

  const loadPriorities = async () => {
    try {
      const res = await api.get(`/snapshots/${snapshotId}/priorities`);
      setPriorities(res.data);
    } catch (e) {
      console.error("Failed to load priorities:", e);
    }
  };

  const loadLateRisks = async () => {
    try {
      const res = await api.get(`/snapshots/${snapshotId}/late-risk`);
      setLateRisks(res.data);
    } catch (e) {
      console.error("Failed to load late risks:", e);
    }
  };

  useEffect(() => {
    if (selectedWeek !== null && drilldownType !== null && isClient) {
      loadDrilldown();
    }
  }, [selectedWeek, drilldownType, isClient]);

  const loadDrilldown = async () => {
    try {
      const res = await api.get(`/snapshots/${snapshotId}/week-details/${selectedWeek}?type=${drilldownType}`);
      setDrilldownData(res.data);
    } catch (e) {
      console.error("Failed to load drilldown:", e);
    }
  };

  if (!isClient || loading) return <div className="p-12 text-center font-bold text-slate-300 animate-pulse">Syncing Command Center...</div>;
  if (!data) return <div className="p-12 text-center text-slate-400">No data available for this snapshot.</div>;

  const formatDate = (dateStr: string) => {
    try {
      return new Date(dateStr).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
    } catch {
      return dateStr;
    }
  };

  const formatFullDate = (dateStr: string) => {
    try {
      return new Date(dateStr).toLocaleDateString();
    } catch {
      return dateStr;
    }
  };

  return (
    <div className="space-y-10">
      {/* As-Of Stamp & Truth Badge Legend */}
      <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4">
        {snapshotMeta && (
          <AsOfStamp 
            timestamp={snapshotMeta.metadata?.as_of || snapshotMeta.created_at || new Date().toISOString()}
            label={`Snapshot: ${snapshotMeta.name}`}
            source="bank"
          />
        )}
        <TruthBadgeLegend />
      </div>

      {/* CFO Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-6 gap-6">
        {[
          { label: 'Opening Cash', value: `€${(data.summary.opening_cash || 0).toLocaleString()}`, icon: DollarSign, color: 'bg-slate-50 text-slate-600' },
          { label: 'Min Projected', value: `€${(data.summary.min_projected || 0).toLocaleString()}`, icon: TrendingDown, color: 'bg-red-50 text-red-600' },
          { label: 'Min Threshold', value: `€${(data.summary.min_threshold || 0).toLocaleString()}`, icon: ShieldCheck, color: 'bg-amber-50 text-amber-600' },
          { label: '4W Inflow', value: `€${(data.grid.slice(0, 4).reduce((sum, w) => sum + (w.inflow_p50 || 0), 0)).toLocaleString()}`, icon: ArrowUpRight, color: 'bg-emerald-50 text-emerald-600' },
          { label: '4W Outflow', value: `€${(data.grid.slice(0, 4).reduce((sum, w) => sum + (w.outflow_total || 0), 0)).toLocaleString()}`, icon: ArrowDownRight, color: 'bg-blue-50 text-blue-600' },
        ].map((stat, i) => (
          <div key={i} className="bg-white p-6 rounded-[32px] border border-[#E5E5E7] shadow-sm hover:shadow-md transition-all">
            <div className={`w-8 h-8 ${stat.color} rounded-xl flex items-center justify-center mb-4`}>
              <stat.icon className="h-4 w-4" />
            </div>
            <div className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1">{stat.label}</div>
            <div className="text-xl font-black text-[#1A1A1A] tracking-tighter">{stat.value}</div>
          </div>
        ))}
        
        {/* Unknown Bucket Card - CFO Trust Feature */}
        {unknownBucket && (
          <div 
            className={`bg-white p-6 rounded-[32px] border shadow-sm hover:shadow-md transition-all cursor-pointer ${
              unknownBucket.kpi_target_met 
                ? 'border-emerald-200 bg-emerald-50/30' 
                : 'border-amber-200 bg-amber-50/30'
            }`}
            onClick={() => setShowUnknownDrilldown(true)}
          >
            <div className={`w-8 h-8 rounded-xl flex items-center justify-center mb-4 ${
              unknownBucket.kpi_target_met ? 'bg-emerald-100 text-emerald-600' : 'bg-amber-100 text-amber-600'
            }`}>
              <HelpCircle className="h-4 w-4" />
            </div>
            <div className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1">Unknown Items</div>
            <div className="text-xl font-black text-[#1A1A1A] tracking-tighter">
              {unknownBucket.unknown_pct.toFixed(1)}%
            </div>
            <div className="mt-3 space-y-2">
              <div className="flex items-center justify-between text-[10px]">
                <span className="font-bold text-slate-500">Target: &lt;5%</span>
                <span className={`font-black uppercase ${unknownBucket.kpi_target_met ? 'text-emerald-600' : 'text-amber-600'}`}>
                  {unknownBucket.kpi_target_met ? 'Met' : 'Action Needed'}
                </span>
              </div>
              {/* Progress bar */}
              <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
                <div 
                  className={`h-full rounded-full transition-all ${
                    unknownBucket.kpi_target_met ? 'bg-emerald-500' : 'bg-amber-500'
                  }`}
                  style={{ width: `${Math.min(100, unknownBucket.unknown_pct * 10)}%` }}
                />
              </div>
              <div className="text-[9px] font-medium text-slate-400">
                €{unknownBucket.total_unknown_amount.toLocaleString()} ({unknownBucket.total_unknown_count} items)
              </div>
              <div className="text-[9px] font-bold text-blue-600 mt-2 hover:underline">
                Click to drill down →
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Red Weeks Alert Strip */}
      <div className="flex items-center gap-3 overflow-x-auto pb-2 scrollbar-hide">
        <div className="text-[10px] font-black text-slate-400 uppercase tracking-widest mr-2 shrink-0">Status Timeline:</div>
        {finalGrid.map((week, i) => (
          <div 
            key={i} 
            className={`px-4 py-2 rounded-full border text-[10px] font-bold tracking-widest flex items-center gap-2 shrink-0 ${
              week.is_critical 
                ? 'bg-red-50 border-red-100 text-red-600 animate-pulse' 
                : 'bg-emerald-50 border-emerald-100 text-emerald-600'
            }`}
          >
            <div className={`w-1.5 h-1.5 rounded-full ${week.is_critical ? 'bg-red-600' : 'bg-emerald-600'}`} />
            {week.week_label}
          </div>
        ))}
      </div>

      {/* Main Grid Workspace */}
      <div className="bg-white rounded-[48px] border border-[#E5E5E7] overflow-hidden shadow-2xl shadow-slate-200/40">
        <div className="p-8 border-b border-[#E5E5E7] bg-slate-50/50 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <h3 className="text-lg font-black tracking-tight text-[#1A1A1A]">Unified Cash Ledger (13-Weeks)</h3>
            <div className="flex items-center gap-2 px-3 py-1 bg-white border border-[#E5E5E7] rounded-full text-[10px] font-bold text-slate-500 uppercase tracking-widest shadow-sm">
              <Zap className="h-3 w-3 text-amber-500" /> Operational Source
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button 
              variant="ghost" 
              size="sm" 
              className="text-[10px] font-bold uppercase tracking-widest text-slate-400 hover:text-blue-600"
              onClick={() => alert("Currency Filter: Currently displaying EUR reporting currency. Entity consolidation active.")}
            >
              <Filter className="h-3 w-3 mr-2" /> Filter
            </Button>
            <Button 
              size="sm" 
              className="bg-[#1A1A1A] text-white hover:bg-slate-800 rounded-xl h-8 px-4 text-[10px] font-bold uppercase tracking-widest"
              onClick={() => alert("Add Outflow: This manual override will be recorded in the Audit Log.")}
            >
              <Plus className="h-3 w-3 mr-2" /> Add Outflow
            </Button>
          </div>
        </div>
        
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-[#E5E5E7]">
                <th className="py-6 px-8 text-[10px] font-black text-slate-400 uppercase tracking-widest sticky left-0 bg-white z-10 w-48">Metric</th>
                {finalGrid.map((w, i) => (
                  <th key={i} className="py-6 px-6 text-[10px] font-black text-slate-600 uppercase tracking-widest min-w-[140px] text-right">
                    {w.week_label}
                    <div className="text-[9px] font-medium text-slate-400 normal-case mt-1">{formatDate(w.start_date)}</div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50">
              <tr className="hover:bg-slate-50/30 transition-colors group">
                <td className="py-5 px-8 text-xs font-bold text-slate-500 sticky left-0 bg-white group-hover:bg-slate-50/30 z-10">Opening Cash</td>
                {finalGrid.map((w, i) => (
                  <td key={i} className="py-5 px-6 text-xs font-black text-slate-700 text-right tabular-nums">€{w.opening_cash.toLocaleString()}</td>
                ))}
              </tr>
              <tr className="hover:bg-emerald-50/20 transition-colors group">
                <td className="py-5 px-8 text-xs font-bold text-emerald-600 sticky left-0 bg-white group-hover:bg-emerald-50/20 z-10">Cash In (Predicted)</td>
                {finalGrid.map((w, i) => (
                  <td 
                    key={i} 
                    className="py-5 px-6 text-xs font-black text-emerald-600 text-right tabular-nums cursor-pointer hover:underline" 
                    onClick={() => {
                      setSelectedWeek(i);
                      setDrilldownType('inflow');
                    }}
                  >
                    +€{(w.adjusted_inflow || 0).toLocaleString()}
                  </td>
                ))}
              </tr>
              <tr className="hover:bg-blue-50/20 transition-colors group">
                <td className="py-5 px-8 text-xs font-bold text-blue-600 sticky left-0 bg-white group-hover:bg-blue-50/20 z-10">Cash Out (Committed)</td>
                {finalGrid.map((w, i) => (
                  <td 
                    key={i} 
                    className="py-5 px-6 text-xs font-black text-blue-600 text-right tabular-nums cursor-pointer hover:underline" 
                    onClick={() => {
                      setSelectedWeek(i);
                      setDrilldownType('outflow');
                    }}
                  >
                    -€{(w.adjusted_outflow || 0).toLocaleString()}
                  </td>
                ))}
              </tr>
              <tr className="bg-slate-50/20 border-t-2 border-slate-100">
                <td className="py-6 px-8 text-xs font-black text-slate-900 sticky left-0 bg-white z-10">Closing Balance</td>
                {finalGrid.map((w, i) => (
                  <td key={i} className={`py-6 px-6 text-sm font-black text-right tabular-nums ${w.is_critical ? 'text-red-600' : 'text-slate-900'}`}>
                    €{(w.closing_cash || 0).toLocaleString()}
                  </td>
                ))}
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-10">
        {/* Action Center - Cash Levers */}
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Layers className="h-5 w-5 text-emerald-500" />
              <h3 className="text-xl font-black tracking-tight text-[#1A1A1A]">Cash Actions</h3>
            </div>
            {leverPolicy && (
              <div className="flex items-center gap-2 text-[10px] font-bold text-emerald-600 bg-emerald-50 px-3 py-1.5 rounded-full uppercase tracking-widest">
                <ShieldCheck className="h-3 w-3" />
                Policy Active
              </div>
            )}
          </div>
          
          {/* Policy Guardrails Banner */}
          {leverPolicy && (
            <div className="bg-gradient-to-r from-slate-50 to-blue-50/30 rounded-2xl p-4 border border-slate-100 space-y-2">
              <div className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Your Policy Limits</div>
              <div className="flex flex-wrap gap-3">
                <div className="px-3 py-1.5 bg-white rounded-lg border border-slate-200 text-[10px] font-bold text-slate-600 shadow-sm">
                  Max Payment Delay: {leverPolicy.max_vendor_delay_days} days
                </div>
                <div className="px-3 py-1.5 bg-white rounded-lg border border-slate-200 text-[10px] font-bold text-slate-600 shadow-sm">
                  Min Cash Reserve: €{leverPolicy.min_cash_threshold.toLocaleString()}
                </div>
                <div className="px-3 py-1.5 bg-amber-50 rounded-lg border border-amber-200 text-[10px] font-bold text-amber-700">
                  CFO Sign-off &gt; €{leverPolicy.approval_threshold.toLocaleString()}
                </div>
                {leverPolicy.protected_vendors?.length > 0 && (
                  <div className="px-3 py-1.5 bg-red-50 rounded-lg border border-red-200 text-[10px] font-bold text-red-600">
                    {leverPolicy.protected_vendors.length} Protected Vendor(s)
                  </div>
                )}
              </div>
            </div>
          )}

          <div className="grid grid-cols-1 gap-4">
            {[
              { 
                id: 'delay_vendor', 
                label: 'Extend Supplier Payments', 
                detail: leverPolicy ? `Push outgoing payments by ${leverPolicy.max_vendor_delay_days} days` : 'Push outgoing payments by 7 days',
                impact: '€124,500', 
                impactNum: 124500,
                color: 'border-blue-200 text-blue-700 bg-blue-50/50',
                requiresApproval: leverPolicy ? 124500 > leverPolicy.approval_threshold : false
              },
              { 
                id: 'push_collections', 
                label: 'Accelerate Customer Collections', 
                detail: 'Contact top customers to collect 5 days earlier',
                impact: '€89,200', 
                impactNum: 89200,
                color: 'border-emerald-200 text-emerald-700 bg-emerald-50/50',
                requiresApproval: leverPolicy ? 89200 > leverPolicy.approval_threshold : false
              },
              { 
                id: 'financing', 
                label: 'Use Credit Facility', 
                detail: 'Draw from available credit line to cover shortfall',
                impact: '€500,000', 
                impactNum: 500000,
                color: 'border-amber-200 text-amber-700 bg-amber-50/50',
                requiresApproval: leverPolicy ? 500000 > leverPolicy.approval_threshold : true
              },
            ].map((lever) => (
              <button 
                key={lever.id}
                onClick={() => setActiveLevers(prev => prev.includes(lever.id) ? prev.filter(i => i !== lever.id) : [...prev, lever.id])}
                className={`flex items-center justify-between p-6 rounded-3xl border-2 transition-all hover:shadow-lg ${
                  activeLevers.includes(lever.id) ? lever.color + ' shadow-md' : 'border-[#F1F1F3] hover:border-slate-200 bg-white'
                }`}
              >
                <div className="flex items-center gap-4">
                  <div className={`w-4 h-4 rounded-lg flex items-center justify-center ${activeLevers.includes(lever.id) ? 'bg-current text-white' : 'bg-slate-100'}`}>
                    {activeLevers.includes(lever.id) && <span className="text-[10px]">✓</span>}
                  </div>
                  <div className="text-left">
                    <span className="text-sm font-bold tracking-tight block">{lever.label}</span>
                    <span className="text-[11px] font-medium text-slate-400">{lever.detail}</span>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  {lever.requiresApproval && (
                    <span className="px-2.5 py-1 bg-amber-100 text-amber-700 rounded-lg text-[9px] font-black uppercase tracking-widest">
                      Needs Approval
                    </span>
                  )}
                  <div className="text-right">
                    <div className="text-xs font-black text-slate-900">{lever.impact}</div>
                    <div className="text-[9px] font-bold text-slate-400 uppercase">Cash Impact</div>
                  </div>
                </div>
              </button>
            ))}
          </div>

          {/* Priority Collection Targets */}
          <div className="space-y-4 pt-4">
            <div className="flex items-center justify-between">
              <h4 className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Priority Collection Calls</h4>
              <span className="text-[9px] font-bold text-blue-600 bg-blue-50 px-2 py-1 rounded-lg">Top 5 by Impact</span>
            </div>
            <div className="bg-white rounded-[32px] border border-[#E5E5E7] overflow-hidden shadow-sm">
              <div className="max-h-[300px] overflow-y-auto divide-y divide-slate-50">
                {priorities.slice(0, 5).map((p, i) => (
                  <div key={i} className="p-5 flex items-center justify-between group hover:bg-blue-50/30 transition-colors cursor-pointer">
                    <div className="flex items-center gap-4">
                      <div className="w-8 h-8 rounded-xl bg-blue-50 flex items-center justify-center text-[10px] font-black text-blue-600">
                        #{i + 1}
                      </div>
                      <div>
                        <div className="text-sm font-black text-[#1A1A1A] tracking-tight">{p.customer}</div>
                        <div className="text-[10px] font-medium text-slate-400">Invoice #{p.invoice_number}</div>
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-lg font-black text-emerald-600">€{p.amount.toLocaleString()}</div>
                      <div className="text-[9px] font-bold text-blue-600 bg-blue-50 px-2 py-0.5 rounded-full inline-block">Call this week</div>
                    </div>
                  </div>
                ))}
                {priorities.length === 0 && (
                  <div className="p-10 text-center">
                    <p className="text-sm text-slate-400">No priority invoices identified for follow-up.</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* High Risk Receivables Panel */}
        <div className="space-y-6">
          <div className="flex items-center gap-3">
            <AlertCircle className="h-5 w-5 text-amber-500" />
            <h3 className="text-xl font-black tracking-tight text-[#1A1A1A]">At-Risk Receivables</h3>
          </div>
          <div className="bg-white rounded-[40px] border border-[#E5E5E7] overflow-hidden shadow-sm">
            <div className="divide-y divide-slate-50">
              {lateRisks.slice(0, 5).map((risk, i) => (
                <div key={i} className="p-6 hover:bg-amber-50/30 transition-all flex items-center justify-between group cursor-pointer">
                  <div className="space-y-1.5">
                    <div className="text-sm font-black text-[#1A1A1A] tracking-tight">{risk.customer}</div>
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] font-bold text-slate-400">Invoice #{risk.invoice_number}</span>
                      <span className="text-[9px] font-black text-amber-600 uppercase tracking-widest bg-amber-50 px-2 py-0.5 rounded-full border border-amber-100">
                        May Pay Late
                      </span>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-lg font-black text-[#1A1A1A]">€{(risk.amount || 0).toLocaleString()}</div>
                    <div className="text-[10px] font-medium text-slate-400">Expected: {formatFullDate(risk.predicted_date || '')}</div>
                  </div>
                </div>
              ))}
              {lateRisks.length === 0 && (
                <div className="p-16 text-center">
                  <div className="w-16 h-16 bg-emerald-50 rounded-2xl flex items-center justify-center mx-auto mb-4">
                    <AlertCircle className="h-8 w-8 text-emerald-400" />
                  </div>
                  <h4 className="text-lg font-black text-emerald-600 mb-2">All Clear</h4>
                  <p className="text-sm text-slate-400 max-w-xs mx-auto">
                    No invoices are predicted to pay late in the next 4 weeks. Great collection performance!
                  </p>
                </div>
              )}
            </div>
            {lateRisks.length > 0 && (
              <div className="p-4 bg-gradient-to-r from-slate-50 to-blue-50/30 text-center border-t border-slate-100">
                <Button variant="ghost" className="text-[10px] font-bold uppercase tracking-widest text-blue-600 hover:bg-white rounded-xl">
                  Open Collections Dashboard <ChevronRight className="h-3 w-3 ml-2" />
                </Button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Drill-down Sidebar */}
      {selectedWeek !== null && (
        <div className="fixed inset-y-0 right-0 w-[400px] bg-white border-l border-[#E5E5E7] shadow-[0_0_100px_rgba(0,0,0,0.1)] z-[100] p-10 animate-in slide-in-from-right duration-300">
          <div className="flex items-center justify-between mb-10">
            <div>
              <h4 className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1">
                {drilldownType === 'inflow' ? 'Inflow Details' : 'Outflow Details'}
              </h4>
              <h3 className="text-2xl font-black tracking-tight text-[#1A1A1A]">Week {selectedWeek + 1}</h3>
            </div>
            <button 
              onClick={() => { setSelectedWeek(null); setDrilldownType(null); }}
              className="p-2 hover:bg-slate-50 rounded-full transition-colors"
            >
              <X className="h-5 w-5 text-slate-400" />
            </button>
          </div>

          <div className="space-y-6">
            {drilldownData.length > 0 ? (
              drilldownData.map((item, idx) => (
                <div key={idx} className="p-5 rounded-2xl border border-[#F1F1F3] bg-slate-50/30 space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-black text-[#1A1A1A] tracking-tight truncate max-w-[200px]">
                      {drilldownType === 'inflow' ? item.customer : item.description}
                    </span>
                    <span className={`text-sm font-black ${drilldownType === 'inflow' ? 'text-emerald-600' : 'text-blue-600'}`}>
                      {drilldownType === 'inflow' ? '+' : '-'}€{item.amount.toLocaleString()}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 text-[10px] font-bold text-slate-400 uppercase tracking-widest">
                      <Clock className="h-3 w-3" /> {formatFullDate(item.date)}
                    </div>
                    {drilldownType === 'inflow' ? (
                      <span className="text-[9px] font-black text-emerald-500 uppercase tracking-widest bg-emerald-50 px-2 py-0.5 rounded-full">
                        {item.confidence} Conf.
                      </span>
                    ) : (
                      <span className={`text-[9px] font-black uppercase tracking-widest px-2 py-0.5 rounded-full ${item.is_discretionary ? 'bg-amber-50 text-amber-600' : 'bg-blue-50 text-blue-600'}`}>
                        {item.is_discretionary ? 'Delayable' : 'Committed'}
                      </span>
                    )}
                  </div>
                </div>
              ))
            ) : (
              <div className="py-20 text-center text-slate-300 font-bold text-xs italic">No items found for this week.</div>
            )}
          </div>
        </div>
      )}

      {/* Unknown Bucket Drilldown Panel */}
      {showUnknownDrilldown && unknownBucket && (
        <div className="fixed inset-y-0 right-0 w-[450px] bg-white border-l border-[#E5E5E7] shadow-[0_0_100px_rgba(0,0,0,0.1)] z-[100] animate-in slide-in-from-right duration-300 overflow-y-auto">
          <div className="p-8 border-b border-[#E5E5E7] sticky top-0 bg-white z-10">
            <div className="flex items-center justify-between">
              <div>
                <h4 className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1">CFO Trust</h4>
                <h3 className="text-2xl font-black tracking-tight text-[#1A1A1A]">Unknown Items</h3>
              </div>
              <button 
                onClick={() => setShowUnknownDrilldown(false)}
                className="p-2 hover:bg-slate-50 rounded-full transition-colors"
              >
                <X className="h-5 w-5 text-slate-400" />
              </button>
            </div>
            <div className="mt-4 flex items-center gap-4">
              <div className={`text-3xl font-black ${unknownBucket.kpi_target_met ? 'text-emerald-600' : 'text-amber-600'}`}>
                {unknownBucket.unknown_pct.toFixed(1)}%
              </div>
              <div className="text-xs text-slate-500">
                €{unknownBucket.total_unknown_amount.toLocaleString()} across {unknownBucket.total_unknown_count} items
              </div>
            </div>
          </div>
          
          <div className="p-8 space-y-6">
            <div className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Breakdown by Category</div>
            
            {/* Missing Due Dates */}
            <div className="p-5 rounded-2xl border border-red-100 bg-red-50/30 space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-xl bg-red-100 flex items-center justify-center">
                    <Calendar className="h-4 w-4 text-red-600" />
                  </div>
                  <div>
                    <div className="text-sm font-black text-[#1A1A1A]">Missing Due Dates</div>
                    <div className="text-[10px] text-slate-500">{unknownBucket.categories?.missing_due_dates?.count || 0} invoices</div>
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-sm font-black text-red-600">€{(unknownBucket.categories?.missing_due_dates?.amount || 0).toLocaleString()}</div>
                </div>
              </div>
              <div className="text-[10px] text-slate-500 bg-white/50 p-3 rounded-xl">
                <strong>Action:</strong> Update invoices with missing due date fields in ERP or manually set expected dates.
              </div>
            </div>

            {/* Held AP Bills */}
            <div className="p-5 rounded-2xl border border-amber-100 bg-amber-50/30 space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-xl bg-amber-100 flex items-center justify-center">
                    <Clock className="h-4 w-4 text-amber-600" />
                  </div>
                  <div>
                    <div className="text-sm font-black text-[#1A1A1A]">Held AP Bills</div>
                    <div className="text-[10px] text-slate-500">{unknownBucket.categories?.held_ap_bills?.count || 0} bills on hold</div>
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-sm font-black text-amber-600">€{(unknownBucket.categories?.held_ap_bills?.amount || 0).toLocaleString()}</div>
                </div>
              </div>
              <div className="text-[10px] text-slate-500 bg-white/50 p-3 rounded-xl">
                <strong>Action:</strong> Review held bills and either release for payment or cancel if no longer needed.
              </div>
            </div>

            {/* Unmatched Bank Cash */}
            <div className="p-5 rounded-2xl border border-blue-100 bg-blue-50/30 space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-xl bg-blue-100 flex items-center justify-center">
                    <Target className="h-4 w-4 text-blue-600" />
                  </div>
                  <div>
                    <div className="text-sm font-black text-[#1A1A1A]">Unmatched Bank Cash</div>
                    <div className="text-[10px] text-slate-500">{unknownBucket.categories?.unmatched_bank_cash?.count || 0} transactions</div>
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-sm font-black text-blue-600">€{(unknownBucket.categories?.unmatched_bank_cash?.amount || 0).toLocaleString()}</div>
                </div>
              </div>
              <div className="text-[10px] text-slate-500 bg-white/50 p-3 rounded-xl">
                <strong>Action:</strong> Review unmatched bank transactions and match to invoices or classify as other cash flows.
              </div>
            </div>

            {/* Missing FX Rates */}
            <div className="p-5 rounded-2xl border border-slate-200 bg-slate-50/30 space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-xl bg-slate-100 flex items-center justify-center">
                    <DollarSign className="h-4 w-4 text-slate-600" />
                  </div>
                  <div>
                    <div className="text-sm font-black text-[#1A1A1A]">Missing FX Rates</div>
                    <div className="text-[10px] text-slate-500">
                      {unknownBucket.categories?.missing_fx_rates?.count || 0} items in {(unknownBucket.categories?.missing_fx_rates?.currencies || []).join(', ') || 'N/A'}
                    </div>
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-sm font-black text-slate-600">€{(unknownBucket.categories?.missing_fx_rates?.amount || 0).toLocaleString()}</div>
                </div>
              </div>
              <div className="text-[10px] text-slate-500 bg-white/50 p-3 rounded-xl">
                <strong>Action:</strong> Add FX rates for missing currencies or configure automatic rate fetching.
              </div>
            </div>

            {/* KPI Target */}
            <div className="mt-8 p-5 rounded-2xl border border-slate-200 bg-white">
              <div className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-3">KPI Target Status</div>
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-xs text-slate-600">Target: Unknown &lt;5%</div>
                  <div className="text-xs text-slate-600">Current: {unknownBucket.unknown_pct.toFixed(1)}%</div>
                </div>
                <div className={`px-4 py-2 rounded-xl font-black text-xs ${
                  unknownBucket.kpi_target_met 
                    ? 'bg-emerald-100 text-emerald-700' 
                    : 'bg-amber-100 text-amber-700'
                }`}>
                  {unknownBucket.kpi_target_met ? '✓ TARGET MET' : '⚠ ACTION NEEDED'}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
