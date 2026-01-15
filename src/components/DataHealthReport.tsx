'use client';

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "./ui/card";
import { Button } from "./ui/button";
import { AlertCircle, CheckCircle2, ChevronRight, X, ShieldAlert, BarChart3 } from "lucide-react";

interface HealthReportProps {
  health: any;
  onApprove: () => void;
  onCancel: () => void;
}

export default function DataHealthReport({ health, onApprove, onCancel }: HealthReportProps) {
  const issues = [];
  if (health.integrity.duplicate_keys > 0) issues.push({ label: 'Duplicates', val: health.integrity.duplicate_keys, status: 'warning' });
  if (health.integrity.impossible_amounts > 0) issues.push({ label: 'Invalid Amounts', val: health.integrity.impossible_amounts, status: 'critical' });
  if (health.integrity.impossible_dates > 0) issues.push({ label: 'Invalid Dates', val: health.integrity.impossible_dates, status: 'critical' });
  if (health.completeness.missing_due_dates > 0) issues.push({ label: 'Missing Dates', val: health.completeness.missing_due_dates, status: 'warning' });

  const hasCritical = issues.some(i => i.status === 'critical');

  return (
    <Card className="max-w-3xl mx-auto rounded-[40px] border-slate-100 shadow-2xl bg-white overflow-hidden">
      <CardHeader className="p-10 border-b border-slate-50 bg-slate-50/50">
        <div className="flex items-center justify-between">
          <div className="space-y-2 text-left">
            <div className="inline-flex items-center px-3 py-1 rounded-full bg-emerald-50 text-[10px] font-black uppercase tracking-widest text-emerald-600">
              <ShieldAlert className="h-3 w-3 mr-1.5" /> Pre-Forecasting Health Gate
            </div>
            <CardTitle className="text-3xl font-black tracking-tighter italic">Data Health Audit.</CardTitle>
            <CardDescription className="text-slate-500 font-medium">Verify data integrity before finalizing the snapshot.</CardDescription>
          </div>
          <div className={`h-16 w-16 rounded-[20px] flex items-center justify-center shadow-lg ${hasCritical ? 'bg-red-50 text-red-500' : 'bg-emerald-50 text-emerald-500'}`}>
            {hasCritical ? <ShieldAlert className="h-8 w-8" /> : <CheckCircle2 className="h-8 w-8" />}
          </div>
        </div>
      </CardHeader>
      <CardContent className="p-10 space-y-10">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="p-8 rounded-[32px] bg-slate-900 text-white space-y-4">
            <div className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-400">Total Scanned Invoices</div>
            <div className="text-4xl font-black italic">{health.total_invoices.toLocaleString()}</div>
            <div className="h-1 w-full bg-white/10 rounded-full overflow-hidden">
              <div className="h-full bg-blue-500" style={{ width: '100%' }} />
            </div>
          </div>
          <div className="p-8 rounded-[32px] border-2 border-slate-100 space-y-4 text-left">
            <div className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-400">Forecast Coverage</div>
            <div className="text-4xl font-black italic text-slate-900">
              {Math.round(((health.total_invoices - health.integrity.impossible_amounts) / health.total_invoices) * 100)}%
            </div>
            <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest leading-relaxed">
              Excluding {health.integrity.impossible_amounts} high-risk items from 13w model.
            </p>
          </div>
        </div>

        <div className="space-y-4 text-left">
          <h4 className="text-[11px] font-black uppercase tracking-[0.2em] text-slate-400 border-b border-slate-50 pb-2">Diagnostic Findings</h4>
          <div className="grid grid-cols-1 gap-3">
            {issues.length > 0 ? issues.map((issue, i) => (
              <div key={i} className="flex items-center justify-between p-5 rounded-2xl bg-slate-50 border border-slate-100 group hover:border-slate-200 transition-all">
                <div className="flex items-center gap-4">
                  <div className={`h-2 w-2 rounded-full ${issue.status === 'critical' ? 'bg-red-500' : 'bg-amber-500'}`} />
                  <span className="text-sm font-black text-slate-900 uppercase tracking-tight">{issue.label}</span>
                </div>
                <div className="text-sm font-bold text-slate-500">{issue.val} items detected</div>
              </div>
            )) : (
              <div className="py-10 text-center space-y-4">
                <CheckCircle2 className="h-12 w-12 text-emerald-500 mx-auto" />
                <p className="text-slate-400 font-bold italic">Zero critical integrity issues found. Data is clean.</p>
              </div>
            )}
          </div>
        </div>

        <div className="pt-10 flex items-center justify-between border-t border-slate-50">
          <Button variant="ghost" onClick={onCancel} className="text-[10px] font-black uppercase tracking-widest text-slate-400">
            <X className="mr-2 h-4 w-4" /> Discard Import
          </Button>
          <Button 
            onClick={onApprove}
            className={`rounded-2xl px-10 h-14 font-black uppercase text-xs shadow-xl transition-all ${hasCritical ? 'bg-amber-500 hover:bg-amber-600 text-white shadow-amber-100' : 'bg-slate-900 hover:bg-emerald-600 text-white shadow-slate-200'}`}
          >
            {hasCritical ? 'Proceed with Exclusions' : 'Commit Snapshot'} <ChevronRight className="ml-2 h-4 w-4" />
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

