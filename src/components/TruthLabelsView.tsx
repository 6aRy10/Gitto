'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "./ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "./ui/table";
import { Button } from "./ui/button";
import { getTruthLabels } from '../lib/api';
import { 
  ShieldCheck, AlertCircle, CheckCircle2, HelpCircle, 
  TrendingUp, RefreshCw, Eye
} from "lucide-react";

interface TruthLabelSummary {
  summary: {
    bank_true: { count: number; amount: number; pct: number };
    reconciled: { count: number; amount: number; pct: number };
    modeled: { count: number; amount: number; pct: number };
    unknown: { count: number; amount: number; pct: number };
  };
  total_count: number;
  total_amount: number;
}

export default function TruthLabelsView({ snapshotId }: { snapshotId: number }) {
  const [labels, setLabels] = useState<TruthLabelSummary | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (snapshotId) {
      loadTruthLabels();
    }
  }, [snapshotId]);

  const loadTruthLabels = async () => {
    setLoading(true);
    try {
      const data = await getTruthLabels(snapshotId);
      setLabels(data);
    } catch (e: any) {
      console.error("Failed to load truth labels:", e);
      alert(e.response?.data?.detail || "Failed to load truth labels");
    }
    setLoading(false);
  };

  const labelConfig = {
    bank_true: {
      label: 'Bank-True',
      icon: ShieldCheck,
      color: 'text-emerald-400',
      bgColor: 'bg-emerald-500/20',
      borderColor: 'border-emerald-500/30',
      description: 'Matched to bank transaction (reconciled)'
    },
    reconciled: {
      label: 'Reconciled',
      icon: CheckCircle2,
      color: 'text-blue-400',
      bgColor: 'bg-blue-500/20',
      borderColor: 'border-blue-500/30',
      description: 'Matched via reconciliation (any tier)'
    },
    modeled: {
      label: 'Modeled',
      icon: TrendingUp,
      color: 'text-amber-400',
      bgColor: 'bg-amber-500/20',
      borderColor: 'border-amber-500/30',
      description: 'Forecasted (not yet paid)'
    },
    unknown: {
      label: 'Unknown',
      icon: HelpCircle,
      color: 'text-red-400',
      bgColor: 'bg-red-500/20',
      borderColor: 'border-red-500/30',
      description: 'Missing data (FX, due date, etc.)'
    }
  };

  if (loading && !labels) {
    return (
      <Card className="rounded-[32px] border-white/10 bg-white/5 p-16 text-center">
        <RefreshCw className="h-12 w-12 text-white/30 mx-auto mb-4 animate-spin" />
        <p className="text-white/60 font-medium">Loading truth labels...</p>
      </Card>
    );
  }

  if (!labels) {
    return null;
  }

  const summary = labels.summary;

  return (
    <div className="space-y-8 mt-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-black tracking-tight text-white">Truth Labels</h2>
          <p className="text-sm text-white/40 font-medium mt-1">
            CFO Trust: Every number explainable to row IDs
          </p>
        </div>
        <Button
          onClick={loadTruthLabels}
          disabled={loading}
          className="bg-white text-[#0A0A0F] hover:bg-white/90 rounded-xl h-10 px-6 text-xs font-bold"
        >
          <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        {Object.entries(labelConfig).map(([key, config]) => {
          const data = summary[key as keyof typeof summary];
          const Icon = config.icon;
          
          return (
            <Card
              key={key}
              className={`rounded-[32px] border ${config.borderColor} ${config.bgColor} overflow-hidden`}
            >
              <CardHeader className="p-6 border-b border-white/10">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className={`p-3 rounded-xl ${config.bgColor} border ${config.borderColor}`}>
                      <Icon className={`h-5 w-5 ${config.color}`} />
                    </div>
                    <div>
                      <CardTitle className="text-sm font-black text-white">{config.label}</CardTitle>
                      <CardDescription className="text-[10px] text-white/40">
                        {data.pct.toFixed(1)}%
                      </CardDescription>
                    </div>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="p-6">
                <div className="space-y-2">
                  <div className="text-2xl font-black text-white">
                    €{data.amount.toLocaleString()}
                  </div>
                  <div className="text-xs text-white/40 font-medium">
                    {data.count.toLocaleString()} items
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Detailed Table */}
      <Card className="rounded-[32px] border-white/10 bg-white/5 overflow-hidden">
        <CardHeader className="p-8 border-b border-white/10">
          <CardTitle className="text-xl font-black text-white">Truth Label Breakdown</CardTitle>
          <CardDescription className="text-white/40">
            Total: {labels.total_count.toLocaleString()} items • €{labels.total_amount.toLocaleString()}
          </CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader className="bg-white/5">
              <TableRow className="border-white/10">
                <TableHead className="text-white/60 font-black uppercase text-[10px] tracking-widest">Label</TableHead>
                <TableHead className="text-white/60 font-black uppercase text-[10px] tracking-widest">Count</TableHead>
                <TableHead className="text-white/60 font-black uppercase text-[10px] tracking-widest">Amount</TableHead>
                <TableHead className="text-white/60 font-black uppercase text-[10px] tracking-widest">Percentage</TableHead>
                <TableHead className="text-white/60 font-black uppercase text-[10px] tracking-widest">Description</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {Object.entries(labelConfig).map(([key, config]) => {
                const data = summary[key as keyof typeof summary];
                const Icon = config.icon;
                
                return (
                  <TableRow key={key} className="border-white/10 hover:bg-white/5">
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <Icon className={`h-4 w-4 ${config.color}`} />
                        <span className="text-white font-bold">{config.label}</span>
                      </div>
                    </TableCell>
                    <TableCell className="text-white font-medium">
                      {data.count.toLocaleString()}
                    </TableCell>
                    <TableCell className="text-white font-black">
                      €{data.amount.toLocaleString()}
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <div className="flex-1 h-2 bg-white/10 rounded-full overflow-hidden">
                          <div
                            className={`h-full ${config.bgColor}`}
                            style={{ width: `${data.pct}%` }}
                          />
                        </div>
                        <span className="text-white/60 text-xs font-bold w-12 text-right">
                          {data.pct.toFixed(1)}%
                        </span>
                      </div>
                    </TableCell>
                    <TableCell className="text-white/60 text-xs font-medium">
                      {config.description}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}


