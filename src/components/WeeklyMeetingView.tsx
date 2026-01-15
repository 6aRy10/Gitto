'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "./ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "./ui/table";
import { Button } from "./ui/button";
import { api, getVariance, getRedWeeks } from '../lib/api';
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Cell,
  AreaChart, Area
} from 'recharts';
import { 
  ChevronRight, ChevronLeft, Landmark, TrendingUp, RefreshCw, AlertTriangle, 
  CheckCircle2, Users, FileText, Lock, PlayCircle, X, Plus, Phone, Mail, ArrowUp, Target
} from 'lucide-react';
import WeeklyCashPack from './WeeklyCashPack';

interface CollectionOutcome {
  id: number;
  action_type: string;
  expected_pullforward_days: number;
  expected_pullforward_amount: number;
  outcome: string | null;
  outcome_amount: number | null;
  owner: string;
  created_at: string;
}

export default function WeeklyMeetingView({ snapshotId, compareId }: { snapshotId: number, compareId?: number }) {
  const [step, setStep] = useState(1);
  const [comparison, setComparison] = useState<any[]>([]);
  const [movers, setMovers] = useState<any[]>([]);
  const [priorities, setPriorities] = useState<any[]>([]);
  const [kpis, setKpis] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [actions, setActions] = useState<any[]>([]);
  const [showPack, setShowPack] = useState(false);
  const [entityData, setEntityData] = useState<any>(null);
  const [collectionOutcomes, setCollectionOutcomes] = useState<{
    summary: any;
    actions: CollectionOutcome[];
    prior_week_outcomes: CollectionOutcome[];
    performance_metrics: { hit_rate: number; avg_pullforward_achieved: number };
  } | null>(null);
  const [variance, setVariance] = useState<any>(null);
  const [redWeeks, setRedWeeks] = useState<any>(null);

  useEffect(() => {
    if (snapshotId) {
      loadMeetingData();
      loadEntityData();
      loadCollectionOutcomes();
    }
  }, [snapshotId, compareId]);

  const loadCollectionOutcomes = async () => {
    try {
      const res = await api.get(`/snapshots/${snapshotId}/collection-actions`);
      setCollectionOutcomes(res.data);
    } catch (e) {
      console.error("Failed to load collection outcomes:", e);
    }
  };

  const loadEntityData = async () => {
    try {
      const snap = await api.get(`/snapshots/${snapshotId}`);
      const entity = await api.get(`/entities/${snap.data.entity_id}`);
      setEntityData(entity.data);
    } catch (e) { console.error(e); }
  };

  useEffect(() => {
    if (snapshotId) loadMeetingData();
  }, [snapshotId, compareId]);

  const loadMeetingData = async () => {
    setLoading(true);
    try {
      const [kpiRes, prioRes, actionRes] = await Promise.all([
        api.get(`/snapshots/${snapshotId}/kpis`),
        api.get(`/snapshots/${snapshotId}/priorities`),
        api.get(`/treasury-actions?snapshot_id=${snapshotId}`)
      ]);
      setKpis(kpiRes.data);
      setPriorities(prioRes.data);
      setActions(actionRes.data);

      if (compareId) {
        const [compRes, moverRes, varianceRes] = await Promise.all([
          api.get(`/snapshots/${snapshotId}/compare/${compareId}`),
          api.get(`/snapshots/${snapshotId}/top-movers?compare_id=${compareId}`),
          getVariance(snapshotId, compareId).catch(() => null)
        ]);
        setComparison(compRes.data);
        setMovers(moverRes.data);
        setVariance(varianceRes);
      }

      // Load red weeks
      const redWeeksData = await getRedWeeks(snapshotId).catch(() => null);
      setRedWeeks(redWeeksData);
    } catch (e) { console.error(e); }
    setLoading(false);
  };

  const steps = [
    { id: 1, title: 'Bank Truth', icon: Landmark, desc: 'Reconciled cash vs exceptions' },
    { id: 2, title: '13-Week Runway', icon: TrendingUp, desc: 'Base vs Downside scenarios' },
    { id: 3, title: 'What Changed', icon: RefreshCw, desc: 'Variance vs last week' },
    { id: 4, title: 'Risks & Drivers', icon: AlertTriangle, desc: 'Top movers and lateness' },
    { id: 5, title: 'Treasury Actions', icon: Users, desc: 'Decisions and ownership' },
  ];

  const nextStep = () => setStep(s => Math.min(s + 1, steps.length));
  const prevStep = () => setStep(s => Math.max(s - 1, 1));

  return (
    <div className="space-y-8 mt-6 max-w-5xl mx-auto pb-24">
      {/* Step Indicator */}
      <div className="flex items-center justify-between px-4 py-8">
        {steps.map((s, i) => (
          <div key={s.id} className="flex items-center group cursor-pointer" onClick={() => setStep(s.id)}>
            <div className={`flex flex-col items-center gap-2 ${step >= s.id ? 'opacity-100' : 'opacity-30'}`}>
              <div className={`h-12 w-12 rounded-2xl flex items-center justify-center transition-all ${step === s.id ? 'bg-slate-900 text-white shadow-xl scale-110' : 'bg-white border-2 border-slate-100 text-slate-400'}`}>
                <s.icon className="h-5 w-5" />
              </div>
              <span className={`text-[10px] font-black uppercase tracking-widest ${step === s.id ? 'text-slate-900' : 'text-slate-400'}`}>{s.title}</span>
            </div>
            {i < steps.length - 1 && (
              <div className={`w-16 h-[2px] mx-4 -mt-6 transition-all ${step > s.id ? 'bg-slate-900' : 'bg-slate-100'}`} />
            )}
          </div>
        ))}
      </div>

      <div className="min-h-[500px] animate-in slide-in-from-bottom-4 duration-500">
        {/* Step 1: Bank Truth */}
        {step === 1 && (
          <Card className="rounded-[40px] border-slate-100 shadow-2xl overflow-hidden bg-white">
            <CardHeader className="p-10 border-b border-slate-50">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-3xl font-black italic tracking-tighter">Bank Reality Check.</CardTitle>
                  <CardDescription className="font-medium text-slate-500">Immutable ledger state and exception status.</CardDescription>
                </div>
                <div className="p-4 bg-emerald-50 rounded-3xl">
                  <Landmark className="h-8 w-8 text-emerald-600" />
                </div>
              </div>
            </CardHeader>
            <CardContent className="p-10 space-y-10">
              <div className="grid grid-cols-3 gap-8">
                <div className="p-8 rounded-[32px] bg-slate-900 text-white">
                  <p className="text-[10px] font-black uppercase tracking-widest text-slate-400 mb-2">Total Bank Cash</p>
                  <p className="text-4xl font-black italic">€{kpis?.opening_bank_balance?.toLocaleString() || '0'}</p>
                </div>
                <div className="p-8 rounded-[32px] border-2 border-slate-50">
                  <p className="text-[10px] font-black uppercase tracking-widest text-slate-400 mb-2">Unmatched Items</p>
                  <p className="text-4xl font-black italic text-red-500">12</p>
                </div>
                <div className="p-8 rounded-[32px] border-2 border-slate-50">
                  <p className="text-[10px] font-black uppercase tracking-widest text-slate-400 mb-2">Open AR Delta</p>
                  <p className="text-4xl font-black italic text-blue-500">€241k</p>
                </div>
              </div>
              <div className="bg-slate-50 rounded-[32px] p-10 flex items-center justify-between border border-slate-100">
                <div className="flex items-center gap-6">
                  <div className="h-14 w-14 bg-white rounded-2xl flex items-center justify-center shadow-sm">
                    <CheckCircle2 className="h-6 w-6 text-emerald-500" />
                  </div>
                  <div>
                    <p className="text-lg font-black text-slate-900 italic">94% of Transactions Reconciled</p>
                    <p className="text-sm text-slate-500 font-medium">Auto-match ladder cleared Tier 1 and Tier 2.</p>
                  </div>
                </div>
                <Button variant="outline" className="rounded-2xl h-12 px-8 font-black uppercase text-[10px] tracking-widest border-slate-200">View Ledger</Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Step 2: 13-Week Runway */}
        {step === 2 && (
          <Card className="rounded-[40px] border-slate-100 shadow-2xl overflow-hidden bg-white">
            <CardHeader className="p-10 border-b border-slate-50">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-3xl font-black italic tracking-tighter">Cash Runway.</CardTitle>
                  <CardDescription className="font-medium text-slate-500">Next 13 weeks projected cash position.</CardDescription>
                </div>
                <div className="p-4 bg-emerald-50 rounded-3xl">
                  <TrendingUp className="h-8 w-8 text-emerald-600" />
                </div>
              </div>
            </CardHeader>
            <CardContent className="p-10">
              {comparison.length > 0 ? (
                <>
                  <div className="h-[400px]">
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={comparison}>
                        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                        <XAxis dataKey="label" tick={{ fill: '#94a3b8', fontSize: 11, fontWeight: 600 }} axisLine={false} tickLine={false} />
                        <YAxis tick={{ fill: '#94a3b8', fontSize: 11, fontWeight: 600 }} axisLine={false} tickLine={false} tickFormatter={(val) => `€${(val/1000).toFixed(0)}k`} />
                        <Tooltip 
                          contentStyle={{ borderRadius: 16, border: '1px solid #e2e8f0', boxShadow: '0 10px 40px rgba(0,0,0,0.08)' }}
                          formatter={(value: any) => [`€${Number(value).toLocaleString()}`, '']}
                        />
                        <Area type="monotone" dataKey="current" name="This Week" stroke="#059669" fill="#059669" fillOpacity={0.1} strokeWidth={3} />
                        <Area type="monotone" dataKey="previous" name="Last Week" stroke="#94a3b8" fill="transparent" strokeDasharray="8 8" strokeWidth={2} />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                  <div className="mt-8 grid grid-cols-2 gap-8 pt-8 border-t border-slate-50">
                    <div className="p-6 rounded-2xl bg-emerald-50/50 border border-emerald-100">
                      <div className="flex items-center gap-3 mb-3">
                        <div className="h-3 w-3 rounded-full bg-emerald-600" />
                        <span className="text-xs font-black uppercase tracking-widest text-emerald-700">Current Forecast</span>
                      </div>
                      <p className="text-slate-600 text-sm font-medium leading-relaxed">
                        Your projected cash balance based on today's receivables and committed payments.
                      </p>
                    </div>
                    <div className="p-6 rounded-2xl bg-slate-50 border border-slate-100">
                      <div className="flex items-center gap-3 mb-3">
                        <div className="h-3 w-3 rounded-full bg-slate-400" />
                        <span className="text-xs font-black uppercase tracking-widest text-slate-500">Last Week's Forecast</span>
                      </div>
                      <p className="text-slate-500 text-sm font-medium leading-relaxed">
                        Compare how your position has changed since last week's review.
                      </p>
                    </div>
                  </div>
                </>
              ) : (
                <div className="h-[400px] flex flex-col items-center justify-center text-center">
                  <div className="w-20 h-20 bg-slate-100 rounded-3xl flex items-center justify-center mb-6">
                    <TrendingUp className="h-10 w-10 text-slate-300" />
                  </div>
                  <h4 className="text-xl font-black text-slate-400 mb-2">No Comparison Data</h4>
                  <p className="text-sm text-slate-400 max-w-md">
                    Select a prior snapshot to compare forecasts. This helps track how your cash position evolves week-over-week.
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {/* Step 3: What Changed */}
        {step === 3 && (
          <div className="space-y-8">
            <Card className="rounded-[40px] border-slate-100 shadow-2xl overflow-hidden bg-white">
              <CardHeader className="p-10 border-b border-slate-50">
                <CardTitle className="text-3xl font-black italic tracking-tighter">Variance Narrative.</CardTitle>
                <CardDescription className="font-medium text-slate-500">Automated root-cause analysis for weekly shifts.</CardDescription>
              </CardHeader>
              <CardContent className="p-10">
                {variance && variance.variance_breakdown ? (
                  <div className="space-y-6">
                    {Object.entries(variance.variance_breakdown.causes || {}).map(([key, cause]: [string, any]) => {
                      if (!cause || cause.count === 0) return null;
                      const isPositive = (cause.amount || 0) >= 0;
                      return (
                        <div key={key} className="p-8 rounded-[32px] border-2 border-slate-50 flex items-start gap-6">
                          <div className={`h-12 w-12 ${isPositive ? 'bg-emerald-50' : 'bg-blue-50'} rounded-2xl flex items-center justify-center shrink-0`}>
                            {isPositive ? <CheckCircle2 className="h-6 w-6 text-emerald-600" /> : <RefreshCw className="h-6 w-6 text-blue-600" />}
                          </div>
                          <div className="space-y-2 flex-1">
                            <p className="text-[10px] font-black uppercase tracking-widest text-slate-400">
                              {key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                            </p>
                            <p className="text-lg font-black text-slate-900 italic">
                              {cause.count} items • €{Math.abs(cause.amount || 0).toLocaleString()}
                            </p>
                            <p className="text-sm text-slate-500 font-medium leading-relaxed">
                              {key === 'new_items' && 'New invoices or bills added to the snapshot'}
                              {key === 'timing_shifts' && 'Payment dates moved forward or backward'}
                              {key === 'reconciliation' && 'Bank transactions matched to invoices'}
                              {key === 'policy_changes' && 'Matching policy or payment run day changed'}
                            </p>
                          </div>
                        </div>
                      );
                    })}
                    {Object.keys(variance.variance_breakdown.causes || {}).length === 0 && (
                      <p className="text-slate-500 text-center py-8">No variance detected</p>
                    )}
                  </div>
                ) : (
                  <div className="text-center py-8 text-slate-500">
                    {compareId ? 'Loading variance analysis...' : 'Select a comparison snapshot to view variance'}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        )}

        {/* Step 4: Risks & Drivers */}
        {step === 4 && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            <Card className="rounded-[40px] border-slate-100 shadow-2xl overflow-hidden bg-white">
              <CardHeader className="p-10 border-b border-slate-50">
                <CardTitle className="text-2xl font-black italic tracking-tighter">Top Movers.</CardTitle>
                <CardDescription className="font-medium text-slate-500">Invoices with significant timing shifts.</CardDescription>
              </CardHeader>
              <CardContent className="p-0">
                 <Table>
                    <TableBody>
                       {movers.slice(0, 6).map((m, i) => (
                          <TableRow key={i} className="hover:bg-slate-50/50 transition-all border-none">
                             <TableCell className="pl-10 py-6">
                                <div className="text-sm font-black text-slate-900 truncate max-w-[150px]">{m.customer}</div>
                                <div className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Inv #{m.invoice_number}</div>
                             </TableCell>
                             <TableCell className="text-right pr-10">
                                <div className={`text-sm font-black ${m.shift_days > 0 ? 'text-red-500' : 'text-emerald-500'}`}>
                                   {m.shift_days > 0 ? '+' : ''}{m.shift_days} Days
                                </div>
                                <div className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">€{m.amount.toLocaleString()}</div>
                             </TableCell>
                          </TableRow>
                       ))}
                    </TableBody>
                 </Table>
              </CardContent>
            </Card>
            <Card className="rounded-[40px] border-slate-100 shadow-2xl overflow-hidden bg-white">
              <CardHeader className="p-10 border-b border-slate-50">
                <CardTitle className="text-2xl font-black italic tracking-tighter">Collections Risks.</CardTitle>
                <CardDescription className="font-medium text-slate-500">Highest risk to next 4 weeks liquidity.</CardDescription>
              </CardHeader>
              <CardContent className="p-0">
                 <Table>
                    <TableBody>
                       {priorities.slice(0, 6).map((p, i) => (
                          <TableRow key={i} className="hover:bg-slate-50/50 transition-all border-none">
                             <TableCell className="pl-10 py-6">
                                <div className="text-sm font-black text-slate-900 truncate max-w-[150px]">{p.customer}</div>
                                <div className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Target Week {p.impact_week}</div>
                             </TableCell>
                             <TableCell className="text-right pr-10">
                                <div className="text-sm font-black text-slate-900">€{p.amount.toLocaleString()}</div>
                                <div className="text-[10px] font-bold text-red-400 uppercase tracking-widest">+{p.lateness_risk_days}d Variance</div>
                             </TableCell>
                          </TableRow>
                       ))}
                    </TableBody>
                 </Table>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Step 5: Treasury Actions */}
        {step === 5 && (
          <div className="space-y-8">
             {/* Prior Week Outcomes */}
             {collectionOutcomes && collectionOutcomes.prior_week_outcomes.length > 0 && (
               <Card className="rounded-[40px] border-emerald-100 shadow-xl overflow-hidden bg-emerald-50/30">
                  <CardHeader className="p-8 border-b border-emerald-100">
                     <div className="flex items-center justify-between">
                        <div>
                           <CardTitle className="text-xl font-black italic tracking-tighter text-emerald-900">Last Week's Outcomes.</CardTitle>
                           <CardDescription className="font-medium text-emerald-700">Closed-loop tracking of prior meeting actions.</CardDescription>
                        </div>
                        <div className="flex items-center gap-4">
                           <div className="text-center">
                              <div className="text-2xl font-black text-emerald-600">{collectionOutcomes.performance_metrics.hit_rate}%</div>
                              <div className="text-[9px] font-black text-emerald-500 uppercase tracking-widest">Hit Rate</div>
                           </div>
                           <div className="text-center">
                              <div className="text-2xl font-black text-emerald-600">{collectionOutcomes.performance_metrics.avg_pullforward_achieved}d</div>
                              <div className="text-[9px] font-black text-emerald-500 uppercase tracking-widest">Avg Pullforward</div>
                           </div>
                        </div>
                     </div>
                  </CardHeader>
                  <CardContent className="p-0">
                     <Table>
                        <TableBody>
                           {collectionOutcomes.prior_week_outcomes.map((o, i) => (
                              <TableRow key={i} className="hover:bg-emerald-50/50 transition-all border-emerald-100">
                                 <TableCell className="pl-8 py-4">
                                    <div className="flex items-center gap-3">
                                       <div className={`h-8 w-8 rounded-xl flex items-center justify-center ${
                                          o.action_type === 'called' ? 'bg-blue-100 text-blue-600' :
                                          o.action_type === 'emailed' ? 'bg-purple-100 text-purple-600' :
                                          'bg-red-100 text-red-600'
                                       }`}>
                                          {o.action_type === 'called' ? <Phone className="h-4 w-4" /> : 
                                           o.action_type === 'emailed' ? <Mail className="h-4 w-4" /> :
                                           <ArrowUp className="h-4 w-4" />}
                                       </div>
                                       <div>
                                          <div className="text-sm font-black text-slate-900 capitalize">{o.action_type}</div>
                                          <div className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">
                                             Expected: -{o.expected_pullforward_days}d / €{o.expected_pullforward_amount?.toLocaleString()}
                                          </div>
                                       </div>
                                    </div>
                                 </TableCell>
                                 <TableCell className="text-center">
                                    <span className={`px-3 py-1.5 rounded-full text-[10px] font-black uppercase tracking-widest ${
                                       o.outcome === 'paid' ? 'bg-emerald-100 text-emerald-700' :
                                       o.outcome === 'partial' ? 'bg-amber-100 text-amber-700' :
                                       'bg-red-100 text-red-700'
                                    }`}>
                                       {o.outcome || 'pending'}
                                    </span>
                                 </TableCell>
                                 <TableCell className="pr-8 text-right font-black text-slate-900">
                                    {o.outcome_amount ? `€${o.outcome_amount.toLocaleString()}` : '-'}
                                 </TableCell>
                              </TableRow>
                           ))}
                        </TableBody>
                     </Table>
                  </CardContent>
               </Card>
             )}

             <Card className="rounded-[40px] border-slate-100 shadow-2xl overflow-hidden bg-white">
                <CardHeader className="p-10 border-b border-slate-50 flex flex-row items-center justify-between">
                   <div>
                      <CardTitle className="text-3xl font-black italic tracking-tighter">Decisions & Ownership.</CardTitle>
                      <CardDescription className="font-medium text-slate-500">Treasury loop actions decided during this meeting.</CardDescription>
                   </div>
                   <Button className="bg-slate-900 text-white rounded-2xl px-6 h-12 font-black uppercase text-[10px] tracking-widest">
                      <Plus className="h-4 w-4 mr-2" /> Add Action
                   </Button>
                </CardHeader>
                <CardContent className="p-0">
                   <Table>
                      <TableHeader className="bg-slate-50/50">
                         <TableRow>
                            <TableHead className="pl-10 py-6 font-black uppercase text-[10px] tracking-widest">Action</TableHead>
                            <TableHead className="font-black uppercase text-[10px] tracking-widest text-center">Impact</TableHead>
                            <TableHead className="font-black uppercase text-[10px] tracking-widest text-center">Owner</TableHead>
                            <TableHead className="pr-10 font-black uppercase text-[10px] tracking-widest text-right">Status</TableHead>
                         </TableRow>
                      </TableHeader>
                      <TableBody>
                         {[
                            { type: 'AP Hold', desc: 'Hold Vendor Bill #44512 until W3', impact: '+€84k', owner: 'Sarah L.', status: 'Pending' },
                            { type: 'Collections', desc: 'Accelerate DACH segment priority list', impact: '+€112k', owner: 'Mike R.', status: 'In Progress' },
                            { type: 'Financing', desc: 'Revolver Draw for W4 buffer', impact: '+€500k', owner: 'CFO', status: 'Approved' },
                         ].map((a, i) => (
                            <TableRow key={i} className="hover:bg-slate-50/50 transition-all">
                               <TableCell className="pl-10 py-6">
                                  <div className="text-sm font-black text-slate-900">{a.type}</div>
                                  <div className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">{a.desc}</div>
                               </TableCell>
                               <TableCell className="text-center font-black text-blue-600 italic">{a.impact}</TableCell>
                               <TableCell className="text-center">
                                  <div className="flex items-center justify-center gap-2">
                                     <div className="h-6 w-6 rounded-full bg-slate-100 flex items-center justify-center text-[8px] font-black">{a.owner[0]}</div>
                                     <span className="text-xs font-bold text-slate-700">{a.owner}</span>
                                  </div>
                               </TableCell>
                               <TableCell className="pr-10 text-right">
                                  <span className="px-3 py-1 rounded-full bg-blue-50 text-blue-600 text-[10px] font-black uppercase tracking-widest">{a.status}</span>
                               </TableCell>
                            </TableRow>
                         ))}
                      </TableBody>
                   </Table>
                </CardContent>
             </Card>

             {/* Collection Action Quick Add */}
             <Card className="rounded-[40px] border-blue-100 shadow-xl overflow-hidden bg-blue-50/20">
                <CardHeader className="p-8">
                   <div className="flex items-center gap-3">
                      <Target className="h-6 w-6 text-blue-600" />
                      <div>
                         <CardTitle className="text-lg font-black tracking-tight text-blue-900">Quick Collection Actions</CardTitle>
                         <CardDescription className="font-medium text-blue-600">Log calls, emails, or escalations for priority invoices.</CardDescription>
                      </div>
                   </div>
                </CardHeader>
                <CardContent className="px-8 pb-8">
                   <div className="grid grid-cols-3 gap-4">
                      {[
                         { type: 'called', label: 'Log Call', icon: Phone, color: 'bg-blue-600 hover:bg-blue-700' },
                         { type: 'emailed', label: 'Log Email', icon: Mail, color: 'bg-purple-600 hover:bg-purple-700' },
                         { type: 'escalated', label: 'Escalate', icon: ArrowUp, color: 'bg-red-600 hover:bg-red-700' },
                      ].map((action) => (
                         <Button 
                            key={action.type}
                            className={`${action.color} text-white rounded-2xl h-14 font-black uppercase text-[10px] tracking-widest shadow-lg`}
                            onClick={() => {
                               // In a real implementation, this would open a modal to select invoice and enter details
                               alert(`Create ${action.type} action - would open invoice selector modal`);
                            }}
                         >
                            <action.icon className="h-4 w-4 mr-2" /> {action.label}
                         </Button>
                      ))}
                   </div>
                </CardContent>
             </Card>

             <div className="flex items-center justify-center pt-8">
                <Button 
                   onClick={() => setShowPack(true)}
                   className="bg-blue-600 hover:bg-emerald-600 text-white rounded-[24px] px-12 h-20 font-black uppercase text-sm shadow-2xl shadow-blue-200 transition-all group"
                >
                   <Lock className="h-5 w-5 mr-3 group-hover:rotate-12 transition-all" /> Lock Forecast & Distribute Pack
                </Button>
             </div>
          </div>
        )}
      </div>

      {showPack && (
         <WeeklyCashPack 
            onClose={() => setShowPack(false)}
            data={{
               kpis,
               forecast: comparison,
               movers,
               priorities,
               entityName: entityData?.name || 'Global Entity',
               snapshotDate: new Date().toLocaleDateString()
            }}
         />
      )}

      {/* Navigation Controls */}
      <div className="fixed bottom-10 left-1/2 -translate-x-1/2 flex items-center gap-4 z-50">
        <Button 
          disabled={step === 1}
          onClick={prevStep}
          className="h-16 w-16 rounded-full bg-white border-2 border-slate-100 text-slate-900 shadow-xl hover:bg-slate-50 disabled:opacity-30 transition-all"
        >
          <ChevronLeft className="h-6 w-6" />
        </Button>
        <div className="px-10 py-4 bg-slate-900 rounded-full text-white text-[10px] font-black uppercase tracking-[0.2em] shadow-2xl">
          Agenda Step {step} of {steps.length}: {steps[step-1].title}
        </div>
        <Button 
          disabled={step === steps.length}
          onClick={nextStep}
          className="h-16 w-16 rounded-full bg-white border-2 border-slate-100 text-slate-900 shadow-xl hover:bg-slate-50 disabled:opacity-30 transition-all"
        >
          <ChevronRight className="h-6 w-6" />
        </Button>
      </div>
    </div>
  );
}
