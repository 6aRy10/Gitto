'use client';

import { useState, useEffect } from 'react';
import { 
  Upload, TrendingUp, AlertCircle, Calendar, RefreshCcw, Trash2, DollarSign, 
  LayoutDashboard, BarChart3, Receipt, Briefcase, FileJson, MessageCircle, Settings,
  ChevronRight, Search, Plus, Database, ShieldCheck
} from "lucide-react";
import { getSnapshots, getForecast, getKPIs, uploadExcel, api } from '@/lib/api';
import { 
  ResponsiveContainer,
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  LineChart, Line, BarChart, Bar,
} from 'recharts';

import FPAView from '@/components/FPAView';
import WeeklyMeetingView from '@/components/WeeklyMeetingView';
import BankLedgerView from '@/components/BankLedgerView';
import OperationsDeskView from '@/components/OperationsDeskView';
import ReportingView from '@/components/ReportingView';
import ThirteenWeekWorkspace from '@/components/ThirteenWeekWorkspace';
import { Button } from "@/components/ui/button";

export default function Dashboard() {
  const [activeTab, setActiveTab] = useState('cfo');
  const [snapshots, setSnapshots] = useState<any[]>([]);
  const [entities, setEntities] = useState<any[]>([]);
  const [selectedEntity, setSelectedEntity] = useState<number | null>(null);
  const [selectedSnapshot, setSelectedSnapshot] = useState<number | null>(null);
  const [compareSnapshot, setCompareSnapshot] = useState<number | null>(null);
  const [kpis, setKpis] = useState<any>(null);
  const [globalStats, setGlobalStats] = useState<any>(null);
  const [forecast, setForecast] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [initError, setInitError] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);

  useEffect(() => {
    initData();
  }, []);

  const initData = async () => {
    setInitError(null);
    try {
      const [snapData, entityData] = await Promise.all([
        getSnapshots().catch(err => {
          console.error("Failed to fetch snapshots:", err);
          return [];
        }),
        api.get('/entities').then(res => res.data).catch(err => {
          console.error("Failed to fetch entities:", err);
          return [];
        })
      ]);
      
      setSnapshots(snapData);
      if (snapData.length > 0) {
        if (!selectedSnapshot) setSelectedSnapshot(snapData[0].id);
        if (snapData.length > 1 && !compareSnapshot) setCompareSnapshot(snapData[1].id);
      }

      setEntities(entityData);
      if (entityData.length > 0 && !selectedEntity) {
        setSelectedEntity(entityData[0].id);
      } else if (entityData.length === 0) {
        try {
          const newEntity = await api.post('/entities?name=Default%20Entity', {});
          setEntities([newEntity.data]);
          setSelectedEntity(newEntity.data.id);
        } catch (entityErr) {
          console.error("Failed to create default entity:", entityErr);
        }
      }
    } catch (globalErr) {
      console.error("Global init data error:", globalErr);
      setInitError("Unable to reach the backend. Please ensure the API is running at http://localhost:8000.");
    }
  };

  useEffect(() => {
    if (selectedSnapshot) {
      loadSnapshotData(selectedSnapshot);
    }
  }, [selectedSnapshot]);

  const loadSnapshotData = async (id: number) => {
    setLoading(true);
    
    // Load each piece of data independently so one failure doesn't block the rest
    getKPIs(id).then(data => setKpis(data)).catch(err => console.error("KPI error:", err));
    getForecast(id, 'week').then(data => setForecast(data)).catch(err => console.error("Forecast error:", err));
    api.get(`/snapshots/${id}/stats`).then(res => setGlobalStats(res.data)).catch(err => console.error("Stats error:", err));
    
    setLoading(false);
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.[0]) {
      setLoading(true);
      setUploadError(null);
      try {
        const res = await uploadExcel(e.target.files[0], selectedEntity || undefined);
        await initData();
        setSelectedSnapshot(res.snapshot_id);
      } catch (e) {
        console.error(e);
        setUploadError("Upload failed. Please verify the API is running and try again.");
      }
      setLoading(false);
    }
  };

  const handleDeleteSnapshot = async () => {
    if (!selectedSnapshot) return;
    if (!confirm("Are you sure you want to delete this snapshot and all its data?")) return;
    
    setLoading(true);
    try {
      await api.delete(`/snapshots/${selectedSnapshot}`);
      await initData();
      setSelectedSnapshot(null);
    } catch (e: any) {
      console.error("Delete failed:", e);
      const msg = e.response?.data?.detail || "Failed to delete snapshot.";
      alert(msg);
    }
    setLoading(false);
  };

  const handleResetAll = async () => {
    if (!confirm("WARNING: This will delete ALL snapshots and ALL uploaded data. Proceed?")) return;
    
    setLoading(true);
    try {
      await api.delete('/snapshots');
      setSnapshots([]);
      setSelectedSnapshot(null);
      setKpis(null);
      setForecast([]);
      alert("Database cleared successfully.");
    } catch (e: any) {
      console.error("Reset failed:", e);
      alert("Failed to reset database.");
    }
    setLoading(false);
  };

  const navItems = [
    { id: 'cfo', label: 'Overview', icon: LayoutDashboard },
    { id: 'forecast13', label: '13-Week View', icon: BarChart3 },
    { id: 'fpa', label: 'Analyst Desk', icon: Search },
    { id: 'bank', label: 'Banking', icon: Receipt },
    { id: 'ops', label: 'Operations', icon: Briefcase },
    { id: 'reporting', label: 'Reporting', icon: FileJson },
    { id: 'meeting', label: 'Meetings', icon: Calendar },
  ];

  return (
    <div className="flex h-screen bg-[#F9F9FB] text-[#1A1A1A] overflow-hidden font-sans">
      {/* Sidebar - Harvey Aesthetic */}
      <aside className="w-64 border-r border-[#E5E5E7] bg-white flex flex-col shrink-0">
        <div className="p-6 flex items-center gap-3">
          <div className="h-8 w-8 bg-[#1A1A1A] rounded-lg flex items-center justify-center">
            <span className="text-white font-black text-xs">G</span>
          </div>
          <span className="text-lg font-black tracking-tight text-[#1A1A1A]">Gitto</span>
        </div>

        <nav className="flex-1 px-3 space-y-1 overflow-y-auto pt-4">
          <div className="px-3 mb-2 text-[10px] font-bold text-slate-400 uppercase tracking-widest">Workspace</div>
          {navItems.map((item) => (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all group ${
                activeTab === item.id 
                ? 'bg-[#1A1A1A] text-white shadow-lg shadow-slate-200' 
                : 'text-slate-500 hover:bg-[#F4F4F5] hover:text-slate-900'
              }`}
            >
              <item.icon className={`h-4 w-4 ${activeTab === item.id ? 'text-white' : 'text-slate-400 group-hover:text-slate-600'}`} />
              <span className="text-sm font-bold tracking-tight">{item.label}</span>
              {activeTab === item.id && <ChevronRight className="ml-auto h-3 w-3 opacity-50" />}
            </button>
          ))}
        </nav>

        <div className="p-4 border-t border-[#E5E5E7] space-y-4">
          <div className="px-3 text-[10px] font-bold text-slate-400 uppercase tracking-widest">Configuration</div>
          <div className="space-y-3 px-3">
            <div className="space-y-1.5">
              <label className="text-[9px] font-bold text-slate-400 uppercase tracking-widest">Legal Entity</label>
              <select 
                className="w-full bg-[#F4F4F5] border-none rounded-lg px-2 py-1.5 text-[11px] font-bold text-slate-700 focus:ring-0"
                value={selectedEntity || ''}
                onChange={(e) => setSelectedEntity(Number(e.target.value))}
              >
                {entities.map(e => (
                  <option key={e.id} value={e.id}>{e.name}</option>
                ))}
              </select>
            </div>
            <div className="space-y-1.5">
              <label className="text-[9px] font-bold text-slate-400 uppercase tracking-widest">Active Snapshot</label>
              <div className="flex gap-2">
                <select 
                  className="flex-1 bg-[#F4F4F5] border-none rounded-lg px-2 py-1.5 text-[11px] font-bold text-slate-700 focus:ring-0"
                  value={selectedSnapshot || ''}
                  onChange={(e) => setSelectedSnapshot(Number(e.target.value))}
                >
                  {snapshots.map(s => (
                    <option key={s.id} value={s.id}>{s.name}</option>
                  ))}
                </select>
                <button onClick={handleDeleteSnapshot} className="p-1.5 text-slate-400 hover:text-red-500 transition-colors">
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
            </div>
          </div>
          
          <button 
            className="w-full mt-4 flex items-center justify-center gap-2 px-4 py-2.5 bg-[#F4F4F5] text-slate-600 rounded-xl hover:bg-slate-200 transition-all text-[10px] font-bold uppercase tracking-widest"
            onClick={handleResetAll}
          >
            <RefreshCcw className="h-3 w-3" /> Reset System
          </button>
        </div>
      </aside>

      {/* Main Workspace - Harvey Canvas */}
      <main className="flex-1 flex flex-col overflow-hidden relative">
        {/* Header Bar */}
        <header className="h-16 border-b border-[#E5E5E7] bg-white flex items-center justify-between px-8 z-10 shrink-0">
          <div className="flex items-center gap-4">
            <h2 className="text-sm font-black text-[#1A1A1A] tracking-tight">
              {navItems.find(n => n.id === activeTab)?.label}
            </h2>
            <div className="h-4 w-[1px] bg-[#E5E5E7]" />
            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">
              {snapshots.find(s => s.id === selectedSnapshot)?.name || 'Syncing Snapshot...'}
            </span>
          </div>
          
          <div className="flex items-center gap-3">
            {loading && (
              <div className="flex items-center gap-2 px-3 py-1.5 bg-blue-50 rounded-lg">
                <div className="h-2 w-2 bg-blue-600 rounded-full animate-pulse" />
                <span className="text-[10px] font-bold text-blue-600 uppercase tracking-widest">Processing Engine...</span>
              </div>
            )}
            {uploadError && (
              <div className="flex items-center gap-2 px-3 py-1.5 bg-red-50 rounded-lg">
                <AlertCircle className="h-3 w-3 text-red-600" />
                <span className="text-[10px] font-bold text-red-600 uppercase tracking-widest">{uploadError}</span>
              </div>
            )}
            <Button className="bg-[#1A1A1A] text-white hover:bg-slate-800 rounded-xl h-9 px-4 text-xs font-bold shadow-md shadow-slate-200 relative">
              <Plus className="mr-2 h-3.5 w-3.5" /> New Ingestion
              <input 
                type="file" 
                className="absolute inset-0 opacity-0 cursor-pointer" 
                onChange={handleFileUpload}
                accept=".xlsx,.xls"
                disabled={loading}
              />
            </Button>
          </div>
        </header>

        {/* Dynamic Canvas Area */}
        <div className="flex-1 overflow-y-auto custom-scrollbar p-8">
          <div className="max-w-6xl mx-auto space-y-8 animate-in fade-in duration-500">
            {activeTab === 'cfo' && (
              <div className="space-y-10">
                <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                  {[
                    { label: 'Total Portfolio Value', value: `€${kpis?.total_portfolio_value?.toLocaleString() || '0'}`, icon: DollarSign, color: 'text-emerald-500' },
                    { label: 'Outstanding Balance', value: `€${kpis?.open_receivables?.toLocaleString() || '0'}`, icon: AlertCircle, color: 'text-blue-500' },
                    { label: 'Total Invoices', value: snapshots.find(s => s.id === selectedSnapshot)?.total_rows?.toLocaleString() || '0', icon: Database, color: 'text-slate-400' },
                    { label: 'Data Health', value: '100%', icon: ShieldCheck, color: 'text-emerald-500' },
                  ].map((stat, i) => (
                    <div key={i} className="bg-white p-6 rounded-[32px] border border-[#E5E5E7] flex flex-col gap-1 transition-all hover:shadow-lg hover:border-slate-300 min-w-0 overflow-hidden">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-[9px] font-bold text-slate-400 uppercase tracking-widest truncate">{stat.label}</span>
                        <stat.icon className={`h-3.5 w-3.5 ${stat.color} opacity-80`} />
                      </div>
                      <div className="text-xl md:text-2xl font-black text-[#1A1A1A] tracking-tighter truncate" title={stat.value}>
                        {stat.value}
                      </div>
                    </div>
                  ))}
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                  <div className="bg-white rounded-[40px] border border-[#E5E5E7] p-10 space-y-8 shadow-sm">
                    <div className="flex items-center justify-between">
                      <div>
                        <h3 className="text-xl font-black tracking-tight text-[#1A1A1A]">Historical Trajectory</h3>
                        <p className="text-[11px] font-bold text-slate-400 uppercase tracking-[0.1em]">Cash Flow by Year</p>
                      </div>
                    </div>
                    <div className="h-[320px] w-full">
                      {globalStats?.cash_flow_by_year?.length > 0 ? (
                        <ResponsiveContainer width="100%" height="100%">
                          <LineChart data={globalStats.cash_flow_by_year}>
                            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#F1F5F9" />
                            <XAxis dataKey="year" tick={{ fill: '#94A3B8', fontSize: 10, fontWeight: 700 }} axisLine={false} tickLine={false} />
                            <YAxis tick={{ fill: '#94A3B8', fontSize: 10, fontWeight: 700 }} axisLine={false} tickLine={false} />
                            <Tooltip
                              contentStyle={{ borderRadius: 20, border: 'none', boxShadow: '0 20px 50px rgba(0,0,0,0.08)', padding: 16 }}
                              formatter={(value: any) => [`€${Number(value || 0).toLocaleString()}`, 'Cash']}
                            />
                            <Line type="monotone" dataKey="cash" stroke="#10B981" strokeWidth={4} dot={{ r: 5, fill: '#10B981', strokeWidth: 0 }} activeDot={{ r: 8 }} />
                          </LineChart>
                        </ResponsiveContainer>
                      ) : <div className="h-full flex items-center justify-center text-slate-300 font-bold text-xs">Waiting for data...</div>}
                    </div>
                  </div>

                  <div className="bg-white rounded-[40px] border border-[#E5E5E7] p-10 space-y-8 shadow-sm">
                    <div className="flex items-center justify-between">
                      <div>
                        <h3 className="text-xl font-black tracking-tight text-[#1A1A1A]">Receivables Aging</h3>
                        <p className="text-[11px] font-bold text-slate-400 uppercase tracking-[0.1em]">Portfolio Delinquency</p>
                      </div>
                    </div>
                    <div className="h-[320px] w-full">
                      {globalStats?.overdue_chart_data?.length > 0 ? (
                        <ResponsiveContainer width="100%" height="100%">
                          <BarChart data={globalStats.overdue_chart_data}>
                            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#F1F5F9" />
                            <XAxis dataKey="label" tick={{ fill: '#94A3B8', fontSize: 10, fontWeight: 700 }} axisLine={false} tickLine={false} />
                            <YAxis tick={{ fill: '#94A3B8', fontSize: 10, fontWeight: 700 }} axisLine={false} tickLine={false} />
                            <Tooltip
                              contentStyle={{ borderRadius: 20, border: 'none', boxShadow: '0 20px 50px rgba(0,0,0,0.08)', padding: 16 }}
                              formatter={(value: any) => [`€${Number(value || 0).toLocaleString()}`, 'Overdue']}
                            />
                            <Bar dataKey="amount" fill="#3B82F6" radius={[12, 12, 0, 0]} />
                          </BarChart>
                        </ResponsiveContainer>
                      ) : <div className="h-full flex items-center justify-center text-slate-300 font-bold text-xs">No overdue items</div>}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'forecast13' && selectedSnapshot && (
              <ThirteenWeekWorkspace snapshotId={selectedSnapshot} />
            )}

            {activeTab === 'fpa' && <FPAView snapshotId={selectedSnapshot || 0} />}
            {activeTab === 'bank' && selectedEntity && <BankLedgerView entityId={selectedEntity} />}
            {activeTab === 'ops' && selectedSnapshot && <OperationsDeskView snapshotId={selectedSnapshot} />}
            {activeTab === 'reporting' && selectedSnapshot && selectedEntity && <ReportingView snapshotId={selectedSnapshot} entityId={selectedEntity} />}
            {activeTab === 'meeting' && selectedSnapshot && <WeeklyMeetingView snapshotId={selectedSnapshot} compareId={compareSnapshot || undefined} />}
          </div>
        </div>

        {/* Floating AI Analyst - Harvey Signature */}
        <div className="absolute bottom-10 right-10 z-50">
          <button 
            onClick={() => setActiveTab('reporting')} 
            className="flex items-center gap-4 bg-[#1A1A1A] text-white pl-8 pr-6 py-5 rounded-full shadow-[0_20px_50px_rgba(0,0,0,0.2)] hover:scale-105 active:scale-95 transition-all group"
          >
            <Sparkles className="h-5 w-5 text-indigo-400 fill-current" />
            <span className="text-sm font-black tracking-tight">Ask Gitto Analyst</span>
            <div className="ml-2 h-6 w-6 bg-white/10 rounded-full flex items-center justify-center text-[10px] font-black group-hover:bg-white/20 transition-all">?</div>
          </button>
        </div>
      </main>
    </div>
  );
}

const Sparkles = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M12 3L14.5 9L21 11.5L14.5 14L12 21L9.5 14L3 11.5L9.5 9L12 3Z" fill="currentColor" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
  </svg>
);
