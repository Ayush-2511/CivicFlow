import React from 'react';
import { Landmark, User, Building2, Languages, ShieldCheck } from 'lucide-react';
import { AudienceType } from '../types';

interface NavbarProps {
  persona: AudienceType;
  setPersona: (p: AudienceType) => void;
  language: string;
  setLanguage: (lang: string) => void;
  isBackendHealthy: boolean;
}

const LANGUAGES = [
  { code: 'hi', label: 'हिन्दी (Hindi)' },
  { code: 'en', label: 'English' },
  { code: 'mr', label: 'मराठी (Marathi)' },
  { code: 'ta', label: 'தமிழ் (Tamil)' },
  { code: 'te', label: 'తెలుగు (Telugu)' },
  { code: 'bn', label: 'বাংলা (Bengali)' },
];

export const Navbar: React.FC<NavbarProps> = ({
  persona,
  setPersona,
  language,
  setLanguage,
  isBackendHealthy,
}) => {
  return (
    <header className="bg-slate-900 border-b border-slate-800 text-white sticky top-0 z-50 shadow-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo & Title */}
          <div className="flex items-center space-x-3">
            <div className="bg-gradient-to-tr from-emerald-600 to-teal-500 p-2.5 rounded-xl shadow-inner">
              <Landmark className="w-6 h-6 text-white" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="text-xl font-bold tracking-tight text-white">CivicFlow</span>
                <span className="bg-emerald-500/20 text-emerald-400 text-xs px-2 py-0.5 rounded-full font-medium border border-emerald-500/30">
                  GovTech 2.0
                </span>
                <span className="hidden md:inline-flex items-center text-xs text-slate-400">
                  <ShieldCheck className="w-3.5 h-3.5 mr-1 text-emerald-400" />
                  Deterministic Grounding
                </span>
              </div>
              <p className="text-xs text-slate-400 hidden sm:block">
                Multilingual Policy, Rights & Scheme Intelligence
              </p>
            </div>
          </div>

          {/* Right Controls: Persona & Language */}
          <div className="flex items-center space-x-3 sm:space-x-4">
            {/* Backend Health Dot */}
            <div className="hidden lg:flex items-center space-x-1.5 text-xs text-slate-400 border border-slate-800 px-2.5 py-1 rounded-lg">
              <span className={`w-2 h-2 rounded-full ${isBackendHealthy ? 'bg-emerald-400 animate-pulse' : 'bg-rose-500'}`} />
              <span>{isBackendHealthy ? 'API Active' : 'Connecting...'}</span>
            </div>

            {/* Persona Toggle */}
            <div className="flex bg-slate-800 p-1 rounded-lg border border-slate-700">
              <button
                onClick={() => setPersona('citizen')}
                className={`flex items-center space-x-1.5 text-xs font-medium px-3 py-1.5 rounded-md transition-all ${
                  persona === 'citizen'
                    ? 'bg-emerald-600 text-white shadow-sm font-semibold'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                <User className="w-3.5 h-3.5" />
                <span>Citizen</span>
              </button>
              <button
                onClick={() => setPersona('business')}
                className={`flex items-center space-x-1.5 text-xs font-medium px-3 py-1.5 rounded-md transition-all ${
                  persona === 'business'
                    ? 'bg-amber-600 text-white shadow-sm font-semibold'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                <Building2 className="w-3.5 h-3.5" />
                <span>Business</span>
              </button>
            </div>

            {/* Language Selector */}
            <div className="relative flex items-center">
              <Languages className="w-4 h-4 text-slate-400 absolute left-2.5 pointer-events-none" />
              <select
                value={language}
                onChange={(e) => setLanguage(e.target.value)}
                className="bg-slate-800 border border-slate-700 text-slate-200 text-xs rounded-lg pl-8 pr-3 py-1.5 font-medium focus:outline-none focus:ring-2 focus:ring-emerald-500 cursor-pointer hover:border-slate-600 transition"
              >
                {LANGUAGES.map((l) => (
                  <option key={l.code} value={l.code}>
                    {l.label}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
};

