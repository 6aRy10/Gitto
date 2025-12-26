'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "./ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "./ui/table";
import { Input } from "./ui/input";
import { Button } from "./ui/button";
import { Slider } from "./ui/slider";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "./ui/tabs";
import SnowflakeConfigView from './SnowflakeConfigView';
import { api } from '../lib/api';
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  LineChart, Line,
} from 'recharts';

export default function FPAView({ snapshotId }: { snapshotId: number }) {
  const [segments, setSegments] = useState<any[]>([]);
  const [invoices, setInvoices] = useState<any[]>([]);
  const [totalInvoices, setTotalInvoices] = useState<number>(0);
  const [invoicePage, setInvoicePage] = useState<number>(0);
  const [invoiceLimit] = useState<number>(100);
  const [stats, setStats] = useState<any>(null);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [allCountries, setAllCountries] = useState<string[]>([]);
  const [availableCustomers, setAvailableCustomers] = useState<string[]>([]);
  const [availableProjects, setAvailableProjects] = useState<string[]>([]);
  
  const [countryFilter, setCountryFilter] = useState<string>('');
  const [customerFilter, setCustomerFilter] = useState<string>('');
  const [projectFilter, setProjectFilter] = useState<string>('');
  const [scenarioConfig, setScenarioConfig] = useState({
    global_shock: 0,
    collections_improvement: 0
  });
  const [scenarioForecast, setScenarioForecast] = useState<any[]>([]);

  useEffect(() => {
    if (snapshotId) {
      loadData();
    }
  }, [snapshotId]);

  const loadData = async (resetPage = false) => {
    if (isLoadingMore && !resetPage) return;
    if (!resetPage) setIsLoadingMore(true);

    const currentPage = resetPage ? 0 : invoicePage;
    if (resetPage) setInvoicePage(0);

    const params = new URLSearchParams();
    if (countryFilter) params.append('country', countryFilter);
    if (customerFilter) params.append('customer', customerFilter);
    if (projectFilter) params.append('project', projectFilter);
    params.append('only_open', 'true');
    
    // Add pagination
    params.append('skip', (currentPage * invoiceLimit).toString());
    params.append('limit', invoiceLimit.toString());

    try {
      const [segData, invRes, filterData, statData] = await Promise.all([
        api.get(`/snapshots/${snapshotId}/segments`).then(res => res.data),
        api.get(`/snapshots/${snapshotId}/invoices?${params.toString()}`).then(res => res.data),
        api.get(`/snapshots/${snapshotId}/filters?${params.toString()}`).then(res => res.data),
        api.get(`/snapshots/${snapshotId}/stats?${params.toString()}`).then(res => res.data)
      ]);
      
      setSegments(segData);
      
      if (resetPage) {
        setInvoices(invRes.items);
      } else {
        setInvoices(prev => [...prev, ...invRes.items]);
      }
      
      setTotalInvoices(invRes.total);
      setStats(statData);
      
      setAllCountries(filterData.countries);
      setAvailableCustomers(filterData.customers);
      setAvailableProjects(filterData.projects);
    } finally {
      setIsLoadingMore(false);
    }
  };

  useEffect(() => {
    if (snapshotId) {
      loadData(true); // Initial load or filter change
    }
  }, [snapshotId, countryFilter, customerFilter, projectFilter]);

  // Handle manual "Load More" click
  const handleLoadMore = () => {
    if ((invoicePage + 1) * invoiceLimit < totalInvoices) {
      setInvoicePage(prev => prev + 1);
    }
  };

  // Only trigger loadData when invoicePage changes AND it's not the first page
  useEffect(() => {
    if (snapshotId && invoicePage > 0) {
      loadData(false);
    }
  }, [invoicePage]);

  const runScenario = async () => {
    const res = await api.post(`/snapshots/${snapshotId}/scenario`, scenarioConfig);
    setScenarioForecast(res.data);
  };

  const countries = allCountries;
  const customers = availableCustomers;
  const projects = availableProjects;

  const cashFlowByYear = stats?.cash_flow_by_year || [];
  const overdueChartData = stats?.overdue_chart_data || [];

  return (
    <div className="space-y-8 mt-6">
      <Tabs defaultValue="scenario" className="w-full">
        <TabsList className="mb-4">
          <TabsTrigger value="scenario">Scenario Modeling</TabsTrigger>
          <TabsTrigger value="datasource">Data Sources (Snowflake/ERP)</TabsTrigger>
        </TabsList>

        <TabsContent value="scenario" className="space-y-8">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Scenario Controls */}
            <Card className="md:col-span-1">
              <CardHeader>
                <CardTitle>Scenario Knobs</CardTitle>
                <CardDescription>Adjust variables to see impact</CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="space-y-4">
                  <label className="text-sm font-medium">Global Delay Shock (Days: {scenarioConfig.global_shock})</label>
                  <Slider 
                    min={-30} max={60} step={1}
                    value={[scenarioConfig.global_shock]}
                    onValueChange={(val) => setScenarioConfig({...scenarioConfig, global_shock: val[0]})}
                  />
                </div>
                <div className="space-y-4">
                  <label className="text-sm font-medium">Collections Improvement (Days: {scenarioConfig.collections_improvement})</label>
                  <Slider 
                    min={0} max={30} step={1}
                    value={[scenarioConfig.collections_improvement]}
                    onValueChange={(val) => setScenarioConfig({...scenarioConfig, collections_improvement: val[0]})}
                  />
                </div>
                <Button className="w-full" onClick={runScenario}>Run Scenario</Button>
              </CardContent>
            </Card>

            {/* Scenario Results */}
            <Card className="md:col-span-2 bg-white border border-slate-200 shadow-lg">
              <CardHeader>
                <CardTitle>Scenario Impact</CardTitle>
                <CardDescription>Comparison against base forecast</CardDescription>
              </CardHeader>
              <CardContent className="h-[320px]">
                {scenarioForecast.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={scenarioForecast} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                      <defs>
                        <linearGradient id="scenarioGradient" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.85}/>
                          <stop offset="95%" stopColor="#60a5fa" stopOpacity={0.15}/>
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e5e7eb" />
                      <XAxis dataKey="label" tick={{ fill: '#6b7280', fontSize: 12 }} />
                      <YAxis tick={{ fill: '#6b7280', fontSize: 12 }} />
                      <Tooltip
                        contentStyle={{ borderRadius: 12, borderColor: '#e5e7eb', boxShadow: '0 8px 24px rgba(15,23,42,0.08)' }}
                        formatter={(value: any) => `€${Number(value || 0).toLocaleString()}`}
                      />
                      <Legend />
                      <Bar dataKey="base" name="Scenario Cash" fill="url(#scenarioGradient)" radius={[8, 8, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="flex items-center justify-center h-full text-slate-400">
                    Adjust knobs and click "Run Scenario" to see impact
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          <Card className="bg-white border border-slate-200 shadow-lg">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <div>
                <CardTitle>Filters</CardTitle>
                <CardDescription>Slice by country, customer, and project</CardDescription>
              </div>
              {(countryFilter || customerFilter || projectFilter) && (
                <Button 
                  variant="ghost" 
                  size="sm" 
                  onClick={() => {
                    setCountryFilter('');
                    setCustomerFilter('');
                    setProjectFilter('');
                  }}
                  className="text-xs text-slate-500 hover:text-blue-600"
                >
                  Clear Filters
                </Button>
              )}
            </CardHeader>
            <CardContent className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="space-y-2">
                <label className="text-sm font-medium text-slate-700">Country</label>
                <select
                  className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm"
                  value={countryFilter}
                  onChange={(e) => {
                    setCountryFilter(e.target.value);
                    setCustomerFilter(''); // Reset children
                    setProjectFilter('');
                  }}
                >
                  <option value="">All Countries</option>
                  {countries.map((c) => (
                    <option key={c} value={c}>{c}</option>
                  ))}
                </select>
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium text-slate-700">Customer</label>
                <select
                  className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm"
                  value={customerFilter}
                  onChange={(e) => {
                    setCustomerFilter(e.target.value);
                    setProjectFilter(''); // Reset child
                  }}
                >
                  <option value="">All Customers</option>
                  {customers.map((c) => (
                    <option key={c} value={c}>{c}</option>
                  ))}
                </select>
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium text-slate-700">Project</label>
                <select
                  className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm"
                  value={projectFilter}
                  onChange={(e) => {
                    setProjectFilter(e.target.value);
                  }}
                >
                  <option value="">All Projects</option>
                  {projects.map((p) => (
                    <option key={p} value={p}>{p}</option>
                  ))}
                </select>
              </div>
            </CardContent>
          </Card>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card className="bg-white border border-slate-200 shadow-lg">
              <CardHeader>
                <CardTitle>Cash Flow per Year</CardTitle>
                <CardDescription>Predicted cash by year (filtered)</CardDescription>
              </CardHeader>
              <CardContent className="h-[300px]">
                {cashFlowByYear.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={cashFlowByYear} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e5e7eb" />
                      <XAxis dataKey="year" tick={{ fill: '#6b7280', fontSize: 12 }} />
                      <YAxis tick={{ fill: '#6b7280', fontSize: 12 }} />
                      <Tooltip
                        contentStyle={{ borderRadius: 12, borderColor: '#e5e7eb', boxShadow: '0 8px 24px rgba(15,23,42,0.08)' }}
                        formatter={(value: any) => `€${Number(value || 0).toLocaleString()}`}
                      />
                      <Legend />
                      <Line
                        type="monotone"
                        dataKey="cash"
                        name="Cash Flow"
                        stroke="#10B981"
                        strokeWidth={3}
                        dot={{ r: 4, strokeWidth: 0, fill: '#10B981' }}
                        activeDot={{ r: 6 }}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="flex items-center justify-center h-full text-slate-400">
                    No data for selected filters.
                  </div>
                )}
              </CardContent>
            </Card>

            <Card className="bg-white border border-slate-200 shadow-lg">
              <CardHeader>
                <CardTitle>Overdue Unpaid</CardTitle>
                <CardDescription>Open invoices past due (filtered)</CardDescription>
              </CardHeader>
              <CardContent className="h-[300px]">
                {overdueChartData.some((d: any) => d.amount > 0) ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={overdueChartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e5e7eb" />
                      <XAxis dataKey="label" tick={{ fill: '#6b7280', fontSize: 12 }} />
                      <YAxis tick={{ fill: '#6b7280', fontSize: 12 }} />
                      <Tooltip
                        contentStyle={{ borderRadius: 12, borderColor: '#e5e7eb', boxShadow: '0 8px 24px rgba(15,23,42,0.08)' }}
                        formatter={(value: any) => `€${Number(value || 0).toLocaleString()}`}
                      />
                      <Legend />
                      <Bar dataKey="amount" name="Overdue €" fill="#3B82F6" radius={[8,8,0,0]} />
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="flex items-center justify-center h-full text-slate-400">
                    No overdue invoices for selected filters.
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

      {/* Model Explainability */}
      <Card>
        <CardHeader>
          <CardTitle>Model Explainability</CardTitle>
          <CardDescription>Delay distributions by segment (Hierarchy fallbacks)</CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Segment Type</TableHead>
                <TableHead>Key</TableHead>
                <TableHead>Count</TableHead>
                <TableHead>P25</TableHead>
                <TableHead>Median (P50)</TableHead>
                <TableHead>P75</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {segments.slice(0, 10).map((seg, i) => (
                <TableRow key={i}>
                  <TableCell className="font-medium">{seg.segment_type}</TableCell>
                  <TableCell className="max-w-[200px] truncate">{seg.segment_key}</TableCell>
                  <TableCell>{seg.count}</TableCell>
                  <TableCell>{seg.p25_delay}d</TableCell>
                  <TableCell className="font-bold">{seg.median_delay}d</TableCell>
                  <TableCell>{seg.p75_delay}d</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0">
              <div>
                <CardTitle>Invoice Drill-down</CardTitle>
                <CardDescription>
                  Showing {invoices.length} of {totalInvoices} open invoices
                </CardDescription>
              </div>
            </CardHeader>
            <CardContent className="space-y-6">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Invoice #</TableHead>
                    <TableHead>Customer</TableHead>
                    <TableHead>Amount</TableHead>
                    <TableHead>Due Date</TableHead>
                    <TableHead>Predicted Date</TableHead>
                    <TableHead>Segment Used</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {invoices.map((inv, i) => (
                    <TableRow key={i}>
                      <TableCell className="font-mono text-[10px]">{inv.document_number}</TableCell>
                      <TableCell className="text-xs font-bold">{inv.customer}</TableCell>
                      <TableCell className="text-xs font-black">€{inv.amount.toLocaleString()}</TableCell>
                      <TableCell className="text-[10px] text-slate-500">{new Date(inv.expected_due_date).toLocaleDateString()}</TableCell>
                      <TableCell className="text-xs font-black text-blue-600">
                        {new Date(inv.predicted_payment_date).toLocaleDateString()}
                      </TableCell>
                      <TableCell className="text-[9px] text-slate-400 uppercase tracking-widest">{inv.prediction_segment}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              
              {invoices.length < totalInvoices && (
                <div className="flex justify-center pt-4">
                  <Button 
                    variant="outline" 
                    className="px-12 py-6 rounded-2xl border-2 border-slate-100 font-bold hover:bg-slate-50 transition-all"
                    onClick={handleLoadMore}
                    disabled={isLoadingMore}
                  >
                    {isLoadingMore ? "Retrieving more..." : `Load next 100 (${totalInvoices - invoices.length} remaining)`}
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="datasource">
          <SnowflakeConfigView />
        </TabsContent>
      </Tabs>
    </div>
  );
}

