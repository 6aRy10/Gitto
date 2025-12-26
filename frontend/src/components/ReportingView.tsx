'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { api } from '@/lib/api';
import { FileText, Globe, CheckCircle2, TrendingDown, ArrowUpRight, Lock, MessageSquare, Send, Sparkles } from "lucide-react";

export default function ReportingView({ snapshotId, entityId }: { snapshotId: number, entityId: number }) {
  const [cashPack, setCashPack] = useState<any>(null);
  const [fxExposure, setFxExposure] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  
  // Q&A State
  const [qaQuery, setQaQuery] = useState('');
  const [qaAnswer, setQaAnswer] = useState<string | null>(null);
  const [qaLoading, setQaLoading] = useState(false);
  const [chatHistory, setChatHistory] = useState<{q: string, a: string}[]>([]);

  useEffect(() => {
    if (snapshotId && entityId) loadReportingData();
  }, [snapshotId, entityId]);

  const loadReportingData = async () => {
    setLoading(true);
    try {
      const [packRes, fxRes] = await Promise.all([
        api.get(`/snapshots/${snapshotId}/cash-pack?entity_id=${entityId}`),
        api.get(`/snapshots/${snapshotId}/fx-exposure`)
      ]);
      setCashPack(packRes.data);
      setFxExposure(fxRes.data);
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  };

  const handleApprove = async () => {
    await api.post(`/reports/1/approve?user=CFO_USER`);
    await loadReportingData();
  };

  const handleAsk = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!qaQuery.trim()) return;
    
    setQaLoading(true);
    try {
      const res = await api.post(`/snapshots/${snapshotId}/ask-insights?entity_id=${entityId}&query=${encodeURIComponent(qaQuery)}`);
      const newEntry = { q: qaQuery, a: res.data.answer };
      setChatHistory([newEntry, ...chatHistory]);
      setQaQuery('');
    } catch (err) {
      console.error(err);
    }
    setQaLoading(false);
  };

  return (
    <div className="space-y-8 mt-6">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Weekly Cash Pack */}
        <Card className="lg:col-span-2 rounded-[40px] border-slate-100 shadow-2xl overflow-hidden bg-white">
          <CardHeader className="p-10 border-b border-slate-50 flex flex-row items-center justify-between">
            <div className="space-y-2">
              <div className="inline-flex items-center px-3 py-1 rounded-full bg-blue-50 text-[10px] font-black uppercase tracking-widest text-blue-600">
                Automated CFO Briefing
              </div>
              <CardTitle className="text-3xl font-black tracking-tighter">Weekly Cash Pack</CardTitle>
              <CardDescription>Comprehensive report for board visibility.</CardDescription>
            </div>
            <FileText className="h-10 w-10 text-slate-100" />
          </CardHeader>
          <CardContent className="p-10 space-y-10">
            <div className="space-y-4 text-left">
              <h4 className="text-[11px] font-black uppercase tracking-[0.2em] text-slate-400">Executive Summary</h4>
              <p className="text-xl font-bold text-slate-900 leading-relaxed">
                {cashPack?.executive_summary || "Report generating..."}
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-10">
              <div className="space-y-4 text-left">
                <h4 className="text-[11px] font-black uppercase tracking-[0.2em] text-slate-400">Variance Analysis</h4>
                <div className="space-y-3">
                  {cashPack?.variance_summary?.narrative?.map((n: string, i: number) => (
                    <div key={i} className="flex gap-3 text-sm font-medium text-slate-600">
                      <div className="h-1.5 w-1.5 rounded-full bg-blue-500 mt-2 shrink-0" />
                      {n}
                    </div>
                  ))}
                </div>
              </div>
              <div className="space-y-4 text-left">
                <h4 className="text-[11px] font-black uppercase tracking-[0.2em] text-slate-400">Priority Actions</h4>
                <div className="space-y-3">
                  {cashPack?.priority_actions?.map((a: any, i: number) => (
                    <div key={i} className="p-3 rounded-2xl bg-slate-50 border border-slate-100 flex items-center justify-between">
                      <div className="text-xs font-bold text-slate-900 truncate max-w-[120px]">{a.customer}</div>
                      <div className="text-[10px] font-black text-blue-600 uppercase tracking-tighter">ROI: {a.roi.toFixed(1)}x</div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <div className="pt-10 border-t border-slate-50 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className={`h-3 w-3 rounded-full ${cashPack?.approval_status === 'pending_cfo_signoff' ? 'bg-amber-400' : 'bg-emerald-400'}`} />
                <span className="text-[11px] font-black uppercase tracking-widest text-slate-400">
                  Status: {cashPack?.approval_status?.replace(/_/g, ' ') || 'Pending'}
                </span>
              </div>
              <Button 
                onClick={handleApprove}
                className="bg-slate-900 text-white hover:bg-slate-800 rounded-2xl px-8 h-12 font-black text-sm"
              >
                <Lock className="mr-2 h-4 w-4" /> Sign Off Report
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* FX Exposure */}
        <div className="space-y-8 text-left">
          <Card className="rounded-[32px] border-slate-100 shadow-sm p-8 bg-slate-900 text-white border-none">
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <Globe className="h-6 w-6 text-blue-400" />
                <span className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-500">Group FX Exposure</span>
              </div>
              <div className="space-y-4">
                {fxExposure.map((fx, i) => (
                  <div key={i} className="flex items-center justify-between border-b border-white/5 pb-4 last:border-none last:pb-0">
                    <div>
                      <div className="text-xl font-black">{fx.currency}</div>
                      <div className="text-[10px] font-bold text-slate-500 uppercase">{fx.invoice_count} Invoices</div>
                    </div>
                    <div className="text-right">
                      <div className="text-lg font-bold">€{fx.total_amount.toLocaleString()}</div>
                      <div className="text-[10px] font-black text-red-400 uppercase tracking-tighter">Implied Risk: €{fx.implied_fx_risk.toLocaleString()}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </Card>

          <Card className="rounded-[32px] border-slate-100 shadow-sm p-8">
            <div className="space-y-4">
              <TrendingDown className="h-6 w-6 text-red-500" />
              <div className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-400">Liquidity Alert</div>
              <h4 className="text-lg font-black tracking-tight text-slate-900">Structurally Changing Segments</h4>
              <p className="text-sm font-medium text-slate-500 leading-relaxed">
                Customer Group 'Enterprise-DE' has shifted behavior by +12 days in the last 3 runs. 
              </p>
              <Button variant="ghost" className="p-0 h-auto text-blue-600 font-black text-xs hover:bg-transparent">
                Review Regime Shift <ArrowUpRight className="ml-1 h-3 w-3" />
              </Button>
            </div>
          </Card>
        </div>
      </div>

      {/* Q&A Section */}
      <Card className="rounded-[40px] border-slate-100 shadow-xl overflow-hidden bg-white">
        <CardHeader className="p-10 border-b border-slate-50 flex flex-row items-center justify-between">
          <div className="space-y-2 text-left">
            <div className="inline-flex items-center px-3 py-1 rounded-full bg-indigo-50 text-[10px] font-black uppercase tracking-widest text-indigo-600">
              <Sparkles className="h-3 w-3 mr-1.5 fill-current" /> Predictive Insights & Analyst Q&A
            </div>
            <CardTitle className="text-3xl font-black tracking-tighter">Ask Gitto Analyst</CardTitle>
            <CardDescription>Get instant answers about your cash variance, risks, and forecasts.</CardDescription>
          </div>
          <MessageSquare className="h-10 w-10 text-slate-100" />
        </CardHeader>
        <CardContent className="p-10">
          <div className="max-w-4xl mx-auto space-y-8">
            {/* Chat History */}
            <div className="space-y-6 max-h-[400px] overflow-y-auto pr-4 custom-scrollbar">
              {chatHistory.length === 0 ? (
                <div className="text-center py-10 space-y-4">
                  <div className="h-16 w-16 bg-slate-50 rounded-full flex items-center justify-center mx-auto">
                    <MessageSquare className="h-8 w-8 text-slate-200" />
                  </div>
                  <p className="text-slate-400 font-medium">Try asking: "Why is there a shortfall?" or "What are my top risks?"</p>
                </div>
              ) : (
                chatHistory.map((chat, i) => (
                  <div key={i} className="space-y-4 animate-in fade-in slide-in-from-bottom-2">
                    <div className="flex justify-end">
                      <div className="bg-slate-100 text-slate-900 px-6 py-3 rounded-2xl rounded-tr-none text-sm font-bold shadow-sm">
                        {chat.q}
                      </div>
                    </div>
                    <div className="flex justify-start">
                      <div className="bg-indigo-600 text-white px-6 py-4 rounded-2xl rounded-tl-none text-sm font-medium shadow-lg max-w-[85%] leading-relaxed">
                        <div className="flex items-center gap-2 mb-2">
                          <Sparkles className="h-3 w-3 fill-current text-indigo-200" />
                          <span className="text-[10px] font-black uppercase tracking-widest text-indigo-200">Analyst Insight</span>
                        </div>
                        {chat.a}
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>

            {/* Input Form */}
            <form onSubmit={handleAsk} className="relative mt-10">
              <input
                type="text"
                placeholder="Ask about your cash swings, risks, or FX exposure..."
                className="w-full h-16 pl-6 pr-20 rounded-2xl border-2 border-slate-100 bg-slate-50 focus:border-indigo-500 focus:ring-0 transition-all font-medium text-slate-900"
                value={qaQuery}
                onChange={(e) => setQaQuery(e.target.value)}
                disabled={qaLoading}
              />
              <Button 
                type="submit"
                disabled={qaLoading || !qaQuery.trim()}
                className="absolute right-3 top-3 h-10 w-10 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white shadow-lg p-0"
              >
                {qaLoading ? (
                  <div className="h-4 w-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                ) : (
                  <Send className="h-4 w-4" />
                )}
              </Button>
            </form>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

