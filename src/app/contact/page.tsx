'use client';

import { useState } from 'react';
import Link from "next/link";
import { CheckCircle2, Mail, Send, ArrowLeft } from "lucide-react";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { api } from "../../lib/api";

export default function Contact() {
  const [contactForm, setContactForm] = useState({ email: '', message: '' });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const handleContactSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      await api.post('/contact', contactForm);
      setSubmitted(true);
      setContactForm({ email: '', message: '' });
    } catch (err) {
      console.error(err);
    }
    setIsSubmitting(false);
  };

  return (
    <div className="min-h-screen bg-[#0A0A0B] text-white font-sans selection:bg-blue-500/30 antialiased overflow-x-hidden relative">
      {/* Shared Design Elements */}
      <div className="fixed inset-0 z-50 pointer-events-none opacity-[0.03]" style={{ backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E")` }} />
      <div className="fixed inset-0 z-0 pointer-events-none overflow-hidden">
        <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-blue-600/5 blur-[120px] rounded-full" />
      </div>

      <nav className="fixed top-0 left-0 right-0 z-[60] bg-[#0A0A0B]/80 backdrop-blur-md border-b border-white/5 px-8 py-5">
        <div className="max-w-[1400px] mx-auto flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2 group">
            <div className="h-6 w-6 rounded-lg bg-blue-600 flex items-center justify-center text-white font-black text-[12px] italic">G</div>
            <span className="font-bold text-lg tracking-[-0.04em] text-white uppercase italic">Gitto</span>
          </Link>
          <div className="flex items-center gap-8">
            <Link href="/" className="text-[11px] font-black uppercase tracking-[0.2em] text-slate-400 hover:text-white transition-colors">Return_Home</Link>
          </div>
        </div>
      </nav>

      <main className="relative z-10 pt-48 pb-32 px-8 min-h-screen flex items-center">
        <div className="max-w-[1400px] mx-auto w-full grid grid-cols-1 lg:grid-cols-12 gap-32 items-center">
          {/* Left: Content */}
          <div className="lg:col-span-7 space-y-16">
            <div className="space-y-8">
              <div className="inline-flex items-center px-3 py-1 rounded-sm bg-white/5 border border-white/10 text-[10px] font-black uppercase tracking-[0.3em] text-blue-400">
                Contact_Module // v1.0
              </div>
              <h1 className="text-[60px] md:text-[100px] font-black tracking-[-0.08em] leading-[0.8] text-white uppercase italic">
                LET'S TALK <br />
                <span className="text-white/10 italic">LIQUIDITY.</span>
              </h1>
              <p className="text-2xl text-slate-400 font-medium max-w-lg leading-tight tracking-tight">
                Secure your collections and automate your behavior-based forecasting. Deterministic cash intelligence starts here.
              </p>
            </div>

            <div className="space-y-8 pt-16 border-t border-white/5">
              <div className="flex items-center gap-8 group">
                <div className="h-px w-12 bg-white/20 mt-1 group-hover:bg-blue-500 transition-colors" />
                <div className="space-y-2">
                  <h4 className="text-[10px] font-black uppercase tracking-[0.3em] text-slate-500">Direct_Access</h4>
                  <p className="text-xl font-black italic tracking-tighter text-white">ayush36rastogi@gmail.com</p>
                </div>
              </div>
            </div>
          </div>

          {/* Right: Form */}
          <div className="lg:col-span-5 relative">
            <div className="absolute inset-0 bg-blue-600/5 blur-[100px] rounded-full" />
            <div className="relative z-10 bg-[#111113] border border-white/5 rounded-[40px] p-12 shadow-[0_40px_100px_rgba(0,0,0,0.5)]">
              {submitted ? (
                <div className="text-center py-24 space-y-8">
                  <div className="h-20 w-20 bg-emerald-500/10 rounded-full flex items-center justify-center mx-auto border border-emerald-500/20">
                    <CheckCircle2 className="h-10 w-10 text-emerald-500" />
                  </div>
                  <div className="space-y-4">
                    <h3 className="text-3xl font-black tracking-tighter text-white">SYSTEM_SYNC_SUCCESS</h3>
                    <p className="text-slate-500 font-medium">Your request has been logged. We will respond within 24h.</p>
                  </div>
                  <Button variant="outline" className="rounded-full border-white/10 text-slate-400" onClick={() => setSubmitted(false)}>Send another message</Button>
                </div>
              ) : (
                <form onSubmit={handleContactSubmit} className="space-y-10">
                  <div className="space-y-4">
                    <label className="text-[10px] font-black uppercase tracking-[0.3em] text-slate-500 px-1">Identity_Input</label>
                    <Input 
                      required
                      type="email" 
                      placeholder="you@enterprise.com" 
                      className="bg-white/5 border-white/10 text-white h-16 rounded-2xl focus:ring-blue-500 focus:border-blue-500 px-6 font-bold tracking-tight text-lg"
                      value={contactForm.email}
                      onChange={(e) => setContactForm({ ...contactForm, email: e.target.value })}
                    />
                  </div>
                  <div className="space-y-4">
                    <label className="text-[10px] font-black uppercase tracking-[0.3em] text-slate-500 px-1">Message_Buffer</label>
                    <textarea 
                      required
                      rows={5}
                      placeholder="Tell us about your finance stack..." 
                      className="w-full bg-white/5 border border-white/10 text-white p-6 rounded-2xl focus:ring-2 focus:ring-blue-500 focus:outline-none transition-all placeholder:text-slate-600 font-bold tracking-tight text-lg resize-none"
                      value={contactForm.message}
                      onChange={(e) => setContactForm({ ...contactForm, message: e.target.value })}
                    />
                  </div>
                  <Button 
                    disabled={isSubmitting}
                    className="w-full bg-blue-600 text-white hover:bg-blue-500 rounded-full h-20 text-xl font-black uppercase tracking-widest shadow-[0_20px_40px_rgba(37,99,235,0.2)] transition-all active:scale-[0.98]"
                  >
                    {isSubmitting ? "Syncing..." : "Transmit Message"}
                  </Button>
                </form>
              )}
            </div>
          </div>
        </div>
      </main>

      {/* Footer - Mirrored */}
      <footer className="px-8 py-20 bg-[#0A0A0B] border-t border-white/5">
        <div className="max-w-[1400px] mx-auto flex justify-between items-center text-[10px] font-black uppercase tracking-[0.5em] text-slate-800 text-left">
          <span>©2025 Gitto_Intelligence_Inc.</span>
        </div>
      </footer>
    </div>
  );
}
