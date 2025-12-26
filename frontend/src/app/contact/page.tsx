'use client';

import { useState } from 'react';
import Link from "next/link";
import { CheckCircle2, Mail, Send, ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api";

export default function ContactPage() {
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
    <div className="min-h-screen bg-white text-slate-900 font-sans selection:bg-blue-100 antialiased flex flex-col">
      {/* Navigation */}
      <nav className="max-w-5xl mx-auto w-full px-8 py-8 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-2 group">
          <ArrowLeft className="h-4 w-4 text-slate-400 group-hover:text-slate-900 transition-colors" />
          <div className="h-6 w-6 rounded-sm bg-slate-900 flex items-center justify-center text-white font-black text-xs">G</div>
          <span className="font-bold text-2xl tracking-tighter text-slate-900">gitto</span>
        </Link>
      </nav>

      <main className="flex-1 flex items-center justify-center px-6 py-12">
        <div className="max-w-4xl w-full grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">
          {/* Left: Content */}
          <div className="space-y-8">
            <div className="space-y-4">
              <div className="inline-flex items-center px-3 py-1 rounded-full bg-slate-100 text-[11px] font-black uppercase tracking-widest text-slate-500">
                Contact Us
              </div>
              <h1 className="text-[56px] md:text-[72px] font-black tracking-tighter text-slate-900 leading-[0.95]">
                Let's talk <br /> cash flow.
              </h1>
              <p className="text-xl text-slate-500 font-medium leading-relaxed tracking-tight max-w-sm">
                Secure your collections and automate your behavior-based forecasting. We'll get back to you within 24 hours.
              </p>
            </div>

            <div className="space-y-6 pt-8 border-t border-slate-100">
              <div className="flex items-center gap-4">
                <div className="h-12 w-12 rounded-2xl bg-blue-50 flex items-center justify-center">
                  <Mail className="h-5 w-5 text-blue-600" />
                </div>
                <div>
                  <div className="text-xs font-black uppercase tracking-widest text-slate-400">Founder Email</div>
                  <div className="text-base font-bold text-slate-900">ayush36rastogi@gmail.com</div>
                </div>
              </div>
            </div>
          </div>

          {/* Right: Form */}
          <div className="bg-slate-900 rounded-[40px] p-10 md:p-12 shadow-2xl relative overflow-hidden">
            <div className="absolute inset-0 opacity-[0.05] pointer-events-none" style={{ backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E")` }} />
            
            {submitted ? (
              <div className="text-center py-12 space-y-6 relative z-10">
                <div className="h-20 w-20 bg-emerald-500/20 rounded-full flex items-center justify-center mx-auto">
                  <CheckCircle2 className="h-10 w-10 text-emerald-500" />
                </div>
                <div className="space-y-2">
                  <h3 className="text-2xl font-black text-white tracking-tight">Message Sent!</h3>
                  <p className="text-emerald-100/60 text-sm font-medium">We'll be in touch with you shortly.</p>
                </div>
                <Button variant="ghost" className="text-white hover:bg-white/10" onClick={() => setSubmitted(false)}>Send another message</Button>
              </div>
            ) : (
              <form onSubmit={handleContactSubmit} className="space-y-6 relative z-10">
                <div className="space-y-2">
                  <label className="text-[11px] font-black uppercase tracking-widest text-slate-400 px-1">Work Email</label>
                  <div className="relative">
                    <Mail className="absolute left-4 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500" />
                    <Input 
                      required
                      type="email" 
                      placeholder="you@company.com" 
                      className="bg-white/10 border-white/10 text-white pl-12 h-14 rounded-2xl focus:ring-blue-500"
                      value={contactForm.email}
                      onChange={(e) => setContactForm({ ...contactForm, email: e.target.value })}
                    />
                  </div>
                </div>
                <div className="space-y-2">
                  <label className="text-[11px] font-black uppercase tracking-widest text-slate-400 px-1">Message</label>
                  <textarea 
                    required
                    rows={5}
                    placeholder="Tell us about your finance stack..." 
                    className="w-full bg-white/10 border border-white/10 text-white p-4 rounded-2xl focus:ring-2 focus:ring-blue-500 focus:outline-none transition-all placeholder:text-slate-500 text-sm"
                    value={contactForm.message}
                    onChange={(e) => setContactForm({ ...contactForm, message: e.target.value })}
                  />
                </div>
                <Button 
                  disabled={isSubmitting}
                  className="w-full bg-white text-slate-900 hover:bg-slate-100 rounded-2xl h-16 text-lg font-black shadow-xl"
                >
                  {isSubmitting ? "Sending..." : "Send Message"}
                  <Send className="ml-2 h-5 w-5" />
                </Button>
              </form>
            )}
          </div>
        </div>
      </main>

      <footer className="max-w-5xl mx-auto w-full px-8 py-12 flex justify-between items-center text-[10px] font-black uppercase tracking-[0.2em] text-slate-400">
        <span>©2025 Gitto. All rights reserved.</span>
      </footer>
    </div>
  );
}




