'use client';

import { useState } from 'react';
import Link from "next/link";
import { 
  ArrowRight, CheckCircle2, Shield, BarChart3, TrendingUp, AlertCircle, 
  Landmark, Users, Search, Bell, Calendar, ChevronRight, MessageSquare,
  Lock, Zap, Database, Globe, Briefcase, Plus, Sparkles, Filter, 
  FileText, ArrowDownRight, ArrowUpRight, Play, Layout, MousePointer2,
  Cloud as CloudIcon
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

      {/* Expressive Hero - Tighter */}
      <section className="relative pt-40 pb-20 px-8 z-10">
        <div className="max-w-[1400px] mx-auto grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">
          <div className="lg:col-span-7 space-y-8">
            <div className="inline-flex items-center px-3 py-1 rounded-sm bg-blue-500/10 border border-blue-500/20 text-[10px] font-black uppercase tracking-[0.3em] text-blue-400">
              Deterministic Cash Intelligence
            </div>
            <h1 className="text-[70px] md:text-[110px] font-black tracking-[-0.06em] leading-[0.85] text-white">
              BANK <span className="text-white/20 italic font-medium">TRUTH</span> <br />
              FOR GROUP <br />
              <span className="text-blue-500">LIQUIDITY.</span>
            </h1>
            <p className="text-lg text-slate-400 font-medium leading-relaxed max-w-xl border-l-2 border-blue-500/30 pl-6">
              Gitto bridges the gap between theoretical forecasts and bank reality. We ingest your direct bank feeds to eliminate behavioral bias and unmodeled delays.
            </p>
          </div>
          
          <div className="lg:col-span-5 relative flex items-center justify-center">
            {/* The Integration Engine - Animated Visual */}
            <div className="relative w-[400px] h-[400px] flex items-center justify-center">
              <div className="absolute inset-0 opacity-10" style={{ backgroundImage: 'linear-gradient(45deg, #ffffff 1px, transparent 1px), linear-gradient(-45deg, #ffffff 1px, transparent 1px)', backgroundSize: '15px 15px' }} />
              
              <div className="relative z-20 w-24 h-24 bg-blue-600 rounded-[24px] flex items-center justify-center shadow-[0_0_60px_rgba(37,99,235,0.4)] animate-pulse-slow">
                <div className="text-white font-black text-4xl italic -skew-x-12">G</div>
              </div>

              <div className="absolute inset-0 animate-spin-slow">
                <div className="absolute top-0 left-1/2 -translate-x-1/2 -translate-y-1/2">
                   <div className="h-12 w-12 rounded-xl bg-white/5 border border-white/10 backdrop-blur-xl flex items-center justify-center group hover:bg-white/10 transition-colors">
                     <Database className="h-5 w-5 text-slate-400" />
                   </div>
                </div>
                <div className="absolute bottom-0 left-1/2 -translate-x-1/2 translate-y-1/2">
                   <div className="h-12 w-12 rounded-xl bg-white/5 border border-white/10 backdrop-blur-xl flex items-center justify-center">
                     <Globe className="h-5 w-5 text-slate-400" />
                   </div>
                </div>
              </div>

              <div className="absolute inset-8 animate-reverse-spin-slow">
                <div className="absolute left-0 top-1/2 -translate-x-1/2 -translate-y-1/2">
                   <div className="h-10 w-10 rounded-xl bg-[#f57c00]/10 border border-[#f57c00]/30 flex items-center justify-center">
                     <div className="h-5 w-5 rounded bg-[#f57c00] flex items-center justify-center text-[7px] font-black text-white">sf</div>
                   </div>
                </div>
                <div className="absolute right-0 top-1/2 translate-x-1/2 -translate-y-1/2">
                   <div className="h-10 w-10 rounded-xl bg-blue-500/10 border border-blue-500/30 flex items-center justify-center shadow-[0_0_20px_rgba(59,130,246,0.2)]">
                     <CloudIcon className="h-5 w-5 text-blue-400" />
                   </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* The Problem: Why Gitto? - More Compact */}
      <section id="problem" className="px-8 py-32 max-w-[1400px] mx-auto border-t border-white/5 relative z-10 text-left bg-[#0D0D0F]">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-20">
          <div className="lg:col-span-5 space-y-8">
            <h2 className="text-5xl font-black tracking-tighter leading-[0.9] text-white uppercase">THE <br /><span className="text-blue-500 italic">DEFICIT</span> <br /> OF TRUST.</h2>
            <p className="text-lg text-slate-400 font-medium leading-relaxed">
              Finance teams are drowning in "Theoretical Cash." Numbers that look perfect in a model but never hit the bank.
            </p>
            <div className="pt-6">
               <Link href="/app">
                 <Button className="bg-white text-black hover:bg-slate-200 rounded-full px-8 h-12 text-xs font-black uppercase tracking-widest shadow-xl transition-all hover:scale-105 active:scale-95">
                   Access Product Terminal
                 </Button>
               </Link>
            </div>
          </div>

          <div className="lg:col-span-7 grid grid-cols-1 md:grid-cols-2 gap-px bg-white/5 border border-white/5">
            {[
              { t: 'Behavioral Blindness', d: 'ERP due dates are ignored by customers. We learn actual payment habits to find the 14-day "Hidden Delay".' },
              { t: 'The Bank-Truth Gap', d: 'Forecasts built in isolation fail. Gitto reconciles live receipts directly to your 13-week grid.' },
              { t: 'Explainability Crisis', d: 'When cash drops, CFOs need evidence. Gitto provides direct citations to underlying bank transactions.' },
              { t: 'Manual Overhead', d: 'Static spreadsheets take days to update. Gitto syncs every hour to provide a live liquidity ledger.' },
            ].map((p, i) => (
              <div key={i} className="bg-[#0A0A0B] p-10 space-y-4 hover:bg-white/[0.02] transition-colors">
                <h4 className="text-[11px] font-black uppercase tracking-[0.3em] text-blue-400">ERROR_0{i+1}</h4>
                <div className="space-y-2">
                  <h3 className="text-xl font-black text-white italic">{p.t}</h3>
                  <p className="text-sm text-slate-500 font-medium leading-relaxed">{p.d}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Product Deep Dive: Core Modules */}
      <section id="enterprise" className="px-8 py-32 bg-white text-black relative z-10 text-left">
        <div className="max-w-[1400px] mx-auto space-y-20">
          <div className="flex flex-col md:flex-row md:items-end justify-between gap-8">
             <div className="space-y-4">
               <span className="text-[10px] font-black text-blue-600 tracking-[0.5em] uppercase">The_Gitto_Stack</span>
               <h2 className="text-6xl font-black tracking-tighter italic">ENGINEERED FOR <br />TREASURY SCALE.</h2>
             </div>
             <p className="text-xl text-slate-500 font-bold max-w-md leading-tight">
               Four deterministic modules built to consolidate group liquidity and automate forecasting.
             </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
            {[
              { t: '13-Week Grid', d: 'Interactive multi-entity grid with snapshot locking and weekly variance tracking.', icon: <Layout className="h-6 w-6" /> },
              { t: 'Bank Ledger', d: 'Live bank ingest with automated receipt matching and "Unmatched Cash" queues.', icon: <Landmark className="h-6 w-6" /> },
              { t: 'Analyst RAG', icon: <Sparkles className="h-6 w-6" />, d: 'Ask natural language questions grounded in verified invoice data with citations.' },
              { t: 'FX Maestro', icon: <Globe className="h-6 w-6" />, d: 'Snapshot-locked FX rates and automated reporting currency normalization across the group.' }
            ].map((m, i) => (
              <div key={i} className="p-10 border border-slate-100 bg-[#F9F9FB] space-y-8 group hover:bg-black hover:text-white transition-all duration-500">
                <div className="h-12 w-12 rounded-xl bg-white border border-slate-200 flex items-center justify-center shadow-sm group-hover:bg-blue-600 group-hover:border-blue-500 group-hover:text-white transition-all">
                  {m.icon}
                </div>
                <div className="space-y-3">
                  <h3 className="text-2xl font-black italic tracking-tight">{m.t}</h3>
                  <p className="text-sm font-bold opacity-60 leading-relaxed group-hover:opacity-100">{m.d}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* The Product Walkthrough - Tighter */}
      <section id="ledger" className="px-8 py-32 max-w-[1400px] mx-auto relative z-10 text-left">
        <div className="space-y-20">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-20 items-center">
            <div className="lg:col-span-5 space-y-8">
              <div className="inline-flex items-center px-3 py-1 rounded-sm bg-blue-500/10 border border-blue-500/20 text-[10px] font-black uppercase tracking-[0.3em] text-blue-400">
                Module_01 // Reconciliation
              </div>
              <h2 className="text-5xl font-black tracking-tighter leading-none text-white uppercase italic">
                LEAVE NO CASH <br /> UNMATCHED.
              </h2>
              <p className="text-lg text-slate-400 font-medium leading-relaxed">
                Our Bank Ledger ingest identifies incoming wires and matches them to open invoices. Unmatched pings your Slack instantly.
              </p>
            </div>
            
            <div className="lg:col-span-7">
              <div className="bg-[#111113] rounded-[32px] border border-white/5 p-8 h-[350px] relative overflow-hidden shadow-2xl">
                <div className="absolute inset-0 opacity-5" style={{ backgroundImage: 'radial-gradient(circle, #ffffff 1px, transparent 1px)', backgroundSize: '25px 25px' }} />
                <div className="relative h-full flex items-center justify-between px-10">
                  <div className="space-y-4">
                    <div className="text-[9px] font-black text-slate-600 uppercase tracking-widest">Bank_Stream</div>
                    {[1,2].map(i => (
                      <div key={i} className="h-14 w-56 bg-white/5 border border-white/10 rounded-xl p-4 flex items-center justify-between animate-workflow-card">
                        <div className="flex items-center gap-3">
                          <Landmark className="h-4 w-4 text-emerald-500" />
                          <div className="text-[10px] font-black text-white">€{12000 * i},000</div>
                        </div>
                      </div>
                    ))}
                  </div>
                  <Zap className="h-8 w-8 text-blue-500 animate-pulse" />
                  <div className="space-y-4 text-right">
                    <div className="text-[9px] font-black text-slate-600 uppercase tracking-widest">Gitto_Ledger</div>
                    {[1,2].map(i => (
                      <div key={i} className="h-14 w-56 bg-blue-600/10 border border-blue-500/30 rounded-xl p-4 flex items-center justify-between animate-workflow-card-reverse">
                        <CheckCircle2 className="h-4 w-4 text-blue-400" />
                        <div className="text-[10px] font-black text-blue-400">#INV-990{i}</div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Testimonial - Stark Style */}
      <section className="px-8 py-64 bg-[#0A0A0B] text-white z-10 text-center">
        <div className="max-w-4xl mx-auto space-y-16">
          <h2 className="text-[40px] md:text-[60px] font-black italic tracking-tight leading-[1.1]">
            "I've been a treasury nerd for my whole career. Gitto is the first command center that actually feels like <span className="text-blue-500">truth</span>."
          </h2>
          <div className="space-y-4">
            <div className="h-[1px] w-24 bg-white/20 mx-auto" />
            <div>
              <p className="text-xl font-black uppercase tracking-[0.2em]">Raphael Leopold</p>
              <p className="text-[11px] font-bold text-slate-500 uppercase tracking-[0.3em]">Partner // Coolwater Capital</p>
            </div>
          </div>
        </div>
      </section>

      {/* Final Call - The Magic Finish */}
      <section className="px-8 py-64 bg-white text-black text-center relative z-10">
        <div className="max-w-5xl mx-auto space-y-12">
          <h2 className="text-[100px] md:text-[180px] font-black tracking-[-0.08em] leading-[0.8] uppercase">KNOW <br /> <span className="text-slate-200">YOUR</span> <br /> CASH.</h2>
          <div className="pt-12">
            <Link href="/app">
              <Button className="bg-black text-white hover:bg-slate-900 rounded-none px-20 h-24 text-2xl font-black uppercase tracking-[0.1em] transition-all hover:scale-105 active:scale-95 shadow-[0_20px_60px_rgba(0,0,0,0.2)]">
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
              <p>Based in New York City</p>
              <p>info@gitto.ai</p>
            </div>
          </div>
          <div className="space-y-8">
            <h4 className="text-[10px] font-black text-slate-600 uppercase tracking-[0.4em]">Platform</h4>
            <ul className="space-y-4 text-[13px] font-black uppercase tracking-widest text-slate-400">
              <li className="hover:text-white cursor-pointer transition-colors">Terminals</li>
              <li className="hover:text-white cursor-pointer transition-colors">Ledger_Truth</li>
              <li className="hover:text-white cursor-pointer transition-colors">RAG_Insights</li>
            </ul>
          </div>
          <div className="space-y-8">
            <h4 className="text-[10px] font-black text-slate-600 uppercase tracking-[0.4em]">Compare</h4>
            <ul className="space-y-4 text-[13px] font-black uppercase tracking-widest text-slate-400">
              <li className="hover:text-white cursor-pointer transition-colors">vs_Kyriba</li>
              <li className="hover:text-white cursor-pointer transition-colors">vs_Manual</li>
              <li className="hover:text-white cursor-pointer transition-colors">vs_Deficit</li>
            </ul>
          </div>
          <div className="space-y-8 text-right">
            <h4 className="text-[10px] font-black text-slate-600 uppercase tracking-[0.4em]">Governance</h4>
            <p className="text-[11px] font-bold text-slate-500 leading-relaxed max-w-[200px] ml-auto">
              Built for external audit transparency and group-level group liquidity controls.
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
      `}</style>
    </div>
  );
}
