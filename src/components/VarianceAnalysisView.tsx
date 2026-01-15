'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "./ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "./ui/table";
import { Button } from "./ui/button";
import { api, getVariance, getVarianceDrilldown } from '../lib/api';
import { 
  TrendingUp, TrendingDown, RefreshCw, ChevronRight, AlertCircle, 
  DollarSign, Calendar, FileText, Settings, Search
} from "lucide-react";

interface VarianceData {
  variance_breakdown: {
    causes: {
      new_items?: { count: number; amount: number; invoice_ids?: number[] };
      timing_shifts?: { count: number; amount: number; invoice_ids?: number[] };
      reconciliation?: { count: number; amount: number; reconciliation_ids?: number[] };
      policy_changes?: { count: number; amount: number; changes?: any[] };
    };
    total_variance: number;
  };
  current_snapshot_id: number;
  previous_snapshot_id: number;
}

export default function VarianceAnalysisView({ 
  snapshotId, 
  compareId 
}: { 
  snapshotId: number; 
  compareId?: number;
}) {
  const [variance, setVariance] = useState<VarianceData | null>(null);
  const [drilldown, setDrilldown] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [selectedCause, setSelectedCause] = useState<string | null>(null);
  const [snapshots, setSnapshots] = useState<any[]>([]);
  const [selectedCompareId, setSelectedCompareId] = useState<number | null>(compareId || null);

  useEffect(() => {
    loadSnapshots();
  }, []);

  useEffect(() => {
    if (snapshotId && selectedCompareId) {
      loadVariance();
    }
  }, [snapshotId, selectedCompareId]);

  const loadSnapshots = async () => {
    try {
      const data = await api.get('/snapshots').then(res => res.data);
      setSnapshots(data);
      if (!selectedCompareId && data.length > 1) {
        // Auto-select previous snapshot
        const currentIdx = data.findIndex((s: any) => s.id === snapshotId);
        if (currentIdx > 0) {
          setSelectedCompareId(data[currentIdx - 1].id);
        }
      }
    } catch (e) {
      console.error(e);
    }
  };

  const loadVariance = async () => {
    if (!selectedCompareId) return;
    setLoading(true);
    try {
      const data = await getVariance(snapshotId, selectedCompareId);
      setVariance(data);
      setDrilldown(null);
      setSelectedCause(null);
    } catch (e: any) {
      console.error("Failed to load variance:", e);
      alert(e.response?.data?.detail || "Failed to load variance analysis");
    }
    setLoading(false);
  };

  const loadDrilldown = async (varianceType: string, weekIndex?: number) => {
    if (!selectedCompareId) return;
    setLoading(true);
    try {
      const data = await getVarianceDrilldown(
        snapshotId, 
        selectedCompareId, 
        weekIndex || 0, 
        varianceType
      );
      setDrilldown(data);
      setSelectedCause(varianceType);
    } catch (e: any) {
      console.error("Failed to load drilldown:", e);
      alert(e.response?.data?.detail || "Failed to load drilldown");
    }
    setLoading(false);
  };

  const causes = variance?.variance_breakdown?.causes || {};
  const totalVariance = variance?.variance_breakdown?.total_variance || 0;

  return (
    <div className="space-y-8 mt-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-black tracking-tight text-white">Variance Analysis</h2>
          <p className="text-sm text-white/40 font-medium mt-1">
            100% delta accounting between snapshots
          </p>
        </div>
        <div className="flex items-center gap-4">
          <select
            className="bg-white/5 border border-white/10 rounded-lg px-4 py-2 text-sm font-bold text-white focus:ring-0 focus:border-white/20"
            value={selectedCompareId || ''}
            onChange={(e) => setSelectedCompareId(Number(e.target.value))}
          >
            <option value="">Select comparison snapshot...</option>
            {snapshots
              .filter((s: any) => s.id !== snapshotId)
              .map((s: any) => (
                <option key={s.id} value={s.id} className="bg-[#0D0D12] text-white">
                  {s.name}
                </option>
              ))}
          </select>
          <Button
            onClick={loadVariance}
            disabled={!selectedCompareId || loading}
            className="bg-white text-[#0A0A0F] hover:bg-white/90 rounded-xl h-10 px-6 text-xs font-bold"
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Analyze
          </Button>
        </div>
      </div>

      {!variance && !loading && (
        <Card className="rounded-[32px] border-white/10 bg-white/5 p-16 text-center">
          <AlertCircle className="h-12 w-12 text-white/30 mx-auto mb-4" />
          <p className="text-white/60 font-medium">
            Select a comparison snapshot to analyze variance
          </p>
        </Card>
      )}

      {loading && !variance && (
        <Card className="rounded-[32px] border-white/10 bg-white/5 p-16 text-center">
          <RefreshCw className="h-12 w-12 text-white/30 mx-auto mb-4 animate-spin" />
          <p className="text-white/60 font-medium">Analyzing variance...</p>
        </Card>
      )}

      {variance && (
        <>
          {/* Summary Card */}
          <Card className="rounded-[32px] border-white/10 bg-white/5 overflow-hidden">
            <CardHeader className="p-8 border-b border-white/10">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-xl font-black text-white">Total Variance</CardTitle>
                  <CardDescription className="text-white/40">
                    Net change between snapshots
                  </CardDescription>
                </div>
                <div className={`text-4xl font-black ${totalVariance >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                  {totalVariance >= 0 ? '+' : ''}€{Math.abs(totalVariance).toLocaleString()}
                </div>
              </div>
            </CardHeader>
            <CardContent className="p-8">
              <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                {Object.entries(causes).map(([key, cause]: [string, any]) => (
                  <div
                    key={key}
                    className="p-6 rounded-2xl border border-white/10 bg-white/5 hover:bg-white/10 transition-all cursor-pointer"
                    onClick={() => loadDrilldown(key)}
                  >
                    <div className="flex items-center justify-between mb-3">
                      <span className="text-[10px] font-black text-white/40 uppercase tracking-widest">
                        {key.replace(/_/g, ' ')}
                      </span>
                      {key === 'new_items' && <FileText className="h-4 w-4 text-blue-400" />}
                      {key === 'timing_shifts' && <Calendar className="h-4 w-4 text-amber-400" />}
                      {key === 'reconciliation' && <RefreshCw className="h-4 w-4 text-emerald-400" />}
                      {key === 'policy_changes' && <Settings className="h-4 w-4 text-purple-400" />}
                    </div>
                    <div className="text-2xl font-black text-white mb-1">
                      €{Math.abs(cause.amount || 0).toLocaleString()}
                    </div>
                    <div className="text-xs text-white/40 font-medium">
                      {cause.count || 0} items
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Drilldown View */}
          {drilldown && selectedCause && (
            <Card className="rounded-[32px] border-white/10 bg-white/5 overflow-hidden">
              <CardHeader className="p-8 border-b border-white/10">
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle className="text-xl font-black text-white">
                      {selectedCause.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())} Drilldown
                    </CardTitle>
                    <CardDescription className="text-white/40">
                      {drilldown.count || 0} items • €{Math.abs(drilldown.amount || 0).toLocaleString()}
                    </CardDescription>
                  </div>
                  <Button
                    variant="outline"
                    onClick={() => {
                      setDrilldown(null);
                      setSelectedCause(null);
                    }}
                    className="border-white/10 text-white hover:bg-white/10"
                  >
                    Close
                  </Button>
                </div>
              </CardHeader>
              <CardContent className="p-8">
                {drilldown.invoice_ids && drilldown.invoice_ids.length > 0 && (
                  <div className="space-y-4">
                    <h4 className="text-sm font-black text-white uppercase tracking-widest mb-4">
                      Invoice IDs
                    </h4>
                    <div className="flex flex-wrap gap-2">
                      {drilldown.invoice_ids.slice(0, 50).map((id: number) => (
                        <Button
                          key={id}
                          variant="outline"
                          size="sm"
                          className="border-white/10 text-white/60 hover:bg-white/10"
                          onClick={() => {
                            // In a real app, this would navigate to invoice detail
                            alert(`View invoice ${id} detail`);
                          }}
                        >
                          #{id}
                        </Button>
                      ))}
                      {drilldown.invoice_ids.length > 50 && (
                        <span className="text-xs text-white/40 font-medium self-center">
                          +{drilldown.invoice_ids.length - 50} more
                        </span>
                      )}
                    </div>
                  </div>
                )}
                {drilldown.transaction_ids && drilldown.transaction_ids.length > 0 && (
                  <div className="space-y-4 mt-6">
                    <h4 className="text-sm font-black text-white uppercase tracking-widest mb-4">
                      Transaction IDs
                    </h4>
                    <div className="flex flex-wrap gap-2">
                      {drilldown.transaction_ids.slice(0, 50).map((id: number) => (
                        <Button
                          key={id}
                          variant="outline"
                          size="sm"
                          className="border-white/10 text-white/60 hover:bg-white/10"
                        >
                          Txn #{id}
                        </Button>
                      ))}
                    </div>
                  </div>
                )}
                {drilldown.reconciliation_ids && drilldown.reconciliation_ids.length > 0 && (
                  <div className="space-y-4 mt-6">
                    <h4 className="text-sm font-black text-white uppercase tracking-widest mb-4">
                      Reconciliation IDs
                    </h4>
                    <div className="flex flex-wrap gap-2">
                      {drilldown.reconciliation_ids.slice(0, 50).map((id: number) => (
                        <Button
                          key={id}
                          variant="outline"
                          size="sm"
                          className="border-white/10 text-white/60 hover:bg-white/10"
                        >
                          Recon #{id}
                        </Button>
                      ))}
                    </div>
                  </div>
                )}
                {drilldown.changes && drilldown.changes.length > 0 && (
                  <div className="space-y-4 mt-6">
                    <h4 className="text-sm font-black text-white uppercase tracking-widest mb-4">
                      Policy Changes
                    </h4>
                    <Table>
                      <TableHeader>
                        <TableRow className="border-white/10">
                          <TableHead className="text-white/60">Type</TableHead>
                          <TableHead className="text-white/60">Old Value</TableHead>
                          <TableHead className="text-white/60">New Value</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {drilldown.changes.map((change: any, i: number) => (
                          <TableRow key={i} className="border-white/10">
                            <TableCell className="text-white font-medium">
                              {change.type}
                            </TableCell>
                            <TableCell className="text-white/60">{change.old}</TableCell>
                            <TableCell className="text-white">{change.new}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                )}
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  );
}


