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
  const [activeWorkflow, setActiveWorkflow] = useState(0);

  const workflows = [
    {
      title: "Bank-Truth Reconciliation",
      desc: "Watch as Gitto automatically matches incoming bank receipts to open invoices with 99% accuracy.",
      videoMock: (
        <div className="w-full h-full bg-slate-900 rounded-3xl p-8 flex flex-col gap-6 relative overflow-hidden">
          <div className="flex items-center justify-between border-b border-white/10 pb-4">
            <div className="flex items-center gap-3">
              <Landmark className="h-5 w-5 text-emerald-400" />
              <span className="text-white font-bold text-sm">Live Bank Feed</span>
            </div>
            <div className="px-3 py-1 bg-emerald-500/20 text-emerald-400 rounded-full text-[10px] font-black uppercase tracking-widest animate-pulse">Syncing</div>
          </div>
          <div className="space-y-4">
            <div className="bg-white/5 border border-white/10 p-4 rounded-2xl flex items-center justify-between animate-in slide-in-from-left duration-700">
              <div className="space-y-1">
                <div className="text-[10px] text-slate-500 font-bold uppercase">Transaction</div>
                <div className="text-white font-bold text-sm">€43,200 from Siemens AG</div>
              </div>
              <ArrowRight className="h-4 w-4 text-emerald-400 animate-bounce-x" />
              <div className="text-right space-y-1">
                <div className="text-[10px] text-slate-500 font-bold uppercase">Matched Invoice</div>
                <div className="text-white font-bold text-sm">#INV-9942</div>
              </div>
            </div>
            <div className="h-[1px] w-full bg-white/5" />
            <div className="bg-emerald-500/10 border border-emerald-500/20 p-4 rounded-2xl flex items-center gap-4">
              <CheckCircle2 className="h-5 w-5 text-emerald-400" />
              <span className="text-emerald-400 font-bold text-sm uppercase tracking-tight">Reconciliation Success: Ledger Updated</span>
            </div>
          </div>
          {/* Mouse pointer simulation */}
          <MousePointer2 className="absolute bottom-10 right-20 text-white h-6 w-6 animate-pulse" />
        </div>
      )
    },
    {
      title: "Grounded RAG Insights",
      desc: "Ask any complex cash question and see Gitto retrieve specific evidence from your snapshots.",
      videoMock: (
        <div className="w-full h-full bg-indigo-950 rounded-3xl p-8 flex flex-col gap-6 relative overflow-hidden">
          <div className="bg-white/10 rounded-2xl p-4 flex items-center gap-3 border border-white/10">
            <Sparkles className="h-4 w-4 text-indigo-300" />
            <div className="text-white text-sm font-medium italic">"Why is my W3 forecast lower than expected?"</div>
          </div>
          <div className="space-y-4">
            <div className="flex gap-3">
              <div className="h-8 w-8 rounded-lg bg-indigo-500 flex items-center justify-center text-white font-black text-xs">G</div>
              <div className="bg-white/5 border border-white/10 p-4 rounded-2xl flex-1 space-y-3">
                <p className="text-indigo-100 text-xs leading-relaxed">
                  Analyzing 1,684 invoices... I found a **regime shift** in 'Enterprise-SaaS' customers. Average payment delay has increased by **4.2 days** this month.
                </p>
                <div className="flex gap-2">
                  <div className="px-2 py-1 rounded-md bg-indigo-500/20 text-[9px] font-black text-indigo-300 uppercase border border-indigo-500/30">Ref: #INV-221</div>
                  <div className="px-2 py-1 rounded-md bg-indigo-500/20 text-[9px] font-black text-indigo-300 uppercase border border-indigo-500/30">MAE: 0.8d</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )
    }
  ];

  return (
    <div className="min-h-screen bg-white text-slate-900 font-sans selection:bg-blue-100 antialiased overflow-x-hidden">
      {/* Translucent Navigation */}
      <nav className="fixed top-0 left-0 right-0 z-50 bg-white/70 backdrop-blur-xl border-b border-slate-100 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-10">
            <Link href="/" className="flex items-center gap-2">
              <div className="h-7 w-7 rounded-lg bg-slate-900 flex items-center justify-center text-white font-black text-sm">G</div>
              <span className="font-bold text-xl tracking-tighter text-slate-900">gitto</span>
            </Link>
            <div className="hidden md:flex items-center gap-8 text-[13px] font-bold text-slate-500 uppercase tracking-widest">
              <button className="hover:text-slate-900 transition-colors">Features</button>
              <button className="hover:text-slate-900 transition-colors">Industries</button>
              <button className="hover:text-slate-900 transition-colors">Resources</button>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <Link href="/app" className="text-[14px] font-bold text-slate-900 hover:text-slate-600 transition-colors px-4">Sign In</Link>
            <Link href="/contact" className="hidden sm:block">
              <Button variant="outline" className="border-slate-200 text-slate-900 rounded-full px-6 h-10 text-[13px] font-bold">
                Product Tour
              </Button>
            </Link>
            <Link href="/app">
              <Button className="bg-slate-900 text-white hover:bg-slate-800 rounded-full px-6 h-10 text-[13px] font-bold shadow-lg shadow-slate-900/10">
                Book a Demo
              </Button>
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero Section - Rings Aesthetic */}
      <section className="relative pt-48 pb-20 px-6">
        <div className="max-w-5xl mx-auto text-center space-y-10">
          <div className="inline-flex items-center px-4 py-1.5 rounded-full bg-slate-50 border border-slate-100 text-[11px] font-black uppercase tracking-[0.2em] text-slate-500">
            Intelligent Cash Command Center
          </div>
          <h1 className="text-[64px] md:text-[92px] font-bold tracking-tight text-slate-900 leading-[0.95]">
            An intelligent <span className="text-slate-400 font-medium italic">Cash Truth Layer</span>
          </h1>
          <p className="text-[22px] text-slate-500 font-medium max-w-3xl mx-auto leading-relaxed">
            An all-in-one data enriched treasury layer to identify, access, and win more liquidity opportunities. Move from theoretical forecasts to bank-anchored reality.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-6">
            <Link href="/app">
              <Button className="bg-slate-900 text-white hover:bg-slate-800 rounded-full px-12 h-16 text-[17px] font-black shadow-2xl shadow-slate-900/20 transition-all hover:scale-[1.02]">
                Book a Demo
              </Button>
            </Link>
            <Link href="/contact">
              <Button variant="outline" className="border-slate-200 text-slate-900 rounded-full px-12 h-16 text-[17px] font-black hover:bg-slate-50 transition-all">
                Product Tour
              </Button>
            </Link>
          </div>
        </div>
      </section>

      {/* The Living Dashboard (Rings Style) */}
      <section className="px-6 py-20 bg-slate-50/50">
        <div className="max-w-6xl mx-auto">
          <div className="bg-white rounded-[40px] border border-slate-200 shadow-[0_32px_64px_-16px_rgba(0,0,0,0.1)] overflow-hidden flex flex-col md:flex-row h-[750px]">
            {/* Sidebar Mockup */}
            <div className="w-72 border-r border-slate-100 p-8 hidden md:block space-y-10 bg-slate-50/30">
              <div className="space-y-6 text-left">
                <h3 className="text-xl font-bold text-slate-900">Good morning, Ayush</h3>
                <div className="space-y-2">
                  <div className="h-9 w-full bg-white border border-slate-100 rounded-xl flex items-center px-3 gap-3 shadow-sm">
                    <Search className="h-4 w-4 text-slate-400" />
                    <div className="h-2 w-24 bg-slate-100 rounded-full" />
                  </div>
                </div>
              </div>
              <div className="space-y-6">
                <div className="px-2 text-[10px] font-black uppercase tracking-[0.2em] text-slate-400">Discover Gitto</div>
                <div className="space-y-1.5">
                  {[
                    { label: 'CFO Desk', icon: Layout, active: true },
                    { label: '13-Week Grid', icon: Calendar },
                    { label: 'Banking Truth', icon: Landmark },
                    { label: 'Analyst RAG', icon: Sparkles },
                    { label: 'Operations', icon: Briefcase },
                  ].map((item, i) => (
                    <div key={i} className={`h-11 w-full rounded-2xl flex items-center px-4 gap-4 transition-all ${item.active ? 'bg-slate-900 text-white shadow-xl shadow-slate-900/20' : 'text-slate-400 hover:bg-white hover:text-slate-600'}`}>
                      <item.icon className={`h-4 w-4 ${item.active ? 'text-white' : 'text-slate-300'}`} />
                      <span className="text-[13px] font-bold tracking-tight">{item.label}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Main Canvas Mockup */}
            <div className="flex-1 p-10 overflow-y-auto space-y-12 text-left bg-white relative">
              <div className="flex items-center justify-between">
                <div className="space-y-1">
                  <h2 className="text-2xl font-black tracking-tight text-slate-900">Liquidity Overview</h2>
                  <p className="text-[11px] font-bold text-slate-400 uppercase tracking-widest">Group Consolidated · Live Sync</p>
                </div>
                <Button variant="outline" size="sm" className="rounded-full gap-2 border-slate-100 text-[11px] font-black h-10 px-5 uppercase tracking-widest">
                  <Plus className="h-3 w-3" /> Add Widget
                </Button>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-10">
                {/* Schedule Card (Rings Schedule Match) */}
                <Card className="rounded-[32px] border-slate-100 shadow-sm overflow-hidden bg-white hover:shadow-xl transition-shadow duration-500">
                  <CardContent className="p-8 space-y-8">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <Calendar className="h-5 w-5 text-slate-900" />
                        <span className="font-black text-lg tracking-tight">Schedule</span>
                      </div>
                      <span className="text-[11px] font-black text-slate-400 uppercase tracking-[0.2em]">December 2025</span>
                    </div>
                    <div className="space-y-5">
                      {[
                        { time: 'In 15 mins', label: 'Payment Run Sync', insights: '12 Insights', color: 'bg-blue-50 text-blue-600' },
                        { time: 'In 2 hours', label: 'Reconciliation Review', insights: '8 Insights', color: 'bg-emerald-50 text-emerald-600' },
                        { time: 'In 4 hours', label: 'Board Cash Briefing', insights: '15 Insights', color: 'bg-indigo-50 text-indigo-600' },
                      ].map((item, i) => (
                        <div key={i} className="group flex items-center justify-between p-5 rounded-3xl border border-slate-50 hover:border-slate-200 hover:bg-slate-50/50 transition-all cursor-pointer">
                          <div className="space-y-1.5">
                            <div className="flex items-center gap-2">
                              <span className="text-[11px] font-black text-slate-400 uppercase tracking-widest">{item.time}</span>
                              <div className="h-1 w-1 rounded-full bg-slate-200" />
                              <span className="text-sm font-bold text-slate-900 group-hover:text-blue-600 transition-colors">{item.label}</span>
                            </div>
                          </div>
                          <div className={`px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-widest ${item.color}`}>
                            {item.insights}
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>

                {/* Key Liquidity Updates (Rings Relationship Match) */}
                <Card className="rounded-[32px] border-slate-100 shadow-sm overflow-hidden bg-white hover:shadow-xl transition-shadow duration-500">
                  <CardContent className="p-8 space-y-8">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <TrendingUp className="h-5 w-5 text-slate-900" />
                        <span className="font-black text-lg tracking-tight">Key Liquidity Updates</span>
                      </div>
                      <span className="text-[11px] font-black text-blue-600 uppercase tracking-widest cursor-pointer hover:text-blue-700 transition-colors">See all</span>
                    </div>
                    <div className="space-y-6">
                      {[
                        { name: 'Siemens AG', role: 'Strategic Enterprise', status: 'Payment Reconciled · Today', insights: '10 Insights', icon: 'S', color: 'bg-slate-900' },
                        { name: 'Emirates Group', role: 'Main Inflow Driver', status: 'Followup Overdue · 3 days ago', insights: '12 Insights', icon: 'E', color: 'bg-indigo-600' },
                        { name: 'Standard Chartered', role: 'Treasury Partner', status: 'New FX Risk Detected', insights: '16 Insights', icon: 'S', color: 'bg-emerald-600' },
                      ].map((update, i) => (
                        <div key={i} className="flex items-start gap-5 group cursor-pointer">
                          <div className={`h-12 w-12 rounded-2xl ${update.color} flex items-center justify-center text-white font-black text-sm shadow-lg group-hover:scale-110 transition-transform`}>
                            {update.icon}
                          </div>
                          <div className="flex-1 space-y-1">
                            <div className="flex items-center justify-between">
                              <span className="text-[15px] font-black text-slate-900 group-hover:text-blue-600 transition-colors">{update.name}</span>
                              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">{update.insights}</span>
                            </div>
                            <p className="text-[12px] text-slate-400 font-bold uppercase tracking-tight">{update.role}</p>
                            <p className={`text-[11px] font-black pt-1 ${update.status.includes('Overdue') ? 'text-red-500' : 'text-emerald-500'} uppercase tracking-widest`}>{update.status}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* High-Fidelity Workflow Videos Section */}
      <section className="px-6 py-32 max-w-7xl mx-auto space-y-24">
        <div className="text-center space-y-6">
          <h2 className="text-[48px] md:text-[64px] font-black tracking-tighter leading-tight text-slate-900">Experience the Workflow</h2>
          <p className="text-xl text-slate-500 font-medium max-w-2xl mx-auto italic">High-fidelity automation for the modern finance stack.</p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-20 items-center">
          <div className="space-y-12">
            {workflows.map((wf, i) => (
              <div 
                key={i} 
                className={`p-10 rounded-[40px] cursor-pointer transition-all duration-500 border ${activeWorkflow === i ? 'bg-white border-slate-200 shadow-2xl' : 'bg-slate-50 border-transparent opacity-50 grayscale hover:opacity-100 hover:grayscale-0'}`}
                onClick={() => setActiveWorkflow(i)}
              >
                <div className="space-y-4 text-left">
                  <div className="flex items-center gap-4">
                    <div className={`h-10 w-10 rounded-xl flex items-center justify-center ${activeWorkflow === i ? 'bg-slate-900 text-white' : 'bg-slate-200 text-slate-400'}`}>
                      {i === 0 ? <RefreshCcw className="h-5 w-5" /> : <Sparkles className="h-5 w-5" />}
                    </div>
                    <h3 className="text-2xl font-black tracking-tight">{wf.title}</h3>
                  </div>
                  <p className="text-slate-500 text-lg font-medium leading-relaxed">{wf.desc}</p>
                </div>
              </div>
            ))}
          </div>
          <div className="aspect-square w-full transition-all duration-700 animate-in fade-in zoom-in">
            {workflows[activeWorkflow].videoMock}
          </div>
        </div>
      </section>

      {/* The 12 Pillars of Finance Excellence (Rings Feature Grid) */}
      <section className="px-6 py-32 max-w-7xl mx-auto border-t border-slate-100">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-10">
          {[
            { title: "7k+ Integrations", desc: "Native integrations to Snowflake, SAP, Oracle, Netsuite, and all major global banks.", icon: <Database /> },
            { title: "Rich Notes & Files", desc: "Never lose context again - capture and access every detail that matters to your deals.", icon: <FileText /> },
            { title: "Smart Privacy", desc: "Intuitive privacy controls ensure that sensitive treasury data stays... private.", icon: <Lock /> },
            { title: "AI Natural Language Search", desc: "Ask anything, find everything - your Gitto data responds to plain English.", icon: <Search /> },
            { title: "Track Cash Movements", desc: "Don't miss an opportunity - view and track your global liquidity in motion.", icon: <TrendingUp /> },
            { title: "Proprietary AI Scoring", desc: "Stop guessing which collections matter - our AI scores customers and risks.", icon: <Zap /> },
            { title: "Team & Workspaces", desc: "One platform, one truth - align your entire finance team around shared intelligence.", icon: <Users /> },
            { title: "Customization", desc: "Your business, your rules - configure Gitto to match how you actually work.", icon: <Filter /> },
            { title: "Project Management", desc: "Powerful treasury management with fully customizable project & task hierarchies.", icon: <Briefcase /> },
            { title: "Dedicated CSM in Slack", desc: "Expert help, zero friction - get answers without leaving your workflow.", icon: <MessageSquare /> },
            { title: "iOS App", desc: "A powerful iOS app to manage your cash and opportunities on the go.", icon: <Globe /> },
            { title: "Chrome Extension", desc: "See Gitto data wherever you browse with our real-time Chrome Extension.", icon: <Plus /> }
          ].map((feature, i) => (
            <Card key={i} className="border-0 shadow-none hover:bg-slate-50 transition-all duration-500 p-10 space-y-6 rounded-[32px] group text-left">
              <div className="h-14 w-14 rounded-2xl bg-white border border-slate-100 flex items-center justify-center text-slate-900 shadow-sm group-hover:scale-110 group-hover:shadow-xl transition-all">
                {feature.icon}
              </div>
              <div className="space-y-3">
                <h3 className="font-black text-xl text-slate-900">{feature.title}</h3>
                <p className="text-slate-500 text-[15px] font-medium leading-relaxed italic opacity-80 group-hover:opacity-100 transition-opacity">
                  {feature.desc}
                </p>
              </div>
            </Card>
          ))}
        </div>
      </section>

      {/* Testimonial Section - Rings Styled Quote */}
      <section className="px-6 py-40 bg-slate-900 text-white relative overflow-hidden">
        <div className="absolute top-0 right-0 w-1/2 h-full bg-blue-600/10 blur-[150px]" />
        <div className="absolute bottom-0 left-0 w-1/2 h-full bg-emerald-600/5 blur-[150px]" />
        <div className="max-w-4xl mx-auto text-center space-y-16 relative z-10">
          <div className="flex justify-center gap-1">
            {[1,2,3,4,5].map(i => <Sparkles key={i} className="h-6 w-6 text-blue-400 fill-blue-400" />)}
          </div>
          <h2 className="text-[36px] md:text-[52px] font-bold leading-tight italic tracking-tight text-indigo-100">
            "I've been a treasury nerd and community builder both in business and personal and have been looking for a tool like this my whole career. This changes everything."
          </h2>
          <div className="space-y-3">
            <div className="h-16 w-16 rounded-full bg-slate-800 mx-auto border-2 border-white/10" />
            <div>
              <p className="text-xl font-black tracking-tight">Raphael Leopold</p>
              <p className="text-sm font-bold text-slate-500 uppercase tracking-widest">Partner, Coolwater Capital</p>
            </div>
          </div>
        </div>
      </section>

      {/* FAQ Section - Rings Styled */}
      <section className="px-6 py-32 max-w-3xl mx-auto space-y-20">
        <h2 className="text-[48px] font-black tracking-tighter text-center text-slate-900">Frequently Asked Questions</h2>
        <div className="space-y-2">
          {[
            "What makes Gitto different from traditional Treasury tools?",
            "Do I have to give up my existing ERP?",
            "What is 'Liquidity Power'?",
            "How can I use Gitto to prepare for board meetings?",
            "How does Gitto protect my data privacy?",
            "How do I get started with Gitto AI in 5 minutes?",
            "What is the level of dedicated support?",
            "Can I access Gitto data on the go?"
          ].map((q, i) => (
            <div key={i} className="group border-b border-slate-100 py-8 flex items-center justify-between cursor-pointer hover:border-slate-300 transition-all">
              <span className="text-[20px] font-bold text-slate-900 group-hover:text-blue-600 transition-colors text-left">{q}</span>
              <Plus className="h-6 w-6 text-slate-300 group-hover:text-blue-600 group-hover:rotate-90 transition-all duration-500" />
            </div>
          ))}
        </div>
      </section>

      {/* Final CTA - Magic Section */}
      <section className="px-6 py-40 text-center bg-slate-50 border-t border-slate-100 relative overflow-hidden">
        <div className="max-w-4xl mx-auto space-y-12 relative z-10">
          <h2 className="text-[56px] md:text-[84px] font-bold tracking-tight leading-[0.95] text-slate-900">Feel the magic today</h2>
          <p className="text-2xl text-slate-500 font-bold italic">Make every connection count.</p>
          <Link href="/app">
            <Button className="bg-slate-900 text-white hover:bg-slate-800 rounded-full px-16 h-20 text-2xl font-black shadow-2xl shadow-slate-900/20 transition-all hover:scale-[1.05] active:scale-[0.95]">
              Book a Demo
            </Button>
          </Link>
        </div>
      </section>

      {/* Footer - Rings Aesthetic */}
      <footer className="px-6 py-24 bg-white border-t border-slate-100">
        <div className="max-w-7xl mx-auto grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-20">
          <div className="space-y-8 text-left">
            <Link href="/" className="flex items-center gap-2">
              <div className="h-8 w-8 rounded-lg bg-slate-900 flex items-center justify-center text-white font-black text-sm">G</div>
              <span className="font-black text-2xl tracking-tighter text-slate-900">gitto</span>
            </Link>
            <div className="space-y-4">
              <p className="text-slate-400 font-bold text-sm uppercase tracking-widest">© 2025 Gitto Inc.</p>
              <p className="text-slate-400 font-bold text-sm hover:text-slate-900 transition-colors cursor-pointer">info@gitto.ai</p>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-12 lg:col-span-3">
            <div className="space-y-8 text-left">
              <h4 className="font-black text-[11px] text-slate-900 uppercase tracking-[0.3em]">Command Desks</h4>
              <ul className="space-y-5 text-[15px] text-slate-400 font-bold">
                <li className="hover:text-slate-900 cursor-pointer transition-colors">CFO Overview</li>
                <li className="hover:text-slate-900 cursor-pointer transition-colors">13-Week Grid</li>
                <li className="hover:text-slate-900 cursor-pointer transition-colors">Banking Truth</li>
                <li className="hover:text-slate-900 cursor-pointer transition-colors">Analyst RAG</li>
              </ul>
            </div>
            <div className="space-y-8 text-left">
              <h4 className="font-black text-[11px] text-slate-900 uppercase tracking-[0.3em]">Company</h4>
              <ul className="space-y-5 text-[15px] text-slate-400 font-bold">
                <li className="hover:text-slate-900 cursor-pointer transition-colors">About Us</li>
                <li className="hover:text-slate-900 cursor-pointer transition-colors">Careers</li>
                <li className="hover:text-slate-900 cursor-pointer transition-colors">Privacy Policy</li>
                <li className="hover:text-slate-900 cursor-pointer transition-colors">Terms of Service</li>
              </ul>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}

const RefreshCcw = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
    <path d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" /><path d="M3 3v5h5" /><path d="M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16" /><path d="M16 21v-5h5" />
  </svg>
);
