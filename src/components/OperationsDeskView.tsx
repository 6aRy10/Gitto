'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "./ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "./ui/table";
import { Button } from "./ui/button";
import { api } from '../lib/api';
import { ShieldAlert, Zap, TrendingUp, DollarSign, Clock, ArrowRight, CheckCircle2, Lightbulb, AlertTriangle } from "lucide-react";

export default function OperationsDeskView({ snapshotId }: { snapshotId: number }) {
  const [disputeRisks, setDisputeRisks] = useState<any[]>([]);
  const [treasuryActions, setTreasuryActions] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (snapshotId) loadOpsData();
  }, [snapshotId]);

  const loadOpsData = async () => {
    setLoading(true);
    try {
      const [riskRes, actionRes] = await Promise.all([
        api.get(`/snapshots/${snapshotId}/dispute-risks`),
        api.get(`/snapshots/${snapshotId}/treasury-actions`)
      ]);
      setDisputeRisks(riskRes.data);
      setTreasuryActions(actionRes.data);
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  };

  return (
    <div className="space-y-8 mt-6">
      {/* Treasury Action Playbook */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        <Card className="rounded-[32px] border-slate-100 shadow-xl overflow-hidden">
          <CardHeader className="bg-gradient-to-br from-slate-900 to-slate-800 text-white p-8">
            <div className="flex items-center justify-between">
              <div className="space-y-2">
                <div className="flex items-center gap-2 text-emerald-400 text-[10px] font-black uppercase tracking-[0.2em]">
                  <Lightbulb className="h-3.5 w-3.5" /> Smart Recommendations
                </div>
                <CardTitle className="text-2xl font-black">Cash Optimization Actions</CardTitle>
                <p className="text-slate-400 text-sm font-medium">AI-suggested actions to improve your cash position</p>
              </div>
              <div className="p-4 bg-white/10 rounded-2xl">
                <DollarSign className="h-8 w-8 text-emerald-400" />
              </div>
            </div>
          </CardHeader>
          <CardContent className="p-0">
            {treasuryActions.length > 0 ? (
              treasuryActions.map((action, i) => (
                <div key={i} className="p-6 border-b border-slate-50 last:border-none flex items-center justify-between hover:bg-emerald-50/30 transition-colors group">
                  <div className="space-y-2 text-left flex-1">
                    <div className="flex items-center gap-2">
                      <span className="px-2.5 py-1 rounded-lg bg-emerald-100 text-emerald-700 text-[9px] font-black uppercase">
                        {action.type.replace(/_/g, ' ')}
                      </span>
                      <span className="text-sm font-bold text-slate-900">{action.customer}</span>
                    </div>
                    <p className="text-xs text-slate-500 font-medium">{action.impact}</p>
                    <div className="text-[10px] text-slate-400 font-bold">Estimated Effort: {action.cost}</div>
                  </div>
                  <div className="text-right space-y-3 pl-4">
                    <div className="text-xl font-black text-emerald-600">{action.roi.toFixed(1)}x ROI</div>
                    <Button className="h-9 rounded-xl bg-slate-900 text-white font-bold text-[10px] uppercase tracking-wider px-5 group-hover:bg-emerald-600 transition-colors">
                      Take Action <ArrowRight className="ml-2 h-3 w-3" />
                    </Button>
                  </div>
                </div>
              ))
            ) : (
              <div className="p-16 text-center">
                <div className="w-20 h-20 bg-emerald-50 rounded-3xl flex items-center justify-center mx-auto mb-6">
                  <CheckCircle2 className="h-10 w-10 text-emerald-400" />
                </div>
                <h4 className="text-xl font-black text-emerald-600 mb-2">You're Optimized!</h4>
                <p className="text-sm text-slate-400 max-w-xs mx-auto leading-relaxed">
                  No additional cash optimization actions recommended. Your treasury operations are running efficiently.
                </p>
                <div className="mt-6 flex justify-center gap-3">
                  <Button variant="outline" className="rounded-xl text-[10px] font-bold uppercase tracking-widest">
                    View History
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Dispute & Blockage Intelligence */}
        <Card className="rounded-[32px] border-slate-100 shadow-xl overflow-hidden">
          <CardHeader className="px-8 py-8 border-b border-slate-50 bg-gradient-to-r from-white to-amber-50/30">
            <div className="flex items-center justify-between">
              <div className="space-y-1">
                <div className="flex items-center gap-2 text-amber-600 text-[10px] font-black uppercase tracking-[0.2em]">
                  <AlertTriangle className="h-3.5 w-3.5" /> Early Warning System
                </div>
                <CardTitle className="text-xl font-black tracking-tighter">Payment Dispute Risk</CardTitle>
                <CardDescription className="text-slate-500">Invoices that may face customer disputes or delays</CardDescription>
              </div>
              <div className="p-4 bg-amber-100 rounded-2xl">
                <ShieldAlert className="h-6 w-6 text-amber-600" />
              </div>
            </div>
          </CardHeader>
          <CardContent className="p-0">
            {disputeRisks.length > 0 ? (
              <Table>
                <TableHeader className="bg-slate-50/50">
                  <TableRow>
                    <TableHead className="px-8 font-black uppercase text-[9px] tracking-[0.15em] text-slate-400">Invoice</TableHead>
                    <TableHead className="font-black uppercase text-[9px] tracking-[0.15em] text-slate-400">Warning Signs</TableHead>
                    <TableHead className="text-right px-8 font-black uppercase text-[9px] tracking-[0.15em] text-slate-400">Risk Level</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {disputeRisks.map((risk, i) => (
                    <TableRow key={i} className="hover:bg-amber-50/30 transition-colors border-slate-50 cursor-pointer">
                      <TableCell className="px-8 text-left">
                        <div className="font-bold text-slate-900 text-xs">#{risk.invoice_number}</div>
                        <div className="text-[10px] text-slate-400 font-medium">{risk.customer}</div>
                      </TableCell>
                      <TableCell>
                        <div className="flex flex-wrap gap-1.5">
                          {risk.potential_blockage_reasons.map((r: string, j: number) => (
                            <span key={j} className="px-2.5 py-1 rounded-lg bg-amber-50 text-amber-700 text-[9px] font-bold border border-amber-100">
                              {r}
                            </span>
                          ))}
                        </div>
                      </TableCell>
                      <TableCell className="text-right px-8">
                        <div className={`inline-flex items-center gap-2 px-3 py-1 rounded-full text-sm font-black ${
                          risk.risk_score > 25 
                            ? 'bg-red-50 text-red-600 border border-red-100' 
                            : 'bg-amber-50 text-amber-600 border border-amber-100'
                        }`}>
                          {risk.risk_score > 25 ? 'High' : 'Medium'}
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            ) : (
              <div className="p-16 text-center">
                <div className="w-20 h-20 bg-emerald-50 rounded-3xl flex items-center justify-center mx-auto mb-6">
                  <CheckCircle2 className="h-10 w-10 text-emerald-400" />
                </div>
                <h4 className="text-xl font-black text-emerald-600 mb-2">No Disputes Expected</h4>
                <p className="text-sm text-slate-400 max-w-xs mx-auto leading-relaxed">
                  All invoices look healthy! No customers are showing dispute patterns or payment issues.
                </p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

