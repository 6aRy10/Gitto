'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "./ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "./ui/table";
import { Button } from "./ui/button";
import { api } from '../lib/api';
import { Database, Landmark, RefreshCw, CheckCircle2, AlertCircle, Upload, ListTodo, TrendingUp, TrendingDown, Target } from "lucide-react";
import UnmatchedQueueView from './UnmatchedQueueView';

interface CashExplained {
  explained_pct: number;
  trend_vs_prior_week: number;
  breakdown: {
    deterministic: number;
    rules: number;
    manual: number;
    suggested: number;
    unmatched: number;
  };
  total_movements: number;
  total_amount: number;
  unmatched_amount: number;
}

export default function BankLedgerView({ entityId }: { entityId: number }) {
  const [activeSubTab, setActiveTab] = useState<'ledger' | 'queue'>('ledger');
  const [ledger, setLedger] = useState<any>(null);
  const [suggestions, setSuggestions] = useState<any[]>([]);
  const [washes, setWashes] = useState<any[]>([]);
  const [cashExplained, setCashExplained] = useState<CashExplained | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (entityId) {
      loadLedger();
      loadSuggestions();
      loadWashes();
      loadCashExplained();
    }
  }, [entityId]);

  const loadLedger = async () => {
    setLoading(true);
    try {
      const res = await api.get(`/entities/${entityId}/cash-ledger`);
      setLedger(res.data);
    } catch (e) { console.error(e); }
    setLoading(false);
  };

  const loadSuggestions = async () => {
    try {
      const res = await api.get(`/entities/${entityId}/reconciliation-suggestions`);
      setSuggestions(res.data);
    } catch (e) { console.error(e); }
  };

  const loadWashes = async () => {
    try {
      const res = await api.get(`/entities/${entityId}/washes`);
      setWashes(res.data);
    } catch (e) { console.error(e); }
  };

  const loadCashExplained = async () => {
    try {
      const res = await api.get(`/entities/${entityId}/cash-explained`);
      setCashExplained(res.data);
    } catch (e) { console.error(e); }
  };

  const handleReconcile = async () => {
    setLoading(true);
    await api.post(`/entities/${entityId}/reconcile`);
    await Promise.all([loadLedger(), loadSuggestions(), loadWashes()]);
    setLoading(false);
  };

  const approveSuggestion = async (txId: number, invId: number) => {
    alert(`Approved Match: Transaction ${txId} -> Invoice ${invId}`);
    handleReconcile();
  };

  const approveWash = async (tx1Id: number, tx2Id: number) => {
    await api.post(`/bank/approve-wash?tx1_id=${tx1Id}&tx2_id=${tx2Id}`);
    loadWashes();
    loadLedger();
  };

  return (
    <div className="space-y-8 mt-6">
      {/* Sub-navigation Cockpit */}
      <div className="flex items-center gap-6 border-b border-[#E5E5E7] pb-4">
        <button 
          onClick={() => setActiveTab('ledger')}
          className={`text-xs font-black uppercase tracking-[0.2em] pb-2 transition-all border-b-2 ${
            activeSubTab === 'ledger' ? 'border-blue-600 text-blue-600' : 'border-transparent text-slate-400 hover:text-slate-600'
          }`}
        >
          Immutable Ledger
        </button>
        <button 
          onClick={() => setActiveTab('queue')}
          className={`flex items-center gap-2 text-xs font-black uppercase tracking-[0.2em] pb-2 transition-all border-b-2 ${
            activeSubTab === 'queue' ? 'border-amber-500 text-amber-600' : 'border-transparent text-slate-400 hover:text-slate-600'
          }`}
        >
          Exceptions Queue
          <span className="px-1.5 py-0.5 rounded-md bg-amber-50 text-[10px] text-amber-600 border border-amber-100">
            {ledger?.recent_transactions?.filter((t: any) => !t.is_reconciled).length || 0}
          </span>
        </button>
      </div>

      {activeSubTab === 'queue' ? (
        <UnmatchedQueueView entityId={entityId} />
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-5 gap-6">
            {/* Cash Explained % - North-Star Trust Metric */}
            {cashExplained && (
              <Card className="md:col-span-2 bg-gradient-to-br from-blue-600 to-indigo-700 text-white border-none shadow-xl overflow-hidden relative">
                <div className="absolute top-0 right-0 w-32 h-32 bg-white/5 rounded-full -translate-y-1/2 translate-x-1/2" />
                <CardHeader className="pb-2">
                  <div className="flex items-center justify-between">
                    <CardDescription className="text-blue-200 uppercase tracking-widest text-[10px] font-black flex items-center gap-2">
                      <Target className="h-3 w-3" /> Trust Metric
                    </CardDescription>
                    <div className={`flex items-center gap-1 text-[10px] font-black px-2 py-1 rounded-full ${
                      cashExplained.trend_vs_prior_week >= 0 
                        ? 'bg-emerald-500/20 text-emerald-300' 
                        : 'bg-red-500/20 text-red-300'
                    }`}>
                      {cashExplained.trend_vs_prior_week >= 0 ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
                      {cashExplained.trend_vs_prior_week >= 0 ? '+' : ''}{cashExplained.trend_vs_prior_week}% WoW
                    </div>
                  </div>
                  <CardTitle className="text-5xl font-black tracking-tighter mt-2">
                    {cashExplained.explained_pct}%
                  </CardTitle>
                  <p className="text-sm font-bold text-blue-100 mt-1">Cash Movements Explained</p>
                </CardHeader>
                <CardContent className="pt-4">
                  {/* Breakdown bar */}
                  <div className="space-y-2">
                    <div className="flex h-2 rounded-full overflow-hidden bg-white/10">
                      <div 
                        className="bg-emerald-400" 
                        style={{ width: `${(cashExplained.breakdown.deterministic / cashExplained.total_movements * 100) || 0}%` }} 
                        title="Deterministic"
                      />
                      <div 
                        className="bg-blue-400" 
                        style={{ width: `${(cashExplained.breakdown.rules / cashExplained.total_movements * 100) || 0}%` }}
                        title="Rules"
                      />
                      <div 
                        className="bg-amber-400" 
                        style={{ width: `${(cashExplained.breakdown.manual / cashExplained.total_movements * 100) || 0}%` }}
                        title="Manual"
                      />
                      <div 
                        className="bg-purple-400" 
                        style={{ width: `${(cashExplained.breakdown.suggested / cashExplained.total_movements * 100) || 0}%` }}
                        title="Suggested"
                      />
                    </div>
                    <div className="flex items-center justify-between text-[9px] font-bold text-blue-200 uppercase">
                      <span>Auto: {cashExplained.breakdown.deterministic + cashExplained.breakdown.rules}</span>
                      <span>Manual: {cashExplained.breakdown.manual}</span>
                      <span className="text-amber-300">Pending: {cashExplained.breakdown.unmatched}</span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}

            <Card className="bg-slate-900 text-white border-none shadow-xl">
              <CardHeader className="pb-2">
                <CardDescription className="text-slate-400 uppercase tracking-widest text-[10px] font-black">Bank-Truth Balance</CardDescription>
                <CardTitle className="text-3xl font-black">€{ledger?.total_cash?.toLocaleString() || '0'}</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex items-center gap-2 text-xs text-emerald-400 font-bold">
                  <CheckCircle2 className="h-3 w-3" />
                  Live Feed Connected
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardDescription className="uppercase tracking-widest text-[10px] font-black">Reconciliation Status</CardDescription>
                <CardTitle className="text-2xl font-black">
                  {ledger?.recent_transactions?.filter((t: any) => t.is_reconciled).length || 0} / {ledger?.recent_transactions?.length || 0}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-xs text-slate-500 font-medium text-left">Recent transactions matched to invoices.</p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardDescription className="uppercase tracking-widest text-[10px] font-black">Suggested Matches</CardDescription>
                <CardTitle className="text-2xl font-black">{suggestions.length}</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-xs text-blue-600 font-bold text-left animate-pulse">Action Required</p>
              </CardContent>
            </Card>

            <Card className="flex flex-col justify-center p-6">
              <Button 
                className="w-full h-full bg-[#1A1A1A] hover:bg-slate-800 text-white font-black rounded-2xl shadow-lg"
                onClick={handleReconcile}
                disabled={loading}
              >
                <RefreshCw className={`mr-2 h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
                Run Recon Engine
              </Button>
            </Card>
          </div>

          {(suggestions.length > 0 || washes.length > 0) && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
              {suggestions.length > 0 && (
                <Card className="border-blue-100 bg-blue-50/30 rounded-[32px] overflow-hidden">
                  <CardHeader className="bg-blue-50/50 px-8 py-4">
                    <CardTitle className="text-sm font-black text-blue-900 uppercase tracking-wider">Matching Queue</CardTitle>
                  </CardHeader>
                  <CardContent className="p-0">
                    <Table>
                      <TableBody>
                        {suggestions.map((s, i) => (
                          <TableRow key={i} className="border-blue-50">
                            <TableCell className="px-6 py-4">
                              <div className="text-[10px] font-bold text-slate-400 uppercase">Transaction</div>
                              <div className="text-xs font-black">€{s.transaction.amount.toLocaleString()} from {s.transaction.counterparty}</div>
                            </TableCell>
                            <TableCell className="px-6 py-4">
                              <div className="text-[10px] font-bold text-slate-400 uppercase">Suggested Invoice</div>
                              <div className="text-xs font-black text-blue-700">Inv #{s.suggestion.document_number} ({s.suggestion.customer})</div>
                            </TableCell>
                            <TableCell className="px-6 text-right">
                              <Button 
                                size="sm" 
                                className="bg-blue-600 text-white font-black text-[10px] rounded-lg h-8"
                                onClick={() => approveSuggestion(s.transaction.id, s.suggestion.id)}
                              >
                                Approve Match
                              </Button>
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </CardContent>
                </Card>
              )}

              {washes.length > 0 && (
                <Card className="border-emerald-100 bg-emerald-50/30 rounded-[32px] overflow-hidden">
                  <CardHeader className="bg-emerald-50/50 px-8 py-4">
                    <CardTitle className="text-sm font-black text-emerald-900 uppercase tracking-wider">Suggested Washes</CardTitle>
                  </CardHeader>
                  <CardContent className="p-0">
                    <Table>
                      <TableBody>
                        {washes.map((w, i) => (
                          <TableRow key={i} className="border-emerald-50">
                            <TableCell className="px-6 py-4">
                              <div className="text-[10px] font-bold text-slate-400 uppercase">Intercompany Transfer</div>
                              <div className="text-xs font-black">€{w.amount.toLocaleString()} detected between {w.from_entity} & {w.to_entity}</div>
                            </TableCell>
                            <TableCell className="px-6 text-right">
                              <Button 
                                size="sm" 
                                className="bg-emerald-600 text-white font-black text-[10px] rounded-lg h-8"
                                onClick={() => approveWash(w.tx1_id, w.tx2_id)}
                              >
                                Mark as Wash
                              </Button>
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </CardContent>
                </Card>
              )}
            </div>
          )}

          <Card className="rounded-[32px] border-slate-100 shadow-sm overflow-hidden">
            <CardHeader className="border-b border-slate-50 px-8 py-6">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-xl font-black tracking-tight">Immutable Cash Ledger</CardTitle>
                  <CardDescription>Actual bank transactions fetched from live feeds.</CardDescription>
                </div>
                <Button variant="outline" className="rounded-xl border-slate-200 font-bold text-xs h-9">
                  <Database className="mr-2 h-3 w-3" /> Export Ledger
                </Button>
              </div>
            </CardHeader>
            <CardContent className="p-0">
              {ledger?.recent_transactions?.length > 0 ? (
                <Table>
                  <TableHeader className="bg-slate-50/50">
                    <TableRow>
                      <TableHead className="px-8 font-black uppercase text-[10px] tracking-widest">Date</TableHead>
                      <TableHead className="font-black uppercase text-[10px] tracking-widest">Counterparty</TableHead>
                      <TableHead className="font-black uppercase text-[10px] tracking-widest">Type</TableHead>
                      <TableHead className="font-black uppercase text-[10px] tracking-widest">Status</TableHead>
                      <TableHead className="text-right px-8 font-black uppercase text-[10px] tracking-widest">Amount</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {ledger?.recent_transactions?.map((tx: any, i: number) => (
                      <TableRow key={i} className="hover:bg-slate-50/50 transition-colors border-slate-50">
                        <TableCell className="px-8 font-semibold text-slate-500 text-xs">
                          {new Date(tx.transaction_date).toLocaleDateString()}
                        </TableCell>
                        <TableCell className="font-bold text-slate-900">{tx.counterparty || 'Unknown'}</TableCell>
                        <TableCell>
                          <span className="px-2 py-1 rounded-lg bg-slate-100 text-slate-600 text-[10px] font-black uppercase tracking-wider">
                            {tx.transaction_type.replace('_', ' ')}
                          </span>
                        </TableCell>
                        <TableCell>
                          {tx.is_reconciled ? (
                            <div className="flex items-center gap-1.5 text-emerald-600 text-[10px] font-black uppercase tracking-tight">
                              <CheckCircle2 className="h-3 w-3" /> Reconciled
                            </div>
                          ) : (
                            <div className="flex items-center gap-1.5 text-amber-500 text-[10px] font-black uppercase tracking-tight">
                              <AlertCircle className="h-3 w-3" /> Unmatched
                            </div>
                          )}
                        </TableCell>
                        <TableCell className={`text-right px-8 font-black ${tx.amount > 0 ? 'text-emerald-600' : 'text-slate-900'}`}>
                          {tx.amount > 0 ? '+' : ''}€{Math.abs(tx.amount).toLocaleString()}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              ) : (
                <div className="p-20 text-center space-y-4">
                  <div className="mx-auto w-12 h-12 rounded-full bg-slate-50 flex items-center justify-center">
                    <Landmark className="h-6 w-6 text-slate-300" />
                  </div>
                  <div className="space-y-1">
                    <p className="text-slate-900 font-bold">No transactions found</p>
                    <p className="text-slate-500 text-sm">Upload a bank CSV or connect a live feed to see your ledger.</p>
                  </div>
                  <Button variant="outline" className="rounded-xl border-slate-200 font-bold text-xs h-9 relative">
                    <Upload className="mr-2 h-3 w-3" /> Upload Bank CSV
                    <input 
                      type="file" 
                      className="absolute inset-0 opacity-0 cursor-pointer" 
                      accept=".csv"
                      onChange={async (e) => {
                        if (e.target.files?.[0]) {
                          const formData = new FormData();
                          formData.append('file', e.target.files[0]);
                          await api.post('/bank-accounts/1/upload-csv', formData);
                          loadLedger();
                        }
                      }}
                    />
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
