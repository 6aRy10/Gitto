'use client';

import { useState } from 'react';
import Link from "next/link";
import { 
  ArrowRight, CheckCircle2, Shield, BarChart3, TrendingUp, AlertCircle, 
  Landmark, Users, Search, Bell, Calendar, ChevronRight, MessageSquare,
  Lock, Zap, Database, Globe, Briefcase, Plus, Sparkles, Filter, 
  FileText, ArrowDownRight, ArrowUpRight, Play, Layout, MousePointer2
} from "lucide-react";
import { Button } from "../components/ui/button";
import { Card, CardContent } from "../components/ui/card";

export default function Landing() {
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
              <div className="h-6 w-6 rounded bg-white flex items-center justify-center text-black font-black text-[10px]">G</div>
              <span className="font-bold text-lg tracking-[-0.04em] text-white uppercase italic">Gitto</span>
            </Link>
            <div className="hidden lg:flex items-center gap-8 text-[11px] font-black uppercase tracking-[0.2em] text-slate-500">
              <button className="hover:text-white transition-colors">The Problem</button>
              <button className="hover:text-white transition-colors">The Ledger</button>
              <button className="hover:text-white transition-colors">Enterprise</button>
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

      {/* Expressive Hero */}
      <section className="relative pt-64 pb-32 px-8 z-10">
        <div className="max-w-[1400px] mx-auto grid grid-cols-1 lg:grid-cols-12 gap-20 items-end">
          <div className="lg:col-span-8 space-y-12">
            <div className="inline-flex items-center px-3 py-1 rounded-sm bg-white/5 border border-white/10 text-[10px] font-black uppercase tracking-[0.3em] text-blue-400">
              Deterministic Cash Intelligence
            </div>
            <h1 className="text-[80px] md:text-[140px] font-black tracking-[-0.07em] leading-[0.85] text-white">
              BANK <span className="text-white/20 italic font-medium">TRUTH</span> <br />
              IS THE ONLY <br />
              <span className="text-blue-500">REALITY.</span>
            </h1>
          </div>
          <div className="lg:col-span-4 pb-6 space-y-8">
            <p className="text-xl text-slate-400 font-medium leading-relaxed tracking-tight border-l-2 border-blue-500/30 pl-8">
              Spreadsheets model the "theoretical." Gitto anchors your liquidity in actual bank receipts, intercompany washes, and behavioral bias.
            </p>
            <div className="pl-8 flex items-center gap-4">
              <div className="h-12 w-12 rounded-full border border-white/10 flex items-center justify-center animate-bounce-y">
                <ArrowDownRight className="h-5 w-5 text-blue-400" />
              </div>
              <span className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-500">Scroll to enter the command center</span>
            </div>
          </div>
        </div>
      </section>

      {/* The Asymmetric Dashboard - Bloomberg/Harvey Style */}
      <section className="px-8 py-20 relative z-10">
        <div className="max-w-[1400px] mx-auto">
          <div className="bg-[#111113] rounded-[24px] border border-white/5 shadow-[0_40px_100px_rgba(0,0,0,0.5)] overflow-hidden flex flex-col h-[850px] relative">
            {/* Terminal Header */}
            <div className="h-14 border-b border-white/5 flex items-center justify-between px-8 bg-[#161618]">
              <div className="flex items-center gap-6">
                <div className="flex gap-1.5">
                  <div className="h-2 w-2 rounded-full bg-white/10" />
                  <div className="h-2 w-2 rounded-full bg-white/10" />
                  <div className="h-2 w-2 rounded-full bg-white/10" />
                </div>
                <div className="h-4 w-[1px] bg-white/10" />
                <span className="text-[10px] font-black uppercase tracking-[0.3em] text-slate-500">Gitto Terminal v4.2 // Main_Ledger</span>
              </div>
              <div className="flex items-center gap-4">
                <div className="text-[10px] font-black uppercase tracking-widest text-emerald-500 flex items-center gap-2">
                  <div className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
                  Live Bank Feed: 100% Sync
                </div>
              </div>
            </div>

            <div className="flex flex-1 overflow-hidden">
              {/* Left: Metadata Column */}
              <div className="w-80 border-r border-white/5 p-8 flex flex-col gap-12 bg-[#0D0D0F]">
                <div className="space-y-6">
                  <h4 className="text-[10px] font-black uppercase tracking-[0.3em] text-slate-600">Liquidity_Metrics</h4>
                  <div className="space-y-8">
                    {[
                      { label: 'Group_Cash', val: '€12.8M', trend: '+4.2%' },
                      { label: 'Unmatched_Inflow', val: '€430k', trend: 'Critical' },
                      { label: 'MAE_Accuracy', val: '0.8d', trend: '99%' },
                    ].map((m, i) => (
                      <div key={i} className="space-y-1">
                        <div className="text-[9px] font-bold text-slate-500 uppercase tracking-widest">{m.label}</div>
                        <div className="flex items-baseline gap-3">
                          <div className="text-2xl font-black tracking-tighter text-white">{m.val}</div>
                          <div className={`text-[9px] font-black uppercase ${m.trend === 'Critical' ? 'text-red-500' : 'text-emerald-500'}`}>{m.trend}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
                
                <div className="mt-auto space-y-4">
                  <div className="p-4 rounded-xl bg-white/5 border border-white/5 space-y-3">
                    <div className="flex items-center gap-2">
                      <Sparkles className="h-3 w-3 text-blue-400" />
                      <span className="text-[9px] font-black uppercase tracking-widest text-blue-400">Analyst_Insight</span>
                    </div>
                    <p className="text-[11px] text-slate-400 leading-relaxed font-medium italic">
                      "Siemens AG has missing payment run for 2 weeks. Predicting +14d delay on #INV-221."
                    </p>
                  </div>
                </div>
              </div>

              {/* Center: The Main Ledger Canvas */}
              <div className="flex-1 p-10 space-y-12 bg-white/[0.01]">
                <div className="grid grid-cols-12 gap-8 items-start">
                  <div className="col-span-8 space-y-8 text-left">
                    <h3 className="text-4xl font-black tracking-tight text-white italic">13-Week Cash Command</h3>
                    <div className="grid grid-cols-4 gap-4">
                      {[1,2,3,4].map(i => (
                        <div key={i} className={`h-24 rounded-2xl border ${i === 1 ? 'bg-blue-600 border-blue-500 shadow-[0_0_30px_rgba(37,99,235,0.3)]' : 'bg-white/5 border-white/5'} p-4 flex flex-col justify-between transition-all hover:scale-105 cursor-pointer`}>
                          <span className={`text-[9px] font-black uppercase tracking-widest ${i === 1 ? 'text-white' : 'text-slate-500'}`}>Week_{i}</span>
                          <span className="text-lg font-black text-white">€{i}.2M</span>
                        </div>
                      ))}
                    </div>
                    
                    {/* Living Grid Mockup */}
                    <div className="rounded-2xl border border-white/5 bg-[#161618] overflow-hidden">
                      <div className="p-4 bg-white/5 flex items-center justify-between px-6">
                        <span className="text-[10px] font-black uppercase tracking-[0.3em] text-slate-400">Transaction_Stream</span>
                        <div className="h-2 w-2 rounded-full bg-emerald-500" />
                      </div>
                      <div className="divide-y divide-white/5 text-left">
                        {[
                          { entity: 'Emirates_Group', amt: '+€120,400', status: 'Reconciled', date: 'TODAY' },
                          { entity: 'Kuwait_Petroleum', amt: '+€88,000', status: 'Predicted', date: 'JAN 04' },
                          { entity: 'Standard_Chartered', amt: '-€45,000', status: 'Wash_Match', date: 'JAN 08' },
                        ].map((tx, i) => (
                          <div key={i} className="p-5 flex items-center justify-between hover:bg-white/5 transition-colors group cursor-pointer text-left">
                            <div className="flex items-center gap-4">
                              <div className="h-8 w-8 rounded bg-white/5 border border-white/10 flex items-center justify-center text-[10px] font-black group-hover:bg-blue-600 group-hover:border-blue-500 transition-all">{tx.entity[0]}</div>
                              <div>
                                <div className="text-xs font-black text-white">{tx.entity}</div>
                                <div className="text-[9px] font-bold text-slate-500 uppercase tracking-widest">{tx.date}</div>
                              </div>
                            </div>
                            <div className="text-right">
                              <div className={`text-xs font-black ${tx.amt.startsWith('+') ? 'text-emerald-500' : 'text-white'}`}>{tx.amt}</div>
                              <div className="text-[9px] font-black uppercase tracking-widest text-slate-500">{tx.status}</div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>

                  {/* Right: Action Playbook */}
                  <div className="col-span-4 space-y-6 text-left">
                    <h4 className="text-[10px] font-black uppercase tracking-[0.3em] text-blue-400">Action_Playbook</h4>
                    <div className="space-y-4">
                      {[
                        { title: 'Accelerate_SaaS_Run', roi: '12.4x' },
                        { title: 'Delay_Vendor_Net30', roi: '4.2x' },
                        { title: 'FX_Hedge_EURUSD', roi: 'Sign-off' },
                      ].map((act, i) => (
                        <div key={i} className="p-5 rounded-2xl bg-[#1A1A1C] border border-white/5 hover:border-blue-500/50 transition-all cursor-pointer group">
                          <div className="flex justify-between items-center">
                            <span className="text-[11px] font-black text-white tracking-tight">{act.title}</span>
                            <ChevronRight className="h-3 w-3 text-slate-600 group-hover:text-blue-400 transition-colors" />
                          </div>
                          <div className="text-[9px] font-black uppercase tracking-[0.2em] text-blue-500 mt-2">ROI: {act.roi}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* The "Brutal" Sections: No more standard cards */}
      <section className="px-8 py-64 max-w-[1400px] mx-auto border-t border-white/5 relative z-10 text-left">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-24">
          <div className="lg:col-span-5 space-y-16">
            <div className="space-y-6">
              <h2 className="text-6xl font-black tracking-[-0.05em] leading-[0.9] text-white">THE <br /><span className="text-white/20 italic font-medium underline underline-offset-8 decoration-blue-500/50">SPREADSHEET</span> <br /> GAP.</h2>
              <p className="text-xl text-slate-400 font-medium leading-relaxed">
                Most finance teams are chasing "theoretical cash." Numbers that exist in a model but don't exist in the bank. Gitto closes the deficit.
              </p>
            </div>
            
            <div className="space-y-12">
              {[
                { title: 'Behavioral_Bias', desc: 'Real life averages 14+ days of unmodeled delay. We find them before they hit your runway.' },
                { title: 'Bank_Truth', desc: 'If the bank doesn\'t see the receipt, it isn\'t truth. Deterministic matching for CFO sign-off.' },
                { title: 'Group_Normalization', desc: 'Consolidated FX and Intercompany washes that don\'t break at scale.' },
              ].map((gap, i) => (
                <div key={i} className="space-y-2 border-l-2 border-white/5 pl-8 hover:border-blue-500 transition-all">
                  <h4 className="text-[11px] font-black uppercase tracking-[0.3em] text-white">{gap.title}</h4>
                  <p className="text-sm text-slate-500 font-medium leading-relaxed">{gap.desc}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="lg:col-span-7 flex items-center justify-center relative">
            <div className="absolute inset-0 bg-blue-600/10 blur-[150px] animate-pulse rounded-full" />
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

      {/* The 6 Pillars - Abstracted Grid */}
      <section className="px-8 py-64 bg-white text-black relative overflow-hidden z-10 text-left">
        <div className="max-w-[1400px] mx-auto grid grid-cols-1 lg:grid-cols-3 gap-px bg-black/10 border border-black/10">
          {[
            { t: 'BANK_TRUTH', d: 'Ingest transactions and reconcile receipts against invoices for a definitive closing cash number.' },
            { t: 'BEHAVIORAL_BIAS', d: 'Spreadsheets use due dates; real life doesn\'t. We learn customer payment habits to predict reality.' },
            { t: 'RAG_INSIGHTS', d: 'Ask anything. Get answers grounded in specific retrieved invoice evidence with citations.' },
            { t: '13_WEEK_GRID', d: 'The single source of truth for the weekly cash meeting. Interactive drill-downs from W1 to W13.' },
            { t: 'FX_NORMALIZATION', d: 'Snapshot-locked rates and intercompany wash detection. Consolidated group visibility.' },
            { t: 'GOVERNANCE', d: 'Enterprise-ready audit logs for every scenario change, lever shift, and CFO sign-off.' },
          ].map((p, i) => (
            <div key={i} className="bg-white p-16 space-y-10 group hover:bg-[#F9F9FB] transition-all">
              <span className="text-[10px] font-black text-slate-300 tracking-[0.4em]">PILLAR_0{i+1}</span>
              <div className="space-y-4">
                <h3 className="text-3xl font-black tracking-tighter leading-none italic uppercase">{p.t}</h3>
                <p className="text-lg text-slate-500 font-bold leading-relaxed">{p.d}</p>
              </div>
            </div>
          ))}
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
              <div className="h-6 w-6 rounded bg-white flex items-center justify-center text-black font-black text-[10px]">G</div>
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
        @keyframes reverse-spin {
          from { transform: rotate(360deg); }
          to { transform: rotate(0deg); }
        }
        .animate-reverse-spin {
          animation: reverse-spin 10s linear infinite;
        }
      `}</style>
    </div>
  );
}
