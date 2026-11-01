import React, { useState } from 'react';
import { HelpCircle, Send, CheckCircle2, AlertCircle } from 'lucide-react';
import { InterviewQuestion } from '../types';

interface InterviewCardProps {
  questions: InterviewQuestion[];
  onSubmit: (answers: Record<string, any>, units: Record<string, string>) => void;
  isSubmitting: boolean;
  language: string;
}

export const InterviewCard: React.FC<InterviewCardProps> = ({
  questions,
  onSubmit,
  isSubmitting,
}) => {
  const [answers, setAnswers] = useState<Record<string, any>>({});
  const [units, setUnits] = useState<Record<string, string>>({});
  const [validationError, setValidationError] = useState<string | null>(null);

  const handleInputChange = (field: string, val: any) => {
    setAnswers((prev) => ({ ...prev, [field]: val }));
    setValidationError(null);
  };

  const handleUnitChange = (field: string, unitVal: string) => {
    setUnits((prev) => ({ ...prev, [field]: unitVal }));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    // Check if at least one question is answered
    const answeredCount = Object.keys(answers).filter((k) => answers[k] !== undefined && answers[k] !== '').length;
    if (answeredCount === 0) {
      setValidationError('Please answer the questions below to evaluate your eligibility.');
      return;
    }

    onSubmit(answers, units);
  };

  const getDefaultUnit = (field: string) => {
    if (field.includes('land') || field.includes('area')) return 'hectares';
    if (field.includes('income') || field.includes('turnover') || field.includes('amount')) return 'INR';
    return '';
  };

  return (
    <div className="bg-white rounded-2xl shadow-sm border-2 border-amber-300 p-5 sm:p-6 mb-6">
      <div className="flex items-center space-x-2.5 mb-4">
        <div className="p-2 bg-amber-100 text-amber-800 rounded-lg">
          <HelpCircle className="w-5 h-5" />
        </div>
        <div>
          <span className="text-xs font-bold text-amber-700 uppercase tracking-wider">
            Human-in-the-Loop Interaction
          </span>
          <h3 className="text-base font-bold text-slate-800">
            A Few Details Needed for Verification
          </h3>
          <p className="text-xs text-slate-500">
            The AI state machine paused to ask only the missing fields required by this policy.
          </p>
        </div>
      </div>

      {validationError && (
        <div className="mb-4 p-3 bg-rose-50 border border-rose-200 text-rose-700 text-xs rounded-lg flex items-center space-x-2">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>{validationError}</span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        {questions.map((q, idx) => {
          const field = q.field;
          const isLand = field.includes('land') || field.includes('area');
          const isMoney = field.includes('income') || field.includes('turnover');
          const isBoolean = q.input_type === 'boolean' || q.choices?.length === 2;

          return (
            <div key={idx} className="bg-slate-50 p-4 rounded-xl border border-slate-200">
              <label className="block text-sm font-semibold text-slate-800 mb-1">
                {q.question_text}
              </label>

              {q.help_text && (
                <p className="text-xs text-slate-500 mb-2">{q.help_text}</p>
              )}

              {/* Input rendering based on type */}
              {isBoolean ? (
                <div className="flex space-x-3 mt-2">
                  <button
                    type="button"
                    onClick={() => handleInputChange(field, true)}
                    className={`flex-1 py-2 px-4 rounded-lg text-xs font-bold border transition ${
                      answers[field] === true
                        ? 'bg-emerald-600 text-white border-emerald-600 shadow-sm'
                        : 'bg-white text-slate-700 border-slate-300 hover:bg-slate-100'
                    }`}
                  >
                    हाँ (Yes)
                  </button>
                  <button
                    type="button"
                    onClick={() => handleInputChange(field, false)}
                    className={`flex-1 py-2 px-4 rounded-lg text-xs font-bold border transition ${
                      answers[field] === false
                        ? 'bg-rose-600 text-white border-rose-600 shadow-sm'
                        : 'bg-white text-slate-700 border-slate-300 hover:bg-slate-100'
                    }`}
                  >
                    नहीं (No)
                  </button>
                </div>
              ) : (
                <div className="flex space-x-2 mt-2">
                  <input
                    type="text"
                    value={answers[field] || ''}
                    onChange={(e) => handleInputChange(field, e.target.value)}
                    placeholder={
                      isLand
                        ? 'e.g. 1.5 or 3.0'
                        : isMoney
                        ? 'e.g. 1,50,000 or 1.5 lakh'
                        : 'Enter your answer'
                    }
                    className="flex-1 px-3.5 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-amber-500 bg-white"
                  />

                  {/* Unit Dropdowns */}
                  {isLand && (
                    <select
                      value={units[field] || 'hectares'}
                      onChange={(e) => handleUnitChange(field, e.target.value)}
                      className="text-xs bg-white border border-slate-300 rounded-lg px-2.5 py-2 font-medium focus:ring-2 focus:ring-amber-500"
                    >
                      <option value="hectares">Hectares (हेक्टेयर)</option>
                      <option value="acres">Acres (एकड़)</option>
                    </select>
                  )}

                  {isMoney && (
                    <select
                      value={units[field] || 'INR'}
                      onChange={(e) => handleUnitChange(field, e.target.value)}
                      className="text-xs bg-white border border-slate-300 rounded-lg px-2.5 py-2 font-medium focus:ring-2 focus:ring-amber-500"
                    >
                      <option value="INR">INR (₹)</option>
                      <option value="lakh">Lakh (लाख)</option>
                      <option value="crore">Crore (करोड़)</option>
                    </select>
                  )}
                </div>
              )}
            </div>
          );
        })}

        <div className="pt-2">
          <button
            type="submit"
            disabled={isSubmitting}
            className={`w-full py-3 px-4 rounded-xl text-sm font-bold flex items-center justify-center space-x-2 text-white shadow-md transition ${
              isSubmitting
                ? 'bg-slate-400 cursor-not-allowed'
                : 'bg-amber-600 hover:bg-amber-700 active:scale-[0.99] shadow-amber-500/20'
            }`}
          >
            {isSubmitting ? (
              <>
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                <span>Resuming LangGraph Engine...</span>
              </>
            ) : (
              <>
                <Send className="w-4 h-4" />
                <span>Submit Answers & Calculate Eligibility</span>
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
};

