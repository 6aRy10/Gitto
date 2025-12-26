'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "./ui/card";
import { Input } from "./ui/input";
import { Button } from "./ui/button";
import { api } from '../lib/api';
import { AlertCircle, CheckCircle2, Database, RefreshCw, Box, Layers, Globe, ShieldCheck } from "lucide-react";

export default function SnowflakeConfigView() {
  const [activeConnector, setActiveConnector] = useState<'snowflake' | 'netsuite' | 'sap'>('snowflake');
  const [config, setConfig] = useState<any>({
    account: '',
    user: '',
    password: '',
    warehouse: '',
    database: '',
    schema_name: '',
    role: '',
    invoice_mapping: {
      table: 'INVOICES',
      mapping: {
        document_number: 'INV_ID',
        customer: 'CUST_NAME',
        amount: 'AMOUNT',
        expected_due_date: 'DUE_DATE',
        payment_date: 'PAID_DATE',
        invoice_issue_date: 'INV_DATE',
        country: 'COUNTRY',
        terms_of_payment: 'TERMS'
      }
    }
  });
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<{ type: 'success' | 'error', message: string } | null>(null);

  useEffect(() => {
    loadConfig();
  }, []);

  const loadConfig = async () => {
    try {
      const res = await api.get('/snowflake/config');
      if (res.data && res.data.account) {
        setConfig(res.data);
      }
    } catch (e) {
      console.error("No existing Snowflake config found");
    }
  };

  const handleSave = async () => {
    setLoading(true);
    try {
      await api.post('/snowflake/config', config);
      setStatus({ type: 'success', message: 'Configuration saved successfully.' });
    } catch (e) {
      setStatus({ type: 'error', message: 'Failed to save configuration.' });
    }
    setLoading(false);
  };

  const handleTest = async () => {
    setLoading(true);
    try {
      const res = await api.post('/snowflake/test', config);
      if (res.data.status === 'success') {
        setStatus({ type: 'success', message: 'Connection successful!' });
      } else {
        setStatus({ type: 'error', message: `Connection failed: ${res.data.message}` });
      }
    } catch (e) {
      setStatus({ type: 'error', message: 'Test failed due to network error.' });
    }
    setLoading(false);
  };

  const handleSync = async () => {
    setLoading(true);
    try {
      const res = await api.post('/snowflake/sync');
      setStatus({ type: 'success', message: `Sync complete. New snapshot ID: ${res.data.snapshot_id}` });
    } catch (e) {
      setStatus({ type: 'error', message: 'Sync failed.' });
    }
    setLoading(false);
  };

  const updateMapping = (field: string, value: string) => {
    setConfig({
      ...config,
      invoice_mapping: {
        ...config.invoice_mapping,
        mapping: {
          ...config.invoice_mapping.mapping,
          [field]: value
        }
      }
    });
  };

  return (
    <div className="space-y-8">
      <div className="grid grid-cols-3 gap-4">
        {[
          { id: 'snowflake', label: 'Snowflake', icon: Database, description: 'Direct Warehouse Sync' },
          { id: 'netsuite', label: 'NetSuite', icon: Box, description: 'ERP API Integration' },
          { id: 'sap', label: 'SAP S/4HANA', icon: Layers, description: 'OData Service Sync' },
        ].map((conn) => (
          <button
            key={conn.id}
            onClick={() => setActiveConnector(conn.id as any)}
            className={`p-6 rounded-[32px] border-2 text-left transition-all ${
              activeConnector === conn.id 
                ? 'border-blue-600 bg-blue-50/30' 
                : 'border-[#E5E5E7] bg-white hover:border-slate-300'
            }`}
          >
            <conn.icon className={`h-6 w-6 mb-4 ${activeConnector === conn.id ? 'text-blue-600' : 'text-slate-400'}`} />
            <div className="text-sm font-black text-[#1A1A1A] tracking-tight">{conn.label}</div>
            <div className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mt-1">{conn.description}</div>
          </button>
        ))}
      </div>

      {activeConnector === 'snowflake' ? (
        <Card className="rounded-[40px] border-[#E5E5E7] shadow-xl overflow-hidden animate-in fade-in slide-in-from-bottom-4 duration-500">
          <CardHeader className="p-10 border-b border-slate-50">
            <div className="flex items-center gap-3">
              <Database className="h-6 w-6 text-blue-600" />
              <div>
                <CardTitle className="text-2xl font-black tracking-tight">Snowflake Enterprise Gateway</CardTitle>
                <CardDescription className="text-slate-500 font-medium">Connect Gitto to your data warehouse for high-scale, behavior-based forecasting.</CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent className="p-10 space-y-10">
            <div className="grid grid-cols-2 gap-8">
              {[
                { label: 'Account', field: 'account', placeholder: 'xy12345.us-east-1' },
                { label: 'User', field: 'user', placeholder: 'FINANCE_APP' },
                { label: 'Password', field: 'password', placeholder: '••••••••', type: 'password' },
                { label: 'Role', field: 'role', placeholder: 'ACCOUNTADMIN' },
                { label: 'Warehouse', field: 'warehouse', placeholder: 'COMPUTE_WH' },
                { label: 'Database', field: 'database', placeholder: 'FINANCE_DB' },
                { label: 'Schema', field: 'schema_name', placeholder: 'PUBLIC' },
              ].map((item) => (
                <div key={item.field} className="space-y-3">
                  <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest">{item.label}</label>
                  <Input 
                    type={item.type || 'text'}
                    placeholder={item.placeholder} 
                    value={config[item.field]} 
                    onChange={(e) => setConfig({...config, [item.field]: e.target.value})}
                    className="h-12 rounded-xl bg-slate-50 border-transparent focus:bg-white focus:ring-blue-600 focus:border-blue-600 transition-all text-sm font-bold"
                  />
                </div>
              ))}
            </div>

            <div className="pt-10 border-t border-slate-50">
              <div className="flex items-center justify-between mb-8">
                <div>
                  <h3 className="text-lg font-black tracking-tight text-[#1A1A1A]">Unified Schema Mapper</h3>
                  <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mt-1">Map source table (INVOICES) to Gitto AI Engine</p>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-x-12 gap-y-6">
                {Object.keys(config.invoice_mapping.mapping).map((field) => (
                  <div key={field} className="flex items-center justify-between gap-6 group">
                    <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest group-hover:text-blue-600 transition-colors w-32">{field}</span>
                    <Input 
                      className="h-10 text-xs font-mono rounded-lg bg-slate-50 border-transparent focus:bg-white" 
                      value={config.invoice_mapping.mapping[field]} 
                      onChange={(e) => updateMapping(field, e.target.value)}
                    />
                  </div>
                ))}
              </div>
            </div>

            {status && (
              <div className={`p-6 rounded-2xl flex items-center gap-4 animate-in zoom-in-95 duration-200 ${status.type === 'success' ? 'bg-emerald-50 text-emerald-800' : 'bg-red-50 text-red-800'}`}>
                {status.type === 'success' ? <CheckCircle2 className="h-5 w-5" /> : <AlertCircle className="h-5 w-5" />}
                <span className="text-sm font-bold">{status.message}</span>
              </div>
            )}

            <div className="flex items-center gap-4 pt-6">
              <Button variant="ghost" onClick={handleTest} disabled={loading} className="rounded-xl h-12 px-8 text-xs font-black uppercase tracking-widest text-slate-500 hover:text-blue-600">
                Test Connectivity
              </Button>
              <Button onClick={handleSave} disabled={loading} className="bg-slate-100 text-slate-900 hover:bg-slate-200 rounded-xl h-12 px-8 text-xs font-black uppercase tracking-widest shadow-sm">
                Save Profile
              </Button>
              <div className="flex-1" />
              <Button variant="secondary" className="bg-[#1A1A1A] text-white hover:bg-slate-800 rounded-2xl h-12 px-10 text-xs font-black uppercase tracking-widest shadow-xl shadow-slate-200" onClick={handleSync} disabled={loading}>
                <RefreshCw className={`mr-3 h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
                Initiate Live Sync
              </Button>
            </div>
          </CardContent>
        </Card>
      ) : (
        <Card className="rounded-[40px] border-dashed border-2 border-slate-200 bg-slate-50/50 p-20 text-center animate-in fade-in duration-500">
          <div className="max-w-md mx-auto space-y-6">
            <Globe className="h-12 w-12 text-slate-300 mx-auto" />
            <div>
              <h3 className="text-2xl font-black tracking-tight text-slate-400">Enterprise {activeConnector === 'sap' ? 'SAP' : 'NetSuite'} Bridge</h3>
              <p className="text-sm font-medium text-slate-400 mt-2">Activate this connector to enable seamless API-driven cash forecasting for your enterprise stack.</p>
            </div>
            <Button disabled className="bg-slate-200 text-white rounded-2xl h-12 px-10 text-xs font-black uppercase tracking-widest">
              Available in Enterprise Tier
            </Button>
          </div>
        </Card>
      )}
      
      <div className="bg-[#F8F9FA] p-8 rounded-[32px] border border-[#E5E5E7] flex items-start gap-6">
        <div className="w-12 h-12 bg-white rounded-2xl flex items-center justify-center shadow-sm shrink-0">
          <ShieldCheck className="h-6 w-6 text-blue-600" />
        </div>
        <div className="space-y-2">
          <h4 className="text-sm font-black text-[#1A1A1A] tracking-tight uppercase tracking-[0.1em]">Security & Governance</h4>
          <p className="text-xs text-slate-500 leading-relaxed font-medium">
            Gitto uses read-only credentials and encrypted storage for all connector profiles. 
            All data ingestion is performed via standard SDKs (like <code className="text-blue-600 font-bold">snowflake-connector-python</code>) 
            ensuring SOX-compliant data handling.
          </p>
        </div>
      </div>
    </div>
  );
}

