import React, { useState, useRef } from 'react';
import { UploadCloud, Link as LinkIcon, FileText, X, Sparkles } from 'lucide-react';
import { VerifiedSource } from '../types';

interface IngestBarProps {
  onStart: (file: File | null, url: string | null) => void;
  isLoading: boolean;
  verifiedSources?: VerifiedSource[];
}

export const IngestBar: React.FC<IngestBarProps> = ({
  onStart,
  isLoading,
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

        {/* Right: URL Input */}
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
                className="w-full pl-9 pr-4 py-2.5 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500"
              />
            </div>
            <p className="text-[11px] text-slate-400 mt-2">
              Enter any official government portal URL or direct PDF notification link.
            </p>
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
