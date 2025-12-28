'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "./ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "./ui/table";
import { Button } from "./ui/button";
import { api } from '../lib/api';
import { ChevronLeft, ChevronRight, Search, Filter, Download } from "lucide-react";

export default function AllInvoicesView({ snapshotId }: { snapshotId: number }) {
  const [data, setData] = useState<any>(null);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (snapshotId) loadInvoices();
  }, [snapshotId, page]);

  const loadInvoices = async () => {
    setLoading(true);
    try {
      const res = await api.get(`/snapshots/${snapshotId}/invoices?page=${page}&page_size=100`);
      setData(res.data);
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  };

  if (!data && loading) return <div className="p-20 text-center font-bold animate-pulse">Loading invoices...</div>;
  if (!data) return null;

  return (
    <div className="space-y-6 mt-6">
      <div className="flex items-center justify-between">
        <div className="text-left">
          <h2 className="text-2xl font-black tracking-tight text-slate-900">All Invoices</h2>
          <p className="text-sm text-slate-500 font-medium">Viewing {data.items.length} of {data.total} total items</p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" className="rounded-xl border-slate-200 font-bold text-xs h-10">
            <Download className="mr-2 h-4 w-4" /> Export CSV
          </Button>
          <div className="flex items-center gap-1 bg-white border border-slate-200 rounded-xl p-1">
            <Button 
              variant="ghost" 
              size="sm" 
              className="h-8 w-8 p-0 rounded-lg"
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page === 1 || loading}
            >
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <div className="px-3 text-xs font-black">
              Page {page} of {data.total_pages}
            </div>
            <Button 
              variant="ghost" 
              size="sm" 
              className="h-8 w-8 p-0 rounded-lg"
              onClick={() => setPage(p => Math.min(data.total_pages, p + 1))}
              disabled={page === data.total_pages || loading}
            >
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>

      <Card className="rounded-[32px] border-slate-100 shadow-sm overflow-hidden bg-white">
        <CardContent className="p-0">
          <Table>
            <TableHeader className="bg-slate-50/50">
              <TableRow>
                <TableHead className="px-8 font-black uppercase text-[10px] tracking-widest">Document #</TableHead>
                <TableHead className="font-black uppercase text-[10px] tracking-widest">Customer</TableHead>
                <TableHead className="font-black uppercase text-[10px] tracking-widest">Country</TableHead>
                <TableHead className="font-black uppercase text-[10px] tracking-widest">Due Date</TableHead>
                <TableHead className="font-black uppercase text-[10px] tracking-widest">Status</TableHead>
                <TableHead className="text-right px-8 font-black uppercase text-[10px] tracking-widest">Amount</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.items.map((inv: any) => (
                <TableRow key={inv.id} className="hover:bg-slate-50/50 transition-colors border-slate-50">
                  <TableCell className="px-8 font-bold text-slate-900 text-xs">
                    {inv.document_number}
                  </TableCell>
                  <TableCell className="font-bold text-slate-700 text-xs">{inv.customer}</TableCell>
                  <TableCell className="text-slate-500 font-medium text-xs">{inv.country}</TableCell>
                  <TableCell className="text-slate-500 font-bold text-xs">
                    {new Date(inv.expected_due_date).toLocaleDateString()}
                  </TableCell>
                  <TableCell>
                    {inv.payment_date ? (
                      <span className="px-2 py-1 rounded-md bg-emerald-50 text-emerald-600 text-[10px] font-black uppercase tracking-wider">Paid</span>
                    ) : (
                      <span className="px-2 py-1 rounded-md bg-amber-50 text-amber-600 text-[10px] font-black uppercase tracking-wider">Open</span>
                    )}
                  </TableCell>
                  <TableCell className="text-right px-8 font-black text-slate-900 text-xs">
                    €{inv.amount.toLocaleString()}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
      
      <div className="flex items-center justify-center gap-4 py-4">
        <Button 
          variant="outline" 
          className="rounded-2xl px-6 border-slate-200 font-black text-xs"
          onClick={() => setPage(p => Math.max(1, p - 1))}
          disabled={page === 1 || loading}
        >
          Previous 100
        </Button>
        <div className="text-sm font-bold text-slate-500">
          Showing {(page-1)*100 + 1} - {Math.min(page*100, data.total)} of {data.total}
        </div>
        <Button 
          variant="outline" 
          className="rounded-2xl px-6 border-slate-200 font-black text-xs"
          onClick={() => setPage(p => Math.min(data.total_pages, p + 1))}
          disabled={page === data.total_pages || loading}
        >
          Next 100
        </Button>
      </div>
    </div>
  );
}

