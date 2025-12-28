'use client';

import Link from "next/link";
import { 
  ArrowLeft, Landmark, Zap, Search, Shield, ShieldCheck, Activity, Layers, Globe
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
              <div className="bg-white text-black px-6 py-2.5 rounded-full text-[11px] font-black uppercase tracking-[0.1em] hover:bg-slate-200 transition-all cursor-pointer shadow-lg shadow-white/5">
                Access Terminal
              </div>
            </Link>
          </div>
        </div>
      </nav>

      <main className="relative z-10">
        {/* About Hero: Authority through Thesis */}
        <section className="pt-40 pb-20 px-8">
          <div className="max-w-[1400px] mx-auto">
            <div className="inline-flex items-center px-3 py-1 rounded-sm bg-blue-500/10 border border-blue-500/20 text-[10px] font-black uppercase tracking-[0.3em] text-blue-400 mb-8">
              The Thesis // Revision 1.0
            </div>
            <h1 className="text-[70px] md:text-[130px] font-black tracking-[-0.08em] leading-[0.8] text-white uppercase italic">
              DEATH TO <br />
              <span className="text-white/10 italic not-italic">AVERAGES.</span>
            </h1>
            <p className="mt-12 text-2xl text-slate-400 font-medium max-w-4xl leading-tight tracking-tight italic border-l border-blue-500/30 pl-8">
              "We believe that the most dangerous number in any enterprise is the one that was guessed. Most treasury departments operate on theoretical due dates while their liquidity depends on behavioral reality."
            </p>
          </div>
        </section>

        {/* The Why: Institutional Knowledge */}
        <section className="px-8 py-32 border-t border-white/5 bg-white text-black">
          <div className="max-w-[1400px] mx-auto grid grid-cols-1 lg:grid-cols-12 gap-24">
            <div className="lg:col-span-4 space-y-8">
              <h2 className="text-[10px] font-black text-blue-600 tracking-[0.5em] uppercase">The_Problem_Statement</h2>
              <h3 className="text-5xl font-black italic tracking-tighter leading-[0.9] uppercase">THE BANK-TRUTH <br /> GAP.</h3>
              <p className="text-lg text-slate-500 font-bold leading-relaxed">
                Most treasury software is just a prettier version of Excel. It takes your assumptions and displays them in a graph. But assumptions don't pay bills—cash does.
              </p>
            </div>
            <div className="lg:col-span-8 space-y-12">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-12">
                <div className="space-y-4">
                  <h4 className="text-[11px] font-black uppercase tracking-widest text-slate-900 border-b-2 border-blue-600 w-fit pb-1">01 // The Behavioral Bias</h4>
                  <p className="text-slate-500 font-medium leading-relaxed">Enterprise customers pay based on their own payment runs, internal bottlenecks, and liquidity constraints—not your invoice terms. Gitto maps these unique behavioral patterns to find the hidden 14-day delay before it hits your runway.</p>
                </div>
                <div className="space-y-4">
                  <h4 className="text-[11px] font-black uppercase tracking-widest text-slate-900 border-b-2 border-blue-600 w-fit pb-1">02 // The Explainability Deficit</h4>
                  <p className="text-slate-500 font-medium leading-relaxed">When a forecast drops by €2M, "the model said so" is an unacceptable answer for a CFO. Gitto provides grounded citations for every movement, linking every variance directly back to specific MT940 statements and invoice line items.</p>
                </div>
                <div className="space-y-4">
                  <h4 className="text-[11px] font-black uppercase tracking-widest text-slate-900 border-b-2 border-blue-600 w-fit pb-1">03 // Fragmented Liquidity</h4>
                  <p className="text-slate-500 font-medium leading-relaxed">Managing group liquidity shouldn't require 14 different portal logins. We consolidate MT940/BAI2 feeds across global banks into a single, snapshot-locked source of truth.</p>
                </div>
                <div className="space-y-4">
                  <h4 className="text-[11px] font-black uppercase tracking-widest text-slate-900 border-b-2 border-blue-600 w-fit pb-1">04 // Static Variance Analysis</h4>
                  <p className="text-slate-500 font-medium leading-relaxed">Weekly meetings often waste 45 minutes debating "which data is right." Gitto's automated variance tracking eliminates the debate, letting teams focus on liquidity levers.</p>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* The Solution: High Density Product Value */}
        <section className="px-8 py-32 bg-[#0A0A0B] text-white overflow-hidden border-t border-white/5">
          <div className="max-w-[1400px] mx-auto grid grid-cols-1 lg:grid-cols-2 gap-32 items-center">
            <div className="space-y-16">
              <h2 className="text-7xl font-black tracking-tighter italic uppercase leading-[0.85]">BUILT FOR <br /><span className="text-blue-500">LIQUIDITY</span> <br /> MASTERY.</h2>
              <div className="space-y-10">
                {[
                  { t: 'Multi-Currency Core', d: 'Real-time FX normalization with snapshot-locked rates. Group-level visibility that doesn\'t drift over time.' },
                  { t: 'Intercompany Netting', d: 'Automatically detect and wash internal transfers to see actual group-level external cash reality.' },
                  { t: 'Audit-Grade Controls', d: 'Every scenario shift, lever adjustment, and manual override is logged with a permanent audit trail for external auditors.' },
                ].map((item, i) => (
                  <div key={i} className="flex gap-8 group">
                    <div className="h-px w-12 bg-white/20 mt-4 group-hover:bg-blue-500 transition-colors" />
                    <div className="space-y-2">
                      <h4 className="text-xl font-black uppercase italic tracking-tight text-white group-hover:text-blue-400 transition-colors">{item.t}</h4>
                      <p className="text-slate-400 font-medium leading-relaxed max-w-md">{item.d}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
            <div className="relative">
              <div className="absolute inset-0 bg-blue-600/10 blur-[150px] animate-pulse rounded-full" />
              <div className="relative z-10 bg-white/5 border border-white/10 rounded-[40px] p-12 space-y-10 shadow-2xl">
                <div className="flex items-center justify-between border-b border-white/10 pb-6">
                  <span className="text-[10px] font-black uppercase tracking-[0.3em] text-slate-500">System_Readiness_Score</span>
                  <span className="text-emerald-500 font-black">STABLE // 99.9%</span>
                </div>
                <div className="space-y-8">
                   <div className="space-y-3">
                      <div className="flex justify-between text-[10px] font-black uppercase tracking-widest text-slate-400">
                         <span>Bank Ingest Throughput</span>
                         <span>100%</span>
                      </div>
                      <div className="h-1.5 w-full bg-white/5 rounded-full overflow-hidden">
                        <div className="h-full bg-blue-600 rounded-full" style={{ width: '100%' }} />
                      </div>
                   </div>
                   <div className="space-y-3">
                      <div className="flex justify-between text-[10px] font-black uppercase tracking-widest text-slate-400">
                         <span>MAE Variance Detection</span>
                         <span>Verified</span>
                      </div>
                      <div className="h-1.5 w-full bg-white/5 rounded-full overflow-hidden">
                        <div className="h-full bg-blue-600 rounded-full" style={{ width: '92%' }} />
                      </div>
                   </div>
                </div>
                <div className="pt-4 flex justify-center">
                   <div className="flex items-center gap-2 px-4 py-2 bg-emerald-500/10 border border-emerald-500/20 rounded-full">
                      <CheckCircle2 className="h-3 w-3 text-emerald-500" />
                      <span className="text-[9px] font-black text-emerald-500 uppercase tracking-[0.2em]">SOC2 Type II Compliant</span>
                   </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Mission Final Call */}
        <section className="px-8 py-64 bg-white text-black text-center">
          <div className="max-w-4xl mx-auto space-y-12">
            <h2 className="text-[60px] md:text-[100px] font-black tracking-[-0.05em] leading-[0.9] uppercase">WE EXIST TO <br /> <span className="text-blue-600 italic">SECURE</span> <br /> THE FUTURE.</h2>
            <div className="pt-12">
              <Link href="/contact">
                <Button className="bg-black text-white hover:bg-slate-900 rounded-none px-20 h-24 text-xl font-black uppercase tracking-[0.1em] shadow-2xl transition-all hover:scale-105 active:scale-95">
                  Partner with Gitto
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
