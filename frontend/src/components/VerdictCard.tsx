import React from 'react';
import { CheckCircle, XCircle, AlertCircle, ArrowRight, ShieldCheck, Printer } from 'lucide-react';
import { Verdict, Reason } from '../types';

interface VerdictCardProps {
  verdict?: Verdict;
}

export const VerdictCard: React.FC<VerdictCardProps> = ({ verdict }) => {
  if (!verdict) return null;

  const isYes = verdict.status === 'YES';
  const isNo = verdict.status === 'NO';
  const isMaybe = verdict.status === 'MAYBE';

  return (
    <div
      className={`rounded-2xl border-2 p-6 mb-6 shadow-sm transition-all ${
        isYes
          ? 'bg-gradient-to-br from-emerald-500/10 via-emerald-500/5 to-transparent border-emerald-500/40'
          : isNo
          ? 'bg-gradient-to-br from-rose-500/10 via-rose-500/5 to-transparent border-rose-500/40'
          : 'bg-gradient-to-br from-amber-500/10 via-amber-500/5 to-transparent border-amber-500/40'
      }`}
    >
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-4 pb-4 border-b border-slate-200/80">
        <div className="flex items-center space-x-3">
          <div
            className={`p-3 rounded-2xl ${
              isYes
                ? 'bg-emerald-600 text-white shadow-emerald-500/30'
                : isNo
                ? 'bg-rose-600 text-white shadow-rose-500/30'
                : 'bg-amber-500 text-white shadow-amber-500/30'
            } shadow-md`}
          >
            {isYes && <CheckCircle className="w-8 h-8 stroke-[2.5]" />}
            {isNo && <XCircle className="w-8 h-8 stroke-[2.5]" />}
            {isMaybe && <AlertCircle className="w-8 h-8 stroke-[2.5]" />}
          </div>

          <div>
            <div className="flex items-center space-x-2">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-500">
                Deterministic Eligibility Verdict
              </span>
              <span className="text-[10px] bg-slate-100 text-slate-600 font-mono px-1.5 py-0.5 rounded flex items-center">
                <ShieldCheck className="w-3 h-3 text-emerald-600 mr-1" />
                Pure Python Evaluation
              </span>
            </div>
            <h2
              className={`text-2xl font-black tracking-tight ${
                isYes
                  ? 'text-emerald-800'
                  : isNo
                  ? 'text-rose-800'
                  : 'text-amber-800'
              }`}
            >
              {isYes && 'QUALIFIED / ELIGIBLE'}
              {isNo && 'NOT ELIGIBLE'}
              {isMaybe && 'CONDITIONAL / AMBIGUOUS'}
            </h2>
          </div>
        </div>

        <div className="text-right sm:self-center flex items-center space-x-2">
          <span
            className={`text-xs font-bold px-3 py-1.5 rounded-full inline-block ${
              isYes
                ? 'bg-emerald-100 text-emerald-800 border border-emerald-300'
                : isNo
                ? 'bg-rose-100 text-rose-800 border border-rose-300'
                : 'bg-amber-100 text-amber-800 border border-amber-300'
            }`}
          >
            Status: {verdict.status}
          </span>
          <button
            onClick={() => window.print()}
            className="flex items-center space-x-1.5 text-xs font-semibold px-3 py-1.5 bg-white hover:bg-slate-100 text-slate-700 border border-slate-300 rounded-lg shadow-sm transition"
            title="Print or Save Official Scheme Report"
          >
            <Printer className="w-3.5 h-3.5 text-slate-600" />
            <span>Print Report</span>
          </button>
        </div>
      </div>

      {/* Plain Language Summary */}
      <div className="bg-white/80 p-3.5 rounded-xl border border-slate-200/60 shadow-sm mb-5">
        <p className="text-sm sm:text-base font-medium text-slate-800 leading-relaxed">
          {verdict.summary}
        </p>
        {isMaybe && verdict.missing_fields && verdict.missing_fields.length > 0 && (
          <p className="text-xs font-bold text-amber-800 mt-2 bg-amber-50 p-2 rounded-lg border border-amber-200">
            👉 Answer the 2 missing questions in the card above to calculate your definitive YES/NO verdict!
          </p>
        )}
      </div>

      {/* Criteria Pass/Fail Breakdown */}
      <div>
        <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">
          Rule-by-Rule Evaluation Trace:
        </h4>
        <div className="space-y-2">
          {verdict.reasons.map((reason: Reason, idx: number) => (
            <div
              key={idx}
              className={`p-3 rounded-xl border text-xs sm:text-sm flex items-start justify-between bg-white ${
                reason.passed
                  ? 'border-emerald-200'
                  : 'border-rose-200'
              }`}
            >
              <div className="flex items-start space-x-2.5">
                {reason.passed ? (
                  <CheckCircle className="w-4 h-4 text-emerald-600 flex-shrink-0 mt-0.5" />
                ) : (
                  <XCircle className="w-4 h-4 text-rose-600 flex-shrink-0 mt-0.5" />
                )}
                <div>
                  <p className="font-semibold text-slate-800">
                    {reason.explanation}
                  </p>
                  <p className="text-[11px] text-slate-500 italic mt-0.5">
                    Field: {reason.condition.field} {reason.condition.operator} {reason.condition.value} {reason.condition.unit || ''}
                  </p>
                </div>
              </div>

              <span className="text-[10px] font-mono text-slate-500 bg-slate-100 px-2 py-0.5 rounded border border-slate-200 flex-shrink-0 ml-2">
                {reason.clause_id}
              </span>
            </div>
          ))}

          {verdict.missing_fields && verdict.missing_fields.length > 0 && (
            <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl text-xs text-amber-900">
              <span className="font-bold">Missing Information:</span> Could not verify [
              {verdict.missing_fields.join(', ')}].
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

