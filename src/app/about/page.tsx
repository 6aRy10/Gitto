'use client';

import Link from "next/link";
import { ArrowLeft, CheckCircle2, Shield, BarChart3, TrendingUp, Zap, Target, Users, Landmark, ChevronRight, Clock, Sparkles } from "lucide-react";
import { Button } from "../../components/ui/button";
import { Card } from "../../components/ui/card";

export default function AboutPage() {
  return (
    <div className="min-h-screen bg-white text-slate-900 font-sans selection:bg-blue-100 antialiased flex flex-col overflow-x-hidden">
      {/* Navigation */}
      <nav className="fixed top-0 left-0 right-0 z-50 px-8 py-6">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2 group bg-white/50 backdrop-blur-xl px-4 py-2 rounded-2xl border border-white/40 shadow-sm">
            <ArrowLeft className="h-4 w-4 text-slate-400 group-hover:text-slate-900 transition-transform group-hover:-translate-x-1" />
            <div className="h-6 w-6 rounded-sm bg-slate-900 flex items-center justify-center text-white font-black text-xs">G</div>
            <span className="font-bold text-xl tracking-tighter text-slate-900">gitto</span>
          </Link>
          <div className="flex gap-4">
            <Link href="/contact">
              <Button variant="ghost" className="text-[13px] font-bold text-slate-600 hover:text-slate-900 rounded-xl px-6 h-11">
                Contact Sales
              </Button>
            </Link>
            <Link href="/app">
              <Button className="bg-slate-900 text-white hover:bg-slate-800 rounded-xl px-8 h-11 text-[13px] font-black tracking-tight shadow-xl shadow-slate-900/10 transition-all hover:scale-[1.02]">
                Get Started
              </Button>
            </Link>
          </div>
        </div>
      </nav>

      <main className="flex-1">
        {/* Modern Hero with Background Effect */}
        <section className="relative pt-48 pb-32 px-8 overflow-hidden">
          {/* Vibrant Background Bars (Gitto Theme) */}
          <div className="absolute inset-0 z-0 flex w-full h-full overflow-hidden pointer-events-none opacity-[0.15]">
            {[...Array(40)].map((_, i) => (
              <div 
                key={i} 
                className="h-full flex-1" 
                style={{ 
                  backgroundColor: i % 2 === 0 ? '#3b82f6' : '#6366f1',
                  opacity: Math.random() * 0.5
                }} 
              />
            ))}
            <div 
              className="absolute inset-0 opacity-[0.8] pointer-events-none" 
              style={{ 
                backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E")`,
                mixBlendMode: 'overlay'
              }} 
            />
            <div className="absolute inset-0 bg-gradient-to-b from-transparent to-white" />
          </div>

          <div className="max-w-4xl mx-auto text-center space-y-10 relative z-10">
            <div className="inline-flex items-center px-4 py-1.5 rounded-full bg-blue-50 text-[11px] font-black uppercase tracking-[0.2em] text-blue-600 border border-blue-100/50 shadow-sm">
              Gitto Intelligence
            </div>
            <h1 className="text-[64px] md:text-[96px] font-black tracking-[-0.06em] text-slate-900 leading-[0.88]">
              Cash truth <br /> 
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-indigo-600">anchored in reality.</span>
            </h1>
            <p className="text-[22px] text-slate-500 font-semibold max-w-2xl mx-auto leading-relaxed tracking-tight">
              We bridge the gap between theoretical accounting and actual liquidity, turning behavioral evidence into an immutable cash ledger.
            </p>
          </div>
        </section>

        {/* Systemic Flow: Problem -> Solution -> Benefits */}
        <div className="max-w-6xl mx-auto px-8 py-24 space-y-48">
          
          {/* Section 1: The Problem (High Contrast) */}
          <section className="grid grid-cols-1 lg:grid-cols-2 gap-24 items-center">
            <div className="space-y-10 order-2 lg:order-1">
              <div className="space-y-4">
                <div className="h-1 w-12 bg-red-500 rounded-full" />
                <h2 className="text-[48px] font-black tracking-tighter text-slate-900 leading-tight">The "Theoretical" Forecast Gap.</h2>
              </div>
              <div className="space-y-6">
                <p className="text-xl text-slate-500 font-medium leading-relaxed">
                  Spreadsheets assume customers pay on due dates. Real life does not.
                </p>
                <p className="text-xl text-slate-900 font-bold leading-relaxed">
                  When you ignore payment behavior and bank reality, your forecast becomes a guess. CFOs shouldn't bet payroll on a guess.
                </p>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 pt-4">
                {[
                  { title: "The 'Due Date' Trap", desc: "Modeling based on theoretical terms instead of actual customer behavior.", icon: <Clock className="h-4 w-4 text-red-600" /> },
                  { title: "Bank-Truth Gap", desc: "No deterministic link between receipts and open invoices.", icon: <Landmark className="h-4 w-4 text-red-600" /> },
                ].map((item, i) => (
                  <div key={i} className="p-6 rounded-3xl bg-slate-50 border border-slate-100/50 space-y-3">
                    <div className="h-10 w-10 rounded-xl bg-red-50 flex items-center justify-center">
                      {item.icon}
                    </div>
                    <h4 className="font-black text-slate-900 text-sm tracking-tight">{item.title}</h4>
                    <p className="text-xs text-slate-500 font-medium leading-relaxed">{item.desc}</p>
                  </div>
                ))}
              </div>
            </div>
            <div className="relative order-1 lg:order-2">
              <div className="aspect-[4/3] bg-slate-50 rounded-[48px] relative overflow-hidden shadow-inner flex items-center justify-center p-12">
                <div className="absolute inset-0 bg-gradient-to-tr from-blue-100/20 to-indigo-100/20 opacity-50" />
                
                {/* Visualizing "Chaos to Order" - much more polished than the broken excel */}
                <div className="relative z-10 w-full bg-white rounded-[32px] shadow-2xl border border-slate-100 p-8 space-y-6">
                  <div className="flex items-center justify-between mb-2">
                    <div className="h-3 w-32 bg-slate-100 rounded-full" />
                    <div className="h-3 w-12 bg-blue-100 rounded-full" />
                  </div>
                  
                  <div className="space-y-4">
                    {[1,2,3].map(i => (
                      <div key={i} className="flex items-center gap-4">
                        <div className="h-8 w-8 rounded-lg bg-slate-50 border border-slate-100" />
                        <div className="flex-1 space-y-2">
                          <div className="h-2 w-full bg-slate-50 rounded-full" />
                          <div className={`h-2 bg-blue-500 rounded-full transition-all duration-1000 delay-${i*200}`} style={{ width: `${30 + i*20}%` }} />
                        </div>
                      </div>
                    ))}
                  </div>

                  <div className="pt-4 border-t border-slate-50 flex justify-between items-center">
                    <div className="text-[10px] font-black uppercase tracking-widest text-slate-400">Behavioral Accuracy</div>
                    <div className="text-xl font-black text-blue-600">98.2%</div>
                  </div>
                </div>

                {/* Decorative floating elements */}
                <div className="absolute top-10 right-10 h-20 w-20 rounded-full bg-blue-400/10 blur-2xl animate-pulse" />
                <div className="absolute bottom-10 left-10 h-32 w-32 rounded-full bg-indigo-400/10 blur-3xl" />
              </div>
            </div>
          </section>

          {/* Section 2: The Solution (Integrated White/Slate Style) */}
          <section className="space-y-20 py-12">
            <div className="text-center space-y-6 max-w-3xl mx-auto">
              <div className="inline-flex items-center px-4 py-1.5 rounded-full bg-blue-50 text-[10px] font-black uppercase tracking-[0.3em] text-blue-600 border border-blue-100">
                The Gitto Trinity
              </div>
              <h2 className="text-[48px] md:text-[72px] font-black tracking-tighter text-slate-900 leading-[0.95]">
                A Single Source <br /> of Cash Reality.
              </h2>
              <p className="text-xl text-slate-500 font-medium">
                We've combined behavioral intelligence with deterministic bank-truth to give you an audit-ready command center.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
              {[
                { 
                  icon: <Landmark className="h-6 w-6" />, 
                  title: "Banking Desk", 
                  desc: "The anchor of cash reality. Treasury teams manage an immutable ledger with deterministic invoice matching.",
                  accent: "text-emerald-600", bg: "bg-emerald-50", border: "border-emerald-100/50"
                },
                { 
                  icon: <BarChart3 className="h-6 w-6" />, 
                  title: "Analyst Desk", 
                  desc: "The brain of FP&A. Model behavioral segment shifts and run complex scenarios with 'Top Movers' shift detection.",
                  accent: "text-blue-600", bg: "bg-blue-50", border: "border-blue-100/50"
                },
                { 
                  icon: <Users className="h-6 w-6" />, 
                  title: "Operations Desk", 
                  desc: "The hands of AR. Protect liquidity by ranking collections effort based on impact week and lateness risk.",
                  accent: "text-amber-600", bg: "bg-amber-50", border: "border-amber-100/50"
                }
              ].map((item, i) => (
                <div key={i} className={`p-10 rounded-[40px] bg-white border ${item.border} shadow-sm hover:shadow-xl hover:-translate-y-1 transition-all group text-left space-y-6`}>
                  <div className={`h-14 w-14 rounded-2xl ${item.bg} ${item.accent} flex items-center justify-center group-hover:scale-110 transition-transform`}>
                    {item.icon}
                  </div>
                  <div className="space-y-3">
                    <h3 className="text-2xl font-black text-slate-900 tracking-tight">{item.title}</h3>
                    <p className="text-slate-500 font-medium leading-relaxed">{item.desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* Section 3: The Benefits (Clean & Systematic) */}
          <section className="space-y-24">
            <div className="flex flex-col md:flex-row justify-between items-end gap-12 border-b border-slate-100 pb-16">
              <div className="space-y-4 max-w-xl">
                <h2 className="text-[56px] font-black tracking-tighter text-slate-900 leading-[0.9]">Quantified <br /> impact.</h2>
                <p className="text-xl text-slate-500 font-medium">Why the world's best finance teams choose Gitto.</p>
              </div>
              <div className="flex gap-4">
                <div className="px-6 py-3 rounded-2xl bg-slate-50 border border-slate-100 text-center">
                  <div className="text-2xl font-black text-slate-900">95%+</div>
                  <div className="text-[10px] font-black uppercase tracking-widest text-slate-400">Accuracy</div>
                </div>
                <div className="px-6 py-3 rounded-2xl bg-slate-50 border border-slate-100 text-center">
                  <div className="text-2xl font-black text-slate-900">40h+</div>
                  <div className="text-[10px] font-black uppercase tracking-widest text-slate-400">Saved/Mo</div>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-x-20 gap-y-24">
              {[
                { 
                  label: "Strategic Value", 
                  title: "13-Week Command Center", 
                  desc: "The single brain for CFOs. Survive the weekly cash meeting with evidence for every number, from W1 to W13.",
                  icon: <Target className="h-6 w-6 text-blue-600" />
                },
                { 
                  label: "Intelligence", 
                  title: "Grounded RAG Insights", 
                  desc: "Our AI Analyst retrieves specific invoice evidence for every answer. Zero hallucinations, 100% data-aware citations.",
                  icon: <Sparkles className="h-6 w-6 text-indigo-600" />
                },
                { 
                  label: "Accuracy", 
                  title: "Behavioral Modeling", 
                  desc: "We learn how customers actually pay by segment (Country, Customer, Terms) to predict the 'theoretical' gap.",
                  icon: <BarChart3 className="h-6 w-6 text-emerald-600" />
                },
                { 
                  label: "Governance", 
                  title: "Multi-Entity Mastery", 
                  desc: "Manage group structures with intercompany wash detection and snapshot-locked FX normalization for accuracy.",
                  icon: <Shield className="h-6 w-6 text-blue-600" />
                }
              ].map((item, i) => (
                <div key={i} className="group space-y-6">
                  <div className="flex items-center gap-4">
                    <div className="h-12 w-12 rounded-2xl bg-slate-50 border border-slate-100 flex items-center justify-center group-hover:bg-white group-hover:shadow-lg transition-all">
                      {item.icon}
                    </div>
                    <div className="text-[11px] font-black uppercase tracking-[0.2em] text-slate-400">{item.label}</div>
                  </div>
                  <div className="space-y-3">
                    <h3 className="text-3xl font-black tracking-tight text-slate-900">{item.title}</h3>
                    <p className="text-lg text-slate-500 font-medium leading-relaxed">{item.desc}</p>
                  </div>
                  <div className="flex items-center gap-2 text-blue-600 font-black text-xs uppercase tracking-widest cursor-pointer opacity-0 group-hover:opacity-100 transition-opacity">
                    Learn more <ChevronRight className="h-3 w-3" />
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* Final CTA */}
          <section className="text-center pt-20">
            <div className="bg-blue-600 rounded-[64px] p-16 md:p-32 space-y-12 relative overflow-hidden shadow-2xl shadow-blue-500/20">
              <div className="absolute inset-0 bg-[url('https://www.transparenttextures.com/patterns/cubes.png')] opacity-10" />
              <div className="relative z-10 space-y-6">
                <h2 className="text-[48px] md:text-[72px] font-black tracking-tighter text-white leading-[0.9]">
                  Stop guessing. <br /> Start knowing.
                </h2>
                <p className="text-xl text-blue-100 font-medium max-w-xl mx-auto opacity-80">
                  Join the companies moving from spreadsheet-based guessing to behavior-based intelligence.
                </p>
              </div>
              <div className="relative z-10">
                <Link href="/app">
                  <Button className="bg-white text-blue-600 hover:bg-blue-50 rounded-[28px] px-16 h-20 text-2xl font-black shadow-3xl transition-all hover:scale-[1.05] active:scale-[0.95]">
                    Get Started Now
                  </Button>
                </Link>
              </div>
            </div>
          </section>

        </div>
      </main>

      <footer className="border-t border-slate-100 py-20 px-8 bg-slate-50/50">
        <div className="max-w-6xl mx-auto flex flex-col md:flex-row justify-between items-start gap-16">
          <div className="space-y-6 max-w-xs">
            <div className="flex items-center gap-2">
              <div className="h-6 w-6 rounded-sm bg-slate-900 flex items-center justify-center text-white font-black text-xs">G</div>
              <span className="font-bold text-2xl tracking-tighter text-slate-900">gitto</span>
            </div>
            <p className="text-[14px] font-bold text-slate-400 leading-relaxed tracking-tight">
              We build winning finance teams for startups, mid-market, and enterprise companies.
            </p>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-20">
            {[
              { label: "Product", links: ["Features", "Pricing", "Security"] },
              { label: "Company", links: ["About", "Careers", "Contact"] },
              { label: "Legal", links: ["Privacy", "Terms", "SOC2"] }
            ].map((col, i) => (
              <div key={i} className="space-y-6 text-left">
                <h4 className="text-[11px] font-black uppercase tracking-[0.2em] text-slate-900">{col.label}</h4>
                <ul className="space-y-4">
                  {col.links.map((link, j) => (
                    <li key={j} className="text-[14px] font-bold text-slate-400 hover:text-slate-900 transition-colors cursor-pointer text-left">
                      {link}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
        <div className="max-w-6xl mx-auto pt-20 flex justify-between items-center text-[10px] font-black uppercase tracking-[0.2em] text-slate-300">
          <span>©2025 Gitto. All rights reserved.</span>
          <div className="flex gap-8">
            <span className="hover:text-slate-900 transition-colors cursor-pointer">Twitter</span>
            <span className="hover:text-slate-900 transition-colors cursor-pointer">LinkedIn</span>
          </div>
        </div>
      </footer>
    </div>
  );
}

