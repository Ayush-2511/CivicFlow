import React, { useState } from 'react';
import { CheckSquare, Square, Printer, CheckCircle, MapPin, Calendar, FileText } from 'lucide-react';
import { Explainer, Scheme, Verdict } from '../types';

interface ActionChecklistProps {
  explainer?: Explainer;
  scheme?: Scheme;
  verdict?: Verdict;
}

export const ActionChecklist: React.FC<ActionChecklistProps> = ({ explainer, scheme }) => {
  if (!explainer && !scheme) return null;

  const obligations = scheme?.obligations || [];

  // Robust document extraction: Check explainer first, fallback to scheme obligations
  const items: string[] = [];

  if (explainer?.checklist && explainer.checklist.length > 0) {
    items.push(...explainer.checklist);
  } else if (obligations.length > 0) {
    // Gather all explicit required_documents
    obligations.forEach((ob) => {
      if (ob.required_documents && ob.required_documents.length > 0) {
        ob.required_documents.forEach((doc) => {
          if (doc && !items.includes(doc)) items.push(doc);
        });
      } else if (ob.description) {
        // Fallback: Extract from obligation description if it specifies document / verification requirement
        const desc = ob.description.trim();
        const lower = desc.toLowerCase();
        if (
          lower.includes('aadhaar') ||
          lower.includes('document') ||
          lower.includes('identification') ||
          lower.includes('record') ||
          lower.includes('certificate') ||
          lower.includes('kyc') ||
          lower.includes('passbook') ||
          lower.includes('pan') ||
          lower.includes('bank')
        ) {
          if (!items.includes(desc)) items.push(desc);
        }
      }
    });

    // If still empty but obligations exist, use obligation descriptions
    if (items.length === 0) {
      obligations.forEach((ob) => {
        if (ob.description && !items.includes(ob.description)) {
          items.push(ob.description);
        }
      });
    }
  }

  // Extract explicit submission channels
  const submissionChannels = obligations
    .map((o) => o.apply_at)
    .filter((a): a is string => Boolean(a && a.trim()));

  const [checkedItems, setCheckedItems] = useState<Record<number, boolean>>({});

  const toggleCheck = (idx: number) => {
    setCheckedItems((prev) => ({ ...prev, [idx]: !prev[idx] }));
  };

  const handlePrint = () => {
    window.print();
  };

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-slate-200/80 p-5 sm:p-6 mb-6">
      <div className="flex items-center justify-between mb-4 pb-3 border-b border-slate-100">
        <div className="flex items-center space-x-2.5">
          <div className="p-2 bg-teal-100 text-teal-800 rounded-lg">
            <CheckCircle className="w-5 h-5" />
          </div>
          <div>
            <span className="text-[11px] font-bold text-teal-700 uppercase tracking-wider">
              Citizen Action Plan
            </span>
            <h3 className="text-sm sm:text-base font-bold text-slate-800">
              Required Documents & Deadlines
            </h3>
          </div>
        </div>

        <button
          onClick={handlePrint}
          className="flex items-center space-x-1.5 text-xs font-semibold px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg transition"
        >
          <Printer className="w-3.5 h-3.5" />
          <span>Print / Save</span>
        </button>
      </div>

      {/* 3 Pillars: Documents, Where, Deadlines */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
        {/* Required Documents */}
        <div className="bg-slate-50 p-4 rounded-xl border border-slate-200">
          <div className="flex items-center space-x-2 text-xs font-bold text-slate-700 uppercase tracking-wider mb-2.5">
            <FileText className="w-4 h-4 text-emerald-600" />
            <span>Document Checklist:</span>
          </div>

          <div className="space-y-2">
            {items.length > 0 ? (
              items.map((item, idx) => (
                <div
                  key={idx}
                  onClick={() => toggleCheck(idx)}
                  className="flex items-center space-x-2 text-xs sm:text-sm text-slate-800 cursor-pointer select-none hover:text-emerald-700 transition"
                >
                  {checkedItems[idx] ? (
                    <CheckSquare className="w-4 h-4 text-emerald-600 flex-shrink-0" />
                  ) : (
                    <Square className="w-4 h-4 text-slate-400 flex-shrink-0" />
                  )}
                  <span className={checkedItems[idx] ? 'line-through text-slate-400' : ''}>
                    {item}
                  </span>
                </div>
              ))
            ) : (
              <p className="text-xs text-slate-400 italic">No specific documents required.</p>
            )}
          </div>
        </div>

        {/* Where to apply & Deadlines */}
        <div className="space-y-3">
          <div className="bg-slate-50 p-3.5 rounded-xl border border-slate-200">
            <div className="flex items-center space-x-2 text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
              <MapPin className="w-4 h-4 text-teal-600" />
              <span>Where to Submit:</span>
            </div>
            {submissionChannels.length > 0 ? (
              <ul className="text-xs text-slate-700 space-y-1 mt-1 font-medium list-disc list-inside">
                {submissionChannels.map((ch, i) => (
                  <li key={i}>{ch}</li>
                ))}
              </ul>
            ) : (
              <p className="text-xs text-slate-600 font-medium">
                Nearest Common Service Centre (CSC), Gram Panchayat office, or the official scheme portal.
              </p>
            )}
          </div>

          {obligations.some((o) => o.deadline) && (
            <div className="bg-rose-50 p-3.5 rounded-xl border border-rose-200">
              <div className="flex items-center space-x-2 text-xs font-bold text-rose-800 uppercase tracking-wider mb-1">
                <Calendar className="w-4 h-4 text-rose-600" />
                <span>Crucial Deadlines:</span>
              </div>
              {obligations
                .filter((o) => o.deadline)
                .map((o, i) => (
                  <p key={i} className="text-xs font-bold text-rose-900">
                    {o.deadline}: {o.description}
                  </p>
                ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

