'use client';

import { useState } from 'react';
import Link from "next/link";
import { 
  ArrowRight, CheckCircle2, Shield, BarChart3, TrendingUp, AlertCircle, 
  Landmark, Users, Search, Bell, Calendar, ChevronRight, MessageSquare,
  Lock, Zap, Database, Globe, Briefcase, Plus, Sparkles, Filter, 
  FileText, ArrowDownRight, ArrowUpRight, Play, Layout, MousePointer2,
  Cloud as CloudIcon, Activity, Layers, Terminal, ShieldCheck, Cpu, Code2, MoveRight
} from "lucide-react";
import { Button } from "../components/ui/button";
import { Card, CardContent } from "../components/ui/card";

export default function Landing() {
  const [activeWorkflow, setActiveWorkflow] = useState(0);

  const scrollTo = (id: string) => {
    const el = document.getElementById(id);
    if (el) el.scrollIntoView({ behavior: 'smooth' });
  };

  return (
    <div className="min-h-screen bg-[#0A0A0B] text-white font-sans selection:bg-blue-500/30 antialiased overflow-x-hidden relative">
      {/* Dynamic Grain Overlay */}
      <div className="fixed inset-0 z-50 pointer-events-none opacity-[0.03]" style={{ backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E")` }} />
      
      {/* Moving Ambient Glows */}
      <div className="fixed inset-0 z-0 pointer-events-none overflow-hidden">
        <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-blue-600/10 blur-[120px] rounded-full animate-pulse" />
        <div className="absolute bottom-[10%] right-[-5%] w-[30%] h-[30%] bg-emerald-600/5 blur-[100px] rounded-full" />
      </div>

      {/* Ultra-Slim Navigation */}
      <nav className="fixed top-0 left-0 right-0 z-[60] bg-[#0A0A0B]/80 backdrop-blur-md border-b border-white/5 px-8 py-5">
        <div className="max-w-[1400px] mx-auto flex items-center justify-between">
          <div className="flex items-center gap-12">
            <Link href="/" className="flex items-center gap-2 group">
              <div className="h-6 w-6 rounded-lg bg-blue-600 flex items-center justify-center text-white font-black text-[12px] italic">G</div>
              <span className="font-bold text-lg tracking-[-0.04em] text-white uppercase italic">Gitto</span>
            </Link>
            <div className="hidden lg:flex items-center gap-8 text-[11px] font-black uppercase tracking-[0.2em] text-slate-500">
              <button onClick={() => scrollTo('problem')} className="hover:text-white transition-colors">The Problem</button>
              <button onClick={() => scrollTo('ledger')} className="hover:text-white transition-colors">The Ledger</button>
              <button onClick={() => scrollTo('enterprise')} className="hover:text-white transition-colors">Enterprise</button>
            </div>
          </div>
          <div className="flex items-center gap-6">
            <Link href="/app" className="text-[11px] font-black uppercase tracking-[0.2em] text-slate-400 hover:text-white transition-colors">Access Terminal</Link>
            <Link href="/app">
              <div className="bg-white text-black px-6 py-2.5 rounded-full text-[11px] font-black uppercase tracking-[0.1em] hover:bg-slate-200 transition-all cursor-pointer shadow-[0_0_20px_rgba(255,255,255,0.1)]">
                Reserve Demo
              </div>
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero: High-Contrast Technical Authority */}
      <section className="relative pt-48 pb-24 px-8 z-10">
        <div className="max-w-[1400px] mx-auto">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-20 items-center">
            <div className="lg:col-span-8 space-y-10">
              <div className="inline-flex items-center gap-3 px-3 py-1 rounded-sm bg-blue-500/10 border border-blue-500/20">
                <span className="h-1.5 w-1.5 rounded-full bg-blue-500 animate-pulse" />
                <span className="text-[10px] font-black uppercase tracking-[0.3em] text-blue-400">Deterministic Treasury Engine v4.2 // Global_Ingest_Active</span>
              </div>
              <h1 className="text-[80px] md:text-[130px] font-black tracking-[-0.08em] leading-[0.8] text-white uppercase italic">
                CASH TRUTH <br />
                <span className="text-white/10 not-italic">IS THE ONLY</span> <br />
                <span className="text-blue-600">REALITY.</span>
              </h1>
              <div className="flex flex-col md:flex-row gap-12 items-start">
                <p className="text-2xl text-slate-400 font-medium leading-tight max-w-xl border-l border-blue-600/30 pl-8 italic">
                  Spreadsheets model the "theoretical." Gitto anchors your liquidity in actual bank receipts, intercompany washes, and deterministic behavioral bias.
                </p>
                <div className="flex flex-col gap-4 bg-white/[0.02] border border-white/5 p-6 rounded-2xl backdrop-blur-xl shrink-0">
                   <div className="flex items-center gap-3">
                      <Activity className="h-4 w-4 text-emerald-500" />
                      <span className="text-[10px] font-black uppercase tracking-widest text-slate-500">Live_Latency</span>
                   </div>
                   <div className="flex items-baseline gap-2">
                      <span className="text-2xl font-black italic">14.2</span>
                      <span className="text-[10px] font-black text-emerald-500 uppercase">ms</span>
                   </div>
                   <div className="h-1 w-32 bg-white/5 rounded-full overflow-hidden">
                      <div className="h-full bg-emerald-500 animate-shimmer" style={{ width: '70%' }} />
                   </div>
                </div>
              </div>
              <div className="flex items-center gap-10 pt-6">
                <Link href="/app">
                  <Button className="bg-white text-black hover:bg-slate-200 rounded-none px-12 h-20 text-sm font-black uppercase tracking-widest shadow-[0_20px_80px_rgba(255,255,255,0.1)] transition-all hover:scale-105">
                    Enter Terminal
                  </Button>
                </Link>
                <div className="hidden md:flex gap-12">
                   <div className="space-y-1">
                      <div className="text-[10px] font-black text-slate-500 uppercase tracking-widest">MAE Accuracy</div>
                      <div className="text-2xl font-black italic text-blue-500">0.8d</div>
                   </div>
                   <div className="space-y-1">
                      <div className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Bank Ingest</div>
                      <div className="text-2xl font-black italic text-emerald-500">Real-Time</div>
                   </div>
                </div>
              </div>
            </div>
            
            <div className="lg:col-span-4 relative group">
               <div className="absolute -inset-4 bg-blue-600/20 blur-[100px] rounded-full opacity-0 group-hover:opacity-100 transition-opacity duration-1000" />
               <div className="relative bg-[#111113] border border-white/10 rounded-[40px] p-10 space-y-8 shadow-2xl overflow-hidden">
                  <div className="flex items-center justify-between">
                     <span className="text-[9px] font-black text-slate-600 uppercase tracking-[0.4em]">Node_Status</span>
                     <div className="h-2 w-2 rounded-full bg-blue-500 shadow-[0_0_10px_rgba(59,130,246,0.5)]" />
                  </div>
                  <div className="space-y-6">
                     {[
                       { label: 'Ingest_Engine', val: 'Active', color: 'text-blue-400' },
                       { label: 'RAG_Citations', val: 'Verified', color: 'text-emerald-400' },
                       { label: 'MAE_Variance', val: '0.82%', color: 'text-white' }
                     ].map((s, i) => (
                       <div key={i} className="flex items-center justify-between border-b border-white/5 pb-4">
                          <span className="text-xs font-bold text-slate-500">{s.label}</span>
                          <span className={`text-xs font-black uppercase tracking-widest ${s.color}`}>{s.val}</span>
                       </div>
                     ))}
                  </div>
                  <div className="pt-4">
                     <div className="h-32 w-full bg-white/[0.02] border border-white/5 rounded-2xl flex items-center justify-center relative">
                        <div className="absolute inset-0 opacity-20" style={{ backgroundImage: 'repeating-linear-gradient(0deg, transparent, transparent 10px, #ffffff 10px, #ffffff 11px)' }} />
                        <Activity className="h-12 w-12 text-blue-600 animate-pulse" />
                     </div>
                  </div>
               </div>
            </div>
          </div>
        </div>
      </section>

      {/* The Problem: Brutalist Breakdown */}
      <section id="problem" className="px-8 py-32 max-w-[1400px] mx-auto border-t border-white/5 relative z-10 text-left bg-[#0D0D0F]">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-24">
          <div className="lg:col-span-5 space-y-12">
            <div className="space-y-6">
              <h2 className="text-6xl font-black tracking-[-0.05em] leading-[0.9] text-white uppercase italic underline decoration-blue-600/50 underline-offset-8">THE <br />TRUST <br /> DEFICIT.</h2>
              <p className="text-xl text-slate-400 font-medium leading-relaxed italic">
                Finance teams operate on "Theoretical Cash." Numbers that exist in a model but don't exist in the bank. We close the gap.
              </p>
            </div>
            
            <div className="space-y-10">
              {[
                { title: 'Behavioral Bias', desc: 'Real life averages 14+ days of unmodeled delay. We find them before they hit your runway.' },
                { title: 'Explainability Crisis', desc: 'Black-box forecasts are useless. Gitto provides provenance for every variance, linked to actual MT940 wires.' },
                { title: 'Fragmented Liquidity', desc: 'Managing group cash shouldn\'t require 14 logins. We normalize global bank data into a single truth layer.' },
              ].map((gap, i) => (
                <div key={i} className="space-y-2 border-l-2 border-white/10 pl-8 hover:border-blue-600 transition-all group cursor-default">
                  <h4 className="text-[11px] font-black uppercase tracking-[0.3em] text-slate-500 group-hover:text-white transition-colors">{gap.title}</h4>
                  <p className="text-sm text-slate-500 font-medium leading-relaxed group-hover:text-slate-400 transition-colors">{gap.desc}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="lg:col-span-7 relative flex items-center justify-center">
            <div className="absolute inset-0 bg-blue-600/5 blur-[150px] animate-pulse rounded-full" />
            
            {/* Diverging Reality Graph - Visualizing the Problem */}
            <div className="absolute top-0 right-0 w-64 h-48 bg-white/[0.02] border border-white/5 rounded-2xl p-6 backdrop-blur-xl z-20 hidden md:block">
               <div className="flex items-center justify-between mb-4">
                  <span className="text-[9px] font-black text-slate-500 uppercase tracking-widest">Theoretical_vs_Reality</span>
                  <TrendingUp className="h-3 w-3 text-red-500" />
               </div>
               <div className="relative h-20 w-full overflow-hidden">
                  {/* Theoretical Line */}
                  <svg className="absolute inset-0 w-full h-full">
                     <path d="M0 60 Q 50 55, 100 50 T 200 40" stroke="#334155" strokeWidth="2" fill="none" />
                     {/* Reality Line - Diverging */}
                     <path d="M0 60 Q 50 70, 100 85 T 200 110" stroke="#2563eb" strokeWidth="2" fill="none" strokeDasharray="4 2" className="animate-draw" />
                  </svg>
               </div>
               <div className="flex justify-between mt-2">
                  <div className="text-[8px] font-bold text-slate-600">Week 1</div>
                  <div className="text-[8px] font-bold text-blue-500">14d Gap</div>
               </div>
            </div>

            <div className="relative z-10 w-full aspect-square border border-white/5 rounded-full flex items-center justify-center p-20 animate-spin-slow">
              <div className="w-full h-full border border-white/10 rounded-full flex items-center justify-center p-20 animate-reverse-spin">
                <div className="w-full h-full bg-blue-600 rounded-full shadow-[0_0_100px_rgba(37,99,235,0.4)] flex items-center justify-center">
                  <span className="text-white font-black text-4xl italic tracking-tighter">TRUTH</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* The Product Engine: No more cards, this is a schematic */}
      <section id="ledger" className="px-8 py-32 bg-white text-black relative z-10 text-left overflow-hidden">
        <div className="max-w-[1400px] mx-auto space-y-32">
          <div className="flex flex-col md:flex-row md:items-end justify-between gap-8">
             <div className="space-y-4">
               <span className="text-[10px] font-black text-blue-600 tracking-[0.5em] uppercase border-b border-blue-600 pb-2">Product_Architecture // Module_Sync</span>
               <h2 className="text-[80px] font-black tracking-[-0.08em] italic leading-[0.8] uppercase">THE <br />DETERMINISTIC <br /> <span className="text-blue-600">STACK.</span></h2>
             </div>
             <p className="text-2xl font-bold text-slate-500 max-w-md leading-none italic uppercase">
               Engineered to eliminate the gap between forecast and reality.
             </p>
          </div>

          {/* Schematic Layout */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-px bg-slate-200 border border-slate-200">
            {/* Feature 01 - Large Schematic */}
            <div className="lg:col-span-8 bg-white p-16 space-y-12 group hover:bg-[#F9F9FB] transition-all">
               <div className="flex justify-between items-start">
                  <div className="space-y-4">
                     <span className="text-[10px] font-black text-slate-300 tracking-[0.4em]">01 // INGEST_LAYER</span>
                     <h3 className="text-5xl font-black italic tracking-tighter uppercase">MT940 Bank-Truth <br /> Reconciliation</h3>
                  </div>
                  <Landmark className="h-12 w-12 text-slate-200 group-hover:text-blue-600 transition-all" />
               </div>
               <div className="grid grid-cols-1 md:grid-cols-2 gap-16">
                  <p className="text-lg text-slate-500 font-bold leading-relaxed">
                    Automatically match MT940 and BAI2 statements against open ledger items. Our engine identifieswires, nets out fees, and identifies intercompany washes with 99.8% precision.
                  </p>
                  <div className="bg-slate-50 border border-slate-100 rounded-3xl p-8 space-y-6">
                     <div className="flex items-center justify-between text-[9px] font-black text-slate-400 uppercase tracking-widest">
                        <span>Terminal_Log</span>
                        <div className="flex gap-1">
                           <div className="h-1 w-1 rounded-full bg-blue-600 animate-ping" />
                           <div className="h-1 w-1 rounded-full bg-blue-600" />
                        </div>
                     </div>
                     <div className="space-y-2 font-mono text-[9px] text-slate-400 h-24 overflow-hidden">
                        <div className="animate-type-log">[14:22:01] INGEST // MT940_PARSE_SUCCESS</div>
                        <div className="animate-type-log" style={{ animationDelay: '0.2s' }}>[14:22:02] RECON // MATCH_FOUND: #INV-9942</div>
                        <div className="animate-type-log" style={{ animationDelay: '0.4s' }}>[14:22:02] LEDGER // SYNC_COMPLETED</div>
                        <div className="animate-type-log" style={{ animationDelay: '0.6s' }}>[14:22:03] SLACK // NOTIFY: UNMATCHED_WIRE_€12K</div>
                     </div>
                     <div className="space-y-3 pt-4 border-t border-slate-100">
                        <div className="h-1 w-full bg-slate-200 rounded-full overflow-hidden">
                           <div className="h-full bg-blue-600 animate-flow-fast" style={{ width: '40%' }} />
                        </div>
                        <div className="h-1 w-2/3 bg-slate-200 rounded-full overflow-hidden">
                           <div className="h-full bg-blue-600 animate-flow-fast" style={{ width: '60%', animationDelay: '0.2s' }} />
                        </div>
                     </div>
                  </div>
               </div>
            </div>

            {/* Feature 02 - Column */}
            <div className="lg:col-span-4 bg-white p-16 space-y-12 group hover:bg-[#F9F9FB] transition-all">
               <div className="flex justify-between items-start">
                  <div className="space-y-4">
                     <span className="text-[10px] font-black text-slate-300 tracking-[0.4em]">02 // BIAS_AI</span>
                     <h3 className="text-4xl font-black italic tracking-tighter uppercase">Behavioral <br /> Variance</h3>
                  </div>
                  <Activity className="h-10 w-10 text-slate-200 group-hover:text-blue-600 transition-all" />
               </div>
               <p className="text-lg text-slate-500 font-bold leading-relaxed">
                 We learn customer payment habit shifts (Regime Shifts) to predict actual cash timing, not just due dates. 
               </p>
               <div className="pt-8 space-y-6">
                  <div className="h-16 w-full bg-slate-50 rounded-xl relative overflow-hidden flex items-end">
                     <svg className="absolute inset-0 w-full h-full opacity-30">
                        <path d="M0 40 Q 20 10, 40 40 T 80 40 T 120 40 T 160 40" stroke="#2563eb" fill="none" className="animate-draw" />
                     </svg>
                     <div className="flex w-full items-baseline px-4 pb-2 justify-between z-10">
                        <span className="text-[8px] font-black text-slate-400">SHIFT_DETECTED</span>
                        <div className="text-xl font-black italic text-blue-600 tracking-tighter">+14 Days</div>
                     </div>
                  </div>
                  <div className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Detected Delay Insight</div>
               </div>
            </div>

            {/* Feature 03 - Column */}
            <div className="lg:col-span-4 bg-white p-16 space-y-12 group hover:bg-[#F9F9FB] transition-all border-t border-slate-200 lg:border-t-0">
               <div className="flex justify-between items-start">
                  <div className="space-y-4">
                     <span className="text-[10px] font-black text-slate-300 tracking-[0.4em]">03 // SIM_ENGINE</span>
                     <h3 className="text-4xl font-black italic tracking-tighter uppercase">Scenario <br /> Levers</h3>
                  </div>
                  <Layers className="h-10 w-10 text-slate-200 group-hover:text-blue-600 transition-all" />
               </div>
               <p className="text-lg text-slate-500 font-bold leading-relaxed">
                 Model "What-If" liquidity levers like vendor delays or SaaS acceleration with real-time ROI projection.
               </p>
               <div className="flex gap-2">
                  <div className="h-8 w-16 rounded bg-slate-100 flex items-center justify-center text-[10px] font-black">W1</div>
                  <div className="h-8 w-16 rounded bg-blue-600 flex items-center justify-center text-[10px] font-black text-white">W2</div>
                  <div className="h-8 w-16 rounded bg-slate-100 flex items-center justify-center text-[10px] font-black">W3</div>
               </div>
            </div>

            {/* Feature 04 - Large Schematic */}
            <div className="lg:col-span-8 bg-white p-16 space-y-12 group hover:bg-[#F9F9FB] transition-all border-t border-slate-200">
               <div className="flex justify-between items-start">
                  <div className="space-y-4">
                     <span className="text-[10px] font-black text-slate-300 tracking-[0.4em]">04 // INSIGHT_RAG</span>
                     <h3 className="text-5xl font-black italic tracking-tighter uppercase">Analyst RAG <br /> & Citations</h3>
                  </div>
                  <Sparkles className="h-12 w-12 text-slate-200 group-hover:text-blue-600 transition-all" />
               </div>
               <div className="grid grid-cols-1 md:grid-cols-2 gap-16">
                  <div className="bg-black text-white p-8 rounded-3xl space-y-6 shadow-2xl">
                     <div className="flex items-center gap-3">
                        <div className="h-6 w-6 rounded bg-blue-600 flex items-center justify-center text-[10px] italic font-black">G</div>
                        <span className="text-[9px] font-black uppercase tracking-widest text-slate-500">Gitto_Analyst</span>
                     </div>
                     <p className="text-sm font-medium italic text-slate-300">
                       "W3 forecast dropped €2.1M due to a regime shift in Enterprise-SaaS payment habits. Found citations in 42 bank receipts."
                     </p>
                     <div className="flex gap-2">
                        <div className="px-2 py-1 bg-white/10 rounded text-[8px] font-black uppercase">Ref: #BAI2-992</div>
                        <div className="px-2 py-1 bg-white/10 rounded text-[8px] font-black uppercase">Ref: #INV-441</div>
                     </div>
                  </div>
                  <div className="space-y-6 pt-4">
                     <p className="text-lg text-slate-500 font-bold leading-relaxed">
                       No more black-box AI answers. Every insight provided by Gitto is retrieved from specific bank truth and invoice reality, grounded in verifiable citations.
                     </p>
                     <Link href="/app">
                        <div className="flex items-center gap-3 text-blue-600 font-black uppercase tracking-widest text-xs cursor-pointer group/link">
                           Try the Analyst <MoveRight className="h-4 w-4 group-hover/link:translate-x-2 transition-transform" />
                        </div>
                     </Link>
                  </div>
               </div>
            </div>
          </div>
        </div>
      </section>

      {/* The Governance Layer - Institutional Strength */}
      <section id="enterprise" className="px-8 py-32 bg-[#0A0A0B] text-white relative z-10 text-left">
        <div className="max-w-[1400px] mx-auto grid grid-cols-1 lg:grid-cols-12 gap-32 items-center">
           <div className="lg:col-span-6 space-y-12">
              <div className="space-y-6">
                 <span className="text-[10px] font-black text-blue-400 tracking-[0.5em] uppercase">Control_Plane // Governance</span>
                 <h2 className="text-7xl font-black tracking-tighter leading-none italic uppercase">AUDIT-READY <br />COMMAND.</h2>
                 <p className="text-xl text-slate-400 font-medium leading-relaxed italic">
                   Gitto is built for the complexity of global group treasury. SOC2 Type II compliant and engineered for external audit transparency.
                 </p>
              </div>
              <div className="grid grid-cols-2 gap-12">
                 <div className="space-y-2">
                    <h4 className="text-xs font-black uppercase tracking-widest text-white">Immutable Snapshots</h4>
                    <p className="text-sm text-slate-500 font-medium leading-relaxed text-left">Every 13-week forecast is version-locked. Track variance from W1 to W13 with zero drift.</p>
                 </div>
                 <div className="space-y-2">
                    <h4 className="text-xs font-black uppercase tracking-widest text-white">Entity Netting</h4>
                    <p className="text-sm text-slate-500 font-medium leading-relaxed text-left">Detect and wash intercompany transfers automatically to see true group liquidity.</p>
                 </div>
              </div>
           </div>
           <div className="lg:col-span-6 relative">
              <div className="absolute inset-0 bg-blue-600/10 blur-[120px] animate-pulse rounded-full" />
              <div className="relative z-10 bg-white/5 border border-white/5 rounded-[40px] p-16 space-y-10 shadow-2xl">
                 <div className="flex items-center justify-between border-b border-white/10 pb-8">
                    <div className="flex items-center gap-4">
                       <ShieldCheck className="h-8 w-8 text-emerald-500" />
                       <div className="space-y-1">
                          <div className="text-lg font-black italic tracking-tight uppercase">SOC2 Certified</div>
                          <div className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Enterprise Security Core</div>
                       </div>
                    </div>
                    <div className="h-12 w-32 bg-white/5 border border-white/10 rounded-xl flex items-center justify-center">
                       <span className="text-[10px] font-black text-emerald-500 uppercase tracking-widest">Active</span>
                    </div>
                 </div>
                 <div className="space-y-6">
                    <div className="flex items-center gap-4">
                       <Code2 className="h-5 w-5 text-slate-600" />
                       <div className="h-2 w-full bg-white/5 rounded-full overflow-hidden">
                          <div className="h-full bg-blue-600 rounded-full" style={{ width: '85%' }} />
                       </div>
                    </div>
                    <div className="flex items-center gap-4">
                       <Cpu className="h-5 w-5 text-slate-600" />
                       <div className="h-2 w-full bg-white/5 rounded-full overflow-hidden">
                          <div className="h-full bg-blue-600 rounded-full" style={{ width: '92%' }} />
                       </div>
                    </div>
                 </div>
                 <p className="text-[11px] text-slate-500 font-bold italic text-center uppercase tracking-widest">Audit Logs Version 4.2.0 // Permanent Trail</p>
              </div>
           </div>
        </div>
      </section>

      {/* Testimonial - CFO Voice */}
      <section className="px-8 py-32 bg-white text-black z-10 text-center border-t border-slate-100">
        <div className="max-w-4xl mx-auto space-y-16">
          <h2 className="text-[40px] md:text-[56px] font-black italic tracking-tight leading-[1.1] uppercase">
            "Gitto is the first command center that actually feels like <span className="text-blue-600 underline decoration-blue-200 underline-offset-8">truth</span>. It has transformed our weekly cash meeting from a debate about data into a session about strategy."
          </h2>
          <div className="space-y-4">
            <div className="h-1 w-16 bg-blue-600 mx-auto" />
            <div>
              <p className="text-2xl font-black uppercase tracking-tighter">Raphael Leopold</p>
              <p className="text-[11px] font-black text-slate-400 uppercase tracking-[0.4em]">Partner // Coolwater Capital</p>
            </div>
          </div>
        </div>
      </section>

      {/* Final Call: Massive Authority */}
      <section className="px-8 py-64 bg-[#0A0A0B] text-white text-center relative z-10 overflow-hidden">
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full h-full bg-blue-600/10 blur-[150px] rounded-full scale-150" />
        <div className="max-w-5xl mx-auto space-y-16 relative z-10">
          <h2 className="text-[80px] md:text-[140px] font-black tracking-[-0.08em] leading-[0.8] uppercase italic">KNOW <br /> <span className="text-white/10 not-italic">YOUR</span> <br /> <span className="text-blue-600">CASH.</span></h2>
          <div className="pt-12">
            <Link href="/app">
              <Button className="bg-white text-black hover:bg-slate-200 rounded-none px-20 h-24 text-2xl font-black uppercase tracking-[0.2em] shadow-[0_40px_100px_rgba(255,255,255,0.1)] transition-all hover:scale-110 active:scale-95">
                Access Terminal
              </Button>
            </Link>
          </div>
        </div>
      </section>

      {/* Footer - Minimalist Brutalist */}
      <footer className="px-8 py-32 bg-[#0A0A0B] text-white border-t border-white/5 text-left">
        <div className="max-w-[1400px] mx-auto grid grid-cols-1 md:grid-cols-4 gap-20">
          <div className="space-y-10">
            <div className="flex items-center gap-2">
              <div className="h-6 w-6 rounded-lg bg-blue-600 flex items-center justify-center text-white font-black text-[12px] italic">G</div>
              <span className="font-bold text-lg tracking-[-0.04em] text-white uppercase italic">Gitto</span>
            </div>
            <div className="space-y-2 text-[11px] font-black uppercase tracking-[0.2em] text-slate-500">
              <p>Global Headquarters // NYC</p>
              <p>info@gitto.ai</p>
            </div>
          </div>
          <div className="space-y-8">
            <h4 className="text-[10px] font-black text-slate-600 uppercase tracking-[0.4em]">The Platform</h4>
            <ul className="space-y-4 text-[13px] font-black uppercase tracking-widest text-slate-400">
              <li className="hover:text-white cursor-pointer transition-colors">MT940_Connectivity</li>
              <li className="hover:text-white cursor-pointer transition-colors">13-Week_Grid</li>
              <li className="hover:text-white cursor-pointer transition-colors">Behavioral_Bias_AI</li>
            </ul>
          </div>
          <div className="space-y-8">
            <h4 className="text-[10px] font-black text-slate-600 uppercase tracking-[0.4em]">Industry Compare</h4>
            <ul className="space-y-4 text-[13px] font-black uppercase tracking-widest text-slate-400">
              <li className="hover:text-white cursor-pointer transition-colors">vs_Kyriba</li>
              <li className="hover:text-white cursor-pointer transition-colors">vs_Trovata</li>
              <li className="hover:text-white cursor-pointer transition-colors">vs_Deficit</li>
            </ul>
          </div>
          <div className="space-y-8 text-right">
            <h4 className="text-[10px] font-black text-slate-600 uppercase tracking-[0.4em]">Audit & Governance</h4>
            <p className="text-[11px] font-bold text-slate-500 leading-relaxed max-w-[200px] ml-auto">
              SOC2 Type II Compliant. Built for SOX and external audit transparency.
            </p>
          </div>
        </div>
        <div className="max-w-[1400px] mx-auto pt-32 flex justify-between items-center text-[9px] font-black uppercase tracking-[0.5em] text-slate-700">
          <span>©2025 Gitto_Intelligence_Inc.</span>
          <span>Security_First_Architecture</span>
        </div>
      </footer>

      {/* Global CSS for unique animations */}
      <style jsx global>{`
        @keyframes bounce-y {
          0%, 100% { transform: translateY(0); }
          50% { transform: translateY(-10px); }
        }
        .animate-bounce-y {
          animation: bounce-y 3s ease-in-out infinite;
        }
        @keyframes spin-slow {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        .animate-spin-slow {
          animation: spin-slow 20s linear infinite;
        }
        @keyframes reverse-spin-slow {
          from { transform: rotate(360deg); }
          to { transform: rotate(0deg); }
        }
        .animate-reverse-spin-slow {
          animation: reverse-spin-slow 15s linear infinite;
        }
        @keyframes reverse-spin {
          from { transform: rotate(360deg); }
          to { transform: rotate(0deg); }
        }
        .animate-reverse-spin {
          animation: reverse-spin 10s linear infinite;
        }
        @keyframes pulse-slow {
          0%, 100% { transform: scale(1); opacity: 1; }
          50% { transform: scale(1.05); opacity: 0.8; }
        }
        .animate-pulse-slow {
          animation: pulse-slow 4s ease-in-out infinite;
        }
        @keyframes flow {
          0% { transform: translate(0, 0); opacity: 0; }
          20% { opacity: 1; }
          80% { opacity: 1; }
          100% { transform: translate(var(--tx), var(--ty)); opacity: 0; }
        }
        .animate-flow {
          animation: flow 3s linear infinite;
        }
        @keyframes flow-fast {
          0% { transform: translateX(-100%); }
          100% { transform: translateX(100%); }
        }
        .animate-flow-fast {
          animation: flow-fast 2s linear infinite;
        }
        @keyframes workflow-card {
          0% { transform: translateX(-100px); opacity: 0; }
          10%, 90% { transform: translateX(0); opacity: 1; }
          100% { transform: translateX(100px); opacity: 0; }
        }
        .animate-workflow-card {
          animation: workflow-card 4.5s ease-in-out infinite;
        }
        @keyframes workflow-card-reverse {
          0% { transform: translateX(100px); opacity: 0; }
          10%, 90% { transform: translateX(0); opacity: 1; }
          100% { transform: translateX(-100px); opacity: 0; }
        }
        .animate-workflow-card-reverse {
          animation: workflow-card-reverse 4.5s ease-in-out infinite;
        }
        @keyframes shimmer {
          0% { opacity: 0.3; }
          50% { opacity: 1; }
          100% { opacity: 0.3; }
        }
        .animate-shimmer {
          animation: shimmer 2s infinite;
        }
        @keyframes fade-in-up {
          from { transform: translateY(20px); opacity: 0; }
          to { transform: translateY(0); opacity: 1; }
        }
        .animate-fade-in-up {
          animation: fade-in-up 0.8s ease-out forwards;
        }
        @keyframes float {
          0%, 100% { transform: translateY(0); }
          50% { transform: translateY(-20px); }
        }
        .animate-float {
          animation: float 5s ease-in-out infinite;
        }
        @keyframes draw {
          from { stroke-dashoffset: 1000; }
          to { stroke-dashoffset: 0; }
        }
        .animate-draw {
          stroke-dasharray: 1000;
          animation: draw 5s linear forwards infinite;
        }
        @keyframes type-log {
          from { opacity: 0; transform: translateY(5px); }
          to { opacity: 1; transform: translateY(0); }
        }
        .animate-type-log {
          animation: type-log 0.5s ease-out forwards;
        }
      `}</style>
    </div>
  );
}
