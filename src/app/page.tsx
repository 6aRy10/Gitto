'use client';

import { useState } from 'react';
import Link from "next/link";
import { 
  ArrowRight, CheckCircle2, Shield, BarChart3, TrendingUp, AlertCircle, 
  Landmark, Users, Search, Bell, Calendar, ChevronRight, MessageSquare,
  Lock, Zap, Database, Globe, Briefcase, Plus, Sparkles, Filter, 
  FileText, ArrowDownRight, ArrowUpRight
} from "lucide-react";
import { Button } from "../components/ui/button";
import { Card, CardContent } from "../components/ui/card";

export default function Landing() {
  return (
    <div className="min-h-screen bg-white text-slate-900 font-sans selection:bg-blue-100 antialiased overflow-x-hidden">
      {/* Navigation */}
      <nav className="fixed top-0 left-0 right-0 z-50 bg-white/80 backdrop-blur-xl border-b border-slate-100">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-10">
            <Link href="/" className="flex items-center gap-2">
              <div className="h-7 w-7 rounded-lg bg-slate-900 flex items-center justify-center text-white font-black text-sm">G</div>
              <span className="font-bold text-xl tracking-tighter text-slate-900">gitto</span>
            </Link>
            <div className="hidden md:flex items-center gap-8 text-[14px] font-medium text-slate-500">
              <Link href="/about" className="hover:text-slate-900 transition-colors">Why Gitto</Link>
              <button className="hover:text-slate-900 transition-colors">Features</button>
              <button className="hover:text-slate-900 transition-colors">CFO Desk</button>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <Link href="/app" className="text-[14px] font-medium text-slate-900 hover:text-slate-600 transition-colors px-4">Sign In</Link>
            <Link href="/app">
              <Button className="bg-slate-900 text-white hover:bg-slate-800 rounded-full px-6 h-10 text-[14px] font-bold">
                Book a Demo
              </Button>
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="relative pt-40 pb-20 px-6">
        <div className="max-w-5xl mx-auto text-center space-y-8">
          <div className="inline-flex items-center px-4 py-1.5 rounded-full bg-blue-50 border border-blue-100 text-[13px] font-bold text-blue-600">
            Enterprise Cash Intelligence
          </div>
          <h1 className="text-[56px] md:text-[84px] font-bold tracking-tight text-slate-900 leading-[1.05]">
            Cash truth anchored <br /> 
            <span className="text-slate-400 font-medium italic">in bank reality.</span>
          </h1>
          <p className="text-[20px] text-slate-500 font-medium max-w-3xl mx-auto leading-relaxed">
            Theoretical forecasts are just modeled numbers. Gitto ingests bank transactions, reconciles receipts, and learns payment behaviors to build an immutable, audit-ready cash ledger.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-4">
            <Link href="/app">
              <Button className="bg-slate-900 text-white hover:bg-slate-800 rounded-full px-10 h-14 text-[16px] font-bold shadow-xl shadow-slate-900/10 transition-all hover:scale-[1.02]">
                Book a Demo
              </Button>
            </Link>
            <Link href="/about">
              <Button variant="outline" className="border-slate-200 text-slate-900 rounded-full px-10 h-14 text-[16px] font-bold hover:bg-slate-50">
                How it works
              </Button>
            </Link>
          </div>
        </div>
      </section>

      {/* Dashboard Mockup (Gitto Core) */}
      <section className="px-6 py-20 bg-slate-50/50">
        <div className="max-w-6xl mx-auto">
          <div className="bg-white rounded-[32px] border border-slate-200 shadow-2xl overflow-hidden flex flex-col md:flex-row h-[700px]">
            {/* Sidebar Mockup */}
            <div className="w-64 border-r border-slate-100 p-6 hidden md:block space-y-8 bg-slate-50/30">
              <div className="space-y-4">
                <div className="px-2 text-[10px] font-black uppercase tracking-widest text-slate-400">Command Desks</div>
                <div className="space-y-1">
                  {[
                    { label: 'CFO Overview', icon: LayoutDashboard },
                    { label: '13-Week View', icon: Calendar },
                    { label: 'Banking (Truth)', icon: Landmark },
                    { label: 'Analyst (RAG)', icon: Search },
                    { label: 'Operations', icon: Briefcase },
                  ].map((item, i) => (
                    <div key={i} className={`h-10 w-full rounded-xl flex items-center px-3 gap-3 ${i === 1 ? 'bg-white shadow-sm border border-slate-100' : 'text-slate-400'}`}>
                      <item.icon className={`h-4 w-4 ${i === 1 ? 'text-slate-900' : 'text-slate-300'}`} />
                      <span className={`text-[12px] font-bold ${i === 1 ? 'text-slate-900' : 'text-slate-400'}`}>{item.label}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Main Content Mockup */}
            <div className="flex-1 p-8 overflow-y-auto space-y-10 text-left">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-xl font-bold text-slate-900">13-Week CFO Grid</h2>
                  <p className="text-sm text-slate-400 font-medium tracking-tight uppercase">Snapshot: Dec 2025 · Group Consolidated</p>
                </div>
                <div className="flex items-center gap-3">
                  <div className="px-3 py-1.5 bg-emerald-50 rounded-full flex items-center gap-2">
                    <div className="h-2 w-2 bg-emerald-500 rounded-full" />
                    <span className="text-[10px] font-black text-emerald-600 uppercase tracking-widest">Bank Sync: Live</span>
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                {/* 13-Week Grid Sample */}
                <Card className="rounded-3xl border border-slate-100 shadow-sm overflow-hidden">
                  <CardContent className="p-6 space-y-6">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <BarChart3 className="h-4 w-4 text-slate-900" />
                        <span className="font-bold text-[15px]">Closing Cash Runway</span>
                      </div>
                      <span className="text-[11px] font-bold text-slate-400 uppercase tracking-widest">W1 - W13</span>
                    </div>
                    <div className="space-y-4">
                      {[
                        { week: 'W1 (Dec 28)', cash: '€2.4M', status: 'Reconciled', color: 'text-emerald-500' },
                        { week: 'W2 (Jan 04)', cash: '€2.1M', status: 'Predicted', color: 'text-blue-500' },
                        { week: 'W3 (Jan 11)', cash: '€3.2M', status: 'Bulk Inflow', color: 'text-blue-500' },
                      ].map((item, i) => (
                        <div key={i} className="flex items-center justify-between p-4 rounded-2xl border border-slate-50 hover:bg-slate-50 transition-colors">
                          <div className="space-y-1">
                            <span className="text-[13px] font-bold text-slate-900">{item.week}</span>
                            <div className={`text-[10px] font-black uppercase tracking-widest ${item.color}`}>{item.status}</div>
                          </div>
                          <div className="text-lg font-black text-slate-900">{item.cash}</div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>

                {/* Grounded Evidence (RAG) Card */}
                <Card className="rounded-3xl border border-slate-100 shadow-sm overflow-hidden">
                  <CardContent className="p-6 space-y-6">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Sparkles className="h-4 w-4 text-indigo-600 fill-indigo-100" />
                        <span className="font-bold text-[15px]">Analyst Insights</span>
                      </div>
                      <span className="text-[10px] font-bold text-indigo-600 uppercase tracking-widest">Grounded Evidence</span>
                    </div>
                    <div className="space-y-4">
                      <div className="p-4 rounded-2xl bg-indigo-50/50 border border-indigo-100 space-y-3">
                        <p className="text-[13px] font-bold text-indigo-900 leading-relaxed">
                          "Shortfall in W2 is driven by a €430k delay from Emirates Group. Retrieval shows they have missed the last 3 Thursday payment runs."
                        </p>
                        <div className="pt-2 border-t border-indigo-100 flex items-center gap-3">
                          <div className="px-2 py-0.5 rounded-lg bg-white text-[9px] font-black text-indigo-600 border border-indigo-100 uppercase tracking-widest">Inv #88432</div>
                          <div className="px-2 py-0.5 rounded-lg bg-white text-[9px] font-black text-indigo-600 border border-indigo-100 uppercase tracking-widest">MAE: 1.2d</div>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* The 6 Pillars of Gitto */}
      <section className="px-6 py-32 max-w-7xl mx-auto space-y-20">
        <div className="text-center space-y-4">
          <h2 className="text-[42px] font-bold tracking-tight">The 6 Pillars of Cash Truth</h2>
          <p className="text-slate-500 text-lg font-medium max-w-2xl mx-auto">Moving finance teams from "theoretical" spreadsheets to bank-anchored intelligence.</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
          {[
            { 
              title: "Bank-Truth Layer", 
              desc: "Don't guess bank balances. We ingest transactions and reconcile cash receipts against invoices for a definitive closing cash number.",
              icon: <Landmark className="h-5 w-5" /> 
            },
            { 
              title: "Behavioral Forecasting", 
              desc: "Spreadsheets use due dates; real life doesn't. We learn customer payment habits to predict when cash actually lands.",
              icon: <Zap className="h-5 w-5" /> 
            },
            { 
              title: "Grounded RAG Insights", 
              desc: "AI answers grounded in specific retrieved invoice evidence. Ask 'Why is there a shortfall?' and get the exact citations.",
              icon: <Sparkles className="h-5 w-5" /> 
            },
            { 
              title: "13-Week Command Center", 
              desc: "The single source of truth for the weekly cash meeting. Interactive grid with drill-downs from W1 to W13.",
              icon: <BarChart3 className="h-5 w-5" /> 
            },
            { 
              title: "Multi-Currency/Entity", 
              desc: "Snapshot-locked FX rates and intercompany wash detection. Consolidated visibility that doesn't break at the group level.",
              icon: <Globe className="h-5 w-5" /> 
            },
            { 
              title: "Audit-Ready Controls", 
              desc: "Enterprise governance with full audit logs for everylever change, scenario override, and CFO sign-off.",
              icon: <Lock className="h-5 w-5" /> 
            }
          ].map((feature, i) => (
            <Card key={i} className="border-0 shadow-none hover:bg-slate-50 transition-colors p-8 space-y-4 rounded-[24px]">
              <div className="h-12 w-12 rounded-2xl bg-white border border-slate-100 flex items-center justify-center text-slate-900 shadow-sm">
                {feature.icon}
              </div>
              <div className="space-y-2 text-left">
                <h3 className="font-bold text-[18px] text-slate-900">{feature.title}</h3>
                <p className="text-slate-500 text-[15px] font-medium leading-relaxed">
                  {feature.desc}
                </p>
              </div>
            </Card>
          ))}
        </div>
      </section>

      {/* Problem Section: Theoretical vs Reality */}
      <section className="px-6 py-32 bg-slate-900 text-white">
        <div className="max-w-5xl mx-auto grid grid-cols-1 md:grid-cols-2 gap-20 items-center">
          <div className="space-y-8 text-left">
            <h2 className="text-[42px] font-bold leading-tight">CFOs can't bet payroll on a guess.</h2>
            <div className="space-y-6">
              <div className="flex gap-4">
                <div className="h-10 w-10 rounded-xl bg-red-500/10 border border-red-500/20 flex items-center justify-center shrink-0">
                  <ArrowDownRight className="h-5 w-5 text-red-400" />
                </div>
                <div>
                  <h4 className="font-bold text-[17px]">The Spreadsheet Gap</h4>
                  <p className="text-slate-400 text-sm font-medium">Traditional models assume customers pay on time. Real life averages 14+ days of unmodeled delay.</p>
                </div>
              </div>
              <div className="flex gap-4">
                <div className="h-10 w-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center shrink-0">
                  <CheckCircle2 className="h-5 w-5 text-emerald-400" />
                </div>
                <div>
                  <h4 className="font-bold text-[17px]">The Gitto Anchor</h4>
                  <p className="text-slate-400 text-sm font-medium">We tie every prediction back to actual bank transactions. If the bank doesn't see it, it's not cash truth.</p>
                </div>
              </div>
            </div>
          </div>
          <div className="bg-white/5 rounded-[40px] p-12 border border-white/10 space-y-8">
            <div className="text-[11px] font-black uppercase tracking-[0.2em] text-blue-400">Explainability Engine</div>
            <div className="space-y-4 text-left">
              {[
                { label: 'Predicted Landing', val: 'Jan 14', color: 'text-white' },
                { label: 'Behavioral Bias', val: '+9.2 days', color: 'text-red-400' },
                { label: 'Bank Match Found', val: 'Yes', color: 'text-emerald-400' },
              ].map((row, i) => (
                <div key={i} className="flex justify-between border-b border-white/5 pb-4">
                  <span className="text-sm font-bold text-slate-500">{row.label}</span>
                  <span className={`text-sm font-black ${row.color}`}>{row.val}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Industries: Real Enterprise Use Cases */}
      <section className="px-6 py-32 max-w-7xl mx-auto space-y-20">
        <div className="text-center space-y-4 text-left">
          <h2 className="text-[42px] font-bold tracking-tight">Built for Enterprise Finance</h2>
          <p className="text-slate-500 text-lg font-medium">Gitto is trusted by teams with complex group structures and global liquidity needs.</p>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            'High-Growth SaaS', 'Global Manufacturing', 'Venture Portfolios', 'Retail & Consumer',
            'Energy & Infra', 'Supply Chain Tech', 'Fintech & Lending', 'Professional Services'
          ].map((industry, i) => (
            <div key={i} className="p-10 rounded-[32px] bg-slate-50 flex flex-col items-center justify-center text-center space-y-4 hover:bg-white hover:shadow-xl hover:-translate-y-1 transition-all cursor-pointer border border-transparent hover:border-slate-100">
              <span className="font-bold text-[17px] text-slate-900">{industry}</span>
            </div>
          ))}
        </div>
      </section>

      {/* Final CTA */}
      <section className="px-6 py-32 text-center bg-slate-50 border-t border-slate-100">
        <div className="max-w-3xl mx-auto space-y-10">
          <h2 className="text-[48px] md:text-[64px] font-bold tracking-tight leading-tight">Stop Guessing. <br /> Start Knowing.</h2>
          <p className="text-xl text-slate-500 font-bold italic">Move to the behavior-based cash command center.</p>
          <Link href="/app">
            <Button className="bg-slate-900 text-white hover:bg-slate-800 rounded-full px-16 h-18 text-xl font-bold shadow-2xl shadow-slate-900/20">
              Book a Demo
            </Button>
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="px-6 py-20 bg-white border-t border-slate-100">
        <div className="max-w-7xl mx-auto grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-16">
          <div className="space-y-8 text-left">
            <Link href="/" className="flex items-center gap-2">
              <div className="h-7 w-7 rounded-lg bg-slate-900 flex items-center justify-center text-white font-black text-sm">G</div>
              <span className="font-bold text-xl tracking-tighter text-slate-900">gitto</span>
            </Link>
            <p className="text-slate-400 font-bold text-sm leading-relaxed">Behavior-based forecasting meets <br /> bank-truth reality.</p>
            <p className="text-slate-400 font-bold text-sm">© 2025 Gitto Inc.</p>
          </div>
          <div className="grid grid-cols-2 gap-8 lg:col-span-3">
            <div className="space-y-6 text-left">
              <h4 className="font-bold text-sm text-slate-900 uppercase tracking-widest">Command Desks</h4>
              <ul className="space-y-4 text-sm text-slate-400 font-bold">
                <li className="hover:text-slate-900 cursor-pointer">CFO 13-Week Grid</li>
                <li className="hover:text-slate-900 cursor-pointer">Banking Truth Layer</li>
                <li className="hover:text-slate-900 cursor-pointer">Analyst RAG Insights</li>
              </ul>
            </div>
            <div className="space-y-6 text-left">
              <h4 className="font-bold text-sm text-slate-900 uppercase tracking-widest">Enterprise</h4>
              <ul className="space-y-4 text-sm text-slate-400 font-bold">
                <li className="hover:text-slate-900 cursor-pointer">Multi-Entity / FX</li>
                <li className="hover:text-slate-900 cursor-pointer">Audit & Governance</li>
                <li className="hover:text-slate-900 cursor-pointer">Privacy Policy</li>
              </ul>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}

const LayoutDashboard = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect width="7" height="9" x="3" y="3" rx="1" /><rect width="7" height="5" x="14" y="3" rx="1" /><rect width="7" height="9" x="14" y="12" rx="1" /><rect width="7" height="5" x="3" y="16" rx="1" />
  </svg>
);
