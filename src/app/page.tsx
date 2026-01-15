'use client';

import { useState, useEffect } from 'react';
import Link from "next/link";
import { Button } from "../components/ui/button";

// ═══════════════════════════════════════════════════════════════════════════════
// CUSTOM FINANCE ICONS - Clean, Technical, Non-AI-Slop
// ═══════════════════════════════════════════════════════════════════════════════

const BankStatementIcon = ({ className = "w-5 h-5" }: { className?: string }) => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className={className}>
    <rect x="3" y="3" width="18" height="18" rx="2" />
    <path d="M3 9h18" />
    <path d="M9 3v6" />
    <path d="M7 13h4" />
    <path d="M7 16h6" />
  </svg>
);

const InvoiceIcon = ({ className = "w-5 h-5" }: { className?: string }) => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className={className}>
    <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8l-6-6z" />
    <path d="M14 2v6h6" />
    <path d="M8 13h8" />
    <path d="M8 17h5" />
    <circle cx="16" cy="17" r="1" fill="currentColor" />
  </svg>
);

const VendorBillIcon = ({ className = "w-5 h-5" }: { className?: string }) => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className={className}>
    <rect x="2" y="4" width="20" height="16" rx="2" />
    <path d="M2 10h20" />
    <path d="M6 15h.01" />
    <path d="M10 15h4" />
  </svg>
);

const PaymentRunIcon = ({ className = "w-5 h-5" }: { className?: string }) => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className={className}>
    <rect x="3" y="4" width="18" height="18" rx="2" />
    <path d="M16 2v4M8 2v4M3 10h18" />
    <path d="M8 14h.01M12 14h.01M16 14h.01M8 18h.01M12 18h.01" />
  </svg>
);

const ApprovalStampIcon = ({ className = "w-5 h-5" }: { className?: string }) => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className={className}>
    <circle cx="12" cy="12" r="9" />
    <path d="M9 12l2 2 4-4" />
  </svg>
);

const AuditLogIcon = ({ className = "w-5 h-5" }: { className?: string }) => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className={className}>
    <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8l-6-6z" />
    <path d="M14 2v6h6" />
    <path d="M12 18v-6" />
    <path d="M9 15l3 3 3-3" />
  </svg>
);

const RedWeekIcon = ({ className = "w-5 h-5" }: { className?: string }) => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className={className}>
    <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
    <path d="M12 9v4M12 17h.01" />
  </svg>
);

const FXIcon = ({ className = "w-5 h-5" }: { className?: string }) => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className={className}>
    <circle cx="12" cy="12" r="9" />
    <path d="M8 12h8M15 9l-3-3-3 3M9 15l3 3 3-3" />
  </svg>
);

const WarehouseIcon = ({ className = "w-5 h-5" }: { className?: string }) => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className={className}>
    <path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z" />
    <path d="M9 22V12h6v10" />
  </svg>
);

const SnowflakeIcon = ({ className = "w-5 h-5" }: { className?: string }) => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className={className}>
    <path d="M12 2v20M2 12h20" />
    <path d="M4.93 4.93l14.14 14.14M19.07 4.93L4.93 19.07" />
    <circle cx="12" cy="12" r="2" />
  </svg>
);

const MatchIcon = ({ className = "w-5 h-5" }: { className?: string }) => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className={className}>
    <path d="M4 12h6M14 12h6" />
    <circle cx="12" cy="12" r="3" />
    <path d="M10 9l2 3 2-3" />
    <path d="M10 15l2-3 2 3" />
  </svg>
);

const PlayIcon = ({ className = "w-4 h-4" }: { className?: string }) => (
  <svg viewBox="0 0 24 24" fill="currentColor" className={className}>
    <path d="M8 5v14l11-7z" />
  </svg>
);

// ═══════════════════════════════════════════════════════════════════════════════
// WORKERS.IO-INSPIRED VISUAL COMPONENTS
// ═══════════════════════════════════════════════════════════════════════════════

// Glowing Orb - Signature Workers.io element
const GlowingOrb = ({ 
  size = 120, 
  className = "",
  variant = "default" 
}: { 
  size?: number; 
  className?: string;
  variant?: "default" | "burgundy" | "cyan" | "emerald";
}) => {
  const gradients = {
    default: "from-rose-500/80 via-purple-500/60 to-blue-500/40",
    burgundy: "from-red-600/80 via-rose-700/60 to-purple-800/40",
    cyan: "from-cyan-400/80 via-blue-500/60 to-indigo-600/40",
    emerald: "from-emerald-400/80 via-teal-500/60 to-cyan-600/40",
  };

  return (
    <div 
      className={`glowing-orb ${className}`}
      style={{ width: size, height: size }}
    >
      <div className={`w-full h-full rounded-full bg-gradient-radial ${gradients[variant]} blur-sm animate-pulse`} 
        style={{ animationDuration: '3s' }}
      />
      <div 
        className="absolute inset-2 rounded-full bg-gradient-radial from-white/30 via-white/10 to-transparent"
        style={{ filter: 'blur(1px)' }}
      />
    </div>
  );
};

// Noise Texture Overlay Component
const NoiseOverlay = ({ opacity = 0.35, className = "" }: { opacity?: number; className?: string }) => (
  <div 
    className={`absolute inset-0 pointer-events-none ${className}`}
    style={{ 
      opacity,
      backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 512 512' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.8' numOctaves='4' seed='15' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E")`,
      mixBlendMode: 'overlay' as const
    }}
  />
);

// ═══════════════════════════════════════════════════════════════════════════════
// WORKERS.IO VISUAL FRAME - Reusable wrapper for all visuals
// ═══════════════════════════════════════════════════════════════════════════════
const WorkersVisualFrame = ({ 
  children, 
  badge,
  className = "",
  showOrb = true,
  glowColor = "rose"
}: { 
  children: React.ReactNode;
  badge?: string;
  className?: string;
  showOrb?: boolean;
  glowColor?: "rose" | "amber" | "emerald" | "cyan" | "purple";
}) => {
  const glowColors = {
    rose: "from-rose-600/50 via-rose-900/25",
    amber: "from-amber-600/50 via-amber-900/25",
    emerald: "from-emerald-600/50 via-emerald-900/25",
    cyan: "from-cyan-600/50 via-cyan-900/25",
    purple: "from-purple-600/50 via-purple-900/25",
  };

  const badgeColors = {
    rose: "from-rose-900/80 via-rose-800/70 to-rose-900/80 border-rose-600/40",
    amber: "from-amber-900/80 via-amber-800/70 to-amber-900/80 border-amber-600/40",
    emerald: "from-emerald-900/80 via-emerald-800/70 to-emerald-900/80 border-emerald-600/40",
    cyan: "from-cyan-900/80 via-cyan-800/70 to-cyan-900/80 border-cyan-600/40",
    purple: "from-purple-900/80 via-purple-800/70 to-purple-900/80 border-purple-600/40",
  };

  const textColors = {
    rose: "text-rose-200/90",
    amber: "text-amber-200/90",
    emerald: "text-emerald-200/90",
    cyan: "text-cyan-200/90",
    purple: "text-purple-200/90",
  };

  const dotColors = {
    rose: "bg-rose-400",
    amber: "bg-amber-400",
    emerald: "bg-emerald-400",
    cyan: "bg-cyan-400",
    purple: "bg-purple-400",
  };

  const cornerColors = {
    rose: "border-rose-500/60",
    amber: "border-amber-500/60",
    emerald: "border-emerald-500/60",
    cyan: "border-cyan-500/60",
    purple: "border-purple-500/60",
  };

  return (
    <div className={`relative ${className}`}>
      {/* Burgundy glow from bottom */}
      <div className={`absolute -bottom-16 left-1/2 -translate-x-1/2 w-[140%] h-[180px] bg-gradient-radial ${glowColors[glowColor]} to-transparent blur-3xl pointer-events-none`} />
      <div className={`absolute -bottom-8 left-1/2 -translate-x-1/2 w-[100%] h-[100px] bg-gradient-radial ${glowColors[glowColor]} to-transparent blur-2xl pointer-events-none`} />
      
      {/* Corner brackets */}
      <div className="absolute -top-1.5 -left-1.5 w-4 h-4 border-l-2 border-t-2 border-white/20 pointer-events-none" />
      <div className="absolute -top-1.5 -right-1.5 w-4 h-4 border-r-2 border-t-2 border-white/20 pointer-events-none" />
      <div className="absolute -bottom-1.5 -left-1.5 w-4 h-4 border-l-2 border-b-2 border-white/20 pointer-events-none" />
      <div className="absolute -bottom-1.5 -right-1.5 w-4 h-4 border-r-2 border-b-2 border-white/20 pointer-events-none" />
      
      {/* Main frame */}
      <div className="relative rounded-lg overflow-hidden border border-white/10 shadow-2xl shadow-black/60">
        {/* Noise layer 1 */}
        <div 
          className="absolute inset-0 pointer-events-none z-30 mix-blend-overlay"
          style={{ 
            opacity: 0.12,
            backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 512 512' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n1'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' seed='15' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n1)'/%3E%3C/svg%3E")`
          }}
        />
        
        {/* Noise layer 2 */}
        <div 
          className="absolute inset-0 pointer-events-none z-31"
          style={{ 
            opacity: 0.08,
            backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n2'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.5' numOctaves='3' seed='42' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n2)'/%3E%3C/svg%3E")`,
            mixBlendMode: 'soft-light'
          }}
        />
        
        {/* Inner glow at bottom */}
        <div className={`absolute bottom-0 left-0 right-0 h-24 bg-gradient-to-t ${glowColors[glowColor]} to-transparent pointer-events-none z-20`} />
        
        {/* Content */}
        <div className="relative z-10">
          {children}
        </div>
      </div>
      
      {/* Badge */}
      {badge && (
        <div className="absolute -bottom-5 left-1/2 -translate-x-1/2 z-50">
          <div className="relative">
            {/* Badge corner brackets */}
            <div className={`absolute -top-0.5 -left-0.5 w-1.5 h-1.5 border-l border-t ${cornerColors[glowColor]}`} />
            <div className={`absolute -top-0.5 -right-0.5 w-1.5 h-1.5 border-r border-t ${cornerColors[glowColor]}`} />
            <div className={`absolute -bottom-0.5 -left-0.5 w-1.5 h-1.5 border-l border-b ${cornerColors[glowColor]}`} />
            <div className={`absolute -bottom-0.5 -right-0.5 w-1.5 h-1.5 border-r border-b ${cornerColors[glowColor]}`} />
            
            <div className={`px-3 py-1 bg-gradient-to-r ${badgeColors[glowColor]} border rounded-sm backdrop-blur-sm`}>
              <div className="flex items-center gap-2">
                <div className="flex gap-0.5">
                  <div className={`w-1 h-1 ${dotColors[glowColor]}/80 rounded-full animate-pulse`} style={{ animationDelay: '0s' }} />
                  <div className={`w-1 h-1 ${dotColors[glowColor]}/60 rounded-full animate-pulse`} style={{ animationDelay: '0.2s' }} />
                  <div className={`w-1 h-1 ${dotColors[glowColor]}/40 rounded-full animate-pulse`} style={{ animationDelay: '0.4s' }} />
                </div>
                <span className={`text-[9px] font-bold ${textColors[glowColor]} tracking-[0.15em] uppercase`}>{badge}</span>
              </div>
            </div>
          </div>
        </div>
      )}
      
      {/* Glowing orb */}
      {showOrb && (
        <div className="absolute -bottom-12 left-1/2 -translate-x-1/2 z-40">
          <div className="relative w-12 h-12">
            <div className="absolute -inset-3 rounded-full bg-gradient-radial from-rose-500/30 via-purple-600/20 to-transparent blur-xl" />
            <div className="absolute inset-0 rounded-full bg-gradient-radial from-rose-500/50 via-purple-600/30 to-blue-700/10 blur-md animate-pulse" style={{ animationDuration: '2.5s' }} />
            <div className="absolute inset-1 rounded-full bg-gradient-radial from-orange-400/70 via-rose-500/50 to-purple-600/30 blur-[2px]" />
            <div className="absolute inset-2 rounded-full bg-gradient-radial from-yellow-200/90 via-orange-400/70 to-rose-500/40" />
            <div className="absolute inset-3 rounded-full bg-gradient-radial from-white/80 via-yellow-200/60 to-transparent" />
          </div>
        </div>
      )}
    </div>
  );
};

// Bento Card Component
const BentoCard = ({ 
  children, 
  className = "", 
  size = "default",
  glowColor = "rgba(150, 30, 60, 0.15)"
}: { 
  children: React.ReactNode; 
  className?: string;
  size?: "default" | "large" | "wide" | "tall";
  glowColor?: string;
}) => {
  const sizeClasses = {
    default: "",
    large: "bento-large",
    wide: "bento-wide",
    tall: "bento-tall"
  };

  return (
    <div 
      className={`bento-card ${sizeClasses[size]} ${className}`}
      style={{ '--glow-color': glowColor } as React.CSSProperties}
    >
      <NoiseOverlay opacity={0.3} />
      <div className="relative z-10 h-full">
        {children}
      </div>
    </div>
  );
};

const ArrowRightIcon = ({ className = "w-4 h-4", animate = false }: { className?: string; animate?: boolean }) => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className={`${className} ${animate ? 'animate-bounce-x' : ''}`}>
    <path d="M5 12h14M12 5l7 7-7 7" />
  </svg>
);

const ChevronRightIcon = ({ className = "w-4 h-4", animate = false, style }: { className?: string; animate?: boolean; style?: React.CSSProperties }) => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className={`${className} ${animate ? 'animate-pulse-right' : ''}`} style={style}>
    <path d="M9 18l6-6-6-6" />
  </svg>
);

// Animated flowing arrow for data flow diagrams
const FlowingArrowIcon = ({ className = "w-6 h-6" }: { className?: string }) => (
  <div className="relative">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className={className}>
      <path d="M5 12h14M12 5l7 7-7 7" className="animate-flow-right" />
    </svg>
    <div className="absolute inset-0 flex items-center">
      <div className="h-0.5 w-2 bg-current rounded-full animate-flow-dot opacity-60" />
            </div>
          </div>
);

// ═══════════════════════════════════════════════════════════════════════════════
// VISUAL COMPONENTS - Finance Artifacts
// ═══════════════════════════════════════════════════════════════════════════════

// Hero: 13-Week Cash Grid (Workers.io-style polished artifact)
const ThirteenWeekGridHero = () => {
  const weeks = ['W1', 'W2', 'W3', 'W4', 'W5', 'W6', 'W7', 'W8', 'W9', 'W10', 'W11', 'W12', 'W13'];
  const redWeeks = [4, 5, 6];
  
  return (
    <div className="bg-[#0a0a0e] overflow-hidden">
      {/* Window Header - macOS style */}
      <div className="bg-[#1a1a1f] border-b border-white/5 px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex gap-2">
            <div className="w-3 h-3 rounded-full bg-[#ff5f57] shadow-sm shadow-red-500/30" />
            <div className="w-3 h-3 rounded-full bg-[#ffbd2e] shadow-sm shadow-yellow-500/30" />
            <div className="w-3 h-3 rounded-full bg-[#28c840] shadow-sm shadow-green-500/30" />
          </div>
          <span className="ml-2 text-[13px] font-medium text-white/90 tracking-tight">13-Week Liquidity Workspace</span>
        </div>
        <div className="flex items-center gap-4">
          <span className="text-[11px] text-white/30 font-mono tracking-wide">As-of: Dec 29, 2024 08:00 UTC</span>
          <div className="flex items-center gap-1.5 px-2 py-0.5 bg-emerald-500/10 rounded-full border border-emerald-500/20">
            <div className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-[10px] font-semibold text-emerald-400 uppercase tracking-wider">Live</span>
          </div>
        </div>
      </div>
      
      {/* Grid - Sharp, professional styling */}
      <div className="p-5">
        <div className="overflow-x-auto">
          <table className="w-full text-[13px]">
            <thead>
              <tr>
                <th className="text-left px-3 py-2.5 font-semibold text-white/40 bg-transparent sticky left-0 tracking-wide">€M</th>
                {weeks.map((w, i) => (
                  <th key={w} className={`px-3 py-2.5 font-semibold text-center min-w-[52px] transition-colors ${
                    redWeeks.includes(i) 
                      ? 'bg-red-500/15 text-red-400 border-b-2 border-red-500/50' 
                      : 'text-white/40 bg-transparent'
                  }`}>
                    <div className="tracking-wide">{w}</div>
                    {redWeeks.includes(i) && <div className="text-[9px] text-red-400/80 font-medium mt-0.5 tracking-wider">▲ RISK</div>}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="text-white/90">
              <tr className="border-t border-white/5 hover:bg-white/[0.02] transition-colors">
                <td className="px-3 py-2.5 font-medium text-white/50 sticky left-0 bg-[#0a0a0e] tracking-wide">Opening</td>
                {[2.4, 2.1, 1.8, 1.2, 0.9, 0.4, 0.2, 0.5, 0.8, 1.1, 1.4, 1.7, 2.0].map((v, i) => (
                  <td key={i} className={`px-3 py-2.5 text-center tabular-nums font-medium ${redWeeks.includes(i) ? 'bg-red-500/10 text-white' : ''}`}>{v.toFixed(1)}</td>
                ))}
              </tr>
              <tr className="border-t border-white/5 hover:bg-white/[0.02] transition-colors">
                <td className="px-3 py-2.5 text-white/40 sticky left-0 bg-[#0a0a0e] tracking-wide">+ Inflows</td>
                {[0.8, 0.6, 0.5, 0.4, 0.3, 0.6, 0.9, 0.8, 0.7, 0.6, 0.5, 0.6, 0.7].map((v, i) => (
                  <td key={i} className={`px-3 py-2.5 text-center tabular-nums font-medium text-emerald-400 ${redWeeks.includes(i) ? 'bg-red-500/10' : ''}`}>+{v.toFixed(1)}</td>
                ))}
              </tr>
              <tr className="border-t border-white/5 hover:bg-white/[0.02] transition-colors">
                <td className="px-3 py-2.5 text-white/40 sticky left-0 bg-[#0a0a0e] tracking-wide">- Outflows</td>
                {[1.1, 0.9, 1.1, 0.7, 0.8, 0.8, 0.6, 0.5, 0.4, 0.3, 0.2, 0.3, 0.4].map((v, i) => (
                  <td key={i} className={`px-3 py-2.5 text-center tabular-nums font-medium text-white/30 ${redWeeks.includes(i) ? 'bg-red-500/10' : ''}`}>-{v.toFixed(1)}</td>
                ))}
              </tr>
              <tr className="border-t-2 border-white/10 font-bold bg-white/[0.03]">
                <td className="px-3 py-3 text-white sticky left-0 bg-white/[0.03] tracking-wide">Closing</td>
                {[2.1, 1.8, 1.2, 0.9, 0.4, 0.2, 0.5, 0.8, 1.1, 1.4, 1.7, 2.0, 2.3].map((v, i) => (
                  <td key={i} className={`px-3 py-3 text-center tabular-nums ${redWeeks.includes(i) ? 'bg-red-500/25 text-red-300' : 'text-white'}`}>{v.toFixed(1)}</td>
                ))}
              </tr>
            </tbody>
          </table>
        </div>
      </div>
      
      {/* Footer - Refined styling */}
      <div className="bg-[#111116] border-t border-white/5 px-5 py-3.5 flex items-center justify-between">
        <div className="flex items-center gap-5 text-[11px]">
          <span className="flex items-center gap-2 text-white/40">
            <span className="h-2.5 w-8 bg-red-500/20 border border-red-500/40 rounded-sm" /> 
            <span className="font-medium">3 red weeks</span>
          </span>
          <span className="text-white/10">│</span>
          <span className="text-white/40">Min balance: <span className="font-bold text-red-400">€0.2M</span> <span className="text-white/30">(W7)</span></span>
        </div>
        <button className="text-[11px] text-emerald-400 font-semibold hover:text-emerald-300 flex items-center gap-1 px-3 py-1.5 bg-emerald-500/10 rounded-lg border border-emerald-500/20 hover:border-emerald-500/30 transition-all">
          View Drilldown <ChevronRightIcon className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
};

// Meet Bank Truth: Cash Ledger + Explained % Gauge
const BankTruthVisual = () => {
  const [explained, setExplained] = useState(0);
  
  useEffect(() => {
    const timer = setTimeout(() => setExplained(97), 500);
    return () => clearTimeout(timer);
  }, []);
  
  const circumference = 2 * Math.PI * 45;
  const offset = circumference - (explained / 100) * circumference;

  return (
    <div className="bg-[#0D0D12] rounded-2xl border border-white/10 shadow-2xl overflow-hidden">
      <div className="bg-white/5 border-b border-white/10 px-4 py-2.5 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="h-8 w-8 rounded-lg bg-emerald-500/20 border border-emerald-500/30 flex items-center justify-center">
            <BankStatementIcon className="w-4 h-4 text-emerald-400" />
          </div>
          <span className="text-xs font-semibold text-white">Cash Ledger</span>
        </div>
        <span className="text-[10px] font-mono text-white/40">As-of: Dec 29, 2024 08:00 UTC</span>
      </div>
            
      <div className="grid grid-cols-3 divide-x divide-white/5">
        {/* Account Table */}
        <div className="col-span-2 p-4">
          <table className="w-full text-xs">
            <thead>
              <tr className="text-white/50 border-b border-white/10">
                <th className="text-left py-2 font-medium">Account</th>
                <th className="text-right py-2 font-medium">Balance</th>
                <th className="text-right py-2 font-medium">Explained</th>
              </tr>
            </thead>
            <tbody>
              {[
                { acc: 'Main Operating (EUR)', bal: '€1,240,500', exp: 98, currency: 'EUR' },
                { acc: 'Treasury Account (USD)', bal: '$890,200', exp: 96, currency: 'USD' },
                { acc: 'Payroll Account (GBP)', bal: '£456,100', exp: 94, currency: 'GBP' },
              ].map((row, i) => (
                <tr key={i} className="border-b border-white/5 hover:bg-white/5 transition-colors">
                  <td className="py-2.5">
                    <div className="font-medium text-white">{row.acc}</div>
                    <div className="text-[10px] text-white/40">{row.currency} • Active</div>
                  </td>
                  <td className="py-2.5 text-right font-mono font-medium text-white">{row.bal}</td>
                  <td className="py-2.5 text-right">
                    <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold ${
                      row.exp >= 95 ? 'bg-emerald-500/20 text-emerald-400' : 'bg-amber-500/20 text-amber-400'
                    }`}>
                      {row.exp}%
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="mt-3 pt-3 border-t border-white/10 flex items-center justify-between">
            <span className="text-[10px] text-white/40">3 accounts • Last sync 2 min ago</span>
            <span className="text-xs font-semibold text-white">Total: €2.6M</span>
          </div>
        </div>
        
        {/* Gauge */}
        <div className="p-4 flex flex-col items-center justify-center bg-white/[0.02]">
          <div className="relative">
            <svg width="110" height="110" className="-rotate-90">
              <circle cx="55" cy="55" r="45" fill="none" stroke="rgba(255,255,255,0.1)" strokeWidth="8" />
              <circle 
                cx="55" cy="55" r="45" fill="none" 
                stroke={explained >= 90 ? '#10b981' : '#3b82f6'} 
                strokeWidth="8" 
                strokeDasharray={circumference} 
                strokeDashoffset={offset}
                strokeLinecap="round"
                className="transition-all duration-1000 ease-out"
              />
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <span className="text-2xl font-bold text-white">{explained}%</span>
              <span className="text-[9px] text-emerald-400 font-medium">EXPLAINED</span>
            </div>
          </div>
          <div className="mt-3 text-center">
            <div className="text-[10px] text-white/50">Cash Explained</div>
            <div className="text-[9px] text-white/30">vs Unknown Bucket</div>
          </div>
        </div>
      </div>
    </div>
  );
};

// Meet Reconciliation Cockpit: 4-Tier Ladder + Unmatched Queue
const ReconciliationCockpitVisual = () => {
  const tiers = [
    { tier: 1, name: 'Deterministic', pct: 72, color: 'bg-emerald-500', desc: 'Auto-cleared' },
    { tier: 2, name: 'Rules-Based', pct: 18, color: 'bg-blue-500', desc: 'Pattern match' },
    { tier: 3, name: 'Suggested', pct: 7, color: 'bg-amber-500', desc: 'Needs approval' },
    { tier: 4, name: 'Manual', pct: 3, color: 'bg-red-500', desc: 'Unmatched queue' },
  ];

  return (
    <div className="bg-[#0D0D12] rounded-2xl border border-white/10 shadow-2xl overflow-hidden">
      <div className="bg-white/5 border-b border-white/10 px-4 py-2.5 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="h-8 w-8 rounded-lg bg-blue-500/20 border border-blue-500/30 flex items-center justify-center">
            <MatchIcon className="w-4 h-4 text-blue-400" />
          </div>
          <span className="text-xs font-semibold text-white">Reconciliation Cockpit</span>
        </div>
        <span className="text-[10px] text-white/40">1,247 transactions this week</span>
      </div>
      
      <div className="p-4">
        {/* 4-Tier Ladder Diagram */}
        <div className="mb-4">
          <div className="text-[10px] font-semibold text-white/50 uppercase tracking-wide mb-3">Match Ladder</div>
          <div className="space-y-2">
            {tiers.map((t) => (
              <div key={t.tier} className="flex items-center gap-3">
                <span className="text-[9px] font-mono text-white/40 w-12">Tier {t.tier}</span>
                <div className="flex-1 h-6 bg-white/5 rounded-md overflow-hidden relative">
                  <div 
                    className={`h-full ${t.color} transition-all duration-1000`} 
                    style={{ width: `${t.pct}%` }} 
                  />
                  <div className="absolute inset-0 flex items-center justify-between px-2">
                    <span className="text-[10px] font-semibold text-white drop-shadow-sm">{t.name}</span>
                    <span className="text-[10px] font-medium text-white/60">{t.pct}%</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Unmatched Cash Queue */}
        <div className="border-t border-white/10 pt-4">
          <div className="flex items-center justify-between mb-3">
            <div className="text-[10px] font-semibold text-white/50 uppercase tracking-wide">Unmatched Cash Queue</div>
            <span className="text-[10px] text-red-400 font-medium">€20,600 pending</span>
          </div>
          <div className="space-y-1.5">
            {[
              { ref: 'TXN-4421', desc: 'Wire transfer - Acme Corp', amt: '€12,400', age: '3d', owner: 'M.S.' },
              { ref: 'TXN-4398', desc: 'Payment received - Unknown', amt: '€8,200', age: '5d', owner: 'Unassigned' },
            ].map((item, i) => (
              <div key={i} className="flex items-center justify-between py-2 px-3 bg-red-500/10 rounded-lg border border-red-500/20">
                <div className="flex items-center gap-3">
                  <span className="text-[9px] font-mono text-white/40">{item.ref}</span>
                  <span className="text-[10px] text-white/60">{item.desc}</span>
                </div>
                <div className="flex items-center gap-4">
                  <span className="text-[10px] font-semibold text-white">{item.amt}</span>
                  <span className="text-[10px] text-red-400 font-medium">{item.age}</span>
                  <span className="text-[9px] px-1.5 py-0.5 bg-white/10 rounded text-white/50">{item.owner}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

// Meet 13-Week Workspace: Chart + P25/P50/P75 Toggle
const ThirteenWeekWorkspaceVisual = () => {
  const [percentile, setPercentile] = useState<'P25' | 'P50' | 'P75'>('P50');
  
  const data = {
    P25: [2.0, 1.6, 1.3, 0.8, 0.3, -0.1, 0.1, 0.4, 0.7, 1.0, 1.3, 1.5, 1.8],
    P50: [2.4, 2.1, 1.8, 1.2, 0.9, 0.4, 0.2, 0.5, 0.8, 1.1, 1.4, 1.7, 2.0],
    P75: [2.8, 2.5, 2.2, 1.6, 1.3, 0.8, 0.6, 0.9, 1.2, 1.5, 1.8, 2.1, 2.4],
  };
  
  const values = data[percentile];
  const minVal = Math.min(...values);
  const maxVal = Math.max(...values);
  const range = maxVal - minVal + 0.5;

  return (
    <div className="bg-[#0D0D12] rounded-2xl border border-white/10 shadow-2xl overflow-hidden">
      <div className="bg-white/5 border-b border-white/10 px-4 py-2.5 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="h-8 w-8 rounded-lg bg-amber-500/20 border border-amber-500/30 flex items-center justify-center">
            <PaymentRunIcon className="w-4 h-4 text-amber-400" />
          </div>
          <span className="text-xs font-semibold text-white">13-Week Liquidity Workspace</span>
        </div>
        <div className="flex items-center gap-1 bg-white/5 rounded-lg p-0.5">
          {(['P25', 'P50', 'P75'] as const).map((p) => (
            <button 
              key={p}
              onClick={() => setPercentile(p)}
              className={`px-2.5 py-1 text-[10px] font-semibold rounded-md transition-all ${
                percentile === p 
                  ? 'bg-white text-[#0A0A0F] shadow-sm' 
                  : 'text-white/50 hover:text-white'
              }`}
            >
              {p}
            </button>
          ))}
        </div>
      </div>

      <div className="p-4">
        {/* Chart */}
        <div className="h-40 flex items-end gap-1 border-b border-white/10 pb-4">
          {values.map((v, i) => {
            const height = ((v - minVal + 0.2) / range) * 100;
            const isRed = v < 0.5;
            return (
              <div key={i} className="flex-1 flex flex-col items-center gap-1">
                <div 
                  className={`w-full rounded-t transition-all duration-500 ${isRed ? 'bg-red-500' : 'bg-blue-500'}`}
                  style={{ height: `${Math.max(height, 5)}%` }}
                />
              </div>
            );
          })}
        </div>
        
        {/* Labels */}
        <div className="flex gap-1 mt-2">
          {['W1', 'W2', 'W3', 'W4', 'W5', 'W6', 'W7', 'W8', 'W9', 'W10', 'W11', 'W12', 'W13'].map((w, i) => (
            <div key={i} className="flex-1 text-center text-[8px] text-white/30">{w}</div>
          ))}
        </div>

        {/* Stats */}
        <div className="mt-4 pt-4 border-t border-white/10 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-1.5">
              <RedWeekIcon className="w-4 h-4 text-red-400" />
              <span className="text-[10px] text-red-400 font-medium">3 red weeks flagged</span>
            </div>
          </div>
          <div className="text-right">
            <div className="text-[10px] text-white/40">Minimum ({percentile})</div>
            <div className="text-sm font-semibold text-white">€{Math.min(...values).toFixed(1)}M</div>
          </div>
        </div>
      </div>
    </div>
  );
};

// Meet Variance Narratives: Snapshot A vs B
const VarianceNarrativesVisual = () => (
  <div className="bg-[#0D0D12] rounded-2xl border border-white/10 shadow-2xl overflow-hidden">
    <div className="bg-white/5 border-b border-white/10 px-4 py-2.5 flex items-center justify-between">
      <div className="flex items-center gap-2">
        <div className="h-8 w-8 rounded-lg bg-purple-500/20 border border-purple-500/30 flex items-center justify-center">
          <AuditLogIcon className="w-4 h-4 text-purple-400" />
        </div>
        <span className="text-xs font-semibold text-white">Variance Analysis</span>
      </div>
      <span className="text-[10px] text-white/40">W3 | Dec 16 → Dec 23</span>
    </div>
    
    <div className="p-4">
      {/* A vs B Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="text-center px-6 py-4 bg-white/5 rounded-lg flex-1 mr-2 border border-white/5">
          <div className="text-[9px] text-white/40 font-medium uppercase tracking-wide mb-1">Snapshot A</div>
          <div className="text-2xl font-bold text-white">€1.8M</div>
          <div className="text-[10px] text-white/50">Dec 16, 2024</div>
        </div>
        
        <div className="flex flex-col items-center px-4">
          <div className="text-lg font-bold text-red-400">-€0.6M</div>
          <div className="flex items-center gap-1 text-white/30">
            <div className="h-px w-8 bg-white/20" />
            <ArrowRightIcon className="w-4 h-4" />
          </div>
          <div className="text-[9px] text-white/40">Delta</div>
        </div>
        
        <div className="text-center px-6 py-4 bg-white/5 rounded-lg flex-1 ml-2 border border-white/5">
          <div className="text-[9px] text-white/40 font-medium uppercase tracking-wide mb-1">Snapshot B</div>
          <div className="text-2xl font-bold text-white">€1.2M</div>
          <div className="text-[10px] text-white/50">Dec 23, 2024</div>
        </div>
      </div>
            
      {/* Driver Chips */}
      <div className="border-t border-white/10 pt-4">
        <div className="text-[10px] font-semibold text-white/50 uppercase tracking-wide mb-3">Variance Drivers</div>
        <div className="space-y-2">
          {[
            { driver: 'New items added', delta: '-€320K', color: 'bg-blue-500/10 text-blue-400 border-blue-500/20', icon: '+' },
            { driver: 'Timing shifts', delta: '-€180K', color: 'bg-amber-500/10 text-amber-400 border-amber-500/20', icon: '~' },
            { driver: 'Reconciled items', delta: '-€100K', color: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20', icon: '✓' },
          ].map((d, i) => (
            <div key={i} className={`flex items-center justify-between px-3 py-2 rounded-lg border ${d.color}`}>
              <div className="flex items-center gap-2">
                <span>{d.icon}</span>
                <span className="text-[11px] font-medium">{d.driver}</span>
              </div>
              <span className="text-[11px] font-semibold">{d.delta}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  </div>
);

// Meet Liquidity Levers: Interactive Sliders
const LiquidityLeversVisual = () => {
  const [vendorDelay, setVendorDelay] = useState(0);
  const [revolverDraw, setRevolverDraw] = useState(0);
  const [factoring, setFactoring] = useState(false);
  
  const baseBalance = 0.2; // W7 minimum
  const vendorImpact = vendorDelay * 0.04;
  const revolverImpact = revolverDraw * 1;
  const factoringImpact = factoring ? 0.3 : 0;
  const newBalance = baseBalance + vendorImpact + revolverImpact + factoringImpact;
  const totalImpact = vendorImpact + revolverImpact + factoringImpact;

  return (
    <div className="bg-[#0D0D12] rounded-2xl border border-white/10 shadow-2xl overflow-hidden">
      <div className="bg-white/5 border-b border-white/10 px-4 py-2.5 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="h-8 w-8 rounded-lg bg-rose-500/20 border border-rose-500/30 flex items-center justify-center">
            <FXIcon className="w-4 h-4 text-rose-400" />
          </div>
          <span className="text-xs font-semibold text-white">Liquidity Levers</span>
        </div>
        <span className="text-[10px] text-white/40">What-if Scenario Builder</span>
      </div>

      <div className="p-4 space-y-5">
        {/* Vendor Payment Delay */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <VendorBillIcon className="w-4 h-4 text-white/40" />
              <span className="text-[11px] font-medium text-white">Vendor Payment Delay</span>
            </div>
            <span className="text-[11px] font-mono text-white/60">{vendorDelay} days</span>
          </div>
          <input 
            type="range" min="0" max="14" value={vendorDelay}
            onChange={(e) => setVendorDelay(Number(e.target.value))}
            className="w-full h-2 bg-white/10 rounded-lg appearance-none cursor-pointer accent-rose-500"
          />
          <div className="flex justify-between text-[9px] text-white/30 mt-1">
            <span>0 days</span>
            <span>14 days</span>
          </div>
        </div>
        
        {/* Revolver Draw */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <BankStatementIcon className="w-4 h-4 text-white/40" />
              <span className="text-[11px] font-medium text-white">Revolver Draw</span>
            </div>
            <span className="text-[11px] font-mono text-white/60">€{revolverDraw}M</span>
          </div>
          <input 
            type="range" min="0" max="5" value={revolverDraw}
            onChange={(e) => setRevolverDraw(Number(e.target.value))}
            className="w-full h-2 bg-white/10 rounded-lg appearance-none cursor-pointer accent-rose-500"
          />
          <div className="flex justify-between text-[9px] text-white/30 mt-1">
            <span>€0M</span>
            <span>€5M (facility limit)</span>
          </div>
        </div>
        
        {/* Factoring Toggle */}
        <div className="flex items-center justify-between py-2">
          <div className="flex items-center gap-2">
            <InvoiceIcon className="w-4 h-4 text-white/40" />
            <div>
              <span className="text-[11px] font-medium text-white">Activate Factoring</span>
              <div className="text-[9px] text-white/40">Accelerate €300K receivables</div>
            </div>
          </div>
          <button 
            onClick={() => setFactoring(!factoring)}
            className={`w-11 h-6 rounded-full transition-colors ${factoring ? 'bg-rose-500' : 'bg-white/10'}`}
          >
            <div className={`w-5 h-5 rounded-full bg-white shadow transition-transform ${factoring ? 'translate-x-5' : 'translate-x-0.5'}`} />
          </button>
        </div>

        {/* Impact Summary */}
        <div className="border-t border-white/10 pt-4">
          <div className="flex items-center justify-between bg-white/5 rounded-lg p-3 border border-white/5">
            <div>
              <div className="text-[10px] text-white/50">W7 Balance Impact</div>
              <div className="text-[9px] text-white/30">After applying levers</div>
            </div>
            <div className="text-right">
              <div className="text-xl font-bold text-white">€{newBalance.toFixed(1)}M</div>
              <div className={`text-[11px] font-medium ${totalImpact > 0 ? 'text-emerald-400' : 'text-white/40'}`}>
                {totalImpact > 0 ? `+€${totalImpact.toFixed(2)}M` : 'No change'}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

// Meet Warehouse Mode: Snowflake Sync
const WarehouseModeVisual = () => (
  <div className="bg-[#0a0a0e] rounded-lg overflow-hidden">
    <div className="bg-[#111116] border-b border-white/5 px-4 py-3 flex items-center justify-between">
      <div className="flex items-center gap-3">
        <div className="h-9 w-9 rounded-lg bg-cyan-500/20 border border-cyan-500/30 flex items-center justify-center">
          <WarehouseIcon className="w-5 h-5 text-cyan-400" />
        </div>
        <span className="text-[13px] font-semibold text-white/90">Warehouse Mode</span>
      </div>
      <div className="flex items-center gap-1.5 px-2 py-0.5 bg-emerald-500/10 rounded-full border border-emerald-500/20">
        <div className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
        <span className="text-[10px] text-emerald-400 font-semibold uppercase tracking-wider">Synced</span>
      </div>
    </div>
    
    <div className="p-6 relative">
      {/* Animated data particles in background */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        {[...Array(8)].map((_, i) => (
          <div 
            key={i}
            className="absolute w-1 h-1 rounded-full bg-emerald-400/60"
            style={{
              left: `${15 + (i % 4) * 20}%`,
              animation: `float-particle ${3 + i * 0.5}s ease-in-out infinite`,
              animationDelay: `${i * 0.3}s`,
              top: '30%'
            }}
          />
        ))}
        {[...Array(6)].map((_, i) => (
          <div 
            key={`b-${i}`}
            className="absolute w-1 h-1 rounded-full bg-blue-400/60"
            style={{
              right: `${15 + (i % 3) * 20}%`,
              animation: `float-particle-reverse ${3.5 + i * 0.4}s ease-in-out infinite`,
              animationDelay: `${i * 0.4}s`,
              top: '40%'
            }}
          />
        ))}
      </div>
      
      {/* Sync Diagram */}
      <div className="flex items-center justify-center gap-8 mb-8 relative z-10">
        <div className="text-center">
          <div className="relative">
            <div className="absolute -inset-2 bg-gradient-radial from-cyan-500/30 to-transparent blur-lg animate-pulse" style={{ animationDuration: '2s' }} />
            <div className="relative h-20 w-20 rounded-xl bg-gradient-to-br from-[#29B5E8] to-[#0D6EAD] flex items-center justify-center shadow-lg shadow-cyan-500/30">
              <SnowflakeIcon className="w-10 h-10 text-white" />
            </div>
          </div>
          <span className="text-sm font-medium text-white mt-3 block">Snowflake</span>
        </div>

        <div className="flex flex-col gap-3 relative">
          {/* Animated data flow - READ */}
          <div className="flex items-center gap-2">
            <span className="text-[10px] text-white/40 w-12 text-right font-medium">read</span>
            <div className="relative w-20 h-0.5 bg-white/10 overflow-hidden rounded-full">
              <div className="absolute inset-y-0 w-8 bg-gradient-to-r from-transparent via-emerald-400 to-transparent animate-data-stream" />
            </div>
            <div className="w-5 h-5 rounded-full bg-emerald-500/20 border border-emerald-500/40 flex items-center justify-center">
              <ArrowRightIcon className="w-3 h-3 text-emerald-400" />
            </div>
          </div>
          {/* Animated data flow - WRITE */}
          <div className="flex items-center gap-2">
            <div className="w-5 h-5 rounded-full bg-blue-500/20 border border-blue-500/40 flex items-center justify-center">
              <ArrowRightIcon className="w-3 h-3 text-blue-400 rotate-180" />
            </div>
            <div className="relative w-20 h-0.5 bg-white/10 overflow-hidden rounded-full">
              <div className="absolute inset-y-0 w-8 bg-gradient-to-r from-transparent via-blue-400 to-transparent animate-data-stream-reverse" />
            </div>
            <span className="text-[10px] text-white/40 w-12 font-medium">write</span>
          </div>
        </div>

        <div className="text-center">
          <div className="relative">
            <div className="absolute -inset-2 bg-gradient-radial from-white/20 to-transparent blur-lg animate-pulse" style={{ animationDuration: '2.5s', animationDelay: '0.5s' }} />
            <div className="relative h-20 w-20 rounded-xl bg-white flex items-center justify-center text-[#0A0A0F] font-bold text-2xl shadow-lg shadow-white/20">
              G
            </div>
          </div>
          <span className="text-sm font-medium text-white mt-3 block">Gitto</span>
        </div>
      </div>

      {/* Table Lists with animated highlights */}
      <div className="grid grid-cols-2 gap-4 relative z-10">
        <div className="bg-[#0D0D14] rounded-lg p-4 border border-emerald-500/20 relative overflow-hidden">
          {/* Scanning line animation */}
          <div className="absolute inset-0 overflow-hidden">
            <div className="absolute inset-x-0 h-px bg-gradient-to-r from-transparent via-emerald-400/50 to-transparent animate-scan-line" />
          </div>
          <div className="text-[10px] font-semibold text-emerald-400/70 uppercase tracking-wider mb-3">Read from Warehouse</div>
          <div className="space-y-2 font-mono text-[11px] text-white/70">
            {['bank_transactions', 'ar_invoices', 'ap_bills', 'gl_balances'].map((table, i) => (
              <div key={table} className="flex items-center gap-2 animate-fade-in-up" style={{ animationDelay: `${i * 0.1}s` }}>
                <span className="text-emerald-400 animate-pulse" style={{ animationDelay: `${i * 0.2}s` }}>↓</span> 
                <span>{table}</span>
              </div>
            ))}
          </div>
        </div>
        <div className="bg-[#0D0D14] rounded-lg p-4 border border-blue-500/20 relative overflow-hidden">
          {/* Scanning line animation */}
          <div className="absolute inset-0 overflow-hidden">
            <div className="absolute inset-x-0 h-px bg-gradient-to-r from-transparent via-blue-400/50 to-transparent animate-scan-line" style={{ animationDelay: '1s' }} />
          </div>
          <div className="text-[10px] font-semibold text-blue-400/70 uppercase tracking-wider mb-3">Writeback to Warehouse</div>
          <div className="space-y-2 font-mono text-[11px] text-white/70">
            {['gitto_snapshots', 'gitto_matches', 'gitto_forecasts', 'gitto_audit_log'].map((table, i) => (
              <div key={table} className="flex items-center gap-2 animate-fade-in-up" style={{ animationDelay: `${0.5 + i * 0.1}s` }}>
                <span className="text-blue-400 animate-pulse" style={{ animationDelay: `${i * 0.2}s` }}>↑</span> 
                <span>{table}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  </div>
);

// ═══════════════════════════════════════════════════════════════════════════════
// MAIN PAGE COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

export default function Landing() {
  return (
    <div className="min-h-screen bg-[#0A0A0F] text-white font-sans antialiased overflow-hidden">
      
      {/* ═══════════════════════════════════════════════════════════════════════════════
          WORKERS.IO-INSPIRED BACKGROUND WITH NOISE & GLOWS
          ═══════════════════════════════════════════════════════════════════════════════ */}
      <div className="fixed inset-0 -z-10 overflow-hidden pointer-events-none">
        {/* Base dark gradient */}
        <div className="absolute inset-0 bg-gradient-to-b from-[#0A0A0F] via-[#0D0D14] to-[#0A0A0F]" />
        
        {/* Noise texture layers - Workers.io signature */}
        <div className="noise-layer-1" />
        <div className="noise-layer-2" />
        
        {/* Moody burgundy/crimson glow at bottom - Workers.io signature */}
        <div className="glow-burgundy bottom-0 left-1/2 -translate-x-1/2" />
        <div className="absolute bottom-0 left-1/2 -translate-x-1/2 w-[800px] h-[400px] bg-gradient-radial from-rose-900/30 via-rose-950/20 to-transparent blur-3xl" />
        
        {/* Subtle ambient orbs */}
        <div className="absolute top-20 left-[10%] w-[500px] h-[500px] bg-gradient-to-br from-blue-500/[0.05] to-cyan-500/[0.02] rounded-full blur-3xl animate-float-slow" />
        <div className="absolute top-[50%] right-[5%] w-[400px] h-[400px] bg-gradient-to-br from-emerald-500/[0.04] to-teal-500/[0.02] rounded-full blur-3xl animate-float" style={{ animationDelay: '-2s' }} />
        <div className="absolute bottom-[10%] left-[30%] w-[300px] h-[300px] bg-gradient-to-br from-violet-500/[0.03] to-purple-500/[0.02] rounded-full blur-3xl animate-float-slow" style={{ animationDelay: '-4s' }} />
        
        {/* Subtle grid pattern */}
        <div className="absolute inset-0 opacity-[0.012]" style={{ 
          backgroundImage: `url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='1'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")` 
        }} />
        
        {/* Vignette overlay */}
        <div className="absolute inset-0 bg-gradient-radial from-transparent via-transparent to-black/40" />
      </div>

      {/* ─────────────────────────────────────────────────────────────────────── */}
      {/* NAVIGATION - Clean, minimal like Solcoa (dark mode) */}
      {/* ─────────────────────────────────────────────────────────────────────── */}
      <nav className="fixed top-0 left-0 right-0 z-50 bg-[#0A0A0F]/90 backdrop-blur-xl border-b border-white/5">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-3 group">
            <div className="h-9 w-9 rounded-xl bg-white flex items-center justify-center text-[#0A0A0F] font-serif font-semibold text-lg tracking-tight group-hover:scale-105 transition-transform">
              G
            </div>
            <span className="font-serif font-semibold text-xl text-white tracking-tight">Gitto</span>
          </Link>
          <div className="hidden md:flex items-center gap-10 text-sm tracking-wide">
            <a href="#primitives" className="text-white/50 hover:text-white transition-colors underline-grow">product</a>
            <a href="#trust" className="text-white/50 hover:text-white transition-colors underline-grow">trust</a>
            <a href="#integrations" className="text-white/50 hover:text-white transition-colors underline-grow">integrations</a>
            <Link href="/about" className="text-white/50 hover:text-white transition-colors underline-grow">about</Link>
          </div>
          <div className="flex items-center gap-4">
            <Link href="/app" className="text-sm text-white/50 hover:text-white transition-colors hidden sm:block underline-grow tracking-wide">
              sign in
            </Link>
            <Link href="/app">
              <Button className="magnetic-button button-glow bg-white text-[#0A0A0F] hover:bg-white/90 text-sm px-6 h-11 rounded-xl font-medium tracking-wide hover:-translate-y-0.5 transition-all">
                Book a Demo
              </Button>
            </Link>
          </div>
        </div>
      </nav>

      {/* ─────────────────────────────────────────────────────────────────────── */}
      {/* HERO SECTION - Solcoa-inspired with Manrope + gradient text */}
      {/* ─────────────────────────────────────────────────────────────────────── */}
      <section className="pt-32 pb-24 px-6 relative min-h-screen">
        {/* Finance-relevant 13-column grid (representing 13 weeks) */}
        <div className="finance-grid">
          <div className="finance-grid-inner">
            {['W1','W2','W3','W4','W5','W6','W7','W8','W9','W10','W11','W12','W13'].map((week, i) => (
              <div key={i} className="finance-grid-line" data-week={week} />
            ))}
          </div>
        </div>

        {/* Horizontal cash threshold lines */}
        <div className="finance-horizontal-grid">
          <div className="finance-h-line" style={{ top: '25%' }}>
            <div className="cash-tick" data-value="€2M" style={{ top: 0 }} />
          </div>
          <div className="finance-h-line" style={{ top: '50%' }}>
            <div className="cash-tick" data-value="€1M" style={{ top: 0 }} />
          </div>
          <div className="finance-h-line" style={{ top: '75%' }}>
            <div className="cash-tick" data-value="€0" style={{ top: 0 }} />
          </div>
        </div>
        
        <div className="max-w-6xl mx-auto relative">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">
            {/* Left: Copy with Solcoa-style typography (dark mode) */}
            <div className="space-y-8">
              <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 animate-text-reveal reveal-delay-1">
                <div className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
                <span className="text-xs font-medium text-emerald-400 tracking-wide">For finance teams that run weekly cash meetings</span>
              </div>

              {/* Solcoa-style headline - Manrope, gradient fade, tight tracking */}
              <div className="mt-8 animate-text-reveal reveal-delay-2">
                <h1 className="headline-solcoa text-4xl sm:text-5xl md:text-6xl lg:text-[72px] text-gradient-fade-dark max-w-[20ch]">
                  Bank-Truth Cash Forecasting, Made Real.
                </h1>
              </div>

              {/* Bold accent statement - Rotating mottos */}
              <div className="headline-bold text-xl md:text-2xl text-white animate-text-reveal reveal-delay-3 h-8 md:h-10 overflow-hidden relative">
                {[
                  "Every number ties to a bank transaction.",
                  "No more spreadsheet chaos.",
                  "Variance explained in seconds.",
                  "Cash truth, not cash guesses.",
                  "From bank feed to forecast.",
                ].map((motto, i) => (
                  <p 
                    key={i}
                    className="absolute w-full opacity-0"
                    style={{
                      animation: `text-slide 15s ease-in-out infinite`,
                      animationDelay: `${i * 3}s`,
                    }}
                  >
                    {motto}
                  </p>
                ))}
              </div>
              
              <p className="text-lg text-white/50 leading-relaxed max-w-lg animate-text-reveal reveal-delay-4 tracking-tight">
                13-week liquidity workspace with reconciliation, variance narratives, and action levers for CFOs who demand truth.
              </p>
              
              <div className="flex items-center gap-4 pt-2 animate-slide-up" style={{ animationDelay: '0.7s' }}>
                <Link href="/app">
                  <Button className="magnetic-button button-glow bg-white text-[#0A0A0F] hover:bg-white/90 h-14 px-8 text-base font-medium rounded-xl flex items-center gap-3 group shadow-xl shadow-black/30 hover:shadow-2xl transition-all hover:-translate-y-1">
                    Book a Demo
                    <ArrowRightIcon className="w-5 h-5 group-hover:translate-x-1 transition-transform" animate />
                  </Button>
                </Link>
                <button className="magnetic-button button-glow-secondary flex items-center gap-3 h-14 px-6 text-base font-medium text-white/70 hover:text-white border-2 border-white/20 rounded-xl hover:bg-white/5 hover:border-white/30 transition-all group hover:-translate-y-1">
                  <div className="h-10 w-10 rounded-full bg-white/10 flex items-center justify-center group-hover:scale-110 transition-transform">
                    <PlayIcon className="w-4 h-4 text-white ml-0.5" />
                  </div>
                  Product Tour
                </button>
              </div>

              {/* Expanding line divider */}
              <div className="h-px bg-white/10 animate-line-expand" style={{ animationDelay: '0.9s' }} />

              <div className="flex items-center gap-8 text-sm text-white/50 animate-slide-up" style={{ animationDelay: '1s' }}>
                <div className="flex items-center gap-2">
                  <ApprovalStampIcon className="w-4 h-4 text-emerald-400" />
                  <span><span className="font-semibold text-white">97%</span> Cash Explained</span>
                </div>
                <div className="flex items-center gap-2">
                  <PaymentRunIcon className="w-4 h-4 text-blue-400" />
                  <span><span className="font-semibold text-white">0.8 day</span> forecast error</span>
                </div>
              </div>
            </div>

            {/* Right: 13-Week Grid - Workers.io Premium Treatment */}
            <div className="relative animate-card-entrance pb-16" style={{ animationDelay: '0.4s' }}>
              <WorkersVisualFrame badge="Viewing Liquidity" glowColor="amber">
                <ThirteenWeekGridHero />
              </WorkersVisualFrame>
            </div>
          </div>

          {/* Scroll indicator like Solcoa - functional */}
          <div className="flex justify-center mt-16 animate-slide-up" style={{ animationDelay: '1.2s' }}>
            <button 
              onClick={() => {
                const nextSection = document.querySelector('section:nth-of-type(2)');
                if (nextSection) {
                  nextSection.scrollIntoView({ behavior: 'smooth' });
                }
              }}
              className="animate-scroll-indicator cursor-pointer hover:scale-110 transition-transform"
              aria-label="Scroll down"
            >
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-white/30 hover:text-emerald-400 transition-colors">
                <path d="M12 5v14M5 12l7 7 7-7" />
              </svg>
            </button>
          </div>
        </div>
      </section>

      {/* ─────────────────────────────────────────────────────────────────────── */}
      {/* SECTION 2: WHAT YOU RUN EVERY WEEK */}
      {/* ─────────────────────────────────────────────────────────────────────── */}
      <section className="py-20 px-6 bg-[#0D0D12] border-y border-white/5 relative overflow-hidden">
        {/* Ambient glow effects */}
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <div className="absolute top-0 left-1/4 w-[400px] h-[400px] bg-gradient-to-br from-emerald-500/10 via-teal-500/5 to-transparent rounded-full blur-3xl" />
          <div className="absolute bottom-0 right-1/4 w-[300px] h-[300px] bg-gradient-to-br from-blue-500/10 via-cyan-500/5 to-transparent rounded-full blur-3xl" />
        </div>
        {/* Animated background line */}
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <div className="w-full h-px bg-gradient-to-r from-transparent via-white/10 to-transparent animate-shimmer" />
        </div>
        
        <div className="max-w-6xl mx-auto relative">
          <div className="text-center mb-12">
            <h2 className="headline-solcoa text-4xl md:text-5xl text-gradient-fade-dark mb-4">What you run every week.</h2>
            <p className="headline-bold text-xl text-white">Monday 9am cash meeting</p>
            <p className="text-white/50 mt-2 tracking-tight">
              <span className="font-medium text-white/70">refresh</span> <ChevronRightIcon className="w-3 h-3 inline text-white/30 animate-pulse-right" /> <span className="font-medium text-white/70">snapshot</span> <ChevronRightIcon className="w-3 h-3 inline text-white/30 animate-pulse-right" style={{ animationDelay: '0.2s' }} /> <span className="font-medium text-white/70">variance</span> <ChevronRightIcon className="w-3 h-3 inline text-white/30 animate-pulse-right" style={{ animationDelay: '0.4s' }} /> <span className="font-medium text-white/70">actions</span>
            </p>
          </div>

          {/* Timeline */}
          <div className="relative flex items-start justify-between max-w-4xl mx-auto">
            {/* Connection Line with animated flow */}
            <div className="absolute top-6 left-[10%] right-[10%] h-0.5 bg-white/10 overflow-hidden">
              <div className="h-full w-20 bg-gradient-to-r from-transparent via-emerald-400 to-transparent animate-data-stream" />
                 </div>

            {[
              { time: '9:00', label: 'Refresh', desc: 'Ingest overnight bank feeds', icon: <BankStatementIcon className="w-5 h-5" />, color: 'from-emerald-500 to-teal-500', textColor: 'text-emerald-400', borderColor: 'border-emerald-500/30', bgColor: 'bg-emerald-500/20' },
              { time: '9:05', label: 'Snapshot', desc: 'Lock as-of balances', icon: <AuditLogIcon className="w-5 h-5" />, color: 'from-blue-500 to-cyan-500', textColor: 'text-blue-400', borderColor: 'border-blue-500/30', bgColor: 'bg-blue-500/20' },
              { time: '9:10', label: 'Variance', desc: 'Review vs last week', icon: <RedWeekIcon className="w-5 h-5" />, color: 'from-amber-500 to-orange-500', textColor: 'text-amber-400', borderColor: 'border-amber-500/30', bgColor: 'bg-amber-500/20' },
              { time: '9:20', label: 'Actions', desc: 'Assign unmatched queue', icon: <ApprovalStampIcon className="w-5 h-5" />, color: 'from-violet-500 to-purple-500', textColor: 'text-violet-400', borderColor: 'border-violet-500/30', bgColor: 'bg-violet-500/20' },
              { time: '9:30', label: 'Levers', desc: 'Model what-if scenarios', icon: <FXIcon className="w-5 h-5" />, color: 'from-rose-500 to-pink-500', textColor: 'text-rose-400', borderColor: 'border-rose-500/30', bgColor: 'bg-rose-500/20' },
            ].map((step, i) => (
              <div key={i} className="relative flex flex-col items-center z-10 group" style={{ flex: 1 }}>
                <div className="text-[10px] font-mono text-white/40 mb-2">{step.time}</div>
                <div className={`h-14 w-14 rounded-2xl ${step.bgColor} ${step.borderColor} border flex items-center justify-center ${step.textColor} mb-3 group-hover:scale-110 group-hover:shadow-lg group-hover:shadow-current/20 transition-all duration-300`}>
                  {step.icon}
                    </div>
                <div className="text-center">
                  <div className={`text-sm font-semibold text-white group-hover:${step.textColor} transition-colors`}>{step.label}</div>
                  <div className="text-[11px] text-white/40 mt-0.5 max-w-[100px]">{step.desc}</div>
                    </div>
                 </div>
            ))}
           </div>
        </div>
      </section>

      {/* ─────────────────────────────────────────────────────────────────────── */}
      {/* SECTIONS 3-8: THE 6 PRIMITIVES */}
      {/* ─────────────────────────────────────────────────────────────────────── */}
      <section id="primitives" className="py-24 px-6 relative bg-[#0A0A0F] overflow-hidden section-premium">
        {/* Workers.io-style noise textures */}
        <div className="noise-layer-1" />
        <div className="noise-layer-2" />
        
        {/* Ambient glow effects */}
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <div className="absolute top-[10%] left-[5%] w-[500px] h-[500px] bg-gradient-to-br from-emerald-500/[0.07] via-teal-500/[0.03] to-transparent rounded-full blur-3xl" />
          <div className="absolute top-[40%] right-[5%] w-[400px] h-[400px] bg-gradient-to-br from-blue-500/[0.07] via-cyan-500/[0.03] to-transparent rounded-full blur-3xl" />
          <div className="absolute bottom-[20%] left-[20%] w-[450px] h-[450px] bg-gradient-to-br from-violet-500/[0.05] via-purple-500/[0.02] to-transparent rounded-full blur-3xl" />
          <div className="absolute bottom-[40%] right-[15%] w-[350px] h-[350px] bg-gradient-to-br from-amber-500/[0.05] via-orange-500/[0.02] to-transparent rounded-full blur-3xl" />
          
          {/* Moody burgundy glow */}
          <div className="absolute bottom-0 left-1/2 -translate-x-1/2 w-[1000px] h-[300px] bg-gradient-radial from-rose-900/15 via-rose-950/10 to-transparent blur-3xl" />
        </div>
        {/* Subtle gradient accent */}
        <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-white/10 to-transparent" />
        
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-20">
            <span className="inline-flex items-center gap-2 text-xs font-medium text-white/40 uppercase tracking-[0.2em] mb-6">
              <span className="h-px w-8 bg-white/20" />
              Finance-Native Primitives
              <span className="h-px w-8 bg-white/20" />
            </span>
            <h2 className="headline-solcoa text-4xl md:text-5xl lg:text-6xl text-gradient-fade-dark">
              Built for how treasury actually works.
            </h2>
            <p className="headline-bold text-xl text-white mt-6">
              Not dashboards. Not charts. Real finance artifacts.
            </p>
          </div>
          
          <div className="space-y-32">
            
            {/* ═══════════════════════════════════════════════════════════════════ */}
            {/* MEET BANK TRUTH */}
            {/* ═══════════════════════════════════════════════════════════════════ */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-16 items-center relative group">
              {/* Subtle gradient background */}
              <div className="absolute -inset-8 bg-gradient-to-br from-emerald-500/5 via-transparent to-teal-500/5 rounded-3xl opacity-0 group-hover:opacity-100 transition-all duration-700 -z-10" />
              
              <div className="order-2 lg:order-1 transform group-hover:scale-[1.02] transition-transform duration-500 pb-16">
                <WorkersVisualFrame badge="Viewing Bank Truth" glowColor="emerald">
                  <BankTruthVisual />
                </WorkersVisualFrame>
              </div>
              <div className="order-1 lg:order-2 space-y-6">
                <div>
                  <span className="inline-block px-3 py-1 bg-emerald-500/10 border border-emerald-500/20 rounded-full text-[11px] font-semibold text-emerald-400 uppercase tracking-wide mb-4 group-hover:bg-emerald-500/20 transition-colors duration-300">
                    Meet Bank Truth
                  </span>
                  <h3 className="text-2xl font-bold text-white leading-tight">
                    Balances and transactions as-of X.<br />
                    <span className="text-white/40">No silent assumptions.</span>
                  </h3>
                 </div>
                <ul className="space-y-3">
                  {[
                    'Bank-True / Reconciled / Modeled / Unknown badges on every number',
                    'Data freshness detection: bank vs ERP age mismatch warnings',
                    'Missing FX rates route to Unknown (never silently default to 1.0)',
                    'Cash Explained % metric with week-over-week trend',
                  ].map((item, i) => (
                    <li key={i} className="flex items-start gap-3 text-white/60">
                      <ApprovalStampIcon className="w-5 h-5 text-emerald-400 mt-0.5 flex-shrink-0" />
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
                <div className="pt-4 border-t border-white/10">
                  <p className="text-xs text-white/40">
                    <span className="font-semibold text-white/60">Under the hood:</span> As-of timestamps locked per snapshot. Stale data blocks snapshot lock. Multi-currency with FX rate versioning.
                  </p>
                </div>
           </div>
                       </div>

            {/* ═══════════════════════════════════════════════════════════════════ */}
            {/* MEET THE RECONCILIATION COCKPIT */}
            {/* ═══════════════════════════════════════════════════════════════════ */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-16 items-center relative group">
              {/* Subtle gradient background */}
              <div className="absolute -inset-8 bg-gradient-to-bl from-blue-500/5 via-transparent to-cyan-500/5 rounded-3xl opacity-0 group-hover:opacity-100 transition-all duration-700 -z-10" />
              
                 <div className="space-y-6">
                <div>
                  <span className="inline-block px-3 py-1 bg-blue-500/10 border border-blue-500/20 rounded-full text-[11px] font-semibold text-blue-400 uppercase tracking-wide mb-4 group-hover:bg-blue-500/20 transition-colors duration-300">
                    Meet the Reconciliation Cockpit
                  </span>
                  <h3 className="text-2xl font-bold text-white leading-tight">
                    Deterministic matches auto-clear.<br />
                    Suggestions require approval.<br />
                    <span className="text-white/40">Exceptions are owned.</span>
                  </h3>
                       </div>
                <ul className="space-y-3">
                  {[
                    '4-tier match ladder: Tier 1 deterministic → Tier 2 rules → Tier 3 suggested → Tier 4 manual',
                    'Many-to-many matching: one bank txn ↔ multiple invoices, partials supported',
                    'Allocation conservation: sum(allocations) always equals txn_amount',
                    'Suggested matches require approval (no auto-apply, confidence shown)',
                  ].map((item, i) => (
                    <li key={i} className="flex items-start gap-3 text-white/60">
                      <ApprovalStampIcon className="w-5 h-5 text-blue-400 mt-0.5 flex-shrink-0" />
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
                <div className="pt-4 border-t border-white/10">
                  <p className="text-xs text-white/40">
                    <span className="font-semibold text-white/60">Under the hood:</span> O(n*k) indexed lookups, configurable tolerance windows, unmatched lifecycle with statuses and SLA aging.
                  </p>
                </div>
                       </div>
            <div className="pb-16">
                <WorkersVisualFrame badge="Reconciling Data" glowColor="cyan">
                  <ReconciliationCockpitVisual />
                </WorkersVisualFrame>
              </div>
          </div>

            {/* ═══════════════════════════════════════════════════════════════════ */}
            {/* MEET THE 13-WEEK LIQUIDITY WORKSPACE */}
            {/* ═══════════════════════════════════════════════════════════════════ */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-16 items-center relative group">
              {/* Subtle gradient background */}
              <div className="absolute -inset-8 bg-gradient-to-br from-amber-500/5 via-transparent to-orange-500/5 rounded-3xl opacity-0 group-hover:opacity-100 transition-all duration-700 -z-10" />
              
              <div className="order-2 lg:order-1 transform group-hover:scale-[1.02] transition-transform duration-500 pb-16">
                <WorkersVisualFrame badge="Viewing Liquidity" glowColor="amber">
                  <ThirteenWeekWorkspaceVisual />
                </WorkersVisualFrame>
              </div>
              <div className="order-1 lg:order-2 space-y-6">
                <div>
                  <span className="inline-block px-3 py-1 bg-amber-500/10 border border-amber-500/20 rounded-full text-[11px] font-semibold text-amber-400 uppercase tracking-wide mb-4 group-hover:bg-amber-500/20 transition-colors duration-300">
                    Meet the 13-Week Workspace
                  </span>
                  <h3 className="text-2xl font-bold text-white leading-tight">
                    Probabilistic forecasting,<br />
                    <span className="text-emerald-400/60">not single-point guesses.</span>
                  </h3>
            </div>
                <ul className="space-y-3">
                  {[
                    'Cash math invariant: close = open + inflows - outflows (always)',
                    'Every cell drills down to row-level invoice/transaction IDs',
                    'P25/P50/P75 probabilistic forecasting with sample size N',
                    'Red week attribution: identifies which invoices cause shortfalls',
                  ].map((item, i) => (
                    <li key={i} className="flex items-start gap-3 text-white/60">
                      <ApprovalStampIcon className="w-5 h-5 text-amber-500 mt-0.5 flex-shrink-0" />
                      <span>{item}</span>
                    </li>
                  ))}
            </ul>
                <div className="pt-4 border-t border-white/10">
                  <p className="text-xs text-white/40">
                    <span className="font-semibold text-white/60">Under the hood:</span> Segment hierarchy with fallback chain. Delay = paid_date - due_date. Regime shift detection for payment behavior changes.
            </p>
          </div>
        </div>
        </div>

            {/* ═══════════════════════════════════════════════════════════════════ */}
            {/* MEET AUDIT & IMMUTABILITY */}
            {/* ═══════════════════════════════════════════════════════════════════ */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-16 items-center relative group">
              {/* Subtle gradient background */}
              <div className="absolute -inset-8 bg-gradient-to-bl from-purple-500/5 via-transparent to-violet-500/5 rounded-3xl opacity-0 group-hover:opacity-100 transition-all duration-700 -z-10" />
              
              <div className="space-y-6">
                <div>
                  <span className="inline-block px-3 py-1 bg-purple-500/10 border border-purple-500/20 rounded-full text-[11px] font-semibold text-purple-400 uppercase tracking-wide mb-4 group-hover:bg-purple-500/20 transition-colors duration-300">
                    Meet Audit & Immutability
                  </span>
                  <h3 className="text-2xl font-bold text-white leading-tight">
                    Locked means locked.<br />
                    <span className="text-emerald-400/60">Every change is traced.</span>
                  </h3>
                  </div>
                <ul className="space-y-3">
                  {[
                    'Locked snapshots are immutable (inputs + outputs frozen)',
                    'Canonical ID deduplication: 10-component fingerprint per row',
                    'Comprehensive audit logging: snapshot locks, match approvals, lever executions',
                    'Unknown bucket drilldown with severity categories',
                  ].map((item, i) => (
                    <li key={i} className="flex items-start gap-3 text-white/60">
                      <ApprovalStampIcon className="w-5 h-5 text-purple-500 mt-0.5 flex-shrink-0" />
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
                <div className="pt-4 border-t border-white/10">
                  <p className="text-xs text-white/40">
                    <span className="font-semibold text-white/60">Under the hood:</span> UNIQUE(snapshot_id, canonical_id) at DB level. Data lineage: SnapshotID, ImportBatchID, FX table version.
                  </p>
                     </div>
                  </div>
              <div className="pb-16">
                <WorkersVisualFrame badge="Analyzing Variance" glowColor="purple">
                  <VarianceNarrativesVisual />
                </WorkersVisualFrame>
              </div>
            </div>

            {/* ═══════════════════════════════════════════════════════════════════ */}
            {/* MEET LIQUIDITY LEVERS */}
            {/* ═══════════════════════════════════════════════════════════════════ */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-16 items-center relative group">
              {/* Subtle gradient background */}
              <div className="absolute -inset-8 bg-gradient-to-br from-rose-500/5 via-transparent to-pink-500/5 rounded-3xl opacity-0 group-hover:opacity-100 transition-all duration-700 -z-10" />
              
              <div className="order-2 lg:order-1 transform group-hover:scale-[1.02] transition-transform duration-500 pb-16">
                <WorkersVisualFrame badge="Adjusting Levers" glowColor="rose">
                  <LiquidityLeversVisual />
                </WorkersVisualFrame>
              </div>
              <div className="order-1 lg:order-2 space-y-6">
                <div>
                  <span className="inline-block px-3 py-1 bg-rose-500/10 border border-rose-500/20 rounded-full text-[11px] font-semibold text-rose-400 uppercase tracking-wide mb-4 group-hover:bg-rose-500/20 transition-colors duration-300">
                    Meet Liquidity Levers
                  </span>
                  <h3 className="text-2xl font-bold text-white leading-tight">
                    What-if scenarios,<br />
                    <span className="text-emerald-400/60">with role-based control.</span>
                  </h3>
               </div>
                <ul className="space-y-3">
                  {[
                    'Vendor payment delay slider with real-time grid impact',
                    'What-if scenarios cascade through 13-week forecast',
                    'Every lever execution logged for audit trail',
                    'Role-based access control (CFO / FP&A / Ops)',
                  ].map((item, i) => (
                    <li key={i} className="flex items-start gap-3 text-white/60">
                      <ApprovalStampIcon className="w-5 h-5 text-rose-500 mt-0.5 flex-shrink-0" />
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
                <div className="pt-4 border-t border-white/10">
                  <p className="text-xs text-white/40">
                    <span className="font-semibold text-white/60">Under the hood:</span> TreasuryAction and LeverPolicy models. RBAC enforces who can simulate vs. who can execute.
                  </p>
                </div>
               </div>
            </div>

            {/* ═══════════════════════════════════════════════════════════════════ */}
            {/* MEET MULTI-ENTITY & FX */}
            {/* ═══════════════════════════════════════════════════════════════════ */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-16 items-center relative group">
              {/* Subtle gradient background */}
              <div className="absolute -inset-8 bg-gradient-to-bl from-cyan-500/5 via-transparent to-sky-500/5 rounded-3xl opacity-0 group-hover:opacity-100 transition-all duration-700 -z-10" />
              
              <div className="space-y-6">
                <div>
                  <span className="inline-block px-3 py-1 bg-cyan-500/10 border border-cyan-500/20 rounded-full text-[11px] font-semibold text-cyan-400 uppercase tracking-wide mb-4 group-hover:bg-cyan-500/20 transition-colors duration-300">
                    Meet Multi-Entity & FX
                  </span>
                  <h3 className="text-2xl font-bold text-white leading-tight">
                    Global treasury,<br />
                    <span className="text-emerald-400/60">zero silent assumptions.</span>
                  </h3>
                  </div>
                <ul className="space-y-3">
                  {[
                    'Entity base currency enforced at ingestion',
                    'FX rates snapshot-locked and versioned per week',
                    'Intercompany wash detection with approval flow',
                    'Secrets never stored plaintext (env var retrieval)',
                  ].map((item, i) => (
                    <li key={i} className="flex items-start gap-3 text-white/60">
                      <ApprovalStampIcon className="w-5 h-5 text-cyan-500 mt-0.5 flex-shrink-0" />
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
                <div className="pt-4 border-t border-white/10">
                  <p className="text-xs text-white/40">
                    <span className="font-semibold text-white/60">Under the hood:</span> WeeklyFXRate linked to snapshot. convert_currency() uses locked rates. No plaintext secrets in DB.
                  </p>
                     </div>
                  </div>
              <div className="pb-16">
                <WorkersVisualFrame badge="Warehouse Mode" glowColor="emerald">
                  <WarehouseModeVisual />
                </WorkersVisualFrame>
              </div>
                  </div>
            
               </div>
            </div>
      </section>


      {/* ─────────────────────────────────────────────────────────────────────── */}
      {/* SECTION 9: CORE GUARANTEES - Workers.io Style */}
      {/* ─────────────────────────────────────────────────────────────────────── */}
      <section id="trust" className="py-32 px-6 bg-[#0A0A0F] relative overflow-hidden section-premium">
        {/* Noise textures */}
        <div className="noise-layer-1" />
        <div className="noise-layer-2" />
        
        {/* Multi-layer glows */}
        <div className="absolute top-0 left-1/3 w-[600px] h-[500px] bg-gradient-radial from-emerald-600/20 via-emerald-900/10 to-transparent blur-3xl pointer-events-none" />
        <div className="absolute bottom-0 right-1/3 w-[600px] h-[500px] bg-gradient-radial from-purple-600/20 via-purple-900/10 to-transparent blur-3xl pointer-events-none" />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[1000px] h-[600px] bg-gradient-radial from-amber-900/10 via-transparent to-transparent blur-3xl pointer-events-none" />
        
        <div className="max-w-6xl mx-auto relative z-10">
          <div className="text-center mb-20">
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-emerald-500/10 border border-emerald-500/20 mb-6">
              <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              <span className="text-xs font-semibold text-emerald-400 uppercase tracking-[0.15em]">Our Guarantees</span>
            </div>
            <h2 className="headline-solcoa text-4xl md:text-5xl text-gradient-fade-dark mb-4">What we promise</h2>
            <p className="text-lg text-white/40">Non-negotiable behaviors built into every feature</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            {[
              { 
                title: 'Every number explains itself', 
                desc: 'Click any cell in the 13-week grid and drill down to the exact invoices and transactions that produced it. No black boxes.',
                icon: <AuditLogIcon className="w-7 h-7" />,
                glowColor: 'emerald',
                badge: 'Transparent'
              },
              { 
                title: 'Uncertain data is never hidden', 
                desc: 'Missing FX rates, stale bank feeds, or unmatched transactions route to an explicit Unknown bucket—never silently assumed.',
                icon: <RedWeekIcon className="w-7 h-7" />,
                glowColor: 'amber',
                badge: 'Honest'
              },
              { 
                title: 'Locked snapshots are immutable', 
                desc: 'Once you lock a weekly snapshot, the inputs and outputs freeze. Reproduce any past state for audit or comparison.',
                icon: <ApprovalStampIcon className="w-7 h-7" />,
                glowColor: 'cyan',
                badge: 'Immutable'
              },
              { 
                title: 'Suggested matches require approval', 
                desc: 'Tier 1 and 2 matches auto-clear. Tier 3 fuzzy matches show confidence scores and require human approval before applying.',
                icon: <MatchIcon className="w-7 h-7" />,
                glowColor: 'purple',
                badge: 'Controlled'
              },
            ].map((item, i) => {
              const colors = {
                emerald: { bg: 'from-emerald-500/15 via-emerald-600/5', icon: 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400', text: 'text-emerald-400', glow: 'from-emerald-900/30', badge: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30' },
                amber: { bg: 'from-amber-500/15 via-amber-600/5', icon: 'bg-amber-500/10 border-amber-500/30 text-amber-400', text: 'text-amber-400', glow: 'from-amber-900/30', badge: 'bg-amber-500/10 text-amber-400 border-amber-500/30' },
                cyan: { bg: 'from-cyan-500/15 via-cyan-600/5', icon: 'bg-cyan-500/10 border-cyan-500/30 text-cyan-400', text: 'text-cyan-400', glow: 'from-cyan-900/30', badge: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30' },
                purple: { bg: 'from-purple-500/15 via-purple-600/5', icon: 'bg-purple-500/10 border-purple-500/30 text-purple-400', text: 'text-purple-400', glow: 'from-purple-900/30', badge: 'bg-purple-500/10 text-purple-400 border-purple-500/30' },
              };
              const c = colors[item.glowColor as keyof typeof colors];
              
              return (
                <div key={i} className="relative group">
                  {/* Card glow on hover */}
                  <div className={`absolute -inset-1 bg-gradient-to-b ${c.bg} to-transparent rounded-2xl blur-xl opacity-0 group-hover:opacity-100 transition-opacity duration-500`} />
                  
                  {/* Corner brackets */}
                  <div className="absolute -top-1 -left-1 w-3 h-3 border-l-2 border-t-2 border-white/20 pointer-events-none" />
                  <div className="absolute -top-1 -right-1 w-3 h-3 border-r-2 border-t-2 border-white/20 pointer-events-none" />
                  <div className="absolute -bottom-1 -left-1 w-3 h-3 border-l-2 border-b-2 border-white/20 pointer-events-none" />
                  <div className="absolute -bottom-1 -right-1 w-3 h-3 border-r-2 border-b-2 border-white/20 pointer-events-none" />
                  
                  <div className="relative bg-[#0D0D14] border border-white/10 rounded-xl p-8 h-full overflow-hidden group-hover:border-white/20 transition-all duration-300">
                    {/* Noise overlay */}
                    <div 
                      className="absolute inset-0 pointer-events-none mix-blend-overlay"
                      style={{ 
                        opacity: 0.1,
                        backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.8' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E")`
                      }}
                    />
                    
                    {/* Inner glow at bottom */}
                    <div className={`absolute bottom-0 left-0 right-0 h-20 bg-gradient-to-t ${c.glow} to-transparent pointer-events-none`} />
                    
                    <div className="relative z-10 flex items-start gap-5">
                      <div className={`h-14 w-14 rounded-xl ${c.icon} border flex items-center justify-center shrink-0 group-hover:scale-110 transition-transform duration-300`}>
                        {item.icon}
                      </div>
                      <div className="flex-1">
                        <div className={`text-xl font-bold ${c.text} mb-3`}>{item.title}</div>
                        <div className="text-sm text-white/50 leading-relaxed">{item.desc}</div>
                      </div>
                    </div>
                    
                    {/* Badge */}
                    <div className="absolute top-4 right-4">
                      <div className={`px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider rounded ${c.badge} border`}>
                        {item.badge}
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* ─────────────────────────────────────────────────────────────────────── */}
      {/* SECTION 10: INTEGRATIONS - REIMAGINED */}
      {/* ─────────────────────────────────────────────────────────────────────── */}
      <section id="integrations" className="py-32 px-6 bg-[#0A0A0F] relative overflow-hidden section-premium">
        {/* Workers.io-style noise textures */}
        <div className="noise-layer-1" />
        <div className="noise-layer-2" />
        
        {/* Animated gradient orbs */}
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <div className="absolute top-0 left-1/4 w-[600px] h-[600px] bg-gradient-to-br from-emerald-500/10 via-teal-500/5 to-transparent rounded-full blur-3xl animate-float-slow" />
          <div className="absolute bottom-0 right-1/4 w-[500px] h-[500px] bg-gradient-to-br from-blue-500/10 via-cyan-500/5 to-transparent rounded-full blur-3xl animate-float" style={{ animationDelay: '-3s' }} />
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[400px] bg-gradient-to-r from-violet-500/5 via-transparent to-rose-500/5 rounded-full blur-3xl" />
          
          {/* Moody burgundy glow */}
          <div className="absolute bottom-0 left-1/2 -translate-x-1/2 w-[900px] h-[350px] bg-gradient-radial from-rose-900/20 via-rose-950/10 to-transparent blur-3xl" />
        </div>

        <div className="max-w-6xl mx-auto relative">
          {/* Hero-style header */}
          <div className="text-center mb-20">
            <div className="inline-flex items-center gap-3 px-4 py-2 rounded-full bg-white/5 border border-white/10 mb-8">
              <div className="flex -space-x-1">
                <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                <div className="w-2 h-2 rounded-full bg-blue-400 animate-pulse" style={{ animationDelay: '0.2s' }} />
                <div className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" style={{ animationDelay: '0.4s' }} />
              </div>
              <span className="text-xs font-medium text-white/60 tracking-wide">Live data connections</span>
            </div>
            <h2 className="headline-solcoa text-4xl md:text-5xl lg:text-6xl text-gradient-fade-dark mb-6">
              Your entire finance stack,<br />unified.
            </h2>
            <p className="text-lg text-white/40 max-w-2xl mx-auto">
              Bank feeds, ERPs, and warehouses flow into a single source of cash truth.
            </p>
          </div>

          {/* Visual Pipeline - The Star of the Show */}
          <div className="relative mb-20">
            {/* Animated connection line */}
            <div className="absolute top-1/2 left-0 right-0 h-px bg-gradient-to-r from-transparent via-white/10 to-transparent -translate-y-1/2 z-0" />
            <div className="absolute top-1/2 left-0 right-0 h-px -translate-y-1/2 z-0 overflow-hidden">
              <div className="h-full w-32 bg-gradient-to-r from-transparent via-emerald-400/50 to-transparent animate-data-stream" />
            </div>

            <div className="flex items-center justify-between relative z-10">
              {/* Source: Banks */}
              <div className="flex flex-col items-center group">
                <div className="relative">
                  <div className="absolute inset-0 bg-emerald-500/20 rounded-2xl blur-xl group-hover:bg-emerald-500/30 transition-all duration-500" />
                  <div className="relative h-24 w-24 rounded-2xl bg-gradient-to-br from-emerald-500/20 to-emerald-600/10 border border-emerald-500/30 flex items-center justify-center group-hover:scale-110 group-hover:border-emerald-400/50 transition-all duration-500">
                    <BankStatementIcon className="w-10 h-10 text-emerald-400" />
                  </div>
                  <div className="absolute -bottom-1 -right-1 w-4 h-4 rounded-full bg-emerald-400 border-2 border-[#0A0A0F] animate-pulse" />
                </div>
                <div className="mt-4 text-center">
                  <div className="font-bold text-white text-sm">Banks</div>
                  <div className="text-[10px] text-white/40 mt-1">Plaid • Nordigen • MT940</div>
                </div>
              </div>

              {/* Source: ERP */}
              <div className="flex flex-col items-center group">
                <div className="relative">
                  <div className="absolute inset-0 bg-blue-500/20 rounded-2xl blur-xl group-hover:bg-blue-500/30 transition-all duration-500" />
                  <div className="relative h-24 w-24 rounded-2xl bg-gradient-to-br from-blue-500/20 to-blue-600/10 border border-blue-500/30 flex items-center justify-center group-hover:scale-110 group-hover:border-blue-400/50 transition-all duration-500">
                    <InvoiceIcon className="w-10 h-10 text-blue-400" />
                  </div>
                  <div className="absolute -bottom-1 -right-1 w-4 h-4 rounded-full bg-blue-400 border-2 border-[#0A0A0F] animate-pulse" style={{ animationDelay: '0.3s' }} />
                </div>
                <div className="mt-4 text-center">
                  <div className="font-bold text-white text-sm">ERP</div>
                  <div className="text-[10px] text-white/40 mt-1">SAP • NetSuite • QuickBooks</div>
                </div>
              </div>

              {/* Center: Gitto Engine - The Hero */}
              <div className="flex flex-col items-center group relative">
                <div className="absolute inset-0 -m-8">
                  <div className="absolute inset-0 bg-gradient-to-r from-emerald-500/10 via-white/5 to-cyan-500/10 rounded-3xl blur-2xl animate-pulse" style={{ animationDuration: '3s' }} />
                </div>
                <div className="relative">
                  <div className="h-32 w-32 rounded-3xl bg-white flex items-center justify-center group-hover:scale-105 transition-all duration-500 shadow-2xl shadow-white/10">
                    <div className="text-center">
                      <span className="text-3xl font-serif font-bold text-[#0A0A0F]">G</span>
                    </div>
                  </div>
                  <div className="absolute -inset-2 rounded-[28px] border border-white/20 animate-pulse" style={{ animationDuration: '2s' }} />
                </div>
                <div className="mt-4 text-center">
                  <div className="font-bold text-white">Gitto Engine</div>
                  <div className="text-[10px] text-emerald-400 mt-1 font-medium">Match • Forecast • Explain</div>
                </div>
              </div>

              {/* Output: 13-Week */}
              <div className="flex flex-col items-center group">
                <div className="relative">
                  <div className="absolute inset-0 bg-amber-500/20 rounded-2xl blur-xl group-hover:bg-amber-500/30 transition-all duration-500" />
                  <div className="relative h-24 w-24 rounded-2xl bg-gradient-to-br from-amber-500/20 to-amber-600/10 border border-amber-500/30 flex items-center justify-center group-hover:scale-110 group-hover:border-amber-400/50 transition-all duration-500">
                    <PaymentRunIcon className="w-10 h-10 text-amber-400" />
                  </div>
                </div>
                <div className="mt-4 text-center">
                  <div className="font-bold text-white text-sm">13-Week</div>
                  <div className="text-[10px] text-white/40 mt-1">Forecast Grid</div>
                </div>
              </div>

              {/* Output: Warehouse */}
              <div className="flex flex-col items-center group">
                <div className="relative">
                  <div className="absolute inset-0 bg-cyan-500/20 rounded-2xl blur-xl group-hover:bg-cyan-500/30 transition-all duration-500" />
                  <div className="relative h-24 w-24 rounded-2xl bg-gradient-to-br from-cyan-500/20 to-cyan-600/10 border border-cyan-500/30 flex items-center justify-center group-hover:scale-110 group-hover:border-cyan-400/50 transition-all duration-500">
                    <WarehouseIcon className="w-10 h-10 text-cyan-400" />
                  </div>
                  <div className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-cyan-400 border-2 border-[#0A0A0F]">
                    <ArrowRightIcon className="w-2 h-2 text-[#0A0A0F] m-0.5" />
                  </div>
                </div>
                <div className="mt-4 text-center">
                  <div className="font-bold text-white text-sm">Warehouse</div>
                  <div className="text-[10px] text-white/40 mt-1">Snowflake • BigQuery</div>
                </div>
              </div>
            </div>
          </div>

          {/* Integration logos grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { name: 'Plaid', category: 'US/Canada Banks' },
              { name: 'Nordigen', category: 'EU/UK Banks' },
              { name: 'SAP S/4HANA', category: 'ERP' },
              { name: 'NetSuite', category: 'ERP' },
              { name: 'Snowflake', category: 'Warehouse' },
              { name: 'QuickBooks', category: 'Accounting' },
              { name: 'Xero', category: 'Accounting' },
              { name: 'BigQuery', category: 'Warehouse' },
            ].map((integration, i) => (
              <div 
                key={i} 
                className="group bg-white/[0.02] hover:bg-white/[0.05] border border-white/5 hover:border-white/10 rounded-xl px-4 py-3 transition-all duration-300 cursor-default"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <div className="font-medium text-white/80 text-sm group-hover:text-white transition-colors">{integration.name}</div>
                    <div className="text-[10px] text-white/30">{integration.category}</div>
                  </div>
                  <div className="w-2 h-2 rounded-full bg-emerald-400/50 group-hover:bg-emerald-400 transition-colors" />
                </div>
              </div>
            ))}
          </div>

          {/* Technical Architecture Cards */}
          <div className="mt-16 grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="group bg-gradient-to-br from-emerald-500/5 to-transparent border border-emerald-500/10 rounded-2xl p-6 hover:border-emerald-500/20 transition-all duration-300">
              <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center mb-4">
                <svg className="w-5 h-5 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16V4m0 0L3 8m4-4l4 4m6 0v12m0 0l4-4m-4 4l-4-4" />
                </svg>
              </div>
              <h4 className="font-bold text-white mb-2">Connector SDK</h4>
              <p className="text-xs text-white/40 leading-relaxed">
                Unified interface for all data sources. Test → Extract → Normalize → Load with incremental sync, cursor-based pulls, and idempotent upserts.
              </p>
            </div>
            
            <div className="group bg-gradient-to-br from-blue-500/5 to-transparent border border-blue-500/10 rounded-2xl p-6 hover:border-blue-500/20 transition-all duration-300">
              <div className="w-10 h-10 rounded-xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center mb-4">
                <svg className="w-5 h-5 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                </svg>
              </div>
              <h4 className="font-bold text-white mb-2">Canonical Identity</h4>
              <p className="text-xs text-white/40 leading-relaxed">
                Stable fingerprints, source-native IDs, DB constraints (UNIQUE snapshot + canonical_id). Dataset versioning with checksums and lineage.
              </p>
            </div>
            
            <div className="group bg-gradient-to-br from-amber-500/5 to-transparent border border-amber-500/10 rounded-2xl p-6 hover:border-amber-500/20 transition-all duration-300">
              <div className="w-10 h-10 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center mb-4">
                <svg className="w-5 h-5 text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <h4 className="font-bold text-white mb-2">Data Freshness</h4>
              <p className="text-xs text-white/40 leading-relaxed">
                Per-source staleness monitoring. Bank vs ERP age mismatch detection. Auto-alert when thresholds exceeded. Lock validation before snapshots.
              </p>
            </div>
          </div>

          {/* Bottom tagline */}
          <div className="mt-12 text-center">
            <p className="text-sm text-white/30">
              <span className="text-white/50">10 live connectors</span> • <span className="text-white/50">Official SDKs</span> • <span className="text-white/50">Bi-directional warehouse sync</span>
            </p>
          </div>
        </div>
      </section>

      {/* ─────────────────────────────────────────────────────────────────────── */}
      {/* SECTION 11: SECURITY & AUDITABILITY - Workers.io Style */}
      {/* ─────────────────────────────────────────────────────────────────────── */}
      <section className="py-32 px-6 bg-[#0A0A0F] relative overflow-hidden section-premium">
        {/* Noise textures */}
        <div className="noise-layer-1" />
        <div className="noise-layer-2" />
        
        {/* Cyan/blue glow at top */}
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[400px] bg-gradient-radial from-cyan-600/20 via-blue-900/10 to-transparent blur-3xl pointer-events-none" />
        
        {/* Moody purple glow at bottom */}
        <div className="absolute bottom-0 left-1/2 -translate-x-1/2 w-[900px] h-[350px] bg-gradient-radial from-purple-900/25 via-indigo-950/15 to-transparent blur-3xl pointer-events-none" />
        
        <div className="max-w-6xl mx-auto relative z-10">
          <div className="text-center mb-16">
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-cyan-500/10 border border-cyan-500/20 mb-6">
              <div className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
              <span className="text-xs font-semibold text-cyan-400 uppercase tracking-[0.15em]">Security & Auditability</span>
            </div>
            <h2 className="headline-solcoa text-4xl md:text-5xl text-gradient-fade-dark mb-4">Audit-friendly by design</h2>
            <p className="text-lg text-white/40 max-w-2xl mx-auto">We don't claim what we don't have. Here's what we actually built.</p>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {[
              { 
                icon: <AuditLogIcon className="w-7 h-7" />,
                title: 'Immutable Snapshots', 
                desc: 'Every weekly snapshot is version-locked. Replay any point-in-time view for audit. No silent overwrites.',
                color: 'cyan',
                badge: 'Versioned'
              },
              { 
                icon: <ApprovalStampIcon className="w-7 h-7" />,
                title: 'Approval Logs', 
                desc: 'Every match approval, lever change, and manual override is logged with user, timestamp, and rationale.',
                color: 'purple',
                badge: 'Tracked'
              },
              { 
                icon: <MatchIcon className="w-7 h-7" />,
                title: 'Full Lineage', 
                desc: 'Trace any forecast number back to the source bank transaction and invoice. Citation links throughout.',
                color: 'emerald',
                badge: 'Traceable'
              },
            ].map((item, i) => (
              <div key={i} className="relative group">
                {/* Card glow */}
                <div className={`absolute -inset-1 bg-gradient-to-b ${
                  item.color === 'cyan' ? 'from-cyan-500/20 via-cyan-600/5' : 
                  item.color === 'purple' ? 'from-purple-500/20 via-purple-600/5' : 
                  'from-emerald-500/20 via-emerald-600/5'
                } to-transparent rounded-2xl blur-xl opacity-0 group-hover:opacity-100 transition-opacity duration-500`} />
                
                {/* Corner brackets */}
                <div className="absolute -top-1 -left-1 w-3 h-3 border-l-2 border-t-2 border-white/20 pointer-events-none" />
                <div className="absolute -top-1 -right-1 w-3 h-3 border-r-2 border-t-2 border-white/20 pointer-events-none" />
                <div className="absolute -bottom-1 -left-1 w-3 h-3 border-l-2 border-b-2 border-white/20 pointer-events-none" />
                <div className="absolute -bottom-1 -right-1 w-3 h-3 border-r-2 border-b-2 border-white/20 pointer-events-none" />
                
                <div className="relative bg-[#0D0D14] border border-white/10 rounded-xl p-8 h-full overflow-hidden group-hover:border-white/20 transition-all duration-300">
                  {/* Noise overlay on card */}
                  <div 
                    className="absolute inset-0 pointer-events-none mix-blend-overlay"
                    style={{ 
                      opacity: 0.1,
                      backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.8' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E")`
                    }}
                  />
                  
                  {/* Inner glow at bottom */}
                  <div className={`absolute bottom-0 left-0 right-0 h-20 bg-gradient-to-t ${
                    item.color === 'cyan' ? 'from-cyan-900/20' : 
                    item.color === 'purple' ? 'from-purple-900/20' : 
                    'from-emerald-900/20'
                  } to-transparent pointer-events-none`} />
                  
                  <div className="relative z-10">
                    <div className={`h-14 w-14 rounded-xl ${
                      item.color === 'cyan' ? 'bg-cyan-500/10 border-cyan-500/30 text-cyan-400' : 
                      item.color === 'purple' ? 'bg-purple-500/10 border-purple-500/30 text-purple-400' : 
                      'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
                    } border flex items-center justify-center mb-6 group-hover:scale-110 transition-transform duration-300`}>
                      {item.icon}
                    </div>
                    <div className="font-bold text-white text-lg mb-3">{item.title}</div>
                    <div className="text-sm text-white/50 leading-relaxed">{item.desc}</div>
                  </div>
                  
                  {/* Badge at bottom right */}
                  <div className="absolute bottom-4 right-4">
                    <div className={`px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider rounded ${
                      item.color === 'cyan' ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/30' : 
                      item.color === 'purple' ? 'bg-purple-500/10 text-purple-400 border border-purple-500/30' : 
                      'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30'
                    }`}>
                      {item.badge}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
          
          <div className="mt-16 text-center">
            <div className="inline-flex items-center gap-4 px-6 py-3 rounded-xl bg-white/5 border border-white/10">
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                <span className="text-sm font-medium text-white/70">SOC 2 Type II certification in progress</span>
              </div>
              <div className="w-px h-4 bg-white/20" />
              <span className="text-sm text-white/40">Enterprise SSO • Self-hosted option</span>
            </div>
          </div>
        </div>
      </section>

      {/* ─────────────────────────────────────────────────────────────────────── */}
      {/* FINAL CTA - Workers.io Premium Style */}
      {/* ─────────────────────────────────────────────────────────────────────── */}
      <section className="py-40 px-6 bg-[#070709] relative overflow-hidden">
        {/* Noise textures */}
        <div className="noise-layer-1" />
        <div className="noise-layer-2" />
        
        {/* Multiple glow layers for depth */}
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[1200px] h-[600px] bg-gradient-radial from-rose-900/30 via-rose-950/15 to-transparent blur-3xl pointer-events-none" />
        <div className="absolute bottom-0 left-1/4 w-[600px] h-[400px] bg-gradient-radial from-purple-900/20 via-purple-950/10 to-transparent blur-3xl pointer-events-none" />
        <div className="absolute bottom-0 right-1/4 w-[600px] h-[400px] bg-gradient-radial from-cyan-900/15 via-cyan-950/8 to-transparent blur-3xl pointer-events-none" />
        
        {/* Animated line at top */}
        <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-white/10 to-transparent" />
        
        {/* Corner brackets for the section */}
        <div className="absolute top-8 left-8 w-12 h-12 border-l-2 border-t-2 border-white/10 pointer-events-none" />
        <div className="absolute top-8 right-8 w-12 h-12 border-r-2 border-t-2 border-white/10 pointer-events-none" />
        <div className="absolute bottom-8 left-8 w-12 h-12 border-l-2 border-b-2 border-white/10 pointer-events-none" />
        <div className="absolute bottom-8 right-8 w-12 h-12 border-r-2 border-b-2 border-white/10 pointer-events-none" />
        
        <div className="max-w-4xl mx-auto text-center relative z-20">
          {/* Glowing orb above text */}
          <div className="flex justify-center mb-12">
            <div className="relative w-20 h-20">
              <div className="absolute -inset-8 rounded-full bg-gradient-radial from-rose-500/30 via-purple-600/15 to-transparent blur-2xl" />
              <div className="absolute inset-0 rounded-full bg-gradient-radial from-rose-500/50 via-purple-600/30 to-transparent blur-lg animate-pulse" style={{ animationDuration: '3s' }} />
              <div className="absolute inset-2 rounded-full bg-gradient-radial from-orange-400/60 via-rose-500/40 to-purple-600/20 blur-sm" />
              <div className="absolute inset-4 rounded-full bg-gradient-radial from-yellow-200/80 via-orange-400/60 to-rose-500/30" />
              <div className="absolute inset-6 rounded-full bg-gradient-radial from-white/70 via-yellow-200/50 to-transparent" />
            </div>
          </div>
          
          <h2 className="headline-solcoa text-4xl md:text-5xl lg:text-6xl text-gradient-fade-dark mb-6 leading-tight">
            Ready to run your Monday cash meeting with actual bank truth?
          </h2>
          <p className="text-xl text-white/40 mb-12 max-w-2xl mx-auto">
            Book a demo to see the 13-week workspace with your data.
          </p>
          
          <div className="flex items-center justify-center gap-6">
            <Link href="/app">
              <button className="button-glow relative group">
                <div className="relative bg-white text-[#0A0A0F] h-14 px-10 text-base font-semibold rounded-xl flex items-center gap-3 group-hover:-translate-y-1 transition-all shadow-xl">
                  Book a Demo
                  <ArrowRightIcon className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
                </div>
              </button>
            </Link>
            <Link href="/contact">
              <button className="button-glow-secondary relative h-14 px-8 text-base font-medium text-white/70 hover:text-white border-2 border-white/20 rounded-xl hover:bg-white/5 hover:border-white/40 transition-all hover:-translate-y-1">
                Contact Sales
              </button>
            </Link>
          </div>
          
          {/* Trust indicators */}
          <div className="mt-16 flex items-center justify-center gap-8 text-sm text-white/30">
            <div className="flex items-center gap-2">
              <div className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
              <span>No credit card required</span>
            </div>
            <div className="w-px h-4 bg-white/10" />
            <div className="flex items-center gap-2">
              <div className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
              <span>15-minute demo</span>
            </div>
            <div className="w-px h-4 bg-white/10" />
            <div className="flex items-center gap-2">
              <div className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
              <span>See your own data</span>
            </div>
          </div>
        </div>
      </section>

      {/* ─────────────────────────────────────────────────────────────────────── */}
      {/* FOOTER */}
      {/* ─────────────────────────────────────────────────────────────────────── */}
      <footer className="py-16 px-6 bg-[#070709] border-t border-white/5 relative overflow-hidden">
        {/* Subtle ambient glow */}
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[600px] h-[200px] bg-gradient-to-b from-emerald-500/[0.03] to-transparent rounded-full blur-3xl" />
        </div>
        <div className="max-w-6xl mx-auto relative">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8 mb-12">
            <div>
              <div className="flex items-center gap-3 mb-4">
                <div className="h-9 w-9 rounded-xl bg-white flex items-center justify-center text-slate-900 font-serif font-bold text-lg">G</div>
                <span className="font-semibold text-lg text-white">Gitto</span>
              </div>
              <p className="text-sm text-white/50 leading-relaxed">
                Bank-truth cash forecasting<br />for finance teams.
              </p>
            </div>
            <div>
              <div className="text-xs font-semibold text-white/30 uppercase tracking-wider mb-4">Product</div>
              <ul className="space-y-2.5 text-sm text-white/50">
                <li><a href="#" className="hover:text-white transition-colors">Bank Truth</a></li>
                <li><a href="#" className="hover:text-white transition-colors">Reconciliation</a></li>
                <li><a href="#" className="hover:text-white transition-colors">13-Week Workspace</a></li>
                <li><a href="#" className="hover:text-white transition-colors">Variance Narratives</a></li>
              </ul>
          </div>
            <div>
              <div className="text-xs font-semibold text-white/30 uppercase tracking-wider mb-4">Company</div>
              <ul className="space-y-2.5 text-sm text-white/50">
                <li><Link href="/about" className="hover:text-white transition-colors">About</Link></li>
                <li><Link href="/contact" className="hover:text-white transition-colors">Contact</Link></li>
                <li><a href="#" className="hover:text-white transition-colors">Careers</a></li>
            </ul>
          </div>
            <div>
              <div className="text-xs font-semibold text-white/30 uppercase tracking-wider mb-4">Legal</div>
              <ul className="space-y-2.5 text-sm text-white/50">
                <li><a href="#" className="hover:text-white transition-colors">Privacy</a></li>
                <li><a href="#" className="hover:text-white transition-colors">Terms</a></li>
                <li><a href="#" className="hover:text-white transition-colors">Security</a></li>
            </ul>
          </div>
          </div>
          <div className="pt-8 border-t border-white/10 flex items-center justify-between text-xs text-white/30">
            <span>© {new Date().getFullYear()} Gitto Intelligence Inc.</span>
            <span>info@gitto.ai</span>
        </div>
        </div>
      </footer>
    </div>
  );
}
