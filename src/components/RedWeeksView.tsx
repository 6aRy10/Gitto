'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "./ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "./ui/table";
import { Button } from "./ui/button";
import { getRedWeeks, getRedWeekDrilldown } from '../lib/api';
import { 
  AlertTriangle, ChevronRight, DollarSign, TrendingDown, 
  Calendar, RefreshCw, Eye
} from "lucide-react";

interface RedWeek {
  week_index: number;
  week_label: string;
  closing_cash: number;
  threshold: number;
  shortfall: number;
  drivers: Array<{
    type: string;
    description: string;
    impact: number;
  }>;
}

export default function RedWeeksView({ snapshotId }: { snapshotId: number }) {
  const [redWeeks, setRedWeeks] = useState<RedWeek[]>([]);
  const [drilldown, setDrilldown] = useState<any>(null);
  const [selectedWeekIndex, setSelectedWeekIndex] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [threshold, setThreshold] = useState<number | null>(null);

  useEffect(() => {
    if (snapshotId) {
      loadRedWeeks();
    }
  }, [snapshotId]);

  const loadRedWeeks = async () => {
    setLoading(true);
    try {
      const data = await getRedWeeks(snapshotId, threshold || undefined);
      setRedWeeks(data.red_weeks || []);
      if (!threshold && data.threshold) {
        setThreshold(data.threshold);
      }
    } catch (e: any) {
      console.error("Failed to load red weeks:", e);
      alert(e.response?.data?.detail || "Failed to load red weeks");
    }
    setLoading(false);
  };

  const loadDrilldown = async (weekIndex: number) => {
    setLoading(true);
    try {
      const data = await getRedWeekDrilldown(snapshotId, weekIndex);
      setDrilldown(data);
      setSelectedWeekIndex(weekIndex);
    } catch (e: any) {
      console.error("Failed to load drilldown:", e);
      alert(e.response?.data?.detail || "Failed to load drilldown");
    }
    setLoading(false);
  };

  return (
    <div className="space-y-8 mt-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-black tracking-tight text-white">Red Weeks Analysis</h2>
          <p className="text-sm text-white/40 font-medium mt-1">
            Weeks where cash falls below threshold
          </p>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <label className="text-xs text-white/40 font-bold uppercase tracking-widest">
              Threshold:
            </label>
            <input
              type="number"
              value={threshold || ''}
              onChange={(e) => setThreshold(e.target.value ? Number(e.target.value) : null)}
              className="bg-white/5 border border-white/10 rounded-lg px-3 py-1.5 text-sm font-bold text-white w-32 focus:ring-0 focus:border-white/20"
              placeholder="Auto"
            />
          </div>
          <Button
            onClick={loadRedWeeks}
            disabled={loading}
            className="bg-white text-[#0A0A0F] hover:bg-white/90 rounded-xl h-10 px-6 text-xs font-bold"
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
      </div>

      {loading && !redWeeks.length && (
        <Card className="rounded-[32px] border-white/10 bg-white/5 p-16 text-center">
          <RefreshCw className="h-12 w-12 text-white/30 mx-auto mb-4 animate-spin" />
          <p className="text-white/60 font-medium">Analyzing red weeks...</p>
        </Card>
      )}

      {!loading && redWeeks.length === 0 && (
        <Card className="rounded-[32px] border-white/10 bg-white/5 p-16 text-center">
          <div className="w-16 h-16 bg-emerald-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
            <TrendingDown className="h-8 w-8 text-emerald-400" />
          </div>
          <h3 className="text-xl font-black text-white mb-2">No Red Weeks</h3>
          <p className="text-white/60 font-medium">
            All weeks are above the cash threshold. Great job!
          </p>
        </Card>
      )}

      {redWeeks.length > 0 && (
        <>
          {/* Summary */}
          <Card className="rounded-[32px] border-red-500/20 bg-red-500/5 overflow-hidden">
            <CardHeader className="p-8 border-b border-red-500/20">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-xl font-black text-white flex items-center gap-2">
                    <AlertTriangle className="h-5 w-5 text-red-400" />
                    {redWeeks.length} Red Week{redWeeks.length !== 1 ? 's' : ''} Detected
                  </CardTitle>
                  <CardDescription className="text-white/40">
                    Total shortfall: €{redWeeks.reduce((sum, w) => sum + w.shortfall, 0).toLocaleString()}
                  </CardDescription>
                </div>
                <div className="text-3xl font-black text-red-400">
                  {redWeeks.length}
                </div>
              </div>
            </CardHeader>
          </Card>

          {/* Red Weeks List */}
          <Card className="rounded-[32px] border-white/10 bg-white/5 overflow-hidden">
            <CardHeader className="p-8 border-b border-white/10">
              <CardTitle className="text-xl font-black text-white">Red Weeks Detail</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <Table>
                <TableHeader className="bg-white/5">
                  <TableRow className="border-white/10">
                    <TableHead className="text-white/60 font-black uppercase text-[10px] tracking-widest">Week</TableHead>
                    <TableHead className="text-white/60 font-black uppercase text-[10px] tracking-widest">Closing Cash</TableHead>
                    <TableHead className="text-white/60 font-black uppercase text-[10px] tracking-widest">Threshold</TableHead>
                    <TableHead className="text-white/60 font-black uppercase text-[10px] tracking-widest">Shortfall</TableHead>
                    <TableHead className="text-white/60 font-black uppercase text-[10px] tracking-widest">Drivers</TableHead>
                    <TableHead className="text-white/60 font-black uppercase text-[10px] tracking-widest"></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {redWeeks.map((week, i) => (
                    <TableRow key={i} className="border-white/10 hover:bg-white/5">
                      <TableCell className="text-white font-bold">
                        {week.week_label}
                      </TableCell>
                      <TableCell className="text-red-400 font-black">
                        €{week.closing_cash.toLocaleString()}
                      </TableCell>
                      <TableCell className="text-white/60 font-medium">
                        €{week.threshold.toLocaleString()}
                      </TableCell>
                      <TableCell className="text-red-400 font-black">
                        €{week.shortfall.toLocaleString()}
                      </TableCell>
                      <TableCell>
                        <div className="flex flex-wrap gap-1.5">
                          {week.drivers?.slice(0, 2).map((driver, j) => (
                            <span
                              key={j}
                              className="px-2 py-1 rounded-lg bg-red-500/20 text-red-300 text-[9px] font-bold border border-red-500/30"
                            >
                              {driver.type}
                            </span>
                          ))}
                          {week.drivers && week.drivers.length > 2 && (
                            <span className="text-[9px] text-white/40 font-medium">
                              +{week.drivers.length - 2} more
                            </span>
                          )}
                        </div>
                      </TableCell>
                      <TableCell>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => loadDrilldown(week.week_index)}
                          className="border-white/10 text-white hover:bg-white/10"
                        >
                          <Eye className="h-3 w-3 mr-1" />
                          View
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>

          {/* Drilldown View */}
          {drilldown && selectedWeekIndex !== null && (
            <Card className="rounded-[32px] border-white/10 bg-white/5 overflow-hidden">
              <CardHeader className="p-8 border-b border-white/10">
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle className="text-xl font-black text-white">
                      Week {drilldown.week_label} Drilldown
                    </CardTitle>
                    <CardDescription className="text-white/40">
                      Shortfall: €{drilldown.shortfall?.toLocaleString() || '0'}
                    </CardDescription>
                  </div>
                  <Button
                    variant="outline"
                    onClick={() => {
                      setDrilldown(null);
                      setSelectedWeekIndex(null);
                    }}
                    className="border-white/10 text-white hover:bg-white/10"
                  >
                    Close
                  </Button>
                </div>
              </CardHeader>
              <CardContent className="p-8">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                  {/* Inflows */}
                  <div>
                    <h4 className="text-sm font-black text-white uppercase tracking-widest mb-4 flex items-center gap-2">
                      <TrendingDown className="h-4 w-4 text-emerald-400 rotate-180" />
                      Inflows
                    </h4>
                    <div className="space-y-3">
                      <div className="p-4 rounded-xl border border-white/10 bg-white/5">
                        <div className="text-xs text-white/40 font-bold uppercase tracking-widest mb-1">
                          Total Inflow
                        </div>
                        <div className="text-2xl font-black text-emerald-400">
                          €{drilldown.total_inflow?.toLocaleString() || '0'}
                        </div>
                      </div>
                      {drilldown.inflow_items && drilldown.inflow_items.length > 0 && (
                        <div className="space-y-2 max-h-64 overflow-y-auto">
                          {drilldown.inflow_items.slice(0, 10).map((item: any, i: number) => (
                            <div
                              key={i}
                              className="p-3 rounded-lg border border-white/10 bg-white/5 flex items-center justify-between"
                            >
                              <div>
                                <div className="text-xs font-bold text-white">
                                  {item.customer || item.invoice_number || `Item ${i + 1}`}
                                </div>
                                <div className="text-[10px] text-white/40 font-medium">
                                  {item.expected_date || 'No date'}
                                </div>
                              </div>
                              <div className="text-sm font-black text-emerald-400">
                                €{item.amount?.toLocaleString() || '0'}
                              </div>
                            </div>
                          ))}
                          {drilldown.inflow_items.length > 10 && (
                            <div className="text-xs text-white/40 font-medium text-center py-2">
                              +{drilldown.inflow_items.length - 10} more items
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Outflows */}
                  <div>
                    <h4 className="text-sm font-black text-white uppercase tracking-widest mb-4 flex items-center gap-2">
                      <TrendingDown className="h-4 w-4 text-red-400" />
                      Outflows
                    </h4>
                    <div className="space-y-3">
                      <div className="p-4 rounded-xl border border-white/10 bg-white/5">
                        <div className="text-xs text-white/40 font-bold uppercase tracking-widest mb-1">
                          Total Outflow
                        </div>
                        <div className="text-2xl font-black text-red-400">
                          €{drilldown.total_outflow?.toLocaleString() || '0'}
                        </div>
                      </div>
                      {drilldown.outflow_items && drilldown.outflow_items.length > 0 && (
                        <div className="space-y-2 max-h-64 overflow-y-auto">
                          {drilldown.outflow_items.slice(0, 10).map((item: any, i: number) => (
                            <div
                              key={i}
                              className="p-3 rounded-lg border border-white/10 bg-white/5 flex items-center justify-between"
                            >
                              <div>
                                <div className="text-xs font-bold text-white">
                                  {item.vendor || item.bill_number || `Item ${i + 1}`}
                                </div>
                                <div className="text-[10px] text-white/40 font-medium">
                                  {item.due_date || 'No date'}
                                </div>
                              </div>
                              <div className="text-sm font-black text-red-400">
                                €{item.amount?.toLocaleString() || '0'}
                              </div>
                            </div>
                          ))}
                          {drilldown.outflow_items.length > 10 && (
                            <div className="text-xs text-white/40 font-medium text-center py-2">
                              +{drilldown.outflow_items.length - 10} more items
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  );
}


