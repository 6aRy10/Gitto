'use client';

import { CheckCircle2, CircleDot, BrainCircuit, HelpCircle, Banknote } from 'lucide-react';

export type TruthLevel = 'bank-true' | 'reconciled' | 'modeled' | 'unknown';

interface TruthBadgeProps {
  level: TruthLevel;
  compact?: boolean;
  showLabel?: boolean;
  dark?: boolean;
}

const TRUTH_CONFIG: Record<TruthLevel, {
  label: string;
  icon: typeof CheckCircle2;
  bgClass: string;
  bgClassDark: string;
  textClass: string;
  textClassDark: string;
  description: string;
}> = {
  'bank-true': {
    label: 'Bank-True',
    icon: Banknote,
    bgClass: 'bg-emerald-50 border-emerald-200',
    bgClassDark: 'bg-emerald-500/20 border-emerald-500/30',
    textClass: 'text-emerald-700',
    textClassDark: 'text-emerald-400',
    description: 'Confirmed by bank statement'
  },
  'reconciled': {
    label: 'Reconciled',
    icon: CheckCircle2,
    bgClass: 'bg-blue-50 border-blue-200',
    bgClassDark: 'bg-blue-500/20 border-blue-500/30',
    textClass: 'text-blue-700',
    textClassDark: 'text-blue-400',
    description: 'Matched to bank transaction'
  },
  'modeled': {
    label: 'Modeled',
    icon: BrainCircuit,
    bgClass: 'bg-amber-50 border-amber-200',
    bgClassDark: 'bg-amber-500/20 border-amber-500/30',
    textClass: 'text-amber-700',
    textClassDark: 'text-amber-400',
    description: 'Forecasted based on historical patterns'
  },
  'unknown': {
    label: 'Unknown',
    icon: HelpCircle,
    bgClass: 'bg-slate-100 border-slate-300',
    bgClassDark: 'bg-zinc-500/20 border-zinc-500/30',
    textClass: 'text-slate-600',
    textClassDark: 'text-zinc-400',
    description: 'Missing data or unprocessed'
  }
};

export function TruthBadge({ level, compact = false, showLabel = true, dark = false }: TruthBadgeProps) {
  const config = TRUTH_CONFIG[level];
  const Icon = config.icon;
  const bgClass = dark ? config.bgClassDark : config.bgClass;
  const textClass = dark ? config.textClassDark : config.textClass;

  if (compact) {
    return (
      <span 
        className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md border ${bgClass} ${textClass}`}
        title={config.description}
      >
        <Icon className="h-3 w-3" />
        {showLabel && <span className="text-[9px] font-black uppercase tracking-wider">{config.label}</span>}
      </span>
    );
  }

  return (
    <div 
      className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-xl border ${bgClass}`}
      title={config.description}
    >
      <Icon className={`h-4 w-4 ${textClass}`} />
      {showLabel && (
        <span className={`text-xs font-bold ${textClass}`}>
          {config.label}
        </span>
      )}
    </div>
  );
}

export function TruthBadgeLegend({ dark = false }: { dark?: boolean }) {
  return (
    <div className={`flex flex-wrap items-center gap-3 p-3 rounded-xl border ${
      dark ? "bg-zinc-800/50 border-zinc-700" : "bg-slate-50 border-slate-100"
    }`}>
      <span className={`text-[10px] font-black uppercase tracking-widest ${
        dark ? "text-zinc-500" : "text-slate-400"
      }`}>Data Sources:</span>
      {(['bank-true', 'reconciled', 'modeled', 'unknown'] as TruthLevel[]).map((level) => (
        <TruthBadge key={level} level={level} compact dark={dark} />
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




