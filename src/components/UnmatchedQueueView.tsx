'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "./ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "./ui/table";
import { Button } from "./ui/button";
import { getUnmatchedTransactions, updateTransactionStatus, assignTransaction, getSLAAging } from '../lib/api';
import { AlertCircle, CheckCircle2, ChevronRight, Search, Landmark, User, Clock, RefreshCw } from "lucide-react";

export default function UnmatchedQueueView({ entityId }: { entityId: number }) {
  const [unmatched, setUnmatched] = useState<any[]>([]);
  const [slaAging, setSlaAging] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [assigneeFilter, setAssigneeFilter] = useState<string>('');

  useEffect(() => {
    if (entityId) {
      loadUnmatched();
      loadSLAAging();
    }
  }, [entityId, statusFilter, assigneeFilter]);

  const loadUnmatched = async () => {
    setLoading(true);
    try {
      const data = await getUnmatchedTransactions(entityId, statusFilter || undefined, assigneeFilter || undefined);
      setUnmatched(data.transactions || []);
    } catch (e: any) {
      console.error("Failed to load unmatched transactions:", e);
      alert(e.response?.data?.detail || "Failed to load unmatched transactions");
    }
    setLoading(false);
  };

  const loadSLAAging = async () => {
    try {
      const data = await getSLAAging(entityId);
      setSlaAging(data);
    } catch (e) {
      console.error("Failed to load SLA aging:", e);
    }
  };

  const handleStatusUpdate = async (txnId: number, newStatus: string) => {
    try {
      await updateTransactionStatus(txnId, newStatus);
      await loadUnmatched();
      await loadSLAAging();
    } catch (e: any) {
      alert(e.response?.data?.detail || "Failed to update status");
    }
  };

  const handleAssign = async (txnId: number, assignee: string) => {
    try {
      await assignTransaction(txnId, assignee);
      await loadUnmatched();
    } catch (e: any) {
      alert(e.response?.data?.detail || "Failed to assign transaction");
    }
  };

  const handleManualReconcile = (txnId: number) => {
    alert(`Opening Manual Reconciliation Dialog for Transaction ${txnId}...`);
    // This would open a search modal to find any invoice and link it
  };

  const statusColors: Record<string, string> = {
    'New': 'bg-blue-500/20 text-blue-300 border-blue-500/30',
    'Assigned': 'bg-purple-500/20 text-purple-300 border-purple-500/30',
    'In Review': 'bg-amber-500/20 text-amber-300 border-amber-500/30',
    'Resolved': 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30',
    'Escalated': 'bg-red-500/20 text-red-300 border-red-500/30',
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-xl font-black tracking-tight text-white">Unmatched Transactions Queue</h3>
          <p className="text-[11px] font-bold text-white/40 uppercase tracking-widest">Action required for {unmatched.length} items</p>
        </div>
        <div className="flex items-center gap-4">
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-white/5 border border-white/10 rounded-lg px-3 py-1.5 text-xs font-bold text-white focus:ring-0 focus:border-white/20"
          >
            <option value="">All Statuses</option>
            <option value="New">New</option>
            <option value="Assigned">Assigned</option>
            <option value="In Review">In Review</option>
            <option value="Resolved">Resolved</option>
            <option value="Escalated">Escalated</option>
          </select>
          <input
            type="text"
            value={assigneeFilter}
            onChange={(e) => setAssigneeFilter(e.target.value)}
            placeholder="Filter by assignee..."
            className="bg-white/5 border border-white/10 rounded-lg px-3 py-1.5 text-xs font-bold text-white placeholder-white/30 focus:ring-0 focus:border-white/20 w-40"
          />
          <Button
            onClick={loadUnmatched}
            disabled={loading}
            className="bg-white text-[#0A0A0F] hover:bg-white/90 rounded-xl h-9 px-4 text-xs font-bold"
          >
            <RefreshCw className={`h-3.5 w-3.5 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
      </div>

      {/* SLA Aging Summary */}
      {slaAging && (
        <Card className="rounded-[32px] border-white/10 bg-white/5 overflow-hidden">
          <CardHeader className="p-6 border-b border-white/10">
            <CardTitle className="text-sm font-black text-white flex items-center gap-2">
              <Clock className="h-4 w-4 text-amber-400" />
              SLA Aging Report
            </CardTitle>
          </CardHeader>
          <CardContent className="p-6">
            <div className="grid grid-cols-4 gap-4">
              {Object.entries(slaAging.aging_buckets || {}).map(([bucket, count]: [string, any]) => (
                <div key={bucket} className="p-4 rounded-xl border border-white/10 bg-white/5">
                  <div className="text-xs text-white/40 font-bold uppercase tracking-widest mb-1">{bucket}</div>
                  <div className="text-2xl font-black text-white">{count}</div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      <Card className="rounded-[32px] border-white/10 bg-white/5 overflow-hidden">
        <CardContent className="p-0">
          {unmatched.length > 0 ? (
            <Table>
              <TableHeader className="bg-white/5">
                <TableRow className="border-white/10">
                  <TableHead className="px-8 font-black uppercase text-[10px] tracking-widest text-white/60">Date</TableHead>
                  <TableHead className="font-black uppercase text-[10px] tracking-widest text-white/60">Reference</TableHead>
                  <TableHead className="font-black uppercase text-[10px] tracking-widest text-white/60">Counterparty</TableHead>
                  <TableHead className="font-black uppercase text-[10px] tracking-widest text-white/60">Status</TableHead>
                  <TableHead className="font-black uppercase text-[10px] tracking-widest text-white/60">Assignee</TableHead>
                  <TableHead className="text-right px-8 font-black uppercase text-[10px] tracking-widest text-white/60">Amount</TableHead>
                  <TableHead className="w-48"></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {unmatched.map((tx: any, i: number) => (
                  <TableRow key={i} className="border-white/10 hover:bg-white/5">
                    <TableCell className="px-8 py-6">
                      <div className="text-xs font-bold text-white">
                        {tx.transaction_date ? new Date(tx.transaction_date).toLocaleDateString() : 'N/A'}
                      </div>
                      {tx.sla_days && (
                        <div className="text-[10px] text-white/40 font-medium">
                          {tx.sla_days} days old
                        </div>
                      )}
                    </TableCell>
                    <TableCell className="text-white/80 text-xs font-medium truncate max-w-[200px]">
                      {tx.reference || tx.transaction_reference || 'N/A'}
                    </TableCell>
                    <TableCell className="font-medium text-sm text-white">{tx.counterparty || 'Unknown'}</TableCell>
                    <TableCell>
                      <span className={`px-2.5 py-1 rounded-lg text-[10px] font-black uppercase tracking-wider border ${
                        statusColors[tx.status] || 'bg-white/10 text-white/60 border-white/10'
                      }`}>
                        {tx.status || 'New'}
                      </span>
                    </TableCell>
                    <TableCell>
                      {tx.assignee ? (
                        <div className="flex items-center gap-2">
                          <User className="h-3 w-3 text-white/40" />
                          <span className="text-xs text-white/60 font-medium">{tx.assignee}</span>
                        </div>
                      ) : (
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => {
                            const assignee = prompt('Enter assignee name:');
                            if (assignee) handleAssign(tx.id, assignee);
                          }}
                          className="border-white/10 text-white/60 hover:bg-white/10 text-[10px] h-7"
                        >
                          Assign
                        </Button>
                      )}
                    </TableCell>
                    <TableCell className="text-right tabular-nums font-black text-white px-8">
                      €{Math.abs(tx.amount || 0).toLocaleString()}
                    </TableCell>
                    <TableCell className="pr-8">
                      <div className="flex items-center gap-2">
                        <select
                          value={tx.status || 'New'}
                          onChange={(e) => handleStatusUpdate(tx.id, e.target.value)}
                          className="bg-white/5 border border-white/10 rounded-lg px-2 py-1 text-[10px] font-bold text-white focus:ring-0 focus:border-white/20"
                        >
                          <option value="New">New</option>
                          <option value="Assigned">Assigned</option>
                          <option value="In Review">In Review</option>
                          <option value="Resolved">Resolved</option>
                          <option value="Escalated">Escalated</option>
                        </select>
                        <Button 
                          variant="outline" 
                          size="sm" 
                          className="rounded-xl border-white/10 text-[10px] font-black uppercase tracking-widest hover:bg-white/10 text-white transition-all"
                          onClick={() => handleManualReconcile(tx.id)}
                        >
                          Match
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <div className="py-24 text-center space-y-4">
              <div className="mx-auto w-16 h-16 rounded-full bg-emerald-500/20 flex items-center justify-center">
                <CheckCircle2 className="h-8 w-8 text-emerald-400" />
              </div>
              <div>
                <p className="text-lg font-black text-white">Queue Cleared</p>
                <p className="text-sm text-white/60 font-medium">All bank transactions are successfully reconciled.</p>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

