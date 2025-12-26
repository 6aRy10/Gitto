'use client';

import { useState } from 'react';
import Link from "next/link";
import { ArrowRight, CheckCircle2, Shield, BarChart3, TrendingUp, AlertCircle, Landmark, Users } from "lucide-react";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "../components/ui/card";
import { api } from "../lib/api";

const features = [
  { title: "Behavior-based forecasting", desc: "Learn actual payment behaviors by customer, country, and terms to predict when cash lands.", icon: <BarChart3 className="h-5 w-5 text-blue-600" /> },
  { title: "13-Week CFO Command Center", desc: "Interactive weekly grid with live drill-downs into invoices and vendor bills.", icon: <CheckCircle2 className="h-5 w-5 text-emerald-600" /> },
  { title: "Liquidity Levers & Actions", desc: "Simulate delay shocks or aggressive collections and track ROI-positive actions.", icon: <ArrowRight className="h-5 w-5 text-indigo-600" /> },
  { title: "Multi-Currency Bank Truth", desc: "Ingest bank balances and reconcile cash receipts with snapshot-locked FX rates.", icon: <Shield className="h-5 w-5 text-amber-600" /> },
];

const steps = [
  { label: "01", title: "Unified Ingest", desc: "Upload Excel for quick starts or connect Snowflake for enterprise-scale integration." },
  { label: "02", title: "Bank-Truth Layer", desc: "Connect actual bank feeds to build an immutable cash ledger and reconcile receipts." },
  { label: "03", title: "Grounded RAG Insights", desc: "Ask 'Why' behind variances and get answers grounded in specific retrieved invoices." },
  { label: "04", title: "Audit-Ready Controls", desc: "Persistent audit logs for every lever change, scenario override, and CFO sign-off." },
];

export default function Landing() {
  const barColors = Array.from({ length: 40 }, (_, i) =>
    i % 2 === 0 ? '#3b82f6' : '#6366f1'
  );
  const barOpacities = Array.from({ length: 40 }, (_, i) =>
    0.2 + ((i % 5) * 0.08)
  ); // deterministic to avoid hydration mismatches
  return (
    <div className="min-h-screen bg-white text-slate-900 font-sans selection:bg-blue-100 antialiased relative">
      {/* Global Background Effect */}
      <div className="fixed inset-0 z-0 flex w-full h-full overflow-hidden pointer-events-none opacity-[0.12]">
        {barColors.map((color, i) => (
          <div 
            key={i} 
            className="h-full flex-1 border-r border-slate-100/10" 
            style={{ 
              backgroundColor: color,
              opacity: barOpacities[i]
            }} 
          />
        ))}
        <div 
          className="absolute inset-0 opacity-[0.6] pointer-events-none" 
          style={{ 
            backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E")`,
            mixBlendMode: 'overlay'
          }} 
        />
      </div>

      {/* Floating Navigation */}
      <nav className="fixed top-8 left-1/2 -translate-x-1/2 w-[90%] max-w-5xl z-50">
        <div className="bg-white/90 backdrop-blur-xl border border-slate-200/50 rounded-2xl px-8 py-3.5 flex items-center justify-between shadow-[0_8px_32px_rgba(0,0,0,0.04)]">
          <div className="flex items-center gap-2">
            <div className="h-6 w-6 rounded-sm bg-slate-900 flex items-center justify-center text-white font-black text-xs">G</div>
            <span className="font-bold text-2xl tracking-tighter text-slate-900">gitto</span>
          </div>
          <div className="hidden md:flex items-center gap-10 text-[13px] font-semibold text-slate-500 tracking-tight">
            <button onClick={() => document.getElementById('features')?.scrollIntoView({ behavior: 'smooth' })} className="hover:text-slate-900 transition-colors">Features</button>
            <button onClick={() => document.getElementById('pricing')?.scrollIntoView({ behavior: 'smooth' })} className="hover:text-slate-900 transition-colors">Pricing</button>
            <Link href="/contact" className="hover:text-slate-900 transition-colors">Contact</Link>
          </div>
          <div className="flex items-center gap-6">
            <Link href="/app" className="text-[13px] font-semibold text-slate-900 hover:text-slate-600 transition-colors">Sign In</Link>
            <Link href="/app">
              <Button className="bg-slate-900 text-white hover:bg-slate-800 rounded-lg px-6 h-10 text-[13px] font-bold tracking-tight">
                Get Started
              </Button>
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="relative z-10 pt-64 pb-48 px-6 min-h-[900px] flex items-center justify-center overflow-hidden">
        <div className="max-w-5xl mx-auto text-center space-y-12 relative z-10">
          <div className="inline-flex items-center px-5 py-2 rounded-full bg-white/60 backdrop-blur-md border border-white/40 text-[13px] font-black text-slate-900 tracking-tight shadow-sm">
            Get started with Gitto
          </div>
          
          <h1 className="text-[64px] md:text-[92px] font-bold tracking-[-0.05em] text-slate-900 leading-[0.92] max-w-4xl mx-auto">
            Enterprise Cash <br className="hidden sm:block" />
            Command Center <br className="hidden sm:block" />
            <span className="text-blue-600">Built for Trust.</span>
          </h1>
          
          <p className="text-[19px] text-slate-600 font-medium max-w-2xl mx-auto tracking-tight leading-relaxed opacity-90">
            Behavior-based forecasting meets bank-truth reality. The only workspace that retrieves specific invoice evidence to explain your cash.
          </p>
          
          <div className="flex flex-col items-center gap-10 pt-6">
            <Link href="/app">
              <Button className="bg-slate-900 text-white hover:bg-slate-800 rounded-xl px-12 h-16 text-[17px] font-black shadow-2xl shadow-slate-900/10 transition-all hover:scale-[1.02] active:scale-[0.98]">
                Get Started
              </Button>
            </Link>
            
            <div className="flex items-center gap-3">
              <span className="text-sm font-bold text-slate-900 tracking-tight">G</span>
              <div className="flex gap-0.5">
                {[1,2,3,4,5].map(i => (
                  <svg key={i} className="w-4 h-4 text-slate-900 fill-current" viewBox="0 0 20 20">
                    <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                  </svg>
                ))}
              </div>
              <span className="text-[13px] font-bold text-slate-900 tracking-tight">4.9 Rating from Users</span>
            </div>
          </div>
        </div>
      </section>

      {/* Feature Section (Talunt Style) */}
      <section id="features" className="relative z-10 max-w-7xl mx-auto px-6 py-32 space-y-24">
        <div className="space-y-4 text-left">
          <div className="flex items-center gap-3 text-slate-400 text-[13px] font-bold uppercase tracking-wider">
            <span className="w-2 h-2 rounded-full bg-slate-900" />
            One stop solution
          </div>
          <h2 className="text-[72px] font-bold tracking-tighter text-slate-900 leading-none">Get Started</h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-10">
          {[
            {
              title: "13-Week Command Center",
              desc: "The single brain for CFOs. Interactive weekly grid with live drill-downs into every invoice and vendor bill.",
              img: (
                <div className="w-full h-full bg-[#111] flex items-center justify-center p-8">
                  <div className="bg-white rounded-xl shadow-2xl p-6 w-full space-y-4 border border-slate-100/50">
                    <div className="flex items-center justify-between border-b pb-3 border-slate-50">
                      <div className="flex items-center gap-2">
                        <div className="h-5 w-5 rounded bg-blue-100 flex items-center justify-center text-[10px] font-black text-blue-600">W1</div>
                        <span className="text-[10px] font-black">+€19.7k</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <div className="h-5 w-5 rounded bg-emerald-100 flex items-center justify-center text-[10px] font-black text-emerald-600">W3</div>
                        <span className="text-[10px] font-black text-emerald-600">+€4.2M</span>
                      </div>
                    </div>
                    <div className="space-y-3 pt-2 text-left">
                      <div className="text-[9px] font-black text-slate-400 uppercase">Live Prediction Grid</div>
                      <div className="h-2 w-full bg-slate-100 rounded-full" />
                      <div className="h-2 w-[60%] bg-slate-100 rounded-full" />
                    </div>
                  </div>
                </div>
              )
            },
            {
              title: "The Three Desks",
              desc: "Specialized workspaces for Banking (Treasury), Analyst (FP&A), and Operations (AR) teams to collaborate on cash truth.",
              img: (
                <div className="w-full h-full bg-[#111] flex items-center justify-center p-8">
                  <div className="w-full space-y-3">
                    {[
                      { label: 'Banking Desk', icon: <Landmark className="h-3 w-3" />, color: 'text-emerald-400' },
                      { label: 'Analyst Desk', icon: <BarChart3 className="h-3 w-3" />, color: 'text-blue-400' },
                      { label: 'Operations Desk', icon: <Users className="h-3 w-3" />, color: 'text-amber-400' },
                    ].map((desk, i) => (
                      <div key={i} className="bg-white/10 backdrop-blur-md border border-white/10 rounded-xl p-3 flex items-center gap-3">
                        <div className={desk.color}>{desk.icon}</div>
                        <span className="text-[10px] font-bold text-white uppercase tracking-widest">{desk.label}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )
            },
            {
              title: "CFO-Grounded RAG Insights",
              desc: "Ask any question and get answers grounded in specific invoice evidence. Zero hallucinations, 100% data-aware.",
              img: (
                <div className="w-full h-full bg-[#111] flex items-center justify-center p-8">
                  <div className="bg-white rounded-xl shadow-2xl p-6 w-full space-y-4 border border-slate-100/50 text-left relative overflow-hidden">
                    <div className="flex items-center gap-2 mb-2">
                      <div className="h-4 w-4 rounded-full bg-indigo-100 flex items-center justify-center text-indigo-600">
                        <Sparkles className="h-2.5 w-2.5" />
                      </div>
                      <span className="text-[10px] font-black uppercase tracking-widest text-slate-400">Grounded Evidence</span>
                    </div>
                    <div className="space-y-3 border-t border-slate-50 pt-4">
                      <div className="p-3 rounded-xl bg-slate-50 border border-slate-100 space-y-2">
                        <div className="text-[10px] font-black text-indigo-900 uppercase">Retrieved from Snapshot</div>
                        <p className="text-[9px] text-slate-600 leading-tight">Inv #2943307 (€4.3k) from Kuwait: Predicted landing delayed 59 days.</p>
                      </div>
                    </div>
                    <div className="flex gap-2 pt-2">
                      <div className="flex-1 h-8 rounded-lg bg-slate-900 flex items-center justify-center text-[10px] font-black text-white">Ask Analyst</div>
                    </div>
                  </div>
                </div>
              )
            }
          ].map((feature, i) => (
            <div key={i} className="group cursor-pointer space-y-8">
              <div className="aspect-[4/3] rounded-[40px] bg-black overflow-hidden shadow-2xl transition-all duration-500 group-hover:scale-[1.02] group-hover:shadow-[0_32px_64px_rgba(0,0,0,0.1)]">
                {feature.img}
              </div>
              <div className="space-y-4 px-2">
                <h3 className="text-2xl font-bold text-slate-900 tracking-tight">{feature.title}</h3>
                <p className="text-slate-500 text-[17px] leading-relaxed font-semibold tracking-tight opacity-70">{feature.desc}</p>
              </div>
            </div>
          ))}
        </div>

        {/* Secondary Features Section (Talunt "... and so much more" Style) */}
        <div className="space-y-16 pt-16">
          <div className="space-y-4">
            <h2 className="text-4xl font-bold tracking-tight text-slate-900 leading-none">... and so much more</h2>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-x-12 gap-y-16">
            {[
              {
                title: "Accuracy Backtesting",
                desc: "Automatically compare historical forecasts against actual collections to measure and improve Mean Absolute Error (MAE).",
                icon: <TrendingUp className="h-6 w-6 text-slate-900" />
              },
              {
                title: "FX Exposure Analysis",
                desc: "Instantly surface multi-currency cash dependencies and implied risk before they impact reporting currency totals.",
                icon: <AlertCircle className="h-6 w-6 text-slate-900" />
              },
              {
                title: "Explainable Predictions",
                desc: "No black boxes. Every collection date is backed by segment-level data and historical behavioral patterns.",
                icon: <BarChart3 className="h-6 w-6 text-slate-900" />
              },
              {
                title: "Enterprise Data Ingest",
                desc: "Seamlessly blend manual Excel exports with Snowflake or ERP pipelines in a single unified workspace.",
                icon: <Shield className="h-6 w-6 text-slate-900" />
              }
            ].map((item, i) => (
              <div key={i} className="space-y-6">
                <div className="h-12 w-12 flex items-center justify-center rounded-xl bg-slate-50 border border-slate-100 shadow-sm group-hover:scale-110 transition-transform">
                  {item.icon}
                </div>
                <div className="space-y-3">
                  <h4 className="text-lg font-bold text-slate-900 tracking-tight">{item.title}:</h4>
                  <p className="text-slate-500 font-medium leading-relaxed text-[15px]">
                    {item.desc}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing Section (Talunt Style) */}
      <section id="pricing" className="relative z-10 max-w-7xl mx-auto px-6 py-32 space-y-20">
        <div className="space-y-4">
          <div className="flex items-center gap-3 text-slate-400 text-[13px] font-bold uppercase tracking-wider">
            <span className="w-2 h-2 rounded-full bg-slate-900" />
            Transparent Pricing
          </div>
          <h2 className="text-[72px] font-bold tracking-tighter text-slate-900 leading-none text-left">Plans</h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-10">
          {[
            {
              name: "Pro",
              price: "€2,500",
              period: "/month",
              desc: "For high-growth finance teams needing rolling visibility.",
              features: [
                "13-Week Behavioral Forecast",
                "Excel & ERP Ingestion",
                "Bank-Truth Reconciliation",
                "Cash Variance Explainer",
                "Scenario Modeling",
                "Segment-Level Analytics"
              ]
            },
            {
              name: "Enterprise",
              price: "Custom",
              period: "",
              desc: "For global enterprises with complex ERP stacks.",
              features: [
                "Snowflake Native Connector",
                "Multi-Entity / Multi-Currency",
                "Treasury Action Hub",
                "Dispute Risk Prediction",
                "CFO-Grade RAG Reporting",
                "Liquidity Lever Simulation",
                "Audit & Enterprise Governance"
              ]
            }
          ].map((plan, i) => (
            <Card key={i} className="rounded-[40px] border border-slate-100 shadow-2xl p-12 space-y-8 group hover:scale-[1.01] transition-transform">
              <div className="space-y-4">
                <h3 className="text-2xl font-black tracking-tight">{plan.name}</h3>
                <div className="flex items-baseline gap-1">
                  <span className="text-[56px] font-black tracking-tighter">{plan.price}</span>
                  <span className="text-slate-400 font-bold">{plan.period}</span>
                </div>
                <p className="text-slate-500 font-semibold text-lg">{plan.desc}</p>
              </div>
              <ul className="space-y-4 pt-8 border-t border-slate-50">
                {plan.features.map((f, j) => (
                  <li key={j} className="flex items-center gap-3 text-[15px] font-bold text-slate-700">
                    <CheckCircle2 className="h-5 w-5 text-blue-600" />
                    {f}
                  </li>
                ))}
              </ul>
              <Button className="w-full h-16 bg-slate-900 text-white rounded-2xl text-lg font-black tracking-tight mt-8">
                Get Started
              </Button>
            </Card>
          ))}
        </div>
      </section>

      {/* Footer (Simplified Talunt Style) */}
      <footer className="relative z-10 border-t border-slate-100 pt-32 pb-16 px-6 bg-white/40 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row justify-between gap-16">
          <div className="space-y-8 max-w-sm">
            <div className="flex items-center gap-2">
              <div className="h-6 w-6 rounded-sm bg-slate-900 flex items-center justify-center text-white font-black text-xs">G</div>
              <span className="font-bold text-2xl tracking-tighter text-slate-900">gitto</span>
            </div>
            <p className="text-[15px] text-slate-500 font-semibold leading-relaxed tracking-tight">
              Enterprise cash intelligence for high-growth teams. Behavior-based forecasting, bank-truth reconciliation, and audit-ready controls in one unified command center.
            </p>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-24">
            <div className="space-y-6">
              <h4 className="text-[13px] font-black uppercase tracking-widest text-slate-900">Resources</h4>
              <ul className="space-y-3 text-[15px] font-semibold text-slate-500 tracking-tight">
                <li onClick={() => document.getElementById('pricing')?.scrollIntoView({ behavior: 'smooth' })} className="hover:text-slate-900 transition-colors cursor-pointer text-left">Pricing</li>
                <li onClick={() => document.getElementById('features')?.scrollIntoView({ behavior: 'smooth' })} className="hover:text-slate-900 transition-colors cursor-pointer text-left">Features</li>
                <li className="hover:text-slate-900 transition-colors cursor-pointer text-left">FAQs</li>
              </ul>
            </div>
            <div className="space-y-6">
              <h4 className="text-[13px] font-black uppercase tracking-widest text-slate-900">Support</h4>
              <ul className="space-y-3 text-[15px] font-semibold text-slate-500 tracking-tight">
                <li><Link href="/contact" className="hover:text-slate-900 transition-colors cursor-pointer text-left">Contact us</Link></li>
                <li><Link href="/about" className="hover:text-slate-900 transition-colors cursor-pointer text-left">About us</Link></li>
              </ul>
            </div>
            <div className="space-y-6">
              <h4 className="text-[13px] font-black uppercase tracking-widest text-slate-900">Legal</h4>
              <ul className="space-y-3 text-[15px] font-semibold text-slate-500 tracking-tight">
                <li className="hover:text-slate-900 transition-colors cursor-pointer text-left">Terms & conditions</li>
                <li className="hover:text-slate-900 transition-colors cursor-pointer text-left">Privacy policy</li>
              </ul>
            </div>
          </div>
        </div>
        <div className="max-w-7xl mx-auto pt-32 flex justify-between items-center text-[11px] font-black uppercase tracking-[0.2em] text-slate-400 px-6">
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

const Sparkles = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M12 3L14.5 9L21 11.5L14.5 14L12 21L9.5 14L3 11.5L9.5 9L12 3Z" fill="currentColor" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
  </svg>
);
