'use client';

import { useState, useEffect } from 'react';
import Link from "next/link";
import { Button } from "../../components/ui/button";

// ═══════════════════════════════════════════════════════════════════════════════
// ANIMATED COUNTER COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════
const AnimatedCounter = ({ end, suffix = '', prefix = '', duration = 2000 }: { end: number; suffix?: string; prefix?: string; duration?: number }) => {
  const [count, setCount] = useState(0);
  
  useEffect(() => {
    let startTime: number;
    const animate = (timestamp: number) => {
      if (!startTime) startTime = timestamp;
      const progress = Math.min((timestamp - startTime) / duration, 1);
      setCount(Math.floor(progress * end));
      if (progress < 1) requestAnimationFrame(animate);
    };
    requestAnimationFrame(animate);
  }, [end, duration]);
  
  return <span>{prefix}{count.toLocaleString()}{suffix}</span>;
};

// ═══════════════════════════════════════════════════════════════════════════════
// CUSTOM ICONS
// ═══════════════════════════════════════════════════════════════════════════════

const ArrowRightIcon = ({ className = "w-4 h-4" }: { className?: string }) => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className={className}>
    <path d="M5 12h14M12 5l7 7-7 7" />
  </svg>
);

const ArrowDownIcon = ({ className = "w-4 h-4" }: { className?: string }) => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className={className}>
    <path d="M12 5v14M5 12l7 7 7-7" />
  </svg>
);

export default function About() {
  const [activePhilosophy, setActivePhilosophy] = useState(0);

  const philosophyItems = [
    {
      id: 'determinism',
      title: 'Radical Determinism',
      subtitle: 'Every number has a source',
      content: 'We reject probabilistic hand-waving. When Gitto shows €1.2M in Week 4, you can click through to the exact 47 invoices, 12 recurring contracts, and 3 one-time payments that compose it. The forecast is not a prediction—it is an aggregation of known commitments with behavioral timing adjustments.',
      stat: '100%',
      statLabel: 'Traceable to source documents',
    },
    {
      id: 'uncertainty',
      title: 'Honest Uncertainty',
      subtitle: 'We show what we don\'t know',
      content: 'Most treasury systems hide uncertainty behind false precision. Gitto maintains an explicit Unknown Bucket for cash that cannot be explained—whether due to missing FX rates, unreconciled transactions, or data gaps. This bucket is not a bug; it is a feature that keeps CFOs honest about their actual visibility.',
      stat: '97%',
      statLabel: 'Average cash explained',
    },
    {
      id: 'behavioral',
      title: 'Behavioral Realism',
      subtitle: 'Customers pay when they pay',
      content: 'Invoice due dates are legal fictions. Enterprise customers pay based on their internal payment runs, approval bottlenecks, and liquidity constraints. Gitto learns each counterparty\'s actual payment behavior—their median delay, variance, and sensitivity to amount size—to forecast when cash will actually arrive.',
      stat: '14.3',
      statLabel: 'Days average hidden delay detected',
    },
    {
      id: 'immutability',
      title: 'Immutable History',
      subtitle: 'Locked means locked',
      content: 'When you close a weekly snapshot, the inputs and outputs freeze permanently. Six months later, you can reproduce exactly what the system showed that Monday morning. This is not version control—it is audit-grade immutability required for external auditors and board-level accountability.',
      stat: '52',
      statLabel: 'Weekly snapshots retained',
    },
  ];

  return (
    <div className="min-h-screen bg-[#0A0A0F] text-white font-sans antialiased">
      
      {/* ═══════════════════════════════════════════════════════════════════════════════
          NAVIGATION
          ═══════════════════════════════════════════════════════════════════════════════ */}
      <nav className="fixed top-0 left-0 right-0 z-50 bg-[#0A0A0F]/90 backdrop-blur-xl border-b border-white/5">
        <div className="max-w-[1400px] mx-auto px-8 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-3 group">
            <div className="h-9 w-9 rounded-xl bg-white flex items-center justify-center text-[#0A0A0F] font-serif font-semibold text-lg tracking-tight group-hover:scale-105 transition-transform">
              G
            </div>
            <span className="font-serif font-semibold text-xl text-white tracking-tight">Gitto</span>
          </Link>
          <div className="hidden md:flex items-center gap-10 text-sm tracking-wide">
            <Link href="/#primitives" className="text-white/50 hover:text-white transition-colors">product</Link>
            <Link href="/#trust" className="text-white/50 hover:text-white transition-colors">trust</Link>
            <Link href="/#integrations" className="text-white/50 hover:text-white transition-colors">integrations</Link>
            <Link href="/about" className="text-white hover:text-white transition-colors">about</Link>
          </div>
          <div className="flex items-center gap-4">
            <Link href="/app" className="text-sm text-white/50 hover:text-white transition-colors hidden sm:block tracking-wide">
              sign in
            </Link>
            <Link href="/contact">
              <Button className="button-glow bg-white text-[#0A0A0F] hover:bg-white/90 text-sm px-6 h-11 rounded-xl font-medium tracking-wide hover:-translate-y-0.5 transition-all">
                Book a Demo
              </Button>
            </Link>
          </div>
        </div>
      </nav>

      {/* ═══════════════════════════════════════════════════════════════════════════════
          HERO: EDITORIAL MASTHEAD
          ═══════════════════════════════════════════════════════════════════════════════ */}
      <section className="pt-32 pb-0 relative overflow-hidden">
        {/* Background grid lines */}
        <div className="absolute inset-0 pointer-events-none">
          <div className="absolute top-0 left-[20%] w-px h-full bg-gradient-to-b from-transparent via-white/5 to-transparent" />
          <div className="absolute top-0 left-[40%] w-px h-full bg-gradient-to-b from-transparent via-white/5 to-transparent" />
          <div className="absolute top-0 left-[60%] w-px h-full bg-gradient-to-b from-transparent via-white/5 to-transparent" />
          <div className="absolute top-0 left-[80%] w-px h-full bg-gradient-to-b from-transparent via-white/5 to-transparent" />
        </div>

        <div className="max-w-[1400px] mx-auto px-8">
          {/* Masthead Grid */}
          <div className="grid grid-cols-12 gap-8 items-end pb-16 border-b border-white/10">
            <div className="col-span-12 lg:col-span-7">
              <div className="flex items-center gap-4 mb-6">
                <span className="text-xs font-medium text-emerald-400 tracking-widest uppercase">The Thesis</span>
                <span className="h-px flex-1 bg-white/10" />
                <span className="text-xs text-white/30 font-mono">Est. 2024</span>
              </div>
              <h1 className="text-5xl md:text-6xl lg:text-7xl font-bold text-white leading-[0.95] tracking-tight">
                The most dangerous number in any enterprise is{' '}
                <span className="bg-gradient-to-r from-emerald-400 via-teal-400 to-cyan-400 bg-clip-text text-transparent">
                  the one that was guessed.
                </span>
              </h1>
            </div>
            <div className="col-span-12 lg:col-span-5 lg:pl-8">
              <p className="text-lg text-white/60 leading-relaxed mb-6">
                Most treasury departments operate on theoretical due dates while their liquidity depends on behavioral reality. We built Gitto to close that gap—permanently.
              </p>
              <div className="flex items-center gap-4">
                <Link href="/contact">
                  <Button className="button-glow bg-white text-[#0A0A0F] hover:bg-white/90 h-12 px-6 rounded-xl font-medium">
                    Partner with Us
                  </Button>
                </Link>
                <button 
                  onClick={() => document.getElementById('philosophy')?.scrollIntoView({ behavior: 'smooth' })}
                  className="flex items-center gap-2 text-white/50 hover:text-white transition-colors"
                >
                  <span className="text-sm">Read our philosophy</span>
                  <ArrowDownIcon className="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>

          {/* Stats Bar */}
          <div className="grid grid-cols-2 md:grid-cols-4 py-12 border-b border-white/10">
            {[
              { value: 2.6, suffix: 'B', prefix: '€', label: 'Cash Monitored Weekly' },
              { value: 97, suffix: '%', label: 'Average Cash Explained' },
              { value: 0.8, suffix: ' days', label: 'Forecast Accuracy (MAE)' },
              { value: 14, suffix: '+', label: 'Enterprise Deployments' },
            ].map((stat, i) => (
              <div key={i} className="text-center py-4 md:py-0">
                <div className="text-3xl md:text-4xl font-bold text-white mb-1">
                  {stat.prefix}<AnimatedCounter end={stat.value * 10} duration={1500} />{stat.suffix?.replace(String(stat.value * 10 / 10), '')}
                </div>
                <div className="text-xs text-white/40 uppercase tracking-wider">{stat.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════════════════════════════════════════
          THE PROBLEM: EDITORIAL LONGFORM
          ═══════════════════════════════════════════════════════════════════════════════ */}
      <section className="py-24 bg-[#0A0A0F]">
        <div className="max-w-[1400px] mx-auto px-8">
          <div className="grid grid-cols-12 gap-8">
            {/* Left Column: Section Label */}
            <div className="col-span-12 lg:col-span-3">
              <div className="lg:sticky lg:top-32">
                <span className="text-xs font-medium text-white/30 tracking-widest uppercase">01</span>
                <h2 className="text-2xl font-bold text-white mt-2 mb-4">The Problem</h2>
                <div className="w-12 h-px bg-emerald-400" />
              </div>
            </div>

            {/* Right Column: Content */}
            <div className="col-span-12 lg:col-span-9">
              <div className="max-w-3xl">
                <p className="text-2xl md:text-3xl text-white/80 leading-relaxed mb-12 font-light">
                  Treasury software promised to revolutionize cash management. Instead, it became a prettier version of the spreadsheet it was meant to replace.
                </p>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-x-12 gap-y-16">
                  {[
                    {
                      number: '01',
                      title: 'The Behavioral Blindspot',
                      content: 'Invoice terms say Net-30. Your largest customer\'s AP department runs payments on the 15th and 30th. They have a $50K approval threshold that delays larger invoices by a week. Your ERP doesn\'t know this. Your treasury system doesn\'t learn it. But your cash position depends on it.',
                    },
                    {
                      number: '02',
                      title: 'The Explainability Deficit',
                      content: 'When your 13-week forecast drops by €2M between Monday and Friday, the only acceptable answer is not "the model updated." It\'s "Invoice #4421 from Acme Corp moved from Week 3 to Week 5 based on their historical payment pattern." Every delta needs a citation.',
                    },
                    {
                      number: '03',
                      title: 'The Fragmentation Tax',
                      content: 'Managing group liquidity across 14 banks, 8 currencies, and 6 ERPs shouldn\'t require a team of analysts reconciling exports in Excel. The cognitive overhead of switching between portals, formats, and time zones creates a hidden tax on every treasury decision.',
                    },
                    {
                      number: '04',
                      title: 'The Audit Gap',
                      content: 'When external auditors ask "What did your Week 37 forecast show for October collections?", most treasury teams cannot answer. The forecast changed. The snapshot wasn\'t saved. The trail doesn\'t exist. This is not a software limitation—it\'s a design choice we reject.',
                    },
                  ].map((item) => (
                    <div key={item.number} className="group">
                      <div className="flex items-baseline gap-4 mb-4">
                        <span className="text-xs font-mono text-emerald-400">{item.number}</span>
                        <h3 className="text-lg font-semibold text-white group-hover:text-emerald-400 transition-colors">{item.title}</h3>
                      </div>
                      <p className="text-white/50 leading-relaxed text-sm">{item.content}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════════════════════════════════════════
          PHILOSOPHY: INTERACTIVE DEEP DIVE
          ═══════════════════════════════════════════════════════════════════════════════ */}
      <section id="philosophy" className="py-24 bg-[#0D0D12] border-y border-white/5">
        <div className="max-w-[1400px] mx-auto px-8">
          <div className="grid grid-cols-12 gap-8 mb-16">
            <div className="col-span-12 lg:col-span-3">
              <span className="text-xs font-medium text-white/30 tracking-widest uppercase">02</span>
              <h2 className="text-2xl font-bold text-white mt-2 mb-4">Our Philosophy</h2>
              <div className="w-12 h-px bg-emerald-400" />
            </div>
            <div className="col-span-12 lg:col-span-9">
              <p className="text-xl text-white/60 leading-relaxed max-w-2xl">
                Four non-negotiable principles that govern every feature we ship and every decision we make.
              </p>
            </div>
          </div>

          {/* Philosophy Navigator */}
          <div className="grid grid-cols-12 gap-8">
            {/* Left: Navigation Tabs */}
            <div className="col-span-12 lg:col-span-4">
              <div className="space-y-2">
                {philosophyItems.map((item, index) => (
                  <button
                    key={item.id}
                    onClick={() => setActivePhilosophy(index)}
                    className={`w-full text-left p-6 rounded-xl transition-all duration-300 group ${
                      activePhilosophy === index 
                        ? 'bg-white/5 border border-white/10' 
                        : 'hover:bg-white/[0.02] border border-transparent'
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <div>
                        <h3 className={`font-semibold mb-1 transition-colors ${
                          activePhilosophy === index ? 'text-white' : 'text-white/60 group-hover:text-white'
                        }`}>
                          {item.title}
                        </h3>
                        <p className="text-sm text-white/40">{item.subtitle}</p>
                      </div>
                      <ArrowRightIcon className={`w-5 h-5 transition-all ${
                        activePhilosophy === index 
                          ? 'text-emerald-400 translate-x-0 opacity-100' 
                          : 'text-white/20 -translate-x-2 opacity-0 group-hover:translate-x-0 group-hover:opacity-100'
                      }`} />
                    </div>
                  </button>
                ))}
              </div>
            </div>

            {/* Right: Content Panel */}
            <div className="col-span-12 lg:col-span-8">
              <div className="bg-[#0A0A0F] border border-white/10 rounded-2xl p-8 md:p-12 min-h-[400px]">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                  <div className="md:col-span-2">
                    <span className="text-xs font-mono text-emerald-400 tracking-wider">PRINCIPLE {activePhilosophy + 1}</span>
                    <h3 className="text-2xl font-bold text-white mt-2 mb-6">{philosophyItems[activePhilosophy].title}</h3>
                    <p className="text-white/60 leading-relaxed">{philosophyItems[activePhilosophy].content}</p>
                  </div>
                  <div className="flex flex-col justify-center items-center p-6 bg-white/[0.02] rounded-xl border border-white/5">
                    <div className="text-4xl md:text-5xl font-bold text-emerald-400 mb-2">
                      {philosophyItems[activePhilosophy].stat}
                    </div>
                    <div className="text-xs text-white/40 text-center uppercase tracking-wider">
                      {philosophyItems[activePhilosophy].statLabel}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════════════════════════════════════════
          THE ARCHITECTURE: TECHNICAL DEPTH
          ═══════════════════════════════════════════════════════════════════════════════ */}
      <section className="py-24 bg-[#0A0A0F]">
        <div className="max-w-[1400px] mx-auto px-8">
          <div className="grid grid-cols-12 gap-8 mb-16">
            <div className="col-span-12 lg:col-span-3">
              <span className="text-xs font-medium text-white/30 tracking-widest uppercase">03</span>
              <h2 className="text-2xl font-bold text-white mt-2 mb-4">The Architecture</h2>
              <div className="w-12 h-px bg-emerald-400" />
            </div>
            <div className="col-span-12 lg:col-span-9">
              <p className="text-xl text-white/60 leading-relaxed max-w-2xl">
                Built from first principles for finance teams that demand auditability, not just functionality.
              </p>
            </div>
          </div>

          {/* Architecture Grid */}
          <div className="grid grid-cols-12 gap-6">
            {/* Large Feature Card */}
            <div className="col-span-12 lg:col-span-6 row-span-2">
              <div className="h-full bg-gradient-to-br from-emerald-500/10 via-[#0D0D12] to-[#0D0D12] border border-white/10 rounded-2xl p-8 flex flex-col">
                <div className="flex items-center gap-3 mb-6">
                  <div className="h-10 w-10 rounded-lg bg-emerald-500/20 border border-emerald-500/30 flex items-center justify-center">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-5 h-5 text-emerald-400">
                      <rect x="3" y="3" width="18" height="18" rx="2" />
                      <path d="M3 9h18M9 3v6M7 13h4M7 16h6" />
                    </svg>
                  </div>
                  <span className="text-xs font-medium text-emerald-400 uppercase tracking-wider">Core Engine</span>
                </div>
                <h3 className="text-2xl font-bold text-white mb-4">Bank-Truth Foundation</h3>
                <p className="text-white/50 leading-relaxed mb-8 flex-1">
                  Every number in Gitto traces back to a bank transaction, invoice, or explicit manual adjustment. We maintain four data tiers—Bank-True, Reconciled, Modeled, and Unknown—so you always know the provenance and confidence level of what you&apos;re seeing.
                </p>
                <div className="grid grid-cols-2 gap-4 pt-6 border-t border-white/10">
                  <div>
                    <div className="text-2xl font-bold text-white">4-Tier</div>
                    <div className="text-xs text-white/40">Data Classification</div>
                  </div>
                  <div>
                    <div className="text-2xl font-bold text-white">100%</div>
                    <div className="text-xs text-white/40">Audit Trail Coverage</div>
                  </div>
                </div>
              </div>
            </div>

            {/* Smaller Feature Cards */}
            <div className="col-span-12 md:col-span-6 lg:col-span-3">
              <div className="h-full bg-[#0D0D12] border border-white/10 rounded-2xl p-6">
                <div className="h-8 w-8 rounded-lg bg-blue-500/20 border border-blue-500/30 flex items-center justify-center mb-4">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-4 h-4 text-blue-400">
                    <path d="M4 12h6M14 12h6" />
                    <circle cx="12" cy="12" r="3" />
                  </svg>
                </div>
                <h4 className="font-semibold text-white mb-2">Reconciliation Cockpit</h4>
                <p className="text-sm text-white/40 leading-relaxed">4-tier match ladder from deterministic to manual. Many-to-many matching with allocation conservation.</p>
              </div>
            </div>

            <div className="col-span-12 md:col-span-6 lg:col-span-3">
              <div className="h-full bg-[#0D0D12] border border-white/10 rounded-2xl p-6">
                <div className="h-8 w-8 rounded-lg bg-amber-500/20 border border-amber-500/30 flex items-center justify-center mb-4">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-4 h-4 text-amber-400">
                    <rect x="3" y="4" width="18" height="18" rx="2" />
                    <path d="M16 2v4M8 2v4M3 10h18" />
                  </svg>
                </div>
                <h4 className="font-semibold text-white mb-2">13-Week Workspace</h4>
                <p className="text-sm text-white/40 leading-relaxed">Probabilistic forecasting with P25/P50/P75 confidence bands. Every cell drills to source documents.</p>
              </div>
            </div>

            <div className="col-span-12 md:col-span-6 lg:col-span-3">
              <div className="h-full bg-[#0D0D12] border border-white/10 rounded-2xl p-6">
                <div className="h-8 w-8 rounded-lg bg-purple-500/20 border border-purple-500/30 flex items-center justify-center mb-4">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-4 h-4 text-purple-400">
                    <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8l-6-6z" />
                    <path d="M14 2v6h6M12 18v-6M9 15l3 3 3-3" />
                  </svg>
                </div>
                <h4 className="font-semibold text-white mb-2">Variance Narratives</h4>
                <p className="text-sm text-white/40 leading-relaxed">Automated week-over-week attribution. Every movement explained with driver categories.</p>
              </div>
            </div>

            <div className="col-span-12 md:col-span-6 lg:col-span-3">
              <div className="h-full bg-[#0D0D12] border border-white/10 rounded-2xl p-6">
                <div className="h-8 w-8 rounded-lg bg-rose-500/20 border border-rose-500/30 flex items-center justify-center mb-4">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-4 h-4 text-rose-400">
                    <circle cx="12" cy="12" r="9" />
                    <path d="M8 12h8M15 9l-3-3-3 3M9 15l3 3 3-3" />
                  </svg>
                </div>
                <h4 className="font-semibold text-white mb-2">Liquidity Levers</h4>
                <p className="text-sm text-white/40 leading-relaxed">What-if scenario builder. Real-time impact calculation across the 13-week horizon.</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════════════════════════════════════════
          TRUST: SECURITY & COMPLIANCE
          ═══════════════════════════════════════════════════════════════════════════════ */}
      <section className="py-24 bg-[#0D0D12] border-y border-white/5">
        <div className="max-w-[1400px] mx-auto px-8">
          <div className="grid grid-cols-12 gap-8">
            <div className="col-span-12 lg:col-span-5">
              <span className="text-xs font-medium text-white/30 tracking-widest uppercase">04</span>
              <h2 className="text-2xl font-bold text-white mt-2 mb-4">Trust & Compliance</h2>
              <div className="w-12 h-px bg-emerald-400 mb-8" />
              
              <p className="text-white/50 leading-relaxed mb-8">
                We understand that treasury systems process sensitive financial data and must withstand both internal audit scrutiny and external regulatory review. Security is not a feature—it is the foundation.
              </p>

              <div className="space-y-4">
                {[
                  'SOC 2 Type II certification (in progress)',
                  'Enterprise SSO via SAML 2.0 and OIDC',
                  'Role-based access control with audit logging',
                  'End-to-end encryption in transit and at rest',
                  'Self-hosted deployment option available',
                  'GDPR and data residency compliance',
                ].map((item, i) => (
                  <div key={i} className="flex items-center gap-3">
                    <div className="h-5 w-5 rounded-full bg-emerald-500/20 border border-emerald-500/30 flex items-center justify-center flex-shrink-0">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-3 h-3 text-emerald-400">
                        <path d="M20 6L9 17l-5-5" />
                      </svg>
                    </div>
                    <span className="text-white/70 text-sm">{item}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="col-span-12 lg:col-span-7 lg:pl-12">
              <div className="grid grid-cols-2 gap-6 h-full">
                <div className="bg-[#0A0A0F] border border-white/10 rounded-2xl p-6 flex flex-col justify-between">
                  <div>
                    <div className="text-xs text-white/30 uppercase tracking-wider mb-2">Data Retention</div>
                    <div className="text-4xl font-bold text-white mb-4">7 Years</div>
                  </div>
                  <p className="text-sm text-white/40">Full audit trail retained with immutable snapshots for regulatory compliance.</p>
                </div>
                <div className="bg-[#0A0A0F] border border-white/10 rounded-2xl p-6 flex flex-col justify-between">
                  <div>
                    <div className="text-xs text-white/30 uppercase tracking-wider mb-2">Uptime SLA</div>
                    <div className="text-4xl font-bold text-white mb-4">99.95%</div>
                  </div>
                  <p className="text-sm text-white/40">Enterprise-grade availability with multi-region redundancy.</p>
                </div>
                <div className="bg-[#0A0A0F] border border-white/10 rounded-2xl p-6 flex flex-col justify-between">
                  <div>
                    <div className="text-xs text-white/30 uppercase tracking-wider mb-2">Encryption</div>
                    <div className="text-4xl font-bold text-white mb-4">AES-256</div>
                  </div>
                  <p className="text-sm text-white/40">Bank-grade encryption with customer-managed key option.</p>
                </div>
                <div className="bg-[#0A0A0F] border border-white/10 rounded-2xl p-6 flex flex-col justify-between">
                  <div>
                    <div className="text-xs text-white/30 uppercase tracking-wider mb-2">Audit Events</div>
                    <div className="text-4xl font-bold text-white mb-4">100%</div>
                  </div>
                  <p className="text-sm text-white/40">Every action logged with user, timestamp, and full context.</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════════════════════════════════════════
          TEAM: LEADERSHIP
          ═══════════════════════════════════════════════════════════════════════════════ */}
      <section className="py-24 bg-[#0A0A0F]">
        <div className="max-w-[1400px] mx-auto px-8">
          <div className="grid grid-cols-12 gap-8 mb-16">
            <div className="col-span-12 lg:col-span-3">
              <span className="text-xs font-medium text-white/30 tracking-widest uppercase">05</span>
              <h2 className="text-2xl font-bold text-white mt-2 mb-4">Leadership</h2>
              <div className="w-12 h-px bg-emerald-400" />
            </div>
            <div className="col-span-12 lg:col-span-9">
              <p className="text-xl text-white/60 leading-relaxed max-w-2xl">
                Built by finance practitioners and engineers who lived the problems we&apos;re solving.
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            {[
              {
                name: 'Ayush Rastogi',
                role: 'Founder & CEO',
                bio: 'Former treasury analyst who spent too many Monday mornings reconciling spreadsheets. Built Gitto to eliminate the gap between what CFOs see and what the bank says.',
                linkedin: '#',
              },
              {
                name: 'Treasury Background',
                role: 'Domain Expertise',
                bio: 'Our team includes former treasury managers from Fortune 500 companies, bringing deep understanding of cash management, FX hedging, and liquidity planning at scale.',
                linkedin: null,
              },
              {
                name: 'Engineering DNA',
                role: 'Technical Foundation',
                bio: 'Engineers from leading fintech and enterprise software companies. We build systems that are auditable by design, not as an afterthought.',
                linkedin: null,
              },
            ].map((person, i) => (
              <div key={i} className="group">
                <div className="aspect-[4/3] bg-gradient-to-br from-white/5 to-white/[0.02] rounded-xl mb-6 flex items-center justify-center border border-white/5 group-hover:border-white/10 transition-colors">
                  <div className="h-16 w-16 rounded-full bg-white/10 flex items-center justify-center text-2xl font-bold text-white/40">
                    {person.name.charAt(0)}
                  </div>
                </div>
                <h3 className="font-semibold text-white mb-1">{person.name}</h3>
                <div className="text-sm text-emerald-400 mb-3">{person.role}</div>
                <p className="text-sm text-white/40 leading-relaxed">{person.bio}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════════════════════════════════════════
          CTA: PARTNERSHIP
          ═══════════════════════════════════════════════════════════════════════════════ */}
      <section className="py-32 bg-gradient-to-b from-[#0D0D12] to-[#0A0A0F] border-t border-white/5">
        <div className="max-w-[1400px] mx-auto px-8">
          <div className="grid grid-cols-12 gap-8 items-center">
            <div className="col-span-12 lg:col-span-8">
              <h2 className="text-4xl md:text-5xl font-bold text-white leading-tight mb-6">
                Ready to close the gap between your forecast and your bank balance?
              </h2>
              <p className="text-xl text-white/50 max-w-2xl">
                Join finance teams that have replaced spreadsheet chaos with bank-truth forecasting. Book a personalized demo with your data.
              </p>
            </div>
            <div className="col-span-12 lg:col-span-4 flex flex-col lg:items-end gap-4">
              <Link href="/contact">
                <Button className="button-glow bg-white text-[#0A0A0F] hover:bg-white/90 h-14 px-8 rounded-xl font-medium text-base w-full lg:w-auto">
                  Book a Demo
                </Button>
              </Link>
              <Link href="/app" className="text-white/50 hover:text-white transition-colors text-sm flex items-center gap-2 justify-center lg:justify-end">
                Or try the demo environment
                <ArrowRightIcon className="w-4 h-4" />
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════════════════════════════════════════
          FOOTER
          ═══════════════════════════════════════════════════════════════════════════════ */}
      <footer className="py-16 px-8 bg-[#070709] border-t border-white/5">
        <div className="max-w-[1400px] mx-auto">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8 mb-12">
            <div>
              <div className="flex items-center gap-3 mb-4">
                <div className="h-9 w-9 rounded-xl bg-white flex items-center justify-center text-[#0A0A0F] font-serif font-bold text-lg">G</div>
                <span className="font-serif font-semibold text-lg text-white">Gitto</span>
              </div>
              <p className="text-sm text-white/50 leading-relaxed">
                Bank-truth cash forecasting<br />for finance teams.
              </p>
            </div>
            <div>
              <div className="text-xs font-semibold text-white/30 uppercase tracking-wider mb-4">Product</div>
              <ul className="space-y-2.5 text-sm text-white/50">
                <li><Link href="/#primitives" className="hover:text-white transition-colors">Bank Truth</Link></li>
                <li><Link href="/#primitives" className="hover:text-white transition-colors">Reconciliation</Link></li>
                <li><Link href="/#primitives" className="hover:text-white transition-colors">13-Week Workspace</Link></li>
                <li><Link href="/#primitives" className="hover:text-white transition-colors">Variance Narratives</Link></li>
              </ul>
            </div>
            <div>
              <div className="text-xs font-semibold text-white/30 uppercase tracking-wider mb-4">Company</div>
              <ul className="space-y-2.5 text-sm text-white/50">
                <li><Link href="/about" className="hover:text-white transition-colors">About</Link></li>
                <li><Link href="/contact" className="hover:text-white transition-colors">Contact</Link></li>
                <li><a href="#" className="hover:text-white transition-colors">Careers</a></li>
              </ul>
            </div>
            <div>
              <div className="text-xs font-semibold text-white/30 uppercase tracking-wider mb-4">Legal</div>
              <ul className="space-y-2.5 text-sm text-white/50">
                <li><a href="#" className="hover:text-white transition-colors">Privacy</a></li>
                <li><a href="#" className="hover:text-white transition-colors">Terms</a></li>
                <li><a href="#" className="hover:text-white transition-colors">Security</a></li>
              </ul>
            </div>
          </div>
          <div className="pt-8 border-t border-white/10 flex items-center justify-between text-xs text-white/30">
            <span>© {new Date().getFullYear()} Gitto Intelligence Inc.</span>
            <span>info@gitto.ai</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
