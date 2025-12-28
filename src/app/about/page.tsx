'use client';

import Link from "next/link";
import { 
  ArrowLeft, CheckCircle2, Shield, BarChart3, TrendingUp, Zap, 
  Target, Users, Landmark, ChevronRight, Clock, Sparkles,
  ShieldCheck, Globe, Database, Lock, Search, Heart, ArrowUpRight
} from "lucide-react";
import { Button } from "../../components/ui/button";
import { Card } from "../../components/ui/card";

export default function AboutPage() {
  return (
    <div className="min-h-screen bg-white text-slate-900 font-sans selection:bg-blue-100 antialiased flex flex-col overflow-x-hidden">
      {/* Navigation */}
      <nav className="fixed top-0 left-0 right-0 z-50 bg-white/80 backdrop-blur-xl border-b border-slate-100 px-8 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2 group">
            <ArrowLeft className="h-4 w-4 text-slate-400 group-hover:text-slate-900 transition-transform group-hover:-translate-x-1" />
            <div className="h-7 w-7 rounded-lg bg-slate-900 flex items-center justify-center text-white font-black text-sm">G</div>
            <span className="font-bold text-xl tracking-tighter text-slate-900">gitto</span>
          </Link>
          <div className="flex gap-4">
            <Link href="/contact">
              <Button variant="ghost" className="text-[14px] font-bold text-slate-600 hover:text-slate-900 rounded-full px-6">
                Contact Sales
              </Button>
            </Link>
            <Link href="/app">
              <Button className="bg-slate-900 text-white hover:bg-slate-800 rounded-full px-8 h-10 text-[14px] font-bold shadow-xl shadow-slate-900/10">
                Book a Demo
              </Button>
            </Link>
          </div>
        </div>
      </nav>

      <main className="flex-1">
        {/* Hero Section */}
        <section className="relative pt-48 pb-32 px-8">
          <div className="max-w-4xl mx-auto text-center space-y-10 relative z-10">
            <div className="inline-flex items-center px-4 py-1.5 rounded-full bg-blue-50 border border-blue-100 text-[11px] font-black uppercase tracking-[0.2em] text-blue-600">
              The Gitto Mission
            </div>
            <h1 className="text-[56px] md:text-[84px] font-bold tracking-tight text-slate-900 leading-[1.05]">
              Closing the gap between <br /> 
              <span className="text-slate-400 font-medium italic">forecast and reality.</span>
            </h1>
            <p className="text-[20px] text-slate-500 font-medium max-w-2xl mx-auto leading-relaxed">
              We believe spreadsheets are the enemy of cash truth. Gitto was built to give CFOs a deterministic anchor for their liquidity.
            </p>
          </div>
        </section>

        {/* The Three Gaps We Solve */}
        <section className="max-w-6xl mx-auto px-8 py-24 border-t border-slate-100">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-24 items-center">
            <div className="space-y-10">
              <div className="space-y-4">
                <h2 className="text-[42px] font-bold tracking-tight text-slate-900">Why we exist</h2>
                <p className="text-xl text-slate-500 font-medium leading-relaxed">
                  Most finance teams are operating on "theoretical cash"—numbers that look good in a model but don't exist in the bank.
                </p>
              </div>
              <div className="space-y-8">
                {[
                  { 
                    title: "The Bank-Truth Gap", 
                    desc: "Models fail when they aren't tied to live transactions. We ingest bank feeds to build an immutable cash ledger.", 
                    icon: <Landmark className="h-5 w-5" /> 
                  },
                  { 
                    title: "The Behavioral Bias", 
                    desc: "Customers pay based on their own habits, not your invoice terms. Our AI learns those habits to find the hidden delay.", 
                    icon: <Zap className="h-5 w-5" /> 
                  },
                  { 
                    title: "The Explainability Deficit", 
                    desc: "When a number changes, CFOs need to know 'Why'. Our RAG-powered analyst provides citations to specific invoices.", 
                    icon: <Search className="h-5 w-5" /> 
                  },
                ].map((value, i) => (
                  <div key={i} className="flex gap-5 text-left">
                    <div className="h-12 w-12 rounded-2xl bg-slate-50 flex items-center justify-center text-slate-900 shadow-sm border border-slate-100 shrink-0">
                      {value.icon}
                    </div>
                    <div className="space-y-1">
                      <h4 className="font-bold text-slate-900 text-[18px]">{value.title}</h4>
                      <p className="text-[15px] text-slate-500 font-medium leading-relaxed">{value.desc}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
            
            <div className="bg-slate-50 rounded-[48px] aspect-square flex items-center justify-center p-12 relative overflow-hidden">
              <div className="absolute inset-0 bg-gradient-to-tr from-blue-500/5 to-indigo-500/5" />
              <div className="relative z-10 w-full bg-white rounded-[32px] shadow-2xl border border-slate-100 p-10 space-y-10">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <ShieldCheck className="h-5 w-5 text-emerald-500" />
                    <span className="font-black text-[11px] uppercase tracking-widest text-slate-400">Audit-Ready Ledger</span>
                  </div>
                  <div className="h-2 w-12 bg-emerald-100 rounded-full" />
                </div>
                <div className="space-y-6">
                  {[
                    { label: 'Reconciled Inflows', val: '+€4.2M', color: 'text-emerald-600' },
                    { label: 'Behavioral Variance', val: '-€120k', color: 'text-red-500' },
                    { label: 'Group Liquidity', val: '€12.8M', color: 'text-slate-900' },
                  ].map((row, i) => (
                    <div key={i} className="flex items-center justify-between border-b border-slate-50 pb-4 last:border-none">
                      <span className="text-sm font-bold text-slate-500">{row.label}</span>
                      <span className={`text-lg font-black tracking-tight ${row.color}`}>{row.val}</span>
                    </div>
                  ))}
                </div>
                <div className="pt-4">
                  <div className="p-4 rounded-2xl bg-blue-50 border border-blue-100 flex items-center justify-between">
                    <span className="text-[10px] font-black text-blue-600 uppercase tracking-widest">CFO Sign-off Status</span>
                    <span className="text-[10px] font-black text-emerald-600 uppercase tracking-widest">Verified</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Enterprise Readiness Section */}
        <section className="bg-slate-900 text-white py-32 px-8 overflow-hidden relative">
          <div className="absolute top-0 right-0 w-1/3 h-full bg-blue-600/10 blur-[120px]" />
          <div className="max-w-5xl mx-auto space-y-20 relative z-10">
            <div className="text-center space-y-4">
              <h2 className="text-[42px] font-bold tracking-tight">Built for Enterprise Readiness</h2>
              <p className="text-slate-400 text-lg font-medium max-w-2xl mx-auto">Gitto isn't just a dashboard; it's a governance layer for global group structures.</p>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-3 gap-12 text-left">
              {[
                { title: "Multi-Currency Mastery", desc: "Group-level visibility with snapshot-locked FX rates and automated reporting currency normalization." },
                { title: "Intercompany Washes", desc: "Instantly detect and exclude intercompany flows to see the true external cash position." },
                { title: "Audit & Controls", desc: "Full history of every lever change and scenario override. Built for external audit transparency." },
              ].map((item, i) => (
                <div key={i} className="space-y-4">
                  <div className="h-10 w-10 rounded-xl bg-white/10 flex items-center justify-center">
                    <Shield className="h-5 w-5 text-blue-400" />
                  </div>
                  <h4 className="text-xl font-bold tracking-tight">{item.title}</h4>
                  <p className="text-slate-400 text-sm leading-relaxed font-medium">{item.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Final CTA */}
        <section className="px-8 py-32 text-center bg-white relative overflow-hidden">
          <div className="max-w-3xl mx-auto space-y-10 relative z-10">
            <h2 className="text-[48px] md:text-[64px] font-bold tracking-tight leading-tight text-slate-900">Ready for cash truth?</h2>
            <p className="text-xl text-slate-500 font-medium italic">Join the next generation of data-aware finance teams.</p>
            <Link href="/app">
              <Button className="bg-slate-900 text-white hover:bg-slate-800 rounded-full px-16 h-18 text-xl font-bold shadow-2xl shadow-slate-900/20">
                Book a Demo
              </Button>
            </Link>
          </div>
        </section>
      </main>

      <footer className="px-8 py-20 bg-white border-t border-slate-100">
        <div className="max-w-7xl mx-auto flex justify-between items-center text-left">
          <div className="flex items-center gap-2">
            <div className="h-7 w-7 rounded-lg bg-slate-900 flex items-center justify-center text-white font-black text-sm">G</div>
            <span className="font-bold text-xl tracking-tighter text-slate-900">gitto</span>
          </div>
          <div className="text-[12px] font-bold text-slate-400 uppercase tracking-widest">
            © 2025 Gitto Inc.
          </div>
        </div>
      </footer>
    </div>
  );
}
