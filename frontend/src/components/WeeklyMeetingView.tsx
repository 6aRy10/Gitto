'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { api } from '@/lib/api';
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Cell
} from 'recharts';

export default function WeeklyMeetingView({ snapshotId, compareId }: { snapshotId: number, compareId?: number }) {
  const [comparison, setComparison] = useState<any[]>([]);
  const [movers, setMovers] = useState<any[]>([]);
  const [priorities, setPriorities] = useState<any[]>([]);

  useEffect(() => {
    if (snapshotId) {
      loadData();
    }
  }, [snapshotId, compareId]);

  const loadData = async () => {
    const [prioData] = await Promise.all([
      api.get(`/snapshots/${snapshotId}/priorities`).then(res => res.data)
    ]);
    setPriorities(prioData);

    if (compareId) {
      const [compData, moverData] = await Promise.all([
        api.get(`/snapshots/${snapshotId}/compare/${compareId}`).then(res => res.data),
        api.get(`/snapshots/${snapshotId}/top-movers?compare_id=${compareId}`).then(res => res.data)
      ]);
      setComparison(compData);
      setMovers(moverData);
    }
  };

  return (
    <div className="space-y-8 mt-6">
      {/* Waterfall Comparison */}
      {compareId && (
        <Card className="bg-white border border-slate-200 shadow-lg">
          <CardHeader>
            <CardTitle>What Changed Since Last Week?</CardTitle>
            <CardDescription>Comparison of expected cash per week (Waterfall effect)</CardDescription>
          </CardHeader>
          <CardContent className="h-[320px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={comparison} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="gainGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#22c55e" stopOpacity={0.85}/>
                    <stop offset="95%" stopColor="#4ade80" stopOpacity={0.15}/>
                  </linearGradient>
                  <linearGradient id="lossGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#f43f5e" stopOpacity={0.9}/>
                    <stop offset="95%" stopColor="#f87171" stopOpacity={0.2}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e5e7eb" />
                <XAxis dataKey="label" tick={{ fill: '#6b7280', fontSize: 12 }} />
                <YAxis tick={{ fill: '#6b7280', fontSize: 12 }} />
                <Tooltip
                  contentStyle={{ borderRadius: 12, borderColor: '#e5e7eb', boxShadow: '0 8px 24px rgba(15,23,42,0.08)' }}
                  formatter={(value: number) => `€${value.toLocaleString()}`}
                />
                <Legend />
                <Bar dataKey="change" name="Net Shift (€)" radius={[8, 8, 0, 0]}>
                  {comparison.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.change >= 0 ? 'url(#gainGradient)' : 'url(#lossGradient)'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      )}

      {/* AR Prioritization */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <Card>
          <CardHeader>
            <CardTitle>Collections Priority List</CardTitle>
            <CardDescription>Top invoices to chase to protect next 4 weeks</CardDescription>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Customer</TableHead>
                  <TableHead>Amount</TableHead>
                  <TableHead>Risk</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {priorities.slice(0, 5).map((prio, i) => (
                  <TableRow key={i}>
                    <TableCell className="text-xs font-bold">{prio.customer}</TableCell>
                    <TableCell className="text-xs font-black">€{prio.amount.toLocaleString()}</TableCell>
                    <TableCell>
                      <span className={`px-1.5 py-0.5 rounded-full text-[10px] font-bold ${
                        prio.lateness_risk_days > 15 ? 'bg-red-100 text-red-700' : 'bg-emerald-100 text-emerald-700'
                      }`}>
                        +{prio.lateness_risk_days}d
                      </span>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>

        {compareId && (
          <Card>
            <CardHeader>
              <CardTitle>Top Drivers (Movers)</CardTitle>
              <CardDescription>Specific invoices that shifted vs last week</CardDescription>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Customer</TableHead>
                    <TableHead>Shift</TableHead>
                    <TableHead>Reason</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {movers.map((m, i) => (
                    <TableRow key={i}>
                      <TableCell className="text-xs font-bold">{m.customer}</TableCell>
                      <TableCell className={`text-xs font-black ${m.shift_days > 0 ? 'text-red-500' : 'text-emerald-500'}`}>
                        {m.shift_days > 0 ? '+' : ''}{m.shift_days}d
                      </TableCell>
                      <TableCell className="text-[10px] text-slate-400 uppercase tracking-tight truncate max-w-[100px]" title={m.reason}>
                        {m.reason}
                      </TableCell>
                    </TableRow>
                  ))}
                  {movers.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={3} className="text-center py-4 text-slate-400 text-xs">No significant date shifts detected.</TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}

