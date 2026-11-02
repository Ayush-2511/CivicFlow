import React, { useState } from 'react';
import { CheckSquare, Square, Printer, CheckCircle, MapPin, Calendar, FileText } from 'lucide-react';
import { Explainer, Scheme, Verdict } from '../types';

interface ActionChecklistProps {
  explainer?: Explainer;
  scheme?: Scheme;
  verdict?: Verdict;
}

const ADMIN_TERMS = [
  'state/ut',
  'sponsoring bank',
  'pfms',
  'it system',
  'department',
  'displayed at',
  'panchayat must',
  'transparency',
  'inter-departmental',
  'destination bank',
  'nodal officer',
  'procedure',
  'fund transfer',
  'shall designate',
  'shall prepare',
  'shall authorize',
  'database of',
  'village authority namely',
  'agriculture census',
];

function canonicalDocName(doc: string): string | null {
  if (!doc) return null;
  const clean = doc.trim();
  const lower = clean.toLowerCase();

  // Reject administrative procedures and duties
  if (ADMIN_TERMS.some((term) => lower.includes(term))) return null;
  if (clean.length > 80) return null;

  if (lower.includes('aadhaar')) return 'Aadhaar Card';
  if (lower.includes('khatauni') || lower.includes('land') || lower.includes('patta') || lower.includes('vanshavali') || lower.includes('village authority') || lower.includes('lineage')) {
    return 'Land Ownership Record (Khatauni / Land Certificate)';
  }
  if (lower.includes('passbook') || lower.includes('bank account') || lower.includes('bank statement') || lower.includes('bank details')) {
    return 'Bank Account Passbook / Statement';
  }
  if (lower.includes('self-declaration') || lower.includes('self declaration')) return 'Self-Declaration Form';
  if (lower.includes('udyam')) return 'Udyam Registration Certificate';
  if (lower.includes('pan')) return 'PAN Card';
  if (lower.includes('gst')) return 'GSTIN Registration';
  if (lower.includes('voter')) return 'Voter ID Card';
  if (lower.includes('driving')) return 'Driving Licence';
  if (lower.includes('income')) return 'Income Certificate';
  if (lower.includes('caste')) return 'Caste Certificate';

  return clean;
}

export const ActionChecklist: React.FC<ActionChecklistProps> = ({ explainer, scheme }) => {
  if (!explainer && !scheme) return null;

  const obligations = scheme?.obligations || [];

  // Robust document extraction: Check explainer first, fallback to scheme obligations
  const items: string[] = [];
  const seenCanonical = new Set<string>();

  if (explainer?.checklist && explainer.checklist.length > 0) {
    explainer.checklist.forEach((item) => {
      const canon = canonicalDocName(item);
      const toAdd = canon || item;
      const lower = toAdd.toLowerCase();
      if (!ADMIN_TERMS.some((term) => lower.includes(term)) && !seenCanonical.has(lower)) {
        seenCanonical.add(lower);
        items.push(toAdd);
      }
    });
  } else if (obligations.length > 0) {
    // Gather all explicit required_documents
    obligations.forEach((ob) => {
      (ob.required_documents || []).forEach((doc) => {
        const canon = canonicalDocName(doc);
        if (canon && !seenCanonical.has(canon.toLowerCase())) {
          seenCanonical.add(canon.toLowerCase());
          items.push(canon);
        }
      });
    });
  }

  // Extract explicit submission channels
  const submissionChannels = Array.from(
    new Set(
      obligations
        .map((o) => o.apply_at?.trim())
        .filter((a): a is string => Boolean(a && a.length > 0))
    )
  );

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
