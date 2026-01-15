'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "./ui/card";
import { Button } from "./ui/button";
import { getMatchingPolicy, setMatchingPolicy } from '../lib/api';
import { Settings, Save, RefreshCw, CheckCircle2 } from "lucide-react";

export default function MatchingPolicyView({ entityId }: { entityId: number }) {
  const [policy, setPolicy] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [currency, setCurrency] = useState<string>('');
  const [formData, setFormData] = useState({
    amount_tolerance: 0.01,
    date_window_days: 7,
    tier_enabled: {
      deterministic: true,
      rules: true,
      suggested: true,
      manual: true
    }
  });

  useEffect(() => {
    if (entityId) {
      loadPolicy();
    }
  }, [entityId, currency]);

  const loadPolicy = async () => {
    setLoading(true);
    try {
      const data = await getMatchingPolicy(entityId, currency || undefined);
      setPolicy(data);
      if (data) {
        setFormData({
          amount_tolerance: data.amount_tolerance || 0.01,
          date_window_days: data.date_window_days || 7,
          tier_enabled: data.tier_enabled || {
            deterministic: true,
            rules: true,
            suggested: true,
            manual: true
          }
        });
      }
    } catch (e: any) {
      console.error("Failed to load matching policy:", e);
      alert(e.response?.data?.detail || "Failed to load matching policy");
    }
    setLoading(false);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await setMatchingPolicy(entityId, {
        currency: currency || undefined,
        ...formData
      });
      await loadPolicy();
      alert("Policy saved successfully!");
    } catch (e: any) {
      alert(e.response?.data?.detail || "Failed to save policy");
    }
    setSaving(false);
  };

  return (
    <div className="space-y-8 mt-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-black tracking-tight text-white">Matching Policy</h2>
          <p className="text-sm text-white/40 font-medium mt-1">
            Configure matching rules per entity and currency
          </p>
        </div>
        <div className="flex items-center gap-4">
          <input
            type="text"
            value={currency}
            onChange={(e) => setCurrency(e.target.value)}
            placeholder="Currency (optional)"
            className="bg-white/5 border border-white/10 rounded-lg px-3 py-1.5 text-sm font-bold text-white placeholder-white/30 focus:ring-0 focus:border-white/20 w-32"
          />
          <Button
            onClick={loadPolicy}
            disabled={loading}
            className="bg-white/10 text-white hover:bg-white/20 rounded-xl h-10 px-6 text-xs font-bold"
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Load
          </Button>
        </div>
      </div>

      <Card className="rounded-[32px] border-white/10 bg-white/5 overflow-hidden">
        <CardHeader className="p-8 border-b border-white/10">
          <CardTitle className="text-xl font-black text-white flex items-center gap-2">
            <Settings className="h-5 w-5" />
            Policy Configuration
          </CardTitle>
          <CardDescription className="text-white/40">
            {currency ? `Policy for ${currency}` : 'Default policy for entity'}
          </CardDescription>
        </CardHeader>
        <CardContent className="p-8 space-y-6">
          {/* Amount Tolerance */}
          <div>
            <label className="text-sm font-black text-white uppercase tracking-widest mb-2 block">
              Amount Tolerance
            </label>
            <input
              type="number"
              step="0.01"
              value={formData.amount_tolerance}
              onChange={(e) => setFormData({ ...formData, amount_tolerance: Number(e.target.value) })}
              className="bg-white/5 border border-white/10 rounded-lg px-4 py-2 text-sm font-bold text-white focus:ring-0 focus:border-white/20 w-full"
            />
            <p className="text-xs text-white/40 font-medium mt-1">
              Maximum difference in amounts for matching (as decimal, e.g., 0.01 = 1%)
            </p>
          </div>

          {/* Date Window */}
          <div>
            <label className="text-sm font-black text-white uppercase tracking-widest mb-2 block">
              Date Window (Days)
            </label>
            <input
              type="number"
              value={formData.date_window_days}
              onChange={(e) => setFormData({ ...formData, date_window_days: Number(e.target.value) })}
              className="bg-white/5 border border-white/10 rounded-lg px-4 py-2 text-sm font-bold text-white focus:ring-0 focus:border-white/20 w-full"
            />
            <p className="text-xs text-white/40 font-medium mt-1">
              Maximum days difference between transaction and invoice dates
            </p>
          </div>

          {/* Tier Enablement */}
          <div>
            <label className="text-sm font-black text-white uppercase tracking-widest mb-4 block">
              Match Tier Enablement
            </label>
            <div className="space-y-3">
              {Object.entries(formData.tier_enabled).map(([tier, enabled]) => (
                <div key={tier} className="flex items-center justify-between p-4 rounded-xl border border-white/10 bg-white/5">
                  <div>
                    <div className="text-sm font-bold text-white capitalize">
                      {tier.replace(/_/g, ' ')}
                    </div>
                    <div className="text-xs text-white/40 font-medium">
                      {tier === 'deterministic' && 'Exact matches (amount + date + reference)'}
                      {tier === 'rules' && 'Rule-based matches (fuzzy logic)'}
                      {tier === 'suggested' && 'AI-suggested matches (requires approval)'}
                      {tier === 'manual' && 'Manual matching only'}
                    </div>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={enabled}
                      onChange={(e) => setFormData({
                        ...formData,
                        tier_enabled: { ...formData.tier_enabled, [tier]: e.target.checked }
                      })}
                      className="sr-only peer"
                    />
                    <div className="w-11 h-6 bg-white/10 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-emerald-500"></div>
                  </label>
                </div>
              ))}
            </div>
          </div>

          <Button
            onClick={handleSave}
            disabled={saving}
            className="w-full bg-white text-[#0A0A0F] hover:bg-white/90 rounded-xl h-12 text-sm font-black"
          >
            <Save className="h-4 w-4 mr-2" />
            {saving ? 'Saving...' : 'Save Policy'}
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}


