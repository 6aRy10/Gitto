'use client';

import { useState } from 'react';
import Link from "next/link";
import { CheckCircle2, Mail, Send, ArrowLeft } from "lucide-react";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { api } from "../../lib/api";

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
    <div className="min-h-screen bg-white text-slate-900 font-sans selection:bg-blue-100 antialiased flex flex-col overflow-x-hidden">
      {/* Navigation */}
      <nav className="fixed top-0 left-0 right-0 z-50 bg-white/80 backdrop-blur-xl border-b border-slate-100 px-8 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2 group">
            <ArrowLeft className="h-4 w-4 text-slate-400 group-hover:text-slate-900 transition-transform group-hover:-translate-x-1" />
            <div className="h-7 w-7 rounded-lg bg-slate-900 flex items-center justify-center text-white font-black text-sm">G</div>
            <span className="font-bold text-xl tracking-tighter text-slate-900">gitto</span>
          </Link>
          <div className="flex gap-4">
            <Link href="/app">
              <Button className="bg-slate-900 text-white hover:bg-slate-800 rounded-full px-8 h-10 text-[14px] font-bold shadow-xl shadow-slate-900/10">
                Book a Demo
              </Button>
            </Link>
          </div>
        </div>
      </nav>

      <main className="flex-1 flex items-center justify-center px-6 py-40">
        <div className="max-w-5xl w-full grid grid-cols-1 lg:grid-cols-2 gap-24 items-start">
          {/* Left: Content */}
          <div className="space-y-10">
            <div className="space-y-6">
              <div className="inline-flex items-center px-4 py-1.5 rounded-full bg-slate-50 border border-slate-100 text-[11px] font-black uppercase tracking-widest text-slate-500">
                Contact Us
              </div>
              <h1 className="text-[56px] md:text-[84px] font-bold tracking-tight text-slate-900 leading-[1.05]">
                Let's talk <br /> 
                <span className="text-slate-400 font-medium italic">cash flow.</span>
              </h1>
              <p className="text-[20px] text-slate-500 font-medium leading-relaxed max-w-sm">
                Secure your collections and automate your behavior-based forecasting. We'll get back to you within 24 hours.
              </p>
            </div>

            <div className="space-y-8 pt-10 border-t border-slate-100">
              <div className="flex items-center gap-5">
                <div className="h-14 w-14 rounded-2xl bg-slate-50 border border-slate-100 flex items-center justify-center shadow-sm">
                  <Mail className="h-6 w-6 text-slate-900" />
                </div>
                <div>
                  <div className="text-[11px] font-black uppercase tracking-widest text-slate-400">Founder Email</div>
                  <div className="text-[18px] font-bold text-slate-900">ayush36rastogi@gmail.com</div>
                </div>
              </div>
            </div>
          </div>

          {/* Right: Form */}
          <div className="bg-white rounded-[40px] border border-slate-100 p-10 md:p-12 shadow-2xl shadow-slate-200/50">
            {submitted ? (
              <div className="text-center py-12 space-y-6 relative z-10">
                <div className="h-20 w-20 bg-emerald-50 rounded-full flex items-center justify-center mx-auto">
                  <CheckCircle2 className="h-10 w-10 text-emerald-600" />
                </div>
                <div className="space-y-2">
                  <h3 className="text-2xl font-bold text-slate-900 tracking-tight">Message Sent!</h3>
                  <p className="text-slate-500 text-sm font-medium">We'll be in touch with you shortly.</p>
                </div>
                <Button variant="outline" className="rounded-full" onClick={() => setSubmitted(false)}>Send another message</Button>
              </div>
            ) : (
              <form onSubmit={handleContactSubmit} className="space-y-8">
                <div className="space-y-3">
                  <label className="text-[12px] font-bold uppercase tracking-widest text-slate-400 px-1">Work Email</label>
                  <Input 
                    required
                    type="email" 
                    placeholder="you@company.com" 
                    className="bg-slate-50 border-slate-100 text-slate-900 h-14 rounded-2xl focus:ring-slate-900 px-6 font-medium"
                    value={contactForm.email}
                    onChange={(e) => setContactForm({ ...contactForm, email: e.target.value })}
                  />
                </div>
                <div className="space-y-3">
                  <label className="text-[12px] font-bold uppercase tracking-widest text-slate-400 px-1">Message</label>
                  <textarea 
                    required
                    rows={6}
                    placeholder="Tell us about your finance stack..." 
                    className="w-full bg-slate-50 border border-slate-100 text-slate-900 p-6 rounded-2xl focus:ring-2 focus:ring-slate-900 focus:outline-none transition-all placeholder:text-slate-400 font-medium"
                    value={contactForm.message}
                    onChange={(e) => setContactForm({ ...contactForm, message: e.target.value })}
                  />
                </div>
                <Button 
                  disabled={isSubmitting}
                  className="w-full bg-slate-900 text-white hover:bg-slate-800 rounded-full h-16 text-lg font-bold shadow-xl shadow-slate-900/10"
                >
                  {isSubmitting ? "Sending..." : "Send Message"}
                  <Send className="ml-2 h-5 w-5" />
                </Button>
              </form>
            )}
          </div>
        </div>
      </main>

      <footer className="px-8 py-20 bg-white border-t border-slate-100">
        <div className="max-w-7xl mx-auto flex justify-between items-center text-[11px] font-black uppercase tracking-[0.2em] text-slate-300">
          <span>©2025 Gitto. All rights reserved.</span>
        </div>
      </footer>
    </div>
  );
}
