'use client';

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "./ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "./ui/table";
import { Button } from "./ui/button";
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  LineChart, Line
} from 'recharts';
import { Download, FileText, Printer, Share2, Mail, ExternalLink, ShieldCheck } from "lucide-react";

interface CashPackProps {
  data: any;
  onClose: () => void;
}

export default function WeeklyCashPack({ data, onClose }: CashPackProps) {
  const { kpis, forecast, movers, priorities, entityName, snapshotDate } = data;

  return (
    <div className="fixed inset-0 z-[100] bg-slate-900/40 backdrop-blur-xl flex items-center justify-center p-8 overflow-y-auto">
      <div className="max-w-5xl w-full bg-[#F8F9FA] rounded-[48px] shadow-[0_40px_100px_rgba(0,0,0,0.3)] overflow-hidden flex flex-col min-h-[90vh]">
        {/* Artifact Header / Toolbar */}
        <div className="h-20 bg-white border-b border-slate-100 px-10 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-4">
             <div className="h-10 w-10 bg-slate-900 rounded-2xl flex items-center justify-center">
                <FileText className="h-5 w-5 text-white" />
             </div>
             <div>
                <h2 className="text-sm font-black text-slate-900 tracking-tight uppercase">Weekly_Cash_Pack_v1.pdf</h2>
                <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">{entityName} // {new Date().toLocaleDateString()}</p>
             </div>
          </div>
          <div className="flex items-center gap-3">
             <Button variant="ghost" className="rounded-xl h-10 px-4 text-[10px] font-black uppercase tracking-widest text-slate-400 hover:text-slate-900">
                <Share2 className="h-3.5 w-3.5 mr-2" /> Share
             </Button>
             <Button variant="ghost" className="rounded-xl h-10 px-4 text-[10px] font-black uppercase tracking-widest text-slate-400 hover:text-slate-900">
                <Printer className="h-3.5 w-3.5 mr-2" /> Print
             </Button>
             <Button className="bg-slate-900 text-white hover:bg-blue-600 rounded-xl h-10 px-6 text-[10px] font-black uppercase tracking-widest shadow-lg shadow-slate-200">
                <Download className="h-3.5 w-3.5 mr-2" /> Download PDF
             </Button>
             <div className="h-8 w-[1px] bg-slate-100 mx-2" />
             <Button variant="ghost" onClick={onClose} className="rounded-full h-10 w-10 p-0 text-slate-400 hover:bg-slate-50">
                <X className="h-5 w-5" />
             </Button>
          </div>
        </div>

        {/* The "Slide" Content */}
        <div className="flex-1 p-16 overflow-y-auto custom-scrollbar">
           <div className="max-w-4xl mx-auto space-y-20 bg-white p-16 rounded-[40px] shadow-sm border border-slate-50">
              
              {/* Cover/Title Section */}
              <div className="space-y-6">
                 <div className="inline-flex items-center px-4 py-1.5 rounded-full bg-blue-50 text-[10px] font-black uppercase tracking-widest text-blue-600">
                    Confidential // Board Level Artifact
                 </div>
                 <h1 className="text-6xl font-black italic tracking-tighter text-slate-900 leading-[0.9]">
                    Liquidity Status <br /> & Weekly Outlook.
                 </h1>
                 <div className="flex items-center gap-10 pt-6">
                    <div>
                       <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1">Entity</p>
                       <p className="text-sm font-black text-slate-900 italic underline decoration-blue-500 decoration-2 underline-offset-4">{entityName}</p>
                    </div>
                    <div>
                       <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1">Snapshot Date</p>
                       <p className="text-sm font-black text-slate-900 italic">{snapshotDate}</p>
                    </div>
                    <div className="ml-auto">
                       <div className="flex items-center gap-2 px-4 py-2 bg-emerald-50 rounded-2xl border border-emerald-100">
                          <ShieldCheck className="h-4 w-4 text-emerald-600" />
                          <span className="text-[10px] font-black text-emerald-700 uppercase tracking-widest">Audit Signed: CFO</span>
                       </div>
                    </div>
                 </div>
              </div>

              {/* KPI Grid */}
              <div className="grid grid-cols-4 gap-4">
                 {[
                    { label: 'Current Bank Cash', val: `€${kpis?.opening_bank_balance?.toLocaleString()}`, desc: 'Verified Ledger' },
                    { label: '13W Min Runway', val: `€${kpis?.min_projected?.toLocaleString()}`, desc: 'W8 Risk Window' },
                    { label: 'Unmatched Cash', val: '€14.2k', desc: '12 Exception Items' },
                    { label: 'Forecast Accuracy', val: '92.4%', desc: 'MAE: 1.4 Days' },
                 ].map((k, i) => (
                    <div key={i} className="p-6 rounded-3xl bg-slate-50 border border-slate-100 space-y-1">
                       <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest">{k.label}</p>
                       <p className="text-xl font-black text-slate-900 italic">{k.val}</p>
                       <p className="text-[8px] font-bold text-slate-400 uppercase tracking-tight">{k.desc}</p>
                    </div>
                 ))}
              </div>

              {/* Forecast Visualization */}
              <div className="space-y-6">
                 <h4 className="text-[11px] font-black uppercase tracking-[0.2em] text-slate-900 border-b-2 border-slate-900 pb-2 flex items-center justify-between">
                    13-Week Liquidity Trajectory
                    <span className="text-[10px] font-bold text-slate-400 normal-case">Values in €000s</span>
                 </h4>
                 <div className="h-[280px] w-full">
                    <ResponsiveContainer width="100%" height="100%">
                       <AreaChart data={forecast}>
                          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                          <XAxis dataKey="label" tick={{ fill: '#94A3B8', fontSize: 9, fontWeight: 700 }} axisLine={false} tickLine={false} />
                          <YAxis tick={{ fill: '#94A3B8', fontSize: 9, fontWeight: 700 }} axisLine={false} tickLine={false} />
                          <Area type="monotone" dataKey="base" stroke="#1A1A1A" fill="#1A1A1A" fillOpacity={0.05} strokeWidth={3} />
                          <Area type="monotone" dataKey="upside" stroke="#3B82F6" fill="transparent" strokeDasharray="5 5" strokeWidth={1.5} />
                       </AreaChart>
                    </ResponsiveContainer>
                 </div>
              </div>

              {/* Two Column Section: Movers & Risks */}
              <div className="grid grid-cols-2 gap-16">
                 <div className="space-y-6">
                    <h4 className="text-[11px] font-black uppercase tracking-[0.2em] text-slate-900 border-b-2 border-slate-900 pb-2">Top Drivers (Weekly Variance)</h4>
                    <div className="space-y-4">
                       {movers.slice(0, 4).map((m: any, i: number) => (
                          <div key={i} className="flex items-center justify-between group">
                             <div>
                                <p className="text-xs font-black text-slate-900">{m.customer}</p>
                                <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">{m.reason}</p>
                             </div>
                             <div className={`text-xs font-black italic ${m.shift_days > 0 ? 'text-red-500' : 'text-emerald-500'}`}>
                                {m.shift_days > 0 ? '+' : ''}{m.shift_days} Days
                             </div>
                          </div>
                       ))}
                    </div>
                 </div>
                 <div className="space-y-6">
                    <h4 className="text-[11px] font-black uppercase tracking-[0.2em] text-slate-900 border-b-2 border-slate-900 pb-2">Critical Actions (W1-W4)</h4>
                    <div className="space-y-4">
                       {[
                          { action: 'Sarah L.', task: 'Chase J.P. Morgan Inv #8821', impact: '€242k' },
                          { action: 'Mike R.', task: 'Hold Vendor #441 (Price Dispute)', impact: '€84k' },
                          { action: 'CFO', task: 'Approve Revolver Draw (Scenario B)', impact: '€500k' },
                       ].map((a, i) => (
                          <div key={i} className="flex items-center justify-between">
                             <div>
                                <p className="text-xs font-black text-slate-900">{a.task}</p>
                                <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Owner: {a.action}</p>
                             </div>
                             <div className="text-xs font-black text-slate-900 italic">{a.impact}</div>
                          </div>
                       ))}
                    </div>
                 </div>
              </div>

              {/* Footer Attribution */}
              <div className="pt-20 border-t border-slate-50 flex items-center justify-between">
                 <div className="flex items-center gap-3">
                    <div className="h-6 w-6 bg-blue-600 rounded-lg flex items-center justify-center">
                       <span className="text-white font-black text-[8px] italic">G</span>
                    </div>
                    <span className="text-[10px] font-black tracking-widest uppercase text-slate-400">Generated by Gitto Intelligence Engine</span>
                 </div>
                 <div className="text-[9px] font-bold text-slate-300 uppercase tracking-widest">
                    Page 1 of 1 // Internal Distribution Only
                 </div>
              </div>

           </div>
        </div>
      </div>
    </div>
  );
}

const X = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
    <line x1="18" y1="6" x2="6" y2="18"></line>
    <line x1="6" y1="6" x2="18" y2="18"></line>
  </svg>
);

