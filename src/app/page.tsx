'use client';

import { useState } from 'react';
import Link from "next/link";
import { 
  ArrowRight, CheckCircle2, Shield, BarChart3, TrendingUp, AlertCircle, 
  Landmark, Users, Search, Bell, Calendar, ChevronRight, MessageSquare,
  Lock, Zap, Database, Globe, Briefcase, Plus, Sparkles, Filter, 
  FileText, ArrowDownRight, ArrowUpRight, Play, Layout, MousePointer2,
  Cloud as CloudIcon, Activity, Layers, Terminal, ShieldCheck
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

      {/* Hero: Authority through Technical Precision */}
      <section className="relative pt-40 pb-20 px-8 z-10">
        <div className="max-w-[1400px] mx-auto grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">
          <div className="lg:col-span-8 space-y-8">
            <div className="inline-flex items-center px-3 py-1 rounded-sm bg-blue-500/10 border border-blue-500/20 text-[10px] font-black uppercase tracking-[0.3em] text-blue-400">
              Enterprise Treasury Engine // Live Ingest Active
            </div>
            <h1 className="text-[70px] md:text-[110px] font-black tracking-[-0.06em] leading-[0.85] text-white">
              CASH REALITY <br />
              ANCHORED IN <br />
              <span className="text-blue-500">BANK TRUTH.</span>
            </h1>
            <p className="text-xl text-slate-400 font-medium leading-relaxed max-w-2xl border-l-2 border-blue-500/30 pl-6">
              The gap between your forecast and your bank balance is where enterprise risk lives. Gitto bridges this deficit with a deterministic ledger that reconciles live MT940/BAI2 bank feeds against your 13-week liquidity grid.
            </p>
            <div className="flex items-center gap-8 pt-4">
              <Link href="/app">
                <Button className="bg-white text-black hover:bg-slate-200 rounded-none px-10 h-16 text-sm font-black uppercase tracking-widest transition-all hover:scale-105">
                  Access Liquidity Terminal
                </Button>
              </Link>
              <div className="flex flex-col">
                <span className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Global Ingest Accuracy</span>
                <span className="text-2xl font-black text-emerald-500">99.98%</span>
              </div>
            </div>
          </div>
          
          <div className="lg:col-span-4 relative">
             <div className="bg-[#111113] border border-white/5 rounded-3xl p-8 space-y-6 shadow-2xl animate-fade-in-up">
                <div className="flex items-center justify-between border-b border-white/5 pb-4">
                  <span className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Network_Health</span>
                  <div className="flex gap-1">
                    <div className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                    <div className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                  </div>
                </div>
                <div className="space-y-4">
                   {[
                     { l: 'SAP Integration', s: 'Connected' },
                     { l: 'Oracle NetSuite', s: 'Synced' },
                     { l: 'Global Bank Feed', s: 'Live' }
                   ].map((sys, i) => (
                     <div key={i} className="flex items-center justify-between bg-white/[0.02] p-3 rounded-xl border border-white/5">
                        <span className="text-xs font-bold text-slate-400">{sys.l}</span>
                        <span className="text-[10px] font-black uppercase tracking-widest text-blue-400">{sys.s}</span>
                     </div>
                   ))}
                </div>
             </div>
          </div>
        </div>
      </section>

      {/* The Problem: Deep Domain Expertise */}
      <section id="problem" className="px-8 py-32 max-w-[1400px] mx-auto border-t border-white/5 relative z-10 text-left bg-[#0D0D0F]">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-20">
          <div className="lg:col-span-5 space-y-8">
            <h2 className="text-5xl font-black tracking-tighter leading-[0.9] text-white uppercase italic">THE <br /><span className="text-blue-500">EXPLAINABILITY</span> <br /> DEFICIT.</h2>
            <p className="text-lg text-slate-400 font-medium leading-relaxed">
              Black-box forecasting models fail CFOs because they lack provenance. When a cash position shifts, you need to know exactly which wire or vendor bill caused the variance.
            </p>
            <div className="space-y-4 pt-6">
               <div className="flex items-center gap-4 text-sm font-bold text-slate-300">
                  <AlertCircle className="h-5 w-5 text-red-500" />
                  <span>Unmodeled Behavioral Bias: Customers ignore due dates.</span>
               </div>
               <div className="flex items-center gap-4 text-sm font-bold text-slate-300">
                  <AlertCircle className="h-5 w-5 text-red-500" />
                  <span>Fragmented Bank Data: 14+ logins to see group liquidity.</span>
               </div>
               <div className="flex items-center gap-4 text-sm font-bold text-slate-300">
                  <AlertCircle className="h-5 w-5 text-red-500" />
                  <span>The Manual Sync Drain: Static 13-week grids are dead on arrival.</span>
               </div>
            </div>
          </div>

          <div className="lg:col-span-7 grid grid-cols-1 md:grid-cols-2 gap-px bg-white/5 border border-white/5">
            {[
              { t: 'MT940/BAI2 Ingest', d: 'Automated direct bank connectivity eliminates the manual download-and-format loop.' },
              { t: 'MAE Optimization', d: 'We track Mean Absolute Error across every scenario to refine your forecasting regime.' },
              { t: 'Entity Netting', d: 'Automated intercompany wash detection for a true consolidated group liquidity view.' },
              { t: 'Provenance Audit', d: 'Every snapshot is locked. Every variance is linked to a specific underlying document.' },
            ].map((p, i) => (
              <div key={i} className="bg-[#0A0A0B] p-12 space-y-4 hover:bg-white/[0.02] transition-colors group">
                <h4 className="text-[11px] font-black uppercase tracking-[0.3em] text-slate-600 group-hover:text-blue-500 transition-colors">CAPABILITY_0{i+1}</h4>
                <div className="space-y-2">
                  <h3 className="text-xl font-black text-white italic tracking-tight">{p.t}</h3>
                  <p className="text-sm text-slate-500 font-medium leading-relaxed">{p.d}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* The Solution: Engineered for Treasury */}
      <section id="ledger" className="px-8 py-32 bg-white text-black relative z-10 text-left">
        <div className="max-w-[1400px] mx-auto space-y-24">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-16 items-end">
            <div className="lg:col-span-7 space-y-6">
               <span className="text-[10px] font-black text-blue-600 tracking-[0.5em] uppercase">Architecture // v4.2</span>
               <h2 className="text-[64px] font-black tracking-tighter italic leading-[0.85] uppercase">
                 THE LIQUIDITY <br /> <span className="text-blue-600">LEDGER.</span>
               </h2>
               <p className="text-2xl font-bold text-slate-500 max-w-2xl leading-tight">
                 A deterministic truth layer that synchronizes your ERP's theoretical due dates with your bank's behavioral reality.
               </p>
            </div>
            <div className="lg:col-span-5 pb-4">
              <div className="flex gap-4">
                 <div className="flex-1 bg-slate-50 p-6 border border-slate-100 rounded-2xl">
                    <div className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1">Direct API Connects</div>
                    <div className="text-3xl font-black">7,000+</div>
                 </div>
                 <div className="flex-1 bg-slate-50 p-6 border border-slate-100 rounded-2xl">
                    <div className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1">MT940 Parse Speed</div>
                    <div className="text-3xl font-black">&lt;1.2s</div>
                 </div>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-12">
            {[
              { t: 'Bank-Truth Reconciliation', d: 'Automated matching of MT940 statements against open ledger items with 99.8% precision.', icon: <Landmark /> },
              { t: 'Behavioral Variance Analysis', d: 'We learn payment habit shifts (Regime Shifts) to predict delay before your runway is impacted.', icon: <Activity /> },
              { t: 'Scenario Stress Testing', d: 'Model "What-If" liquidity levers (Delay Vendor, Accelerate SaaS) with real-time ROI projection.', icon: <Layers /> },
              { t: 'Multi-Entity Maestro', d: 'Consolidated group visibility with snapshot-locked FX rates and reporting currency normalization.', icon: <Globe /> },
              { t: 'Analyst RAG Engine', d: 'Natural language queries grounded in verified document citations. No more black-box answers.', icon: <Sparkles /> },
              { t: 'Enterprise Governance', d: 'Audit-ready logs for every lever shift and manual override. Built for external audit transparency.', icon: <ShieldCheck /> }
            ].map((m, i) => (
              <div key={i} className="p-12 border border-slate-100 bg-[#F9F9FB] space-y-10 group hover:bg-black hover:text-white transition-all duration-700">
                <div className="h-14 w-14 rounded-2xl bg-white border border-slate-200 flex items-center justify-center shadow-sm group-hover:bg-blue-600 group-hover:border-blue-500 group-hover:text-white transition-all group-hover:scale-110">
                  {m.icon}
                </div>
                <div className="space-y-4">
                  <h3 className="text-3xl font-black italic tracking-tight uppercase leading-none">{m.t}</h3>
                  <p className="text-lg font-bold opacity-50 leading-relaxed group-hover:opacity-100">{m.d}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* The Impact: Real-Time Command */}
      <section id="enterprise" className="px-8 py-32 max-w-[1400px] mx-auto relative z-10 text-left bg-[#0A0A0B]">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-24 items-center">
          <div className="lg:col-span-5 space-y-12">
            <div className="inline-flex items-center px-3 py-1 rounded-sm bg-blue-500/10 border border-blue-500/20 text-[10px] font-black uppercase tracking-[0.3em] text-blue-400">
              Operational Impact // v1.0
            </div>
            <h2 className="text-6xl font-black tracking-tighter leading-none text-white uppercase italic">
              COMMAND YOUR <br /> RUNWAY.
            </h2>
            <div className="space-y-8">
               <div className="border-l-2 border-blue-600 pl-8 space-y-2">
                  <div className="text-4xl font-black">14 Days</div>
                  <p className="text-slate-500 font-bold uppercase tracking-widest text-xs">Earlier insight into cash shortfalls</p>
               </div>
               <div className="border-l-2 border-blue-600 pl-8 space-y-2">
                  <div className="text-4xl font-black">92%</div>
                  <p className="text-slate-500 font-bold uppercase tracking-widest text-xs">Reduction in manual sync overhead</p>
               </div>
               <div className="border-l-2 border-blue-600 pl-8 space-y-2">
                  <div className="text-4xl font-black">0.8d</div>
                  <p className="text-slate-500 font-bold uppercase tracking-widest text-xs">Average MAE forecast accuracy</p>
               </div>
            </div>
          </div>
          
          <div className="lg:col-span-7">
             <div className="bg-[#111113] border border-white/5 rounded-[40px] p-12 overflow-hidden relative group">
                <div className="absolute inset-0 bg-blue-600/5 opacity-0 group-hover:opacity-100 transition-opacity duration-1000" />
                <div className="relative z-10 space-y-8">
                   <div className="flex items-center justify-between">
                      <span className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Active_Liquidity_Simulation</span>
                      <Terminal className="h-4 w-4 text-blue-500" />
                   </div>
                   <div className="h-px w-full bg-white/5" />
                   <p className="text-xl text-slate-400 font-medium italic leading-relaxed">
                     "Simulating 14-day delay on Enterprise SaaS inflows. Liquidity buffer remains above €4.2M threshold. No lever adjustment required for W4 payment run."
                   </p>
                   <div className="flex gap-4">
                      <div className="px-4 py-2 bg-blue-600/10 border border-blue-600/20 rounded-lg text-[9px] font-black text-blue-400 uppercase tracking-widest">Status: Deterministic</div>
                      <div className="px-4 py-2 bg-emerald-600/10 border border-emerald-600/20 rounded-lg text-[9px] font-black text-emerald-500 uppercase tracking-widest">Risk: Cleared</div>
                   </div>
                </div>
             </div>
          </div>
        </div>
      </section>

      {/* Testimonial - The CFO Voice */}
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

      {/* Final CTA: Massive Authority */}
      <section className="px-8 py-64 bg-[#0A0A0B] text-white text-center relative z-10 overflow-hidden">
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full h-full bg-blue-600/10 blur-[150px] rounded-full scale-150" />
        <div className="max-w-5xl mx-auto space-y-16 relative z-10">
          <h2 className="text-[80px] md:text-[140px] font-black tracking-[-0.08em] leading-[0.8] uppercase">ELIMINATE <br /> <span className="text-white/10 italic">THE DEFICIT.</span></h2>
          <div className="pt-12">
            <Link href="/app">
              <Button className="bg-white text-black hover:bg-slate-200 rounded-none px-20 h-24 text-2xl font-black uppercase tracking-[0.2em] shadow-[0_40px_100px_rgba(255,255,255,0.1)] transition-all hover:scale-110">
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
    </div>
  );
}
