import React, { useState } from 'react';
import {
  ShieldCheck,
  FileCheck2,
  Gift,
  Scale,
  CalendarClock,
  AlertTriangle,
  Quote,
  ChevronRight,
  ChevronDown,
  Info,
} from 'lucide-react';
import { Scheme, Condition, Benefit, Obligation } from '../types';

interface GroundingInspectorProps {
  scheme?: Scheme;
}

export const GroundingInspector: React.FC<GroundingInspectorProps> = ({ scheme }) => {
  const [selectedCitation, setSelectedCitation] = useState<{
    clause_id: string;
    quote: string;
    type: string;
  } | null>(null);

  const [expandedSection, setExpandedSection] = useState<'benefits' | 'conditions' | 'obligations' | 'uncertain'>('conditions');

  if (!scheme) {
    return (
      <div className="bg-white rounded-2xl shadow-sm border border-slate-200/80 p-6 flex flex-col items-center justify-center text-center min-h-[350px]">
        <div className="p-3 bg-slate-100 rounded-full text-slate-400 mb-3">
          <FileCheck2 className="w-8 h-8 text-slate-400" />
        </div>
        <h3 className="text-base font-semibold text-slate-700">Legal Grounding Inspector</h3>
        <p className="text-xs text-slate-400 max-w-xs mt-1">
          Upload an official document to inspect extracted conditions, benefits, and clause-level citations.
        </p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-slate-200/80 overflow-hidden flex flex-col h-full">
      {/* Header */}
      <div className="bg-slate-900 text-white p-5">
        <div className="flex items-center justify-between mb-2">
          <span className="text-[11px] font-bold uppercase tracking-wider text-emerald-400 flex items-center">
            <ShieldCheck className="w-3.5 h-3.5 mr-1" />
            Verified Policy Extraction
          </span>
          <span className="text-xs bg-slate-800 text-slate-300 px-2 py-0.5 rounded font-mono">
            {scheme.doc_id.slice(0, 10)}...
          </span>
        </div>
        <h2 className="text-lg font-bold text-white line-clamp-2">
          {scheme.title || 'Official Policy Document'}
        </h2>
        <div className="flex items-center space-x-2 mt-2">
          <span className="text-xs bg-emerald-500/20 text-emerald-300 px-2 py-0.5 rounded-full font-medium">
            {scheme.audience === 'citizen' ? 'Citizen Scheme' : 'Business Regulation'}
          </span>
          <span className="text-xs text-slate-400">
            {scheme.conditions.length} conditions • {scheme.benefits.length} benefits
          </span>
        </div>
      </div>

      {/* Accordion List */}
      <div className="p-4 space-y-3 overflow-y-auto flex-1">
        {/* Conditions Section */}
        <div className="border border-slate-200 rounded-xl overflow-hidden">
          <button
            onClick={() => setExpandedSection(expandedSection === 'conditions' ? ('' as any) : 'conditions')}
            className="w-full flex items-center justify-between p-3.5 bg-slate-50 hover:bg-slate-100/70 text-left transition"
          >
            <div className="flex items-center space-x-2">
              <Scale className="w-4 h-4 text-emerald-600" />
              <span className="text-xs font-bold text-slate-800 uppercase tracking-wider">
                Eligibility Rules & Thresholds ({scheme.conditions.length})
              </span>
            </div>
            {expandedSection === 'conditions' ? <ChevronDown className="w-4 h-4 text-slate-400" /> : <ChevronRight className="w-4 h-4 text-slate-400" />}
          </button>

          {expandedSection === 'conditions' && (
            <div className="p-3 space-y-2 bg-white divide-y divide-slate-100">
              {scheme.conditions.map((cond: Condition, idx: number) => (
                <div key={idx} className="pt-2 first:pt-0">
                  <div className="flex items-start justify-between">
                    <div>
                      <span className="text-xs font-semibold text-slate-800">
                        {cond.field.replace(/_/g, ' ')}
                      </span>
                      <span className="text-xs font-mono text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded ml-2 font-medium">
                        {cond.operator} {cond.value} {cond.unit || ''}
                      </span>
                    </div>
                    <button
                      onClick={() =>
                        setSelectedCitation({
                          clause_id: cond.clause_id,
                          quote: cond.quote,
                          type: 'Condition Rule',
                        })
                      }
                      className="text-[11px] font-mono text-slate-500 hover:text-emerald-700 bg-slate-100 hover:bg-emerald-50 px-2 py-0.5 rounded border border-slate-200 transition"
                    >
                      {cond.clause_id}
                    </button>
                  </div>
                  <p className="text-xs text-slate-500 italic mt-1 bg-slate-50/60 p-1.5 rounded border-l-2 border-slate-300">
                    "{cond.quote}"
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Benefits Section */}
        <div className="border border-slate-200 rounded-xl overflow-hidden">
          <button
            onClick={() => setExpandedSection(expandedSection === 'benefits' ? ('' as any) : 'benefits')}
            className="w-full flex items-center justify-between p-3.5 bg-slate-50 hover:bg-slate-100/70 text-left transition"
          >
            <div className="flex items-center space-x-2">
              <Gift className="w-4 h-4 text-teal-600" />
              <span className="text-xs font-bold text-slate-800 uppercase tracking-wider">
                Welfare Benefits & Grants ({scheme.benefits.length})
              </span>
            </div>
            {expandedSection === 'benefits' ? <ChevronDown className="w-4 h-4 text-slate-400" /> : <ChevronRight className="w-4 h-4 text-slate-400" />}
          </button>

          {expandedSection === 'benefits' && (
            <div className="p-3 space-y-2 bg-white divide-y divide-slate-100">
              {scheme.benefits.map((ben: Benefit, idx: number) => (
                <div key={idx} className="pt-2 first:pt-0">
                  <div className="flex items-start justify-between">
                    <p className="text-xs font-medium text-slate-800 flex-1 pr-2">
                      {ben.description}
                    </p>
                    <button
                      onClick={() =>
                        setSelectedCitation({
                          clause_id: ben.clause_id,
                          quote: ben.quote,
                          type: 'Benefit Clause',
                        })
                      }
                      className="text-[11px] font-mono text-slate-500 hover:text-teal-700 bg-slate-100 px-2 py-0.5 rounded border border-slate-200"
                    >
                      {ben.clause_id}
                    </button>
                  </div>
                  {ben.amount !== undefined && (
                    <span className="inline-block mt-1 text-xs font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded">
                      ₹{ben.amount.toLocaleString('en-IN')} {ben.frequency ? `(${ben.frequency})` : ''}
                    </span>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Obligations Section */}
        <div className="border border-slate-200 rounded-xl overflow-hidden">
          <button
            onClick={() => setExpandedSection(expandedSection === 'obligations' ? ('' as any) : 'obligations')}
            className="w-full flex items-center justify-between p-3.5 bg-slate-50 hover:bg-slate-100/70 text-left transition"
          >
            <div className="flex items-center space-x-2">
              <CalendarClock className="w-4 h-4 text-amber-600" />
              <span className="text-xs font-bold text-slate-800 uppercase tracking-wider">
                Mandatory Obligations ({scheme.obligations.length})
              </span>
            </div>
            {expandedSection === 'obligations' ? <ChevronDown className="w-4 h-4 text-slate-400" /> : <ChevronRight className="w-4 h-4 text-slate-400" />}
          </button>

          {expandedSection === 'obligations' && (
            <div className="p-3 space-y-2 bg-white divide-y divide-slate-100">
              {scheme.obligations.map((ob: Obligation, idx: number) => (
                <div key={idx} className="pt-2 first:pt-0">
                  <div className="flex items-start justify-between">
                    <p className="text-xs font-medium text-slate-800 flex-1 pr-2">
                      {ob.description}
                    </p>
                    <button
                      onClick={() =>
                        setSelectedCitation({
                          clause_id: ob.clause_id,
                          quote: ob.quote,
                          type: 'Obligation Clause',
                        })
                      }
                      className="text-[11px] font-mono text-slate-500 hover:text-amber-700 bg-slate-100 px-2 py-0.5 rounded border border-slate-200"
                    >
                      {ob.clause_id}
                    </button>
                  </div>
                  {ob.deadline && (
                    <span className="inline-block mt-1 text-[11px] font-semibold text-rose-700 bg-rose-50 px-2 py-0.5 rounded">
                      Deadline: {ob.deadline}
                    </span>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Uncertain Claims (If Any) */}
        {scheme.uncertain && scheme.uncertain.length > 0 && (
          <div className="border border-amber-200 bg-amber-50/50 rounded-xl overflow-hidden">
            <button
              onClick={() => setExpandedSection(expandedSection === 'uncertain' ? ('' as any) : 'uncertain')}
              className="w-full flex items-center justify-between p-3.5 text-left transition"
            >
              <div className="flex items-center space-x-2">
                <AlertTriangle className="w-4 h-4 text-amber-600" />
                <span className="text-xs font-bold text-amber-900 uppercase tracking-wider">
                  Quarantined / Uncertain Claims ({scheme.uncertain.length})
                </span>
              </div>
              {expandedSection === 'uncertain' ? <ChevronDown className="w-4 h-4 text-amber-600" /> : <ChevronRight className="w-4 h-4 text-amber-600" />}
            </button>

            {expandedSection === 'uncertain' && (
              <div className="p-3 text-xs text-amber-800 space-y-1.5 bg-amber-50">
                <p className="text-[11px] text-amber-700 mb-2">
                  <Info className="w-3 h-3 inline mr-1" />
                  These claims failed strict 3-stage grounding checks and were quarantined so they never produce false eligibility verdicts.
                </p>
                {scheme.uncertain.map((unc, idx) => (
                  <div key={idx} className="bg-white p-2 rounded border border-amber-200 font-mono text-[11px]">
                    {typeof unc === 'object' ? JSON.stringify(unc) : String(unc)}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Citation Proof Drawer / Modal */}
      {selectedCitation && (
        <div className="p-4 bg-slate-800 text-slate-100 border-t border-slate-700">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-bold text-emerald-400 flex items-center">
              <Quote className="w-3.5 h-3.5 mr-1" />
              Source Citation: {selectedCitation.clause_id}
            </span>
            <button
              onClick={() => setSelectedCitation(null)}
              className="text-xs text-slate-400 hover:text-white"
            >
              Close
            </button>
          </div>
          <p className="text-xs italic text-slate-300 bg-slate-900/80 p-2.5 rounded-lg border border-slate-700 font-serif">
            "{selectedCitation.quote}"
          </p>
          <p className="text-[10px] text-slate-400 mt-1.5">
            Verified verbatim against the original official policy gazette.
          </p>
        </div>
      )}
    </div>
  );
};

