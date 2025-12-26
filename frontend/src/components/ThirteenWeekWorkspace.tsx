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
  X
} from 'lucide-react';
import { Button } from './ui/button';
import { Card, CardContent } from './ui/card';

interface WorkspaceData {
  summary: {
    opening_cash: number;
    min_cash_threshold: number;
    min_projected_cash: number;
    total_inflows_4w: number;
    total_outflows_4w: number;
  };
  grid: any[];
  top_risks: any[];
}

export default function ThirteenWeekWorkspace({ snapshotId }: { snapshotId: number }) {
  const [data, setData] = useState<WorkspaceData | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedWeek, setSelectedWeek] = useState<number | null>(null);
  const [drilldownType, setDrilldownType] = useState<'inflow' | 'outflow' | null>(null);
  const [drilldownData, setDrilldownData] = useState<any[]>([]);
  const [activeLevers, setActiveLevers] = useState<string[]>([]);
  const [priorities, setPriorities] = useState<any[]>([]);

  const [isClient, setIsClient] = useState(false);

  useEffect(() => {
    setIsClient(true);
  }, []);

  useEffect(() => {
    if (snapshotId && isClient) {
      loadWorkspace();
      loadPriorities();
    }
  }, [snapshotId, isClient]);

  useEffect(() => {
    if (selectedWeek !== null && drilldownType !== null && isClient) {
      loadDrilldown();
    }
  }, [selectedWeek, drilldownType, isClient]);

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

  const loadPriorities = async () => {
    try {
      const res = await api.get(`/snapshots/${snapshotId}/priorities`);
      setPriorities(res.data);
    } catch (e) {
      console.error("Failed to load priorities:", e);
    }
  };

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
      {/* CFO Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-6">
        {[
          { label: 'Opening Cash', value: `€${data.summary.opening_cash.toLocaleString()}`, icon: DollarSign, color: 'bg-slate-50 text-slate-600' },
          { label: 'Min Projected', value: `€${data.summary.min_projected_cash.toLocaleString()}`, icon: TrendingDown, color: 'bg-red-50 text-red-600' },
          { label: 'Inflows (4W)', value: `€${data.summary.total_inflows_4w.toLocaleString()}`, icon: ArrowUpRight, color: 'bg-emerald-50 text-emerald-600' },
          { label: 'Outflows (4W)', value: `€${data.summary.total_outflows_4w.toLocaleString()}`, icon: ArrowDownRight, color: 'bg-blue-50 text-blue-600' },
          { label: 'Risk Coverage', value: '1.2x', icon: ShieldCheck, color: 'bg-amber-50 text-amber-600' },
        ].map((stat, i) => (
          <div key={i} className="bg-white p-6 rounded-[32px] border border-[#E5E5E7] shadow-sm hover:shadow-md transition-all">
            <div className={`w-8 h-8 ${stat.color} rounded-xl flex items-center justify-center mb-4`}>
              <stat.icon className="h-4 w-4" />
            </div>
            <div className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1">{stat.label}</div>
            <div className="text-xl font-black text-[#1A1A1A] tracking-tighter">{stat.value}</div>
          </div>
        ))}
      </div>

      {/* Red Weeks Alert Strip */}
      <div className="flex items-center gap-3 overflow-x-auto pb-2 scrollbar-hide">
        <div className="text-[10px] font-black text-slate-400 uppercase tracking-widest mr-2 shrink-0">Status Timeline:</div>
        {data.grid.map((week, i) => (
          <div 
            key={i} 
            className={`px-4 py-2 rounded-full border text-[10px] font-bold tracking-widest flex items-center gap-2 shrink-0 ${
              week.is_red 
                ? 'bg-red-50 border-red-100 text-red-600 animate-pulse' 
                : 'bg-emerald-50 border-emerald-100 text-emerald-600'
            }`}
          >
            <div className={`w-1.5 h-1.5 rounded-full ${week.is_red ? 'bg-red-600' : 'bg-emerald-600'}`} />
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
                {data.grid.map((w, i) => (
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
                {data.grid.map((w, i) => (
                  <td key={i} className="py-5 px-6 text-xs font-black text-slate-700 text-right tabular-nums">€{w.opening_cash.toLocaleString()}</td>
                ))}
              </tr>
              <tr className="hover:bg-emerald-50/20 transition-colors group">
                <td className="py-5 px-8 text-xs font-bold text-emerald-600 sticky left-0 bg-white group-hover:bg-emerald-50/20 z-10">Cash In (Predicted)</td>
                {data.grid.map((w, i) => (
                  <td 
                    key={i} 
                    className="py-5 px-6 text-xs font-black text-emerald-600 text-right tabular-nums cursor-pointer hover:underline" 
                    onClick={() => {
                      setSelectedWeek(i);
                      setDrilldownType('inflow');
                    }}
                  >
                    +€{w.inflows.toLocaleString()}
                  </td>
                ))}
              </tr>
              <tr className="hover:bg-blue-50/20 transition-colors group">
                <td className="py-5 px-8 text-xs font-bold text-blue-600 sticky left-0 bg-white group-hover:bg-blue-50/20 z-10">Cash Out (Committed)</td>
                {data.grid.map((w, i) => (
                  <td 
                    key={i} 
                    className="py-5 px-6 text-xs font-black text-blue-600 text-right tabular-nums cursor-pointer hover:underline" 
                    onClick={() => {
                      setSelectedWeek(i);
                      setDrilldownType('outflow');
                    }}
                  >
                    -€{w.outflows.toLocaleString()}
                  </td>
                ))}
              </tr>
              <tr className="bg-slate-50/20 border-t-2 border-slate-100">
                <td className="py-6 px-8 text-xs font-black text-slate-900 sticky left-0 bg-white z-10">Closing Balance</td>
                {data.grid.map((w, i) => (
                  <td key={i} className={`py-6 px-6 text-sm font-black text-right tabular-nums ${w.is_red ? 'text-red-600' : 'text-slate-900'}`}>
                    €{w.closing_cash.toLocaleString()}
                  </td>
                ))}
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-10">
        {/* Action Center - Liquidity Levers */}
        <div className="space-y-6">
          <div className="flex items-center gap-3">
            <Layers className="h-5 w-5 text-slate-400" />
            <h3 className="text-xl font-black tracking-tight text-[#1A1A1A]">Liquidity Levers</h3>
          </div>
          <div className="grid grid-cols-1 gap-4">
            {[
              { id: 'delay_vendor', label: 'Delay Vendor Payments (+7d)', impact: '€124,500', color: 'border-blue-100 text-blue-700 bg-blue-50/30' },
              { id: 'push_collections', label: 'Aggressive Collections (-5d)', impact: '€89,200', color: 'border-emerald-100 text-emerald-700 bg-emerald-50/30' },
              { id: 'financing', label: 'Draw Credit Line (Facility A)', impact: '€500,000', color: 'border-amber-100 text-amber-700 bg-amber-50/30' },
            ].map((lever) => (
              <button 
                key={lever.id}
                onClick={() => setActiveLevers(prev => prev.includes(lever.id) ? prev.filter(i => i !== lever.id) : [...prev, lever.id])}
                className={`flex items-center justify-between p-6 rounded-3xl border-2 transition-all ${
                  activeLevers.includes(lever.id) ? lever.color : 'border-[#F1F1F3] hover:border-slate-200 bg-white'
                }`}
              >
                <div className="flex items-center gap-4">
                  <div className={`w-2.5 h-2.5 rounded-full ${activeLevers.includes(lever.id) ? 'bg-current' : 'bg-slate-200'}`} />
                  <span className="text-sm font-bold tracking-tight">{lever.label}</span>
                </div>
                <div className="text-xs font-black uppercase tracking-widest opacity-60">Impact: {lever.impact}</div>
              </button>
            ))}
          </div>

          {/* Collections Playbook Action Center */}
          <div className="space-y-4 pt-4">
            <h4 className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Target Collections Push</h4>
            <div className="bg-white rounded-[32px] border border-[#E5E5E7] overflow-hidden">
              <div className="max-h-[300px] overflow-y-auto divide-y divide-slate-50">
                {priorities.slice(0, 5).map((p, i) => (
                  <div key={i} className="p-5 flex items-center justify-between group">
                    <div className="flex items-center gap-4">
                      <div className="w-8 h-8 rounded-full bg-slate-50 flex items-center justify-center text-[10px] font-black text-slate-400">
                        {i + 1}
                      </div>
                      <div>
                        <div className="text-sm font-black text-[#1A1A1A] tracking-tight">{p.customer}</div>
                        <div className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Inv: {p.invoice_number}</div>
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-sm font-black text-emerald-600">€{p.amount.toLocaleString()}</div>
                      <div className="text-[9px] font-bold text-slate-400 uppercase tracking-widest">Action: Protect W{p.impact_week}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* High Risk Receivables Panel */}
        <div className="space-y-6">
          <div className="flex items-center gap-3">
            <AlertCircle className="h-5 w-5 text-red-400" />
            <h3 className="text-xl font-black tracking-tight text-[#1A1A1A]">Top Risks (4W Window)</h3>
          </div>
          <div className="bg-white rounded-[40px] border border-[#E5E5E7] overflow-hidden">
            <div className="divide-y divide-slate-50">
              {data.top_risks.map((risk, i) => (
                <div key={i} className="p-6 hover:bg-slate-50/50 transition-all flex items-center justify-between group">
                  <div className="space-y-1">
                    <div className="text-sm font-black text-[#1A1A1A] tracking-tight">{risk.customer}</div>
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Inv: {risk.invoice_number}</span>
                      <span className="text-[10px] font-black text-red-500 uppercase tracking-widest bg-red-50 px-2 py-0.5 rounded-full">High Risk</span>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-sm font-black text-[#1A1A1A]">€{(risk.amount || 0).toLocaleString()}</div>
                    <div className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Est: {formatFullDate(risk.predicted_date || '')}</div>
                  </div>
                </div>
              ))}
            </div>
            <div className="p-4 bg-slate-50 text-center">
              <Button variant="ghost" className="text-[10px] font-bold uppercase tracking-widest text-blue-600 hover:bg-white">
                View Collections Playbook <ChevronRight className="h-3 w-3 ml-2" />
              </Button>
            </div>
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
    </div>
  );
}

