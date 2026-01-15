'use client';

import { useState } from 'react';
import Link from "next/link";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { api } from "../../lib/api";

// ═══════════════════════════════════════════════════════════════════════════════
// CUSTOM ICONS - Matching main landing page
// ═══════════════════════════════════════════════════════════════════════════════

const CheckIcon = ({ className = "w-5 h-5" }: { className?: string }) => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className={className}>
    <path d="M20 6L9 17l-5-5" />
  </svg>
);

const ArrowRightIcon = ({ className = "w-4 h-4" }: { className?: string }) => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className={className}>
    <path d="M5 12h14M12 5l7 7-7 7" />
  </svg>
);

const MailIcon = ({ className = "w-5 h-5" }: { className?: string }) => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className={className}>
    <rect x="2" y="4" width="20" height="16" rx="2" />
    <path d="M22 6l-10 7L2 6" />
  </svg>
);

const CalendarIcon = ({ className = "w-5 h-5" }: { className?: string }) => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className={className}>
    <rect x="3" y="4" width="18" height="18" rx="2" />
    <path d="M16 2v4M8 2v4M3 10h18" />
    <path d="M8 14h.01M12 14h.01M16 14h.01M8 18h.01M12 18h.01" />
  </svg>
);

const BuildingIcon = ({ className = "w-5 h-5" }: { className?: string }) => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className={className}>
    <path d="M3 21h18" />
    <path d="M5 21V7l8-4v18" />
    <path d="M19 21V11l-6-4" />
    <path d="M9 9v.01M9 12v.01M9 15v.01M9 18v.01" />
  </svg>
);

export default function Contact() {
  const [contactForm, setContactForm] = useState({ email: '', message: '', company: '' });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const handleContactSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      await api.post('/contact', contactForm);
      setSubmitted(true);
      setContactForm({ email: '', message: '', company: '' });
    } catch (err) {
      console.error(err);
    }
    setIsSubmitting(false);
  };

  return (
    <div className="min-h-screen bg-[#0A0A0F] text-white font-sans antialiased overflow-hidden">
      
      {/* ═══════════════════════════════════════════════════════════════════════════════
          ANIMATED BACKGROUND ELEMENTS (Matching main landing page)
          ═══════════════════════════════════════════════════════════════════════════════ */}
      <div className="fixed inset-0 -z-10 overflow-hidden pointer-events-none">
        {/* Subtle glow orbs */}
        <div className="absolute top-20 left-[10%] w-[500px] h-[500px] bg-gradient-to-br from-blue-500/[0.07] to-cyan-500/[0.03] rounded-full blur-3xl animate-float-slow" />
        <div className="absolute top-[50%] right-[5%] w-[400px] h-[400px] bg-gradient-to-br from-emerald-500/[0.05] to-teal-500/[0.02] rounded-full blur-3xl" style={{ animationDelay: '-2s' }} />
        
        {/* Subtle grid pattern */}
        <div className="absolute inset-0 opacity-[0.015]" style={{ 
          backgroundImage: `url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='1'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")` 
        }} />
      </div>

      {/* ─────────────────────────────────────────────────────────────────────── */}
      {/* NAVIGATION - Matching main landing page */}
      {/* ─────────────────────────────────────────────────────────────────────── */}
      <nav className="fixed top-0 left-0 right-0 z-50 bg-[#0A0A0F]/90 backdrop-blur-xl border-b border-white/5">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
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
            <Link href="/about" className="text-white/50 hover:text-white transition-colors">about</Link>
          </div>
          <div className="flex items-center gap-4">
            <Link href="/app" className="text-sm text-white/50 hover:text-white transition-colors hidden sm:block tracking-wide">
              sign in
            </Link>
            <Link href="/app">
              <Button className="button-glow bg-white text-[#0A0A0F] hover:bg-white/90 text-sm px-6 h-11 rounded-xl font-medium tracking-wide hover:-translate-y-0.5 transition-all">
                Book a Demo
              </Button>
            </Link>
          </div>
        </div>
      </nav>

      {/* ─────────────────────────────────────────────────────────────────────── */}
      {/* MAIN CONTENT */}
      {/* ─────────────────────────────────────────────────────────────────────── */}
      <main className="relative pt-32 pb-24 px-6 min-h-screen">
        <div className="max-w-6xl mx-auto">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-16 items-start">
            
            {/* Left: Content */}
            <div className="space-y-10">
              <div className="space-y-6">
                <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/20">
                  <div className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
                  <span className="text-xs font-medium text-emerald-400 tracking-wide">Let&apos;s connect</span>
                </div>

                <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold text-white leading-tight tracking-tight">
                  Ready to see<br />
                  <span className="bg-gradient-to-r from-white via-white/80 to-white/50 bg-clip-text text-transparent">
                    bank-truth in action?
                  </span>
                </h1>

                <p className="text-lg text-white/50 leading-relaxed max-w-md">
                  Book a personalized demo with your data, or reach out to discuss how Gitto can transform your weekly cash meeting.
                </p>
              </div>

              {/* Contact Options */}
              <div className="space-y-4">
                <div className="flex items-center gap-4 p-4 bg-white/[0.02] border border-white/5 rounded-xl hover:bg-white/[0.04] hover:border-white/10 transition-all group cursor-pointer">
                  <div className="h-12 w-12 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 group-hover:scale-105 transition-transform">
                    <CalendarIcon className="w-5 h-5" />
                  </div>
                  <div className="flex-1">
                    <div className="font-semibold text-white">Schedule a Demo</div>
                    <div className="text-sm text-white/40">See the 13-week workspace with sample data</div>
                  </div>
                  <ArrowRightIcon className="w-5 h-5 text-white/30 group-hover:text-emerald-400 group-hover:translate-x-1 transition-all" />
                </div>

                <div className="flex items-center gap-4 p-4 bg-white/[0.02] border border-white/5 rounded-xl hover:bg-white/[0.04] hover:border-white/10 transition-all group">
                  <div className="h-12 w-12 rounded-xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-blue-400 group-hover:scale-105 transition-transform">
                    <MailIcon className="w-5 h-5" />
                  </div>
                  <div className="flex-1">
                    <div className="font-semibold text-white">Email Us Directly</div>
                    <div className="text-sm text-white/40">info@gitto.ai</div>
                  </div>
                </div>
              </div>

              {/* Trust Indicators */}
              <div className="pt-8 border-t border-white/10">
                <div className="text-xs text-white/30 uppercase tracking-wider mb-4">Trusted by finance teams at</div>
                <div className="flex items-center gap-6">
                  {['Enterprise CFOs', 'PE-backed Companies', 'Mid-market Treasury'].map((item, i) => (
                    <div key={i} className="flex items-center gap-2 text-sm text-white/40">
                      <div className="h-1 w-1 rounded-full bg-emerald-400" />
                      {item}
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Right: Form */}
            <div className="relative">
              <div className="absolute -inset-4 bg-gradient-to-br from-emerald-500/5 via-white/[0.02] to-blue-500/5 rounded-3xl -z-10" />
              
              <div className="bg-[#0D0D12] border border-white/10 rounded-2xl overflow-hidden shadow-2xl">
                {/* Form Header */}
                <div className="bg-white/5 border-b border-white/10 px-6 py-4 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="flex gap-1.5">
                      <div className="w-3 h-3 rounded-full bg-red-400" />
                      <div className="w-3 h-3 rounded-full bg-amber-400" />
                      <div className="w-3 h-3 rounded-full bg-emerald-400" />
                    </div>
                    <span className="ml-3 text-xs font-semibold text-white">Contact Sales</span>
                  </div>
                  <span className="text-[10px] text-white/40 font-mono">Response time: &lt;24h</span>
                </div>

                {/* Form Content */}
                <div className="p-6">
                  {submitted ? (
                    <div className="text-center py-12 space-y-6">
                      <div className="h-16 w-16 bg-emerald-500/10 border border-emerald-500/20 rounded-full flex items-center justify-center mx-auto">
                        <CheckIcon className="h-8 w-8 text-emerald-400" />
                      </div>
                      <div className="space-y-2">
                        <h3 className="text-xl font-bold text-white">Message Received</h3>
                        <p className="text-white/50 text-sm">We&apos;ll be in touch within 24 hours to schedule your demo.</p>
                      </div>
                      <Button 
                        variant="outline" 
                        className="border-white/10 text-white/60 hover:text-white hover:border-white/20 rounded-xl"
                        onClick={() => setSubmitted(false)}
                      >
                        Send another message
                      </Button>
                    </div>
                  ) : (
                    <form onSubmit={handleContactSubmit} className="space-y-5">
                      <div className="space-y-2">
                        <label className="text-xs font-medium text-white/50">Work Email</label>
                        <Input 
                          required
                          type="email" 
                          placeholder="you@company.com" 
                          className="bg-white/5 border-white/10 text-white h-12 rounded-xl focus:ring-emerald-500 focus:border-emerald-500 placeholder:text-white/30"
                          value={contactForm.email}
                          onChange={(e) => setContactForm({ ...contactForm, email: e.target.value })}
                        />
                      </div>

                      <div className="space-y-2">
                        <label className="text-xs font-medium text-white/50">Company</label>
                        <Input 
                          type="text" 
                          placeholder="Your company name" 
                          className="bg-white/5 border-white/10 text-white h-12 rounded-xl focus:ring-emerald-500 focus:border-emerald-500 placeholder:text-white/30"
                          value={contactForm.company}
                          onChange={(e) => setContactForm({ ...contactForm, company: e.target.value })}
                        />
                      </div>

                      <div className="space-y-2">
                        <label className="text-xs font-medium text-white/50">How can we help?</label>
                        <textarea 
                          required
                          rows={4}
                          placeholder="Tell us about your cash forecasting challenges..." 
                          className="w-full bg-white/5 border border-white/10 text-white p-4 rounded-xl focus:ring-2 focus:ring-emerald-500 focus:outline-none transition-all placeholder:text-white/30 resize-none text-sm"
                          value={contactForm.message}
                          onChange={(e) => setContactForm({ ...contactForm, message: e.target.value })}
                        />
                      </div>

                      <Button 
                        disabled={isSubmitting}
                        className="button-glow w-full bg-white text-[#0A0A0F] hover:bg-white/90 rounded-xl h-12 font-medium text-sm transition-all hover:-translate-y-0.5 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        {isSubmitting ? (
                          <span className="flex items-center gap-2">
                            <div className="h-4 w-4 border-2 border-[#0A0A0F]/20 border-t-[#0A0A0F] rounded-full animate-spin" />
                            Sending...
                          </span>
                        ) : (
                          <span className="flex items-center gap-2">
                            Send Message
                            <ArrowRightIcon className="w-4 h-4" />
                          </span>
                        )}
                      </Button>

                      <p className="text-[11px] text-white/30 text-center">
                        By submitting, you agree to our privacy policy. We&apos;ll never share your information.
                      </p>
                    </form>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* ─────────────────────────────────────────────────────────────────────── */}
      {/* FOOTER - Matching main landing page */}
      {/* ─────────────────────────────────────────────────────────────────────── */}
      <footer className="py-16 px-6 bg-[#070709] border-t border-white/5 relative overflow-hidden">
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[600px] h-[200px] bg-gradient-to-b from-emerald-500/[0.03] to-transparent rounded-full blur-3xl" />
        </div>
        <div className="max-w-6xl mx-auto relative">
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
            <span>© 2025 Gitto Intelligence Inc.</span>
            <span>info@gitto.ai</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
