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
        {/* About Hero - Massive Type */}
        <section className="pt-64 pb-32 px-8">
          <div className="max-w-[1400px] mx-auto">
            <div className="inline-flex items-center px-3 py-1 rounded-sm bg-white/5 border border-white/10 text-[10px] font-black uppercase tracking-[0.3em] text-blue-400 mb-12">
              The Thesis // v1.0
            </div>
            <h1 className="text-[80px] md:text-[160px] font-black tracking-[-0.08em] leading-[0.8] text-white uppercase">
              DEATH TO <br />
              <span className="text-white/10 italic">AVERAGES.</span>
            </h1>
            <p className="mt-20 text-3xl text-slate-400 font-medium max-w-4xl leading-tight tracking-tight italic">
              "We believe that the most dangerous number in any enterprise is the one that was guessed."
            </p>
          </div>
        </section>

        {/* The Why - Two Column Brutalist */}
        <section className="px-8 py-64 border-t border-white/5 bg-white text-black">
          <div className="max-w-[1400px] mx-auto grid grid-cols-1 lg:grid-cols-12 gap-24">
            <div className="lg:col-span-4 space-y-8">
              <h2 className="text-[10px] font-black text-slate-300 tracking-[0.5em] uppercase">The_Problem</h2>
              <h3 className="text-5xl font-black italic tracking-tighter leading-none">THE BANK-TRUTH GAP.</h3>
            </div>
            <div className="lg:col-span-8 space-y-12">
              <p className="text-2xl font-bold leading-relaxed text-slate-600">
                Most treasury software is just a prettier version of Excel. It takes your assumptions and displays them in a graph. But assumptions don't pay bills—cash does.
              </p>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-12 pt-12">
                <div className="space-y-4">
                  <h4 className="text-[11px] font-black uppercase tracking-widest text-slate-900">01 // The Behavioral Bias</h4>
                  <p className="text-slate-500 font-medium leading-relaxed">Customers don't pay on due dates. They pay according to their own internal bottlenecks, payment runs, and liquidity constraints. Gitto learns these patterns.</p>
                </div>
                <div className="space-y-4">
                  <h4 className="text-[11px] font-black uppercase tracking-widest text-slate-900">02 // The Explainability Deficit</h4>
                  <p className="text-slate-500 font-medium leading-relaxed">When a forecast is wrong, "the model said so" isn't an answer. Gitto provides grounded citations for every movement, linked back to specific bank receipts.</p>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* The Solution - High Density */}
        <section className="px-8 py-64 bg-[#0A0A0B] text-white overflow-hidden">
          <div className="max-w-[1400px] mx-auto grid grid-cols-1 lg:grid-cols-2 gap-32 items-center">
            <div className="space-y-16">
              <h2 className="text-7xl font-black tracking-tighter italic">BUILT FOR <br /><span className="text-blue-500">LIQUIDITY</span> <br /> MASTERY.</h2>
              <div className="space-y-10">
                {[
                  { t: 'Multi-Currency Core', d: 'Snapshot-locked FX rates and cross-border normalization that doesn\'t drift.' },
                  { t: 'Intercompany Washes', d: 'Automatically detect and net-out internal transfers to see group reality.' },
                  { t: 'Audit-Grade Controls', d: 'Every scenario change is logged. Every lever shift is attributed.' },
                ].map((item, i) => (
                  <div key={i} className="flex gap-8 group">
                    <div className="h-px w-12 bg-white/20 mt-4 group-hover:bg-blue-500 transition-colors" />
                    <div className="space-y-2">
                      <h4 className="text-xl font-black uppercase italic tracking-tight">{item.t}</h4>
                      <p className="text-slate-400 font-medium leading-relaxed max-w-md">{item.d}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
            <div className="relative">
              <div className="absolute inset-0 bg-blue-600/10 blur-[150px] animate-pulse rounded-full" />
              <div className="relative z-10 bg-white/5 border border-white/5 rounded-[40px] p-12 space-y-8">
                <div className="flex items-center justify-between border-b border-white/10 pb-6">
                  <span className="text-[10px] font-black uppercase tracking-[0.3em] text-slate-500">Enterprise_Readiness_Score</span>
                  <span className="text-emerald-500 font-black">99.9%</span>
                </div>
                <div className="space-y-6">
                  {[1,2,3,4].map(i => (
                    <div key={i} className="h-2 w-full bg-white/5 rounded-full overflow-hidden">
                      <div className="h-full bg-blue-600 rounded-full" style={{ width: `${90 - (i*10)}%` }} />
                    </div>
                  ))}
                </div>
                <p className="text-[11px] text-slate-500 font-bold italic text-center">Gitto v4.2 // Production Ready</p>
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
