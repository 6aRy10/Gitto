'use client';

import { Clock, Database, RefreshCw } from 'lucide-react';

interface AsOfStampProps {
  asOf?: string;
  snapshotId?: number;
  snapshotName?: string;
  statementPeriod?: { start?: string; end?: string };
  lastSync?: string;
  compact?: boolean;
}

export function AsOfStamp({ 
  asOf, 
  snapshotId, 
  snapshotName,
  statementPeriod, 
  lastSync,
  compact = false 
}: AsOfStampProps) {
  const formatDate = (dateStr?: string) => {
    if (!dateStr) return 'N/A';
    try {
      return new Date(dateStr).toLocaleDateString(undefined, {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
      });
    } catch {
      return dateStr;
    }
  };

  const formatDateTime = (dateStr?: string) => {
    if (!dateStr) return 'N/A';
    try {
      return new Date(dateStr).toLocaleString(undefined, {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return dateStr;
    }
  };

  if (compact) {
    return (
      <div className="flex items-center gap-3 text-[10px] font-bold text-slate-400 uppercase tracking-widest">
        {snapshotId && (
          <div className="flex items-center gap-1.5">
            <Database className="h-3 w-3" />
            <span>Snapshot #{snapshotId}</span>
          </div>
        )}
        {asOf && (
          <div className="flex items-center gap-1.5">
            <Clock className="h-3 w-3" />
            <span>As of {formatDateTime(asOf)}</span>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="flex flex-wrap items-center gap-4 px-4 py-3 bg-slate-50 rounded-2xl border border-slate-100">
      {snapshotId && (
        <div className="flex items-center gap-2">
          <div className="h-6 w-6 bg-slate-200 rounded-lg flex items-center justify-center">
            <Database className="h-3 w-3 text-slate-600" />
          </div>
          <div>
            <div className="text-[9px] font-black text-slate-400 uppercase tracking-widest">Snapshot</div>
            <div className="text-xs font-bold text-slate-700">#{snapshotId}{snapshotName ? ` - ${snapshotName}` : ''}</div>
          </div>
        </div>
      )}
      
      {asOf && (
        <div className="flex items-center gap-2">
          <div className="h-6 w-6 bg-blue-50 rounded-lg flex items-center justify-center">
            <Clock className="h-3 w-3 text-blue-600" />
          </div>
          <div>
            <div className="text-[9px] font-black text-slate-400 uppercase tracking-widest">Data As-Of</div>
            <div className="text-xs font-bold text-slate-700">{formatDateTime(asOf)}</div>
          </div>
        </div>
      )}
      
      {statementPeriod && (statementPeriod.start || statementPeriod.end) && (
        <div className="flex items-center gap-2">
          <div className="h-6 w-6 bg-emerald-50 rounded-lg flex items-center justify-center">
            <Database className="h-3 w-3 text-emerald-600" />
          </div>
          <div>
            <div className="text-[9px] font-black text-slate-400 uppercase tracking-widest">Statement Period</div>
            <div className="text-xs font-bold text-slate-700">
              {formatDate(statementPeriod.start)} - {formatDate(statementPeriod.end)}
            </div>
          </div>
        </div>
      )}
      
      {lastSync && (
        <div className="flex items-center gap-2">
          <div className="h-6 w-6 bg-amber-50 rounded-lg flex items-center justify-center">
            <RefreshCw className="h-3 w-3 text-amber-600" />
          </div>
          <div>
            <div className="text-[9px] font-black text-slate-400 uppercase tracking-widest">Last Sync</div>
            <div className="text-xs font-bold text-slate-700">{formatDateTime(lastSync)}</div>
          </div>
        </div>
      )}
    </div>
  );
}

export default AsOfStamp;

