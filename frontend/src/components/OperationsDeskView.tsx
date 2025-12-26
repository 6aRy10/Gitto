'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { api } from '@/lib/api';
import { ShieldAlert, Zap, TrendingUp, DollarSign, Clock, ArrowRight } from "lucide-react";

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
          <CardHeader className="bg-slate-900 text-white p-8">
            <div className="flex items-center justify-between">
              <div className="space-y-1">
                <div className="flex items-center gap-2 text-blue-400 text-[10px] font-black uppercase tracking-[0.2em]">
                  <Zap className="h-3 w-3 fill-current" /> Playbook Suggestions
                </div>
                <CardTitle className="text-2xl font-black">Treasury ROI Optimization</CardTitle>
              </div>
              <DollarSign className="h-8 w-8 text-slate-700" />
            </div>
          </CardHeader>
          <CardContent className="p-0">
            {treasuryActions.length > 0 ? (
              treasuryActions.map((action, i) => (
                <div key={i} className="p-6 border-b border-slate-50 last:border-none flex items-center justify-between hover:bg-slate-50 transition-colors">
                  <div className="space-y-1.5 text-left">
                    <div className="flex items-center gap-2">
                      <span className="px-2 py-0.5 rounded-full bg-blue-100 text-blue-700 text-[9px] font-black uppercase">
                        {action.type.replace(/_/g, ' ')}
                      </span>
                      <span className="text-sm font-bold text-slate-900">{action.customer}</span>
                    </div>
                    <p className="text-xs text-slate-500 font-medium">{action.impact}</p>
                    <div className="text-[10px] text-slate-400 font-bold uppercase tracking-tight">Cost: {action.cost}</div>
                  </div>
                  <div className="text-right space-y-2">
                    <div className="text-lg font-black text-blue-600">ROI: {action.roi.toFixed(1)}x</div>
                    <Button className="h-8 rounded-xl bg-slate-900 text-white font-bold text-[10px] uppercase tracking-wider px-4">
                      Execute <ArrowRight className="ml-1.5 h-3 w-3" />
                    </Button>
                  </div>
                </div>
              ))
            ) : (
              <div className="p-12 text-center text-slate-500 font-medium">
                No treasury recommendations available for this snapshot.
              </div>
            )}
          </CardContent>
        </Card>

        {/* Dispute & Blockage Intelligence */}
        <Card className="rounded-[32px] border-slate-100 shadow-sm overflow-hidden">
          <CardHeader className="px-8 py-8 border-b border-slate-50">
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-xl font-black tracking-tighter">Blockage Prediction</CardTitle>
                <CardDescription>Predicting disputes before they hit due date.</CardDescription>
              </div>
              <ShieldAlert className="h-6 w-6 text-amber-500" />
            </div>
          </CardHeader>
          <CardContent className="p-0">
            {disputeRisks.length > 0 ? (
              <Table>
                <TableHeader className="bg-slate-50/50">
                  <TableRow>
                    <TableHead className="px-8 font-black uppercase text-[9px] tracking-[0.15em] text-slate-400">Invoice</TableHead>
                    <TableHead className="font-black uppercase text-[9px] tracking-[0.15em] text-slate-400">Potential Reason</TableHead>
                    <TableHead className="text-right px-8 font-black uppercase text-[9px] tracking-[0.15em] text-slate-400">Risk Score</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {disputeRisks.map((risk, i) => (
                    <TableRow key={i} className="hover:bg-slate-50/50 transition-colors border-slate-50">
                      <TableCell className="px-8 text-left">
                        <div className="font-bold text-slate-900 text-xs">#{risk.invoice_number}</div>
                        <div className="text-[10px] text-slate-400 font-medium">{risk.customer}</div>
                      </TableCell>
                      <TableCell>
                        <div className="flex flex-wrap gap-1">
                          {risk.potential_blockage_reasons.map((r: string, j: number) => (
                            <span key={j} className="px-2 py-0.5 rounded-md bg-amber-50 text-amber-700 text-[9px] font-bold">
                              {r}
                            </span>
                          ))}
                        </div>
                      </TableCell>
                      <TableCell className="text-right px-8">
                        <div className={`text-sm font-black ${risk.risk_score > 25 ? 'text-red-600' : 'text-amber-600'}`}>
                          {risk.risk_score}%
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            ) : (
              <div className="p-12 text-center text-slate-500 font-medium">
                No blockage risks detected in this snapshot.
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

