import React from 'react';
import {
  Landmark,
  Calendar,
  MapPin,
  FileText,
  ShieldCheck,
  Award,
  Clock,
  Briefcase,
  Users,
} from 'lucide-react';
import { Scheme, Verdict, Explainer } from '../types';

interface SchemePrintReportProps {
  scheme?: Scheme;
  verdict?: Verdict;
  explainer?: Explainer;
}

const LANGUAGE_DISPLAY_NAMES: Record<string, string> = {
  hi: 'Hindi (हिन्दी)',
  mr: 'Marathi (मराठी)',
  en: 'English',
  ta: 'Tamil (தமிழ்)',
  te: 'Telugu (తెలుగు)',
  bn: 'Bengali (বাংলা)',
  gu: 'Gujarati (ગુજરાતી)',
  kn: 'Kannada (ಕನ್ನಡ)',
  ml: 'Malayalam (മലയാളം)',
  ur: 'Urdu (اردو)',
};

export const SchemePrintReport: React.FC<SchemePrintReportProps> = ({
  scheme,
  explainer,
}) => {
  if (!scheme && !explainer) {
    return null;
  }

  const obligations = scheme?.obligations || [];
  const benefits = scheme?.benefits || [];

  // User requirement: "instead of evaluation, the voice transcript should be there and in the start,
  // in the regional language. remove the 1st point that explains if the user is eligible or not
  // and keep the rest points in pdf"
  const allSegments = explainer?.segments || [];
  const transcriptPoints = allSegments.length > 1 ? allSegments.slice(1) : allSegments;

  // Extract all required documents
  const documentItems: string[] = [];
  obligations.forEach((ob) => {
    if (ob.required_documents && ob.required_documents.length > 0) {
      ob.required_documents.forEach((doc) => {
        const clean = doc.trim();
        if (clean && !documentItems.includes(clean)) {
          documentItems.push(clean);
        }
      });
    }
  });

  if (explainer?.checklist && explainer.checklist.length > 0) {
    explainer.checklist.forEach((item) => {
      const clean = item.trim();
      if (clean && !documentItems.includes(clean)) {
        documentItems.push(clean);
      }
    });
  }

  obligations.forEach((ob) => {
    if (ob.description) {
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
        lower.includes('gstin') ||
        lower.includes('bank statement')
      ) {
        if (!documentItems.includes(desc)) {
          documentItems.push(desc);
        }
      }
    }
  });

  // Extract deadlines
  const deadlines: { date: string; description: string; clause_id?: string }[] = [];
  obligations.forEach((ob) => {
    if (ob.deadline && ob.deadline.trim()) {
      deadlines.push({
        date: ob.deadline.trim(),
        description: ob.description,
        clause_id: ob.clause_id,
      });
    } else if (
      ob.description.toLowerCase().includes('deadline') ||
      ob.description.toLowerCase().includes('march') ||
      ob.description.toLowerCase().includes('last date')
    ) {
      deadlines.push({
        date: 'Mandatory Cut-Off',
        description: ob.description,
        clause_id: ob.clause_id,
      });
    }
  });

  // Extract submission channels
  const submissionChannels = obligations
    .map((o) => o.apply_at)
    .filter((a): a is string => Boolean(a && a.trim()));

  const currentDate = new Date().toLocaleDateString('en-IN', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  });

  const languageKey = explainer?.language?.toLowerCase().trim() || 'hi';
  const displayLangName = LANGUAGE_DISPLAY_NAMES[languageKey] || languageKey.toUpperCase();

  return (
    <div className="bg-white text-slate-900 p-8 max-w-4xl mx-auto font-sans text-sm print:p-0">
      {/* Official Government Scheme Header */}
      <div className="border-b-2 border-slate-900 pb-5 mb-6">
        <div className="flex items-start justify-between">
          <div className="flex items-center space-x-3">
            <div className="p-2.5 bg-slate-900 text-white rounded-xl">
              <Landmark className="w-8 h-8" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="text-xs font-bold uppercase tracking-widest text-slate-600">
                  CivicFlow GovTech 2.0 • Official Scheme Intelligence Dossier
                </span>
                <span className="text-[10px] bg-slate-100 text-slate-700 px-2 py-0.5 rounded font-mono border border-slate-300">
                  {scheme?.confidence ? `${Math.round(scheme.confidence * 100)}% Verified Grounding` : '100% Grounded'}
                </span>
              </div>
              <h1 className="text-2xl font-black text-slate-950 mt-1 leading-tight">
                {scheme?.title || 'Government Scheme & Policy Intelligence Report'}
              </h1>
            </div>
          </div>
        </div>

        {/* Meta Bar */}
        <div className="grid grid-cols-3 gap-4 mt-4 pt-3 border-t border-slate-200 text-xs">
          <div>
            <span className="text-slate-500 font-semibold block uppercase tracking-wider text-[10px]">
              Target Audience
            </span>
            <span className="font-bold text-slate-800 capitalize flex items-center mt-0.5">
              {scheme?.audience === 'business' ? (
                <>
                  <Briefcase className="w-3.5 h-3.5 mr-1 text-slate-600" />
                  Business & Enterprise Regulation
                </>
              ) : (
                <>
                  <Users className="w-3.5 h-3.5 mr-1 text-slate-600" />
                  Citizen & Household Welfare
                </>
              )}
            </span>
          </div>

          <div>
            <span className="text-slate-500 font-semibold block uppercase tracking-wider text-[10px]">
              Report Generation Date
            </span>
            <span className="font-bold text-slate-800 flex items-center mt-0.5">
              <Calendar className="w-3.5 h-3.5 mr-1 text-slate-600" />
              {currentDate}
            </span>
          </div>

          <div>
            <span className="text-slate-500 font-semibold block uppercase tracking-wider text-[10px]">
              Document Verification Reference
            </span>
            <span className="font-mono text-slate-700 font-medium mt-0.5 block truncate">
              {scheme?.doc_id ? scheme.doc_id.slice(0, 18) : 'Grounded Circular'}
            </span>
          </div>
        </div>
      </div>

      {/* 1. Regional Policy Explainer (Voice Transcript) in Target Language */}
      {transcriptPoints.length > 0 && (
        <div className="border-2 border-emerald-600 rounded-xl p-5 mb-6 bg-emerald-50/40 print-break-inside-avoid">
          <div className="flex items-center justify-between pb-3 border-b border-emerald-200 mb-3.5">
            <div className="flex items-center space-x-2.5">
              <div className="p-2 bg-emerald-700 text-white rounded-lg shadow-sm">
                <FileText className="w-4 h-4" />
              </div>
              <div>
                <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-800 block">
                  Regional Policy Explainer • प्रादेशिक भाषा स्पष्टीकरण
                </span>
                <h2 className="text-base font-black text-slate-900 leading-tight">
                  {displayLangName} Explainer Summary
                </h2>
              </div>
            </div>

            <span className="text-[10px] font-bold px-2.5 py-0.5 rounded-full bg-emerald-100 text-emerald-900 border border-emerald-300">
              Official Explainer Transcript
            </span>
          </div>

          <div className="space-y-2.5">
            {transcriptPoints.map((seg, idx) => (
              <div
                key={idx}
                className="p-3.5 rounded-xl bg-white border border-emerald-200 shadow-xs flex items-start justify-between gap-3 text-xs"
              >
                <div className="flex items-start space-x-3 flex-1">
                  <span className="w-5 h-5 rounded-full bg-emerald-100 text-emerald-900 font-bold flex items-center justify-center text-[10px] flex-shrink-0 mt-0.5 border border-emerald-300">
                    {idx + 1}
                  </span>
                  <p className="text-slate-900 font-medium leading-relaxed text-sm">
                    {seg.text}
                  </p>
                </div>
                {seg.clause_ids && seg.clause_ids[0] && (
                  <span className="text-[10px] font-mono text-slate-500 bg-slate-50 px-2 py-0.5 rounded border border-slate-200 flex-shrink-0">
                    {seg.clause_ids[0]}
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 2. Critical Deadlines & Timelines (Highlighted) */}
      {deadlines.length > 0 && (
        <div className="bg-rose-50 border-2 border-rose-500 rounded-xl p-4 mb-6 print-break-inside-avoid">
          <div className="flex items-center space-x-2 text-rose-900 font-bold text-xs uppercase tracking-wider mb-2">
            <Clock className="w-4 h-4 text-rose-600" />
            <span>CRITICAL DEADLINES & TIMELINES:</span>
          </div>
          <div className="space-y-1.5">
            {deadlines.map((dl, idx) => (
              <div key={idx} className="flex items-start justify-between text-xs">
                <span className="font-bold text-rose-950">
                  {dl.date}: <span className="font-medium text-slate-800">{dl.description}</span>
                </span>
                {dl.clause_id && (
                  <span className="text-[10px] font-mono text-rose-700 bg-rose-100 px-1.5 py-0.5 rounded ml-2 flex-shrink-0">
                    {dl.clause_id}
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 3. Scheme Benefits & Welfare Grants */}
      {benefits.length > 0 && (
        <div className="border border-slate-300 rounded-xl p-4 mb-6 print-break-inside-avoid">
          <div className="flex items-center space-x-2 text-slate-900 font-bold text-xs uppercase tracking-wider mb-3 pb-2 border-b border-slate-200">
            <Award className="w-4 h-4 text-emerald-700" />
            <span>Welfare Benefits, Subsidies & Guarantees ({benefits.length}):</span>
          </div>
          <div className="space-y-2.5">
            {benefits.map((b, idx) => (
              <div
                key={idx}
                className="flex items-start justify-between p-2.5 bg-slate-50 rounded-lg border border-slate-200 text-xs"
              >
                <div>
                  <p className="font-bold text-slate-900">{b.description}</p>
                  {(b.amount !== undefined || b.frequency) && (
                    <p className="text-emerald-800 font-bold mt-0.5">
                      {b.amount !== undefined ? `₹${Number(b.amount).toLocaleString('en-IN')}` : ''}
                      {b.frequency ? ` (${b.frequency})` : ''}
                    </p>
                  )}
                </div>
                {b.clause_id && (
                  <span className="text-[10px] font-mono text-slate-500 bg-white border border-slate-200 px-1.5 py-0.5 rounded ml-3 flex-shrink-0">
                    {b.clause_id}
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 4. Mandatory Document Checklist */}
      <div className="border border-slate-300 rounded-xl p-4 mb-6 print-break-inside-avoid">
        <div className="flex items-center space-x-2 text-slate-900 font-bold text-xs uppercase tracking-wider mb-3 pb-2 border-b border-slate-200">
          <FileText className="w-4 h-4 text-teal-700" />
          <span>Mandatory Documents Required for Application:</span>
        </div>
        <p className="text-xs text-slate-600 mb-3">
          Ensure you have the original and photocopies of the following documents before proceeding to the application counter:
        </p>

        {documentItems.length > 0 ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
            {documentItems.map((item, idx) => (
              <div
                key={idx}
                className="flex items-start space-x-2.5 p-2 rounded bg-slate-50 border border-slate-200"
              >
                <div className="w-4 h-4 border-2 border-slate-600 rounded flex-shrink-0 mt-0.5" />
                <span className="font-semibold text-slate-800 leading-snug">{item}</span>
              </div>
            ))}
          </div>
        ) : (
          <div className="space-y-1.5 text-xs text-slate-700">
            <div className="flex items-center space-x-2">
              <div className="w-4 h-4 border-2 border-slate-600 rounded flex-shrink-0" />
              <span>Valid Government Identity Proof (Aadhaar / Voter ID / Passport)</span>
            </div>
            <div className="flex items-center space-x-2">
              <div className="w-4 h-4 border-2 border-slate-600 rounded flex-shrink-0" />
              <span>Proof of Address & Active Bank Account details (Passbook / Cancelled Cheque)</span>
            </div>
          </div>
        )}
      </div>

      {/* 5. Where to Apply & Submission Channels */}
      <div className="border border-slate-300 rounded-xl p-4 mb-6 print-break-inside-avoid">
        <div className="flex items-center space-x-2 text-slate-900 font-bold text-xs uppercase tracking-wider mb-2">
          <MapPin className="w-4 h-4 text-indigo-700" />
          <span>Where to Apply & Official Submission Channels:</span>
        </div>
        {submissionChannels.length > 0 ? (
          <ul className="list-disc list-inside space-y-1 text-xs text-slate-800 font-medium">
            {submissionChannels.map((channel, i) => (
              <li key={i}>{channel}</li>
            ))}
          </ul>
        ) : (
          <p className="text-xs text-slate-700 font-medium">
            Member Lending Institutions (MLIs), Nearest Common Service Centre (CSC), Gram Panchayat office, or the official government scheme portal.
          </p>
        )}
      </div>

      {/* 6. Statutory Obligations & Compliance Notice */}
      {obligations.length > 0 && (
        <div className="border border-slate-300 rounded-xl p-4 mb-6 print-break-inside-avoid bg-slate-50">
          <span className="text-[11px] font-bold uppercase tracking-wider text-slate-700 block mb-2">
            Mandatory Beneficiary Obligations & Compliance:
          </span>
          <div className="space-y-1.5 text-xs text-slate-800">
            {obligations.map((ob, idx) => (
              <div key={idx} className="flex items-start justify-between">
                <span className="font-medium">• {ob.description}</span>
                {ob.clause_id && (
                  <span className="text-[10px] font-mono text-slate-500 ml-2 flex-shrink-0">
                    {ob.clause_id}
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Footer & Grounding Notice */}
      <div className="border-t-2 border-slate-900 pt-4 mt-8 flex flex-col sm:flex-row items-center justify-between text-[11px] text-slate-500">
        <div className="flex items-center space-x-1.5">
          <ShieldCheck className="w-4 h-4 text-emerald-700 flex-shrink-0" />
          <span>
            Deterministic Clause Grounding • Zero-Hallucination Policy Verification
          </span>
        </div>
        <p className="mt-2 sm:mt-0 font-medium">
          CivicFlow GovTech 2.0 • For official reference and citizen action planning.
        </p>
      </div>
    </div>
  );
};
