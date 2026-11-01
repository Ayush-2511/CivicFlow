import React, { useState, useRef } from 'react';
import { UploadCloud, Link as LinkIcon, FileText, X, Sparkles, CheckCircle2, FileCheck } from 'lucide-react';
import { VerifiedSource } from '../types';

const PM_KISAN_DEMO_TEXT = `MINISTRY OF AGRICULTURE AND FARMERS WELFARE
NOTIFICATION
New Delhi, the 24th February, 2019

PRADHAN MANTRI KISAN SAMMAN NIDHI (PM-KISAN) OPERATIONAL GUIDELINES

1. Short Title and Commencement:
This scheme shall be known as the Pradhan Mantri Kisan Samman Nidhi (PM-KISAN). The scheme has come into effect from 1st December 2018.

2. Definition and Eligibility Conditions:
(a) A small and marginal farmer family is defined as a family comprising of husband, wife and minor children who collectively own cultivable land up to 2 hectares as per land records of the concerned State/UT.
(b) All landholder farmer families having cultivable landholding up to 2 hectares shall be eligible for financial assistance under this scheme.
(c) The following categories of beneficiaries of higher economic status shall be excluded from the benefit: institutional landholders, farmer families holding constitutional posts, serving or retired government officers and employees, and income tax payees.

3. Benefits Provided:
(a) Under the scheme, financial benefit of Rs. 6000 per year will be provided to eligible beneficiary farmer families.
(b) The assistance of Rs. 6000 will be credited directly to the bank accounts of the beneficiaries in three equal four-monthly installments of Rs. 2000 each.

4. Mandatory Obligations and Required Documents:
(a) To receive financial benefits under PM-KISAN, the beneficiary must submit Aadhaar card details or Aadhaar enrollment number.
(b) Beneficiaries must provide their bank account details and land ownership records (Khatauni) for electronic direct benefit transfer.
(c) Beneficiaries must complete e-KYC authentication before the designated annual cut-off date of 31st March 2026.
(d) Application forms and verification documents may be submitted at the nearest Common Service Centre (CSC) or online through the PM-KISAN portal.`;

const MSME_DEMO_TEXT = `MINISTRY OF MICRO, SMALL AND MEDIUM ENTERPRISES
NOTIFICATION
New Delhi, the 1st June, 2020

CREDIT GUARANTEE SCHEME FOR MICRO AND SMALL ENTERPRISES (CGTMSE)

1. Scope and Objective:
The scheme aims to encourage first-generation entrepreneurs to set up Micro and Small Enterprises (MSEs) by providing collateral-free credit facilities.

2. Eligibility Conditions:
(a) The scheme is available to both existing and new Micro and Small Enterprises engaged in manufacturing or service activities.
(b) The annual turnover of the eligible enterprise must not exceed Rs. 50 crore as per verified GST returns.
(c) The maximum loan amount eligible for guarantee coverage shall be up to Rs. 200 lakh (Rs. 2 crore) per borrowing unit.
(d) Retail trade, educational institutions, training institutions, and Self Help Groups are not eligible for credit guarantee coverage.

3. Guarantee and Financial Benefit:
(a) The Trust shall provide guarantee cover up to 85% of the sanctioned credit facility for micro enterprises up to Rs. 5 lakh.
(b) For credit facilities above Rs. 5 lakh and up to Rs. 200 lakh, guarantee coverage of 75% shall be extended by the Trust.

4. Procedural Obligations and Applications:
(a) Eligible enterprises must submit their Udyam Registration Certificate along with audited financial statements for the previous financial year.
(b) The borrowing unit must submit PAN card, GSTIN registration, and business bank statements.
(c) Applications must be processed through Member Lending Institutions (MLIs) including scheduled commercial banks and regional rural banks.`;

interface IngestBarProps {
  onStart: (file: File | null, url: string | null) => void;
  isLoading: boolean;
  verifiedSources: VerifiedSource[];
}

export const IngestBar: React.FC<IngestBarProps> = ({
  onStart,
  isLoading,
  verifiedSources,
}) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [urlInput, setUrlInput] = useState<string>('');
  const [isDragOver, setIsDragOver] = useState<boolean>(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setSelectedFile(e.dataTransfer.files[0]);
      setUrlInput('');
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
      setUrlInput('');
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile && !urlInput.trim()) return;
    onStart(selectedFile, urlInput.trim() || null);
  };

  const handleSelectVerifiedSource = (src: VerifiedSource) => {
    setUrlInput(src.url);
    setSelectedFile(null);
  };

  const loadPreset = (filename: string, content: string) => {
    const file = new File([content], filename, { type: 'text/plain' });
    setSelectedFile(file);
    setUrlInput('');
  };

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-slate-200/80 p-5 sm:p-6 mb-6">
      <div className="flex flex-col lg:flex-row gap-5 items-stretch">
        {/* Left: Drag & Drop Zone */}
        <div
          onDragOver={(e) => {
            e.preventDefault();
            setIsDragOver(true);
          }}
          onDragLeave={() => setIsDragOver(false)}
          onDrop={handleFileDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`flex-1 border-2 border-dashed rounded-xl p-4 sm:p-6 flex flex-col items-center justify-center cursor-pointer transition-all ${
            isDragOver
              ? 'border-emerald-500 bg-emerald-50/50'
              : selectedFile
              ? 'border-emerald-400 bg-emerald-50/20'
              : 'border-slate-300 hover:border-slate-400 bg-slate-50/50'
          }`}
        >
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileChange}
            accept=".pdf,.png,.jpg,.jpeg,.txt"
            className="hidden"
          />

          {selectedFile ? (
            <div className="flex items-center space-x-3 text-slate-800">
              <div className="p-2.5 bg-emerald-100 text-emerald-700 rounded-lg">
                <FileText className="w-6 h-6" />
              </div>
              <div className="text-left">
                <p className="text-sm font-semibold truncate max-w-[200px] sm:max-w-xs">
                  {selectedFile.name}
                </p>
                <p className="text-xs text-slate-500">
                  {(selectedFile.size / 1024).toFixed(1)} KB • Click or drop to replace
                </p>
              </div>
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  setSelectedFile(null);
                }}
                className="p-1 hover:bg-slate-200 text-slate-500 rounded-full transition"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          ) : (
            <div className="flex flex-col items-center text-center">
              <div className="p-2.5 bg-slate-100 text-slate-500 rounded-full mb-2">
                <UploadCloud className="w-6 h-6 text-emerald-600" />
              </div>
              <p className="text-sm font-medium text-slate-700">
                Drop official notification or gazette here
              </p>
              <p className="text-xs text-slate-400 mt-0.5">
                Supports PDF, scanned images (PNG/JPG), or text
              </p>
            </div>
          )}
        </div>

        {/* Middle Separator */}
        <div className="hidden lg:flex items-center justify-center text-xs font-semibold text-slate-400 uppercase tracking-wider">
          OR
        </div>

        {/* Right: URL Input & Verified Sources */}
        <div className="flex-1 flex flex-col justify-between">
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1.5">
              Paste Official Policy / Scheme URL
            </label>
            <div className="relative">
              <LinkIcon className="w-4 h-4 text-slate-400 absolute left-3 top-3 pointer-events-none" />
              <input
                type="url"
                value={urlInput}
                onChange={(e) => {
                  setUrlInput(e.target.value);
                  if (e.target.value) setSelectedFile(null);
                }}
                placeholder="https://myscheme.gov.in/schemes/pm-kisan"
                className="w-full pl-9 pr-4 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500"
              />
            </div>
          </div>

          {/* Quick-Pick Chips */}
          <div className="mt-3">
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-[11px] font-medium text-slate-500 uppercase tracking-wider block">
                Quick Demo Policy Presets (Guaranteed Offline / Working):
              </span>
            </div>
            <div className="flex flex-wrap gap-1.5 mb-2.5">
              <button
                type="button"
                onClick={() => loadPreset('pm_kisan_operational_guidelines.txt', PM_KISAN_DEMO_TEXT)}
                className={`text-xs px-2.5 py-1 rounded-md border font-medium transition-all text-left flex items-center space-x-1 ${
                  selectedFile?.name === 'pm_kisan_operational_guidelines.txt'
                    ? 'bg-emerald-100 border-emerald-400 text-emerald-800 shadow-sm'
                    : 'bg-emerald-50 hover:bg-emerald-100/70 border-emerald-200 text-emerald-800'
                }`}
              >
                <span>🌾 PM-Kisan Scheme (Citizen Demo)</span>
              </button>
              <button
                type="button"
                onClick={() => loadPreset('msme_cgtmse_guidelines.txt', MSME_DEMO_TEXT)}
                className={`text-xs px-2.5 py-1 rounded-md border font-medium transition-all text-left flex items-center space-x-1 ${
                  selectedFile?.name === 'msme_cgtmse_guidelines.txt'
                    ? 'bg-amber-100 border-amber-400 text-amber-800 shadow-sm'
                    : 'bg-amber-50 hover:bg-amber-100/70 border-amber-200 text-amber-800'
                }`}
              >
                <span>🏭 MSME Credit Guarantee (Business Demo)</span>
              </button>
            </div>

            {verifiedSources.length > 0 && (
              <>
                <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider block mb-1">
                  Live Government URLs:
                </span>
                <div className="flex flex-wrap gap-1.5">
                  {verifiedSources.slice(0, 4).map((src, i) => (
                    <button
                      key={i}
                      type="button"
                      onClick={() => handleSelectVerifiedSource(src)}
                      className={`text-xs px-2.5 py-1 rounded-md border transition-all text-left flex items-center space-x-1 ${
                        urlInput === src.url
                          ? 'bg-emerald-100 border-emerald-400 text-emerald-800 font-medium'
                          : 'bg-slate-100/80 hover:bg-slate-200/70 border-slate-200 text-slate-700'
                      }`}
                    >
                      {urlInput === src.url && <CheckCircle2 className="w-3 h-3 text-emerald-600 mr-0.5" />}
                      <span>{src.title}</span>
                    </button>
                  ))}
                </div>
              </>
            )}
          </div>

          {/* Submit Button */}
          <div className="mt-4">
            <button
              onClick={handleSubmit}
              disabled={isLoading || (!selectedFile && !urlInput.trim())}
              className={`w-full py-2.5 px-4 rounded-xl text-sm font-semibold flex items-center justify-center space-x-2 text-white transition-all shadow-sm ${
                isLoading || (!selectedFile && !urlInput.trim())
                  ? 'bg-slate-300 cursor-not-allowed'
                  : 'bg-emerald-600 hover:bg-emerald-700 active:scale-[0.99] shadow-emerald-500/20'
              }`}
            >
              {isLoading ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2" />
                  <span>Processing Policy Document...</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4" />
                  <span>Analyze Scheme & Check Eligibility</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

