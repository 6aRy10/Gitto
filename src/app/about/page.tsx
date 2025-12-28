'use client';

import Link from "next/link";
import { 
  ArrowLeft, CheckCircle2, Shield, BarChart3, TrendingUp, Zap, 
  Target, Users, Landmark, ChevronRight, Clock, Sparkles,
  ShieldCheck, Globe, Database, Lock, Search, Heart
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
            <div className="inline-flex items-center px-4 py-1.5 rounded-full bg-slate-50 border border-slate-100 text-[11px] font-black uppercase tracking-[0.2em] text-slate-500">
              The Gitto Story
            </div>
            <h1 className="text-[56px] md:text-[84px] font-bold tracking-tight text-slate-900 leading-[1.05]">
              Cash truth anchored <br /> 
              <span className="text-slate-400 font-medium italic">in reality.</span>
            </h1>
            <p className="text-[20px] text-slate-500 font-medium max-w-2xl mx-auto leading-relaxed">
              We bridge the gap between theoretical accounting and actual liquidity, turning behavioral evidence into an immutable cash ledger.
            </p>
          </div>
        </section>

        {/* Mission & Values */}
        <section className="max-w-6xl mx-auto px-8 py-24 border-t border-slate-100">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-24 items-center">
            <div className="space-y-10">
              <div className="space-y-4">
                <h2 className="text-[42px] font-bold tracking-tight text-slate-900">Our Mission</h2>
                <p className="text-xl text-slate-500 font-medium leading-relaxed">
                  To empower the world's most ambitious finance teams with a single source of cash truth.
                </p>
              </div>
              <div className="space-y-6">
                {[
                  { title: "Trust first", desc: "Every number in Gitto is backed by deterministic evidence.", icon: <ShieldCheck className="h-5 w-5" /> },
                  { title: "Global by design", desc: "Multi-entity, multi-currency, and multi-bank from day one.", icon: <Globe className="h-5 w-5" /> },
                  { title: "AI with citations", desc: "No hallucinations. Our AI analyst always shows its work.", icon: <Sparkles className="h-5 w-5" /> },
                ].map((value, i) => (
                  <div key={i} className="flex gap-4">
                    <div className="h-10 w-10 rounded-xl bg-slate-50 flex items-center justify-center text-slate-900 shadow-sm border border-slate-100 shrink-0">
                      {value.icon}
                    </div>
                    <div className="space-y-1">
                      <h4 className="font-bold text-slate-900 text-[17px]">{value.title}</h4>
                      <p className="text-[15px] text-slate-500 font-medium leading-relaxed">{value.desc}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
            <div className="bg-slate-50 rounded-[48px] aspect-square flex items-center justify-center p-12 relative overflow-hidden">
              <div className="absolute inset-0 bg-gradient-to-tr from-blue-500/5 to-indigo-500/5" />
              <div className="relative z-10 w-full bg-white rounded-[32px] shadow-2xl border border-slate-100 p-8 space-y-8">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Heart className="h-4 w-4 text-red-500 fill-red-500" />
                    <span className="font-bold text-sm">Customer Trust</span>
                  </div>
                  <span className="text-[11px] font-bold text-slate-400 uppercase tracking-widest">99.9% Retention</span>
                </div>
                <div className="space-y-4">
                  {[1,2,3].map(i => (
                    <div key={i} className="flex items-center gap-4">
                      <div className="h-10 w-10 rounded-full bg-slate-100" />
                      <div className="flex-1 space-y-2">
                        <div className="h-2 w-full bg-slate-100 rounded-full" />
                        <div className="h-2 w-2/3 bg-slate-50 rounded-full" />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Final CTA */}
        <section className="px-8 py-32 text-center bg-slate-900 text-white relative overflow-hidden">
          <div className="absolute inset-0 bg-blue-600/10 blur-[120px]" />
          <div className="max-w-3xl mx-auto space-y-10 relative z-10">
            <h2 className="text-[48px] md:text-[64px] font-bold tracking-tight leading-tight">Ready to see the magic?</h2>
            <p className="text-xl text-slate-400 font-medium">Join 500+ finance teams building the future of treasury.</p>
            <Link href="/app">
              <Button className="bg-white text-slate-900 hover:bg-slate-50 rounded-full px-16 h-18 text-xl font-bold shadow-2xl shadow-white/10">
                Book a Demo
              </Button>
            </Link>
          </div>
        </section>
      </main>

      <footer className="px-8 py-20 bg-white border-t border-slate-100">
        <div className="max-w-7xl mx-auto flex justify-between items-center">
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
