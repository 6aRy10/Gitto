'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "./ui/table";
import { Button } from "./ui/button";
import { getAuditTrail } from '../lib/api';
import { FileText, RefreshCw, Filter, Calendar } from "lucide-react";

export default function AuditTrailView() {
  const [logs, setLogs] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [filters, setFilters] = useState({
    resource_type: '',
    resource_id: '',
    action: '',
    user: '',
    since: ''
  });

  useEffect(() => {
    loadAuditTrail();
  }, [filters]);

  const loadAuditTrail = async () => {
    setLoading(true);
    try {
      const data = await getAuditTrail({
        resource_type: filters.resource_type || undefined,
        resource_id: filters.resource_id ? Number(filters.resource_id) : undefined,
        action: filters.action || undefined,
        user: filters.user || undefined,
        since: filters.since || undefined
      });
      setLogs(data.logs || []);
    } catch (e: any) {
      console.error("Failed to load audit trail:", e);
      alert(e.response?.data?.detail || "Failed to load audit trail");
    }
    setLoading(false);
  };

  return (
    <div className="space-y-8 mt-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-black tracking-tight text-white">Audit Trail</h2>
          <p className="text-sm text-white/40 font-medium mt-1">
            Complete audit log of all system actions
          </p>
        </div>
        <Button
          onClick={loadAuditTrail}
          disabled={loading}
          className="bg-white text-[#0A0A0F] hover:bg-white/90 rounded-xl h-10 px-6 text-xs font-bold"
        >
          <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      {/* Filters */}
      <Card className="rounded-[32px] border-white/10 bg-white/5 overflow-hidden">
        <CardHeader className="p-6 border-b border-white/10">
          <CardTitle className="text-sm font-black text-white flex items-center gap-2">
            <Filter className="h-4 w-4" />
            Filters
          </CardTitle>
        </CardHeader>
        <CardContent className="p-6">
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            <input
              type="text"
              placeholder="Resource Type"
              value={filters.resource_type}
              onChange={(e) => setFilters({ ...filters, resource_type: e.target.value })}
              className="bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-xs font-bold text-white placeholder-white/30 focus:ring-0 focus:border-white/20"
            />
            <input
              type="text"
              placeholder="Resource ID"
              value={filters.resource_id}
              onChange={(e) => setFilters({ ...filters, resource_id: e.target.value })}
              className="bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-xs font-bold text-white placeholder-white/30 focus:ring-0 focus:border-white/20"
            />
            <input
              type="text"
              placeholder="Action"
              value={filters.action}
              onChange={(e) => setFilters({ ...filters, action: e.target.value })}
              className="bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-xs font-bold text-white placeholder-white/30 focus:ring-0 focus:border-white/20"
            />
            <input
              type="text"
              placeholder="User"
              value={filters.user}
              onChange={(e) => setFilters({ ...filters, user: e.target.value })}
              className="bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-xs font-bold text-white placeholder-white/30 focus:ring-0 focus:border-white/20"
            />
            <input
              type="date"
              value={filters.since}
              onChange={(e) => setFilters({ ...filters, since: e.target.value })}
              className="bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-xs font-bold text-white focus:ring-0 focus:border-white/20"
            />
          </div>
        </CardContent>
      </Card>

      {/* Audit Logs */}
      <Card className="rounded-[32px] border-white/10 bg-white/5 overflow-hidden">
        <CardHeader className="p-8 border-b border-white/10">
          <CardTitle className="text-xl font-black text-white">Audit Logs</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader className="bg-white/5">
              <TableRow className="border-white/10">
                <TableHead className="text-white/60 font-black uppercase text-[10px] tracking-widest">Timestamp</TableHead>
                <TableHead className="text-white/60 font-black uppercase text-[10px] tracking-widest">User</TableHead>
                <TableHead className="text-white/60 font-black uppercase text-[10px] tracking-widest">Action</TableHead>
                <TableHead className="text-white/60 font-black uppercase text-[10px] tracking-widest">Resource</TableHead>
                <TableHead className="text-white/60 font-black uppercase text-[10px] tracking-widest">Details</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {logs.map((log: any, i: number) => (
                <TableRow key={i} className="border-white/10 hover:bg-white/5">
                  <TableCell className="text-white/80 text-xs font-medium">
                    {log.timestamp ? new Date(log.timestamp).toLocaleString() : 'N/A'}
                  </TableCell>
                  <TableCell className="text-white font-medium">{log.user || 'System'}</TableCell>
                  <TableCell>
                    <span className="px-2.5 py-1 rounded-lg bg-blue-500/20 text-blue-300 text-[10px] font-black uppercase border border-blue-500/30">
                      {log.action}
                    </span>
                  </TableCell>
                  <TableCell className="text-white/80 text-xs">
                    {log.resource_type} #{log.resource_id}
                  </TableCell>
                  <TableCell className="text-white/60 text-xs">
                    {log.changes ? JSON.stringify(log.changes).substring(0, 50) + '...' : '-'}
                  </TableCell>
                </TableRow>
              ))}
              {logs.length === 0 && !loading && (
                <TableRow>
                  <TableCell colSpan={5} className="text-center py-12 text-white/40">
                    No audit logs found
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}


