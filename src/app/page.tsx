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
          <div className="lg:col-span-7 space-y-12">
            <div className="inline-flex items-center px-3 py-1 rounded-sm bg-white/5 border border-white/10 text-[10px] font-black uppercase tracking-[0.3em] text-blue-400">
              Deterministic Cash Intelligence
            </div>
            <h1 className="text-[80px] md:text-[140px] font-black tracking-[-0.07em] leading-[0.85] text-white">
              BANK <span className="text-white/20 italic font-medium">TRUTH</span> <br />
              IS THE ONLY <br />
              <span className="text-blue-500">REALITY.</span>
            </h1>
          </div>
          
          <div className="lg:col-span-5 relative flex items-center justify-center min-h-[500px]">
            {/* The Integration Engine - Animated Visual from User Query */}
            <div className="relative w-[450px] h-[450px] flex items-center justify-center">
              {/* Background Scanline Mesh */}
              <div className="absolute inset-0 opacity-20" style={{ backgroundImage: 'linear-gradient(45deg, #ffffff 1px, transparent 1px), linear-gradient(-45deg, #ffffff 1px, transparent 1px)', backgroundSize: '20px 20px' }} />
              
              {/* Central Logo Core */}
              <div className="relative z-20 w-32 h-32 bg-blue-600 rounded-[32px] flex items-center justify-center shadow-[0_0_80px_rgba(37,99,235,0.6)] animate-pulse-slow">
                <div className="text-white font-black text-6xl italic -skew-x-12">G</div>
                {/* Internal data pings */}
                <div className="absolute inset-0 rounded-[32px] border-2 border-white/20 animate-ping" />
              </div>

              {/* Orbiting Integrations - Layer 1 (Slow) */}
              <div className="absolute inset-0 animate-spin-slow">
                <div className="absolute top-0 left-1/2 -translate-x-1/2 -translate-y-1/2">
                   <div className="h-14 w-14 rounded-2xl bg-white/5 border border-white/10 backdrop-blur-xl flex items-center justify-center group hover:bg-white/10 transition-colors">
                     <Database className="h-6 w-6 text-slate-400" />
                     <div className="absolute -top-1 -right-1 h-2 w-2 bg-blue-500 rounded-full animate-ping" />
                   </div>
                </div>
                <div className="absolute bottom-0 left-1/2 -translate-x-1/2 translate-y-1/2">
                   <div className="h-14 w-14 rounded-2xl bg-white/5 border border-white/10 backdrop-blur-xl flex items-center justify-center">
                     <Globe className="h-6 w-6 text-slate-400" />
                   </div>
                </div>
              </div>

              {/* Orbiting Integrations - Layer 2 (Reverse, Faster) */}
              <div className="absolute inset-8 animate-reverse-spin-slow">
                <div className="absolute left-0 top-1/2 -translate-x-1/2 -translate-y-1/2">
                   <div className="h-12 w-12 rounded-2xl bg-[#f57c00]/10 border border-[#f57c00]/30 flex items-center justify-center shadow-[0_0_20px_rgba(245,124,0,0.2)]">
                     <div className="h-6 w-6 rounded bg-[#f57c00] flex items-center justify-center text-[8px] font-black">sf</div>
                   </div>
                </div>
                <div className="absolute right-0 top-1/2 translate-x-1/2 -translate-y-1/2">
                   <div className="h-12 w-12 rounded-2xl bg-blue-500/10 border border-blue-500/30 flex items-center justify-center shadow-[0_0_20px_rgba(59,130,246,0.2)]">
                     <CloudIcon className="h-6 w-6 text-blue-400" />
                   </div>
                </div>
              </div>

              {/* Connecting Data Particles */}
              <div className="absolute inset-0">
                {[...Array(6)].map((_, i) => (
                  <div 
                    key={i} 
                    className="absolute h-1 w-1 bg-blue-400 rounded-full animate-flow" 
                    style={{ 
                      top: '50%', 
                      left: '50%', 
                      '--tx': `${Math.cos(i * 60 * Math.PI / 180) * 200}px`,
                      '--ty': `${Math.sin(i * 60 * Math.PI / 180) * 200}px`,
                      animationDelay: `${i * 0.5}s`
                    } as any} 
                  />
                ))}
              </div>
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

      {/* Animated Workflows - "The Video Wall" */}
      <section className="px-8 py-64 max-w-[1400px] mx-auto border-t border-white/5 relative z-10 text-left">
        <div className="space-y-32">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-24 items-center">
            <div className="lg:col-span-5 space-y-12">
              <div className="inline-flex items-center px-3 py-1 rounded-sm bg-blue-500/10 border border-blue-500/20 text-[10px] font-black uppercase tracking-[0.3em] text-blue-400">
                Workflow_01 // Reconciliation
              </div>
              <h2 className="text-6xl font-black tracking-tighter leading-none text-white uppercase italic">
                AUTOMATED <br /> RECONCILIATION.
              </h2>
              <p className="text-xl text-slate-400 font-medium leading-relaxed">
                Watch as Gitto's core engine identifies incoming bank receipts and matches them against open ledger items in real-time. 
              </p>
              <div className="flex items-center gap-6">
                 <div className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
                 <span className="text-[10px] font-black uppercase tracking-[0.3em] text-emerald-500">Live Simulation Active</span>
              </div>
            </div>
            
            <div className="lg:col-span-7">
              <div className="bg-[#111113] rounded-[32px] border border-white/5 p-8 h-[450px] relative overflow-hidden shadow-2xl">
                {/* Background Grid */}
                <div className="absolute inset-0 opacity-10" style={{ backgroundImage: 'radial-gradient(circle, #ffffff 1px, transparent 1px)', backgroundSize: '30px 30px' }} />
                
                {/* Animated Stream */}
                <div className="relative h-full flex items-center justify-between px-12">
                  <div className="space-y-6 z-10">
                    <div className="text-[10px] font-black text-slate-600 uppercase tracking-widest mb-4">Inbound_Bank_Feed</div>
                    {[1,2,3].map(i => (
                      <div key={i} className={`h-16 w-64 bg-white/5 border border-white/10 rounded-2xl p-4 flex items-center justify-between animate-workflow-card`} style={{ animationDelay: `${i * 1.5}s` }}>
                        <div className="flex items-center gap-3">
                          <div className="h-8 w-8 rounded bg-emerald-500/20 flex items-center justify-center">
                            <Landmark className="h-4 w-4 text-emerald-500" />
                          </div>
                          <div className="space-y-0.5">
                            <div className="text-[10px] font-black text-white">€{12000 * i},000</div>
                            <div className="text-[8px] font-bold text-slate-500 uppercase">Incoming_Wire</div>
                          </div>
              </div>
            </div>
          ))}
        </div>

                  <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-0">
                    <Zap className="h-12 w-12 text-blue-500 animate-pulse opacity-50" />
                  </div>

                  <div className="space-y-6 z-10 text-right">
                    <div className="text-[10px] font-black text-slate-600 uppercase tracking-widest mb-4">Ledger_Truth</div>
                    {[1,2,3].map(i => (
                      <div key={i} className={`h-16 w-64 bg-blue-600/10 border border-blue-500/30 rounded-2xl p-4 flex items-center justify-between animate-workflow-card-reverse`} style={{ animationDelay: `${i * 1.5}s` }}>
                        <div className="flex items-center gap-3">
                          <div className="space-y-0.5">
                            <div className="text-[10px] font-black text-blue-400">#INV-990{i}</div>
                            <div className="text-[8px] font-bold text-slate-500 uppercase">Siemens_AG</div>
                          </div>
                          <div className="h-8 w-8 rounded bg-blue-500/20 flex items-center justify-center">
                            <CheckCircle2 className="h-4 w-4 text-blue-400" />
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-24 items-center">
            <div className="lg:col-span-7 order-2 lg:order-1">
              <div className="bg-[#111113] rounded-[32px] border border-white/5 p-12 h-[450px] relative overflow-hidden shadow-2xl flex flex-col justify-center">
                <div className="space-y-8 relative z-10">
                   <div className="flex items-center gap-4 bg-white/5 border border-white/10 p-6 rounded-3xl animate-fade-in-up">
                      <div className="h-10 w-10 rounded-full bg-blue-600 flex items-center justify-center text-white font-black">?</div>
                      <p className="text-xl font-medium italic text-slate-300">"Show me the invoices behind the W3 forecast shift."</p>
                   </div>
                   
                   <div className="flex gap-4 animate-fade-in-up" style={{ animationDelay: '1s' }}>
                      <div className="h-10 w-10 rounded-xl bg-blue-600 flex items-center justify-center text-white font-black text-sm italic shadow-lg shadow-blue-600/20">G</div>
                      <div className="flex-1 bg-blue-600/10 border border-blue-500/20 p-8 rounded-3xl space-y-4">
                        <div className="h-2 w-3/4 bg-blue-400/30 rounded-full animate-shimmer" />
                        <div className="h-2 w-1/2 bg-blue-400/30 rounded-full animate-shimmer" style={{ animationDelay: '0.2s' }} />
                        <div className="pt-4 flex gap-3">
                           <div className="px-3 py-1 bg-white/5 rounded-md text-[9px] font-black text-slate-400 uppercase tracking-widest border border-white/10">Ref: #INV-221</div>
                           <div className="px-3 py-1 bg-white/5 rounded-md text-[9px] font-black text-slate-400 uppercase tracking-widest border border-white/10">Bank_Balance: Verified</div>
                        </div>
                      </div>
                   </div>
                </div>
                {/* Floating particles */}
                <div className="absolute inset-0 z-0">
                   {[...Array(12)].map((_, i) => (
                     <div key={i} className="absolute h-1 w-1 bg-blue-500/20 rounded-full animate-float" style={{ left: `${Math.random() * 100}%`, top: `${Math.random() * 100}%`, animationDelay: `${Math.random() * 5}s` }} />
                   ))}
                </div>
              </div>
            </div>

            <div className="lg:col-span-5 space-y-12 order-1 lg:order-2">
              <div className="inline-flex items-center px-3 py-1 rounded-sm bg-blue-500/10 border border-blue-500/20 text-[10px] font-black uppercase tracking-[0.3em] text-blue-400">
                Workflow_02 // RAG_Analyst
              </div>
              <h2 className="text-6xl font-black tracking-tighter leading-none text-white uppercase italic">
                GROUNDED <br /> INSIGHTS.
              </h2>
              <p className="text-xl text-slate-400 font-medium leading-relaxed">
                Query your entire treasury history with natural language. Every answer is retrieved from specific bank truth and invoice reality.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* The "Brutal" Sections */}
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
