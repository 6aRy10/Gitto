'use client';

import Link from "next/link";
import { 
  ArrowLeft, Landmark, Zap, Search, Shield, ShieldCheck
} from "lucide-react";
import { Button } from "../../components/ui/button";

export default function About() {
  return (
    <div className="min-h-screen bg-[#0A0A0B] text-white font-sans selection:bg-blue-500/30 antialiased overflow-x-hidden relative">
      {/* Shared Design Elements */}
      <div className="fixed inset-0 z-50 pointer-events-none opacity-[0.03]" style={{ backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E")` }} />
      <div className="fixed inset-0 z-0 pointer-events-none overflow-hidden">
        <div className="absolute top-[-10%] right-[-10%] w-[40%] h-[40%] bg-blue-600/5 blur-[120px] rounded-full" />
      </div>

      <nav className="fixed top-0 left-0 right-0 z-[60] bg-[#0A0A0B]/80 backdrop-blur-md border-b border-white/5 px-8 py-5">
        <div className="max-w-[1400px] mx-auto flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2 group">
            <div className="h-6 w-6 rounded-lg bg-blue-600 flex items-center justify-center text-white font-black text-[12px] italic">G</div>
            <span className="font-bold text-lg tracking-[-0.04em] text-white uppercase italic">Gitto</span>
          </Link>
          <div className="flex items-center gap-8">
            <Link href="/" className="text-[11px] font-black uppercase tracking-[0.2em] text-slate-400 hover:text-white transition-colors">Return_Home</Link>
            <Link href="/app">
              <div className="bg-white text-black px-6 py-2.5 rounded-full text-[11px] font-black uppercase tracking-[0.1em] hover:bg-slate-200 transition-all cursor-pointer">
                Access Terminal
              </div>
            </Link>
          </div>
        </div>
      </nav>

      <main className="relative z-10">
        {/* About Hero - Tighter */}
        <section className="pt-40 pb-20 px-8">
          <div className="max-w-[1400px] mx-auto">
            <div className="inline-flex items-center px-3 py-1 rounded-sm bg-blue-500/10 border border-blue-500/20 text-[10px] font-black uppercase tracking-[0.3em] text-blue-400 mb-8">
              The Thesis // v1.0
            </div>
            <h1 className="text-[70px] md:text-[130px] font-black tracking-[-0.08em] leading-[0.8] text-white uppercase">
              DEATH TO <br />
              <span className="text-white/10 italic">AVERAGES.</span>
            </h1>
            <p className="mt-12 text-2xl text-slate-400 font-medium max-w-3xl leading-tight tracking-tight italic border-l border-blue-500/30 pl-6">
              "We believe that the most dangerous number in any enterprise is the one that was guessed. Gitto was built to replace theoretical assumptions with deterministic bank reality."
            </p>
          </div>
        </section>

        {/* The Why - Two Column Brutalist - Tighter */}
        <section className="px-8 py-32 border-t border-white/5 bg-white text-black">
          <div className="max-w-[1400px] mx-auto grid grid-cols-1 lg:grid-cols-12 gap-16">
            <div className="lg:col-span-4 space-y-6">
              <h2 className="text-[10px] font-black text-blue-600 tracking-[0.5em] uppercase">The_Core_Problem</h2>
              <h3 className="text-4xl font-black italic tracking-tighter leading-none">THE DEFICIT OF BANK TRUTH.</h3>
            </div>
            <div className="lg:col-span-8 space-y-10">
              <p className="text-xl font-bold leading-relaxed text-slate-600">
                Treasury is broken because it relies on static due dates. Gitto solves this by integrating directly with your bank feeds to map actual behavioral reality.
              </p>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-10 pt-8">
                <div className="space-y-3">
                  <h4 className="text-[11px] font-black uppercase tracking-widest text-slate-900 border-b border-slate-100 pb-2">01 // Behavioral Intelligence</h4>
                  <p className="text-sm text-slate-500 font-medium leading-relaxed">Most ERPs assume net-30. We track individual customer payment cycles to find the unmodeled 14-day delay before it hits your runway.</p>
                </div>
                <div className="space-y-3">
                  <h4 className="text-[11px] font-black uppercase tracking-widest text-slate-900 border-b border-slate-100 pb-2">02 // Deterministic Reconcilation</h4>
                  <p className="text-sm text-slate-500 font-medium leading-relaxed">Forecasts without bank pings are just guesses. Gitto reconciles every wire against your 13-week grid for a verified closing cash number.</p>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* The Solution - High Density - Tighter */}
        <section className="px-8 py-32 bg-[#0A0A0B] text-white overflow-hidden">
          <div className="max-w-[1400px] mx-auto grid grid-cols-1 lg:grid-cols-2 gap-24 items-center">
            <div className="space-y-12">
              <h2 className="text-6xl font-black tracking-tighter italic">BUILT FOR <br /><span className="text-blue-500">LIQUIDITY</span> <br /> MASTERY.</h2>
              <div className="space-y-8">
                {[
                  { t: '13-Week Dynamic Grid', d: 'Interactive multi-entity grid with snapshot locking and weekly variance comparison.' },
                  { t: 'Multi-Currency Core', d: 'Snapshot-locked FX rates and cross-border normalization across all group accounts.' },
                  { t: 'Audit-Grade Controls', d: 'Every scenario shift and manual override is logged and attributed for external audit.' },
                ].map((item, i) => (
                  <div key={i} className="flex gap-6 group">
                    <div className="h-px w-8 bg-white/20 mt-4 group-hover:bg-blue-500 transition-colors" />
                    <div className="space-y-1">
                      <h4 className="text-lg font-black uppercase italic tracking-tight">{item.t}</h4>
                      <p className="text-sm text-slate-400 font-medium leading-relaxed max-w-md">{item.d}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
            <div className="relative">
              <div className="absolute inset-0 bg-blue-600/10 blur-[100px] animate-pulse rounded-full" />
              <div className="relative z-10 bg-white/5 border border-white/5 rounded-[32px] p-10 space-y-6">
                <div className="flex items-center justify-between border-b border-white/10 pb-4">
                  <span className="text-[9px] font-black uppercase tracking-[0.3em] text-slate-500">Enterprise_Readiness_Module</span>
                  <span className="text-emerald-500 font-black text-xs">READY</span>
                </div>
                <div className="space-y-4">
                  {[1,2,3].map(i => (
                    <div key={i} className="h-1.5 w-full bg-white/5 rounded-full overflow-hidden">
                      <div className="h-full bg-blue-600 rounded-full" style={{ width: `${95 - (i*15)}%` }} />
                    </div>
                  ))}
                </div>
                <p className="text-[10px] text-slate-500 font-bold italic text-center">Gitto Engine v4.2 // Production_Build</p>
              </div>
            </div>
          </div>
        </section>

        {/* Mission Final Call */}
        <section className="px-8 py-64 bg-white text-black text-center">
          <div className="max-w-4xl mx-auto space-y-12">
            <h2 className="text-[60px] md:text-[100px] font-black tracking-[-0.05em] leading-[0.9] uppercase">WE EXIST TO <br /> <span className="text-slate-300 italic">SECURE</span> <br /> THE FUTURE.</h2>
            <div className="pt-12">
              <Link href="/contact">
                <Button className="bg-black text-white hover:bg-slate-900 rounded-none px-20 h-20 text-xl font-black uppercase tracking-[0.1em]">
                  Join the Mission
                </Button>
              </Link>
            </div>
          </div>
        </section>
      </main>

      {/* Footer - Mirrored from Home */}
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
      </footer>
    </div>
  );
}
