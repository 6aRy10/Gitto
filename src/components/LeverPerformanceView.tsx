'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "./ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "./ui/table";
import { Button } from "./ui/button";
import { getLeverPerformance, predictLeverImpact, trackLeverOutcome } from '../lib/api';
import { TrendingUp, Target, RefreshCw, CheckCircle2, AlertCircle } from "lucide-react";

export default function LeverPerformanceView({ snapshotId }: { snapshotId: number }) {
  const [performance, setPerformance] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (snapshotId) {
      loadPerformance();
    }
  }, [snapshotId]);

  const loadPerformance = async () => {
    setLoading(true);
    try {
      const data = await getLeverPerformance(snapshotId);
      setPerformance(data);
    } catch (e: any) {
      console.error("Failed to load lever performance:", e);
      alert(e.response?.data?.detail || "Failed to load lever performance");
    }
    setLoading(false);
  };

  return (
    <div className="space-y-8 mt-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-black tracking-tight text-white">Liquidity Lever Performance</h2>
          <p className="text-sm text-white/40 font-medium mt-1">
            Track realized impact of treasury actions
          </p>
        </div>
        <Button
          onClick={loadPerformance}
          disabled={loading}
          className="bg-white text-[#0A0A0F] hover:bg-white/90 rounded-xl h-10 px-6 text-xs font-bold"
        >
          <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      {performance && (
        <>
          {/* Summary Cards */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            <Card className="rounded-[32px] border-white/10 bg-white/5 overflow-hidden">
              <CardContent className="p-6">
                <div className="text-xs text-white/40 font-black uppercase tracking-widest mb-2">Total Actions</div>
                <div className="text-3xl font-black text-white">{performance.total_actions || 0}</div>
              </CardContent>
            </Card>
            <Card className="rounded-[32px] border-white/10 bg-white/5 overflow-hidden">
              <CardContent className="p-6">
                <div className="text-xs text-white/40 font-black uppercase tracking-widest mb-2">Realized Impact</div>
                <div className="text-3xl font-black text-emerald-400">
                  €{(performance.total_realized_impact || 0).toLocaleString()}
                </div>
              </CardContent>
            </Card>
            <Card className="rounded-[32px] border-white/10 bg-white/5 overflow-hidden">
              <CardContent className="p-6">
                <div className="text-xs text-white/40 font-black uppercase tracking-widest mb-2">Hit Rate</div>
                <div className="text-3xl font-black text-blue-400">
                  {performance.hit_rate ? `${(performance.hit_rate * 100).toFixed(1)}%` : '0%'}
                </div>
              </CardContent>
            </Card>
            <Card className="rounded-[32px] border-white/10 bg-white/5 overflow-hidden">
              <CardContent className="p-6">
                <div className="text-xs text-white/40 font-black uppercase tracking-widest mb-2">Avg Accuracy</div>
                <div className="text-3xl font-black text-amber-400">
                  {performance.avg_accuracy ? `${(performance.avg_accuracy * 100).toFixed(1)}%` : '0%'}
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Actions Table */}
          <Card className="rounded-[32px] border-white/10 bg-white/5 overflow-hidden">
            <CardHeader className="p-8 border-b border-white/10">
              <CardTitle className="text-xl font-black text-white">Action Performance</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <Table>
                <TableHeader className="bg-white/5">
                  <TableRow className="border-white/10">
                    <TableHead className="text-white/60 font-black uppercase text-[10px] tracking-widest">Action</TableHead>
                    <TableHead className="text-white/60 font-black uppercase text-[10px] tracking-widest">Predicted</TableHead>
                    <TableHead className="text-white/60 font-black uppercase text-[10px] tracking-widest">Realized</TableHead>
                    <TableHead className="text-white/60 font-black uppercase text-[10px] tracking-widest">Accuracy</TableHead>
                    <TableHead className="text-white/60 font-black uppercase text-[10px] tracking-widest">Status</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {(performance.actions || []).map((action: any, i: number) => (
                    <TableRow key={i} className="border-white/10 hover:bg-white/5">
                      <TableCell className="text-white font-bold">{action.type}</TableCell>
                      <TableCell className="text-white/80 font-medium">
                        €{action.predicted_impact?.toLocaleString() || '0'}
                      </TableCell>
                      <TableCell className="text-white font-black">
                        €{action.realized_impact?.toLocaleString() || '-'}
                      </TableCell>
                      <TableCell>
                        {action.accuracy ? (
                          <span className={`px-2.5 py-1 rounded-lg text-[10px] font-black ${
                            action.accuracy > 0.8 ? 'bg-emerald-500/20 text-emerald-300' :
                            action.accuracy > 0.5 ? 'bg-amber-500/20 text-amber-300' :
                            'bg-red-500/20 text-red-300'
                          }`}>
                            {(action.accuracy * 100).toFixed(0)}%
                          </span>
                        ) : (
                          <span className="text-white/40 text-xs">Pending</span>
                        )}
                      </TableCell>
                      <TableCell>
                        <span className={`px-2.5 py-1 rounded-lg text-[10px] font-black uppercase ${
                          action.status === 'completed' ? 'bg-emerald-500/20 text-emerald-300' :
                          action.status === 'in_progress' ? 'bg-blue-500/20 text-blue-300' :
                          'bg-white/10 text-white/60'
                        }`}>
                          {action.status || 'pending'}
                        </span>
                      </TableCell>
                    </TableRow>
                  ))}
                  {(!performance.actions || performance.actions.length === 0) && (
                    <TableRow>
                      <TableCell colSpan={5} className="text-center py-12 text-white/40">
                        No actions tracked yet
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}


