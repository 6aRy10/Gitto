'use client';

import { useState } from 'react';
import Link from "next/link";
import { 
  ArrowRight, CheckCircle2, Shield, BarChart3, TrendingUp, AlertCircle, 
  Landmark, Users, Search, Bell, Calendar, ChevronRight, MessageSquare,
  Lock, Zap, Database, Globe, Briefcase, Plus, Sparkles, Filter
} from "lucide-react";
import { Button } from "../components/ui/button";
import { Card, CardContent } from "../components/ui/card";

export default function Landing() {
  const [activeTab, setActiveTab] = useState('features');

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
              <button className="hover:text-slate-900 transition-colors">Features</button>
              <button className="hover:text-slate-900 transition-colors">Industries</button>
              <button className="hover:text-slate-900 transition-colors">Resources</button>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <Link href="/app" className="text-[14px] font-medium text-slate-900 hover:text-slate-600 transition-colors px-4">Sign In</Link>
            <Link href="/contact" className="hidden sm:block">
              <Button variant="outline" className="border-slate-200 text-slate-900 rounded-full px-6 h-10 text-[14px] font-semibold">
                Product Tour
              </Button>
            </Link>
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
        <div className="max-w-4xl mx-auto text-center space-y-8">
          <div className="inline-flex items-center px-4 py-1.5 rounded-full bg-slate-50 border border-slate-100 text-[13px] font-semibold text-slate-600">
            Introducing Gitto Intelligence
          </div>
          <h1 className="text-[56px] md:text-[84px] font-bold tracking-tight text-slate-900 leading-[1.05]">
            An intelligent <span className="text-slate-400 font-medium italic">Cash Command Center</span>
          </h1>
          <p className="text-[19px] text-slate-500 font-medium max-w-2xl mx-auto leading-relaxed">
            An all-in-one data enriched treasury layer (or CRM for your cash) to identify, access, and win more liquidity opportunities.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-4">
            <Link href="/app">
              <Button className="bg-slate-900 text-white hover:bg-slate-800 rounded-full px-10 h-14 text-[16px] font-bold shadow-xl shadow-slate-900/10">
                Book a Demo
              </Button>
            </Link>
            <Link href="/contact">
              <Button variant="outline" className="border-slate-200 text-slate-900 rounded-full px-10 h-14 text-[16px] font-bold hover:bg-slate-50">
                Product Tour
              </Button>
            </Link>
          </div>
        </div>
      </section>

      {/* Dashboard Mockup (Rings Style) */}
      <section className="px-6 py-20 bg-slate-50/50">
        <div className="max-w-6xl mx-auto">
          <div className="bg-white rounded-[32px] border border-slate-200 shadow-2xl overflow-hidden flex flex-col md:flex-row h-[700px]">
            {/* Sidebar Mockup */}
            <div className="w-64 border-r border-slate-100 p-6 hidden md:block space-y-8 bg-slate-50/30">
              <div className="space-y-4">
                <div className="h-4 w-24 bg-slate-100 rounded-full" />
                <div className="space-y-2">
                  <div className="h-8 w-full bg-white border border-slate-100 rounded-lg flex items-center px-3 gap-2">
                    <Search className="h-3.5 w-3.5 text-slate-400" />
                    <div className="h-2 w-16 bg-slate-50 rounded-full" />
                  </div>
                </div>
              </div>
              <div className="space-y-4">
                <div className="h-2 w-16 bg-slate-100 rounded-full ml-2" />
                <div className="space-y-1">
                  {[1,2,3,4,5].map(i => (
                    <div key={i} className={`h-10 w-full rounded-xl flex items-center px-3 gap-3 ${i === 1 ? 'bg-white shadow-sm border border-slate-100' : 'text-slate-400'}`}>
                      <div className={`h-4 w-4 rounded ${i === 1 ? 'bg-slate-900' : 'bg-slate-100'}`} />
                      <div className={`h-2 w-20 rounded-full ${i === 1 ? 'bg-slate-900' : 'bg-slate-100'}`} />
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Main Content Mockup */}
            <div className="flex-1 p-8 overflow-y-auto space-y-10">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-xl font-bold text-slate-900">Good morning, Ayush</h2>
                  <p className="text-sm text-slate-400 font-medium">Discover Gitto Insights</p>
                </div>
                <div className="flex items-center gap-3">
                  <Button variant="outline" size="sm" className="rounded-full gap-2 border-slate-100 text-[12px] h-9">
                    <Plus className="h-3.5 w-3.5" /> Add Widget
                  </Button>
                </div>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                {/* Schedule Card */}
                <Card className="rounded-3xl border border-slate-100 shadow-sm overflow-hidden">
                  <CardContent className="p-6 space-y-6">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Calendar className="h-4 w-4 text-slate-900" />
                        <span className="font-bold text-[15px]">Schedule</span>
                      </div>
                      <span className="text-[12px] font-bold text-slate-400 uppercase tracking-widest">December 2025</span>
                    </div>
                    <div className="space-y-4">
                      {[
                        { time: 'In 15 mins', label: 'Payment Run Review', insights: '12 Insights', color: 'bg-blue-50 text-blue-600' },
                        { time: 'In 2 hours', label: 'Reconciliation Sync', insights: '8 Insights', color: 'bg-emerald-50 text-emerald-600' },
                        { time: 'In 4 hours', label: 'Cash Flow Forecast', insights: '15 Insights', color: 'bg-indigo-50 text-indigo-600' },
                      ].map((item, i) => (
                        <div key={i} className="flex items-center justify-between p-4 rounded-2xl border border-slate-50 hover:bg-slate-50 transition-colors">
                          <div className="space-y-1">
                            <div className="flex items-center gap-2">
                              <span className="text-[11px] font-bold text-slate-400">{item.time}</span>
                              <span className="h-1 w-1 rounded-full bg-slate-200" />
                              <span className="text-[13px] font-bold text-slate-900">{item.label}</span>
                            </div>
                          </div>
                          <div className={`px-3 py-1 rounded-full text-[11px] font-bold ${item.color}`}>
                            {item.insights}
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>

                {/* Key Relationship Updates (Liquidity) */}
                <Card className="rounded-3xl border border-slate-100 shadow-sm overflow-hidden">
                  <CardContent className="p-6 space-y-6">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <TrendingUp className="h-4 w-4 text-slate-900" />
                        <span className="font-bold text-[15px]">Key Liquidity Updates</span>
                      </div>
                      <span className="text-[12px] font-bold text-blue-600 cursor-pointer">See all</span>
                    </div>
                    <div className="space-y-5">
                      {[
                        { name: 'Emirates Group', role: 'Main Enterprise Customer', status: 'Payment Overdue · 3 days ago', insights: '10 Insights', icon: 'E' },
                        { name: 'Kuwait Finance', role: 'Strategic Partner', status: 'Account Balance Low · Today', insights: '12 Insights', icon: 'K' },
                        { name: 'Standard Chartered', role: 'Main Banking Partner', status: 'New FX Risk Detected', insights: '16 Insights', icon: 'S' },
                      ].map((update, i) => (
                        <div key={i} className="flex items-start gap-4">
                          <div className="h-10 w-10 rounded-xl bg-slate-900 flex items-center justify-center text-white font-black text-xs">
                            {update.icon}
                          </div>
                          <div className="flex-1 space-y-0.5">
                            <div className="flex items-center justify-between">
                              <span className="text-[14px] font-bold text-slate-900">{update.name}</span>
                              <span className="text-[11px] font-bold text-slate-400">{update.insights}</span>
                            </div>
                            <p className="text-[12px] text-slate-400 font-medium">{update.role}</p>
                            <p className="text-[11px] text-red-500 font-bold pt-1">{update.status}</p>
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

      {/* Features Grid (Rings Style) */}
      <section className="px-6 py-32 max-w-7xl mx-auto">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
          {[
            { 
              title: "7k+ Integrations", 
              desc: "Native integrations to Snowflake, SAP, Oracle, Netsuite, and all major global banks.",
              icon: <Database className="h-5 w-5" /> 
            },
            { 
              title: "Rich Notes & Files", 
              desc: "Never lose context again - capture and access every detail that matters to your cash.",
              icon: <MessageSquare className="h-5 w-5" /> 
            },
            { 
              title: "Smart Privacy", 
              desc: "Intuitive privacy controls ensure that sensitive treasury data stays... private.",
              icon: <Lock className="h-5 w-5" /> 
            },
            { 
              title: "AI & Natural Language Search", 
              desc: "Ask anything, find everything - your Gitto data responds to plain English.",
              icon: <Search className="h-5 w-5" /> 
            },
            { 
              title: "Track Cash Movements", 
              desc: "Don't miss an opportunity - view and track your global liquidity in motion.",
              icon: <TrendingUp className="h-5 w-5" /> 
            },
            { 
              title: "Proprietary AI Scoring", 
              desc: "Stop guessing which collections matter - our AI scores customers and risks.",
              icon: <Zap className="h-5 w-5" /> 
            },
            { 
              title: "Team & Workspaces", 
              desc: "One platform, one truth - align your entire finance team around shared intelligence.",
              icon: <Users className="h-5 w-5" /> 
            },
            { 
              title: "Customization", 
              desc: "Your business, your rules - configure Gitto to match how you actually work.",
              icon: <Filter className="h-5 w-5" /> 
            },
            { 
              title: "Project Management", 
              desc: "Powerful treasury management with fully customizable project & task hierarchies.",
              icon: <Briefcase className="h-5 w-5" /> 
            },
            { 
              title: "Dedicated CSM in Slack", 
              desc: "Expert help, zero friction - get answers without leaving your workflow.",
              icon: <MessageSquare className="h-5 w-5" /> 
            },
            { 
              title: "iOS App", 
              desc: "A powerful iOS app to manage your cash and opportunities on the go.",
              icon: <Globe className="h-5 w-5" /> 
            },
            { 
              title: "Chrome Extension", 
              desc: "See Gitto data wherever you browse with our real-time Chrome Extension.",
              icon: <Plus className="h-5 w-5" /> 
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

      {/* Testimonial (Rings Style) */}
      <section className="px-6 py-32 bg-slate-900 text-white overflow-hidden relative">
        <div className="absolute top-0 right-0 w-1/3 h-full bg-blue-600/10 blur-[120px]" />
        <div className="max-w-4xl mx-auto text-center space-y-12 relative z-10">
          <h2 className="text-[32px] md:text-[42px] font-bold leading-tight italic">
            "I've been a treasury nerd and community builder both in business and personal and have been looking for a tool like this my whole career. This changes everything."
          </h2>
          <div className="space-y-2">
            <p className="text-[18px] font-bold">Raphael Leopold</p>
            <p className="text-[15px] text-slate-400 font-medium">Partner, Coolwater Capital</p>
          </div>
        </div>
      </section>

      {/* Industries Section (Rings Style) */}
      <section className="px-6 py-32 max-w-7xl mx-auto space-y-20">
        <div className="text-center space-y-4">
          <h2 className="text-[42px] font-bold tracking-tight">The platform for finance excellence</h2>
          <p className="text-slate-500 text-lg font-medium">Powering the next generation of global companies.</p>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            'Venture Capital', 'Private Equity', 'Sales & BD', 'Investment Banking',
            'Startups', 'Fund of Funds', 'Recruiting', 'Wealth Management'
          ].map((industry, i) => (
            <div key={i} className="p-10 rounded-[32px] bg-slate-50 flex flex-col items-center justify-center text-center space-y-4 hover:bg-white hover:shadow-xl hover:-translate-y-1 transition-all cursor-pointer border border-transparent hover:border-slate-100">
              <span className="font-bold text-[17px] text-slate-900">{industry}</span>
            </div>
          ))}
        </div>
      </section>

      {/* FAQ Section (Rings Style) */}
      <section className="px-6 py-32 max-w-3xl mx-auto space-y-16">
        <h2 className="text-[42px] font-bold tracking-tight text-center">Frequently Asked Questions</h2>
        <div className="space-y-4">
          {[
            "What makes Gitto different from traditional Treasury tools?",
            "Do I have to give up my existing ERP?",
            "What is Liquidity Power?",
            "How can I use Gitto to prepare for board meetings?",
            "How does Gitto protect my privacy?",
            "How do I get started with Gitto AI in 5 minutes?",
            "What is the level of support?",
            "Can I access Gitto data on the go?"
          ].map((q, i) => (
            <div key={i} className="group border-b border-slate-100 py-6 flex items-center justify-between cursor-pointer">
              <span className="text-[18px] font-bold text-slate-900 group-hover:text-blue-600 transition-colors text-left">{q}</span>
              <Plus className="h-5 w-5 text-slate-400 group-hover:text-blue-600" />
            </div>
          ))}
        </div>
      </section>

      {/* Final CTA (Rings Style) */}
      <section className="px-6 py-32 text-center bg-slate-50 border-t border-slate-100">
        <div className="max-w-3xl mx-auto space-y-10">
          <h2 className="text-[48px] md:text-[64px] font-bold tracking-tight leading-tight">Feel the magic today</h2>
          <p className="text-xl text-slate-500 font-bold">Make every connection count.</p>
          <Link href="/app">
            <Button className="bg-slate-900 text-white hover:bg-slate-800 rounded-full px-16 h-18 text-xl font-bold shadow-2xl shadow-slate-900/20">
              Book a Demo
            </Button>
          </Link>
        </div>
      </section>

      {/* Footer (Rings Style) */}
      <footer className="px-6 py-20 bg-white border-t border-slate-100">
        <div className="max-w-7xl mx-auto grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-16">
          <div className="space-y-8">
            <Link href="/" className="flex items-center gap-2">
              <div className="h-7 w-7 rounded-lg bg-slate-900 flex items-center justify-center text-white font-black text-sm">G</div>
              <span className="font-bold text-xl tracking-tighter text-slate-900">gitto</span>
            </Link>
            <p className="text-slate-400 font-bold text-sm">© 2025 Gitto Inc.</p>
            <p className="text-slate-400 font-bold text-sm">info@gitto.ai</p>
          </div>
          <div className="grid grid-cols-2 gap-8 lg:col-span-3">
            <div className="space-y-6 text-left">
              <h4 className="font-bold text-sm text-slate-900">Features</h4>
              <ul className="space-y-4 text-sm text-slate-400 font-bold">
                <li className="hover:text-slate-900 cursor-pointer text-left">Integrations</li>
                <li className="hover:text-slate-900 cursor-pointer text-left">Blog</li>
                <li className="hover:text-slate-900 cursor-pointer text-left">Compare</li>
              </ul>
            </div>
            <div className="space-y-6 text-left">
              <h4 className="font-bold text-sm text-slate-900">Company</h4>
              <ul className="space-y-4 text-sm text-slate-400 font-bold">
                <li className="hover:text-slate-900 cursor-pointer text-left">About</li>
                <li className="hover:text-slate-900 cursor-pointer text-left">Careers</li>
                <li className="hover:text-slate-900 cursor-pointer text-left">Privacy Policy</li>
              </ul>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
