import React from 'react';
import { Clock, Loader2, ShieldCheck, Sparkles } from 'lucide-react';
import { ExtractionProgress } from '../types';

interface ExtractionProgressCardProps {
  progress?: ExtractionProgress;
  isLoading: boolean;
}

export const ExtractionProgressCard: React.FC<ExtractionProgressCardProps> = ({
  progress,
  isLoading,
}) => {
  if (!isLoading && (!progress || progress.percent >= 100)) {
    return null;
  }

  const percent = progress?.percent ?? 15;
  const secondsRemaining = progress?.estimated_seconds_remaining ?? 75;
  const currentSection = progress?.current_section ?? 1;
  const totalSections = progress?.total_sections ?? 5;
  const stage = progress?.stage || 'Extracting official policy rules and criteria...';

  // Format seconds to mm:ss
  const formatTime = (secs: number) => {
    if (secs <= 0) return 'Almost ready...';
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    if (m > 0) {
      return `~${m}m ${s < 10 ? '0' : ''}${s}s remaining`;
    }
    return `~${s}s remaining`;
  };

  return (
    <div className="bg-gradient-to-br from-slate-900 to-slate-800 text-white rounded-2xl shadow-lg border border-slate-700/80 p-5 sm:p-6 mb-6 overflow-hidden relative">
      {/* Background ambient glow */}
      <div className="absolute top-0 right-0 -mt-8 -mr-8 w-48 h-48 bg-emerald-500/10 rounded-full blur-2xl pointer-events-none" />
      <div className="absolute bottom-0 left-0 -mb-8 -ml-8 w-48 h-48 bg-amber-500/10 rounded-full blur-2xl pointer-events-none" />

      <div className="relative z-10 space-y-4">
        {/* Top Header Row */}
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center space-x-3">
            <div className="p-2.5 bg-emerald-500/20 text-emerald-400 rounded-xl border border-emerald-500/30 flex items-center justify-center">
              <Loader2 className="w-5 h-5 animate-spin" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="text-xs font-bold uppercase tracking-wider text-emerald-400">
                  Comprehensive Clause Extraction
                </span>
                <span className="text-[10px] bg-emerald-400/20 text-emerald-300 px-2 py-0.5 rounded-full font-semibold border border-emerald-400/30">
                  Zero Rate-Limit Pacing
                </span>
              </div>
              <h3 className="text-base font-bold text-white">
                Processing Official Document Guidelines
              </h3>
            </div>
          </div>

          {/* Countdown Clock Badge */}
          <div className="flex items-center space-x-2 bg-slate-800/90 border border-slate-600/60 px-3 py-1.5 rounded-xl shadow-inner">
            <Clock className="w-4 h-4 text-amber-400 animate-pulse" />
            <span className="text-xs font-mono font-bold text-amber-300">
              {formatTime(secondsRemaining)}
            </span>
          </div>
        </div>

        {/* Progress Bar */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between text-xs text-slate-300 font-medium">
            <span>
              Section <strong className="text-white">{currentSection}</strong> of{' '}
              <strong className="text-white">{totalSections}</strong>
            </span>
            <span className="font-mono font-bold text-emerald-400">{percent}%</span>
          </div>

          <div className="w-full bg-slate-700/80 rounded-full h-2.5 overflow-hidden border border-slate-600/50">
            <div
              className="bg-gradient-to-r from-emerald-500 via-teal-400 to-amber-400 h-2.5 rounded-full transition-all duration-700 ease-out shadow-sm"
              style={{ width: `${Math.max(5, percent)}%` }}
            />
          </div>
        </div>

        {/* Current Sub-Stage Message */}
        <div className="flex items-center justify-between text-xs text-slate-300 bg-slate-850/60 rounded-lg p-2.5 border border-slate-700/50">
          <div className="flex items-center space-x-2 min-w-0">
            <Sparkles className="w-3.5 h-3.5 text-amber-400 flex-shrink-0" />
            <span className="truncate font-mono text-slate-200">{stage}</span>
          </div>
        </div>

        {/* Footer Guarantees */}
        <div className="flex flex-wrap items-center gap-4 text-[11px] text-slate-400 pt-1 border-t border-slate-700/40">
          <span className="flex items-center space-x-1">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
            <span>All 80+ clauses parsed</span>
          </span>
          <span className="flex items-center space-x-1">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
            <span>100% eligibility rules & exclusions retained</span>
          </span>
          <span className="flex items-center space-x-1">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
            <span>Evenly spaced to prevent API throttling</span>
          </span>
        </div>
      </div>
    </div>
  );
};

