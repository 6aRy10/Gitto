'use client';

import { CheckCircle2, CircleDot, BrainCircuit, HelpCircle, Banknote } from 'lucide-react';

export type TruthLevel = 'bank-true' | 'reconciled' | 'modeled' | 'unknown';

interface TruthBadgeProps {
  level: TruthLevel;
  compact?: boolean;
  showLabel?: boolean;
}

const TRUTH_CONFIG: Record<TruthLevel, {
  label: string;
  icon: typeof CheckCircle2;
  bgClass: string;
  textClass: string;
  description: string;
}> = {
  'bank-true': {
    label: 'Bank-True',
    icon: Banknote,
    bgClass: 'bg-emerald-50 border-emerald-200',
    textClass: 'text-emerald-700',
    description: 'Confirmed by bank statement'
  },
  'reconciled': {
    label: 'Reconciled',
    icon: CheckCircle2,
    bgClass: 'bg-blue-50 border-blue-200',
    textClass: 'text-blue-700',
    description: 'Matched to bank transaction'
  },
  'modeled': {
    label: 'Modeled',
    icon: BrainCircuit,
    bgClass: 'bg-amber-50 border-amber-200',
    textClass: 'text-amber-700',
    description: 'Forecasted based on historical patterns'
  },
  'unknown': {
    label: 'Unknown',
    icon: HelpCircle,
    bgClass: 'bg-slate-100 border-slate-300',
    textClass: 'text-slate-600',
    description: 'Missing data or unprocessed'
  }
};

export function TruthBadge({ level, compact = false, showLabel = true }: TruthBadgeProps) {
  const config = TRUTH_CONFIG[level];
  const Icon = config.icon;

  if (compact) {
    return (
      <span 
        className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md border ${config.bgClass} ${config.textClass}`}
        title={config.description}
      >
        <Icon className="h-3 w-3" />
        {showLabel && <span className="text-[9px] font-black uppercase tracking-wider">{config.label}</span>}
      </span>
    );
  }

  return (
    <div 
      className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-xl border ${config.bgClass}`}
      title={config.description}
    >
      <Icon className={`h-4 w-4 ${config.textClass}`} />
      {showLabel && (
        <span className={`text-xs font-bold ${config.textClass}`}>
          {config.label}
        </span>
      )}
    </div>
  );
}

export function TruthBadgeLegend() {
  return (
    <div className="flex flex-wrap items-center gap-3 p-3 bg-slate-50 rounded-xl border border-slate-100">
      <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Data Sources:</span>
      {(['bank-true', 'reconciled', 'modeled', 'unknown'] as TruthLevel[]).map((level) => (
        <TruthBadge key={level} level={level} compact />
      ))}
    </div>
  );
}

export function getTruthLevelFromSource(source: string | null | undefined): TruthLevel {
  if (!source) return 'unknown';
  
  const s = source.toLowerCase();
  if (s.includes('bank') || s === 'bank-true') return 'bank-true';
  if (s.includes('reconciled') || s.includes('matched')) return 'reconciled';
  if (s.includes('model') || s.includes('forecast') || s.includes('predicted')) return 'modeled';
  return 'unknown';
}




