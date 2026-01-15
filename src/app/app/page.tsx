'use client';

import { useState, useEffect } from 'react';
import { 
  Upload, TrendingUp, AlertCircle, Calendar, RefreshCcw, Trash2, DollarSign, 
  LayoutDashboard, BarChart3, Receipt, Briefcase, FileJson, MessageCircle, Settings,
  ChevronRight, Search, Plus, Database, ShieldCheck, FileText
} from "lucide-react";
import { getSnapshots, getForecast, getKPIs, uploadExcel, api } from '../../lib/api';
import { 
  ResponsiveContainer,
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  LineChart, Line, BarChart, Bar,
} from 'recharts';

import FPAView from '../../components/FPAView';
import WeeklyMeetingView from '../../components/WeeklyMeetingView';
import BankLedgerView from '../../components/BankLedgerView';
import OperationsDeskView from '../../components/OperationsDeskView';
import ReportingView from '../../components/ReportingView';
import ThirteenWeekWorkspace from '../../components/ThirteenWeekWorkspace';
import AllInvoicesView from '../../components/AllInvoicesView';
import MappingUI from '../../components/MappingUI';
import DataHealthReport from '../../components/DataHealthReport';
import ConnectorSettings from '../../components/ConnectorSettings';
import VarianceAnalysisView from '../../components/VarianceAnalysisView';
import RedWeeksView from '../../components/RedWeeksView';
import TruthLabelsView from '../../components/TruthLabelsView';
import UnmatchedQueueView from '../../components/UnmatchedQueueView';
import MatchingPolicyView from '../../components/MatchingPolicyView';
import AuditTrailView from '../../components/AuditTrailView';
import LeverPerformanceView from '../../components/LeverPerformanceView';
import { Button } from "../../components/ui/button";

const Sparkles = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M12 3L14.5 9L21 11.5L14.5 14L12 21L9.5 14L3 11.5L9.5 9L12 3Z" fill="currentColor" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
  </svg>
);

export default function Dashboard() {
  const [activeTab, setActiveTab] = useState('cfo');
  const [snapshots, setSnapshots] = useState<Array<{ id: number; name: string; [key: string]: unknown }>>([]);
  const [entities, setEntities] = useState<Array<{ id: number; name: string; [key: string]: unknown }>>([]);
  const [selectedEntity, setSelectedEntity] = useState<number | null>(null);
  const [selectedSnapshot, setSelectedSnapshot] = useState<number | null>(null);
  const [compareSnapshot, setCompareSnapshot] = useState<number | null>(null);
  const [kpis, setKpis] = useState<Record<string, unknown> | null>(null);
  const [globalStats, setGlobalStats] = useState<{
    cash_flow_by_year?: Array<{ year: number; cash: number }>;
    overdue_chart_data?: Array<{ label: string; amount: number }>;
    [key: string]: unknown;
  } | null>(null);
  const [forecast, setForecast] = useState<Array<Record<string, unknown>>>([]);
  const [loading, setLoading] = useState(false);
  const [initError, setInitError] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);

  // Ingestion Pipeline State
  const [ingestionStage, setIngestionStage] = useState<'ready' | 'mapping' | 'health_report'>('ready');
  const [currentFile, setCurrentFile] = useState<File | null>(null);
  const [fileColumns, setFileColumns] = useState<string[]>([]);
  const [activeMapping, setActiveMapping] = useState<Record<string, string>>({});
  const [healthData, setHealthData] = useState<Record<string, unknown> | null>(null);

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
      }
    } catch (globalErr) {
      console.error("Global init data error:", globalErr);
      setInitError("Unable to reach the backend. Please ensure the API server is running.");
    }
  };

  const loadSnapshotData = async (id: number) => {
    setLoading(true);
    
    // Load each piece of data independently so one failure doesn't block the rest
    getKPIs(id).then(data => setKpis(data)).catch(err => console.error("KPI error:", err));
    getForecast(id, 'week').then(data => setForecast(data)).catch(err => console.error("Forecast error:", err));
    api.get(`/snapshots/${id}/stats`).then(res => setGlobalStats(res.data)).catch(err => console.error("Stats error:", err));
    
    setLoading(false);
  };

  // Initialize data on mount
  useEffect(() => {
    initData();
  }, []);

  // Load snapshot data when selection changes
  useEffect(() => {
    if (selectedSnapshot) {
      loadSnapshotData(selectedSnapshot);
    }
  }, [selectedSnapshot]);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.[0]) {
      const file = e.target.files[0];
      setCurrentFile(file);
      setLoading(true);
      setUploadError(null);
      try {
        const formData = new FormData();
        formData.append('file', file);
        const res = await api.post('/upload/inspect', formData);
        setFileColumns(res.data.columns);
        setIngestionStage('mapping');
      } catch (err) {
        console.error(err);
        setUploadError("Failed to inspect file. Ensure it is a valid Excel document.");
      }
      setLoading(false);
    }
  };

  const handleMappingConfirm = async (mapping: Record<string, string>) => {
    setActiveMapping(mapping);
    setLoading(true);
    try {
      const formData = new FormData();
      formData.append('file', currentFile!);
      formData.append('mapping_config', JSON.stringify(mapping));
      const res = await api.post('/upload/dry-run', formData);
      setHealthData(res.data.health);
      setIngestionStage('health_report');
    } catch (err) {
      console.error(err);
      alert("Mapping check failed.");
    }
    setLoading(false);
  };

  const handleHealthApprove = async () => {
    setLoading(true);
    try {
      const formData = new FormData();
      formData.append('file', currentFile!);
      formData.append('mapping_config', JSON.stringify(activeMapping));
      if (selectedEntity) formData.append('entity_id', selectedEntity.toString());
      
      const res = await api.post('/upload', formData, {
        timeout: 120000, // 2 minutes for large files
      });
      await initData();
      setSelectedSnapshot(res.data.snapshot_id);
      setIngestionStage('ready');
      setCurrentFile(null);
    } catch (err: any) {
      console.error("Upload error:", err);
      const errorMsg = err.response?.data?.detail || err.message || "Unknown error";
      alert(`Upload failed: ${errorMsg}`);
    }
    setLoading(false);
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
    { id: 'all_invoices', label: 'All Invoices', icon: FileJson },
    { id: 'fpa', label: 'Analyst Desk', icon: Search },
    { id: 'bank', label: 'Banking', icon: Receipt },
    { id: 'ops', label: 'Operations', icon: Briefcase },
    { id: 'variance', label: 'Variance Analysis', icon: TrendingUp },
    { id: 'red_weeks', label: 'Red Weeks', icon: AlertCircle },
    { id: 'truth_labels', label: 'Truth Labels', icon: ShieldCheck },
    { id: 'unmatched', label: 'Unmatched Queue', icon: AlertCircle },
    { id: 'matching_policy', label: 'Matching Policy', icon: Settings },
    { id: 'audit', label: 'Audit Trail', icon: FileText },
    { id: 'levers', label: 'Lever Performance', icon: TrendingUp },
    { id: 'reporting', label: 'Reporting', icon: FileJson },
    { id: 'meeting', label: 'Meetings', icon: Calendar },
    { id: 'integrations', label: 'Integrations', icon: Settings },
  ];

  return (
    <div className="flex h-screen bg-[#0A0A0F] text-white overflow-hidden">
      {/* Sidebar - Dark theme matching landing page */}
      <aside className="w-64 border-r border-white/10 bg-[#0D0D12] flex flex-col shrink-0">
        <div className="p-6 flex items-center gap-3">
          <div className="h-9 w-9 bg-white rounded-xl flex items-center justify-center">
            <span className="text-[#0A0A0F] font-serif font-semibold text-lg">G</span>
          </div>
          <span className="text-xl font-serif font-semibold tracking-tight text-white">Gitto</span>
        </div>

        <nav className="flex-1 px-3 space-y-1 overflow-y-auto pt-4">
          <div className="px-3 mb-2 text-[10px] font-bold text-white/30 uppercase tracking-widest">Workspace</div>
          {navItems.map((item) => (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all group ${
                activeTab === item.id 
                ? 'bg-white text-[#0A0A0F]' 
                : 'text-white/50 hover:bg-white/5 hover:text-white'
              }`}
            >
              <item.icon className={`h-4 w-4 ${activeTab === item.id ? 'text-[#0A0A0F]' : 'text-white/40 group-hover:text-white/60'}`} />
              <span className="text-sm font-bold tracking-tight">{item.label}</span>
              {activeTab === item.id && <ChevronRight className="ml-auto h-3 w-3 opacity-50" />}
            </button>
          ))}
        </nav>

        <div className="p-4 border-t border-white/10 space-y-4">
          <div className="px-3 text-[10px] font-bold text-white/30 uppercase tracking-widest">Configuration</div>
          <div className="space-y-3 px-3">
            <div className="space-y-1.5">
              <label className="text-[9px] font-bold text-white/40 uppercase tracking-widest">Legal Entity</label>
              <select 
                className="w-full bg-white/5 border border-white/10 rounded-lg px-2 py-1.5 text-[11px] font-bold text-white focus:ring-0 focus:border-white/20"
                value={selectedEntity || ''}
                onChange={(e) => setSelectedEntity(Number(e.target.value))}
              >
                {entities.map(e => (
                  <option key={e.id} value={e.id} className="bg-[#0D0D12] text-white">{e.name}</option>
                ))}
              </select>
            </div>
            <div className="space-y-1.5">
              <label className="text-[9px] font-bold text-white/40 uppercase tracking-widest">Active Snapshot</label>
              <div className="flex gap-2">
                <select 
                  className="flex-1 bg-white/5 border border-white/10 rounded-lg px-2 py-1.5 text-[11px] font-bold text-white focus:ring-0 focus:border-white/20"
                  value={selectedSnapshot || ''}
                  onChange={(e) => setSelectedSnapshot(Number(e.target.value))}
                >
                  {snapshots.map(s => (
                    <option key={s.id} value={s.id} className="bg-[#0D0D12] text-white">{s.name}</option>
                  ))}
                </select>
                <button onClick={handleDeleteSnapshot} className="p-1.5 text-white/40 hover:text-red-400 transition-colors">
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
            </div>
          </div>
          
          <button 
            className="w-full mt-4 flex items-center justify-center gap-2 px-4 py-2.5 bg-white/5 border border-white/10 text-white/60 rounded-xl hover:bg-white/10 hover:text-white transition-all text-[10px] font-bold uppercase tracking-widest"
            onClick={handleResetAll}
          >
            <RefreshCcw className="h-3 w-3" /> Reset System
          </button>
        </div>
      </aside>

      {/* Main Workspace */}
      <main className="flex-1 flex flex-col overflow-hidden relative bg-[#0A0A0F]">
        {/* Header Bar */}
        <header className="h-16 border-b border-white/10 bg-[#0D0D12] flex items-center justify-between px-8 z-10 shrink-0">
          <div className="flex items-center gap-4">
            <h2 className="text-sm font-black text-white tracking-tight">
              {navItems.find(n => n.id === activeTab)?.label}
            </h2>
            <div className="h-4 w-[1px] bg-white/10" />
            <span className="text-[10px] font-bold text-white/40 uppercase tracking-widest">
              {snapshots.find(s => s.id === selectedSnapshot)?.name || 'Syncing Snapshot...'}
            </span>
          </div>
          
          <div className="flex items-center gap-3">
            {loading && (
              <div className="flex items-center gap-2 px-3 py-1.5 bg-emerald-500/10 border border-emerald-500/20 rounded-lg">
                <div className="h-2 w-2 bg-emerald-400 rounded-full animate-pulse" />
                <span className="text-[10px] font-bold text-emerald-400 uppercase tracking-widest">Processing Engine...</span>
              </div>
            )}
            {uploadError && (
              <div className="flex items-center gap-2 px-3 py-1.5 bg-red-500/10 border border-red-500/20 rounded-lg">
                <AlertCircle className="h-3 w-3 text-red-400" />
                <span className="text-[10px] font-bold text-red-400 uppercase tracking-widest">{uploadError}</span>
              </div>
            )}
            <Button className="button-glow bg-white text-[#0A0A0F] hover:bg-white/90 rounded-xl h-9 px-4 text-xs font-bold relative">
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
            {ingestionStage === 'mapping' && (
              <MappingUI 
                columns={fileColumns} 
                onConfirm={handleMappingConfirm} 
                onCancel={() => setIngestionStage('ready')}
                sourceType="Manual_Upload"
              />
            )}

            {ingestionStage === 'health_report' && (
              <DataHealthReport 
                health={healthData} 
                onApprove={handleHealthApprove} 
                onCancel={() => setIngestionStage('mapping')} 
              />
            )}

            {ingestionStage === 'ready' && activeTab === 'cfo' && (
              <div className="space-y-10">
                <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                  {[
                    { label: 'Total Portfolio Value', value: `€${kpis?.total_portfolio_value?.toLocaleString() || '0'}`, icon: DollarSign, color: 'text-emerald-400' },
                    { label: 'Outstanding Balance', value: `€${kpis?.open_receivables?.toLocaleString() || '0'}`, icon: AlertCircle, color: 'text-blue-400' },
                    { label: 'Total Invoices', value: snapshots.find(s => s.id === selectedSnapshot)?.total_rows?.toLocaleString() || '0', icon: Database, color: 'text-white/40' },
                    { label: 'Data Health', value: '100%', icon: ShieldCheck, color: 'text-emerald-400' },
                  ].map((stat, i) => (
                    <div key={i} className="bg-white/5 p-6 rounded-2xl border border-white/10 flex flex-col gap-1 transition-all hover:bg-white/10 hover:border-white/20 min-w-0 overflow-hidden">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-[9px] font-bold text-white/40 uppercase tracking-widest truncate">{stat.label}</span>
                        <stat.icon className={`h-3.5 w-3.5 ${stat.color} opacity-80`} />
                      </div>
                      <div className="text-xl md:text-2xl font-black text-white tracking-tighter truncate" title={stat.value}>
                        {stat.value}
                      </div>
                    </div>
                  ))}
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                  <div className="bg-white/5 rounded-2xl border border-white/10 p-10 space-y-8">
                    <div className="flex items-center justify-between">
                      <div>
                        <h3 className="text-xl font-black tracking-tight text-white">Historical Trajectory</h3>
                        <p className="text-[11px] font-bold text-white/40 uppercase tracking-[0.1em]">Cash Flow by Year</p>
                      </div>
                    </div>
                    <div className="h-[320px] w-full">
                      {globalStats?.cash_flow_by_year && globalStats.cash_flow_by_year.length > 0 ? (
                        <ResponsiveContainer width="100%" height="100%">
                          <LineChart data={globalStats.cash_flow_by_year}>
                            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(255,255,255,0.05)" />
                            <XAxis dataKey="year" tick={{ fill: 'rgba(255,255,255,0.4)', fontSize: 10, fontWeight: 700 }} axisLine={false} tickLine={false} />
                            <YAxis tick={{ fill: 'rgba(255,255,255,0.4)', fontSize: 10, fontWeight: 700 }} axisLine={false} tickLine={false} />
                            <Tooltip
                              contentStyle={{ borderRadius: 12, border: '1px solid rgba(255,255,255,0.1)', backgroundColor: '#1a1a22', padding: 16, color: 'white' }}
                              formatter={(value: any) => [`€${Number(value || 0).toLocaleString()}`, 'Cash']}
                            />
                            <Line type="monotone" dataKey="cash" stroke="#10B981" strokeWidth={3} dot={{ r: 4, fill: '#10B981', strokeWidth: 0 }} activeDot={{ r: 6 }} />
                          </LineChart>
                        </ResponsiveContainer>
                      ) : <div className="h-full flex items-center justify-center text-white/30 font-bold text-xs">Waiting for data...</div>}
                    </div>
                  </div>

                  <div className="bg-white/5 rounded-2xl border border-white/10 p-10 space-y-8">
                    <div className="flex items-center justify-between">
                      <div>
                        <h3 className="text-xl font-black tracking-tight text-white">Receivables Aging</h3>
                        <p className="text-[11px] font-bold text-white/40 uppercase tracking-[0.1em]">Portfolio Delinquency</p>
                      </div>
                    </div>
                    <div className="h-[320px] w-full">
                      {globalStats?.overdue_chart_data && globalStats.overdue_chart_data.length > 0 ? (
                        <ResponsiveContainer width="100%" height="100%">
                          <BarChart data={globalStats.overdue_chart_data}>
                            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(255,255,255,0.05)" />
                            <XAxis dataKey="label" tick={{ fill: 'rgba(255,255,255,0.4)', fontSize: 10, fontWeight: 700 }} axisLine={false} tickLine={false} />
                            <YAxis tick={{ fill: 'rgba(255,255,255,0.4)', fontSize: 10, fontWeight: 700 }} axisLine={false} tickLine={false} />
                            <Tooltip
                              contentStyle={{ borderRadius: 12, border: '1px solid rgba(255,255,255,0.1)', backgroundColor: '#1a1a22', padding: 16, color: 'white' }}
                              formatter={(value: any) => [`€${Number(value || 0).toLocaleString()}`, 'Overdue']}
                            />
                            <Bar dataKey="amount" fill="#3B82F6" radius={[8, 8, 0, 0]} />
                          </BarChart>
                        </ResponsiveContainer>
                      ) : <div className="h-full flex items-center justify-center text-white/30 font-bold text-xs">No overdue items</div>}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {ingestionStage === 'ready' && activeTab === 'forecast13' && selectedSnapshot && (
              <ThirteenWeekWorkspace snapshotId={selectedSnapshot} />
            )}

            {ingestionStage === 'ready' && activeTab === 'all_invoices' && selectedSnapshot && (
              <AllInvoicesView snapshotId={selectedSnapshot} />
            )}

            {ingestionStage === 'ready' && activeTab === 'fpa' && <FPAView snapshotId={selectedSnapshot || 0} />}
            {ingestionStage === 'ready' && activeTab === 'bank' && selectedEntity && <BankLedgerView entityId={selectedEntity} />}
            {ingestionStage === 'ready' && activeTab === 'ops' && selectedSnapshot && <OperationsDeskView snapshotId={selectedSnapshot} />}
            {ingestionStage === 'ready' && activeTab === 'variance' && selectedSnapshot && <VarianceAnalysisView snapshotId={selectedSnapshot} compareId={compareSnapshot || undefined} />}
            {ingestionStage === 'ready' && activeTab === 'red_weeks' && selectedSnapshot && <RedWeeksView snapshotId={selectedSnapshot} />}
            {ingestionStage === 'ready' && activeTab === 'truth_labels' && selectedSnapshot && <TruthLabelsView snapshotId={selectedSnapshot} />}
            {ingestionStage === 'ready' && activeTab === 'unmatched' && selectedEntity && <UnmatchedQueueView entityId={selectedEntity} />}
            {ingestionStage === 'ready' && activeTab === 'matching_policy' && selectedEntity && <MatchingPolicyView entityId={selectedEntity} />}
            {ingestionStage === 'ready' && activeTab === 'audit' && <AuditTrailView />}
            {ingestionStage === 'ready' && activeTab === 'levers' && selectedSnapshot && <LeverPerformanceView snapshotId={selectedSnapshot} />}
            {ingestionStage === 'ready' && activeTab === 'reporting' && selectedSnapshot && selectedEntity && <ReportingView snapshotId={selectedSnapshot} entityId={selectedEntity} />}
            {ingestionStage === 'ready' && activeTab === 'meeting' && selectedSnapshot && <WeeklyMeetingView snapshotId={selectedSnapshot} compareId={compareSnapshot || undefined} />}
            {ingestionStage === 'ready' && activeTab === 'integrations' && <ConnectorSettings />}
          </div>
        </div>

        {/* Floating AI Analyst */}
        <div className="absolute bottom-10 right-10 z-50">
          <button 
            onClick={() => setActiveTab('reporting')} 
            className="flex items-center gap-4 bg-white text-[#0A0A0F] pl-8 pr-6 py-5 rounded-full shadow-[0_20px_50px_rgba(0,0,0,0.3)] hover:scale-105 active:scale-95 transition-all group"
          >
            <Sparkles className="h-5 w-5 text-emerald-500 fill-current" />
            <span className="text-sm font-black tracking-tight">Ask Gitto Analyst</span>
            <div className="ml-2 h-6 w-6 bg-[#0A0A0F]/10 rounded-full flex items-center justify-center text-[10px] font-black group-hover:bg-[#0A0A0F]/20 transition-all">?</div>
          </button>
        </div>
      </main>
    </div>
  );
}
